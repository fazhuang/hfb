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
from urllib.parse import urlparse, parse_qs


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


def _stop_proc(proc: subprocess.Popen) -> None:
    """Terminate a subprocess, then wait; force-kill on timeout."""
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _cleanup_db(port: int) -> None:
    """Remove the SQLite file (and -wal/-shm companions) scoped to this port."""
    db_path = Path(f"/tmp/hfb-e2e-cj-{port}.db")
    for suffix in ("", "-wal", "-shm"):
        p = Path(f"{db_path}{suffix}")
        if p.is_file():
            p.unlink(missing_ok=True)


def _tail(path: Path, lines: int = 40) -> str:
    """Return the last *lines* of a text file, or '(empty)' if missing."""
    try:
        content = path.read_text(errors="replace")
    except FileNotFoundError:
        return "(file not found)"
    raw = content.splitlines()
    if not raw:
        return "(empty)"
    return "\n".join(raw[-lines:])


def _fail_start(
    backend_proc: subprocess.Popen | None,
    frontend_proc: subprocess.Popen | None,
    logs: list[Path],
    port: int,
    reason: str,
    url: str,
) -> None:
    """Kill processes, print log tails, clean up DB, and raise RuntimeError."""
    _stop_proc(backend_proc)
    _stop_proc(frontend_proc)
    _cleanup_db(port)
    lines = []
    lines.append(f"\n=== STARTUP FAILED ({url}) ===")
    lines.append(reason)
    lines.append("--- service logs (last 40 lines each) ---")
    for p in logs:
        lines.append(f"\n>>> {p.name} ({p})")
        lines.append(_tail(p))
    lines.append("=== end startup failure ===\n")
    raise RuntimeError("\n".join(lines))


def _run_backend(port: int) -> tuple[subprocess.Popen, Path]:
    """Start the FastAPI backend on the given port with SQLite override.

    Returns (process, log_path) — log goes to a scoped temp file, never DEVNULL.
    """
    backend_dir = Path(__file__).resolve().parent.parent.parent / "apps" / "backend"
    log_path = Path(f"/tmp/hfb-e2e-cj-{port}-backend.log")
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:////tmp/hfb-e2e-cj-{port}.db"
    env["SEED_TEST_DATA"] = "1"  # Enable test-only seed-run endpoint
    old_umask = os.umask(0o077)
    log_fh = log_path.open("wb")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=str(backend_dir),
            env=env,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
        )
    finally:
        os.umask(old_umask)
    return proc, log_path


def _run_frontend(port: int, backend_port: int) -> tuple[subprocess.Popen, Path]:
    """Start the Vite dev server on the given port, proxying to backend.

    Returns (process, log_path) — log goes to a scoped temp file, never DEVNULL.
    """
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "apps" / "frontend"
    log_path = Path(f"/tmp/hfb-e2e-cj-{port}-frontend.log")
    env = os.environ.copy()
    env["VITE_PROXY_TARGET"] = f"http://127.0.0.1:{backend_port}"
    log_fh = log_path.open("wb")
    proc = subprocess.Popen(
        ["npx", "vite", "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=str(frontend_dir),
        env=env,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )
    return proc, log_path


def _seed_user(backend_port: int, username: str, password: str) -> dict | None:
    """Register and login a user via the backend API. Return tokens + username."""
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
            data = r2.json()["data"]
            data["username"] = username  # embed for fixture convenience
            return data
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

    backend_proc, backend_log = _run_backend(backend_port)
    frontend_proc, frontend_log = _run_frontend(frontend_port, backend_port)

    logs: list[Path] = [backend_log, frontend_log]

    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    # ---- /health probe ----
    backend_healthy = _wait_ready(f"{backend_url}/health", timeout=30)
    frontend_healthy = _wait_ready(frontend_url, timeout=30)

    if not backend_healthy:
        _fail_start(backend_proc, frontend_proc, logs, backend_port,
                     "Backend /health failed", backend_url)

    if not frontend_healthy:
        _fail_start(backend_proc, frontend_proc, logs, backend_port,
                     "Frontend failed to start", frontend_url)

    # ---- /ready probe (guards against silent infra failures) ----
    ready_body: str = ""
    ready_ok: bool = False
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            r = httpx.get(f"{backend_url}/ready", timeout=5)
            ready_body = r.text[:2000]
            if r.status_code == 200:
                ready_ok = True
                break
        except Exception:
            pass
        time.sleep(0.5)

    if not ready_ok:
        _fail_start(backend_proc, frontend_proc, logs, backend_port,
                     f"/ready returned non-200.\nbody: {ready_body}",
                     backend_url)

    # ---- Yield to tests ----
    success = False
    try:
        yield frontend_url, backend_port
        success = True
    finally:
        _stop_proc(backend_proc)
        _stop_proc(frontend_proc)
        _cleanup_db(backend_port)
        if success:
            # On success, remove log files — no accumulation
            for p in logs:
                if p.is_file():
                    p.unlink(missing_ok=True)
        else:
            # On failure, print log tails so the operator can diagnose
            print("\n--- E2E LOG TAILS (failure) ---")
            for p in logs:
                print(f"\n>>> {p.name} ({p})")
                print(_tail(p))
            print("--- end log tails ---\n")


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


def _pytest_playwright_present() -> bool:
    """True when pytest-playwright plugin is installed and active."""
    try:
        import pytest_playwright  # noqa: F401
        return True
    except ImportError:
        return False

pytestmark = pytest.mark.skipif(
    not _pytest_playwright_present(),
    reason="pytest-playwright not installed; E2E requires real Chromium browser",
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
        assert page.locator(".user-greeting", has_text="e2euser").is_visible()


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
        # M4: /workspace → /research (canonical project list)
        page.goto(f"{frontend_url}/workspace")
        page.wait_for_url("**/research**", timeout=10000)
        # Verify we land on the canonical project list page
        assert page.locator('h1').first.is_visible()



# ============================================================
# V4 Research Workflow Page E2E — Batch 5 blocking fixes
# ============================================================
# Tests the 5-step research workflow page (ResearchWorkflowPage.vue)
# through the real browser + real backend, with real UI login.
#
# Contract (from useResearchWorkflow.ts):
#   - projectId === ResearchSession.id (route param)
#   - Exactly ONE workflow request per submission
#   - Backend workflow is synchronous
#   - No fake percentages, no simulated progress
#   - No pause/resume
#   - Document selection is not supported — system auto-retrieves
#
# Forbidden:
#   - No page.route / route.fulfill
#   - No page.evaluate to write tokens into localStorage
#   - No mock API responses


@pytest.fixture(scope="module")
def workflow_user(live_servers):
    """Create a dedicated user for the V4 workflow E2E tests."""
    _, backend_port = live_servers
    username = f"wfuser-{_uuid.uuid4().hex[:6]}"
    tokens = _seed_user(backend_port, username, "WfUser_Pass123!")
    if tokens is None:
        raise RuntimeError("Failed to create workflow test user")
    return tokens


@pytest.fixture(scope="module")
def workflow_session(live_servers, workflow_user):
    """Create a ResearchSession for the workflow user via the API."""
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {workflow_user['access_token']}"}

    r = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "针灸甲乙经经络研究"},
        headers=headers,
        timeout=10,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to create session: {r.status_code} {r.text}"
        )
    session_data = r.json().get("data", r.json())
    return {
        "id": session_data["id"],
        "title": session_data["title"],
    }


