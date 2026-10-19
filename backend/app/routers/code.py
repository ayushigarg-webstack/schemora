"""
Code analysis, pedagogical explanations, and sandboxed execution tracing endpoints.
"""

import ast
import sys
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

from code_tracer.ast_analyzer import AstCodeAnalyzer
from code_tracer.tracer import SafeExecutionTracer
from layout.engine import DiagramLayoutEngine
from layout.models import LayoutOptions

from ..schemas.code import (
    LanguageInfo,
    CodeAnalyzeRequest,
    CodeAnalyzeResponse,
    CodeExplainRequest,
    CodeExplainResponse,
    CodeTraceRequest,
    CodeTraceResponse,
)

router = APIRouter(prefix="/api/code", tags=["Live Code Explainer"])

SUPPORTED_LANGUAGES: List[LanguageInfo] = [
    LanguageInfo(
        language="python",
        name="Python 3",
        status="supported",
        capabilities=[
            "static_analysis",
            "cfg_generation",
            "call_graph_generation",
            "execution_tracing",
            "pedagogical_explanation",
        ],
        is_sandboxed=True,
        version=sys.version.split()[0],
    ),
    LanguageInfo(
        language="javascript",
        name="JavaScript (ES6+)",
        status="planned",
        capabilities=[],
        is_sandboxed=False,
        version=None,
    ),
]


@router.get("/languages", response_model=List[LanguageInfo])
def list_supported_languages() -> List[LanguageInfo]:
    """
    Returns supported programming languages and their verified analysis capabilities.
    Only features actually implemented and tested are marked as supported.
    """
    return SUPPORTED_LANGUAGES


@router.post("/analyze", response_model=CodeAnalyzeResponse)
def analyze_code_endpoint(request: CodeAnalyzeRequest) -> CodeAnalyzeResponse:
    """
    Statically analyzes source code into a Control Flow Graph (CFG) or Call Graph.
    Attaches bidirectional SourceLocation line mappings and geometric canvas coordinates.
    """
    lang = request.language.strip().lower()
    if lang != "python":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{request.language}' is not yet supported for static analysis. Currently supported: 'python'",
        )

    # Parse and build graph
    try:
        if request.view_mode == "call_graph":
            raw_graph = AstCodeAnalyzer.build_call_graph(request.code)
        else:
            raw_graph = AstCodeAnalyzer.build_cfg(request.code)
    except SyntaxError as syn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Python syntax error on line {syn.lineno}: {syn.msg}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AST analysis error: {str(e)}",
        )

    # Layout graph
    opts = LayoutOptions(direction=request.layout_direction or "TB")
    laid_out_graph = DiagramLayoutEngine.layout(raw_graph, options=opts)

    warnings = [w.message for w in laid_out_graph.warnings]

    return CodeAnalyzeResponse(
        success=True,
        language="python",
        view_mode=request.view_mode,
        diagram=laid_out_graph,
        total_nodes=len(laid_out_graph.nodes),
        total_edges=len(laid_out_graph.edges),
        warnings=warnings,
    )


