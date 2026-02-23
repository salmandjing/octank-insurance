/* ═══════════════════════════════════════════════════════
   Octank Insurance Virtual Agent — Frontend Application
   With Under the Hood panel, traces, sentiment, and more
   ═══════════════════════════════════════════════════════ */

const API_BASE = '';
let state = {
    sessionId: null,
    memberId: null,
    memberData: null,
    ws: null,
    isProcessing: false,
    hoodOpen: true,
    escalated: false,
    turnCount: 0,
    currentAgent: '—',
    agentDesktopData: null,
    agentTimerInterval: null,
    agentTimerSeconds: 0,
    latencySimEnabled: false,
    regionEU: false,
    fillerInterval: null,
    reviewQueue: [],
    escalationThreshold: 0.7,
    voiceRecognition: null,
};

// ── Initialization ──────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    await loadMembers();
    bindEvents();
});

async function loadMembers() {
    try {
        const res = await fetch(`${API_BASE}/api/members`);
        const data = await res.json();
        const select = document.getElementById('member-select');
        data.members.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.member_id;
            opt.textContent = `${m.name} — ${m.policy_number} (${m.policy_type})`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load members:', e);
    }
}

function bindEvents() {
    const select = document.getElementById('member-select');
    const startBtn = document.getElementById('start-btn');
    const sendBtn = document.getElementById('send-btn');
    const input = document.getElementById('message-input');
    const hoodToggle = document.getElementById('hood-toggle');
    const hoodClose = document.getElementById('hood-close');
    const escalateBtn = document.getElementById('escalate-btn');
    const newChatBtn = document.getElementById('new-chat-btn');

    select.addEventListener('change', () => {
        startBtn.disabled = !select.value;
        updateMemberPreview(select.value);
    });

    startBtn.addEventListener('click', () => startSession(select.value));
    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('input', () => {
        sendBtn.disabled = !input.value.trim() || state.isProcessing;
        autoResizeInput(input);
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (input.value.trim() && !state.isProcessing) sendMessage();
        }
    });

    // Hood panel toggle
    hoodToggle.addEventListener('click', toggleHood);
    hoodClose.addEventListener('click', toggleHood);

    // Hood tabs
    document.querySelectorAll('.hood-tab').forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    escalateBtn.addEventListener('click', () => {
        if (!state.isProcessing && state.sessionId) {
            document.getElementById('message-input').value = 'I want to speak to a human agent';
            sendMessage();
        }
    });

    newChatBtn.addEventListener('click', resetToAuth);

    // Latency simulation toggle
    document.getElementById('latency-toggle').addEventListener('click', toggleLatencySim);

    // Region toggle
    document.getElementById('region-toggle').addEventListener('click', toggleRegion);

    // Analytics button
    document.getElementById('analytics-btn').addEventListener('click', showAnalytics);

    // Architecture modal
    document.getElementById('arch-btn').addEventListener('click', openArchModal);
    document.getElementById('arch-close').addEventListener('click', closeArchModal);
    document.getElementById('arch-overlay').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeArchModal();
    });

    // Discovery mode
    document.getElementById('discovery-btn').addEventListener('click', toggleDiscoveryMode);

    // Keyboard shortcuts: G for architecture, D for discovery
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        const tag = document.activeElement?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (e.key === 'g') openArchModal();
        if (e.key === 'd') toggleDiscoveryMode();
    });

    // Voice mic button
    document.getElementById('voice-mic-btn').addEventListener('click', toggleVoiceInput);

    // Escalation threshold slider
    document.getElementById('threshold-slider').addEventListener('input', (e) => {
        const val = e.target.value;
        document.getElementById('threshold-value').textContent = val + '%';
        state.escalationThreshold = parseInt(val) / 100;
    });

    // Quick action buttons
    document.querySelectorAll('.quick-action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!state.isProcessing && state.sessionId) {
                document.getElementById('message-input').value = btn.dataset.message;
                sendMessage();
            }
        });
    });
}

// ── Hood Panel ──────────────────────────────────────────

function toggleHood() {
    state.hoodOpen = !state.hoodOpen;
    const panel = document.getElementById('hood-panel');
    const toggle = document.getElementById('hood-toggle');

    panel.classList.toggle('open', state.hoodOpen);
    toggle.classList.toggle('active', state.hoodOpen);
}

function switchTab(tabName) {
    document.querySelectorAll('.hood-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.hood-tab-content').forEach(c => c.classList.remove('active'));

    document.querySelector(`.hood-tab[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`tab-${tabName}`).classList.add('active');
}

// ── Session Management ──────────────────────────────────

async function startSession(memberId) {
    try {
        const res = await fetch(`${API_BASE}/api/session/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ member_id: memberId }),
        });

        if (!res.ok) throw new Error('Failed to start session');

        const data = await res.json();
        state.sessionId = data.session_id;
        state.memberId = memberId;
        state.memberData = data.member;
        state.escalated = false;
        state.turnCount = 0;

        // Switch to chat screen
        document.getElementById('auth-screen').classList.remove('active');
        const chatScreen = document.getElementById('chat-screen');
        chatScreen.classList.add('active');
        chatScreen.style.display = 'flex';
        chatScreen.style.flexDirection = 'column';

        updateMemberCard(data.member);
        showWelcomeMessage(data.member);
        connectWebSocket(data.session_id);

        // Open hood panel by default
        state.hoodOpen = true;
        document.getElementById('hood-panel').classList.add('open');
        document.getElementById('hood-toggle').classList.add('active');

        // Update session stats
        document.getElementById('stat-session').textContent = data.session_id.slice(0, 8);
        document.getElementById('stat-turn').textContent = '0';
        document.getElementById('stat-agent').textContent = '—';

        document.getElementById('message-input').focus();
    } catch (e) {
        console.error('Session start failed:', e);
        alert('Failed to start session. Is the backend running?');
    }
}

function resetToAuth() {
    if (state.ws) state.ws.close();
    if (state.agentTimerInterval) clearInterval(state.agentTimerInterval);
    if (state.fillerInterval) clearInterval(state.fillerInterval);
    state = {
        sessionId: null, memberId: null, memberData: null, ws: null,
        isProcessing: false, hoodOpen: true, escalated: false, turnCount: 0, currentAgent: '—',
        agentDesktopData: null, agentTimerInterval: null, agentTimerSeconds: 0,
        latencySimEnabled: state.latencySimEnabled, regionEU: state.regionEU,
        fillerInterval: null, reviewQueue: [],
        escalationThreshold: state.escalationThreshold, voiceRecognition: null,
    };

    document.getElementById('chat-screen').classList.remove('active');
    document.getElementById('chat-screen').style.display = 'none';
    document.getElementById('agent-desktop-screen').classList.remove('active');
    document.getElementById('agent-desktop-screen').style.display = 'none';
    document.getElementById('analytics-screen').classList.remove('active');
    document.getElementById('analytics-screen').style.display = 'none';
    document.getElementById('auth-screen').classList.add('active');
    document.getElementById('messages').innerHTML = '';
    document.getElementById('escalation-banner').classList.add('hidden');
    document.getElementById('member-select').value = '';
    document.getElementById('start-btn').disabled = true;
    document.getElementById('member-preview').classList.add('hidden');

    // Reset hood panel
    clearHoodPanel();
}

function clearHoodPanel() {
    document.getElementById('trace-timeline').innerHTML = '';
    document.getElementById('trace-empty').style.display = 'flex';
    document.getElementById('tools-list').innerHTML = '';
    document.getElementById('tools-empty').style.display = 'flex';
    document.getElementById('knowledge-list').innerHTML = '';
    document.getElementById('knowledge-empty').style.display = 'flex';
    document.getElementById('review-queue-list').innerHTML = '';
    document.getElementById('review-queue-empty').style.display = 'flex';
    document.getElementById('audit-log').innerHTML = '<p class="audit-empty">No entries yet</p>';
    updateSentiment('neutral');

    // Reset compliance tab
    const hipaaItem = document.getElementById('compliance-hipaa');
    if (hipaaItem) {
        hipaaItem.classList.remove('triggered');
        hipaaItem.querySelector('.compliance-dot').className = 'compliance-dot gray';
    }
    const flagsContainer = document.getElementById('compliance-flags');
    if (flagsContainer) {
        flagsContainer.innerHTML = '<div class="compliance-flag-empty">No compliance flags triggered this session</div>';
    }
    // Reset region to current state (don't change region, just re-render)
    updateComplianceRegion();
}

// ── WebSocket ───────────────────────────────────────────

