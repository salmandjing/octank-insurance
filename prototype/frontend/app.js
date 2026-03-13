/* ═══════════════════════════════════════════════════════════════════
   ClaimFlow AI — Frontend Application
   Nebraska Insurance FNOL Automation — Premium SaaS Demo
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = '';
let currentClaimId = null;
let claimsData = [];
let ws = null;

/* ═══════════════════════════════════════════════════════════════════
   SCREEN NAVIGATION
   ═══════════════════════════════════════════════════════════════════ */

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(function (s) {
        s.classList.remove('active');
    });
    var target = document.getElementById(screenId);
    if (target) {
        target.classList.add('active');
    }
}

function showDashboardView() {
    document.querySelectorAll('.nav-tab').forEach(function (t) { t.classList.remove('nav-active'); });
    document.querySelector('[data-view="dashboard"]').classList.add('nav-active');
}

function showClaimsView() {
    document.querySelectorAll('.nav-tab').forEach(function (t) { t.classList.remove('nav-active'); });
    document.querySelector('[data-view="claims"]').classList.add('nav-active');
}

/* ═══════════════════════════════════════════════════════════════════
   DASHBOARD
   ═══════════════════════════════════════════════════════════════════ */

async function loadDashboard() {
    try {
        var res = await fetch(API_BASE + '/api/claims');
        var data = await res.json();
        claimsData = data.claims || [];
    } catch (e) {
        console.warn('Could not load claims:', e.message);
        claimsData = [];
    }
    renderClaimsQueue();
    updateStats();
}

function renderClaimsQueue() {
    var container = document.getElementById('claims-queue');
    var countEl = document.getElementById('queue-count');
    if (!container) return;

    if (countEl) {
        countEl.textContent = claimsData.length + ' claim' + (claimsData.length !== 1 ? 's' : '');
    }

    if (!claimsData.length) {
        container.innerHTML =
            '<div class="empty-state">' +
            '<svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="8" y="6" width="32" height="36" rx="4" stroke="#C5CDD8" stroke-width="1.5"/><path d="M16 16h16M16 22h16M16 28h10" stroke="#C5CDD8" stroke-width="1.5" stroke-linecap="round"/></svg>' +
            '<p>No claims processed yet</p>' +
            '<span>Click an incoming email to get started</span>' +
            '</div>';
        return;
    }

    container.innerHTML = claimsData.map(function (c) {
        var statusText = formatStatus(c.status);
        var timeStr = formatTime(c.created_at);

        return '<div class="claim-queue-item" onclick="openClaim(\'' + escapeHtml(c.claim_id) + '\')">' +
            '<div class="claim-status-dot dot-' + escapeHtml(c.status || 'new') + '"></div>' +
            '<div class="claim-queue-info">' +
            '<div class="claim-queue-name">' + escapeHtml(c.reporter_name || c.email_from || 'Unknown') + '</div>' +
            '<div class="claim-queue-subject">' + escapeHtml(c.email_subject || 'No subject') + '</div>' +
            '</div>' +
            '<div class="claim-queue-meta">' +
            '<span class="claim-queue-status status-' + escapeHtml(c.status || 'new') + '">' + escapeHtml(statusText) + '</span>' +
            '<span class="claim-queue-time">' + escapeHtml(timeStr) + '</span>' +
            '</div>' +
            '</div>';
    }).join('');
}

function updateStats() {
    var todayEl = document.getElementById('stat-today');
    var pendingEl = document.getElementById('stat-pending');
    var avgTimeEl = document.getElementById('stat-avg-time');

    if (todayEl) animateCounter(todayEl, claimsData.length);
    if (pendingEl) {
        var pending = claimsData.filter(function (c) { return c.status === 'needs_review'; }).length;
        animateCounter(pendingEl, pending);
    }
    if (avgTimeEl) {
        if (claimsData.length > 0) {
            var totalMs = claimsData.reduce(function (sum, c) { return sum + (c.processing_time_ms || 0); }, 0);
            var avgMs = totalMs / claimsData.length;
            avgTimeEl.textContent = avgMs > 0 ? (avgMs / 1000).toFixed(1) + 's' : '< 1s';
        } else {
            avgTimeEl.textContent = '--';
        }
    }
}