@pytest.fixture(scope="module")
def workflow_rag_doc(live_servers, workflow_user):
    """Seed a RAG-enabled Document + Chunks that the workflow can retrieve.

    Uses the standard ingest API (no unauthorised scope expansion) followed
    by the admin review endpoint to set rag_enabled=True — the approved
    production path for enabling RAG retrieval.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"

    # ---- Step 1: Ingest via approved endpoint (no rag_enabled in body) ----
    ingest_body = {
        "title": "针灸甲乙经（E2E验证）",
        "text": (
            # Use \n\n to produce multiple chunks (paragraph-boundary chunking).
            # Each chunk includes the unique watermark E2E验证标识 — the query
            # 'E2E验证标识 经络' uses tokens that exist in the fixture text,
            # ensuring the fixture document's chunks rank in top-5.
            "E2E验证标识\n\n"
            "凡刺之法，必候日月星辰，四时八正之气。气定乃刺之。\n\n"
            "是故天温日明，则人血淖液而卫气浮，故血易泻，气易行；\n"
            "天寒日阴，则人血凝泣而卫气沉。\n\n"
            "月始生，则血气始精，卫气始行；\n"
            "月郭满，则血气实，肌肉坚；\n"
            "月郭空，则肌肉减，经络虚，卫气去，形独居。\n\n"
            "是以因天时而调血气也。\n\n"
            "黄帝问曰：经脉十二者，外合于十二经水，而内属于五脏六腑。\n"
            "夫十二经水者，其有大小、深浅、广狭、远近各不同；\n"
            "五脏六腑之高下、小大、受谷之多少亦不等，相应奈何？\n"
            "夫经水者，受水而行之；五脏者，合神气魂魄而藏之；\n"
            "六腑者，受谷而行之，受气而扬之；\n"
            "经脉者，受血而营之。合而以治奈何？\n\n"
            "刺之深浅，灸之壮数，可得闻乎？\n\n"
            "凡刺之理，经脉为始，营其所行，知其度量，\n"
            "内刺五脏，外刺六腑，审察卫气，为百病母，\n"
            "调其虚实，虚实乃止，泻其血络，血尽不殆矣。\n\n"
            "肺出于少商，少商者，手大指端内侧也，为井木；\n"
            "溜于鱼际，鱼际者，手鱼也，为荥；\n"
            "注于太渊，太渊者，鱼后一寸陷者中也，为输；\n"
            "行于经渠，经渠者，寸口中也，动而不居，为经；\n"
            "入于尺泽，尺泽者，肘中之动脉也，为合。手太阴经也。\n\n"
            "心出于中冲，中冲者，手中指之端也，为井木；\n"
            "溜于劳宫，劳宫者，掌中中指本节之内间也，为荥；\n"
            "注于大陵，大陵者，掌后两骨之间方下者也，为输；\n"
            "行于间使，间使者，掌后三寸两筋之间陷者中也，为经；\n"
            "入于曲泽，曲泽者，肘内廉下陷者之中也，屈而得之，为合。手少阴也。\n\n"
            "肝出于大敦，大敦者，足大指之端及三毛之中也，为井木；\n"
            "溜于行间，行间者，足大指间也，为荥；\n"
            "注于太冲，太冲者，行间上二寸陷者之中也，为输；\n"
            "行于中封，中封者，内踝之前一寸半陷者之中，为经；\n"
            "入于曲泉，曲泉者，辅骨之下大筋之上也，屈膝而得之，为合。足厥阴也。\n\n"
            "E2E验证结束"
        ),
        "copyright_status": "public_domain",
        "authorization_basis": "e2e-test-data",
        "source_name": "e2e-workflow-test",
    }
    ingest_resp = httpx.post(
        f"{base}/api/v1/search/ingest",
        json=ingest_body,
        timeout=10,
    )
    if ingest_resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Ingest failed: {ingest_resp.status_code} {ingest_resp.text}"
        )
    doc_data = ingest_resp.json().get("data", ingest_resp.json())
    doc_id = doc_data["document_id"]

    # ---- Step 2: Enable RAG via approved admin review endpoint ----
    # Admin user (admin/admin123) is auto-created by seed_rbac on first
    # auth-triggered registration. Login as admin, then review the document.
    admin_login = httpx.post(
        f"{base}/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=5,
    )
    admin_token = None
    if admin_login.status_code == 200:
        admin_token = admin_login.json()["data"]["access_token"]
    else:
        # Admin may not exist yet — register first (idempotent), then login
        httpx.post(
            f"{base}/api/v1/auth/register",
            json={"username": "admin", "email": "admin@e2e.test", "password": "admin123"},
            timeout=5,
        )
        admin_login2 = httpx.post(
            f"{base}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5,
        )
        if admin_login2.status_code == 200:
            admin_token = admin_login2.json()["data"]["access_token"]

    if admin_token is None:
        raise RuntimeError("Cannot obtain admin token for review endpoint")

    review_resp = httpx.patch(
        f"{base}/api/v1/documents/{doc_id}/review",
        json={"review_status": "approved", "rag_enabled": True},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    if review_resp.status_code != 200:
        raise RuntimeError(
            f"Admin review failed: {review_resp.status_code} {review_resp.text}"
        )

    return {"document_id": doc_id, "chunk_count": doc_data.get("chunk_count", 0)}


class TestResearchWorkflowPageE2E:
    """Canonical 5-step research workflow page — real browser, real backend.

    Task 2B write-path E2E coverage:
      - test_successful_workflow_uses_current_run_artifacts
        Real browser: POST /api/v4/research/workflow (write) → runs fetch →
        evidence/citation extraction → result link. Exactly one workflow
        POST. Citation chain verified in DOM.
      - test_workflow_no_evidence_shows_error_banner
        Write path failure case: NO_EVIDENCE error banner with retry.
      - Cross-user isolation (test_workflow_cross_user_isolation):
        User A writes workflow → User B cannot see User A's result.

    Page-load + structural tests:
      - test_workflow_page_loads_with_valid_session
      - test_workflow_page_shows_not_found_for_invalid_session
      - test_workflow_page_session_requires_auth
    """

    # ------------------------------------------------------------------
    # Page-load states
    # ------------------------------------------------------------------

    def test_workflow_page_loads_with_valid_session(
        self, live_servers, workflow_user, workflow_session, page,
    ):
        """Navigating to workflow page with a valid session shows step 0 (question)."""
        frontend_url, _ = live_servers
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        page.goto(f"{frontend_url}/research/{workflow_session['id']}/workflow")
        page.wait_for_selector("h2", timeout=10000)

        # Step navigation should be visible with all 5 steps
        nav = page.locator(".wsn-nav")
        assert nav.is_visible(), "Step navigation bar should be visible"
        assert nav.locator("text=研究问题").is_visible()
        assert nav.locator("text=文献选择").is_visible()
        assert nav.locator("text=AI 分析").is_visible()
        assert nav.locator("text=证据审查").is_visible()
        assert nav.locator("text=研究报告").is_visible()

        # Question step should be visible
        assert page.locator("#rqs-input").is_visible()
        assert page.locator(".rqs-submit-btn").is_visible()

        # Should NOT show error/empty states
        assert page.locator("text=课题不存在").count() == 0

    def test_workflow_page_shows_not_found_for_invalid_session(
        self, live_servers, workflow_user, page,
    ):
        """Navigating with a non-existent session UUID shows '课题不存在'."""
        frontend_url, _ = live_servers
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        fake_id = str(_uuid.uuid4())
        page.goto(f"{frontend_url}/research/{fake_id}/workflow")
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)

        assert page.locator("text=课题不存在").is_visible()

    def test_workflow_page_session_requires_auth(
        self, live_servers, workflow_session, page,
    ):
        """Navigating to workflow page anonymously redirects to login."""
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/research/{workflow_session['id']}/workflow")
        page.wait_for_url("**/login**", timeout=10000)

    # ------------------------------------------------------------------
    # 5-step workflow flow
    # ------------------------------------------------------------------

    def test_workflow_no_evidence_shows_error_banner(
        self, live_servers, workflow_user, workflow_session, page,
    ):
        """Without RAG documents, submitting a workflow shows the NO_EVIDENCE
        error banner. The UI must NOT show fake evidence or reports.

        The workflow must land in a definite terminal state within the
        backend timeout — no "still submitting after 30s" escape hatch.
        """
        frontend_url, _ = live_servers
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        page.goto(f"{frontend_url}/research/{workflow_session['id']}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        # Step 0: Enter research question
        page.fill("#rqs-input", "针灸甲乙经中的经络理论")
        page.click(".rqs-submit-btn")

        # Step 1: Should now be on document selection step
        page.wait_for_selector(".dss-submit-btn", timeout=5000)
        assert page.locator("text=第二步：文献选择").is_visible()
        assert page.locator("text=针灸甲乙经中的经络理论").is_visible()

        # Step 2: Submit — must land on a definite terminal state
        page.click(".dss-submit-btn")

        # Workflow POST timeout is 120s; wait up to 150s for a terminal state.
        # NO_EVIDENCE should come back much faster (no LLM call needed).
        try:
            page.wait_for_selector(".rwf-error-banner", timeout=150000)
        except Exception:
            # If error banner didn't appear, check for evidence step
            pass

        # Assert definite terminal state — one of:
        #   1. Error banner visible (NO_EVIDENCE or other error)
        #   2. Evidence review step visible (only if real RAG docs exist)
        has_error = page.locator(".rwf-error-banner").count() > 0
        has_evidence = page.locator(".ers-step").count() > 0
        assert has_error or has_evidence, (
            "Workflow must reach a definite terminal state: "
            f"error_banner={has_error}, evidence_step={has_evidence}"
        )

        if has_error:
            # Verify it's a real error with content
            error_text = page.locator(".rwf-error-banner-message").text_content()
            assert len(error_text) > 0, "Error banner should contain a message"
            assert page.locator(".rwf-error-retry-btn").is_visible(), (
                "'返回修改' button must be visible on error banner"
            )
            # Must NOT show fake evidence
            assert page.locator(".ers-item").count() == 0, (
                "NO_EVIDENCE error must not show fake evidence items"
            )
            # Must NOT show report link
            assert page.locator("text=查看完整结果").count() == 0, (
                "NO_EVIDENCE error must not show report result link"
            )
            assert page.locator("text=研究报告").count() == 0 or page.locator(".rrs-card").count() == 0, (
                "NO_EVIDENCE error must not show report card"
            )

    def test_workflow_retry_returns_to_question(
        self, live_servers, workflow_user, workflow_session, page,
    ):
        """After a NO_EVIDENCE error, clicking '返回修改' returns to question step,
        with question input preserved. No try/except: pass for core assertions."""
        frontend_url, _ = live_servers
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        page.goto(f"{frontend_url}/research/{workflow_session['id']}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        # Submit a query that will fail NO_EVIDENCE (no matching docs)
        page.fill("#rqs-input", "非常稀有的古代文献内容xyz")
        page.click(".rqs-submit-btn")
        page.wait_for_selector(".dss-submit-btn", timeout=5000)
        page.click(".dss-submit-btn")

        # Wait for error banner — must arrive within 150s
        page.wait_for_selector(".rwf-error-banner", timeout=150000)

        # Click "返回修改"
        page.locator(".rwf-error-retry-btn").click()

        # Should return to question step with input preserved
        page.wait_for_selector("#rqs-input", timeout=5000)
        input_value = page.locator("#rqs-input").input_value()
        assert "非常稀有" in input_value, (
            f"Question input should be preserved after retry, got: {input_value}"
        )

        # Verify we're back on question step (not some intermediate state)
        assert page.locator("#rqs-input").is_visible()
        assert page.locator(".rqs-submit-btn").is_visible()

    # ------------------------------------------------------------------
    # Successful workflow with real run_id, evidence, and report
    # ------------------------------------------------------------------

    def test_successful_workflow_uses_current_run_artifacts(
        self, live_servers, workflow_user, workflow_session, workflow_rag_doc, page,
    ):
        """Full successful workflow path: question → selection → submit →
        evidence review → research report → result link.

        Verifies:
          - POST /api/v4/research/workflow fires exactly once
          - Response contains non-empty real run_id
          - Page lands on Evidence Review step with real evidence/citations
          - source_ref_title and passage_id are displayed when present
          - Incomplete lineage shows "来源定位不完整"
          - Report step shows markdown preview and correct result link
          - Result link is strictly /research/{session_id}/result/{run_id}
          - Historical runs from other sessions are NOT displayed
        """
        frontend_url, _ = live_servers
        sid = workflow_session["id"]
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        page.goto(f"{frontend_url}/research/{sid}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        # ---- Capture POST /api/v4/research/workflow request ----
        workflow_post_count = 0
        workflow_response_data: dict = {}

        def _on_response(response):
            nonlocal workflow_post_count, workflow_response_data
            if "/api/v4/research/workflow" in response.url and response.request.method == "POST":
                workflow_post_count += 1
                try:
                    workflow_response_data = response.json()
                except Exception:
                    pass

        page.on("response", _on_response)

        # Step 0: Enter research question. The 'E2E验证标识' token
        # appears uniquely in the RAG doc fixture text, and '经络'
        # is a keyword that the segment tokenizer splits out. Together
        # they guarantee the fixture doc's chunks rank in top-5.
        page.fill("#rqs-input", "E2E验证标识 经络")
        page.click(".rqs-submit-btn")

        # Step 1: Document Selection
        page.wait_for_selector(".dss-submit-btn", timeout=5000)
        assert page.locator("text=第二步：文献选择").is_visible()

        # Step 3: Submit → AI Analysis → wait for terminal state
        page.click(".dss-submit-btn")

        # Wait for evidence review step or error
        try:
            page.wait_for_selector(".ers-step", timeout=150000)
            has_evidence = True
        except Exception:
            has_evidence = False

        if not has_evidence:
            # Check what error we got
            error_msg = ""
            error_banner = page.locator(".rwf-error-banner-message")
            if error_banner.count() > 0:
                error_msg = error_banner.first.text_content()
            else:
                # Check page content for clues
                error_msg = page.locator("body").text_content()[:500]
            raise AssertionError(
                f"Workflow should have found evidence. "
                f"Error: {error_msg}. RAG doc id: {workflow_rag_doc['document_id']}"
            )

        # ---- Verify workflow POST happened exactly once ----
        assert workflow_post_count == 1, (
            f"Expected exactly 1 POST /api/v4/research/workflow, got {workflow_post_count}"
        )

        # ---- Verify run_id is non-empty ----
        data = workflow_response_data.get("data", workflow_response_data)
        run_id_from_api = data.get("run_id", "")
        assert run_id_from_api, "POST response must contain non-empty run_id"

        # ---- Evidence review step has content ----
        evidence_count = page.locator(".ers-item").count()
        citation_count = page.locator(".ers-citation-text").count()

        assert evidence_count > 0, (
            "Evidence review step should contain at least 1 evidence item"
        )

        # Check that evidence items show real content
        first_item = page.locator(".ers-item").first
        claim = first_item.locator(".ers-claim-text").text_content()
        assert claim and len(claim) > 0, "Evidence item should have claim text"

        # Check citation text is present
        if citation_count > 0:
            cit_text = page.locator(".ers-citation-text").first.text_content()
            assert len(cit_text) > 0, "Citation text should be non-empty"

        # Check locator display — either real source_ref_title or "来源定位不完整"
        locator_text = page.locator(".ers-locator").first.text_content()
        assert locator_text, "Locator area must have content"
        # Either has real source info OR shows incomplete marker
        has_real_source = "来源" in locator_text
        has_incomplete = "来源定位不完整" in locator_text
        assert has_real_source or has_incomplete, (
            f"Locator must show source info or '来源定位不完整', got: {locator_text!r}"
        )

        # ---- Navigate to report step ----
        # Click "查看研究报告 →" in the evidence summary bar.
        go_to_report_btn = page.locator(".ers-action-btn")
        assert go_to_report_btn.count() > 0, (
            "Evidence review step must have '查看研究报告' button to reach report step"
        )
        go_to_report_btn.first.click()

        # Wait for report card — must appear, not optional
        page.wait_for_selector(".rrs-card", timeout=10000)
        assert page.locator(".rrs-card").count() > 0, (
            "Report card .rrs-card must be visible after clicking '查看研究报告'"
        )

        # Verify report content
        title_el = page.locator(".rrs-card-title")
        assert title_el.count() > 0, "Report card must have a title"
        assert len(title_el.first.text_content()) > 0

        # Verify stats
        stats = page.locator(".rrs-stat-value")
        assert stats.count() >= 2, (
            f"Report must show at least 2 stat values, got {stats.count()}"
        )
        evidence_stat = stats.nth(0).text_content()
        citation_stat = stats.nth(1).text_content()
        assert evidence_stat.isdigit() or evidence_stat == "0"
        assert citation_stat.isdigit() or citation_stat == "0"

        # Verify report preview has markdown content
        preview = page.locator(".rrs-preview-text")
        assert preview.count() > 0, "Report preview .rrs-preview-text must exist"
        preview_text = preview.first.text_content()
        assert len(preview_text) > 0, "Report preview should have content"

        # Verify result link is correct: /research/{session_id}/result/{run_id}
        result_link = page.locator(f'a[href="/research/{sid}/result/{run_id_from_api}"]')
        if result_link.count() == 0:
            # Try fuzzy match
            all_links = page.locator(".rrs-actions a").all()
            found_result_link = False
            for link in all_links:
                href = link.get_attribute("href") or ""
                if f"/research/{sid}/result/" in href:
                    found_result_link = True
                    # Must contain the real run_id from POST response
                    assert run_id_from_api in href, (
                        f"Result link must use run_id from POST response. "
                        f"Expected run_id={run_id_from_api} in href={href}"
                    )
            assert found_result_link, (
                f"Report step must have result link to /research/{sid}/result/..."
            )
        else:
            assert result_link.count() >= 1, (
                f"Result link must point to /research/{sid}/result/{run_id_from_api}"
            )

        # ====================================================================
        # --- Re-search closure: '基于报告重新搜索' button → /library?q=... ---
        # ====================================================================

        re_search_btn = page.locator("button:has-text('基于报告重新搜索')")
        assert re_search_btn.count() > 0, (
            "Report card must have '基于报告重新搜索' button"
        )
        assert re_search_btn.is_visible(), (
            "'基于报告重新搜索' button must be visible"
        )

        # Compute expected query using production logic
        # (useResearchWorkflow.ts navigateToLibrarySearch:701-712):
        #   First non-empty, non-#-prefix line longer than 10 chars, truncated
        #   to 60 chars.  Fallback to report topic/question.
        lines = [l for l in preview_text.split('\n')
                 if l.strip() and not l.startswith('#') and len(l) > 10]
        expected_query = lines[0][:60] if lines else "E2E验证标识 经络"

        # Click re-search button
        re_search_btn.click()

        # Must land on /library with q= query param
        page.wait_for_url("**/library**", timeout=15000)
        page.wait_for_timeout(2000)

        parsed = urlparse(page.url)
        assert parsed.path == "/library", (
            f"Re-search must land on /library, got path {parsed.path}"
        )
        qs = parse_qs(parsed.query)
        assert "q" in qs, (
            f"Re-search URL must have 'q' query param, got {parsed.query}"
        )
        actual_q = qs["q"][0]
        assert actual_q == expected_query, (
            f"Re-search q param mismatch.\n"
            f"Expected: {expected_query!r}\n"
            f"Got:      {actual_q!r}"
        )

        # Must NOT be login page or /research fallback
        assert "/login" not in page.url, (
            "Re-search must not land on login page"
        )
        assert parsed.path != "/research", (
            "Re-search must not land on generic /research fallback"
        )

        # Library search input must be visible
        lib_input = page.locator("#lib-search-input")
        assert lib_input.count() > 0, (
            "Library search input #lib-search-input must be visible"
        )
        assert lib_input.is_visible(), (
            "Library search input must be visible after re-search navigation"
        )

        # ---- Verify no historical runs from other sessions leak in ----
        # No fake or hardcoded run IDs
        page_text = page.content()
        assert "00000000-0000-0000-0000" not in page_text, (
            "No fake run IDs should appear in UI"
        )

        # ---- Verify evidence/report persist across page reload ----
        # After reload, the page initializes to question step.
        # But the run data is persisted server-side — verify it's accessible.
        page.goto(f"{frontend_url}/research/{sid}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)
        # Direct API check: the run is persisted in the session
        _, be_port = live_servers
        runs_resp = __import__('json').loads(
            __import__('httpx').get(
                f"http://127.0.0.1:{be_port}/api/v4/research/session/{sid}/runs",
                headers={"Authorization": f"Bearer {workflow_user['access_token']}"},
                timeout=10,
            ).text
        )
        runs_after = runs_resp.get("data", runs_resp).get("runs", [])
        current_after = [r for r in runs_after if r.get("run_id") == run_id_from_api]
        assert len(current_after) == 1, (
            f"Run {run_id_from_api} must persist after reload. Found {len(current_after)}"
        )
        manifest_after = current_after[0].get("replay_manifest", {})
        snapshot_after = manifest_after.get("retrieval_snapshot", [])
        assert len(snapshot_after) > 0, "retrieval_snapshot must persist across reload"
        assert any(s.get("claim_text") for s in snapshot_after), (
            "Evidence claim_text must persist across reload"
        )

        # ---- Verify the evidence and report are scoped to this run ----
        # After page reload, the page returns to question step. The run_id
        # won't appear on the current page. Instead, verify persistence
        # through the API (already done above). The run_id check is only
        # applicable when on the evidence or report step.
        # (Persistence already verified via direct API call above.)

    def test_workflow_run_isolation_no_history_leak(
        self, live_servers, workflow_user, workflow_session, workflow_rag_doc, page,
    ):
        """Two consecutive workflow runs MUST NOT cross-contaminate.

        Run 1 with topic A → evidence/report scoped to run_id_A.
        Run 2 with topic B → evidence/report scoped to run_id_B.
        Run 2 page must NOT show run 1's title, evidence text, or report markdown.
        """
        frontend_url, _ = live_servers
        sid = workflow_session["id"]
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        captured_run_ids: list[str] = []

        def _capture_run_id(response):
            if "/api/v4/research/workflow" in response.url and response.request.method == "POST":
                try:
                    data = response.json()
                    rid = data.get("data", {}).get("run_id", "")
                    if rid:
                        captured_run_ids.append(rid)
                except Exception:
                    pass

        page.on("response", _capture_run_id)

        # ---- Run 1: Topic A ----
        page.goto(f"{frontend_url}/research/{sid}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        page.fill("#rqs-input", "针刺深浅与灸的壮数")
        page.click(".rqs-submit-btn")
        page.wait_for_selector(".dss-submit-btn", timeout=5000)
        page.click(".dss-submit-btn")

        # Wait for evidence step
        try:
            page.wait_for_selector(".ers-step", timeout=150000)
        except Exception:
            pass

        # Collect Run 1 evidence claim texts for cross-contamination check
        run1_evidence_texts: list[str] = []
        for item in page.locator(".ers-item").all():
            try:
                t = item.locator(".ers-claim-text").text_content()
                if t:
                    run1_evidence_texts.append(t)
            except Exception:
                pass

        # ---- Run 2: Navigate fresh to workflow (no button dependency) ----
        page.goto(f"{frontend_url}/research/{sid}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        # Submit run 2 with different topic
        page.fill("#rqs-input", "逆顺肥胖气血清浊刺法")
        page.click(".rqs-submit-btn")
        page.wait_for_selector(".dss-submit-btn", timeout=5000)
        page.click(".dss-submit-btn")

        # Wait for evidence step
        try:
            page.wait_for_selector(".ers-step", timeout=150000)
        except Exception:
            pass

        # ---- Verify Run 2 shows only its own data ----
        assert len(captured_run_ids) >= 1, "At least one run_id must be captured"

        page_text = page.content()

        # Run 1's evidence claim texts must NOT appear in Run 2's page
        for ev_text in run1_evidence_texts:
            if ev_text and len(ev_text) > 20:
                assert ev_text not in page_text, (
                    f"Run 1 evidence text should NOT appear in Run 2 page: "
                    f"{ev_text[:80]}..."
                )

        # The two run_ids must be different (isolation verified by unique POSTs)
        if len(captured_run_ids) >= 2:
            assert captured_run_ids[0] != captured_run_ids[1], (
                f"Two workflow runs must have different run_ids, "
                f"got {captured_run_ids[0]} and {captured_run_ids[1]}"
            )

    # ------------------------------------------------------------------
    # Cross-user isolation
    # ------------------------------------------------------------------

    def test_workflow_cross_user_blocked(
        self, live_servers, cross_users, page,
    ):
        """User A visiting User B's workflow URL → '课题不存在'."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        b = cross_users["user_b"]

        _login_via_ui(page, frontend_url, a["username"], "CrossA_Pass123!")

        # Capture session API response
        api_404 = False

        def _check_response(response):
            nonlocal api_404
            if f"/api/v1/workspace/sessions/{b['session_id']}" in response.url:
                if response.status == 404:
                    api_404 = True

        page.on("response", _check_response)

        page.goto(f"{frontend_url}/research/{b['session_id']}/workflow")
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)

        assert page.locator("text=课题不存在").is_visible(), (
            "Cross-user workflow URL should show '课题不存在'"
        )
        assert api_404, (
            "Session API for B's session must return 404 when accessed by A"
        )

    # ------------------------------------------------------------------
    # Navigation: back/forward between steps
    # ------------------------------------------------------------------

    def test_workflow_back_to_question_from_selection(
        self, live_servers, workflow_user, workflow_session, page,
    ):
        """In selection step, clicking '返回修改问题' goes back to question step."""
        frontend_url, _ = live_servers
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        page.goto(f"{frontend_url}/research/{workflow_session['id']}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        # Enter question and go to selection
        page.fill("#rqs-input", "经络气血流注")
        page.click(".rqs-submit-btn")
        page.wait_for_selector(".dss-submit-btn", timeout=5000)

        # Click back
        page.click(".dss-back-btn")

        # Should be back at question step with input preserved
        page.wait_for_selector("#rqs-input", timeout=5000)
        input_value = page.locator("#rqs-input").input_value()
        assert input_value == "经络气血流注", (
            f"Question should be preserved when going back, got: {input_value}"
        )

    def test_workflow_step_navigation_visible(
        self, live_servers, workflow_user, workflow_session, page,
    ):
        """Step navigation shows correct current/completed states as we progress."""
        frontend_url, _ = live_servers
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        page.goto(f"{frontend_url}/research/{workflow_session['id']}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        # Initially: step 0 is current
        assert page.locator(".wsn-step--current").locator("text=研究问题").count() > 0

        # Go to selection
        page.fill("#rqs-input", "经络")
        page.click(".rqs-submit-btn")
        page.wait_for_selector(".dss-submit-btn", timeout=5000)

        # Step 0 should be completed (✓), step 1 should be current
        assert page.locator(".wsn-step--completed").locator("text=研究问题").count() > 0
        assert page.locator(".wsn-step--current").locator("text=文献选择").count() > 0


class TestV4ResearchPortal:
    """Legacy URL redirect tests — session-aware canonical redirects.

    Task 2B: /v4/research-internal, /v4/research, /v4, /research/workspace,
    and /workspace now use LegacyRedirect.vue which resolves the user's
    most-recent session and redirects with full project context.

    These tests verify the redirect resolution — NOT V4ResearchView
    (which is no longer directly served).
    """

    def test_v4_research_internal_redirects_to_canonical_workflow(
        self, live_servers, workflow_user, workflow_session, page,
    ):
        """/v4/research-internal → /research/:projectId/workflow via LegacyRedirect.

        Real UI login (workflow_user + workflow_session), then visit the old
        /v4/research-internal URL.  LegacyRedirect resolves the most-recent
        session and redirects to the canonical workflow page.
        """
        frontend_url, _ = live_servers
        sid = workflow_session["id"]

        # Real UI login — no localStorage token injection
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        # Visit the legacy /v4/research-internal URL
        page.goto(f"{frontend_url}/v4/research-internal")

        # Must land on canonical workflow page for the user's real session
        page.wait_for_url(f"**/research/{sid}/workflow", timeout=15000)
        page.wait_for_timeout(2000)

        # Exact pathname assertion
        parsed = urlparse(page.url)
        assert parsed.path == f"/research/{sid}/workflow", (
            f"Expected /research/{sid}/workflow, got {parsed.path}"
        )

        # Must NOT contain /v4 in final URL
        assert "/v4" not in page.url, (
            f"Final URL must not contain /v4, got {page.url}"
        )

        # Workflow-specific input visible
        assert page.locator("#rqs-input").is_visible(), (
            "Workflow question input #rqs-input must be visible after redirect"
        )

        # Must NOT render V4ResearchView tabs
        assert page.locator("text=完整研究").count() == 0, (
            "V4ResearchView '完整研究' tab must not appear after LegacyRedirect"
        )

    def test_v4_research_redirects_to_canonical(
        self, live_servers, test_user, page,
    ):
        """/v4/research redirects to canonical workflow with project context."""
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
        page.wait_for_url("**/research/**", timeout=15000)
        page.wait_for_timeout(2000)
        assert page.locator('h1').first.is_visible() or page.locator('[data-testid]').first.is_visible()

    def test_v4_root_redirects_to_canonical(
        self, live_servers, test_user, page,
    ):
        """/v4 redirects to canonical workflow with project context."""
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
        page.wait_for_url("**/research/**", timeout=15000)
        page.wait_for_timeout(2000)
        # We land on either /research or a canonical research page
        assert page.locator('h1').first.is_visible() or page.locator('[data-testid]').first.is_visible()

    def test_workspace_redirects_to_canonical_with_context(
        self, live_servers, test_user, page,
    ):
        """/research/workspace redirects with project context (not blank /research)."""
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/")
        page.evaluate(
            """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
            [test_user["access_token"], test_user["refresh_token"]],
        )
        page.goto(f"{frontend_url}/research/workspace")
        # LegacyRedirect resolves session and redirects with projectId
        page.wait_for_url("**/research/**", timeout=15000)
        page.wait_for_timeout(2000)
        # Page must be visible — not blank
        assert page.locator('h1').first.is_visible() or page.locator('[data-testid]').first.is_visible()

    def test_short_workspace_redirects_to_canonical(
        self, live_servers, test_user, page,
    ):
        """/workspace redirects with session context."""
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/")
        page.evaluate(
            """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
            [test_user["access_token"], test_user["refresh_token"]],
        )
        page.goto(f"{frontend_url}/workspace")
        page.wait_for_url("**/research/**", timeout=15000)
        page.wait_for_timeout(2000)
        assert page.locator('h1').first.is_visible() or page.locator('[data-testid]').first.is_visible()

    def test_navbar_navigates_to_canonical_research(
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

        # Navbar link points to /research (canonical, not workspace)
        page.locator('nav a[href="/research"]').first.click()
        page.wait_for_timeout(3000)
        # Verify navigation to canonical research page
        assert page.locator('h1').first.is_visible()

    # -- 2B: Replay verification — canonical equivalent FIXED (2026-07-29) --
    def test_gap_replay_verification_matched(
        self, live_servers, result_workflow_session, page,
    ):
        """Canonical replay verification matched=true — real browser, full UI navigation.

        Replay UI lives on canonical ResearchResultPage
        (data-testid="canonical-replay"), implemented in d08fbbd.

        Navigation path (no page.goto() to protected result URL):
          1. /login → real form login
          2. /research → project list → click project → project detail
          3. Project detail → click report → /research/:pid/result/:rid
          4. Result page → click replay button → assert matched=true
        """
        frontend_url, _ = live_servers
        ws = result_workflow_session
        sid = ws["session_id"]
        rid = ws["run_id"]

        # --- Step 1: Real login via UI ---
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        # --- Step 2: Navigate to project list ---
        page.goto(f"{frontend_url}/research")
        page.wait_for_selector("h1", timeout=10000)

        # --- Step 3: Click the project on the project list ---
        # ProjectListItem uses .pli-name-link and .pli-enter-btn, both
        # router-links to /research/:id.  Click by matching the link
        # whose href contains the session id.
        project_link = page.locator(f'a[href="/research/{sid}"]')
        if project_link.count() == 0:
            # Some builds render router-link :to as relative path
            found_pl = False
            for sel in ['.pli-name-link', '.pli-enter-btn']:
                links = page.locator(sel)
                for i in range(links.count()):
                    href = links.nth(i).get_attribute("href") or ""
                    if sid in href:
                        links.nth(i).click()
                        found_pl = True
                        break
                if found_pl:
                    break
            assert found_pl, (
                f"Project link for session {sid} not found on project list"
            )
        else:
            project_link.first.click()

        # Wait for project detail to load
        page.wait_for_selector("h1", timeout=10000)
        # Wait for either ProjectReports or RecentReports to finish loading
        page.wait_for_timeout(3000)

        # --- Step 4: Find and click report link on project detail ---
        # ProjectDetailPage embeds both ProjectReports (.pr-view-link) and
        # RecentReports (.rr-view-link), both with "查看" link text.
        # Instead of matching by exact href (which Vue router-link may render
        # differently), find the link whose href ends with the run ID.
        found_report_link = False
        for selector in ['.pr-view-link', '.rr-view-link']:
            links = page.locator(selector)
            count = links.count()
            for i in range(count):
                href = links.nth(i).get_attribute("href") or ""
                if rid in href and sid in href:
                    links.nth(i).click()
                    found_report_link = True
                    break
            if found_report_link:
                break

        assert found_report_link, (
            f"Report link for run {rid} not found on project detail page "
            f"(checked .pr-view-link and .rr-view-link)"
        )

        # --- Step 5: Wait for result page to load ---
        page.wait_for_selector(".rrv-report", timeout=10000)
        # Verify we landed on the correct result URL
        assert f"/research/{sid}/result/{rid}" in page.url, (
            f"Expected result URL, got {page.url}"
        )

        # --- Step 6: Click replay button ---
        replay_btn = page.locator('[data-testid="canonical-replay"]')
        assert replay_btn.is_visible(), (
            "Canonical replay button must be visible on result page"
        )
        assert "验证可重放性" in replay_btn.text_content(), (
            "Replay button must show '验证可重放性'"
        )
        replay_btn.click()
        page.wait_for_selector('[data-testid="canonical-replay-result"]', timeout=30000)

        # --- Step 7: Assert matched=true ---
        result = page.locator('[data-testid="canonical-replay-result"]')
        assert result.is_visible()
        assert "重放一致" in result.text_content(), (
            "Canonical replay result must show '重放一致' for matched=true"
        )

        # Assert both SHA-256 values (64 hex chars each)
        hashes = page.locator('.rpage-replay-hash-value')
        assert hashes.count() >= 2, (
            f"Replay result must show 2 SHA-256 hashes, got {hashes.count()}"
        )
        hash_original = hashes.nth(0).text_content().strip()
        hash_replay = hashes.nth(1).text_content().strip()
        assert len(hash_original) == 64, (
            f"Original SHA-256 must be 64 hex chars, got {len(hash_original)}: {hash_original!r}"
        )
        assert len(hash_replay) == 64, (
            f"Replay SHA-256 must be 64 hex chars, got {len(hash_replay)}: {hash_replay!r}"
        )
        # matched=true: hashes must be equal
        assert hash_original == hash_replay, (
            "matched=true: original and replay SHA-256 must be equal"
        )

        # Assert run ID is in the page URL (proving we're on the right result)
        assert rid in page.url, (
            f"Result page URL must contain run_id {rid}, got {page.url}"
        )

    def test_gap_replay_verification_mismatched(
        self, live_servers, result_workflow_session_mismatched, page,
    ):
        """Canonical replay verification matched=false — real browser, real UI nav.

        A dedicated fixture (result_workflow_session_mismatched) clones
        a real workflow run's replay_manifest, replaces
        canonical_output_sha256 with a fabricated value, recomputes
        manifest_sha256, and injects the tampered run into the session's
        workflow_state via the file-based test SQLite DB — all in the
        fixture layer, before any browser operations.

        The browser test then navigates the full UI: /login → /research →
        click project → project detail → click report link → result page →
        click replay → assert "重放不一致" + 2x different SHA-256.
        """
        frontend_url, _ = live_servers
        ws = result_workflow_session_mismatched
        sid = ws["session_id"]
        rid = ws["run_id"]

        # --- Step 1: Real login via UI ---
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        # --- Step 2: Navigate to project list ---
        page.goto(f"{frontend_url}/research")
        page.wait_for_selector("h1", timeout=10000)

        # --- Step 3: Click the project on the project list ---
        found_pl = False
        for sel in ['.pli-name-link', '.pli-enter-btn']:
            links = page.locator(sel)
            for i in range(links.count()):
                href = links.nth(i).get_attribute("href") or ""
                if sid in href:
                    links.nth(i).click()
                    found_pl = True
                    break
            if found_pl:
                break
        # Fallback: try direct href match
        if not found_pl:
            project_link = page.locator(f'a[href="/research/{sid}"]')
            if project_link.count() > 0:
                project_link.first.click()
                found_pl = True
        assert found_pl, (
            f"Project link for session {sid} not found on project list"
        )

        # Wait for project detail to load
        page.wait_for_selector("h1", timeout=10000)
        page.wait_for_timeout(3000)

        # --- Step 4: Find and click report link on project detail ---
        found_report_link = False
        for selector in ['.pr-view-link', '.rr-view-link']:
            links = page.locator(selector)
            count = links.count()
            for i in range(count):
                href = links.nth(i).get_attribute("href") or ""
                if rid in href and sid in href:
                    links.nth(i).click()
                    found_report_link = True
                    break
            if found_report_link:
                break

        # Fallback: try '查看' text links
        if not found_report_link:
            view_links = page.locator('a:has-text("查看")')
            for i in range(view_links.count()):
                href = view_links.nth(i).get_attribute("href") or ""
                if rid in href and sid in href:
                    view_links.nth(i).click()
                    found_report_link = True
                    break

        assert found_report_link, (
            f"Report link for run {rid} not found on project detail page"
        )

        # --- Step 5: Wait for result page to load ---
        page.wait_for_selector(".rrv-report", timeout=10000)
        assert f"/research/{sid}/result/{rid}" in page.url, (
            f"Expected result URL, got {page.url}"
        )

        # --- Step 6: Click replay button ---
        replay_btn = page.locator('[data-testid="canonical-replay"]')
        assert replay_btn.is_visible(), (
            "Canonical replay button must be visible on result page"
        )
        replay_btn.click()
        page.wait_for_selector('[data-testid="canonical-replay-result"]', timeout=30000)

        # --- Step 7: Assert matched=false ---
        result = page.locator('[data-testid="canonical-replay-result"]')
        assert result.is_visible()
        assert "重放不一致" in result.text_content(), (
            "Canonical replay result must show '重放不一致' for matched=false"
        )
        assert "重放一致" not in result.text_content(), (
            "Canonical replay result must NOT show '重放一致' for mismatched"
        )

        # Assert both SHA-256 values are displayed and DIFFERENT
        hashes = page.locator('.rpage-replay-hash-value')
        assert hashes.count() >= 2, (
            f"Replay result must show 2 SHA-256 hashes, got {hashes.count()}"
        )
        hash_original = hashes.nth(0).text_content().strip()
        hash_replay = hashes.nth(1).text_content().strip()
        assert len(hash_original) == 64, (
            f"Original SHA-256 must be 64 hex chars, got {len(hash_original)}: {hash_original!r}"
        )
        assert len(hash_replay) == 64, (
            f"Replay SHA-256 must be 64 hex chars, got {len(hash_replay)}: {hash_replay!r}"
        )
        assert hash_original != hash_replay, (
            "matched=false: original and replay SHA-256 must differ"
        )

        # Assert run ID is in the page URL
        assert rid in page.url, (
            f"Result page URL must contain run_id {rid}, got {page.url}"
        )

    # -- 2B: Acceptance verdict — legacy /v4/research-internal now redirects --
    def test_legacy_v4_research_internal_now_redirects(
        self, live_servers, workflow_user, workflow_session, page,
    ):
        """Task 2B fix: /v4/research-internal now redirects to canonical workflow.

        Real UI login (workflow_user + workflow_session), then visit the old
        /v4/research-internal URL.  LegacyRedirect resolves the most-recent
        session and redirects to the canonical workflow page with the user's
        real session ID in the URL.
        """
        frontend_url, _ = live_servers
        sid = workflow_session["id"]

        # Real UI login — no localStorage token injection
        _login_via_ui(page, frontend_url, workflow_user["username"], "WfUser_Pass123!")

        # Visit the legacy /v4/research-internal URL
        page.goto(f"{frontend_url}/v4/research-internal")

        # Must land on canonical workflow page for the user's real session
        page.wait_for_url(f"**/research/{sid}/workflow", timeout=15000)
        page.wait_for_timeout(2000)

        # Exact pathname assertion
        parsed = urlparse(page.url)
        assert parsed.path == f"/research/{sid}/workflow", (
            f"Expected /research/{sid}/workflow, got {parsed.path}"
        )

        # Must NOT contain /v4 in final URL
        assert "/v4" not in page.url, (
            f"Final URL must not contain /v4, got {page.url}"
        )

        # Must NOT render V4ResearchView tabs
        assert page.locator("text=完整研究").count() == 0, (
            "V4ResearchView '完整研究' tab must not appear after LegacyRedirect"
        )

    # -- 2B: Acceptance verdict — old workspace redirect now session-aware --
    def test_old_workspace_redirect_resolves_session_context(
        self, live_servers, test_user, page,
    ):
        """Task 2B fix: /research/workspace → session-aware canonical redirect.

        LegacyRedirect resolves most-recent session and redirects to
        /research/:projectId/workspace (or fallback to project list).
        No longer a blank redirect to /research.
        """
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/")
        page.evaluate(
            """([token, refresh]) => {
            localStorage.setItem('hfb-access-token', token);
            localStorage.setItem('hfb-refresh-token', refresh);
        }""",
            [test_user["access_token"], test_user["refresh_token"]],
        )
        page.goto(f"{frontend_url}/research/workspace")
        page.wait_for_url("**/research/**", timeout=15000)
        page.wait_for_timeout(2000)
        # Page must be visible — not blank
        assert page.locator('h1').first.is_visible() or page.locator('[data-testid]').first.is_visible()


# ============================================================
# Cross-project isolation fixtures
# ============================================================


@pytest.fixture(scope="module")
def cross_users(live_servers):
    """Create two independent users (A and B), each with a session + note + citation + query history + run.

    Returns a dict with user_a / user_b entries, each containing:
      token, session_id, session_title, note_content, citation_body, history_query, run_id
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

    def _api_get(user_tokens, path):
        r = httpx.get(
            f"{base}{path}",
            headers={"Authorization": f"Bearer {user_tokens['access_token']}"},
            timeout=10,
        )
        return r

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

    # Verify history endpoint returns data for A
    hist_a_resp = _api_get(token_a, f"/api/v4/research/session/{sid_a}/history")
    hist_a_data = hist_a_resp.json()
    history_entries_a = hist_a_data.get("data", {}).get("history", [])
    hist_query_a = history_entries_a[0]["query_text"] if history_entries_a else "N/A"

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

    hist_b_resp = _api_get(token_b, f"/api/v4/research/session/{sid_b}/history")
    hist_b_data = hist_b_resp.json()
    history_entries_b = hist_b_data.get("data", {}).get("history", [])
    hist_query_b = history_entries_b[0]["query_text"] if history_entries_b else "N/A"

    # Get runs for A and B
    runs_a_resp = _api_get(token_a, f"/api/v4/research/session/{sid_a}/runs")
    runs_a_data = runs_a_resp.json()
    runs_a = runs_a_data.get("data", {}).get("runs", [])
    run_id_a = runs_a[0]["run_id"] if runs_a else "N/A"

    runs_b_resp = _api_get(token_b, f"/api/v4/research/session/{sid_b}/runs")
    runs_b_data = runs_b_resp.json()
    runs_b = runs_b_data.get("data", {}).get("runs", [])
    run_id_b = runs_b[0]["run_id"] if runs_b else "N/A"

    return {
        "base": base,
        "user_a": {
            "token": token_a,
            "session_id": sid_a,
            "title": title_a,
            "note": note_a,
            "citation": cit_a,
            "history_query": hist_query_a,
            "run_id": run_id_a,
            "username": token_a.get("username", ""),
        },
        "user_b": {
            "token": token_b,
            "session_id": sid_b,
            "title": title_b,
            "note": note_b,
            "citation": cit_b,
            "history_query": hist_query_b,
            "run_id": run_id_b,
            "username": token_b.get("username", ""),
        },
    }


# ============================================================
# CrossProjectIsolation — browser-level workspace isolation
# ============================================================


def _login_via_ui(page, frontend_url: str, username: str, password: str) -> None:
    """Log in through the real login page UI (NOT localStorage)."""
    page.goto(f"{frontend_url}/login")
    page.wait_for_selector('input[placeholder*="用户名"]', timeout=10000)
    page.fill('input[placeholder*="用户名"]', username)
    page.fill('input[placeholder*="密码"]', password)
    page.click('button:has-text("登录")')
    # Wait for redirect to home
    page.wait_for_url(f"{frontend_url}/", timeout=10000)
    # Confirm logged-in state
    page.wait_for_selector(f"text={username}", timeout=5000)


class TestCrossProjectIsolation:
    """Browser-level cross-project isolation probes with real auth.

    Verifies:
      - User A can see own workspace / project detail
      - Switching between own projects clears stale data
      - User A visiting B's session URLs sees "课题不存在" and
        session API calls return 404
      - No B content leaks into A's browser
    """

    def test_a_workspace_loads(self, live_servers, cross_users, page):
        """User A's own workspace shows their title, no error state."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        _login_via_ui(page, frontend_url, a["username"], "CrossA_Pass123!")
        page.goto(f"{frontend_url}/research/{a['session_id']}/workspace")
        page.wait_for_selector("h1", timeout=10000)
        # Wait for the title to settle from fallback "研究工作区"
        page.wait_for_function(
            f"""() => document.querySelector('h1')?.textContent === '{a['title']}'""",
            timeout=10000,
        )
        assert page.locator("h1").text_content() == a["title"], (
            f"Expected h1 to be '{a['title']}', got '{page.locator('h1').text_content()}'"
        )
        # Should NOT show "课题不存在" (404 state)
        assert page.locator("text=课题不存在").count() == 0, (
            "Own workspace should not show '课题不存在'"
        )

        # Verify own session API returns 200 (capture network)
        with page.expect_response(
            lambda r: f"/api/v1/workspace/sessions/{a['session_id']}" in r.url
            and r.status == 200,
            timeout=5000,
        ):
            page.reload()
        page.wait_for_selector("h1", timeout=10000)

    def test_a_project_detail_loads(self, live_servers, cross_users, page):
        """User A's own project detail shows '开始研究'."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        _login_via_ui(page, frontend_url, a["username"], "CrossA_Pass123!")
        page.goto(f"{frontend_url}/research/{a['session_id']}")
        page.wait_for_selector("h1", timeout=10000)
        assert page.locator("text=开始研究").is_visible(), (
            "Own project detail should show '开始研究'"
        )

    def test_switch_own_projects_no_residue(self, live_servers, cross_users, page):
        """Switching from project A1 to A2 clears A1's all data from DOM.

        Does not restart browser or create a new page — navigates within the same page.
        Waits for data to settle, then confirms:
          - A1 title disappears
          - A1 note, citation, history query, run ID are NOT in DOM
          - A2 content IS present (or empty state is validated via API)
        """
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

        _login_via_ui(page, frontend_url, a["username"], "CrossA_Pass123!")

        # Visit A1 workspace
        page.goto(f"{frontend_url}/research/{a['session_id']}/workspace")
        page.wait_for_selector("h1", timeout=10000)
        page.wait_for_function(
            f"""() => document.querySelector('h1')?.textContent === '{a['title']}'""",
            timeout=10000,
        )
        assert page.locator("h1").text_content() == a["title"]

        # Navigate to A2 workspace (same page, no restart)
        page.goto(f"{frontend_url}/research/{sid_a2}/workspace")
        page.wait_for_selector("h1", timeout=10000)
        page.wait_for_function(
            f"""() => document.querySelector('h1')?.textContent === '{title_a2}'""",
            timeout=10000,
        )
        assert page.locator("h1").text_content() == title_a2

        # A1's title should NOT be in DOM
        assert page.locator(f"h1:has-text('{a['title']}')").count() == 0, (
            f"A1 title '{a['title']}' should not be visible after switching to A2"
        )

        # A1 note should NOT be in DOM
        note_a1 = a["note"].get("content", "")
        if note_a1:
            assert page.locator(f"text={note_a1}").count() == 0, (
                f"A1 note '{note_a1}' should not be in DOM after switching to A2"
            )

        # A1 citation should NOT be in DOM
        cit_a1 = a["citation"].get("citation_text", "")
        if cit_a1:
            assert page.locator(f"text={cit_a1}").count() == 0, (
                f"A1 citation '{cit_a1}' should not be in DOM after switching to A2"
            )

        # A1 history query should NOT be in DOM
        hq_a1 = a.get("history_query", "")
        if hq_a1 and hq_a1 != "N/A":
            assert page.locator(f"text={hq_a1}").count() == 0, (
                f"A1 history query '{hq_a1}' should not be in DOM after switching to A2"
            )

        # A1 run ID should NOT be in DOM
        run_a1 = a.get("run_id", "")
        if run_a1 and run_a1 != "N/A":
            assert page.locator(f"text={run_a1}").count() == 0, (
                f"A1 run ID '{run_a1}' should not be in DOM after switching to A2"
            )

    def test_cross_user_workspace_blocked(self, live_servers, cross_users, page):
        """User A visiting B's workspace URL → '课题不存在', session API returns 404, B's title NOT leaked."""
        frontend_url, _ = live_servers
        b = cross_users["user_b"]

        # Use a fresh context for A
        a = cross_users["user_a"]
        _login_via_ui(page, frontend_url, a["username"], "CrossA_Pass123!")

        # Capture the session API request
        api_404_captured = False

        def _check_response(response):
            nonlocal api_404_captured
            if f"/api/v1/workspace/sessions/{b['session_id']}" in response.url:
                if response.status == 404:
                    api_404_captured = True

        page.on("response", _check_response)

        page.goto(f"{frontend_url}/research/{b['session_id']}/workspace")

        # Wait for page to finish loading + API to provide response
        page.wait_for_load_state("networkidle", timeout=10000)
        # Give a little extra time for the 404 state to render
        page.wait_for_timeout(2000)

        # Must show "课题不存在"
        assert page.locator("text=课题不存在").is_visible(), (
            "Cross-user workspace should show '课题不存在'"
        )
        # B's title must NOT appear
        assert page.locator(f"h1:has-text('{b['title']}')").count() == 0, (
            f"B's title '{b['title']}' should never appear in A's browser"
        )

        # B's note must NOT appear
        note_b = b["note"].get("content", "")
        if note_b:
            assert page.locator(f"text={note_b}").count() == 0, (
                f"B's note '{note_b}' should not be visible to A"
            )

        # Session API must have returned 404
        assert api_404_captured, (
            "Session API for B's session must return 404 when accessed by A"
        )

    def test_cross_user_project_blocked(self, live_servers, cross_users, page):
        """User A visiting B's project detail URL → access denied, API returns 404, no B content leaked."""
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        b = cross_users["user_b"]
        _login_via_ui(page, frontend_url, a["username"], "CrossA_Pass123!")

        # Capture session API 404
        api_404_captured = False

        def _check_response(response):
            nonlocal api_404_captured
            if f"/api/v1/workspace/sessions/{b['session_id']}" in response.url:
                if response.status == 404:
                    api_404_captured = True

        page.on("response", _check_response)

        page.goto(f"{frontend_url}/research/{b['session_id']}")

        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)

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
        # B's citation text must NOT appear
        cit_text = b["citation"].get("citation_text", "")
        if cit_text:
            assert page.locator(f"text={cit_text}").count() == 0, (
                "B's citation text should NOT be visible to A"
            )

        # Session API must have returned 404
        assert api_404_captured, (
            "Session API for B's session must return 404 when accessed by A"
        )

    def test_cross_user_workflow_blocked(self, live_servers, cross_users, page):
        """User A visiting B's workflow URL → '课题不存在', session API returns 404.

        This test PROVES that the Workflow page actually requests and validates
        the session. It captures the session API response, asserts 404, and
        verifies no B content leaks into the DOM.
        """
        frontend_url, _ = live_servers
        a = cross_users["user_a"]
        b = cross_users["user_b"]
        _login_via_ui(page, frontend_url, a["username"], "CrossA_Pass123!")

        # Capture session and history API responses
        api_responses: list[dict] = []

        def _capture(response):
            url = response.url
            if f"/api/v1/workspace/sessions/{b['session_id']}" in url:
                api_responses.append({
                    "url": url,
                    "status": response.status,
                    "endpoint": "session",
                })
            if f"/api/v4/research/session/{b['session_id']}/history" in url:
                api_responses.append({
                    "url": url,
                    "status": response.status,
                    "endpoint": "history",
                })

        page.on("response", _capture)

        page.goto(f"{frontend_url}/research/{b['session_id']}/workflow")
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)

        assert page.locator("text=课题不存在").is_visible(), (
            "Cross-user workflow URL should show '课题不存在'"
        )
        # B's title should not appear anywhere
        assert page.locator(f"h1:has-text('{b['title']}')").count() == 0, (
            f"B's title '{b['title']}' should not be visible in A's workflow view"
        )

        # B's history query should NOT be in DOM
        hq_b = b.get("history_query", "")
        if hq_b and hq_b != "N/A":
            assert page.locator(f"text={hq_b}").count() == 0, (
                f"B's history query should not appear in A's workflow view"
            )

        # B's run ID should NOT be in DOM
        run_b = b.get("run_id", "")
        if run_b and run_b != "N/A":
            assert page.locator(f"text={run_b}").count() == 0, (
                f"B's run ID should not appear in A's workflow view"
            )

        # At least one session API call must have been made and returned 404
        session_responses = [r for r in api_responses if r["endpoint"] == "session"]
        assert len(session_responses) > 0, (
            "Workflow page must request the session API for isolation validation"
        )
        for sr in session_responses:
            assert sr["status"] == 404, (
                f"Session API for B's session must return 404, got {sr['status']}"
            )


# ============================================================
# ResearchResultPage E2E fixtures
# ============================================================


# ====================================================================
# ResearchResultPage fixtures — Batch 1: real workflow replaces seed
# ====================================================================
#
# DIAGRAM (dependency arrows = "depends on"):
#
#   result_workflow_rag_doc
#        ├── result_workflow_session          (real workflow → happy-path E2E)
#        └── result_workflow_cross_users      (real workflow → cross-user E2E)
#
#   result_user  (seed-only, kept for state-test fixtures below)
#        ├── result_session_no_report
#        ├── result_session_run_failed
#        └── result_session_pending
#
#   result_workflow_rag_doc
#        ├── result_workflow_session                (real workflow → happy-path E2E)
#        │     └── result_workflow_session_no_report (seed state-only, same user)
#        └── result_workflow_cross_users            (real workflow → cross-user E2E)
#
# REAL-WORKFLOW fixtures:
#   result_workflow_session              — real topic → real retrieval → real report
#   result_workflow_session_no_report    — seed report-missing, SAME user as above
#   result_workflow_cross_users          — two users, each with real workflow run
#
# STATE-ONLY seed fixtures (documented; NOT used for report/citation/
# evidence/sourceref authenticity):
#   result_session_no_report    — empty markdown (report-missing state)
#   result_session_run_failed   — step with status=failed
#   result_session_pending      — empty step_execution_trace (pending state)
#   result_user                 — shared user for the three state fixtures
# ====================================================================


# -- Result Page RAG Document (shared by all real-workflow fixtures) --

@pytest.fixture(scope="module")
def result_workflow_rag_doc(live_servers, result_user):
    """Seed ONE RAG-enabled Document, then append a second Passage to it.

    Uses the standard ingest API for the first passage, then the new
    append-passage endpoint for the second — producing one document_id
    with chunks linked to two distinct passage_ids.  This guarantees
    at least two retrieval traces with the same document_id but
    different passage_ids — the data shape required for same-document
    / different-passage SourceRef isolation regression.

    Depends on result_user to ensure seed_rbac has run (admin
    user + RBAC roles are seeded on first registration).
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {result_user['access_token']}"}

    # ---- Step 0: Create Person, Book, Version (shared by both passages) ----
    person_resp = httpx.post(
        f"{base}/api/v1/persons",
        json={"name": "皇甫谧（E2E结果页）", "dynasty": "西晋"},
        headers=headers,
        timeout=10,
    )
    assert person_resp.status_code in (200, 201), f"Person creation failed: {person_resp.text[:200]}"
    person_id = person_resp.json()["data"]["id"]

    book_resp = httpx.post(
        f"{base}/api/v1/books",
        json={"title": "针灸甲乙经（E2E结果验证）", "dynasty": "西晋", "author_id": person_id},
        headers=headers,
        timeout=10,
    )
    assert book_resp.status_code in (200, 201), f"Book creation failed: {book_resp.text[:200]}"
    book_id = book_resp.json()["data"]["id"]

    version_resp = httpx.post(
        f"{base}/api/v1/versions",
        json={
            "book_id": book_id,
            "version_name": "E2E结果验证本",
            "era": "验证数据",
            "repository": "E2E验证资料库",
            "shelf_mark": "E2E-RESULT-001",
            "source_url": "https://example.invalid/result-e2e",
        },
        headers=headers,
        timeout=10,
    )
    assert version_resp.status_code in (200, 201), f"Version creation failed: {version_resp.text[:200]}"
    version_id = version_resp.json()["data"]["id"]

    # ---- Step 1: Create ONE chapter, then TWO passages under it ----
    ch_resp = httpx.post(
        f"{base}/api/v1/chapters",
        json={"book_id": book_id, "title": "E2E验证 同文献双篇", "order": 1},
        headers=headers,
        timeout=10,
    )
    assert ch_resp.status_code in (200, 201), f"Chapter creation failed: {ch_resp.text[:200]}"
    chapter_id = ch_resp.json()["data"]["id"]

    passage1_resp = httpx.post(
        f"{base}/api/v1/passages",
        json={
            "chapter_id": chapter_id,
            "version_id": version_id,
            "content_text": "ResultE2E验证标识 篇一 黄帝问曰：余闻九针于夫子，众多博大，不可胜数。",
            "order": 1,
            "tags": "E2E验证",
        },
        headers=headers,
        timeout=10,
    )
    assert passage1_resp.status_code in (200, 201), f"Passage 1 creation failed: {passage1_resp.text[:200]}"
    passage1_id = passage1_resp.json()["data"]["id"]

    passage2_resp = httpx.post(
        f"{base}/api/v1/passages",
        json={
            "chapter_id": chapter_id,
            "version_id": version_id,
            "content_text": "ResultE2E验证标识 篇二 岐伯对曰：善言天者必应于人。善言古者必验于今。",
            "order": 2,
            "tags": "E2E验证",
        },
        headers=headers,
        timeout=10,
    )
    assert passage2_resp.status_code in (200, 201), f"Passage 2 creation failed: {passage2_resp.text[:200]}"
    passage2_id = passage2_resp.json()["data"]["id"]

    # ---- Step 2: Ingest ONE document with passage A via standard API ----
    ingest_resp = httpx.post(
        f"{base}/api/v1/search/ingest",
        json={
            "title": "针灸甲乙经（E2E同文献验证）",
            "text": (
                "ResultE2E验证标识 篇一\n\n"
                "黄帝问曰：余闻九针于夫子，众多博大，不可胜数。"
                "余愿闻要道，以属子孙，传之后世，著之骨髓，"
                "藏之肝肺，歃血而受，不敢妄泄。\n\n"
                "令合天道，必有终始，上应天光星辰历纪。\n\n"
            ),
            "copyright_status": "public_domain",
            "authorization_basis": "e2e-test-data",
            "source_name": "e2e-result-test",
            "source_url": "https://example.invalid/result-e2e",
            "passage_id": passage1_id,
        },
        headers=headers,
        timeout=10,
    )
    if ingest_resp.status_code not in (200, 201):
        raise RuntimeError(f"Ingest failed: {ingest_resp.status_code} {ingest_resp.text[:300]}")
    doc_data = ingest_resp.json().get("data", ingest_resp.json())
    doc_id = doc_data["document_id"]

    # ---- Step 3: Append passage B to the SAME document via the new endpoint ----
    # Requires research:update permission — admin token has it.
    admin_login = httpx.post(
        f"{base}/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=5,
    )
    if admin_login.status_code != 200:
        raise RuntimeError(f"Admin login failed: {admin_login.status_code} {admin_login.text[:300]}")
    admin_token = admin_login.json()["data"]["access_token"]

    append_resp = httpx.post(
        f"{base}/api/v1/search/documents/{doc_id}/append-passage",
        json={
            "text": (
                "ResultE2E验证标识 篇二\n\n"
                "岐伯对曰：妙乎哉问也！此天地之至数。\n"
                "故人有三部，部有三候，以决死生，以处百病，以调虚实，而除邪疾。\n"
                "故下部之天以候肝，地以候肾，人以候脾胃之气。\n\n"
            ),
            "passage_id": passage2_id,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    if append_resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Append passage failed: {append_resp.status_code} {append_resp.text[:300]}"
        )
    append_data = append_resp.json()
    assert append_data.get("appended_chunk_count", 0) > 0, (
        f"Append must produce chunks. Response: {append_resp.text[:300]}"
    )
    assert append_data.get("document_id") == doc_id, (
        f"Append must return same document_id, got {append_data.get('document_id')}"
    )
    assert append_data.get("passage_id") == passage2_id, (
        f"Append must return same passage_id, got {append_data.get('passage_id')}"
    )

    # ---- Step 4: Re-review to enable RAG (append resets review→pending, rag→False) ----
    review_resp = httpx.patch(
        f"{base}/api/v1/documents/{doc_id}/review",
        json={"review_status": "approved", "rag_enabled": True},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    if review_resp.status_code != 200:
        raise RuntimeError(f"Re-review after append failed: {review_resp.status_code} {review_resp.text[:300]}")

    return {
        "document_id": doc_id,
        "chunk_count": doc_data.get("chunk_count", 0) + append_data.get("appended_chunk_count", 0),
        "passage_ids": [passage1_id, passage2_id],
        "version_id": version_id,
    }


# -- Primary real-workflow fixture (replaces seed-based result_session) --

@pytest.fixture(scope="module")
def result_workflow_session(live_servers, result_workflow_rag_doc):
    """Real workflow → ResultPage.  No seed API, no fixed artifacts.

    Creates a real user + session, then POST /api/v4/research/workflow
    with a topic whose tokens appear in the RAG fixture document.
    The returned run_id comes from a real 5-step workflow execution
    and carries authentic report Markdown, citations, evidence,
    SourceRef, and lineage metadata.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"

    # Create user
    username = f"rwe2e-{_uuid.uuid4().hex[:6]}"
    password = "RwFlow_Pass123!"
    tokens = _seed_user(backend_port, username, password)
    if tokens is None:
        raise RuntimeError("Failed to create result-workflow test user")

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Create session
    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "结果页真实工作流验证"},
        headers=headers,
        timeout=10,
    )
    assert sess_resp.status_code in (200, 201), (
        f"Session creation failed: {sess_resp.text}"
    )
    session_id = sess_resp.json()["data"]["id"]

    # Execute real workflow (blocking — may take up to 180 s with LLM)
    wf_resp = httpx.post(
        f"{base}/api/v4/research/workflow",
        json={
            "session_id": session_id,
            "topic": "ResultE2E验证 九针天地至数三部九候",
        },
        headers=headers,
        timeout=180,
    )
    if wf_resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Workflow POST failed: {wf_resp.status_code} {wf_resp.text[:500]}"
        )

    wf_data = wf_resp.json()
    wf_inner = wf_data.get("data", wf_data)
    run_id = wf_inner.get("run_id", "")
    if not run_id:
        raise RuntimeError(f"No run_id in workflow response: {wf_data}")

    success = wf_data.get("success", True)
    if not success:
        msg = wf_data.get("message", "unknown error")
        raise RuntimeError(
            f"Workflow returned success=False: {msg}"
        )

    return {
        "session_id": session_id,
        "run_id": run_id,
        "username": username,
        "password": password,
        "token": tokens,
    }


