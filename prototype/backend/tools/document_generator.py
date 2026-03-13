"""Document generation tools — carrier submissions and client emails."""
from __future__ import annotations
import time
import logging
import anthropic

from backend.config import SPECIALIST_MODEL, MAX_TOKENS

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()


def generate_carrier_submission(fnol_data: dict, policy_data: dict, carrier_data: dict) -> dict:
    """Generate a formatted carrier FNOL submission."""
    start = time.time()

    prompt = f"""Generate a professional FNOL carrier submission based on this data.

CLAIM DATA:
{_format_dict(fnol_data)}

POLICY DATA:
{_format_dict(policy_data)}

CARRIER: {carrier_data.get('carrier_name', 'Unknown')}
SUBMISSION FORMAT: {carrier_data.get('submission_format', 'acord_form')}
REQUIRED FIELDS: {', '.join(carrier_data.get('required_fields', []))}

Format this as a clean, professional carrier submission document. Include all required fields.
Use the carrier's preferred format. Include the agency name "Prairie Shield Insurance Group" as the reporting agency.
Mark any missing required fields as "[NEEDS INFORMATION]".

Output ONLY the formatted submission text, no commentary."""

    try:
        response = client.messages.create(
            model=SPECIALIST_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        duration_ms = int((time.time() - start) * 1000)

        return {
            "submission_text": text,
            "carrier": carrier_data.get("carrier_name", ""),
            "format": carrier_data.get("submission_format", "acord_form"),
            "duration_ms": duration_ms,
        }
    except Exception as e:
        logger.error(f"Carrier submission generation failed: {e}")
        return {"error": str(e), "submission_text": "Generation failed. Please prepare submission manually."}


def generate_client_confirmation(fnol_data: dict, client_data: dict, carrier_data: dict, claim_id: str = "") -> dict:
    """Generate a professional client confirmation email."""
    start = time.time()

    client_name = client_data.get("name", fnol_data.get("reporter_name", "Valued Client"))

    prompt = f"""Write a professional, empathetic client confirmation email for an insurance claim that has been filed.

CLIENT: {client_name}
EMAIL: {client_data.get('email', fnol_data.get('reporter_email', ''))}
CLAIM ID: {claim_id or 'Pending'}
CARRIER: {carrier_data.get('carrier_name', 'your carrier')}
LOSS TYPE: {fnol_data.get('loss_type', fnol_data.get('type', 'claim'))}
DATE OF LOSS: {fnol_data.get('date_of_loss', 'as reported')}
DESCRIPTION: {fnol_data.get('description', '')[:200]}

The email should:
1. Acknowledge receipt of their claim with empathy
2. Provide the claim reference number
3. Name the carrier who will handle the claim
4. Explain what to expect next (adjuster contact timeline: {carrier_data.get('avg_response_time_hours', 24)} hours typical)
5. Tell them what they should do (document damage with photos, get repair estimates, don't dispose of damaged property)
6. Provide agency contact info: Prairie Shield Insurance Group, (402) 555-0100, claims@prairieshield.com

Sign as "The Claims Team at Prairie Shield Insurance Group"

Output ONLY the email text, no commentary."""

    try:
        response = client.messages.create(
            model=SPECIALIST_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        duration_ms = int((time.time() - start) * 1000)

        return {
            "email_text": text,
            "to": client_data.get("email", fnol_data.get("reporter_email", "")),
            "subject": f"Your Claim Has Been Filed — {claim_id or 'Reference Pending'}",
            "duration_ms": duration_ms,
        }
    except Exception as e:
        logger.error(f"Client email generation failed: {e}")
        return {"error": str(e), "email_text": "Email generation failed."}


def generate_followup_email(fnol_data: dict, missing_fields: list[str]) -> dict:
    """Generate a follow-up email requesting missing information."""
    start = time.time()

    reporter_name = fnol_data.get("reporter_name", "there")

    prompt = f"""Write a polite, professional follow-up email requesting missing information needed to complete an FNOL claim filing.

RECIPIENT: {reporter_name}
EMAIL: {fnol_data.get('reporter_email', '')}
MISSING INFORMATION: {', '.join(missing_fields)}
WHAT WE KNOW: {fnol_data.get('description', 'Claim reported')[:200]}

The email should:
1. Thank them for reporting the claim
2. Explain we need a few more details to complete the filing
3. List each missing item clearly with a brief explanation of why it's needed
4. Ask them to reply to this email or call the office
5. Note that prompt reporting helps ensure the best outcome

Sign as "Prairie Shield Insurance Group Claims Team"
Phone: (402) 555-0100

Output ONLY the email text, no commentary."""

    try:
        response = client.messages.create(
            model=SPECIALIST_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        duration_ms = int((time.time() - start) * 1000)

        return {
            "email_text": text,
            "to": fnol_data.get("reporter_email", ""),
            "subject": "Additional Information Needed for Your Claim",
            "missing_fields": missing_fields,
            "duration_ms": duration_ms,
        }
    except Exception as e:
        logger.error(f"Follow-up email generation failed: {e}")
        return {"error": str(e), "email_text": "Email generation failed."}


def _format_dict(d: dict, indent: int = 0) -> str:
    """Format a dict for LLM prompting."""
    lines = []
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}{k}:")
            lines.append(_format_dict(v, indent + 1))
        elif isinstance(v, list):
            lines.append(f"{prefix}{k}: {v}")
        else:
            lines.append(f"{prefix}{k}: {v}")
    return "\n".join(lines)
