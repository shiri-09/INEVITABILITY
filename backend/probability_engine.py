"""
INEVITABILITY v2.0 - Probabilistic Risk Engine
Quantitative risk layer sitting on top of the Z3 structural solver.
Computes path risk, goal risk, Monte Carlo simulations, and control impact rankings.
"""

from __future__ import annotations
import random
import math
from collections import defaultdict
from .models import (
    SCM, CausalGraph, GoalPredicate, InfraNode, InfraEdge,
    InevitabilityResult, NodeType, ControlState,
)


# ─── Adversary Profiles ──────────────────────────────────────────────────────

ADVERSARY_PROFILES = {
    "apt": {
        "name": "Advanced Persistent Threat (APT)",
        "skill_multiplier": 1.3,
        "bypass_bonus": 0.15,
        "noise_level": 0.1,
        "description": "Nation-state or elite group — high stealth, high sophistication",
    },
    "organized_crime": {
        "name": "Organized Crime",
        "skill_multiplier": 1.0,
        "bypass_bonus": 0.0,
        "noise_level": 0.4,
        "description": "Financially motivated group — moderate skill, moderate noise",
    },
    "script_kiddie": {
        "name": "Script Kiddie",
        "skill_multiplier": 0.6,
        "bypass_bonus": -0.15,
        "noise_level": 0.8,
        "description": "Low sophistication — uses off-the-shelf tools, easily detected",
    },
}


