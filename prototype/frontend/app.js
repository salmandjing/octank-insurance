/* ═══════════════════════════════════════════════════════════════════
   ClaimFlow AI — Frontend Application
   Nebraska Insurance FNOL Automation
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

/* ═══════════════════════════════════════════════════════════════════
   DASHBOARD
   ═══════════════════════════════════════════════════════════════════ */

async function loadDashboard() {
    try {
        var res = await fetch(API_BASE + '/api/claims');
        var data = await res.json();
        claimsData = data.claims || [];
        renderClaimsQueue();
        updateStats();
    } catch (e) {
        console.warn('Could not load claims:', e.message);
        claimsData = [];
        renderClaimsQueue();
        updateStats();
    }
}

function renderClaimsQueue() {
    var tbody = document.getElementById('claims-queue-body');
    if (!tbody) return;

    if (!claimsData.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No claims yet. Use a demo scenario to get started.</td></tr>';
        return;
    }

    tbody.innerHTML = claimsData.map(function (c) {
        var statusHtml = '<span class="status-badge status-' + escapeHtml(c.status || '') + '">' + formatStatus(c.status) + '</span>';
        var priorityHtml = '<span class="priority-badge priority-' + escapeHtml(c.priority || 'normal') + '">' + escapeHtml(c.priority || 'normal') + '</span>';
        var confidenceHtml = renderConfidence(c.confidence);
        var timeStr = formatTime(c.created_at);
        var fromStr = escapeHtml(c.email_from || 'N/A');
        var subjectStr = escapeHtml(c.email_subject || 'N/A');
        var lossStr = formatLossType(c.loss_type);

        return '<tr onclick="openClaim(\'' + escapeHtml(c.claim_id) + '\')" class="claim-row">' +
            '<td>' + statusHtml + '</td>' +
            '<td>' + fromStr + '</td>' +
            '<td>' + subjectStr + '</td>' +
            '<td>' + priorityHtml + '</td>' +
            '<td>' + escapeHtml(lossStr) + '</td>' +
            '<td>' + confidenceHtml + '</td>' +
            '<td>' + escapeHtml(timeStr) + '</td>' +
            '</tr>';
    }).join('');
}

