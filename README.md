# Octank Insurance — Agentic Virtual Agent Prototype

A working prototype of an agentic virtual agent for auto insurance member servicing. Built to demonstrate multi-agent orchestration, RAG retrieval, tool use, guardrails, and AI-to-human handoff in a single-page web app. Everything runs locally — no cloud infrastructure required beyond AWS Bedrock API access.

**This is a demo prototype, not production software.** All data is mock, sessions are in-memory, and there is no authentication. It is designed to look and feel polished for a presales walkthrough.

## What It Actually Does

A member selects their identity from a dropdown (no real auth), then chats with an AI agent powered by Claude via AWS Bedrock. The AI classifies intent, routes to a specialist agent, calls mock tools, retrieves policy documents via RAG, and returns a response with full observability. If the conversation escalates, the UI transitions to a human agent desktop with an LLM-generated briefing, sentiment history, knowledge articles, and suggested next steps.

All of this is real — the LLM calls, the tool use decisions, the RAG retrieval, the multi-agent routing, the guardrails, and the agent desktop briefing. The things that are mocked are the data (members, claims, policy docs), the telephony layer (no actual voice), and the analytics (hardcoded baselines).

## Architecture

```
Browser (Vanilla JS, ~2200 lines)
  ↕ HTTP + WebSocket
FastAPI Backend (~880 lines)
  ├── Supervisor Agent (Claude 3.5 Haiku) — classifies intent + sentiment
  ├── Specialist Agents (Claude 3.5 Sonnet) — reasoning + tool use
  │     ├── Eligibility Agent
  │     ├── FNOL Agent (claim filing)
  │     ├── Claims Status Agent
  │     └── General Agent
  ├── Tools (mock APIs returning hardcoded JSON)
  ├── RAG (TF-IDF + cosine similarity over 5 markdown docs, 30 chunks)
  ├── Guardrails (PII regex, topic blocking, hallucination detection, confidence scoring)
  └── Session State (in-memory dict, lost on restart)
```

### How a message flows

