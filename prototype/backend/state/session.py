"""Session and data management for ClaimFlow AI."""
from __future__ import annotations
import uuid
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from backend.config import DATA_DIR, SESSION_TIMEOUT_MINUTES
from backend.models import AuditEntry, FNOLExtraction, ClaimStatus


def _load_json(filename: str) -> dict:
    path = DATA_DIR / filename
    with open(path) as f:
        return json.load(f)


def get_clients_db() -> dict[str, Any]:
    return _load_json("clients.json")["clients"]


def get_policies_db() -> dict[str, Any]:
    return _load_json("policies.json")["policies"]


def get_carriers_db() -> dict[str, Any]:
    return _load_json("carriers.json")["carriers"]


def get_claims_db() -> dict[str, Any]:
    return _load_json("claims.json")["claims"]


# In-memory claims store for new claims created during session
_active_claims: dict[str, dict] = {}


def get_all_claims() -> dict[str, Any]:
    """Get claims from file + any created during this session."""
    claims = get_claims_db()
    claims.update(_active_claims)
    return claims


def add_active_claim(claim_id: str, claim_data: dict) -> None:
    _active_claims[claim_id] = claim_data


@dataclass
class ClaimRecord:
    """A claim being processed through the FNOL pipeline."""
    claim_id: str
    status: str = "new"
    email_raw: str = ""
    email_from: str = ""
    email_subject: str = ""
    extraction: dict = field(default_factory=dict)
    policy_data: dict = field(default_factory=dict)
    carrier_data: dict = field(default_factory=dict)
    carrier_submission: str = ""
    client_email: str = ""
    followup_email: str = ""
    priority: str = "normal"
    trace_steps: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Session:
    session_id: str
    member_id: str
    member_data: dict[str, Any]
    created_at: float
    last_active: float
    messages: list[dict[str, str]] = field(default_factory=list)
    turn_count: int = 0
    tools_called: list[str] = field(default_factory=list)
    current_intent: str = ""
    current_agent: str = ""
    escalated: bool = False
    fnol_data: dict[str, Any] = field(default_factory=dict)
    audit_log: list[dict] = field(default_factory=list)
    sentiment_history: list[str] = field(default_factory=list)
    rag_history: list[dict] = field(default_factory=list)
    review_queue: list[dict] = field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > (SESSION_TIMEOUT_MINUTES * 60)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        self.last_active = time.time()
        if role == "user":
            self.turn_count += 1

    def add_audit_entry(self, entry: AuditEntry) -> None:
        self.audit_log.append({
            "timestamp": entry.timestamp,
            "turn": entry.turn,
            "user_message": entry.user_message,
            "intent": entry.intent,
            "agent": entry.agent,
            "tools_called": entry.tools_called,
            "rag_sources": entry.rag_sources,
            "response": entry.response[:200],
            "latency_ms": entry.latency_ms,
            "sentiment": getattr(entry, "sentiment", "neutral"),
        })

    def get_conversation_history(self) -> list[dict[str, str]]:
        return list(self.messages)


class ClaimPipeline:
    """Manages claims being processed through the FNOL pipeline."""

    def __init__(self):
        self._claims: dict[str, ClaimRecord] = {}

    def create_claim(self, email_raw: str = "", email_from: str = "", email_subject: str = "") -> ClaimRecord:
        claim_id = f"CF-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        record = ClaimRecord(
            claim_id=claim_id,
            email_raw=email_raw,
            email_from=email_from,
            email_subject=email_subject,
            created_at=now,
            updated_at=now,
        )
        self._claims[claim_id] = record
        return record

    def get_claim(self, claim_id: str) -> ClaimRecord | None:
        return self._claims.get(claim_id)

    def list_claims(self) -> list[dict]:
        return [
            {
                "claim_id": c.claim_id,
                "status": c.status,
                "email_from": c.email_from,
                "email_subject": c.email_subject,
                "priority": c.priority,
                "loss_type": c.extraction.get("loss_type", ""),
                "reporter_name": c.extraction.get("reporter_name", ""),
                "policy_number": c.extraction.get("policy_number", ""),
                "confidence": c.extraction.get("confidence_score", 0),
                "created_at": c.created_at,
            }
            for c in sorted(self._claims.values(), key=lambda x: x.created_at, reverse=True)
        ]

    def update_claim(self, claim_id: str, **kwargs) -> ClaimRecord | None:
        record = self._claims.get(claim_id)
        if not record:
            return None
        for key, value in kwargs.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.updated_at = datetime.now(timezone.utc).isoformat()
        return record


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, client_id: str) -> Session:
        clients = get_clients_db()
        if client_id not in clients:
            raise ValueError(f"Unknown client: {client_id}")

        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = time.time()
        session = Session(
            session_id=session_id,
            member_id=client_id,
            member_data=clients[client_id],
            created_at=now,
            last_active=now,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session and session.is_expired:
            del self._sessions[session_id]
            return None
        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        return [
            {
                "session_id": s.session_id,
                "member_id": s.member_id,
                "member_name": s.member_data.get("name", ""),
                "turn_count": s.turn_count,
                "escalated": s.escalated,
            }
            for s in self._sessions.values()
            if not s.is_expired
        ]

    def get_clients(self) -> list[dict[str, Any]]:
        clients = get_clients_db()
        return [
            {
                "id": c.get("id", cid),
                "name": c["name"],
                "type": c.get("type", "personal"),
                "email": c.get("email", ""),
                "phone": c.get("phone", ""),
                "agent": c.get("agent", ""),
            }
            for cid, c in clients.items()
        ]