class ProbabilityEngine:
    """Quantitative risk engine for INEVITABILITY v2.0.

    Layer 1 (Z3) proves structural necessity.
    Layer 2 (this) computes risk magnitude under uncertainty.
    """

    def __init__(self, scm: SCM, adversary_profile: str = "apt"):
        self.scm = scm
        self.graph = scm.graph
        self.profile = ADVERSARY_PROFILES.get(adversary_profile, ADVERSARY_PROFILES["apt"])
        self.adversary_key = adversary_profile
        self._node_map: dict[str, InfraNode] = {n.id: n for n in self.graph.nodes}
        self._edge_map: dict[str, list[InfraEdge]] = defaultdict(list)
        for e in self.graph.edges:
            self._edge_map[e.target].append(e)

    # ─── Path Risk ────────────────────────────────────────────────────────

    def compute_path_risk(self, path: list[str]) -> float:
        """Compute the probability of a specific attack path succeeding.

        PathRisk = Π(edge_probability × residual_control_factor)
        where residual_control_factor = Π(bypass_probability) for all
        active controls that protect each hop.
        """
        if len(path) < 2:
            return 0.0

        risk = 1.0
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            # Find the edge between src and tgt
            edge_prob = self._get_edge_probability(src, tgt)
            # Compute residual through controls protecting this hop
            control_residual = self._compute_control_residual(tgt)
            # Apply adversary skill
            effective_prob = min(1.0, edge_prob * self.profile["skill_multiplier"])
            risk *= effective_prob * control_residual

        return round(risk, 6)

    def _get_edge_probability(self, source: str, target: str) -> float:
        """Get the exploit probability for an edge between two nodes."""
        for edge in self.graph.edges:
            if edge.source == source and edge.target == target:
                return edge.exploit_probability
        return 0.5  # default

    def _compute_control_residual(self, target_id: str) -> float:
        """Compute residual risk after all active controls protecting a node.

        Defense-in-depth: controls stack multiplicatively.
        If WAF (70% effective) + Firewall (80% effective) protect a node:
        residual = (1-0.7) × (1-0.8) = 0.06 → 6% gets through.
        """
        residual = 1.0
        for eq in self.scm.equations:
            if eq.target_variable == target_id:
                for ctrl_id in eq.negated_parents:
                    ctrl = self._node_map.get(ctrl_id)
                    if ctrl and ctrl.type == NodeType.CONTROL:
                        if ctrl.control_state == ControlState.ACTIVE:
                            bp = ctrl.bypass_probability
                            # Apply adversary bypass bonus
                            bp = min(1.0, max(0.01, bp + self.profile["bypass_bonus"]))
                            residual *= bp
                        elif ctrl.control_state == ControlState.PARTIAL:
                            bp = ctrl.bypass_probability * 1.5  # partial = weaker
                            bp = min(1.0, max(0.01, bp + self.profile["bypass_bonus"]))
                            residual *= bp
                        # INACTIVE controls contribute nothing (residual stays 1.0)
        return residual

    # ─── Goal Risk ────────────────────────────────────────────────────────

    def compute_goal_risk(
        self,
        goal: GoalPredicate,
        inevitability_result: InevitabilityResult,
    ) -> dict:
        """Compute quantitative risk for a goal using all identified attack paths.

        Returns a dict with probabilistic metrics.
        """
        paths = self._enumerate_attack_paths(goal)
        if not paths:
            # Use witness path from Z3 if available
            if inevitability_result.witness_path:
                paths = [inevitability_result.witness_path]
            else:
                return {
                    "goal_id": goal.id,
                    "goal_name": goal.name,
                    "probabilistic_score": 0.0,
                    "path_risks": [],
                    "combined_risk": 0.0,
                    "adversary_profile": self.profile["name"],
                    "defense_depth_factor": 1.0,
                }

        # Compute per-path risk
        path_risks = []
        for path in paths:
            risk = self.compute_path_risk(path)
            path_risks.append({
                "path": path,
                "risk": risk,
                "path_length": len(path),
            })

        # Combined risk: probability of at least one path succeeding
        # P(any) = 1 - Π(1 - P(path_i))
        combined = 1.0
        for pr in path_risks:
            combined *= (1.0 - pr["risk"])
        combined_risk = round(1.0 - combined, 4)

        # Sort paths by risk (highest first)
        path_risks.sort(key=lambda x: x["risk"], reverse=True)

        # Defense depth = average # of active controls per path hop
        all_controls = self._count_controls_on_paths(paths)

        return {
            "goal_id": goal.id,
            "goal_name": goal.name,
            "probabilistic_score": combined_risk,
            "path_risks": path_risks[:5],  # Top 5 riskiest paths
            "combined_risk": combined_risk,
            "adversary_profile": self.profile["name"],
            "defense_depth_factor": round(all_controls, 2),
            "total_paths_analyzed": len(paths),
        }

    def _enumerate_attack_paths(self, goal: GoalPredicate) -> list[list[str]]:
        """Find all attack paths from identity nodes to goal targets using BFS."""
        identities = [n for n in self.graph.nodes if n.type == NodeType.IDENTITY]
        targets = set(goal.target_assets)
        all_paths = []

        # Build adjacency list
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in self.graph.edges:
            adj[edge.source].append(edge.target)

        for identity in identities:
            for target in targets:
                paths = self._find_paths_bfs(adj, identity.id, target, max_depth=10)
                all_paths.extend(paths)

        return all_paths[:20]  # Cap at 20 paths for performance

    def _find_paths_bfs(
        self, adj: dict, start: str, end: str, max_depth: int = 10
    ) -> list[list[str]]:
        """BFS path finding with depth limit."""
        paths = []
        queue: list[tuple[str, list[str]]] = [(start, [start])]

        while queue and len(paths) < 5:
            node, path = queue.pop(0)
            if len(path) > max_depth:
                continue
            if node == end:
                paths.append(path)
                continue
            for neighbor in adj.get(node, []):
                if neighbor not in path:  # avoid cycles
                    queue.append((neighbor, path + [neighbor]))

        return paths

    def _count_controls_on_paths(self, paths: list[list[str]]) -> float:
        """Average number of active controls per path hop."""
        total_controls = 0
        total_hops = 0
        for path in paths:
            for node_id in path:
                for eq in self.scm.equations:
                    if eq.target_variable == node_id:
                        for ctrl_id in eq.negated_parents:
                            ctrl = self._node_map.get(ctrl_id)
                            if ctrl and ctrl.control_state == ControlState.ACTIVE:
                                total_controls += 1
                total_hops += 1
        return total_controls / max(total_hops, 1)

    # ─── Monte Carlo Simulation ───────────────────────────────────────────

    def monte_carlo_simulate(
        self,
        goal: GoalPredicate,
        inevitability_result: InevitabilityResult,
        n_simulations: int = 10000,
    ) -> dict:
        """Run Monte Carlo simulation for a goal.

        For each simulation:
        1. Randomly decide if each control holds or fails (based on bypass rate)
        2. Randomly evaluate each edge exploit success
        3. Check if any path from identity → goal target succeeds
        """
        paths = self._enumerate_attack_paths(goal)
        if not paths:
            if inevitability_result.witness_path:
                paths = [inevitability_result.witness_path]
            else:
                return self._empty_mc_result(goal)

        successes = 0
        risk_samples = []

        for _ in range(n_simulations):
            attack_succeeded = False
            for path in paths:
                if self._simulate_path(path):
                    attack_succeeded = True
                    break
            if attack_succeeded:
                successes += 1

        probability = successes / n_simulations
        # Build distribution buckets
        bucket_size = n_simulations // 10
        distribution = {}
        for i in range(10):
            bucket_label = f"{i*10}-{(i+1)*10}%"
            distribution[bucket_label] = 0

        # Compute confidence interval using normal approximation
        if n_simulations > 30:
            se = math.sqrt(probability * (1 - probability) / n_simulations)
            ci_lower = max(0.0, probability - 1.96 * se)
            ci_upper = min(1.0, probability + 1.96 * se)
        else:
            ci_lower = probability
            ci_upper = probability

        return {
            "goal_id": goal.id,
            "goal_name": goal.name,
            "simulations": n_simulations,
            "successes": successes,
            "probability": round(probability, 4),
            "probability_percent": round(probability * 100, 1),
            "confidence_interval": {
                "lower": round(ci_lower, 4),
                "upper": round(ci_upper, 4),
                "level": "95%",
            },
            "adversary_profile": self.profile["name"],
        }

    def _simulate_path(self, path: list[str]) -> bool:
        """Simulate a single attack path attempt."""
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]

            # Edge exploit roll
            edge_prob = self._get_edge_probability(src, tgt)
            effective_prob = min(1.0, edge_prob * self.profile["skill_multiplier"])
            if random.random() > effective_prob:
                return False  # Exploit failed

            # Control bypass roll for each control protecting this hop
            for eq in self.scm.equations:
                if eq.target_variable == tgt:
                    for ctrl_id in eq.negated_parents:
                        ctrl = self._node_map.get(ctrl_id)
                        if ctrl and ctrl.type == NodeType.CONTROL:
                            if ctrl.control_state == ControlState.ACTIVE:
                                bp = min(1.0, max(0.01, ctrl.bypass_probability + self.profile["bypass_bonus"]))
                                if random.random() > bp:
                                    return False  # Control blocked
                            elif ctrl.control_state == ControlState.PARTIAL:
                                bp = min(1.0, ctrl.bypass_probability * 1.5 + self.profile["bypass_bonus"])
                                if random.random() > bp:
                                    return False
        return True  # All hops succeeded

    def _empty_mc_result(self, goal: GoalPredicate) -> dict:
        return {
            "goal_id": goal.id,
            "goal_name": goal.name,
            "simulations": 0,
            "successes": 0,
            "probability": 0.0,
            "probability_percent": 0.0,
            "confidence_interval": {"lower": 0.0, "upper": 0.0, "level": "95%"},
            "adversary_profile": self.profile["name"],
        }

    # ─── Control Impact Ranking ───────────────────────────────────────────

    def rank_control_impact(
        self,
        goals: list[GoalPredicate],
        inevitability_results: list[InevitabilityResult],
    ) -> list[dict]:
        """Rank controls by their risk reduction impact and cost-effectiveness.

        For each control: compute risk_with vs risk_without → marginal value.
        """
        controls = [n for n in self.graph.nodes if n.type == NodeType.CONTROL]
        rankings = []

        # Compute baseline risk (all controls as-is)
        baseline_risks = {}
        for goal, inev in zip(goals, inevitability_results):
            result = self.compute_goal_risk(goal, inev)
            baseline_risks[goal.id] = result["combined_risk"]

        for ctrl in controls:
            # Temporarily disable this control and recompute risk
            original_state = ctrl.control_state
            ctrl.control_state = ControlState.INACTIVE

            risk_increase = 0.0
            for goal, inev in zip(goals, inevitability_results):
                result = self.compute_goal_risk(goal, inev)
                risk_without = result["combined_risk"]
                risk_increase += risk_without - baseline_risks.get(goal.id, 0.0)

            # Restore control state
            ctrl.control_state = original_state

            # Compute cost-effectiveness
            cost = ctrl.annual_cost or 0.0
            marginal_reduction = max(0.0, risk_increase)
            cost_effectiveness = (marginal_reduction / cost * 100) if cost > 0 else float('inf') if marginal_reduction > 0 else 0.0

            rankings.append({
                "control_id": ctrl.id,
                "control_name": ctrl.name,
                "control_type": ctrl.control_type or "unknown",
                "annual_cost": cost,
                "effectiveness": ctrl.effectiveness,
                "marginal_risk_reduction": round(marginal_reduction, 4),
                "risk_reduction_percent": round(marginal_reduction * 100, 1),
                "cost_effectiveness_score": round(cost_effectiveness, 2),
                "is_critical": marginal_reduction > 0.05,
                "is_redundant": marginal_reduction < 0.001 and cost > 0,
            })

        # Sort by marginal risk reduction (most impactful first)
        rankings.sort(key=lambda x: x["marginal_risk_reduction"], reverse=True)
        return rankings

    # ─── Naked Critical Asset Detection ───────────────────────────────────

    def detect_naked_critical_assets(self) -> list[dict]:
        """Find critical assets with no protective control."""
        from .models import Criticality
        critical_assets = [
            n for n in self.graph.nodes
            if n.type == NodeType.ASSET and n.criticality in (Criticality.CRITICAL, Criticality.HIGH)
        ]

        naked = []
        for asset in critical_assets:
            has_control = False
            for eq in self.scm.equations:
                if eq.target_variable == asset.id and eq.negated_parents:
                    for ctrl_id in eq.negated_parents:
                        ctrl = self._node_map.get(ctrl_id)
                        if ctrl and ctrl.control_state == ControlState.ACTIVE:
                            has_control = True
                            break
                if has_control:
                    break

            if not has_control:
                naked.append({
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "criticality": asset.criticality.value if asset.criticality else "unknown",
                    "data_classification": asset.data_classification or [],
                    "warning": f"CRITICAL: {asset.name} has no active protective control",
                })

        return naked

    # ─── Full Analysis ────────────────────────────────────────────────────

    def run_full_analysis(
        self,
        goals: list[GoalPredicate],
        inevitability_results: list[InevitabilityResult],
        run_monte_carlo: bool = True,
        mc_simulations: int = 10000,
    ) -> dict:
        """Run complete probabilistic analysis.

        Returns all probabilistic results in a structured dict.
        """
        goal_risks = []
        mc_results = []

        for goal, inev in zip(goals, inevitability_results):
            # Compute goal risk
            risk = self.compute_goal_risk(goal, inev)
            goal_risks.append(risk)

            # Update the InevitabilityResult with probabilistic score
            inev.probabilistic_score = risk["probabilistic_score"]
            inev.adversary_profile = self.profile["name"]

            # Monte Carlo
            if run_monte_carlo:
                mc = self.monte_carlo_simulate(goal, inev, mc_simulations)
                mc_results.append(mc)
                inev.risk_distribution = {
                    "mean": mc["probability"],
                    "ci_lower": mc["confidence_interval"]["lower"],
                    "ci_upper": mc["confidence_interval"]["upper"],
                }

        # Control rankings
        control_rankings = self.rank_control_impact(goals, inevitability_results)

        # Naked asset detection
        naked_assets = self.detect_naked_critical_assets()

        return {
            "engine_version": "2.0",
            "adversary_profile": {
                "key": self.adversary_key,
                **self.profile,
            },
            "goal_risks": goal_risks,
            "monte_carlo": mc_results if run_monte_carlo else None,
            "control_rankings": control_rankings,
            "naked_critical_assets": naked_assets,
            "summary": {
                "max_risk": max((r["combined_risk"] for r in goal_risks), default=0.0),
                "avg_risk": sum(r["combined_risk"] for r in goal_risks) / max(len(goal_risks), 1),
                "critical_controls": len([c for c in control_rankings if c["is_critical"]]),
                "redundant_controls": len([c for c in control_rankings if c["is_redundant"]]),
                "naked_assets": len(naked_assets),
            },
        }
