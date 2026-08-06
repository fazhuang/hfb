"""
Unit tests for app/api/v1/ai.py — AI chat, generate, summarize, translate,
compare, and workspace CRUD routes.

Uses FastAPI TestClient with dependency_overrides + unittest.mock.patch
targeting the module-level service imports in app.api.v1.ai.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.generation import GenerationMetadata, GroundedGenerationResponse


# ---------------------------------------------------------------------------
# FastAPI app with auth/permission/db overrides for every test
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """TestClient with auth/permission/db overrides per test."""
    from main import app
    from app.middleware.auth import get_current_user
    from app.db.database import get_session
    from app.api.v1.ai import guard_ai_read, guard_workspace_read, guard_workspace_write

    async def _fake_user() -> str:
        return "test-user-id"

    async def _fake_session():
        return AsyncMock()

    app.dependency_overrides[guard_ai_read] = lambda: None
    app.dependency_overrides[guard_workspace_read] = lambda: None
    app.dependency_overrides[guard_workspace_write] = lambda: None
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_session] = _fake_session

    return TestClient(app)


# ---------------------------------------------------------------------------
# Shared mock factories
# ---------------------------------------------------------------------------

def _mock_ai_service_instance(**overrides):
    """Return a MagicMock AIService instance with async methods."""
    m = MagicMock()
    m.summarize = AsyncMock(return_value="摘要结果")
    m.translate = AsyncMock(return_value="翻译结果")
    m.ai_compare = AsyncMock(return_value="版本比较结果")

    async def _chat_stream(messages, context="", model=None):
        yield "chunk-1"
        yield "chunk-2"
    m.chat_stream = _chat_stream

    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def _mock_rag_instance(chunks=None):
    """Return a MagicMock RAGService instance."""
    m = MagicMock()
    m.retrieve = AsyncMock(return_value=chunks or [])
    m.assemble_context = AsyncMock(return_value="assembled context")
    return m


def _mock_generation_pipeline(query="test query", answer="Test answer",
                               error_code=None):
    """Return a MagicMock GenerationPipeline with .generate()"""
    metadata = GenerationMetadata(top_k=5, error_code=error_code)
    response = GroundedGenerationResponse(
        query=query,
        answer=answer,
        results=[{"document_id": "d1", "chunk_id": "c1"}],
        citations=[{"citation": "test"}],
        metadata=metadata,
    )
    m = MagicMock()
    m.generate = AsyncMock(return_value=response)
    return m


# ===================================================================
# TestAuth — verify unauthenticated access is rejected
# ===================================================================

class TestAuth:
    """401/403 when dependency_overrides are NOT in place."""

    @pytest.fixture
    def bare_client(self):
        from main import app
        app.dependency_overrides.clear()
        c = TestClient(app)
        yield c
        # Restore overrides via module fixture
        app.dependency_overrides.clear()

    def test_ai_summarize_unauthorized(self, bare_client):
        resp = bare_client.post("/api/v1/ai/summarize",
                                json={"text": "test"})
        assert resp.status_code == 401

    def test_ai_chat_unauthorized(self, bare_client):
        resp = bare_client.post("/api/v1/ai/chat",
                                json={"message": "hi"})
        assert resp.status_code == 401

    def test_ws_sessions_unauthorized(self, bare_client):
        resp = bare_client.get("/api/v1/workspace/sessions")
        assert resp.status_code == 401


# ===================================================================
# TestSummarize
# ===================================================================

class TestSummarize:
    """POST /api/v1/ai/summarize"""

    def test_success_returns_summary(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            resp = client.post("/api/v1/ai/summarize",
                               json={"text": "test text", "max_words": 100})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["summary"] == "摘要结果"

    def test_passes_max_words_to_service(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            client.post("/api/v1/ai/summarize",
                        json={"text": "test", "max_words": 50})
        mock_svc.summarize.assert_awaited_once_with("test", 50)

    def test_default_max_words_is_200(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            client.post("/api/v1/ai/summarize", json={"text": "test"})
        mock_svc.summarize.assert_awaited_once_with("test", 200)

    def test_422_empty_text(self, client):
        resp = client.post("/api/v1/ai/summarize", json={"text": ""})
        assert resp.status_code == 422

    def test_422_missing_text(self, client):
        resp = client.post("/api/v1/ai/summarize", json={})
        assert resp.status_code == 422


# ===================================================================
# TestTranslate
# ===================================================================

class TestTranslate:
    """POST /api/v1/ai/translate"""

    def test_success_returns_translation(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            resp = client.post("/api/v1/ai/translate",
                               json={"text": "test", "target_lang": "现代汉语"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["translation"] == "翻译结果"

    def test_passes_target_lang_to_service(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            client.post("/api/v1/ai/translate",
                        json={"text": "test", "target_lang": "英文"})
        mock_svc.translate.assert_awaited_once_with("test", "英文")

    def test_default_target_lang_modern_chinese(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            client.post("/api/v1/ai/translate", json={"text": "test"})
        mock_svc.translate.assert_awaited_once_with("test", "现代汉语")

    def test_422_empty_text(self, client):
        resp = client.post("/api/v1/ai/translate", json={"text": ""})
        assert resp.status_code == 422

    def test_422_missing_text(self, client):
        resp = client.post("/api/v1/ai/translate", json={})
        assert resp.status_code == 422


# ===================================================================
# TestAiCompare
# ===================================================================

class TestAiCompare:
    """POST /api/v1/ai/compare"""

    def test_success_returns_comparison(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            resp = client.post("/api/v1/ai/compare",
                               json={"source_text": "s", "target_text": "t"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["comparison"] == "版本比较结果"

    def test_passes_labels_to_service(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            client.post("/api/v1/ai/compare",
                        json={"source_text": "s", "target_text": "t",
                              "source_label": "A", "target_label": "B"})
        mock_svc.ai_compare.assert_awaited_once_with("s", "t", "A", "B")

    def test_default_labels(self, client):
        mock_svc = _mock_ai_service_instance()
        with patch("app.api.v1.ai.AIService", return_value=mock_svc):
            client.post("/api/v1/ai/compare",
                        json={"source_text": "s", "target_text": "t"})
        mock_svc.ai_compare.assert_awaited_once_with("s", "t", "源版本", "目标版本")

    def test_422_empty_source_text(self, client):
        resp = client.post("/api/v1/ai/compare",
                           json={"source_text": "", "target_text": "t"})
        assert resp.status_code == 422

    def test_422_empty_target_text(self, client):
        resp = client.post("/api/v1/ai/compare",
                           json={"source_text": "s", "target_text": ""})
        assert resp.status_code == 422

    def test_422_missing_source_text(self, client):
        resp = client.post("/api/v1/ai/compare", json={"target_text": "t"})
        assert resp.status_code == 422

    def test_422_missing_target_text(self, client):
        resp = client.post("/api/v1/ai/compare", json={"source_text": "s"})
        assert resp.status_code == 422


# ===================================================================
# TestChatEndpoint
# ===================================================================

class TestChatEndpoint:
    """POST /api/v1/ai/chat — SSE streaming with evidence-gated RAG"""

    # ------------------------------------------------------------------
    # Input validation (422)
    # ------------------------------------------------------------------

    def test_422_empty_message(self, client):
        resp = client.post("/api/v1/ai/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_422_missing_message(self, client):
        resp = client.post("/api/v1/ai/chat", json={})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # Evidence gate: no RAG results -> refusal
    # ------------------------------------------------------------------

    def test_refusal_when_rag_returns_empty(self, client):
        mock_ai = _mock_ai_service_instance()
        mock_rag = _mock_rag_instance(chunks=[])   # empty RAG

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                resp = client.post("/api/v1/ai/chat",
                                   json={"message": "test", "use_rag": True,
                                         "session_id": None})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse_events(resp.text)
        assert len(events) >= 2
        assert "structured" in events[0]
        assert "抱歉" in events[0]["content"]
        assert events[-1] == {"done": True}

    def test_refusal_has_empty_evidence_in_structured(self, client):
        mock_ai = _mock_ai_service_instance()
        mock_rag = _mock_rag_instance(chunks=[])

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                resp = client.post("/api/v1/ai/chat",
                                   json={"message": "test", "use_rag": True})
        events = _parse_sse_events(resp.text)
        structured = events[0]["structured"]
        assert structured["evidence"] == []
        assert structured["citations"] == []
        assert structured["graph_context"] == []

    # ------------------------------------------------------------------
    # RAG with chunks -> streaming with structured envelope
    # ------------------------------------------------------------------

    def test_streams_chunks_when_rag_has_results(self, client):
        mock_ai = _mock_ai_service_instance()
        mock_rag = _mock_rag_instance(chunks=[{
            "entity_type": "passage", "entity_id": "p1",
            "title": "Test", "content": "test content",
            "citation": "Test citation", "score": 0.9,
        }])

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                resp = client.post("/api/v1/ai/chat",
                                   json={"message": "test", "use_rag": True,
                                         "session_id": None})
        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        # At least content, structured, done
        assert len(events) >= 3
        assert events[-1] == {"done": True}

    def test_stream_contains_structured_envelope(self, client):
        mock_ai = _mock_ai_service_instance()
        mock_rag = _mock_rag_instance(chunks=[{
            "entity_type": "passage", "entity_id": "p1",
            "title": "Test Title", "content": "test content",
            "citation": "Test citation", "score": 0.9,
        }])

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                resp = client.post("/api/v1/ai/chat",
                                   json={"message": "test", "use_rag": True})
        events = _parse_sse_events(resp.text)
        structured_event = next(e for e in events if "structured" in e)
        struct = structured_event["structured"]
        assert "answer" in struct
        assert "evidence" in struct
        assert "citations" in struct
        assert "graph_context" in struct

    def test_structured_includes_evidence_from_rag_chunks(self, client):
        mock_ai = _mock_ai_service_instance()
        chunk = {
            "entity_type": "passage", "entity_id": "p-123",
            "title": "针灸甲乙经", "content": "some content data",
            "citation": "《针灸甲乙经》卷三", "score": 0.95,
        }
        mock_rag = _mock_rag_instance(chunks=[chunk])

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                resp = client.post("/api/v1/ai/chat",
                                   json={"message": "test", "use_rag": True})
        events = _parse_sse_events(resp.text)
        structured_event = next(e for e in events if "structured" in e)
        struct = structured_event["structured"]
        assert len(struct["evidence"]) == 1
        assert struct["evidence"][0]["entity_type"] == "passage"
        assert struct["evidence"][0]["entity_id"] == "p-123"
        assert len(struct["citations"]) == 1
        assert len(struct["graph_context"]) == 1

    # ------------------------------------------------------------------
    # use_rag=False: skip RAG, get empty chunks -> refusal
    # ------------------------------------------------------------------

    def test_use_rag_false_triggers_refusal(self, client):
        mock_ai = _mock_ai_service_instance()
        # RAG not called, but rag_chunks is empty since use_rag=False
        mock_rag = _mock_rag_instance(chunks=[])

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                resp = client.post("/api/v1/ai/chat",
                                   json={"message": "test", "use_rag": False})
        events = _parse_sse_events(resp.text)
        assert "抱歉" in events[0]["content"]

    # ------------------------------------------------------------------
    # Chat with session_id: history + persistence
    # ------------------------------------------------------------------

    def test_chat_with_session_id_fetches_history(self, client):
        mock_ai = _mock_ai_service_instance()
        mock_rag = _mock_rag_instance(chunks=[{
            "entity_type": "passage", "entity_id": "p1",
            "title": "T", "content": "c", "citation": "cit", "score": 1.0,
        }])
        mock_ws = MagicMock()
        mock_ws.get_chat_history = AsyncMock(return_value=[
            {"role": "user", "content": "prior question"},
            {"role": "assistant", "content": "prior answer"},
        ])
        mock_ws.append_chat_message = AsyncMock()

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                with patch("app.api.v1.ai.WorkspaceService",
                           return_value=mock_ws):
                    client.post("/api/v1/ai/chat",
                                json={"message": "test", "session_id": "s-1",
                                      "use_rag": True})
        mock_ws.get_chat_history.assert_awaited_once_with("s-1")
        # User message is saved
        assert mock_ws.append_chat_message.call_count >= 2
        # First call saves user message
        user_call_args = [c[0] for c in mock_ws.append_chat_message.call_args_list]
        assert any(args == ("s-1", "user", "test") for args in user_call_args)

    def test_chat_without_session_id_does_not_use_workspace(self, client):
        mock_ai = _mock_ai_service_instance()
        mock_rag = _mock_rag_instance(chunks=[])  # empty -> refusal, skipping ws

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                with patch("app.api.v1.ai.WorkspaceService") as mock_ws_cls:
                    mock_ws_cls.return_value.append_chat_message = AsyncMock()
                    mock_ws_cls.return_value.get_chat_history = AsyncMock(
                        return_value=[])
                    resp = client.post("/api/v1/ai/chat",
                                       json={"message": "test",
                                             "session_id": None})
                    assert resp.status_code == 200
                    assert mock_ws_cls.return_value.get_chat_history.call_count == 0

    # ------------------------------------------------------------------
    # Cache-Control header on streaming response
    # ------------------------------------------------------------------

    def test_chat_response_has_no_cache_headers(self, client):
        mock_ai = _mock_ai_service_instance()
        mock_rag = _mock_rag_instance(chunks=[])

        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                resp = client.post("/api/v1/ai/chat",
                                   json={"message": "test"})
        assert resp.headers["Cache-Control"] == "no-cache"
        assert resp.headers["X-Accel-Buffering"] == "no"

    # ------------------------------------------------------------------
    # ChatRequest optional fields
    # ------------------------------------------------------------------

    def test_chat_optional_fields_default(self, client):
        mock_ai = _mock_ai_service_instance()
        mock_rag = _mock_rag_instance(chunks=[])
        with patch("app.api.v1.ai.AIService", return_value=mock_ai):
            with patch("app.api.v1.ai.RAGService", return_value=mock_rag):
                resp = client.post("/api/v1/ai/chat",
                                   json={"message": "test"})
        assert resp.status_code == 200


# ===================================================================
# TestGroundedGenerate
# ===================================================================

class TestGroundedGenerate:
    """POST /api/v1/ai/generate — GenerationPipeline"""

    def test_success_returns_generation_response(self, client):
        mock_pipeline = _mock_generation_pipeline(
            query="什么是针灸", answer="针灸是..."
        )
        with patch("app.api.v1.ai.GenerationPipeline",
                   return_value=mock_pipeline):
            resp = client.post("/api/v1/ai/generate",
                               json={"query": "什么是针灸", "top_k": 5})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["query"] == "什么是针灸"
        assert data["answer"] == "针灸是..."
        assert "results" in data
        assert "citations" in data
        assert "metadata" in data

    def test_passes_top_k_to_pipeline(self, client):
        mock_pipeline = _mock_generation_pipeline()
        with patch("app.api.v1.ai.GenerationPipeline",
                   return_value=mock_pipeline):
            client.post("/api/v1/ai/generate",
                        json={"query": "test", "top_k": 10})
        mock_pipeline.generate.assert_awaited_once_with(
            query="test", top_k=10
        )

    def test_default_top_k_is_5(self, client):
        mock_pipeline = _mock_generation_pipeline()
        with patch("app.api.v1.ai.GenerationPipeline",
                   return_value=mock_pipeline):
            client.post("/api/v1/ai/generate", json={"query": "test"})
        mock_pipeline.generate.assert_awaited_once_with(
            query="test", top_k=5
        )

    # ------------------------------------------------------------------
    # Input validation (422)
    # ------------------------------------------------------------------

    def test_422_empty_query(self, client):
        resp = client.post("/api/v1/ai/generate", json={"query": ""})
        assert resp.status_code == 422

    def test_422_missing_query(self, client):
        resp = client.post("/api/v1/ai/generate", json={})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # top_k boundary values
    # ------------------------------------------------------------------

    def test_top_k_minimum_1(self, client):
        mock_pipeline = _mock_generation_pipeline()
        with patch("app.api.v1.ai.GenerationPipeline",
                   return_value=mock_pipeline):
            resp = client.post("/api/v1/ai/generate",
                               json={"query": "test", "top_k": 1})
        assert resp.status_code == 200
        mock_pipeline.generate.assert_awaited_once_with(
            query="test", top_k=1
        )

    def test_top_k_maximum_20(self, client):
        mock_pipeline = _mock_generation_pipeline()
        with patch("app.api.v1.ai.GenerationPipeline",
                   return_value=mock_pipeline):
            resp = client.post("/api/v1/ai/generate",
                               json={"query": "test", "top_k": 20})
        assert resp.status_code == 200
        mock_pipeline.generate.assert_awaited_once_with(
            query="test", top_k=20
        )

    def test_422_top_k_below_minimum(self, client):
        resp = client.post("/api/v1/ai/generate",
                           json={"query": "test", "top_k": 0})
        assert resp.status_code == 422

    def test_422_top_k_above_maximum(self, client):
        resp = client.post("/api/v1/ai/generate",
                           json={"query": "test", "top_k": 21})
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # Metadata with error_code (service-level validation failures)
    # ------------------------------------------------------------------

    def test_metadata_included_without_error_code(self, client):
        mock_pipeline = _mock_generation_pipeline(error_code=None)
        with patch("app.api.v1.ai.GenerationPipeline",
                   return_value=mock_pipeline):
            resp = client.post("/api/v1/ai/generate",
                               json={"query": "test"})
        data = resp.json()["data"]
        assert data["metadata"]["error_code"] is None

    def test_metadata_included_with_error_code(self, client):
        mock_pipeline = _mock_generation_pipeline(
            error_code="QUOTE_NOT_IN_CHUNK"
        )
        with patch("app.api.v1.ai.GenerationPipeline",
                   return_value=mock_pipeline):
            resp = client.post("/api/v1/ai/generate",
                               json={"query": "test"})
        data = resp.json()["data"]
        assert data["metadata"]["error_code"] == "QUOTE_NOT_IN_CHUNK"

    # ------------------------------------------------------------------
    # Response envelope shape
    # ------------------------------------------------------------------

    def test_response_envelope_has_timestamp(self, client):
        mock_pipeline = _mock_generation_pipeline()
        with patch("app.api.v1.ai.GenerationPipeline",
                   return_value=mock_pipeline):
            resp = client.post("/api/v1/ai/generate",
                               json={"query": "test"})
        body = resp.json()
        assert "timestamp" in body


# ===================================================================
# TestWorkspaceSessions
# ===================================================================

class TestWorkspaceSessions:
    """GET/POST/PATCH/DELETE /api/v1/workspace/sessions"""

    _SESSION_KWARGS = {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "user_id": "test-user-id",
        "title": "Test Session",
        "active_entities": None,
        "context_notes": None,
        "created_at": None,
        "updated_at": None,
    }

    def _make_session_mock(self, **overrides):
        kw = dict(self._SESSION_KWARGS)
        kw.update(overrides)
        return MagicMock(**kw)

    # --- list_sessions ---

    def test_list_sessions_success(self, client):
        mock_ws = MagicMock()
        mock_ws.list_sessions = AsyncMock(return_value=[
            self._make_session_mock(title="S1"),
            self._make_session_mock(id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                                     title="S2"),
        ])
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.get("/api/v1/workspace/sessions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) == 2
        assert body["data"][0]["title"] == "S1"

    def test_list_sessions_empty(self, client):
        mock_ws = MagicMock()
        mock_ws.list_sessions = AsyncMock(return_value=[])
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.get("/api/v1/workspace/sessions")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    # --- create_session ---

    def test_create_session_success(self, client):
        mock_ws = MagicMock()
        mock_ws.create_session = AsyncMock(
            return_value=self._make_session_mock())
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.post("/api/v1/workspace/sessions",
                               json={"title": "New Study"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Created"
        assert body["data"]["title"] == "Test Session"
        mock_ws.create_session.assert_awaited_once_with(
            "test-user-id", "New Study"
        )

    def test_create_session_default_title(self, client):
        mock_ws = MagicMock()
        mock_ws.create_session = AsyncMock(
            return_value=self._make_session_mock())
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.post("/api/v1/workspace/sessions", json={})
        assert resp.status_code == 200
        mock_ws.create_session.assert_awaited_once_with(
            "test-user-id", "未命名研究"
        )

    def test_create_session_empty_title_uses_default(self, client):
        """SessionCreateRequest has no min_length, empty string is accepted."""
        mock_ws = MagicMock()
        mock_ws.create_session = AsyncMock(
            return_value=self._make_session_mock())
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.post("/api/v1/workspace/sessions",
                               json={"title": ""})
        # SessionCreateRequest has no validation on title, so empty is OK
        assert resp.status_code == 200

    # --- get_session ---

    def test_get_session_success(self, client):
        mock_ws = MagicMock()
        sess = self._make_session_mock()
        mock_ws.get_session = AsyncMock(return_value=sess)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.get(
                "/api/v1/workspace/sessions/"
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    def test_get_session_not_found(self, client):
        mock_ws = MagicMock()
        mock_ws.get_session = AsyncMock(return_value=None)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.get(
                "/api/v1/workspace/sessions/"
                "00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_get_session_wrong_user(self, client):
        mock_ws = MagicMock()
        sess = self._make_session_mock(user_id="other-user")
        mock_ws.get_session = AsyncMock(return_value=sess)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.get(
                "/api/v1/workspace/sessions/"
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        assert resp.status_code == 404

    # --- update_session ---

    def test_update_session_success(self, client):
        mock_ws = MagicMock()
        sess = self._make_session_mock()
        mock_ws.get_session = AsyncMock(return_value=sess)
        mock_ws.update_session = AsyncMock(return_value=sess)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.patch(
                "/api/v1/workspace/sessions/"
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                json={"title": "Updated"},
            )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Updated"

    def test_update_session_not_found(self, client):
        mock_ws = MagicMock()
        mock_ws.get_session = AsyncMock(return_value=None)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.patch(
                "/api/v1/workspace/sessions/"
                "00000000-0000-0000-0000-000000000000",
                json={"title": "Nope"},
            )
        assert resp.status_code == 404

    def test_update_session_no_fields(self, client):
        """SessionUpdateRequest has all optional fields — empty body is OK."""
        mock_ws = MagicMock()
        sess = self._make_session_mock()
        mock_ws.get_session = AsyncMock(return_value=sess)
        mock_ws.update_session = AsyncMock(return_value=sess)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.patch(
                "/api/v1/workspace/sessions/"
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                json={},
            )
        assert resp.status_code == 200

    # --- delete_session ---

    def test_delete_session_success(self, client):
        mock_ws = MagicMock()
        sess = self._make_session_mock()
        mock_ws.get_session = AsyncMock(return_value=sess)
        mock_ws.delete_session = AsyncMock()
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.delete(
                "/api/v1/workspace/sessions/"
                "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Deleted"

    def test_delete_session_not_found(self, client):
        mock_ws = MagicMock()
        mock_ws.get_session = AsyncMock(return_value=None)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.delete(
                "/api/v1/workspace/sessions/"
                "00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ===================================================================
# TestWorkspaceNotes
# ===================================================================

class TestWorkspaceNotes:
    """Notes CRUD under /api/v1/workspace/sessions/{id}/notes and /notes/{id}"""

    _SESSION_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    _NOTE_ID = "11111111-1111-1111-1111-111111111111"

    def _make_session_mock(self, **kw):
        defaults = {
            "id": self._SESSION_ID,
            "user_id": "test-user-id",
            "title": "Test",
            "active_entities": None,
            "context_notes": None,
            "created_at": None,
            "updated_at": None,
        }
        defaults.update(kw)
        return MagicMock(**defaults)

    def _make_note_mock(self, **kw):
        defaults = {
            "id": self._NOTE_ID,
            "session_id": self._SESSION_ID,
            "entity_type": None,
            "entity_id": None,
            "content": "note content",
            "tags": None,
            "created_at": None,
            "updated_at": None,
        }
        defaults.update(kw)
        return MagicMock(**defaults)

    # --- list_notes ---

    def test_list_notes_success(self, client):
        mock_ws = MagicMock()
        mock_ws.get_session = AsyncMock(
            return_value=self._make_session_mock())
        mock_ws.list_notes = AsyncMock(return_value=[
            self._make_note_mock(content="N1"),
            self._make_note_mock(id="22222222-2222-2222-2222-222222222222",
                                  content="N2"),
        ])
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.get(
                f"/api/v1/workspace/sessions/{self._SESSION_ID}/notes")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 2

    def test_list_notes_session_not_found(self, client):
        mock_ws = MagicMock()
        mock_ws.get_session = AsyncMock(return_value=None)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.get(
                f"/api/v1/workspace/sessions/{self._SESSION_ID}/notes")
        assert resp.status_code == 404

    # --- create_note ---

    def test_create_note_success(self, client):
        mock_ws = MagicMock()
        mock_ws.get_session = AsyncMock(
            return_value=self._make_session_mock())
        mock_ws.create_note = AsyncMock(
            return_value=self._make_note_mock())
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.post(
                f"/api/v1/workspace/sessions/{self._SESSION_ID}/notes",
                json={"content": "New note", "entity_type": "passage",
                      "entity_id": "p-1", "tags": "tag1"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Created"
        mock_ws.create_note.assert_awaited_once()
        args, _ = mock_ws.create_note.call_args
        assert str(args[0]) == self._SESSION_ID
        assert args[1:] == ("New note", "passage", "p-1", "tag1")

    def test_create_note_missing_content(self, client):
        resp = client.post(
            f"/api/v1/workspace/sessions/{self._SESSION_ID}/notes",
            json={})
        assert resp.status_code == 422

    def test_create_note_session_not_found(self, client):
        mock_ws = MagicMock()
        mock_ws.get_session = AsyncMock(return_value=None)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.post(
                f"/api/v1/workspace/sessions/{self._SESSION_ID}/notes",
                json={"content": "test"})
        assert resp.status_code == 404

    # --- update_note ---

    def test_update_note_success(self, client):
        mock_ws = MagicMock()
        note = self._make_note_mock()
        sess = self._make_session_mock()
        # get_note_with_session returns (note, session) tuple
        mock_ws.get_note_with_session = AsyncMock(
            return_value=(note, sess))
        mock_ws.update_note = AsyncMock(return_value=note)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.patch(
                f"/api/v1/workspace/notes/{self._NOTE_ID}",
                json={"content": "Updated"},
            )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Updated"

    def test_update_note_not_found(self, client):
        mock_ws = MagicMock()
        mock_ws.get_note_with_session = AsyncMock(return_value=None)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.patch(
                f"/api/v1/workspace/notes/{self._NOTE_ID}",
                json={"content": "x"},
            )
        assert resp.status_code == 404

    # --- delete_note ---

    def test_delete_note_success(self, client):
        mock_ws = MagicMock()
        note = self._make_note_mock()
        sess = self._make_session_mock()
        mock_ws.get_note_with_session = AsyncMock(
            return_value=(note, sess))
        mock_ws.delete_note = AsyncMock()
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.delete(
                f"/api/v1/workspace/notes/{self._NOTE_ID}")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Deleted"

    def test_delete_note_not_found(self, client):
        mock_ws = MagicMock()
        mock_ws.get_note_with_session = AsyncMock(return_value=None)
        with patch("app.api.v1.ai.WorkspaceService", return_value=mock_ws):
            resp = client.delete(
                f"/api/v1/workspace/notes/{self._NOTE_ID}")
        assert resp.status_code == 404


# ===================================================================
# TestSummaryCrossCuttingValidation
# ===================================================================

class TestSummaryCrossCuttingValidation:
    """Cross-cutting input validation tests across endpoints."""

    def test_all_ai_endpoints_require_min_length_1(self, client):
        """All AI request models use Field(..., min_length=1) on text fields."""
        endpoints = [
            ("/api/v1/ai/summarize", {"text": ""}),
            ("/api/v1/ai/translate", {"text": ""}),
            ("/api/v1/ai/compare", {"source_text": "", "target_text": "t"}),
            ("/api/v1/ai/compare", {"source_text": "t", "target_text": ""}),
            ("/api/v1/ai/chat", {"message": ""}),
            ("/api/v1/ai/generate", {"query": ""}),
        ]
        for path, body in endpoints:
            resp = client.post(path, json=body)
            assert resp.status_code == 422, (
                f"Expected 422 for {path} with {body}, got {resp.status_code}"
            )

    def test_all_ai_endpoints_require_required_fields(self, client):
        endpoints = [
            ("/api/v1/ai/summarize", {}),
            ("/api/v1/ai/translate", {}),
            ("/api/v1/ai/compare", {}),
            ("/api/v1/ai/chat", {}),
            ("/api/v1/ai/generate", {}),
        ]
        for path, body in endpoints:
            resp = client.post(path, json=body)
            assert resp.status_code == 422, (
                f"Expected 422 for {path} with empty body, got {resp.status_code}"
            )


# ===================================================================
# Helpers
# ===================================================================

def _parse_sse_events(text: str) -> list[dict]:
    """Parse SSE text/event-stream output into a list of JSON objects."""
    events: list[dict] = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            payload = line[6:]
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                continue
    return events
