"""Mock eligibility API tool."""
from __future__ import annotations
from backend.state.session import MEMBERS_DB


def get_eligibility(member_id: str) -> dict:
    """Retrieve eligibility and coverage details for a member."""
    member = MEMBERS_DB.get(member_id)
    if not member:
        return {"error": f"Member {member_id} not found"}

    coverage = member.get("coverage", {})
    return {
        "member_id": member_id,
        "name": member["name"],
        "policy_number": member["policy_number"],
        "policy_type": member["policy_type"],
        "coverage_type": coverage.get("type", "Unknown"),
        "liability_limit": coverage.get("liability_limit", "N/A"),
        "deductible": coverage.get("deductible", 0),
        "out_of_pocket_max": coverage.get("out_of_pocket_max", 0),
        "uninsured_motorist": coverage.get("uninsured_motorist", False),
        "rental_coverage": coverage.get("rental_coverage", False),
        "roadside_assistance": coverage.get("roadside_assistance", False),
        "effective_date": member.get("effective_date", ""),
        "expiration_date": member.get("expiration_date", ""),
        "vehicles": member.get("vehicles", []),
    }
