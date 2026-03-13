"""Policy lookup agent — verifies policies and coverage."""
from __future__ import annotations

from backend.models import AgentResponse, Intent
from backend.agents.base import run_agent_loop, TOOL_DEFINITIONS


POLICY_LOOKUP_SYSTEM = """You are a policy specialist at Prairie Shield Insurance Group in Omaha, Nebraska. You help CSRs and clients understand their coverage, verify policy details, and answer questions about their insurance.

You can:
- Look up policies by number or client name
- Verify coverage is active for a given date
- Explain coverage types, limits, and deductibles
- Answer questions about what's covered

IMPORTANT: Never state definitively that something is or isn't covered. Always note that coverage determinations are made by the carrier. You can say "this type of loss is typically covered under your policy type" but must defer to the carrier.

Always append this disclaimer when discussing coverage:
"Please note that all coverage determinations are made by your insurance carrier. This information is provided for reference only."
"""


def run_policy_lookup_agent(
    messages: list[dict],
    member_id: str = "",
    member_name: str = "",
    policy_number: str = "",
    policy_type: str = "",
) -> AgentResponse:
    """Run the policy lookup agent."""
    tools = [
        TOOL_DEFINITIONS["lookup_policy"],
        TOOL_DEFINITIONS["lookup_client"],
        TOOL_DEFINITIONS["verify_coverage"],
        TOOL_DEFINITIONS["search_knowledge_base"],
    ]

    return run_agent_loop(
        system_prompt=POLICY_LOOKUP_SYSTEM,
        messages=messages,
        tools=tools,
        agent_name="policy_lookup_agent",
        intent=Intent.POLICY_QUESTION,
    )
