"""
Pytest configuration for E2E test modules under tests/e2e/.

Provides shared fixtures (live_servers, auth helpers, test data) so that
individual test files like test_reader_e2e.py don't need to duplicate them.
"""
from __future__ import annotations

import os
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
    env["SEED_TEST_DATA"] = "1"  # Enable test-only seed-run endpoint
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


# ============================================================
# Module-scoped fixtures
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
def library_test_users(live_servers):
    """Create two users for Library + Reader cross-user isolation tests.

    Uses the test-only /_test/seed-reader-data endpoint which creates:
      User → Document → Chunks → Book→Version→Chapter→Passage →
      Evidence → Citation
    """
    _, backend_port = live_servers
    base = f"http://127.0.0.1:{backend_port}"

    # Register users first so they exist in DB
    token_a = _seed_user(backend_port, f"lib-a-{_uuid.uuid4().hex[:6]}", "LibA_Pass123!")
    token_b = _seed_user(backend_port, f"lib-b-{_uuid.uuid4().hex[:6]}", "LibB_Pass123!")

    # User A: full reader data
    a_body = {
        "username": token_a["username"],
        "password": "LibA_Pass123!",
        "document_title": f"用户A的Reader文献-{_uuid.uuid4().hex[:6]}",
        "document_text": (
            "ReaderE2E验证标识\n\n"
            "黄帝问曰：余闻九针于夫子，众多博大，不可胜数。"
            "余愿闻要道，以属子孙，传之后世，著之骨髓，"
            "藏之肝肺，歃血而受，不敢妄泄。\n\n"
            "令合天道，必有终始，上应天光星辰历纪，"
            "下副四时五行。贵贱更互，冬阴夏阳。\n\n"
            "以人应之奈何？愿闻其方。\n\n"
            "岐伯对曰：妙乎哉问也！此天地之至数。\n\n"
            "ReaderE2E结束"
        ),
        "passage_text": "黄帝问曰：余闻九针于夫子，众多博大，不可胜数。余愿闻要道。",
        "passage_translation": "黄帝问道：我从夫子那里听说了九针，内容广博，不可胜数。我希望听闻要旨。",
        "with_passage": True,
    }
    a_resp = httpx.post(f"{base}/api/v1/_test/seed-reader-data", json=a_body, timeout=10)
    if a_resp.status_code not in (200, 201):
        raise RuntimeError(f"seed-reader-data A failed: {a_resp.status_code} {a_resp.text}")

    # User B: document only (no passage/citation/evidence — minimal isolation fixture)
    b_body = {
        "username": token_b["username"],
        "password": "LibB_Pass123!",
        "document_title": f"用户B的Reader文献-{_uuid.uuid4().hex[:6]}",
        "document_text": (
            "这是用户B的私有文献内容。\n\n"
            "第二段内容。\n\n"
            "第三段内容。"
        ),
        "with_passage": False,
    }
    b_resp = httpx.post(f"{base}/api/v1/_test/seed-reader-data", json=b_body, timeout=10)
    if b_resp.status_code not in (200, 201):
        raise RuntimeError(f"seed-reader-data B failed: {b_resp.status_code} {b_resp.text}")

    seed_a = a_resp.json()["data"]
    seed_b = b_resp.json()["data"]

    # Merge: keep real auth tokens, overlay seed data (doc, chunks, passage_id, etc.)
    doc_a = seed_a["doc"]
    doc_a["id"] = doc_a.get("id") or doc_a.get("document_id")
    doc_b = seed_b["doc"]
    doc_b["id"] = doc_b.get("id") or doc_b.get("document_id")

    return {
        "user_a": {
            **token_a,
            "doc": doc_a,
            "chunks": seed_a.get("chunks", []),
            "passage_id": seed_a.get("passage_id"),
            "evidence_id": seed_a.get("evidence_id"),
            "citation_id": seed_a.get("citation_id"),
        },
        "user_b": {
            **token_b,
            "doc": doc_b,
            "chunks": seed_b.get("chunks", []),
            "passage_id": seed_b.get("passage_id"),
            "evidence_id": seed_b.get("evidence_id"),
            "citation_id": seed_b.get("citation_id"),
        },
    }
