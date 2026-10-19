"""
Pydantic schemas for Code Analysis, Pedagogical Explanations, and Sandboxed Tracing.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ir.models import DiagramGraph
from code_tracer.models import ExecutionTrace


class LanguageInfo(BaseModel):
    """Supported language capabilities and operational status."""
    language: str = Field(description="Language identifier e.g. 'python'")
    name: str = Field(description="Display name e.g. 'Python 3'")
    status: str = Field(description="'supported', 'experimental', or 'planned'")
    capabilities: List[str] = Field(default_factory=list)
    is_sandboxed: bool = Field(default=True)
    version: Optional[str] = Field(default=None)


class CodeAnalyzeRequest(BaseModel):
    """Request payload for static code analysis."""
    code: str = Field(
        min_length=1,
        max_length=20000,
        description="Source code snippet to analyze"
    )
    language: str = Field(default="python", description="Programming language ('python')")
    view_mode: str = Field(
        default="cfg",
        description="View mode: 'cfg' (Control Flow Graph) or 'call_graph' (Function Hierarchy)"
    )
    layout_direction: Optional[str] = Field(default="TB", description="'TB' or 'LR'")


class CodeAnalyzeResponse(BaseModel):
    """Structured code analysis diagram with exact source mappings."""
    success: bool = True
    language: str
    view_mode: str
    diagram: DiagramGraph = Field(description="DiagramGraph with SourceLocation line mappings and layout coordinates")
    total_nodes: int
    total_edges: int
    warnings: List[str] = Field(default_factory=list)


class CodeExplainRequest(BaseModel):
    """Request payload for plain-English beginner explanation."""
    code: str = Field(min_length=1, max_length=20000, description="Source code containing snippet")
    language: str = Field(default="python")
    line_number: Optional[int] = Field(default=None, ge=1, description="1-indexed line number to explain")
    node_id: Optional[str] = Field(default=None, description="Optional CFG node ID to explain")


class CodeExplainResponse(BaseModel):
    """Beginner-friendly explanation for a specific code line or block."""
    success: bool = True
    line_number: Optional[int] = None
    explanation: str
    construct_type: str = Field(description="e.g. 'assignment', 'condition', 'loop', 'function_def', 'return'")
    pedagogical_tip: Optional[str] = None


class CodeTraceRequest(BaseModel):
    """Request payload for isolated runtime execution tracing."""
    code: str = Field(min_length=1, max_length=20000, description="Python code to trace in sandbox")
    language: str = Field(default="python")
    max_steps: int = Field(default=500, ge=10, le=2000, description="Maximum execution events before cutoff")
    timeout_seconds: float = Field(default=2.0, ge=0.5, le=5.0, description="Execution timeout limit in seconds")


class CodeTraceResponse(BaseModel):
    """Structured execution trace mapped to visual diagram."""
    success: bool = True
    trace: ExecutionTrace = Field(description="Chronological step events and local variable states")
    total_steps: int
    terminated_normally: bool
    termination_reason: str
    stdout: str
    diagram: Optional[DiagramGraph] = Field(
        default=None,
        description="Annotated CFG graph with observed execution states on nodes"
    )
    error_message: Optional[str] = None
