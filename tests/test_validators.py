"""
Comprehensive test suite for Diagram IR validators across all diagram families and code explainer semantics.
"""

import sys
import os
import pytest
from pathlib import Path

# Add ml-engine to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "ml-engine"))

from ir.models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramType,
    SourceLocation,
    ExecutionStateSnapshot,
)
from ir.validators import validate_diagram


# ============================================================================
# 1. STRUCTURAL INTEGRITY TESTS
# ============================================================================

def test_empty_graph_fails():
    graph = DiagramGraph(diagram_type=DiagramType.FLOWCHART, nodes=[], edges=[])
    report = validate_diagram(graph)
    assert not report.is_valid
    assert any(err.code == "E_EMPTY_GRAPH" for err in report.errors)


def test_duplicate_node_id_fails():
    graph = DiagramGraph(
        diagram_type=DiagramType.FLOWCHART,
        nodes=[
            DiagramNode(id="node_a", label="First", type="process"),
            DiagramNode(id="node_a", label="Duplicate", type="process"),
        ],
        edges=[],
    )
    report = validate_diagram(graph)
    assert not report.is_valid
    assert any(err.code == "E_DUPLICATE_NODE_ID" for err in report.errors)


def test_duplicate_edge_id_fails():
    graph = DiagramGraph(
        diagram_type=DiagramType.FLOWCHART,
        nodes=[
            DiagramNode(id="n1", label="First", type="process"),
            DiagramNode(id="n2", label="Second", type="process"),
        ],
        edges=[
            DiagramEdge(id="e1", source="n1", target="n2", edge_type="flow"),
            DiagramEdge(id="e1", source="n1", target="n2", edge_type="flow"),
        ],
    )
    report = validate_diagram(graph)
    assert not report.is_valid
    assert any(err.code == "E_DUPLICATE_EDGE_ID" for err in report.errors)


def test_dangling_edge_fails():
    graph = DiagramGraph(
        diagram_type=DiagramType.FLOWCHART,
        nodes=[DiagramNode(id="n1", label="Existing", type="process")],
        edges=[DiagramEdge(id="e1", source="n1", target="non_existent_node", edge_type="flow")],
    )
    report = validate_diagram(graph)
    assert not report.is_valid
    assert any(err.code == "E_DANGLING_EDGE" for err in report.errors)


def test_oversized_graph_fails():
    nodes = [DiagramNode(id=f"n_{i}", label=f"Node {i}", type="process") for i in range(15)]
    graph = DiagramGraph(diagram_type=DiagramType.FLOWCHART, nodes=nodes, edges=[])
    report = validate_diagram(graph, max_nodes=10)
    assert not report.is_valid
    assert any(err.code == "E_GRAPH_TOO_LARGE" for err in report.errors)


# ============================================================================
# 2. FLOWCHART VALIDATION TESTS
# ============================================================================

