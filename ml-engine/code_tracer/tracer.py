"""
Safe Subprocess-Isolated Python Execution Tracer.
Executes supported Python snippets in a dedicated, isolated child process
with strict timeouts, step limits, AST security pre-scanning, and output capping.
Produces structured chronological ExecutionTrace objects and maps them to CFG graphs.
"""

import sys
import os
import json
import subprocess
import time
from typing import List, Dict, Any, Optional

from ir.models import DiagramGraph, SourceLocation, ExecutionStateSnapshot
from .models import ExecutionEvent, ExecutionTrace
from .security import AstSecurityScanner, SecurityViolationError

# Worker script template executed in isolated child process
WORKER_TEMPLATE = r"""
import sys
import json
import io
import traceback

def serialize_val(val, depth=0):
    if depth > 2:
        return "<nested>"
    if val is None or isinstance(val, (int, float, bool)):
        return val
    elif isinstance(val, str):
        return val if len(val) <= 100 else val[:97] + "..."
    elif isinstance(val, (list, tuple)):
        items = [serialize_val(x, depth + 1) for x in val[:15]]
        if len(val) > 15:
            items.append("...")
        return items if isinstance(val, list) else tuple(items)
    elif isinstance(val, dict):
        d = {}
        for k, v in list(val.items())[:15]:
            d[str(k)] = serialize_val(v, depth + 1)
        if len(val) > 15:
            d["..."] = "..."
        return d
    elif isinstance(val, set):
        return [serialize_val(x, depth + 1) for x in list(val)[:15]]
    else:
        return f"<{type(val).__name__}>"

class MaxStepsExceededException(Exception):
    pass

def make_explanation(event_type, fn_name, line_no, variables, ret_val, exc_info):
    if event_type == "call":
        args_str = ", ".join(f"{k}={v}" for k, v in variables.items() if not k.startswith("__"))
        return f"Entered function '{fn_name}' with arguments ({args_str})"
    elif event_type == "return":
        return f"Function '{fn_name}' returned: {ret_val}"
    elif event_type == "exception":
        return f"Exception raised at line {line_no}: {exc_info}"
    else:
        vars_str = ", ".join(f"{k}={v}" for k, v in variables.items() if not k.startswith("__"))
        if vars_str:
            return f"Executing line {line_no} (active state: {vars_str})"
        return f"Executing line {line_no}"

def run_tracer(user_code, max_steps):
    events = []
    step_id = 0
    terminated_normally = True
    termination_reason = "completed"
    error_msg = None

    # Redirect stdout
    captured_stdout = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured_stdout

    def trace_func(frame, event, arg):
        nonlocal step_id, terminated_normally, termination_reason
        if frame.f_code.co_filename != "<user_code>":
            return trace_func

        if step_id >= max_steps:
            terminated_normally = False
            termination_reason = "max_steps_exceeded"
            sys.settrace(None)
            raise MaxStepsExceededException()

        raw_line = frame.f_lineno
        line_no = max(1, raw_line if raw_line is not None else 1)
        fn_name = frame.f_code.co_name if frame.f_code.co_name != "<module>" else "main"

        # Build call stack
        call_stack = []
        curr = frame
        while curr and curr.f_code.co_filename == "<user_code>":
            name = curr.f_code.co_name if curr.f_code.co_name != "<module>" else "main"
            call_stack.append(name)
            curr = curr.f_back
        call_stack.reverse()

        # Extract locals safely
        raw_locals = frame.f_locals
        safe_vars = {}
        for k, v in raw_locals.items():
            if not k.startswith("__"):
                safe_vars[k] = serialize_val(v)

        ret_val = None
        exc_info = None

        if event == "return":
            ret_val = serialize_val(arg)
        elif event == "exception":
            exc_info = f"{arg[0].__name__}: {str(arg[1])}"

        explanation = make_explanation(event, fn_name, line_no, safe_vars, ret_val, exc_info)

        events.append({
            "step_id": step_id,
            "line_number": line_no,
            "event_type": event,
            "function_name": fn_name,
            "call_stack": call_stack,
            "variables": safe_vars,
            "return_value": ret_val,
            "exception_info": exc_info,
            "explanation": explanation,
            "is_runtime_observed": True,
        })
        step_id += 1
        return trace_func

    # Compile and execute
    try:
        compiled = compile(user_code, "<user_code>", "exec")
        safe_globals = {
            "__name__": "__main__",
            "__builtins__": {
                "print": print,
                "range": range,
                "len": len,
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "enumerate": enumerate,
                "zip": zip,
                "sorted": sorted,
                "reversed": reversed,
                "map": map,
                "filter": filter,
                "any": any,
                "all": all,
                "True": True,
                "False": False,
                "None": None,
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "IndexError": IndexError,
                "KeyError": KeyError,
                "ZeroDivisionError": ZeroDivisionError,
            }
        }
        sys.settrace(trace_func)
        exec(compiled, safe_globals)
    except MaxStepsExceededException:
        terminated_normally = False
        termination_reason = "max_steps_exceeded"
    except Exception as e:
        terminated_normally = False
        if termination_reason == "completed":
            termination_reason = "exception"
        error_msg = f"{type(e).__name__}: {str(e)}"
    finally:
        sys.settrace(None)
        sys.stdout = old_stdout

    out_text = captured_stdout.getvalue()
    if len(out_text) > 10000:
        out_text = out_text[:9997] + "..."

    output_payload = {
        "events": events,
        "total_steps": len(events),
        "terminated_normally": terminated_normally,
        "termination_reason": termination_reason,
        "stdout": out_text,
        "error_message": error_msg,
    }
    # Output single JSON line to stdout
    print("__TRACER_OUTPUT_START__")
    print(json.dumps(output_payload))
    print("__TRACER_OUTPUT_END__")

if __name__ == "__main__":
    payload = json.loads(sys.stdin.read())
    run_tracer(payload["code"], payload["max_steps"])
"""