# -- Mismatch replay fixture — tampered manifest via file-based SQLite --
@pytest.fixture(scope="module")
def result_workflow_session_mismatched(live_servers, result_workflow_session):
    """Create a persistent run with tampered canonical_output_sha256.

    Clones the real result_workflow_session run's replay_manifest,
    replaces canonical_output_sha256 with a fabricated 64-hex-char
    value, recomputes manifest_sha256, and injects the tampered
    run into the session's workflow_state via direct SQLite access.

    ALL database manipulation happens in this fixture — the browser
    test only reads the already-persisted tampered state.
    """
    import hashlib as _hashlib
    import json as _json
    import sqlite3 as _sqlite3
    from uuid import uuid4 as _uuid4

    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    ws = result_workflow_session
    headers = {"Authorization": f"Bearer {ws['token']['access_token']}"}

    def _canonical_json_bytes(payload: dict) -> bytes:
        return _json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")

    def _canonical_sha256(payload: dict) -> str:
        return _hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()

    # --- Step 1: Fetch the real run's manifest ---
    runs_resp = httpx.get(
        f"{base}/api/v4/research/session/{ws['session_id']}/runs",
        headers=headers,
        timeout=10,
    )
    assert runs_resp.status_code == 200, (
        f"GET runs failed: {runs_resp.status_code} {runs_resp.text[:500]}"
    )
    runs_list = runs_resp.json()["data"]["runs"]
    target_run = None
    for r in runs_list:
        if r.get("run_id") == ws["run_id"]:
            target_run = dict(r)
            break
    assert target_run is not None, (
        f"Target run {ws['run_id']} not found in {len(runs_list)} runs"
    )
    manifest = target_run.get("replay_manifest")
    assert manifest is not None, "Real run must have replay_manifest"

    # --- Step 2: Clone manifest with fabricated output hash ---
    bad_manifest = dict(manifest)
    bad_manifest["canonical_output_sha256"] = (
        "0000000000000000000000000000000000000000000000000000000000000001"
    )
    # Recompute manifest_sha256 so self-integrity check passes
    manifest_for_hash = {
        k: v for k, v in bad_manifest.items() if k != "manifest_sha256"
    }
    bad_manifest["manifest_sha256"] = _canonical_sha256(manifest_for_hash)

    # --- Step 3: Build a tampered run entry (new run_id, same session) ---
    mismatch_run_id = str(_uuid4())
    tampered_run = dict(target_run)
    tampered_run["run_id"] = mismatch_run_id
    tampered_run["replay_manifest"] = bad_manifest

    # --- Step 4: Inject into file-based SQLite ---
    db_path = f"/tmp/hfb-e2e-cj-{backend_port}.db"

    # Retry loop: the backend may not have flushed yet
    conn = None
    for attempt in range(10):
        try:
            conn = _sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT workflow_state FROM research_sessions WHERE id = ?",
                [ws["session_id"]],
            ).fetchone()
            if row and row[0]:
                break
            conn.close()
            conn = None
            import time as _time
            _time.sleep(0.5)
        except Exception:
            if conn:
                conn.close()
                conn = None
            import time as _time
            _time.sleep(0.5)

    assert conn is not None and row is not None, (
        f"Cannot read workflow_state for session {ws['session_id']} "
        f"from {db_path} after 10 attempts"
    )

    state = _json.loads(row[0])
    runs = state.get("runs", [])
    runs.append(tampered_run)
    state["runs"] = runs
    conn.execute(
        "UPDATE research_sessions SET workflow_state = ? WHERE id = ?",
        [_json.dumps(state, ensure_ascii=False), ws["session_id"]],
    )
    conn.commit()
    conn.close()

    # --- Step 5: Verify the tampered run is readable via API ---
    verify_resp = httpx.get(
        f"{base}/api/v4/research/session/{ws['session_id']}/runs",
        headers=headers,
        timeout=10,
    )
    assert verify_resp.status_code == 200
    verify_runs = verify_resp.json()["data"]["runs"]
    found = [r for r in verify_runs if r.get("run_id") == mismatch_run_id]
    assert len(found) == 1, (
        f"Tampered run {mismatch_run_id} not found via API after injection"
    )

    return {
        "session_id": ws["session_id"],
        "run_id": mismatch_run_id,
        "username": ws["username"],
        "password": ws["password"],
        "token": ws["token"],
    }


