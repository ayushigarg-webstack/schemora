"""
Pydantic schemas for API health and system diagnostics.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ComponentStatus(BaseModel):
    """Health status of an individual backend subsystem."""
    status: str = Field(description="'available', 'degraded', or 'unavailable'")
    details: Optional[str] = Field(default=None, description="Diagnostic details or version info")
    operational: bool = Field(default=True)


class HealthResponse(BaseModel):
    """System health check response."""
    status: str = Field(default="healthy", description="'healthy' or 'degraded'")
    version: str = Field(default="2.0.0")
    uptime_seconds: float = Field(ge=0.0)
    components: Dict[str, ComponentStatus] = Field(default_factory=dict)
