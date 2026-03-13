"""Mock Agency Management System (AMS) API — policy and client lookup tools."""
from __future__ import annotations
import json
from pathlib import Path

from backend.config import DATA_DIR

# Load data at module level
_clients_path = DATA_DIR / "clients.json"
_policies_path = DATA_DIR / "policies.json"

def _load_clients():
    with open(_clients_path) as f:
        return json.load(f)["clients"]

def _load_policies():
    with open(_policies_path) as f:
        return json.load(f)["policies"]


def lookup_policy(policy_number: str) -> dict:
    """Look up a policy by policy number. Returns full policy details."""
    policies = _load_policies()
    clients = _load_clients()

    # Search by policy_number field or by ID
    for pol_id, pol in policies.items():
        if pol.get("policy_number", "").lower() == policy_number.lower() or pol_id.lower() == policy_number.lower():
            # Attach client info
            client_id = pol.get("client_id", "")
            client = clients.get(client_id, {})
            return {
                **pol,
                "client_name": client.get("name", "Unknown"),
                "client_email": client.get("email", ""),
                "client_phone": client.get("phone", ""),
                "client_address": client.get("address", ""),
            }

    return {"error": f"Policy '{policy_number}' not found in our system. Please verify the policy number."}


def lookup_client(client_name: str) -> dict:
    """Look up a client by name (fuzzy match). Returns client details and policies."""
    clients = _load_clients()
    policies = _load_policies()

    search = client_name.lower()
    matches = []

    for client_id, client in clients.items():
        name = client.get("name", "").lower()
        contact = client.get("contact_person", "").lower()
        if search in name or search in contact or any(word in name for word in search.split()):
            # Get their policies
            client_policies = []
            for pol_id in client.get("policies", []):
                pol = policies.get(pol_id, {})
                if pol:
                    client_policies.append({
                        "id": pol_id,
                        "type": pol.get("type", ""),
                        "carrier": pol.get("carrier", ""),
                        "policy_number": pol.get("policy_number", ""),
                        "status": pol.get("status", ""),
                        "effective_date": pol.get("effective_date", ""),
                        "expiration_date": pol.get("expiration_date", ""),
                    })

            matches.append({
                **client,
                "active_policies": client_policies,
            })

    if not matches:
        return {"error": f"No client found matching '{client_name}'"}

    if len(matches) == 1:
        return matches[0]

    return {"matches": matches, "message": f"Found {len(matches)} clients matching '{client_name}'"}


def verify_coverage(policy_id: str, date_of_loss: str, loss_type: str) -> dict:
    """Verify that a loss type is potentially covered under a policy as of a date."""
    policies = _load_policies()

    policy = policies.get(policy_id)
    if not policy:
        # Try by policy_number
        for pid, pol in policies.items():
            if pol.get("policy_number", "") == policy_id:
                policy = pol
                policy_id = pid
                break

    if not policy:
        return {"error": f"Policy '{policy_id}' not found"}

    # Check if policy is active
    status = policy.get("status", "")
    if status != "active":
        return {
            "covered": False,
            "reason": f"Policy status is '{status}'. Only active policies provide coverage.",
            "policy_id": policy_id,
        }

    # Check date is within policy period
    eff = policy.get("effective_date", "")
    exp = policy.get("expiration_date", "")
    if eff and exp and date_of_loss:
        if date_of_loss < eff or date_of_loss > exp:
            return {
                "covered": False,
                "reason": f"Date of loss ({date_of_loss}) is outside the policy period ({eff} to {exp}).",
                "policy_id": policy_id,
            }

    # Check loss type vs policy type coverage
    policy_type = policy.get("type", "")
    coverage = policy.get("coverage", {})

    # Build coverage details response
    coverage_info = {
        "potentially_covered": True,
        "policy_id": policy_id,
        "policy_type": policy_type,
        "carrier": policy.get("carrier", ""),
        "carrier_id": policy.get("carrier_id", ""),
        "policy_number": policy.get("policy_number", ""),
        "coverage_details": coverage,
        "date_of_loss": date_of_loss,
        "loss_type": loss_type,
        "note": "Coverage determinations are made by the carrier. This is a preliminary assessment only.",
    }

    # Add deductible info
    if "deductible" in coverage:
        coverage_info["applicable_deductible"] = coverage["deductible"]
    if loss_type in ("hail", "wind") and "wind_hail_deductible" in coverage:
        coverage_info["applicable_deductible"] = coverage["wind_hail_deductible"]
        coverage_info["deductible_note"] = "Wind/hail deductible applies (percentage of dwelling value)"
    if "collision" in coverage and loss_type in ("collision", "auto_collision"):
        coverage_info["applicable_deductible"] = coverage["collision"].get("deductible", "See policy")
    if "comprehensive" in coverage and loss_type in ("comprehensive", "auto_comprehensive", "theft", "hail", "vandalism"):
        coverage_info["applicable_deductible"] = coverage["comprehensive"].get("deductible", "See policy")

    return coverage_info
