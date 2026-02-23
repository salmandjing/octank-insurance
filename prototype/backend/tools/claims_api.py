"""Mock claims API tools."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from backend.state.session import MEMBERS_DB, CLAIMS_DB


def get_claim_status(member_id: str, claim_id: str | None = None) -> dict:
    """Retrieve claim status for a member. If no claim_id, return all recent claims."""
    member = MEMBERS_DB.get(member_id)
    if not member:
        return {"error": f"Member {member_id} not found"}

    if claim_id:
        claim = CLAIMS_DB.get(claim_id)
        if not claim:
            return {"error": f"Claim {claim_id} not found"}
        if claim["member_id"] != member_id:
            return {"error": f"Claim {claim_id} does not belong to member {member_id}"}
        return _format_claim(claim)

    # Return all claims for this member
    member_claims = [
        _format_claim(c) for c in CLAIMS_DB.values()
        if c["member_id"] == member_id
    ]

    if not member_claims:
        return {
            "member_id": member_id,
            "claims": [],
            "message": "No claims found for this member."
        }

    return {
        "member_id": member_id,
        "claims": member_claims,
    }


def _format_claim(claim: dict) -> dict:
    return {
        "claim_id": claim["claim_id"],
        "status": claim["status"],
        "type": claim["type"],
        "filed_date": claim["filed_date"],
        "date_of_loss": claim["date_of_loss"],
        "description": claim["description"],
        "estimated_damage": claim.get("estimated_damage"),
        "approved_amount": claim.get("approved_amount"),
        "adjuster": claim.get("adjuster"),
        "timeline": claim.get("timeline", []),
        "next_steps": claim.get("next_steps", []),
    }


def create_fnol(
    member_id: str,
    date_of_loss: str,
    description: str,
    location: str = "",
    injuries: bool = False,
    injury_description: str = "",
    police_report_number: str = "",
) -> dict:
    """Create a First Notice of Loss (FNOL) claim."""
    member = MEMBERS_DB.get(member_id)
    if not member:
        return {"error": f"Member {member_id} not found"}

    claim_id = f"CLM-{datetime.now().year}-{uuid.uuid4().hex[:3].upper()}"
    confirmation_number = f"CONF-{uuid.uuid4().hex[:8].upper()}"

    new_claim = {
        "claim_id": claim_id,
        "confirmation_number": confirmation_number,
        "member_id": member_id,
        "policy_number": member["policy_number"],
        "status": "filed",
        "type": "collision",
        "filed_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "date_of_loss": date_of_loss,
        "description": description,
        "location": location,
        "injuries": injuries,
        "injury_description": injury_description if injuries else "",
        "police_report_number": police_report_number,
        "next_steps": [
            "A claims adjuster will be assigned within 24 hours and will contact you directly",
            "Please have photos of the damage ready for the adjuster",
            f"Your claim number is {claim_id} — use this for any follow-up inquiries",
            "You can check your claim status anytime through our virtual agent or member portal",
        ],
    }

    # Add to in-memory DB
    CLAIMS_DB[claim_id] = new_claim

    return {
        "claim_id": claim_id,
        "confirmation_number": confirmation_number,
        "status": "filed",
        "filed_date": new_claim["filed_date"],
        "next_steps": new_claim["next_steps"],
        "message": f"Your FNOL has been successfully filed. Claim ID: {claim_id}, Confirmation: {confirmation_number}",
    }


def escalate_to_human(reason: str, conversation_summary: str) -> dict:
    """Escalate the conversation to a human agent."""
    escalation_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    return {
        "escalation_id": escalation_id,
        "status": "escalated",
        "reason": reason,
        "conversation_summary": conversation_summary,
        "estimated_wait_time": "3 minutes",
        "message": "You are being connected to a claims specialist. Your estimated wait time is approximately 3 minutes. A summary of our conversation has been shared with the specialist so you won't need to repeat yourself.",
        "queue_position": 2,
    }


def schedule_callback(
    member_id: str,
    preferred_time: str = "",
    phone_number: str = "",
    reason: str = "",
) -> dict:
    """Schedule a callback from a human agent."""
    member = MEMBERS_DB.get(member_id)
    if not member:
        return {"error": f"Member {member_id} not found"}

    callback_id = f"CB-{uuid.uuid4().hex[:8].upper()}"
    return {
        "callback_id": callback_id,
        "status": "scheduled",
        "member_id": member_id,
        "preferred_time": preferred_time or "Next available slot",
        "phone_number": phone_number or member.get("phone", "On file"),
        "reason": reason,
        "message": f"Your callback has been scheduled (ID: {callback_id}). An agent will call you at {preferred_time or 'the next available time'}. You'll receive a confirmation via text.",
    }
