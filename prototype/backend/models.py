from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class Intent(str, Enum):
    FNOL_AUTO = "fnol_auto"
    FNOL_PROPERTY = "fnol_property"
    FNOL_FARM = "fnol_farm"
    FNOL_COMMERCIAL = "fnol_commercial"
    FNOL_WORKERS_COMP = "fnol_workers_comp"
    CLAIM_STATUS = "claim_status"
    POLICY_QUESTION = "policy_question"
    COI_REQUEST = "coi_request"
    BILLING_QUESTION = "billing_question"
    GENERAL = "general"
    ESCALATE = "escalate"


# All FNOL intents for routing convenience
FNOL_INTENTS = {
    Intent.FNOL_AUTO, Intent.FNOL_PROPERTY, Intent.FNOL_FARM,
    Intent.FNOL_COMMERCIAL, Intent.FNOL_WORKERS_COMP,
}


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    ELEVATED = "elevated"
    NORMAL = "normal"


class ClaimStatus(str, Enum):
    NEW = "new"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    FOLLOW_UP = "follow_up"
    DRAFT = "draft"


@dataclass
class FNOLExtraction:
    """Structured data extracted from an incoming claim email."""
    reporter_name: str = ""
    reporter_email: str | None = None
    reporter_phone: str | None = None
    client_name: str | None = None
    policy_number: str | None = None
    date_of_loss: str | None = None
    time_of_loss: str | None = None
    location: str | None = None
    loss_type: str | None = None
    description: str = ""
    injuries: bool | None = None
    injury_description: str | None = None
    police_report: bool | None = None
    police_report_number: str | None = None
    other_parties: list[dict] | None = None
    photos_mentioned: bool = False
    attachments: list[str] = field(default_factory=list)
    urgency: str = "normal"
    missing_fields: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    raw_email_text: str = ""


@dataclass
class TraceStep:
    """A single step in the agent processing trace."""
    name: str
    step_type: str
    duration_ms: int = 0
    status: str = "success"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    tool_name: str
    tool_input: dict[str, Any]
    tool_output: dict[str, Any] | None = None
    duration_ms: int = 0


@dataclass
class RAGSource:
    chunk_text: str
    source_doc: str
    heading: str = ""
    page: int | None = None
    relevance_score: float = 0.0


@dataclass
class HandoffContext:
    """Context package for agent escalation handoff."""
    summary: str = ""
    intent: str = ""
    actions_taken: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    retrieved_docs: list[str] = field(default_factory=list)
    sentiment: str = "neutral"


@dataclass
class AgentResponse:
    text: str
    intent: Intent | None = None
    agent_name: str = ""
    tools_called: list[ToolCall] = field(default_factory=list)
    rag_sources: list[RAGSource] = field(default_factory=list)
    trace_steps: list[TraceStep] = field(default_factory=list)
    escalated: bool = False
    escalation_reason: str = ""
    handoff_context: HandoffContext | None = None
    confidence: float = 1.0
    sentiment: str = "neutral"
    latency_ms: int = 0


@dataclass
class Message:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEntry:
    timestamp: str
    session_id: str
    member_id: str
    turn: int
    user_message: str
    intent: str
    agent: str
    tools_called: list[str]
    rag_sources: list[str]
    response: str
    latency_ms: int
    sentiment: str = "neutral"
