"""
INEVITABILITY - Core Data Models
Pydantic models for the Structural Causal Model (SCM) based cybersecurity analysis engine.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import uuid


# ─── Enums ────────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    ASSET = "asset"
    IDENTITY = "identity"
    PRIVILEGE = "privilege"
    CONTROL = "control"
    CHANNEL = "channel"
    TRUST_BOUNDARY = "trust_boundary"


class EdgeType(str, Enum):
    ACCESS = "access"
    PRIVILEGE = "privilege"
    ESCALATION = "escalation"
    LATERAL = "lateral"
    CONTROL = "control"
    TRUST = "trust"
    DEPENDENCY = "dependency"


class ConstraintType(str, Enum):
    DETERMINISTIC = "deterministic"
    CONDITIONAL = "conditional"
    INFERRED = "inferred"


class ControlState(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class DefenseClassification(str, Enum):
    CRITICAL = "critical"
    NECESSARY = "necessary"
    PARTIAL = "partial"
    IRRELEVANT = "irrelevant"


class GoalTemplate(str, Enum):
    DATA_EXFILTRATION = "data_exfiltration"
    DOMAIN_ADMIN = "domain_admin"
    RANSOMWARE = "ransomware"
    SUPPLY_CHAIN = "supply_chain"
    PERSISTENT_BACKDOOR = "persistent_backdoor"
    CUSTOM = "custom"


class Criticality(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SolverStatus(str, Enum):
    SAT = "sat"
    UNSAT = "unsat"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class FragilityGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


# ─── Infrastructure Nodes ────────────────────────────────────────────────────

class InfraNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: NodeType
    name: str
    description: str = ""
    properties: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    confidence: float = 1.0

    # Control-specific fields
    control_state: Optional[ControlState] = None
    annual_cost: Optional[float] = None
    control_type: Optional[str] = None

    # Identity-specific fields
    privilege_level: Optional[str] = None
    mfa_enabled: Optional[bool] = None

    # Asset-specific fields
    criticality: Optional[Criticality] = None
    data_classification: Optional[list[str]] = None


class EdgeConstraint(BaseModel):
    type: ConstraintType = ConstraintType.DETERMINISTIC
    preconditions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class InfraEdge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str  # Node ID
    target: str  # Node ID
    edge_type: EdgeType
    label: str = ""
    constraint: EdgeConstraint = Field(default_factory=EdgeConstraint)
    weight: float = 1.0


# ─── Causal Graph ────────────────────────────────────────────────────────────

class CausalGraph(BaseModel):
    nodes: list[InfraNode] = Field(default_factory=list)
    edges: list[InfraEdge] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    def get_node(self, node_id: str) -> Optional[InfraNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_controls(self) -> list[InfraNode]:
        return [n for n in self.nodes if n.type == NodeType.CONTROL]

    def get_edges_from(self, node_id: str) -> list[InfraEdge]:
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> list[InfraEdge]:
        return [e for e in self.edges if e.target == node_id]

    def get_parents(self, node_id: str) -> list[str]:
        return [e.source for e in self.edges if e.target == node_id]

    def get_children(self, node_id: str) -> list[str]:
        return [e.target for e in self.edges if e.source == node_id]


# ─── Structural Causal Model ────────────────────────────────────────────────

class Assumption(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = "threat"  # threat, config, trust, business
    active: bool = True
    sensitivity: Optional[float] = None


class StructuralEquation(BaseModel):
    target_variable: str
    parent_variables: list[str] = Field(default_factory=list)
    equation_type: str = "boolean_conjunction"  # boolean_conjunction, boolean_disjunction, threshold
    negated_parents: list[str] = Field(default_factory=list)
    smt_encoding: Optional[str] = None


class SCM(BaseModel):
    """Structural Causal Model - core formal representation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    graph: CausalGraph
    equations: list[StructuralEquation] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    exogenous_constraints: dict = Field(default_factory=dict)
    node_metadata: dict = Field(default_factory=dict)
    version: str = "1.0"


# ─── Goal Predicates ─────────────────────────────────────────────────────────

class GoalPredicate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    template: GoalTemplate = GoalTemplate.CUSTOM
    target_assets: list[str] = Field(default_factory=list)
    required_conditions: list[str] = Field(default_factory=list)
    priority: Criticality = Criticality.HIGH
    threshold: float = 0.7  # Inevitability threshold for "defended"


# ─── Solver Results ──────────────────────────────────────────────────────────

class SolverResult(BaseModel):
    status: SolverStatus
    witness: Optional[dict] = None
    unsat_core: Optional[list[str]] = None
    solve_time_ms: float = 0.0
    solver_used: str = "z3"


class InevitabilityResult(BaseModel):
    goal_id: str
    goal_name: str
    score: float  # 0.0 to 1.0
    is_inevitable: bool  # score > threshold
    witness_path: Optional[list[str]] = None
    solver_result: Optional[SolverResult] = None


# ─── MCS Results ─────────────────────────────────────────────────────────────

class MCSElement(BaseModel):
    control_id: str
    control_name: str
    control_type: Optional[str] = None
    blocked_value: str = "disabled"
    remediation_action: str = ""
    estimated_cost: float = 0.0


