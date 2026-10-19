"""
Diagram Intermediate Representation (IR) Semantic Validators.
Implements universal structural validation, graph topological analysis,
and diagram-family specific semantic rules.
"""

from typing import List, Dict, Set, Tuple, Any, Optional
from collections import defaultdict, deque
import re

from .models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramType,
    ValidationReport,
    ValidationErrorDetail,
    ValidationWarning,
)


class GraphTopologicalAnalyzer:
    """Helper for cycle detection, reachability, and graph connectivity metrics."""

    @staticmethod
    def find_cycles(node_ids: Set[str], edges: List[DiagramEdge]) -> List[List[str]]:
        """Finds directed cycles using DFS."""
        adj = defaultdict(list)
        for e in edges:
            if e.directed and e.source in node_ids and e.target in node_ids:
                adj[e.source].append(e.target)

        visited: Dict[str, int] = {nid: 0 for nid in node_ids}  # 0=unvisited, 1=visiting, 2=visited
        cycles: List[List[str]] = []
        path: List[str] = []

        def dfs(u: str):
            visited[u] = 1
            path.append(u)
            for v in adj[u]:
                if visited[v] == 1:
                    cycle_start = path.index(v)
                    cycles.append(list(path[cycle_start:] + [v]))
                elif visited[v] == 0:
                    dfs(v)
            path.pop()
            visited[u] = 2

        for nid in sorted(node_ids):
            if visited[nid] == 0:
                dfs(nid)

        return cycles

    @staticmethod
    def compute_metrics(node_ids: Set[str], edges: List[DiagramEdge]) -> Dict[str, Any]:
        """Calculates graph connectivity, degrees, and density."""
        n_nodes = len(node_ids)
        n_edges = len(edges)
        density = (n_edges / (n_nodes * (n_nodes - 1))) if n_nodes > 1 else 0.0

        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        for e in edges:
            out_degree[e.source] += 1
            in_degree[e.target] += 1

        isolated_nodes = [nid for nid in node_ids if in_degree[nid] == 0 and out_degree[nid] == 0]

        return {
            "node_count": n_nodes,
            "edge_count": n_edges,
            "density": round(density, 4),
            "isolated_node_count": len(isolated_nodes),
            "isolated_nodes": isolated_nodes,
        }


class BaseDiagramValidator:
    """Base class for diagram-family specific validation."""

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        raise NotImplementedError


class FlowchartValidator(BaseDiagramValidator):
    """
    Flowchart semantic validation:
    - Verifies start and end terminals
    - Enforces that decision nodes have at least 2 outgoing branches
    - Allows cycles (loops/retries)
    """

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        errors: List[ValidationErrorDetail] = []
        warnings: List[ValidationWarning] = []

        node_types = {n.type.lower() for n in graph.nodes}
        terminal_types = {"terminal", "start", "end", "start_node", "end_node"}

        # 1. Check for terminal presence
        if not (node_types & terminal_types):
            warnings.append(
                ValidationWarning(
                    code="W_FLOWCHART_NO_TERMINALS",
                    message="Flowchart has no start or end terminal nodes. Consider adding explicit terminal steps.",
                    level="info",
                )
            )

        # 2. Check decision nodes
        for node in graph.nodes:
            if "decision" in node.type.lower() or "condition" in node.type.lower():
                out_edges = graph.get_outgoing_edges(node.id)
                if len(out_edges) < 2:
                    errors.append(
                        ValidationErrorDetail(
                            code="E_DECISION_INSUFFICIENT_BRANCHES",
                            message=f"Decision node '{node.label}' ({node.id}) has {len(out_edges)} outgoing branches. Decision nodes require at least 2 branches (e.g. Yes/No).",
                            element_id=node.id,
                        )
                    )
                else:
                    unlabeled = [e for e in out_edges if not e.label or not e.label.strip()]
                    if unlabeled:
                        warnings.append(
                            ValidationWarning(
                                code="W_DECISION_UNLABELED_BRANCH",
                                message=f"Decision node '{node.label}' ({node.id}) has {len(unlabeled)} outgoing branch(es) without a condition label (e.g. 'Yes' or 'No').",
                                level="warning",
                                element_id=node.id,
                            )
                        )

        return errors, warnings


