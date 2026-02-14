"""
INEVITABILITY - Counterfactual Engine
Implements the do-operator for "what-if" analysis and assumption toggling.
"""

from __future__ import annotations
from .models import (
    SCM, GoalPredicate, InevitabilityResult, NodeType
)
from .solver_engine import CausalSolver


class CounterfactualEngine:
    """Counterfactual reasoning engine using do-operator interventions."""

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    def what_if(
        self,
        goal: GoalPredicate,
        interventions: dict[str, bool],
        baseline_interventions: dict[str, bool] | None = None,
    ) -> dict:
        """Run a counterfactual "what-if" query.
        
        Returns the before/after inevitability comparison.
        """
        # Baseline
        baseline = self.solver.compute_inevitability(goal, baseline_interventions)

        # After intervention
        merged = dict(baseline_interventions or {})
        merged.update(interventions)
        after = self.solver.compute_inevitability(goal, merged)

        delta = after.score - baseline.score
        direction = "INCREASED" if delta > 0 else "DECREASED" if delta < 0 else "UNCHANGED"

        explanation = self._explain_delta(goal, interventions, baseline, after)

        return {
            "goal": goal.name,
            "before": baseline.score,
            "after": after.score,
            "delta": round(delta, 3),
            "direction": direction,
            "is_inevitable_before": baseline.is_inevitable,
            "is_inevitable_after": after.is_inevitable,
            "crossed_threshold": baseline.is_inevitable != after.is_inevitable,
            "interventions_applied": interventions,
            "explanation": explanation,
        }

    def toggle_assumption(
        self,
        goal: GoalPredicate,
        assumption_id: str,
        new_value: bool,
        current_interventions: dict[str, bool] | None = None,
    ) -> dict:
        """Toggle a specific assumption and recompute inevitability.
        
        Maps assumption IDs to control variables for live toggling (Section 38).
        """
        interventions = dict(current_interventions or {})

        # Map assumption to control variable
        for assumption in self.scm.assumptions:
            if assumption.id == assumption_id or assumption.name == assumption_id:
                # Find associated control
                for node in self.scm.graph.nodes:
                    if node.type == NodeType.CONTROL:
                        if node.id in assumption.id or node.name in assumption.name:
                            interventions[node.id] = new_value
                            break
                break

        return self.what_if(goal, interventions, current_interventions)

    def sensitivity_analysis(
        self,
        goal: GoalPredicate,
        baseline_interventions: dict[str, bool] | None = None,
    ) -> list[dict]:
        """Compute sensitivity: how much does each variable affect inevitability?"""
        results = []
        baseline = self.solver.compute_inevitability(goal, baseline_interventions)

        for node in self.scm.graph.nodes:
            # Toggle this variable and measure impact
            for value in [True, False]:
                interventions = dict(baseline_interventions or {})
                interventions[node.id] = value
                after = self.solver.compute_inevitability(goal, interventions)
                delta = after.score - baseline.score

                if abs(delta) > 0.01:
                    results.append({
                        "variable": node.name,
                        "variable_id": node.id,
                        "variable_type": node.type.value,
                        "set_to": value,
                        "delta": round(delta, 3),
                        "new_score": after.score,
                        "impact": "high" if abs(delta) > 0.2 else "medium" if abs(delta) > 0.1 else "low",
                    })

        results.sort(key=lambda x: abs(x["delta"]), reverse=True)
        return results

    def _explain_delta(
        self,
        goal: GoalPredicate,
        interventions: dict[str, bool],
        before: InevitabilityResult,
        after: InevitabilityResult,
    ) -> str:
        """Generate a human-readable explanation of the delta."""
        parts = []
        for var_id, value in interventions.items():
            node = self.scm.graph.get_node(var_id)
            name = node.name if node else var_id
            action = "enabled" if value else "disabled"
            parts.append(f"{name} {action}")

        intervention_text = ", ".join(parts)
        delta = after.score - before.score

        if abs(delta) < 0.01:
            return f"Toggling {intervention_text} has no measurable effect on '{goal.name}'. This suggests causal independence."
        elif delta > 0:
            return f"Toggling {intervention_text} INCREASED inevitability of '{goal.name}' by {delta:.2f} (from {before.score:.2f} to {after.score:.2f})."
        else:
            return f"Toggling {intervention_text} DECREASED inevitability of '{goal.name}' by {abs(delta):.2f} (from {before.score:.2f} to {after.score:.2f})."