class MCSSet(BaseModel):
    mcs_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    elements: list[MCSElement] = Field(default_factory=list)
    cardinality: int = 0
    total_cost: float = 0.0
    feasibility: str = "immediate"
    validated: bool = False


class MCSResult(BaseModel):
    goal_id: str
    goal_name: str
    mcs_sets: list[MCSSet] = Field(default_factory=list)
    computation_time_ms: float = 0.0
    algorithm: str = "greedy"


# ─── Security Theater ────────────────────────────────────────────────────────

class ControlClassification(BaseModel):
    control_id: str
    control_name: str
    control_type: Optional[str] = None
    classification: DefenseClassification
    causal_contribution_score: float = 0.0
    mcs_membership_count: int = 0
    annual_cost: float = 0.0
    reason: str = ""
    recommendation: str = ""


class TheaterReport(BaseModel):
    goal_id: str
    goal_name: str
    classifications: list[ControlClassification] = Field(default_factory=list)
    total_controls: int = 0
    critical_count: int = 0
    necessary_count: int = 0
    partial_count: int = 0
    irrelevant_count: int = 0
    total_waste: float = 0.0
    waste_ratio: float = 0.0


# ─── Economic Impact ─────────────────────────────────────────────────────────

class EconomicReport(BaseModel):
    total_security_spend: float = 0.0
    effective_spend: float = 0.0
    wasted_spend: float = 0.0
    partial_waste: float = 0.0
    waste_ratio: float = 0.0
    efficiency_ratio: float = 0.0
    top_waste_controls: list[ControlClassification] = Field(default_factory=list)
    remediation_recommendations: list[dict] = Field(default_factory=list)
    roi_projections: list[dict] = Field(default_factory=list)


# ─── Proof Artifacts ─────────────────────────────────────────────────────────

class ProofArtifact(BaseModel):
    proof_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proof_type: str  # inevitability, mcs_blocking, mcs_minimality, causal_independence
    claim: str
    formal_statement: str = ""
    goal_id: str = ""
    evidence: dict = Field(default_factory=dict)
    assumptions_in_scope: list[str] = Field(default_factory=list)
    solver_used: str = "z3"
    verification_time_ms: float = 0.0


# ─── Collapse & Fragility ───────────────────────────────────────────────────

class CollapseMetrics(BaseModel):
    control_id: str
    control_name: str
    collapse_radius: int = 0
    total_inevitability_increase: float = 0.0
    single_point_of_failure_count: int = 0
    criticality_rank: float = 0.0


class CollapseFrame(BaseModel):
    step: int
    control_disabled: Optional[str] = None
    label: str = ""
    node_states: dict = Field(default_factory=dict)  # node_id -> {color, score, status}
    goal_states: dict = Field(default_factory=dict)  # goal_id -> {score, status, newly_inevitable}
    narration: str = ""


class FragilityProfile(BaseModel):
    afi: float = 0.0  # Architectural Fragility Index
    grade: FragilityGrade = FragilityGrade.C
    spof_count: int = 0
    high_collapse_controls: int = 0
    mean_mcs_cardinality: float = 0.0
    structural_brittleness: float = 0.0
    anti_patterns: list[dict] = Field(default_factory=list)


# ─── Explanation ─────────────────────────────────────────────────────────────

class ExplanationStep(BaseModel):
    step_number: int
    statement: str
    evidence_type: str = ""  # edge_type, constraint, etc.
    source_node: Optional[str] = None
    target_node: Optional[str] = None
    proof_ref: Optional[str] = None


class ExplanationTree(BaseModel):
    goal_name: str
    finding: str
    inevitability_score: float
    causal_chain: list[ExplanationStep] = Field(default_factory=list)
    mcs_explanation: str = ""
    theater_summary: list[str] = Field(default_factory=list)


# ─── Full Analysis Result ────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scenario_name: str = ""
    inevitability_results: list[InevitabilityResult] = Field(default_factory=list)
    mcs_results: list[MCSResult] = Field(default_factory=list)
    theater_reports: list[TheaterReport] = Field(default_factory=list)
    economic_report: Optional[EconomicReport] = None
    fragility_profile: Optional[FragilityProfile] = None
    collapse_frames: list[CollapseFrame] = Field(default_factory=list)
    explanations: list[ExplanationTree] = Field(default_factory=list)
    proof_artifacts: list[ProofArtifact] = Field(default_factory=list)
    collapse_ranking: list[CollapseMetrics] = Field(default_factory=list)
    scm: Optional[SCM] = None
    computation_time_ms: float = 0.0


# ─── Breach Case Study ──────────────────────────────────────────────────────

class AttackStep(BaseModel):
    step: int
    technique: str = ""
    technique_id: str = ""  # MITRE ATT&CK ID
    description: str = ""
    domain: str = ""  # AD, Azure, AWS, etc.


class BreachCaseStudy(BaseModel):
    breach_id: str
    name: str
    organization: str
    year: int
    timeline: dict = Field(default_factory=dict)
    attack_path: list[AttackStep] = Field(default_factory=list)
    infrastructure_details: dict = Field(default_factory=dict)
    impact: dict = Field(default_factory=dict)
    analysis_result: Optional[AnalysisResult] = None
    headline: str = ""
    data_sources: list[str] = Field(default_factory=list)
