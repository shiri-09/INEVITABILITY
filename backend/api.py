"""
INEVITABILITY - FastAPI REST API
API layer exposing the causal analysis engine to the frontend dashboard.
"""

from __future__ import annotations
import time
import pathlib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from .models import (
    AnalysisResult, GoalPredicate, BreachCaseStudy,
    CausalGraph, InfraNode, InfraEdge, GoalTemplate, NodeType,
)
from .scm_builder import SCMBuilder
from .solver_engine import CausalSolver
from .mcs_extractor import MCSExtractor
from .theater_detector import TheaterDetector
from .counterfactual import CounterfactualEngine
from .economic import EconomicAnalyzer
from .collapse import CollapseEngine
from .explainability import ExplainabilityEngine
from .breach_data import load_scenario, get_all_scenarios
from .advanced_features import (
    MultiGoalOptimizer, CertificationEngine, FailureForecaster,
    GoalCollisionAnalyzer, AdversarialTester,
)


# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="INEVITABILITY",
    description="Structural Reverse-Engineered Causal Goal Decompiler for Cybersecurity",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for active analysis sessions
_active_sessions: dict[str, dict] = {}


# ─── Request Models ──────────────────────────────────────────────────────────

class RunScenarioRequest(BaseModel):
    scenario_id: str
    algorithm: str = "greedy"  # greedy or exact
    max_mcs_cardinality: int = 5


class CustomAnalysisRequest(BaseModel):
    """Request model for user-submitted infrastructure graphs."""
    scenario_name: str = "Custom Analysis"
    nodes: list[dict]
    edges: list[dict]
    goals: list[dict]
    algorithm: str = "greedy"
    max_mcs_cardinality: int = 5


class CounterfactualRequest(BaseModel):
    session_id: str
    interventions: dict[str, bool]
    goal_id: Optional[str] = None


class ToggleAssumptionRequest(BaseModel):
    session_id: str
    control_id: str
    new_value: bool
    goal_id: Optional[str] = None


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "engine": "INEVITABILITY v1.0.0"}


# ─── Scenarios ────────────────────────────────────────────────────────────────

@app.get("/api/demo/scenarios")
async def list_scenarios():
    """List all available demo scenarios."""
    return get_all_scenarios()


# ─── Shared Analysis Pipeline ────────────────────────────────────────────────

