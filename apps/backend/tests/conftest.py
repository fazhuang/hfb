"""Conftest for apps/backend/tests/ — re-export E2E fixtures from tests/e2e/conftest.py.

The test_v4_real_sourceref_integration.py browser-closure test depends on:
  - live_servers   (backend + frontend subprocesses on free ports)
  - page           (Playwright browser page injected by pytest-playwright)

These are defined in tests/e2e/conftest.py which pytest cannot discover
from apps/backend/tests/ because conftest hierarchy only searches upward
in the directory tree, never across sibling branches.

We import them explicitly so that test collection finds them.
"""

from tests.e2e.conftest import library_test_users, live_servers  # noqa: F401
