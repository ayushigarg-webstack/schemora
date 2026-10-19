"""
Global exception handlers and structured error formatting middleware.
Ensures uniform error responses and protects against internal traceback exposure.
"""

import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from code_tracer.security import SecurityViolationError

logger = logging.getLogger(__name__)


def make_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: any = None
) -> JSONResponse:
    """Creates a consistent, structured JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
            }
        }
    )


async def security_violation_handler(request: Request, exc: SecurityViolationError) -> JSONResponse:
    """Handles sandbox security policy rejections."""
    logger.warning(f"Security violation blocked on {request.url.path}: {exc.message}")
    return make_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code="SECURITY_VIOLATION",
        message=exc.message,
        details={
            "line_number": exc.line_number,
            "construct": exc.construct,
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic request payload validation errors."""
    error_details = []
    for err in exc.errors():
        loc = " -> ".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "Invalid field")
        error_details.append({"location": loc, "message": msg})

    return make_error_response(
        status_code=422,
        error_code="REQUEST_VALIDATION_ERROR",
        message="Request payload failed schema validation",
        details=error_details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles standard FastAPI / Starlette HTTP exceptions."""
    return make_error_response(
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled exceptions."""
    logger.error(f"Unhandled exception processing {request.url.path}: {str(exc)}", exc_info=True)
    return make_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred while processing the request.",
    )
