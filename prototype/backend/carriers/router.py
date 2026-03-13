"""Carrier routing — routes claims to correct carrier with correct format."""
from __future__ import annotations
import json
from pathlib import Path

from backend.config import DATA_DIR

_carriers_path = DATA_DIR / "carriers.json"
_policies_path = DATA_DIR / "policies.json"


def _load_carriers():
    with open(_carriers_path) as f:
        return json.load(f)["carriers"]

def _load_policies():
    with open(_policies_path) as f:
        return json.load(f)["policies"]


class CarrierRouter:
    """Routes FNOL submissions to the correct carrier with the correct format."""

    def get_carrier_for_policy(self, policy_id: str) -> dict:
        """Look up which carrier insures this policy."""
        policies = _load_policies()
        carriers = _load_carriers()

        policy = policies.get(policy_id)
        if not policy:
            # Try by policy_number
            for pid, pol in policies.items():
                if pol.get("policy_number", "") == policy_id:
                    policy = pol
                    break

        if not policy:
            return {"error": f"Policy {policy_id} not found"}

        carrier_id = policy.get("carrier_id", "")
        carrier = carriers.get(carrier_id, {})

        return {
            "carrier_id": carrier_id,
            "carrier_name": carrier.get("name", policy.get("carrier", "Unknown")),
            "fnol_method": carrier.get("fnol_method", "portal"),
            "fnol_phone": carrier.get("fnol_phone", ""),
            "claims_email": carrier.get("claims_email", ""),
            "submission_format": carrier.get("submission_format", "acord_form"),
            "required_fields": carrier.get("required_fnol_fields", []),
            "avg_response_time_hours": carrier.get("avg_response_time_hours", 24),
        }

    def get_required_fields(self, carrier_id: str, loss_type: str = "") -> list[str]:
        """Get the required FNOL fields for this carrier."""
        carriers = _load_carriers()
        carrier = carriers.get(carrier_id, {})
        return carrier.get("required_fnol_fields", [
            "policy_number", "date_of_loss", "location", "description", "claimant_contact"
        ])

    def validate_submission(self, carrier_id: str, fnol_data: dict) -> dict:
        """Check if the FNOL data meets the carrier's requirements."""
        required = self.get_required_fields(carrier_id)

        field_mapping = {
            "policy_number": fnol_data.get("policy_number"),
            "date_of_loss": fnol_data.get("date_of_loss"),
            "time_of_loss": fnol_data.get("time_of_loss"),
            "location": fnol_data.get("location"),
            "description": fnol_data.get("description"),
            "claimant_contact": fnol_data.get("reporter_phone") or fnol_data.get("reporter_email"),
            "police_report_number": fnol_data.get("police_report_number"),
            "injuries": fnol_data.get("injuries"),
            "other_parties": fnol_data.get("other_parties"),
            "estimated_damage": fnol_data.get("estimated_damage"),
            "witness_info": fnol_data.get("witness_info"),
            "photos": fnol_data.get("photos_mentioned"),
            "emergency_services_called": fnol_data.get("emergency_services_called"),
            "type_of_loss": fnol_data.get("loss_type"),
        }

        missing = [f for f in required if not field_mapping.get(f)]

        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "provided_fields": [f for f in required if field_mapping.get(f)],
            "carrier_id": carrier_id,
        }


# Singleton
carrier_router = CarrierRouter()