function connectWebSocket(sessionId) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws/${sessionId}`;
    state.ws = new WebSocket(wsUrl);

    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWSMessage(data);
    };

    state.ws.onclose = () => console.log('WebSocket closed');
}

function handleWSMessage(data) {
    switch (data.type) {
        case 'processing_started':
            // Could add a live trace step here
            break;
        case 'intent_classified':
            updateSentiment(data.sentiment || 'neutral');
            // Add supervisor trace step live
            addLiveTraceStep('Supervisor Classification', 'supervisor', data.supervisor_ms || 0, {
                intent: data.intent,
                confidence: `${(data.confidence * 100).toFixed(0)}%`,
                sentiment: data.sentiment || 'neutral',
            });
            addLiveTraceStep(`Route → ${data.intent}`, 'routing', 0, {
                reasoning: data.reasoning,
            });
            break;
        case 'response_ready':
            // Full update handled by chat response
            break;
    }
}

function addLiveTraceStep(name, type, durationMs, details) {
    const timeline = document.getElementById('trace-timeline');
    document.getElementById('trace-empty').style.display = 'none';

    const step = createTraceStepEl(name, type, durationMs, 'success', details);
    timeline.appendChild(step);
    timeline.scrollTop = timeline.scrollHeight;
}

// ── Chat ────────────────────────────────────────────────

async function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    if (!text || state.isProcessing || !state.sessionId) return;

    state.isProcessing = true;
    state.turnCount++;
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('send-btn').disabled = true;

    // Update turn counter
    document.getElementById('stat-turn').textContent = state.turnCount;

    appendMessage('user', text, state.memberData?.name || 'You');
    showThinking();

    // Check for injury/medical keywords → trigger HIPAA compliance flag
    if (/\b(injur|hurt|hospital|doctor|medical|pain|ambulance|emergency room|ER|broken|bleeding)\b/i.test(text)) {
        updateComplianceFlags('hipaa', 'Member disclosed injury/medical information');
    }

    // Clear previous trace for this turn (keep history in tools/knowledge)
    document.getElementById('trace-timeline').innerHTML = '';
    document.getElementById('trace-empty').style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.sessionId, message: text }),
        });

        removeThinking();

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Chat request failed');
        }

        const data = await res.json();

        appendMessage('assistant', data.response, 'Octank Agent', {
            tools: data.tools_called,
            sources: data.rag_sources,
        });

        if (data.escalated) {
            showEscalation(data.escalation_reason, data.handoff_context);
        }

        // Update hood panel with full response data
        updateHoodFromResponse(data);
        updateSentiment(data.sentiment || 'neutral');

        // Handle guardrail blocks — show trace for blocked responses too
        if (data.intent === 'blocked' && data.trace_steps) {
            const timeline = document.getElementById('trace-timeline');
            document.getElementById('trace-empty').style.display = 'none';
            data.trace_steps.forEach(step => {
                const el = createTraceStepEl(step.name, step.step_type, step.duration_ms, step.status, step.details);
                // Add flash animation for blocked guardrails
                if (step.status === 'blocked') {
                    const dot = el.querySelector('.trace-dot');
                    if (dot) dot.classList.add('blocked');
                }
                timeline.appendChild(el);
            });
            // Auto-switch to trace tab to show the guardrail firing
            switchTab('trace');
        }

        // Update session stats
        state.currentAgent = data.agent || '—';
        document.getElementById('stat-agent').textContent = formatAgentName(data.agent);

    } catch (e) {
        removeThinking();
        appendMessage('assistant', 'I apologize, but I encountered an error processing your request. Please try again.', 'Octank Agent');
        console.error('Chat error:', e);
    } finally {
        state.isProcessing = false;
        document.getElementById('send-btn').disabled = !input.value.trim();
        input.focus();
    }
}

// ── Message Rendering ───────────────────────────────────

function appendMessage(role, text, sender, metadata = {}) {
    const container = document.getElementById('messages');

    // Remove welcome message if present
    const welcome = container.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    const msgEl = document.createElement('div');
    msgEl.className = `message ${role}`;

    const avatar = role === 'assistant' ? 'AI' : sender.charAt(0).toUpperCase();
    const formattedText = formatMessageText(text);

    let toolsHtml = '';
    if (metadata.tools && metadata.tools.length > 0) {
        toolsHtml = `<div class="message-tools">${metadata.tools.map(t =>
            `<span class="tool-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                ${t.tool}
            </span>`
        ).join('')}</div>`;
    }

    let sourcesHtml = '';
    if (metadata.sources && metadata.sources.length > 0) {
        const uniqueSources = [...new Set(metadata.sources.map(s => s.source_doc))];
        sourcesHtml = `<div class="message-sources">${uniqueSources.map(s =>
            `<span class="source-badge">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                ${s}
            </span>`
        ).join('')}</div>`;
    }

    // iMessage-style: user right-aligned, assistant/agent left-aligned with avatar
    if (role === 'user') {
        msgEl.innerHTML = `
            <div class="message-body">
                <div class="message-bubble">${formattedText}</div>
            </div>
        `;
    } else if (role === 'agent') {
        msgEl.className = 'message agent';
        msgEl.innerHTML = `
            <div class="message-avatar agent-avatar">AG</div>
            <div class="message-body">
                <div class="message-sender">Human Agent</div>
                <div class="message-bubble agent-bubble">
                    <div class="message-text">${formattedText}</div>
                </div>
            </div>
        `;
    } else {
        msgEl.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-body">
                <div class="message-sender">Octank Agent</div>
                <div class="message-bubble">
                    <div class="message-text">${formattedText}</div>
                    ${toolsHtml}
                    ${sourcesHtml}
                </div>
                <button class="voice-speak-btn" onclick="speakText(this.dataset.text)" data-text="${text.replace(/"/g, '&quot;')}">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
                    TTS Preview
                </button>
            </div>
        `;
    }

    container.appendChild(msgEl);
    scrollToBottom();
}

function formatMessageText(text) {
    // Normalize: LLM sometimes outputs literal <br> tags instead of newlines
    text = text.replace(/<br\s*\/?>/gi, '\n');

    // Split into blocks by double newline
    const blocks = text.split(/\n\n+/);
    const htmlParts = [];

    for (const block of blocks) {
        const trimmed = block.trim();
        if (!trimmed) continue;

        const lines = trimmed.split('\n');

        // Check if this block is a list (all lines start with - or • or digits.)
        const isBulletList = lines.every(l => /^[-•]\s+/.test(l.trim()));
        const isNumberedList = lines.every(l => /^\d+\.\s+/.test(l.trim()));

        if (isBulletList) {
            const items = lines.map(l => `<li>${formatInline(l.trim().replace(/^[-•]\s+/, ''))}</li>`).join('');
            htmlParts.push(`<ul>${items}</ul>`);
        } else if (isNumberedList) {
            const items = lines.map(l => `<li>${formatInline(l.trim().replace(/^\d+\.\s+/, ''))}</li>`).join('');
            htmlParts.push(`<ol>${items}</ol>`);
        } else {
            // Regular paragraph — escape first, THEN insert <br> for single newlines
            htmlParts.push(`<p>${formatInline(trimmed).replace(/\n/g, '<br>')}</p>`);
        }
    }

    return htmlParts.join('');
}

function formatInline(text) {
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    return html;
}

const FILLER_PHRASES = [
    "Let me check that for you...",
    "Pulling up your account details...",
    "Searching our records...",
    "Looking into your policy...",
    "One moment while I verify that...",
    "Checking with our system...",
];

function showThinking() {
    const container = document.getElementById('messages');
    const el = document.createElement('div');
    el.className = 'thinking-indicator';
    el.id = 'thinking';
    el.innerHTML = `
        <div class="message-avatar">AI</div>
        <div>
            <div class="thinking-dots">
                <span></span><span></span><span></span>
            </div>
            <div class="thinking-label" id="thinking-label">Agent is reasoning...</div>
        </div>
    `;
    container.appendChild(el);
    scrollToBottom();

    // Stream filler phrases when latency sim is enabled
    if (state.latencySimEnabled) {
        let phraseIndex = 0;
        const label = el.querySelector('#thinking-label');
        label.className = 'filler-phrase';
        label.textContent = FILLER_PHRASES[0];
        state.fillerInterval = setInterval(() => {
            phraseIndex = (phraseIndex + 1) % FILLER_PHRASES.length;
            label.textContent = FILLER_PHRASES[phraseIndex];
            label.style.animation = 'none';
            label.offsetHeight; // trigger reflow
            label.style.animation = 'fillerFade 0.3s ease';
        }, 2500);
    }
}

function removeThinking() {
    if (state.fillerInterval) {
        clearInterval(state.fillerInterval);
        state.fillerInterval = null;
    }
    const el = document.getElementById('thinking');
    if (el) el.remove();
}