1. User sends a message via `POST /api/chat`
2. **Supervisor Agent** (Haiku) classifies intent (`eligibility`, `fnol`, `claim_status`, `general`, `escalate`) and sentiment (`positive`, `neutral`, `concerned`, `frustrated`, `angry`) with a confidence score. This classification is broadcast over WebSocket so the UI shows it before the full response arrives.
3. Message is routed to the appropriate **Specialist Agent** (Sonnet) with full conversation history
4. Specialist runs an **agentic tool loop** — up to 5 iterations where it can call tools, get results, and reason again
5. RAG sources are attached if the agent searched the knowledge base (or as a fallback if it didn't)
6. **Guardrails** run on the response: PII scan, topic blocking, hallucination signal check, confidence scoring
7. Full response returned with metadata: tools called, RAG sources, trace steps, latency breakdown, confidence score

## Quick Start

```bash
cd prototype
cp .env.example .env
# Requires AWS credentials configured (~/.aws/credentials) with Bedrock access
chmod +x start.sh
./start.sh
```

Opens at **http://localhost:8000**. The start script creates a venv, installs dependencies, and runs uvicorn with hot-reload.

Use Chrome for voice features (Web Speech API).

## Features

### Core AI

- **Multi-agent orchestration**: Supervisor (Haiku) classifies and routes; specialist agents (Sonnet) handle domain-specific reasoning with tool use
- **Agentic tool loop**: Claude autonomously decides which tools to call, executes them, reasons on results, and iterates (up to 5 steps)
- **RAG retrieval**: TF-IDF vectorization + cosine similarity over 5 policy documents (30 chunks), with relevance scoring and source attribution
- **Guardrails**: PII redaction (SSN, phone, email, credit card), topic blocking (medical/legal/financial advice), hallucination detection, confidence scoring
- **Escalation**: Triggered by intent classification or angry sentiment — hands off to human agent with full context

### Observability — Under the Hood Panel

Collapsible right panel with 5 tabs that show everything happening behind the scenes:

- **Agent Trace**: Step-by-step timeline (supervisor → routing → specialist → tool calls → RAG → guardrails) with durations, expandable details, confidence badge, and an optional Gantt-style latency waterfall showing proportional timing of each stage
- **Tools & APIs**: Expandable cards for each tool call with full input/output JSON, read/write badges, and timing
- **Knowledge**: RAG source cards with relevance percentage bars, chunk text preview, and "Open Document" button that opens a full document viewer modal with the matched section highlighted
- **Review Queue**: Flagged responses (confidence below threshold) and PII detections, with turn number and reason. Threshold is adjustable via a sidebar slider (30%–95%).
- **Compliance**: Regulatory framework status (NAIC, HIPAA, FCRA, E&O audit trail), data residency details (US/EU), live session flags (HIPAA triggers when injuries mentioned, PII detection events, topic blocking events), and bias & fairness statement

### Agent Desktop (Post-Escalation)

When escalation triggers, the UI transitions to a 4-panel agent desktop — what the human agent sees when they accept the handoff:

- **AI Summary Banner** (top): 3-5 sentence LLM-generated briefing — who the member is, what happened, what's unresolved, emotional state. Dismissible.
- **Screen Pop** (left): Member details, sentiment timeline (colored dots showing emotional arc), AI actions taken with turn numbers, session metadata, and a collapsible **Handoff Context Payload** showing the exact JSON structure that maps to Genesys `transferToAcd` conversation attributes
- **Transcript** (center): Full chat history with avatars, plus text input for simulated agent replies
- **Knowledge** (right): Two tabs — "Retrieved" (docs the AI used) and "Suggested" (proactive RAG search using full conversation context, surfacing docs the AI may have missed). Cards show full chunk text and relevance scores.
- **Agent Assist** (far right): LLM-generated open questions, checkable suggested actions, escalation details (queue, timestamp, reason)

The three LLM calls (summary, guidance, proactive RAG) run concurrently via `asyncio.gather` using Haiku for cost efficiency (~$0.001 per agent desktop load).

### Genesys Cloud CX Integration Mapping

- **Discovery Mode** (press D): Annotated overlay showing how every UI component maps to a Genesys CX capability (Web Messenger, Bot Connector API, Data Actions, Predictive Engagement, Agent Workspace, WEM). Includes business metrics: 73% containment, ~$0.02/interaction, <3s response, 10K/day designed scale.
- **Architecture Modal** (press G): Side-by-side component mapping table (prototype → Genesys), 4 integration point cards (Voice, Digital, WEM, Routing), resilience & failure mode grid (4 scenarios with circuit breakers and fallbacks), cost breakdown (Haiku/Sonnet per-message and daily estimates)
- **Escalation labels**: Banners show ACD queue name (CLM-PRIORITY), skill (claims-specialist), and priority level — matching `transferToAcd` semantics

### Additional Features

- **Sentiment visualization**: Color-coded header indicator + animated ring around chat input (green → yellow → orange → red pulsing) that shifts with detected sentiment
- **Voice simulation**: Microphone button for browser-based speech-to-text (Web Speech API), TTS Preview button on every AI response. Labeled as "Simulated ASR" — no real telephony.
- **Latency simulation**: Toggle in header. When enabled, shows streaming filler phrases ("Let me check that for you...") while the AI reasons, plus ASR/TTS timing badges. The trace panel renders a Gantt-style waterfall with proportional bars for each processing stage.
- **Multi-region toggle**: US/EU selector in header. Switches compliance display to show GDPR data residency details. UI-only — no actual regional deployment.
- **Analytics dashboard**: 6 KPI cards + 8 pure-CSS charts (intent distribution, daily volume, escalation reasons, sentiment breakdown, tool frequency, handle time by intent). Data is hardcoded baselines with live session overlay.
- **Quick actions**: 4 sidebar buttons for common demo scenarios (eligibility check, claim filing, claim status, guardrails demo)

## What's Real vs. What's Mocked

| Component | Status | Notes |
|-----------|--------|-------|
| LLM reasoning | **Real** | Claude 3.5 Haiku + Sonnet via AWS Bedrock |
| Intent classification | **Real** | Haiku classifies every message with structured JSON output |
| Sentiment detection | **Real** | Haiku detects sentiment alongside intent |
| Tool use decisions | **Real** | Claude autonomously decides which tools to call |
| Agentic loop | **Real** | Up to 5 iterations of reason → tool call → reason |
| RAG retrieval | **Real** | TF-IDF + cosine similarity over 5 docs, 30 chunks |
| Guardrails (PII/topic) | **Real** | Regex-based detection, runs on every message |
| Confidence scoring | **Real** | Hallucination signal detection in responses |
| Agent Desktop AI summary | **Real** | Haiku generates briefing from conversation history |
| Suggested actions | **Real** | Haiku generates next steps from conversation context |
| Proactive RAG | **Real** | Fresh retrieval using full conversation as query |
| Member data | **Mock** | 3 hardcoded members in `members.json` |
| Claims data | **Mock** | 2 hardcoded claims in `claims.json` |
| Policy documents | **Mock** | 5 markdown files written for the demo |
| Analytics data | **Mock** | Hardcoded KPIs with live session overlay |
| Authentication | **None** | Dropdown selector, no real auth |
| Session persistence | **None** | In-memory, lost on server restart |
| Voice/telephony | **Simulated** | Browser Web Speech API only — labeled as simulated ASR |
| Multi-region | **Simulated** | UI toggle changes compliance display, no actual regional deployment |
| Human agent replies | **Simulated** | Appended to UI only, not sent to backend |
| Genesys integration | **Mapped** | Architecture and payloads designed, no actual API calls |

## Screens

The app has 4 screens (one visible at a time):

1. **Auth Screen** — member selector with ambient glow background
2. **Chat Screen** — iMessage-style chat + sidebar + Under the Hood panel (5 tabs)
3. **Agent Desktop** — 4-panel layout (screen pop, transcript, knowledge, agent assist) with AI summary banner
4. **Analytics Dashboard** — 6 KPI cards + 8 CSS bar charts

## Demo Walkthrough

### Quick Version

1. **Eligibility**: Select Sarah Chen → "What does my policy cover?" → watch trace panel show supervisor → routing → specialist → tools → RAG → guardrails
2. **FNOL**: "I was in a fender bender" → multi-turn guided claim filing → confirmation number
3. **Claim Status**: Select James Wilson → "What's the status of my claim?" → timeline and adjuster info
4. **Guardrails**: Click Guardrails Demo → topic blocking fires, visible in trace panel
5. **Escalation**: "I want to speak to a human" → banner → View Agent Desktop → AI summary, sentiment timeline, knowledge, suggested actions
6. **Genesys Mapping**: Press D for Discovery Mode overlay, G for Architecture modal

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check (includes RAG chunk count) |
| `GET` | `/api/members` | List the 3 test members |
| `POST` | `/api/session/start` | Create a new session (in-memory) |
| `GET` | `/api/session/{id}` | Get session state |
| `GET` | `/api/session/{id}/audit` | Get audit log entries |
| `POST` | `/api/chat` | Send message, get agent response with full metadata |
| `GET` | `/api/agent-desktop/{id}` | Assemble agent desktop context (triggers 3 parallel LLM calls) |
| `GET` | `/api/docs/{name}` | Fetch raw markdown for a policy document |
| `GET` | `/api/analytics` | Returns mock analytics with live session overlay |
| `GET` | `/api/review-queue/{id}` | Get flagged responses for a session |
| `WS` | `/ws/{id}` | Real-time trace events during LLM processing |

## Project Structure

```
prototype/
├── backend/
│   ├── main.py                    # FastAPI app, all routes, WebSocket, agent desktop endpoint
│   ├── config.py                  # Environment config (models, RAG params, timeouts)
│   ├── models.py                  # Pydantic request/response models
│   ├── agents/
│   │   ├── base.py                # Agentic loop — calls Claude, executes tools, repeats
│   │   ├── supervisor.py          # Intent + sentiment classification (Haiku)
│   │   ├── eligibility.py         # Coverage lookup specialist (Sonnet)
│   │   ├── fnol.py                # Claim filing specialist (Sonnet)
│   │   └── claims.py              # Claim status specialist (Sonnet)
│   ├── tools/
│   │   ├── eligibility_api.py     # Returns hardcoded coverage from members.json
│   │   ├── claims_api.py          # Returns hardcoded claims + FNOL creation
│   │   └── knowledge_base.py      # RAG search wrapper (delegates to retriever)
│   ├── rag/
│   │   ├── indexer.py             # Section-aware markdown chunking (500 words, 100 overlap)
│   │   └── retriever.py           # TF-IDF vectorization + cosine similarity search
│   ├── guardrails/
│   │   └── safety.py              # PII regex, topic blocking, hallucination detection
│   ├── state/
│   │   └── session.py             # In-memory session store + mock member/claims data
│   └── data/
│       ├── members.json           # 3 test members with coverage details
│       ├── claims.json            # 2 test claims with timelines
│       └── docs/                  # 5 policy documents for RAG
│           ├── auto_policy_coverage.md
│           ├── claims_procedures.md
│           ├── deductibles_copays.md
│           ├── eligibility_faq.md
│           └── fnol_guide.md
├── frontend/
│   ├── index.html                 # All 4 screens (~800 lines)
│   ├── app.js                     # All UI logic, state, WebSocket (~2200 lines, no framework)
│   └── styles.css                 # Dark mode, Apple-inspired design (~3500 lines)
├── requirements.txt               # 8 Python dependencies
├── .env.example
└── start.sh                       # Creates venv, installs deps, runs uvicorn with hot-reload
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Python 3.11+ / FastAPI / Uvicorn | Async support, easy to demo, hot-reload |
| LLM | AWS Bedrock (Claude 3.5 Haiku + Sonnet) | Two-tier: Haiku ~$0.001/classification, Sonnet ~$0.02/reasoning |
| RAG | scikit-learn TF-IDF + cosine similarity | No GPU, no vector DB, 30 chunks indexed at startup in ~50ms |
| Frontend | Vanilla HTML / CSS / JS | Zero build step, zero dependencies, single-page |
| Real-time | WebSocket (native) | Live trace events broadcast during LLM processing |
| State | In-memory Python dict | Simple, no database to set up |

## Mock Data

### Members
| Member | Policy | Type | Deductible | Has Claims |
|--------|--------|------|------------|-----------|
| Sarah Chen (M-10042) | POL-2024-78432 | Comprehensive + Collision | $500 | No |
| James Wilson (M-10043) | POL-2024-78433 | Liability Only | $1,000 | CLM-2024-001 (under review) |
| Maria Rodriguez (M-10044) | POL-2024-78434 | Comprehensive + Collision | $250 | CLM-2024-002 (approved) |

### Policy Documents (RAG Source)
| Document | Content | Chunks |
|----------|---------|--------|
| `auto_policy_coverage.md` | Coverage types, limits, exclusions | ~6 |
| `claims_procedures.md` | Filing process, timelines, required docs | ~6 |
| `eligibility_faq.md` | Common coverage questions and answers | ~6 |
| `fnol_guide.md` | First Notice of Loss process, scene documentation | ~6 |
| `deductibles_copays.md` | Cost sharing explanation, examples | ~6 |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock |
| `SUPERVISOR_MODEL_ID` | `us.anthropic.claude-3-5-haiku-20241022-v1:0` | Haiku for classification |
| `SPECIALIST_MODEL_ID` | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | Sonnet for reasoning |
| `MAX_AGENT_STEPS` | `5` | Max tool-use iterations per request |
| `MAX_TOKENS` | `4096` | Max tokens per LLM response |
| `TEMPERATURE` | `0.1` | LLM temperature (low for consistency) |
| `RAG_CHUNK_SIZE` | `500` | Words per RAG chunk |
| `RAG_CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `RAG_TOP_K` | `4` | Number of RAG results to return |
| `SESSION_TIMEOUT_MINUTES` | `30` | Session expiry |

AWS credentials must be configured separately (`~/.aws/credentials` or environment variables) with permissions to invoke Bedrock models in the configured region.

## Known Limitations

- **No persistence** — everything is in-memory. Restart the server and all sessions are gone.
- **No concurrent users** — sessions are stored in a global dict with no locking. Works fine for a single-user demo.
- **No streaming** — responses arrive all at once after the full agent loop completes. The thinking indicator and filler phrases mask the 1-3 second wait, but a production system would stream tokens.
- **RAG is basic** — TF-IDF with cosine similarity works for 5 small docs but wouldn't scale. A production system needs semantic embeddings (e.g., Titan Embeddings) and a vector database (e.g., OpenSearch, pgvector).
- **Guardrails are regex** — PII detection and topic blocking use pattern matching, not ML classifiers. They catch obvious patterns (SSNs, phone numbers) but miss edge cases and obfuscated inputs.
- **Mock tools** — all "API calls" return hardcoded data. `create_fnol` always succeeds. `get_claim_status` only knows about 2 claims. In production, these would be Genesys Data Actions calling real backend systems.
- **No voice** — the voice simulation uses the browser's Web Speech API for basic speech-to-text and text-to-speech. There is no telephony integration, no real ASR engine, and no voice biometrics. The labels explicitly say "Simulated ASR."
- **Analytics are static** — the dashboard shows hardcoded baselines (73% containment, 1,247 conversations) with a thin overlay of live session data. It is not a real analytics engine.
- **Agent replies are client-side only** — when a human agent types in the agent desktop, the message appears in the chat UI but is not sent to the backend or to any real routing system.
- **Single-user demo** — no multi-tenant support, no session isolation, no rate limiting. Designed for one person presenting on one machine.

## What Production Would Require

This prototype demonstrates the architecture and UX. Bridging to production would involve:

| Prototype | Production |
|-----------|------------|
| Mock member data | Genesys Data Actions → CRM/policy admin system |
| In-memory sessions | Genesys conversation state + persistent storage |
| TF-IDF RAG | Bedrock Knowledge Bases with Titan Embeddings + OpenSearch |
| Regex guardrails | Bedrock Guardrails (content filters, denied topics, PII classifiers) |
| No auth | Genesys Web Messenger authentication / IVR ANI lookup |
| No voice | Genesys Voice IVR → AudioHook → ASR → Bot Connector API |
| FastAPI backend | Genesys Bot Connector API + Architect Bot Flow |
| Browser WebSocket | Genesys notification service |
| Mock analytics | Genesys WEM + Performance DNA |

## Cost Estimates

Based on Claude 3.5 pricing via AWS Bedrock:

| Component | Cost | Notes |
|-----------|------|-------|
| Supervisor classification (Haiku) | ~$0.001/message | Runs on every user message |
| Specialist reasoning (Sonnet) | ~$0.02/response | Includes tool use iterations |
| Agent Desktop briefing (Haiku) | ~$0.001/escalation | 3 parallel calls |
| RAG retrieval | ~$0 | In-memory, no API cost |
| **Estimated daily (10K conversations)** | **~$210** | Assumes 3 turns avg, 8% escalation |
