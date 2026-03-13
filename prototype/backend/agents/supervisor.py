"""Supervisor agent — intent classification and routing for ClaimFlow AI."""
from __future__ import annotations
import json
import logging
import anthropic

from backend.config import SUPERVISOR_MODEL, TEMPERATURE
from backend.models import Intent, Priority

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()

SUPERVISOR_SYSTEM_PROMPT = """You are the supervisor agent for ClaimFlow AI at Prairie Shield Insurance Group in Omaha, Nebraska. Your job is to classify the intent and priority of incoming messages.

## Intent Categories

- **fnol_auto**: Auto accident/damage claim (collision, comprehensive, theft, vandalism)
- **fnol_property**: Home/commercial property damage claim (hail, wind, fire, water, theft)
- **fnol_farm**: Farm/ranch loss claim (livestock, structures, equipment, crop)
- **fnol_commercial**: Commercial liability/vehicle claim (commercial auto, GL, product liability)
- **fnol_workers_comp**: Workers compensation claim (workplace injury)
- **claim_status**: Check on existing claim, claim progress, adjuster info
- **policy_question**: Coverage question, policy lookup, deductible question
- **coi_request**: Certificate of insurance request
- **billing_question**: Payment, premium question
- **general**: Greetings, general questions, unclear intent
- **escalate**: Wants to talk to a human, extreme frustration

## Priority Levels

- **critical**: Ongoing damage, injuries requiring medical attention, fire
- **high**: Minor injuries, commercial vehicle, workers comp, livestock
- **elevated**: Large loss estimate, multiple vehicles, time-sensitive
- **normal**: Standard FNOL filing or inquiry

## Routing Rules

1. Mentions accident, crash, collision, hit, damage to vehicle -> **fnol_auto**
2. Mentions hail, wind, roof, water damage, fire, theft at home/building -> **fnol_property**
3. Mentions barn, grain bin, cattle, livestock, farm equipment -> **fnol_farm**
4. Mentions truck accident, company vehicle, slip and fall at business -> **fnol_commercial**
5. Mentions workplace injury, hurt at work, on the job -> **fnol_workers_comp**
6. Mentions existing claim, claim number, adjuster, claim status -> **claim_status**
7. Mentions coverage, deductible, what's covered, policy details -> **policy_question**
8. Mentions certificate, COI, proof of insurance -> **coi_request**
9. Mentions payment, bill, premium -> **billing_question**
10. Wants human, manager, real person, extremely frustrated -> **escalate**
11. Greetings or unclear -> **general**

Look at the FULL conversation history, not just the last message. If conversation has been about filing a claim, keep routing to the appropriate fnol type.
"""

CLASSIFY_TOOL = {
    "name": "classify_intent",
    "description": "Classify the intent and priority of the message",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [i.value for i in Intent],
                "description": "The classified intent"
            },
            "priority": {
                "type": "string",
                "enum": [p.value for p in Priority],
                "description": "Priority level"
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score 0.0 to 1.0"
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation"
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "concerned", "frustrated", "angry"],
                "description": "Emotional state"
            }
        },
        "required": ["intent", "priority", "confidence", "reasoning", "sentiment"]
    }
}


def classify_intent(
    messages: list[dict],
    member_name: str = "",
    current_agent: str = "",
) -> tuple[Intent, float, str, str, Priority]:
    """Returns (intent, confidence, reasoning, sentiment, priority)."""
    context_note = ""
    if current_agent:
        context_note = f"\n\nNote: Currently handled by {current_agent}. Only reclassify if intent has clearly changed."

    try:
        response = client.messages.create(
            model=SUPERVISOR_MODEL,
            max_tokens=512,
            temperature=0.0,
            system=SUPERVISOR_SYSTEM_PROMPT + context_note,
            messages=messages,
            tools=[CLASSIFY_TOOL],
            tool_choice={"type": "tool", "name": "classify_intent"},
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "classify_intent":
                result = block.input
                intent_str = result.get("intent", "general")
                confidence = result.get("confidence", 0.5)
                reasoning = result.get("reasoning", "")
                sentiment = result.get("sentiment", "neutral")
                priority_str = result.get("priority", "normal")

                try:
                    intent = Intent(intent_str)
                except ValueError:
                    intent = Intent.GENERAL

                try:
                    priority = Priority(priority_str)
                except ValueError:
                    priority = Priority.NORMAL

                logger.info(f"[Supervisor] Intent: {intent.value} Priority: {priority.value} ({confidence:.0%}) Sentiment: {sentiment}")
                return intent, confidence, reasoning, sentiment, priority

    except Exception as e:
        logger.error(f"[Supervisor] Classification failed: {e}")

    return Intent.GENERAL, 0.5, "Classification failed, defaulting to general", "neutral", Priority.NORMAL
