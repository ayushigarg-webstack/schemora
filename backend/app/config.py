"""
Backend Application Configuration.
Environment-driven settings for FastAPI server, CORS policies, security limits,
and component timeouts.
"""

import os
from typing import List
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application configuration settings."""
    app_name: str = "AI Diagram Generator & Live Code Explainer API"
    app_version: str = "2.0.0"
    app_description: str = (
        "Production-grade FastAPI backend for automated text-to-diagram generation, "
        "semantic graph validation, static AST analysis, and sandboxed execution tracing."
    )
    host: str = os.getenv("API_HOST", "127.0.0.1")
    port: int = int(os.getenv("API_PORT", "8000"))
    debug: bool = os.getenv("API_DEBUG", "false").lower() == "true"

    # CORS configuration for React frontend development and preview
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Security & resource quotas
    max_text_length: int = 10000  # chars for natural language prompts
    max_code_length: int = 20000  # chars for Python snippets
    default_trace_steps: int = 500
    max_trace_steps: int = 2000
    default_trace_timeout: float = 2.0  # seconds
    max_trace_timeout: float = 5.0  # seconds


settings = Settings()
