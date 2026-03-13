"""ClaimFlow AI — FastAPI application entry point."""
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
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BASE_DIR, DOCS_DIR
from backend.models import (
    Intent, FNOL_INTENTS, Priority, AuditEntry, TraceStep, HandoffContext, ClaimStatus,
)
from backend.state.session import SessionManager, ClaimPipeline
from backend.rag.retriever import retriever
from backend.agents.supervisor import classify_intent
from backend.agents.email_parser import parse_email
from backend.agents.fnol import run_fnol_agent
from backend.agents.policy_lookup import run_policy_lookup_agent
from backend.agents.claims import run_claims_agent
from backend.agents.base import run_agent_loop, TOOL_DEFINITIONS
from backend.carriers.router import carrier_router
from backend.tools.ams_api import lookup_policy, lookup_client, verify_coverage
from backend.tools.carrier_api import get_carrier_requirements
from backend.tools.document_generator import (
    generate_carrier_submission, generate_client_confirmation, generate_followup_email,
)
from backend.tools.email_intake import get_sample_email, list_scenarios, SAMPLE_EMAILS
from backend.tools.claims_api import create_claim_record
from backend.guardrails.safety import (
    redact_pii, check_blocked_topics, detect_pii, validate_response, check_compliance_flags,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

session_manager = SessionManager()
claim_pipeline = ClaimPipeline()

ws_connections: Dict[str, List[WebSocket]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG index on startup."""
    retriever.initialize()
    logger.info("ClaimFlow AI ready — Prairie Shield Insurance Group")
    yield


app = FastAPI(title="ClaimFlow AI — FNOL Automation", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = BASE_DIR.parent / "frontend"


# ── Pydantic models ──────────────────────────────────────────────────

class EmailIntakeRequest(BaseModel):
    email_text: str
    from_address: str = ""
    subject: str = ""

class ClaimApproveRequest(BaseModel):
    extraction: dict = {}

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
    priority: str = "normal"
    latency_ms: int = 0
    latency_breakdown: Dict[str, int] = {}
    guardrail_flags: List[dict] = []


# ── Health & Data ────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "claimflow-ai", "rag_ready": retriever._ready}


@app.get("/api/clients")
def list_clients():
    return {"clients": session_manager.get_clients()}


@app.get("/api/policies")
def list_policies():
    from backend.state.session import get_policies_db
    policies = get_policies_db()
    return {"policies": list(policies.values())}


@app.get("/api/policies/search")
def search_policies(q: str = ""):
    from backend.state.session import get_policies_db, get_clients_db
    if not q:
        return {"results": []}
    policies = get_policies_db()
    clients = get_clients_db()
    results = []
    q_lower = q.lower()
    for pid, pol in policies.items():
        pn = pol.get("policy_number", "").lower()
        client = clients.get(pol.get("client_id", ""), {})
        cname = client.get("name", "").lower()
        if q_lower in pn or q_lower in pid.lower() or q_lower in cname:
            results.append({**pol, "client_name": client.get("name", "")})
    return {"results": results}


@app.get("/api/policies/{policy_id}")
def get_policy(policy_id: str):
    from backend.state.session import get_policies_db
    policies = get_policies_db()
    pol = policies.get(policy_id)
    if not pol:
        for pid, p in policies.items():
            if p.get("policy_number", "") == policy_id:
                pol = p
                break
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found")
    return pol


@app.get("/api/carriers")
def list_carriers():
    from backend.state.session import get_carriers_db
    return {"carriers": list(get_carriers_db().values())}


@app.get("/api/carriers/{carrier_id}")
def get_carrier(carrier_id: str):
    from backend.state.session import get_carriers_db
    carriers = get_carriers_db()
    carrier = carriers.get(carrier_id)
    if not carrier:
        raise HTTPException(status_code=404, detail="Carrier not found")
    return carrier


@app.get("/api/docs/{doc_name}")
def get_document(doc_name: str):
    doc_path = DOCS_DIR / doc_name
    if not doc_path.exists() or not doc_path.suffix == ".md":
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_name": doc_name, "content": doc_path.read_text(encoding="utf-8")}


# ── Claims Pipeline ─────────────────────────────────────────────────

@app.post("/api/claims/intake")
async def intake_claim(req: EmailIntakeRequest):
    """Submit an email for FNOL processing. Core pipeline endpoint."""
    start_time = time.time()
    all_trace = []

    # 1. Create claim record
    record = claim_pipeline.create_claim(
        email_raw=req.email_text,
        email_from=req.from_address,
        email_subject=req.subject,
    )
    all_trace.append({"name": "Email Received", "step_type": "intake", "duration_ms": 0,
                       "status": "success", "details": {"claim_id": record.claim_id, "from": req.from_address}})

    await _ws_broadcast("claims", {"type": "email_received", "claim_id": record.claim_id,
                                     "from": req.from_address, "subject": req.subject})

    # 2. Parse email
    record.status = "processing"
    await _ws_broadcast("claims", {"type": "parsing_started", "claim_id": record.claim_id})

    loop = asyncio.get_event_loop()
    extraction, parse_traces = await loop.run_in_executor(
        None, parse_email, req.email_text, req.from_address, req.subject
    )
    all_trace.extend([{"name": t.name, "step_type": t.step_type, "duration_ms": t.duration_ms,
                        "status": t.status, "details": t.details} for t in parse_traces])

    record.extraction = {
        "reporter_name": extraction.reporter_name,
        "reporter_email": extraction.reporter_email,
        "reporter_phone": extraction.reporter_phone,
        "client_name": extraction.client_name,
        "policy_number": extraction.policy_number,
        "date_of_loss": extraction.date_of_loss,
        "time_of_loss": extraction.time_of_loss,
        "location": extraction.location,
        "loss_type": extraction.loss_type,
        "description": extraction.description,
        "injuries": extraction.injuries,
        "injury_description": extraction.injury_description,
        "police_report": extraction.police_report,
        "police_report_number": extraction.police_report_number,
        "other_parties": extraction.other_parties,
        "photos_mentioned": extraction.photos_mentioned,
        "urgency": extraction.urgency,
        "missing_fields": extraction.missing_fields,
        "confidence_score": extraction.confidence_score,
    }
    record.priority = extraction.urgency

    await _ws_broadcast("claims", {"type": "extraction_complete", "claim_id": record.claim_id,
                                     "extraction": record.extraction})

    # 3. Policy lookup
    policy_data = {}
    if extraction.policy_number:
        await _ws_broadcast("claims", {"type": "policy_lookup_started", "claim_id": record.claim_id})
        pol_start = time.time()
        policy_data = await loop.run_in_executor(None, lookup_policy, extraction.policy_number)
        pol_ms = int((time.time() - pol_start) * 1000)
        all_trace.append({"name": "Policy Lookup", "step_type": "tool_call", "duration_ms": pol_ms,
                           "status": "error" if "error" in policy_data else "success",
                           "details": {"policy_number": extraction.policy_number,
                                       "found": "error" not in policy_data}})
        record.policy_data = policy_data

        if "error" not in policy_data:
            await _ws_broadcast("claims", {"type": "policy_verified", "claim_id": record.claim_id,
                                             "policy": {"carrier": policy_data.get("carrier", ""),
                                                        "type": policy_data.get("type", ""),
                                                        "status": policy_data.get("status", "")}})

            # 4. Coverage verification
            if extraction.date_of_loss and extraction.loss_type:
                cov_data = await loop.run_in_executor(
                    None, verify_coverage,
                    policy_data.get("id", ""), extraction.date_of_loss, extraction.loss_type
                )
                all_trace.append({"name": "Coverage Check", "step_type": "tool_call", "duration_ms": 0,
                                   "status": "success",
                                   "details": {"potentially_covered": cov_data.get("potentially_covered", False)}})

            # 5. Carrier requirements
            carrier_id = policy_data.get("carrier_id", "")
            if carrier_id:
                await _ws_broadcast("claims", {"type": "carrier_identified", "claim_id": record.claim_id,
                                                 "carrier": policy_data.get("carrier", "")})
                carrier_data = await loop.run_in_executor(None, get_carrier_requirements, carrier_id)
                record.carrier_data = carrier_data
                all_trace.append({"name": "Carrier Requirements Loaded", "step_type": "tool_call",
                                   "duration_ms": 0, "status": "success",
                                   "details": {"carrier": carrier_data.get("carrier_name", ""),
                                               "format": carrier_data.get("submission_format", "")}})

                # 6. Validate submission completeness
                validation = carrier_router.validate_submission(carrier_id, record.extraction)
                all_trace.append({"name": "Submission Validation", "step_type": "validation",
                                   "duration_ms": 0, "status": "success" if validation.get("valid") else "warning",
                                   "details": validation})

    # 7. Compliance flags
    compliance_flags = check_compliance_flags(record.extraction)
    if compliance_flags:
        all_trace.append({"name": "Compliance Check", "step_type": "guardrail", "duration_ms": 0,
                           "status": "warning", "details": {"flags": compliance_flags}})

    # Determine final status
    if extraction.missing_fields and "policy_number" in extraction.missing_fields:
        record.status = "follow_up"
    elif extraction.confidence_score >= 0.7 and "error" not in policy_data:
        record.status = "needs_review"
    else:
        record.status = "needs_review"

    record.trace_steps = all_trace
    total_ms = int((time.time() - start_time) * 1000)

    all_trace.append({"name": "Ready for Review", "step_type": "pipeline", "duration_ms": total_ms,
                       "status": "success", "details": {"final_status": record.status}})

    await _ws_broadcast("claims", {"type": "ready_for_review", "claim_id": record.claim_id,
                                     "status": record.status, "total_ms": total_ms})

    return {
        "claim_id": record.claim_id,
        "status": record.status,
        "extraction": record.extraction,
        "policy_data": record.policy_data,
        "carrier_data": record.carrier_data,
        "priority": record.priority,
        "compliance_flags": compliance_flags,
        "trace_steps": all_trace,
        "latency_ms": total_ms,
    }


@app.get("/api/claims")
def list_claims():
    return {"claims": claim_pipeline.list_claims()}


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: str):
    record = claim_pipeline.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")
    return {
        "claim_id": record.claim_id,
        "status": record.status,
        "email_raw": record.email_raw,
        "email_from": record.email_from,
        "email_subject": record.email_subject,
        "extraction": record.extraction,
        "policy_data": record.policy_data,
        "carrier_data": record.carrier_data,
        "carrier_submission": record.carrier_submission,
        "client_email": record.client_email,
        "followup_email": record.followup_email,
        "priority": record.priority,
        "trace_steps": record.trace_steps,
        "created_at": record.created_at,
    }


@app.post("/api/claims/{claim_id}/approve")
async def approve_claim(claim_id: str, req: ClaimApproveRequest):
    """Approve AI extraction (optionally with edits) and generate submission documents."""
    record = claim_pipeline.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Apply any edits from the CSR
    if req.extraction:
        record.extraction.update(req.extraction)

    record.status = "approved"
    start = time.time()
    loop = asyncio.get_event_loop()

    # Generate carrier submission and client email in parallel
    sub_future = loop.run_in_executor(
        None, generate_carrier_submission,
        record.extraction, record.policy_data, record.carrier_data
    )
    email_future = loop.run_in_executor(
        None, generate_client_confirmation,
        record.extraction, record.policy_data, record.carrier_data, claim_id
    )

    sub_result, email_result = await asyncio.gather(sub_future, email_future)

    record.carrier_submission = sub_result.get("submission_text", "")
    record.client_email = email_result.get("email_text", "")

    total_ms = int((time.time() - start) * 1000)

    await _ws_broadcast("claims", {"type": "submission_generated", "claim_id": claim_id})

    return {
        "claim_id": claim_id,
        "status": "approved",
        "carrier_submission": record.carrier_submission,
        "client_email": record.client_email,
        "client_email_to": email_result.get("to", ""),
        "client_email_subject": email_result.get("subject", ""),
        "latency_ms": total_ms,
    }


@app.post("/api/claims/{claim_id}/submit")
async def submit_claim(claim_id: str):
    """Mark claim as submitted to carrier (mock)."""
    record = claim_pipeline.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")

    record.status = "submitted"

    # Create a claim record in the mock AMS
    if record.policy_data and record.extraction:
        create_claim_record(
            client_id=record.policy_data.get("client_id", ""),
            policy_id=record.policy_data.get("id", ""),
            carrier=record.policy_data.get("carrier", ""),
            carrier_id=record.policy_data.get("carrier_id", ""),
            loss_type=record.extraction.get("loss_type", ""),
            date_of_loss=record.extraction.get("date_of_loss", ""),
            description=record.extraction.get("description", ""),
            location=record.extraction.get("location", ""),
            injuries=record.extraction.get("injuries", False),
            police_report=record.extraction.get("police_report", False),
            police_report_number=record.extraction.get("police_report_number", ""),
            priority=record.priority,
        )

    await _ws_broadcast("claims", {"type": "claim_submitted", "claim_id": claim_id})

    return {
        "claim_id": claim_id,
        "status": "submitted",
        "message": f"Claim {claim_id} has been submitted to {record.carrier_data.get('carrier_name', 'the carrier')}.",
    }


@app.get("/api/claims/{claim_id}/submission")
def get_claim_submission(claim_id: str):
    record = claim_pipeline.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")
    return {"claim_id": claim_id, "carrier_submission": record.carrier_submission}


@app.get("/api/claims/{claim_id}/client-email")
def get_claim_client_email(claim_id: str):
    record = claim_pipeline.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")
    return {"claim_id": claim_id, "client_email": record.client_email}


@app.post("/api/claims/{claim_id}/followup")
async def generate_claim_followup(claim_id: str):
    """Generate a follow-up email for missing information."""
    record = claim_pipeline.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")

    missing = record.extraction.get("missing_fields", [])
    if not missing:
        return {"claim_id": claim_id, "message": "No missing fields identified."}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, generate_followup_email, record.extraction, missing)

    record.followup_email = result.get("email_text", "")
    record.status = "follow_up"

    return {
        "claim_id": claim_id,
        "followup_email": record.followup_email,
        "to": result.get("to", ""),
        "subject": result.get("subject", ""),
        "missing_fields": missing,
    }


@app.post("/api/claims/{claim_id}/draft")
async def save_claim_draft(claim_id: str, req: ClaimApproveRequest):
    """Save the current extraction as a draft."""
    record = claim_pipeline.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")
    if req.extraction:
        record.extraction.update(req.extraction)
    record.status = "draft"
    return {"claim_id": claim_id, "status": "draft", "message": "Draft saved."}


@app.post("/api/claims/{claim_id}/escalate")
async def escalate_claim(claim_id: str):
    """Escalate a claim to a senior adjuster."""
    record = claim_pipeline.get_claim(claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")
    record.status = "escalated"
    await _ws_broadcast("claims", {"type": "claim_escalated", "claim_id": claim_id})
    return {"claim_id": claim_id, "status": "escalated",
            "message": f"Claim {claim_id} has been escalated to a senior adjuster for review."}


# ── Demo Scenarios ───────────────────────────────────────────────────

@app.get("/api/demo/scenarios")
def demo_scenarios():
    return {"scenarios": list_scenarios()}


@app.post("/api/demo/scenario/{scenario_name}")
async def run_demo_scenario(scenario_name: str):
    """Trigger a demo scenario — loads a pre-written email and processes it."""
    email = get_sample_email(scenario_name)
    if not email:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' not found")

    # Process through the intake pipeline
    req = EmailIntakeRequest(
        email_text=email["body"],
        from_address=email["from"],
        subject=email["subject"],
    )
    return await intake_claim(req)


# ── Chat (for claim status queries, interactive mode) ────────────────

@app.post("/api/session/start")
def start_session(client_id: str = "CLI-1001"):
    try:
        session = session_manager.create_session(client_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"session_id": session.session_id, "client": session.member_data}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session = session_manager.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    pii_found = detect_pii(user_message)
    guardrail_flags = []
    if pii_found:
        guardrail_flags.append({"type": "pii_detected", "details": pii_found, "action": "redacted_in_logs"})

    blocked, blocked_topic = check_blocked_topics(user_message)
    if blocked:
        session.add_message("user", user_message)
        session.add_message("assistant", blocked)
        return ChatResponse(
            response=blocked, intent="blocked", agent="guardrails",
            trace_steps=[{"name": "Topic Blocked", "step_type": "guardrail", "duration_ms": 0,
                          "status": "blocked", "details": {"topic": blocked_topic}}],
            guardrail_flags=guardrail_flags,
        )

    session.add_message("user", user_message)
    start_time = time.time()

    await _ws_broadcast(session.session_id, {"type": "processing_started", "message": user_message})

    # Classify intent
    conversation_history = session.get_conversation_history()
    sup_start = time.time()
    intent, confidence, reasoning, sentiment, priority = classify_intent(
        messages=conversation_history,
        member_name=session.member_data.get("name", ""),
        current_agent=session.current_agent,
    )
    sup_ms = int((time.time() - sup_start) * 1000)

    session.sentiment_history.append(sentiment)

    trace_steps = [
        {"name": "Supervisor Classification", "step_type": "supervisor", "duration_ms": sup_ms,
         "status": "success", "details": {"intent": intent.value, "confidence": confidence,
                                           "sentiment": sentiment, "priority": priority.value, "reasoning": reasoning}},
    ]

    await _ws_broadcast(session.session_id, {"type": "intent_classified", "intent": intent.value,
                                               "confidence": confidence, "priority": priority.value})

    # Route to specialist
    agent_kwargs = dict(
        messages=conversation_history,
        member_id=session.member_id,
        member_name=session.member_data.get("name", ""),
    )

    if intent == Intent.ESCALATE:
        from backend.tools.claims_api import escalate_to_human
        from backend.models import AgentResponse, ToolCall
        result = escalate_to_human("Client requested human agent", "Chat escalation")
        agent_response = AgentResponse(
            text=result["message"], intent=Intent.ESCALATE, agent_name="escalation_handler",
            tools_called=[ToolCall("escalate_to_human", {"reason": "client_request"}, result)],
            escalated=True, escalation_reason="client_request",
        )
    elif intent in FNOL_INTENTS:
        agent_response = run_fnol_agent(**agent_kwargs, intent=intent)
    elif intent == Intent.CLAIM_STATUS:
        agent_response = run_claims_agent(**agent_kwargs)
    elif intent == Intent.POLICY_QUESTION:
        agent_response = run_policy_lookup_agent(**agent_kwargs)
    else:
        # General, billing, COI — use general handler
        system_prompt = f"""You are the ClaimFlow AI assistant for Prairie Shield Insurance Group in Omaha, Nebraska.

Client: {agent_kwargs['member_name']}

You can help with:
- Filing new claims (FNOL)
- Checking claim status
- Looking up policy information
- Answering insurance questions

If the client wants to file a claim, help them get started.
If they need a Certificate of Insurance (COI) or have billing questions, let them know those features are coming soon and offer to connect them with a CSR.
Use search_knowledge_base for general insurance questions.
"""
        tools = [TOOL_DEFINITIONS["search_knowledge_base"], TOOL_DEFINITIONS["lookup_client"]]
        agent_response = run_agent_loop(
            system_prompt=system_prompt, messages=conversation_history,
            tools=tools, agent_name="general_agent", intent=intent,
        )

    # Build response trace
    all_trace = trace_steps + [
        {"name": ts.name, "step_type": ts.step_type, "duration_ms": ts.duration_ms,
         "status": ts.status, "details": ts.details}
        for ts in agent_response.trace_steps
    ]

    # Response guardrails
    is_valid, resp_confidence = validate_response(agent_response.text)
    all_trace.append({"name": "Response Guardrails", "step_type": "guardrail", "duration_ms": 0,
                       "status": "success" if is_valid else "warning",
                       "details": {"valid": is_valid, "confidence": round(resp_confidence, 2)}})

    session.current_intent = intent.value
    session.current_agent = agent_response.agent_name
    session.add_message("assistant", agent_response.text)

    if agent_response.escalated:
        session.escalated = True

    latency = int((time.time() - start_time) * 1000)
    tools_ms = sum(tc.duration_ms for tc in agent_response.tools_called)

    tools_data = [
        {"tool": tc.tool_name, "input": tc.tool_input, "output": tc.tool_output, "duration_ms": tc.duration_ms}
        for tc in agent_response.tools_called
    ]
    rag_data = [
        {"source_doc": rs.source_doc, "heading": rs.heading, "chunk_text": rs.chunk_text, "relevance_score": rs.relevance_score}
        for rs in agent_response.rag_sources
    ]

    # Audit
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

    await _ws_broadcast(session.session_id, {"type": "response_ready", "response": agent_response.text,
                                               "intent": intent.value, "latency_ms": latency})

    return ChatResponse(
        response=agent_response.text,
        intent=intent.value,
        agent=agent_response.agent_name,
        tools_called=tools_data,
        rag_sources=rag_data,
        trace_steps=all_trace,
        escalated=agent_response.escalated,
        escalation_reason=agent_response.escalation_reason,
        confidence=agent_response.confidence,
        sentiment=sentiment,
        priority=priority.value,
        latency_ms=latency,
        latency_breakdown={"classification_ms": sup_ms, "tools_ms": tools_ms,
                           "generation_ms": max(0, latency - sup_ms - tools_ms)},
        guardrail_flags=guardrail_flags,
    )


# ── WebSocket ─────────────────────────────────────────────────────────

@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    await websocket.accept()
    if channel not in ws_connections:
        ws_connections[channel] = []
    ws_connections[channel].append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_connections[channel].remove(websocket)
        if not ws_connections[channel]:
            del ws_connections[channel]


async def _ws_broadcast(channel: str, data: dict):
    connections = ws_connections.get(channel, [])
    for ws in connections:
        try:
            await ws.send_json(data)
        except Exception:
            pass


# ── Static files ──────────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
