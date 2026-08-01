"""Integration test: A1 evidence provenance for real-end-to-end SourceRef chain.

Upgraded from v4 integration test to full A1 evidence closure:
  trace_id -> passage_id -> source_ref_id/title -> document_id -> Reader href

Uses real ingest/append-passage to construct TWO distinct passages on the
SAME document, then proves each trace maps to its own SourceRef/Reader query
with full UUID precision. No mock, no pseudo document: IDs, no page.route.

Architecture (matching test_critical_journeys.py):
    live_servers  ->  backend (SQLite :memory:) + frontend (Vite dev)
    HTTP API calls for data setup (controlled Document + SourceRef)
    Playwright Chromium for UI interactions
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid

import httpx
import pytest

logger = logging.getLogger(__name__)

# =============================================================================
# Helpers
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


def _is_real_uuid(value: str | None) -> bool:
    """Return True if value looks like a real UUID v4 string (36 chars, 4 hyphens)."""
    if not value or not isinstance(value, str):
        return False
    return len(value) == 36 and value.count("-") == 4


def _is_pseudo_id(value: str | None) -> bool:
    """Return True if value is a pseudo document: or passage: ID."""
    if not value or not isinstance(value, str):
        return False
    return value.startswith("document:") or value.startswith("passage:")


# =============================================================================
# Test
# =============================================================================


class TestV4A1SourceRefMultiPassageClosure:
    """Proves A1 evidence closure across two passages on one document.

    Key invariant per passage P:
      trace_id(P) -> passage_id(P) -> source_ref_id(P) -> document_id(P)
      Reader href = /library/{document_id}?passage={passage_id}
      Click -> Library API 200, page not /login.

    Two passages MUST each point to their own Reader query with full UUID.
    No pseudo document: IDs. No mutual bleed.
    """

    # ------------------------------------------------------------------
    # Data setup
    # ------------------------------------------------------------------

    @staticmethod
    def _create_user(backend_port: int) -> dict:
        return _seed_user(
            backend_port,
            f"a1cls-{_uuid.uuid4().hex[:6]}",
            "A1Close_Pass123!",
        )

    @staticmethod
    def _create_book_chain(
        base_url: str,
        headers: dict,
        doc_title: str,
        source_url: str,
    ) -> dict:
        """Create Person -> Book -> Version -> Chapter, return IDs."""
        # Person
        p_resp = httpx.post(
            f"{base_url}/api/v1/persons",
            json={"name": "皇甫谧（A1闭环保真）", "dynasty": "西晋"},
            headers=headers,
            timeout=10,
        )
        assert p_resp.status_code in (200, 201), f"Person: {p_resp.text[:200]}"
        person_id = p_resp.json()["data"]["id"]

        # Book
        b_resp = httpx.post(
            f"{base_url}/api/v1/books",
            json={"title": doc_title, "dynasty": "西晋", "author_id": person_id},
            headers=headers,
            timeout=10,
        )
        assert b_resp.status_code in (200, 201), f"Book: {b_resp.text[:200]}"
        book_id = b_resp.json()["data"]["id"]

        # Version
        v_resp = httpx.post(
            f"{base_url}/api/v1/versions",
            json={
                "book_id": book_id,
                "version_name": "A1闭环保真本",
                "era": "验证数据",
                "repository": "A1闭环保真库",
                "shelf_mark": "A1-CLOSURE-001",
                "source_url": source_url,
            },
            headers=headers,
            timeout=10,
        )
        assert v_resp.status_code in (200, 201), f"Version: {v_resp.text[:200]}"
        version_id = v_resp.json()["data"]["id"]

        # Chapter
        ch_resp = httpx.post(
            f"{base_url}/api/v1/chapters",
            json={"book_id": book_id, "title": "A1闭环保真章", "order": 1},
            headers=headers,
            timeout=10,
        )
        assert ch_resp.status_code in (200, 201), f"Chapter: {ch_resp.text[:200]}"
        chapter_id = ch_resp.json()["data"]["id"]

        return {
            "person_id": person_id,
            "book_id": book_id,
            "version_id": version_id,
            "chapter_id": chapter_id,
        }

    @staticmethod
    def _create_passage(
        base_url: str,
        headers: dict,
        chapter_id: str,
        version_id: str,
        content_text: str,
        order: int,
        tags: str,
    ) -> str:
        """Create a Passage and return its passage_id."""
        resp = httpx.post(
            f"{base_url}/api/v1/passages",
            json={
                "chapter_id": chapter_id,
                "version_id": version_id,
                "content_text": content_text,
                "order": order,
                "tags": tags,
            },
            headers=headers,
            timeout=10,
        )
        assert resp.status_code in (200, 201), f"Passage: {resp.text[:200]}"
        return resp.json()["data"]["id"]

    @staticmethod
    def _ingest_document(
        base_url: str,
        headers: dict,
        doc_title: str,
        text: str,
        source_url: str,
        source_name: str,
        passage_id: str,
    ) -> str:
        """Ingest text. Returns document_id."""
        body = {
            "title": doc_title,
            "text": text,
            "copyright_status": "public_domain",
            "authorization_basis": "a1-closure-test",
            "source_name": source_name,
            "source_url": source_url,
            "passage_id": passage_id,
        }
        resp = httpx.post(
            f"{base_url}/api/v1/search/ingest",
            json=body,
            headers=headers,
            timeout=15,
        )
        assert resp.status_code in (200, 201), (
            f"Ingest: {resp.status_code} {resp.text[:300]}"
        )
        return resp.json().get("data", resp.json())["document_id"]

    @staticmethod
    def _admin_review(base_url: str, document_id: str) -> None:
        """Admin approve + RAG-enable a document."""
        admin_login = httpx.post(
            f"{base_url}/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=5,
        )
        assert admin_login.status_code == 200, f"Admin login: {admin_login.text[:200]}"
        admin_token = admin_login.json()["data"]["access_token"]

        review = httpx.patch(
            f"{base_url}/api/v1/documents/{document_id}/review",
            json={"review_status": "approved", "rag_enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10,
        )
        assert review.status_code == 200, (
            f"Review: {review.status_code} {review.text[:200]}"
        )

    # ------------------------------------------------------------------
    # Test
    # ------------------------------------------------------------------

    @pytest.mark.e2e
    def test_a1_two_passages_source_ref_closure(
        self,
        live_servers,
        page,
    ):
        """A1 closure: two passages -> two traces -> each maps to own Reader query.

        Proof steps:
        1. Create one document with two distinct passages via ingest + append-passage.
        2. Run workflow, parse runs API for trace->passage->source_ref->doc mapping.
        3. For each of 2 traces with distinct passage_ids:
           a. Click citation in UI
           b. Verify Evidence card shows same trace_id
           c. Verify Evidence passage_id matches runs API mapping
           d. Verify SourceReferenceCard title = expected SourceRef title
           e. Verify source_ref_id is a real UUID (not document: pseudo-ID)
           f. Verify href = /library/{document_id}?passage={passage_id} (full UUID)
           g. Real click on SourceRef link (not page.goto)
           h. Library API returns 200, final URL preserves ?passage=, not /login.
        4. Both passages must each point to their own Reader query.
        """
        frontend_url, backend_port = live_servers
        base = f"http://127.0.0.1:{backend_port}"

        # ---- Phase 1: Create user ----
        user = self._create_user(backend_port)
        user_h = {"Authorization": f"Bearer {user['access_token']}"}

        # ---- Phase 2: Create Book chain ----
        UNIQUE_TITLE = f"A1闭环保真-{_uuid.uuid4().hex[:6]}"
        UNIQUE_URL = f"https://a1-closure.invalid/{_uuid.uuid4().hex[:12]}"

        chain = self._create_book_chain(base, user_h, UNIQUE_TITLE, UNIQUE_URL)

        # ---- Phase 3: Two passages with distinctive content ----
        SEARCH_TERM = "A1标识"

        passage_1_text = (
            f"{SEARCH_TERM} 黄帝问曰：余闻九针于夫子，众多博大，不可胜数。余愿闻要道。"
        )
        passage_2_text = (
            f"{SEARCH_TERM} 天地之至数，始于一终于九焉。一者天二者地三者人。三部九候以决死生。"
        )

        passage_1_id = self._create_passage(
            base, user_h, chain["chapter_id"], chain["version_id"],
            passage_1_text, order=1, tags="A1-passage-1",
        )
        passage_2_id = self._create_passage(
            base, user_h, chain["chapter_id"], chain["version_id"],
            passage_2_text, order=2, tags="A1-passage-2",
        )

        # ---- Phase 4: Ingest document with passage 1 ----
        ingest_text = (
            f"{SEARCH_TERM}\n\n"
            "黄帝问曰：余闻九针于夫子，众多博大，不可胜数。"
            "余愿闻要道，以属子孙，传之后世。\n\n"
            "A1闭环保真结束"
        )
        doc_id = self._ingest_document(
            base, user_h, UNIQUE_TITLE, ingest_text,
            source_url=UNIQUE_URL, source_name="a1-passage-1-source",
            passage_id=passage_1_id,
        )

        # ---- Phase 5: Append passage 2 ----
        append_text = (
            f"{SEARCH_TERM}\n\n"
            "天地之至数，始于一，终于九焉。"
            "一者天，二者地，三者人。\n\n"
            "故人有三部，部有三候，以决死生，以处百病。\n\n"
            "A1闭环保真附加结束"
        )

        # Try user first; fall back to admin if user lacks document.update
        append_resp = httpx.post(
            f"{base}/api/v1/search/documents/{doc_id}/append-passage",
            json={"text": append_text, "passage_id": passage_2_id},
            headers=user_h, timeout=15,
        )
        if append_resp.status_code == 403:
            admin_login = httpx.post(
                f"{base}/api/v1/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=5,
            )
            assert admin_login.status_code == 200, f"Admin login: {admin_login.text[:200]}"
            admin_token = admin_login.json()["data"]["access_token"]
            append_resp = httpx.post(
                f"{base}/api/v1/search/documents/{doc_id}/append-passage",
                json={"text": append_text, "passage_id": passage_2_id},
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=15,
            )
        assert append_resp.status_code in (200, 201), (
            f"AppendPassage: {append_resp.status_code} {append_resp.text[:300]}"
        )
        append_data = append_resp.json().get("data", append_resp.json())
        assert append_data.get("appended_chunk_count", 0) > 0, (
            "Append should create at least one chunk"
        )

        # ---- Phase 6: Admin review + RAG enable ----
        self._admin_review(base, doc_id)

        # ---- Phase 7: Create research session ----
        sess_resp = httpx.post(
            f"{base}/api/v1/workspace/sessions",
            json={"title": "A1闭环保真研究"},
            headers=user_h,
            timeout=10,
        )
        assert sess_resp.status_code in (200, 201), f"Session: {sess_resp.text[:200]}"
        session_id = sess_resp.json()["data"]["id"]

        # ---- Phase 8: Browser login + workflow submit ----
        _login_via_ui(page, frontend_url, user["username"], "A1Close_Pass123!")

        page.goto(f"{frontend_url}/research/{session_id}/workflow")
        page.wait_for_selector("#rqs-input", timeout=10000)

        page.fill("#rqs-input", f"{SEARCH_TERM} 三部九候 天地之至数")
        page.click(".rqs-submit-btn")
        page.wait_for_selector(".dss-submit-btn", timeout=5000)
        page.click(".dss-submit-btn")

        # Wait for evidence step
        try:
            page.wait_for_selector(".ers-step", timeout=180000)
        except (TimeoutError, RuntimeError):
            error_text = ""
            err = page.locator(".rwf-error-banner-message")
            if err.count() > 0:
                error_text = err.first.text_content()
            raise AssertionError(
                f"Workflow should find evidence. Error: {error_text}. "
                f"Doc: {doc_id} Session: {session_id}"
            )

        # ---- Phase 9: Navigate to report step then result page ----
        # Click the "查看研究报告" button on the evidence step
        page.locator(".ers-action-btn").click()
        page.wait_for_selector(".rrs-step", timeout=5000)

        result_link = page.locator(".rrs-action-btn--primary").first
        assert result_link.count() > 0, "Result link should be visible"

        result_href = result_link.get_attribute("href")
        page.goto(
            frontend_url
            + (result_href if result_href.startswith("/") else f"/{result_href}")
        )
        page.wait_for_load_state("networkidle", timeout=10000)
        page.wait_for_timeout(2000)

        # =====================================================================
        # Phase 10: Parse runs API -> build trace->passage->source_ref mapping
        # =====================================================================
        runs_resp = httpx.get(
            f"{base}/api/v4/research/session/{session_id}/runs",
            headers=user_h,
            timeout=10,
        )
        assert runs_resp.status_code == 200, f"Runs API: {runs_resp.text[:200]}"
        runs_data = runs_resp.json().get("data", {}).get("runs", [])
        assert len(runs_data) > 0, "Should have at least one run"

        manifest = runs_data[-1].get("replay_manifest", {})
        retrieval_snapshot = manifest.get("retrieval_snapshot", [])
        assert len(retrieval_snapshot) > 0, "Retrieval snapshot should have entries"

        # Build trace_id -> passage_id from canonical traces (most reliable)
        trace_to_passage: dict[str, str] = {}
        for tr in manifest.get("traces", []):
            tid = tr.get("trace_id", "")
            pid = tr.get("passage_id", "")
            if tid and pid:
                trace_to_passage[tid] = pid

        # Build trace_id -> {source_ref_id, source_ref_title, document_id}
        trace_to_sr: dict[str, dict] = {}
        for rec in retrieval_snapshot:
            tid = rec.get("trace_id", "")
            if not tid:
                continue
            # Fallback: snapshot may have passage_id when traces don't
            if tid not in trace_to_passage:
                pid = rec.get("passage_id", "")
                if pid:
                    trace_to_passage[tid] = pid
            trace_to_sr[tid] = {
                "source_ref_id": rec.get("source_ref_id"),
                "source_ref_title": rec.get("source_ref_title"),
                "document_id": rec.get("document_id"),
            }

        assert len(trace_to_sr) >= 2, (
            f"Need at least 2 snapshot entries, got {len(trace_to_sr)}"
        )

        # Validate every trace has required fields — fail immediately if any missing
        for tid, sr in trace_to_sr.items():
            assert sr["source_ref_id"] is not None, (
                f"T={tid}: source_ref_id must not be None"
            )
            assert not _is_pseudo_id(sr["source_ref_id"]), (
                f"T={tid}: source_ref_id is pseudo: {sr['source_ref_id']!r}"
            )
            assert _is_real_uuid(sr["source_ref_id"]), (
                f"T={tid}: source_ref_id not a real UUID: {sr['source_ref_id']!r}"
            )
            assert sr["source_ref_title"], (
                f"T={tid}: source_ref_title must be non-empty"
            )
            assert sr["document_id"] is not None, (
                f"T={tid}: document_id must not be None"
            )

        # Validate passage mapping exists for each trace
        for tid in trace_to_sr:
            assert tid in trace_to_passage, (
                f"T={tid}: no passage_id in canonical traces or snapshot. "
                f"Traces count: {len(manifest.get('traces', []))}, "
                f"Snapshot count: {len(retrieval_snapshot)}"
            )
            pid = trace_to_passage[tid]
            assert _is_real_uuid(pid), (
                f"T={tid}: passage_id not a real UUID: {pid!r}"
            )

        # =====================================================================
        # Phase 11: Select at least two traces with distinct passage_ids
        # =====================================================================
        distinct_passages = list(dict.fromkeys(trace_to_passage.values()))
        assert len(distinct_passages) >= 2, (
            f"Need >= 2 distinct passage_ids in traces, "
            f"got {len(distinct_passages)}: {distinct_passages}. "
            f"Expected at least: P1={passage_1_id}, P2={passage_2_id}"
        )

        # Pick one trace per distinct passage
        selected: list[dict] = []
        seen_pids: set[str] = set()
        for tid, pid in trace_to_passage.items():
            if pid not in seen_pids and tid in trace_to_sr:
                sr = trace_to_sr[tid]
                selected.append({
                    "trace_id": tid,
                    "passage_id": pid,
                    "source_ref_id": sr["source_ref_id"],
                    "source_ref_title": sr["source_ref_title"],
                    "document_id": sr["document_id"],
                })
                seen_pids.add(pid)
            if len(selected) >= 2:
                break

        assert len(selected) >= 2, (
            f"Could not select 2 traces with distinct passages. Found: {selected}"
        )

        # =====================================================================
        # Phase 12: Build DOM citation index
        # =====================================================================
        citation_items = page.locator(".rcp-citation-item")
        assert citation_items.count() > 0, "At least one citation item expected"

        dom_trace_prefixes: list[tuple[int, str]] = []
        for i in range(citation_items.count()):
            item = citation_items.nth(i)
            code_el = item.locator(".rcp-citation-id")
            if code_el.count() > 0:
                prefix = (code_el.first.text_content() or "").strip()
                dom_trace_prefixes.append((i, prefix))

        def _match_trace(api_tid: str) -> int | None:
            for idx, prefix in dom_trace_prefixes:
                if prefix and prefix.startswith(api_tid[:16]):
                    return idx
            return None

        # =====================================================================
        # Phase 13: For each selected trace, click citation + verify chain
        # =====================================================================
        verified_passages = 0
        reader_api_200_count = 0

        for sel in selected:
            tid = sel["trace_id"]
            pid = sel["passage_id"]
            sr_id = sel["source_ref_id"]
            sr_title = sel["source_ref_title"]
            did = sel["document_id"]
            expected_href = f"/library/{did}?passage={pid}"

            # ---- 13a: Find and click the citation item ----
            cit_idx = _match_trace(tid)
            assert cit_idx is not None, (
                f"T={tid}: citation not found in panel. "
                f"DOM prefixes: {dom_trace_prefixes}"
            )

            citation_items.nth(cit_idx).click()
            page.wait_for_timeout(1500)

            # ---- 13b: Evidence detail card visible + shows this trace_id ----
            evidence_card = page.locator(".eed-card")
            assert evidence_card.count() > 0, (
                f"T={tid}: Evidence detail card should be visible"
            )

            # Evidence card shows trace_id as first 16 chars + "..."
            ev_text = evidence_card.first.text_content() or ""
            assert tid[:16] in ev_text, (
                f"T={tid}: Evidence card should display trace_id prefix. "
                f"Card text: {ev_text[:300]}"
            )

            # ---- 13c: Evidence passage_id matches runs API ----
            passage_meta_rows = page.locator(".eed-meta-row")
            found_passage = False
            visible_passage = ""
            for j in range(passage_meta_rows.count()):
                row = passage_meta_rows.nth(j)
                label_el = row.locator(".eed-meta-label")
                if label_el.count() > 0 and "Passage" in (label_el.first.text_content() or ""):
                    value_el = row.locator(".eed-meta-value")
                    if value_el.count() > 0:
                        visible_passage = (value_el.first.text_content() or "").strip()
                        found_passage = True
                        break

            assert found_passage, (
                f"T={tid}: Evidence card should show Passage ID row. P={pid}"
            )

            visible_prefix = visible_passage.rstrip("...").strip()
            assert pid.startswith(visible_prefix), (
                f"T={tid}: Evidence passage_id mismatch. "
                f"Expected prefix of {pid}, got visible: {visible_prefix!r}"
            )

            # ---- 13d: SourceReferenceCard visible + title matches ----
            src_card = page.locator(".esrc-card")
            assert src_card.count() > 0, (
                f"T={tid}: SourceReferenceCard should be visible"
            )

            src_text = src_card.first.text_content() or ""
            assert "缺少来源文献" not in src_text, (
                f"T={tid}: SourceRef card shows '缺少来源文献'. "
                f"Expected source_ref_title={sr_title}, P={pid}"
            )

            assert sr_title in src_text, (
                f"T={tid}: SourceRef card should display title '{sr_title}'. "
                f"Card text: {src_text[:200]}"
            )

            # ---- 13e: source_ref_id in api is real UUID (validated in phase 10) ----
            # no-op — already validated in Phase 10 loop

            # ---- 13f: SourceRef href = /library/{doc}?passage={pid} ----
            source_link = page.locator(".esrc-link")
            assert source_link.count() > 0, (
                f"T={tid}: SourceRef link (.esrc-link) should be visible"
            )
            actual_href = (source_link.first.get_attribute("href") or "").strip()
            assert actual_href == expected_href, (
                f"T={tid}: SourceRef href mismatch.\n"
                f"  Expected: {expected_href}\n"
                f"  Actual:   {actual_href}"
            )

            # ---- 13g: Real click on SourceRef link (not page.goto) ----
            captured_200: list[str] = []

            def _capture(response):
                url = response.url
                if f"/api/v1/documents/{did}" in url and "/reader" not in url and "/stats" not in url:
                    if response.status == 200:
                        captured_200.append(response.url)

            page.on("response", _capture)
            source_link.first.click()
            page.wait_for_load_state("networkidle", timeout=15000)
            page.wait_for_timeout(2000)
            try:
                page.remove_listener("response", _capture)
            except Exception:
                pass

            # ---- 13h: Library document API returned 200 ----
            assert len(captured_200) > 0, (
                f"T={tid}: /api/v1/documents/{did} should return 200 "
                f"after clicking SourceRef link. Captured: {captured_200}"
            )
            reader_api_200_count += 1

            # ---- 13i: Not on /login + URL preserves ?passage= ----
            current_url = page.url
            assert "/login" not in current_url, (
                f"T={tid}: Navigation landed on /login. URL: {current_url}"
            )
            assert f"passage={pid}" in current_url, (
                f"T={tid}: URL missing passage query. "
                f"Expected passage={pid}. URL: {current_url}"
            )

            verified_passages += 1

            # Navigate back to result page for next check
            page.goto(
                frontend_url
                + (result_href if result_href.startswith("/") else f"/{result_href}")
            )
            page.wait_for_load_state("networkidle", timeout=10000)
            page.wait_for_timeout(1500)

        # =====================================================================
        # Phase 14: Final assertions
        # =====================================================================
        assert verified_passages >= 2, (
            f"Must verify at least 2 passages. Verified: {verified_passages}"
        )
        assert reader_api_200_count >= 2, (
            f"Both passages' Library APIs must return 200. "
            f"Count: {reader_api_200_count}"
        )

        # SourceRef ID from snapshot must be real UUID
        for sel in selected:
            assert _is_real_uuid(sel["source_ref_id"]), (
                f"T={sel['trace_id']}: source_ref_id not real UUID: "
                f"{sel['source_ref_id']!r}"
            )

        print("\nA1 SourceRef closure verified (multi-passage):")
        print(f"  Document: {doc_id}")
        print(f"  Session:  {session_id}")
        print(f"  Verified passages: {verified_passages}")
        for s in selected:
            print(f"    T={s['trace_id'][:16]}... P={s['passage_id'][:16]}... "
                  f"SR={s['source_ref_title'][:30]}...")