function showWelcomeMessage(member) {
    const container = document.getElementById('messages');
    container.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
            </div>
            <h2>Welcome, ${member.name}!</h2>
            <p>I'm your Octank Insurance virtual agent. I can help you check your coverage, file a claim, check claim status, or schedule a callback. How can I assist you today?</p>
        </div>
    `;
}

function showEscalation(reason, handoffContext) {
    state.escalated = true;
    const banner = document.getElementById('escalation-banner');
    banner.classList.remove('hidden');
    document.getElementById('escalation-detail').textContent =
        'Transferring to human agent — assembling context...';

    // Show handoff context with Genesys routing info
    const metaEl = document.getElementById('escalation-meta');
    if (handoffContext) {
        metaEl.innerHTML = `
            <div style="margin-top: 8px; font-size: 11px; color: var(--text-muted);">
                <span style="color: var(--accent);">ACD Queue:</span> CLM-PRIORITY |
                <span style="color: var(--accent);">Skills:</span> claims-specialist |
                Sentiment: ${handoffContext.sentiment || '—'} |
                AI Actions: ${(handoffContext.actions_taken || []).join(', ') || 'none'}
            </div>
        `;
    }

    // Auto-transition to agent desktop after a brief pause
    // so the user sees the escalation banner before switching
    setTimeout(() => {
        if (state.escalated && state.sessionId) {
            transitionToAgentDesktop();
        }
    }, 2000);
}

// ── Sentiment ───────────────────────────────────────────

function updateSentiment(sentiment) {
    const indicator = document.getElementById('sentiment-indicator');
    const label = document.getElementById('sentiment-label');

    indicator.setAttribute('data-sentiment', sentiment);

    const labels = {
        positive: 'Positive',
        neutral: 'Neutral',
        concerned: 'Concerned',
        frustrated: 'Frustrated',
        angry: 'Angry',
    };

    label.textContent = labels[sentiment] || 'Neutral';

    // Update sentiment ring around input
    const ring = document.getElementById('sentiment-ring');
    if (ring) ring.setAttribute('data-sentiment', sentiment);

    // Update compliance HIPAA flag if injury/medical mentioned
    if (sentiment === 'frustrated' || sentiment === 'angry') {
        updateComplianceFlags('sentiment_escalation', `Sentiment: ${sentiment}`);
    }
}

// ── Hood Panel Updates ──────────────────────────────────

function updateHoodFromResponse(data) {
    // Update trace
    updateTraceFromResponse(data);

    // Update tools
    updateToolsFromResponse(data);

    // Update knowledge
    updateKnowledgeFromResponse(data);

    // Add audit entry
    addAuditEntry(data);

    // Show latency waterfall if sim enabled
    if (state.latencySimEnabled && data.latency_breakdown) {
        renderLatencyWaterfall(data.latency_breakdown, data.latency_ms);
    }

    // Update review queue based on threshold slider
    if (data.confidence < state.escalationThreshold) {
        state.reviewQueue.push({
            turn: state.turnCount,
            confidence: data.confidence,
            intent: data.intent,
            preview: data.response?.slice(0, 150) || '',
            reason: 'low_confidence',
        });
        updateReviewQueue();
    }

    // Handle guardrail flags
    if (data.guardrail_flags && data.guardrail_flags.length > 0) {
        handleGuardrailFlags(data.guardrail_flags);
    }
}

function updateTraceFromResponse(data) {
    const timeline = document.getElementById('trace-timeline');

    // Add specialist trace steps from response
    if (data.trace_steps) {
        data.trace_steps.forEach(step => {
            // Skip supervisor and routing (already added live via WebSocket)
            if (step.step_type === 'supervisor' || step.step_type === 'routing') return;

            const el = createTraceStepEl(step.name, step.step_type, step.duration_ms, step.status, step.details);
            timeline.appendChild(el);
        });
    }

    // Add total time + confidence
    if (data.latency_ms) {
        const existing = timeline.querySelector('.trace-total');
        if (existing) existing.remove();

        const conf = data.confidence !== undefined ? data.confidence : 1.0;
        const confClass = conf >= 0.8 ? 'high' : conf >= 0.5 ? 'medium' : 'low';
        const confPct = (conf * 100).toFixed(0);

        const total = document.createElement('div');
        total.className = 'trace-total';
        total.innerHTML = `
            <span>Total: <span class="total-time">${data.latency_ms}ms</span></span>
            <span class="confidence-badge ${confClass}">Conf: ${confPct}%</span>
        `;
        timeline.appendChild(total);
    }
}

function createTraceStepEl(name, type, durationMs, status, details) {
    const step = document.createElement('div');
    step.className = 'trace-step';

    const icon = getTraceIcon(type);
    const durationHtml = durationMs > 0 ? `<span class="trace-duration">${durationMs}ms</span>` : '';

    let detailHtml = '';
    if (details) {
        const detailParts = [];
        for (const [key, value] of Object.entries(details)) {
            if (key === 'access') {
                detailParts.push(`<span class="trace-badge ${value}">${value}</span>`);
            } else if (typeof value === 'object') {
                detailParts.push(`${key}: ${JSON.stringify(value).slice(0, 60)}`);
            } else {
                detailParts.push(`${key}: ${String(value).slice(0, 80)}`);
            }
        }
        detailHtml = `<div class="trace-detail">${detailParts.join(' · ')}</div>`;
    }

    step.innerHTML = `
        <div class="trace-dot ${type}">${icon}</div>
        <div class="trace-info">
            <div class="trace-name">${name} ${durationHtml}</div>
            ${detailHtml}
        </div>
    `;

    return step;
}

function getTraceIcon(type) {
    const icons = {
        supervisor: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6"/></svg>',
        routing: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>',
        specialist: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10"/><path d="M12 12l7-7"/></svg>',
        tool_call: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>',
        rag_search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
        guardrail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
        escalation: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    };
    return icons[type] || icons.specialist;
}

function updateToolsFromResponse(data) {
    if (!data.tools_called || data.tools_called.length === 0) return;

    const list = document.getElementById('tools-list');
    document.getElementById('tools-empty').style.display = 'none';

    data.tools_called.forEach(tool => {
        const isRead = ['get_eligibility', 'get_claim_status', 'search_knowledge_base'].includes(tool.tool);
        const badgeClass = isRead ? 'read' : 'write';
        const badgeText = isRead ? 'Read' : 'Write';

        const card = document.createElement('div');
        card.className = 'tool-card';

        card.innerHTML = `
            <div class="tool-card-header">
                <span class="tool-card-name">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                    ${tool.tool}
                </span>
                <div class="tool-card-meta">
                    <span class="tool-card-badge ${badgeClass}">${badgeText}</span>
                    ${tool.duration_ms ? `<span class="tool-card-time">${tool.duration_ms}ms</span>` : ''}
                    <svg class="tool-card-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
            </div>
            <div class="tool-card-body">
                <div class="tool-card-section">
                    <div class="tool-card-section-title">Input</div>
                    <div class="tool-card-json">${JSON.stringify(tool.input, null, 2)}</div>
                </div>
                <div class="tool-card-section">
                    <div class="tool-card-section-title">Output</div>
                    <div class="tool-card-json">${JSON.stringify(tool.output, null, 2)}</div>
                </div>
            </div>
        `;

        // Toggle expand on header click
        card.querySelector('.tool-card-header').addEventListener('click', () => {
            card.classList.toggle('expanded');
        });

        list.appendChild(card);
    });
}

function updateKnowledgeFromResponse(data) {
    if (!data.rag_sources || data.rag_sources.length === 0) return;

    const list = document.getElementById('knowledge-list');
    document.getElementById('knowledge-empty').style.display = 'none';

    data.rag_sources.forEach(source => {
        const score = source.relevance_score;
        const scorePercent = (score * 100).toFixed(0);
        const scoreColor = score >= 0.5 ? 'var(--success)' : score >= 0.3 ? 'var(--warning)' : 'var(--text-muted)';

        const card = document.createElement('div');
        card.className = 'rag-card';

        card.innerHTML = `
            <div class="rag-card-header">
                <span class="rag-card-doc">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    ${escapeHtml(source.source_doc)}
                </span>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="rag-card-score" style="color: ${scoreColor}">${scorePercent}%</span>
                    <svg class="rag-card-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
            </div>
            <div class="rag-score-bar">
                <div class="rag-score-fill" style="width: ${scorePercent}%; background: ${scoreColor}"></div>
            </div>
            <div class="rag-card-body">
                ${source.heading ? `<div class="rag-card-heading">${escapeHtml(source.heading)}</div>` : ''}
                <div class="rag-card-full-text">${escapeHtml(source.chunk_text || '')}</div>
                <button class="rag-card-open-doc" data-doc="${escapeHtml(source.source_doc)}" data-chunk="${escapeHtml((source.chunk_text || '').slice(0, 80))}">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    Open Document
                </button>
            </div>
        `;

        card.querySelector('.rag-card-header').addEventListener('click', () => {
            card.classList.toggle('expanded');
        });

        card.querySelector('.rag-card-open-doc').addEventListener('click', (e) => {
            e.stopPropagation();
            openDocViewer(source.source_doc, source.chunk_text);
        });

        list.appendChild(card);
    });
}

function addAuditEntry(data) {
    const auditLog = document.getElementById('audit-log');
    const emptyMsg = auditLog.querySelector('.audit-empty');
    if (emptyMsg) emptyMsg.remove();

    const entry = document.createElement('div');
    entry.className = 'audit-entry';

    const now = new Date().toLocaleTimeString();
    const tools = (data.tools_called || []).map(t => t.tool).join(', ');

    entry.innerHTML = `
        <div class="audit-entry-header">
            <span class="audit-entry-turn">Turn ${state.turnCount}</span>
            <span class="audit-entry-time">${now} · ${data.latency_ms}ms</span>
        </div>
        <div class="audit-entry-body">
            <span class="audit-tag" style="background: var(--accent-soft); color: var(--accent);">${data.intent || '—'}</span>
            <span class="audit-tag">${formatAgentName(data.agent)}</span>
            ${data.sentiment && data.sentiment !== 'neutral' ? `<span class="audit-tag" style="background: var(--warning-soft); color: var(--warning);">${data.sentiment}</span>` : ''}
            ${tools ? `<span class="audit-tag" style="background: var(--warning-soft); color: var(--warning);">${tools}</span>` : ''}
        </div>
    `;

    auditLog.insertBefore(entry, auditLog.firstChild);
}

// ── Member Display ──────────────────────────────────────

function updateMemberPreview(memberId) {
    const preview = document.getElementById('member-preview');
    if (!memberId) {
        preview.classList.add('hidden');
        return;
    }
    const select = document.getElementById('member-select');
    const text = select.options[select.selectedIndex].textContent;
    preview.innerHTML = `<span class="mp-detail">${text}</span>`;
    preview.classList.remove('hidden');
}

function updateMemberCard(member) {
    const card = document.getElementById('member-info');
    const coverage = member.coverage || {};
    card.innerHTML = `
        <div class="mc-name">${member.name}</div>
        <div class="mc-row"><span>Member ID</span><span>${member.member_id}</span></div>
        <div class="mc-row"><span>Policy</span><span>${member.policy_number}</span></div>
        <div class="mc-row"><span>Type</span><span>${(member.policy_type || '').toUpperCase()}</span></div>
        <div class="mc-row"><span>Coverage</span><span>${coverage.type || 'N/A'}</span></div>
        <div class="mc-row"><span>Deductible</span><span>$${coverage.deductible || 'N/A'}</span></div>
        <span class="mc-badge">Active</span>
    `;
}

// ── Utilities ───────────────────────────────────────────

function scrollToBottom() {
    const container = document.getElementById('messages-container');
    requestAnimationFrame(() => {
        container.scrollTop = container.scrollHeight;
    });
}

function autoResizeInput(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function formatAgentName(name) {
    if (!name) return '—';
    return name
        .replace(/_/g, ' ')
        .replace(/agent/i, '')
        .trim()
        .replace(/^\w/, c => c.toUpperCase()) || name;
}


// ═══════════════════════════════════════════════════════
// AGENT DESKTOP
// ═══════════════════════════════════════════════════════

function bindAgentDesktopEvents() {
    // View Agent Desktop button (in escalation banner)
    document.getElementById('view-agent-desktop-btn')?.addEventListener('click', transitionToAgentDesktop);

    // Back to Demo button
    document.getElementById('back-to-demo-btn')?.addEventListener('click', backToChat);

    // New button in agent desktop
    document.getElementById('agent-new-btn')?.addEventListener('click', resetToAuth);

    // Accept button
    document.getElementById('agent-accept-btn')?.addEventListener('click', () => {
        const btn = document.getElementById('agent-accept-btn');
        btn.classList.add('accepted');
        btn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
            Accepted
        `;
    });

    // AI Summary dismiss
    document.getElementById('ai-summary-dismiss')?.addEventListener('click', () => {
        document.getElementById('ai-summary-banner').classList.add('dismissed');
    });

    // Knowledge tabs in agent desktop
    document.querySelectorAll('.knowledge-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const ktab = tab.dataset.ktab;
            if (!ktab) return;
            document.querySelectorAll('.knowledge-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.knowledge-tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`ktab-${ktab}`).classList.add('active');
        });
    });

    // Agent reply (simulated)
    document.getElementById('agent-reply-btn')?.addEventListener('click', () => {
        const input = document.getElementById('agent-reply-input');
        const text = input.value.trim();
        if (!text) return;

        // Add to agent desktop transcript
        const container = document.getElementById('transcript-messages');
        const msg = document.createElement('div');
        msg.className = 'transcript-msg assistant';
        msg.innerHTML = `
            <div class="tm-avatar">AG</div>
            <div class="tm-body">
                <div class="tm-sender">Agent (You)</div>
                <div class="tm-text">${escapeHtml(text)}</div>
            </div>
        `;
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
        input.value = '';

        // Also add to main chat so it persists when switching back
        appendMessage('agent', text, 'Human Agent');
    });
}

