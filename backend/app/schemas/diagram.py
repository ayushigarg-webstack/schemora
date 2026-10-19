"""
Pydantic schemas for Diagram generation, validation, and capability queries.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ir.models import (
    DiagramGraph,
    DiagramType,
    ValidationWarning,
    ValidationErrorDetail,
)


class DiagramTypeInfo(BaseModel):
    """Information regarding a supported diagram family."""
    type: str = Field(description="Unique identifier of diagram family")
    label: str = Field(description="Display name")
    description: str = Field(description="Semantic purpose and CS domain")
    layout_strategy: str = Field(description="Associated geometric layout strategy")
    example_prompt: str = Field(description="Sample natural language input")


class DiagramGenerateRequest(BaseModel):
    """Request payload for text-to-diagram generation."""
    text: str = Field(
        min_length=5,
        max_length=10000,
        description="Natural language prompt describing the system or workflow"
    )
    diagram_type: Optional[str] = Field(
        default=None,
        description="Optional explicit diagram type override (e.g. 'flowchart', 'architecture')"
    )
    layout_direction: Optional[str] = Field(
        default="TB",
        description="Layout flow direction: 'TB' (Top-to-Bottom) or 'LR' (Left-to-Right)"
    )


class DiagramGenerateResponse(BaseModel):
    """Structured response from the text-to-diagram generation pipeline."""
    success: bool = True
    diagram: DiagramGraph = Field(description="Complete DiagramGraph IR with geometric layout coordinates")
    diagram_type: str = Field(description="Inferred or requested diagram family")
    confidence: Optional[float] = Field(default=None, description="Classifier confidence score if predicted")
    warnings: List[ValidationWarning] = Field(default_factory=list, description="Structural or validation warnings")
    execution_time_ms: float = Field(ge=0.0, description="Pipeline latency in milliseconds")


class DiagramValidateRequest(BaseModel):
    """Request payload for standalone diagram validation."""
    diagram: DiagramGraph = Field(description="Diagram intermediate representation to validate")


class DiagramValidateResponse(BaseModel):
    """Structured validation report."""
    is_valid: bool
    diagram_type: str
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
    warnings: List[ValidationWarning] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Topological and connectivity metrics")
