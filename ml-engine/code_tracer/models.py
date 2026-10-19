"""
Data models for code analysis and runtime execution tracing.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ir.models import DiagramGraph, SourceLocation, ExecutionStateSnapshot


class ExecutionEvent(BaseModel):
    """
    Structured runtime execution event captured during step-by-step tracing.
    """
    step_id: int = Field(ge=0, description="0-indexed sequence counter")
    line_number: int = Field(default=1, ge=0, description="1-indexed source code line number")
    event_type: str = Field(description="Event category: 'line', 'call', 'return', 'exception'")
    function_name: Optional[str] = Field(default=None, description="Name of active function frame")
    call_stack: List[str] = Field(default_factory=list, description="Active call stack frames")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Snapshot of local variables")
    return_value: Optional[Any] = Field(default=None, description="Return value if event_type is 'return'")
    exception_info: Optional[str] = Field(default=None, description="Error details if exception occurred")
    explanation: Optional[str] = Field(default=None, description="Pedagogical plain-English explanation")
    is_runtime_observed: bool = Field(default=True, description="Observed from execution, not static inference")

    def to_snapshot(self) -> ExecutionStateSnapshot:
        """Converts to the IR ExecutionStateSnapshot model."""
        return ExecutionStateSnapshot(
            step_id=self.step_id,
            line_number=self.line_number,
            event_type=self.event_type,
            function_name=self.function_name,
            call_stack=self.call_stack,
            variables=self.variables,
            is_runtime_observed=self.is_runtime_observed,
            explanation=self.explanation,
        )


class ExecutionTrace(BaseModel):
    """
    Complete chronological execution trace of a Python code snippet.
    """
    events: List[ExecutionEvent] = Field(default_factory=list)
    total_steps: int = 0
    terminated_normally: bool = True
    termination_reason: str = Field(
        default="completed",
        description="'completed', 'max_steps_exceeded', 'timeout', 'exception', 'security_violation'"
    )
    stdout: str = Field(default="", description="Captured standard output")
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed")
    execution_time_ms: float = Field(default=0.0, description="Wall clock runtime in milliseconds")
    source_code: str = Field(default="", description="Original source code analyzed")


class CodeAnalysisResult(BaseModel):
    """
    Combined static analysis and runtime tracing outcome.
    """
    source_code: str
    cfg_graph: DiagramGraph = Field(description="Static Control Flow Graph")
    call_graph: Optional[DiagramGraph] = Field(default=None, description="Static Call Graph")
    trace: Optional[ExecutionTrace] = Field(default=None, description="Runtime execution trace if executed")
    annotated_graph: Optional[DiagramGraph] = Field(
        default=None,
        description="CFG graph with runtime execution states attached to nodes"
    )