def _run_analysis_pipeline(
    graph: CausalGraph,
    goals: list[GoalPredicate],
    scenario_name: str,
    organization: str = "Custom",
    algorithm: str = "greedy",
    max_mcs_cardinality: int = 5,
    case_study: BreachCaseStudy | None = None,
) -> dict:
    """Run the full analysis pipeline on a graph + goals. Shared by demo and custom endpoints."""
    start = time.perf_counter()

    # Build SCM
    builder = SCMBuilder(graph)
    scm = builder.build()

    # Create solver
    solver = CausalSolver(scm)

    # Create analysis engines
    mcs_extractor = MCSExtractor(solver, scm)
    theater = TheaterDetector(solver, scm)
    economic = EconomicAnalyzer()
    collapse_engine = CollapseEngine(solver, scm)
    explainer = ExplainabilityEngine(scm)
    optimizer = MultiGoalOptimizer(solver, scm)
    certifier = CertificationEngine(solver, scm)
    forecaster = FailureForecaster(solver, scm)
    collision_analyzer = GoalCollisionAnalyzer(solver, scm)
    adversarial = AdversarialTester(solver, scm)

    # Run analyses
    inevitability_results = []
    mcs_results = []
    theater_reports = []
    explanations = []
    proof_artifacts = []

    for goal in goals:
        inev = solver.compute_inevitability(goal)
        inevitability_results.append(inev)

        mcs = mcs_extractor.extract_mcs(goal, max_cardinality=max_mcs_cardinality, algorithm=algorithm)
        mcs_results.append(mcs)

        mcs_ids = set()
        for mcs_set in mcs.mcs_sets:
            for elem in mcs_set.elements:
                mcs_ids.add(elem.control_id)
        theater_report = theater.classify_controls(goal, mcs_ids)
        theater_reports.append(theater_report)

        explanation = explainer.generate_explanation(goal, inev, mcs, theater_report)
        explanations.append(explanation)

        for mcs_set in mcs.mcs_sets:
            proof = mcs_extractor.generate_mcs_proof(goal, mcs_set)
            proof_artifacts.append(proof)

    econ_report = economic.analyze(theater_reports)
    fragility = collapse_engine.compute_fragility(goals)
    collapse_frames = collapse_engine.simulate_collapse(goals)
    collapse_ranking = collapse_engine.compute_all_collapse_metrics(goals)
    optimization_strategies = optimizer.compute_optimal_strategies(goals)
    certification = certifier.generate_certification(goals, inevitability_results, organization)
    forecast = forecaster.forecast(goals, inevitability_results)
    goal_collisions = collision_analyzer.analyze_collisions(goals)
    adversarial_report = adversarial.run_adversarial_test(goals)

    elapsed = (time.perf_counter() - start) * 1000

    result = AnalysisResult(
        scenario_name=scenario_name,
        inevitability_results=inevitability_results,
        mcs_results=mcs_results,
        theater_reports=theater_reports,
        economic_report=econ_report,
        fragility_profile=fragility,
        collapse_frames=collapse_frames,
        explanations=explanations,
        proof_artifacts=proof_artifacts,
        collapse_ranking=collapse_ranking,
        scm=scm,
        computation_time_ms=round(elapsed, 2),
    )

    # Cache session for counterfactual queries
    _active_sessions[result.analysis_id] = {
        "scm": scm,
        "solver": solver,
        "goals": goals,
        "graph": graph,
        "case_study": case_study,
        "result": result,
    }

    response = {
        "analysis_id": result.analysis_id,
        "scenario_name": result.scenario_name,
        "computation_time_ms": result.computation_time_ms,
        "inevitability_results": [r.model_dump() for r in result.inevitability_results],
        "mcs_results": [r.model_dump() for r in result.mcs_results],
        "theater_reports": [r.model_dump() for r in result.theater_reports],
        "economic_report": result.economic_report.model_dump() if result.economic_report else None,
        "fragility_profile": result.fragility_profile.model_dump() if result.fragility_profile else None,
        "collapse_frames": [f.model_dump() for f in result.collapse_frames],
        "explanations": [e.model_dump() for e in result.explanations],
        "proof_artifacts": [p.model_dump() for p in result.proof_artifacts],
        "collapse_ranking": [c.model_dump() for c in result.collapse_ranking],
        "optimization_strategies": optimization_strategies,
        "certification": certification,
        "forecast": forecast,
        "goal_collisions": goal_collisions,
        "adversarial_report": adversarial_report,
        "graph": {
            "nodes": [n.model_dump() for n in graph.nodes],
            "edges": [e.model_dump() for e in graph.edges],
        },
    }

    if case_study:
        response["case_study"] = case_study.model_dump()

    return response


# ─── Run Demo Analysis ────────────────────────────────────────────────────────

@app.post("/api/demo/run/{scenario_id}")
async def run_scenario(scenario_id: str, request: RunScenarioRequest | None = None):
    """Run a complete analysis on a pre-built breach scenario."""
    try:
        graph, goals, case_study = load_scenario(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    algo = request.algorithm if request else "greedy"
    max_card = request.max_mcs_cardinality if request else 5

    return _run_analysis_pipeline(
        graph=graph,
        goals=goals,
        scenario_name=case_study.name,
        organization=case_study.organization,
        algorithm=algo,
        max_mcs_cardinality=max_card,
        case_study=case_study,
    )


# ─── Run Custom Analysis ─────────────────────────────────────────────────────

def _validate_custom_graph(nodes: list[dict], edges: list[dict], goals: list[dict]):
    """Validate user-submitted graph data."""
    if not nodes:
        raise HTTPException(status_code=400, detail="At least one node is required.")
    if not goals:
        raise HTTPException(status_code=400, detail="At least one goal is required.")

    node_ids = {n.get("id", n.get("name", "")) for n in nodes}

    # Validate edge references
    for i, edge in enumerate(edges):
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if src not in node_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Edge {i}: source '{src}' does not match any node ID.",
            )
        if tgt not in node_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Edge {i}: target '{tgt}' does not match any node ID.",
            )

    # Warn (but don't block) if no controls exist
    has_control = any(n.get("type") == "control" for n in nodes)
    if not has_control:
        # Still allow — the solver will just find everything inevitable
        pass


@app.post("/api/custom/run")
async def run_custom_analysis(request: CustomAnalysisRequest):
    """Run a complete analysis on a user-submitted infrastructure graph."""
    _validate_custom_graph(request.nodes, request.edges, request.goals)

    # Build typed model objects from raw dicts
    infra_nodes = []
    for n in request.nodes:
        # Use 'id' field if provided, otherwise auto-generate from 'name'
        if "id" not in n and "name" in n:
            n["id"] = n["name"].lower().replace(" ", "_")
        infra_nodes.append(InfraNode(**n))

    infra_edges = []
    for e in request.edges:
        infra_edges.append(InfraEdge(**e))

    graph = CausalGraph(nodes=infra_nodes, edges=infra_edges)

    goals = []
    for g in request.goals:
        goals.append(GoalPredicate(**g))

    return _run_analysis_pipeline(
        graph=graph,
        goals=goals,
        scenario_name=request.scenario_name,
        organization="Custom",
        algorithm=request.algorithm,
        max_mcs_cardinality=request.max_mcs_cardinality,
    )


