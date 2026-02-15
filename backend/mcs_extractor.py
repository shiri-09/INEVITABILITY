"""
INEVITABILITY - Minimal Causal Set (MCS) Extractor
Computes the smallest set of controls whose enforcement prevents a goal.
"""

from __future__ import annotations
import time
import itertools
from .models import (
    SCM, GoalPredicate, MCSResult, MCSSet, MCSElement,
    SolverStatus, NodeType, ProofArtifact
)
from .solver_engine import CausalSolver


class MCSExtractor:
    """Extracts Minimal Causal Sets from an SCM."""

    def __init__(self, solver: CausalSolver, scm: SCM):
        self.solver = solver
        self.scm = scm

    def extract_mcs(
        self,
        goal: GoalPredicate,
        max_cardinality: int = 5,
        algorithm: str = "greedy",
    ) -> MCSResult:
        """Extract Minimal Causal Sets for a goal.
        
        Arguments:
            goal: The attacker goal to defend against
            max_cardinality: Maximum size of MCS to search for
            algorithm: 'greedy' (fast, approximate) or 'exact' (exhaustive)
        """
        start = time.perf_counter()

        controls = self.scm.graph.get_controls()
        if not controls:
            return MCSResult(
                goal_id=goal.id,
                goal_name=goal.name,
                mcs_sets=[],
                computation_time_ms=0,
                algorithm=algorithm,
            )

        if algorithm == "exact":
            mcs_sets = self._exact_mcs(goal, controls, max_cardinality)
        else:
            mcs_sets = self._greedy_mcs(goal, controls, max_cardinality)

        elapsed = (time.perf_counter() - start) * 1000

        return MCSResult(
            goal_id=goal.id,
            goal_name=goal.name,
            mcs_sets=mcs_sets,
            computation_time_ms=round(elapsed, 2),
            algorithm=algorithm,
        )

    # ── Greedy MCS ────────────────────────────────────────────────────────

    def _greedy_mcs(
        self,
        goal: GoalPredicate,
        controls: list,
        max_cardinality: int,
    ) -> list[MCSSet]:
        """Greedy MCS extraction: iteratively add the most impactful control.
        
        Algorithm (from PRD Section 8):
        1. Score each control by its causal contribution
        2. Add highest-scoring control to candidate set
        3. Re-check if goal is still satisfiable
        4. Repeat until goal is UNSAT (defended)
        """
        # Score each control by impact
        control_impacts = []
        for ctrl in controls:
            # Disable this control and check impact
            interventions_enabled = {ctrl.id: True}  # Control is ON → blocks attack
            result_with = self.solver.compute_inevitability(goal, interventions_enabled)

            interventions_disabled = {ctrl.id: False}  # Control is OFF
            result_without = self.solver.compute_inevitability(goal, interventions_disabled)

            impact = result_without.score - result_with.score
            control_impacts.append((ctrl, impact))

        # Sort by impact descending
        control_impacts.sort(key=lambda x: x[1], reverse=True)

        # Greedy: build MCS by adding most impactful controls
        mcs_sets = []
        candidate_controls = []
        candidate_interventions = {}

        for ctrl, impact in control_impacts:
            if len(candidate_controls) >= max_cardinality:
                break

            candidate_controls.append(ctrl)
            candidate_interventions[ctrl.id] = True  # Enable this control

            # Check if goal is now blocked
            result = self.solver.check_satisfiability(goal, candidate_interventions)

            if result.status == SolverStatus.UNSAT:
                # Goal is blocked — we have an MCS candidate
                elements = [
                    MCSElement(
                        control_id=c.id,
                        control_name=c.name,
                        control_type=c.control_type,
                        remediation_action=f"Enforce {c.name}",
                        estimated_cost=c.annual_cost or 0.0,
                    )
                    for c in candidate_controls
                ]
                mcs_set = MCSSet(
                    elements=elements,
                    cardinality=len(elements),
                    total_cost=sum(e.estimated_cost for e in elements),
                    feasibility="immediate" if all(c.annual_cost == 0 or c.annual_cost is None for c in candidate_controls) else "budgeted",
                    validated=True,
                )
                mcs_sets.append(mcs_set)
                break

        # If still SAT after trying all controls, then no MCS exists with the current control set.
        # We do NOT return the candidate set because it fails to achieve the objective (blocking the goal).
        if not mcs_sets:
            pass  # Return empty list, signifying "Defense Impossible"

        return mcs_sets

    # ── Exact MCS ─────────────────────────────────────────────────────────

    def _exact_mcs(
        self,
        goal: GoalPredicate,
        controls: list,
        max_cardinality: int,
    ) -> list[MCSSet]:
        """Exact MCS: enumerate all minimal sets via subset search.
        
        Searches control subsets from smallest to largest.
        A set is an MCS if:
        1. Enabling these controls makes the goal UNSAT
        2. No proper subset also makes the goal UNSAT (minimality)
        """
        mcs_sets = []
        known_supersets = set()  # Prune supersets of known MCS

        for size in range(1, min(max_cardinality + 1, len(controls) + 1)):
            for combo in itertools.combinations(controls, size):
                combo_ids = frozenset(c.id for c in combo)

                # Prune: skip if it's a superset of a known MCS
                if any(known <= combo_ids for known in known_supersets):
                    continue

                # Test this combination
                interventions = {c.id: True for c in combo}
                result = self.solver.check_satisfiability(goal, interventions)

                if result.status == SolverStatus.UNSAT:
                    # This set blocks the goal — check minimality
                    is_minimal = True
                    for ctrl in combo:
                        subset = {c.id: True for c in combo if c.id != ctrl.id}
                        sub_result = self.solver.check_satisfiability(goal, subset)
                        if sub_result.status == SolverStatus.UNSAT:
                            is_minimal = False
                            break

                    if is_minimal:
                        known_supersets.add(combo_ids)
                        elements = [
                            MCSElement(
                                control_id=c.id,
                                control_name=c.name,
                                control_type=c.control_type,
                                remediation_action=f"Enforce {c.name}",
                                estimated_cost=c.annual_cost or 0.0,
                            )
                            for c in combo
                        ]
                        mcs_sets.append(MCSSet(
                            elements=elements,
                            cardinality=len(elements),
                            total_cost=sum(e.estimated_cost for e in elements),
                            feasibility="immediate" if all(c.annual_cost == 0 or c.annual_cost is None for c in combo) else "budgeted",
                            validated=True,
                        ))

        return mcs_sets

    # ── Proof Generation ──────────────────────────────────────────────────

    def generate_mcs_proof(self, goal: GoalPredicate, mcs: MCSSet) -> ProofArtifact:
        """Generate a proof artifact for an MCS claim."""
        # Verify MCS blocks the goal
        interventions = {e.control_id: True for e in mcs.elements}
        blocking_result = self.solver.check_satisfiability(goal, interventions)

        # Verify minimality — each proper subset still allows the goal
        minimality_checks = {}
        for element in mcs.elements:
            subset = {e.control_id: True for e in mcs.elements if e.control_id != element.control_id}
            sub_result = self.solver.check_satisfiability(goal, subset)
            minimality_checks[element.control_name] = sub_result.status.value

        return ProofArtifact(
            proof_type="mcs_blocking",
            claim=f"Controls {{{', '.join(e.control_name for e in mcs.elements)}}} form an MCS for goal '{goal.name}'",
            goal_id=goal.id,
            evidence={
                "blocking_verified": blocking_result.status == SolverStatus.UNSAT,
                "minimality_checks": minimality_checks,
                "all_subsets_sat": all(v == "sat" for v in minimality_checks.values()),
            },
            solver_used="z3",
            verification_time_ms=blocking_result.solve_time_ms,
        )
