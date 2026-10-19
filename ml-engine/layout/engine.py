"""
Diagram Layout Engine.
Modular coordinator that selects and executes appropriate geometric layout algorithms
for DiagramGraph intermediate representation objects.
"""

from typing import Optional, Dict, Any, Type
import logging

from ir.models import DiagramGraph, DiagramType
from .models import LayoutOptions, LayoutStrategy, LayoutResult, BoundingBox
from .strategies import (
    BaseLayoutStrategy,
    FlowchartLayoutStrategy,
    ArchitectureLayoutStrategy,
    ConceptMapLayoutStrategy,
    SequenceDiagramLayoutStrategy,
    ERDiagramLayoutStrategy,
    NetworkTopologyLayoutStrategy,
    DependencyGraphLayoutStrategy,
)

logger = logging.getLogger(__name__)


class DiagramLayoutEngine:
    """
    Coordinates diagram-specific layout strategies.
    Applies calculated geometric coordinates to DiagramNodes without altering graph semantics.
    """

    DEFAULT_STRATEGY_MAP: Dict[DiagramType, Type[BaseLayoutStrategy]] = {
        DiagramType.FLOWCHART: FlowchartLayoutStrategy,
        DiagramType.ARCHITECTURE: ArchitectureLayoutStrategy,
        DiagramType.CONCEPT_MAP: ConceptMapLayoutStrategy,
        DiagramType.SEQUENCE_DIAGRAM: SequenceDiagramLayoutStrategy,
        DiagramType.ER_DIAGRAM: ERDiagramLayoutStrategy,
        DiagramType.NETWORK_TOPOLOGY: NetworkTopologyLayoutStrategy,
        DiagramType.DEPENDENCY_GRAPH: DependencyGraphLayoutStrategy,
        # Code-to-Diagram specialized families
        DiagramType.CODE_FLOW: FlowchartLayoutStrategy,
        DiagramType.CODE_CALL_GRAPH: ArchitectureLayoutStrategy,
        DiagramType.CODE_DATA_FLOW: FlowchartLayoutStrategy,
        DiagramType.CODE_CLASS_HIERARCHY: ArchitectureLayoutStrategy,
    }

    STRATEGY_REGISTRY: Dict[LayoutStrategy, Type[BaseLayoutStrategy]] = {
        LayoutStrategy.LAYERED_SUGIYAMA: FlowchartLayoutStrategy,
        LayoutStrategy.HIERARCHICAL_TIERED: ArchitectureLayoutStrategy,
        LayoutStrategy.FORCE_DIRECTED: ConceptMapLayoutStrategy,
        LayoutStrategy.TIMELINE_LIFELINE: SequenceDiagramLayoutStrategy,
        LayoutStrategy.ORTHOGONAL_GRID: ERDiagramLayoutStrategy,
        LayoutStrategy.CLUSTER_TOPOLOGY: NetworkTopologyLayoutStrategy,
        LayoutStrategy.STRICT_DAG: DependencyGraphLayoutStrategy,
    }

    @classmethod
    def layout(
        cls,
        graph: DiagramGraph,
        options: Optional[LayoutOptions] = None,
        strategy: Optional[LayoutStrategy] = None
    ) -> DiagramGraph:
        """
        Computes 2D canvas coordinates for all nodes in graph and updates their positions.
        Returns a new DiagramGraph instance with populated LayoutCoordinate positions
        and layout_config metadata.

        Preserves all node IDs, labels, edges, and semantic attributes untouched.
        """
        opts = options or LayoutOptions()

        # Select strategy class
        strat_cls: Type[BaseLayoutStrategy]
        if strategy is not None:
            strat_cls = cls.STRATEGY_REGISTRY.get(strategy, FlowchartLayoutStrategy)
        else:
            strat_cls = cls.DEFAULT_STRATEGY_MAP.get(graph.diagram_type, FlowchartLayoutStrategy)

        instance = strat_cls()

        # Compute coordinates
        try:
            node_coords = instance.compute_layout(graph, opts)
        except Exception as e:
            logger.warning(
                f"Layout computation with {strat_cls.__name__} failed: {e}. Falling back to default grid."
            )
            instance = FlowchartLayoutStrategy()
            node_coords = instance.compute_layout(graph, opts)

        # Compute bounding box
        bbox = instance.compute_bounding_box(node_coords, opts)

        # Clone graph and attach positions
        cloned_nodes = []
        for node in graph.nodes:
            node_copy = node.model_copy(deep=True)
            if node.id in node_coords:
                node_copy.position = node_coords[node.id]
            cloned_nodes.append(node_copy)

        layout_config = {
            "strategy": instance.strategy.value,
            "canvas_width": round(bbox.width + opts.canvas_padding * 2, 2),
            "canvas_height": round(bbox.height + opts.canvas_padding * 2, 2),
            "bounding_box": {
                "min_x": round(bbox.min_x, 2),
                "min_y": round(bbox.min_y, 2),
                "max_x": round(bbox.max_x, 2),
                "max_y": round(bbox.max_y, 2),
            },
            "direction": opts.direction,
        }

        return DiagramGraph(
            id=graph.id,
            diagram_type=graph.diagram_type,
            version=graph.version,
            nodes=cloned_nodes,
            edges=[e.model_copy(deep=True) for e in graph.edges],
            metadata=graph.metadata.model_copy(deep=True),
            warnings=list(graph.warnings),
            layout_config=layout_config,
        )