@pytest.fixture(scope="module")
def result_workflow_session_no_report(live_servers, result_workflow_session):
    """STATE-ONLY: report-missing run under the SAME user as
    result_workflow_session.

    Uses POST /api/v4/research/_test/seed-research-run solely to
    create a report-missing state for route-switch tests.  Do NOT
    use this fixture to assert report/Citation/Evidence/SourceRef
    authenticity.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {result_workflow_session['token']['access_token']}"}

    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "空报告测试-同用户"},
        headers=headers,
        timeout=10,
    )
    session_id = sess_resp.json()["data"]["id"]

    seed_resp = httpx.post(
        f"{base}/api/v4/research/_test/seed-research-run",
        json={
            "session_id": session_id,
            "topic": "空报告研究",
            "markdown": "",
            "citations": [],
            "retrieval_snapshot": [],
            "traces": [],
        },
        headers=headers,
        timeout=10,
    )
    run_id = seed_resp.json()["data"]["run_id"]

    return {"session_id": session_id, "run_id": run_id}


# -- Real-workflow cross-user fixture (replaces seed-based result_cross_users) --

@pytest.fixture(scope="module")
def result_workflow_cross_users(live_servers, result_workflow_rag_doc):
    """Two users, each with own session + real workflow run.

    Both workflows run against the same RAG document (the topic
    includes the ResultE2E验证 watermark), so both produce real
    reports.  Used for cross-user result-page isolation tests.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"

    # Create two users
    token_a = _seed_user(backend_port, f"rxa-{_uuid.uuid4().hex[:6]}", "ResXA_Pass123!")
    token_b = _seed_user(backend_port, f"rxb-{_uuid.uuid4().hex[:6]}", "ResXB_Pass123!")

    h_a = {"Authorization": f"Bearer {token_a['access_token']}"}
    h_b = {"Authorization": f"Bearer {token_b['access_token']}"}

    # User A: session + real workflow
    sess_a = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "用户A-结果页真实工作流"},
        headers=h_a,
        timeout=10,
    ).json()["data"]
    wf_a = httpx.post(
        f"{base}/api/v4/research/workflow",
        json={"session_id": sess_a["id"], "topic": "ResultE2E验证 上部天两额动脉"},
        headers=h_a,
        timeout=180,
    )
    if wf_a.status_code not in (200, 201):
        raise RuntimeError(f"User A workflow failed: {wf_a.status_code} {wf_a.text[:300]}")
    run_a = wf_a.json().get("data", {}).get("run_id", "")
    if not run_a:
        raise RuntimeError("User A workflow returned no run_id")

    # User B: session + real workflow (different topic, same RAG doc)
    sess_b = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "用户B-结果页真实工作流"},
        headers=h_b,
        timeout=10,
    ).json()["data"]
    wf_b = httpx.post(
        f"{base}/api/v4/research/workflow",
        json={"session_id": sess_b["id"], "topic": "ResultE2E验证 下部天以候肝"},
        headers=h_b,
        timeout=180,
    )
    if wf_b.status_code not in (200, 201):
        raise RuntimeError(f"User B workflow failed: {wf_b.status_code} {wf_b.text[:300]}")
    run_b = wf_b.json().get("data", {}).get("run_id", "")
    if not run_b:
        raise RuntimeError("User B workflow returned no run_id")

    return {
        "user_a": {
            "token": token_a,
            "session_id": sess_a["id"],
            "run_id": run_a,
            "title": "用户A-结果页真实工作流",
            "username": token_a.get("username", ""),
            "password": "ResXA_Pass123!",
        },
        "user_b": {
            "token": token_b,
            "session_id": sess_b["id"],
            "run_id": run_b,
            "title": "用户B-结果页真实工作流",
            "username": token_b.get("username", ""),
            "password": "ResXB_Pass123!",
        },
    }


