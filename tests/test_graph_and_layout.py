"""
Comprehensive unit and integration tests for Graph Processing and Diagram Layout Engines.
Tests NetworkX connectivity, reachability, cycle semantics, duplicate normalization,
and all 7 diagram layout strategies.
"""

import pytest
from ir.models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramType,
    DiagramMetadata,
    LayoutCoordinate,
)
from graph.processor import GraphProcessor
from layout.engine import DiagramLayoutEngine
from layout.models import LayoutOptions, LayoutStrategy


# --- Fixtures ---

@pytest.fixture
def sample_flowchart_with_loop() -> DiagramGraph:
    """Flowchart with a while-loop cycle (n3 -> n2)."""
    return DiagramGraph(
        id="flow_loop",
        diagram_type=DiagramType.FLOWCHART,
        nodes=[
            DiagramNode(id="start", label="Start", type="terminal"),
            DiagramNode(id="init", label="i = 0", type="process"),
            DiagramNode(id="check", label="i < 5?", type="decision"),
            DiagramNode(id="body", label="i = i + 1", type="process"),
            DiagramNode(id="end", label="Done", type="terminal"),
        ],
        edges=[
            DiagramEdge(id="e1", source="start", target="init", edge_type="flow"),
            DiagramEdge(id="e2", source="init", target="check", edge_type="flow"),
            DiagramEdge(id="e3", source="check", target="body", label="True", edge_type="branch_yes"),
            DiagramEdge(id="e4", source="body", target="check", label="repeat", edge_type="flow"),
            DiagramEdge(id="e5", source="check", target="end", label="False", edge_type="branch_no"),
        ],
    )


@pytest.fixture
def sample_disconnected_graph() -> DiagramGraph:
    """Graph with two disconnected components and an isolated node."""
    return DiagramGraph(
        id="disconnected",
        diagram_type=DiagramType.ARCHITECTURE,
        nodes=[
            # Component 1
            DiagramNode(id="web", label="Web App", type="client"),
            DiagramNode(id="api", label="API Gateway", type="gateway"),
            # Component 2
            DiagramNode(id="worker", label="Worker", type="worker"),
            DiagramNode(id="queue", label="Queue", type="queue"),
            # Isolated
            DiagramNode(id="standalone", label="Analytics", type="service"),
        ],
        edges=[
            DiagramEdge(id="e1", source="web", target="api", edge_type="http"),
            DiagramEdge(id="e2", source="worker", target="queue", edge_type="message"),
        ],
    )


# --- 1. Graph Integrity and Connectivity Tests ---

def test_graph_integrity_valid(sample_flowchart_with_loop):
    res = GraphProcessor.check_integrity(sample_flowchart_with_loop)
    assert res.is_valid is True
    assert len(res.errors) == 0
    assert len(res.missing_nodes) == 0


def test_graph_integrity_dangling_edge():
    graph = DiagramGraph(
        id="dangling",
        diagram_type=DiagramType.FLOWCHART,
        nodes=[DiagramNode(id="n1", label="A", type="process")],
        edges=[DiagramEdge(id="e1", source="n1", target="n_ghost", edge_type="flow")],
    )
    res = GraphProcessor.check_integrity(graph)
    assert res.is_valid is False
    assert "n_ghost" in res.missing_nodes


def test_connectivity_analysis(sample_disconnected_graph):
    res = GraphProcessor.analyze_connectivity(sample_disconnected_graph)
    assert res.is_weakly_connected is False
    assert res.wcc_count == 3  # (web, api), (worker, queue), (standalone)
    assert res.largest_component_size == 2


def test_reachability_analysis(sample_flowchart_with_loop):
    res = GraphProcessor.analyze_reachability(sample_flowchart_with_loop)
    assert "start" in res.root_nodes
    assert "end" in res.leaf_nodes
    assert len(res.unreachable_nodes) == 0
    assert "end" in res.reachability_map["start"]


# --- 2. Cycle Detection According to Diagram Semantics ---

def test_flowchart_cycle_permitted(sample_flowchart_with_loop):
    cycle_res = GraphProcessor.detect_cycles(sample_flowchart_with_loop)
    assert cycle_res.has_cycles is True
    assert cycle_res.cycle_count == 1
    assert cycle_res.is_valid_for_diagram is True  # Valid in flowcharts!
    assert any("Permitted iterative loop" in note for note in cycle_res.semantic_notes)


def test_dependency_graph_cycle_rejected():
    dep_graph = DiagramGraph(
        id="cyclic_dep",
        diagram_type=DiagramType.DEPENDENCY_GRAPH,
        nodes=[
            DiagramNode(id="pkg_a", label="pkg_a", type="package"),
            DiagramNode(id="pkg_b", label="pkg_b", type="package"),
        ],
        edges=[
            DiagramEdge(id="e1", source="pkg_a", target="pkg_b", edge_type="depends_on"),
            DiagramEdge(id="e2", source="pkg_b", target="pkg_a", edge_type="depends_on"),
        ],
    )
    cycle_res = GraphProcessor.detect_cycles(dep_graph)
    assert cycle_res.has_cycles is True
    assert cycle_res.is_valid_for_diagram is False  # Circular dependencies are fatal!
    assert any("FATAL" in note for note in cycle_res.semantic_notes)


