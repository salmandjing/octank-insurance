# Octank Insurance Virtual Agent — 10-Minute Demo Script

This script walks through the key features in a natural order designed for a presales audience. Times are approximate — adjust pacing based on audience engagement.

---

## Before You Start

- Server running: `cd prototype && ./start.sh`
- Open http://localhost:8000 in Chrome (required for voice features)
- Hard-refresh (Cmd+Shift+R) to clear any cached JS
- Verify the "Under the Hood" panel is visible on the right (toggle with the panel button in the header if not)

---

## Act 1: The AI Agent Experience (0:00 – 5:00)

### Opening — Set the Scene (30 seconds)

> "This is a working prototype of an agentic virtual agent for auto insurance member servicing. Everything you're about to see is real — real LLM calls to Claude via AWS Bedrock, real multi-agent routing, real RAG retrieval over policy documents. The only things that are mocked are the member data and the backend APIs."

### 1.1 — Member Authentication & Eligibility (1:30)

1. **Select Sarah Chen** from the dropdown — point out the member preview card
2. Click **Start Conversation**
3. Type: **"What does my policy cover?"**
4. While the thinking indicator is showing, narrate what's happening:
   > "Right now the Supervisor Agent — Claude 3.5 Haiku — is classifying the intent and sentiment. Watch the trace panel on the right..."
5. When the response arrives, walk through:
   - **Agent Trace tab**: Show the step-by-step timeline — supervisor classification, routing decision, specialist agent, tool calls, RAG retrieval, guardrails. Expand a step to show the detail.
   - **Tool badges** on the message (orange pills): "The agent autonomously decided to call `get_eligibility` — we didn't hardcode that."
   - **Source badges** (blue pills): "It also searched the knowledge base and grounded its response in these policy documents."
   - **Knowledge tab**: Show the RAG source cards with relevance scores. Click "Open Document" to show the full document viewer with the matched section highlighted.
   - **Confidence badge**: "Every response gets a confidence score based on hallucination signal detection."

### 1.2 — Filing a Claim / FNOL (2:00)

1. Type: **"I was in a fender bender yesterday on Highway 101"**
2. The FNOL agent will ask follow-up questions — answer them naturally:
   - Location: "San Jose, near the Costco on Coleman"
   - Injuries: "No injuries, just bumper damage"
   - Other party: "Yes, we exchanged info"
3. When it asks to confirm and file, say **"Yes, go ahead"**
4. Point out:
   - **Multi-turn orchestration**: "The FNOL agent guided us through a structured intake process across multiple turns — collecting date, location, description, injury status — then confirmed before filing."
   - **Tool call in Tools tab**: Expand the `create_fnol` card to show the structured input/output
   - **Write badge**: "This was a write operation — the agent created a record, not just a read."

### 1.3 — Guardrails in Action (1:00)

1. Click the **Guardrails Demo** quick action button in the sidebar (or type: "Should I see a doctor about my neck pain?")
2. Watch the trace panel auto-switch to show the **guardrail firing**:
   > "The system detected a medical advice request and blocked it. This isn't just keyword matching — the guardrail evaluates the response content and redirects the conversation. In the trace you can see exactly where it fired and why."
3. **Optional** — type an SSN like "My SSN is 123-45-6789" to show PII detection:
   > "PII is automatically detected and redacted from logs. Check the Review Queue tab — it's flagged with the turn number and pattern detected."

---

## Act 2: The Genesys Story (5:00 – 7:30)

### 2.1 — Discovery Mode (30 seconds)

1. Press **D** on the keyboard (or click the Discovery button in the header)
2. Walk through the annotated overlay:
   > "Every component in this prototype maps to a Genesys Cloud CX capability. The chat interface maps to Web Messenger. The sidebar is CRM Screen Pop via Data Actions. The AI agent maps to Bot Connector API backed by Bedrock Agents. The trace panel is the Agent Supervisor Dashboard."
3. Point out the **business metrics bar** at the bottom: 73% containment, ~$0.02/interaction, <3s response, 10K/day scale
4. Click anywhere to dismiss

### 2.2 — Architecture Deep Dive (1:00)

1. Press **G** (or click Architecture in the header)
2. Walk through the **component mapping table**:
   > "Left column is what we built. Right column is the exact Genesys component. FastAPI becomes Bot Connector API. The Supervisor Agent becomes an Architect Bot Flow. Specialist agents map to Bedrock Agents. Our mock tools become Genesys Data Actions."
3. Point out the **4 integration cards**: Voice (IVR), Digital (Web Messaging), WEM (Quality Management), Routing (ACD + Skills)
4. Scroll to **Resilience & Failure Modes**: "We've mapped 4 failure scenarios — Bedrock timeout, RAG index failure, tool API timeout, confidence below threshold — each with a circuit breaker pattern and graceful fallback."
5. Note the **cost grid**: "Haiku classification costs roughly $0.001 per message. Sonnet reasoning about $0.02. At 10,000 conversations per day, that's approximately $210/day for the AI layer."
6. Close the modal

