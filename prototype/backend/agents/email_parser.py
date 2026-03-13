"""Email parser agent — extracts structured FNOL data from incoming claim emails."""
from __future__ import annotations
import json
import time
import logging
import anthropic

from backend.config import SPECIALIST_MODEL, MAX_TOKENS
from backend.models import FNOLExtraction, TraceStep

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()

EMAIL_PARSER_SYSTEM = """You are an insurance claims intake specialist at Prairie Shield Insurance Group in Omaha, Nebraska. Your job is to parse incoming emails that report insurance claims (First Notice of Loss) and extract structured data.

From the email, extract:
- Reporter name and contact info
- Policy number (if mentioned)
- Client name (if different from reporter)
- Date of loss (exact or approximate)
- Time of loss (if mentioned)
- Location of loss (specific address or description)
- Type of loss (auto_collision, auto_comprehensive, homeowners_property, homeowners_liability, commercial_property, commercial_auto, farm_ranch, workers_comp, general_liability, unknown)
- Description of what happened
- Injuries (yes/no, description if yes)
- Police/fire report filed (yes/no, report number if available)
- Other parties involved (names, insurance info if provided)
- Photos or documents mentioned/attached
- Urgency indicators (ongoing damage, injuries, commercial vehicle, livestock)

If critical information is missing, flag it specifically. Always flag:
- Missing policy number (CRITICAL — cannot proceed without it)
- Missing date of loss (CRITICAL)
- Ambiguous loss type
- Any mention of injuries (auto-escalate priority)

Output your extraction as a JSON object with these fields:
- reporter_name, reporter_email, reporter_phone
- client_name (if different from reporter, null otherwise)
- policy_number (null if not found)
- date_of_loss (ISO format, null if not found)
- time_of_loss (null if not mentioned)
- location (null if not mentioned)
- loss_type (one of the types listed above)
- description (full description of what happened)
- injuries (boolean or null)
- injury_description (null if no injuries)
- police_report (boolean or null)
- police_report_number (null if not mentioned)
- other_parties (list of {name, insurance_company, policy_number} or null)
- photos_mentioned (boolean)
- urgency (normal, elevated, high, critical)
- missing_fields (list of field names that need follow-up)
- confidence_score (0.0 to 1.0)
"""

EXTRACT_TOOL = {
    "name": "extract_fnol_data",
    "description": "Extract structured FNOL data from an email",
    "input_schema": {
        "type": "object",
        "properties": {
            "reporter_name": {"type": "string"},
            "reporter_email": {"type": ["string", "null"]},
            "reporter_phone": {"type": ["string", "null"]},
            "client_name": {"type": ["string", "null"]},
            "policy_number": {"type": ["string", "null"]},
            "date_of_loss": {"type": ["string", "null"]},
            "time_of_loss": {"type": ["string", "null"]},
            "location": {"type": ["string", "null"]},
            "loss_type": {
                "type": "string",
                "enum": ["auto_collision", "auto_comprehensive", "homeowners_property", "homeowners_liability", "commercial_property", "commercial_auto", "farm_ranch", "workers_comp", "general_liability", "unknown"]
            },
            "description": {"type": "string"},
            "injuries": {"type": ["boolean", "null"]},
            "injury_description": {"type": ["string", "null"]},
            "police_report": {"type": ["boolean", "null"]},
            "police_report_number": {"type": ["string", "null"]},
            "other_parties": {
                "type": ["array", "null"],
                "items": {"type": "object"}
            },
            "photos_mentioned": {"type": "boolean"},
            "urgency": {"type": "string", "enum": ["normal", "elevated", "high", "critical"]},
            "missing_fields": {"type": "array", "items": {"type": "string"}},
            "confidence_score": {"type": "number"}
        },
        "required": ["reporter_name", "loss_type", "description", "urgency", "missing_fields", "confidence_score"]
    }
}


def parse_email(email_text: str, from_address: str = "", subject: str = "") -> tuple[FNOLExtraction, list[TraceStep]]:
    """Parse an incoming claim email and extract structured FNOL data.

    Returns (extraction, trace_steps).
    """
    trace_steps = []
    start = time.time()

    full_email = ""
    if from_address:
        full_email += f"From: {from_address}\n"
    if subject:
        full_email += f"Subject: {subject}\n"
    full_email += f"\n{email_text}"

    trace_steps.append(TraceStep(
        name="Email Parser Started",
        step_type="specialist",
        details={"email_length": len(email_text), "has_from": bool(from_address), "has_subject": bool(subject)},
    ))

    try:
        response = client.messages.create(
            model=SPECIALIST_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.0,
            system=EMAIL_PARSER_SYSTEM,
            messages=[{"role": "user", "content": f"Parse this incoming claim email:\n\n{full_email}"}],
            tools=[EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "extract_fnol_data"},
        )

        parse_ms = int((time.time() - start) * 1000)

        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_fnol_data":
                data = block.input
                extraction = FNOLExtraction(
                    reporter_name=data.get("reporter_name", ""),
                    reporter_email=data.get("reporter_email") or from_address,
                    reporter_phone=data.get("reporter_phone"),
                    client_name=data.get("client_name"),
                    policy_number=data.get("policy_number"),
                    date_of_loss=data.get("date_of_loss"),
                    time_of_loss=data.get("time_of_loss"),
                    location=data.get("location"),
                    loss_type=data.get("loss_type", "unknown"),
                    description=data.get("description", ""),
                    injuries=data.get("injuries"),
                    injury_description=data.get("injury_description"),
                    police_report=data.get("police_report"),
                    police_report_number=data.get("police_report_number"),
                    other_parties=data.get("other_parties"),
                    photos_mentioned=data.get("photos_mentioned", False),
                    urgency=data.get("urgency", "normal"),
                    missing_fields=data.get("missing_fields", []),
                    confidence_score=data.get("confidence_score", 0.0),
                    raw_email_text=email_text,
                )

                trace_steps.append(TraceStep(
                    name="Email Parsed",
                    step_type="specialist",
                    duration_ms=parse_ms,
                    details={
                        "loss_type": extraction.loss_type,
                        "urgency": extraction.urgency,
                        "confidence": extraction.confidence_score,
                        "missing_fields": extraction.missing_fields,
                        "has_policy_number": bool(extraction.policy_number),
                        "has_injuries": extraction.injuries,
                    },
                ))

                return extraction, trace_steps

    except Exception as e:
        logger.error(f"Email parsing failed: {e}")
        parse_ms = int((time.time() - start) * 1000)
        trace_steps.append(TraceStep(
            name="Email Parse Error",
            step_type="specialist",
            duration_ms=parse_ms,
            status="error",
            details={"error": str(e)},
        ))

    # Fallback extraction
    return FNOLExtraction(
        reporter_name="Unknown",
        description=email_text,
        missing_fields=["reporter_name", "policy_number", "date_of_loss", "loss_type"],
        confidence_score=0.1,
        raw_email_text=email_text,
    ), trace_steps
