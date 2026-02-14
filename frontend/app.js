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
    renderCollapseView(data.collapse_frames);
    renderCertification(data.certification);
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

    // Get nodes and edges from case study, graph data, or fallback
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
    } else if (data.graph && data.graph.nodes && data.graph.nodes.length > 0) {
        // Build graph from API response nodes/edges
        const gNodes = data.graph.nodes;
        const gEdges = data.graph.edges || [];

        // Color by node type
        const typeColors = {
            identity: '#00ff88',
            asset: '#00f0ff',
            control: '#ffcc00',
            channel: '#aa55ff',
            privilege: '#ff8844',
        };

        // Compute topological layers for left-to-right layout
        const idToIdx = {};
        gNodes.forEach((n, i) => { idToIdx[n.id] = i; });

        // Build adjacency for non-control edges
        const children = gNodes.map(() => []);
        const parentCount = new Array(gNodes.length).fill(0);
        gEdges.forEach(e => {
            if (e.edge_type === 'control') return; // skip control edges for layout
            const si = idToIdx[e.source], ti = idToIdx[e.target];
            if (si !== undefined && ti !== undefined) {
                children[si].push(ti);
                parentCount[ti]++;
            }
        });

        // BFS layering
        const layer = new Array(gNodes.length).fill(0);
        const queue = [];
        for (let i = 0; i < gNodes.length; i++) {
            if (parentCount[i] === 0) queue.push(i);
        }
        while (queue.length > 0) {
            const cur = queue.shift();
            children[cur].forEach(c => {
                layer[c] = Math.max(layer[c], layer[cur] + 1);
                parentCount[c]--;
                if (parentCount[c] === 0) queue.push(c);
            });
        }

        // Group nodes by layer
        const maxLayer = Math.max(...layer, 0);
        const layerGroups = {};
        gNodes.forEach((n, i) => {
            const l = layer[i];
            if (!layerGroups[l]) layerGroups[l] = [];
            layerGroups[l].push(i);
        });

        // Position nodes in a layered layout
        const marginX = 120, marginY = 80;
        gNodes.forEach((n, i) => {
            const l = layer[i];
            const group = layerGroups[l];
            const posInGroup = group.indexOf(i);
            const groupSize = group.length;

            const x = marginX + (l / Math.max(maxLayer, 1)) * (W - 2 * marginX);
            const totalHeight = (groupSize - 1) * 100;
            const y = H / 2 - totalHeight / 2 + posInGroup * 100;

            const isCritical = n.criticality === 'critical';
            let color = typeColors[n.type] || '#00f0ff';
            if (n.type === 'asset' && isCritical) color = '#ff3355';

            nodes.push({
                id: n.id,
                x, y,
                label: n.name || n.id,
                color,
                radius: isCritical ? 26 : n.type === 'identity' ? 24 : 20,
                nodeType: n.type,
            });
        });

        // Build edges using node indices
        gEdges.forEach(e => {
            const fromIdx = idToIdx[e.source];
            const toIdx = idToIdx[e.target];
            if (fromIdx !== undefined && toIdx !== undefined) {
                edges.push({
                    from: fromIdx,
                    to: toIdx,
                    label: e.label || '',
                    isControl: e.edge_type === 'control',
                });
            }
        });
    } else {
        // No graph data at all
        nodes = [{
            id: 'empty', x: W / 2, y: H / 2, label: 'No graph data', color: '#555', radius: 30,
        }];
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

        const isControl = e.isControl;
        const edgeColor = isControl ? 'rgba(255, 204, 0, 0.6)' : 'rgba(0, 240, 255, 0.6)';
        const glowColor = isControl ? 'rgba(255, 204, 0, 0.12)' : 'rgba(0, 240, 255, 0.15)';

        // Glow
        ctx.strokeStyle = glowColor;
        ctx.lineWidth = 6;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();

        // Main line
        ctx.strokeStyle = edgeColor;
        ctx.lineWidth = 2;
        ctx.setLineDash(isControl ? [8, 6] : []);
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();
        ctx.setLineDash([]);

        // Arrow
        const angle = Math.atan2(to.y - from.y, to.x - from.x);
        const arrowX = to.x - Math.cos(angle) * to.radius;
        const arrowY = to.y - Math.sin(angle) * to.radius;
        ctx.fillStyle = isControl ? 'rgba(255, 204, 0, 0.8)' : 'rgba(0, 240, 255, 0.8)';
        ctx.beginPath();
        ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(arrowX - 10 * Math.cos(angle - 0.4), arrowY - 10 * Math.sin(angle - 0.4));
        ctx.lineTo(arrowX - 10 * Math.cos(angle + 0.4), arrowY - 10 * Math.sin(angle + 0.4));
        ctx.closePath();
        ctx.fill();

        // Edge label
        if (e.label) {
            const midX = (from.x + to.x) / 2;
            const midY = (from.y + to.y) / 2 - 8;
            ctx.fillStyle = 'rgba(255, 255, 255, 0.35)';
            ctx.font = '9px Inter, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(e.label, midX, midY);
        }
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

// ══════════════════════════════════════════════════════════════════════════════
// CUSTOM ANALYSIS — User Input Feature
// ══════════════════════════════════════════════════════════════════════════════

// ── Tab Switching ────────────────────────────────────────────────────────────
function switchCustomTab(mode) {
    document.querySelectorAll('.custom-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.custom-mode').forEach(m => m.classList.remove('active'));

    document.getElementById(`tab-${mode}`).classList.add('active');
    document.getElementById(`custom-mode-${mode}`).classList.add('active');
}

// ── Visual Builder Helpers ───────────────────────────────────────────────────
function addNodeRow() {
    const container = document.getElementById('node-builder-rows');
    const row = document.createElement('div');
    row.className = 'builder-row';
    row.dataset.rowType = 'node';
    row.innerHTML = `
        <input type="text" placeholder="Node ID" class="builder-input node-id">
        <select class="builder-select node-type">
            <option value="asset">Asset</option>
            <option value="identity">Identity</option>
            <option value="control">Control</option>
            <option value="privilege">Privilege</option>
            <option value="channel">Channel</option>
            <option value="trust_boundary">Trust Boundary</option>
        </select>
        <input type="text" placeholder="Display Name" class="builder-input node-name">
        <input type="number" placeholder="Cost ($/yr)" class="builder-input node-cost" style="width:110px;">
        <button class="builder-remove" onclick="this.closest('.builder-row').remove()">✕</button>
    `;
    container.appendChild(row);
    row.querySelector('.node-id').focus();
}

function addEdgeRow() {
    const container = document.getElementById('edge-builder-rows');
    const row = document.createElement('div');
    row.className = 'builder-row';
    row.dataset.rowType = 'edge';
    row.innerHTML = `
        <input type="text" placeholder="Source Node ID" class="builder-input edge-source">
        <span style="color:var(--accent-cyan); font-weight:700;">→</span>
        <input type="text" placeholder="Target Node ID" class="builder-input edge-target">
        <select class="builder-select edge-type">
            <option value="access">Access</option>
            <option value="control">Control</option>
            <option value="lateral">Lateral</option>
            <option value="privilege">Privilege</option>
            <option value="escalation">Escalation</option>
            <option value="trust">Trust</option>
            <option value="dependency">Dependency</option>
        </select>
        <input type="text" placeholder="Label" class="builder-input edge-label">
        <button class="builder-remove" onclick="this.closest('.builder-row').remove()">✕</button>
    `;
    container.appendChild(row);
    row.querySelector('.edge-source').focus();
}

function addGoalRow() {
    const container = document.getElementById('goal-builder-rows');
    const row = document.createElement('div');
    row.className = 'builder-row';
    row.dataset.rowType = 'goal';
    row.innerHTML = `
        <input type="text" placeholder="Goal Name" class="builder-input goal-name">
        <input type="text" placeholder="Target Asset IDs (comma-separated)" class="builder-input goal-targets" style="flex:2;">
        <button class="builder-remove" onclick="this.closest('.builder-row').remove()">✕</button>
    `;
    container.appendChild(row);
    row.querySelector('.goal-name').focus();
}

// ── Build JSON from Visual Forms ─────────────────────────────────────────────
function buildJsonFromForms() {
    const nodes = [];
    document.querySelectorAll('#node-builder-rows .builder-row').forEach(row => {
        const id = row.querySelector('.node-id')?.value?.trim();
        const type = row.querySelector('.node-type')?.value;
        const name = row.querySelector('.node-name')?.value?.trim();
        const cost = parseFloat(row.querySelector('.node-cost')?.value) || 0;
        if (!id) return;

        const node = { id, type, name: name || id };
        if (type === 'control') {
            node.control_state = 'active';
            if (cost > 0) node.annual_cost = cost;
        }
        nodes.push(node);
    });

    const edges = [];
    document.querySelectorAll('#edge-builder-rows .builder-row').forEach(row => {
        const source = row.querySelector('.edge-source')?.value?.trim();
        const target = row.querySelector('.edge-target')?.value?.trim();
        const edgeType = row.querySelector('.edge-type')?.value;
        const label = row.querySelector('.edge-label')?.value?.trim();
        if (!source || !target) return;
        edges.push({ source, target, edge_type: edgeType, label: label || '' });
    });

    const goals = [];
    document.querySelectorAll('#goal-builder-rows .builder-row').forEach(row => {
        const name = row.querySelector('.goal-name')?.value?.trim();
        const targetsStr = row.querySelector('.goal-targets')?.value?.trim();
        if (!name) return;
        const targetAssets = targetsStr ? targetsStr.split(',').map(s => s.trim()).filter(Boolean) : [];
        goals.push({ name, target_assets: targetAssets, required_conditions: targetAssets });
    });

    return { nodes, edges, goals };
}

// ── JSON File Upload ─────────────────────────────────────────────────────────
function handleJsonUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const parsed = JSON.parse(e.target.result);
            document.getElementById('custom-json-editor').value = JSON.stringify(parsed, null, 2);
            switchCustomTab('json');
            showToast('JSON file loaded successfully', 'success');
        } catch (err) {
            showToast('Invalid JSON file: ' + err.message, 'danger');
        }
    };
    reader.readAsText(file);
}

