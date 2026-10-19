"""
Health diagnostic routes.
"""

from fastapi import APIRouter
from ..config import settings
from ..schemas.health import HealthResponse
from ..dependencies import get_uptime_seconds, get_system_components_health

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Returns system status, active version, uptime, and availability
    of individual subsystems (NLP pipeline, ML classifier, Layout engine, Sandbox tracer).
    """
    components = get_system_components_health()
    all_operational = all(c.operational for c in components.values())
    status_str = "healthy" if all_operational else "degraded"

    return HealthResponse(
        status=status_str,
        version=settings.app_version,
        uptime_seconds=get_uptime_seconds(),
        components=components,
    )
