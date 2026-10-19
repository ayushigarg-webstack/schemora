"""
Code-to-Diagram Explainer Bridge & Preparation Interface.
Prepares the data contracts and integration surface for Phase 6 (Code Analysis Engine).
Accepts structured entities, relationships, source locations, and execution snapshots
derived from AST parsers, producing strongly typed DiagramGraph IRs.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from ir.models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramType,
    SourceLocation,
    ExecutionStateSnapshot,
    NodeStyle,
    NodeShape,
    DiagramMetadata,
)
from ir.validators import validate_diagram


class CodeGraphInput(BaseModel):
    """
    Standard interchange structure for code analysis components.
    Will be populated by Phase 6 AST and CFG extractors.
    """
    source_code: str = Field(description="Raw source code snippet")
    language: str = Field(default="python", description="Source code language (python, javascript, typescript)")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted code elements")
    relations: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted relationships")
    execution_snapshots: Optional[List[Dict[str, Any]]] = Field(default=None, description="Execution trace states")


class CodeDiagramBridge:
    """
    Converts structured program analysis data into validated DiagramGraph IRs.
    Enforces SourceLocation line-number constraints and execution snapshot monotonicity.
    """

    @staticmethod
    def build_code_diagram(
        data: CodeGraphInput,
        diagram_type: DiagramType = DiagramType.CODE_FLOW
    ) -> DiagramGraph:
        """
        Builds a validated DiagramGraph from code analysis input.
        """
        nodes: List[DiagramNode] = []
        edges: List[DiagramEdge] = []

        # 1. Map entities to DiagramNode with SourceLocation
        for ent in data.entities:
            nid = ent.get("id", f"node_{len(nodes) + 1}")
            label = ent.get("label", nid)
            ntype = ent.get("type", "statement")

            # Extract source location if provided
            src_loc = None
            if "line_start" in ent and "line_end" in ent:
                src_loc = SourceLocation(
                    line_start=int(ent["line_start"]),
                    line_end=int(ent["line_end"]),
                    col_start=ent.get("col_start"),
                    col_end=ent.get("col_end"),
                    symbol_name=ent.get("symbol_name"),
                    scope=ent.get("scope"),
                    file_path=ent.get("file_path"),
                    code_snippet=ent.get("code_snippet"),
                )

            # Extract execution state if provided
            exec_state = None
            if "execution_state" in ent and isinstance(ent["execution_state"], dict):
                es = ent["execution_state"]
                exec_state = ExecutionStateSnapshot(
                    step_id=int(es.get("step_id", 0)),
                    line_number=int(es.get("line_number", 1)),
                    event_type=es.get("event_type", "line"),
                    function_name=es.get("function_name"),
                    call_stack=es.get("call_stack", []),
                    variables=es.get("variables", {}),
                    is_runtime_observed=es.get("is_runtime_observed", False),
                    explanation=es.get("explanation"),
                )

            # Assign shape based on node type
            shape = NodeShape.ROUNDED_RECTANGLE
            if ntype in ["condition", "decision", "if_branch"]:
                shape = NodeShape.DIAMOND
            elif ntype in ["function", "method"]:
                shape = NodeShape.HEXAGON
            elif ntype in ["class"]:
                shape = NodeShape.RECTANGLE

            node = DiagramNode(
                id=nid,
                label=label,
                type=ntype,
                source_location=src_loc,
                execution_state=exec_state,
                style=NodeStyle(shape=shape),
                attributes=ent.get("attributes", {}),
            )
            nodes.append(node)

        # 2. Map relations to DiagramEdge
        for rel in data.relations:
            edge = DiagramEdge(
                id=rel.get("id", f"edge_{len(edges) + 1}"),
                source=rel["source"],
                target=rel["target"],
                label=rel.get("label"),
                edge_type=rel.get("edge_type", "control_flow"),
                directed=rel.get("directed", True),
                sequence_order=rel.get("sequence_order"),
                metadata=rel.get("metadata", {}),
            )
            edges.append(edge)

        # 3. Assemble DiagramGraph
        meta = DiagramMetadata(
            title="Code Analysis Diagram",
            domain="source_code",
            diagram_type=diagram_type.value,
            provenance="code_analysis_bridge",
            created_at=datetime.now(timezone.utc).isoformat(),
            is_code_derived=True,
            source_language=data.language,
        )

        graph = DiagramGraph(
            id=f"graph_code_{int(datetime.now(timezone.utc).timestamp())}",
            diagram_type=diagram_type,
            nodes=nodes,
            edges=edges,
            metadata=meta,
        )

        # 4. Validate through Phase 2 validators
        report = validate_diagram(graph)
        graph.warnings.extend(report.warnings)

        return graph