@router.post("/explain", response_model=CodeExplainResponse)
def explain_code_endpoint(request: CodeExplainRequest) -> CodeExplainResponse:
    """
    Produces a pedagogical beginner-friendly plain-English explanation
    for a selected line number or code region.
    """
    lang = request.language.strip().lower()
    if lang != "python":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{request.language}' is not supported for explanation.",
        )

    try:
        tree = ast.parse(request.code)
    except SyntaxError as syn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SyntaxError on line {syn.lineno}: {syn.msg}",
        )

    lines = request.code.splitlines()
    target_line = request.line_number or 1

    if target_line > len(lines):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Line number {target_line} exceeds file length ({len(lines)} lines)",
        )

    line_text = lines[target_line - 1].strip()

    # Find the AST node closest to the target line
    matched_node: Optional[ast.AST] = None
    for node in ast.walk(tree):
        if getattr(node, "lineno", None) == target_line:
            matched_node = node
            break

    # Generate beginner-friendly explanation based on node type
    construct_type = "statement"
    explanation = f"Executing line {target_line}: `{line_text}`."
    tip = None

    if matched_node:
        if isinstance(matched_node, (ast.Assign, ast.AugAssign)):
            construct_type = "assignment"
            explanation = (
                f"Variable assignment: Evaluates the expression on the right-hand side and updates the variable binding. `{line_text}`"
            )
            tip = "Variables in Python store references to values in memory; reassignment updates the reference."
        elif isinstance(matched_node, ast.If):
            construct_type = "condition"
            explanation = (
                f"Conditional decision (`if`): Checks whether the condition is True. If True, executes the indented code block; otherwise branches to `elif` or `else`."
            )
            tip = "Conditions in Python evaluate truthiness (non-zero numbers and non-empty collections are considered True)."
        elif isinstance(matched_node, ast.For):
            construct_type = "loop"
            explanation = (
                f"Counted iteration (`for` loop): Iterates sequentially over elements in the sequence, updating the loop variable on each round."
            )
            tip = "Use `range(n)` to repeat a block of code exactly `n` times."
        elif isinstance(matched_node, ast.While):
            construct_type = "loop"
            explanation = (
                f"Conditional iteration (`while` loop): Continuously executes the loop body as long as the test condition remains True."
            )
            tip = "Ensure that the loop variable changes inside the body so the loop eventually terminates!"
        elif isinstance(matched_node, ast.FunctionDef):
            construct_type = "function_def"
            explanation = (
                f"Function definition: Declares reusable subroutine `{matched_node.name}` with parameters. The function body is not executed until called."
            )
            tip = "Functions promote modularity and code reuse, avoiding duplicated logic."
        elif isinstance(matched_node, ast.Return):
            construct_type = "return"
            explanation = (
                f"Return statement: Immediately halts execution of the active function and sends the result back to the caller."
            )
            tip = "If a function finishes without an explicit return statement, it implicitly returns `None`."
        elif isinstance(matched_node, ast.Call):
            construct_type = "function_call"
            explanation = (
                f"Function call: Transfers execution control to the called function with the provided arguments, pausing the current line until it returns."
            )
            tip = "Function calls push a new frame onto the call stack."

    return CodeExplainResponse(
        success=True,
        line_number=target_line,
        explanation=explanation,
        construct_type=construct_type,
        pedagogical_tip=tip,
    )


@router.post("/trace", response_model=CodeTraceResponse)
def trace_code_endpoint(request: CodeTraceRequest) -> CodeTraceResponse:
    """
    Executes supported Python code inside a secure, subprocess-isolated sandbox.
    Captures step-by-step line execution, local variable states, call-stack depth,
    and returns an annotated Control Flow Graph ready for canvas playback.
    """
    lang = request.language.strip().lower()
    if lang != "python":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{request.language}' is not supported for execution tracing.",
        )

    # Step 1: Run isolated execution tracer
    trace = SafeExecutionTracer.trace(
        source_code=request.code,
        timeout=request.timeout_seconds,
        max_steps=request.max_steps,
    )

    # Step 2: Build static CFG
    try:
        cfg = AstCodeAnalyzer.build_cfg(request.code)
        # Step 3: Map trace events to CFG nodes
        annotated_cfg = SafeExecutionTracer.map_trace_to_graph(trace, cfg)
        # Step 4: Apply layout
        laid_out_cfg = DiagramLayoutEngine.layout(annotated_cfg)
    except Exception:
        laid_out_cfg = None

    return CodeTraceResponse(
        success=trace.terminated_normally,
        trace=trace,
        total_steps=trace.total_steps,
        terminated_normally=trace.terminated_normally,
        termination_reason=trace.termination_reason,
        stdout=trace.stdout,
        diagram=laid_out_cfg,
        error_message=trace.error_message,
    )
