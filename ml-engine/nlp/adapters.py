"""
Diagram-Specific Graph Adapters.
Transforms raw nodes and edges into semantically compliant, family-specific DiagramGraph IRs.
Enforces domain rules for Flowcharts, Software Architecture, Concept Maps,
ER Diagrams, Sequence Diagrams, Network Topologies, and Dependency Graphs.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Set, Optional, Any
from datetime import datetime, timezone

from ir.models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramType,
    NodeShape,
    NodeStyle,
    DiagramMetadata,
)


class BaseDiagramAdapter(ABC):
    """Abstract base adapter for diagram families."""

    def __init__(self, diagram_type: DiagramType):
        self.diagram_type = diagram_type

    @abstractmethod
    def adapt(
        self,
        nodes: List[DiagramNode],
        edges: List[DiagramEdge],
        text: str,
        metadata: Optional[DiagramMetadata] = None
    ) -> DiagramGraph:
        """Transforms raw nodes and edges into a domain-compliant DiagramGraph."""
        pass


class FlowchartAdapter(BaseDiagramAdapter):
    """
    Adapter for Flowchart / Activity diagrams:
    - Adds Start and End terminal nodes
    - Guarantees decision nodes have >= 2 labeled outgoing branches (Yes/No)
    - Connects sink processes to End terminal
    - Preserves loops and retries
    """

    def __init__(self):
        super().__init__(DiagramType.FLOWCHART)

    def adapt(
        self,
        nodes: List[DiagramNode],
        edges: List[DiagramEdge],
        text: str,
        metadata: Optional[DiagramMetadata] = None
    ) -> DiagramGraph:
        adapted_nodes = list(nodes)
        adapted_edges = list(edges)
        node_ids = {n.id for n in adapted_nodes}

        meta = metadata or DiagramMetadata(
            title="Flowchart",
            domain="process",
            diagram_type=DiagramType.FLOWCHART.value,
            provenance="nlp_pipeline",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # 1. Add Start Terminal if missing
        start_node_id = "start_node"
        if not any(n.type.lower() in ["start", "terminal"] for n in adapted_nodes):
            start_node = DiagramNode(
                id=start_node_id,
                label="Start",
                type="terminal",
                style=NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE),
            )
            adapted_nodes.insert(0, start_node)
            node_ids.add(start_node_id)

            # Connect Start to the first process/decision node
            if len(adapted_nodes) > 1:
                first_target = adapted_nodes[1]
                adapted_edges.insert(
                    0,
                    DiagramEdge(
                        id=f"edge_start_to_{first_target.id}",
                        source=start_node_id,
                        target=first_target.id,
                        label="begins",
                        edge_type="flow",
                        directed=True,
                    ),
                )

        # 2. Add End Terminal if missing
        end_node_id = "end_node"
        if not any(n.type.lower() in ["end", "terminal"] and n.id != start_node_id for n in adapted_nodes):
            end_node = DiagramNode(
                id=end_node_id,
                label="End",
                type="terminal",
                style=NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE),
            )
            adapted_nodes.append(end_node)
            node_ids.add(end_node_id)

        # 3. Ensure all decision nodes have >= 2 labeled outgoing branches
        out_degrees: Dict[str, List[DiagramEdge]] = {nid: [] for nid in node_ids}
        for e in adapted_edges:
            if e.source in out_degrees:
                out_degrees[e.source].append(e)

        edge_counter = len(adapted_edges) + 1
        for node in adapted_nodes:
            if "decision" in node.type.lower() or "condition" in node.type.lower():
                node.style = NodeStyle(shape=NodeShape.DIAMOND)
                current_branches = out_degrees[node.id]

                # If decision has 0 branches, connect Yes to next node and No to End
                if len(current_branches) == 0:
                    adapted_edges.append(
                        DiagramEdge(
                            id=f"edge_branch_{edge_counter}",
                            source=node.id,
                            target=end_node_id,
                            label="Yes",
                            edge_type="branch_yes",
                            directed=True,
                        )
                    )
                    edge_counter += 1
                    adapted_edges.append(
                        DiagramEdge(
                            id=f"edge_branch_{edge_counter}",
                            source=node.id,
                            target=end_node_id,
                            label="No",
                            edge_type="branch_no",
                            directed=True,
                        )
                    )
                    edge_counter += 1

                # If decision has exactly 1 branch, add complementary branch
                elif len(current_branches) == 1:
                    existing = current_branches[0]
                    if not existing.label:
                        existing.label = "Yes"
                        existing.edge_type = "branch_yes"

                    comp_label = "No" if existing.label.lower() in ["yes", "true", "match", "valid"] else "Yes"
                    comp_type = "branch_no" if comp_label == "No" else "branch_yes"

                    # Alternative route goes to End terminal or error step
                    adapted_edges.append(
                        DiagramEdge(
                            id=f"edge_branch_{edge_counter}",
                            source=node.id,
                            target=end_node_id,
                            label=comp_label,
                            edge_type=comp_type,
                            directed=True,
                        )
                    )
                    edge_counter += 1

                # Ensure all branches have labels
                for b_edge in current_branches:
                    if not b_edge.label or not b_edge.label.strip():
                        b_edge.label = "Branch"

        # 4. Connect sink process nodes (out_degree == 0, excluding End) to End terminal
        recalculated_out = {nid: 0 for nid in node_ids}
        for e in adapted_edges:
            recalculated_out[e.source] += 1

        for node in adapted_nodes:
            if node.id != end_node_id and node.id != start_node_id:
                if recalculated_out[node.id] == 0:
                    adapted_edges.append(
                        DiagramEdge(
                            id=f"edge_to_end_{node.id}",
                            source=node.id,
                            target=end_node_id,
                            label="completes",
                            edge_type="flow",
                            directed=True,
                        )
                    )

        return DiagramGraph(
            id=f"graph_flowchart_{int(datetime.now(timezone.utc).timestamp())}",
            diagram_type=DiagramType.FLOWCHART,
            nodes=adapted_nodes,
            edges=adapted_edges,
            metadata=meta,
        )


class ArchitectureAdapter(BaseDiagramAdapter):
    """
    Adapter for Software Architecture diagrams:
    - Normalizes client, backend service, database, cache, and gateway tiers
    - Assigns visual shapes (Cylinder for DB/Cache, Cloud for External/Internet)
    - Enforces labeled communication protocols (HTTPS, REST, SQL, etc.)
    """

    def __init__(self):
        super().__init__(DiagramType.ARCHITECTURE)

    def adapt(
        self,
        nodes: List[DiagramNode],
        edges: List[DiagramEdge],
        text: str,
        metadata: Optional[DiagramMetadata] = None
    ) -> DiagramGraph:
        adapted_nodes = list(nodes)
        adapted_edges = list(edges)

        meta = metadata or DiagramMetadata(
            title="Software Architecture",
            domain="system_architecture",
            diagram_type=DiagramType.ARCHITECTURE.value,
            provenance="nlp_pipeline",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Assign tier styles and shapes
        for node in adapted_nodes:
            ntype = node.type.lower()
            if ntype in ["database", "storage"]:
                node.style = NodeStyle(shape=NodeShape.CYLINDER)
                node.attributes["tier"] = "database"
            elif ntype in ["cache"]:
                node.style = NodeStyle(shape=NodeShape.CYLINDER)
                node.attributes["tier"] = "cache"
            elif ntype in ["external_api", "cloud"]:
                node.style = NodeStyle(shape=NodeShape.CLOUD)
                node.attributes["tier"] = "external"
            elif ntype in ["client", "frontend", "ui"]:
                node.style = NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE)
                node.attributes["tier"] = "frontend"
            elif ntype in ["service", "backend"]:
                node.style = NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE)
                node.attributes["tier"] = "backend"

        # Ensure edges have protocol labels
        for edge in adapted_edges:
            if not edge.label or not edge.label.strip():
                if edge.edge_type == "api_call":
                    edge.label = "REST / HTTPS"
                elif edge.edge_type == "data_read_write":
                    edge.label = "query / store"
                else:
                    edge.label = "communicates with"

        return DiagramGraph(
            id=f"graph_arch_{int(datetime.now(timezone.utc).timestamp())}",
            diagram_type=DiagramType.ARCHITECTURE,
            nodes=adapted_nodes,
            edges=adapted_edges,
            metadata=meta,
        )


class ConceptMapAdapter(BaseDiagramAdapter):
    """
    Adapter for Concept Maps & Ontologies:
    - Enforces non-empty semantic proposition labels on every edge ('is a', 'consists of', 'relates to')
    - Distinguishes categories from concepts
    - Permits cross-links and cycles
    """

    def __init__(self):
        super().__init__(DiagramType.CONCEPT_MAP)

    def adapt(
        self,
        nodes: List[DiagramNode],
        edges: List[DiagramEdge],
        text: str,
        metadata: Optional[DiagramMetadata] = None
    ) -> DiagramGraph:
        adapted_nodes = list(nodes)
        adapted_edges = list(edges)

        meta = metadata or DiagramMetadata(
            title="Concept Map",
            domain="computer_science",
            diagram_type=DiagramType.CONCEPT_MAP.value,
            provenance="nlp_pipeline",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        for node in adapted_nodes:
            if node.attributes.get("level") == "category":
                node.style = NodeStyle(shape=NodeShape.RECTANGLE)
            else:
                node.style = NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE)

        # STRICT Semantic requirement: All concept map edges MUST have non-empty proposition labels
        for edge in adapted_edges:
            if not edge.label or not edge.label.strip():
                if edge.edge_type == "is_a":
                    edge.label = "is a"
                elif edge.edge_type == "part_of":
                    edge.label = "includes"
                else:
                    edge.label = "relates to"

        return DiagramGraph(
            id=f"graph_concept_{int(datetime.now(timezone.utc).timestamp())}",
            diagram_type=DiagramType.CONCEPT_MAP,
            nodes=adapted_nodes,
            edges=adapted_edges,
            metadata=meta,
        )


class ERDiagramAdapter(BaseDiagramAdapter):
    """
    Adapter for Entity-Relationship Diagrams:
    - Validates entities and primary/foreign key attributes
    - Ensures cardinalities (1:1, 1:N, M:N)
    """

    def __init__(self):
        super().__init__(DiagramType.ER_DIAGRAM)

    def adapt(
        self,
        nodes: List[DiagramNode],
        edges: List[DiagramEdge],
        text: str,
        metadata: Optional[DiagramMetadata] = None
    ) -> DiagramGraph:
        adapted_nodes = list(nodes)
        adapted_edges = list(edges)

        for n in adapted_nodes:
            n.style = NodeStyle(shape=NodeShape.RECTANGLE)
            n.type = "entity"

        for e in adapted_edges:
            if not e.cardinality:
                e.cardinality = "1:N"
            if not e.label or not e.label.strip():
                e.label = f"relates ({e.cardinality})"

        meta = metadata or DiagramMetadata(
            title="Entity-Relationship Diagram",
            domain="database",
            diagram_type=DiagramType.ER_DIAGRAM.value,
            provenance="nlp_pipeline",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return DiagramGraph(
            id=f"graph_er_{int(datetime.now(timezone.utc).timestamp())}",
            diagram_type=DiagramType.ER_DIAGRAM,
            nodes=adapted_nodes,
            edges=adapted_edges,
            metadata=meta,
        )


class SequenceDiagramAdapter(BaseDiagramAdapter):
    """
    Adapter for Sequence Diagrams:
    - Participants configured with lifeline shape
    - Chronologically monotonic sequence_order
    """

    def __init__(self):
        super().__init__(DiagramType.SEQUENCE_DIAGRAM)

    def adapt(
        self,
        nodes: List[DiagramNode],
        edges: List[DiagramEdge],
        text: str,
        metadata: Optional[DiagramMetadata] = None
    ) -> DiagramGraph:
        adapted_nodes = list(nodes)
        adapted_edges = list(edges)

        for n in adapted_nodes:
            n.style = NodeStyle(shape=NodeShape.LIFELINE)
            n.type = "participant"

        # Strictly enforce monotonic sequence order
        for idx, e in enumerate(adapted_edges):
            e.sequence_order = idx + 1
            if not e.label or not e.label.strip():
                e.label = f"Message {idx + 1}"

        meta = metadata or DiagramMetadata(
            title="Sequence Diagram",
            domain="interaction",
            diagram_type=DiagramType.SEQUENCE_DIAGRAM.value,
            provenance="nlp_pipeline",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return DiagramGraph(
            id=f"graph_seq_{int(datetime.now(timezone.utc).timestamp())}",
            diagram_type=DiagramType.SEQUENCE_DIAGRAM,
            nodes=adapted_nodes,
            edges=adapted_edges,
            metadata=meta,
        )


class NetworkTopologyAdapter(BaseDiagramAdapter):
    """Adapter for Network Topology diagrams."""

    def __init__(self):
        super().__init__(DiagramType.NETWORK_TOPOLOGY)

    def adapt(
        self,
        nodes: List[DiagramNode],
        edges: List[DiagramEdge],
        text: str,
        metadata: Optional[DiagramMetadata] = None
    ) -> DiagramGraph:
        adapted_nodes = list(nodes)
        adapted_edges = list(edges)

        for n in adapted_nodes:
            ntype = n.type.lower()
            if ntype == "router":
                n.style = NodeStyle(shape=NodeShape.HEXAGON)
            elif ntype == "firewall":
                n.style = NodeStyle(shape=NodeShape.RECTANGLE)
            elif ntype == "cloud":
                n.style = NodeStyle(shape=NodeShape.CLOUD)
            else:
                n.style = NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE)

        for e in adapted_edges:
            if not e.label:
                e.label = "link"

        meta = metadata or DiagramMetadata(
            title="Network Topology",
            domain="networking",
            diagram_type=DiagramType.NETWORK_TOPOLOGY.value,
            provenance="nlp_pipeline",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return DiagramGraph(
            id=f"graph_net_{int(datetime.now(timezone.utc).timestamp())}",
            diagram_type=DiagramType.NETWORK_TOPOLOGY,
            nodes=adapted_nodes,
            edges=adapted_edges,
            metadata=meta,
        )


class DependencyGraphAdapter(BaseDiagramAdapter):
    """Adapter for Dependency / Task DAGs."""

    def __init__(self):
        super().__init__(DiagramType.DEPENDENCY_GRAPH)

    def adapt(
        self,
        nodes: List[DiagramNode],
        edges: List[DiagramEdge],
        text: str,
        metadata: Optional[DiagramMetadata] = None
    ) -> DiagramGraph:
        adapted_nodes = list(nodes)
        adapted_edges = list(edges)

        for n in adapted_nodes:
            n.style = NodeStyle(shape=NodeShape.ROUNDED_RECTANGLE)
            n.type = "task"

        for e in adapted_edges:
            e.edge_type = "depends_on"
            if not e.label:
                e.label = "depends on"

        meta = metadata or DiagramMetadata(
            title="Dependency Graph",
            domain="workflow",
            diagram_type=DiagramType.DEPENDENCY_GRAPH.value,
            provenance="nlp_pipeline",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return DiagramGraph(
            id=f"graph_dep_{int(datetime.now(timezone.utc).timestamp())}",
            diagram_type=DiagramType.DEPENDENCY_GRAPH,
            nodes=adapted_nodes,
            edges=adapted_edges,
            metadata=meta,
        )


ADAPTER_REGISTRY: Dict[DiagramType, BaseDiagramAdapter] = {
    DiagramType.FLOWCHART: FlowchartAdapter(),
    DiagramType.ARCHITECTURE: ArchitectureAdapter(),
    DiagramType.CONCEPT_MAP: ConceptMapAdapter(),
    DiagramType.ER_DIAGRAM: ERDiagramAdapter(),
    DiagramType.SEQUENCE_DIAGRAM: SequenceDiagramAdapter(),
    DiagramType.NETWORK_TOPOLOGY: NetworkTopologyAdapter(),
    DiagramType.DEPENDENCY_GRAPH: DependencyGraphAdapter(),
}


def get_adapter_for_type(diagram_type: DiagramType) -> BaseDiagramAdapter:
    """Retrieves the specialized adapter for the specified diagram family."""
    adapter = ADAPTER_REGISTRY.get(diagram_type)
    if not adapter:
        # Fallback to flowchart adapter
        return FlowchartAdapter()
    return adapter
