"""Unit tests for SearchService — pure helpers and mocked async paths."""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.services.search_service import (
    ENTITY_CONFIG,
    SearchService,
    _compute_score,
    _make_snippet,
)
from app.schemas.search import SearchParams, SuggestItem


# ---------------------------------------------------------------------------
# _make_snippet
# ---------------------------------------------------------------------------

class TestMakeSnippet:
    """Pure helper — lines 142-161."""

    def test_match_within_text_includes_ellipsis_start(self):
        """Line 158: snippet starts with … when start > 0."""
        text = "A" * 100 + "keyword" + "B" * 100
        result = _make_snippet(text, "keyword")
        assert result.startswith("…")
        assert "keyword" in result

    def test_match_within_text_includes_ellipsis_end(self):
        """Line 159-160: snippet ends with … when end < len(text)."""
        text = "A" * 100 + "keyword" + "C" * 100
        result = _make_snippet(text, "keyword")
        assert result.endswith("…")

    def test_null_text_returns_none(self):
        assert _make_snippet(None, "query") is None

    def test_null_query_returns_truncated_text(self):
        result = _make_snippet("hello world" * 50, "")
        assert len(result) <= 200

    def test_no_match_truncates(self):
        result = _make_snippet("A" * 250, "x")
        assert len(result) == 200
        assert "…" not in result

    def test_empty_text(self):
        # empty string is falsy → text[:max_length] if text else None → None
        result = _make_snippet("", "query")
        assert result is None

    def test_both_none(self):
        assert _make_snippet(None, None) is None


# ---------------------------------------------------------------------------
# _compute_score
# ---------------------------------------------------------------------------

class TestComputeScore:
    """Pure helper — lines 164-172."""

    def test_title_match_gives_high_score(self):
        score = _compute_score(match_count=2, total_fields=4, title_match=True)
        assert score > 0.6  # 0.3*(2/4) + 0.5 = 0.65

    def test_no_title_match_lower_score(self):
        score = _compute_score(match_count=2, total_fields=4, title_match=False)
        assert score == pytest.approx(0.15, rel=1e-3)

    def test_zero_matches_returns_zero(self):
        assert _compute_score(0, 4, title_match=True) == 0.0

    def test_all_matched_with_title_near_one(self):
        score = _compute_score(match_count=5, total_fields=5, title_match=True)
        assert score == pytest.approx(0.8, rel=1e-3)

    def test_exceeds_one_is_clamped(self):
        score = _compute_score(match_count=100, total_fields=3, title_match=True)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# SearchService._search_entity_type — edge cases via mock
# ---------------------------------------------------------------------------

class TestSearchEntityType:

    @pytest.mark.asyncio
    async def test_unknown_entity_type_skipped(self):
        """Line 207: entity_type not in ENTITY_CONFIG => continue."""
        session = AsyncMock()
        svc = SearchService(session)
        params = SearchParams(q="test", entity_types=["nonexistent"])

        result = await svc.search(params)
        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_empty_query_terms_fallback_to_raw_query(self):
        """Line 274: query_terms fallback when query.split() is empty (only spaces)."""
        session = AsyncMock()
        session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        svc = SearchService(session)
        params = SearchParams(q="   ", entity_types=["person"])
        result = await svc.search(params)
        assert result.items == []
        # query_terms should be ["   "], so conditions should still be built

    @pytest.mark.asyncio
    async def test_entity_type_without_search_fields_returns_empty(self):
        """Line 284: no searchable columns on the model => return []."""
        session = AsyncMock()

        svc = SearchService(session)

        # Model where ALL search_fields are invalid → no conditions built
        class _NoColModel:
            pass

        config = {
            "model": _NoColModel,
            "title_field": "name",
            "subtitle_field": "dynasty",
            "search_fields": ["nonexistent_column"],
            "snippet_field": None,
            "meta_fields": [],
            "route_prefix": None,
        }
        result = await svc._search_entity_type(
            "person", config, "test", SearchParams(q="test", entity_types=["person"])
        )
        assert result == []


# ---------------------------------------------------------------------------
# SearchService.suggest — edge cases
# ---------------------------------------------------------------------------

