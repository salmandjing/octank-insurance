"""Base agent with agentic tool-use loop.

Handles the core pattern: send message -> Claude responds -> execute tools -> repeat.
Uses the Anthropic API directly (ANTHROPIC_API_KEY env var).
"""
from __future__ import annotations
import json
import time
import logging
from typing import Any
import anthropic

from backend.config import SPECIALIST_MODEL, MAX_TOKENS, TEMPERATURE, MAX_AGENT_STEPS
from backend.models import AgentResponse, ToolCall, RAGSource, TraceStep, Intent

logger = logging.getLogger(__name__)

client = anthropic.Anthropic()


# Tool definitions shared across agents
TOOL_DEFINITIONS = {
    "lookup_policy": {
        "name": "lookup_policy",
        "description": "Look up a policy by number or ID. Returns full policy details including coverage, carrier, status, effective dates, and client info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_number": {"type": "string", "description": "The policy number to look up"}
            },
            "required": ["policy_number"]
        }
    },
    "lookup_client": {
        "name": "lookup_client",
        "description": "Look up a client by name (fuzzy match). Returns client details and all associated policies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "The client name to search for"}
            },
            "required": ["client_name"]
        }
    },
    "verify_coverage": {
        "name": "verify_coverage",
        "description": "Verify that a specific loss type is potentially covered under a policy as of the date of loss.",
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_id": {"type": "string", "description": "The policy ID"},
                "date_of_loss": {"type": "string", "description": "Date of loss (YYYY-MM-DD)"},
                "loss_type": {"type": "string", "description": "Type of loss (collision, comprehensive, property, wind, hail, fire, theft, liability, etc.)"}
            },
            "required": ["policy_id", "date_of_loss", "loss_type"]
        }
    },
    "get_carrier_requirements": {
        "name": "get_carrier_requirements",
        "description": "Get the FNOL requirements for a specific carrier.",
        "input_schema": {
            "type": "object",
            "properties": {
                "carrier_id": {"type": "string", "description": "The carrier ID"}
            },
            "required": ["carrier_id"]
        }
    },
    "get_claim_status": {
        "name": "get_claim_status",
        "description": "Retrieve claim status, timeline, and next steps for a client.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "The client ID"},
                "claim_id": {"type": "string", "description": "Optional specific claim ID"}
            },
            "required": ["client_id"]
        }
    },
    "search_knowledge_base": {
        "name": "search_knowledge_base",
        "description": "Search Prairie Shield's policy documents and knowledge base for procedures, coverage info, and regulations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    "escalate_to_human": {
        "name": "escalate_to_human",
        "description": "Escalate the conversation to a human CSR or agency principal.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for escalation"},
                "conversation_summary": {"type": "string", "description": "Brief summary of the conversation"}
            },
            "required": ["reason", "conversation_summary"]
        }
    }
}


# Tool executors
def _execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool and return the result."""
    from backend.tools.ams_api import lookup_policy, lookup_client, verify_coverage
    from backend.tools.carrier_api import get_carrier_requirements
    from backend.tools.claims_api import get_claim_status, escalate_to_human
    from backend.tools.knowledge_base import search_knowledge_base

    executors = {
        "lookup_policy": lambda args: lookup_policy(**args),
        "lookup_client": lambda args: lookup_client(**args),
        "verify_coverage": lambda args: verify_coverage(**args),
        "get_carrier_requirements": lambda args: get_carrier_requirements(**args),
        "get_claim_status": lambda args: get_claim_status(**args),
        "search_knowledge_base": lambda args: search_knowledge_base(**args),
        "escalate_to_human": lambda args: escalate_to_human(**args),
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
        details={"model": SPECIALIST_MODEL, "tools_available": [t["name"] for t in tools]},
    ))

    for step in range(MAX_AGENT_STEPS):
        logger.info(f"[{agent_name}] Step {step + 1}/{MAX_AGENT_STEPS}")
        llm_start = time.time()

        response = client.messages.create(
            model=SPECIALIST_MODEL,
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
            is_read = tool_block.name in ("lookup_policy", "lookup_client", "verify_coverage", "get_claim_status", "search_knowledge_base")
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
