"""
Graph Processing Engine using NetworkX.
Provides graph integrity checks, connected-component analysis, reachability analysis,
duplicate relationship handling, cycle detection according to diagram semantics,
and graph metrics computation.
"""

from typing import List, Dict, Set, Tuple, Any, Optional, Union
from pydantic import BaseModel, Field
import networkx as nx
from collections import defaultdict

from ir.models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramType,
    ValidationWarning,
    DiagramMetadata,
)


class GraphIntegrityResult(BaseModel):
    """Integrity check findings."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_nodes: List[str] = Field(default_factory=list)
    duplicate_edges: List[Dict[str, str]] = Field(default_factory=list)
    self_loops: List[str] = Field(default_factory=list)
    isolated_nodes: List[str] = Field(default_factory=list)


class ConnectivityResult(BaseModel):
    """Connectivity and component analysis."""
    is_weakly_connected: bool
    is_strongly_connected: bool
    weakly_connected_components: List[List[str]] = Field(default_factory=list)
    strongly_connected_components: List[List[str]] = Field(default_factory=list)
    wcc_count: int = 0
    scc_count: int = 0
    largest_component_size: int = 0


class ReachabilityResult(BaseModel):
    """Reachability from roots and dead-end detection."""
    root_nodes: List[str] = Field(default_factory=list)
    leaf_nodes: List[str] = Field(default_factory=list)
    unreachable_nodes: List[str] = Field(default_factory=list)
    reachability_map: Dict[str, List[str]] = Field(default_factory=dict)
    dead_ends: List[str] = Field(default_factory=list)


class CycleAnalysisResult(BaseModel):
    """Cycle detection and semantic interpretation."""
    has_cycles: bool
    cycle_count: int = 0
    cycles: List[List[str]] = Field(default_factory=list)
    is_valid_for_diagram: bool = True
    semantic_notes: List[str] = Field(default_factory=list)


class GraphAnalysisReport(BaseModel):
    """Comprehensive graph analysis report."""
    node_count: int
    edge_count: int
    density: float
    is_dag: bool
    integrity: GraphIntegrityResult
    connectivity: ConnectivityResult
    reachability: ReachabilityResult
    cycles: CycleAnalysisResult
    metrics: Dict[str, Any] = Field(default_factory=dict)


class GraphProcessor:
    """
    Core graph processor utilizing NetworkX for topological analysis,
    connectivity computation, cycle validation, and relationship normalization.
    """

    MAX_NODES: int = 500
    MAX_EDGES: int = 1000

    @classmethod
    def to_networkx(
        cls,
        graph: DiagramGraph,
        directed: bool = True,
        include_attributes: bool = True
    ) -> Union[nx.DiGraph, nx.Graph]:
        """
        Converts a DiagramGraph into a NetworkX DiGraph or Graph.
        Preserves node types, labels, and edge metadata.
        """
        G = nx.DiGraph() if directed else nx.Graph()

        # Add nodes
        for node in graph.nodes:
            attrs = {
                "label": node.label,
                "type": node.type,
                "confidence": node.confidence,
            }
            if include_attributes and node.attributes:
                attrs.update(node.attributes)
            if node.position:
                attrs["pos_x"] = node.position.x
                attrs["pos_y"] = node.position.y
            G.add_node(node.id, **attrs)

        # Add edges
        for edge in graph.edges:
            attrs = {
                "id": edge.id,
                "label": edge.label or "",
                "edge_type": edge.edge_type,
                "directed": edge.directed,
                "confidence": edge.confidence,
            }
            if edge.sequence_order is not None:
                attrs["sequence_order"] = edge.sequence_order
            if edge.cardinality:
                attrs["cardinality"] = edge.cardinality
            G.add_edge(edge.source, edge.target, **attrs)

        return G

    @classmethod
    def check_integrity(cls, graph: DiagramGraph) -> GraphIntegrityResult:
        """
        Performs structural integrity checks:
        - Detects dangling edges referencing nonexistent nodes.
        - Detects duplicate/parallel edges.
        - Detects self-loops.
        - Identifies isolated nodes.
        - Enforces graph size safety limits.
        """
        errors: List[str] = []
        warnings: List[str] = []
        node_ids = {n.id for n in graph.nodes}

        # Size limits
        if len(graph.nodes) > cls.MAX_NODES:
            errors.append(f"Node count ({len(graph.nodes)}) exceeds maximum limit of {cls.MAX_NODES}")
        if len(graph.edges) > cls.MAX_EDGES:
            errors.append(f"Edge count ({len(graph.edges)}) exceeds maximum limit of {cls.MAX_EDGES}")

        # Missing nodes / dangling edges
        missing: Set[str] = set()
        for edge in graph.edges:
            if edge.source not in node_ids:
                missing.add(edge.source)
            if edge.target not in node_ids:
                missing.add(edge.target)

        missing_list = sorted(list(missing))
        if missing_list:
            errors.append(f"Edges reference undefined node IDs: {missing_list}")

        # Duplicate edges and self-loops
        seen_pairs: Dict[Tuple[str, str], int] = defaultdict(int)
        duplicate_edges: List[Dict[str, str]] = []
        self_loops: List[str] = []

        for edge in graph.edges:
            pair = (edge.source, edge.target)
            seen_pairs[pair] += 1
            if edge.source == edge.target:
                self_loops.append(edge.source)

        for (src, tgt), count in seen_pairs.items():
            if count > 1:
                duplicate_edges.append({
                    "source": src,
                    "target": tgt,
                    "count": str(count),
                })
                warnings.append(f"Parallel edges detected between '{src}' and '{tgt}' ({count} occurrences)")

        if self_loops:
            unique_loops = sorted(list(set(self_loops)))
            warnings.append(f"Self-loops detected on nodes: {unique_loops}")

        # Isolated nodes (no incoming and no outgoing edges)
        connected_nodes: Set[str] = set()
        for edge in graph.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)

        isolated = sorted([nid for nid in node_ids if nid not in connected_nodes])
        if isolated and len(node_ids) > 1:
            warnings.append(f"Isolated nodes with no relationships: {isolated}")

        is_valid = len(errors) == 0

        return GraphIntegrityResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_nodes=missing_list,
            duplicate_edges=duplicate_edges,
            self_loops=sorted(list(set(self_loops))),
            isolated_nodes=isolated,
        )

    @classmethod
    def analyze_connectivity(cls, graph: DiagramGraph) -> ConnectivityResult:
        """
        Analyzes connected components using NetworkX:
        - Weakly connected components (ignoring edge direction).
        - Strongly connected components (respecting edge direction).
        """
        G = cls.to_networkx(graph, directed=True)

        if len(G) == 0:
            return ConnectivityResult(
                is_weakly_connected=False,
                is_strongly_connected=False,
                weakly_connected_components=[],
                strongly_connected_components=[],
                wcc_count=0,
                scc_count=0,
                largest_component_size=0,
            )

        wcc = [sorted(list(c)) for c in nx.weakly_connected_components(G)]
        wcc.sort(key=lambda x: (-len(x), x[0]))

        scc = [sorted(list(c)) for c in nx.strongly_connected_components(G)]
        scc.sort(key=lambda x: (-len(x), x[0]))

        is_wcc = nx.is_weakly_connected(G)
        is_scc = nx.is_strongly_connected(G)
        largest = len(wcc[0]) if wcc else 0

        return ConnectivityResult(
            is_weakly_connected=is_wcc,
            is_strongly_connected=is_scc,
            weakly_connected_components=wcc,
            strongly_connected_components=scc,
            wcc_count=len(wcc),
            scc_count=len(scc),
            largest_component_size=largest,
        )

    @classmethod
    def analyze_reachability(
        cls,
        graph: DiagramGraph,
        explicit_roots: Optional[List[str]] = None
    ) -> ReachabilityResult:
        """
        Computes reachability from root nodes (in_degree == 0):
        - Detects roots and leaves.
        - Identifies unreachable nodes not accessible from any root.
        - Maps reachable subgraphs per root.
        """
        G = cls.to_networkx(graph, directed=True)
        node_ids = set(G.nodes)

        # Roots: in_degree == 0
        if explicit_roots:
            roots = [r for r in explicit_roots if r in node_ids]
        else:
            roots = [n for n, d in G.in_degree() if d == 0]
        roots.sort()

        # Leaves: out_degree == 0
        leaves = sorted([n for n, d in G.out_degree() if d == 0])

        reachability_map: Dict[str, List[str]] = {}
        all_reachable_from_roots: Set[str] = set()

        for root in roots:
            reachable = sorted(list(nx.descendants(G, root)) + [root])
            reachability_map[root] = reachable
            all_reachable_from_roots.update(reachable)

        # If there are roots, unreachable nodes are those not reachable from any root
        if roots:
            unreachable = sorted(list(node_ids - all_reachable_from_roots))
        else:
            # Graph is pure cycle or empty
            unreachable = []

        # Dead ends: nodes with out_degree == 0 that are not marked terminal
        dead_ends: List[str] = []
        terminal_types = {"terminal", "end", "stop", "exit", "sink", "database", "storage"}
        for leaf in leaves:
            node_obj = graph.get_node(leaf)
            if node_obj and node_obj.type.lower() not in terminal_types:
                dead_ends.append(leaf)

        return ReachabilityResult(
            root_nodes=roots,
            leaf_nodes=leaves,
            unreachable_nodes=unreachable,
            reachability_map=reachability_map,
            dead_ends=sorted(dead_ends),
        )

    @classmethod
    def detect_cycles(
        cls,
        graph: DiagramGraph,
        diagram_type: Optional[DiagramType] = None
    ) -> CycleAnalysisResult:
        """
        Detects elementary directed cycles using NetworkX (Johnson's algorithm)
        and evaluates validity based on the diagram family's semantics:
        - Flowchart: Cycles valid (iterative loops, retry policies).
        - Architecture: Cycles valid (bidirectional or circular service calls), flagged with notice.
        - Concept Map: Cycles valid (ontological cross-links).
        - Network Topology: Cycles valid (redundant ring or mesh paths).
        - Dependency Graph: Cycles INVALID (fatal cycle/deadlock).
        - Sequence Diagram: Cycles INVALID (sequence flow must be chronologically acyclic).
        """
        dtype = diagram_type or graph.diagram_type
        G = cls.to_networkx(graph, directed=True)

        try:
            raw_cycles = list(nx.simple_cycles(G))
        except Exception:
            raw_cycles = []

        # Sort cycles stably
        cycles: List[List[str]] = []
        for c in raw_cycles:
            # normalize rotation to start with minimum element
            if c:
                min_idx = c.index(min(c))
                normalized = c[min_idx:] + c[:min_idx]
                cycles.append(normalized)
        cycles.sort(key=lambda x: (len(x), x))

        has_cycles = len(cycles) > 0
        is_valid = True
        notes: List[str] = []

        if has_cycles:
            cycle_desc = [f"({' -> '.join(c + [c[0]])})" for c in cycles[:5]]

            if dtype == DiagramType.DEPENDENCY_GRAPH:
                is_valid = False
                notes.append(f"FATAL: Dependency graph contains circular dependencies: {cycle_desc}")
            elif dtype == DiagramType.SEQUENCE_DIAGRAM:
                is_valid = False
                notes.append(f"FATAL: Sequence diagram messages contain cyclical dependencies: {cycle_desc}")
            elif dtype == DiagramType.FLOWCHART:
                is_valid = True
                notes.append(f"Permitted iterative loop(s) detected in flowchart: {cycle_desc}")
            elif dtype == DiagramType.ARCHITECTURE:
                is_valid = True
                notes.append(f"Architectural circular dependency detected (review for coupling): {cycle_desc}")
            elif dtype == DiagramType.CONCEPT_MAP:
                is_valid = True
                notes.append(f"Semantic cross-link cycle(s) detected in concept map: {cycle_desc}")
            elif dtype == DiagramType.NETWORK_TOPOLOGY:
                is_valid = True
                notes.append(f"Redundant network loop(s) detected (spanning tree candidate): {cycle_desc}")
            else:
                is_valid = True
                notes.append(f"Cycles detected in diagram: {cycle_desc}")

        return CycleAnalysisResult(
            has_cycles=has_cycles,
            cycle_count=len(cycles),
            cycles=cycles,
            is_valid_for_diagram=is_valid,
            semantic_notes=notes,
        )

    @classmethod
    def normalize_relationships(
        cls,
        graph: DiagramGraph,
        merge_parallel_edges: bool = True
    ) -> DiagramGraph:
        """
        Normalizes relationships in a DiagramGraph:
        - Trims whitespace from labels and IDs.
        - Merges parallel edges between the same source and target if requested,
          combining labels without loss of semantic information.
        - Returns a clean DiagramGraph copy.
        """
        clean_nodes = [node.model_copy(deep=True) for node in graph.nodes]
        edge_groups: Dict[Tuple[str, str, bool], List[DiagramEdge]] = defaultdict(list)

        for edge in graph.edges:
            key = (edge.source.strip(), edge.target.strip(), edge.directed)
            edge_groups[key].append(edge)

        normalized_edges: List[DiagramEdge] = []
        edge_counter = 1

        for (src, tgt, directed), group in edge_groups.items():
            if not merge_parallel_edges or len(group) == 1:
                for e in group:
                    e_copy = e.model_copy(deep=True)
                    e_copy.source = src
                    e_copy.target = tgt
                    normalized_edges.append(e_copy)
            else:
                # Merge parallel edges
                labels = [e.label.strip() for e in group if e.label and e.label.strip()]
                combined_label = " / ".join(dict.fromkeys(labels)) if labels else None

                # Select best confidence
                confidences = [e.confidence for e in group if e.confidence is not None]
                avg_confidence = (sum(confidences) / len(confidences)) if confidences else None

                primary = group[0]
                merged_edge = DiagramEdge(
                    id=f"edge_norm_{edge_counter}",
                    source=src,
                    target=tgt,
                    label=combined_label,
                    edge_type=primary.edge_type,
                    directed=directed,
                    cardinality=primary.cardinality,
                    sequence_order=primary.sequence_order,
                    metadata={"merged_count": len(group), "original_ids": [e.id for e in group]},
                    confidence=avg_confidence,
                )
                normalized_edges.append(merged_edge)
                edge_counter += 1

        return DiagramGraph(
            id=graph.id,
            diagram_type=graph.diagram_type,
            version=graph.version,
            nodes=clean_nodes,
            edges=normalized_edges,
            metadata=graph.metadata.model_copy(deep=True),
            warnings=list(graph.warnings),
            layout_config=graph.layout_config.copy() if graph.layout_config else None,
        )

    @classmethod
    def analyze(cls, graph: DiagramGraph) -> GraphAnalysisReport:
        """
        Runs complete graph analysis pipeline:
        integrity, connectivity, reachability, cycle validation, and topological density.
        """
        G = cls.to_networkx(graph, directed=True)
        node_count = len(G.nodes)
        edge_count = len(G.edges)
        density = nx.density(G) if node_count > 1 else 0.0
        is_dag = nx.is_directed_acyclic_graph(G) if node_count > 0 else True

        integrity = cls.check_integrity(graph)
        connectivity = cls.analyze_connectivity(graph)
        reachability = cls.analyze_reachability(graph)
        cycle_res = cls.detect_cycles(graph)

        metrics = {
            "density": round(density, 4),
            "is_dag": is_dag,
            "average_degree": round(2 * edge_count / node_count, 2) if node_count > 0 else 0.0,
            "root_count": len(reachability.root_nodes),
            "leaf_count": len(reachability.leaf_nodes),
            "wcc_count": connectivity.wcc_count,
            "scc_count": connectivity.scc_count,
        }

        return GraphAnalysisReport(
            node_count=node_count,
            edge_count=edge_count,
            density=round(density, 4),
            is_dag=is_dag,
            integrity=integrity,
            connectivity=connectivity,
            reachability=reachability,
            cycles=cycle_res,
            metrics=metrics,
        )