// ── Starter Templates ────────────────────────────────────────────────────────
const TEMPLATES = {
    simple_network: {
        nodes: [
            { id: "attacker", type: "identity", name: "External Attacker" },
            { id: "firewall", type: "control", name: "Firewall", control_state: "active", annual_cost: 50000 },
            { id: "web_server", type: "asset", name: "Web Server" },
            { id: "waf", type: "control", name: "Web App Firewall (WAF)", control_state: "inactive", annual_cost: 30000 },
            { id: "sqli_vuln", type: "channel", name: "SQL Injection Vulnerability" },
            { id: "database", type: "asset", name: "Production Database", criticality: "critical" }
        ],
        edges: [
            { source: "attacker", target: "web_server", edge_type: "access", label: "HTTP Access" },
            { source: "firewall", target: "web_server", edge_type: "control", label: "Blocks unauthorized traffic" },
            { source: "web_server", target: "database", edge_type: "lateral", label: "Legitimate SQL Connection" },
            { source: "attacker", target: "sqli_vuln", edge_type: "access", label: "Crafted HTTP payload" },
            { source: "waf", target: "sqli_vuln", edge_type: "control", label: "Blocks SQLi patterns" },
            { source: "sqli_vuln", target: "database", edge_type: "access", label: "Direct DB query via SQLi" }
        ],
        goals: [
            { name: "Database Exfiltration", target_assets: ["database"], required_conditions: ["database"] }
        ]
    },
    cloud_iam: {
        nodes: [
            { id: "attacker", type: "identity", name: "External Attacker" },
            { id: "phished_user", type: "identity", name: "Phished Employee" },
            { id: "mfa", type: "control", name: "Multi-Factor Authentication", control_state: "active", annual_cost: 25000 },
            { id: "ec2_instance", type: "asset", name: "EC2 Instance" },
            { id: "leaked_key", type: "channel", name: "Leaked API Key in GitHub" },
            { id: "secret_scanning", type: "control", name: "Secret Scanning", control_state: "inactive", annual_cost: 15000 },
            { id: "s3_bucket", type: "asset", name: "S3 Data Bucket", criticality: "critical" }
        ],
        edges: [
            { source: "attacker", target: "phished_user", edge_type: "access", label: "Spear phishing email" },
            { source: "mfa", target: "phished_user", edge_type: "control", label: "Requires second factor" },
            { source: "phished_user", target: "ec2_instance", edge_type: "privilege", label: "AssumeRole" },
            { source: "ec2_instance", target: "s3_bucket", edge_type: "lateral", label: "IMDS cred theft" },
            { source: "attacker", target: "leaked_key", edge_type: "access", label: "Found in public repo" },
            { source: "secret_scanning", target: "leaked_key", edge_type: "control", label: "Detects exposed keys" },
            { source: "leaked_key", target: "s3_bucket", edge_type: "access", label: "Direct S3 access with key" }
        ],
        goals: [
            { name: "S3 Data Exfiltration", target_assets: ["s3_bucket"], required_conditions: ["s3_bucket"] }
        ]
    },
    ad_escalation: {
        nodes: [
            { id: "attacker", type: "identity", name: "Compromised User" },
            { id: "workstation", type: "asset", name: "Corporate Workstation" },
            { id: "edr", type: "control", name: "EDR Agent", control_state: "active", annual_cost: 80000 },
            { id: "kerberoast", type: "channel", name: "Kerberoasting Attack" },
            { id: "strong_pw", type: "control", name: "Strong Service Acct Pwds", control_state: "inactive", annual_cost: 5000 },
            { id: "domain_admin", type: "privilege", name: "Domain Admin Credentials" },
            { id: "domain_controller", type: "asset", name: "Domain Controller", criticality: "critical" }
        ],
        edges: [
            { source: "attacker", target: "workstation", edge_type: "access", label: "Initial foothold" },
            { source: "edr", target: "workstation", edge_type: "control", label: "Behavior monitoring" },
            { source: "workstation", target: "domain_admin", edge_type: "escalation", label: "Credential dumping" },
            { source: "attacker", target: "kerberoast", edge_type: "access", label: "Request service tickets" },
            { source: "strong_pw", target: "kerberoast", edge_type: "control", label: "Prevents offline cracking" },
            { source: "kerberoast", target: "domain_admin", edge_type: "escalation", label: "Offline hash cracking" },
            { source: "domain_admin", target: "domain_controller", edge_type: "access", label: "Full domain control" }
        ],
        goals: [
            { name: "Domain Takeover", target_assets: ["domain_controller"], required_conditions: ["domain_controller"] }
        ]
    },
    supply_chain: {
        nodes: [
            { id: "attacker", type: "identity", name: "Nation-State Actor" },
            { id: "vendor", type: "asset", name: "Third-Party Vendor" },
            { id: "vendor_review", type: "control", name: "Vendor Security Review", control_state: "active", annual_cost: 35000 },
            { id: "oss_dep", type: "channel", name: "Compromised OSS Package" },
            { id: "sca_tool", type: "control", name: "SCA Tool", control_state: "inactive", annual_cost: 20000 },
            { id: "build_system", type: "asset", name: "CI/CD Pipeline" },
            { id: "prod_server", type: "asset", name: "Production Server", criticality: "critical" }
        ],
        edges: [
            { source: "attacker", target: "vendor", edge_type: "access", label: "Compromise vendor" },
            { source: "vendor_review", target: "vendor", edge_type: "control", label: "Reviews security posture" },
            { source: "vendor", target: "build_system", edge_type: "lateral", label: "Inject into build" },
            { source: "attacker", target: "oss_dep", edge_type: "access", label: "Typosquat npm package" },
            { source: "sca_tool", target: "oss_dep", edge_type: "control", label: "Flags malicious pkg" },
            { source: "oss_dep", target: "build_system", edge_type: "lateral", label: "Auto-pulled by CI" },
            { source: "build_system", target: "prod_server", edge_type: "lateral", label: "Auto-deploy to prod" }
        ],
        goals: [
            { name: "Production Compromise", target_assets: ["prod_server"], required_conditions: ["prod_server"] }
        ]
    },
};

