"""FastAPI application — main entry point."""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from anthropic import AnthropicBedrock

from backend.config import BASE_DIR, DOCS_DIR, AWS_REGION, SUPERVISOR_MODEL_ID
from backend.models import Intent, AuditEntry, TraceStep, HandoffContext
from backend.state.session import SessionManager
from backend.rag.retriever import retriever
from backend.agents.supervisor import classify_intent
from backend.agents.eligibility import run_eligibility_agent
from backend.agents.fnol import run_fnol_agent
from backend.agents.claims import run_claims_agent
from backend.agents.base import run_agent_loop, TOOL_DEFINITIONS
from backend.guardrails.safety import redact_pii, check_blocked_topics, detect_pii, validate_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

session_manager = SessionManager()

# WebSocket connections per session
ws_connections: Dict[str, List[WebSocket]] = {}

# Live analytics counters — tracked across all sessions
_live_analytics = {
    "intents": {"eligibility": 0, "fnol": 0, "claim_status": 0, "general": 0, "escalate": 0},
    "sentiments": {"positive": 0, "neutral": 0, "concerned": 0, "frustrated": 0, "angry": 0},
    "tools": {},
    "total_turns": 0,
    "total_sessions": 0,
    "total_latency_ms": 0,
    "escalation_count": 0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG index on startup."""
    retriever.initialize()
    logger.info("Octank Insurance Virtual Agent ready")
    yield


app = FastAPI(title="Octank Insurance Virtual Agent", lifespan=lifespan)

FRONTEND_DIR = BASE_DIR.parent / "frontend"


# ── REST API ──────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    member_id: str

class StartSessionResponse(BaseModel):
    session_id: str
    member: dict

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    agent: str = ""
    tools_called: List[dict] = []
    rag_sources: List[dict] = []
    trace_steps: List[dict] = []
    escalated: bool = False
    escalation_reason: str = ""
    handoff_context: Optional[dict] = None
    confidence: float = 1.0
    sentiment: str = "neutral"
    latency_ms: int = 0
    latency_breakdown: Dict[str, int] = {}
    guardrail_flags: List[dict] = []


class AgentDesktopResponse(BaseModel):
    session_id: str
    member: dict
    sentiment_history: List[str] = []
    current_sentiment: str = "neutral"
    conversation: List[dict] = []
    ai_summary: str = ""
    actions_taken: List[dict] = []
    knowledge_retrieved: List[dict] = []
    knowledge_proactive: List[dict] = []
    suggested_actions: List[str] = []
    open_questions: List[str] = []
    escalation: dict = {}
    session_meta: dict = {}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "octank-virtual-agent", "rag_ready": retriever._ready}


@app.get("/api/docs/{doc_name}")
def get_document(doc_name: str):
    """Serve a raw policy document for the document viewer."""
    doc_path = DOCS_DIR / doc_name
    if not doc_path.exists() or not doc_path.suffix == ".md":
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_name": doc_name, "content": doc_path.read_text(encoding="utf-8")}


@app.get("/api/members")
def list_members():
    return {"members": session_manager.get_members()}


@app.post("/api/session/start", response_model=StartSessionResponse)
def start_session(req: StartSessionRequest):
    try:
        session = session_manager.create_session(req.member_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    _live_analytics["total_sessions"] += 1

    return StartSessionResponse(
        session_id=session.session_id,
        member=session.member_data,
    )


@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return {
        "session_id": session.session_id,
        "member_id": session.member_id,
        "member": session.member_data,
        "turn_count": session.turn_count,
        "escalated": session.escalated,
        "current_agent": session.current_agent,
        "messages": session.messages,
    }


@app.get("/api/session/{session_id}/audit")
def get_audit_log(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return {"audit_log": session.audit_log}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session = session_manager.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Detect PII in user message
    pii_found = detect_pii(user_message)
    guardrail_flags = []
    if pii_found:
        guardrail_flags.append({"type": "pii_detected", "details": pii_found, "action": "redacted_in_logs"})

    # Check guardrails — blocked topics
    blocked, blocked_topic = check_blocked_topics(user_message)
    if blocked:
        session.add_message("user", user_message)
        session.add_message("assistant", blocked)
        guardrail_flags.append({"type": "topic_blocked", "topic": blocked_topic, "action": "redirected"})
        trace_data = [
            {"name": "Input Guardrails", "step_type": "guardrail", "duration_ms": 1, "status": "blocked",
             "details": {"check": "topic_blocking", "topic": blocked_topic, "result": "BLOCKED"}},
        ]
        if pii_found:
            trace_data.insert(0, {"name": "PII Detection", "step_type": "guardrail", "duration_ms": 0, "status": "warning",
                                  "details": {"pii_types": [p["type"] for p in pii_found], "action": "redacted"}})
        return ChatResponse(
            response=blocked, intent="blocked", agent="guardrails",
            trace_steps=trace_data, guardrail_flags=guardrail_flags,
        )

    # Add user message to session
    session.add_message("user", user_message)

    start_time = time.time()

    # Broadcast processing start via WebSocket
    await _ws_broadcast(session.session_id, {
        "type": "processing_started",
        "message": user_message,
    })

    # 1. Classify intent via Supervisor
    conversation_history = session.get_conversation_history()
    supervisor_start = time.time()
    intent, confidence, reasoning, sentiment = classify_intent(
        messages=conversation_history,
        member_name=session.member_data.get("name", ""),
        current_agent=session.current_agent,
    )
    supervisor_ms = int((time.time() - supervisor_start) * 1000)

    # Track sentiment history
    session.sentiment_history.append(sentiment)

    # Initialize trace steps
    trace_steps = [
        TraceStep(
            name="Supervisor Classification",
            step_type="supervisor",
            duration_ms=supervisor_ms,
            details={"intent": intent.value, "confidence": confidence, "sentiment": sentiment, "reasoning": reasoning},
        ),
        TraceStep(
            name=f"Route → {intent.value}",
            step_type="routing",
            duration_ms=0,
            details={"from": session.current_agent or "none", "to": intent.value},
        ),
    ]

    await _ws_broadcast(session.session_id, {
        "type": "intent_classified",
        "intent": intent.value,
        "confidence": confidence,
        "reasoning": reasoning,
        "sentiment": sentiment,
        "supervisor_ms": supervisor_ms,
    })

    # 2. Route to specialist agent
    member = session.member_data
    agent_kwargs = dict(
        messages=conversation_history,
        member_id=session.member_id,
        member_name=member.get("name", ""),
        policy_number=member.get("policy_number", ""),
        policy_type=member.get("policy_type", ""),
    )

    if intent == Intent.ESCALATE:
        agent_response = _handle_escalation(session, conversation_history)
    elif intent == Intent.ELIGIBILITY:
        agent_response = run_eligibility_agent(**agent_kwargs)
    elif intent == Intent.FNOL:
        agent_response = run_fnol_agent(**agent_kwargs)
    elif intent == Intent.CLAIM_STATUS:
        agent_response = run_claims_agent(**agent_kwargs)
    else:
        # General — run with all tools
        agent_response = _handle_general(session, conversation_history, agent_kwargs)

    # Merge trace steps
    all_trace_steps = trace_steps + agent_response.trace_steps

    # Add PII guardrail trace step if PII was detected in the user message
    if pii_found:
        all_trace_steps.insert(0, TraceStep(
            name="PII Detection",
            step_type="guardrail",
            duration_ms=0,
            status="warning",
            details={"pii_types": [p["type"] for p in pii_found], "action": "redacted_in_logs"},
        ))

    # Guardrails trace — response validation
    guardrail_start = time.time()
    is_valid, resp_confidence = validate_response(agent_response.text)
    guardrail_ms = int((time.time() - guardrail_start) * 1000)
    all_trace_steps.append(TraceStep(
        name="Response Guardrails",
        step_type="guardrail",
        duration_ms=guardrail_ms,
        status="success" if is_valid else "warning",
        details={"valid": is_valid, "confidence": round(resp_confidence, 2)},
    ))
    if not is_valid:
        agent_response.confidence = resp_confidence

    # Update session state
    session.current_intent = intent.value
    session.current_agent = agent_response.agent_name
    session.add_message("assistant", agent_response.text)

    if agent_response.escalated:
        session.escalated = True

    for tc in agent_response.tools_called:
        session.tools_called.append(tc.tool_name)

    # Store full RAG data in session for agent desktop
    for rs in agent_response.rag_sources:
        session.rag_history.append({
            "source_doc": rs.source_doc,
            "heading": rs.heading,
            "chunk_text": rs.chunk_text,
            "relevance_score": rs.relevance_score,
            "turn": session.turn_count,
            "intent": intent.value,
        })

    # Build handoff context if escalated
    handoff_ctx = None
    if agent_response.escalated:
        handoff_ctx = HandoffContext(
            summary=agent_response.escalation_reason,
            intent=intent.value,
            actions_taken=[tc.tool_name for tc in agent_response.tools_called],
            open_questions=[],
            retrieved_docs=[rs.source_doc for rs in agent_response.rag_sources],
            sentiment=sentiment,
        )
        all_trace_steps.append(TraceStep(
            name="Escalation Handoff",
            step_type="escalation",
            details={"reason": agent_response.escalation_reason, "sentiment": sentiment},
        ))

    # Compute latency breakdown
    latency = int((time.time() - start_time) * 1000)
    tools_ms = sum(tc.duration_ms for tc in agent_response.tools_called)
    generation_ms = max(0, latency - supervisor_ms - tools_ms - guardrail_ms)
    latency_breakdown = {
        "classification_ms": supervisor_ms,
        "tools_ms": tools_ms,
        "generation_ms": generation_ms,
        "guardrails_ms": guardrail_ms,
    }

    # Flag for review queue if low confidence
    if agent_response.confidence < 0.7:
        session.review_queue.append({
            "turn": session.turn_count,
            "intent": intent.value,
            "confidence": round(agent_response.confidence, 2),
            "response_preview": agent_response.text[:150],
            "reason": "low_confidence",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Audit log
    audit = AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        session_id=session.session_id,
        member_id=session.member_id,
        turn=session.turn_count,
        user_message=redact_pii(user_message),
        intent=intent.value,
        agent=agent_response.agent_name,
        tools_called=[tc.tool_name for tc in agent_response.tools_called],
        rag_sources=[rs.source_doc for rs in agent_response.rag_sources],
        response=redact_pii(agent_response.text[:200]),
        latency_ms=latency,
        sentiment=sentiment,
    )
    session.add_audit_entry(audit)
    logger.info(f"[Audit] Turn {session.turn_count}: {intent.value} → {agent_response.agent_name} | sentiment={sentiment} ({latency}ms)")

    # Update live analytics
    _live_analytics["intents"][intent.value] = _live_analytics["intents"].get(intent.value, 0) + 1
    _live_analytics["sentiments"][sentiment] = _live_analytics["sentiments"].get(sentiment, 0) + 1
    for tc in agent_response.tools_called:
        _live_analytics["tools"][tc.tool_name] = _live_analytics["tools"].get(tc.tool_name, 0) + 1
    _live_analytics["total_turns"] += 1
    _live_analytics["total_latency_ms"] += latency
    if agent_response.escalated:
        _live_analytics["escalation_count"] += 1

    # Serialize for response
    tools_data = [
        {"tool": tc.tool_name, "input": tc.tool_input, "output": tc.tool_output, "duration_ms": tc.duration_ms}
        for tc in agent_response.tools_called
    ]
    rag_data = [
        {"source_doc": rs.source_doc, "heading": rs.heading, "chunk_text": rs.chunk_text, "relevance_score": rs.relevance_score}
        for rs in agent_response.rag_sources
    ]
    trace_data = [
        {"name": ts.name, "step_type": ts.step_type, "duration_ms": ts.duration_ms, "status": ts.status, "details": ts.details}
        for ts in all_trace_steps
    ]
    handoff_data = None
    if handoff_ctx:
        handoff_data = {
            "summary": handoff_ctx.summary,
            "intent": handoff_ctx.intent,
            "actions_taken": handoff_ctx.actions_taken,
            "open_questions": handoff_ctx.open_questions,
            "retrieved_docs": handoff_ctx.retrieved_docs,
            "sentiment": handoff_ctx.sentiment,
        }

    # Broadcast completion
    await _ws_broadcast(session.session_id, {
        "type": "response_ready",
        "response": agent_response.text,
        "intent": intent.value,
        "agent": agent_response.agent_name,
        "tools_called": tools_data,
        "rag_sources": rag_data,
        "trace_steps": trace_data,
        "escalated": agent_response.escalated,
        "handoff_context": handoff_data,
        "sentiment": sentiment,
        "latency_ms": latency,
    })

    return ChatResponse(
        response=agent_response.text,
        intent=intent.value,
        agent=agent_response.agent_name,
        tools_called=tools_data,
        rag_sources=rag_data,
        trace_steps=trace_data,
        escalated=agent_response.escalated,
        escalation_reason=agent_response.escalation_reason,
        handoff_context=handoff_data,
        confidence=agent_response.confidence,
        sentiment=sentiment,
        latency_ms=latency,
        latency_breakdown=latency_breakdown,
        guardrail_flags=guardrail_flags,
    )


def _handle_escalation(session, conversation_history):
    """Handle escalation intent."""
    from backend.tools.claims_api import escalate_to_human
    from backend.models import AgentResponse, ToolCall

    summary = " | ".join(
        f"{m['role']}: {m['content'][:80]}" for m in conversation_history[-6:]
    )
    result = escalate_to_human("Member requested human agent", summary)
    return AgentResponse(
        text=result["message"],
        intent=Intent.ESCALATE,
        agent_name="escalation_handler",
        tools_called=[ToolCall("escalate_to_human", {"reason": "member_request"}, result)],
        escalated=True,
        escalation_reason="member_request",
    )


def _handle_general(session, conversation_history, agent_kwargs):
    """Handle general intent with a friendly response."""
    system_prompt = f"""You are the Octank Insurance virtual assistant. You're friendly, professional, and helpful.

Member: {agent_kwargs['member_name']} (ID: {agent_kwargs['member_id']})
Policy: {agent_kwargs['policy_number']}

You can help with:
- Checking coverage and eligibility
- Filing a new claim (FNOL)
- Checking claim status
- Answering questions about their policy

If the member greets you, welcome them warmly and let them know what you can help with.
If you're unsure what they need, ask a clarifying question.
Use search_knowledge_base if they ask general policy questions.
"""
    tools = [TOOL_DEFINITIONS["search_knowledge_base"], TOOL_DEFINITIONS["schedule_callback"]]
    return run_agent_loop(
        system_prompt=system_prompt,
        messages=conversation_history,
        tools=tools,
        agent_name="general_agent",
        intent=Intent.GENERAL,
    )


# ── Agent Desktop ─────────────────────────────────────────────────────

_haiku_client = AnthropicBedrock(aws_region=AWS_REGION)


def _tool_description(tool_name: str) -> str:
    """Human-readable description of a tool action."""
    descriptions = {
        "get_eligibility": "Checked member coverage and eligibility details",
        "get_claim_status": "Retrieved claim status and timeline",
        "create_fnol": "Filed a First Notice of Loss claim",
        "search_knowledge_base": "Searched policy knowledge base",
        "escalate_to_human": "Escalated conversation to human agent",
        "schedule_callback": "Scheduled a callback for the member",
    }
    return descriptions.get(tool_name, f"Called {tool_name}")


def _generate_conversation_summary(session) -> str:
    """Use Haiku to generate a concise agent briefing."""
    convo = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in session.messages
    )
    prompt = f"""You are preparing a briefing for a human insurance agent who is about to take over this conversation.

Member: {session.member_data.get('name', 'Unknown')} (ID: {session.member_id})
Policy: {session.member_data.get('policy_number', 'N/A')} ({session.member_data.get('policy_type', 'N/A')})

Conversation:
{convo}

Sentiment progression: {', '.join(session.sentiment_history) if session.sentiment_history else 'neutral'}

Write a 3-5 sentence briefing covering:
1. WHO the member is and their policy type
2. WHAT they needed help with
3. WHAT the AI agent did (tools used, information provided)
4. WHAT is still unresolved or why they were escalated
5. The member's EMOTIONAL STATE

Be concise and actionable. Write in third person."""

    try:
        resp = _haiku_client.messages.create(
            model=SUPERVISOR_MODEL_ID,
            max_tokens=400,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        summary_parts = []
        for m in session.messages[-6:]:
            summary_parts.append(f"{m['role']}: {m['content'][:80]}")
        return "AI summary unavailable. Recent conversation: " + " | ".join(summary_parts)


def _generate_agent_guidance(session) -> tuple:
    """Use Haiku to generate suggested actions and open questions in a single call."""
    convo = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in session.messages[-10:]
    )
    tools_used = ", ".join(session.tools_called) if session.tools_called else "none"

    prompt = f"""You are an AI assistant helping a human insurance agent prepare to handle this conversation.

Member: {session.member_data.get('name', 'Unknown')}
Policy type: {session.member_data.get('policy_type', 'N/A')}
Tools already used by AI: {tools_used}
Current intent: {session.current_intent}

Recent conversation:
{convo}

Provide TWO sections in valid JSON format:

{{
  "suggested_actions": [
    "3-5 specific, actionable next steps the human agent should take"
  ],
  "open_questions": [
    "2-4 unresolved items or questions the agent should address"
  ]
}}

Be specific to this member's situation. Use imperative verbs (e.g., "Review...", "Confirm...", "Offer...")."""

    try:
        resp = _haiku_client.messages.create(
            model=SUPERVISOR_MODEL_ID,
            max_tokens=500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            return (
                data.get("suggested_actions", []),
                data.get("open_questions", []),
            )
    except Exception as e:
        logger.error(f"Guidance generation failed: {e}")

    return (
        ["Review conversation history", "Address member's primary concern", "Check if additional follow-up needed"],
        ["What is the member's primary unresolved issue?"],
    )


def _do_contextual_knowledge_retrieval(session) -> list:
    """Retrieve policy docs based on conversation context when the AI didn't call search_knowledge_base."""
    # Build query from both user messages and the conversation intent
    user_messages = [m["content"] for m in session.messages if m["role"] == "user"]
    intent_terms = {
        "eligibility": "coverage eligibility deductible benefits",
        "fnol": "claim filing accident loss damage",
        "claim_status": "claim status timeline adjuster",
        "general": "",
        "escalate": "",
    }
    boost = intent_terms.get(session.current_intent, "")
    query = " ".join(user_messages[-5:]) + " " + boost

    if not query.strip():
        return []

    results = retriever.search(query.strip(), top_k=5)
    return [
        {
            "source_doc": r["source_doc"],
            "heading": r.get("heading", ""),
            "chunk_text": r["chunk_text"],
            "relevance_score": r["relevance_score"],
            "turn": 0,
            "intent": session.current_intent,
        }
        for r in results
    ]


def _do_proactive_knowledge_retrieval(session) -> list:
    """Run a fresh RAG search using full conversation context — returns full chunk text."""
    # Build a rich query from the conversation
    user_messages = [m["content"] for m in session.messages if m["role"] == "user"]
    query = " ".join(user_messages[-5:])  # Last 5 user messages as context

    if not query.strip():
        return []

    results = retriever.search(query, top_k=6)
    return [
        {
            "source_doc": r["source_doc"],
            "heading": r.get("heading", ""),
            "chunk_text": r["chunk_text"],  # Full text, not truncated
            "relevance_score": r["relevance_score"],
        }
        for r in results
    ]


@app.get("/api/agent-desktop/{session_id}", response_model=AgentDesktopResponse)
async def get_agent_desktop(session_id: str):
    """Assemble full agent context package for the human agent desktop."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    start_time = time.time()

    # Run LLM calls and proactive RAG in parallel
    loop = asyncio.get_event_loop()
    summary_future = loop.run_in_executor(None, _generate_conversation_summary, session)
    guidance_future = loop.run_in_executor(None, _generate_agent_guidance, session)
    knowledge_future = loop.run_in_executor(None, _do_proactive_knowledge_retrieval, session)

    ai_summary, (suggested_actions, open_questions), proactive_knowledge = await asyncio.gather(
        summary_future, guidance_future, knowledge_future
    )

    # Build actions taken from audit log
    actions_taken = []
    for entry in session.audit_log:
        for tool_name in entry.get("tools_called", []):
            actions_taken.append({
                "tool": tool_name,
                "description": _tool_description(tool_name),
                "turn": entry.get("turn", 0),
                "intent": entry.get("intent", ""),
            })

    # Collect knowledge retrieved during chat (full RAG data from session)
    # If the AI agent didn't call search_knowledge_base (common for eligibility/FNOL/claims
    # flows that use specific tools), do a contextual retrieval so the human agent still
    # sees relevant policy documents in the Retrieved tab.
    if session.rag_history:
        knowledge_retrieved = [
            {
                "source_doc": r["source_doc"],
                "heading": r.get("heading", ""),
                "chunk_text": r["chunk_text"],
                "relevance_score": r["relevance_score"],
                "turn": r.get("turn", 0),
                "intent": r.get("intent", ""),
            }
            for r in session.rag_history
        ]
    else:
        # Contextual retrieval: search using conversation topics
        knowledge_retrieved = await loop.run_in_executor(
            None, _do_contextual_knowledge_retrieval, session
        )

    # Current sentiment
    current_sentiment = session.sentiment_history[-1] if session.sentiment_history else "neutral"

    # Escalation details
    escalation = {}
    if session.escalated:
        escalation = {
            "escalated": True,
            "reason": next(
                (e.get("intent", "") for e in reversed(session.audit_log) if "escalate" in str(e.get("tools_called", []))),
                session.current_intent,
            ),
            "turn": session.turn_count,
            "timestamp": session.audit_log[-1].get("timestamp", "") if session.audit_log else "",
        }

    latency = int((time.time() - start_time) * 1000)
    logger.info(f"[AgentDesktop] Context assembled for {session_id} in {latency}ms")

    return AgentDesktopResponse(
        session_id=session.session_id,
        member=session.member_data,
        sentiment_history=session.sentiment_history,
        current_sentiment=current_sentiment,
        conversation=session.messages,
        ai_summary=ai_summary,
        actions_taken=actions_taken,
        knowledge_retrieved=knowledge_retrieved,
        knowledge_proactive=proactive_knowledge,
        suggested_actions=suggested_actions,
        open_questions=open_questions,
        escalation=escalation,
        session_meta={
            "created_at": session.created_at,
            "turn_count": session.turn_count,
            "current_intent": session.current_intent,
            "current_agent": session.current_agent,
            "tools_used_count": len(session.tools_called),
            "assembly_ms": latency,
        },
    )


# ── Analytics & Review Queue ──────────────────────────────────────────

@app.get("/api/analytics")
def get_analytics():
    """Return analytics data — mock historical baseline + live session metrics."""
    sessions = session_manager.list_sessions()
    live = _live_analytics

    # Merge live counts onto mock baselines
    mock_intents = {"eligibility": 412, "fnol": 287, "claim_status": 334, "general": 156, "escalate": 58}
    merged_intents = {k: mock_intents.get(k, 0) + live["intents"].get(k, 0) for k in mock_intents}
    total_conv = 1247 + live["total_sessions"]

    mock_tools = {"search_knowledge_base": 567, "get_eligibility": 398, "get_claim_status": 312,
                  "create_fnol": 189, "schedule_callback": 78, "escalate_to_human": 58}
    merged_tools = {k: mock_tools.get(k, 0) + live["tools"].get(k, 0) for k in mock_tools}
    # Include any tools only seen in live data
    for k, v in live["tools"].items():
        if k not in merged_tools:
            merged_tools[k] = v

    mock_sentiments = {"positive": 42, "neutral": 38, "concerned": 12, "frustrated": 6, "angry": 2}
    total_live_sentiments = sum(live["sentiments"].values()) or 1
    merged_escalations = 58 + live["escalation_count"]

    # Use fixed realistic KPIs — small live deltas won't skew them
    base_containment = 73  # Realistic for insurance vertical
    base_escalation_rate = 8
    # Live escalations only nudge slightly
    live_esc = live["escalation_count"]
    adj_containment = max(60, base_containment - live_esc)
    adj_escalation = min(25, base_escalation_rate + live_esc)

    # Sentiment: fixed realistic percentages, live data shown as a separate field
    sentiment_pcts = {"positive": 42, "neutral": 38, "concerned": 12, "frustrated": 6, "angry": 2}

    return {
        "containment_rate": adj_containment,
        "total_conversations": total_conv,
        "avg_handle_time_seconds": 142,
        "escalation_rate": adj_escalation,
        "csat_score": 4.2,
        "first_contact_resolution": 68,
        "intent_distribution": [
            {"intent": k, "count": v, "pct": round(v / max(sum(merged_intents.values()), 1) * 100)}
            for k, v in merged_intents.items()
        ],
        "avg_handle_time_by_intent": [
            {"intent": "eligibility", "seconds": 95},
            {"intent": "fnol", "seconds": 210},
            {"intent": "claim_status", "seconds": 120},
            {"intent": "general", "seconds": 45},
        ],
        "escalation_reasons": [
            {"reason": "Member request", "count": 22 + live_esc},
            {"reason": "Injury reported", "count": 15},
            {"reason": "Complex claim", "count": 12},
            {"reason": "System limitation", "count": 6},
            {"reason": "Frustrated member", "count": 3},
        ],
        "tool_call_frequency": [
            {"tool": k, "count": v} for k, v in sorted(merged_tools.items(), key=lambda x: -x[1])
        ],
        "daily_volume": [
            {"day": "Mon", "count": 198},
            {"day": "Tue", "count": 234},
            {"day": "Wed", "count": 212},
            {"day": "Thu", "count": 187},
            {"day": "Fri", "count": 241},
            {"day": "Sat", "count": 98},
            {"day": "Sun", "count": 77},
        ],
        "sentiment_distribution": [
            {"sentiment": k, "pct": v}
            for k, v in sentiment_pcts.items()
        ],
        "hourly_pattern": [
            {"hour": "8am", "count": 45}, {"hour": "9am", "count": 112},
            {"hour": "10am", "count": 156}, {"hour": "11am", "count": 134},
            {"hour": "12pm", "count": 98}, {"hour": "1pm", "count": 123},
            {"hour": "2pm", "count": 145}, {"hour": "3pm", "count": 167},
            {"hour": "4pm", "count": 132}, {"hour": "5pm", "count": 78},
        ],
        "active_sessions": len(sessions),
        "live_session_turns": live["total_turns"],
    }


@app.get("/api/review-queue/{session_id}")
def get_review_queue(session_id: str):
    """Return flagged responses for human review."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"items": session.review_queue}


# ── WebSocket ─────────────────────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    if session_id not in ws_connections:
        ws_connections[session_id] = []
    ws_connections[session_id].append(websocket)

    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        ws_connections[session_id].remove(websocket)
        if not ws_connections[session_id]:
            del ws_connections[session_id]


async def _ws_broadcast(session_id: str, data: dict):
    """Broadcast a message to all WebSocket connections for a session."""
    connections = ws_connections.get(session_id, [])
    for ws in connections:
        try:
            await ws.send_json(data)
        except Exception:
            pass


# ── Static files (frontend) ──────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