# ─── Counterfactual ──────────────────────────────────────────────────────────

@app.post("/api/counterfactual")
async def run_counterfactual(request: CounterfactualRequest):
    """Run a counterfactual what-if analysis."""
    session = _active_sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session. Run an analysis first.")

    solver = session["solver"]
    goals = session["goals"]
    scm = session["scm"]
    cf_engine = CounterfactualEngine(solver, scm)

    results = {}
    target_goals = goals
    if request.goal_id:
        target_goals = [g for g in goals if g.id == request.goal_id]

    for goal in target_goals:
        result = cf_engine.what_if(goal, request.interventions)
        results[goal.id] = result

    return {"counterfactual_results": results}


# ─── Assumption Toggle ───────────────────────────────────────────────────────

@app.post("/api/assumption/toggle")
async def toggle_assumption(request: ToggleAssumptionRequest):
    """Toggle a control/assumption and get updated inevitability scores."""
    session = _active_sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session. Run an analysis first.")

    solver = session["solver"]
    goals = session["goals"]
    scm = session["scm"]
    cf_engine = CounterfactualEngine(solver, scm)

    results = {}
    target_goals = goals
    if request.goal_id:
        target_goals = [g for g in goals if g.id == request.goal_id]

    for goal in target_goals:
        result = cf_engine.what_if(goal, {request.control_id: request.new_value})
        results[goal.id] = result

    return {"toggle_results": results, "control_toggled": request.control_id, "new_value": request.new_value}


# ─── Breach Case Studies ─────────────────────────────────────────────────────

@app.get("/api/breach/{breach_id}")
async def get_breach(breach_id: str):
    """Get a historical breach case study."""
    try:
        graph, goals, case_study = load_scenario(breach_id)
        return case_study.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Collapse Simulation ─────────────────────────────────────────────────────

@app.get("/api/collapse/simulate/{session_id}")
async def get_collapse_simulation(session_id: str):
    """Get collapse simulation frames for an active session."""
    session = _active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session.")

    result = session["result"]
    return {
        "frames": [f.model_dump() for f in result.collapse_frames],
        "total_frames": len(result.collapse_frames),
        "fragility": result.fragility_profile.model_dump() if result.fragility_profile else None,
    }


# ─── Graph Data ──────────────────────────────────────────────────────────────

@app.get("/api/graph/{session_id}")
async def get_graph_data(session_id: str):
    """Get the causal graph data for visualization."""
    session = _active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session.")

    scm = session["scm"]
    return {
        "nodes": [n.model_dump() for n in scm.graph.nodes],
        "edges": [e.model_dump() for e in scm.graph.edges],
        "assumptions": [a.model_dump() for a in scm.assumptions],
    }


# ─── Advanced Feature Endpoints ────────────────────────────────────────────────

@app.get("/api/advanced/optimize/{session_id}")
async def get_optimization(session_id: str):
    """Get Pareto-optimal defense strategies."""
    session = _active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session.")
    solver = session["solver"]
    scm = session["scm"]
    goals = session["goals"]
    optimizer = MultiGoalOptimizer(solver, scm)
    return {"strategies": optimizer.compute_optimal_strategies(goals)}


@app.get("/api/advanced/certify/{session_id}")
async def get_certification(session_id: str):
    """Generate formal certification report."""
    session = _active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session.")
    solver = session["solver"]
    scm = session["scm"]
    goals = session["goals"]
    result = session["result"]
    case_study = session["case_study"]
    certifier = CertificationEngine(solver, scm)
    return certifier.generate_certification(goals, result.inevitability_results, case_study.organization)


@app.get("/api/advanced/forecast/{session_id}")
async def get_forecast(session_id: str):
    """Get failure forecasting projections."""
    session = _active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session.")
    solver = session["solver"]
    scm = session["scm"]
    goals = session["goals"]
    result = session["result"]
    forecaster = FailureForecaster(solver, scm)
    return forecaster.forecast(goals, result.inevitability_results)


# ─── Static File Serving ─────────────────────────────────────────────────────

_frontend_dir = pathlib.Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
async def serve_root():
    return FileResponse(_frontend_dir / "index.html")


# Mount static files (CSS, JS, etc.) — MUST be after all API routes
app.mount("/", StaticFiles(directory=str(_frontend_dir)), name="frontend")