def test_architecture_cycle_permitted_with_warning():
    arch_graph = DiagramGraph(
        id="arch_cycle",
        diagram_type=DiagramType.ARCHITECTURE,
        nodes=[
            DiagramNode(id="svc_a", label="Order Service", type="service"),
            DiagramNode(id="svc_b", label="Payment Service", type="service"),
        ],
        edges=[
            DiagramEdge(id="e1", source="svc_a", target="svc_b", edge_type="rpc"),
            DiagramEdge(id="e2", source="svc_b", target="svc_a", edge_type="callback"),
        ],
    )
    cycle_res = GraphProcessor.detect_cycles(arch_graph)
    assert cycle_res.has_cycles is True
    assert cycle_res.is_valid_for_diagram is True
    assert any("Architectural circular dependency" in note for note in cycle_res.semantic_notes)


# --- 3. Duplicate Relationship Normalization ---

def test_relationship_normalization():
    graph = DiagramGraph(
        id="dup_edges",
        diagram_type=DiagramType.ARCHITECTURE,
        nodes=[
            DiagramNode(id="srv1", label="Client", type="client"),
            DiagramNode(id="srv2", label="Backend", type="service"),
        ],
        edges=[
            DiagramEdge(id="e1", source="srv1", target="srv2", label="GET /items", edge_type="http"),
            DiagramEdge(id="e2", source="srv1", target="srv2", label="POST /order", edge_type="http"),
        ],
    )
    norm = GraphProcessor.normalize_relationships(graph, merge_parallel_edges=True)
    assert len(norm.edges) == 1
    assert "GET /items" in norm.edges[0].label
    assert "POST /order" in norm.edges[0].label
    assert norm.edges[0].metadata["merged_count"] == 2


# --- 4. Diagram-Specific Layout Strategy Tests ---

def test_flowchart_layout_stable_coordinates(sample_flowchart_with_loop):
    laid_out = DiagramLayoutEngine.layout(sample_flowchart_with_loop)
    assert laid_out.layout_config is not None
    assert laid_out.layout_config["strategy"] == LayoutStrategy.LAYERED_SUGIYAMA.value

    # All nodes have non-null, valid coordinates
    for node in laid_out.nodes:
        assert node.position is not None
        assert node.position.x >= 0.0
        assert node.position.y >= 0.0
        assert node.position.width > 0.0
        assert node.position.height > 0.0

    # Start should be at top (lower Y than End in TB layout)
    start_node = laid_out.get_node("start")
    end_node = laid_out.get_node("end")
    assert start_node.position.y < end_node.position.y


def test_architecture_tiered_layout():
    arch = DiagramGraph(
        id="tiered_arch",
        diagram_type=DiagramType.ARCHITECTURE,
        nodes=[
            DiagramNode(id="ui", label="React Frontend", type="client"),
            DiagramNode(id="gw", label="API Gateway", type="gateway"),
            DiagramNode(id="svc", label="Order Service", type="service"),
            DiagramNode(id="db", label="Postgres DB", type="database"),
        ],
        edges=[
            DiagramEdge(id="e1", source="ui", target="gw", edge_type="http"),
            DiagramEdge(id="e2", source="gw", target="svc", edge_type="grpc"),
            DiagramEdge(id="e3", source="svc", target="db", edge_type="sql"),
        ],
    )
    laid_out = DiagramLayoutEngine.layout(arch)
    assert laid_out.layout_config["strategy"] == LayoutStrategy.HIERARCHICAL_TIERED.value

    # Check tier monotonicity: UI < GW < SVC < DB on Y axis
    ui = laid_out.get_node("ui")
    gw = laid_out.get_node("gw")
    svc = laid_out.get_node("svc")
    db = laid_out.get_node("db")

    assert ui.position.y < gw.position.y
    assert gw.position.y < svc.position.y
    assert svc.position.y < db.position.y


def test_concept_map_force_directed_layout():
    cmap = DiagramGraph(
        id="cmap_test",
        diagram_type=DiagramType.CONCEPT_MAP,
        nodes=[
            DiagramNode(id="c1", label="Machine Learning", type="concept"),
            DiagramNode(id="c2", label="Supervised Learning", type="concept"),
            DiagramNode(id="c3", label="Neural Networks", type="concept"),
            DiagramNode(id="c4", label="Deep Learning", type="concept"),
        ],
        edges=[
            DiagramEdge(id="e1", source="c1", target="c2", label="subfield", edge_type="is_a"),
            DiagramEdge(id="e2", source="c2", target="c3", label="utilizes", edge_type="uses"),
            DiagramEdge(id="e3", source="c3", target="c4", label="forms basis of", edge_type="leads_to"),
        ],
    )
    laid_out = DiagramLayoutEngine.layout(cmap)
    assert laid_out.layout_config["strategy"] == LayoutStrategy.FORCE_DIRECTED.value

    # Positions should be non-overlapping
    coords = [n.position for n in laid_out.nodes]
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            dist = ((coords[i].x - coords[j].x) ** 2 + (coords[i].y - coords[j].y) ** 2) ** 0.5
            assert dist > 30.0, "Nodes in concept map should not collide"