class ArchitectureValidator(BaseDiagramValidator):
    """
    Software Architecture validation:
    - Detects architectural anti-patterns (e.g. direct Client -> Database access)
    - Validates component tiers (clients, services, caches, databases)
    - Permits cycles but flags circular service calls with a warning
    """

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        errors: List[ValidationErrorDetail] = []
        warnings: List[ValidationWarning] = []

        node_map = {n.id: n for n in graph.nodes}
        client_types = {"client", "frontend", "ui", "mobile_app", "web_app", "browser"}
        storage_types = {"database", "db", "cache", "data_store", "storage"}

        for edge in graph.edges:
            src = node_map.get(edge.source)
            tgt = node_map.get(edge.target)
            if src and tgt:
                src_type = src.type.lower()
                tgt_type = tgt.type.lower()

                # Anti-pattern: Client directly accessing database
                if src_type in client_types and tgt_type in storage_types:
                    warnings.append(
                        ValidationWarning(
                            code="W_ARCH_CLIENT_DIRECT_DB",
                            message=f"Architectural Anti-Pattern: Client tier '{src.label}' directly accesses database '{tgt.label}' without an intermediate API or service layer.",
                            level="caution",
                            element_id=edge.id,
                        )
                    )

        # Check for circular service dependencies
        cycles = GraphTopologicalAnalyzer.find_cycles(graph.node_ids(), graph.edges)
        if cycles:
            cycle_desc = " -> ".join(cycles[0])
            warnings.append(
                ValidationWarning(
                    code="W_CIRCULAR_DEPENDENCY",
                    message=f"Circular service communication detected: {cycle_desc}. While valid in event-driven systems, ensure this is not an unintentional deadlock.",
                    level="warning",
                )
            )

        return errors, warnings


class ConceptMapValidator(BaseDiagramValidator):
    """
    Concept Map validation:
    - Requires labeled semantic propositions on edges
    - Allows arbitrary cycles and cross-links
    """

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        errors: List[ValidationErrorDetail] = []
        warnings: List[ValidationWarning] = []

        unlabeled_edges = [e for e in graph.edges if not e.label or not e.label.strip()]
        if len(unlabeled_edges) > len(graph.edges) * 0.5 and len(graph.edges) > 0:
            warnings.append(
                ValidationWarning(
                    code="W_CONCEPT_UNLABELED_RELATIONS",
                    message="More than 50% of relationships in this concept map are unlabeled. Concept maps should have explicit semantic linking phrases (e.g. 'is a', 'part of').",
                    level="info",
                )
            )

        return errors, warnings


class ERDiagramValidator(BaseDiagramValidator):
    """
    Entity-Relationship Diagram validation:
    - Validates cardinality format (1:1, 1:N, N:M)
    - Validates key attribute attachments
    - Checks that entities have associated attributes
    """

    CARDINALITY_PATTERN = re.compile(r"^(1:1|1:N|N:1|M:N|1:M|N:M|1:many|many:many)$", re.IGNORECASE)

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        errors: List[ValidationErrorDetail] = []
        warnings: List[ValidationWarning] = []

        node_map = {n.id: n for n in graph.nodes}
        entity_ids = {n.id for n in graph.nodes if "entity" in n.type.lower()}
        attribute_ids = {n.id for n in graph.nodes if "attribute" in n.type.lower()}

        for edge in graph.edges:
            card = edge.cardinality or edge.label
            if card:
                clean_card = card.replace("(", "").replace(")", "").strip()
                if ":" in clean_card:
                    if not self.CARDINALITY_PATTERN.match(clean_card):
                        warnings.append(
                            ValidationWarning(
                                code="W_ERD_NONSTANDARD_CARDINALITY",
                                message=f"Relationship '{edge.id}' has non-standard cardinality format '{card}'. Recommended formats: 1:1, 1:N, or M:N.",
                                level="info",
                                element_id=edge.id,
                            )
                        )

            # Key attributes must attach to entities
            src = node_map.get(edge.source)
            tgt = node_map.get(edge.target)
            if src and tgt:
                if "key" in src.type.lower() and tgt.id not in entity_ids:
                    errors.append(
                        ValidationErrorDetail(
                            code="E_KEY_ATTACHED_TO_NON_ENTITY",
                            message=f"Key attribute '{src.label}' ({src.id}) must attach to an Entity, but connects to non-entity '{tgt.label}'.",
                            element_id=edge.id,
                        )
                    )
                elif "key" in tgt.type.lower() and src.id not in entity_ids:
                    errors.append(
                        ValidationErrorDetail(
                            code="E_KEY_ATTACHED_TO_NON_ENTITY",
                            message=f"Key attribute '{tgt.label}' ({tgt.id}) must attach to an Entity, but connects to non-entity '{src.label}'.",
                            element_id=edge.id,
                        )
                    )

        if attribute_ids:
            entities_with_attrs = set()
            for edge in graph.edges:
                if edge.source in entity_ids and edge.target in attribute_ids:
                    entities_with_attrs.add(edge.source)
                elif edge.target in entity_ids and edge.source in attribute_ids:
                    entities_with_attrs.add(edge.target)

            bare_entities = entity_ids - entities_with_attrs
            for be_id in bare_entities:
                be = node_map.get(be_id)
                warnings.append(
                    ValidationWarning(
                        code="W_ERD_ENTITY_WITHOUT_ATTRIBUTES",
                        message=f"Entity '{be.label if be else be_id}' has no defined attributes or primary keys.",
                        level="info",
                        element_id=be_id,
                    )
                )

        return errors, warnings


