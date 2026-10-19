"""
Comprehensive automated tests for FastAPI Backend API and Live Code Explainer Integration.
Tests health diagnostics, diagram generation, validation, static code analysis,
pedagogical explanations, sandboxed execution tracing, and security error handling.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure ml-engine and backend are on sys.path
root_dir = Path(__file__).parent.parent
for p in [str(root_dir / "ml-engine"), str(root_dir / "backend"), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
from ir.models import DiagramGraph, DiagramNode, DiagramEdge, DiagramType


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


# --- 1. Health & Discovery Endpoints ---

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["health"] == "/health"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert data["uptime_seconds"] >= 0.0

    # Subsystem component checks
    components = data["components"]
    assert "nlp_pipeline" in components
    assert "classifier_model" in components
    assert "layout_engine" in components
    assert "code_tracer_sandbox" in components

    assert components["nlp_pipeline"]["operational"] is True
    assert components["layout_engine"]["operational"] is True
    assert components["code_tracer_sandbox"]["operational"] is True


def test_diagram_types_endpoint(client):
    response = client.get("/api/diagram/types")
    assert response.status_code == 200
    types = response.json()
    assert len(types) >= 7

    type_names = {t["type"] for t in types}
    assert "flowchart" in type_names
    assert "architecture" in type_names
    assert "concept_map" in type_names
    assert "sequence_diagram" in type_names
    assert "er_diagram" in type_names
    assert "network_topology" in type_names
    assert "dependency_graph" in type_names

    for t in types:
        assert t["layout_strategy"] is not None
        assert len(t["example_prompt"]) > 5


def test_code_languages_endpoint(client):
    response = client.get("/api/code/languages")
    assert response.status_code == 200
    langs = response.json()
    assert len(langs) >= 1

    py_lang = next((l for l in langs if l["language"] == "python"), None)
    assert py_lang is not None
    assert py_lang["status"] == "supported"
    assert py_lang["is_sandboxed"] is True
    assert "execution_tracing" in py_lang["capabilities"]
    assert "cfg_generation" in py_lang["capabilities"]


# --- 2. Diagram Generation Endpoints ---

def test_generate_diagram_flowchart(client):
    payload = {
        "text": "User submits login form. If credentials valid, redirect to dashboard; otherwise show error.",
        "layout_direction": "TB"
    }
    response = client.post("/api/diagram/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["diagram_type"] == "flowchart"
    assert len(data["diagram"]["nodes"]) >= 3
    assert len(data["diagram"]["edges"]) >= 2

    # Check geometric layout was applied
    assert data["diagram"]["layout_config"] is not None
    for node in data["diagram"]["nodes"]:
        assert node["position"] is not None
        assert "x" in node["position"]
        assert "y" in node["position"]


def test_generate_diagram_architecture_with_override(client):
    payload = {
        "text": "Frontend communicates with API Gateway, which accesses Postgres database and Redis cache.",
        "diagram_type": "architecture",
        "layout_direction": "TB"
    }
    response = client.post("/api/diagram/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["diagram_type"] == "architecture"

    # Layout config reflects hierarchical tiered strategy
    assert data["diagram"]["layout_config"]["strategy"] == "hierarchical_tiered"


def test_generate_diagram_validation_error_empty_text(client):
    payload = {"text": "   "}
    response = client.post("/api/diagram/generate", json=payload)
    assert response.status_code in [400, 422]
    data = response.json()
    assert data["success"] is False
    assert "error" in data


# --- 3. Diagram Validation Endpoints ---

def test_validate_diagram_valid(client):
    valid_graph = DiagramGraph(
        id="valid_flow",
        diagram_type=DiagramType.FLOWCHART,
        nodes=[
            DiagramNode(id="start", label="Start", type="terminal"),
            DiagramNode(id="step", label="Process Step", type="process"),
            DiagramNode(id="end", label="Done", type="terminal"),
        ],
        edges=[
            DiagramEdge(id="e1", source="start", target="step", edge_type="flow"),
            DiagramEdge(id="e2", source="step", target="end", edge_type="flow"),
        ],
    )
    payload = {"diagram": valid_graph.to_dict()}
    response = client.post("/api/diagram/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert len(data["errors"]) == 0
    assert "density" in data["metrics"]


def test_validate_diagram_invalid_decision_node(client):
    invalid_graph = DiagramGraph(
        id="invalid_flow",
        diagram_type=DiagramType.FLOWCHART,
        nodes=[
            DiagramNode(id="start", label="Start", type="terminal"),
            DiagramNode(id="cond", label="Is Active?", type="decision"),
            DiagramNode(id="end", label="Done", type="terminal"),
        ],
        edges=[
            DiagramEdge(id="e1", source="start", target="cond", edge_type="flow"),
            # Decision node only has 1 outgoing branch, violating flowchart rules
            DiagramEdge(id="e2", source="cond", target="end", edge_type="branch_yes"),
        ],
    )
    payload = {"diagram": invalid_graph.to_dict()}
    response = client.post("/api/diagram/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert len(data["errors"]) >= 1
    assert any("decision" in err["message"].lower() for err in data["errors"])


# --- 4. Code Analysis Endpoints ---

def test_code_analyze_cfg(client):
    py_code = """x = 10