class SafeExecutionTracer:
    """
    Orchestrates execution of Python code in an isolated subprocess.
    Enforces security pre-scanning, timeouts, memory/event limits, and safe cleanup.
    """

    DEFAULT_TIMEOUT: float = 2.0  # seconds
    MAX_TIMEOUT: float = 5.0
    DEFAULT_MAX_STEPS: int = 500
    MAX_ALLOWED_STEPS: int = 2000

    @classmethod
    def trace(
        cls,
        source_code: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_steps: int = DEFAULT_MAX_STEPS
    ) -> ExecutionTrace:
        """
        Executes source_code in an isolated child process with tracing enabled.
        Returns a strongly-typed ExecutionTrace containing all step events.
        """
        # Step 1: AST Security Pre-Scan
        scanner = AstSecurityScanner()
        try:
            scanner.verify_or_raise(source_code)
        except SecurityViolationError as sve:
            return ExecutionTrace(
                events=[],
                total_steps=0,
                terminated_normally=False,
                termination_reason="security_violation",
                stdout="",
                error_message=str(sve),
                source_code=source_code,
            )
        except SyntaxError as syn:
            return ExecutionTrace(
                events=[],
                total_steps=0,
                terminated_normally=False,
                termination_reason="exception",
                stdout="",
                error_message=f"SyntaxError at line {syn.lineno}: {syn.msg}",
                source_code=source_code,
            )

        clamped_timeout = max(0.5, min(timeout, cls.MAX_TIMEOUT))
        clamped_steps = max(10, min(max_steps, cls.MAX_ALLOWED_STEPS))

        # Prepare child process execution
        payload = json.dumps({"code": source_code, "max_steps": clamped_steps})
        sanitized_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "COMSPEC": os.environ.get("COMSPEC", "C:\\Windows\\System32\\cmd.exe"),
            "PATH": os.environ.get("PATH", ""),
        }

        start_time = time.perf_counter()

        try:
            proc = subprocess.Popen(
                [sys.executable, "-c", WORKER_TEMPLATE],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=sanitized_env,
            )

            try:
                stdout_text, stderr_text = proc.communicate(input=payload, timeout=clamped_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return ExecutionTrace(
                    events=[],
                    total_steps=0,
                    terminated_normally=False,
                    termination_reason="timeout",
                    stdout="",
                    error_message=f"Execution timed out after {clamped_timeout}s",
                    execution_time_ms=round(elapsed_ms, 2),
                    source_code=source_code,
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Parse JSON output between delimiters
            if "__TRACER_OUTPUT_START__" in stdout_text and "__TRACER_OUTPUT_END__" in stdout_text:
                parts = stdout_text.split("__TRACER_OUTPUT_START__")[1].split("__TRACER_OUTPUT_END__")[0]
                data = json.loads(parts.strip())

                events = [
                    ExecutionEvent(
                        step_id=e["step_id"],
                        line_number=e["line_number"],
                        event_type=e["event_type"],
                        function_name=e.get("function_name"),
                        call_stack=e.get("call_stack", []),
                        variables=e.get("variables", {}),
                        return_value=e.get("return_value"),
                        exception_info=e.get("exception_info"),
                        explanation=e.get("explanation"),
                        is_runtime_observed=True,
                    )
                    for e in data["events"]
                ]

                return ExecutionTrace(
                    events=events,
                    total_steps=data["total_steps"],
                    terminated_normally=data["terminated_normally"],
                    termination_reason=data["termination_reason"],
                    stdout=data.get("stdout", ""),
                    error_message=data.get("error_message"),
                    execution_time_ms=round(elapsed_ms, 2),
                    source_code=source_code,
                )
            else:
                err = stderr_text.strip() or stdout_text.strip() or "Child worker failed to produce output."
                return ExecutionTrace(
                    events=[],
                    total_steps=0,
                    terminated_normally=False,
                    termination_reason="exception",
                    stdout="",
                    error_message=err[:500],
                    execution_time_ms=round(elapsed_ms, 2),
                    source_code=source_code,
                )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionTrace(
                events=[],
                total_steps=0,
                terminated_normally=False,
                termination_reason="exception",
                stdout="",
                error_message=f"Subprocess launcher error: {str(e)}",
                execution_time_ms=round(elapsed_ms, 2),
                source_code=source_code,
            )

    @classmethod
    def map_trace_to_graph(
        cls,
        trace: ExecutionTrace,
        cfg_graph: DiagramGraph
    ) -> DiagramGraph:
        """
        Maps observed runtime execution events to static CFG nodes.
        Attaches active ExecutionStateSnapshot to nodes matching executed lines.
        """
        cloned_nodes = []
        # Index events by line number to find latest state
        events_by_line: Dict[int, ExecutionEvent] = {}
        for ev in trace.events:
            events_by_line[ev.line_number] = ev

        for node in cfg_graph.nodes:
            node_copy = node.model_copy(deep=True)
            if node.source_location and node.source_location.line_start in events_by_line:
                ev = events_by_line[node.source_location.line_start]
                node_copy.execution_state = ev.to_snapshot()
            cloned_nodes.append(node_copy)

        return DiagramGraph(
            id=cfg_graph.id,
            diagram_type=cfg_graph.diagram_type,
            version=cfg_graph.version,
            nodes=cloned_nodes,
            edges=[e.model_copy(deep=True) for e in cfg_graph.edges],
            metadata=cfg_graph.metadata.model_copy(deep=True),
            warnings=list(cfg_graph.warnings),
            layout_config=cfg_graph.layout_config.copy() if cfg_graph.layout_config else None,
        )
