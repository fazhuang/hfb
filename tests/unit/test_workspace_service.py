"""Unit tests for WorkspaceService — sessions, notes, query history, citations.

Covers all CRUD operations, guard logic, error paths, and edge cases.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models.workspace import (
    CitationCollection,
    QueryHistory,
    ResearchNote,
    ResearchSession,
)
from app.services.workspace_service import WorkspaceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_mock(**kwargs) -> MagicMock:
    """Build a MagicMock ResearchSession with sensible defaults."""
    defaults = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "title": "未命名研究",
        "active_entities": None,
        "chat_history": None,
        "context_notes": None,
        "is_deleted": False,
        "deleted_at": None,
        "updated_at": None,
    }
    defaults.update(kwargs)
    return MagicMock(spec=ResearchSession, **defaults)


def _make_note_mock(**kwargs) -> MagicMock:
    defaults = {
        "id": str(uuid4()),
        "session_id": str(uuid4()),
        "entity_type": None,
        "entity_id": None,
        "content": "test note content",
        "tags": None,
        "is_deleted": False,
        "deleted_at": None,
        "updated_at": None,
    }
    defaults.update(kwargs)
    return MagicMock(spec=ResearchNote, **defaults)


def _make_qh_mock(**kwargs) -> MagicMock:
    defaults = {
        "id": str(uuid4()),
        "session_id": str(uuid4()),
        "query_text": "test query",
        "query_type": "search",
        "result_summary": None,
        "citation_count": 0,
    }
    defaults.update(kwargs)
    return MagicMock(spec=QueryHistory, **defaults)


def _make_citation_mock(**kwargs) -> MagicMock:
    defaults = {
        "id": str(uuid4()),
        "session_id": str(uuid4()),
        "trace_json": "{}",
        "citation_text": "test citation",
        "source_document": "test doc",
        "tags": None,
        "notes": None,
    }
    defaults.update(kwargs)
    return MagicMock(spec=CitationCollection, **defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def session() -> AsyncMock:
    """Return a bare AsyncMock standing in for AsyncSession."""
    s = AsyncMock()
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.delete = AsyncMock()
    return s


@pytest.fixture
def svc(session: AsyncMock) -> WorkspaceService:
    return WorkspaceService(session)


# ===================================================================
# Sessions — create / get / list
# ===================================================================

class TestCreateSession:
    @pytest.mark.asyncio
    async def test_creates_with_default_title(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_session(user_id="u1")

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert isinstance(result, ResearchSession)
        assert result.user_id == "u1"
        assert result.title == "未命名研究"

    @pytest.mark.asyncio
    async def test_creates_with_custom_title(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_session(user_id="u1", title="Custom")

        assert result.title == "Custom"


class TestGetSession:
    @pytest.mark.asyncio
    async def test_returns_session_when_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        result = await svc.get_session("sid")

        assert result is s

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.get_session("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_accepts_uuid(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock()
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        result = await svc.get_session(UUID(s.id))

        assert result is s


class TestListSessions:
    @pytest.mark.asyncio
    async def test_returns_list(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s1, s2 = _make_session_mock(), _make_session_mock()
        scalars_mock = MagicMock(all=MagicMock(return_value=[s1, s2]))
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

        result = await svc.list_sessions("u1")

        assert result == [s1, s2]

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, svc: WorkspaceService, session: AsyncMock) -> None:
        scalars_mock = MagicMock(all=MagicMock(return_value=[]))
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

        result = await svc.list_sessions("u1")

        assert result == []


# ===================================================================
# Sessions — update / delete
# ===================================================================

class TestUpdateSession:
    @pytest.mark.asyncio
    async def test_updates_title(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        result = await svc.update_session("sid", title="New Title")

        assert result is s
        assert s.title == "New Title"
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_active_entities_as_json(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        await svc.update_session("sid", active_entities=["ent1", "ent2"])

        assert s.active_entities == '["ent1", "ent2"]'

    @pytest.mark.asyncio
    async def test_updates_context_notes(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        await svc.update_session("sid", context_notes="# Markdown notes")

        assert s.context_notes == "# Markdown notes"

    @pytest.mark.asyncio
    async def test_partial_update_does_not_overwrite_other_fields(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid", title="Old", active_entities='["e1"]', context_notes="old notes")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        await svc.update_session("sid", title="New")

        assert s.title == "New"
        assert s.active_entities == '["e1"]'
        assert s.context_notes == "old notes"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.update_session("nonexistent", title="X")

        assert result is None
        session.flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_noop_when_all_params_none(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid", title="Old")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        result = await svc.update_session("sid")

        assert result is s
        assert s.title == "Old"  # unchanged


class TestDeleteSession:
    @pytest.mark.asyncio
    async def test_soft_deletes(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        result = await svc.delete_session("sid")

        assert result is True
        assert s.is_deleted is True
        assert s.deleted_at is not None
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.delete_session("nonexistent")

        assert result is False
        session.flush.assert_not_awaited()


# ===================================================================
# Chat history
# ===================================================================

class TestAppendChatMessage:
    @pytest.mark.asyncio
    async def test_appends_to_empty_history(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid", chat_history=None)
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        await svc.append_chat_message("sid", "user", "Hello")

        history = json.loads(s.chat_history)
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert "timestamp" in history[0]

    @pytest.mark.asyncio
    async def test_appends_to_existing_history(self, svc: WorkspaceService, session: AsyncMock) -> None:
        existing = [{"role": "user", "content": "Hi"}]
        s = _make_session_mock(id="sid", chat_history=json.dumps(existing))
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        await svc.append_chat_message("sid", "assistant", "Hi back")

        history = json.loads(s.chat_history)
        assert len(history) == 2
        assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_handles_corrupt_json_by_resetting(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid", chat_history="{bad json")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        await svc.append_chat_message("sid", "user", "Hello")

        history = json.loads(s.chat_history)
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_truncates_at_100_messages(self, svc: WorkspaceService, session: AsyncMock) -> None:
        existing = [{"role": "user", "content": f"msg{i}"} for i in range(100)]
        s = _make_session_mock(id="sid", chat_history=json.dumps(existing))
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        await svc.append_chat_message("sid", "user", "overflow")

        history = json.loads(s.chat_history)
        assert len(history) == 100
        # first message should be dropped (101 -> keep last 100)
        assert history[0]["content"] == "msg1"
        assert history[-1]["content"] == "overflow"

    @pytest.mark.asyncio
    async def test_returns_none_when_session_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.append_chat_message("nonexistent", "user", "Hello")

        assert result is None


class TestGetChatHistory:
    @pytest.mark.asyncio
    async def test_returns_parsed_history(self, svc: WorkspaceService, session: AsyncMock) -> None:
        existing = [{"role": "user", "content": "Hi"}]
        s = _make_session_mock(id="sid", chat_history=json.dumps(existing))
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        result = await svc.get_chat_history("sid")

        assert result == existing

    @pytest.mark.asyncio
    async def test_returns_empty_for_none_history(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid", chat_history=None)
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        result = await svc.get_chat_history("sid")

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_session_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.get_chat_history("nonexistent")

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_corrupt_json(self, svc: WorkspaceService, session: AsyncMock) -> None:
        s = _make_session_mock(id="sid", chat_history="not json")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=s)))

        result = await svc.get_chat_history("sid")

        assert result == []


# ===================================================================
# Notes — create / list / update / delete
# ===================================================================

class TestCreateNote:
    @pytest.mark.asyncio
    async def test_creates_minimal_note(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_note("sid", "some content")

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert isinstance(result, ResearchNote)
        assert result.content == "some content"
        assert result.session_id == "sid"

    @pytest.mark.asyncio
    async def test_creates_note_with_entity(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_note("sid", "content", entity_type="disease", entity_id="aaa-bbb")

        assert result.entity_type == "disease"
        assert result.entity_id == "aaa-bbb"

    @pytest.mark.asyncio
    async def test_stores_entity_id_as_str(self, svc: WorkspaceService, session: AsyncMock) -> None:
        uid = UUID("12345678-1234-5678-1234-567812345678")
        result = await svc.create_note("sid", "content", entity_id=uid)

        assert result.entity_id == str(uid)

    @pytest.mark.asyncio
    async def test_entity_id_none_when_not_provided(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_note("sid", "content")

        assert result.entity_id is None

    @pytest.mark.asyncio
    async def test_creates_note_with_tags(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_note("sid", "content", tags="tag1,tag2")

        assert result.tags == "tag1,tag2"


class TestListNotes:
    @pytest.mark.asyncio
    async def test_returns_notes(self, svc: WorkspaceService, session: AsyncMock) -> None:
        n1, n2 = _make_note_mock(), _make_note_mock()
        scalars_mock = MagicMock(all=MagicMock(return_value=[n1, n2]))
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

        result = await svc.list_notes("sid")

        assert result == [n1, n2]
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, svc: WorkspaceService, session: AsyncMock) -> None:
        scalars_mock = MagicMock(all=MagicMock(return_value=[]))
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

        result = await svc.list_notes("sid")

        assert result == []


class TestUpdateNote:
    @pytest.mark.asyncio
    async def test_updates_content(self, svc: WorkspaceService, session: AsyncMock) -> None:
        n = _make_note_mock(id="nid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=n)))

        result = await svc.update_note("nid", content="updated")

        assert result is n
        assert n.content == "updated"
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_tags(self, svc: WorkspaceService, session: AsyncMock) -> None:
        n = _make_note_mock(id="nid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=n)))

        result = await svc.update_note("nid", tags="newtag")

        assert result is n
        assert n.tags == "newtag"

    @pytest.mark.asyncio
    async def test_partial_update_preserves_other_fields(self, svc: WorkspaceService, session: AsyncMock) -> None:
        n = _make_note_mock(id="nid", content="old", tags="oldtag")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=n)))

        await svc.update_note("nid", content="new")

        assert n.content == "new"
        assert n.tags == "oldtag"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.update_note("nonexistent", content="x")

        assert result is None


class TestDeleteNote:
    @pytest.mark.asyncio
    async def test_soft_deletes(self, svc: WorkspaceService, session: AsyncMock) -> None:
        n = _make_note_mock(id="nid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=n)))

        result = await svc.delete_note("nid")

        assert result is True
        assert n.is_deleted is True
        assert n.deleted_at is not None

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.delete_note("nonexistent")

        assert result is False


class TestGetNoteWithSession:
    @pytest.mark.asyncio
    async def test_returns_note_and_session(self, svc: WorkspaceService, session: AsyncMock) -> None:
        n = _make_note_mock(id="nid")
        s = _make_session_mock(id="sid")
        session.execute = AsyncMock(return_value=MagicMock(one_or_none=MagicMock(return_value=(n, s))))

        result = await svc.get_note_with_session("nid")

        assert result == (n, s)

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(one_or_none=MagicMock(return_value=None)))

        result = await svc.get_note_with_session("nonexistent")

        assert result is None


# ===================================================================
# QueryHistory
# ===================================================================

class TestCreateQueryHistory:
    @pytest.mark.asyncio
    async def test_creates_query(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_query_history("sid", "search text", "search", result_summary="{}", citation_count=3)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert isinstance(result, QueryHistory)
        assert result.session_id == "sid"
        assert result.query_text == "search text"
        assert result.query_type == "search"
        assert result.result_summary == "{}"
        assert result.citation_count == 3

    @pytest.mark.asyncio
    async def test_defaults_citation_count_to_zero(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_query_history("sid", "q", "report")

        assert result.citation_count == 0
        assert result.result_summary is None


class TestGetQueryHistory:
    @pytest.mark.asyncio
    async def test_returns_queries(self, svc: WorkspaceService, session: AsyncMock) -> None:
        q1, q2 = _make_qh_mock(), _make_qh_mock()
        scalars_mock = MagicMock(all=MagicMock(return_value=[q1, q2]))
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

        result = await svc.get_query_history("sid")

        assert result == [q1, q2]

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, svc: WorkspaceService, session: AsyncMock) -> None:
        scalars_mock = MagicMock(all=MagicMock(return_value=[]))
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

        result = await svc.get_query_history("sid")

        assert result == []


# ===================================================================
# CitationCollection
# ===================================================================

class TestCreateCitation:
    @pytest.mark.asyncio
    async def test_creates_citation(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_citation(
            "sid",
            trace_json='{"key":"val"}',
            citation_text="formatted text",
            source_document="doc-name",
            tags="tag1",
            notes="user note",
        )

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert isinstance(result, CitationCollection)
        assert result.session_id == "sid"
        assert result.trace_json == '{"key":"val"}'
        assert result.citation_text == "formatted text"
        assert result.source_document == "doc-name"
        assert result.tags == "tag1"
        assert result.notes == "user note"

    @pytest.mark.asyncio
    async def test_optional_tags_and_notes(self, svc: WorkspaceService, session: AsyncMock) -> None:
        result = await svc.create_citation("sid", "{}", "text", "doc")

        assert result.tags is None
        assert result.notes is None


class TestListCitations:
    @pytest.mark.asyncio
    async def test_returns_citations(self, svc: WorkspaceService, session: AsyncMock) -> None:
        c1, c2 = _make_citation_mock(), _make_citation_mock()
        scalars_mock = MagicMock(all=MagicMock(return_value=[c1, c2]))
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

        result = await svc.list_citations("sid")

        assert result == [c1, c2]

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, svc: WorkspaceService, session: AsyncMock) -> None:
        scalars_mock = MagicMock(all=MagicMock(return_value=[]))
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=scalars_mock)))

        result = await svc.list_citations("sid")

        assert result == []


class TestGetCitation:
    @pytest.mark.asyncio
    async def test_returns_citation_when_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        c = _make_citation_mock(id="cid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=c)))

        result = await svc.get_citation("cid")

        assert result is c

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.get_citation("nonexistent")

        assert result is None


class TestUpdateCitation:
    @pytest.mark.asyncio
    async def test_updates_tags_and_notes(self, svc: WorkspaceService, session: AsyncMock) -> None:
        c = _make_citation_mock(id="cid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=c)))

        result = await svc.update_citation("cid", tags="new-tag", notes="new-note")

        assert result is c
        assert c.tags == "new-tag"
        assert c.notes == "new-note"
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_partial_update(self, svc: WorkspaceService, session: AsyncMock) -> None:
        c = _make_citation_mock(id="cid", tags="old", notes="old")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=c)))

        await svc.update_citation("cid", tags="new")

        assert c.tags == "new"
        assert c.notes == "old"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.update_citation("nonexistent", tags="x")

        assert result is None


class TestDeleteCitation:
    @pytest.mark.asyncio
    async def test_hard_deletes(self, svc: WorkspaceService, session: AsyncMock) -> None:
        c = _make_citation_mock(id="cid")
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=c)))

        result = await svc.delete_citation("cid")

        assert result is True
        session.delete.assert_called_once_with(c)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self, svc: WorkspaceService, session: AsyncMock) -> None:
        session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.delete_citation("nonexistent")

        assert result is False
        session.delete.assert_not_called()
