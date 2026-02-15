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

// ── Custom Adversary Dropdown ────────────────────────────────────────────────
function toggleAdversaryDropdown() {
    const wrapper = document.getElementById('adversary-select-wrapper');
    wrapper.classList.toggle('open');
}

function selectAdversary(el) {
    const value = el.dataset.value;
    const name = el.querySelector('.option-name').textContent;
    document.getElementById('adversary-select').value = value;
    document.querySelector('.custom-select-value').textContent = name;
    document.querySelectorAll('.custom-select-option').forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    document.getElementById('adversary-select-wrapper').classList.remove('open');
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const wrapper = document.getElementById('adversary-select-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        wrapper.classList.remove('open');
    }
});

// ── View Routing ─────────────────────────────────────────────────────────────
function showView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    const view = document.getElementById(`view-${viewName}`);
    if (view) view.classList.add('active');

    const link = document.querySelector(`.nav-link[data-view="${viewName}"]`);
    if (link) link.classList.add('active');

    state.activeView = viewName;

    // Re-layout collapse graph when view becomes visible
    if (viewName === 'collapse' && state.analysisData?.graph) {
        setTimeout(() => {
            layoutCollapseGraph(state.analysisData.graph);
            if (state.analysisData.collapse_frames) {
                showCollapseFrame(state.collapseFrame || 0);
                startCollapseAnimation();
            }
        }, 50);
    }
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
            adversary_profile: document.getElementById('adversary-select')?.value || 'apt',
            run_monte_carlo: true,
            mc_simulations: 10000,
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
    document.getElementById('dash-computation-time').textContent = `v2.0 Engine — Computed in ${data.computation_time_ms}ms`;

    renderScoreGrid(data.inevitability_results, data.probabilistic_results);
    renderProbabilisticSummary(data.probabilistic_results);
    renderGraph(data);
    renderTogglePanel(data);
    renderMCSGrid(data.mcs_results);
    renderTheaterGrid(data.theater_reports);
    renderEconomicPanel(data.economic_report);
    renderExplanations(data.explanations);
    renderCollapseView(data.collapse_frames);
    renderCertification(data.certification);
    showToast('Analysis complete — structural + probabilistic engine loaded', 'success');
}

// ── Score Cards ──────────────────────────────────────────────────────────────
function renderScoreGrid(results, probResults) {
    const grid = document.getElementById('score-grid');
    const goalRisks = probResults?.goal_risks || [];
    const mcResults = probResults?.monte_carlo || [];

    grid.innerHTML = results.map((r, i) => {
        const status = r.is_inevitable ? 'inevitable' : r.score > 0.4 ? 'at-risk' : 'defended';
        const label = r.is_inevitable ? 'INEVITABLE' : r.score > 0.4 ? 'AT RISK' : 'DEFENDED';
        const probScore = r.probabilistic_score ?? goalRisks[i]?.probabilistic_score ?? null;
        const mc = mcResults[i] || null;
        const probDisplay = probScore !== null ? `${(probScore * 100).toFixed(1)}%` : '—';
        const mcDisplay = mc ? `${mc.probability_percent}%` : '';
        const ciDisplay = mc ? `[${(mc.confidence_interval.lower * 100).toFixed(1)}–${(mc.confidence_interval.upper * 100).toFixed(1)}%]` : '';

        return `
            <div class="score-card ${status}">
                <div class="score-card-header">
                    <div class="score-name">${r.goal_name || 'Goal'}</div>
                    <div class="score-badge ${status}">${label}</div>
                </div>
                <div class="score-value ${status}">${(r.score * 100).toFixed(0)}%</div>
                <div class="score-label" style="font-size:0.7rem;color:var(--text-secondary);margin-top:-4px">Structural Inevitability</div>
                <div class="score-bar">
                    <div class="score-bar-fill ${status}" style="width: ${r.score * 100}%"></div>
                </div>
                ${probScore !== null ? `
                    <div style="margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06)">
                        <div style="display:flex;justify-content:space-between;align-items:baseline">
                            <span style="font-size:0.7rem;color:var(--text-secondary)">Probabilistic Risk</span>
                            <span style="font-size:1.4rem;font-weight:700;color:${probScore > 0.5 ? 'var(--accent-red)' : probScore > 0.2 ? 'var(--accent-yellow)' : 'var(--accent-green)'}">${probDisplay}</span>
                        </div>
                        <div class="score-bar" style="margin-top:6px">
                            <div class="score-bar-fill" style="width:${probScore * 100}%;background:${probScore > 0.5 ? 'var(--accent-red)' : probScore > 0.2 ? 'var(--accent-yellow)' : 'var(--accent-green)'}"></div>
                        </div>
                        ${mcDisplay ? `<div style="font-size:0.65rem;color:var(--text-secondary);margin-top:4px">MC: ${mcDisplay} ${ciDisplay} (95% CI, n=${mc.simulations.toLocaleString()})</div>` : ''}
                    </div>
                ` : ''}
             </div>
        `;
    }).join('');
}

