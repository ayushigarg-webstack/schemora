"""
Unit tests for Generalized Intermediate Representation (IR) models and schema serialization.
"""

import sys
import os
import json
import pytest
from pathlib import Path

# Add ml-engine to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "ml-engine"))

from ir.models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramType,
    NodeShape,
    SourceLocation,
    ExecutionStateSnapshot,
    LayoutCoordinate,
    NodeStyle,
    ValidationWarning,
    ValidationErrorDetail,
    ValidationReport,
    DiagramMetadata,
)


def test_diagram_node_creation():
    node = DiagramNode(
        id="node_1",
        label="Order Service",
        type="service",
        attributes={"framework": "FastAPI", "port": 8000},
        confidence=0.95,
    )
    assert node.id == "node_1"
    assert node.label == "Order Service"
    assert node.type == "service"
    assert node.attributes["port"] == 8000
    assert node.confidence == 0.95


def test_diagram_node_whitespace_stripping():
    node = DiagramNode(id="  node_ws  ", label="  Label  ", type="  process  ")
    assert node.id == "node_ws"
    assert node.label == "Label"
    assert node.type == "process"


def test_diagram_node_empty_id_raises():
    with pytest.raises(ValueError):
        DiagramNode(id="", label="Test", type="process")
    with pytest.raises(ValueError):
        DiagramNode(id="   ", label="Test", type="process")


def test_diagram_edge_creation():
    edge = DiagramEdge(
        id="edge_1",
        source="node_1",
        target="node_2",
        label="calls API",
        edge_type="http_request",
        directed=True,
        cardinality="1:N",
        sequence_order=1,
    )
    assert edge.id == "edge_1"
    assert edge.source == "node_1"
    assert edge.target == "node_2"
    assert edge.directed is True
    assert edge.sequence_order == 1


def test_source_location_validation():
    # Valid source location
    sl = SourceLocation(
        file_path="src/order.py",
        line_start=10,
        line_end=25,
        col_start=0,
        col_end=40,
        symbol_name="create_order",
    )
    assert sl.line_start == 10
    assert sl.line_end == 25

    # Invalid source location: line_end < line_start
    with pytest.raises(ValueError, match="cannot be less than line_start"):
        SourceLocation(file_path="src/order.py", line_start=30, line_end=20)


def test_execution_state_snapshot():
    snapshot = ExecutionStateSnapshot(
        step_id=3,
        line_number=14,
        event_type="line",
        function_name="calculate_total",
        call_stack=["main", "checkout", "calculate_total"],
        variables={"subtotal": 120.50, "discount": 0.10},
        is_runtime_observed=True,
        explanation="Applying 10% discount to subtotal of $120.50",
    )
    assert snapshot.step_id == 3
    assert snapshot.variables["discount"] == 0.10
    assert snapshot.is_runtime_observed is True


def test_json_roundtrip_serialization():
    graph = DiagramGraph(
        id="FLOW_0001",
        diagram_type=DiagramType.FLOWCHART,
        metadata=DiagramMetadata(title="Login Flow", domain="security"),
        nodes=[
            DiagramNode(id="n1", label="Start", type="terminal", position=LayoutCoordinate(x=0.0, y=0.0)),
            DiagramNode(id="n2", label="Enter Credentials", type="process", position=LayoutCoordinate(x=0.0, y=50.0)),
        ],
        edges=[
            DiagramEdge(id="e1", source="n1", target="n2", label="proceed", edge_type="flow", directed=True)
        ],
    )

    json_str = graph.to_json()
    assert isinstance(json_str, str)

    restored = DiagramGraph.from_json(json_str)
    assert restored.id == graph.id
    assert restored.diagram_type == DiagramType.FLOWCHART
    assert len(restored.nodes) == 2
    assert len(restored.edges) == 1
    assert restored.nodes[0].position.x == 0.0
    assert restored.to_dict() == graph.to_dict()


def test_backward_compatibility_with_dataset():
    """Verifies that all 700 samples in data/dataset.json seamlessly load into DiagramGraph."""
    dataset_path = Path(__file__).parent.parent / "data" / "dataset.json"
    assert dataset_path.exists(), "data/dataset.json must exist"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 700
    for idx, sample in enumerate(data):
        graph = DiagramGraph.from_dict(sample)
        assert graph.id == sample["id"]
        assert graph.diagram_type.value == sample["diagram_type"]
        assert len(graph.nodes) == len(sample["nodes"])
        assert len(graph.edges) == len(sample["edges"])


def test_backward_compatibility_with_splits():
    """Verifies train, val, and test split JSON files can be deserialized into DiagramGraph."""
    splits_dir = Path(__file__).parent.parent / "data" / "splits"
    for split_name in ["train.json", "val.json", "test.json"]:
        split_path = splits_dir / split_name
        assert split_path.exists(), f"{split_name} must exist"
        with open(split_path, "r", encoding="utf-8") as f:
            split_data = json.load(f)
        for sample in split_data:
            graph = DiagramGraph.from_dict(sample)
            assert len(graph.nodes) >= 2


def test_dataset_all_samples_semantic_validation_pass():
    """Verifies that all 700 samples in dataset.json pass semantic diagram validation."""
    from ir.validators import validate_diagram

    dataset_path = Path(__file__).parent.parent / "data" / "dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    invalid_samples = []
    for sample in data:
        graph = DiagramGraph.from_dict(sample)
        report = validate_diagram(graph)
        if not report.is_valid:
            invalid_samples.append((sample["id"], [e.message for e in report.errors]))

    assert len(invalid_samples) == 0, f"Found {len(invalid_samples)} invalid samples: {invalid_samples[:5]}"