if x > 5:
    res = "large"
else:
    res = "small"
"""
    payload = {
        "code": py_code,
        "language": "python",
        "view_mode": "cfg"
    }
    response = client.post("/api/code/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["language"] == "python"
    assert data["view_mode"] == "cfg"
    assert data["total_nodes"] >= 4

    # Every node has SourceLocation line mapping
    for node in data["diagram"]["nodes"]:
        assert node["source_location"] is not None
        assert node["source_location"]["line_start"] >= 1


def test_code_analyze_call_graph(client):
    py_code = """def foo():
    return 1

def bar():
    return foo()
"""
    payload = {
        "code": py_code,
        "language": "python",
        "view_mode": "call_graph"
    }
    response = client.post("/api/code/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["view_mode"] == "call_graph"
    assert data["total_nodes"] == 2


def test_code_analyze_unsupported_language(client):
    payload = {
        "code": "fn main() { println!(\"Hello\"); }",
        "language": "rust"
    }
    response = client.post("/api/code/analyze", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "rust" in data["error"]["message"].lower()


def test_code_analyze_syntax_error(client):
    payload = {
        "code": "def bad_syntax(:\n    pass",
        "language": "python"
    }
    response = client.post("/api/code/analyze", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "syntax" in data["error"]["message"].lower()


# --- 5. Pedagogical Code Explanation Endpoints ---

def test_code_explain_assignment(client):
    code = """x = 42\ny = x * 2\n"""
    payload = {
        "code": code,
        "language": "python",
        "line_number": 1
    }
    response = client.post("/api/code/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["construct_type"] == "assignment"
    assert "variable" in data["explanation"].lower()


def test_code_explain_condition(client):
    code = """val = 10\nif val > 5:\n    print(val)\n"""
    payload = {
        "code": code,
        "language": "python",
        "line_number": 2
    }
    response = client.post("/api/code/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["construct_type"] == "condition"


def test_code_explain_out_of_bounds_line(client):
    code = "x = 1\n"
    payload = {
        "code": code,
        "language": "python",
        "line_number": 999
    }
    response = client.post("/api/code/explain", json=payload)
    assert response.status_code == 400


# --- 6. Sandboxed Execution Tracing Endpoints ---

def test_code_trace_loop_and_variables(client):
    code = """total = 0
for i in range(3):
    total += i
"""
    payload = {
        "code": code,
        "language": "python",
        "max_steps": 50
    }
    response = client.post("/api/code/trace", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["terminated_normally"] is True
    assert data["total_steps"] >= 6
    assert data["diagram"] is not None

    # Check variable updates
    events = data["trace"]["events"]
    assert any(e["variables"].get("total") == 3 for e in events)


def test_code_trace_max_steps_exceeded(client):
    infinite_loop = """i = 0
while True:
    i += 1
"""
    payload = {
        "code": infinite_loop,
        "language": "python",
        "max_steps": 25
    }
    response = client.post("/api/code/trace", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] == "max_steps_exceeded"
    assert data["total_steps"] == 25


def test_code_trace_security_violation_blocked(client):
    malicious_code = """import os
os.system('whoami')
"""
    payload = {
        "code": malicious_code,
        "language": "python"
    }
    response = client.post("/api/code/trace", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] == "security_violation"
    assert "os" in data["error_message"].lower()


# --- 7. CORS and Request Integrity ---

def test_cors_headers(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