// Initialize agent desktop events after DOM ready
document.addEventListener('DOMContentLoaded', () => {
    bindAgentDesktopEvents();
    // Analytics back button
    document.getElementById('analytics-back-btn')?.addEventListener('click', backFromAnalytics);
});

async function transitionToAgentDesktop() {
    if (!state.sessionId) return;

    // Fetch agent desktop context
    try {
        const res = await fetch(`${API_BASE}/api/agent-desktop/${state.sessionId}`);
        if (!res.ok) throw new Error('Failed to load agent desktop');

        state.agentDesktopData = await res.json();

        // Switch screens
        document.getElementById('chat-screen').classList.remove('active');
        document.getElementById('chat-screen').style.display = 'none';

        const desktop = document.getElementById('agent-desktop-screen');
        desktop.classList.add('active');
        desktop.style.display = 'flex';
        desktop.style.flexDirection = 'column';

        // Render all panels
        renderAgentDesktop(state.agentDesktopData);

        // Start handle timer
        startHandleTimer();

    } catch (e) {
        console.error('Agent desktop load failed:', e);
        alert('Failed to load agent desktop. Please try again.');
    }
}

function backToChat() {
    if (state.agentTimerInterval) clearInterval(state.agentTimerInterval);

    document.getElementById('agent-desktop-screen').classList.remove('active');
    document.getElementById('agent-desktop-screen').style.display = 'none';

    const chatScreen = document.getElementById('chat-screen');
    chatScreen.classList.add('active');
    chatScreen.style.display = 'flex';
    chatScreen.style.flexDirection = 'column';
}

function startHandleTimer() {
    state.agentTimerSeconds = 0;
    if (state.agentTimerInterval) clearInterval(state.agentTimerInterval);

    const timerEl = document.getElementById('agent-handle-timer');
    state.agentTimerInterval = setInterval(() => {
        state.agentTimerSeconds++;
        const mins = Math.floor(state.agentTimerSeconds / 60).toString().padStart(2, '0');
        const secs = (state.agentTimerSeconds % 60).toString().padStart(2, '0');
        timerEl.textContent = `${mins}:${secs}`;
    }, 1000);
}

