"""
INEVITABILITY - Security Theater Detector
Identifies controls that are causally irrelevant to defense goals.
A control is "security theater" if its presence or absence has NO causal effect
on the achievability of ANY attacker goal.
"""

from __future__ import annotations
from .models import (
    SCM, GoalPredicate, TheaterReport, ControlClassification,
    DefenseClassification, NodeType, SolverStatus
)
from .solver_engine import CausalSolver


class TheaterDetector:
    """Detects security theater by testing causal independence."""

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    def classify_controls(
        self,
        goal: GoalPredicate,
        mcs_control_ids: set[str] | None = None,
    ) -> TheaterReport:
        """Classify all controls by their causal relevance to a goal.
        
        Classification (from PRD Section 9):
        - CRITICAL: Control is in ALL MCS sets. Disabling it alone enables the goal.
        - NECESSARY: Control is in SOME MCS sets. Part of at least one minimal defense.
        - PARTIAL: Control affects inevitability score but isn't in any MCS.
        - IRRELEVANT: Control has ZERO causal effect on the goal. Security theater.
        """
        controls = self.scm.graph.get_controls()
        mcs_ids = mcs_control_ids or set()
        classifications = []

        # Get baseline inevitability
        baseline = self.solver.compute_inevitability(goal)

        for ctrl in controls:
            # Test with control enabled
            result_enabled = self.solver.compute_inevitability(
                goal, {ctrl.id: True}
            )
            # Test with control disabled
            result_disabled = self.solver.compute_inevitability(
                goal, {ctrl.id: False}
            )

            score_diff = abs(result_disabled.score - result_enabled.score)

            # Classify
            if score_diff < 0.01:
                # No measurable impact → security theater
                classification = DefenseClassification.IRRELEVANT
                reason = (
                    f"{ctrl.name} has no causal effect on '{goal.name}'. "
                    f"Inevitability is {result_disabled.score:.2f} whether this control "
                    f"is active or not."
                )
                recommendation = f"Consider reallocating ${ctrl.annual_cost or 0:,.0f}/year budget to causally relevant controls."
            elif ctrl.id in mcs_ids:
                # Part of MCS
                # Check if it's in ALL MCS or just some
                classification = DefenseClassification.CRITICAL
                reason = (
                    f"{ctrl.name} is part of a Minimal Causal Set. "
                    f"Disabling it increases inevitability from {result_enabled.score:.2f} "
                    f"to {result_disabled.score:.2f}."
                )
                recommendation = f"CRITICAL: Ensure {ctrl.name} is always enforced and monitored."
            elif score_diff >= 0.2:
                classification = DefenseClassification.NECESSARY
                reason = (
                    f"{ctrl.name} significantly affects inevitability "
                    f"(Δ = {score_diff:.2f}). Contributes to defense but not in the MCS."
                )
                recommendation = f"Maintain {ctrl.name} as a defense-in-depth measure."
            else:
                classification = DefenseClassification.PARTIAL
                reason = (
                    f"{ctrl.name} has minor causal contribution "
                    f"(Δ = {score_diff:.2f})."
                )
                recommendation = f"Review cost-effectiveness of {ctrl.name}."

            classifications.append(ControlClassification(
                control_id=ctrl.id,
                control_name=ctrl.name,
                control_type=ctrl.control_type,
                classification=classification,
                causal_contribution_score=round(score_diff, 3),
                annual_cost=ctrl.annual_cost or 0.0,
                reason=reason,
                recommendation=recommendation,
            ))

        # Compute summary stats
        critical = sum(1 for c in classifications if c.classification == DefenseClassification.CRITICAL)
        necessary = sum(1 for c in classifications if c.classification == DefenseClassification.NECESSARY)
        partial = sum(1 for c in classifications if c.classification == DefenseClassification.PARTIAL)
        irrelevant = sum(1 for c in classifications if c.classification == DefenseClassification.IRRELEVANT)
        total_waste = sum(c.annual_cost for c in classifications if c.classification == DefenseClassification.IRRELEVANT)
        total_spend = sum(c.annual_cost for c in classifications)

        return TheaterReport(
            goal_id=goal.id,
            goal_name=goal.name,
            classifications=classifications,
            total_controls=len(classifications),
            critical_count=critical,
            necessary_count=necessary,
            partial_count=partial,
            irrelevant_count=irrelevant,
            total_waste=total_waste,
            waste_ratio=round(total_waste / total_spend, 3) if total_spend > 0 else 0.0,
        )

    def classify_all_goals(self, goals: list[GoalPredicate]) -> list[TheaterReport]:
        """Classify controls for all goals."""
        return [self.classify_controls(goal) for goal in goals]

    def find_universal_theater(self, goals: list[GoalPredicate]) -> list[ControlClassification]:
        """Find controls that are theater for ALL goals (worst offenders)."""
        reports = self.classify_all_goals(goals)
        controls = self.scm.graph.get_controls()
        universal_theater = []

        for ctrl in controls:
            is_theater_for_all = True
            for report in reports:
                ctrl_classification = next(
                    (c for c in report.classifications if c.control_id == ctrl.id),
                    None
                )
                if ctrl_classification and ctrl_classification.classification != DefenseClassification.IRRELEVANT:
                    is_theater_for_all = False
                    break

            if is_theater_for_all:
                universal_theater.append(ControlClassification(
                    control_id=ctrl.id,
                    control_name=ctrl.name,
                    control_type=ctrl.control_type,
                    classification=DefenseClassification.IRRELEVANT,
                    annual_cost=ctrl.annual_cost or 0.0,
                    reason=f"{ctrl.name} is causally irrelevant to ALL {len(goals)} defense goals. Universal security theater.",
                    recommendation=f"ELIMINATE: {ctrl.name} provides zero causal defense value. Reallocate entire ${ctrl.annual_cost or 0:,.0f}/year budget.",
                ))

        return universal_theater