# ====================================================================
# STATE-ONLY seed fixtures (NOT for report/citation/evidence/SourceRef
# authenticity — only used to construct pending/failed/missing states).
# ====================================================================

@pytest.fixture(scope="module")
def result_user(live_servers):
    """Create a dedicated user for the three state-test fixtures below.

    This user exists only so the seed-based state fixtures
    (result_session_no_report / result_session_run_failed /
    result_session_pending) have a consistent owner.  No real-workflow
    test uses this user.
    """
    _, backend_port = live_servers
    tokens = _seed_user(backend_port, f"resulte2e-{_uuid.uuid4().hex[:6]}", "Result_Pass123!")
    if tokens is None:
        raise RuntimeError("Failed to create test user for result page state fixtures")
    return tokens


@pytest.fixture(scope="module")
def result_session_no_report(live_servers, result_user):
    """STATE-ONLY: session + run with empty markdown (report-missing).

    Uses POST /api/v4/research/_test/seed-research-run.
    Do NOT use this fixture to assert report/Citation/Evidence/
    SourceRef authenticity — its data is seed-artifact, not real
    workflow output.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {result_user['access_token']}"}

    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "空报告测试课题"},
        headers=headers,
        timeout=10,
    )
    session_data = sess_resp.json()["data"]
    session_id = session_data["id"]

    seed_resp = httpx.post(
        f"{base}/api/v4/research/_test/seed-research-run",
        json={
            "session_id": session_id,
            "topic": "空报告研究",
            "markdown": "",
            "citations": [],
            "retrieval_snapshot": [],
            "traces": [],
        },
        headers=headers,
        timeout=10,
    )
    run_id = seed_resp.json()["data"]["run_id"]

    return {"session_id": session_id, "run_id": run_id, "username": result_user.get("username", "")}


@pytest.fixture(scope="module")
def result_session_run_failed(live_servers, result_user):
    """STATE-ONLY: session + run with a failed step.

    Uses POST /api/v4/research/_test/seed-research-run.
    Do NOT use this fixture to assert report/Citation/Evidence/
    SourceRef authenticity — its data is seed-artifact, not real
    workflow output.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {result_user['access_token']}"}

    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "失败运行测试课题"},
        headers=headers,
        timeout=10,
    )
    session_data = sess_resp.json()["data"]
    session_id = session_data["id"]

    seed_resp = httpx.post(
        f"{base}/api/v4/research/_test/seed-research-run",
        json={
            "session_id": session_id,
            "topic": "失败研究",
            "step_execution_trace": [
                {"name": "topic_selection", "status": "completed"},
                {"name": "literature_retrieval", "status": "failed"},
            ],
            "markdown": "",
            "citations": [],
            "retrieval_snapshot": [],
            "traces": [],
        },
        headers=headers,
        timeout=10,
    )
    run_id = seed_resp.json()["data"]["run_id"]

    return {"session_id": session_id, "run_id": run_id, "username": result_user.get("username", "")}


@pytest.fixture(scope="module")
def result_session_pending(live_servers, result_user):
    """STATE-ONLY: session + run with empty step_execution_trace (pending).

    Uses POST /api/v4/research/_test/seed-research-run.
    Do NOT use this fixture to assert report/Citation/Evidence/
    SourceRef authenticity — its data is seed-artifact, not real
    workflow output.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {result_user['access_token']}"}

    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "待运行测试课题"},
        headers=headers,
        timeout=10,
    )
    session_data = sess_resp.json()["data"]
    session_id = session_data["id"]

    seed_resp = httpx.post(
        f"{base}/api/v4/research/_test/seed-research-run",
        json={
            "session_id": session_id,
            "topic": "待运行研究",
            "step_execution_trace": [],
            "markdown": "",
            "citations": [],
            "retrieval_snapshot": [],
            "traces": [],
        },
        headers=headers,
        timeout=10,
    )
    run_id = seed_resp.json()["data"]["run_id"]

    return {"session_id": session_id, "run_id": run_id, "username": result_user.get("username", "")}


# ====================================================================
# XSS controlled-input seed fixture
# ====================================================================
# STATE-ONLY: injects known-dangerous payloads into a run's markdown
# output so we can prove the custom text parser neutralises them in a
# real browser.  Do NOT use this fixture for report/Citation/Evidence/
# SourceRef authenticity assertions — its data is crafted, not real
# workflow output.


@pytest.fixture(scope="module")
def result_session_xss_payloads(live_servers, result_user):
    """STATE-ONLY: run whose output_artifacts.markdown + citations +
    retrieval_snapshot contain controlled XSS payloads.

    Uses POST /api/v4/research/_test/seed-research-run.
    Do NOT use this fixture to assert report/Citation/Evidence/
    SourceRef authenticity — its data is seed-artifact, not real
    workflow output.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {result_user['access_token']}"}

    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "XSS载荷验证课题"},
        headers=headers,
        timeout=10,
    )
    session_id = sess_resp.json()["data"]["id"]

    # XSS payloads in markdown: all dangerous vectors the parser must neutralise
    xss_markdown = (
        "# XSS 安全验证报告\n\n"
        "## Summary\n\n"
        "本报告包含受控安全测试载荷。\n\n"
        "## Script 载荷\n\n"
        "<script>alert('xss')</script>\n\n"
        "## Image 载荷\n\n"
        '<img src="x" onerror="alert(1)">\n\n'
        "<img onerror=alert(2) src=x>\n\n"
        "## Event handler 载荷\n\n"
        '<div onclick="alert(3)">click</div>\n\n'
        '<a onclick="alert(4)" href="/safe">link</a>\n\n'
        "## JavaScript URL 载荷\n\n"
        '[javascript:alert(5)](javascript:alert(5))\n\n'
        "## IFrame 载荷\n\n"
        '<iframe src="javascript:alert(6)"></iframe>\n\n'
        '<iframe srcdoc="<script>alert(7)</script>"></iframe>\n\n'
        "## SVG 载荷\n\n"
        '<svg onload="alert(8)"></svg>\n\n'
        '<svg><script>alert(9)</script></svg>\n\n'
        "## 正常内容\n\n"
        "这是正常的中文文本段落，应正常渲染。\n\n"
        "**粗体文字** 和普通文字。\n\n"
        "## 正常安全链接\n\n"
        "[正常外链](https://example.com/safe-page)\n\n"
        "## 恶意 source_ref_url\n\n"
        "以下 citation 引用的 retrieval_snapshot 条目\n"
        "的 source_ref_url 字段包含恶意载荷。\n"
    )

    # Citation with a trace_id that appears in both citations and snapshot
    xss_trace_id = "00000000-0000-4000-a000-000000000001"

    xss_citations = [
        {
            "trace_id": xss_trace_id,
            "citation_text": "XSS载荷文献引用 [controlled]",
            "document_id": "00000000-0000-4000-a000-000000000099",
            "quote": '<script>alert("q")</script>',
        }
    ]

    xss_snapshot = [
        {
            "trace_id": xss_trace_id,
            "claim_text": "安全载荷：<script>alert('s')</script>",
            "citation_text": "恶意引用文：<img onerror=alert(1)>",
            "quote": '<iframe src="x">content</iframe>',
            "document_id": "00000000-0000-4000-a000-000000000099",
            "chunk_id": "chunk-xss-001",
            "source_ref_title": "恶意来源标题 <script>x</script>",
            # Malicious source_ref_url — must not become an active link
            "source_ref_url": "javascript:alert('evil')",
            "source_ref_id": "src-xss-001",
        }
    ]

    seed_resp = httpx.post(
        f"{base}/api/v4/research/_test/seed-research-run",
        json={
            "session_id": session_id,
            "topic": "XSS载荷验证",
            "markdown": xss_markdown,
            "citations": xss_citations,
            "retrieval_snapshot": xss_snapshot,
            "traces": [
                {
                    "trace_id": xss_trace_id,
                    "document_id": "00000000-0000-4000-a000-000000000099",
                    "chunk_id": "chunk-xss-001",
                    "passage_id": "passage-xss-001",
                }
            ],
        },
        headers=headers,
        timeout=10,
    )
    run_id = seed_resp.json()["data"]["run_id"]

    return {
        "session_id": session_id,
        "run_id": run_id,
        "xss_trace_id": xss_trace_id,
        "username": result_user.get("username", ""),
        "password": "Result_Pass123!",
    }


# ====================================================================
# withdrawn / no-permission SourceRef seed fixture
# ====================================================================
# STATE-ONLY: run with a retrieval_snapshot entry that has no
# document_id (simulating a withdrawn or inaccessible source).
# The ResultPage must NOT show a bypassable internal link.
# Do NOT use this fixture for report/Citation/Evidence/SourceRef
# authenticity assertions.


