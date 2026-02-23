from __future__ import annotations
import uuid
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any

from backend.config import DATA_DIR, SESSION_TIMEOUT_MINUTES
from backend.models import Message, AuditEntry

# Load member data
_members_path = DATA_DIR / "members.json"
with open(_members_path) as f:
    MEMBERS_DB: dict[str, Any] = json.load(f)["members"]

_claims_path = DATA_DIR / "claims.json"
with open(_claims_path) as f:
    CLAIMS_DB: dict[str, Any] = json.load(f)["claims"]


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
    rag_history: list[dict] = field(default_factory=list)  # Full RAG results per turn
    review_queue: list[dict] = field(default_factory=list)  # Flagged for human review

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


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, member_id: str) -> Session:
        if member_id not in MEMBERS_DB:
            raise ValueError(f"Unknown member: {member_id}")

        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = time.time()
        session = Session(
            session_id=session_id,
            member_id=member_id,
            member_data=MEMBERS_DB[member_id],
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

    def get_members(self) -> list[dict[str, Any]]:
        return [
            {
                "member_id": m["member_id"],
                "name": m["name"],
                "policy_number": m["policy_number"],
                "policy_type": m["policy_type"],
            }
            for m in MEMBERS_DB.values()
        ]
