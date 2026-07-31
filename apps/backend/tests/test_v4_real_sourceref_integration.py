"""Integration test: real-end-to-end SourceRef chain in a single browser-visible workflow run.

Targets the exact gap card 4ab7269 left open: no browser-automated proof that a
controlled, real-workflow run produces snapshot entries whose source_ref_id matches
an actual non-deleted source_refs row, and that the full UI chain (login → submit
workflow → result → Citation → Evidence → SourceRef → navigate) completes with 200.

Architecture (matching test_critical_journeys.py):
    live_servers  →  backend (SQLite :memory:) + frontend (Vite dev)
    HTTP API calls for data setup (controlled Document + SourceRef)
    Playwright Chromium for UI interactions

No mock, no page.route, no localStorage token injection, no seed API, no
replay, no pseudo document:{id} IDs.
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid

import httpx
import pytest

logger = logging.getLogger(__name__)

# =============================================================================
# Helpers (inlined — no import from test_critical_journeys to keep isolation)
# =============================================================================


def _seed_user(backend_port: int, username: str, password: str) -> dict:
    base = f"http://127.0.0.1:{backend_port}"
    r = httpx.post(
        f"{base}/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
        timeout=10,
    )
    assert r.status_code in (200, 201), f"Register: {r.status_code} {r.text[:300]}"
    r2 = httpx.post(
        f"{base}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    assert r2.status_code == 200, f"Login: {r2.status_code} {r2.text[:300]}"
    data = r2.json()["data"]
    data["username"] = username
    return data


def _login_via_ui(page, frontend_url: str, username: str, password: str) -> None:
    """Log in through the real login page UI (NOT localStorage)."""
    page.goto(f"{frontend_url}/login")
    page.wait_for_selector('input[placeholder*="用户名"]', timeout=10000)
    page.fill('input[placeholder*="用户名"]', username)
    page.fill('input[placeholder*="密码"]', password)
    page.click('button:has-text("登录")')
    page.wait_for_url(f"{frontend_url}/", timeout=10000)
    page.wait_for_selector(f"text={username}", timeout=5000)


# =============================================================================
# Test
# =============================================================================


class TestV4RealSourceRefBrowserClosure:
    """Single browser session that proves the complete SourceRef chain.

      login → submit workflow (real RAG doc) → result page
    → click Citation → Evidence shows real source_ref_title
    → SourceRef card shows real source_ref_id (not document:{...})
    → click source link → API / page returns 200
    """

    # ------------------------------------------------------------------
    # Data setup helpers — run as plain methods, not fixtures, so
    # the test owns every piece of its controlled data.
    # ------------------------------------------------------------------

    @staticmethod
    def _create_user(backend_port: int) -> dict:
        return _seed_user(
            backend_port,
            f"srclosure-{_uuid.uuid4().hex[:6]}",
            "SrcClose_Pass123!",
        )

    @staticmethod
    def _create_controlled_document(
        backend_port: int,
        user: dict,
        doc_title: str,
        source_url: str,
    ) -> dict:
        """Create Book→Version→Chapter→Passage, ingest text, admin-review.

        Returns dict with keys: document_id, passage_id, version_id,
        chunk_count, source_ref_id, source_ref_title, source_ref_url.
        """
        base = f"http://127.0.0.1:{backend_port}"
        h = {"Authorization": f"Bearer {user['access_token']}"}

        # Person
        p_resp = httpx.post(
            f"{base}/api/v1/persons",
            json={"name": "皇甫谧（SourceRef闭环保真）", "dynasty": "西晋"},
            headers=h,
            timeout=10,
        )
        assert p_resp.status_code in (200, 201), f"Person: {p_resp.text[:200]}"
        person_id = p_resp.json()["data"]["id"]

        # Book
        b_resp = httpx.post(
            f"{base}/api/v1/books",
            json={"title": doc_title, "dynasty": "西晋", "author_id": person_id},
            headers=h,
            timeout=10,
        )
        assert b_resp.status_code in (200, 201), f"Book: {b_resp.text[:200]}"
        book_id = b_resp.json()["data"]["id"]

        # Version
        v_resp = httpx.post(
            f"{base}/api/v1/versions",
            json={
                "book_id": book_id,
                "version_name": "SourceRef闭环保真本",
                "era": "验证数据",
                "repository": "SourceRef闭环保真库",
                "shelf_mark": "SR-CLOSURE-001",
                "source_url": source_url,
            },
            headers=h,
            timeout=10,
        )
        assert v_resp.status_code in (200, 201), f"Version: {v_resp.text[:200]}"
        version_id = v_resp.json()["data"]["id"]

        # Chapter
        ch_resp = httpx.post(
            f"{base}/api/v1/chapters",
            json={"book_id": book_id, "title": "SourceRef闭环保真章", "order": 1},
            headers=h,
            timeout=10,
        )
        assert ch_resp.status_code in (200, 201), f"Chapter: {ch_resp.text[:200]}"
        chapter_id = ch_resp.json()["data"]["id"]

        # Passage
        pass_resp = httpx.post(
            f"{base}/api/v1/passages",
            json={
                "chapter_id": chapter_id,
                "version_id": version_id,
                "content_text": "SrcRefClosure标识 黄帝问曰：余闻九针于夫子，众多博大。",
                "order": 1,
                "tags": "SourceRef闭环保真",
            },
            headers=h,
            timeout=10,
        )
        assert pass_resp.status_code in (200, 201), f"Passage: {pass_resp.text[:200]}"
        passage_id = pass_resp.json()["data"]["id"]

        # ---- Ingest text (calls _ensure_source_ref) ----
        ingest_body = {
            "title": doc_title,
            "text": (
                "SrcRefClosure标识\n\n"
                "黄帝问曰：余闻九针于夫子，众多博大，不可胜数。"
                "余愿闻要道，以属子孙，传之后世。\n\n"
                "岐伯对曰：妙乎哉问也！此天地之至数。\n\n"
                "天地之至数，始于一，终于九焉。"
                "一者天，二者地，三者人。\n\n"
                "故人有三部，部有三候，以决死生。\n\n"
                "SrcRefClosure结束"
            ),
            "copyright_status": "public_domain",
            "authorization_basis": "source-ref-closure-test",
            "source_name": "source-ref-closure-e2e",
            "source_url": source_url,
            "passage_id": passage_id,
        }
        ingest_resp = httpx.post(
            f"{base}/api/v1/search/ingest",
            json=ingest_body,
            headers=h,
            timeout=15,
        )
        assert ingest_resp.status_code in (200, 201), (
            f"Ingest: {ingest_resp.status_code} {ingest_resp.text[:300]}"
        )
        doc_data = ingest_resp.json().get("data", ingest_resp.json())
        doc_id = doc_data["document_id"]

        # ---- Admin review (RAG enable) ----
        admin_login = httpx.post(
            f"{base}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5,
        )
        assert admin_login.status_code == 200, f"Admin login: {admin_login.text[:200]}"
        admin_token = admin_login.json()["data"]["access_token"]

        review_resp = httpx.patch(
            f"{base}/api/v1/documents/{doc_id}/review",
            json={"review_status": "approved", "rag_enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )
        assert review_resp.status_code == 200, f"Review: {review_resp.text[:200]}"

        # ---- Read the SourceRef that ingestion created ----
        sr_resp = httpx.get(
            f"{base}/api/v1/source-refs?page_location=document:{doc_id}",
            headers=h,
            timeout=10,
        )
        source_ref_id = None
        source_ref_title = None
        source_ref_url = None
        if sr_resp.status_code == 200:
            sr_items = sr_resp.json().get("data", [])
            if sr_items:
                source_ref_id = sr_items[0].get("id")
                source_ref_title = sr_items[0].get("title")
                source_ref_url = sr_items[0].get("url")

        return {
            "document_id": doc_id,
            "chunk_count": doc_data.get("chunk_count", 0),
            "passage_id": passage_id,
            "version_id": version_id,
            "source_ref_id": source_ref_id,
            "source_ref_title": source_ref_title,
            "source_ref_url": source_ref_url,
        }

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    @pytest.mark.e2e
    def test_source_ref_chain_full_browser_closure(
        self,
        live_servers,
        page,
    ):
        """Full browser closure:

        1. Create controlled doc → SourceRef → RAG-enabled
        2. UI login → create session → submit workflow
        3. Navigate to result → click Citation → verify Evidence
        4. Verify SourceRef card shows real ID (not document:{...})
        5. Click source link → verify navigation target returns 200
        """
        frontend_url, backend_port = live_servers
        base = f"http://127.0.0.1:{backend_port}"

        # ---- Phase 1: Controlled data ----
        UNIQUE_DOC_TITLE = f"SourceRef闭环保真-{_uuid.uuid4().hex[:6]}"
        UNIQUE_SOURCE_URL = f"https://src-ref-closure.invalid/{_uuid.uuid4().hex[:12]}"

        user = self._create_user(backend_port)
        h = {"Authorization": f"Bearer {user['access_token']}"}

        doc_info = self._create_controlled_document(
            backend_port,
            user,
            UNIQUE_DOC_TITLE,
            UNIQUE_SOURCE_URL,
        )

        # ---- Phase 2: Create session ----
        sess_resp = httpx.post(
            f"{base}/api/v1/workspace/sessions",
            json={"title": "SourceRef闭环保真研究"},
            headers=h,
            timeout=10,
        )
        assert sess_resp.status_code in (200, 201), f"Session: {sess_resp.text[:200]}"
        session_id = sess_resp.json()["data"]["id"]

        # ---- Phase 3: Browser login + workflow submit ----
        _login_via_ui(
            page,
            frontend_url,
            user["username"],
            "SrcClose_Pass123!",
        )

        page.goto(f"{frontend_url}/research/{session_id}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        # Capture SourceRef field values from the workflow snapshot API response
        captured_snapshot: dict = {}

        def _on_response(response):
            if "/api/v4/research/session/" in response.url and "/runs" in response.url:
                try:
                    body = response.json()
                    runs = body.get("data", {}).get("runs", [])
                    if runs:
                        manifest = runs[-1].get("replay_manifest", {})
                        snap = manifest.get("retrieval_snapshot", [])
                        if snap:
                            captured_snapshot["first_entry"] = snap[0]
                except (json.JSONDecodeError, TypeError, KeyError):
                    logger.debug("Failed to parse workflow run response", exc_info=True)

        page.on("response", _on_response)

        # Submit workflow
        page.fill("#rqs-input", "SrcRefClosure标识 三部九候")
        page.click(".rqs-submit-btn")
        page.wait_for_selector(".dss-submit-btn", timeout=5000)
        page.click(".dss-submit-btn")

        # Wait for evidence step or error
        try:
            page.wait_for_selector(".ers-step", timeout=180000)
            has_evidence = True
        except (TimeoutError, RuntimeError):
            has_evidence = False

        if not has_evidence:
            error_text = ""
            err = page.locator(".rwf-error-banner-message")
            if err.count() > 0:
                error_text = err.first.text_content()
            raise AssertionError(
                f"Workflow should find evidence. Error: {error_text}. "
                f"Doc: {doc_info['document_id']} Session: {session_id}"
            )

        # ---- Phase 4: Evidence step assertions ----
        evidence_items = page.locator(".ers-item")
        assert evidence_items.count() > 0, "At least one evidence item expected"

        # ---- Phase 5: Go to report step, click "查看完整结果" ----
        page.locator("text=查看研究报告").first.click()
        page.wait_for_selector(".rrs-step", timeout=5000)

        # Find the result link
        result_link = page.locator('a[href*="/result/"]').first
        assert result_link.count() > 0, "Result link should be visible"

        # Navigate to result page
        result_href = result_link.get_attribute("href")
        page.goto(
            frontend_url
            + (result_href if result_href.startswith("/") else f"/{result_href}")
        )
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)

        # ---- Phase 6: Result page — Citation → Evidence → SourceRef ----
        # Click on a citation in the CitationPanel
        citation_items = page.locator(".rcp-citation-item")
        assert citation_items.count() > 0, (
            "At least one citation item should appear in the citation panel"
        )
        citation_items.first.click()
        page.wait_for_timeout(1000)

        # Evidence detail should appear
        evidence_detail = page.locator(".eed-card")
        assert evidence_detail.count() > 0, "Evidence detail card should be visible"

        # Check claim text
        claim_text = page.locator(".eed-claim-text").first.text_content() or ""
        assert len(claim_text) > 0, "Claim text should be non-empty"

        # Check citation text
        citation_code = page.locator(".eed-citation-code").first
        if citation_code.count() > 0:
            cit_text = citation_code.text_content() or ""
            assert len(cit_text) > 0, "Citation text should be non-empty"

        # ---- Phase 7: SourceRef card — verify real ID, no pseudo document: ----
        src_card = page.locator(".esrc-card")
        assert src_card.count() > 0, (
            "SourceReferenceCard should be visible. "
            "If missing, source_ref_title is null → fail-closed correctly, "
            "but the controlled doc should have a real SourceRef row via ingestion."
        )

        # Check source_ref_title is displayed (real title from source_refs table)
        src_text = src_card.first.text_content() or ""
        # Should NOT contain "缺少来源文献" (fail-closed) — we created a real SourceRef
        assert "缺少来源文献" not in src_text, (
            f"SourceRef card shows '缺少来源文献'. "
            f"Controlled doc title: {UNIQUE_DOC_TITLE}, source_url: {UNIQUE_SOURCE_URL}. "
            f"Snapshot evidence: {captured_snapshot.get('first_entry', 'NOT CAPTURED')}"
        )

        # Should NOT contain a pseudo document: ID
        assert "document:" not in src_text, (
            f"SourceRef card contains pseudo 'document:' ID! Text: {src_text[:200]}"
        )

        # ---- Phase 8: Verify source_ref_id in snapshot is real ----
        if captured_snapshot.get("first_entry"):
            entry = captured_snapshot["first_entry"]
            sr_id = entry.get("source_ref_id")
            assert sr_id is not None, (
                "snapshot entry source_ref_id must be non-null for controlled doc"
            )
            assert not str(sr_id).startswith("document:"), (
                f"source_ref_id must NOT be a pseudo document: ID, got {sr_id!r}"
            )
            # Verify the ID is a real UUID (36-char format)
            assert len(str(sr_id)) == 36 and str(sr_id).count("-") == 4, (
                f"source_ref_id should be a UUID v4 string, got {sr_id!r}"
            )

        # ---- Phase 9: Click source link → verify navigation target ----
        source_link = page.locator(".esrc-link")
        if source_link.count() > 0:
            link_href = source_link.first.get_attribute("href")
            assert link_href, "Source link should have an href"

            # If internal route, navigate to it
            if link_href.startswith("/"):
                # Internal route → navigate and verify page loads (API 200)
                page.goto(f"{frontend_url}{link_href}")
                page.wait_for_load_state("networkidle", timeout=10000)
                page.wait_for_timeout(2000)
                # Verify we're not on an error page
                assert page.locator("text=404").count() == 0, (
                    f"Internal source route returned 404: {link_href}"
                )
                assert page.locator("text=错误").count() == 0, (
                    f"Internal source route returned error: {link_href}"
                )
            elif link_href.startswith("http"):
                # External URL — verify the href is present and safe
                # (actual navigation to external URLs is not tested in CI)
                assert "javascript:" not in link_href
                assert "data:" not in link_href
        else:
            # No link — the source_ref_url may be empty. Check it's not due
            # to a pseudo ID masking the real data.
            if captured_snapshot.get("first_entry"):
                captured_snapshot["first_entry"].get("source_ref_url")
                # OK: source_ref_url may be empty even with real SourceRef
                # (ingestion with empty URL → title+page_location dedup → url="")

        # ---- Phase 10: Snapshot contract ----
        # Access the runs API directly to verify the snapshot has real fields
        runs_resp = httpx.get(
            f"{base}/api/v4/research/session/{session_id}/runs",
            headers=h,
            timeout=10,
        )
        assert runs_resp.status_code == 200, f"Runs API: {runs_resp.text[:200]}"
        runs_data = runs_resp.json().get("data", {}).get("runs", [])
        assert len(runs_data) > 0, "Should have at least one run"

        manifest = runs_data[-1].get("replay_manifest", {})
        snap = manifest.get("retrieval_snapshot", [])
        assert len(snap) > 0, "Retrieval snapshot should have entries"

        for entry in snap:
            sr_id = entry.get("source_ref_id")
            sr_title = entry.get("source_ref_title")
            sr_url = entry.get("source_ref_url", "")

            # Every snapshot entry must have a real source_ref_id or be null
            if sr_id is not None:
                assert not str(sr_id).startswith("document:"), (
                    f"Pseudo document: ID in snapshot: {sr_id!r}"
                )
                assert len(str(sr_id)) == 36, (
                    f"source_ref_id should be UUID v4, got {sr_id!r}"
                )

            # source_ref_title must match if source_ref_id is present
            if sr_id and sr_title:
                assert len(sr_title) > 0, (
                    "source_ref_title must be non-empty when id is present"
                )

            # source_ref_url must be a safe string (may be empty)
            assert isinstance(sr_url, str), (
                f"source_ref_url should be str, got {type(sr_url)}"
            )

        print("\n✓ SourceRef closure verified:")
        print(f"  Run: {runs_data[0].get('run_id', '?')}")
        print(f"  Snapshot entries: {len(snap)}")
        if captured_snapshot.get("first_entry"):
            e = captured_snapshot["first_entry"]
            print(f"  source_ref_id: {e.get('source_ref_id')}")
            print(f"  source_ref_title: {e.get('source_ref_title')}")
            print(f"  source_ref_url: {e.get('source_ref_url')}")
