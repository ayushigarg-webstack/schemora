"""
Generalized Intermediate Representation (IR) Models.
Strongly typed, versioned Pydantic v2 schemas for all diagram families
and code-to-diagram explainer structures.
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field, field_validator, model_validator


class DiagramType(str, Enum):
    """Supported diagram families."""
    FLOWCHART = "flowchart"
    ARCHITECTURE = "architecture"
    CONCEPT_MAP = "concept_map"
    ER_DIAGRAM = "er_diagram"
    SEQUENCE_DIAGRAM = "sequence_diagram"
    NETWORK_TOPOLOGY = "network_topology"
    DEPENDENCY_GRAPH = "dependency_graph"
    # Code-to-Diagram specialized families
    CODE_FLOW = "code_flow"
    CODE_CALL_GRAPH = "code_call_graph"
    CODE_DATA_FLOW = "code_data_flow"
    CODE_CLASS_HIERARCHY = "code_class_hierarchy"


class NodeShape(str, Enum):
    """Visual rendering shapes for diagram nodes."""
    RECTANGLE = "rectangle"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    DIAMOND = "diamond"
    CYLINDER = "cylinder"
    CIRCLE = "circle"
    PARALLELOGRAM = "parallelogram"
    HEXAGON = "hexagon"
    CLOUD = "cloud"
    LIFELINE = "lifeline"


class SourceLocation(BaseModel):
    """
    Bidirectional source code mapping.
    Links diagram nodes to exact source code positions.
    """
    file_path: Optional[str] = None
    line_start: int = Field(ge=1, description="1-indexed starting line number")
    line_end: int = Field(ge=1, description="1-indexed ending line number")
    col_start: Optional[int] = Field(default=None, ge=0, description="0-indexed column start")
    col_end: Optional[int] = Field(default=None, ge=0, description="0-indexed column end")
    symbol_name: Optional[str] = None
    scope: Optional[str] = None
    code_snippet: Optional[str] = None

    @model_validator(mode="after")
    def validate_line_range(self) -> "SourceLocation":
        if self.line_end < self.line_start:
            raise ValueError(f"line_end ({self.line_end}) cannot be less than line_start ({self.line_start})")
        return self


class ExecutionStateSnapshot(BaseModel):
    """
    Runtime execution state recorded during step-by-step code tracing.
    """
    step_id: int = Field(ge=0, description="Sequential step index in execution trace")
    line_number: int = Field(ge=1, description="Active line being executed")
    event_type: str = Field(default="line", description="Trace event: line, call, return, exception")
    function_name: Optional[str] = None
    call_stack: List[str] = Field(default_factory=list, description="Active call stack frames")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Snapshot of local variables")
    is_runtime_observed: bool = Field(default=True, description="True if captured from execution, False if static")
    explanation: Optional[str] = Field(default=None, description="Plain-English explanation of this step")


class LayoutCoordinate(BaseModel):
    """Geometric coordinates and dimensions calculated by layout engines."""
    x: float = 0.0
    y: float = 0.0
    width: Optional[float] = None
    height: Optional[float] = None
    rank: Optional[int] = None


class NodeStyle(BaseModel):
    """Styling metadata for node rendering."""
    color: Optional[str] = None
    fill: Optional[str] = None
    border_style: Optional[str] = "solid"
    shape: Optional[NodeShape] = NodeShape.ROUNDED_RECTANGLE
    icon: Optional[str] = None


class DiagramNode(BaseModel):
    """
    Universal Diagram Node representation.
    Supports system components, flowchart steps, DB entities, and code AST elements.
    """
    id: str = Field(min_length=1, description="Unique node identifier within graph")
    label: str = Field(min_length=1, description="Human-readable display text")
    type: str = Field(min_length=1, description="Semantic node type specific to diagram family")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific attributes")
    group_id: Optional[str] = Field(default=None, description="Identifier of parent cluster/subnet/class")
    source_location: Optional[SourceLocation] = Field(default=None, description="Code mapping if code-derived")
    execution_state: Optional[ExecutionStateSnapshot] = Field(default=None, description="Active trace state")
    position: Optional[LayoutCoordinate] = Field(default=None, description="Canvas layout coordinates")
    style: Optional[NodeStyle] = Field(default=None, description="Visual styling configuration")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Extraction confidence score")

    @field_validator("id", "label", "type")
    @classmethod
    def strip_and_validate_nonempty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or pure whitespace")
        return s


class DiagramEdge(BaseModel):
    """
    Universal Diagram Edge representation.
    Supports procedural flow, API calls, data access, database relations, and call graphs.
    """
    id: str = Field(min_length=1, description="Unique edge identifier")
    source: str = Field(min_length=1, description="Source node id")
    target: str = Field(min_length=1, description="Target node id")
    label: Optional[str] = Field(default=None, description="Edge label or branch condition")
    edge_type: str = Field(default="default", description="Semantic edge type specific to diagram family")
    directed: bool = Field(default=True, description="Whether the relation is directed")
    cardinality: Optional[str] = Field(default=None, description="Database relation cardinality (e.g. 1:1, 1:N, M:N)")
    sequence_order: Optional[int] = Field(default=None, ge=0, description="Chronological sequence order for sequence diagrams")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional relationship metadata")
    style: Optional[Dict[str, Any]] = Field(default=None, description="Visual line/arrow styling")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Relationship extraction confidence")

    @field_validator("id", "source", "target")
    @classmethod
    def strip_and_validate_identifiers(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Identifier cannot be empty or pure whitespace")
        return s


class ValidationWarning(BaseModel):
    """Non-fatal structural or architectural caution."""
    code: str = Field(description="Unique warning code e.g. W_DIRECT_DB_ACCESS")
    message: str = Field(description="Actionable explanation of the warning")
    level: str = Field(default="warning", description="info, warning, or caution")
    element_id: Optional[str] = Field(default=None, description="Affected node or edge ID")


class ValidationErrorDetail(BaseModel):
    """Fatal structural or semantic validation error."""
    code: str = Field(description="Unique error code e.g. E_DANGLING_EDGE")
    message: str = Field(description="Detailed error explanation")
    element_id: Optional[str] = Field(default=None, description="Affected node or edge ID")


class ValidationReport(BaseModel):
    """Complete validation outcome with status, errors, warnings, and graph metrics."""
    is_valid: bool
    diagram_type: DiagramType
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
    warnings: List[ValidationWarning] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class DiagramMetadata(BaseModel):
    """Provenance, domain classification, and execution parameters."""
    title: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    template_id: Optional[str] = None
    complexity: Optional[str] = "medium"
    provenance: str = "user_input"
    version: str = "2.0.0"
    created_at: Optional[str] = None
    is_code_derived: bool = False
    source_language: Optional[str] = None


class DiagramGraph(BaseModel):
    """
    Generalized Diagram Graph Intermediate Representation (IR).
    Core interchange format between NLP extraction, AST parsing, layout engines, and frontend canvas.
    """
    id: Optional[str] = None
    diagram_type: DiagramType
    version: str = "2.0.0"
    nodes: List[DiagramNode] = Field(default_factory=list)
    edges: List[DiagramEdge] = Field(default_factory=list)
    metadata: DiagramMetadata = Field(default_factory=DiagramMetadata)
    warnings: List[ValidationWarning] = Field(default_factory=list)
    layout_config: Optional[Dict[str, Any]] = Field(default=None, description="Layout configuration and bounding dimensions")

    @field_validator("diagram_type", mode="before")
    @classmethod
    def parse_diagram_type(cls, v: Any) -> DiagramType:
        if isinstance(v, DiagramType):
            return v
        if isinstance(v, str):
            clean_str = v.strip().lower()
            for member in DiagramType:
                if member.value == clean_str:
                    return member
            raise ValueError(f"Unsupported diagram_type '{v}'")
        raise ValueError(f"diagram_type must be a string or DiagramType enum, got {type(v)}")

    def get_node(self, node_id: str) -> Optional[DiagramNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_outgoing_edges(self, node_id: str) -> List[DiagramEdge]:
        return [e for e in self.edges if e.source == node_id]

    def get_incoming_edges(self, node_id: str) -> List[DiagramEdge]:
        return [e for e in self.edges if e.target == node_id]

    def node_ids(self) -> Set[str]:
        return {n.id for n in self.nodes}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiagramGraph":
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> "DiagramGraph":
        return cls.model_validate_json(json_str)
