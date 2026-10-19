"""
Phase 8: Comprehensive End-to-End Integration and Robustness Test Suite.
Validates all 7 diagram families, semantic distinction, loop handling,
all 8 Python code analysis and execution trace archetypes, AST security isolation,
resource limits, and diagram editing roundtrip validation.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

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


# =====================================================================
# 1. TEXT TO DIAGRAM: ALL DIAGRAM FAMILIES & COMPLEX WORKFLOWS
# =====================================================================

def test_e2e_sequential_flowchart(client):
    """Test 1: Simple sequential flowchart process."""
    prompt = "User opens mobile app, enters email and password, clicks login, and views the personal dashboard."
    resp = client.post("/api/diagram/generate", json={"text": prompt})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["diagram_type"] == "flowchart"
    diagram = data["diagram"]
    assert len(diagram["nodes"]) >= 3
    assert len(diagram["edges"]) >= 2
    # Verify nodes have positions and labels
    for node in diagram["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "position" in node
        assert isinstance(node["position"]["x"], (int, float))
        assert isinstance(node["position"]["y"], (int, float))


def test_e2e_conditional_branching_flowchart(client):
    """Test 2: Conditional process with alternative branches (if/otherwise)."""
    prompt = "User submits loan application. If credit score is above 700, approve loan immediately and disburse funds; otherwise request guarantor and send for manual review."
    resp = client.post("/api/diagram/generate", json={"text": prompt})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagram_type"] == "flowchart"
    diagram = data["diagram"]
    # Check for decision node or branches
    node_types = [n.get("type") for n in diagram["nodes"]]
    assert any(t in ["decision", "condition", "process"] for t in node_types)
    assert len(diagram["nodes"]) >= 4
    assert len(diagram["edges"]) >= 3


def test_e2e_process_with_loop(client):
    """Test 3: Process containing an iterative loop."""
    prompt = "Sensor controller reads temperature. If temperature exceeds threshold, sound alarm; otherwise sleep for 10 seconds and loop back to read temperature."
    resp = client.post("/api/diagram/generate", json={"text": prompt})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    diagram = data["diagram"]
    assert len(diagram["nodes"]) >= 3
    # Check edge labels or branch targets
    assert any("loop" in str(e.get("label", "")).lower() or e.get("edge_type") in ["branch_no", "loop", "flow"] for e in diagram["edges"])


def test_e2e_software_architecture(client):
    """Test 4: Tiered multi-service software architecture."""
    prompt = "React Web App communicates with API Gateway, which routes requests to Order Microservice and User Microservice. Order Microservice reads from Redis Cache and writes to Postgres Database."
    resp = client.post("/api/diagram/generate", json={"text": prompt, "diagram_type": "architecture"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagram_type"] == "architecture"
    diagram = data["diagram"]
    node_labels = [n["label"].lower() for n in diagram["nodes"]]
    assert any("gateway" in lbl for lbl in node_labels)
    assert any("database" in lbl or "postgres" in lbl for lbl in node_labels)
    assert any("cache" in lbl or "redis" in lbl for lbl in node_labels)
    # Verify semantic node roles
    node_types = [n.get("type", "").lower() for n in diagram["nodes"]]
    assert any(t in ["service", "database", "cache", "gateway", "client"] for t in node_types)


def test_e2e_concept_map(client):
    """Test 5: Semantic concept map with propositions."""
    prompt = "Artificial Intelligence encompasses Machine Learning and Computer Vision. Machine Learning comprises Supervised Learning and Unsupervised Learning. Deep Learning utilizes Neural Networks."
    resp = client.post("/api/diagram/generate", json={"text": prompt, "diagram_type": "concept_map"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagram_type"] == "concept_map"
    diagram = data["diagram"]
    assert len(diagram["nodes"]) >= 4
    assert len(diagram["edges"]) >= 3


def test_e2e_er_diagram(client):
    """Test 6: Entity-Relationship database schema with cardinalities."""
    prompt = "Customer places Order with 1:N cardinality. Order contains OrderItem with 1:N cardinality. Product belongs to OrderItem with 1:N cardinality."
    resp = client.post("/api/diagram/generate", json={"text": prompt, "diagram_type": "er_diagram"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagram_type"] == "er_diagram"
    diagram = data["diagram"]
    assert len(diagram["nodes"]) >= 3
    # Check cardinalities
    cardinalities = [e.get("cardinality") for e in diagram["edges"]]
    assert any(c in ["1:N", "1:1", "M:N"] for c in cardinalities)


def test_e2e_sequence_diagram(client):
    """Test 7: Chronological sequence diagram message flow."""
    prompt = "Client sends authentication request to Auth Server. Auth Server queries User Database. User Database returns user credentials. Auth Server issues JWT token to Client."
    resp = client.post("/api/diagram/generate", json={"text": prompt, "diagram_type": "sequence_diagram"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagram_type"] == "sequence_diagram"
    diagram = data["diagram"]
    assert len(diagram["nodes"]) >= 2
    assert len(diagram["edges"]) >= 2


def test_e2e_network_topology(client):
    """Test 8: Network topology with device infrastructure."""
    prompt = "Edge Router connects to Corporate Firewall. Firewall directs traffic to Core Switch. Core Switch connects to Database Server, Web Server, and two Workstations."
    resp = client.post("/api/diagram/generate", json={"text": prompt, "diagram_type": "network_topology"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagram_type"] == "network_topology"
    diagram = data["diagram"]
    assert len(diagram["nodes"]) >= 4
    assert len(diagram["edges"]) >= 3


def test_e2e_dependency_graph(client):
    """Test 9: Strict directed acyclic graph (DAG) build pipeline."""
    prompt = "Task A compiles frontend assets. Task B runs unit tests. Task C packages Docker container which depends on Task A and Task B. Task D deploys to cluster depending on Task C."
    resp = client.post("/api/diagram/generate", json={"text": prompt, "diagram_type": "dependency_graph"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagram_type"] == "dependency_graph"
    diagram = data["diagram"]
    assert len(diagram["nodes"]) >= 3
    assert len(diagram["edges"]) >= 2


# =====================================================================
# 2. EDGE CASES & INPUT VALIDATION
# =====================================================================

def test_edge_case_empty_prompt(client):
    """Empty string prompt is rejected with 422."""
    resp = client.post("/api/diagram/generate", json={"text": ""})
    assert resp.status_code == 422


def test_edge_case_whitespace_prompt(client):
    """Whitespace-only prompt is rejected with 422."""
    resp = client.post("/api/diagram/generate", json={"text": "   "})
    assert resp.status_code == 422


def test_edge_case_too_short_prompt(client):
    """Prompt with < 5 characters is rejected with 422."""
    resp = client.post("/api/diagram/generate", json={"text": "hey"})
    assert resp.status_code == 422


def test_edge_case_oversized_prompt(client):
    """Prompt exceeding 10,000 characters is rejected with 422."""
    huge_text = "Step A leads to Step B. " * 500
    resp = client.post("/api/diagram/generate", json={"text": huge_text})
    assert resp.status_code == 422


def test_edge_case_invalid_diagram_type(client):
    """Unsupported diagram type override returns 400 Bad Request."""
    resp = client.post("/api/diagram/generate", json={"text": "Step 1 leads to Step 2.", "diagram_type": "nonexistent_type"})
    assert resp.status_code == 400
    err_body = resp.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "DiagramType" in err_msg or "Unsupported diagram type" in err_msg


def test_edge_case_ambiguous_prompt_fallback(client):
    """Ambiguous or underspecified text falls back gracefully to a valid diagram."""
    resp = client.post("/api/diagram/generate", json={"text": "Things operate together and communicate constantly."})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "diagram" in data
    assert len(data["diagram"]["nodes"]) >= 1


# =====================================================================
# 3. EXPLAIN CODE: ALL 8 PYTHON ARCHETYPES & ERROR CASES
# =====================================================================

def test_code_archetype_1_variables_arithmetic(client):
    """Archetype 1: Variables, expressions, and arithmetic."""
    code = """x = 10