### 2.3 — Escalation & Handoff (1:00)

1. Type: **"I want to speak to a human agent"**
2. The escalation banner appears — point out the Genesys labels:
   > "Notice the escalation banner shows the ACD queue (CLM-PRIORITY), the skill (claims-specialist), and the priority level. This maps directly to a `transferToAcd` action in Genesys Architect."
3. Click **"View Agent Desktop"**

---

## Act 3: The Human Agent Experience (7:30 – 9:30)

### 3.1 — Agent Desktop Overview (1:00)

> "This is what the human agent sees when they accept the handoff. Zero context loss."

Walk through the 4 panels:

1. **AI Summary Banner** (top): "Haiku generated a 3-5 sentence briefing — who the member is, what happened, what's unresolved, and their emotional state."
2. **Screen Pop** (left): Member details, sentiment timeline showing the emotional arc as colored dots, every AI action taken with turn numbers
3. **Transcript** (center): Full conversation history with avatars — the agent can scroll through everything that happened
4. **Knowledge** (right): Two tabs:
   - "Retrieved" — documents the AI actually used during the conversation
   - "Suggested" — fresh proactive RAG search using the full conversation as the query, surfacing documents the AI may not have found
5. **Agent Assist** (far right): LLM-generated open questions (what's still unresolved), checkable suggested actions (concrete next steps), escalation details

### 3.2 — Handoff Context Payload (30 seconds)

1. Expand the **Handoff Payload** section in the screen pop panel
2. Show the JSON:
   > "This is the exact structure that would be sent as Genesys conversation attributes during `transferToAcd`. AI summary, intent, sentiment history, tools used, routing priority — all structured data the agent or downstream systems can consume."

### 3.3 — Handle Timer & Accept (30 seconds)

Point out the header: "INBOUND" queue badge, handle timer counting up, pulsing Accept button.

> "This mimics the Genesys Agent Workspace experience. The agent sees the queue, the timer, and can accept. In production, this would be the actual Genesys agent workspace with all of this context injected via screen pop."

---

## Act 4: Operational Readiness (9:30 – 10:00)

### Quick Hits (pick 1-2 based on audience interest)

**Compliance** (if regulated industry audience):
- Switch to the **Compliance tab** in the Under the Hood panel
- Show: HIPAA triggering dynamically when injuries are mentioned, PII detection, topic blocking, data residency (toggle EU region to show GDPR notice), bias & fairness statement

**Analytics** (if ops/WFM audience):
- Click **Analytics** in the header
- Show the dashboard: 6 KPI cards, intent distribution, sentiment breakdown, escalation reasons, tool usage frequency
- Note: "These are baseline metrics. In production, these would be fed by Genesys WEM and real conversation data."

**Latency** (if technical audience):
- Toggle **Latency Sim** in the header, send a message
- Show the **Gantt-style waterfall** in the trace panel: ASR → Classification → Tools → Generation → Guardrails → TTS
- "Each bar is proportional. Total end-to-end is typically under 3 seconds. The filler phrases you see — 'Let me check that for you...' — mask the wait, same pattern as production IVR systems."

**Confidence & Review Queue** (if quality/compliance audience):
- Show the **escalation threshold slider** in the sidebar
- Drag it up to 90% — now more responses get flagged for human review
- Check the Review Queue tab to see flagged items

---

## Closing (at 10:00)

> "Everything you saw is running locally on my machine — a single Python process, no infrastructure beyond Bedrock API access. The AI reasoning, tool use, RAG, guardrails, and agent handoff are all real. What's mocked is the data and the telephony layer. The path to production is swapping those mock tools for Genesys Data Actions, the mock data for your CRM, and deploying behind Bot Connector API."

---

## Tips

- **Keep the Hood panel open** throughout — it's the most impressive part for technical audiences. The live trace showing supervisor → routing → specialist → tools → RAG → guardrails in real time is the key differentiator.
- **Don't rush Act 1.1** — the first message + trace walkthrough is where the audience "gets it." Everything after that builds on that understanding.
- **Adapt Act 4** to your audience — pick the quick hit that resonates most. Skip the others.
- **If something takes too long to respond** — narrate what's happening ("Sonnet is reasoning through the tool results..."). The thinking indicator and trace panel events fill the gap.
- **If asked "is this production-ready?"** — be honest: "This is a working prototype that demonstrates the architecture and UX. The AI reasoning and RAG are production-grade. What needs work for production is persistence, streaming responses, embeddings-based RAG, proper authentication, and Genesys API integration."

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **D** | Toggle Discovery Mode overlay |
| **G** | Open Architecture modal |
| **Enter** | Send message |
| **Shift+Enter** | New line in message |