// ── v2.0: Probabilistic Summary Panel ────────────────────────────────────────
function renderProbabilisticSummary(probResults) {
    const container = document.getElementById('probabilistic-panel');
    if (!container || !probResults) return;

    const summary = probResults.summary || {};
    const profile = probResults.adversary_profile || {};
    const controlRankings = probResults.control_rankings || [];
    const nakedAssets = probResults.naked_critical_assets || [];

    let html = `
        <div class="section-title" style="margin-bottom:16px">
            <span style="color:var(--accent-purple)">⚡</span> Probabilistic Risk Engine v2.0
        </div>

        <!-- Adversary Profile -->
        <div class="panel-card" style="margin-bottom:16px;padding:16px;background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.2);border-radius:12px">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-weight:600;color:var(--accent-purple)">${profile.name || 'APT'}</div>
                    <div style="font-size:0.75rem;color:var(--text-secondary)">${profile.description || ''}</div>
                </div>
                <div style="font-size:0.8rem;color:var(--text-secondary)">Skill ×${profile.skill_multiplier || '1.0'}</div>
            </div>
        </div>

        <!-- Risk Summary -->
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px">
            <div class="panel-card" style="padding:12px;text-align:center;border-radius:10px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.15)">
                <div style="font-size:1.5rem;font-weight:800;color:var(--accent-red)">${(summary.max_risk * 100).toFixed(0)}%</div>
                <div style="font-size:0.65rem;color:var(--text-secondary)">Max Risk</div>
            </div>
            <div class="panel-card" style="padding:12px;text-align:center;border-radius:10px;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.15)">
                <div style="font-size:1.5rem;font-weight:800;color:var(--accent-yellow)">${(summary.avg_risk * 100).toFixed(0)}%</div>
                <div style="font-size:0.65rem;color:var(--text-secondary)">Avg Risk</div>
            </div>
            <div class="panel-card" style="padding:12px;text-align:center;border-radius:10px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.15)">
                <div style="font-size:1.5rem;font-weight:800;color:var(--accent-green)">${summary.critical_controls || 0}</div>
                <div style="font-size:0.65rem;color:var(--text-secondary)">Critical Controls</div>
            </div>
            <div class="panel-card" style="padding:12px;text-align:center;border-radius:10px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.15)">
                <div style="font-size:1.5rem;font-weight:800;color:${nakedAssets.length > 0 ? 'var(--accent-red)' : 'var(--accent-green)'}">${nakedAssets.length}</div>
                <div style="font-size:0.65rem;color:var(--text-secondary)">Naked Assets</div>
            </div>
        </div>
    `;

    // Naked Assets Warning
    if (nakedAssets.length > 0) {
        html += `
            <div style="margin-top:16px;padding:12px 16px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:10px">
                <div style="font-weight:600;color:var(--accent-red);margin-bottom:6px">⚠ Unprotected Critical Assets</div>
                ${nakedAssets.map(a => `<div style="font-size:0.8rem;color:var(--text-secondary);padding:2px 0">• ${a.asset_name} (${a.criticality})</div>`).join('')}
            </div>
        `;
    }

    container.innerHTML = html;
}

