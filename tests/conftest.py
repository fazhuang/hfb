"""
Shared pytest configuration — ensures apps/backend and project root are on sys.path.
"""
import sys
from pathlib import Path

# Add apps/backend to sys.path so that `from app.xxx import yyy` works in tests
backend_path = Path(__file__).resolve().parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Also add project root so that `from tests.xxx import yyy` works under uv run
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))
