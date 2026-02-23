"""Guardrails — PII redaction, topic blocking, response validation."""
from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

# PII patterns for redaction in logs
PII_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),           # SSN
    (r'\b\d{9}\b', '[SSN REDACTED]'),                         # SSN no dashes
    (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE REDACTED]'),  # Phone
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REDACTED]'),
    (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD REDACTED]'),  # Credit card
]

# Topics the agent should not provide advice on
BLOCKED_TOPICS = [
    "medical advice",
    "legal advice",
    "investment advice",
    "tax advice",
]

BLOCKED_TOPIC_PATTERNS = [
    (r'\b(should I see a doctor|medical treatment|diagnosis|prescription|medication|what medicine|neck pain|take for my)\b', 'medical_advice'),
    (r'\b(sue|lawsuit|attorney|lawyer|legal action)\b', 'legal_advice'),
    (r'\b(invest|stock|portfolio|financial advisor)\b', 'investment_advice'),
    (r'\b(tax deduction|tax advice|write off|tax return)\b', 'tax_advice'),
]

# Low confidence indicators in responses
HALLUCINATION_SIGNALS = [
    "I'm not sure but",
    "I think it might be",
    "I believe it could be",
    "This is just my guess",
    "I'm making an assumption",
]


def redact_pii(text: str) -> str:
    """Redact PII patterns from text (for logging purposes)."""
    redacted = text
    for pattern, replacement in PII_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted)
    return redacted


def detect_pii(text: str) -> list[dict]:
    """Detect PII in text and return types found (without exposing actual data)."""
    found = []
    pii_types = [
        (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
        (r'\b\d{9}\b', 'SSN'),
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'Phone Number'),
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'Email'),
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'Credit Card'),
    ]
    for pattern, pii_type in pii_types:
        if re.search(pattern, text):
            found.append({"type": pii_type, "action": "redacted_in_logs"})
    return found


def check_blocked_topics(user_message: str) -> tuple:
    """Check if the user is asking about a blocked topic.

    Returns (redirect_message, topic_name) if blocked, (None, None) if OK.
    """
    message_lower = user_message.lower()

    for pattern, topic in BLOCKED_TOPIC_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return (
                "I understand your concern, but I'm not able to provide medical, legal, tax, "
                "or investment advice. For those matters, I'd recommend consulting with "
                "a qualified professional. Is there anything else related to your "
                "Octank Insurance policy that I can help with?",
                topic,
            )

    return None, None


def validate_response(response_text: str) -> tuple[bool, float]:
    """Validate agent response for hallucination signals.

    Returns (is_valid, confidence_score).
    """
    text_lower = response_text.lower()
    signals_found = sum(
        1 for signal in HALLUCINATION_SIGNALS
        if signal.lower() in text_lower
    )

    confidence = max(0.0, 1.0 - (signals_found * 0.2))
    is_valid = confidence >= 0.5

    if not is_valid:
        logger.warning(f"Low confidence response detected (score: {confidence})")

    return is_valid, confidence
