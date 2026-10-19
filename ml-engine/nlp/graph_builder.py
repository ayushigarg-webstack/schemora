"""
Graph Construction Module.
Synthesizes raw DiagramNode and DiagramEdge objects from extracted entities and relations.
Guarantees referential integrity, eliminates dangling edges, and assigns initial styles.
"""

from typing import List, Dict, Set, Tuple, Optional, Any
from ir.models import (
    DiagramNode,
    DiagramEdge,
    NodeShape,
    NodeStyle,
)
from .entity_extractor import ExtractedEntity
from .relation_extractor import ExtractedRelation


# Category to default shape mapping
CATEGORY_SHAPE_MAP: Dict[str, NodeShape] = {
    "client": NodeShape.ROUNDED_RECTANGLE,
    "frontend": NodeShape.ROUNDED_RECTANGLE,
    "service": NodeShape.ROUNDED_RECTANGLE,
    "backend": NodeShape.ROUNDED_RECTANGLE,
    "gateway": NodeShape.ROUNDED_RECTANGLE,
    "database": NodeShape.CYLINDER,
    "cache": NodeShape.CYLINDER,
    "storage": NodeShape.CYLINDER,
    "external_api": NodeShape.CLOUD,
    "cloud": NodeShape.CLOUD,
    "decision": NodeShape.DIAMOND,
    "condition": NodeShape.DIAMOND,
    "terminal": NodeShape.ROUNDED_RECTANGLE,
    "process": NodeShape.ROUNDED_RECTANGLE,
    "concept": NodeShape.ROUNDED_RECTANGLE,
    "entity": NodeShape.RECTANGLE,
    "participant": NodeShape.LIFELINE,
    "host": NodeShape.ROUNDED_RECTANGLE,
    "switch": NodeShape.ROUNDED_RECTANGLE,
    "router": NodeShape.HEXAGON,
    "firewall": NodeShape.RECTANGLE,
    "task": NodeShape.ROUNDED_RECTANGLE,
}


class GraphBuilder:
    """Constructs valid DiagramNode and DiagramEdge IR elements."""

    def __init__(self):
        pass

    def build_elements(
        self,
        entities: List[ExtractedEntity],
        relations: List[ExtractedRelation]
    ) -> Tuple[List[DiagramNode], List[DiagramEdge]]:
        """
        Builds DiagramNode and DiagramEdge collections while verifying referential integrity.
        """
        nodes: List[DiagramNode] = []
        node_ids: Set[str] = set()

        # 1. Build Nodes
        for ent in entities:
            # Avoid duplicate node IDs
            nid = ent.id
            counter = 1
            while nid in node_ids:
                nid = f"{ent.id}_{counter}"
                counter += 1
            node_ids.add(nid)

            # Determine shape and style
            shape = CATEGORY_SHAPE_MAP.get(ent.category.lower(), NodeShape.ROUNDED_RECTANGLE)
            style = NodeStyle(shape=shape)

            node = DiagramNode(
                id=nid,
                label=ent.label,
                type=ent.category,
                attributes=dict(ent.attributes),
                style=style,
                confidence=ent.confidence,
            )
            nodes.append(node)

        # 2. Build Edges (filtering out any dangling edges)
        edges: List[DiagramEdge] = []
        seen_edge_keys: Set[Tuple[str, str, str]] = set()

        for rel in relations:
            # Check source and target exist
            if rel.source_id not in node_ids or rel.target_id not in node_ids:
                continue

            edge_key = (rel.source_id, rel.target_id, rel.relation_type)
            if edge_key in seen_edge_keys:
                continue
            seen_edge_keys.add(edge_key)

            edge = DiagramEdge(
                id=rel.id,
                source=rel.source_id,
                target=rel.target_id,
                label=rel.label,
                edge_type=rel.relation_type,
                directed=rel.directed,
                cardinality=rel.cardinality,
                sequence_order=rel.sequence_order,
                confidence=rel.confidence,
                metadata=dict(rel.metadata),
            )
            edges.append(edge)

        return nodes, edges


def build_raw_graph(
    entities: List[ExtractedEntity],
    relations: List[ExtractedRelation]
) -> Tuple[List[DiagramNode], List[DiagramEdge]]:
    """Convenience helper function for raw graph construction."""
    builder = GraphBuilder()
    return builder.build_elements(entities, relations)