function updateStats() {
    var todayEl = document.getElementById('stat-today');
    var pendingEl = document.getElementById('stat-pending');
    var submittedEl = document.getElementById('stat-submitted');
    var avgTimeEl = document.getElementById('stat-avg-time');

    if (todayEl) todayEl.textContent = claimsData.length;
    if (pendingEl) {
        pendingEl.textContent = claimsData.filter(function (c) {
            return c.status === 'needs_review';
        }).length;
    }
    if (submittedEl) {
        submittedEl.textContent = claimsData.filter(function (c) {
            return c.status === 'submitted';
        }).length;
    }
    if (avgTimeEl) {
        if (claimsData.length > 0) {
            var totalMs = claimsData.reduce(function (sum, c) {
                return sum + (c.processing_time_ms || 0);
            }, 0);
            var avgMs = totalMs / claimsData.length;
            if (avgMs > 0) {
                avgTimeEl.textContent = (avgMs / 1000).toFixed(1) + 's';
            } else {
                avgTimeEl.textContent = '--';
            }
        } else {
            avgTimeEl.textContent = '--';
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════
   DEMO SCENARIOS
   ═══════════════════════════════════════════════════════════════════ */

async function runScenario(name) {
    showLoading('Processing email...');
    try {
        var res = await fetch(API_BASE + '/api/demo/scenario/' + encodeURIComponent(name), {
            method: 'POST'
        });
        var data = await res.json();
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
        showToast('Error loading claim', 'error');
    } finally {
        hideLoading();
    }
}

function renderClaimProcessing(claim) {
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

    // Dropdowns
    var lossType = document.getElementById('field-loss_type');
    if (lossType) lossType.value = ext.loss_type || 'unknown';

    // Checkboxes
    var injuries = document.getElementById('field-injuries');
    if (injuries) injuries.checked = ext.injuries || false;

    var policeReport = document.getElementById('field-police_report');
    if (policeReport) policeReport.checked = ext.police_report || false;

    // Other parties
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
            if (pct >= 80) {
                dot.classList.add('dot-high');
            } else if (pct >= 50) {
                dot.classList.add('dot-medium');
            } else {
                dot.classList.add('dot-low');
            }
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
            missingEl.innerHTML = '<div class="missing-warning">Missing: ' + escapeHtml(missing.join(', ')) + '</div>';
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

    container.innerHTML = steps.map(function (step) {
        var statusClass = step.status || 'success';
        var statusIcon;
        if (step.status === 'success') {
            statusIcon = '&#10003;';
        } else if (step.status === 'error') {
            statusIcon = '&#10007;';
        } else {
            statusIcon = '&#9888;';
        }

        var detailsHtml = '';
        if (step.details) {
            detailsHtml = '<div class="trace-details">' + formatTraceDetails(step.details) + '</div>';
        }

        var durationStr = step.duration_ms ? step.duration_ms + 'ms' : '';

        return '<div class="trace-step trace-' + escapeHtml(statusClass) + '">' +
            '<div class="trace-header">' +
            '<span class="trace-icon">' + statusIcon + '</span>' +
            '<span class="trace-name">' + escapeHtml(step.name || '') + '</span>' +
            '<span class="trace-time">' + escapeHtml(durationStr) + '</span>' +
            '</div>' +
            detailsHtml +
            '</div>';
    }).join('');
}

function formatTraceDetails(details) {
    return Object.entries(details).map(function (entry) {
        var k = entry[0];
        var v = entry[1];
        var val = (typeof v === 'object') ? JSON.stringify(v) : String(v);
        return '<span class="trace-detail"><strong>' + escapeHtml(k) + ':</strong> ' + escapeHtml(val) + '</span>';
    }).join(' ');
}

/* ═══════════════════════════════════════════════════════════════════
   APPROVE & GENERATE SUBMISSION
   ═══════════════════════════════════════════════════════════════════ */

async function approveClaim() {
    if (!currentClaimId) return;
    showLoading('Generating carrier submission and client email...');

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

    // Reset success state
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
   FOLLOW-UP EMAIL
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
                '<hr>' +
                '<pre style="white-space:pre-wrap;font-family:inherit;">' + escapeHtml(data.followup_email) + '</pre>'
            );
        } else {
            showToast('No follow-up email generated.', 'warning');
        }
    } catch (e) {
        showToast('Error generating follow-up', 'error');
    } finally {
        hideLoading();
    }
}

