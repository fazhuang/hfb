"""
Tests for Unified Search — SearchService, schemas, and API.

Per HFB-PS-1706 Unified Search Product Specification.
"""

from __future__ import annotations

import pytest
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.passage import Passage
from app.models.person import Person
from app.models.version import Version
from app.schemas.search import (
    SearchParams,
    SearchResultItem,
    SuggestItem,
)
from app.services.search_service import (
    ENTITY_CONFIG,
    SEARCHABLE_TYPES,
    SearchService,
    _compute_score,
    _make_snippet,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401

# ============================================================
# Unit: snippet and scoring
# ============================================================


class TestSnippet:
    def test_exact_match(self) -> None:
        text = "皇甫谧编撰《针灸甲乙经》十二卷。"
        snip = _make_snippet(text, "针灸")
        assert "针灸" in (snip or "")

    def test_no_query_returns_prefix(self) -> None:
        text = "A" * 300
        snip = _make_snippet(text, "")
        assert len(snip or "") == 200

    def test_none_text(self) -> None:
        assert _make_snippet(None, "test") is None

    def test_no_match_truncates(self) -> None:
        text = "这是一段不匹配的文本" * 20
        snip = _make_snippet(text, "不存在")
        assert len(snip or "") == 200


class TestScore:
    def test_perfect_match(self) -> None:
        score = _compute_score(3, 3, True)
        assert score > 0.7

    def test_no_match(self) -> None:
        score = _compute_score(0, 3, False)
        assert score == 0.0

    def test_title_bonus(self) -> None:
        with_title = _compute_score(1, 5, True)
        without_title = _compute_score(1, 5, False)
        assert with_title > without_title


# ============================================================
# Unit: schema validation
# ============================================================


class TestSearchSchemas:
    def test_search_params_defaults(self) -> None:
        params = SearchParams(q="针灸")
        assert params.q == "针灸"
        assert "person" in params.entity_types
        assert params.page == 1
        assert params.limit == 20

    def test_suggest_item(self) -> None:
        item = SuggestItem(text="针灸甲乙经", entity_type="book")
        assert item.text == "针灸甲乙经"
        assert item.entity_type == "book"

    def test_search_result_item(self) -> None:
        item = SearchResultItem(
            id="abc",
            entity_type="book",
            title="针灸甲乙经",
            subtitle="西晋",
            snippet="针灸专著",
            score=0.85,
        )
        assert item.score == 0.85
        assert item.entity_type == "book"


# ============================================================
# Unit: ENTITY_CONFIG
# ============================================================


class TestEntityConfig:
    def test_all_types_have_config(self) -> None:
        for et in SEARCHABLE_TYPES:
            assert et in ENTITY_CONFIG, f"Missing config for {et}"

    def test_required_fields(self) -> None:
        for et, cfg in ENTITY_CONFIG.items():
            assert "model" in cfg, f"{et}: missing model"
            assert "title_field" in cfg, f"{et}: missing title_field"
            assert "search_fields" in cfg, f"{et}: missing search_fields"
            assert len(cfg["search_fields"]) > 0, f"{et}: empty search_fields"

    def test_all_models_have_search_fields(self) -> None:
        """Ensure every search field actually exists on the model."""
        # We don't need a real session for this — just check attribute existence
        for et, cfg in ENTITY_CONFIG.items():
            model = cfg["model"]
            for field_name in cfg["search_fields"]:
                assert hasattr(model, field_name), f"{et}.{field_name} missing"


# ============================================================
# Integration: SearchService with test database
# ============================================================


@pytest.mark.asyncio
class TestSearchService:
    async def test_empty_search(self, db_session: AsyncSession) -> None:
        svc = SearchService(db_session)
        result = await svc.search(SearchParams(q="somethingthatwillnevermatchxyz"))
        assert result.total == 0
        assert len(result.items) == 0

    async def test_search_with_data(self, db_session: AsyncSession) -> None:
        # Seed test data
        p = Person(name="测试人物", dynasty="唐", biography="针灸大师")
        db_session.add(p)
        await db_session.flush()

        b = Book(
            title="针灸测试经",
            dynasty="唐",
            category="针灸",
            abstract="一部关于针灸的经典",
        )
        db_session.add(b)
        await db_session.flush()

        svc = SearchService(db_session)
        result = await svc.search(
            SearchParams(q="针灸", entity_types=["person", "book"])
        )

        assert result.total >= 2
        assert result.query == "针灸"

        types_in_results = {r.entity_type for r in result.items}
        assert "person" in types_in_results
        assert "book" in types_in_results

    async def test_search_filter_by_type(self, db_session: AsyncSession) -> None:
        p = Person(name="李医师", dynasty="明")
        db_session.add(p)
        await db_session.flush()

        svc = SearchService(db_session)
        result = await svc.search(SearchParams(q="李医师", entity_types=["book"]))
        # Searching only "book" type — person shouldn't appear
        book_results = [r for r in result.items if r.entity_type == "person"]
        assert len(book_results) == 0

    async def test_passage_result_includes_version_provenance(
        self,
        db_session: AsyncSession,
    ) -> None:
        book = Book(title="针灸甲乙经（验证）")
        db_session.add(book)
        await db_session.flush()
        chapter = Chapter(book_id=book.id, title="卷一", order=1)
        version = Version(
            book_id=book.id,
            version_name="验证本 A",
            repository="流程验证资料库",
            shelf_mark="VALIDATION-A",
        )
        db_session.add_all([chapter, version])
        await db_session.flush()
        passage = Passage(
            chapter_id=chapter.id,
            version_id=version.id,
            content_text="凡刺之法，必候日月星辰。",
            order=1,
        )
        db_session.add(passage)
        await db_session.flush()

        result = await SearchService(db_session).search(
            SearchParams(q="日月星辰", entity_types=["passage"])
        )

        item = result.items[0]
        assert item.metadata["version_name"] == "验证本 A"
        assert item.metadata["repository"] == "流程验证资料库"
        assert item.metadata["shelf_mark"] == "VALIDATION-A"
        assert item.metadata["chapter_title"] == "卷一"

    async def test_search_by_dynasty_filter(self, db_session: AsyncSession) -> None:
        p1 = Person(name="唐医", dynasty="唐")
        p2 = Person(name="宋医", dynasty="宋")
        db_session.add_all([p1, p2])
        await db_session.flush()

        svc = SearchService(db_session)
        result = await svc.search(
            SearchParams(q="医", entity_types=["person"], dynasty="唐")
        )

        for r in result.items:
            if r.entity_type == "person":
                assert r.metadata.get("dynasty") == "唐"

    async def test_search_pagination(self, db_session: AsyncSession) -> None:
        for i in range(5):
            p = Person(name=f"分页测试人物{i}")
            db_session.add(p)
        await db_session.flush()

        svc = SearchService(db_session)
        result = await svc.search(
            SearchParams(q="分页测试", entity_types=["person"], page=1, limit=3)
        )
        assert result.page == 1
        assert result.limit == 3
        assert result.total >= 5
        assert result.total_pages >= 2

    async def test_suggest(self, db_session: AsyncSession) -> None:
        p = Person(name="皇甫谧")
        db_session.add(p)
        await db_session.flush()

        b = Book(title="针灸甲乙经", dynasty="西晋")
        db_session.add(b)
        await db_session.flush()

        svc = SearchService(db_session)
        suggestions = await svc.suggest("皇", limit=3)
        assert len(suggestions) >= 1
        assert any("皇甫" in s.text for s in suggestions)

    async def test_suggest_empty_query(self, db_session: AsyncSession) -> None:
        svc = SearchService(db_session)
        suggestions = await svc.suggest("")
        assert len(suggestions) == 0

    async def test_suggest_limit(self, db_session: AsyncSession) -> None:
        for i in range(10):
            p = Person(name=f"张医师{i:02d}")
            db_session.add(p)
        await db_session.flush()

        svc = SearchService(db_session)
        suggestions = await svc.suggest("张医", limit=4)
        assert len(suggestions) <= 4

    async def test_reindex(self, db_session: AsyncSession) -> None:
        p = Person(name="repair-tool-test")
        db_session.add(p)
        await db_session.flush()

        svc = SearchService(db_session)
        result = await svc.reindex()
        assert result["status"] == "completed"
        assert result["entities_indexed"] >= 1

    async def test_search_result_has_required_fields(
        self, db_session: AsyncSession
    ) -> None:
        b = Book(title="伤寒论研究", dynasty="东汉", abstract="张仲景著作研究")
        db_session.add(b)
        await db_session.flush()

        svc = SearchService(db_session)
        result = await svc.search(SearchParams(q="伤寒论"))

        for item in result.items:
            assert item.id
            assert item.entity_type
            assert item.title
            assert item.score >= 0
            assert item.score <= 1

    async def test_search_score_ordering(self, db_session: AsyncSession) -> None:
        # Title match should score higher
        b1 = Book(title="针灸甲乙经", dynasty="西晋", abstract="无关联内容")
        b2 = Book(title="本草纲目", dynasty="明", abstract="针灸相关内容在本草纲目中")
        db_session.add_all([b1, b2])
        await db_session.flush()

        svc = SearchService(db_session)
        result = await svc.search(SearchParams(q="针灸", entity_types=["book"]))

        book_results = [r for r in result.items if r.entity_type == "book"]
        if len(book_results) >= 2:
            # Title match (针灸甲乙经) should score higher than abstract-only match (本草纲目)
            scores = [r.score for r in book_results]
            assert scores == sorted(scores, reverse=True), (
                f"Results not score-sorted: {scores}"
            )