class SequenceDiagramValidator(BaseDiagramValidator):
    """
    Sequence Diagram validation:
    - Enforces chronological sequence ordering
    - Detects temporal inversion (return before call)
    - Validates participant interactions
    """

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        errors: List[ValidationErrorDetail] = []
        warnings: List[ValidationWarning] = []

        ordered_edges = [e for e in graph.edges if e.sequence_order is not None]
        if ordered_edges:
            seen_orders = set()
            for edge in ordered_edges:
                if edge.sequence_order in seen_orders:
                    warnings.append(
                        ValidationWarning(
                            code="W_DUPLICATE_SEQUENCE_ORDER",
                            message=f"Sequence message '{edge.id}' shares duplicate sequence_order #{edge.sequence_order}. Messages should have distinct sequential orders.",
                            level="warning",
                            element_id=edge.id,
                        )
                    )
                seen_orders.add(edge.sequence_order)

            # Check for temporal inversion between reciprocal messages
            edge_by_pair = defaultdict(list)
            for e in ordered_edges:
                edge_by_pair[(e.source, e.target)].append(e)

            for (src, tgt), fwd_edges in edge_by_pair.items():
                rev_edges = edge_by_pair.get((tgt, src), [])
                for fwd in fwd_edges:
                    for rev in rev_edges:
                        if (
                            rev.edge_type in ("return_value", "return_signal", "response")
                            and rev.sequence_order <= fwd.sequence_order
                        ):
                            errors.append(
                                ValidationErrorDetail(
                                    code="E_SEQUENCE_ORDER_INVERTED",
                                    message=f"Temporal inversion: Response message '{rev.id}' (order #{rev.sequence_order}) cannot occur before or simultaneously with request '{fwd.id}' (order #{fwd.sequence_order}).",
                                    element_id=rev.id,
                                )
                            )
        else:
            cycles = GraphTopologicalAnalyzer.find_cycles(graph.node_ids(), graph.edges)
            if cycles:
                warnings.append(
                    ValidationWarning(
                        code="W_SEQUENCE_UNORDERED_MESSAGES",
                        message="Sequence diagram contains reciprocal messages between participants without explicit sequence_order metadata.",
                        level="warning",
                    )
                )

        return errors, warnings


