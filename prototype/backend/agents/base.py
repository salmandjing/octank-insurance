"""Base agent with agentic tool-use loop.

Handles the core pattern: send message → Claude responds → execute tools → repeat.
Uses AWS Bedrock for Claude access.
"""
from __future__ import annotations
import json
import time
import logging
from typing import Any
from anthropic import AnthropicBedrock

from backend.config import AWS_REGION, SPECIALIST_MODEL_ID, MAX_TOKENS, TEMPERATURE, MAX_AGENT_STEPS
from backend.models import AgentResponse, ToolCall, RAGSource, TraceStep, Intent

logger = logging.getLogger(__name__)

client = AnthropicBedrock(aws_region=AWS_REGION)


# Tool definitions shared across agents
TOOL_DEFINITIONS = {
    "get_eligibility": {
        "name": "get_eligibility",
        "description": "Retrieve eligibility and coverage details for the authenticated member. Returns coverage type, deductible, limits, and benefits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "member_id": {
                    "type": "string",
                    "description": "The member ID to look up"
                }
            },
            "required": ["member_id"]
        }
    },
    "get_claim_status": {
        "name": "get_claim_status",
        "description": "Retrieve claim status, timeline, and next steps. If no claim_id provided, returns all recent claims for the member.",
        "input_schema": {
            "type": "object",
            "properties": {
                "member_id": {
                    "type": "string",
                    "description": "The member ID"
                },
                "claim_id": {
                    "type": "string",
                    "description": "Optional specific claim ID. If omitted, returns all claims for the member."
                }
            },
            "required": ["member_id"]
        }
    },
    "create_fnol": {
        "name": "create_fnol",
        "description": "File a First Notice of Loss (FNOL) claim. IMPORTANT: Only call this AFTER the member has explicitly confirmed they want to file. Present a summary of collected information and ask for confirmation first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "member_id": {"type": "string", "description": "The member ID"},
                "date_of_loss": {"type": "string", "description": "Date of the incident (YYYY-MM-DD)"},
                "description": {"type": "string", "description": "Description of what happened"},
                "location": {"type": "string", "description": "Location of the incident"},
                "injuries": {"type": "boolean", "description": "Whether anyone was injured"},
                "injury_description": {"type": "string", "description": "Description of injuries if any"},
                "police_report_number": {"type": "string", "description": "Police report number if filed"}
            },
            "required": ["member_id", "date_of_loss", "description"]
        }
    },
    "search_knowledge_base": {
        "name": "search_knowledge_base",
        "description": "Search Octank Insurance policy documents and knowledge base. Use this to find information about coverage details, procedures, deductibles, filing requirements, and policy terms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query describing what information is needed"
                }
            },
            "required": ["query"]
        }
    },
    "escalate_to_human": {
        "name": "escalate_to_human",
        "description": "Escalate the conversation to a human claims specialist. Use when: the member explicitly asks for a human, the issue involves injuries/fatality, sentiment is very negative, or you cannot resolve the issue.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Reason for escalation"
                },
                "conversation_summary": {
                    "type": "string",
                    "description": "Brief summary of the conversation so far for the human agent"
                }
            },
            "required": ["reason", "conversation_summary"]
        }
    },
    "schedule_callback": {
        "name": "schedule_callback",
        "description": "Schedule a callback from a human agent. Use when the member wants to be called back rather than wait on hold, or when they need to speak with someone but not urgently.",
        "input_schema": {
            "type": "object",
            "properties": {
                "member_id": {
                    "type": "string",
                    "description": "The member ID"
                },
                "preferred_time": {
                    "type": "string",
                    "description": "Member's preferred callback time (e.g. 'tomorrow morning', '2pm today')"
                },
                "phone_number": {
                    "type": "string",
                    "description": "Phone number to call back on. If not provided, uses number on file."
                },
                "reason": {
                    "type": "string",
                    "description": "Brief reason for the callback request"
                }
            },
            "required": ["member_id"]
        }
    }
}