def test_sequence_diagram_lifeline_layout():
    seq = DiagramGraph(
        id="seq_test",
        diagram_type=DiagramType.SEQUENCE_DIAGRAM,
        nodes=[
            DiagramNode(id="client", label="Client", type="participant"),
            DiagramNode(id="auth", label="Auth Service", type="participant"),
            DiagramNode(id="db", label="User DB", type="participant"),
        ],
        edges=[
            DiagramEdge(id="m1", source="client", target="auth", label="login()", sequence_order=1),
            DiagramEdge(id="m2", source="auth", target="db", label="query_user()", sequence_order=2),
            DiagramEdge(id="m3", source="db", target="auth", label="user_record", sequence_order=3),
            DiagramEdge(id="m4", source="auth", target="client", label="token", sequence_order=4),
        ],
    )
    laid_out = DiagramLayoutEngine.layout(seq)
    assert laid_out.layout_config["strategy"] == LayoutStrategy.TIMELINE_LIFELINE.value

    # Participants should have distinct, ascending X coordinates
    p1 = laid_out.get_node("client")
    p2 = laid_out.get_node("auth")
    p3 = laid_out.get_node("db")
    assert p1.position.x < p2.position.x < p3.position.x
    assert p1.position.y == p2.position.y == p3.position.y  # Lifeline heads aligned


def test_er_diagram_grid_layout():
    er = DiagramGraph(
        id="er_test",
        diagram_type=DiagramType.ER_DIAGRAM,
        nodes=[
            DiagramNode(id="Customer", label="Customer", type="entity"),
            DiagramNode(id="Order", label="Order", type="entity"),
            DiagramNode(id="OrderItem", label="OrderItem", type="entity"),
            DiagramNode(id="Product", label="Product", type="entity"),
        ],
        edges=[
            DiagramEdge(id="r1", source="Customer", target="Order", cardinality="1:N"),
            DiagramEdge(id="r2", source="Order", target="OrderItem", cardinality="1:N"),
            DiagramEdge(id="r3", source="Product", target="OrderItem", cardinality="1:N"),
        ],
    )
    laid_out = DiagramLayoutEngine.layout(er)
    assert laid_out.layout_config["strategy"] == LayoutStrategy.ORTHOGONAL_GRID.value
    assert len(laid_out.nodes) == 4
    for n in laid_out.nodes:
        assert n.position is not None


def test_network_topology_cluster_layout():
    net = DiagramGraph(
        id="net_test",
        diagram_type=DiagramType.NETWORK_TOPOLOGY,
        nodes=[
            DiagramNode(id="switch", label="Core Switch", type="switch"),
            DiagramNode(id="pc1", label="Workstation 1", type="workstation"),
            DiagramNode(id="pc2", label="Workstation 2", type="workstation"),
            DiagramNode(id="server", label="File Server", type="server"),
        ],
        edges=[
            DiagramEdge(id="l1", source="switch", target="pc1"),
            DiagramEdge(id="l2", source="switch", target="pc2"),
            DiagramEdge(id="l3", source="switch", target="server"),
        ],
    )
    laid_out = DiagramLayoutEngine.layout(net)
    assert laid_out.layout_config["strategy"] == LayoutStrategy.CLUSTER_TOPOLOGY.value
    # Hub node should be at center (rank 0)
    switch = laid_out.get_node("switch")
    assert switch.position.rank == 0


def test_layout_preserves_semantics(sample_flowchart_with_loop):
    original_ids = [n.id for n in sample_flowchart_with_loop.nodes]
    original_edges = [(e.source, e.target, e.label) for e in sample_flowchart_with_loop.edges]

    laid_out = DiagramLayoutEngine.layout(sample_flowchart_with_loop)

    assert [n.id for n in laid_out.nodes] == original_ids
    assert [(e.source, e.target, e.label) for e in laid_out.edges] == original_edges
    assert laid_out.diagram_type == sample_flowchart_with_loop.diagram_type


def test_empty_and_single_node_graph_layout():
    # Empty graph
    empty_graph = DiagramGraph(id="empty", diagram_type=DiagramType.FLOWCHART, nodes=[], edges=[])
    laid_out_empty = DiagramLayoutEngine.layout(empty_graph)
    assert len(laid_out_empty.nodes) == 0

    # Single node graph
    single = DiagramGraph(
        id="single",
        diagram_type=DiagramType.FLOWCHART,
        nodes=[DiagramNode(id="n1", label="Single", type="process")],
        edges=[],
    )
    laid_out_single = DiagramLayoutEngine.layout(single)
    assert len(laid_out_single.nodes) == 1
    assert laid_out_single.nodes[0].position.x >= 0.0
    assert laid_out_single.nodes[0].position.y >= 0.0