class NetworkTopologyValidator(BaseDiagramValidator):
    """
    Network Topology validation:
    - Device types: workstation, switch, router, firewall, server, internet
    - Allows physical network loops (Spanning Tree Protocol)
    - Warns on disconnected network devices
    """

    VALID_NET_TYPES = {
        "workstation", "switch", "router", "firewall", "server", "internet",
        "client", "cloud", "gateway", "access_point"
    }

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        errors: List[ValidationErrorDetail] = []
        warnings: List[ValidationWarning] = []

        for node in graph.nodes:
            ntype = node.type.lower()
            if ntype not in self.VALID_NET_TYPES:
                warnings.append(
                    ValidationWarning(
                        code="W_NET_NONSTANDARD_DEVICE",
                        message=f"Node '{node.label}' ({node.id}) has non-standard network type '{node.type}'.",
                        level="info",
                        element_id=node.id,
                    )
                )

        metrics = GraphTopologicalAnalyzer.compute_metrics(graph.node_ids(), graph.edges)
        for iso_id in metrics["isolated_nodes"]:
            node = graph.get_node(iso_id)
            warnings.append(
                ValidationWarning(
                    code="W_NET_DISCONNECTED_DEVICE",
                    message=f"Device '{node.label if node else iso_id}' has no connected network interfaces or links.",
                    level="warning",
                    element_id=iso_id,
                )
            )

        return errors, warnings


class DependencyGraphValidator(BaseDiagramValidator):
    """
    Dependency Graph validation:
    - Tasks and deliverables
    - STRICTLY FORBIDS CYCLES: A dependency graph must be a Directed Acyclic Graph (DAG)
    """

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        errors: List[ValidationErrorDetail] = []
        warnings: List[ValidationWarning] = []

        # STRICT DAG ENFORCEMENT
        cycles = GraphTopologicalAnalyzer.find_cycles(graph.node_ids(), graph.edges)
        if cycles:
            for cycle in cycles:
                cycle_str = " -> ".join(cycle)
                errors.append(
                    ValidationErrorDetail(
                        code="E_DEPENDENCY_CYCLE",
                        message=f"Deadlock detected: Dependency graph contains circular dependency cycle: {cycle_str}. Tasks cannot depend on themselves directly or indirectly.",
                    )
                )

        return errors, warnings


class CodeDiagramValidator(BaseDiagramValidator):
    """
    Code-to-Diagram Explainer validation:
    - Validates source code location references (line_start <= line_end)
    - Validates execution trace snapshots (sequential step ordering)
    - Distinguishes static analysis from observed execution
    """

    def validate(self, graph: DiagramGraph) -> Tuple[List[ValidationErrorDetail], List[ValidationWarning]]:
        errors: List[ValidationErrorDetail] = []
        warnings: List[ValidationWarning] = []

        for node in graph.nodes:
            if node.source_location:
                sl = node.source_location
                if sl.line_start < 1 or sl.line_end < 1:
                    errors.append(
                        ValidationErrorDetail(
                            code="E_INVALID_SOURCE_LINE",
                            message=f"Node '{node.label}' has non-positive line numbers: start={sl.line_start}, end={sl.line_end}.",
                            element_id=node.id,
                        )
                    )
                if sl.line_end < sl.line_start:
                    errors.append(
                        ValidationErrorDetail(
                            code="E_INVALID_SOURCE_RANGE",
                            message=f"Node '{node.label}' has invalid line range: end ({sl.line_end}) < start ({sl.line_start}).",
                            element_id=node.id,
                        )
                    )

        traced_nodes = [n for n in graph.nodes if n.execution_state is not None]
        if traced_nodes:
            step_ids = [n.execution_state.step_id for n in traced_nodes]
            if len(step_ids) != len(set(step_ids)):
                warnings.append(
                    ValidationWarning(
                        code="W_CODE_TRACE_STEP_COLLISION",
                        message="Multiple nodes share identical execution step_id in trace snapshot.",
                        level="warning",
                    )
                )

        return errors, warnings