// ── Causal Graph (Interactive Canvas with Pan/Zoom/Drag) ─────────────────────
let causalGraphState = {
    nodes: [],
    edges: [],
    canvas: null,
    ctx: null,
    // Camera transform
    offsetX: 0,
    offsetY: 0,
    scale: 1,
    // Interaction state
    isPanning: false,
    isDraggingNode: false,
    dragNodeIndex: -1,
    lastMouseX: 0,
    lastMouseY: 0,
    hoveredNode: -1,
    initialized: false,
};

function renderGraph(data) {
    const canvas = document.getElementById('causal-graph-canvas');
    const ctx = canvas.getContext('2d');

    // Set canvas size (use 2x for retina)
    const containerW = canvas.parentElement.clientWidth;
    const containerH = 500;
    canvas.width = containerW;
    canvas.height = containerH;

    const W = canvas.width;
    const H = canvas.height;

    // Get nodes and edges from case study, graph data, or fallback
    let nodes = [];
    let edges = [];

    if (data.case_study && data.case_study.attack_path) {
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
        const gNodes = data.graph.nodes;
        const gEdges = data.graph.edges || [];
        const typeColors = {
            identity: '#00ff88', asset: '#00f0ff', control: '#ffcc00',
            channel: '#aa55ff', privilege: '#ff8844',
        };
        const idToIdx = {};
        gNodes.forEach((n, i) => { idToIdx[n.id] = i; });

        const children = gNodes.map(() => []);
        const parentCount = new Array(gNodes.length).fill(0);
        gEdges.forEach(e => {
            if (e.edge_type === 'control') return;
            const si = idToIdx[e.source], ti = idToIdx[e.target];
            if (si !== undefined && ti !== undefined) {
                children[si].push(ti);
                parentCount[ti]++;
            }
        });

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

        const maxLayer = Math.max(...layer, 0);
        const layerGroups = {};
        gNodes.forEach((n, i) => {
            const l = layer[i];
            if (!layerGroups[l]) layerGroups[l] = [];
            layerGroups[l].push(i);
        });

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
                id: n.id, x, y,
                label: n.name || n.id, color,
                radius: isCritical ? 26 : n.type === 'identity' ? 24 : 20,
                nodeType: n.type,
            });
        });

        gEdges.forEach(e => {
            const fromIdx = idToIdx[e.source];
            const toIdx = idToIdx[e.target];
            if (fromIdx !== undefined && toIdx !== undefined) {
                edges.push({
                    from: fromIdx, to: toIdx,
                    label: e.label || '',
                    isControl: e.edge_type === 'control',
                });
            }
        });
    } else {
        nodes = [{ id: 'empty', x: W / 2, y: H / 2, label: 'No graph data', color: '#555', radius: 30 }];
    }

    // Store in state for interactive redraw
    causalGraphState.nodes = nodes;
    causalGraphState.edges = edges;
    causalGraphState.canvas = canvas;
    causalGraphState.ctx = ctx;
    causalGraphState.offsetX = 0;
    causalGraphState.offsetY = 0;
    causalGraphState.scale = 1;
    causalGraphState.hoveredNode = -1;

    // Attach event listeners only once
    if (!causalGraphState.initialized) {
        causalGraphState.initialized = true;
        setupGraphInteraction(canvas);
    }

    drawCausalGraph();
}

