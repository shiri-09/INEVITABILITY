"""
INEVITABILITY - Causal Solver Engine
Core SMT-based solver using Z3 for inevitability computation.
Encodes Structural Causal Models into SMT formulas and checks satisfiability.
"""

from __future__ import annotations
import time
from z3 import (
    Bool, BoolRef, Solver, And, Or, Not, Implies, sat, unsat, unknown,
    BoolVal, ModelRef
)
from .models import (
    SCM, GoalPredicate, SolverResult, SolverStatus,
    InevitabilityResult, StructuralEquation, NodeType
)


class CausalSolver:
    """SMT-based solver for structural causal models."""

    def __init__(self, scm: SCM, timeout_ms: int = 30000):
        self.scm = scm
        self.timeout_ms = timeout_ms
        self._z3_vars: dict[str, BoolRef] = {}
        self._solver: Solver | None = None
        self._build_variables()

    # ── Variable Construction ─────────────────────────────────────────────

    def _build_variables(self):
        """Create Z3 Boolean variables for each node in the SCM."""
        for node in self.scm.graph.nodes:
            self._z3_vars[node.id] = Bool(node.id)

    def get_var(self, node_id: str) -> BoolRef:
        """Get or create a Z3 variable for a node."""
        if node_id not in self._z3_vars:
            self._z3_vars[node_id] = Bool(node_id)
        return self._z3_vars[node_id]

    # ── SCM Encoding ─────────────────────────────────────────────────────

    def _encode_scm(self, interventions: dict[str, bool] | None = None) -> list[BoolRef]:
        """Encode the SCM as Z3 constraints.
        
        For each structural equation:
        target = (parent1 AND parent2 AND ...) AND NOT(control1) AND NOT(control2)
        
        Interventions override variable values (do-operator).
        """
        constraints = []
        interventions = interventions or {}

        for eq in self.scm.equations:
            target = self.get_var(eq.target_variable)

            # If target is intervened upon, set it directly
            if eq.target_variable in interventions:
                constraints.append(target == BoolVal(interventions[eq.target_variable]))
                continue

            # Build enabling condition: ANY source can enable (disjunction)
            # This models that any single attack path reaching a node is sufficient
            enabling_parts = []
            for parent_id in eq.parent_variables:
                if parent_id in interventions:
                    enabling_parts.append(BoolVal(interventions[parent_id]))
                else:
                    enabling_parts.append(self.get_var(parent_id))

            # Build blocking condition: active controls block the path
            blocking_parts = []
            for ctrl_id in eq.negated_parents:
                if ctrl_id in interventions:
                    blocking_parts.append(BoolVal(interventions[ctrl_id]))
                else:
                    blocking_parts.append(self.get_var(ctrl_id))

            # Structural equation:
            #   target = (ANY enabler is true) AND (NO blocking control is active)
            # Using OR for enablers: any single attack path suffices
            # Using AND-NOT for controls: each active control blocks
            if enabling_parts and blocking_parts:
                enabler = Or(*enabling_parts) if len(enabling_parts) > 1 else enabling_parts[0]
                blocker = Or(*blocking_parts)
                formula = And(enabler, Not(blocker))
            elif enabling_parts:
                formula = Or(*enabling_parts) if len(enabling_parts) > 1 else enabling_parts[0]
            elif blocking_parts:
                formula = Not(Or(*blocking_parts))
            else:
                continue

            constraints.append(target == formula)

        return constraints

    def _encode_exogenous_constraints(self, interventions: dict[str, bool] | None = None) -> list[BoolRef]:
        """Encode constraints on exogenous (root) variables."""
        constraints = []
        interventions = interventions or {}

        for node in self.scm.graph.nodes:
            parents = self.scm.graph.get_parents(node.id)
            if not parents:  # Exogenous variable
                if node.id in interventions:
                    constraints.append(
                        self.get_var(node.id) == BoolVal(interventions[node.id])
                    )
                elif node.type == NodeType.CONTROL:
                    # Controls default based on their actual state
                    from .models import ControlState
                    if node.control_state:
                        active = node.control_state == ControlState.ACTIVE
                    else:
                        active = False
                    constraints.append(self.get_var(node.id) == BoolVal(active))
                elif node.type == NodeType.IDENTITY:
                    # Identities (potential attacker entry points) default to True
                    # The attacker exists in the threat model
                    constraints.append(self.get_var(node.id) == BoolVal(True))
                # Other exogenous nodes (assets, channels) are unconstrained
                # letting Z3 decide their value

        return constraints

    def _encode_assumption_constraints(self, disabled_assumptions: set[str] | None = None) -> list[BoolRef]:
        """Encode assumption states as constraints."""
        constraints = []
        disabled = disabled_assumptions or set()

        for assumption in self.scm.assumptions:
            # Find the control node related to this assumption
            for node in self.scm.graph.nodes:
                if node.type == NodeType.CONTROL:
                    expected_name = f"{node.name}_is_active"
                    if assumption.name == expected_name or assumption.id == f"ctrl_assumption_{node.id}":
                        is_active = assumption.active and assumption.id not in disabled
                        constraints.append(
                            self.get_var(node.id) == BoolVal(is_active)
                        )

        return constraints

    # ── Goal Encoding ────────────────────────────────────────────────────

    def _encode_goal(self, goal: GoalPredicate) -> BoolRef:
        """Encode a goal predicate as a Z3 formula.
        
        Goal is achieved if ALL target assets are compromised AND
        ALL required conditions are met.
        """
        conditions = []

        for asset_id in goal.target_assets:
            conditions.append(self.get_var(asset_id))

        for condition_id in goal.required_conditions:
            conditions.append(self.get_var(condition_id))

        if len(conditions) == 0:
            return BoolVal(False)
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return And(*conditions)

    # ── Core Solving ─────────────────────────────────────────────────────

    def check_satisfiability(
        self,
        goal: GoalPredicate,
        interventions: dict[str, bool] | None = None,
        extra_constraints: list[BoolRef] | None = None,
    ) -> SolverResult:
        """Check if a goal is satisfiable under the current SCM.
        
        Returns SAT if the goal CAN be achieved (attacker wins).
        Returns UNSAT if the goal CANNOT be achieved (defender wins).
        """
        start = time.perf_counter()
        solver = Solver()
        solver.set("timeout", self.timeout_ms)

        # Add SCM structural equations
        for c in self._encode_scm(interventions):
            solver.add(c)

        # Add exogenous constraints
        for c in self._encode_exogenous_constraints(interventions):
            solver.add(c)

        # Assert the goal
        goal_formula = self._encode_goal(goal)
        solver.add(goal_formula)

        # Extra constraints (for MCS computation, etc.)
        if extra_constraints:
            for c in extra_constraints:
                solver.add(c)

        # Solve
        result = solver.check()
        elapsed = (time.perf_counter() - start) * 1000

        if result == sat:
            model = solver.model()
            witness = self._extract_witness(model)
            return SolverResult(
                status=SolverStatus.SAT,
                witness=witness,
                solve_time_ms=elapsed,
            )
        elif result == unsat:
            return SolverResult(
                status=SolverStatus.UNSAT,
                solve_time_ms=elapsed,
            )
        else:
            return SolverResult(
                status=SolverStatus.TIMEOUT,
                solve_time_ms=elapsed,
            )

    def _extract_witness(self, model: ModelRef) -> dict:
        """Extract a satisfying assignment (witness) from a Z3 model."""
        witness = {}
        for var_name, var in self._z3_vars.items():
            val = model.evaluate(var, model_completion=True)
            witness[var_name] = str(val) == "True"
        return witness

    # ── Inevitability Computation ─────────────────────────────────────────

    def compute_inevitability(
        self,
        goal: GoalPredicate,
        interventions: dict[str, bool] | None = None,
    ) -> InevitabilityResult:
        """Compute the inevitability score for a goal.
        
        Score methodology:
        1. Check if goal is SAT under default conditions → base reachability
        2. Enumerate exogenous configurations to estimate inevitability fraction
        3. For each identity (potential attacker entry point), check if goal is achievable
        
        Score = (number of entry points that enable the goal) / (total entry points)
        
        This maps to: "what fraction of realistic attacker starting positions
        make the goal achievable?"
        """
        # Step 1: Check base satisfiability
        base_result = self.check_satisfiability(goal, interventions)

        if base_result.status == SolverStatus.UNSAT:
            return InevitabilityResult(
                goal_id=goal.id,
                goal_name=goal.name,
                score=0.0,
                is_inevitable=False,
                solver_result=base_result,
            )

        # Step 2: Compute inevitability score via entry point analysis
        identities = [
            n for n in self.scm.graph.nodes
            if n.type == NodeType.IDENTITY
        ]

        if not identities:
            # No identities → if SAT, it's fully inevitable
            return InevitabilityResult(
                goal_id=goal.id,
                goal_name=goal.name,
                score=1.0 if base_result.status == SolverStatus.SAT else 0.0,
                is_inevitable=base_result.status == SolverStatus.SAT,
                witness_path=self._extract_attack_path(base_result.witness, goal) if base_result.witness else None,
                solver_result=base_result,
            )

        # Test each identity as a starting point
        achievable_count = 0
        for identity in identities:
            # Intervene: only this identity is compromised
            test_interventions = dict(interventions or {})
            for other in identities:
                if other.id != identity.id:
                    test_interventions[other.id] = False
            test_interventions[identity.id] = True

            result = self.check_satisfiability(goal, test_interventions)
            if result.status == SolverStatus.SAT:
                achievable_count += 1

        # Also check "any identity compromised" scenario
        score = achievable_count / len(identities) if identities else 0.0

        # Amplify score based on base reachability and structural factors
        # If the base case is SAT with all identities available, the score is higher
        if base_result.status == SolverStatus.SAT:
            score = max(score, 0.3)  # Minimum if achievable at all

        # Boost for lack of controls
        controls = self.scm.graph.get_controls()
        active_controls_on_path = 0
        for ctrl in controls:
            children = self.scm.graph.get_children(ctrl.id)
            for asset_id in goal.target_assets:
                if asset_id in children:
                    active_controls_on_path += 1

        if active_controls_on_path == 0 and base_result.status == SolverStatus.SAT:
            score = max(score, 0.8)  # Very high if no controls defend the target

        return InevitabilityResult(
            goal_id=goal.id,
            goal_name=goal.name,
            score=round(score, 2),
            is_inevitable=score >= goal.threshold,
            witness_path=self._extract_attack_path(base_result.witness, goal) if base_result.witness else None,
            solver_result=base_result,
        )

    def _extract_attack_path(self, witness: dict, goal: GoalPredicate) -> list[str]:
        """Extract the attack path from a witness (satisfying assignment)."""
        if not witness:
            return []

        path = []
        # Find the true nodes in the witness that lead to the goal
        for target_id in goal.target_assets:
            self._trace_path(target_id, witness, path, set())

        return path

    def _trace_path(self, node_id: str, witness: dict, path: list[str], visited: set):
        """Recursively trace the attack path backward from a goal target."""
        if node_id in visited:
            return
        visited.add(node_id)

        if not witness.get(node_id, False):
            return

        # Find parents that are true in the witness
        parents = self.scm.graph.get_parents(node_id)
        for parent_id in parents:
            if witness.get(parent_id, False):
                self._trace_path(parent_id, witness, path, visited)

        node = self.scm.graph.get_node(node_id)
        if node:
            path.append(node.name)

    # ── Intervention (do-operator) ────────────────────────────────────────

    def apply_do_operator(
        self,
        variable_id: str,
        value: bool,
        existing_interventions: dict[str, bool] | None = None,
    ) -> dict[str, bool]:
        """Apply do-operator: do(variable := value).
        
        Returns a new intervention dict with the added intervention.
        """
        interventions = dict(existing_interventions or {})
        interventions[variable_id] = value
        return interventions

    def compute_inevitability_with_interventions(
        self,
        goal: GoalPredicate,
        interventions: dict[str, bool],
    ) -> InevitabilityResult:
        """Compute inevitability under a set of interventions."""
        return self.compute_inevitability(goal, interventions)
