"""
Backend Application package.
"""

import sys
from pathlib import Path

# Ensure ml-engine and backend directories are in sys.path
_root = Path(__file__).parent.parent.parent
_ml_engine = _root / "ml-engine"
_backend = _root / "backend"

for _p in [str(_ml_engine), str(_backend), str(_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from .main import app, create_app

__all__ = ["app", "create_app"]