// ── Draw the graph using current camera transform ────────────────────────────
function drawCausalGraph() {
    const { nodes, edges, canvas, ctx, offsetX, offsetY, scale, hoveredNode } = causalGraphState;
    if (!canvas || !ctx) return;

    const W = canvas.width;
    const H = canvas.height;

    // Clear
    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, W, H);

    // Draw grid (fixed, no transform)
    ctx.strokeStyle = 'rgba(0, 240, 255, 0.04)';
    ctx.lineWidth = 1;
    const gridSpacing = 40 * scale;
    const gridOffX = offsetX % gridSpacing;
    const gridOffY = offsetY % gridSpacing;
    for (let x = gridOffX; x < W; x += gridSpacing) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }
    for (let y = gridOffY; y < H; y += gridSpacing) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }

    // Apply camera transform
    ctx.save();
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);

    // Draw edges with glow
    edges.forEach(e => {
        const from = nodes[e.from];
        const to = nodes[e.to];
        if (!from || !to) return;

        const isControl = e.isControl;
        const edgeColor = isControl ? 'rgba(255, 204, 0, 0.6)' : 'rgba(0, 240, 255, 0.6)';
        const glowColor = isControl ? 'rgba(255, 204, 0, 0.12)' : 'rgba(0, 240, 255, 0.15)';

        ctx.strokeStyle = glowColor;
        ctx.lineWidth = 6 / scale;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();

        ctx.strokeStyle = edgeColor;
        ctx.lineWidth = 2 / scale;
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
            ctx.font = `${9 / scale}px Inter, sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(e.label, midX, midY);
        }
    });

    // Draw nodes
    nodes.forEach((node, idx) => {
        const isHovered = idx === hoveredNode;

        // Glow
        const grad = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, node.radius * 2);
        grad.addColorStop(0, node.color + (isHovered ? '70' : '40'));
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * (isHovered ? 2.5 : 2), 0, Math.PI * 2);
        ctx.fill();

        // Node body
        ctx.fillStyle = isHovered ? '#1a1a2a' : '#12121a';
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = node.color;
        ctx.lineWidth = isHovered ? 3 / scale : 2 / scale;
        ctx.stroke();

        // Label
        ctx.fillStyle = '#e8e8ef';
        ctx.font = `${11 / scale}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

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

    ctx.restore();

    // Title overlay (fixed position, not affected by transform)
    ctx.fillStyle = 'rgba(0, 240, 255, 0.5)';
    ctx.font = '12px JetBrains Mono, monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText('CAUSAL ATTACK GRAPH', 20, 20);

    // Zoom indicator (fixed position)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.25)';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'top';
    ctx.fillText(`${Math.round(scale * 100)}%`, W - 20, 20);

    // Interaction hint (fixed position, subtle)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    ctx.fillText('Scroll to zoom · Drag to pan · Drag nodes to move', W - 20, H - 12);
}

// ── Mouse / Touch interaction for graph ──────────────────────────────────────
function setupGraphInteraction(canvas) {
    // Convert screen coordinates to graph coordinates
    function screenToGraph(sx, sy) {
        return {
            x: (sx - causalGraphState.offsetX) / causalGraphState.scale,
            y: (sy - causalGraphState.offsetY) / causalGraphState.scale,
        };
    }

    // Find node under cursor
    function hitTestNode(gx, gy) {
        const { nodes } = causalGraphState;
        for (let i = nodes.length - 1; i >= 0; i--) {
            const n = nodes[i];
            const dx = gx - n.x;
            const dy = gy - n.y;
            if (dx * dx + dy * dy <= (n.radius + 8) * (n.radius + 8)) {
                return i;
            }
        }
        return -1;
    }

    function getCanvasPos(e) {
        const rect = canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
        };
    }

    // Mouse down — start pan or node drag
    canvas.addEventListener('mousedown', (e) => {
        const pos = getCanvasPos(e);
        const gp = screenToGraph(pos.x, pos.y);
        const hitNode = hitTestNode(gp.x, gp.y);

        causalGraphState.lastMouseX = pos.x;
        causalGraphState.lastMouseY = pos.y;

        if (hitNode >= 0) {
            causalGraphState.isDraggingNode = true;
            causalGraphState.dragNodeIndex = hitNode;
            canvas.style.cursor = 'grabbing';
        } else {
            causalGraphState.isPanning = true;
            canvas.style.cursor = 'grabbing';
        }
    });

    // Mouse move — pan or drag node or hover
    canvas.addEventListener('mousemove', (e) => {
        const pos = getCanvasPos(e);
        const dx = pos.x - causalGraphState.lastMouseX;
        const dy = pos.y - causalGraphState.lastMouseY;

        if (causalGraphState.isDraggingNode) {
            const node = causalGraphState.nodes[causalGraphState.dragNodeIndex];
            if (node) {
                node.x += dx / causalGraphState.scale;
                node.y += dy / causalGraphState.scale;
                drawCausalGraph();
            }
        } else if (causalGraphState.isPanning) {
            causalGraphState.offsetX += dx;
            causalGraphState.offsetY += dy;
            drawCausalGraph();
        } else {
            // Hover detection
            const gp = screenToGraph(pos.x, pos.y);
            const hitNode = hitTestNode(gp.x, gp.y);
            if (hitNode !== causalGraphState.hoveredNode) {
                causalGraphState.hoveredNode = hitNode;
                canvas.style.cursor = hitNode >= 0 ? 'grab' : 'default';
                drawCausalGraph();
            }
        }

        causalGraphState.lastMouseX = pos.x;
        causalGraphState.lastMouseY = pos.y;
    });

    // Mouse up — stop pan/drag
    canvas.addEventListener('mouseup', () => {
        causalGraphState.isPanning = false;
        causalGraphState.isDraggingNode = false;
        causalGraphState.dragNodeIndex = -1;
        canvas.style.cursor = causalGraphState.hoveredNode >= 0 ? 'grab' : 'default';
    });

    canvas.addEventListener('mouseleave', () => {
        causalGraphState.isPanning = false;
        causalGraphState.isDraggingNode = false;
        causalGraphState.dragNodeIndex = -1;
        if (causalGraphState.hoveredNode !== -1) {
            causalGraphState.hoveredNode = -1;
            drawCausalGraph();
        }
        canvas.style.cursor = 'default';
    });

    // Mouse wheel — zoom
    canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const pos = getCanvasPos(e);

        // Zoom factor
        const zoomSpeed = 0.1;
        const delta = e.deltaY > 0 ? -zoomSpeed : zoomSpeed;
        const newScale = Math.max(0.2, Math.min(5, causalGraphState.scale + delta));

        // Zoom toward cursor position
        const scaleChange = newScale / causalGraphState.scale;
        causalGraphState.offsetX = pos.x - (pos.x - causalGraphState.offsetX) * scaleChange;
        causalGraphState.offsetY = pos.y - (pos.y - causalGraphState.offsetY) * scaleChange;
        causalGraphState.scale = newScale;

        drawCausalGraph();
    }, { passive: false });
}