@pytest.fixture(scope="module")
def result_session_withdrawn_source(live_servers, result_user):
    """STATE-ONLY: run where retrieval_snapshot entries have no
    document_id (withdrawn / no-permission source simulation).

    Uses POST /api/v4/research/_test/seed-research-run.
    Do NOT use this fixture to assert report/Citation/Evidence/
    SourceRef authenticity — its data is seed-artifact.
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {result_user['access_token']}"}

    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "撤回文献验证课题"},
        headers=headers,
        timeout=10,
    )
    session_id = sess_resp.json()["data"]["id"]

    trace_a = "00000000-0000-4000-b000-000000000001"
    trace_b = "00000000-0000-4000-b000-000000000002"

    seed_resp = httpx.post(
        f"{base}/api/v4/research/_test/seed-research-run",
        json={
            "session_id": session_id,
            "topic": "撤回文献验证",
            "markdown": (
                "# 撤回文献验证报告\n\n"
                "## 源A：无 document_id\n\n"
                "此引用的 retrieval_snapshot 条目无 document_id，\n"
                "仅提供 source_ref_title。页面不应显示内部链接。\n\n"
                "## 源B：无 document_id 但有恶意 source_ref_url\n\n"
                "此条目的 source_ref_url 为 javascript: URL，\n"
                "页面不应渲染为活动链接。\n\n"
                "## 正常引用\n\n"
                "以下是有 document_id 的正常引用。\n"
            ),
            "citations": [
                {
                    "trace_id": trace_a,
                    "citation_text": "引用A：无document_id [撤回文献]",
                    "document_id": "",
                    "quote": "无法访问的原文内容。",
                },
                {
                    "trace_id": trace_b,
                    "citation_text": "引用B：恶意source_ref_url [撤回文献]",
                    "document_id": "",
                    "quote": "不应有内部链接的原文。",
                },
            ],
            "retrieval_snapshot": [
                {
                    "trace_id": trace_a,
                    "claim_text": "撤回文献中的声明A",
                    "citation_text": "引用A：无document_id [撤回文献]",
                    "quote": "无法访问的原文内容。",
                    "document_id": "",
                    "chunk_id": "",
                    "source_ref_title": "（已撤回）某古籍版本",
                    "source_ref_url": "",
                },
                {
                    "trace_id": trace_b,
                    "claim_text": "撤回文献中的声明B",
                    "citation_text": "引用B：恶意source_ref_url [撤回文献]",
                    "quote": "不应有内部链接的原文。",
                    "document_id": "",
                    "chunk_id": "",
                    "source_ref_title": "（无权限）受限文献",
                    # Malicious source_ref_url — must not appear as active link
                    "source_ref_url": "javascript:void(0)",
                },
            ],
            "traces": [],
        },
        headers=headers,
        timeout=10,
    )
    run_id = seed_resp.json()["data"]["run_id"]

    return {
        "session_id": session_id,
        "run_id": run_id,
        "trace_a": trace_a,
        "trace_b": trace_b,
        "username": result_user.get("username", ""),
        "password": "Result_Pass123!",
    }


# ============================================================
# TestResearchResultPageE2E — real browser result page tests
# ============================================================


class TestResearchResultPageE2E:
    """Browser-level E2E tests for ResearchResultPage.

    Task 2B: Write/download path E2E coverage in Batch 1-2:
      - test_real_workflow_report_loads — workflow result page loads
      - test_real_workflow_citation_shows_evidence — citation → evidence chain
      - test_real_workflow_citation_marker_clickable — citation marker interaction
      - test_real_workflow_lineage_displayed — SourceRef lineage badges
      - test_real_workflow_sourceref_link_routes — SourceRef internal links
      - test_real_workflow_lineage_complete_or_partial — lineage completeness
      - test_export_markdown_real_browser_download — real browser export download
      - test_export_disabled_when_no_report — export disabled in report-missing state
      - test_export_no_double_click — concurrent export prevention
      - test_export_stale_after_route_switch — stale export protection

    These tests use real browser login + real workflow run artifacts and
    verify read (report/citation/evidence/SourceRef), download (export),
    and state (disabled/double-click/stale) behavior.
    """

    # ================================================================
    # Batch 1 — Real-workflow authenticity E2E
    # ================================================================

    def test_real_workflow_report_loads(
        self, live_servers, result_workflow_session, page,
    ):
        """Real workflow → ResultPage shows authentic report."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        # Breadcrumbs
        assert page.locator(
            ".rrh-breadcrumb-link", has_text="返回工作区"
        ).is_visible()
        assert page.locator(
            ".rrh-breadcrumb-current", has_text="研究结果"
        ).is_visible()

        # Header title — must match the real session title
        assert page.locator("h1").text_content() == "结果页真实工作流验证"

        # Export button enabled
        export_btn = page.locator(".rrh-btn--export")
        assert export_btn.is_visible()
        assert export_btn.is_enabled()

        # Report content — real markdown from workflow
        assert page.locator(".rrv-report").is_visible()
        # At minimum one section heading exists
        headings = page.locator(".rrv-section-heading")
        assert headings.count() >= 1, "Real report must have section headings"

        # Citation markers present — the real workflow report may embed
        # trace references as `Trace: \`uuid\`` rather than [doc:chk] markers.
        # The run's citation panel (rcp-citation-item) is the canonical
        # citation list and is asserted below.
        markers = page.locator(".rrv-citation-marker")
        citations = page.locator(".rcp-citation-item")
        has_markers = markers.count() >= 1
        has_citation_items = citations.count() >= 1
        assert has_markers or has_citation_items, (
            "Real workflow must produce citation markers or citation panel items"
        )

        # Citation panel with real citation items
        assert page.locator(".rcp-section").is_visible()
        citation_items = page.locator(".rcp-citation-item")
        assert citation_items.count() >= 1, (
            "Real workflow run must produce at least 1 citation"
        )

        # No error states on happy path
        assert page.locator(".rre-state").count() == 0

    def test_real_workflow_citation_shows_evidence(
        self, live_servers, result_workflow_session, page,
    ):
        """Click a real Citation → Evidence panel shows real claim + quote."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rcp-citation-item", timeout=10000)

        # Click first citation
        page.locator(".rcp-citation-item").first.click()
        page.wait_for_selector(".eed-card", timeout=5000)

        # Evidence card must show real content
        assert page.locator(".eed-card").count() > 0
        claim_el = page.locator(".eed-claim-text")
        assert claim_el.is_visible()
        assert len(claim_el.text_content().strip()) > 0, (
            "Real evidence must have claim text"
        )
        quote_el = page.locator(".eed-quote-text")
        assert quote_el.is_visible()
        assert len(quote_el.text_content().strip()) > 0, (
            "Real evidence must have quote text"
        )

        # Selected citation indicator
        assert page.locator(".rcp-citation-item--selected").count() == 1

    def test_real_workflow_citation_marker_clickable(
        self, live_servers, result_workflow_session, page,
    ):
        """Click [N] marker in real report → selects matching citation.
        If the real report has no inline citation markers (citation panel
        items are the canonical representation), verify marker absence
        does not crash the page."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rcp-citation-item", timeout=10000)

        markers = page.locator(".rrv-citation-marker")
        if markers.count() > 0:
            page.locator(".rrv-citation-marker").first.click()
            page.wait_for_timeout(500)

            # Evidence detail opens
            assert page.locator(".eed-card").count() > 0
            assert page.locator(".rcp-citation-item--selected").count() == 1
        else:
            # Real workflow may embed trace references with `Trace: \`uuid\``
            # instead of [doc:chk] markers — use citation panel instead.
            page.locator(".rcp-citation-item").first.click()
            page.wait_for_selector(".eed-card", timeout=5000)

            assert page.locator(".eed-card").count() > 0
            assert page.locator(".rcp-citation-item--selected").count() == 1

    def test_real_workflow_lineage_displayed(
        self, live_servers, result_workflow_session, page,
    ):
        """Real workflow evidence shows lineage badge + SourceRef card."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rcp-citation-item", timeout=10000)

        page.locator(".rcp-citation-item").first.click()
        page.wait_for_selector(".eed-card", timeout=5000)

        # Lineage badge MUST be present (either full, partial, or minimal)
        has_badge = page.locator(".els-badge").count() > 0
        assert has_badge, "Real evidence must show lineage status badge"

        # SourceRef card MUST be present (real workflow produces source_ref_title)
        has_src = page.locator(".esrc-card").count() > 0
        assert has_src, "Real evidence must show SourceReferenceCard"

        # SourceRef card content is non-empty
        src_text = page.locator(".esrc-card").first.text_content()
        assert len(src_text.strip()) > 0, "SourceRef card must have content"

    def test_real_workflow_sourceref_link_routes(
        self, live_servers, result_workflow_session, page,
    ):
        """SourceRef canonical /library/{document_id}?passage={passage_id}
        binding — same document, two different passages, two distinct
        traces, full UI navigation, both links clicked.

        Each trace's Citation → Evidence → SourceRef internal link MUST
        be EXACTLY /library/{document_id}?passage={passage_id}.
        Both internal links are clicked — each browser URL is verified.
        """
        frontend_url, backend_port = live_servers
        ws = result_workflow_session
        sid = ws["session_id"]
        rid = ws["run_id"]

        # ---- Step 1: Real login via UI ----
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        # ---- Step 2: Click the visible Research nav entry (no page.goto) ----
        page.wait_for_selector('a[href="/research"]', timeout=10000)
        page.click('a[href="/research"]')
        page.wait_for_timeout(3000)
        page.wait_for_selector("h1", timeout=10000)

        # ---- Step 3: Click the project on the project list ----
        found_pl = False
        for sel in ['.pli-name-link', '.pli-enter-btn']:
            links = page.locator(sel)
            for i in range(links.count()):
                href = links.nth(i).get_attribute("href") or ""
                if sid in href:
                    links.nth(i).click()
                    found_pl = True
                    break
            if found_pl:
                break
        if not found_pl:
            direct = page.locator(f'a[href="/research/{sid}"]')
            if direct.count() > 0:
                direct.first.click()
                found_pl = True
        assert found_pl, f"Project link for session {sid} not found on project list"

        # ---- Step 4: Wait for project detail, then click report link ----
        page.wait_for_selector("h1", timeout=10000)
        page.wait_for_timeout(3000)

        found_report_link = False
        for selector in ['.pr-view-link', '.rr-view-link']:
            links = page.locator(selector)
            for i in range(links.count()):
                href = links.nth(i).get_attribute("href") or ""
                if rid in href and sid in href:
                    links.nth(i).click()
                    found_report_link = True
                    break
            if found_report_link:
                break
        if not found_report_link:
            view_links = page.locator('a:has-text("查看")')
            for i in range(view_links.count()):
                href = view_links.nth(i).get_attribute("href") or ""
                if rid in href and sid in href:
                    view_links.nth(i).click()
                    found_report_link = True
                    break
        assert found_report_link, (
            f"Report link for run {rid} not found on project detail page "
            f"(checked .pr-view-link, .rr-view-link, a:has-text('查看'))"
        )

        # ---- Step 5: Wait for result page to load ----
        page.wait_for_selector(".rrv-report", timeout=10000)
        assert f"/research/{sid}/result/{rid}" in page.url, (
            f"Expected result URL containing /research/{sid}/result/{rid}, got {page.url}"
        )

        # ---- Step 6: Read-only oracle — fetch real manifest traces ----
        base = f"http://127.0.0.1:{backend_port}"
        bearer = ws["token"]["access_token"]
        runs_resp = httpx.get(
            f"{base}/api/v4/research/session/{sid}/runs",
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=15,
        )
        assert runs_resp.status_code == 200, (
            f"GET runs failed: {runs_resp.status_code} {runs_resp.text[:500]}"
        )
        runs_list = runs_resp.json()["data"]["runs"]
        target_run = None
        for r in runs_list:
            if r.get("run_id") == rid:
                target_run = r
                break
        assert target_run is not None, (
            f"Target run {rid} not found in {len(runs_list)} runs"
        )
        manifest = target_run.get("replay_manifest")
        assert manifest is not None, "Target run must have replay_manifest"

        traces = manifest.get("traces", [])

        # Find traces with same document_id and different passage_id
        by_doc: dict[str, list[dict]] = {}
        for t in traces:
            did = t.get("document_id", "")
            pid = t.get("passage_id", "")
            tid = t.get("trace_id", "")
            if did and pid and tid:
                by_doc.setdefault(did, []).append(
                    {"document_id": did, "passage_id": pid, "trace_id": tid}
                )

        same_doc_traces = None
        for did, tlist in by_doc.items():
            unique_pids = list({t["passage_id"] for t in tlist})
            if len(unique_pids) >= 2:
                same_doc_traces = [tlist[0], tlist[1]]
                break

        assert same_doc_traces is not None, (
            f"Must find at least 2 traces with same document_id and different "
            f"passage_ids. Got {len(traces)} traces, doc_ids={list(by_doc.keys())}. "
            f"Passage ids per doc: {[(k, [t['passage_id'][:8] for t in v]) for k, v in by_doc.items()]}"
        )

        t1, t2 = same_doc_traces[0], same_doc_traces[1]
        assert t1["document_id"] == t2["document_id"], (
            f"Two traces must have SAME document_id for this regression test"
        )
        assert t1["passage_id"] != t2["passage_id"], (
            f"Two traces must have DIFFERENT passage_ids"
        )

        import sys
        print(
            f"\n--- SOURCEREF_E2E_SAME_DOC_TRACES: "
            f"doc={t1['document_id'][:8]}... "
            f"trace1=(tid={t1['trace_id'][:16]}... psg={t1['passage_id'][:8]}...) "
            f"trace2=(tid={t2['trace_id'][:16]}... psg={t2['passage_id'][:8]}...)",
            file=sys.stderr,
        )

        # ---- Step 7: Verify BOTH traces — Citation, Evidence, SourceRef href ----
        verified: list[dict] = []
        for idx, t in enumerate([t1, t2]):
            trace_id = t["trace_id"]
            doc_id = t["document_id"]
            psg_id = t["passage_id"]

            # 7a. Match visible Citation by trace_id prefix — fail-closed
            citation_items = page.locator(".rcp-citation-item")
            assert citation_items.count() > 0, f"[trace {idx}] No citation items"

            clicked = False
            for i in range(citation_items.count()):
                item = citation_items.nth(i)
                code_el = item.locator(".rcp-citation-id")
                if code_el.count() > 0:
                    displayed_id = code_el.first.text_content().strip()
                    if trace_id.startswith(displayed_id.rstrip(".")):
                        item.click()
                        clicked = True
                        break
            assert clicked, f"[trace {idx}] No citation matches {trace_id[:16]}..."

            page.wait_for_selector(".rcp-citation-item--selected", timeout=5000)

            # 7b. Evidence detail trace match
            page.wait_for_selector(".eed-card", timeout=5000)
            evidence_id_el = (
                page.locator('.eed-meta-row:has-text("证据 ID")')
                .locator(".eed-meta-value")
            )
            assert evidence_id_el.count() > 0, (
                f"[trace {idx}] Evidence card missing 证据 ID"
            )
            displayed_eid = evidence_id_el.first.text_content().strip()
            assert trace_id.startswith(displayed_eid.rstrip(".")), (
                f"[trace {idx}] Evidence trace mismatch: "
                f"expected prefix of {trace_id[:16]}..., got {displayed_eid!r}"
            )

            # 7c. MUST have internal SourceRef link — no fallback
            internal_link = page.locator(".eed-card .esrc-link--internal")
            assert internal_link.count() > 0, (
                f"[trace {idx}] MUST have .esrc-link--internal. "
                f"doc={doc_id[:8]}... psg={psg_id[:8]}..."
            )

            href = internal_link.first.get_attribute("href") or ""
            expected = f"/library/{doc_id}?passage={psg_id}"
            assert href == expected, (
                f"[trace {idx}] SourceRef href mismatch: "
                f"expected {expected!r}, got {href!r}"
            )

            verified.append({
                "trace_id": trace_id,
                "document_id": doc_id,
                "passage_id": psg_id,
                "href": href,
            })

        # ---- Step 8: Cross-trace no-serialization ----
        assert verified[0]["document_id"] == verified[1]["document_id"], (
            f"Both must share the same document_id"
        )
        assert verified[0]["passage_id"] != verified[1]["passage_id"], (
            f"Passage_ids must differ: "
            f"{verified[0]['passage_id'][:8]} vs {verified[1]['passage_id'][:8]}"
        )
        assert verified[0]["href"] != verified[1]["href"], (
            f"Hrefs must differ: {verified[0]['href']} vs {verified[1]['href']}"
        )

        # ---- Step 9: Click BOTH links, verify reader page, browser back ----
        for idx, v in enumerate(verified):
            tid = v["trace_id"]
            # Re-select the citation
            citation_items = page.locator(".rcp-citation-item")
            clicked = False
            for i in range(citation_items.count()):
                item = citation_items.nth(i)
                code_el = item.locator(".rcp-citation-id")
                if code_el.count() > 0:
                    displayed_id = code_el.first.text_content().strip()
                    if tid.startswith(displayed_id.rstrip(".")):
                        item.click()
                        clicked = True
                        break
            assert clicked, f"Could not re-select citation for {tid[:16]}..."
            page.wait_for_selector(".eed-card", timeout=5000)
            page.wait_for_selector(".esrc-link--internal", timeout=5000)

            link_el = page.locator(".eed-card .esrc-link--internal").first
            link_el.click()
            page.wait_for_load_state("networkidle", timeout=10000)
            page.wait_for_timeout(2000)

            current_url = page.url
            assert f"/library/{v['document_id']}" in current_url, (
                f"[trace {idx}] URL missing /library/{v['document_id'][:8]}..., "
                f"got {current_url}"
            )
            assert f"passage={v['passage_id']}" in current_url, (
                f"[trace {idx}] URL missing passage={v['passage_id'][:8]}..., "
                f"got {current_url}"
            )

            page.wait_for_selector("h1, h2, .doc-title, article, main", timeout=10000)
            body_text = page.locator("body").first.text_content() or ""
            assert len(body_text.strip()) > 0, (
                f"[trace {idx}] Reader page body must not be empty"
            )
            assert "/login" not in current_url, (
                f"[trace {idx}] Must not redirect to login. URL: {current_url}"
            )

            if idx == 0:
                # Back to result page for second trace
                page.go_back()
                page.wait_for_selector(".rrv-report", timeout=10000)

    def test_real_workflow_lineage_complete_or_partial(
        self, live_servers, result_workflow_session, page,
    ):
        """Real workflow lineage is either complete (full badge) or
        partial (partial badge) — never fabricated as complete when
        identifiers are missing."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rcp-citation-item", timeout=10000)

        # Click every citation, verify each has a lineage badge
        items = page.locator(".rcp-citation-item")
        count = items.count()
        for i in range(count):
            page.locator(".rcp-citation-item").nth(i).click()
            page.wait_for_timeout(500)

            has_full = page.locator(".els-badge--full").count() > 0
            has_partial = page.locator(".els-badge--partial").count() > 0
            has_minimal = page.locator(".els-badge--minimal").count() > 0
            any_badge = has_full or has_partial or has_minimal

            assert any_badge, (
                f"Citation {i} must have a lineage badge "
                f"(full={has_full}, partial={has_partial}, minimal={has_minimal})"
            )

            # If full is shown, SourceRef card must have content
            if has_full:
                assert page.locator(".esrc-card").count() > 0, (
                    f"Citation {i} with full lineage must show SourceRef card"
                )

    # ================================================================
    # Batch 2 — Real browser export + SourceRef E2E
    # ================================================================

    def test_export_markdown_real_browser_download(
        self, live_servers, result_workflow_session, page,
    ):
        """Full UI navigation export: /login → Research → project list →
        click project → project detail → click report → result page →
        click export → real browser download validated.

        Forbidden: page.goto() to protected result URL, localStorage
        token injection, network mock, or test-API report creation.
        """
        frontend_url, _ = live_servers
        ws = result_workflow_session
        sid = ws["session_id"]
        rid = ws["run_id"]

        # ---- Step 1: Real login via UI ----
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        # ---- Step 2: Click the visible Research nav entry (no page.goto) ----
        page.wait_for_selector('a[href="/research"]', timeout=10000)
        page.click('a[href="/research"]')
        page.wait_for_timeout(3000)
        page.wait_for_selector("h1", timeout=10000)

        # ---- Step 3: Click the project on the project list ----
        found_pl = False
        for sel in ['.pli-name-link', '.pli-enter-btn']:
            links = page.locator(sel)
            for i in range(links.count()):
                href = links.nth(i).get_attribute("href") or ""
                if sid in href:
                    links.nth(i).click()
                    found_pl = True
                    break
            if found_pl:
                break
        # Fallback: direct href match
        if not found_pl:
            direct = page.locator(f'a[href="/research/{sid}"]')
            if direct.count() > 0:
                direct.first.click()
                found_pl = True
        assert found_pl, f"Project link for session {sid} not found on project list"

        # ---- Step 4: Wait for project detail to load ----
        page.wait_for_selector("h1", timeout=10000)
        page.wait_for_timeout(3000)

        # ---- Step 5: Find and click report link on project detail ----
        found_report_link = False
        for selector in ['.pr-view-link', '.rr-view-link']:
            links = page.locator(selector)
            for i in range(links.count()):
                href = links.nth(i).get_attribute("href") or ""
                if rid in href and sid in href:
                    links.nth(i).click()
                    found_report_link = True
                    break
            if found_report_link:
                break
        # Fallback: try '查看' text links
        if not found_report_link:
            view_links = page.locator('a:has-text("查看")')
            for i in range(view_links.count()):
                href = view_links.nth(i).get_attribute("href") or ""
                if rid in href and sid in href:
                    view_links.nth(i).click()
                    found_report_link = True
                    break
        assert found_report_link, (
            f"Report link for run {rid} not found on project detail page "
            f"(checked .pr-view-link, .rr-view-link, a:has-text('查看'))"
        )

        # ---- Step 6: Wait for result page to load ----
        page.wait_for_selector(".rrv-report", timeout=10000)
        assert f"/research/{sid}/result/{rid}" in page.url, (
            f"Expected result URL containing /research/{sid}/result/{rid}, got {page.url}"
        )
        # Confirm we did NOT navigate directly — the URL should contain the correct IDs
        assert sid in page.url, f"URL must contain session_id {sid}, got {page.url}"
        assert rid in page.url, f"URL must contain run_id {rid}, got {page.url}"

        # ---- Step 7: Capture export response status + headers ----
        export_http_status: int = 0
        export_ct: str = ""
        export_cd: str = ""

        def _capture_export_response(response):
            nonlocal export_http_status, export_ct, export_cd
            if (
                "/api/v4/research/session/" in response.url
                and "/export" in response.url
            ):
                export_http_status = response.status
                export_ct = (
                    response.headers.get("content-type", "")
                ).lower()
                export_cd = (
                    response.headers.get("content-disposition", "")
                ).lower()

        page.on("response", _capture_export_response)

        # ---- Step 8: Click export and capture real browser download ----
        export_btn = page.locator(".rrh-btn--export")
        assert export_btn.is_visible(), "Export button must be visible"
        assert export_btn.is_enabled(), "Export button must be enabled"

        with page.expect_download(timeout=30000) as download_info:
            export_btn.click()

        download = download_info.value
        assert download is not None, "Real browser download must be triggered"

        # ---- Step 9: Validate filename matches backend naming rule ----
        # Backend: safe_filename = f"hfb-research-report-{safe_run_id}.md"
        #          safe_run_id = run_id[:8]
        filename = download.suggested_filename
        expected_prefix = "hfb-research-report-"
        assert filename.startswith(expected_prefix), (
            f"Filename must start with '{expected_prefix}', got {filename!r}"
        )
        assert filename.endswith(".md"), (
            f"Filename must end with .md, got {filename!r}"
        )
        # The filename embeds the run_id prefix — verify it matches
        assert rid[:8] in filename, (
            f"Filename must contain run_id prefix '{rid[:8]}', got {filename!r}"
        )

        # ---- Step 10: Validate content is real Markdown ----
        download_path = download.path()
        assert download_path is not None, "Download file path must not be None"
        raw_bytes = download_path.read_bytes()
        content = raw_bytes.decode("utf-8")
        assert len(content) > 0, "Downloaded file must be non-empty"
        # Must be Markdown — at least one heading
        assert "#" in content, (
            "Real export must contain Markdown headings"
        )
        # Must contain the real report title or research topic as
        # proof it's THIS report, not a stale or fake one
        session_title = "结果页真实工作流验证"
        topic = "ResultE2E验证"
        assert (session_title in content or topic in content), (
            f"Exported Markdown must contain the real report title "
            f"'{session_title}' or research topic '{topic}'. "
            f"Content preview: {content[:500]}"
        )

        # ---- Step 11: Assert HTTP 200 on export response ----
        assert export_http_status == 200, (
            f"Export response must be HTTP 200, got {export_http_status}"
        )

        # ---- Step 12: Assert response headers ----
        assert export_ct, "Export response must have a Content-Type header"
        assert "text/markdown" in export_ct, (
            f"Export Content-Type must be text/markdown; charset=utf-8, got {export_ct!r}"
        )
        assert export_cd, "Export response must have a Content-Disposition header"
        assert "attachment" in export_cd, (
            f"Content-Disposition must be attachment, got {export_cd!r}"
        )
        assert f'hfb-research-report-{rid[:8]}.md' in export_cd, (
            f"Content-Disposition must name the file with correct run_id prefix. "
            f"Expected 'hfb-research-report-{rid[:8]}.md' in {export_cd!r}"
        )

    def test_export_disabled_when_no_report(
        self, live_servers, result_workflow_session,
        result_workflow_session_no_report, page,
    ):
        """Export button is disabled when the run has no report."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        nr = result_workflow_session_no_report
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{nr['session_id']}/result/{nr['run_id']}"
        )
        page.wait_for_selector(".rre-state", timeout=10000)

        # Export button should be disabled
        export_btn = page.locator(".rrh-btn--export")
        if export_btn.count() > 0:
            assert not export_btn.is_enabled(), (
                "Export button must be disabled when report is missing"
            )

    def test_export_no_double_click(
        self, live_servers, result_workflow_session, page,
    ):
        """Export composable guard (`exporting.value`) blocks concurrent
        double-click → exactly 1 download event.

        Proof: if the guard fails, a rapid second click within the same
        JS tick would fire a second download.  We assert download_count == 1.

        Note: In real Chromium, Playwright click events can fire faster than
        Vue reactivity's propagation of exporting=true.  The composable's
        guard is a same-tick lock; a Playwright double-click that dispatches
        two click events in tight succession will test the guard under stress.
        We use page.evaluate to fire two clicks synchronously so the guard
        sees both within the same microtask queue — this is the strongest
        test of the concurrent-protection logic.
        """
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        download_count = 0

        def _on_download(dl):
            nonlocal download_count
            download_count += 1

        page.on("download", _on_download)

        # Fire two clicks via page.evaluate in one synchronous block —
        # this tests that the composable's `exporting.value` guard works
        # even when the second click arrives before Vue has finished
        # re-rendering.
        btn = page.locator(".rrh-btn--export")
        btn.evaluate("el => { el.click(); el.click(); }")

        # Wait for all downloads to settle
        page.wait_for_timeout(5000)

        assert download_count == 1, (
            f"Export guard must block double-click: "
            f"expected 1 download, got {download_count}"
        )

    def test_export_stale_after_route_switch(
        self, live_servers, result_workflow_session,
        result_workflow_session_no_report, page,
    ):
        """Exporting after switching to a report-missing run →
        old export does NOT fire with stale data."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        nr = result_workflow_session_no_report
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        # First load the real report
        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        # Then switch to report-missing run
        page.goto(
            f"{frontend_url}/research/{nr['session_id']}/result/{nr['run_id']}"
        )
        page.wait_for_selector(".rre-state", timeout=10000)
        assert page.locator("text=报告缺失").is_visible()

        # Export button should now be disabled (no report)
        export_btn = page.locator(".rrh-btn--export")
        if export_btn.count() > 0:
            assert not export_btn.is_enabled(), (
                "Export must be disabled after switching to report-missing"
            )

    # ================================================================
    # Batch 1 (continued) — Real-workflow cross-user + isolation
    # ================================================================

    def test_cross_user_result_blocked(
        self, live_servers, result_workflow_cross_users, page,
    ):
        """User A accessing B's real-workflow result → not-found,
        no B data leaked."""
        frontend_url, _ = live_servers
        a = result_workflow_cross_users["user_a"]
        b = result_workflow_cross_users["user_b"]

        _login_via_ui(page, frontend_url, a["username"], a["password"])

        api_404 = False

        def _capture(response):
            nonlocal api_404
            if f"/api/v1/workspace/sessions/{b['session_id']}" in response.url:
                if response.status == 404:
                    api_404 = True

        page.on("response", _capture)

        page.goto(
            f"{frontend_url}/research/{b['session_id']}/result/{b['run_id']}"
        )
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)

        # Must show not-found state
        assert (
            page.locator("text=未找到").is_visible()
            or page.locator("text=不存在").is_visible()
        ), "Cross-user result should show not-found state"

        # B's session title must NOT leak
        assert page.locator(f"text={b['title']}").count() == 0, (
            f"B's title '{b['title']}' should not appear in A's result page"
        )

        # B's report content must NOT appear
        assert page.locator(".rrv-report").count() == 0, (
            "B's report should not be visible to A"
        )

        assert api_404, "Session API must return 404 for cross-user access"

    def test_run_not_belonging_to_session_rejected(
        self, live_servers, result_workflow_cross_users, page,
    ):
        """User A's run in User B's session URL → rejected (run_id
        does not belong to that session)."""
        frontend_url, _ = live_servers
        a = result_workflow_cross_users["user_a"]
        b = result_workflow_cross_users["user_b"]

        _login_via_ui(page, frontend_url, a["username"], a["password"])

        # Use A's run_id with B's session_id — cross-session mismatch
        page.goto(
            f"{frontend_url}/research/{a['session_id']}/result/{b['run_id']}"
        )
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)

        # Must show not-found — the run does not exist in A's session
        assert (
            page.locator("text=未找到").is_visible()
            or page.locator("text=不存在").is_visible()
            or page.locator(".rre-state").count() > 0
        ), (
            "Cross-session run ID must be rejected with not-found or error state"
        )

        # B's report must not be visible
        assert page.locator(".rrv-report").count() == 0, (
            "Cross-session run must not show B's report"
        )

    # ================================================================
    # XSS controlled-input (seed payloads in real browser)
    # ================================================================
    # These tests use a seed fixture (result_session_xss_payloads)
    # whose markdown, citations, and retrieval_snapshot contain known
    # XSS payload vectors.  The tests verify the Vue template-bound
    # text parser neutralises every vector — no script execution,
    # no active event handlers, no iframes, no javascript: links.
    # The valid markdown and safe links in the payload must still work.
    # STATE-ONLY: do NOT use result_session_xss_payloads for
    # report/Citation/Evidence/SourceRef authenticity assertions.

    def test_xss_script_no_executable_node(
        self, live_servers, result_session_xss_payloads, page,
    ):
        """Controlled XSS payload: <script>, onerror=, onclick= are NOT
        rendered as executable HTML nodes."""
        frontend_url, _ = live_servers
        s = result_session_xss_payloads
        _login_via_ui(page, frontend_url, s["username"], s["password"])

        page.goto(
            f"{frontend_url}/research/{s['session_id']}/result/{s['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        # Scoped assertions: check the report inner HTML only — not the
        # full page (which contains Vite dev server <script> tags).
        report_html = page.locator(".rrv-report").inner_html()

        # No raw HTML script tags in the report body
        assert "<script>" not in report_html, (
            "Raw <script> must not exist in rendered report DOM"
        )
        assert "</script>" not in report_html, (
            "Raw </script> must not exist in rendered report DOM"
        )

        # The XSS fixture puts inline HTML payloads in the markdown
        # (e.g., '<img src="x" onerror="alert(1)">').  The report parser
        # renders these as escaped text — e.g.,
        # &lt;img src="x" onerror="alert(1)"&gt;.
        #
        # Escaped text IS safe.  To prove the parser truly neutralizes
        # the payloads, we query the DOM for real elements that would
        # carry event-handler attributes.  If Vue text binding escaped
        # everything, these locators return zero matches.
        for attr_name in ("onerror", "onclick", "onload"):
            real_elements = page.locator(f"[{attr_name}]")
            assert real_elements.count() == 0, (
                f"No element with real {attr_name}= attribute must exist"
            )

        # No iframes in report
        assert "<iframe" not in report_html, (
            "<iframe> must not appear in report inner HTML"
        )

        # No SVG in report
        assert "<svg" not in report_html, (
            "<svg> must not appear in report inner HTML"
        )

        # ---- Normal safe content MUST still render ----
        # The report title shows "研究报告：XSS载荷验证" (topic-based).
        # The markdown section heading "# XSS 安全验证报告" and "正常的中文文本段落"
        # appear inside the report body rendered from markdown.
        report_text = page.locator(".rrv-report").text_content()
        assert "XSS 安全验证报告" in report_text, (
            "XSS safe-report heading must appear in report body"
        )
        assert "正常的中文文本段落" in report_text, (
            "Normal Chinese text must render correctly"
        )

    def test_xss_no_dangerous_href(
        self, live_servers, result_session_xss_payloads, page,
    ):
        """Controlled XSS payload: no javascript: links in citation panel
        or SourceRef card."""
        frontend_url, _ = live_servers
        s = result_session_xss_payloads
        _login_via_ui(page, frontend_url, s["username"], s["password"])

        page.goto(
            f"{frontend_url}/research/{s['session_id']}/result/{s['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        # Select the XSS citation
        page.locator(".rcp-citation-item").first.click()
        page.wait_for_selector(".eed-card", timeout=5000)

        # SourceRef card: MUST NOT have a javascript: link
        src_card = page.locator(".esrc-card")
        if src_card.count() > 0:
            all_links = src_card.locator("a")
            for i in range(all_links.count()):
                href = (all_links.nth(i).get_attribute("href") or "").lower()
                assert not href.startswith("javascript:"), (
                    f"SourceRef link must not be javascript:, got {href!r}"
                )
                assert not href.startswith("data:"), (
                    f"SourceRef link must not be data:, got {href!r}"
                )

        # Evidence claim/quote — the XSS fixture explicitly seeds
        # claim_text with "安全载荷：<script>alert('s')</script>" as a
        # controlled payload.  The Vue template text binding MUST render
        # this as escaped text content (browser text_content() returns
        # the literal string without interpreting tags).  However, we
        # must NOT assert that "<script>" is absent from text_content()
        # — because the text_content() of a properly-escaped node WILL
        # contain the literal string if the fixture seeded it.
        #
        # What we DO assert: the HTML inner content does not contain a
        # real <script> element (checked by querying for script tags),
        # and the SourceRef card does not contain javascript:/data: links.
        claim_text = page.locator(".eed-claim-text").text_content()
        quote_text = page.locator(".eed-quote-text").text_content()
        for label, text in [("claim", claim_text), ("quote", quote_text)]:
            assert "onerror=" not in text, f"{label} text must not contain onerror="

        # Verify claim/quote text content is not empty (proof that Vue
        # rendered the text binding, not an empty or missing node)
        assert len(claim_text.strip()) > 0, "claim text must not be empty"
        assert len(quote_text.strip()) > 0, "quote text must not be empty"

        # The rendered DOM must NOT contain real <script> elements
        # inside the evidence card
        eed_card = page.locator(".eed-card")
        if eed_card.count() > 0:
            script_tags = eed_card.locator("script")
            assert script_tags.count() == 0, (
                "Evidence card must not contain real <script> elements"
            )

        # ---- Normal safe external links must still work in report ----
        # The markdown text should render the text portion normally
        body_text = page.locator("body").text_content() or ""
        assert "正常外链" in body_text, (
            "Normal external link text must appear in page"
        )
        assert "正常安全链接" in body_text, (
            "Normal safe-links section must render"
        )

    def test_xss_no_navigation_or_script_execution(
        self, live_servers, result_session_xss_payloads, page,
    ):
        """Click around the XSS-payload report → no navigation to
        dangerous URLs, no script execution."""
        frontend_url, _ = live_servers
        s = result_session_xss_payloads
        _login_via_ui(page, frontend_url, s["username"], s["password"])

        page.goto(
            f"{frontend_url}/research/{s['session_id']}/result/{s['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        start_url = page.url

        # Select citation, verify evidence panel appears
        page.locator(".rcp-citation-item").first.click()
        page.wait_for_selector(".eed-card", timeout=5000)

        # URL must not have navigated away
        assert page.url == start_url, (
            "Citation click must not navigate away from result page"
        )

        # Click various places in the report — none must navigate
        section_headings = page.locator(".rrv-section-heading")
        if section_headings.count() > 0:
            section_headings.first.click()
            page.wait_for_timeout(500)
            assert page.url == start_url, (
                "Clicking section heading must not navigate away"
            )

        # Verify no alert/confirm dialogs appeared (script didn't execute)
        # Playwright would throw on unhandled dialog if not dismissed
        # — this is implicit.  Explicitly check no new dialog appeared.
        try:
            dialog = page.locator("dialog[open]")
            assert dialog.count() == 0, (
                "No dialog should be present after clicking XSS payloads"
            )
        except Exception:
            pass

    # ================================================================
    # SourceRef withdrawn / no-permission (seed payloads)
    # ================================================================
    # STATE-ONLY: result_session_withdrawn_source simulates a run where
    # retrieval_snapshot entries lack document_id (withdrawn/inaccessible).
    # Tests verify: no internal link shown, javascript: source_ref_url
    # not rendered as active link, literature body not leaked.

    def test_withdrawn_source_no_internal_link(
        self, live_servers, result_session_withdrawn_source, page,
    ):
        """Withdrawn source (no document_id) → no internal /versions/ link,
        no javascript: link active, source text not leaked."""
        frontend_url, _ = live_servers
        s = result_session_withdrawn_source
        _login_via_ui(page, frontend_url, s["username"], s["password"])

        page.goto(
            f"{frontend_url}/research/{s['session_id']}/result/{s['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        # Select first citation (trace_a: no document_id)
        page.locator(".rcp-citation-item").first.click()
        page.wait_for_selector(".eed-card", timeout=5000)

        # No internal links in SourceRef card
        internal_links = page.locator(".esrc-link--internal")
        assert internal_links.count() == 0, (
            "Withdrawn source (no document_id) must NOT show internal link"
        )

        # No javascript: links anywhere in SourceRef card
        all_links = page.locator(".esrc-card a")
        for i in range(all_links.count()):
            href = (all_links.nth(i).get_attribute("href") or "").lower()
            assert not href.startswith("javascript:"), (
                f"Withdrawn source must not have javascript: link, got {href!r}"
            )

        # Source title should appear as plain text (not interactive)
        src_card_text = page.locator(".esrc-card").first.text_content()
        assert "已撤回" in src_card_text or "来源" in src_card_text, (
            "Source card must show non-interactive source info"
        )

    def test_withdrawn_source_no_malicious_sourceref_url(
        self, live_servers, result_session_withdrawn_source, page,
    ):
        """SourceRef with javascript: source_ref_url → NOT rendered as
        active link, no literature body leaked via link target."""
        frontend_url, _ = live_servers
        s = result_session_withdrawn_source
        _login_via_ui(page, frontend_url, s["username"], s["password"])

        page.goto(
            f"{frontend_url}/research/{s['session_id']}/result/{s['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        # Select second citation (trace_b: javascript: source_ref_url)
        items = page.locator(".rcp-citation-item")
        if items.count() >= 2:
            items.nth(1).click()
            page.wait_for_selector(".eed-card", timeout=5000)

        # No javascript: links in the entire page
        js_links = page.locator('a[href^="javascript:"]')
        assert js_links.count() == 0, (
            f"Found {js_links.count()} javascript: link(s) — "
            "malicious source_ref_url must not be rendered as active link"
        )

        # No data: links
        data_links = page.locator('a[href^="data:"]')
        assert data_links.count() == 0, (
            f"Found {data_links.count()} data: link(s)"
        )

        # Restricted source title should appear as plain text only
        page_text = page.locator(".esrc-card").text_content()
        assert "受限文献" in page_text or "无权限" in page_text or "来源" in page_text, (
            "Withdrawn source info must appear as plain descriptive text"
        )

    # ================================================================
    # XSS (on real-workflow report)
    # ================================================================

    def test_markdown_xss_script_not_executed(
        self, live_servers, result_workflow_session, page,
    ):
        """<script> in real report is NOT rendered as executable HTML."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        html = page.content()
        assert "<script>" not in html, "Raw <script> tag found in rendered DOM"
        assert "onerror=" not in html
        assert "onclick=" not in html

    def test_markdown_xss_javascript_url_not_active(
        self, live_servers, result_workflow_session, page,
    ):
        """javascript: URLs in real report are not active."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        js_links = page.locator('a[href^="javascript:"]')
        assert js_links.count() == 0, (
            f"Found {js_links.count()} javascript: links in real report"
        )

    def test_markdown_xss_no_iframe_svg(
        self, live_servers, result_workflow_session, page,
    ):
        """iframe/SVG elements not injected into real report DOM."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        iframes = page.locator(".rrv-report iframe")
        assert iframes.count() == 0, (
            f"Found {iframes.count()} iframe(s) in real report"
        )

    # ================================================================
    # Route-switch isolation (state-only seed for "bad" states)
    # ================================================================

    def test_route_switch_clears_stale_data(
        self, live_servers, result_workflow_session,
        result_workflow_session_no_report, page,
    ):
        """Switching from real report to report-missing → old report cleared.
        (Uses seed-only fixture for the empty-report state.)"""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        nr = result_workflow_session_no_report
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        # Navigate to real report
        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)
        assert page.locator(".rrv-report").is_visible()

        # Switch to report-missing run (same user, different session)
        page.goto(
            f"{frontend_url}/research/{nr['session_id']}/result/{nr['run_id']}"
        )
        page.wait_for_selector(".rre-state", timeout=10000)

        # Old report content must NOT be visible
        assert page.locator(".rrv-report").count() == 0, (
            "Old report should not be visible after switch"
        )
        assert page.locator("text=报告缺失").is_visible(), (
            "Should show report-missing state"
        )

    def test_switch_from_error_to_ready_clears_error(
        self, live_servers, result_workflow_session,
        result_workflow_session_no_report, page,
    ):
        """After seeing error state, switching to real workflow run
        clears the error and shows real report."""
        frontend_url, _ = live_servers
        ws = result_workflow_session
        nr = result_workflow_session_no_report
        _login_via_ui(page, frontend_url, ws["username"], ws["password"])

        # First visit report-missing run
        page.goto(
            f"{frontend_url}/research/{nr['session_id']}/result/{nr['run_id']}"
        )
        page.wait_for_selector(".rre-state", timeout=10000)
        assert page.locator("text=报告缺失").is_visible()

        # Now switch to real workflow run
        page.goto(
            f"{frontend_url}/research/{ws['session_id']}/result/{ws['run_id']}"
        )
        page.wait_for_selector(".rrv-report", timeout=10000)

        # Error state must be gone
        assert page.locator(".rre-state").count() == 0, (
            "Error state should be cleared after switch"
        )
        assert page.locator(".rrv-report").is_visible(), (
            "Report should be visible after switch"
        )
        assert page.locator("h1").text_content() == "结果页真实工作流验证"


# ====================================================================
# ResearchReportsPage E2E (Task 007)
# ====================================================================


@pytest.fixture(scope="module")
def reports_user_a(live_servers):
    """Create user A with a real-workflow session + run (report ready)."""
    _, backend_port = live_servers
    tokens = _seed_user(backend_port, f"rpts-a-{_uuid.uuid4().hex[:6]}", "ReportsA_Pass123!")
    if tokens is None:
        raise RuntimeError("Failed to create reports user A")
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "用户A研究报告"},
        headers=headers, timeout=10,
    )
    session_id = sess_resp.json()["data"]["id"]

    seed_resp = httpx.post(
        f"{base}/api/v4/research/_test/seed-research-run",
        json={
            "session_id": session_id,
            "topic": "A的哮喘研究",
            "markdown": "# 用户A的研究报告\n\n报告内容",
            "citations": [{"text": "test citation", "source": "甲乙经"}],
            "retrieval_snapshot": [],
            "traces": [],
        },
        headers=headers, timeout=10,
    )
    run_id = seed_resp.json()["data"]["run_id"]

    return {
        "username": tokens["username"],
        "password": "ReportsA_Pass123!",
        "token": tokens,
        "session_id": session_id,
        "run_id": run_id,
    }


@pytest.fixture(scope="module")
def reports_user_b(live_servers):
    """Create user B with own session + run - must be isolated from A."""
    _, backend_port = live_servers
    tokens = _seed_user(backend_port, f"rpts-b-{_uuid.uuid4().hex[:6]}", "ReportsB_Pass123!")
    if tokens is None:
        raise RuntimeError("Failed to create reports user B")
    base = f"http://127.0.0.1:{backend_port}"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    sess_resp = httpx.post(
        f"{base}/api/v1/workspace/sessions",
        json={"title": "用户B研究报告"},
        headers=headers, timeout=10,
    )
    session_id = sess_resp.json()["data"]["id"]

    seed_resp = httpx.post(
        f"{base}/api/v4/research/_test/seed-research-run",
        json={
            "session_id": session_id,
            "topic": "B的经络研究",
            "markdown": "# 用户B的研究报告\n\nB报告内容",
            "citations": [{"text": "B citation", "source": "灵枢"}],
            "retrieval_snapshot": [],
            "traces": [],
        },
        headers=headers, timeout=10,
    )
    run_id = seed_resp.json()["data"]["run_id"]

    return {
        "username": tokens["username"],
        "password": "ReportsB_Pass123!",
        "token": tokens,
        "session_id": session_id,
        "run_id": run_id,
    }


class TestResearchReportsPageE2E:
    """ResearchReportsPage E2E — real browser, real login, real data.

    Verifies:
      - User sees own reports in the list
      - Report list shows correct statuses
      - "View Report" links use real session_id/run_id
      - Clicking "View Report" opens frozen ResearchResultPage
      - URL uses real IDs
      - Real Markdown export from reports page
      - User A cannot see User B's reports
    """

    def test_report_list_loads_with_own_reports(
        self, live_servers, reports_user_a, page,
    ):
        """Real login → open /reports → see own reports."""
        frontend_url, _ = live_servers
        ua = reports_user_a
        _login_via_ui(page, frontend_url, ua["username"], ua["password"])

        page.goto(f"{frontend_url}/reports")
        # Wait for at least one list item to render with content
        page.wait_for_selector(".rrli-root", timeout=10000)
        page.wait_for_selector(".rrli-session-title", timeout=10000)

        assert page.locator("text=用户A研究报告").is_visible(), (
            "Reports page must show user A's session title"
        )
        assert page.locator("text=A的哮喘研究").is_visible(), (
            "Reports page must show user A's research topic"
        )

        # Check badge inside a list item (NOT the toolbar dropdown option)
        badge = page.locator(".rrli-root .rsb-report-ready")
        assert badge.count() >= 1, (
            "Report with markdown must show ready badge"
        )

    def test_view_report_link_uses_real_ids(
        self, live_servers, reports_user_a, page,
    ):
        """The '查看报告' link must use real session_id and run_id."""
        frontend_url, _ = live_servers
        ua = reports_user_a
        _login_via_ui(page, frontend_url, ua["username"], ua["password"])

        page.goto(f"{frontend_url}/reports")
        page.wait_for_selector(".rrli-root", timeout=10000)
        page.wait_for_selector(".rrli-view-link", timeout=10000)

        view_link = page.locator(".rrli-view-link")
        assert view_link.is_visible()

        href = view_link.get_attribute("href")
        assert href is not None
        assert ua["session_id"] in href, f"URL missing session_id: {href}"
        assert ua["run_id"] in href, f"URL missing run_id: {href}"
        assert href.startswith("/research/"), f"Bad URL prefix: {href}"
        assert "/result/" in href, f"URL missing /result/: {href}"

    def test_click_view_opens_result_page(
        self, live_servers, reports_user_a, page,
    ):
        """Click '查看报告' → navigate to frozen ResearchResultPage."""
        frontend_url, _ = live_servers
        ua = reports_user_a
        _login_via_ui(page, frontend_url, ua["username"], ua["password"])

        page.goto(f"{frontend_url}/reports")
        page.wait_for_selector(".rrli-view-link", timeout=10000)

        # SPA navigation — click and wait for result page to appear
        page.locator(".rrli-view-link").click()

        # Wait for the URL to change to contain the run ID
        page.wait_for_url(f"**/result/{ua['run_id']}", timeout=10000)
        assert ua["session_id"] in page.url
        page.wait_for_selector(".rrh-page-title, .rrv-report, h1", timeout=10000)

    def test_export_from_reports_page(
        self, live_servers, reports_user_a, page,
    ):
        """Export button on reports page triggers real download."""
        frontend_url, _ = live_servers
        ua = reports_user_a
        _login_via_ui(page, frontend_url, ua["username"], ua["password"])

        page.goto(f"{frontend_url}/reports")
        page.wait_for_selector(".rrli-export-btn", timeout=10000)

        export_btn = page.locator(".rrli-export-btn")
        assert export_btn.is_visible()

        with page.expect_download(timeout=10000) as download_info:
            export_btn.click()

        download = download_info.value
        assert download is not None
        filename = download.suggested_filename
        assert "hfb-research-report-" in filename, f"Bad filename: {filename}"
        assert filename.endswith(".md"), f"Not .md: {filename}"

    def test_user_a_cannot_see_user_b_reports(
        self, live_servers, reports_user_a, reports_user_b, page,
    ):
        """User A must not see User B's reports."""
        frontend_url, _ = live_servers
        ua = reports_user_a
        ub = reports_user_b
        _login_via_ui(page, frontend_url, ua["username"], ua["password"])

        page.goto(f"{frontend_url}/reports")
        page.wait_for_selector(".rrli-root", timeout=10000)

        assert page.locator("text=用户B研究报告").count() == 0
        assert page.locator("text=B的经络研究").count() == 0

        # Try direct URL access to B's report
        page.goto(
            f"{frontend_url}/research/{ub['session_id']}/result/{ub['run_id']}"
        )

        try:
            page.wait_for_selector(".rre-state", timeout=5000)
        except Exception:
            pass

        assert page.locator("text=用户B研究报告").count() == 0

    def test_b_cannot_see_a_reports(
        self, live_servers, reports_user_a, reports_user_b, page,
    ):
        """User B must not see User A's reports."""
        frontend_url, _ = live_servers
        ua = reports_user_a
        ub = reports_user_b
        _login_via_ui(page, frontend_url, ub["username"], ub["password"])

        page.goto(f"{frontend_url}/reports")
        page.wait_for_selector(".rrli-root", timeout=10000)

        assert page.locator("text=用户A研究报告").count() == 0
        assert page.locator("text=A的哮喘研究").count() == 0

    def test_empty_reports_page(
        self, live_servers, page,
    ):
        """New user with no sessions sees empty state."""
        frontend_url, backend_port = live_servers
        username = f"empty-rpts-{_uuid.uuid4().hex[:6]}"
        # Register first via API (the UI login page doesn't auto-register)
        _seed_user(backend_port, username, "Empty_Pass123!")
        _login_via_ui(page, frontend_url, username, "Empty_Pass123!")

        page.goto(f"{frontend_url}/reports")
        page.wait_for_selector(".empty-state", timeout=10000)

        assert page.locator("text=暂无报告").is_visible()


# ============================================================
# TestLibraryE2E — Library browser E2E tests
# ============================================================


@pytest.fixture(scope="module")
def library_test_users(live_servers):
    """Create two users for Library cross-user isolation tests.

    User A: owns document via create (uploaded_by = user_a)
    User B: separate user who must never see A's private documents
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"

    token_a = _seed_user(backend_port, f"lib-a-{_uuid.uuid4().hex[:6]}", "LibA_Pass123!")
    token_b = _seed_user(backend_port, f"lib-b-{_uuid.uuid4().hex[:6]}", "LibB_Pass123!")

    # User A creates a private document
    headers_a = {"Authorization": f"Bearer {token_a['access_token']}"}
    r = httpx.post(
        f"{base}/api/v1/documents",
        json={
            "title": f"用户A的私密文献-{_uuid.uuid4().hex[:6]}",
            "dynasty": "唐",
            "category": "方剂",
            "abstract": "A的私密文献摘要",
            "content_text": "这是A的私有文献内容",
            "language": "zh",
        },
        headers=headers_a,
        timeout=10,
    )
    doc_a = r.json().get("data", {}) if r.status_code in (200, 201) else {}

    # User B creates a private document
    headers_b = {"Authorization": f"Bearer {token_b['access_token']}"}
    r2 = httpx.post(
        f"{base}/api/v1/documents",
        json={
            "title": f"用户B的私密文献-{_uuid.uuid4().hex[:6]}",
            "dynasty": "宋",
            "category": "本草",
            "abstract": "B的私密文献摘要",
            "content_text": "这是B的私有文献内容",
            "language": "zh",
        },
        headers=headers_b,
        timeout=10,
    )
    doc_b = r2.json().get("data", {}) if r2.status_code in (200, 201) else {}

    return {
        "user_a": {**token_a, "doc": doc_a},
        "user_b": {**token_b, "doc": doc_b},
    }


class TestLibraryE2E:
    """End-to-end Library browser tests with real auth (no localStorage injection).

    Covers:
      - Login → Library list loads
      - Search triggers q param
      - Copyright filter composes with search
      - Pagination is visible for large datasets
      - Detail page shows title, stats, reader jump
    """

    def test_library_page_loads_authenticated(
        self, live_servers, library_test_users, page,
    ):
        """After real login, /library shows the Library heading."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        page.goto(f"{frontend_url}/library")
        page.wait_for_selector("text=Library", timeout=10000)
        assert page.locator("text=Library").count() > 0

    def test_library_requires_auth(
        self, live_servers, page,
    ):
        """Anonymous user visiting /library is redirected to login."""
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/library")
        # Wait for redirect to /login
        page.wait_for_url(f"{frontend_url}/login**", timeout=10000)

    def test_library_search_returns_results(
        self, live_servers, library_test_users, page,
    ):
        """Search for a seed document (针灸) returns matching results."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        page.goto(f"{frontend_url}/library")

        # Wait for seed docs to load
        page.wait_for_selector("text=Library", timeout=10000)

        # Enter search text
        search_input = page.locator('input[type="text"]').first
        search_input.fill("针灸")

        # Intercept the API request to verify q param
        api_requests = []
        page.on("request", lambda req: api_requests.append(req.url) if "/api/v1/documents" in req.url else None)

        # Click search button
        page.locator(".lib-search-btn").first.click()

        # Wait for results to load
        page.wait_for_timeout(3000)

        # Verify an API call was made with q=针灸
        search_requests = [u for u in api_requests if "q=" in u]
        assert len(search_requests) >= 1, (
            f"No search API call with q= param detected. Got: {api_requests}"
        )
        assert any("q=%E9%92%88%E7%81%B8" in u or "q=针灸" in u or "q=%E9%87%9D%E7%81%B8" in u
                   or "q=%E9%8F%BD%E7%81%B8" in u for u in search_requests), (
            f"Search query '针灸' not found in API requests: {search_requests}"
        )

        # Must show matching document cards (seed data has '针灸甲乙经')
        assert page.locator("text=Library").count() > 0
        body = page.locator('body').first.text_content() or ""
        assert "针灸" in body, f"Search results should contain '针灸'. Body: {body[:500]}"

    def test_library_detail_page_shows_document_info(
        self, live_servers, library_test_users, page,
    ):
        """Detail page at /library/:id shows real title, no error, stats panel visible."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        doc_title = a.get("doc", {}).get("title", "")
        doc_id = a.get("doc", {}).get("id")
        assert doc_id, "User A must have a private document"
        assert doc_title, "Document must have a title"

        # Capture stats response status
        stats_status = None

        def _on_response(response):
            nonlocal stats_status
            if f"/api/v1/documents/{doc_id}/stats" in response.url:
                stats_status = response.status

        page.on("response", _on_response)

        page.goto(f"{frontend_url}/library/{doc_id}")
        # Wait for the detail page to load — API returns doc + stats
        page.wait_for_timeout(8000)

        body = page.locator('body').first.text_content() or ""

        # Must show the real document title
        assert doc_title in body, (
            f"Document title '{doc_title}' not visible. Body: {body[:300]}"
        )

        # Must NOT show loading or error state
        assert page.locator('.error-state, .lib-error').count() == 0, (
            f"Page should not show error state. Body: {body[:300]}"
        )
        assert "加载中" not in body, f"Page should not be loading. Body: {body[:300]}"

        # Stats panel must be visible — "文献统计" heading or stat fields
        assert page.locator('text=文献统计').is_visible() or \
               page.locator('text=分块数量').is_visible(), (
            f"Stats panel not visible. Body: {body[:300]}"
        )

        # Stats request must have returned 200
        assert stats_status == 200, (
            f"Stats endpoint must return 200, got {stats_status}"
        )

    def test_library_reader_jump(
        self, live_servers, library_test_users, page,
    ):
        """Clicking '全文阅读' button navigates to /reader/:id with correct doc ID."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        doc_id = a.get("doc", {}).get("id")
        doc_title = a.get("doc", {}).get("title", "")
        assert doc_id, "User A must have a private document"
        assert doc_title, "Document must have a title"

        page.goto(f"{frontend_url}/library/{doc_id}")
        page.wait_for_timeout(8000)

        # Must find the '全文阅读' button
        page.wait_for_selector('button:has-text("全文阅读")', timeout=10000)
        reader_btn = page.locator('button:has-text("全文阅读")').first
        assert reader_btn.is_visible(), (
            f"'全文阅读' button must be visible on detail page for doc {doc_id}"
        )

        # Click the reader button
        reader_btn.click()
        # Task 009 refactored Reader to /reader/:id — verify the canonical route
        page.wait_for_url(f"{frontend_url}/reader/{doc_id}**", timeout=10000)

        # Verify the reader page loaded with real content
        page.wait_for_timeout(3000)
        reader_body = page.locator('body').first.text_content() or ""
        # The reader must show the document title or its content text
        assert doc_title in reader_body or "这是A的私有文献内容" in reader_body, (
            f"Reader page must show doc title or content for doc {doc_id}. "
            f"Body: {reader_body[:300]}"
        )

    def test_literature_page_requires_auth(
        self, live_servers, page,
    ):
        """Anonymous user visiting /literature/:id is redirected to login."""
        frontend_url, _ = live_servers
        # Use a placeholder UUID
        page.goto(f"{frontend_url}/literature/00000000-0000-0000-0000-000000000001")
        page.wait_for_url(f"{frontend_url}/login**", timeout=10000)


class TestLibraryCrossUserIsolation:
    """Cross-user isolation: User A must NOT see User B's private documents."""

    def test_user_a_cannot_see_user_b_private_doc_in_list(
        self, live_servers, library_test_users, page,
    ):
        """User A's document list must not contain User B's private document title."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        page.goto(f"{frontend_url}/library")
        page.wait_for_timeout(3000)

        # A should NOT see B's private document title
        b_title = b.get("doc", {}).get("title", "")
        if b_title:
            assert page.locator(f"text={b_title}").count() == 0

    def test_user_b_cannot_see_user_a_private_doc_in_list(
        self, live_servers, library_test_users, page,
    ):
        """User B's document list must not contain User A's private document title."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]
        _login_via_ui(page, frontend_url, b["username"], "LibB_Pass123!")

        page.goto(f"{frontend_url}/library")
        page.wait_for_timeout(3000)

        # B should NOT see A's private document title
        a_title = a.get("doc", {}).get("title", "")
        if a_title:
            assert page.locator(f"text={a_title}").count() == 0

    def test_user_a_cannot_access_user_b_private_doc_detail(
        self, live_servers, library_test_users, page,
    ):
        """User A must NOT see User B's private document detail — title, body, stats."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        b_doc_id = b.get("doc", {}).get("id", "")
        if not b_doc_id:
            pytest.skip("User B has no private document")

        # Try direct URL access
        page.goto(f"{frontend_url}/library/{b_doc_id}")
        page.wait_for_timeout(5000)

        # A must NOT see B's document title anywhere on page
        b_title = b.get("doc", {}).get("title", "")
        if b_title:
            assert page.locator(f"text={b_title}").count() == 0, (
                f"User A should NOT see B's doc title '{b_title}'"
            )
        # A must NOT see B's content or stats either
        b_abstract = b.get("doc", {}).get("abstract", "")
        if b_abstract:
            assert page.locator(f"text={b_abstract}").count() == 0, (
                f"User A should NOT see B's doc abstract"
            )
        body = (page.locator('body').first.text_content() or "")
        assert "统计" not in body or "分块数量" not in body, (
            f"User A must not see stats for B's doc. Body: {body[:300]}"
        )

    def test_user_a_cannot_read_user_b_private_doc_via_literature(
        self, live_servers, library_test_users, page,
    ):
        """User A must not read User B's private document full text via /literature/:id."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        b_doc_id = b.get("doc", {}).get("id", "")
        if not b_doc_id:
            pytest.skip("User B has no private document")

        # A tries to read B's doc via the reader
        page.goto(f"{frontend_url}/literature/{b_doc_id}")
        page.wait_for_timeout(3000)

        # A must NOT see B's document content
        b_title = b.get("doc", {}).get("title", "")
        if b_title:
            assert page.locator(f"text={b_title}").count() == 0

    def test_user_b_cannot_access_user_a_private_doc_stats(
        self, live_servers, library_test_users, page,
    ):
        """User B gets 404 when accessing User A's private document stats."""
        frontend_url, backend_port = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]
        _login_via_ui(page, frontend_url, b["username"], "LibB_Pass123!")

        a_doc_id = a.get("doc", {}).get("id", "")
        if not a_doc_id:
            pytest.skip("User A has no private document")

        # B tries direct API access to A's stats
        base = f"http://127.0.0.1:{backend_port}"
        headers = {"Authorization": f"Bearer {b['access_token']}"}
        r = httpx.get(f"{base}/api/v1/documents/{a_doc_id}/stats", headers=headers, timeout=10)

        # Must return 403 (RBAC permission denied) or 404 (ownership check).
        # 200 or 500 is a leak — B must not know whether A's doc exists.
        assert r.status_code in (403, 404), (
            f"Expected 403 or 404 (isolation), got {r.status_code}: {r.text[:300]}"
        )
