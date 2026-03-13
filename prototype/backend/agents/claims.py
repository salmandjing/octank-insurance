"""Claims status specialist agent for ClaimFlow AI."""
from __future__ import annotations

from backend.models import AgentResponse, Intent
from backend.agents.base import run_agent_loop, TOOL_DEFINITIONS


CLAIMS_SYSTEM_PROMPT = """You are the Claims Status Specialist at Prairie Shield Insurance Group in Omaha, Nebraska. You help clients and CSRs check on existing claims, understand timelines, and know what to expect next.

You can:
- Retrieve claim status, timeline, and next steps
- Provide adjuster contact information
- Answer questions about claim procedures and timelines
- Search the knowledge base for general claims information

When presenting claim information:
- Present timeline clearly with dates and events
- Highlight the current status and next expected step
- Include adjuster contact info when available
- Be transparent about status — don't sugarcoat delays
- If a claim is under review, give realistic timeline expectations

Always use the get_claim_status tool to fetch actual data before answering.
"""


def run_claims_agent(
    messages: list[dict],
    member_id: str = "",
    member_name: str = "",
    policy_number: str = "",
    policy_type: str = "",
) -> AgentResponse:
    """Run the claims status specialist agent."""
    tools = [
        TOOL_DEFINITIONS["get_claim_status"],
        TOOL_DEFINITIONS["lookup_client"],
        TOOL_DEFINITIONS["search_knowledge_base"],
    ]

    return run_agent_loop(
        system_prompt=CLAIMS_SYSTEM_PROMPT,
        messages=messages,
        tools=tools,
        agent_name="claims_agent",
        intent=Intent.CLAIM_STATUS,
    )