y = 25
total = x + y * 2
"""
    # 1. AST Analysis
    ana_resp = client.post("/api/code/analyze", json={"code": code, "language": "python"})
    assert ana_resp.status_code == 200
    assert len(ana_resp.json()["diagram"]["nodes"]) >= 3

    # 2. Trace Execution
    trace_resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert trace_resp.status_code == 200
    t_data = trace_resp.json()
    assert t_data["terminated_normally"] is True
    events = t_data["trace"]["events"]
    final_event = events[-1]
    assert final_event["variables"].get("total") == 60


def test_code_archetype_2_functions_returns(client):
    """Archetype 2: Function definition, call, and return value."""
    code = """def square(n):
    return n * n

ans = square(6)
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is True
    events = data["trace"]["events"]
    # Check return event
    returns = [e for e in events if e["event_type"] == "return" and e["function_name"] == "square"]
    assert len(returns) >= 1
    assert returns[0]["return_value"] == 36


def test_code_archetype_3_conditions_branches(client):
    """Archetype 3: If-else branching logic."""
    code = """score = 85
if score >= 90:
    grade = 'A'
elif score >= 80:
    grade = 'B'
else:
    grade = 'C'
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    events = data["trace"]["events"]
    last_vars = events[-1]["variables"]
    assert last_vars.get("grade") == "B"


def test_code_archetype_4_loops(client):
    """Archetype 4: For and while loops with accumulator."""
    code = """accum = 0
