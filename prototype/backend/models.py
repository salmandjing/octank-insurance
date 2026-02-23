from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class Intent(str, Enum):
    ELIGIBILITY = "eligibility"
    FNOL = "fnol"
    CLAIM_STATUS = "claim_status"
    GENERAL = "general"
    ESCALATE = "escalate"


@dataclass
class TraceStep:
    """A single step in the agent processing trace."""
    name: str
    step_type: str  # "supervisor", "routing", "tool_call", "rag_search", "specialist", "guardrail", "escalation"
    duration_ms: int = 0
    status: str = "success"  # "success", "error", "skipped"
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
    role: str  # "user" or "assistant"
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
