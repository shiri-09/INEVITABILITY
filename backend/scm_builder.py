"""
INEVITABILITY - Structural Causal Model Builder
Transforms infrastructure graphs into formal Structural Causal Models (SCMs).
"""

from __future__ import annotations
import networkx as nx
from .models import (
    CausalGraph, SCM, InfraNode, InfraEdge, StructuralEquation,
    Assumption, NodeType, EdgeType, ConstraintType
)


class SCMBuilder:
    """Builds a Structural Causal Model from an infrastructure causal graph."""

    def __init__(self, graph: CausalGraph):
        self.graph = graph
        self._nx_graph: nx.DiGraph | None = None

    def build(self) -> SCM:
        """Full SCM construction pipeline."""
        self._validate_graph()
        self._nx_graph = self._to_networkx()
        equations = self._generate_equations()
        assumptions = self._extract_assumptions()
        exogenous = self._compute_exogenous_constraints()

        # Build node metadata lookup for advanced features
        node_meta = {}
        for node in self.graph.nodes:
            node_meta[node.id] = node

        return SCM(
            graph=self.graph,
            equations=equations,
            assumptions=assumptions,
            exogenous_constraints=exogenous,
            node_metadata=node_meta,
        )

    # ── Graph Validation ──────────────────────────────────────────────────

    def _validate_graph(self):
        """Ensure graph is a valid DAG (acyclic)."""
        g = self._to_networkx()
        if not nx.is_directed_acyclic_graph(g):
            cycles = list(nx.simple_cycles(g))
            raise ValueError(
                f"Causal graph contains cycles — SCM requires a DAG. "
                f"Cycles found: {cycles[:3]}"
            )

    # ── Networkx Conversion ───────────────────────────────────────────────

    def _to_networkx(self) -> nx.DiGraph:
        """Convert CausalGraph to networkx DiGraph for analysis."""
        g = nx.DiGraph()
        for node in self.graph.nodes:
            g.add_node(node.id, **{
                "type": node.type.value,
                "name": node.name,
                "control_state": node.control_state.value if node.control_state else None,
                "annual_cost": node.annual_cost,
            })
        for edge in self.graph.edges:
            g.add_edge(edge.source, edge.target, **{
                "edge_type": edge.edge_type.value,
                "label": edge.label,
                "constraint_type": edge.constraint.type.value,
                "weight": edge.weight,
            })
        return g

    # ── Structural Equations ──────────────────────────────────────────────

    def _generate_equations(self) -> list[StructuralEquation]:
        """Generate structural equations for each endogenous variable.
        
        For each node with parents, we create a structural equation:
        - ACCESS edges: target is reachable IF source has access AND no blocking control
        - CONTROL edges: target is defended IF control is active
        - PRIVILEGE edges: target gains privilege IF source provides it
        - ESCALATION: target gains elevated access IF source allows escalation
        """
        equations = []

        for node in self.graph.nodes:
            parents = self.graph.get_parents(node.id)
            if not parents:
                continue  # Exogenous variable (no parents)

            incoming_edges = self.graph.get_edges_to(node.id)

            # Identify control edges (negated — they BLOCK the goal)
            control_parents = []
            enabling_parents = []

            for edge in incoming_edges:
                source_node = self.graph.get_node(edge.source)
                if source_node and source_node.type == NodeType.CONTROL:
                    if edge.edge_type == EdgeType.CONTROL:
                        control_parents.append(edge.source)
                    else:
                        enabling_parents.append(edge.source)
                else:
                    enabling_parents.append(edge.source)

            # Determine equation type
            if node.type == NodeType.ASSET:
                # Asset compromise = ANY parent access AND NOT ALL controls
                eq_type = "boolean_conjunction"
            elif node.type == NodeType.PRIVILEGE:
                # Privilege = source identity AND enabling conditions
                eq_type = "boolean_conjunction"
            else:
                eq_type = "boolean_conjunction"

            eq = StructuralEquation(
                target_variable=node.id,
                parent_variables=enabling_parents,
                equation_type=eq_type,
                negated_parents=control_parents,
            )
            equations.append(eq)

        return equations

    # ── Assumption Extraction ─────────────────────────────────────────────

    def _extract_assumptions(self) -> list[Assumption]:
        """Extract assumptions from edge constraints and node properties."""
        assumptions = []
        seen = set()

        for edge in self.graph.edges:
            for assumption_text in edge.constraint.assumptions:
                if assumption_text not in seen:
                    seen.add(assumption_text)
                    assumptions.append(Assumption(
                        id=f"assumption_{len(assumptions)}",
                        name=assumption_text,
                        description=f"Assumed by edge {edge.label or edge.id}",
                        active=True,
                    ))

        # Add implicit assumptions from control states
        for node in self.graph.nodes:
            if node.type == NodeType.CONTROL and node.control_state:
                assumption_text = f"{node.name}_is_{node.control_state.value}"
                if assumption_text not in seen:
                    seen.add(assumption_text)
                    assumptions.append(Assumption(
                        id=f"ctrl_assumption_{node.id}",
                        name=assumption_text,
                        description=f"Control {node.name} state assumption",
                        category="config",
                        active=True,
                    ))

        # Add implicit assumptions from identity properties
        for node in self.graph.nodes:
            if node.type == NodeType.IDENTITY and node.mfa_enabled is not None:
                tag = "mfa_enabled" if node.mfa_enabled else "mfa_disabled"
                assumption_text = f"{node.name}_{tag}"
                if assumption_text not in seen:
                    seen.add(assumption_text)
                    assumptions.append(Assumption(
                        id=f"mfa_assumption_{node.id}",
                        name=assumption_text,
                        description=f"MFA status for {node.name}",
                        category="config",
                        active=True,
                    ))

        return assumptions

    # ── Exogenous Constraints ─────────────────────────────────────────────

    def _compute_exogenous_constraints(self) -> dict:
        """Compute constraints on exogenous (root-level) variables."""
        constraints = {}

        for node in self.graph.nodes:
            parents = self.graph.get_parents(node.id)
            if not parents:
                # This is an exogenous variable
                constraints[node.id] = {
                    "type": node.type.value,
                    "name": node.name,
                    "range": "boolean",
                    "default": True if node.type == NodeType.IDENTITY else None,
                }

        return constraints

    # ── Utility ───────────────────────────────────────────────────────────

    def get_topological_order(self) -> list[str]:
        """Return node IDs in topological order."""
        if self._nx_graph is None:
            self._nx_graph = self._to_networkx()
        return list(nx.topological_sort(self._nx_graph))

    def get_backward_slice(self, target_id: str) -> set[str]:
        """Get all ancestors of a target node (backward causal slice)."""
        if self._nx_graph is None:
            self._nx_graph = self._to_networkx()
        return nx.ancestors(self._nx_graph, target_id) | {target_id}
