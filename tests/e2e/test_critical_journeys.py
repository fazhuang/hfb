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
    env["VITE_PROXY_TARGET"] = f"http://127.0.0.1:{backend_port}"
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
            "username": username, "email": f"{username}@example.com", "password": password,
        }, timeout=5)
        if r.status_code not in (201, 200):
            raise RuntimeError(
                f"Registration failed: {r.status_code} {r.text}"
            )
        r2 = httpx.post(f"{base}/api/v1/auth/login", json={
            "username": username, "password": password,
        }, timeout=5)
        if r2.status_code == 200:
            return r2.json()["data"]
        raise RuntimeError(f"Login failed: {r2.status_code} {r2.text}")
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Auth request failed: {exc}") from exc
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


@pytest.fixture(scope="module")
def research_data(live_servers, test_user):
    """Create an isolated validation corpus through the public API."""
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {test_user['access_token']}"}
    me_response = httpx.get(
        f"{base}/api/v1/auth/me",
        headers=headers,
        timeout=10,
    )
    if me_response.status_code != 200:
        raise RuntimeError(
            f"Authenticated /auth/me failed: "
            f"{me_response.status_code} {me_response.text}"
        )

    def create(resource: str, payload: dict) -> dict:
        response = httpx.post(
            f"{base}/api/v1/{resource}",
            json=payload,
            headers=headers,
            timeout=10,
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to create {resource}: "
                f"{response.status_code} {response.text}"
            )
        return response.json()["data"]

    person = create("persons", {
        "name": "皇甫谧",
        "dynasty": "西晋",
        "biography": "流程验证人物资料。",
    })
    book = create("books", {
        "title": "针灸甲乙经（流程验证）",
        "dynasty": "西晋",
        "author_id": person["id"],
    })
    source_version = create("versions", {
        "book_id": book["id"],
        "version_name": "流程验证本 A",
        "era": "验证数据",
        "repository": "流程验证资料库",
        "shelf_mark": "VALIDATION-A",
        "source_url": "https://example.invalid/validation-a",
    })
    target_version = create("versions", {
        "book_id": book["id"],
        "version_name": "流程验证本 B",
        "era": "验证数据",
        "repository": "流程验证资料库",
        "shelf_mark": "VALIDATION-B",
        "source_url": "https://example.invalid/validation-b",
    })
    chapter = create("chapters", {
        "book_id": book["id"],
        "title": "流程验证章节",
        "order": 1,
    })
    source_passage = create("passages", {
        "chapter_id": chapter["id"],
        "version_id": source_version["id"],
        "content_text": "凡刺之法，必候日月星辰，四时八正之气。",
        "order": 1,
        "tags": "流程验证",
    })
    target_passage = create("passages", {
        "chapter_id": chapter["id"],
        "version_id": target_version["id"],
        "content_text": "凡刺之法，必候日月星辰，四时八节之气。",
        "order": 1,
        "tags": "流程验证",
    })
    return {
        "source_passage": source_passage,
        "target_passage": target_passage,
    }


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

    def test_login_succeeds(self, live_servers, test_user, page):
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


class TestResearchWorkflow:
    """The first product workflow works through the browser."""

    def test_version_comparison_note_and_export(
        self,
        live_servers,
        test_user,
        research_data,
        page,
    ):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/")
        page.evaluate(
            """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
            [test_user["access_token"], test_user["refresh_token"]],
        )

        page.goto(f"{frontend_url}/research")
        page.wait_for_selector("text=证据驱动的版本比较", timeout=10000)
        page.fill("#research-query", "凡刺之法")
        page.click(".search-form button")
        page.wait_for_selector(".result-item", timeout=10000)

        source = page.locator(".result-item").filter(has_text="流程验证本 A")
        target = page.locator(".result-item").filter(has_text="流程验证本 B")
        source.get_by_role("button", name="设为底本").click()
        target.get_by_role("button", name="设为对校本").click()
        page.get_by_test_id("compare-passages").click()

        try:
            page.wait_for_selector(".comparison-panel", timeout=10000)
        except Exception as exc:
            error_text = (
                page.locator(".message--error").text_content()
                if page.locator(".message--error").count()
                else "No visible error message"
            )
            raise AssertionError(
                f"Comparison did not render: {error_text}"
            ) from exc
        assert page.locator(".comparison-panel").get_by_text("1 处差异").is_visible()
        assert page.get_by_text("来源完整").count() == 2

        page.fill("#research-note", "验证八正与八节的版本差异。")
        page.get_by_role("button", name="保存研究笔记").click()
        page.get_by_text("研究笔记已保存。").wait_for()

        with page.expect_download() as download_info:
            page.get_by_role("button", name="导出研究记录").click()
        filename = download_info.value.suggested_filename
        assert filename.startswith("hfb-research-record-")
        assert filename.endswith(".md")


class TestV4ResearchPortal:
    """V4 Research Portal loads and tabs switch correctly."""

    def test_v4_research_route_accessible(
        self, live_servers, test_user, page,
    ):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/")
        page.evaluate(
            """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
            [test_user["access_token"], test_user["refresh_token"]],
        )
        page.goto(f"{frontend_url}/v4/research")
        page.wait_for_selector('text=皇甫谧数字人文', timeout=10000)

        # Three tabs visible
        assert page.locator('text=完整研究').is_visible()
        assert page.locator('text=教育模式').is_visible()
        assert page.locator('text=可视化').is_visible()

    def test_v4_research_tab_switching(
        self, live_servers, test_user, page,
    ):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/")
        page.evaluate(
            """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
            [test_user["access_token"], test_user["refresh_token"]],
        )
        page.goto(f"{frontend_url}/v4/research")
        page.wait_for_selector('text=完整研究', timeout=10000)

        # Switch to education tab
        page.locator('text=教育模式').click()
        assert page.locator('#v4-edu-level').is_visible()

        # Switch to visualization tab
        page.locator('text=可视化').click()
        assert page.locator('#v4-viz-type').is_visible()

        # Switch back to research tab
        page.locator('text=完整研究').click()
        assert page.locator('#v4-topic').is_visible()

    def test_v4_research_core_inputs_present(
        self, live_servers, test_user, page,
    ):
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/")
        page.evaluate(
            """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
            [test_user["access_token"], test_user["refresh_token"]],
        )
        page.goto(f"{frontend_url}/v4/research")
        page.wait_for_selector('text=完整研究', timeout=10000)

        # Research tab: topic input and run button
        assert page.locator('#v4-topic').is_visible()
        assert page.locator('[data-testid="v4-run-workflow"]').is_visible()

        # Education tab: inputs
        page.locator('text=教育模式').click()
        assert page.locator('#v4-edu-topic').is_visible()
        assert page.locator('[data-testid="v4-run-education"]').is_visible()

        # Visualization tab: inputs
        page.locator('text=可视化').click()
        assert page.locator('#v4-viz-labels').is_visible()
        assert page.locator('[data-testid="v4-run-viz"]').is_visible()
