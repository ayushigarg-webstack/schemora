"""
CLI entry point to run the FastAPI backend using Uvicorn.
Usage:
    python backend/run.py
    or
    uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
"""

import sys
from pathlib import Path

# Ensure ml-engine and backend directories are in sys.path
root_dir = Path(__file__).parent.parent
ml_engine_dir = root_dir / "ml-engine"
backend_dir = root_dir / "backend"

for d in [str(ml_engine_dir), str(backend_dir), str(root_dir)]:
    if d not in sys.path:
        sys.path.insert(0, d)

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.app_name} on http://{settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