// ── Graph zoom controls (called from HTML buttons) ───────────────────────────
function graphZoomIn() {
    const canvas = causalGraphState.canvas;
    if (!canvas) return;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const newScale = Math.min(5, causalGraphState.scale + 0.2);
    const scaleChange = newScale / causalGraphState.scale;
    causalGraphState.offsetX = cx - (cx - causalGraphState.offsetX) * scaleChange;
    causalGraphState.offsetY = cy - (cy - causalGraphState.offsetY) * scaleChange;
    causalGraphState.scale = newScale;
    drawCausalGraph();
}

function graphZoomOut() {
    const canvas = causalGraphState.canvas;
    if (!canvas) return;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const newScale = Math.max(0.2, causalGraphState.scale - 0.2);
    const scaleChange = newScale / causalGraphState.scale;
    causalGraphState.offsetX = cx - (cx - causalGraphState.offsetX) * scaleChange;
    causalGraphState.offsetY = cy - (cy - causalGraphState.offsetY) * scaleChange;
    causalGraphState.scale = newScale;
    drawCausalGraph();
}

function graphResetView() {
    causalGraphState.offsetX = 0;
    causalGraphState.offsetY = 0;
    causalGraphState.scale = 1;
    drawCausalGraph();
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
                `).join('')
            }
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

    // Sort: necessary/critical first, then irrelevant (theater) last
    allClassifications.sort((a, b) => {
        const order = {
            'necessary': 0, 'critical': 1, 'partial': 2, 'irrelevant': 3,
            'NECESSARY': 0, 'CRITICAL': 1, 'PARTIAL': 2, 'IRRELEVANT': 3
        };
        return (order[a.classification] ?? 4) - (order[b.classification] ?? 4) || (b.annual_cost || 0) - (a.annual_cost || 0);
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
                `).join('')
            }
                ${exp.mcs_explanation ? `<div class="explanation-mcs">${exp.mcs_explanation}</div>` : ''}
                ${(exp.theater_summary || []).map(t => `<div class="explanation-theater">${t}</div>`).join('')}
            </div>
        `;
    }).join('');
}


// ── Collapse Simulation (Canvas Graph) ───────────────────────────────────────
let collapseGraphState = {
    nodes: [],
    edges: [],
    nodePositions: {},
    animFrame: null,
    pulsePhase: 0,
    transitioning: false,
    prevNodeStates: null,
    transitionProgress: 0,
    targetNodeStates: null,
};

function layoutCollapseGraph(graphData) {
    const canvas = document.getElementById('collapse-graph-canvas');
    if (!canvas) return;
    const container = canvas.parentElement;
    canvas.width = container.clientWidth * 2;
    canvas.height = container.clientHeight * 2;

    const nodes = graphData.nodes || [];
    const edges = graphData.edges || [];
    collapseGraphState.nodes = nodes;
    collapseGraphState.edges = edges;

    // Categorize nodes
    const identities = nodes.filter(n => n.type === 'identity');
    const assets = nodes.filter(n => n.type === 'asset' || n.type === 'privilege');
    const controls = nodes.filter(n => n.type === 'control');

    const W = canvas.width;
    const H = canvas.height;
    const padX = 160, padY = 100;

    // Layout: identities left column, assets center, controls right
    const positions = {};
    const colX = [padX, W * 0.38, W * 0.62, W - padX];

    // Identities — left
    identities.forEach((n, i) => {
        const spacing = (H - padY * 2) / Math.max(identities.length - 1, 1);
        positions[n.id] = { x: colX[0], y: padY + i * spacing };
    });

    // Assets/Privileges — center columns, staggered
    assets.forEach((n, i) => {
        const spacing = (H - padY * 2) / Math.max(assets.length - 1, 1);
        const colIdx = i % 2 === 0 ? 1 : 2;
        positions[n.id] = { x: colX[colIdx], y: padY + i * spacing };
    });

    // Controls — right
    controls.forEach((n, i) => {
        const spacing = (H - padY * 2) / Math.max(controls.length - 1, 1);
        positions[n.id] = { x: colX[3], y: padY + i * spacing };
    });

    // Position any orphan nodes
    nodes.forEach((n, i) => {
        if (!positions[n.id]) {
            positions[n.id] = { x: W / 2, y: padY + i * 50 };
        }
    });

    collapseGraphState.nodePositions = positions;
}

function renderCollapseView(frames) {
    if (!frames || frames.length === 0) return;

    const graphData = state.analysisData?.graph;
    if (!graphData) return;

    layoutCollapseGraph(graphData);

    // Build timeline
    const timeline = document.getElementById('collapse-timeline');
    timeline.innerHTML = frames.map((frame, i) => `
        <div class="timeline-step ${i === 0 ? 'active' : ''}" onclick="showCollapseFrame(${i})" data-frame="${i}">
            <div class="timeline-dot"></div>
            <div class="timeline-label">${frame.label || 'Step ' + frame.step}</div>
            <div class="timeline-detail">${frame.control_disabled ? 'Disable: ' + frame.control_disabled : 'Baseline'}</div>
        </div>
    `).join('');

    showCollapseFrame(0);
    startCollapseAnimation();
}

function startCollapseAnimation() {
    if (collapseGraphState.animFrame) return;
    function loop() {
        collapseGraphState.pulsePhase += 0.03;
        if (collapseGraphState.transitioning) {
            collapseGraphState.transitionProgress = Math.min(1, collapseGraphState.transitionProgress + 0.04);
            if (collapseGraphState.transitionProgress >= 1) {
                collapseGraphState.transitioning = false;
                collapseGraphState.prevNodeStates = collapseGraphState.targetNodeStates;
            }
        }
        drawCollapseGraph();
        collapseGraphState.animFrame = requestAnimationFrame(loop);
    }
    loop();
}

function showCollapseFrame(index) {
    const frames = state.analysisData?.collapse_frames;
    if (!frames || !frames[index]) return;

    const prevFrame = state.collapseFrame;
    state.collapseFrame = index;
    const frame = frames[index];

    // For step 0 (baseline), force all nodes to "defended" state so the graph starts all-green
    let nodeStates = frame.node_states;
    if (index === 0 && nodeStates) {
        const allDefended = {};
        for (const [id, ns] of Object.entries(nodeStates)) {
            allDefended[id] = { ...ns, color: '#22c55e', score: 0, status: 'defended', pulse: false };
        }
        nodeStates = allDefended;
    }

    // Animate transition
    if (collapseGraphState.prevNodeStates && index !== prevFrame) {
        collapseGraphState.transitioning = true;
        collapseGraphState.transitionProgress = 0;
        collapseGraphState.targetNodeStates = nodeStates;
    } else {
        collapseGraphState.prevNodeStates = nodeStates;
        collapseGraphState.targetNodeStates = nodeStates;
    }

    // Update frame info
    document.getElementById('collapse-frame-info').innerHTML = `
        <div class="frame-label">Step ${frame.step} — ${frame.label || ''}</div>
        <div class="frame-narration">${frame.narration || ''}</div>
    `;

    // Update score cards
    const scores = document.getElementById('collapse-scores');
    if (frame.goal_states) {
        let goalStates = Object.values(frame.goal_states);
        // Override step 0 to show all goals at 0% / defended
        if (index === 0) {
            goalStates = goalStates.map(g => ({ ...g, score: 0, status: 'defended', newly_inevitable: false }));
        }
        scores.innerHTML = goalStates.map(g => `
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