# Tool executors
def _execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool and return the result."""
    from backend.tools.eligibility_api import get_eligibility
    from backend.tools.claims_api import get_claim_status, create_fnol, escalate_to_human, schedule_callback
    from backend.tools.knowledge_base import search_knowledge_base

    executors = {
        "get_eligibility": lambda args: get_eligibility(**args),
        "get_claim_status": lambda args: get_claim_status(**args),
        "create_fnol": lambda args: create_fnol(**args),
        "search_knowledge_base": lambda args: search_knowledge_base(**args),
        "escalate_to_human": lambda args: escalate_to_human(**args),
        "schedule_callback": lambda args: schedule_callback(**args),
    }

    executor = executors.get(tool_name)
    if not executor:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        return executor(tool_input)
    except Exception as e:
        logger.error(f"Tool execution error [{tool_name}]: {e}")
        return {"error": str(e)}


def run_agent_loop(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    agent_name: str = "agent",
    intent: Intent | None = None,
) -> AgentResponse:
    """Run the agentic tool-use loop.

    Sends messages to Claude, executes any tool calls, feeds results back,
    and repeats until Claude produces a final text response or max steps reached.
    """
    start_time = time.time()
    working_messages = [_normalize_message(m) for m in messages]
    tools_called: list[ToolCall] = []
    rag_sources: list[RAGSource] = []
    trace_steps: list[TraceStep] = []
    escalated = False
    escalation_reason = ""

    # Trace: specialist started
    trace_steps.append(TraceStep(
        name=f"{agent_name} started",
        step_type="specialist",
        details={"model": SPECIALIST_MODEL_ID, "tools_available": [t["name"] for t in tools]},
    ))

    for step in range(MAX_AGENT_STEPS):
        logger.info(f"[{agent_name}] Step {step + 1}/{MAX_AGENT_STEPS}")
        llm_start = time.time()

        response = client.messages.create(
            model=SPECIALIST_MODEL_ID,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            system=system_prompt,
            messages=working_messages,
            tools=tools,
        )
        llm_ms = int((time.time() - llm_start) * 1000)

        # Check for tool use
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Final text response
            text = "".join(b.text for b in response.content if b.type == "text")
            latency = int((time.time() - start_time) * 1000)

            trace_steps.append(TraceStep(
                name="Response generated",
                step_type="specialist",
                duration_ms=llm_ms,
                details={"step": step + 1, "response_length": len(text)},
            ))

            return AgentResponse(
                text=text,
                intent=intent,
                agent_name=agent_name,
                tools_called=tools_called,
                rag_sources=rag_sources,
                trace_steps=trace_steps,
                escalated=escalated,
                escalation_reason=escalation_reason,
                latency_ms=latency,
            )

        # Execute tools and collect results
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        working_messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tool_block in tool_use_blocks:
            logger.info(f"[{agent_name}] Calling tool: {tool_block.name}")
            tool_start = time.time()
            result = _execute_tool(tool_block.name, tool_block.input)
            tool_ms = int((time.time() - tool_start) * 1000)

            # Determine tool type for trace
            is_read = tool_block.name in ("get_eligibility", "get_claim_status", "search_knowledge_base")
            tool_type = "rag_search" if tool_block.name == "search_knowledge_base" else "tool_call"

            tool_call = ToolCall(
                tool_name=tool_block.name,
                tool_input=tool_block.input,
                tool_output=result,
                duration_ms=tool_ms,
            )
            tools_called.append(tool_call)

            trace_steps.append(TraceStep(
                name=f"Tool: {tool_block.name}",
                step_type=tool_type,
                duration_ms=tool_ms,
                status="error" if "error" in result else "success",
                details={
                    "input": {k: str(v)[:80] for k, v in tool_block.input.items()},
                    "access": "read" if is_read else "write",
                },
            ))

            # Track RAG sources
            if tool_block.name == "search_knowledge_base" and "results" in result:
                for r in result["results"]:
                    rag_sources.append(RAGSource(
                        chunk_text=r.get("chunk_text", ""),
                        source_doc=r.get("source_doc", ""),
                        heading=r.get("heading", ""),
                        relevance_score=r.get("relevance_score", 0),
                    ))

            # Track escalation
            if tool_block.name == "escalate_to_human":
                escalated = True
                escalation_reason = tool_block.input.get("reason", "")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": json.dumps(result),
            })

        working_messages.append({"role": "user", "content": tool_results})

    # Max steps exceeded
    latency = int((time.time() - start_time) * 1000)
    trace_steps.append(TraceStep(
        name="Max steps exceeded",
        step_type="escalation",
        status="error",
        details={"max_steps": MAX_AGENT_STEPS},
    ))
    return AgentResponse(
        text="I apologize, but I'm having difficulty processing your request. Let me connect you with a specialist who can help.",
        intent=intent,
        agent_name=agent_name,
        tools_called=tools_called,
        rag_sources=rag_sources,
        trace_steps=trace_steps,
        escalated=True,
        escalation_reason="max_steps_exceeded",
        latency_ms=latency,
    )


def _normalize_message(msg: dict) -> dict:
    """Ensure message has the right format for the API."""
    if isinstance(msg.get("content"), str):
        return {"role": msg["role"], "content": msg["content"]}
    return msg