def test_valid_flowchart_with_cycle():
    """Flowcharts legitimately permit cycles (loops/retries)."""
    graph = DiagramGraph(
        diagram_type=DiagramType.FLOWCHART,
        nodes=[
            DiagramNode(id="n1", label="Start", type="terminal"),
            DiagramNode(id="n2", label="Check Condition", type="decision"),
            DiagramNode(id="n3", label="Process Step", type="process"),
            DiagramNode(id="n4", label="End", type="terminal"),
        ],
        edges=[
            DiagramEdge(id="e1", source="n1", target="n2", label="begins", edge_type="flow"),
            DiagramEdge(id="e2", source="n2", target="n3", label="Retry", edge_type="branch_yes"),
            DiagramEdge(id="e3", source="n3", target="n2", label="loops back", edge_type="loop_back"),
            DiagramEdge(id="e4", source="n2", target="n4", label="Done", edge_type="branch_no"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert len(report.errors) == 0
    assert report.metrics["has_cycles"] is True


def test_flowchart_decision_with_single_branch_fails():
    """A decision node with fewer than 2 outgoing branches is an invalid flowchart."""
    graph = DiagramGraph(
        diagram_type=DiagramType.FLOWCHART,
        nodes=[
            DiagramNode(id="n1", label="Start", type="terminal"),
            DiagramNode(id="n2", label="Is Valid?", type="decision"),
            DiagramNode(id="n3", label="Continue", type="process"),
        ],
        edges=[
            DiagramEdge(id="e1", source="n1", target="n2", edge_type="flow"),
            DiagramEdge(id="e2", source="n2", target="n3", label="Yes", edge_type="branch_yes"),
        ],
    )
    report = validate_diagram(graph)
    assert not report.is_valid
    assert any(err.code == "E_DECISION_INSUFFICIENT_BRANCHES" for err in report.errors)


# ============================================================================
# 3. SOFTWARE ARCHITECTURE VALIDATION TESTS
# ============================================================================

def test_valid_software_architecture():
    graph = DiagramGraph(
        diagram_type=DiagramType.ARCHITECTURE,
        nodes=[
            DiagramNode(id="client", label="React App", type="client"),
            DiagramNode(id="gw", label="API Gateway", type="api_gateway"),
            DiagramNode(id="svc", label="Order Service", type="service"),
            DiagramNode(id="db", label="Postgres DB", type="database"),
        ],
        edges=[
            DiagramEdge(id="e1", source="client", target="gw", label="HTTPS", edge_type="http_request"),
            DiagramEdge(id="e2", source="gw", target="svc", label="gRPC", edge_type="rpc_call"),
            DiagramEdge(id="e3", source="svc", target="db", label="read/write", edge_type="db_read_write"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert len(report.errors) == 0


def test_architecture_client_direct_db_warning():
    """Direct client to DB connection triggers anti-pattern warning."""
    graph = DiagramGraph(
        diagram_type=DiagramType.ARCHITECTURE,
        nodes=[
            DiagramNode(id="client", label="Mobile App", type="client"),
            DiagramNode(id="db", label="Production DB", type="database"),
        ],
        edges=[
            DiagramEdge(id="e1", source="client", target="db", label="direct SQL", edge_type="db_read_write"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert any(w.code == "W_ARCH_CLIENT_DIRECT_DB" for w in report.warnings)


# ============================================================================
# 4. CONCEPT MAP VALIDATION TESTS
# ============================================================================

def test_valid_concept_map():
    graph = DiagramGraph(
        diagram_type=DiagramType.CONCEPT_MAP,
        nodes=[
            DiagramNode(id="c1", label="Data Structures", type="concept"),
            DiagramNode(id="c2", label="Trees", type="concept"),
            DiagramNode(id="c3", label="Binary Search Tree", type="concept"),
        ],
        edges=[
            DiagramEdge(id="e1", source="c1", target="c2", label="classified as", edge_type="is_a"),
            DiagramEdge(id="e2", source="c2", target="c3", label="specialized by", edge_type="is_a"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert len(report.errors) == 0


def test_concept_map_unlabeled_warning():
    """More than 50% unlabeled edges triggers a concept map warning."""
    graph = DiagramGraph(
        diagram_type=DiagramType.CONCEPT_MAP,
        nodes=[
            DiagramNode(id="c1", label="Algorithms", type="concept"),
            DiagramNode(id="c2", label="Sorting", type="concept"),
            DiagramNode(id="c3", label="Searching", type="concept"),
        ],
        edges=[
            DiagramEdge(id="e1", source="c1", target="c2", label="", edge_type="relates_to"),
            DiagramEdge(id="e2", source="c1", target="c3", label="", edge_type="relates_to"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert any(w.code == "W_CONCEPT_UNLABELED_RELATIONS" for w in report.warnings)


# ============================================================================
# 5. ER DIAGRAM VALIDATION TESTS
# ============================================================================

def test_valid_er_diagram():
    graph = DiagramGraph(
        diagram_type=DiagramType.ER_DIAGRAM,
        nodes=[
            DiagramNode(id="e1", label="Student", type="entity"),
            DiagramNode(id="k1", label="student_id (PK)", type="key_attribute"),
            DiagramNode(id="e2", label="Course", type="entity"),
        ],
        edges=[
            DiagramEdge(id="rel1", source="e1", target="k1", label="primary key", edge_type="has_attribute"),
            DiagramEdge(id="rel2", source="e1", target="e2", label="enrolls (M:N)", cardinality="M:N", edge_type="many_to_many"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert len(report.errors) == 0


def test_er_key_attached_to_non_entity_fails():
    """A primary key attached to a non-entity is invalid ER semantics."""
    graph = DiagramGraph(
        diagram_type=DiagramType.ER_DIAGRAM,
        nodes=[
            DiagramNode(id="a1", label="Email", type="attribute"),
            DiagramNode(id="k1", label="key_id", type="key_attribute"),
        ],
        edges=[
            DiagramEdge(id="rel1", source="a1", target="k1", edge_type="has_attribute"),
        ],
    )
    report = validate_diagram(graph)
    assert not report.is_valid
    assert any(err.code == "E_KEY_ATTACHED_TO_NON_ENTITY" for err in report.errors)


# ============================================================================
# 6. SEQUENCE DIAGRAM VALIDATION TESTS
# ============================================================================

def test_valid_sequence_diagram():
    graph = DiagramGraph(
        diagram_type=DiagramType.SEQUENCE_DIAGRAM,
        nodes=[
            DiagramNode(id="actor", label="Customer", type="actor"),
            DiagramNode(id="fe", label="Frontend", type="participant"),
            DiagramNode(id="be", label="Backend", type="participant"),
        ],
        edges=[
            DiagramEdge(id="m1", source="actor", target="fe", label="Submit Order", sequence_order=1, edge_type="sync_call"),
            DiagramEdge(id="m2", source="fe", target="be", label="POST /orders", sequence_order=2, edge_type="sync_call"),
            DiagramEdge(id="m3", source="be", target="fe", label="OrderCreated", sequence_order=3, edge_type="return_value"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert len(report.errors) == 0


def test_sequence_diagram_temporal_cycle_fails():
    """A return message with sequence order <= request violates chronological flow."""
    graph = DiagramGraph(
        diagram_type=DiagramType.SEQUENCE_DIAGRAM,
        nodes=[
            DiagramNode(id="p1", label="Service A", type="participant"),
            DiagramNode(id="p2", label="Service B", type="participant"),
        ],
        edges=[
            DiagramEdge(id="m1", source="p1", target="p2", label="request", sequence_order=5, edge_type="sync_call"),
            DiagramEdge(id="m2", source="p2", target="p1", label="response", sequence_order=2, edge_type="return_value"),
        ],
    )
    report = validate_diagram(graph)
    assert not report.is_valid
    assert any(err.code == "E_SEQUENCE_ORDER_INVERTED" for err in report.errors)


# ============================================================================
# 7. DEPENDENCY GRAPH VALIDATION TESTS
# ============================================================================

def test_valid_dependency_dag():
    graph = DiagramGraph(
        diagram_type=DiagramType.DEPENDENCY_GRAPH,
        nodes=[
            DiagramNode(id="t1", label="Compile Source", type="task"),
            DiagramNode(id="t2", label="Run Tests", type="task"),
            DiagramNode(id="t3", label="Deploy", type="milestone"),
        ],
        edges=[
            DiagramEdge(id="d1", source="t1", target="t2", edge_type="depends_on"),
            DiagramEdge(id="d2", source="t2", target="t3", edge_type="depends_on"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert len(report.errors) == 0
    assert report.metrics["has_cycles"] is False


def test_dependency_graph_cycle_strictly_fails():
    """Dependency graphs STRICTLY FORBID CYCLES (deadlock)."""
    graph = DiagramGraph(
        diagram_type=DiagramType.DEPENDENCY_GRAPH,
        nodes=[
            DiagramNode(id="t1", label="Task A", type="task"),
            DiagramNode(id="t2", label="Task B", type="task"),
            DiagramNode(id="t3", label="Task C", type="task"),
        ],
        edges=[
            DiagramEdge(id="d1", source="t1", target="t2", edge_type="depends_on"),
            DiagramEdge(id="d2", source="t2", target="t3", edge_type="depends_on"),
            DiagramEdge(id="d3", source="t3", target="t1", edge_type="depends_on"),
        ],
    )
    report = validate_diagram(graph)
    assert not report.is_valid
    assert any(err.code == "E_DEPENDENCY_CYCLE" for err in report.errors)


# ============================================================================
# 8. NETWORK TOPOLOGY VALIDATION TESTS
# ============================================================================

def test_valid_network_topology():
    graph = DiagramGraph(
        diagram_type=DiagramType.NETWORK_TOPOLOGY,
        nodes=[
            DiagramNode(id="w1", label="PC 1", type="workstation"),
            DiagramNode(id="sw", label="Access Switch", type="switch"),
            DiagramNode(id="rt", label="Core Router", type="router"),
        ],
        edges=[
            DiagramEdge(id="e1", source="w1", target="sw", edge_type="ethernet", directed=False),
            DiagramEdge(id="e2", source="sw", target="rt", edge_type="ethernet", directed=False),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert len(report.errors) == 0


def test_network_disconnected_device_warning():
    graph = DiagramGraph(
        diagram_type=DiagramType.NETWORK_TOPOLOGY,
        nodes=[
            DiagramNode(id="w1", label="Connected PC", type="workstation"),
            DiagramNode(id="sw", label="Switch", type="switch"),
            DiagramNode(id="isolated", label="Unplugged Server", type="server"),
        ],
        edges=[
            DiagramEdge(id="e1", source="w1", target="sw", edge_type="ethernet", directed=False),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert any(w.code == "W_NET_DISCONNECTED_DEVICE" for w in report.warnings)


# ============================================================================
# 9. CODE-TO-DIAGRAM EXPLAINER VALIDATION TESTS
# ============================================================================

def test_valid_code_flow_diagram():
    graph = DiagramGraph(
        diagram_type=DiagramType.CODE_FLOW,
        nodes=[
            DiagramNode(
                id="block_1",
                label="def check_loan()",
                type="function_def",
                source_location=SourceLocation(file_path="loan.py", line_start=1, line_end=15),
            ),
            DiagramNode(
                id="block_2",
                label="if credit_score >= 750:",
                type="condition",
                source_location=SourceLocation(file_path="loan.py", line_start=5, line_end=9),
                execution_state=ExecutionStateSnapshot(step_id=1, line_number=5, variables={"credit_score": 780}),
            ),
        ],
        edges=[
            DiagramEdge(id="cfg_1", source="block_1", target="block_2", edge_type="flow"),
        ],
    )
    report = validate_diagram(graph)
    assert report.is_valid
    assert len(report.errors) == 0


def test_code_diagram_invalid_source_range_fails():
    with pytest.raises(ValueError, match="cannot be less than line_start"):
        SourceLocation(file_path="app.py", line_start=20, line_end=10)
