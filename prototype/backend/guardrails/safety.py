"""Guardrails — PII redaction, topic blocking, coverage opinion blocking, compliance flags."""
from __future__ import annotations
import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# PII patterns for redaction in logs
PII_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN REDACTED]'),
    (r'\b\d{9}\b', '[SSN REDACTED]'),
    (r'\b[A-Z]{2}-[A-Z]\d{8,}\b', '[DL REDACTED]'),
    (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD REDACTED]'),
]

# Topics the agent should not provide advice on
BLOCKED_TOPIC_PATTERNS = [
    (r'\b(should I see a doctor|medical treatment|diagnosis|prescription|medication|what medicine)\b', 'medical_advice'),
    (r'\b(sue|lawsuit|attorney|lawyer|legal action)\b', 'legal_advice'),
    (r'\b(invest|stock|portfolio|financial advisor)\b', 'investment_advice'),
    (r'\b(tax deduction|tax advice|write off|tax return)\b', 'tax_advice'),
]

# Coverage opinion phrases the AI must NEVER use definitively
BLOCKED_COVERAGE_PHRASES = [
    "this is covered",
    "this is not covered",
    "your claim will be approved",
    "your claim will be denied",
    "you are entitled to",
    "the carrier must pay",
    "you should receive",
]

COVERAGE_DISCLAIMER = (
    "Please note that all coverage determinations are made by your insurance carrier. "
    "This information is provided for reference only and does not constitute a coverage opinion."
)

# Hallucination signals
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
    """Detect PII in text and return types found."""
    found = []
    pii_types = [
        (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
        (r'\b\d{9}\b', 'SSN'),
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', 'Credit Card'),
    ]
    for pattern, pii_type in pii_types:
        if re.search(pattern, text):
            found.append({"type": pii_type, "action": "redacted_in_logs"})
    return found


def check_blocked_topics(user_message: str) -> tuple:
    """Check if the user is asking about a blocked topic."""
    message_lower = user_message.lower()

    for pattern, topic in BLOCKED_TOPIC_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return (
                "I understand your concern, but I'm not able to provide medical, legal, tax, "
                "or investment advice. For those matters, I'd recommend consulting with "
                "a qualified professional. Is there anything else related to your "
                "insurance that I can help with?",
                topic,
            )

    return None, None


def check_coverage_opinion(response_text: str) -> list[dict]:
    """Check if response contains definitive coverage opinions."""
    flags = []
    text_lower = response_text.lower()
    for phrase in BLOCKED_COVERAGE_PHRASES:
        if phrase in text_lower:
            flags.append({
                "type": "coverage_opinion",
                "phrase": phrase,
                "action": "flagged",
                "note": "AI should not make definitive coverage determinations",
            })
    return flags


def check_compliance_flags(fnol_data: dict) -> list[dict]:
    """Check for Nebraska-specific compliance concerns."""
    flags = []

    # Late reporting check (>48 hours)
    date_of_loss = fnol_data.get("date_of_loss")
    if date_of_loss:
        try:
            loss_date = datetime.fromisoformat(date_of_loss)
            if datetime.now() - loss_date > timedelta(hours=48):
                flags.append({
                    "type": "late_reporting",
                    "severity": "warning",
                    "message": "Claim reported more than 48 hours after date of loss. Most carriers require prompt notification.",
                })
        except (ValueError, TypeError):
            pass

    # Injury flag
    if fnol_data.get("injuries"):
        flags.append({
            "type": "injury_reported",
            "severity": "high",
            "message": "Injuries reported. Notify agency principal. May trigger additional reporting requirements.",
        })

    # Workers comp flag
    if fnol_data.get("loss_type") == "workers_comp":
        flags.append({
            "type": "workers_comp",
            "severity": "high",
            "message": "Workers compensation claim. OSHA reporting may be required. Nebraska Workers' Compensation Court notification needed.",
        })

    # Commercial vehicle flag
    if fnol_data.get("loss_type") in ("commercial_auto",):
        flags.append({
            "type": "commercial_vehicle",
            "severity": "elevated",
            "message": "Commercial vehicle incident. Check if DOT/FMCSA reporting required (vehicles over 10,001 lbs).",
        })

    return flags


def validate_response(response_text: str) -> tuple[bool, float]:
    """Validate agent response for hallucination signals and coverage opinions."""
    text_lower = response_text.lower()
    signals_found = sum(
        1 for signal in HALLUCINATION_SIGNALS
        if signal.lower() in text_lower
    )

    coverage_flags = check_coverage_opinion(response_text)

    confidence = max(0.0, 1.0 - (signals_found * 0.2) - (len(coverage_flags) * 0.1))
    is_valid = confidence >= 0.5

    if not is_valid:
        logger.warning(f"Low confidence response detected (score: {confidence})")

    return is_valid, confidence
