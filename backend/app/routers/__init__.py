"""
Routers package.
"""

from .health import router as health_router
from .diagram import router as diagram_router
from .code import router as code_router

__all__ = ["health_router", "diagram_router", "code_router"]
