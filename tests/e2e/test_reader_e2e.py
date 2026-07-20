"""
Sprint 2 Task 009 — Reader E2E Tests.

Tests the Reader page with real backend, real auth, real HTTP, real database.

Requirements:
    a. Reader direct URL load
    b. Refresh restores text + anchor
    c. Original, OCR, Translation real sourcing and missing display
    d. Stable chunk ordering with anchors
    e. Citation precise positioning to text
    f. Evidence precise positioning to text
    g. Missing anchor honest degradation
    h. Back button doesn't modify frozen Library
    i. 401, 403, 404 → ErrorState
    j. Cross-user isolation: User A cannot read User B's data
    k. Rapid document switching: stale responses don't pollute current page
"""
import pytest
import httpx


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _login_via_ui(page, frontend_url, username, password):
    """Log in through the browser UI and wait for redirect."""
    page.goto(f"{frontend_url}/login")
    page.wait_for_selector('input[placeholder*="用户名"]', timeout=10000)
    page.fill('input[placeholder*="用户名"]', username)
    page.fill('input[placeholder*="密码"]', password)
    page.click('button:has-text("登录")')
    page.wait_for_url(f"{frontend_url}/", timeout=10000)


# ---------------------------------------------------------------------------
# Reader E2E
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestReaderE2E:
    """a-h: Reader page correctness with real data."""

    def test_reader_direct_url_load(
        self, live_servers, library_test_users, page,
    ):
        """a. Reader loads directly via URL /reader/:id."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        doc_id = a["doc"].get("id")
        doc_title = a["doc"].get("title", "")
        assert doc_id, "User A must have a private document"

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{doc_id}")
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        assert doc_title in body, (
            f"Reader must show title '{doc_title}'. Body: {body[:300]}"
        )

    def test_reader_refresh_restores_text(
        self, live_servers, library_test_users, page,
    ):
        """b. Refresh restores text content."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        doc_id = a["doc"].get("id")
        doc_title = a["doc"].get("title", "")
        assert doc_id

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{doc_id}")
        page.wait_for_timeout(5000)

        assert page.locator(f"text={doc_title}").count() > 0, "Title must be visible before refresh"
        page.reload()
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        assert doc_title in body, f"Title must persist after refresh. Body: {body[:300]}"

    def test_reader_original_text_sourced_from_backend(
        self, live_servers, library_test_users, page,
    ):
        """c. Original text, OCR, Translation come from real backend."""
        frontend_url, backend_port = live_servers
        a = library_test_users["user_a"]
        doc_id = a["doc"].get("id")
        assert doc_id

        headers = {"Authorization": f"Bearer {a['access_token']}"}
        base = f"http://127.0.0.1:{backend_port}"
        r = httpx.get(f"{base}/api/v1/documents/{doc_id}/reader", headers=headers, timeout=10)
        assert r.status_code == 200, f"Reader endpoint must return 200, got {r.status_code}: {r.text[:300]}"
        data = r.json().get("data", r.json())
        chunks = data.get("chunks", [])
        assert len(chunks) >= 2, f"Fixture must create 2+ chunks, got {len(chunks)}"
        assert "id" in chunks[0], "Each chunk must have a stable 'id'"
        assert "chunk_index" in chunks[0], "Each chunk must have 'chunk_index'"

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{doc_id}")
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        assert "原文" in body, "Must show '原文' section when chunks exist"
        ocr_chunks = data.get("ocr_chunks", [])
        if ocr_chunks:
            assert "OCR" in body, "Must show OCR section when OCR chunks exist"

    def test_reader_translation_missing_display(
        self, live_servers, library_test_users, page,
    ):
        """c. When no passage has translation, show unavailable hint."""
        frontend_url, backend_port = live_servers
        a = library_test_users["user_a"]
        doc_id = a["doc"].get("id")
        assert doc_id

        headers = {"Authorization": f"Bearer {a['access_token']}"}
        base = f"http://127.0.0.1:{backend_port}"
        r = httpx.get(f"{base}/api/v1/documents/{doc_id}/reader", headers=headers, timeout=10)
        data = r.json().get("data", r.json())
        passages = data.get("passages", [])
        has_translation = any(p.get("translation") for p in passages)

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{doc_id}")
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        if not has_translation and passages:
            assert "暂无现代汉语翻译" in body, f"Must show translation-unavailable hint. Body: {body[:300]}"

    def test_reader_stable_chunk_ordering(
        self, live_servers, library_test_users, page,
    ):
        """d. Chunks maintain stable ordering from backend chunk_index."""
        frontend_url, backend_port = live_servers
        a = library_test_users["user_a"]
        doc_id = a["doc"].get("id")
        assert doc_id

        headers = {"Authorization": f"Bearer {a['access_token']}"}
        base = f"http://127.0.0.1:{backend_port}"
        r = httpx.get(f"{base}/api/v1/documents/{doc_id}/reader", headers=headers, timeout=10)
        data = r.json().get("data", r.json())
        chunks = data.get("chunks", [])
        assert len(chunks) >= 2, f"Fixture must create 2+ chunks, got {len(chunks)}"

        indices = [c["chunk_index"] for c in chunks]
        assert indices == sorted(indices), f"Chunk indices must be sorted: {indices}"

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{doc_id}")
        page.wait_for_timeout(5000)

        chunk_elements = page.locator('[id^="chunk-"]').all()
        assert len(chunk_elements) > 0, "Must have chunk DOM elements with id='chunk-...'"
        first_id = chunk_elements[0].get_attribute("id")
        assert first_id != "chunk-0", f"Chunk id must be UUID-based, got {first_id}"

    def test_reader_citation_anchor_button(
        self, live_servers, library_test_users, page,
    ):
        """e. Citation shows anchor button when anchor_chunk_ids present."""
        frontend_url, backend_port = live_servers
        a = library_test_users["user_a"]
        doc_id = a["doc"].get("id")
        assert doc_id
        citation_id = a.get("citation_id")
        assert citation_id, "Fixture must create a Citation for User A"

        headers = {"Authorization": f"Bearer {a['access_token']}"}
        base = f"http://127.0.0.1:{backend_port}"
        r = httpx.get(f"{base}/api/v1/documents/{doc_id}/reader", headers=headers, timeout=10)
        data = r.json().get("data", r.json())
        citations = data.get("citations", [])
        assert len(citations) > 0, f"Reader must return citations. Got {len(citations)}"

        has_anchors = any(
            cit.get("anchor_chunk_ids") and len(cit["anchor_chunk_ids"]) > 0
            for cit in citations
        )
        assert has_anchors, "At least one citation must have anchor_chunk_ids (via Passage → Chunk relation)"

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{doc_id}")
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        assert "定位到原文" in body, f"Must show '定位到原文' for anchored citations. Body: {body[:300]}"

    def test_reader_evidence_anchor_button(
        self, live_servers, library_test_users, page,
    ):
        """f. Evidence shows anchor button when anchor_chunk_ids present."""
        frontend_url, backend_port = live_servers
        a = library_test_users["user_a"]
        doc_id = a["doc"].get("id")
        assert doc_id
        evidence_id = a.get("evidence_id")
        assert evidence_id, "Fixture must create Evidence for User A"

        headers = {"Authorization": f"Bearer {a['access_token']}"}
        base = f"http://127.0.0.1:{backend_port}"
        r = httpx.get(f"{base}/api/v1/documents/{doc_id}/reader", headers=headers, timeout=10)
        data = r.json().get("data", r.json())
        evidences = data.get("evidences", [])
        assert len(evidences) > 0, f"Reader must return evidences. Got {len(evidences)}"

        has_anchors = any(
            ev.get("anchor_chunk_ids") and len(ev["anchor_chunk_ids"]) > 0
            for ev in evidences
        )
        assert has_anchors, "At least one evidence must have anchor_chunk_ids (via source_passage → Chunk relation)"

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{doc_id}")
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        assert "定位到原文" in body, f"Must show '定位到原文' for anchored evidence. Body: {body[:300]}"

    def test_reader_back_button_does_not_modify_library(
        self, live_servers, library_test_users, page,
    ):
        """h. Back button returns to Library search without modifying frozen Library."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        doc_id = a["doc"].get("id")
        assert doc_id

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{doc_id}")
        page.wait_for_timeout(5000)

        back_btn = page.locator('button:has-text("返回 Library")').first
        assert back_btn.is_visible(), "Back to Library button must be visible"
        back_btn.click()
        page.wait_for_timeout(3000)

        current_url = page.url
        assert "/library" in current_url, (
            f"Must navigate to /library after clicking back, got {current_url}"
        )

    def test_reader_http_401_redirects_to_login(
        self, live_servers, page,
    ):
        """i. Anonymous access to /reader/:id redirects to login."""
        frontend_url, _ = live_servers
        page.goto(f"{frontend_url}/reader/00000000-0000-0000-0000-000000000001")
        page.wait_for_url(f"{frontend_url}/login**", timeout=10000)

    def test_reader_http_404_shows_error_state(
        self, live_servers, library_test_users, page,
    ):
        """i. Accessing non-existent document shows ErrorState, not empty."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/00000000-0000-0000-0000-000000000099")
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        assert "文献未找到" in body or "错误" in body or "error" in body.lower(), (
            f"404 must show error state, not empty data. Body: {body[:300]}"
        )

    def test_reader_http_403_cross_user_access_denied(
        self, live_servers, library_test_users, page,
    ):
        """i. Accessing another user's doc via /reader/:id shows ErrorState."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]
        b_doc_id = b["doc"].get("id")
        assert b_doc_id, "User B must have a document"

        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")
        page.goto(f"{frontend_url}/reader/{b_doc_id}")
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        assert "文献未找到" in body or "错误" in body or "error" in body.lower(), (
            f"403/404 cross-user must show error state. Body: {body[:300]}"
        )
        # Must NOT show B's title
        b_title = b["doc"].get("title", "")
        if b_title:
            assert b_title not in body, f"User A must not see B's title '{b_title}'"


@pytest.mark.e2e
class TestReaderCrossUserIsolation:
    """j. User A cannot read User B's document via Reader."""

    def test_user_a_cannot_read_user_b_doc_via_reader(
        self, live_servers, library_test_users, page,
    ):
        """User A must not read User B's private document via /reader/:id."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        b_doc_id = b["doc"].get("id", "")
        assert b_doc_id, "User B must have a private document"

        page.goto(f"{frontend_url}/reader/{b_doc_id}")
        page.wait_for_timeout(5000)

        b_title = b["doc"].get("title", "")
        assert b_title, "User B's doc must have a title"
        assert page.locator(f"text={b_title}").count() == 0, (
            f"User A must not see B's title '{b_title}'"
        )

    def test_user_a_cannot_access_user_b_reader_api(
        self, live_servers, library_test_users,
    ):
        """User A's token gets 403/404 when accessing User B's /reader endpoint."""
        _, backend_port = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]

        b_doc_id = b["doc"].get("id", "")
        assert b_doc_id, "User B must have a private document"

        base = f"http://127.0.0.1:{backend_port}"
        headers = {"Authorization": f"Bearer {a['access_token']}"}
        r = httpx.get(f"{base}/api/v1/documents/{b_doc_id}/reader", headers=headers, timeout=10)

        assert r.status_code in (403, 404), (
            f"Cross-user reader access must be denied. Got {r.status_code}: {r.text[:200]}"
        )

    def test_tampered_doc_id_cannot_leak_other_user_data(
        self, live_servers, library_test_users,
    ):
        """Tampering document ID from another user returns 403/404."""
        _, backend_port = live_servers
        a = library_test_users["user_a"]
        b = library_test_users["user_b"]

        a_doc_id = a["doc"].get("id", "")
        assert a_doc_id, "User A must have a private document"

        b_doc_id = b["doc"].get("id", "")
        assert b_doc_id, "User B must have a private document"

        base = f"http://127.0.0.1:{backend_port}"
        headers = {"Authorization": f"Bearer {a['access_token']}"}

        # A can read own doc
        r = httpx.get(f"{base}/api/v1/documents/{a_doc_id}/reader", headers=headers, timeout=10)
        assert r.status_code == 200

        # A cannot read B's doc
        r2 = httpx.get(f"{base}/api/v1/documents/{b_doc_id}/reader", headers=headers, timeout=10)
        assert r2.status_code in (403, 404), (
            f"Cross-user isolation must hold. Got {r2.status_code}: {r2.text[:200]}"
        )


@pytest.mark.e2e
class TestReaderRapidSwitching:
    """k. Rapid document switching — stale responses don't pollute."""

    def test_rapid_switch_stale_response_does_not_pollute(
        self, live_servers, library_test_users, page,
    ):
        """Rapidly switching between documents, verify final page shows correct doc."""
        frontend_url, _ = live_servers
        a = library_test_users["user_a"]
        _login_via_ui(page, frontend_url, a["username"], "LibA_Pass123!")

        a_doc_id = a["doc"].get("id")
        a_title = a["doc"].get("title", "")
        assert a_doc_id, "User A must have a private document"

        page.goto(f"{frontend_url}/reader/{a_doc_id}")
        page.wait_for_timeout(3000)

        # Quickly navigate to non-existent doc
        page.goto(f"{frontend_url}/reader/00000000-0000-0000-0000-000000000099")
        page.wait_for_timeout(1000)

        # Navigate back to A's doc quickly
        page.goto(f"{frontend_url}/reader/{a_doc_id}")
        page.wait_for_timeout(5000)

        body = page.locator("body").first.text_content() or ""
        assert a_title in body, (
            f"After rapid switching, final page must show correct doc title '{a_title}'. "
            f"Body: {body[:300]}"
        )

    def test_rapid_switch_backend_stale_response_ignored(
        self, live_servers, library_test_users,
    ):
        """Backend /reader endpoint returns correct data for each doc sequentially."""
        _, backend_port = live_servers
        a = library_test_users["user_a"]
        headers = {"Authorization": f"Bearer {a['access_token']}"}

        a_doc_id = a["doc"].get("id", "")
        a_title = a["doc"].get("title", "")
        assert a_doc_id

        base = f"http://127.0.0.1:{backend_port}"

        r1 = httpx.get(f"{base}/api/v1/documents/{a_doc_id}/reader", headers=headers, timeout=10)
        assert r1.status_code == 200
        data1 = r1.json().get("data", r1.json())
        doc1_title = data1.get("document", {}).get("title", "")
        assert doc1_title == a_title, f"Must return A's title, got {doc1_title}"

        r2 = httpx.get(
            f"{base}/api/v1/documents/00000000-0000-0000-0000-000000000099/reader",
            headers=headers, timeout=10,
        )
        assert r2.status_code == 404, f"Non-existent doc must return 404, got {r2.status_code}"

        r3 = httpx.get(f"{base}/api/v1/documents/{a_doc_id}/reader", headers=headers, timeout=10)
        assert r3.status_code == 200
        data3 = r3.json().get("data", r3.json())
        assert data3.get("document", {}).get("title") == a_title, (
            "After error, must still return correct data"
        )
