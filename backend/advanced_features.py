"""
INEVITABILITY — Advanced Features Module
Multi-Goal Strategic Optimization, Certification Mode, Failure Forecasting,
Goal Collision Analysis, and Adversarial Defense Testing.
"""

from __future__ import annotations
import time
import math
import json
from itertools import combinations
from .models import (
    SCM, GoalPredicate, NodeType, ControlState, InevitabilityResult
)
from .solver_engine import CausalSolver
from .mcs_extractor import MCSExtractor
from .theater_detector import TheaterDetector


# ═══════════════════════════════════════════════════════════════════════════════
# §20 — MULTI-GOAL STRATEGIC OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class MultiGoalOptimizer:
    """
    Computes Pareto-optimal defense strategies across multiple goals.
    Finds the cheapest set of controls that reduces all goal inevitability
    below a threshold.
    """

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    def compute_optimal_strategies(
        self,
        goals: list[GoalPredicate],
        budget_limit: float = float('inf'),
        max_strategies: int = 5,
    ) -> list[dict]:
        """
        Find the top-N defense strategies ranked by cost-effectiveness.
        Each strategy is a set of controls to enable/fix.
        """
        # Get all inactive/partial controls
        fixable_controls = []
        for eq in self.scm.equations:
            node = self._find_node(eq.target_variable)
            if node and node.type == NodeType.CONTROL:
                if node.control_state in (ControlState.INACTIVE, ControlState.PARTIAL):
                    cost = node.annual_cost or 0
                    fixable_controls.append({
                        "id": node.id,
                        "name": node.name,
                        "cost": cost,
                        "type": node.control_type or "unknown",
                    })

        # Compute baseline inevitability for all goals
        baselines = {}
        for goal in goals:
            result = self.solver.compute_inevitability(goal)
            baselines[goal.id] = result.score

        # Enumerate combinations of controls (up to size 4 for tractability)
        strategies = []
        max_combo_size = min(4, len(fixable_controls))

        for size in range(1, max_combo_size + 1):
            for combo in combinations(fixable_controls, size):
                total_cost = sum(c["cost"] for c in combo)
                if total_cost > budget_limit:
                    continue

                # Simulate enabling these controls
                interventions = {c["id"]: True for c in combo}

                total_reduction = 0
                goal_impacts = []
                for goal in goals:
                    new_result = self.solver.compute_inevitability(goal, interventions)
                    reduction = baselines[goal.id] - new_result.score
                    total_reduction += max(0, reduction)
                    goal_impacts.append({
                        "goal_id": goal.id,
                        "goal_name": goal.name,
                        "before": round(baselines[goal.id], 3),
                        "after": round(new_result.score, 3),
                        "reduction": round(max(0, reduction), 3),
                    })

                # Calculate ROI
                roi = (total_reduction / (total_cost / 100000)) if total_cost > 0 else total_reduction * 1000

                strategies.append({
                    "controls": [c["name"] for c in combo],
                    "control_ids": [c["id"] for c in combo],
                    "total_cost": total_cost,
                    "total_reduction": round(total_reduction, 3),
                    "roi_score": round(roi, 2),
                    "goal_impacts": goal_impacts,
                    "description": self._generate_strategy_description(combo, goal_impacts),
                })

        # Sort by ROI (best first)
        strategies.sort(key=lambda s: s["roi_score"], reverse=True)

        # Mark the best as recommended
        for i, s in enumerate(strategies[:max_strategies]):
            s["rank"] = i + 1
            s["recommended"] = (i == 0)

        return strategies[:max_strategies]

    def _find_node(self, node_id: str):
        for eq in self.scm.equations:
            if eq.target_variable == node_id:
                pass
        # Fallback: search through node_metadata
        if hasattr(self.scm, 'node_metadata') and self.scm.node_metadata:
            return self.scm.node_metadata.get(node_id)
        return None

    def _generate_strategy_description(self, controls, impacts):
        names = [c["name"] for c in controls]
        reductions = [i for i in impacts if i["reduction"] > 0]
        if not reductions:
            return f"Enable {', '.join(names)} — minimal impact on current goals"
        best = max(reductions, key=lambda x: x["reduction"])
        return f"Enable {', '.join(names)} — reduces {best['goal_name']} by {best['reduction']*100:.0f}%"


# ═══════════════════════════════════════════════════════════════════════════════
# §27 — CERTIFICATION MODE
# ═══════════════════════════════════════════════════════════════════════════════

