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
import json
import socket
import subprocess
import sys
import time
import uuid as _uuid
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

    def test_v4_redirects_to_v4_research(
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
        page.goto(f"{frontend_url}/v4")
        page.wait_for_url("**/v4/research**", timeout=10000)
        assert page.locator('#v4-topic').is_visible()

    def test_navbar_navigates_to_v4_research(
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
        page.goto(f"{frontend_url}/")
        page.wait_for_selector('nav', timeout=5000)

        # Click the V4 Research nav link
        page.locator('nav a[href="/v4/research"]').click()
        page.wait_for_url("**/v4/research**", timeout=10000)
        assert page.locator('#v4-topic').is_visible()


# ============================================================
# Cross-project isolation fixtures
# ============================================================


@pytest.fixture(scope="module")
def cross_users(live_servers):
    """Create two independent users (A and B), each with a session + note + citation + query history + run.

    Returns a dict with user_a / user_b entries, each containing:
      token, session_id, session_title, note_content, citation_body
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"

    def _api_post(user_tokens, path, json_payload):
        r = httpx.post(
            f"{base}{path}",
            json=json_payload,
            headers={"Authorization": f"Bearer {user_tokens['access_token']}"},
            timeout=10,
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"POST {path} failed with {r.status_code}: {r.text[:300]}"
            )
        return r.json().get("data", r.json())

    # Create two users
    token_a = _seed_user(backend_port, f"cross-a-{_uuid.uuid4().hex[:6]}", "CrossA_Pass123!")
    token_b = _seed_user(backend_port, f"cross-b-{_uuid.uuid4().hex[:6]}", "CrossB_Pass123!")

    # User A: session + note + citation + v4 query history
    sess_a = _api_post(token_a, "/api/v1/workspace/sessions", {"title": "用户A的课题"})
    sid_a = sess_a["id"]
    title_a = sess_a["title"]
    note_a = _api_post(token_a, f"/api/v1/workspace/sessions/{sid_a}/notes", {"content": "A的笔记内容"})
    cit_a = _api_post(token_a, f"/api/v1/workspace/sessions/{sid_a}/citations", {
        "trace_json": json.dumps({"document_id": "cross-doc", "chunk_id": "cross-chunk", "passage_id": str(_uuid.uuid4())}),
        "citation_text": "A引用某条文",
        "source_document": "cross-doc",
    })
    # v4 research session run (for history + runs endpoints)
    try:
        _api_post(token_a, "/api/v4/research/session", {"title": title_a, "query": "测试查询"})
    except RuntimeError:
        pass  # v4 session creation may fail without passages — we still have the session

    # User B: session + note + citation + v4 query history
    sess_b = _api_post(token_b, "/api/v1/workspace/sessions", {"title": "用户B的课题"})
    sid_b = sess_b["id"]
    title_b = sess_b["title"]
    note_b = _api_post(token_b, f"/api/v1/workspace/sessions/{sid_b}/notes", {"content": "B的笔记内容"})
    cit_b = _api_post(token_b, f"/api/v1/workspace/sessions/{sid_b}/citations", {
        "trace_json": json.dumps({"document_id": "cross-doc", "chunk_id": "cross-chunk", "passage_id": str(_uuid.uuid4())}),
        "citation_text": "B引用某条文",
        "source_document": "cross-doc",
    })
    try:
        _api_post(token_b, "/api/v4/research/session", {"title": title_b, "query": "测试查询"})
    except RuntimeError:
        pass

    return {
        "base": base,
        "user_a": {"token": token_a, "session_id": sid_a, "title": title_a, "note": note_a, "citation": cit_a},
        "user_b": {"token": token_b, "session_id": sid_b, "title": title_b, "note": note_b, "citation": cit_b},
    }


# ============================================================
# CrossProjectIsolation — browser-level workspace isolation
# ============================================================


def _auth_nav(page, frontend_url, tokens):
    """Inject auth tokens into localStorage and navigate to base."""
    page.goto(f"{frontend_url}/")
    page.evaluate(
        """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
        [tokens["access_token"], tokens["refresh_token"]],
    )


class TestCrossProjectIsolation:
    """Browser-level cross-project isolation probes.

    Verifies:
      - User A can see own workspace / project detail
      - Switching between own projects clears stale data
      - User A visiting B's session URLs sees  "课题不存在" and NOT B's content
    """

    def test_a_workspace_loads(self, live_servers, cross_users, page):
        """User A's own workspace shows their title, no error state."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        _auth_nav(page, frontend_url, a["token"])
        page.goto(f"{frontend_url}/research/{a['session_id']}/workspace")
        page.wait_for_selector("h1", timeout=10000)
        # Wait for the title to settle from fallback "研究工作区"
        page.wait_for_function(
            f"""() => document.querySelector('h1')?.textContent === '{a['title']}'""",
            timeout=10000,
        )
        # Title should contain A's session title
        assert page.locator("h1").text_content() == a["title"], (
            f"Expected h1 to be '{a['title']}', got '{page.locator('h1').text_content()}'"
        )
        # Should NOT show "课题不存在" (404 state)
        assert page.locator("text=课题不存在").count() == 0, (
            "Own workspace should not show '课题不存在'"
        )

    def test_a_project_detail_loads(self, live_servers, cross_users, page):
        """User A's own project detail shows '开始研究'."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        _auth_nav(page, frontend_url, a["token"])
        page.goto(f"{frontend_url}/research/{a['session_id']}")
        page.wait_for_selector("h1", timeout=10000)
        assert page.locator("text=开始研究").is_visible(), (
            "Own project detail should show '开始研究'"
        )

    def test_switch_own_projects_no_residue(self, live_servers, cross_users, page):
        """Switching from project A1 to A2 clears A1's title from DOM."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]

        # Create a SECOND session for user A
        base = cross_users["base"]
        sess_a2_data = httpx.post(
            f"{base}/api/v1/workspace/sessions",
            json={"title": "用户A的第二课题"},
            headers={"Authorization": f"Bearer {a['token']['access_token']}"},
            timeout=10,
        ).json()["data"]
        sid_a2 = sess_a2_data["id"]
        title_a2 = sess_a2_data["title"]

        _auth_nav(page, frontend_url, a["token"])

        # Visit A1 workspace
        page.goto(f"{frontend_url}/research/{a['session_id']}/workspace")
        page.wait_for_selector("h1", timeout=10000)
        # Wait for the title to settle from fallback "研究工作区"
        page.wait_for_function(
            f"""() => document.querySelector('h1')?.textContent === '{a['title']}'""",
            timeout=10000,
        )
        assert page.locator("h1").text_content() == a["title"]

        # Navigate to A2 workspace
        page.goto(f"{frontend_url}/research/{sid_a2}/workspace")
        page.wait_for_selector("h1", timeout=10000)
        # Wait for the title to settle (fallback is "研究工作区" while loading)
        page.wait_for_function(
            f"""() => document.querySelector('h1')?.textContent === '{title_a2}'""",
            timeout=10000,
        )
        assert page.locator("h1").text_content() == title_a2
        # A1's title should NOT be in DOM
        assert page.locator(f"h1:has-text('{a['title']}')").count() == 0, (
            f"A1 title '{a['title']}' should not be visible after switching to A2"
        )

    def test_cross_user_workspace_blocked(self, live_servers, cross_users, page):
        """User A visiting B's workspace URL → '课题不存在', B's title NOT leaked."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        b = cross_users["user_b"]
        _auth_nav(page, frontend_url, a["token"])
        page.goto(f"{frontend_url}/research/{b['session_id']}/workspace")
        page.wait_for_timeout(3000)  # let the 404 state render
        # Must show "课题不存在"
        assert page.locator("text=课题不存在").is_visible(), (
            "Cross-user workspace should show '课题不存在'"
        )
        # B's title must NOT appear
        assert page.locator(f"h1:has-text('{b['title']}')").count() == 0, (
            f"B's title '{b['title']}' should never appear in A's browser"
        )

    def test_cross_user_project_blocked(self, live_servers, cross_users, page):
        """User A visiting B's project detail URL → access denied, no B content leaked."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        b = cross_users["user_b"]
        _auth_nav(page, frontend_url, a["token"])
        page.goto(f"{frontend_url}/research/{b['session_id']}")
        page.wait_for_timeout(3000)
        # Must show access-denied or not-found state
        denied = page.locator("text=课题不存在")
        no_permission = page.locator("text=没有访问权限")
        assert denied.is_visible() or no_permission.is_visible(), (
            "Cross-user project should show access-denied state"
        )
        # B's note content must NOT appear
        note_text = b["note"].get("content", "")
        if note_text:
            assert page.locator(f"text={note_text}").count() == 0, (
                "B's note content should NOT be visible to A"
            )

    def test_cross_user_workflow_blocked(self, live_servers, cross_users, page):
        """User A visiting B's workflow URL → '课题不存在', no workflow session loaded."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        b = cross_users["user_b"]
        _auth_nav(page, frontend_url, a["token"])
        page.goto(f"{frontend_url}/research/{b['session_id']}/workflow")
        page.wait_for_timeout(3000)
        assert page.locator("text=课题不存在").is_visible(), (
            "Cross-user workflow URL should show '课题不存在'"
        )
        # B's title should not appear anywhere
        assert page.locator(f"h1:has-text('{b['title']}')").count() == 0, (
            f"B's title '{b['title']}' should not be visible in A's workflow view"
        )