for i in range(1, 5):
    accum += i
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    events = data["trace"]["events"]
    assert data["terminated_normally"] is True
    last_vars = events[-1]["variables"]
    assert last_vars.get("accum") == 10


def test_code_archetype_5_recursion(client):
    """Archetype 5: Recursive function execution and stack depth."""
    code = """def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

val = fib(4)
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is True
    events = data["trace"]["events"]
    last_vars = events[-1]["variables"]
    assert last_vars.get("val") == 3
    # Check max call stack depth exceeded 2
    max_stack_depth = max(len(e["call_stack"]) for e in events)
    assert max_stack_depth >= 3


def test_code_archetype_6_multi_function_calls(client):
    """Archetype 6: Multiple functions invoking each other."""
    code = """def add_tax(price):
    return price * 1.1

def calculate_total(subtotal):
    return add_tax(subtotal)

final_price = calculate_total(100.0)
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    events = data["trace"]["events"]
    last_vars = events[-1]["variables"]
    assert round(last_vars.get("final_price"), 1) == 110.0


def test_code_archetype_7_data_structures(client):
    """Archetype 7: Lists, dictionaries, and built-in aggregations."""
    code = """users = {"alice": 95, "bob": 80, "charlie": 90}
top_scorer = max(users, key=users.get)
scores_list = list(users.values())
average = sum(scores_list) / len(scores_list)
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is True
    events = data["trace"]["events"]
    last_vars = events[-1]["variables"]
    assert last_vars.get("top_scorer") == "alice"
    assert round(last_vars.get("average"), 2) == 88.33


def test_code_archetype_8_syntax_error_reported_honestly(client):
    """Archetype 8: Invalid syntax produces structured error response without crashing."""
    code = """def invalid_function(x:
    return x + 1
"""
    resp = client.post("/api/code/analyze", json={"code": code, "language": "python"})
    assert resp.status_code == 400
    err_body = resp.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "syntax error" in err_msg.lower()


def test_code_pedagogical_explanation(client):
    """Pedagogical explanation returns summary explanation, construct type, and pedagogical tip."""
    code = """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    resp = client.post("/api/code/explain", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "explanation" in data
    assert isinstance(data["explanation"], str)
    assert len(data["explanation"]) > 10
    assert data["construct_type"] in ["function_def", "statement", "condition", "loop", "return", "assignment"]
    assert "pedagogical_tip" in data


# =====================================================================
# 4. SECURITY BOUNDARIES & RESOURCE LIMITS
# =====================================================================

def test_security_blocked_import_os(client):
    """Attempted 'import os' is blocked by AST scanner."""
    code = """import os
os.system('echo test')
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] == "security_violation"
    assert "os" in data["error_message"].lower()


def test_security_blocked_import_subprocess(client):
    """Attempted 'import subprocess' is blocked by AST scanner."""
    code = """import subprocess
subprocess.run(['echo', 'hacked'])
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] == "security_violation"
    assert "subprocess" in data["error_message"].lower()


def test_security_blocked_open_call(client):
    """Attempted 'open()' call is blocked by AST scanner."""
    code = """with open('test.txt', 'w') as f:
    f.write('hello')
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] == "security_violation"
    assert "open" in data["error_message"].lower()


def test_security_blocked_eval_exec(client):
    """Attempted 'eval()' or 'exec()' calls are blocked by AST scanner."""
    code = """eval("__import__('os').system('ls')")"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] == "security_violation"


def test_security_blocked_dunder_subclasses(client):
    """Attempted sandbox escape via __subclasses__ is blocked."""
    code = """classes = ().__class__.__subclasses__()"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] == "security_violation"


def test_resource_limit_max_steps(client):
    """Exceeding max_steps stops execution safely with reason 'max_steps_exceeded'."""
    code = """count = 0
for i in range(1000):
    count += 1
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python", "max_steps": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] == "max_steps_exceeded"
    assert data["total_steps"] == 30


def test_resource_limit_timeout(client):
    """Infinite loop is halted by subprocess timeout without freezing the server."""
    code = """while True:
    pass
"""
    resp = client.post("/api/code/trace", json={"code": code, "language": "python", "timeout_seconds": 1.0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["terminated_normally"] is False
    assert data["termination_reason"] in ["timeout", "max_steps_exceeded"]


def test_unsupported_language_rejected(client):
    """Requesting an unsupported language returns 400 Bad Request."""
    code = "package main; func main() {}"
    resp = client.post("/api/code/analyze", json={"code": code, "language": "golang"})
    assert resp.status_code == 400
    err_body = resp.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "supported" in err_msg.lower() or "golang" in err_msg.lower()


# =====================================================================
# 5. DIAGRAM EDITING & VALIDATION ROUNDTRIP
# =====================================================================

def test_diagram_validation_roundtrip(client):
    """Validates that a diagram generated, edited with custom labels, validates successfully."""
    # 1. Generate initial graph
    gen_resp = client.post("/api/diagram/generate", json={"text": "Service A queries Service B."})
    assert gen_resp.status_code == 200
    diagram = gen_resp.json()["diagram"]

    # 2. Simulate user editing labels and adding a node
    new_node = {
        "id": "user_node_3",
        "label": "User Added Service",
        "type": "service",
        "position": {"x": 400.0, "y": 300.0, "width": 160.0, "height": 60.0, "rank": 2},
        "attributes": {"custom": "true"}
    }
    diagram["nodes"].append(new_node)
    new_edge = {
        "id": "user_edge_2",
        "source": diagram["nodes"][0]["id"],
        "target": "user_node_3",
        "label": "syncs with",
        "edge_type": "flow",
        "directed": True
    }
    diagram["edges"].append(new_edge)

    # 3. Validate edited diagram via /api/diagram/validate
    val_resp = client.post("/api/diagram/validate", json={"diagram": diagram})
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["is_valid"] is True
    assert val_data["diagram_type"] in ["flowchart", "architecture", "sequence_diagram"]
    assert len(val_data["errors"]) == 0