class CertificationEngine:
    """
    Generates formal certification reports with proof artifacts.
    Produces machine-readable and human-readable audit reports.
    """

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    def generate_certification(
        self,
        goals: list[GoalPredicate],
        inevitability_results: list[InevitabilityResult],
        organization: str = "Unknown",
    ) -> dict:
        """Generate a formal certification report."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Count controls by state
        controls = self._get_controls()
        active_controls = [c for c in controls if c.get("state") == "ACTIVE"]
        inactive_controls = [c for c in controls if c.get("state") == "INACTIVE"]
        partial_controls = [c for c in controls if c.get("state") == "PARTIAL"]

        # Compute overall posture score
        if inevitability_results:
            avg_inev = sum(r.score for r in inevitability_results) / len(inevitability_results)
        else:
            avg_inev = 0

        posture_score = max(0, min(100, int((1 - avg_inev) * 100)))

        # Determine grade
        if posture_score >= 90:
            grade = "A"
        elif posture_score >= 75:
            grade = "B"
        elif posture_score >= 60:
            grade = "C"
        elif posture_score >= 40:
            grade = "D"
        else:
            grade = "F"

        # Build goal assessments
        goal_assessments = []
        for goal, result in zip(goals, inevitability_results):
            goal_assessments.append({
                "goal_id": goal.id,
                "goal_name": goal.name,
                "inevitability_score": round(result.score, 4),
                "status": "INEVITABLE" if result.is_inevitable else "DEFENDED",
                "verdict": "FAIL" if result.is_inevitable else "PASS",
                "attack_path_length": len(result.witness_path) if result.witness_path else 0,
            })

        # Build findings
        findings = []
        failing_goals = [g for g in goal_assessments if g["verdict"] == "FAIL"]
        if failing_goals:
            findings.append({
                "severity": "CRITICAL",
                "finding": f"{len(failing_goals)} of {len(goals)} attack goals are structurally inevitable",
                "recommendation": "Address controls identified in MCS analysis immediately",
            })
        if inactive_controls:
            findings.append({
                "severity": "HIGH",
                "finding": f"{len(inactive_controls)} security controls are INACTIVE",
                "recommendation": "Enable or properly configure inactive controls",
            })
        if partial_controls:
            findings.append({
                "severity": "MEDIUM",
                "finding": f"{len(partial_controls)} security controls are only PARTIALLY effective",
                "recommendation": "Review partial controls for configuration gaps",
            })
        if not failing_goals:
            findings.append({
                "severity": "INFO",
                "finding": "All analyzed attack goals are structurally defended",
                "recommendation": "Maintain current control configuration and implement periodic review",
            })

        return {
            "certification_id": f"INEV-CERT-{int(time.time())}",
            "timestamp": timestamp,
            "organization": organization,
            "engine_version": "1.0.0",
            "posture_score": posture_score,
            "grade": grade,
            "total_controls": len(controls),
            "active_controls": len(active_controls),
            "inactive_controls": len(inactive_controls),
            "partial_controls": len(partial_controls),
            "goals_analyzed": len(goals),
            "goals_defended": len(goals) - len(failing_goals),
            "goals_inevitable": len(failing_goals),
            "goal_assessments": goal_assessments,
            "findings": findings,
            "scm_nodes": len(self.scm.equations),
            "methodology": "Structural Causal Model + Z3 SMT Solver",
            "formal_guarantee": "Results are provably correct under the modeled infrastructure topology",
        }

    def _get_controls(self) -> list[dict]:
        controls = []
        if hasattr(self.scm, 'node_metadata') and self.scm.node_metadata:
            for nid, meta in self.scm.node_metadata.items():
                if hasattr(meta, 'type') and meta.type == NodeType.CONTROL:
                    controls.append({
                        "id": nid,
                        "name": meta.name,
                        "state": meta.control_state.value if meta.control_state else "UNKNOWN",
                        "type": meta.control_type or "unknown",
                        "cost": meta.annual_cost or 0,
                    })
        return controls


# ═══════════════════════════════════════════════════════════════════════════════
# §29 — FAILURE FORECASTING
# ═══════════════════════════════════════════════════════════════════════════════

class FailureForecaster:
    """
    Projects how inevitability scores will drift over time based on
    common infrastructure degradation patterns.
    """

    # Default drift rates (per month)
    DEFAULT_DRIFT_RATES = {
        "privilege_creep": 0.08,        # 8% monthly privilege expansion
        "identity_growth": 0.05,        # 5% monthly identity growth
        "patch_decay": 0.03,            # 3% monthly patch coverage decline
        "config_drift": 0.04,           # 4% monthly config drift
        "control_degradation": 0.02,    # 2% monthly control effectiveness decay
    }

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    def forecast(
        self,
        goals: list[GoalPredicate],
        inevitability_results: list[InevitabilityResult],
        months_ahead: int = 12,
        drift_rates: dict | None = None,
    ) -> dict:
        """
        Project inevitability scores forward in time.
        Uses a degradation model where each control loses effectiveness over time.
        """
        rates = drift_rates or self.DEFAULT_DRIFT_RATES
        combined_drift = sum(rates.values()) / len(rates) if rates else 0.04

        goal_forecasts = []
        for goal, result in zip(goals, inevitability_results):
            current = result.score
            projections = []

            for month in range(0, months_ahead + 1):
                # Model: score increases sigmoidally toward 1.0
                # Faster growth when current score is in the middle range
                projected = current + (1 - current) * (1 - math.exp(-combined_drift * month))
                projected = min(1.0, projected)
                projections.append({
                    "month": month,
                    "projected_score": round(projected, 4),
                    "status": "INEVITABLE" if projected >= goal.threshold else "AT_RISK" if projected >= 0.5 else "DEFENDED",
                })

            # Find when threshold is crossed
            crossing_month = None
            for p in projections:
                if p["projected_score"] >= goal.threshold and current < goal.threshold:
                    crossing_month = p["month"]
                    break

            goal_forecasts.append({
                "goal_id": goal.id,
                "goal_name": goal.name,
                "current_score": round(current, 4),
                "threshold": goal.threshold,
                "projections": projections,
                "crossing_month": crossing_month,
                "months_to_inevitable": crossing_month,
                "risk_trajectory": "ACCELERATING" if current > 0.3 else "STABLE" if current < 0.1 else "DRIFTING",
                "primary_driver": max(rates, key=rates.get) if rates else "unknown",
            })

        # Overall assessment
        min_crossing = min(
            (f["crossing_month"] for f in goal_forecasts if f["crossing_month"] is not None),
            default=None
        )

        return {
            "forecast_horizon_months": months_ahead,
            "drift_rates": rates,
            "goal_forecasts": goal_forecasts,
            "earliest_inevitable": min_crossing,
            "overall_risk": "CRITICAL" if min_crossing and min_crossing <= 3 else "HIGH" if min_crossing and min_crossing <= 6 else "MODERATE" if min_crossing else "LOW",
            "recommendation": self._generate_recommendation(goal_forecasts, min_crossing),
        }

    def _generate_recommendation(self, forecasts, min_crossing):
        if min_crossing is None:
            return "Current posture is stable. Continue monitoring for drift."
        if min_crossing <= 3:
            return f"URGENT: Without intervention, a goal becomes inevitable within {min_crossing} months. Immediate remediation required."
        if min_crossing <= 6:
            return f"WARNING: Structural degradation will reach inevitability in ~{min_crossing} months. Schedule remediation sprint."
        return f"Architecture projected to degrade to inevitability in ~{min_crossing} months. Plan proactive review."


# ═══════════════════════════════════════════════════════════════════════════════
# §31 — GOAL COLLISION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

class GoalCollisionAnalyzer:
    """
    Detects interactions between multiple goals: conflicts (fixing one breaks another),
    synergies (one fix helps both), and independence.
    """

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    def analyze_collisions(self, goals: list[GoalPredicate]) -> list[dict]:
        """Analyze pairwise interactions between goals."""
        if len(goals) < 2:
            return []

        collisions = []
        for i, g1 in enumerate(goals):
            for g2 in goals[i + 1:]:
                collision = self._analyze_pair(g1, g2)
                collisions.append(collision)

        return collisions

    def _analyze_pair(self, g1: GoalPredicate, g2: GoalPredicate) -> dict:
        """Analyze the interaction between two goals."""
        # Baseline scores
        r1 = self.solver.compute_inevitability(g1)
        r2 = self.solver.compute_inevitability(g2)

        # Find shared controls (controls that appear in attack paths of both goals)
        controls_g1 = self._get_relevant_controls(g1)
        controls_g2 = self._get_relevant_controls(g2)

        shared = controls_g1 & controls_g2
        unique_g1 = controls_g1 - controls_g2
        unique_g2 = controls_g2 - controls_g1

        # Determine relationship
        if shared:
            # Check if fixing shared controls helps both
            interventions = {c: True for c in shared}
            new_r1 = self.solver.compute_inevitability(g1, interventions)
            new_r2 = self.solver.compute_inevitability(g2, interventions)

            d1 = r1.score - new_r1.score
            d2 = r2.score - new_r2.score

            if d1 > 0.1 and d2 > 0.1:
                collision_type = "SYNERGY"
                description = f"Fixing shared controls reduces both goals significantly"
            elif (d1 > 0.1 and d2 < -0.05) or (d2 > 0.1 and d1 < -0.05):
                collision_type = "CONFLICT"
                description = f"Fixing one goal's controls worsens the other"
            else:
                collision_type = "PARTIAL_OVERLAP"
                description = f"Goals share {len(shared)} controls with mixed impact"
        else:
            collision_type = "INDEPENDENT"
            description = "Goals use completely independent control sets"

        return {
            "goal_1": {"id": g1.id, "name": g1.name, "score": round(r1.score, 3)},
            "goal_2": {"id": g2.id, "name": g2.name, "score": round(r2.score, 3)},
            "collision_type": collision_type,
            "description": description,
            "shared_controls": list(shared),
            "shared_control_count": len(shared),
            "unique_to_goal_1": len(unique_g1),
            "unique_to_goal_2": len(unique_g2),
        }

    def _get_relevant_controls(self, goal: GoalPredicate) -> set[str]:
        """Get all control IDs that are structurally relevant to a goal."""
        controls = set()
        target_ids = set(goal.target_assets)

        # Walk backward from target to find all relevant controls
        for eq in self.scm.equations:
            if eq.target_variable in target_ids:
                for parent in (eq.negated_parents or []):
                    controls.add(parent)
                # Recursively add parents
                for parent in (eq.parent_variables or []):
                    target_ids.add(parent)

        return controls


# ═══════════════════════════════════════════════════════════════════════════════
# §32 — ADVERSARIAL DEFENSE TESTING
# ═══════════════════════════════════════════════════════════════════════════════

class AdversarialTester:
    """
    Red team simulation: finds the optimal attack strategy given current defenses.
    Identifies which single control failure would be most devastating.
    """

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    def run_adversarial_test(self, goals: list[GoalPredicate]) -> dict:
        """Simulate an optimal adversary and find the weakest links."""
        # Get all active controls
        active_controls = []
        if hasattr(self.scm, 'node_metadata') and self.scm.node_metadata:
            for nid, meta in self.scm.node_metadata.items():
                if hasattr(meta, 'type') and meta.type == NodeType.CONTROL:
                    if meta.control_state == ControlState.ACTIVE:
                        active_controls.append({
                            "id": nid,
                            "name": meta.name,
                            "cost": meta.annual_cost or 0,
                        })

        # Baseline
        baselines = {}
        for goal in goals:
            r = self.solver.compute_inevitability(goal)
            baselines[goal.id] = r.score

        # Test each control failure
        attack_vectors = []
        for ctrl in active_controls:
            interventions = {ctrl["id"]: False}
            max_impact = 0
            impacts = []

            for goal in goals:
                new_r = self.solver.compute_inevitability(goal, interventions)
                impact = new_r.score - baselines[goal.id]
                max_impact = max(max_impact, impact)
                impacts.append({
                    "goal": goal.name,
                    "before": round(baselines[goal.id], 3),
                    "after": round(new_r.score, 3),
                    "delta": round(impact, 3),
                })

            attack_vectors.append({
                "control_to_bypass": ctrl["name"],
                "control_id": ctrl["id"],
                "bypass_cost_estimate": ctrl["cost"],
                "max_impact": round(max_impact, 3),
                "goal_impacts": impacts,
                "severity": "CRITICAL" if max_impact > 0.5 else "HIGH" if max_impact > 0.2 else "MEDIUM" if max_impact > 0.05 else "LOW",
            })

        # Sort by impact (most devastating first)
        attack_vectors.sort(key=lambda v: v["max_impact"], reverse=True)

        return {
            "total_controls_tested": len(active_controls),
            "critical_vectors": len([v for v in attack_vectors if v["severity"] == "CRITICAL"]),
            "high_vectors": len([v for v in attack_vectors if v["severity"] == "HIGH"]),
            "attack_vectors": attack_vectors,
            "optimal_attack": attack_vectors[0] if attack_vectors else None,
            "recommendation": self._summarize(attack_vectors),
        }

    def _summarize(self, vectors):
        if not vectors:
            return "No active controls to test."
        critical = [v for v in vectors if v["severity"] == "CRITICAL"]
        if critical:
            return f"ALERT: {len(critical)} critical single-point-of-failure controls identified. Bypassing '{critical[0]['control_to_bypass']}' causes maximum damage."
        return "No critical single-point-of-failure controls found. Defense posture is reasonably resilient to individual control bypass."
