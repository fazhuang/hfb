"""Unit tests for PersonService and DocumentService validation hooks and methods."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.document_service import DocumentService
from app.services.person_service import PersonService

# ---------------------------------------------------------------------------
# PersonService
# ---------------------------------------------------------------------------


class TestPersonServiceValidateCreate:
    """Lines 20-21: _validate_create raises on empty/missing name."""

    @pytest.mark.asyncio
    async def test_empty_name_raises_valueerror(self):
        svc = PersonService(MagicMock())
        with pytest.raises(ValueError, match="Person name is required"):
            await svc._validate_create({"name": ""})

    @pytest.mark.asyncio
    async def test_whitespace_name_raises_valueerror(self):
        svc = PersonService(MagicMock())
        with pytest.raises(ValueError, match="Person name is required"):
            await svc._validate_create({"name": "   "})

    @pytest.mark.asyncio
    async def test_valid_name_passes(self):
        svc = PersonService(MagicMock())
        await svc._validate_create({"name": "皇甫谧"})  # no raise


class TestPersonServiceSearch:
    """Line 24: search delegates to repo.search_query."""

    @pytest.mark.asyncio
    async def test_search_delegates_to_repo(self):
        session = MagicMock()
        svc = PersonService(session)
        svc.repo.search_query = AsyncMock(return_value=([], 0))

        result = await svc.search("皇甫谧", page=1, limit=10)
        svc.repo.search_query.assert_awaited_once_with("皇甫谧", page=1, limit=10)
        assert result == ([], 0)


class TestPersonServiceGetByDynasty:
    """Line 27: get_by_dynasty delegates to repo.get_by_dynasty."""

    @pytest.mark.asyncio
    async def test_get_by_dynasty_delegates_to_repo(self):
        session = MagicMock()
        svc = PersonService(session)
        svc.repo.get_by_dynasty = AsyncMock(return_value=([], 0))

        result = await svc.get_by_dynasty("晋", page=2, limit=15)
        svc.repo.get_by_dynasty.assert_awaited_once_with("晋", page=2, limit=15)
        assert result == ([], 0)


# ---------------------------------------------------------------------------
# DocumentService
# ---------------------------------------------------------------------------


class TestDocumentServiceValidateCreate:
    """Line 23: _validate_create raises on empty/missing title."""

    @pytest.mark.asyncio
    async def test_empty_title_raises_valueerror(self):
        svc = DocumentService(MagicMock())
        with pytest.raises(ValueError, match="Document title is required"):
            await svc._validate_create({"title": ""})

    @pytest.mark.asyncio
    async def test_whitespace_title_raises_valueerror(self):
        svc = DocumentService(MagicMock())
        with pytest.raises(ValueError, match="Document title is required"):
            await svc._validate_create({"title": "   "})

    @pytest.mark.asyncio
    async def test_valid_title_passes(self):
        svc = DocumentService(MagicMock())
        await svc._validate_create({"title": "针灸甲乙经"})  # no raise


class TestDocumentServiceSearch:
    """Line 40: search delegates with all filter params to repo.search_query."""

    @pytest.mark.asyncio
    async def test_search_delegates_all_params_to_repo(self):
        session = MagicMock()
        svc = DocumentService(session)
        svc.repo.search_query = AsyncMock(return_value=([], 0))

        result = await svc.search(
            query="伤寒",
            page=1,
            limit=5,
            copyright_status="public_domain",
            review_status="approved",
            rag_enabled=True,
            source_name="ctext",
            dynasty="汉",
            category="方剂",
            user_id="user-1",
            session_id="session-1",
        )

        svc.repo.search_query.assert_awaited_once_with(
            "伤寒",
            page=1,
            limit=5,
            copyright_status="public_domain",
            review_status="approved",
            rag_enabled=True,
            source_name="ctext",
            dynasty="汉",
            category="方剂",
            user_id="user-1",
            session_id="session-1",
        )
        assert result == ([], 0)

    @pytest.mark.asyncio
    async def test_search_defaults_none_filters(self):
        session = MagicMock()
        svc = DocumentService(session)
        svc.repo.search_query = AsyncMock(return_value=([], 0))

        await svc.search("query")
        svc.repo.search_query.assert_awaited_once_with(
            "query",
            page=1,
            limit=20,
            copyright_status=None,
            review_status=None,
            rag_enabled=None,
            source_name=None,
            dynasty=None,
            category=None,
            user_id=None,
            session_id=None,
        )
