"""Mock carrier API — carrier requirements and submission handling."""
from __future__ import annotations
import json
from pathlib import Path

from backend.config import DATA_DIR

_carriers_path = DATA_DIR / "carriers.json"

def _load_carriers():
    with open(_carriers_path) as f:
        return json.load(f)["carriers"]


def get_carrier_requirements(carrier_id: str) -> dict:
    """Get the FNOL requirements for a specific carrier."""
    carriers = _load_carriers()

    carrier = carriers.get(carrier_id)
    if not carrier:
        # Try by name
        for cid, c in carriers.items():
            if carrier_id.lower() in c.get("name", "").lower():
                carrier = c
                break

    if not carrier:
        return {
            "error": f"Carrier '{carrier_id}' not found. Using generic ACORD form format.",
            "fallback_format": "acord_form",
            "required_fields": ["policy_number", "date_of_loss", "location", "description", "claimant_contact"],
        }

    return {
        "carrier_id": carrier["id"],
        "carrier_name": carrier["name"],
        "fnol_method": carrier.get("fnol_method", "portal"),
        "fnol_phone": carrier.get("fnol_phone", ""),
        "fnol_portal_url": carrier.get("fnol_portal_url", ""),
        "claims_email": carrier.get("claims_email", ""),
        "required_fields": carrier.get("required_fnol_fields", []),
        "submission_format": carrier.get("submission_format", "acord_form"),
        "avg_response_time_hours": carrier.get("avg_response_time_hours", 24),
        "lines_of_business": carrier.get("lines", []),
    }
