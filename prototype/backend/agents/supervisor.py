"""Supervisor agent — intent classification and routing."""
from __future__ import annotations
import json
import logging
from anthropic import AnthropicBedrock

from backend.config import AWS_REGION, SUPERVISOR_MODEL_ID
from backend.models import Intent

logger = logging.getLogger(__name__)
client = AnthropicBedrock(aws_region=AWS_REGION)

SUPERVISOR_SYSTEM_PROMPT = """You are a supervisor agent for Octank Insurance's virtual assistant. Your ONLY job is to classify the member's intent and decide which specialist agent should handle their request.

Analyze the member's message and the conversation history, then use the classify_intent tool to return your classification.

## Intent Categories

- **eligibility**: Questions about coverage, benefits, deductibles, policy details, what's covered/not covered, limits, discounts, premiums, billing
- **fnol**: Member wants to report an accident or incident, file a new claim, or report damage/theft/loss. Keywords: accident, fender bender, crash, hit, damage, stolen, vandalized, hail, file a claim
- **claim_status**: Questions about an existing claim, claim progress, timeline, adjuster info, next steps, payment status. Keywords: my claim, claim status, where is my claim, claim number, adjuster
- **general**: Greetings, general questions about Octank, questions not related to the above categories, or unclear intent
- **escalate**: Member explicitly asks to speak to a human, agent, representative, manager, or supervisor. Also if member expresses extreme frustration or anger.

## Routing Rules

1. If the member mentions an accident, incident, or wants to file/report something → **fnol**
2. If the member asks about an existing claim or claim number → **claim_status**
3. If the member asks about their coverage, deductible, benefits, or policy → **eligibility**
4. If the member says "talk to a human", "speak to someone", "real person", "manager" → **escalate**
5. If the member uses profanity or expresses extreme frustration → **escalate**
6. For greetings or unclear messages → **general**

## Important
- Look at the FULL conversation history, not just the last message
- If the conversation has been about FNOL and the member is providing follow-up info, keep routing to **fnol**
- If the conversation has been about claims and member asks a follow-up, keep routing to **claim_status**
"""

CLASSIFY_TOOL = {
    "name": "classify_intent",
    "description": "Classify the member's intent, assess sentiment, and route to the appropriate specialist",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["eligibility", "fnol", "claim_status", "general", "escalate"],
                "description": "The classified intent"
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score from 0.0 to 1.0"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of why this intent was chosen"
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "concerned", "frustrated", "angry"],
                "description": "The member's current emotional state based on their message tone and language"
            }
        },
        "required": ["intent", "confidence", "reasoning", "sentiment"]
    }
}


def classify_intent(
    messages: list[dict],
    member_name: str = "",
    current_agent: str = "",
) -> tuple[Intent, float, str, str]:
    """Classify the intent of the latest user message given conversation history.

    Returns (intent, confidence, reasoning, sentiment).
    """
    # Add context about current agent for continuity
    context_note = ""
    if current_agent:
        context_note = f"\n\nNote: The conversation is currently being handled by the {current_agent}. Only reclassify if the member's intent has clearly changed."

    response = client.messages.create(
        model=SUPERVISOR_MODEL_ID,
        max_tokens=512,
        temperature=0.0,
        system=SUPERVISOR_SYSTEM_PROMPT + context_note,
        messages=messages,
        tools=[CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "classify_intent"},
    )

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use" and block.name == "classify_intent":
            result = block.input
            intent_str = result.get("intent", "general")
            confidence = result.get("confidence", 0.5)
            reasoning = result.get("reasoning", "")
            sentiment = result.get("sentiment", "neutral")

            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.GENERAL

            logger.info(f"[Supervisor] Intent: {intent.value} ({confidence:.0%}) Sentiment: {sentiment} — {reasoning}")
            return intent, confidence, reasoning, sentiment

    # Fallback
    logger.warning("[Supervisor] Failed to classify intent, defaulting to GENERAL")
    return Intent.GENERAL, 0.5, "Classification failed, defaulting to general", "neutral"
