"""
INEVITABILITY - Explainability Layer
Generates deterministic, verifiable explanations from causal graph structure.
No LLM generation — every claim maps to a formal proof artifact.
"""

from __future__ import annotations
from .models import (
    SCM, GoalPredicate, ExplanationTree, ExplanationStep,
    InevitabilityResult, MCSResult, TheaterReport,
    NodeType, DefenseClassification
)


class ExplainabilityEngine:
    """Generates human-readable explanations from structural analysis."""

    def __init__(self, scm: SCM):
        self.scm = scm

    def generate_explanation(
        self,
        goal: GoalPredicate,
        inevitability: InevitabilityResult,
        mcs: MCSResult | None = None,
        theater: TheaterReport | None = None,
    ) -> ExplanationTree:
        """Generate a full explanation tree for an analysis result."""
        # Determine finding
        if inevitability.is_inevitable:
            finding = f"STRUCTURALLY INEVITABLE (score: {inevitability.score:.2f})"
        elif inevitability.score > 0.4:
            finding = f"AT RISK (score: {inevitability.score:.2f})"
        else:
            finding = f"DEFENDED (score: {inevitability.score:.2f})"

        # Generate causal chain
        causal_chain = self._trace_causal_chain(goal, inevitability)

        # MCS explanation
        mcs_explanation = ""
        if mcs and mcs.mcs_sets:
            best_mcs = mcs.mcs_sets[0]
            controls = ", ".join(e.control_name for e in best_mcs.elements)
            mcs_explanation = (
                f"MINIMUM DEFENSE (MCS): Implement [{controls}] "
                f"(cost: ${best_mcs.total_cost:,.0f}) to block this goal."
            )

        # Theater summary
        theater_summary = []
        if theater:
            for c in theater.classifications:
                if c.classification == DefenseClassification.IRRELEVANT:
                    theater_summary.append(
                        f"✗ {c.control_name} — {c.reason}"
                    )

        return ExplanationTree(
            goal_name=goal.name,
            finding=finding,
            inevitability_score=inevitability.score,
            causal_chain=causal_chain,
            mcs_explanation=mcs_explanation,
            theater_summary=theater_summary,
        )

    def _trace_causal_chain(
        self,
        goal: GoalPredicate,
        inevitability: InevitabilityResult,
    ) -> list[ExplanationStep]:
        """Trace the causal chain backward from goal to initial conditions."""
        steps = []
        witness = inevitability.solver_result.witness if inevitability.solver_result else None

        if not witness:
            # Generate a generic chain from graph structure
            return self._generate_structural_chain(goal)

        # Trace from goal targets backward through true nodes in the witness
        visited = set()
        for target_id in goal.target_assets:
            self._backward_trace(target_id, witness, steps, visited)

        # Number the steps
        for i, step in enumerate(steps):
            step.step_number = i + 1

        return steps

    def _backward_trace(
        self,
        node_id: str,
        witness: dict,
        steps: list[ExplanationStep],
        visited: set,
    ):
        """Recursively trace backward through the causal graph."""
        if node_id in visited:
            return
        visited.add(node_id)

        node = self.scm.graph.get_node(node_id)
        if not node:
            return

        # Get parents that contribute to this node being true
        incoming = self.scm.graph.get_edges_to(node_id)
        contributing_parents = []

        for edge in incoming:
            source = self.scm.graph.get_node(edge.source)
            if source and witness.get(edge.source, False):
                contributing_parents.append((source, edge))

        for parent, edge in contributing_parents:
            # Recurse deeper first (build chain from root to goal)
            self._backward_trace(parent.id, witness, steps, visited)

        # Add this node's step
        if contributing_parents:
            parent_names = [p.name for p, _ in contributing_parents]
            edge_labels = [e.label or e.edge_type.value for _, e in contributing_parents]

            statement = self._format_step(node, contributing_parents)
            steps.append(ExplanationStep(
                step_number=0,
                statement=statement,
                evidence_type=edge_labels[0] if edge_labels else "",
                source_node=contributing_parents[0][0].id if contributing_parents else None,
                target_node=node_id,
            ))

    def _format_step(self, node, parents: list) -> str:
        """Format a single explanation step in human-readable language."""
        if node.type == NodeType.ASSET:
            parent_descs = " AND ".join(
                f"'{p.name}' provides {e.edge_type.value} via '{e.label or 'direct'}'"
                for p, e in parents
            )
            return f"BECAUSE {parent_descs}, '{node.name}' is compromised"

        elif node.type == NodeType.PRIVILEGE:
            if parents:
                p, e = parents[0]
                return f"BECAUSE '{p.name}' has {e.edge_type.value} to '{node.name}'"
            return f"'{node.name}' privilege is available"

        elif node.type == NodeType.CHANNEL:
            if parents:
                p, e = parents[0]
                return f"BECAUSE '{p.name}' enables network path to '{node.name}'"
            return f"'{node.name}' channel is open"

        else:
            if parents:
                p, e = parents[0]
                return f"BECAUSE '{p.name}' enables '{node.name}' via {e.edge_type.value}"
            return f"'{node.name}' is active"

    def _generate_structural_chain(self, goal: GoalPredicate) -> list[ExplanationStep]:
        """Generate chain from graph structure when no witness is available."""
        steps = []
        step_num = 1

        for target_id in goal.target_assets:
            node = self.scm.graph.get_node(target_id)
            if not node:
                continue

            # Walk backward from target
            current = target_id
            visited = set()
            chain = []

            while current and current not in visited:
                visited.add(current)
                current_node = self.scm.graph.get_node(current)
                if current_node:
                    chain.append(current_node)
                parents = self.scm.graph.get_parents(current)
                current = parents[0] if parents else None

            # Reverse to get root-to-goal order
            chain.reverse()

            for i, cn in enumerate(chain):
                if i == 0:
                    statement = f"STARTING FROM '{cn.name}' ({cn.type.value})"
                elif i == len(chain) - 1:
                    statement = f"THEREFORE '{cn.name}' is achievable"
                else:
                    statement = f"THROUGH '{cn.name}' ({cn.type.value})"

                steps.append(ExplanationStep(
                    step_number=step_num,
                    statement=statement,
                    source_node=chain[i - 1].id if i > 0 else None,
                    target_node=cn.id,
                ))
                step_num += 1

        return steps

    def format_text_report(self, explanation: ExplanationTree) -> str:
        """Format explanation as a human-readable text report."""
        lines = [
            f"INEVITABILITY ANALYSIS: {explanation.goal_name}",
            "",
            f"FINDING: {explanation.finding}",
            "",
            "CAUSAL CHAIN:",
        ]

        for step in explanation.causal_chain:
            lines.append(f"  {step.step_number}. {step.statement}")

        if explanation.mcs_explanation:
            lines.append("")
            lines.append(explanation.mcs_explanation)

        if explanation.theater_summary:
            lines.append("")
            lines.append("SECURITY THEATER (controls that DO NOT MATTER for this goal):")
            for item in explanation.theater_summary:
                lines.append(f"  {item}")

        return "\n".join(lines)