function animateCounter(el, target) {
    var current = parseInt(el.textContent) || 0;
    if (current === target) return;
    var step = target > current ? 1 : -1;
    var interval = setInterval(function () {
        current += step;
        el.textContent = current;
        if (current === target) clearInterval(interval);
    }, 50);
}

/* ═══════════════════════════════════════════════════════════════════
   DEMO SCENARIOS
   ═══════════════════════════════════════════════════════════════════ */

async function runScenario(name) {
    showLoading('Receiving email...');
    addActivity('Incoming email received', 'blue');

    try {
        // Animate pipeline steps
        setTimeout(function () { advanceLoadingStep(2); updateLoadingText('AI analyzing email...'); }, 600);
        setTimeout(function () { addActivity('AI parsing and extracting FNOL data', 'amber'); }, 800);

        var res = await fetch(API_BASE + '/api/demo/scenario/' + encodeURIComponent(name), {
            method: 'POST'
        });
        var data = await res.json();

        advanceLoadingStep(3);
        updateLoadingText('Extraction complete!');
        addActivity('FNOL extraction complete — ' + formatLossType(data.extraction && data.extraction.loss_type || ''), 'green');

        await new Promise(function (r) { setTimeout(r, 500); });

        if (data.claim_id) {
            await loadDashboard();
            openClaim(data.claim_id);
        } else {
            showToast('Scenario completed but no claim ID returned.', 'warning');
            await loadDashboard();
        }
    } catch (e) {
        showToast('Error processing scenario: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

/* ═══════════════════════════════════════════════════════════════════
   CLAIM PROCESSING
   ═══════════════════════════════════════════════════════════════════ */

async function openClaim(claimId) {
    currentClaimId = claimId;
    showLoading('Loading claim...');
    try {
        var res = await fetch(API_BASE + '/api/claims/' + encodeURIComponent(claimId));
        var claim = await res.json();
        renderClaimProcessing(claim);
        showScreen('claim-processing');
    } catch (e) {
        showToast('Error loading claim: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderClaimProcessing(claim) {
    // Claim ID badge
    var idBadge = document.getElementById('claim-id-badge');
    if (idBadge) idBadge.textContent = claim.claim_id || '';

    // Left panel: Original email
    setTextContent('email-from', claim.email_from || '');
    setTextContent('email-subject', claim.email_subject || '');
    setTextContent('email-body', claim.email_raw || '');

    // Center panel: Extraction form
    var ext = claim.extraction || {};
    var textFields = [
        'reporter_name', 'policy_number', 'date_of_loss', 'time_of_loss',
        'location', 'description', 'injury_description', 'police_report_number'
    ];
    textFields.forEach(function (f) {
        var el = document.getElementById('field-' + f);
        if (el) el.value = ext[f] || '';
    });

    var lossType = document.getElementById('field-loss_type');
    if (lossType) lossType.value = ext.loss_type || 'unknown';

    var injuries = document.getElementById('field-injuries');
    if (injuries) injuries.checked = ext.injuries || false;

    var policeReport = document.getElementById('field-police_report');
    if (policeReport) policeReport.checked = ext.police_report || false;

    var op = document.getElementById('field-other_parties');
    if (op) {
        if (ext.other_parties && typeof ext.other_parties === 'object') {
            op.value = JSON.stringify(ext.other_parties, null, 2);
        } else if (ext.other_parties) {
            op.value = String(ext.other_parties);
        } else {
            op.value = '';
        }
    }

    // Priority badge
    var priorityEl = document.getElementById('claim-priority');
    if (priorityEl) {
        priorityEl.innerHTML = '<span class="priority-badge priority-' +
            escapeHtml(claim.priority || 'normal') + '">' +
            escapeHtml(claim.priority || 'normal') + '</span>';
    }

    // Confidence score
    var confidenceEl = document.getElementById('claim-confidence');
    if (confidenceEl) {
        confidenceEl.innerHTML = renderConfidence(ext.confidence_score);
    }

    // Field-level confidence dots
    var fieldConfidences = ext.field_confidences || {};
    document.querySelectorAll('.confidence-dot.confidence-field').forEach(function (dot) {
        var field = dot.getAttribute('data-field');
        var score = fieldConfidences[field];
        dot.classList.remove('dot-high', 'dot-medium', 'dot-low');
        if (score !== undefined && score !== null) {
            var pct = Math.round(score * 100);
            if (pct >= 80) dot.classList.add('dot-high');
            else if (pct >= 50) dot.classList.add('dot-medium');
            else dot.classList.add('dot-low');
            dot.title = 'Confidence: ' + pct + '%';
        } else {
            dot.title = 'Field confidence';
        }
    });

    // Missing fields warnings
    var missing = ext.missing_fields || [];
    var missingEl = document.getElementById('missing-fields');
    if (missingEl) {
        if (missing.length) {
            missingEl.innerHTML = '<div class="missing-warning">' +
                '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1L1 12h12L7 1z" stroke="currentColor" stroke-width="1.5"/><path d="M7 5.5v3M7 10v.01" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>' +
                'Missing: ' + escapeHtml(missing.join(', ')) + '</div>';
            missingEl.style.display = 'block';
        } else {
            missingEl.style.display = 'none';
        }
    }

    // Right panel: AI Transparency
    renderTraceSteps(claim.trace_steps || []);

    // Policy data
    var policyInfo = document.getElementById('policy-info');
    if (policyInfo) {
        if (claim.policy_data && !claim.policy_data.error) {
            policyInfo.innerHTML = '<div class="info-card">' +
                '<div class="info-label">Policy</div>' +
                '<div class="info-value">' + escapeHtml(claim.policy_data.policy_number || 'N/A') + '</div>' +
                '<div class="info-label">Carrier</div>' +
                '<div class="info-value">' + escapeHtml(claim.policy_data.carrier || 'N/A') + '</div>' +
                '<div class="info-label">Type</div>' +
                '<div class="info-value">' + escapeHtml(formatLossType(claim.policy_data.type || '')) + '</div>' +
                '<div class="info-label">Status</div>' +
                '<div class="info-value">' + escapeHtml(claim.policy_data.status || 'N/A') + '</div>' +
                '<div class="info-label">Client</div>' +
                '<div class="info-value">' + escapeHtml(claim.policy_data.client_name || 'N/A') + '</div>' +
                '</div>';
        } else {
            policyInfo.innerHTML = '<div class="info-card warning">Policy not found or not yet verified</div>';
        }
    }

    // Show/hide action buttons based on status
    var btnApprove = document.getElementById('btn-approve');
    var btnFollowup = document.getElementById('btn-followup');
    if (btnApprove) {
        btnApprove.style.display = (claim.status === 'needs_review' || claim.status === 'new') ? '' : 'none';
    }
    if (btnFollowup) {
        btnFollowup.style.display = (missing.length > 0) ? '' : 'none';
    }
}

function renderTraceSteps(steps) {
    var container = document.getElementById('trace-steps');
    if (!container) return;

    if (!steps.length) {
        container.innerHTML = '<div class="trace-empty">Run a scenario to see the AI processing trace.</div>';
        return;
    }

    container.innerHTML = steps.map(function (step, i) {
        var statusClass = step.status || 'success';
        var icon = getTraceIcon(step.step_type || step.name, statusClass);
        var detailsHtml = '';
        if (step.details) {
            detailsHtml = '<div class="trace-details">' + formatTraceDetails(step.details) + '</div>';
        }
        var durationStr = step.duration_ms ? step.duration_ms + 'ms' : '';

        return '<div class="trace-step trace-' + escapeHtml(statusClass) + '" style="animation-delay:' + (i * 0.1) + 's">' +
            '<div class="trace-header">' +
            '<span class="trace-icon">' + icon + '</span>' +
            '<span class="trace-name">' + escapeHtml(step.name || '') + '</span>' +
            '<span class="trace-time">' + escapeHtml(durationStr) + '</span>' +
            '</div>' +
            detailsHtml +
            '</div>';
    }).join('');
}

function getTraceIcon(type, status) {
    if (status === 'error') return '<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 3l6 6M9 3l-6 6" stroke="#C4342D" stroke-width="1.5" stroke-linecap="round"/></svg>';
    if (status === 'warning') return '<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 2L1 10h10L6 2z" stroke="#D4930D" stroke-width="1" fill="none"/><path d="M6 5v2.5M6 9v.01" stroke="#D4930D" stroke-width="1" stroke-linecap="round"/></svg>';
    return '<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 6l2 2 4-4" stroke="#2D8A4E" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
}

function formatTraceDetails(details) {
    return Object.entries(details).map(function (entry) {
        var k = entry[0];
        var v = entry[1];
        var val = (typeof v === 'object') ? JSON.stringify(v) : String(v);
        if (val.length > 80) val = val.substring(0, 77) + '...';
        return '<span class="trace-detail"><strong>' + escapeHtml(k) + ':</strong> ' + escapeHtml(val) + '</span>';
    }).join(' ');
}

/* ═══════════════════════════════════════════════════════════════════
   APPROVE & GENERATE SUBMISSION
   ═══════════════════════════════════════════════════════════════════ */

async function approveClaim() {
    if (!currentClaimId) return;
    showLoading('Generating carrier submission and client email...');
    addActivity('Generating carrier submission for ' + currentClaimId, 'blue');

    var extraction = collectFormData();
    try {
        var res = await fetch(API_BASE + '/api/claims/' + encodeURIComponent(currentClaimId) + '/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extraction: extraction })
        });
        var data = await res.json();
        renderSubmissionPreview(data);
        showScreen('submission-preview');
        addActivity('Submission documents generated', 'green');
    } catch (e) {
        showToast('Error generating submission: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

function collectFormData() {
    return {
        reporter_name: getFieldValue('field-reporter_name'),
        policy_number: getFieldValue('field-policy_number'),
        date_of_loss: getFieldValue('field-date_of_loss'),
        time_of_loss: getFieldValue('field-time_of_loss'),
        location: getFieldValue('field-location'),
        loss_type: getFieldValue('field-loss_type'),
        description: getFieldValue('field-description'),
        injuries: getFieldChecked('field-injuries'),
        injury_description: getFieldValue('field-injury_description'),
        police_report: getFieldChecked('field-police_report'),
        police_report_number: getFieldValue('field-police_report_number'),
        other_parties: getFieldValue('field-other_parties')
    };
}

function getFieldValue(id) {
    var el = document.getElementById(id);
    return el ? el.value || '' : '';
}

function getFieldChecked(id) {
    var el = document.getElementById(id);
    return el ? el.checked : false;
}

function renderSubmissionPreview(data) {
    var carrierTextarea = document.getElementById('carrier-submission-text');
    var clientTextarea = document.getElementById('client-email-text');
    var clientTo = document.getElementById('client-email-to');
    var clientSubject = document.getElementById('client-email-subject');

    if (carrierTextarea) carrierTextarea.value = data.carrier_submission || 'No submission generated.';
    if (clientTextarea) clientTextarea.value = data.client_email || 'No email generated.';
    if (clientTo) clientTo.textContent = data.client_email_to || '';
    if (clientSubject) clientSubject.textContent = data.client_email_subject || '';

    var successEl = document.getElementById('submit-success');
    if (successEl) successEl.style.display = 'none';
    var submitBtn = document.getElementById('btn-submit-carrier');
    if (submitBtn) submitBtn.style.display = '';
}

/* ═══════════════════════════════════════════════════════════════════
   SUBMIT TO CARRIER
   ═══════════════════════════════════════════════════════════════════ */

async function submitToCarrier() {
    if (!currentClaimId) return;
    showLoading('Submitting to carrier...');
    try {
        var res = await fetch(API_BASE + '/api/claims/' + encodeURIComponent(currentClaimId) + '/submit', {
            method: 'POST'
        });
        var data = await res.json();
        showToast(data.message || 'Claim submitted!', 'success');
        addActivity('Claim ' + currentClaimId + ' submitted to carrier', 'green');

        var successEl = document.getElementById('submit-success');
        if (successEl) successEl.style.display = 'flex';

        var submitBtn = document.getElementById('btn-submit-carrier');
        if (submitBtn) submitBtn.style.display = 'none';

        await loadDashboard();
    } catch (e) {
        showToast('Error submitting claim', 'error');
    } finally {
        hideLoading();
    }
}

/* ═══════════════════════════════════════════════════════════════════
   FOLLOW-UP, DRAFT, ESCALATE
   ═══════════════════════════════════════════════════════════════════ */

async function generateFollowup() {
    if (!currentClaimId) return;
    showLoading('Generating follow-up email...');
    try {
        var res = await fetch(API_BASE + '/api/claims/' + encodeURIComponent(currentClaimId) + '/followup', {
            method: 'POST'
        });
        var data = await res.json();
        if (data.followup_email) {
            showModal('Follow-up Email Draft',
                '<p><strong>To:</strong> ' + escapeHtml(data.to || '') + '</p>' +
                '<p><strong>Subject:</strong> ' + escapeHtml(data.subject || '') + '</p>' +
                '<p><strong>Missing Fields:</strong> ' + escapeHtml((data.missing_fields || []).join(', ')) + '</p>' +
                '<hr style="border:none;border-top:1px solid #E2E6ED;margin:12px 0;">' +
                '<pre style="white-space:pre-wrap;font-family:Inter,sans-serif;font-size:13px;line-height:1.6;">' + escapeHtml(data.followup_email) + '</pre>'
            );
            addActivity('Follow-up email generated for ' + currentClaimId, 'amber');
        } else {
            showToast('No follow-up email generated.', 'warning');
        }
    } catch (e) {
        showToast('Error generating follow-up', 'error');
    } finally {
        hideLoading();
    }
}

async function saveDraft() {
    if (!currentClaimId) return;
    var extraction = collectFormData();
    showLoading('Saving draft...');
    try {
        var res = await fetch(API_BASE + '/api/claims/' + encodeURIComponent(currentClaimId) + '/draft', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ extraction: extraction })
        });
        await res.json();
        showToast('Draft saved successfully.', 'success');
        addActivity('Draft saved for ' + currentClaimId, 'blue');
    } catch (e) {
        showToast('Error saving draft: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

async function escalateClaim() {
    if (!currentClaimId) return;
    if (!confirm('Escalate this claim to a senior adjuster?')) return;
    showLoading('Escalating claim...');
    try {
        var res = await fetch(API_BASE + '/api/claims/' + encodeURIComponent(currentClaimId) + '/escalate', {
            method: 'POST'
        });
        var data = await res.json();
        showToast(data.message || 'Claim escalated.', 'warning');
        addActivity('Claim ' + currentClaimId + ' escalated', 'red');
        await loadDashboard();
        showScreen('dashboard');
    } catch (e) {
        showToast('Error escalating claim: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

/* ═══════════════════════════════════════════════════════════════════
   CHAT PANEL
   ═══════════════════════════════════════════════════════════════════ */

var chatSessionId = null;

function toggleChat() {
    var panel = document.getElementById('chat-panel');
    if (!panel) return;
    panel.classList.toggle('open');

    if (panel.classList.contains('open') && !chatSessionId) {
        initChatSession();
    }
}

async function initChatSession() {
    try {
        var res = await fetch(API_BASE + '/api/session/start?client_id=CLI-1001', {
            method: 'POST'
        });
        var data = await res.json();
        chatSessionId = data.session_id;
    } catch (e) {
        console.warn('Could not start chat session:', e.message);
    }
}

function sendSuggestion(text) {
    var input = document.getElementById('chat-input');
    if (input) input.value = text;
    // Hide suggestions after click
    var suggestions = document.getElementById('chat-suggestions');
    if (suggestions) suggestions.style.display = 'none';
    sendChatMessage();
}

async function sendChatMessage() {
    var input = document.getElementById('chat-input');
    if (!input) return;
    var msg = input.value.trim();
    if (!msg) return;

    addChatBubble(msg, 'user');
    input.value = '';

    // Hide suggestions after first message
    var suggestions = document.getElementById('chat-suggestions');
    if (suggestions) suggestions.style.display = 'none';

    if (!chatSessionId) {
        await initChatSession();
    }

    if (!chatSessionId) {
        addChatBubble('Sorry, I could not connect to the server. Please try again.', 'assistant');
        return;
    }

    // Show typing indicator
    showTypingIndicator();

    try {
        var res = await fetch(API_BASE + '/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: chatSessionId,
                message: msg
            })
        });
        var data = await res.json();
        hideTypingIndicator();
        addChatBubble(data.response || 'No response received.', 'assistant');
    } catch (e) {
        hideTypingIndicator();
        addChatBubble('Sorry, I encountered an error. Please try again.', 'assistant');
    }
}

function addChatBubble(text, role) {
    var container = document.getElementById('chat-messages');
    if (!container) return;

    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-' + role;

    if (role === 'assistant') {
        bubble.innerHTML =
            '<div class="chat-bubble-avatar">' +
            '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1a6 6 0 100 12A6 6 0 007 1z" stroke="currentColor" stroke-width="1"/><path d="M4.5 6h.01M9.5 6h.01" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M5 9c.4.6 1 1 2 1s1.6-.4 2-1" stroke="currentColor" stroke-width="1" stroke-linecap="round"/></svg>' +
            '</div>' +
            '<div class="chat-bubble-content">' + escapeHtml(text) + '</div>';
    } else {
        bubble.innerHTML = '<div class="chat-bubble-content">' + escapeHtml(text) + '</div>';
    }

    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    var container = document.getElementById('chat-messages');
    if (!container) return;
    var typing = document.createElement('div');
    typing.id = 'typing-indicator';
    typing.className = 'chat-bubble chat-assistant';
    typing.innerHTML =
        '<div class="chat-bubble-avatar">' +
        '<svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1a6 6 0 100 12A6 6 0 007 1z" stroke="currentColor" stroke-width="1"/></svg>' +
        '</div>' +
        '<div class="chat-typing"><span></span><span></span><span></span></div>';
    container.appendChild(typing);
    container.scrollTop = container.scrollHeight;
}

function hideTypingIndicator() {
    var el = document.getElementById('typing-indicator');
    if (el && el.parentNode) el.parentNode.removeChild(el);
}

/* ═══════════════════════════════════════════════════════════════════
   ACTIVITY FEED
   ═══════════════════════════════════════════════════════════════════ */

function addActivity(text, color) {
    var feed = document.getElementById('activity-feed');
    if (!feed) return;

    var item = document.createElement('div');
    item.className = 'activity-item';
    item.style.animation = 'slideUp 0.3s ease';
    item.innerHTML =
        '<div class="activity-dot dot-' + (color || 'blue') + '"></div>' +
        '<div class="activity-content">' +
        '<span class="activity-text">' + escapeHtml(text) + '</span>' +
        '<span class="activity-time">' + new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) + '</span>' +
        '</div>';

    // Insert at top
    if (feed.firstChild) {
        feed.insertBefore(item, feed.firstChild);
    } else {
        feed.appendChild(item);
    }

    // Keep max 20 items
    while (feed.children.length > 20) {
        feed.removeChild(feed.lastChild);
    }
}

/* ═══════════════════════════════════════════════════════════════════
   FORMATTING UTILITIES
   ═══════════════════════════════════════════════════════════════════ */

function formatStatus(s) {
    var map = {
        new: 'New', processing: 'Processing', needs_review: 'Review',
        approved: 'Approved', submitted: 'Submitted', follow_up: 'Follow Up',
        draft: 'Draft', escalated: 'Escalated'
    };
    return map[s] || s || 'Unknown';
}

function formatLossType(t) {
    var map = {
        auto_collision: 'Auto - Collision', auto_comprehensive: 'Auto - Comprehensive',
        homeowners_property: 'Homeowners', homeowners_liability: 'Home Liability',
        commercial_property: 'Commercial Property', commercial_auto: 'Commercial Auto',
        farm_ranch: 'Farm/Ranch', workers_comp: 'Workers Comp',
        general_liability: 'General Liability', unknown: 'Unknown'
    };
    return map[t] || t || '';
}

function formatTime(iso) {
    if (!iso) return '';
    try {
        return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return '';
    }
}

function renderConfidence(score) {
    if (score === undefined || score === null) return '';
    var pct = Math.round((score || 0) * 100);
    var cls = pct >= 80 ? 'high' : pct >= 50 ? 'medium' : 'low';
    return '<span class="confidence confidence-' + cls + '">' + pct + '% confidence</span>';
}

/* ═══════════════════════════════════════════════════════════════════
   UI UTILITIES
   ═══════════════════════════════════════════════════════════════════ */

function showLoading(msg) {
    var el = document.getElementById('loading-overlay');
    updateLoadingText(msg);
    // Reset pipeline steps
    for (var i = 1; i <= 3; i++) {
        var step = document.getElementById('load-step-' + i);
        if (step) { step.classList.remove('active', 'done'); }
    }
    document.querySelectorAll('.pipeline-connector').forEach(function (c) { c.classList.remove('active'); });
    var step1 = document.getElementById('load-step-1');
    if (step1) step1.classList.add('active');

    if (el) el.style.display = 'flex';
}

function hideLoading() {
    var el = document.getElementById('loading-overlay');
    if (el) el.style.display = 'none';
}

function advanceLoadingStep(stepNum) {
    // Mark previous steps as done
    for (var i = 1; i < stepNum; i++) {
        var prev = document.getElementById('load-step-' + i);
        if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
    }
    // Mark connectors
    document.querySelectorAll('.pipeline-connector').forEach(function (c, idx) {
        if (idx < stepNum - 1) c.classList.add('active');
    });
    // Activate current step
    var curr = document.getElementById('load-step-' + stepNum);
    if (curr) curr.classList.add('active');
}

function updateLoadingText(msg) {
    var textEl = document.getElementById('loading-text');
    if (textEl) textEl.textContent = msg || 'Processing...';
}

function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    if (!container) return;

    var icon = '';
    if (type === 'success') icon = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8l3.5 3.5L13 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    else if (type === 'error') icon = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
    else if (type === 'warning') icon = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 4v5M8 11v.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.innerHTML = icon + escapeHtml(message);
    container.appendChild(toast);

    setTimeout(function () { toast.classList.add('show'); }, 10);

    setTimeout(function () {
        toast.classList.remove('show');
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300);
    }, 4000);
}

function showModal(title, content) {
    var titleEl = document.getElementById('modal-title');
    var bodyEl = document.getElementById('modal-body');
    var overlayEl = document.getElementById('modal-overlay');
    if (titleEl) titleEl.textContent = title;
    if (bodyEl) bodyEl.innerHTML = content;
    if (overlayEl) overlayEl.style.display = 'flex';
}

function closeModal() {
    var overlayEl = document.getElementById('modal-overlay');
    if (overlayEl) overlayEl.style.display = 'none';
}

function setTextContent(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
}

function escapeHtml(str) {
    if (!str) return '';
    var s = String(str);
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/* ═══════════════════════════════════════════════════════════════════
   WEBSOCKET — Real-time updates
   ═══════════════════════════════════════════════════════════════════ */

function connectWebSocket() {
    try {
        var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(protocol + '//' + window.location.host + '/ws/claims');

        ws.onopen = function () {
            console.log('WebSocket connected');
        };

        ws.onmessage = function (event) {
            try {
                var data = JSON.parse(event.data);
                if (data.type === 'ready_for_review' || data.type === 'claim_submitted') {
                    loadDashboard();
                }
                if (data.type === 'processing_update' && data.claim_id === currentClaimId) {
                    if (data.trace_step) {
                        appendTraceStep(data.trace_step);
                    }
                }
            } catch (e) {
                console.warn('WebSocket message parse error:', e.message);
            }
        };

        ws.onerror = function () {
            console.log('WebSocket error — will retry');
        };

        ws.onclose = function () {
            console.log('WebSocket closed — reconnecting in 5s');
            setTimeout(connectWebSocket, 5000);
        };
    } catch (e) {
        console.log('WebSocket not available');
    }
}

function appendTraceStep(step) {
    var container = document.getElementById('trace-steps');
    if (!container) return;

    var empty = container.querySelector('.trace-empty');
    if (empty) container.removeChild(empty);

    var statusClass = step.status || 'success';
    var icon = getTraceIcon(step.step_type, statusClass);
    var detailsHtml = '';
    if (step.details) {
        detailsHtml = '<div class="trace-details">' + formatTraceDetails(step.details) + '</div>';
    }
    var durationStr = step.duration_ms ? step.duration_ms + 'ms' : '';

    var div = document.createElement('div');
    div.className = 'trace-step trace-' + escapeHtml(statusClass);
    div.innerHTML =
        '<div class="trace-header">' +
        '<span class="trace-icon">' + icon + '</span>' +
        '<span class="trace-name">' + escapeHtml(step.name || '') + '</span>' +
        '<span class="trace-time">' + escapeHtml(durationStr) + '</span>' +
        '</div>' +
        detailsHtml;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

/* ═══════════════════════════════════════════════════════════════════
   KEYBOARD SHORTCUTS
   ═══════════════════════════════════════════════════════════════════ */

function handleKeyboardShortcuts(e) {
    if (e.key === 'Escape') {
        var modal = document.getElementById('modal-overlay');
        if (modal && modal.style.display !== 'none') {
            closeModal();
            return;
        }
        // Close chat if open
        var panel = document.getElementById('chat-panel');
        if (panel && panel.classList.contains('open')) {
            toggleChat();
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════
   INITIALIZATION
   ═══════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {
    loadDashboard();
    connectWebSocket();

    var chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') sendChatMessage();
        });
    }

    document.addEventListener('keydown', handleKeyboardShortcuts);
});
