"""
Tests for AI and Workspace services.

Per HFB-PS-1705 AI Research Workspace Product Specification.
"""

from __future__ import annotations

import json

import httpx
import pytest
from app.models.book import Book
from app.models.person import Person
from app.services.ai_service import (
    EVIDENCE_GATED_SYSTEM_PROMPT,
    AIService,
    RateLimiter,
    _mock_compare,
    _mock_summarize,
    _mock_translate,
    _rate_limiter,
)
from app.services.rag_service import RAGService
from app.services.workspace_service import WorkspaceService
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401

# ---------------------------------------------------------------------------
# helpers — patch httpx.AsyncClient without recursion
# ---------------------------------------------------------------------------

_original_AsyncClient = httpx.AsyncClient


def _patch_async_client(monkeypatch, transport):
    """monkeypatch httpx.AsyncClient to use *transport* for all calls."""

    def _factory(**kw):
        return _original_AsyncClient(
            transport=transport,
            **{k: v for k, v in kw.items() if k != "transport"},
        )

    monkeypatch.setattr(httpx, "AsyncClient", _factory)


# ============================================================
# Rate Limiter
# ============================================================


class TestRateLimiter:
    def test_allows_requests_up_to_limit(self) -> None:
        rl = RateLimiter(max_per_minute=5)
        for _ in range(5):
            assert rl.allow() is True

    def test_denies_over_limit(self) -> None:
        rl = RateLimiter(max_per_minute=3)
        for _ in range(3):
            assert rl.allow() is True
        assert rl.allow() is False

    def test_remaining(self) -> None:
        rl = RateLimiter(max_per_minute=5)
        assert rl.remaining == 5
        rl.allow()
        assert rl.remaining == 4

    def test_window_expiry_recovers_slots(self, monkeypatch) -> None:
        rl = RateLimiter(max_per_minute=2)
        assert rl.allow() is True
        assert rl.allow() is True
        assert rl.allow() is False  # exhausted

        fake_now = rl._timestamps[-1] + 61.0 if rl._timestamps else 100.0
        monkeypatch.setattr("app.services.ai_service.time.monotonic", lambda: fake_now)
        assert rl.allow() is True

    def test_remaining_reflects_pruned_window(self, monkeypatch) -> None:
        rl = RateLimiter(max_per_minute=5)
        for _ in range(3):
            rl.allow()
        assert rl.remaining == 2

        fake_now = rl._timestamps[-1] + 61.0
        monkeypatch.setattr("app.services.ai_service.time.monotonic", lambda: fake_now)
        assert rl.remaining == 5


# ============================================================
# AIService (mock mode — no API key)
# ============================================================


class TestAIService:
    def test_available_false_by_default(self) -> None:
        svc = AIService()
        assert svc.available is False  # No API key in test

    def test_rate_limit_available(self) -> None:
        svc = AIService()
        assert svc.check_rate_limit() is True

    @pytest.mark.asyncio
    async def test_summarize_mock(self) -> None:
        svc = AIService()
        result = await svc.summarize("针灸甲乙经是皇甫谧编撰的经典著作。", max_words=30)
        assert "摘要" in result or "AI" in result
        assert "针灸" in result

    @pytest.mark.asyncio
    async def test_translate_mock(self) -> None:
        svc = AIService()
        result = await svc.translate("凡刺之法，必候日月星辰。", target_lang="现代汉语")
        assert "翻译" in result or "AI" in result

    @pytest.mark.asyncio
    async def test_compare_mock(self) -> None:
        svc = AIService()
        result = await svc.ai_compare("凡刺之法", "凡刺之要", "源版本", "目标版本")
        assert "相似度" in result or "差异" in result


# ============================================================
# chat_stream — evidence gate (no HTTP happens)
# ============================================================


