"""Mock claims API tools for ClaimFlow AI."""
from __future__ import annotations
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.config import DATA_DIR

_claims_path = DATA_DIR / "claims.json"

# Load initial claims data
def _load_claims():
    with open(_claims_path) as f:
        return json.load(f)["claims"]

# In-memory claims store (loaded from file + any new claims added during session)
_claims_db: dict | None = None

def _get_claims_db():
    global _claims_db
    if _claims_db is None:
        _claims_db = _load_claims()
    return _claims_db


def get_claim_status(client_id: str, claim_id: str | None = None) -> dict:
    """Retrieve claim status for a client."""
    claims = _get_claims_db()

    if claim_id:
        claim = claims.get(claim_id)
        if not claim:
            return {"error": f"Claim {claim_id} not found"}
        return _format_claim(claim)

    # Return all claims for this client
    client_claims = [
        _format_claim(c) for c in claims.values()
        if c.get("client_id") == client_id
    ]

    if not client_claims:
        return {
            "client_id": client_id,
            "claims": [],
            "message": "No claims found for this client."
        }

    return {
        "client_id": client_id,
        "claims": client_claims,
    }


def _format_claim(claim: dict) -> dict:
    return {
        "claim_id": claim.get("id", claim.get("claim_id", "")),
        "client_id": claim.get("client_id", ""),
        "policy_id": claim.get("policy_id", ""),
        "carrier": claim.get("carrier", ""),
        "status": claim.get("status", ""),
        "type": claim.get("type", ""),
        "peril": claim.get("peril", ""),
        "date_of_loss": claim.get("date_of_loss", ""),
        "date_reported": claim.get("date_reported", ""),
        "description": claim.get("description", ""),
        "estimated_damage": claim.get("estimated_damage"),
        "approved_amount": claim.get("approved_amount"),
        "adjuster": claim.get("adjuster"),
        "timeline": claim.get("timeline", []),
        "police_report": claim.get("police_report", False),
        "police_report_number": claim.get("police_report_number", ""),
        "injuries": claim.get("injuries", False),
    }


def create_claim_record(
    client_id: str,
    policy_id: str,
    carrier: str,
    carrier_id: str,
    loss_type: str,
    date_of_loss: str,
    description: str,
    location: str = "",
    injuries: bool = False,
    injury_description: str = "",
    police_report: bool = False,
    police_report_number: str = "",
    estimated_damage: float | None = None,
    priority: str = "normal",
) -> dict:
    """Create a new claim record in the mock AMS."""
    claims = _get_claims_db()

    claim_id = f"CLM-{datetime.now().year}-{uuid.uuid4().hex[:4].upper()}"

    new_claim = {
        "id": claim_id,
        "client_id": client_id,
        "policy_id": policy_id,
        "carrier": carrier,
        "carrier_id": carrier_id,
        "type": loss_type,
        "peril": loss_type,
        "date_of_loss": date_of_loss,
        "date_reported": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "status": "new",
        "description": description,
        "location": location,
        "injuries": injuries,
        "injury_description": injury_description if injuries else "",
        "police_report": police_report,
        "police_report_number": police_report_number,
        "estimated_damage": estimated_damage,
        "adjuster": None,
        "photos_submitted": False,
        "priority": priority,
        "timeline": [
            {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "event": "FNOL submitted by agency via ClaimFlow AI"}
        ],
    }

    claims[claim_id] = new_claim

    return {
        "claim_id": claim_id,
        "status": "new",
        "message": f"Claim {claim_id} created successfully.",
        "next_steps": [
            f"Carrier ({carrier}) will be notified",
            "An adjuster will be assigned — typical response within 24 hours",
            "Client confirmation email will be sent",
        ],
    }


def escalate_to_human(reason: str, conversation_summary: str) -> dict:
    """Escalate the conversation to a human agent."""
    escalation_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    return {
        "escalation_id": escalation_id,
        "status": "escalated",
        "reason": reason,
        "conversation_summary": conversation_summary,
        "message": "This has been escalated to a CSR for manual review. A team member will follow up shortly.",
    }