function drawCollapseGraph() {
    const canvas = document.getElementById('collapse-graph-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    const { nodes, edges, nodePositions, pulsePhase, transitioning, transitionProgress, prevNodeStates, targetNodeStates } = collapseGraphState;

    if (!prevNodeStates || !targetNodeStates) return;

    ctx.clearRect(0, 0, W, H);

    // Get interpolated node state
    function getNodeState(nodeId) {
        const target = targetNodeStates[nodeId] || {};
        if (!transitioning || !prevNodeStates[nodeId]) return target;
        const prev = prevNodeStates[nodeId];
        const t = transitionProgress;
        return {
            ...target,
            score: prev.score + (target.score - prev.score) * t,
            color: target.color,
            pulse: target.pulse,
            status: t > 0.5 ? target.status : prev.status,
        };
    }

    // Draw edges
    edges.forEach(edge => {
        const from = nodePositions[edge.source];
        const to = nodePositions[edge.target];
        if (!from || !to) return;

        const sourceState = getNodeState(edge.source);
        const targetState = getNodeState(edge.target);

        // Edge color based on states
        let edgeColor, edgeAlpha;
        if (sourceState.status === 'inevitable' || sourceState.status === 'compromised') {
            edgeColor = '#ef4444';
            edgeAlpha = 0.6 + Math.sin(pulsePhase * 2) * 0.2;
        } else if (sourceState.status === 'disabled') {
            edgeColor = '#4b5563';
            edgeAlpha = 0.2;
        } else {
            edgeColor = '#1e90ff';
            edgeAlpha = 0.25;
        }

        ctx.save();
        ctx.globalAlpha = edgeAlpha;
        ctx.strokeStyle = edgeColor;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();

        // Arrow head
        const angle = Math.atan2(to.y - from.y, to.x - from.x);
        const arrowLen = 16;
        const arrowX = to.x - Math.cos(angle) * 30;
        const arrowY = to.y - Math.sin(angle) * 30;
        ctx.fillStyle = edgeColor;
        ctx.beginPath();
        ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(arrowX - arrowLen * Math.cos(angle - 0.4), arrowY - arrowLen * Math.sin(angle - 0.4));
        ctx.lineTo(arrowX - arrowLen * Math.cos(angle + 0.4), arrowY - arrowLen * Math.sin(angle + 0.4));
        ctx.closePath();
        ctx.fill();
        ctx.restore();
    });

    // Draw nodes
    nodes.forEach(node => {
        const pos = nodePositions[node.id];
        if (!pos) return;
        const ns = getNodeState(node.id);
        const radius = node.type === 'control' ? 22 : node.type === 'identity' ? 24 : 26;

        // Glow for inevitable/compromised nodes
        if (ns.pulse) {
            const glowSize = 12 + Math.sin(pulsePhase * 2) * 6;
            const gradient = ctx.createRadialGradient(pos.x, pos.y, radius, pos.x, pos.y, radius + glowSize);
            gradient.addColorStop(0, 'rgba(239, 68, 68, 0.4)');
            gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, radius + glowSize, 0, Math.PI * 2);
            ctx.fill();
        }

        // Node shape
        let fillColor, strokeColor;
        if (ns.status === 'inevitable' || ns.status === 'compromised') {
            fillColor = 'rgba(239, 68, 68, 0.2)';
            strokeColor = '#ef4444';
        } else if (ns.status === 'disabled') {
            fillColor = 'rgba(75, 85, 99, 0.2)';
            strokeColor = '#4b5563';
        } else {
            fillColor = 'rgba(34, 197, 94, 0.12)';
            strokeColor = '#22c55e';
        }

        ctx.fillStyle = fillColor;
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 2.5;

        if (node.type === 'control') {
            // Hexagon for controls
            ctx.beginPath();
            for (let i = 0; i < 6; i++) {
                const a = (Math.PI / 3) * i - Math.PI / 6;
                const px = pos.x + radius * Math.cos(a);
                const py = pos.y + radius * Math.sin(a);
                i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
            }
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
        } else if (node.type === 'identity') {
            // Diamond for identities
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y - radius);
            ctx.lineTo(pos.x + radius, pos.y);
            ctx.lineTo(pos.x, pos.y + radius);
            ctx.lineTo(pos.x - radius, pos.y);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
        } else {
            // Circle for assets
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
        }

        // Node icon
        ctx.fillStyle = strokeColor;
        ctx.font = '600 20px "Inter", sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const icon = node.type === 'control' ? '🛡' : node.type === 'identity' ? '👤' : '●';
        ctx.fillText(icon, pos.x, pos.y);

        // Label
        ctx.fillStyle = '#e5e7eb';
        ctx.font = '500 18px "Inter", sans-serif';
        ctx.textAlign = 'center';
        const name = node.name || node.id;
        const shortName = name.length > 20 ? name.slice(0, 18) + '…' : name;
        ctx.fillText(shortName, pos.x, pos.y + radius + 18);

        // Status badge
        if (ns.status === 'inevitable' || ns.status === 'compromised') {
            ctx.fillStyle = '#ef4444';
            ctx.font = 'bold 14px "JetBrains Mono", monospace';
            ctx.fillText(`${(ns.score * 100).toFixed(0)}%`, pos.x, pos.y + radius + 36);
        } else if (ns.status === 'disabled') {
            ctx.fillStyle = '#6b7280';
            ctx.font = 'bold 14px "JetBrains Mono", monospace';
            ctx.fillText('DISABLED', pos.x, pos.y + radius + 36);
        }
    });

    // Legend
    ctx.fillStyle = '#9ca3af';
    ctx.font = '500 16px "Inter", sans-serif';
    ctx.textAlign = 'left';
    const legendY = H - 40;
    // Defended
    ctx.fillStyle = '#22c55e';
    ctx.fillRect(20, legendY - 6, 12, 12);
    ctx.fillStyle = '#9ca3af';
    ctx.fillText('Defended', 38, legendY + 4);
    // Inevitable
    ctx.fillStyle = '#ef4444';
    ctx.fillRect(130, legendY - 6, 12, 12);
    ctx.fillStyle = '#9ca3af';
    ctx.fillText('Inevitable', 148, legendY + 4);
    // Disabled
    ctx.fillStyle = '#4b5563';
    ctx.fillRect(250, legendY - 6, 12, 12);
    ctx.fillStyle = '#9ca3af';
    ctx.fillText('Disabled', 268, legendY + 4);
    // Shapes
    ctx.fillText('◆ Identity   ● Asset   ⬡ Control', 380, legendY + 4);
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
    }, 2000);
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
    if (n >= 1000000) return `$${(n / 1000000).toFixed(1)} M`;
    if (n >= 1000) return `$${(n / 1000).toFixed(0)} K`;
    return `$${n} `;
}

// ── Toast Notifications ──────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type} `;
    toast.innerHTML = `<span class="toast-icon"> ${type === 'success' ? '✓' : type === 'danger' ? '✕' : 'ℹ'}</span> ${message} `;
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
            `).join('') || ''
        }

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

    document.getElementById(`tab - ${mode} `).classList.add('active');
    document.getElementById(`custom - mode - ${mode} `).classList.add('active');
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

