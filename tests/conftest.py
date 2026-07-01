"""
Shared pytest configuration — ensures apps/backend and project root are on sys.path.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add apps/backend to sys.path so that `from app.xxx import yyy` works in tests
backend_path = Path(__file__).resolve().parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Also add project root so that `from tests.xxx import yyy` works under uv run
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Reset the global rate limiter between tests to prevent cross-test pollution."""
    from app.services.ai_service import _rate_limiter
    _rate_limiter._timestamps.clear()
