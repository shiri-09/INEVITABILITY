"""
INEVITABILITY - Collapse & Fragility Engine
Computes structural collapse radius, fragility index, and collapse simulation frames.
"""

from __future__ import annotations
from .models import (
    SCM, GoalPredicate, CollapseMetrics, CollapseFrame,
    FragilityProfile, FragilityGrade, NodeType, ControlState
)
from .solver_engine import CausalSolver


class CollapseEngine:
    """Computes structural collapse metrics and simulation frames."""

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    # ── Collapse Radius ───────────────────────────────────────────────────

    def compute_collapse_radius(
        self,
        control_id: str,
        goals: list[GoalPredicate],
    ) -> CollapseMetrics:
        """Compute the collapse radius of a single control."""
        ctrl_node = self.scm.graph.get_node(control_id)
        if not ctrl_node:
            raise ValueError(f"Control {control_id} not found")

        goals_collapsed = 0
        total_inev_increase = 0.0
        spof = 0

        for goal in goals:
            # Score with control active
            score_before = self.solver.compute_inevitability(goal, {control_id: True})
            # Score with control disabled
            score_after = self.solver.compute_inevitability(goal, {control_id: False})
            delta = score_after.score - score_before.score

            if score_before.score < goal.threshold and score_after.score >= goal.threshold:
                goals_collapsed += 1

            total_inev_increase += max(0, delta)

            if score_after.is_inevitable and not score_before.is_inevitable:
                spof += 1

        return CollapseMetrics(
            control_id=control_id,
            control_name=ctrl_node.name,
            collapse_radius=goals_collapsed,
            total_inevitability_increase=round(total_inev_increase, 3),
            single_point_of_failure_count=spof,
            criticality_rank=goals_collapsed * 100 + total_inev_increase * 10,
        )

    def compute_all_collapse_metrics(
        self,
        goals: list[GoalPredicate],
    ) -> list[CollapseMetrics]:
        """Compute collapse metrics for all controls, ranked by criticality."""
        controls = self.scm.graph.get_controls()
        metrics = [
            self.compute_collapse_radius(ctrl.id, goals)
            for ctrl in controls
        ]
        metrics.sort(key=lambda m: m.criticality_rank, reverse=True)
        return metrics

    # ── Fragility Profile ─────────────────────────────────────────────────

    def compute_fragility(self, goals: list[GoalPredicate]) -> FragilityProfile:
        """Compute the Architectural Fragility Index."""
        controls = self.scm.graph.get_controls()
        if not controls or not goals:
            return FragilityProfile()

        metrics = self.compute_all_collapse_metrics(goals)

        total_goals = len(goals)
        total_controls = len(controls)

        # AFI = average normalized collapse radius
        avg_collapse = sum(m.collapse_radius for m in metrics) / total_controls if total_controls > 0 else 0
        afi = avg_collapse / total_goals if total_goals > 0 else 0

        spof_count = sum(1 for m in metrics if m.collapse_radius == total_goals)
        high_collapse = sum(1 for m in metrics if m.collapse_radius > total_goals / 2)
        brittleness = spof_count / total_controls if total_controls > 0 else 0

        # Grade
        if afi <= 0.10:
            grade = FragilityGrade.A
        elif afi <= 0.25:
            grade = FragilityGrade.B
        elif afi <= 0.45:
            grade = FragilityGrade.C
        elif afi <= 0.70:
            grade = FragilityGrade.D
        else:
            grade = FragilityGrade.F

        # Anti-patterns
        anti_patterns = self._detect_anti_patterns(metrics, goals)

        return FragilityProfile(
            afi=round(afi, 3),
            grade=grade,
            spof_count=spof_count,
            high_collapse_controls=high_collapse,
            mean_mcs_cardinality=0,  # Computed separately
            structural_brittleness=round(brittleness, 3),
            anti_patterns=anti_patterns,
        )

    # ── Collapse Simulation ───────────────────────────────────────────────

    def simulate_collapse(self, goals: list[GoalPredicate]) -> list[CollapseFrame]:
        """Generate frame-by-frame collapse simulation data.
        
        Progressively disables controls and recomputes which remaining
        control has the highest impact, creating a true cascading collapse
        where each failure reveals the next weakest link.
        """
        frames = []
        disabled_controls: dict[str, bool] = {}
        already_disabled: set[str] = set()

        # Frame 0: Baseline (all controls active)
        frame0_goals = {}
        for goal in goals:
            result = self.solver.compute_inevitability(goal)
            frame0_goals[goal.id] = {
                "name": goal.name,
                "score": result.score,
                "status": self._classify_status(result.score, goal.threshold),
                "newly_inevitable": False,
            }

        frame0_nodes = self._compute_node_states(goals, disabled_controls)

        frames.append(CollapseFrame(
            step=0,
            control_disabled=None,
            label="Current Architecture — All Controls Active",
            node_states=frame0_nodes,
            goal_states=frame0_goals,
            narration="Baseline state with all security controls active.",
        ))

        # Progressive collapse: recompute metrics after each disable
        prev_goal_states = dict(frame0_goals)
        step_counter = 0
        all_controls = self.scm.graph.get_controls()
        max_steps = len(all_controls)  # Safety limit

        while step_counter < max_steps:
            # Recompute collapse metrics for remaining active controls
            best_metric = None
            best_rank = -1

            for ctrl in all_controls:
                if ctrl.id in already_disabled:
                    continue

                # Compute impact of disabling this control given current state
                interventions_on = dict(disabled_controls)
                interventions_on[ctrl.id] = True
                interventions_off = dict(disabled_controls)
                interventions_off[ctrl.id] = False

                goals_collapsed = 0
                total_increase = 0.0

                for goal in goals:
                    score_with = self.solver.compute_inevitability(goal, interventions_on)
                    score_without = self.solver.compute_inevitability(goal, interventions_off)
                    delta = score_without.score - score_with.score

                    if (score_with.score < goal.threshold and
                            score_without.score >= goal.threshold):
                        goals_collapsed += 1
                    total_increase += max(0, delta)

                rank = goals_collapsed * 100 + total_increase * 10

                if rank > best_rank:
                    best_rank = rank
                    best_metric = CollapseMetrics(
                        control_id=ctrl.id,
                        control_name=ctrl.name,
                        collapse_radius=goals_collapsed,
                        total_inevitability_increase=round(total_increase, 3),
                        single_point_of_failure_count=0,
                        criticality_rank=rank,
                    )

            # Stop if no control causes further collapse
            if not best_metric or best_metric.collapse_radius == 0:
                # Check if any control still has nonzero increase
                if best_metric and best_metric.total_inevitability_increase > 0:
                    pass  # Still worth showing
                else:
                    break

            step_counter += 1
            already_disabled.add(best_metric.control_id)
            disabled_controls[best_metric.control_id] = False

            goal_states = {}
            newly_inevitable_goals = []

            for goal in goals:
                result = self.solver.compute_inevitability(goal, disabled_controls)
                status = self._classify_status(result.score, goal.threshold)
                newly = (status == "inevitable" and
                         prev_goal_states.get(goal.id, {}).get("status") != "inevitable")

                goal_states[goal.id] = {
                    "name": goal.name,
                    "score": result.score,
                    "status": status,
                    "newly_inevitable": newly,
                }

                if newly:
                    newly_inevitable_goals.append(goal.name)

            node_states = self._compute_node_states(goals, disabled_controls)

            # Generate narration
            if newly_inevitable_goals:
                narration = (
                    f"Disabling {best_metric.control_name} causes "
                    f"{len(newly_inevitable_goals)} goal(s) to become inevitable: "
                    f"{', '.join(newly_inevitable_goals)}"
                )
            else:
                narration = (
                    f"Disabling {best_metric.control_name} increases risk "
                    f"but no goals crossed threshold yet."
                )

            frames.append(CollapseFrame(
                step=step_counter,
                control_disabled=best_metric.control_name,
                label=f"{best_metric.control_name} Failure",
                node_states=node_states,
                goal_states=goal_states,
                narration=narration,
            ))

            prev_goal_states = dict(goal_states)

        return frames

    # ── Helpers ───────────────────────────────────────────────────────────

    def _classify_status(self, score: float, threshold: float) -> str:
        if score >= threshold:
            return "inevitable"
        elif score >= threshold * 0.6:
            return "at_risk"
        else:
            return "defended"

    def _compute_node_states(
        self,
        goals: list[GoalPredicate],
        interventions: dict[str, bool],
    ) -> dict:
        """Compute color/status for each node based on goal inevitability."""
        node_states = {}
        for node in self.scm.graph.nodes:
            # Find max inevitability among goals that this node affects
            max_score = 0.0
            for goal in goals:
                if node.id in goal.target_assets or node.id in goal.required_conditions:
                    result = self.solver.compute_inevitability(goal, interventions)
                    max_score = max(max_score, result.score)

            if max_score >= 0.7:
                color = "#ef4444"  # Red
                status = "inevitable"
            elif max_score >= 0.4:
                color = "#eab308"  # Yellow
                status = "at_risk"
            else:
                color = "#22c55e"  # Green
                status = "defended"

            node_states[node.id] = {
                "name": node.name,
                "color": color,
                "score": round(max_score, 2),
                "status": status,
                "pulse": max_score > 0.8,
            }

        return node_states

    def _detect_anti_patterns(
        self,
        metrics: list[CollapseMetrics],
        goals: list[GoalPredicate],
    ) -> list[dict]:
        """Detect architectural anti-patterns from collapse metrics."""
        patterns = []
        total_goals = len(goals)

        # SPOF Collapse
        for m in metrics:
            if m.collapse_radius >= total_goals * 0.7:
                patterns.append({
                    "name": "SPOF_COLLAPSE",
                    "severity": "CRITICAL",
                    "control": m.control_name,
                    "description": f"Single control failure collapses {m.collapse_radius}/{total_goals} goals",
                    "fix": f"Add redundant controls to reduce dependence on {m.control_name}",
                })

        # High average collapse
        if metrics:
            avg_collapse = sum(m.collapse_radius for m in metrics) / len(metrics)
            if avg_collapse > total_goals * 0.3:
                patterns.append({
                    "name": "HIGH_AVERAGE_COLLAPSE",
                    "severity": "HIGH",
                    "description": f"Average collapse radius is {avg_collapse:.1f}/{total_goals} — architecture is fragile",
                    "fix": "Implement defense-in-depth with independent control layers",
                })

        return patterns
