"""Claims status specialist agent."""
from __future__ import annotations

from backend.models import AgentResponse, Intent
from backend.agents.base import run_agent_loop, TOOL_DEFINITIONS


CLAIMS_SYSTEM_PROMPT = """You are the Claims Status Specialist for Octank Insurance's virtual assistant. You help members check on their existing claims, understand timelines, and know what to expect next.

## Member Context
Member: {member_name} (ID: {member_id})
Policy: {policy_number} ({policy_type})

## Your Job
- Retrieve and explain claim status, timeline, and next steps
- Help members understand where their claim is in the process
- Provide adjuster contact information when relevant
- Answer questions about claim procedures and timelines

## Tools Available
1. **get_claim_status** — Retrieve claim details, timeline, and next steps
2. **search_knowledge_base** — Look up claims procedures and general information

## Instructions
- Use get_claim_status to fetch actual claim data before answering
- If the member doesn't specify a claim ID, retrieve all their claims
- Present timeline information clearly, highlighting the current step
- Always include next steps so the member knows what to expect
- If a claim is under review, give realistic timeline expectations
- When citing procedures, mention the source document
- Be transparent about status — don't sugarcoat delays

## Response Style
- Professional and informative
- Use clear formatting for timelines (dates, status, events)
- Be specific with dates and next steps
- Empathetic if the member seems frustrated with the process
- Offer to help with anything else
"""


def run_claims_agent(
    messages: list[dict],
    member_id: str,
    member_name: str,
    policy_number: str,
    policy_type: str,
) -> AgentResponse:
    """Run the claims status specialist agent."""
    system_prompt = CLAIMS_SYSTEM_PROMPT.format(
        member_name=member_name,
        member_id=member_id,
        policy_number=policy_number,
        policy_type=policy_type,
    )

    tools = [
        TOOL_DEFINITIONS["get_claim_status"],
        TOOL_DEFINITIONS["search_knowledge_base"],
    ]

    return run_agent_loop(
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
        agent_name="claims_agent",
        intent=Intent.CLAIM_STATUS,
    )
