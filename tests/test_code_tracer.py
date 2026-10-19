"""
Comprehensive tests for Static AST Code Analysis, Security Sandboxing,
and Subprocess-Isolated Python Execution Tracer.
"""

import pytest
from ir.models import DiagramType
from code_tracer.security import AstSecurityScanner, SecurityViolationError
from code_tracer.ast_analyzer import AstCodeAnalyzer
from code_tracer.tracer import SafeExecutionTracer


# --- 1. Static AST Analysis & CFG Tests ---

def test_ast_cfg_generation_simple_branch():
    code = """x = 5
if x > 0:
    res = "positive"
else:
    res = "non-positive"
"""
    cfg = AstCodeAnalyzer.build_cfg(code, title="Branch Test")
    assert cfg.diagram_type == DiagramType.CODE_FLOW
    assert len(cfg.nodes) >= 5  # Start, x=5, if x>0, res='pos', res='non-pos', Merge, End

    # Verify decision node
    decision_nodes = [n for n in cfg.nodes if n.type == "decision"]
    assert len(decision_nodes) == 1
    assert "if x > 0" in decision_nodes[0].label
    assert decision_nodes[0].source_location.line_start == 2

    # Verify outgoing branch edges
    out_edges = cfg.get_outgoing_edges(decision_nodes[0].id)
    # The decision node connects through the branches
    assert any(e.label == "True" for e in cfg.edges)
    assert any(e.label == "False" for e in cfg.edges)


def test_ast_cfg_generation_while_loop():
    code = """i = 0
while i < 3:
    i += 1
"""
    cfg = AstCodeAnalyzer.build_cfg(code)
    loop_nodes = [n for n in cfg.nodes if n.type == "loop"]
    assert len(loop_nodes) == 1
    assert "while i < 3" in loop_nodes[0].label
    assert loop_nodes[0].source_location.line_start == 2

    # Loop back-edge exists
    back_edges = [e for e in cfg.edges if e.edge_type == "loop_back"]
    assert len(back_edges) == 1


def test_ast_call_graph_recursion():
    code = """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def helper():
    return factorial(5)
"""
    cg = AstCodeAnalyzer.build_call_graph(code)
    assert cg.diagram_type == DiagramType.CODE_CALL_GRAPH
    assert len(cg.nodes) == 2  # factorial, helper

    # Factorial has recursive call
    rec_edges = [e for e in cg.edges if e.source == "fn_factorial" and e.target == "fn_factorial"]
    assert len(rec_edges) == 1
    assert rec_edges[0].label == "recursive call"

    # Helper calls factorial
    helper_edges = [e for e in cg.edges if e.source == "fn_helper" and e.target == "fn_factorial"]
    assert len(helper_edges) == 1


# --- 2. AST Security Scanner Tests ---

def test_security_scanner_rejects_banned_imports():
    scanner = AstSecurityScanner()

    # Prohibited modules
    for mod in ["os", "sys", "subprocess", "socket", "shutil", "ctypes"]:
        code = f"import {mod}\nprint('hello')"
        with pytest.raises(SecurityViolationError) as exc_info:
            scanner.verify_or_raise(code)
        assert mod in str(exc_info.value)


def test_security_scanner_rejects_banned_from_imports():
    scanner = AstSecurityScanner()
    code = "from subprocess import Popen\nPopen(['ls'])"
    with pytest.raises(SecurityViolationError) as exc_info:
        scanner.verify_or_raise(code)
    assert "subprocess" in str(exc_info.value)


def test_security_scanner_rejects_dangerous_calls():
    scanner = AstSecurityScanner()

    for dangerous in ["eval('1+1')", "exec('x=1')", "open('file.txt', 'r')"]:
        with pytest.raises(SecurityViolationError) as exc_info:
            scanner.verify_or_raise(dangerous)
        assert "restricted" in str(exc_info.value).lower()


def test_security_scanner_rejects_dunder_attribute_traversal():
    scanner = AstSecurityScanner()
    code = "subclasses = ().__class__.__bases__[0].__subclasses__()"
    with pytest.raises(SecurityViolationError) as exc_info:
        scanner.verify_or_raise(code)
    assert "__subclasses__" in str(exc_info.value)