/* ═══════════════════════════════════════════════════════════════════
   SAVE DRAFT & ESCALATE
   ═══════════════════════════════════════════════════════════════════ */

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
        showToast('Draft saved.', 'success');
    } catch (e) {
        showToast('Error saving draft: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

async function escalateClaim() {
    if (!currentClaimId) return;
    if (!confirm('Escalate this claim to a senior adjuster? This action cannot be undone.')) return;
    showLoading('Escalating claim...');
    try {
        var res = await fetch(API_BASE + '/api/claims/' + encodeURIComponent(currentClaimId) + '/escalate', {
            method: 'POST'
        });
        var data = await res.json();
        showToast(data.message || 'Claim escalated.', 'warning');
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

async function sendChatMessage() {
    var input = document.getElementById('chat-input');
    if (!input) return;
    var msg = input.value.trim();
    if (!msg) return;

    addChatBubble(msg, 'user');
    input.value = '';

    if (!chatSessionId) {
        await initChatSession();
    }

    if (!chatSessionId) {
        addChatBubble('Sorry, I could not connect to the server. Please try again.', 'assistant');
        return;
    }

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
        addChatBubble(data.response || 'No response received.', 'assistant');
    } catch (e) {
        addChatBubble('Sorry, I encountered an error. Please try again.', 'assistant');
    }
}

function addChatBubble(text, role) {
    var container = document.getElementById('chat-messages');
    if (!container) return;
    var bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-' + role;
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

/* ═══════════════════════════════════════════════════════════════════
   FORMATTING UTILITIES
   ═══════════════════════════════════════════════════════════════════ */

function formatStatus(s) {
    var map = {
        new: 'New',
        processing: 'Processing',
        needs_review: 'Needs Review',
        approved: 'Approved',
        submitted: 'Submitted',
        follow_up: 'Follow Up',
        draft: 'Draft'
    };
    return map[s] || s || 'Unknown';
}

function formatLossType(t) {
    var map = {
        auto_collision: 'Auto - Collision',
        auto_comprehensive: 'Auto - Comprehensive',
        homeowners_property: 'Homeowners',
        homeowners_liability: 'Home Liability',
        commercial_property: 'Commercial Property',
        commercial_auto: 'Commercial Auto',
        farm_ranch: 'Farm/Ranch',
        workers_comp: 'Workers Comp',
        general_liability: 'General Liability',
        unknown: 'Unknown'
    };
    return map[t] || t || '';
}

function formatTime(iso) {
    if (!iso) return '';
    try {
        return new Date(iso).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return '';
    }
}

function renderConfidence(score) {
    if (score === undefined || score === null) return '';
    var pct = Math.round((score || 0) * 100);
    var cls;
    if (pct >= 80) {
        cls = 'high';
    } else if (pct >= 50) {
        cls = 'medium';
    } else {
        cls = 'low';
    }
    return '<span class="confidence confidence-' + cls + '">' + pct + '%</span>';
}

/* ═══════════════════════════════════════════════════════════════════
   UI UTILITIES
   ═══════════════════════════════════════════════════════════════════ */

function showLoading(msg) {
    var el = document.getElementById('loading-overlay');
    var textEl = document.getElementById('loading-text');
    if (textEl) textEl.textContent = msg || 'Processing...';
    if (el) el.style.display = 'flex';
}

function hideLoading() {
    var el = document.getElementById('loading-overlay');
    if (el) el.style.display = 'none';
}

function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toast-container');
    if (!container) return;

    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = message;
    container.appendChild(toast);

    // Trigger the slide-in animation
    setTimeout(function () {
        toast.classList.add('show');
    }, 10);

    // Auto-dismiss
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
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/* ═══════════════════════════════════════════════════════════════════
   WEBSOCKET — Real-time claim updates
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
            console.log('WebSocket closed — reconnecting in 3s');
            setTimeout(connectWebSocket, 3000);
        };
    } catch (e) {
        console.log('WebSocket not available');
    }
}

function appendTraceStep(step) {
    var container = document.getElementById('trace-steps');
    if (!container) return;

    // Remove the "empty" placeholder if present
    var empty = container.querySelector('.trace-empty');
    if (empty) {
        container.removeChild(empty);
    }

    var statusClass = step.status || 'success';
    var statusIcon;
    if (step.status === 'success') {
        statusIcon = '&#10003;';
    } else if (step.status === 'error') {
        statusIcon = '&#10007;';
    } else {
        statusIcon = '&#9888;';
    }

    var detailsHtml = '';
    if (step.details) {
        detailsHtml = '<div class="trace-details">' + formatTraceDetails(step.details) + '</div>';
    }

    var durationStr = step.duration_ms ? step.duration_ms + 'ms' : '';

    var div = document.createElement('div');
    div.className = 'trace-step trace-' + escapeHtml(statusClass);
    div.innerHTML =
        '<div class="trace-header">' +
        '<span class="trace-icon">' + statusIcon + '</span>' +
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
    // Escape closes modal
    if (e.key === 'Escape') {
        var modal = document.getElementById('modal-overlay');
        if (modal && modal.style.display !== 'none') {
            closeModal();
            return;
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════
   INITIALIZATION
   ═══════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {
    // Load dashboard data
    loadDashboard();

    // Connect WebSocket for real-time updates
    connectWebSocket();

    // Chat enter key handler
    var chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
});