function loadTemplate(templateName) {
    const template = TEMPLATES[templateName];
    if (!template) return;

    const json = JSON.stringify(template, null, 2);
    document.getElementById('custom-json-editor').value = json;
    switchCustomTab('json');
    showToast(`Template "${templateName.replace(/_/g, ' ')}" loaded`, 'success');
}

// ── Run Custom Analysis ──────────────────────────────────────────────────────
async function runCustomAnalysis() {
    const errorDiv = document.getElementById('custom-error');
    errorDiv.style.display = 'none';

    let payload;
    const activeTab = document.querySelector('.custom-tab.active')?.id;

    if (activeTab === 'tab-visual') {
        // Build from visual forms
        const formData = buildJsonFromForms();
        if (formData.nodes.length === 0) {
            errorDiv.textContent = '⚠ Add at least one node using the visual builder.';
            errorDiv.style.display = 'block';
            return;
        }
        if (formData.goals.length === 0) {
            errorDiv.textContent = '⚠ Add at least one goal.';
            errorDiv.style.display = 'block';
            return;
        }
        payload = formData;
    } else {
        // Parse from JSON editor
        const jsonText = document.getElementById('custom-json-editor').value.trim();
        if (!jsonText) {
            errorDiv.textContent = '⚠ Paste or type JSON in the editor, or use a template.';
            errorDiv.style.display = 'block';
            return;
        }
        try {
            payload = JSON.parse(jsonText);
        } catch (err) {
            errorDiv.textContent = `⚠ Invalid JSON: ${err.message}`;
            errorDiv.style.display = 'block';
            return;
        }
        if (!payload.nodes || !payload.goals) {
            errorDiv.textContent = '⚠ JSON must have "nodes" and "goals" arrays.';
            errorDiv.style.display = 'block';
            return;
        }
    }

    // Add scenario name
    payload.scenario_name = document.getElementById('custom-scenario-name').value || 'Custom Analysis';

    // Switch to dashboard and show loading
    showView('dashboard');
    const loading = document.getElementById('dashboard-loading');
    loading.style.display = 'flex';

    try {
        const data = await apiCall('/custom/run', 'POST', payload);

        state.analysisId = data.analysis_id;
        state.analysisData = data;

        renderDashboard(data);
        showToast('Custom analysis complete — all modules loaded', 'success');
    } catch (err) {
        console.error('Custom analysis failed:', err);
        showView('custom');
        errorDiv.textContent = `⚠ Analysis failed: ${err.message}`;
        errorDiv.style.display = 'block';
    } finally {
        loading.style.display = 'none';
    }
}