def test_security_scanner_allows_safe_code():
    scanner = AstSecurityScanner()
    safe_code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

res = bubble_sort([5, 2, 9, 1])
"""
    # Should not raise any exception
    scanner.verify_or_raise(safe_code)


# --- 3. Isolated Subprocess Execution Tracer Tests ---

def test_tracer_simple_assignments_and_arithmetic():
    code = """x = 10
y = 20
z = x + y
"""
    trace = SafeExecutionTracer.trace(code)
    assert trace.terminated_normally is True
    assert trace.termination_reason == "completed"
    assert trace.total_steps >= 3

    # Check variable progression
    final_event = trace.events[-1]
    assert final_event.variables.get("z") == 30
    assert final_event.variables.get("x") == 10
    assert final_event.variables.get("y") == 20


def test_tracer_conditional_branching():
    code = """val = 42
if val > 100:
    branch = "high"
else:
    branch = "normal"
"""
    trace = SafeExecutionTracer.trace(code)
    assert trace.terminated_normally is True

    # Check that else-branch executed, not if-branch
    executed_lines = [e.line_number for e in trace.events]
    assert 4 not in executed_lines or any(e.variables.get("branch") == "normal" for e in trace.events)
    final_event = trace.events[-1]
    assert final_event.variables.get("branch") == "normal"


def test_tracer_loops():
    code = """total = 0
for i in range(4):
    total += i
"""
    trace = SafeExecutionTracer.trace(code)
    assert trace.terminated_normally is True
    assert trace.total_steps >= 8

    final_event = trace.events[-1]
    assert final_event.variables.get("total") == 6


def test_tracer_function_calls_and_call_stack():
    code = """def add(a, b):
    return a + b

res = add(15, 25)
"""
    trace = SafeExecutionTracer.trace(code)
    assert trace.terminated_normally is True

    # Check function call event for 'add'
    call_events = [e for e in trace.events if e.event_type == "call" and e.function_name == "add"]
    assert len(call_events) >= 1
    assert call_events[0].function_name == "add"
    assert "add" in call_events[0].call_stack

    # Check return event
    return_events = [e for e in trace.events if e.event_type == "return" and e.function_name == "add"]
    assert len(return_events) == 1
    assert return_events[0].return_value == 40


def test_tracer_recursion():
    code = """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

ans = factorial(3)
"""
    trace = SafeExecutionTracer.trace(code)
    assert trace.terminated_normally is True

    # Call stack should reach depth >= 3
    max_stack_depth = max(len(e.call_stack) for e in trace.events)
    assert max_stack_depth >= 3

    # Check final return value
    final_returns = [e for e in trace.events if e.event_type == "return" and e.function_name == "factorial"]
    assert any(e.return_value == 6 for e in final_returns)


def test_tracer_max_steps_limit():
    infinite_loop = """count = 0
while True:
    count += 1
"""
    trace = SafeExecutionTracer.trace(infinite_loop, max_steps=50)
    assert trace.terminated_normally is False
    assert trace.termination_reason == "max_steps_exceeded"
    assert trace.total_steps == 50


def test_tracer_security_rejection_at_entry():
    malicious = """import os
os.listdir('.')
"""
    trace = SafeExecutionTracer.trace(malicious)
    assert trace.terminated_normally is False
    assert trace.termination_reason == "security_violation"
    assert "os" in trace.error_message


def test_map_trace_to_graph():
    code = """x = 1
y = 2
"""
    cfg = AstCodeAnalyzer.build_cfg(code)
    trace = SafeExecutionTracer.trace(code)

    annotated = SafeExecutionTracer.map_trace_to_graph(trace, cfg)
    assert len(annotated.nodes) == len(cfg.nodes)

    # Executed nodes have execution_state populated
    active_nodes = [n for n in annotated.nodes if n.execution_state is not None]
    assert len(active_nodes) >= 2
    for n in active_nodes:
        assert n.execution_state.is_runtime_observed is True