function renderAgentDesktop(data) {
    renderAISummary(data);
    renderScreenPop(data);
    renderSentimentTimeline(data);
    renderActionsTaken(data);
    renderSessionInfo(data);
    renderTranscript(data);
    renderKnowledgeRetrieved(data);
    renderKnowledgeProactive(data);
    renderOpenQuestions(data);
    renderSuggestedActions(data);
    renderEscalationDetails(data);

    // Update turn badge
    document.getElementById('transcript-turn-badge').textContent = `${data.session_meta?.turn_count || 0} turns`;

    // Reset accept button
    const btn = document.getElementById('agent-accept-btn');
    btn.classList.remove('accepted');
    btn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        Accept
    `;

    // Reset summary banner
    document.getElementById('ai-summary-banner').classList.remove('dismissed');
}

function renderAISummary(data) {
    document.getElementById('ai-summary-text').textContent = data.ai_summary || 'No summary available.';
}

function renderScreenPop(data) {
    const member = data.member || {};
    const coverage = member.coverage || {};
    const container = document.getElementById('screen-pop-member');

    container.innerHTML = `
        <div class="sp-name">${member.name || 'Unknown'}</div>
        <div class="sp-row"><span>Member ID</span><span>${member.member_id || '—'}</span></div>
        <div class="sp-row"><span>Policy</span><span>${member.policy_number || '—'}</span></div>
        <div class="sp-row"><span>Type</span><span>${(member.policy_type || '').toUpperCase()}</span></div>
        <div class="sp-row"><span>Coverage</span><span>${coverage.type || 'N/A'}</span></div>
        <div class="sp-row"><span>Deductible</span><span>$${coverage.deductible || 'N/A'}</span></div>
        <div class="sp-row"><span>Phone</span><span>${member.phone || 'N/A'}</span></div>
        <div class="sp-row"><span>Email</span><span>${member.email || 'N/A'}</span></div>
        <span class="sp-policy-badge">${(member.policy_type || 'auto').toUpperCase()} POLICY</span>
    `;
}

function renderSentimentTimeline(data) {
    const container = document.getElementById('sentiment-timeline');
    const history = data.sentiment_history || [];

    if (history.length === 0) {
        container.innerHTML = '<span style="color: var(--text-muted); font-size: 11px;">No data yet</span>';
        return;
    }

    container.innerHTML = history.map((s, i) => {
        const parts = [];
        parts.push(`<span class="st-dot" data-sentiment="${s}" title="Turn ${i + 1}: ${s}"></span>`);
        if (i < history.length - 1) {
            parts.push(`<span class="st-arrow">→</span>`);
        }
        return parts.join('');
    }).join('');
}

function renderActionsTaken(data) {
    const container = document.getElementById('actions-taken-list');
    const actions = data.actions_taken || [];

    if (actions.length === 0) {
        container.innerHTML = '<span style="color: var(--text-muted); font-size: 11px;">No actions taken</span>';
        return;
    }

    container.innerHTML = actions.map(a =>
        `<div class="action-item">
            <span class="action-dot"></span>
            <span>${escapeHtml(a.description)} <span style="color: var(--text-muted); font-size: 10px;">(turn ${a.turn})</span></span>
        </div>`
    ).join('');
}

function renderSessionInfo(data) {
    const meta = data.session_meta || {};
    const container = document.getElementById('agent-session-info');

    const createdAt = meta.created_at ? new Date(meta.created_at * 1000).toLocaleTimeString() : '—';

    container.innerHTML = `
        <div class="asi-row"><span>Session</span><span>${data.session_id?.slice(0, 12) || '—'}</span></div>
        <div class="asi-row"><span>Started</span><span>${createdAt}</span></div>
        <div class="asi-row"><span>Turns</span><span>${meta.turn_count || 0}</span></div>
        <div class="asi-row"><span>Intent</span><span>${meta.current_intent || '—'}</span></div>
        <div class="asi-row"><span>Agent</span><span>${formatAgentName(meta.current_agent)}</span></div>
        <div class="asi-row"><span>Tools Used</span><span>${meta.tools_used_count || 0}</span></div>
        <div class="asi-row"><span>Assembly</span><span>${meta.assembly_ms || 0}ms</span></div>
    `;

    // Render context payload JSON
    renderContextPayload(data);
}

function renderContextPayload(data) {
    const toggle = document.getElementById('context-payload-toggle');
    const body = document.getElementById('context-payload-body');
    const jsonEl = document.getElementById('context-payload-json');

    if (!toggle || !jsonEl) return;

    // Build the exact JSON that would be sent as Genesys conversation attributes
    const payload = {
        "genesys.conversationAttributes": {
            "AI.Summary": (data.ai_summary || '').slice(0, 500),
            "AI.Intent": data.session_meta?.current_intent || 'unknown',
            "AI.Sentiment": data.current_sentiment || 'neutral',
            "AI.SentimentHistory": (data.sentiment_history || []).join(','),
            "AI.TurnCount": String(data.session_meta?.turn_count || 0),
            "AI.ToolsUsed": (data.actions_taken || []).map(a => a.tool).join(','),
            "AI.Escalated": String(!!data.escalation?.escalated),
            "AI.EscalationReason": data.escalation?.reason || '',
            "AI.MemberID": data.member?.member_id || '',
            "AI.PolicyNumber": data.member?.policy_number || '',
            "AI.PolicyType": data.member?.policy_type || '',
        },
        "routing": {
            "queueName": "CLM-PRIORITY",
            "skills": ["claims-specialist"],
            "priority": data.current_sentiment === 'angry' ? 1 : data.current_sentiment === 'frustrated' ? 2 : 5,
            "languageSkill": "en-US",
        },
        "screenPop": {
            "memberLookupKey": data.member?.member_id || '',
            "sessionId": data.session_id || '',
            "transcriptUrl": `/api/session/${data.session_id || ''}/transcript`,
        }
    };

    jsonEl.textContent = JSON.stringify(payload, null, 2);

    // Toggle handler
    toggle.onclick = () => {
        body.classList.toggle('hidden');
        toggle.classList.toggle('expanded');
    };
}

function renderTranscript(data) {
    const container = document.getElementById('transcript-messages');
    const messages = data.conversation || [];

    container.innerHTML = messages.map(m => {
        const isUser = m.role === 'user';
        const avatar = isUser ? (data.member?.name?.charAt(0) || 'U') : 'AI';
        const sender = isUser ? (data.member?.name || 'Member') : 'AI Agent';
        const cls = isUser ? 'user' : 'assistant';

        return `<div class="transcript-msg ${cls}">
            <div class="tm-avatar">${avatar}</div>
            <div class="tm-body">
                <div class="tm-sender">${sender}</div>
                <div class="tm-text">${escapeHtml(m.content)}</div>
            </div>
        </div>`;
    }).join('');

    container.scrollTop = container.scrollHeight;
}

function renderKnowledgeRetrieved(data) {
    const container = document.getElementById('knowledge-retrieved-cards');
    const items = data.knowledge_retrieved || [];

    if (items.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted); font-size: 12px; padding: 16px; text-align: center;">No documents retrieved during chat</p>';
        return;
    }

    container.innerHTML = '';
    items.forEach(item => {
        const score = item.relevance_score || 0;
        const scorePercent = (score * 100).toFixed(0);
        const scoreClass = score >= 0.5 ? 'high' : score >= 0.3 ? 'medium' : 'low';
        const scoreColor = score >= 0.5 ? 'var(--success)' : score >= 0.3 ? 'var(--warning)' : 'var(--text-muted)';

        const card = document.createElement('div');
        card.className = 'kcard';
        card.innerHTML = `
            <div class="kcard-header">
                <span class="kcard-doc">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    ${escapeHtml(item.source_doc)}
                </span>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="kcard-score ${scoreClass}">${scorePercent}%</span>
                    <svg class="kcard-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
            </div>
            <div class="kcard-relevance">
                <div class="kcard-relevance-fill" style="width: ${scorePercent}%; background: ${scoreColor}"></div>
            </div>
            <div class="kcard-body">
                ${item.heading ? `<div class="kcard-heading">${escapeHtml(item.heading)}</div>` : ''}
                <div class="kcard-text">${escapeHtml(item.chunk_text || '')}</div>
                <div style="margin-top: 8px; display: flex; align-items: center; justify-content: space-between;">
                    <span style="font-size: 10px; color: var(--text-muted);">Turn ${item.turn || '?'} · ${item.intent || ''}</span>
                    <button class="rag-card-open-doc" data-doc="${escapeHtml(item.source_doc)}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                        Open Document
                    </button>
                </div>
            </div>
        `;

        card.querySelector('.kcard-header').addEventListener('click', () => {
            card.classList.toggle('expanded');
        });

        card.querySelector('.rag-card-open-doc').addEventListener('click', (e) => {
            e.stopPropagation();
            openDocViewer(item.source_doc, item.chunk_text);
        });

        container.appendChild(card);
    });
}

function renderKnowledgeProactive(data) {
    const container = document.getElementById('knowledge-proactive-cards');
    const items = data.knowledge_proactive || [];

    if (items.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted); font-size: 12px; padding: 16px; text-align: center;">No suggested documents</p>';
        return;
    }

    container.innerHTML = '';
    items.forEach(item => {
        const score = item.relevance_score || 0;
        const scorePercent = (score * 100).toFixed(0);
        const scoreClass = score >= 0.5 ? 'high' : score >= 0.3 ? 'medium' : 'low';
        const scoreColor = score >= 0.5 ? 'var(--success)' : score >= 0.3 ? 'var(--warning)' : 'var(--text-muted)';

        const card = document.createElement('div');
        card.className = 'kcard';
        card.innerHTML = `
            <div class="kcard-header">
                <span class="kcard-doc">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    ${escapeHtml(item.source_doc)}
                </span>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="kcard-score ${scoreClass}">${scorePercent}%</span>
                    <svg class="kcard-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
            </div>
            <div class="kcard-relevance">
                <div class="kcard-relevance-fill" style="width: ${scorePercent}%; background: ${scoreColor}"></div>
            </div>
            <div class="kcard-body">
                ${item.heading ? `<div class="kcard-heading">${escapeHtml(item.heading)}</div>` : ''}
                <div class="kcard-text">${escapeHtml(item.chunk_text || '')}</div>
                <div style="margin-top: 8px; text-align: right;">
                    <button class="rag-card-open-doc" data-doc="${escapeHtml(item.source_doc)}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                        Open Document
                    </button>
                </div>
            </div>
        `;

        card.querySelector('.kcard-header').addEventListener('click', () => {
            card.classList.toggle('expanded');
        });

        card.querySelector('.rag-card-open-doc').addEventListener('click', (e) => {
            e.stopPropagation();
            openDocViewer(item.source_doc, item.chunk_text);
        });

        container.appendChild(card);
    });
}

function renderOpenQuestions(data) {
    const container = document.getElementById('open-questions-list');
    const questions = data.open_questions || [];

    if (questions.length === 0) {
        container.innerHTML = '<li class="oq-item" style="border-left-color: var(--text-muted);">No open questions identified</li>';
        return;
    }

    container.innerHTML = questions.map(q =>
        `<li class="oq-item">${escapeHtml(q)}</li>`
    ).join('');
}

function renderSuggestedActions(data) {
    const container = document.getElementById('suggested-actions-list');
    const actions = data.suggested_actions || [];

    if (actions.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 12px;">No suggestions available</div>';
        return;
    }

    container.innerHTML = actions.map((a, i) =>
        `<div class="sa-item" data-index="${i}" onclick="this.classList.toggle('checked')">
            <span class="sa-checkbox"></span>
            <span>${escapeHtml(a)}</span>
        </div>`
    ).join('');
}

function renderEscalationDetails(data) {
    const container = document.getElementById('escalation-details');
    const esc = data.escalation || {};

    if (!esc.escalated) {
        container.innerHTML = '<div style="color: var(--text-muted); font-size: 12px;">Not escalated</div>';
        return;
    }

    const ts = esc.timestamp ? new Date(esc.timestamp).toLocaleTimeString() : '—';

    container.innerHTML = `
        <div class="ed-row"><span>Status</span><span style="color: var(--danger);">Escalated</span></div>
        <div class="ed-row"><span>Turn</span><span>${esc.turn || '—'}</span></div>
        <div class="ed-row"><span>Timestamp</span><span>${ts}</span></div>
        <div class="ed-row"><span>Current Sentiment</span><span>${data.current_sentiment || 'neutral'}</span></div>
        ${esc.reason ? `<div class="ed-reason">${escapeHtml(esc.reason)}</div>` : ''}
    `;
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}


// ═══════════════════════════════════════════════════════
// LATENCY SIMULATION
// ═══════════════════════════════════════════════════════

function toggleLatencySim() {
    state.latencySimEnabled = !state.latencySimEnabled;
    const btn = document.getElementById('latency-toggle');
    btn.classList.toggle('active', state.latencySimEnabled);
}

function renderLatencyWaterfall(breakdown, totalMs) {
    const timeline = document.getElementById('trace-timeline');

    // Remove existing waterfall
    const existing = timeline.querySelector('.latency-waterfall');
    if (existing) existing.remove();

    const simASR = state.latencySimEnabled ? 380 : 0;
    const simTTS = state.latencySimEnabled ? 290 : 0;
    const fullTotal = totalMs + simASR + simTTS;
    const maxMs = fullTotal || 1;

    // Build sequential bars with offset (Gantt-style)
    const bars = [];
    let offset = 0;
    if (state.latencySimEnabled) {
        bars.push({ label: 'ASR', ms: simASR, cls: 'asr', sim: true, offset });
        offset += simASR;
    }
    const classMs = breakdown.classification_ms || 0;
    bars.push({ label: 'Classify', ms: classMs, cls: 'classification', offset });
    offset += classMs;
    const toolsMs = breakdown.tools_ms || 0;
    bars.push({ label: 'Tools', ms: toolsMs, cls: 'tools', offset });
    offset += toolsMs;
    const genMs = breakdown.generation_ms || 0;
    bars.push({ label: 'Generate', ms: genMs, cls: 'generation', offset });
    offset += genMs;
    const guardMs = breakdown.guardrails_ms || 0;
    bars.push({ label: 'Guardrails', ms: guardMs, cls: 'guardrails', offset });
    offset += guardMs;
    if (state.latencySimEnabled) {
        bars.push({ label: 'TTS', ms: simTTS, cls: 'tts', sim: true, offset });
    }

    const warnClass = fullTotal > 3000 ? 'danger' : fullTotal > 2000 ? 'warn' : 'ok';

    const el = document.createElement('div');
    el.className = 'latency-waterfall';
    el.innerHTML = `
        <div class="waterfall-title">Latency Waterfall</div>
        ${bars.map(b => {
            const widthPct = (b.ms / maxMs) * 100;
            const leftPct = (b.offset / maxMs) * 100;
            const narrow = widthPct < 8 ? 'narrow-bar' : '';
            return `
            <div class="waterfall-bar">
                <span class="waterfall-label">${b.label}${b.sim ? ' <span class="sim-badge">SIM</span>' : ''}</span>
                <div class="waterfall-track">
                    <div class="waterfall-fill ${b.cls} ${narrow}" style="left: ${leftPct}%; width: ${Math.max(widthPct, 1)}%">${b.ms}ms</div>
                </div>
            </div>`;
        }).join('')}
        <div class="waterfall-total">
            <span>End-to-End${state.latencySimEnabled ? ' (with ASR/TTS)' : ''}</span>
            <span class="total-value ${warnClass}">${fullTotal}ms${fullTotal > 2000 ? ' ⚠' : ''}</span>
        </div>
    `;

    timeline.appendChild(el);
}


// ═══════════════════════════════════════════════════════
// REGION TOGGLE
// ═══════════════════════════════════════════════════════

function toggleRegion() {
    state.regionEU = !state.regionEU;
    const toggle = document.getElementById('region-toggle');
    const flag = document.getElementById('region-flag');
    const label = document.getElementById('region-label');

    toggle.classList.toggle('eu', state.regionEU);
    flag.textContent = state.regionEU ? 'EU' : 'US';
    label.textContent = state.regionEU ? 'eu-west-1' : 'us-east-1';

    // Show/hide GDPR notice in audit
    updateRegionNotice();

    // Update compliance tab
    updateComplianceRegion();
}

function updateRegionNotice() {
    const existing = document.querySelector('.gdpr-notice');
    if (existing) existing.remove();

    if (state.regionEU) {
        const auditLog = document.getElementById('audit-log');
        const notice = document.createElement('div');
        notice.className = 'gdpr-notice';
        notice.innerHTML = `
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            GDPR compliant · Data residency: eu-west-1 · 90-day retention
        `;
        auditLog.parentNode.insertBefore(notice, auditLog);
    }
}


// ═══════════════════════════════════════════════════════
// GUARDRAIL VISUALS
// ═══════════════════════════════════════════════════════

function handleGuardrailFlags(flags) {
    flags.forEach(flag => {
        if (flag.type === 'topic_blocked') {
            // Flash the guardrails status in session tab
            const guardItems = document.querySelectorAll('.guardrail-item');
            guardItems.forEach(item => {
                item.style.animation = 'guardrailFlash 0.6s ease';
                setTimeout(() => item.style.animation = '', 600);
            });
            // Add compliance flag
            const topic = flag.topic || 'unknown';
            updateComplianceFlags('topic_blocked', `Blocked: ${topic.replace(/_/g, ' ')}`);
            if (topic === 'medical_advice') {
                updateComplianceFlags('hipaa', 'Medical/injury topic detected — HIPAA handling engaged');
            }
        }
        if (flag.type === 'pii_detected') {
            // Add PII warning to review queue
            state.reviewQueue.push({
                turn: state.turnCount,
                confidence: 1.0,
                intent: 'pii_detected',
                preview: `PII detected: ${flag.details.map(d => d.type).join(', ')}`,
                reason: 'pii_in_input',
            });
            updateReviewQueue();
            // Add compliance flag
            updateComplianceFlags('pii', `PII types: ${flag.details.map(d => d.type).join(', ')}`);
        }
    });
}


// ═══════════════════════════════════════════════════════
// REVIEW QUEUE
// ═══════════════════════════════════════════════════════

function updateReviewQueue() {
    const list = document.getElementById('review-queue-list');
    const empty = document.getElementById('review-queue-empty');

    if (state.reviewQueue.length === 0) {
        empty.style.display = 'flex';
        list.innerHTML = '';
        return;
    }

    empty.style.display = 'none';
    list.innerHTML = state.reviewQueue.map(item => `
        <div class="review-item">
            <div class="review-item-header">
                <span class="review-item-turn">Turn ${item.turn} · ${item.intent}</span>
                <span class="review-item-confidence">${item.reason === 'pii_in_input' ? 'PII' : (item.confidence * 100).toFixed(0) + '%'}</span>
            </div>
            <div class="review-item-preview">${escapeHtml(item.preview)}</div>
            <div class="review-item-reason">${item.reason === 'pii_in_input' ? 'PII detected in member input — redacted in logs' : 'Low confidence — flagged for human audit'}</div>
        </div>
    `).join('');
}


// ═══════════════════════════════════════════════════════
// ANALYTICS DASHBOARD
// ═══════════════════════════════════════════════════════

async function showAnalytics() {
    try {
        const res = await fetch(`${API_BASE}/api/analytics`);
        if (!res.ok) throw new Error('Failed to load analytics');
        const data = await res.json();

        // Hide other screens
        document.getElementById('chat-screen').classList.remove('active');
        document.getElementById('chat-screen').style.display = 'none';
        document.getElementById('agent-desktop-screen').classList.remove('active');
        document.getElementById('agent-desktop-screen').style.display = 'none';

        const screen = document.getElementById('analytics-screen');
        screen.classList.add('active');
        screen.style.display = 'flex';
        screen.style.flexDirection = 'column';

        renderAnalytics(data);
    } catch (e) {
        console.error('Analytics load failed:', e);
    }
}

function renderAnalytics(data) {
    // KPI cards
    const kpiRow = document.getElementById('kpi-row');
    kpiRow.innerHTML = `
        <div class="kpi-card accent">
            <div class="kpi-label">Total Conversations</div>
            <div class="kpi-value">${data.total_conversations.toLocaleString()}</div>
            <div class="kpi-sub">Last 30 days</div>
        </div>
        <div class="kpi-card success">
            <div class="kpi-label">Containment Rate</div>
            <div class="kpi-value">${data.containment_rate}%</div>
            <div class="kpi-sub">Resolved without escalation</div>
        </div>
        <div class="kpi-card cyan">
            <div class="kpi-label">Avg Handle Time</div>
            <div class="kpi-value">${Math.floor(data.avg_handle_time_seconds / 60)}m ${data.avg_handle_time_seconds % 60}s</div>
            <div class="kpi-sub">All intents combined</div>
        </div>
        <div class="kpi-card purple">
            <div class="kpi-label">CSAT Score</div>
            <div class="kpi-value">${data.csat_score}</div>
            <div class="kpi-sub">Out of 5.0</div>
        </div>
        <div class="kpi-card warning">
            <div class="kpi-label">Escalation Rate</div>
            <div class="kpi-value">${data.escalation_rate}%</div>
            <div class="kpi-sub">${data.escalation_reasons.reduce((s, r) => s + r.count, 0)} escalations</div>
        </div>
        <div class="kpi-card success">
            <div class="kpi-label">First Contact Resolution</div>
            <div class="kpi-value">${data.first_contact_resolution}%</div>
            <div class="kpi-sub">Single-session resolution</div>
        </div>
    `;

    // Intent distribution (vertical bar chart)
    const intentColors = {
        eligibility: 'var(--accent)',
        fnol: 'var(--orange)',
        claim_status: 'var(--cyan)',
        general: 'var(--purple)',
        escalate: 'var(--danger)',
    };
    const maxIntentCount = Math.max(...data.intent_distribution.map(i => i.count));
    document.getElementById('chart-intent').innerHTML = `
        <div class="v-bar-chart">
            ${data.intent_distribution.map(i => `
                <div class="v-bar-col">
                    <span class="v-bar-value">${i.count}</span>
                    <div class="v-bar" style="height: ${(i.count / maxIntentCount) * 120}px; background: ${intentColors[i.intent] || 'var(--accent)'}"></div>
                    <span class="v-bar-label">${i.intent}</span>
                </div>
            `).join('')}
        </div>
    `;

    // Daily volume
    const maxDaily = Math.max(...data.daily_volume.map(d => d.count));
    document.getElementById('chart-daily').innerHTML = `
        <div class="v-bar-chart">
            ${data.daily_volume.map(d => `
                <div class="v-bar-col">
                    <span class="v-bar-value">${d.count}</span>
                    <div class="v-bar" style="height: ${(d.count / maxDaily) * 120}px; background: var(--accent)"></div>
                    <span class="v-bar-label">${d.day}</span>
                </div>
            `).join('')}
        </div>
    `;

    // Escalation reasons (horizontal bar)
    const maxEsc = Math.max(...data.escalation_reasons.map(r => r.count));
    document.getElementById('chart-escalation').innerHTML = `
        <div class="h-bar-chart">
            ${data.escalation_reasons.map(r => `
                <div class="h-bar-row">
                    <span class="h-bar-label">${r.reason}</span>
                    <div class="h-bar-track">
                        <div class="h-bar-fill" style="width: ${(r.count / maxEsc) * 100}%; background: var(--danger)">${r.count}</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    // Sentiment distribution
    const sentimentColors = {
        positive: 'var(--success)',
        neutral: 'var(--accent)',
        concerned: 'var(--warning)',
        frustrated: 'var(--danger)',
        angry: 'var(--danger)',
    };
    document.getElementById('chart-sentiment').innerHTML = `
        <div class="sentiment-bars">
            ${data.sentiment_distribution.map(s => `
                <div class="sentiment-bar-row">
                    <span class="sentiment-bar-dot" style="background: ${sentimentColors[s.sentiment]}"></span>
                    <span class="sentiment-bar-name">${s.sentiment}</span>
                    <div class="sentiment-bar-track">
                        <div class="sentiment-bar-fill" style="width: ${s.pct}%; background: ${sentimentColors[s.sentiment]}"></div>
                    </div>
                    <span class="sentiment-bar-pct">${s.pct}%</span>
                </div>
            `).join('')}
        </div>
    `;

    // Tool call frequency (horizontal)
    const maxTool = Math.max(...data.tool_call_frequency.map(t => t.count));
    const toolColors = {
        search_knowledge_base: 'var(--success)',
        get_eligibility: 'var(--accent)',
        get_claim_status: 'var(--cyan)',
        create_fnol: 'var(--orange)',
        schedule_callback: 'var(--purple)',
        escalate_to_human: 'var(--danger)',
    };
    document.getElementById('chart-tools').innerHTML = `
        <div class="h-bar-chart">
            ${data.tool_call_frequency.map(t => `
                <div class="h-bar-row">
                    <span class="h-bar-label" style="font-family: var(--mono); font-size: 10px;">${t.tool}</span>
                    <div class="h-bar-track">
                        <div class="h-bar-fill" style="width: ${(t.count / maxTool) * 100}%; background: ${toolColors[t.tool] || 'var(--accent)'}">${t.count}</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    // Avg handle time by intent
    const maxAHT = Math.max(...data.avg_handle_time_by_intent.map(i => i.seconds));
    document.getElementById('chart-handle-time').innerHTML = `
        <div class="h-bar-chart">
            ${data.avg_handle_time_by_intent.map(i => `
                <div class="h-bar-row">
                    <span class="h-bar-label">${i.intent}</span>
                    <div class="h-bar-track">
                        <div class="h-bar-fill" style="width: ${(i.seconds / maxAHT) * 100}%; background: ${intentColors[i.intent] || 'var(--accent)'}">${Math.floor(i.seconds / 60)}m ${i.seconds % 60}s</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function backFromAnalytics() {
    document.getElementById('analytics-screen').classList.remove('active');
    document.getElementById('analytics-screen').style.display = 'none';

    if (state.sessionId) {
        const chatScreen = document.getElementById('chat-screen');
        chatScreen.classList.add('active');
        chatScreen.style.display = 'flex';
        chatScreen.style.flexDirection = 'column';
    } else {
        document.getElementById('auth-screen').classList.add('active');
    }
}


// ═══════════════════════════════════════════════════════
// DOCUMENT VIEWER
// ═══════════════════════════════════════════════════════

// Cache for fetched documents
const _docCache = {};

function initDocViewer() {
    document.getElementById('doc-viewer-close')?.addEventListener('click', closeDocViewer);
    document.getElementById('doc-viewer-overlay')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeDocViewer();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeDocViewer();
    });
}

document.addEventListener('DOMContentLoaded', initDocViewer);

async function openDocViewer(docName, highlightChunk) {
    const overlay = document.getElementById('doc-viewer-overlay');
    const nameEl = document.getElementById('doc-viewer-name');
    const bodyEl = document.getElementById('doc-viewer-body');

    nameEl.textContent = docName;
    bodyEl.innerHTML = '<div class="doc-viewer-loading">Loading document...</div>';
    overlay.classList.remove('hidden');

    try {
        let content;
        if (_docCache[docName]) {
            content = _docCache[docName];
        } else {
            const res = await fetch(`${API_BASE}/api/docs/${encodeURIComponent(docName)}`);
            if (!res.ok) throw new Error('Document not found');
            const data = await res.json();
            content = data.content;
            _docCache[docName] = content;
        }

        bodyEl.innerHTML = renderMarkdownWithHighlight(content, highlightChunk);

        // Scroll to highlighted section
        requestAnimationFrame(() => {
            const highlight = bodyEl.querySelector('.highlight-chunk');
            if (highlight) {
                highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    } catch (e) {
        bodyEl.innerHTML = `<div class="doc-viewer-loading">Failed to load document: ${escapeHtml(e.message)}</div>`;
    }
}

function closeDocViewer() {
    document.getElementById('doc-viewer-overlay').classList.add('hidden');
}

function renderMarkdownWithHighlight(markdown, highlightChunk) {
    // Find the best matching region in the document for highlighting
    let highlightStart = -1;
    let highlightEnd = -1;

    if (highlightChunk && highlightChunk.length > 30) {
        // Use the first 60 chars of the chunk to find the match location
        const searchText = highlightChunk.slice(0, 60).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const match = markdown.match(new RegExp(searchText.slice(0, 40), 'i'));
        if (match) {
            highlightStart = match.index;
            // Find a reasonable end point (next section heading or ~chunk length)
            const chunkLen = Math.min(highlightChunk.length, markdown.length - highlightStart);
            highlightEnd = highlightStart + chunkLen;
        }
    }

    // Convert markdown to HTML with highlighting
    const lines = markdown.split('\n');
    let html = '';
    let charPos = 0;
    let inHighlight = false;
    let inList = false;

    for (const line of lines) {
        const lineStart = charPos;
        const lineEnd = charPos + line.length;

        // Check if this line should start/end highlight
        const shouldHighlight = highlightStart >= 0 && lineStart < highlightEnd && lineEnd > highlightStart;

        if (shouldHighlight && !inHighlight) {
            if (inList) { html += '</ul>'; inList = false; }
            html += '<div class="highlight-chunk">';
            inHighlight = true;
        }

        if (line.startsWith('# ')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h1>${escapeHtml(line.slice(2))}</h1>`;
        } else if (line.startsWith('## ')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h2>${escapeHtml(line.slice(3))}</h2>`;
        } else if (line.startsWith('### ')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h3>${escapeHtml(line.slice(4))}</h3>`;
        } else if (line.startsWith('#### ')) {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<h4>${escapeHtml(line.slice(5))}</h4>`;
        } else if (line.match(/^[-*]\s/)) {
            if (!inList) { html += '<ul>'; inList = true; }
            html += `<li>${formatInlineMarkdown(line.slice(2))}</li>`;
        } else if (line.match(/^\d+\.\s/)) {
            if (!inList) { html += '<ul>'; inList = true; }
            html += `<li>${formatInlineMarkdown(line.replace(/^\d+\.\s/, ''))}</li>`;
        } else if (line.trim() === '') {
            if (inList) { html += '</ul>'; inList = false; }
            // Skip blank lines in highlight
        } else {
            if (inList) { html += '</ul>'; inList = false; }
            html += `<p>${formatInlineMarkdown(line)}</p>`;
        }

        if (inHighlight && lineEnd >= highlightEnd) {
            if (inList) { html += '</ul>'; inList = false; }
            html += '</div>';
            inHighlight = false;
        }

        charPos = lineEnd + 1; // +1 for \n
    }

    if (inList) html += '</ul>';
    if (inHighlight) html += '</div>';

    return html;
}

function formatInlineMarkdown(text) {
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    return html;
}


// ═══════════════════════════════════════════════════════
// ARCHITECTURE MODAL
// ═══════════════════════════════════════════════════════

function openArchModal() {
    document.getElementById('arch-overlay').classList.remove('hidden');
}

function closeArchModal() {
    document.getElementById('arch-overlay').classList.add('hidden');
}


// ═══════════════════════════════════════════════════════
// VOICE INPUT / OUTPUT (Web Speech API)
// ═══════════════════════════════════════════════════════

function toggleVoiceInput() {
    const btn = document.getElementById('voice-mic-btn');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert('Speech recognition requires Chrome. Please open this demo in Google Chrome.');
        return;
    }

    // If already recording, stop
    if (state.voiceRecognition) {
        state.voiceRecognition.stop();
        state.voiceRecognition = null;
        btn.classList.remove('recording');
        removeVoiceIndicator();
        return;
    }

    const input = document.getElementById('message-input');
    let finalTranscript = '';

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            } else {
                interim += event.results[i][0].transcript;
            }
        }
        input.value = finalTranscript + interim;
        autoResizeInput(input);
        document.getElementById('send-btn').disabled = !input.value.trim();
    };

    recognition.onend = () => {
        btn.classList.remove('recording');
        state.voiceRecognition = null;
        input.placeholder = 'Type your message...';
        removeVoiceIndicator();
        // Auto-send if we got a result
        if (finalTranscript.trim() && !state.isProcessing) {
            sendMessage();
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        btn.classList.remove('recording');
        state.voiceRecognition = null;
        input.placeholder = 'Type your message...';
        removeVoiceIndicator();

        if (event.error === 'not-allowed') {
            alert('Microphone access denied. Please allow microphone access in your browser settings and try again.');
        } else if (event.error === 'no-speech') {
            // Silent timeout — not an error to show
        } else {
            const hint = document.getElementById('input-area')?.querySelector('.input-hint');
            if (hint) {
                const orig = hint.textContent;
                hint.textContent = `Voice error: ${event.error}. Try again or use Chrome.`;
                hint.style.color = 'var(--danger)';
                setTimeout(() => { hint.textContent = orig; hint.style.color = ''; }, 4000);
            }
        }
    };

    // Show indicator and start recognition — indicator must appear before start()
    showVoiceIndicator();
    btn.classList.add('recording');
    input.placeholder = 'Listening...';

    try {
        recognition.start();
        state.voiceRecognition = recognition;
    } catch (err) {
        console.error('Failed to start speech recognition:', err);
        btn.classList.remove('recording');
        input.placeholder = 'Type your message...';
        // Keep indicator visible briefly so user sees it attempted
        setTimeout(removeVoiceIndicator, 2000);
    }
}

function showVoiceIndicator() {
    // Show a "Simulated ASR" badge above the input
    const existing = document.getElementById('voice-indicator');
    if (existing) return;

    const indicator = document.createElement('div');
    indicator.id = 'voice-indicator';
    indicator.className = 'voice-indicator';
    indicator.innerHTML = `
        <span class="voice-indicator-dot"></span>
        <span>Simulated ASR — Listening</span>
        <span class="voice-indicator-channel">VOICE CHANNEL</span>
    `;

    const inputArea = document.getElementById('input-area');
    inputArea.insertBefore(indicator, inputArea.firstChild);
}

function removeVoiceIndicator() {
    const indicator = document.getElementById('voice-indicator');
    if (indicator) indicator.remove();
}

function speakText(text) {
    if (!window.speechSynthesis) return;

    // Stop any ongoing speech
    window.speechSynthesis.cancel();

    // Clean markdown from text
    const clean = text
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/`(.*?)`/g, '$1')
        .replace(/^[-•]\s+/gm, '')
        .replace(/^\d+\.\s+/gm, '');

    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 0.8;

    window.speechSynthesis.speak(utterance);
}


// ═══════════════════════════════════════════════════════
// COMPLIANCE TRACKING
// ═══════════════════════════════════════════════════════

function updateComplianceFlags(type, detail) {
    const container = document.getElementById('compliance-flags');
    const empty = container.querySelector('.compliance-flag-empty');
    if (empty) empty.remove();

    // Don't add duplicate flags of the same type
    if (container.querySelector(`[data-flag-type="${type}"]`)) return;

    const flag = document.createElement('div');
    flag.className = 'compliance-item triggered';
    flag.setAttribute('data-flag-type', type);
    flag.innerHTML = `
        <span class="compliance-dot yellow"></span>
        <div>
            <strong>${type === 'hipaa' ? 'HIPAA — PHI Detected' :
                     type === 'pii' ? 'PII Detected in Input' :
                     type === 'sentiment_escalation' ? 'Sentiment Escalation Risk' :
                     type === 'topic_blocked' ? 'Restricted Topic Blocked' : type}</strong>
            <p>${escapeHtml(detail)}</p>
        </div>
    `;
    container.appendChild(flag);

    // If HIPAA, also activate the HIPAA item in the regulatory section
    if (type === 'hipaa') {
        const hipaaItem = document.getElementById('compliance-hipaa');
        if (hipaaItem) {
            hipaaItem.classList.add('triggered');
            hipaaItem.querySelector('.compliance-dot').className = 'compliance-dot yellow';
        }
    }
}

// ═══════════════════════════════════════════════════════
// DISCOVERY MODE
// ═══════════════════════════════════════════════════════

function toggleDiscoveryMode() {
    const existing = document.getElementById('discovery-overlay');
    if (existing) {
        existing.remove();
        document.getElementById('discovery-btn')?.classList.remove('active');
        return;
    }

    document.getElementById('discovery-btn')?.classList.add('active');

    const overlay = document.createElement('div');
    overlay.id = 'discovery-overlay';
    overlay.className = 'discovery-overlay';

    // Annotations for key UI elements
    const annotations = [
        { target: '.chat-header', label: 'Genesys Web Messenger Header', detail: 'Maps to Genesys Messenger SDK config', position: 'below' },
        { target: '.sidebar', label: 'CRM Screen Pop', detail: 'Genesys Data Actions fetch from policy admin system', position: 'right' },
        { target: '.messages-container', label: 'Bot Conversation', detail: 'Genesys Bot Connector API ↔ Bedrock Agent', position: 'center' },
        { target: '.hood-panel.open', label: 'Agent Supervisor Dashboard', detail: 'Genesys Workforce Engagement Mgmt analytics', position: 'left' },
        { target: '.sentiment-indicator', label: 'Predictive Engagement', detail: 'Real-time sentiment → Genesys journey analytics', position: 'below' },
        { target: '.input-area', label: 'Omnichannel Input', detail: 'Voice (IVR), Chat (Web Msg), SMS (Open Msg)', position: 'above' },
    ];

    let html = '<div class="discovery-dismiss" id="discovery-dismiss">Click anywhere or press D to exit Discovery Mode</div>';

    annotations.forEach((ann, i) => {
        const el = document.querySelector(ann.target);
        if (!el || el.offsetHeight === 0) return;

        const rect = el.getBoundingClientRect();
        let top, left;

        if (ann.position === 'below') {
            top = rect.bottom + 8;
            left = rect.left + rect.width / 2;
        } else if (ann.position === 'above') {
            top = rect.top - 8;
            left = rect.left + rect.width / 2;
        } else if (ann.position === 'center') {
            top = rect.top + rect.height / 2;
            left = rect.left + rect.width / 2;
        } else if (ann.position === 'right') {
            top = rect.top + rect.height / 3;
            left = rect.right + 8;
        } else {
            top = rect.top + rect.height / 3;
            left = rect.left - 8;
        }

        html += `
            <div class="discovery-annotation" style="top: ${top}px; left: ${left}px; animation-delay: ${i * 0.1}s">
                <div class="discovery-dot"></div>
                <div class="discovery-card">
                    <strong>${ann.label}</strong>
                    <span>${ann.detail}</span>
                </div>
            </div>
        `;
    });

    // Business metrics callout
    html += `
        <div class="discovery-metrics">
            <div class="discovery-metric-card">
                <span class="dm-value">73%</span>
                <span class="dm-label">Containment Rate</span>
                <span class="dm-detail">Conversations resolved without human agent</span>
            </div>
            <div class="discovery-metric-card">
                <span class="dm-value">~$0.02</span>
                <span class="dm-label">Cost per Interaction</span>
                <span class="dm-detail">Haiku classify + Sonnet generate</span>
            </div>
            <div class="discovery-metric-card">
                <span class="dm-value">&lt;3s</span>
                <span class="dm-label">Avg Response Time</span>
                <span class="dm-detail">Classification + tools + generation</span>
            </div>
            <div class="discovery-metric-card">
                <span class="dm-value">10K/day</span>
                <span class="dm-label">Designed Scale</span>
                <span class="dm-detail">~$210/day LLM cost at volume</span>
            </div>
        </div>
    `;

    overlay.innerHTML = html;
    document.body.appendChild(overlay);

    // Dismiss handlers
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay || e.target.id === 'discovery-dismiss') {
            toggleDiscoveryMode();
        }
    });
}

function updateComplianceRegion() {
    const label = document.getElementById('compliance-region-label');
    const detail = document.getElementById('compliance-region-detail');
    if (state.regionEU) {
        label.textContent = 'EU — eu-west-1';
        detail.textContent = 'Data processed in AWS EU West. GDPR Article 17 (right to erasure) enforced. 90-day retention policy.';
    } else {
        label.textContent = 'US — us-east-1';
        detail.textContent = 'Data processed and stored in AWS US East region. SOC 2 Type II compliant.';
    }
}