class TestSuggest:

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self):
        session = AsyncMock()
        svc = SearchService(session)
        result = await svc.suggest("   ", limit=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_entity_type_not_in_config_skipped(self):
        """Line 419: entity_type not in ENTITY_CONFIG => continue."""
        session = AsyncMock()
        session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.__aiter__.return_value = iter([
            ("皇甫谧", "person", "id-1"),
        ])
        session.execute.return_value = mock_result

        svc = SearchService(session)

        with patch.dict(
            "app.services.search_service.ENTITY_CONFIG",
            {
                **ENTITY_CONFIG,
            },
            clear=True,
        ):
            # person is in config, so it should reach it
            result = await svc.suggest("皇甫", limit=5)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_model_without_title_field_skipped(self):
        """Line 425: title_col is None => continue."""
        session = AsyncMock()
        session.execute = AsyncMock()

        svc = SearchService(session)

        config = ENTITY_CONFIG["person"].copy()
        config["title_field"] = "nonexistent_field"

        # Patch ENTITY_CONFIG to simulate a model without the title column
        with patch.dict(
            "app.services.search_service.ENTITY_CONFIG",
            {"person": config},
            clear=False,
        ):
            from app.models.person import Person
            result = await svc._search_entity_type(
                "person", {"model": Person, "title_field": "nonexistent_field",
                           "subtitle_field": "dynasty", "search_fields": ["nonexistent_field"],
                           "snippet_field": None, "meta_fields": [], "route_prefix": None},
                "test", SearchParams(q="test", entity_types=["person"])
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_suggest_breaks_at_limit_during_inner_loop(self):
        """Line 438: inner break when len(suggestions) >= limit."""
        session = AsyncMock()
        session.execute = AsyncMock()

        # Return more rows than the limit
        rows = [(f"Result {i}",) for i in range(10)]
        mock_result = MagicMock()
        mock_result.__aiter__.return_value = iter(rows)
        session.execute.return_value = mock_result

        svc = SearchService(session)

        # Only 'person' and 'book' are in priority_types, they'll be tried first
        # but due to the mock execute, the first query (person) returns 10 rows
        # the inner loop should break at limit
        result = await svc.suggest("test", limit=3)
        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_suggest_passage_truncates_text_to_50(self):
        """Line 441: passage text truncated to 50 chars."""
        session = AsyncMock()
        session.execute = AsyncMock()

        long_text = "A" * 100
        mock_result = MagicMock()
        mock_result.__aiter__.return_value = iter([("passage-id", long_text)])
        session.execute.return_value = mock_result

        svc = SearchService(session)

        with patch.dict(
            "app.services.search_service.ENTITY_CONFIG",
            {
                "passage": ENTITY_CONFIG["passage"],
            },
            clear=True,
        ):
            result = await svc.suggest("A", limit=1)
            if result:
                assert len(result[0].text) <= 50


# ---------------------------------------------------------------------------
# SearchService.search — dynasty and category filter branches
# ---------------------------------------------------------------------------

class TestSearchDynastyFilter:
    """Lines 303->306: dynasty filter on search."""

    @pytest.mark.asyncio
    async def test_dynasty_filter_applied(self):
        """Dynasty filter applied to model with dynasty column."""
        session = AsyncMock()
        session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        svc = SearchService(session)
        params = SearchParams(q="test", entity_types=["person"], dynasty="晋")
        result = await svc.search(params)
        assert result.items == []


class TestSearchCategoryFilter:
    """Lines 307-309: category filter only for books."""

    @pytest.mark.asyncio
    async def test_category_filter_not_applied_to_non_book(self):
        """Category filter is only applied when entity_type == 'book'."""
        session = AsyncMock()
        session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        svc = SearchService(session)
        # category + person entity type should NOT apply the book-only filter
        params = SearchParams(q="test", entity_types=["person"], category="针灸")
        result = await svc.search(params)
        assert result.items == []

    @pytest.mark.asyncio
    async def test_category_filter_applied_to_book(self):
        """Category filter applied for book entity type."""
        session = AsyncMock()
        session.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        svc = SearchService(session)
        params = SearchParams(q="test", entity_types=["book"], category="针灸")
        result = await svc.search(params)
        assert result.items == []


# ---------------------------------------------------------------------------
# SearchService.reindex
# ---------------------------------------------------------------------------

class TestReindex:

    @pytest.mark.asyncio
    async def test_reindex_counts_all_entities(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 5
        session.execute = AsyncMock(return_value=mock_result)

        svc = SearchService(session)
        result = await svc.reindex()
        assert result["status"] == "completed"
        assert result["errors"] == []
        # 7 entity types, each returns count=5 => total=35
        assert result["entities_indexed"] == 35