def validate_diagram(graph: DiagramGraph, max_nodes: int = 500, max_edges: int = 1000) -> ValidationReport:
    """
    Universal diagram validation pipeline:
    1. Structural graph integrity (unique IDs, referential integrity, size caps)
    2. Duplicate relationships detection
    3. Diagram-family specific semantic validation
    4. Graph metrics computation
    """
    errors: List[ValidationErrorDetail] = []
    warnings: List[ValidationWarning] = []

    # 1. Structural graph checks
    if not graph.nodes:
        errors.append(
            ValidationErrorDetail(
                code="E_EMPTY_GRAPH",
                message="Graph contains 0 nodes. A valid diagram requires at least one node.",
            )
        )
        return ValidationReport(
            is_valid=False,
            diagram_type=graph.diagram_type,
            errors=errors,
            warnings=warnings,
            metrics={"node_count": 0, "edge_count": 0},
        )

    # Size limits
    if len(graph.nodes) > max_nodes:
        errors.append(
            ValidationErrorDetail(
                code="E_GRAPH_TOO_LARGE",
                message=f"Graph node count ({len(graph.nodes)}) exceeds maximum allowed limit ({max_nodes}).",
            )
        )
    if len(graph.edges) > max_edges:
        errors.append(
            ValidationErrorDetail(
                code="E_GRAPH_TOO_LARGE",
                message=f"Graph edge count ({len(graph.edges)}) exceeds maximum allowed limit ({max_edges}).",
            )
        )

    # Unique node IDs
    node_ids: Set[str] = set()
    for n in graph.nodes:
        if n.id in node_ids:
            errors.append(
                ValidationErrorDetail(
                    code="E_DUPLICATE_NODE_ID",
                    message=f"Duplicate node ID detected: '{n.id}'. All node IDs must be strictly unique.",
                    element_id=n.id,
                )
            )
        else:
            node_ids.add(n.id)

    # Referential integrity & unique edge IDs
    edge_ids: Set[str] = set()
    seen_edges: Set[Tuple[str, str, str]] = set()

    for e in graph.edges:
        if e.id in edge_ids:
            errors.append(
                ValidationErrorDetail(
                    code="E_DUPLICATE_EDGE_ID",
                    message=f"Duplicate edge ID detected: '{e.id}'. All edge IDs must be strictly unique.",
                    element_id=e.id,
                )
            )
        else:
            edge_ids.add(e.id)

        if e.source not in node_ids:
            errors.append(
                ValidationErrorDetail(
                    code="E_DANGLING_EDGE",
                    message=f"Edge '{e.id}' references unknown source node '{e.source}'.",
                    element_id=e.id,
                )
            )
        if e.target not in node_ids:
            errors.append(
                ValidationErrorDetail(
                    code="E_DANGLING_EDGE",
                    message=f"Edge '{e.id}' references unknown target node '{e.target}'.",
                    element_id=e.id,
                )
            )

        edge_key = (e.source, e.target, e.edge_type)
        if edge_key in seen_edges:
            warnings.append(
                ValidationWarning(
                    code="W_DUPLICATE_EDGE",
                    message=f"Duplicate relationship between '{e.source}' and '{e.target}' of type '{e.edge_type}'.",
                    level="info",
                    element_id=e.id,
                )
            )
        else:
            seen_edges.add(edge_key)

    # 2. Family-specific validation dispatch
    validator_map: Dict[DiagramType, BaseDiagramValidator] = {
        DiagramType.FLOWCHART: FlowchartValidator(),
        DiagramType.ARCHITECTURE: ArchitectureValidator(),
        DiagramType.CONCEPT_MAP: ConceptMapValidator(),
        DiagramType.ER_DIAGRAM: ERDiagramValidator(),
        DiagramType.SEQUENCE_DIAGRAM: SequenceDiagramValidator(),
        DiagramType.NETWORK_TOPOLOGY: NetworkTopologyValidator(),
        DiagramType.DEPENDENCY_GRAPH: DependencyGraphValidator(),
        DiagramType.CODE_FLOW: CodeDiagramValidator(),
        DiagramType.CODE_CALL_GRAPH: CodeDiagramValidator(),
        DiagramType.CODE_DATA_FLOW: CodeDiagramValidator(),
        DiagramType.CODE_CLASS_HIERARCHY: CodeDiagramValidator(),
    }

    family_validator = validator_map.get(graph.diagram_type)
    if family_validator:
        fam_errors, fam_warnings = family_validator.validate(graph)
        errors.extend(fam_errors)
        warnings.extend(fam_warnings)

    # 3. Compute graph metrics
    metrics = GraphTopologicalAnalyzer.compute_metrics(node_ids, graph.edges)
    cycles = GraphTopologicalAnalyzer.find_cycles(node_ids, graph.edges)
    metrics["has_cycles"] = len(cycles) > 0
    metrics["cycle_count"] = len(cycles)

    is_valid = len(errors) == 0

    return ValidationReport(
        is_valid=is_valid,
        diagram_type=graph.diagram_type,
        errors=errors,
        warnings=warnings,
        metrics=metrics,
    )
