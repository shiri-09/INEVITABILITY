/* ═══════════════════════════════════════════════════════════════════════════
   INEVITABILITY — Main Application Logic
   API communication, state management, view routing, and UI rendering
   ═══════════════════════════════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:8000/api';

// ── State ────────────────────────────────────────────────────────────────────
let state = {
    activeView: 'hero',
    analysisId: null,
    analysisData: null,
    collapseFrame: 0,
    collapseTimer: null,
};

// ── View Routing ─────────────────────────────────────────────────────────────
function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    const view = document.getElementById(`view-${viewName}`);
    if (view) view.classList.add('active');

    const link = document.querySelector(`.nav-link[data-view="${viewName}"]`);
    if (link) link.classList.add('active');

    state.activeView = viewName;
}

// Navigation click handlers
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        showView(link.dataset.view);
    });
});

// ── API Communication ────────────────────────────────────────────────────────
async function apiCall(endpoint, method = 'GET', body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, opts);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error('API call failed:', err);
        throw err;
    }
}

// ── Run Demo Scenario ────────────────────────────────────────────────────────
async function runDemoScenario(scenarioId) {
    showView('dashboard');
    const loading = document.getElementById('dashboard-loading');
    loading.style.display = 'flex';

    try {
        const data = await apiCall(`/demo/run/${scenarioId}`, 'POST', {
            scenario_id: scenarioId,
            algorithm: 'greedy',
            max_mcs_cardinality: 5,
        });

        state.analysisId = data.analysis_id;
        state.analysisData = data;

        renderDashboard(data);
    } catch (err) {
        console.error('Analysis failed:', err);
        // Show error state
        document.getElementById('score-grid').innerHTML = `
            <div class="score-card" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <div style="color: var(--accent-red); font-size: 1.2rem; margin-bottom: 8px;">⚠ API Connection Failed</div>
                <div style="color: var(--text-secondary);">Make sure the backend is running: <code>python -m uvicorn backend.api:app --port 8000</code></div>
            </div>
        `;
    } finally {
        loading.style.display = 'none';
    }
}

// ── Render Dashboard ─────────────────────────────────────────────────────────
function renderDashboard(data) {
    document.getElementById('dash-scenario-name').textContent = data.scenario_name || 'Analysis Results';
    document.getElementById('dash-computation-time').textContent = `Computed in ${data.computation_time_ms}ms`;

    renderScoreGrid(data.inevitability_results);
    renderGraph(data);
    renderTogglePanel(data);
    renderMCSGrid(data.mcs_results);
    renderTheaterGrid(data.theater_reports);
    renderEconomicPanel(data.economic_report);
    renderExplanations(data.explanations);
    renderFragility(data.fragility_profile);
    renderCollapseView(data.collapse_frames);
    renderOptimization(data.optimization_strategies);
    renderCertification(data.certification);
    renderForecast(data.forecast);
    renderCollisions(data.goal_collisions);
    renderAdversarial(data.adversarial_report);
    showToast('Analysis complete — all modules loaded', 'success');
}

// ── Score Cards ──────────────────────────────────────────────────────────────
function renderScoreGrid(results) {
    const grid = document.getElementById('score-grid');
    grid.innerHTML = results.map(r => {
        const status = r.is_inevitable ? 'inevitable' : r.score > 0.4 ? 'at-risk' : 'defended';
        const label = r.is_inevitable ? 'INEVITABLE' : r.score > 0.4 ? 'AT RISK' : 'DEFENDED';
        return `
            <div class="score-card ${status}">
                <div class="score-card-header">
                    <div class="score-name">${r.goal_name || 'Goal'}</div>
                    <div class="score-badge ${status}">${label}</div>
                </div>
                <div class="score-value ${status}">${(r.score * 100).toFixed(0)}%</div>
                <div class="score-bar">
                    <div class="score-bar-fill ${status}" style="width: ${r.score * 100}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

// ── Causal Graph (Canvas) ────────────────────────────────────────────────────
function renderGraph(data) {
    const canvas = document.getElementById('causal-graph-canvas');
    const ctx = canvas.getContext('2d');

    // Set canvas size
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = 500;

    const W = canvas.width;
    const H = canvas.height;

    // Get nodes and edges from SCM or raw data
    let nodes = [];
    let edges = [];

    if (data.case_study && data.case_study.attack_path) {
        // Use case study attack path for layout
        const attackPath = data.case_study.attack_path;
        nodes = attackPath.map((step, i) => ({
            id: `step_${i}`,
            x: 100 + (i * (W - 200) / Math.max(attackPath.length - 1, 1)),
            y: H / 2 + Math.sin(i * 0.8) * 80,
            label: step.technique || step.description,
            description: step.description,
            color: i === attackPath.length - 1 ? '#ff3355' : i === 0 ? '#00ff88' : '#00f0ff',
            radius: 22,
        }));

        for (let i = 0; i < nodes.length - 1; i++) {
            edges.push({ from: i, to: i + 1 });
        }
    } else {
        // Fallback: generate layout from graph data
        const graphNodes = data.inevitability_results?.length > 0 ? [] : [{
            id: 'empty', x: W / 2, y: H / 2, label: 'No graph data', color: '#555', radius: 30,
        }];
        nodes = graphNodes;
    }

    // Clear
    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, W, H);

    // Draw grid
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }
    for (let y = 0; y < H; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }

    // Draw edges with glow
    edges.forEach(e => {
        const from = nodes[e.from];
        const to = nodes[e.to];
        if (!from || !to) return;

        // Glow
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.15)';
        ctx.lineWidth = 6;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();

        // Main line
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.6)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();

        // Arrow
        const angle = Math.atan2(to.y - from.y, to.x - from.x);
        const arrowX = to.x - Math.cos(angle) * to.radius;
        const arrowY = to.y - Math.sin(angle) * to.radius;
        ctx.fillStyle = 'rgba(0, 240, 255, 0.8)';
        ctx.beginPath();
        ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(arrowX - 10 * Math.cos(angle - 0.4), arrowY - 10 * Math.sin(angle - 0.4));
        ctx.lineTo(arrowX - 10 * Math.cos(angle + 0.4), arrowY - 10 * Math.sin(angle + 0.4));
        ctx.closePath();
        ctx.fill();
    });

    // Draw nodes
    nodes.forEach(node => {
        // Glow
        const grad = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, node.radius * 2);
        grad.addColorStop(0, node.color + '40');
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * 2, 0, Math.PI * 2);
        ctx.fill();

        // Node body
        ctx.fillStyle = '#12121a';
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = node.color;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label
        ctx.fillStyle = '#e8e8ef';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        // Word wrap
        const words = node.label.split(' ');
        let line = '';
        let lineY = node.y + node.radius + 8;
        words.forEach(word => {
            const testLine = line + word + ' ';
            if (ctx.measureText(testLine).width > 120 && line) {
                ctx.fillText(line.trim(), node.x, lineY);
                line = word + ' ';
                lineY += 14;
            } else {
                line = testLine;
            }
        });
        ctx.fillText(line.trim(), node.x, lineY);
    });

    // Title overlay
    ctx.fillStyle = 'rgba(0, 240, 255, 0.5)';
    ctx.font = '12px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('CAUSAL ATTACK GRAPH', 20, 20);
}

// ── Toggle Panel ─────────────────────────────────────────────────────────────
function renderTogglePanel(data) {
    const panel = document.getElementById('toggle-panel');

    // Extract controls from theater reports
    const controls = [];
    const seen = new Set();

    if (data.theater_reports) {
        data.theater_reports.forEach(report => {
            report.classifications?.forEach(c => {
                if (!seen.has(c.control_id)) {
                    seen.add(c.control_id);
                    controls.push(c);
                }
            });
        });
    }

    if (controls.length === 0) {
        panel.innerHTML = '<div style="color: var(--text-muted); padding: 20px;">No controls found in analysis.</div>';
        return;
    }

    panel.innerHTML = controls.map(ctrl => {
        const isActive = ctrl.classification !== 'IRRELEVANT';
        return `
            <div class="toggle-item">
                <div class="toggle-info">
                    <div class="toggle-name">${ctrl.control_name}</div>
                    <div class="toggle-type">${ctrl.control_type || 'control'} · $${(ctrl.annual_cost || 0).toLocaleString()}/yr</div>
                </div>
                <label class="toggle-switch">
                    <input type="checkbox" ${isActive ? 'checked' : ''} onchange="handleToggle('${ctrl.control_id}', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        `;
    }).join('');
}

// Handle assumption toggle
async function handleToggle(controlId, value) {
    if (!state.analysisId) return;

    try {
        const result = await apiCall('/assumption/toggle', 'POST', {
            session_id: state.analysisId,
            control_id: controlId,
            new_value: value,
        });

        // Update score display
        if (result.toggle_results) {
            const updatedResults = Object.values(result.toggle_results).map(r => ({
                goal_name: r.goal,
                score: r.after,
                is_inevitable: r.is_inevitable_after,
            }));
            renderScoreGrid(updatedResults);

            // Flash effect
            document.querySelectorAll('.score-card').forEach(card => {
                card.style.transition = 'none';
                card.style.boxShadow = '0 0 30px rgba(0, 240, 255, 0.3)';
                setTimeout(() => {
                    card.style.transition = 'box-shadow 0.5s ease';
                    card.style.boxShadow = 'none';
                }, 50);
            });
        }
    } catch (err) {
        console.error('Toggle failed:', err);
    }
}

// ── MCS Grid ─────────────────────────────────────────────────────────────────
function renderMCSGrid(results) {
    const grid = document.getElementById('mcs-grid');
    grid.innerHTML = results.map(mcs => {
        const sets = mcs.mcs_sets || [];
        if (sets.length === 0) return '';

        const best = sets[0];
        return `
            <div class="mcs-card">
                <div class="mcs-card-header">
                    <div class="mcs-goal">${mcs.goal_name || 'Goal'}</div>
                    <div class="mcs-cardinality">|MCS| = ${best.cardinality}</div>
                </div>
                ${best.elements.map(el => `
                    <div class="mcs-element">
                        <span class="mcs-element-icon">✓</span>
                        <span>${el.control_name}</span>
                    </div>
                `).join('')}
                <div class="mcs-cost">
                    Total remediation cost: $${(best.total_cost || 0).toLocaleString()}/yr
                    ${best.validated ? ' · ✓ Verified' : ''}
                </div>
            </div>
        `;
    }).join('');
}

// ── Theater Grid ─────────────────────────────────────────────────────────────
function renderTheaterGrid(reports) {
    const grid = document.getElementById('theater-grid');
    const allClassifications = [];

    reports.forEach(report => {
        report.classifications?.forEach(c => allClassifications.push(c));
    });

    // Sort: irrelevant first (theater!), then by cost
    allClassifications.sort((a, b) => {
        const order = { 'IRRELEVANT': 0, 'PARTIAL': 1, 'NECESSARY': 2, 'CRITICAL': 3 };
        return (order[a.classification] || 0) - (order[b.classification] || 0) || (b.annual_cost || 0) - (a.annual_cost || 0);
    });

    grid.innerHTML = allClassifications.map(c => `
        <div class="theater-item">
            <div class="theater-classification ${c.classification?.toLowerCase()}">${c.classification}</div>
            <div class="theater-name">${c.control_name}</div>
            <div class="theater-cost">$${(c.annual_cost || 0).toLocaleString()}/yr</div>
            <div></div>
            <div class="theater-reason">${c.reason || ''}</div>
        </div>
    `).join('');
}

// ── Economic Panel ───────────────────────────────────────────────────────────
function renderEconomicPanel(report) {
    const panel = document.getElementById('economic-panel');
    if (!report) {
        panel.innerHTML = '<div style="color: var(--text-muted);">No economic data.</div>';
        return;
    }

    panel.innerHTML = `
        <div class="econ-card">
            <div class="econ-value total">$${(report.total_security_spend || 0).toLocaleString()}</div>
            <div class="econ-label">Total Annual Security Spend</div>
        </div>
        <div class="econ-card">
            <div class="econ-value effective">$${(report.effective_spend || 0).toLocaleString()}</div>
            <div class="econ-label">Causally Effective Spend</div>
        </div>
        <div class="econ-card">
            <div class="econ-value waste">$${(report.wasted_spend || 0).toLocaleString()}</div>
            <div class="econ-label">Security Theater Waste</div>
        </div>
        <div class="econ-card">
            <div class="econ-value" style="color: var(--accent-yellow);">${((report.waste_ratio || 0) * 100).toFixed(1)}%</div>
            <div class="econ-label">Waste Ratio</div>
        </div>
    `;
}

// ── Explanations ─────────────────────────────────────────────────────────────
function renderExplanations(explanations) {
    const panel = document.getElementById('explanation-panel');
    if (!explanations || explanations.length === 0) {
        panel.innerHTML = '<div style="color: var(--text-muted);">No explanations generated.</div>';
        return;
    }

    panel.innerHTML = explanations.map(exp => {
        const statusClass = exp.inevitability_score > 0.7 ? 'inevitable' : 'defended';
        return `
            <div class="explanation-card">
                <div class="explanation-finding ${statusClass}">${exp.finding || ''}</div>
                ${(exp.causal_chain || []).map(step => `
                    <div class="explanation-step">${step.step_number}. ${step.statement}</div>
                `).join('')}
                ${exp.mcs_explanation ? `<div class="explanation-mcs">${exp.mcs_explanation}</div>` : ''}
                ${(exp.theater_summary || []).map(t => `<div class="explanation-theater">${t}</div>`).join('')}
            </div>
        `;
    }).join('');
}

// ── Fragility ────────────────────────────────────────────────────────────────
function renderFragility(profile) {
    const panel = document.getElementById('fragility-panel');
    if (!profile) {
        panel.innerHTML = '<div style="color: var(--text-muted);">No fragility data.</div>';
        return;
    }

    panel.innerHTML = `
        <div class="fragility-grade ${profile.grade || 'C'}">${profile.grade || '?'}</div>
        <div class="fragility-details">
            <div class="fragility-stat">
                <div class="fragility-stat-label">Architectural Fragility Index</div>
                <div class="fragility-stat-value">${(profile.afi || 0).toFixed(3)}</div>
            </div>
            <div class="fragility-stat">
                <div class="fragility-stat-label">Single Points of Failure</div>
                <div class="fragility-stat-value" style="color: ${profile.spof_count > 0 ? 'var(--accent-red)' : 'var(--accent-green)'};">${profile.spof_count || 0}</div>
            </div>
            <div class="fragility-stat">
                <div class="fragility-stat-label">High-Collapse Controls</div>
                <div class="fragility-stat-value">${profile.high_collapse_controls || 0}</div>
            </div>
            <div class="fragility-stat">
                <div class="fragility-stat-label">Structural Brittleness</div>
                <div class="fragility-stat-value">${(profile.structural_brittleness || 0).toFixed(3)}</div>
            </div>
        </div>
    `;
}

// ── Collapse Simulation ──────────────────────────────────────────────────────
function renderCollapseView(frames) {
    if (!frames || frames.length === 0) return;

    const timeline = document.getElementById('collapse-timeline');
    timeline.innerHTML = frames.map((frame, i) => `
        <div class="timeline-step ${i === 0 ? 'active' : ''}" onclick="showCollapseFrame(${i})" data-frame="${i}">
            <div class="timeline-dot"></div>
            <div class="timeline-label">${frame.label || `Step ${frame.step}`}</div>
            <div class="timeline-detail">${frame.control_disabled ? `Disable: ${frame.control_disabled}` : 'Baseline'}</div>
        </div>
    `).join('');

    showCollapseFrame(0);
}

function showCollapseFrame(index) {
    const frames = state.analysisData?.collapse_frames;
    if (!frames || !frames[index]) return;

    state.collapseFrame = index;
    const frame = frames[index];

    // Update frame info
    document.getElementById('collapse-frame-info').innerHTML = `
        <div class="frame-label">Step ${frame.step} — ${frame.label || ''}</div>
        <div class="frame-narration">${frame.narration || ''}</div>
    `;

    // Update score cards
    const scores = document.getElementById('collapse-scores');
    if (frame.goal_states) {
        scores.innerHTML = Object.values(frame.goal_states).map(g => `
            <div class="collapse-score-card ${g.status}">
                <div style="font-weight: 700; margin-bottom: 4px;">${g.name}</div>
                <div style="font-family: var(--font-mono); font-size: 1.8rem; font-weight: 700;">${(g.score * 100).toFixed(0)}%</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase;">${g.status}</div>
                ${g.newly_inevitable ? '<div style="color: var(--accent-red); font-weight: 700; margin-top: 4px;">⚠ NEWLY INEVITABLE</div>' : ''}
            </div>
        `).join('');
    }

    // Highlight active timeline step
    document.querySelectorAll('.timeline-step').forEach(s => {
        s.classList.remove('active', 'doom');
        if (parseInt(s.dataset.frame) === index) {
            s.classList.add('active');
        }
        if (parseInt(s.dataset.frame) <= index && parseInt(s.dataset.frame) > 0) {
            s.classList.add('doom');
        }
    });
}

function playCollapse() {
    const frames = state.analysisData?.collapse_frames;
    if (!frames) return;

    if (state.collapseTimer) {
        clearInterval(state.collapseTimer);
        state.collapseTimer = null;
        document.getElementById('collapse-play-btn').textContent = '▶ Play Simulation';
        return;
    }

    state.collapseFrame = 0;
    showCollapseFrame(0);
    document.getElementById('collapse-play-btn').textContent = '⏸ Pause';

    state.collapseTimer = setInterval(() => {
        state.collapseFrame++;
        if (state.collapseFrame >= frames.length) {
            clearInterval(state.collapseTimer);
            state.collapseTimer = null;
            document.getElementById('collapse-play-btn').textContent = '▶ Play Simulation';
            return;
        }
        showCollapseFrame(state.collapseFrame);
    }, 1500);
}

function resetCollapse() {
    if (state.collapseTimer) {
        clearInterval(state.collapseTimer);
        state.collapseTimer = null;
    }
    state.collapseFrame = 0;
    showCollapseFrame(0);
    document.getElementById('collapse-play-btn').textContent = '▶ Play Simulation';
}

// ── Utility ──────────────────────────────────────────────────────────────────
function formatDollars(n) {
    if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
    return `$${n}`;
}

// ── Toast Notifications ──────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-icon">${type === 'success' ? '✓' : type === 'danger' ? '✕' : 'ℹ'}</span> ${message}`;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ── Optimization Strategies ──────────────────────────────────────────────────
function renderOptimization(strategies) {
    const panel = document.getElementById('optimization-panel');
    if (!strategies || strategies.length === 0) {
        panel.innerHTML = '<div style="color: var(--text-muted); padding: 20px;">No optimization strategies computed.</div>';
        return;
    }

    panel.innerHTML = strategies.map(s => `
        <div class="opt-strategy ${s.recommended ? 'recommended' : ''}">
            <div class="opt-rank">#${s.rank}</div>
            <div class="opt-name">${s.controls.join(' + ')}</div>
            <div class="opt-description">${s.description}</div>
            <div class="opt-metrics">
                <div>
                    <div class="opt-metric-value cost">${formatDollars(s.total_cost)}/yr</div>
                    <div class="opt-metric-label">ANNUAL COST</div>
                </div>
                <div>
                    <div class="opt-metric-value reduction">${(s.total_reduction * 100).toFixed(0)}%</div>
                    <div class="opt-metric-label">RISK REDUCTION</div>
                </div>
                <div>
                    <div class="opt-metric-value roi">${s.roi_score.toFixed(1)}</div>
                    <div class="opt-metric-label">ROI SCORE</div>
                </div>
            </div>
        </div>
    `).join('');
}

// ── Certification Report ─────────────────────────────────────────────────────
function renderCertification(cert) {
    const panel = document.getElementById('certification-panel');
    if (!cert) {
        panel.innerHTML = '<div style="color: var(--text-muted); padding: 20px;">No certification data.</div>';
        return;
    }

    const gradeColor = cert.grade <= 'B' ? 'var(--accent-green)' : cert.grade === 'C' ? 'var(--accent-yellow)' : 'var(--accent-red)';

    panel.innerHTML = `
        <div class="cert-panel">
            <div class="cert-header">
                <div>
                    <div style="font-weight: 700; font-size: 1.1rem; margin-bottom: 4px;">Security Posture Certification</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">${cert.certification_id} · ${cert.timestamp}</div>
                </div>
                <div class="cert-badge-icon" style="border-color: ${gradeColor}; color: ${gradeColor};">${cert.grade}</div>
            </div>

            <div class="cert-stat">
                <span class="cert-stat-label">Posture Score</span>
                <span class="cert-stat-value" style="color: ${gradeColor};">${cert.posture_score}/100</span>
            </div>
            <div class="cert-stat">
                <span class="cert-stat-label">Goals Analyzed</span>
                <span class="cert-stat-value">${cert.goals_analyzed}</span>
            </div>
            <div class="cert-stat">
                <span class="cert-stat-label">Goals Defended</span>
                <span class="cert-stat-value" style="color: var(--accent-green);">${cert.goals_defended}</span>
            </div>
            <div class="cert-stat">
                <span class="cert-stat-label">Goals Inevitable</span>
                <span class="cert-stat-value" style="color: ${cert.goals_inevitable > 0 ? 'var(--accent-red)' : 'var(--accent-green)'};">${cert.goals_inevitable}</span>
            </div>
            <div class="cert-stat">
                <span class="cert-stat-label">Active Controls</span>
                <span class="cert-stat-value">${cert.active_controls} / ${cert.total_controls}</span>
            </div>
            <div class="cert-stat">
                <span class="cert-stat-label">Methodology</span>
                <span class="cert-stat-value">${cert.methodology}</span>
            </div>

            ${cert.findings?.map(f => `
                <div style="margin-top: 12px; padding: 10px 14px; border-radius: 8px;
                    background: ${f.severity === 'CRITICAL' ? 'var(--accent-red-dim)' : f.severity === 'HIGH' ? 'rgba(255, 200, 0, 0.05)' : 'rgba(255,255,255,0.02)'};
                    border: 1px solid ${f.severity === 'CRITICAL' ? 'rgba(255,51,85,0.2)' : f.severity === 'HIGH' ? 'rgba(255,200,0,0.15)' : 'var(--border)'};
                    font-size: 0.82rem;">
                    <div style="font-weight: 600; color: ${f.severity === 'CRITICAL' ? 'var(--accent-red)' : f.severity === 'HIGH' ? 'var(--accent-yellow)' : 'var(--accent-green)'};
                        margin-bottom: 4px;">${f.severity}: ${f.finding}</div>
                    <div style="color: var(--text-secondary);">${f.recommendation}</div>
                </div>
            `).join('') || ''}

            <button class="cert-export-btn" onclick="exportCertification()">📄 Export Certification Report</button>
        </div>
    `;
}

function exportCertification() {
    if (!state.analysisData?.certification) return;
    const cert = state.analysisData.certification;
    const blob = new Blob([JSON.stringify(cert, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${cert.certification_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Certification exported', 'success');
}

// ── Failure Forecast ─────────────────────────────────────────────────────────
function renderForecast(forecast) {
    const panel = document.getElementById('forecast-panel');
    if (!forecast || !forecast.goal_forecasts) {
        panel.innerHTML = '<div style="color: var(--text-muted); padding: 20px;">No forecast data.</div>';
        return;
    }

    panel.innerHTML = `
        <div class="forecast-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <div style="font-weight: 700; font-size: 1rem;">Inevitability Drift Projection</div>
                <div style="font-family: var(--font-mono); font-size: 0.75rem; padding: 3px 10px;
                    border-radius: 4px; color: ${forecast.overall_risk === 'CRITICAL' ? 'var(--accent-red)' : forecast.overall_risk === 'HIGH' ? 'var(--accent-yellow)' : 'var(--accent-green)'};
                    border: 1px solid; opacity: 0.8;">${forecast.overall_risk} RISK</div>
            </div>

            <div class="forecast-chart">
                <div class="forecast-threshold" style="top: 30%;"></div>
                ${forecast.goal_forecasts.map((gf, idx) => {
        const color = idx === 0 ? '#ff3355' : idx === 1 ? '#00f0ff' : '#aa55ff';
        const points = gf.projections.map((p, i) => {
            const x = (i / (gf.projections.length - 1)) * 100;
            const y = 100 - (p.projected_score * 100);
            return `${x}%,${y}%`;
        });
        // Create SVG polyline
        return '';
    }).join('')}
                <svg width="100%" height="100%" style="position: absolute; inset: 0;" preserveAspectRatio="none" viewBox="0 0 100 100">
                    ${forecast.goal_forecasts.map((gf, idx) => {
        const color = idx === 0 ? '#ff3355' : idx === 1 ? '#00f0ff' : '#aa55ff';
        const points = gf.projections.map((p, i) => {
            const x = (i / Math.max(gf.projections.length - 1, 1)) * 100;
            const y = 100 - (p.projected_score * 100);
            return `${x},${y}`;
        }).join(' ');
        return `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="0.8" vector-effect="non-scaling-stroke"/>`;
    }).join('')}
                </svg>
            </div>

            ${forecast.goal_forecasts.map(gf => `
                <div class="forecast-stat">
                    <span>${gf.goal_name}</span>
                    <span class="forecast-stat-value ${gf.risk_trajectory === 'ACCELERATING' ? 'danger' : gf.risk_trajectory === 'DRIFTING' ? 'warning' : 'safe'}">
                        ${(gf.current_score * 100).toFixed(0)}% → ${(gf.projections[gf.projections.length - 1]?.projected_score * 100 || 0).toFixed(0)}% (${forecast.forecast_horizon_months}mo)
                    </span>
                </div>
                ${gf.crossing_month !== null ? `
                    <div class="forecast-stat">
                        <span style="color: var(--accent-red);">⚠ Crosses inevitable threshold</span>
                        <span class="forecast-stat-value danger">Month ${gf.crossing_month}</span>
                    </div>
                ` : ''}
            `).join('')}

            <div style="margin-top: 12px; font-size: 0.82rem; color: var(--text-secondary);">
                ${forecast.recommendation}
            </div>
        </div>
    `;
}

// ── Goal Collision Analysis ──────────────────────────────────────────────────
function renderCollisions(collisions) {
    const panel = document.getElementById('collision-panel');
    if (!collisions || collisions.length === 0) {
        panel.innerHTML = '<div style="color: var(--text-muted); padding: 20px;">Single-goal scenario — no collision analysis applicable.</div>';
        return;
    }

    panel.innerHTML = collisions.map(c => `
        <div class="collision-card">
            <div>
                <div class="collision-type ${c.collision_type.toLowerCase()}">${c.collision_type}</div>
            </div>
            <div>
                <div style="font-weight: 600; margin-bottom: 4px;">${c.goal_1.name} ↔ ${c.goal_2.name}</div>
                <div style="font-size: 0.82rem; color: var(--text-secondary);">${c.description}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px;">
                    Shared controls: ${c.shared_control_count} · Unique: ${c.unique_to_goal_1} / ${c.unique_to_goal_2}
                </div>
            </div>
            <div style="text-align: right; font-family: var(--font-mono); font-size: 0.85rem;">
                <div style="color: var(--accent-red);">${(c.goal_1.score * 100).toFixed(0)}%</div>
                <div style="color: var(--accent-cyan);">${(c.goal_2.score * 100).toFixed(0)}%</div>
            </div>
        </div>
    `).join('');
}

// ── Adversarial Testing ──────────────────────────────────────────────────────
function renderAdversarial(report) {
    const panel = document.getElementById('adversarial-panel');
    if (!report || !report.attack_vectors) {
        panel.innerHTML = '<div style="color: var(--text-muted); padding: 20px;">No adversarial test data.</div>';
        return;
    }

    panel.innerHTML = `
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); padding: var(--space-xl);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <div style="font-weight: 700; font-size: 1rem;">Red Team Simulation</div>
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted);">
                    ${report.total_controls_tested} controls tested · ${report.critical_vectors} critical vectors
                </div>
            </div>

            ${report.recommendation ? `
                <div style="padding: 10px 14px; border-radius: 8px; margin-bottom: 16px;
                    background: ${report.critical_vectors > 0 ? 'var(--accent-red-dim)' : 'rgba(0,255,136,0.05)'};
                    border: 1px solid ${report.critical_vectors > 0 ? 'rgba(255,51,85,0.2)' : 'rgba(0,255,136,0.15)'};
                    font-size: 0.82rem; color: var(--text-secondary);">
                    ${report.recommendation}
                </div>
            ` : ''}

            ${report.attack_vectors.slice(0, 5).map((v, i) => `
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px;">
                    <div style="font-family: var(--font-mono); font-size: 1.2rem; font-weight: 700; opacity: 0.3; min-width: 30px;">${i + 1}</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 0.9rem;">${v.control_to_bypass}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Bypassing this control causes ${(v.max_impact * 100).toFixed(0)}% increase in inevitability</div>
                    </div>
                    <div style="font-family: var(--font-mono); font-size: 0.65rem; letter-spacing: 1px; padding: 3px 8px;
                        border-radius: 4px; font-weight: 700;
                        background: ${v.severity === 'CRITICAL' ? 'var(--accent-red-dim)' : v.severity === 'HIGH' ? 'rgba(255,200,0,0.05)' : 'rgba(255,255,255,0.03)'};
                        color: ${v.severity === 'CRITICAL' ? 'var(--accent-red)' : v.severity === 'HIGH' ? 'var(--accent-yellow)' : 'var(--text-muted)'};
                        border: 1px solid ${v.severity === 'CRITICAL' ? 'rgba(255,51,85,0.2)' : v.severity === 'HIGH' ? 'rgba(255,200,0,0.15)' : 'var(--border)'};
                    ">${v.severity}</div>
                </div>
            `).join('')}
        </div>
    `;
}
