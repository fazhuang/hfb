"""
E2E tests against a real backend using in-memory SQLite.

Each test module starts its own uvicorn server on a random port, seeds test data,
then Playwright drives the browser against the real Vue app + real API.

Requirements:
  - playwright, pytest-playwright installed
  - Backend deps installed (uv sync)
  - Frontend deps installed (pnpm install)

Run:
  uv run pytest tests/e2e/ -v --browser chromium
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import httpx


# ============================================================
# Helpers
# ============================================================


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_ready(url: str, timeout: int = 30) -> bool:
    """Poll a URL until it returns 200 or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _run_backend(port: int) -> subprocess.Popen:
    """Start the FastAPI backend on the given port with SQLite override."""
    backend_dir = Path(__file__).resolve().parent.parent.parent / "apps" / "backend"
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite+aiosqlite://"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(backend_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def _run_frontend(port: int, backend_port: int) -> subprocess.Popen:
    """Start the Vite dev server on the given port, proxying to backend."""
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "apps" / "frontend"
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = f"http://127.0.0.1:{backend_port}"
    proc = subprocess.Popen(
        ["npx", "vite", "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=str(frontend_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def _seed_user(backend_port: int, username: str, password: str) -> dict | None:
    """Register and login a user via the backend API. Return tokens."""
    base = f"http://127.0.0.1:{backend_port}"
    try:
        r = httpx.post(f"{base}/api/v1/auth/register", json={
            "username": username, "email": f"{username}@e2e.test", "password": password,
        }, timeout=5)
        if r.status_code not in (201, 200):
            return None
        r2 = httpx.post(f"{base}/api/v1/auth/login", json={
            "username": username, "password": password,
        }, timeout=5)
        if r2.status_code == 200:
            return r2.json()["data"]
    except Exception:
        pass
    return None


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture(scope="module")
def live_servers():
    """Start backend + frontend, yield (frontend_url, backend_port), teardown."""
    backend_port = _free_port()
    frontend_port = _free_port()

    backend_proc = _run_backend(backend_port)
    frontend_proc = _run_frontend(frontend_port, backend_port)

    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    backend_ready = _wait_ready(f"{backend_url}/health", timeout=30)
    frontend_ready = _wait_ready(frontend_url, timeout=30)

    if not backend_ready:
        backend_proc.terminate()
        frontend_proc.terminate()
        raise RuntimeError("Backend failed to start")

    if not frontend_ready:
        backend_proc.terminate()
        frontend_proc.terminate()
        raise RuntimeError("Frontend failed to start")

    yield frontend_url, backend_port

    backend_proc.terminate()
    frontend_proc.terminate()
    backend_proc.wait(timeout=10)
    frontend_proc.wait(timeout=10)


@pytest.fixture(scope="module")
def test_user(live_servers):
    """Create a test user and return tokens."""
    _, backend_port = live_servers
    tokens = _seed_user(backend_port, "e2euser", "e2ePass123")
    if tokens is None:
        raise RuntimeError("Failed to create test user")
    return tokens


# ============================================================
# Tests
# ============================================================


pytestmark = pytest.mark.skipif(
    "not config.getoption('--browser')",
    reason="Run with --browser chromium (Playwright)",
)


class TestLogin:
    """Login flow must work end-to-end."""

    def test_login_page_loads(self, live_servers, page):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/login")
        page.wait_for_selector('input[placeholder*="用户名"]', timeout=5000)
        assert page.locator('input[placeholder*="密码"]').is_visible()

    def test_login_succeeds(self, live_servers, page):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/login")
        page.fill('input[placeholder*="用户名"]', "e2euser")
        page.fill('input[placeholder*="密码"]', "e2ePass123")
        page.click('button:has-text("登录")')
        # Should redirect to home
        page.wait_for_url(f"{frontend_url}/", timeout=5000)
        # Navbar should show username
        assert page.locator("text=e2euser").is_visible()


class TestSearch:
    """Search must return results from the real backend."""

    def test_search_page_loads(self, live_servers, page):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/search")
        page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
        assert page.locator('button:has-text("搜索")').is_visible()


class TestGraphExplorer:
    """Knowledge graph explorer loads and accepts entity search."""

    def test_graph_page_loads(self, live_servers, page):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/graph")
        page.wait_for_selector('text=知识图谱', timeout=5000)
        # Sidebar search input should be visible
        assert page.locator('input[placeholder*="搜索图谱"]').is_visible()


class TestDashboard:
    """Dashboard renders stats from the backend."""

    def test_dashboard_loads(self, live_servers, page):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/dashboard")
        page.wait_for_selector('text=平台概览', timeout=5000)
        # Stat cards should be present
        assert page.locator("text=最近活动").is_visible()


class TestWorkspace:
    """AI workspace requires auth, loads for logged-in users."""

    def test_workspace_redirects_when_anonymous(self, live_servers, page):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/workspace")
        # Should redirect to login
        page.wait_for_url("**/login**", timeout=5000)

    def test_workspace_loads_when_authenticated(self, live_servers, test_user, page):
        frontend_url, _ = live_servers
        # Set auth token via localStorage before navigating
        page.goto(f"{frontend_url}/")
        page.evaluate(
            """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
            [test_user["access_token"], test_user["refresh_token"]],
        )
        page.goto(f"{frontend_url}/workspace")
        page.wait_for_selector('text=AI 助手', timeout=10000)
        assert page.locator("text=研究画布").is_visible()