@pytest.mark.asyncio
class TestChatStreamGate:
    """chat_stream must refuse before any HTTP call when gate fails."""

    async def test_unconfigured_yields_unavailable(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.ai_service.settings.AI_API_KEY", "")
        svc = AIService()
        chunks = [c async for c in svc.chat_stream(
            [{"role": "user", "content": "什么是针灸？"}],
            context="针灸甲乙经记载...",
        )]
        assert len(chunks) == 1
        assert "EVIDENCE_GATE_UNAVAILABLE" in chunks[0]

    async def test_rate_limited_refused(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.ai_service.settings.AI_API_KEY", "fake-key")
        saved_ts = list(_rate_limiter._timestamps)
        try:
            _rate_limiter._timestamps.clear()
            for _ in range(_rate_limiter._max):
                _rate_limiter._timestamps.append(999999.0)
            svc = AIService()
            chunks = [c async for c in svc.chat_stream(
                [{"role": "user", "content": "test"}],
                context="some evidence",
            )]
            assert len(chunks) == 1
            assert "EVIDENCE_GATE_RATE_LIMITED" in chunks[0]
        finally:
            _rate_limiter._timestamps.clear()
            _rate_limiter._timestamps.extend(saved_ts)

    async def test_empty_context_refused(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.ai_service.settings.AI_API_KEY", "fake-key")
        svc = AIService()
        saved_ts = list(_rate_limiter._timestamps)
        try:
            _rate_limiter._timestamps.clear()
            chunks = [c async for c in svc.chat_stream(
                [{"role": "user", "content": "test"}],
                context="   ",
            )]
            assert len(chunks) == 1
            assert "EVIDENCE_GATE_REFUSAL" in chunks[0]
        finally:
            _rate_limiter._timestamps.clear()
            _rate_limiter._timestamps.extend(saved_ts)


# ============================================================
# chat_stream SSE — httpx MockTransport
# ============================================================


def _sse_body(*lines: str) -> bytes:
    return "\n".join(lines).encode()


@pytest.fixture
def configured_ai(monkeypatch):
    """Return AIService with a fake API key and isolated rate limiter."""
    monkeypatch.setattr("app.services.ai_service.settings.AI_API_KEY", "fake-key")
    monkeypatch.setattr("app.services.ai_service.settings.AI_BASE_URL", "https://fake")
    monkeypatch.setattr("app.services.ai_service.settings.AI_MODEL", "fake-model")
    saved_ts = list(_rate_limiter._timestamps)
    _rate_limiter._timestamps.clear()
    svc = AIService()
    yield svc
    _rate_limiter._timestamps.clear()
    _rate_limiter._timestamps.extend(saved_ts)


@pytest.mark.asyncio
class TestChatStreamSSE:
    async def test_success_sse_yields_content_and_marker(
        self, configured_ai, monkeypatch
    ) -> None:
        body = _sse_body(
            'data: {"choices":[{"delta":{"content":"针灸"}}]}',
            'data: {"choices":[{"delta":{"content":"是中医"}}]}',
            "data: [DONE]",
        )

        def handler(req):
            return httpx.Response(200, content=body, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        chunks = [c async for c in configured_ai.chat_stream(
            [{"role": "user", "content": "什么是针灸？"}],
            context="针灸甲乙经记载...",
        )]
        content = "".join(chunks)
        assert "针灸" in content
        assert "中医" in content
        assert "AI 生成内容" in content
        assert "[DONE]" not in content

    async def test_malformed_sse_ignored(self, configured_ai, monkeypatch) -> None:
        body = _sse_body(
            'data: {"choices":[{"delta":{"content":"good"}}]}',
            "data: not-valid-json {{{",
            'data: {"choices":[{"delta":{"content":"more"}}]}',
            "data: [DONE]",
        )

        def handler(req):
            return httpx.Response(200, content=body, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        chunks = [c async for c in configured_ai.chat_stream(
            [{"role": "user", "content": "test"}],
            context="evidence text",
        )]
        content = "".join(chunks)
        assert "good" in content
        assert "more" in content

    async def test_http_non_200_yields_error(self, configured_ai, monkeypatch) -> None:
        def handler(req):
            return httpx.Response(502, content=b"Bad Gateway", request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        chunks = [c async for c in configured_ai.chat_stream(
            [{"role": "user", "content": "test"}],
            context="evidence text",
        )]
        content = "".join(chunks)
        assert "HTTP 502" in content


# ============================================================
# Non-streaming complete — payload and errors
# ============================================================


@pytest.mark.asyncio
class TestComplete:
    async def test_payload_includes_system_prompt_temperature_seed(
        self, configured_ai, monkeypatch
    ) -> None:
        captured: dict | None = None

        async def handler(req):
            nonlocal captured
            captured = json.loads(req.content)
            return httpx.Response(200, json={"choices": [{"message": {"content": "reply"}}]}, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        result = await configured_ai.complete(
            [{"role": "user", "content": "test"}],
            system_prompt="custom system prompt",
            temperature=0.0,
            seed=42,
        )
        assert "reply" in result
        assert captured is not None
        assert captured["temperature"] == 0.0
        assert captured["seed"] == 42
        assert captured["stream"] is False
        msgs = captured["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "custom system prompt"

    async def test_default_system_prompt_is_evidence_gated(
        self, configured_ai, monkeypatch
    ) -> None:
        captured: dict | None = None

        async def handler(req):
            nonlocal captured
            captured = json.loads(req.content)
            return httpx.Response(200, json={"choices": [{"message": {"content": "reply"}}]}, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        await configured_ai.complete([{"role": "user", "content": "test"}])
        assert captured is not None
        msgs = captured["messages"]
        assert msgs[0]["content"] == EVIDENCE_GATED_SYSTEM_PROMPT

    async def test_http_non_200_returns_error_text(
        self, configured_ai, monkeypatch
    ) -> None:
        def handler(req):
            return httpx.Response(500, content=b"Internal Error", request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        result = await configured_ai.complete([{"role": "user", "content": "test"}])
        assert "HTTP 500" in result


# ============================================================
# complete_structured — success, empty, non-200, exceptions
# ============================================================


@pytest.mark.asyncio
class TestCompleteStructured:
    async def test_success_returns_content(self, configured_ai, monkeypatch) -> None:
        async def handler(req):
            return httpx.Response(200, json={"choices": [{"message": {"content": "  structured reply  "}}]}, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        result = await configured_ai.complete_structured(
            [{"role": "user", "content": "test"}],
        )
        assert result == "structured reply"

    async def test_empty_content_returns_none(self, configured_ai, monkeypatch) -> None:
        async def handler(req):
            return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        result = await configured_ai.complete_structured(
            [{"role": "user", "content": "test"}],
        )
        assert result is None

    async def test_whitespace_only_content_returns_none(
        self, configured_ai, monkeypatch
    ) -> None:
        async def handler(req):
            return httpx.Response(200, json={"choices": [{"message": {"content": "   "}}]}, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        result = await configured_ai.complete_structured(
            [{"role": "user", "content": "test"}],
        )
        assert result is None

    async def test_http_non_200_returns_none(self, configured_ai, monkeypatch) -> None:
        def handler(req):
            return httpx.Response(503, content=b"Unavailable", request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        result = await configured_ai.complete_structured(
            [{"role": "user", "content": "test"}],
        )
        assert result is None

    async def test_connect_error_returns_none(self, configured_ai, monkeypatch) -> None:
        def handler(req):
            raise httpx.ConnectError("connection refused")

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        result = await configured_ai.complete_structured(
            [{"role": "user", "content": "test"}],
        )
        assert result is None

    async def test_json_decode_error_returns_none(
        self, configured_ai, monkeypatch
    ) -> None:
        async def handler(req):
            return httpx.Response(200, content=b"not json at all {{{", request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        result = await configured_ai.complete_structured(
            [{"role": "user", "content": "test"}],
        )
        assert result is None

    async def test_payload_includes_temperature_and_seed(
        self, configured_ai, monkeypatch
    ) -> None:
        captured: dict | None = None

        async def handler(req):
            nonlocal captured
            captured = json.loads(req.content)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        await configured_ai.complete_structured(
            [{"role": "user", "content": "test"}],
            temperature=0.1,
            seed=99,
        )
        assert captured is not None
        assert captured["temperature"] == 0.1
        assert captured["seed"] == 99
        assert captured["stream"] is False

    async def test_no_seed_when_none(self, configured_ai, monkeypatch) -> None:
        captured: dict | None = None

        async def handler(req):
            nonlocal captured
            captured = json.loads(req.content)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}, request=req)

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        await configured_ai.complete_structured(
            [{"role": "user", "content": "test"}],
        )
        assert "seed" not in captured


# ============================================================
# Mock fallback methods — unconfigured/rate-limited paths
# ============================================================


@pytest.mark.asyncio
class TestMockFallbacks:
    async def test_summarize_unconfigured_truncates_text(self) -> None:
        svc = AIService()
        text = "针灸" * 100
        result = await svc.summarize(text, max_words=20)
        assert "摘要" in result
        assert "AI 服务未配置" in result

    async def test_translate_unconfigured_truncates_text(self) -> None:
        svc = AIService()
        result = await svc.translate("针灸甲乙经", target_lang="现代汉语")
        assert "翻译" in result
        assert "AI 服务未配置" in result
        assert "针灸甲乙经" in result

    async def test_ai_compare_unconfigured_uses_sequence_matcher(self) -> None:
        svc = AIService()
        result = await svc.ai_compare("凡刺之法", "凡刺之要", "源", "目标")
        assert "相似度" in result
        assert "AI 服务未配置" in result

    async def test_summarize_rate_limited(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.ai_service.settings.AI_API_KEY", "fake-key")
        saved_ts = list(_rate_limiter._timestamps)
        try:
            _rate_limiter._timestamps.clear()
            for _ in range(_rate_limiter._max):
                _rate_limiter._timestamps.append(999999.0)
            svc = AIService()
            result = await svc.summarize("test text", max_words=30)
            assert "请求过于频繁" in result
        finally:
            _rate_limiter._timestamps.clear()
            _rate_limiter._timestamps.extend(saved_ts)

    async def test_translate_rate_limited(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.ai_service.settings.AI_API_KEY", "fake-key")
        saved_ts = list(_rate_limiter._timestamps)
        try:
            _rate_limiter._timestamps.clear()
            for _ in range(_rate_limiter._max):
                _rate_limiter._timestamps.append(999999.0)
            svc = AIService()
            result = await svc.translate("test", target_lang="现代汉语")
            assert "请求过于频繁" in result
        finally:
            _rate_limiter._timestamps.clear()
            _rate_limiter._timestamps.extend(saved_ts)

    async def test_ai_compare_rate_limited(self, monkeypatch) -> None:
        monkeypatch.setattr("app.services.ai_service.settings.AI_API_KEY", "fake-key")
        saved_ts = list(_rate_limiter._timestamps)
        try:
            _rate_limiter._timestamps.clear()
            for _ in range(_rate_limiter._max):
                _rate_limiter._timestamps.append(999999.0)
            svc = AIService()
            result = await svc.ai_compare("a", "b")
            assert "请求过于频繁" in result
        finally:
            _rate_limiter._timestamps.clear()
            _rate_limiter._timestamps.extend(saved_ts)


# ============================================================
# Mock helper functions — direct unit coverage
# ============================================================


class TestMockHelpers:
    def test_mock_summarize_truncates_long_text(self) -> None:
        result = _mock_summarize("x" * 500, max_words=30)
        assert "[摘要]" in result
        assert "AI 服务未配置" in result
        assert "…" in result

    def test_mock_summarize_short_text_no_ellipsis(self) -> None:
        result = _mock_summarize("short", max_words=200)
        assert "[摘要]" in result
        assert "short" in result
        assert "…" not in result

    def test_mock_translate_truncates_long_text(self) -> None:
        result = _mock_translate("x" * 500, target_lang="英文")
        assert "[翻译至英文]" in result
        assert "…" in result

    def test_mock_translate_short_text_no_ellipsis(self) -> None:
        result = _mock_translate("hello", target_lang="法文")
        assert "[翻译至法文]" in result
        assert "hello" in result

    def test_mock_compare_detects_similarity(self) -> None:
        result = _mock_compare("凡刺之法", "凡刺之要", "源版本", "目标版本")
        assert "相似度" in result
        assert "源版本" in result
        assert "目标版本" in result
        assert "75.0%" in result

    def test_mock_compare_identical_texts(self) -> None:
        result = _mock_compare("相同文本", "相同文本", "A", "B")
        assert "相似度" in result
        assert "0 处差异" in result


# ============================================================
# chat_stream request payload verification
# ============================================================


@pytest.mark.asyncio
class TestChatStreamPayload:
    async def test_payload_contains_evidence_gated_system_prompt(
        self, configured_ai, monkeypatch
    ) -> None:
        captured: dict | None = None

        async def handler(req):
            nonlocal captured
            captured = json.loads(req.content)
            return httpx.Response(
                200,
                content=b'data: {"choices":[{"delta":{"content":"ok"}}]}\ndata: [DONE]\n',
                request=req,
            )

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        _ = [c async for c in configured_ai.chat_stream(
            [{"role": "user", "content": "什么是针灸？"}],
            context="针灸甲乙经记载：经络者，所以行血气。",
        )]
        assert captured is not None
        assert captured["model"] == "fake-model"
        msgs = captured["messages"]
        assert msgs[0]["content"] == EVIDENCE_GATED_SYSTEM_PROMPT
        assert "针灸甲乙经记载" in msgs[1]["content"]

    async def test_request_headers_no_real_key_leak(
        self, configured_ai, monkeypatch
    ) -> None:
        captured_headers: dict | None = None

        async def handler(req):
            nonlocal captured_headers
            captured_headers = dict(req.headers)
            return httpx.Response(
                200,
                content=b'data: {"choices":[{"delta":{"content":"ok"}}]}\ndata: [DONE]\n',
                request=req,
            )

        _patch_async_client(monkeypatch, httpx.MockTransport(handler))

        _ = [c async for c in configured_ai.chat_stream(
            [{"role": "user", "content": "test"}],
            context="evidence",
        )]
        assert captured_headers is not None
        auth = captured_headers.get("authorization", "")
        assert auth == "Bearer fake-key"


# ============================================================
# Workspace Service
# ============================================================


@pytest.mark.asyncio
class TestWorkspaceService:
    async def test_create_and_get_session(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-1",
            username="test_user_1",
            email="user-1@test.com",
            hashed_password="test-hash-1",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-1", "测试研究会话")
        assert s.id is not None
        assert s.title == "测试研究会话"

        got = await svc.get_session(s.id)
        assert got is not None
        assert got.title == "测试研究会话"

    async def test_list_sessions(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-2",
            username="test_user_2",
            email="user-2@test.com",
            hashed_password="test-hash-2",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        await svc.create_session("user-2", "研究1")
        await svc.create_session("user-2", "研究2")

        sessions = await svc.list_sessions("user-2")
        assert len(sessions) >= 2

    async def test_update_session(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-3",
            username="test_user_3",
            email="user-3@test.com",
            hashed_password="test-hash-3",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-3", "原标题")

        updated = await svc.update_session(
            s.id, title="新标题", active_entities=["b1", "p2"]
        )
        assert updated is not None
        assert updated.title == "新标题"

    async def test_delete_session(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-4",
            username="test_user_4",
            email="user-4@test.com",
            hashed_password="test-hash-4",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-4", "待删除")

        ok = await svc.delete_session(s.id)
        assert ok is True
        assert await svc.get_session(s.id) is None

    async def test_chat_history(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-5",
            username="test_user_5",
            email="user-5@test.com",
            hashed_password="test-hash-5",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-5", "聊天测试")

        await svc.append_chat_message(s.id, "user", "什么是针灸？")
        await svc.append_chat_message(s.id, "assistant", "针灸是一种中医治疗方法...")

        history = await svc.get_chat_history(s.id)
        assert len(history) >= 2
        assert history[0]["role"] == "user"
        assert "针灸" in history[0]["content"]

    async def test_create_and_list_notes(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-6",
            username="test_user_6",
            email="user-6@test.com",
            hashed_password="test-hash-6",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-6", "笔记测试")

        await svc.create_note(s.id, "这是一条测试笔记", entity_type="book", tags="重要")
        await svc.create_note(s.id, "另一条笔记", entity_type="passage")

        notes = await svc.list_notes(s.id)
        assert len(notes) >= 2

    async def test_update_note(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-7",
            username="test_user_7",
            email="user-7@test.com",
            hashed_password="test-hash-7",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-7", "更新笔记测试")
        n = await svc.create_note(s.id, "原始内容")

        updated = await svc.update_note(n.id, content="更新后内容")
        assert updated is not None
        assert updated.content == "更新后内容"

    async def test_delete_note(self, db_session: AsyncSession) -> None:
        from app.models.user import User

        u = User(
            id="user-8",
            username="test_user_8",
            email="user-8@test.com",
            hashed_password="test-hash-8",
        )
        db_session.add(u)
        await db_session.flush()

        svc = WorkspaceService(db_session)
        s = await svc.create_session("user-8", "删除笔记测试")
        n = await svc.create_note(s.id, "待删除笔记")

        ok = await svc.delete_note(n.id)
        assert ok is True

        notes = await svc.list_notes(s.id)
        assert not any(x.id == n.id for x in notes)


# ============================================================
# RAG Service
# ============================================================


@pytest.mark.asyncio
class TestRAGService:
    async def test_retrieve_empty(self, db_session: AsyncSession) -> None:
        svc = RAGService(db_session)
        chunks = await svc.retrieve("nonexistent_xyz_query", top_k=3)
        assert len(chunks) == 0

    async def test_assemble_context_empty(self, db_session: AsyncSession) -> None:
        svc = RAGService(db_session)
        ctx = await svc.assemble_context("nonexistent_xyz_query")
        assert ctx == ""

    async def test_retrieve_with_data(self, db_session: AsyncSession) -> None:
        p = Person(name="扁鹊", dynasty="春秋", biography="扁鹊是春秋时期著名医学家。")
        db_session.add(p)
        await db_session.flush()

        b = Book(title="难经", dynasty="春秋", abstract="《难经》相传为扁鹊所著。")
        db_session.add(b)
        await db_session.flush()

        svc = RAGService(db_session)
        chunks = await svc.retrieve("扁鹊", entity_types=["person", "book"], top_k=3)
        assert len(chunks) >= 1
        assert any("扁鹊" in str(c.get("content", "")) for c in chunks)

    async def test_assemble_context_with_data(self, db_session: AsyncSession) -> None:
        p = Person(name="王叔和", dynasty="西晋", biography="王叔和编次《伤寒论》。")
        db_session.add(p)
        await db_session.flush()

        svc = RAGService(db_session)
        ctx = await svc.assemble_context("王叔和", top_k=2)
        assert len(ctx) > 0
        assert "王叔和" in ctx
