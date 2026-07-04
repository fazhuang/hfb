"""
Version Center tests — lineage, comparison, diff, passage mapping.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.version_center import VersionComparisonService
from app.models.version import Version
from app.models.passage import Passage

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


async def _seed_versions(
    session: AsyncSession,
) -> tuple[Version, Version, Passage, Passage]:
    """Create two versions with passages for testing."""
    from app.models.book import Book
    from app.models.chapter import Chapter

    book = Book(id="b1", title="测试书籍", dynasty="宋")
    session.add(book)
    chapter = Chapter(id="c1", book_id="b1", title="第一章", order=1)
    session.add(chapter)
    await session.flush()

    v1 = Version(
        book_id="b1", version_name="北宋刻本", era="宋", repository="国家图书馆"
    )
    v2 = Version(book_id="b1", version_name="明刻本", era="明", repository="上海图书馆")
    session.add_all([v1, v2])
    await session.flush()

    p1 = Passage(
        chapter_id="c1",
        version_id=v1.id,
        content_text="凡刺之法，必候日月星辰，四时八正之气，气定乃刺之。",
        order=1,
    )
    p2 = Passage(
        chapter_id="c1",
        version_id=v2.id,
        content_text="凡刺之法，必候日月星辰，四时八节之气，气定乃可刺也。",
        order=1,
    )
    p3 = Passage(
        chapter_id="c1",
        version_id=v1.id,
        content_text="是故天温日明，则人血淖液而卫气浮。",
        order=2,
    )
    session.add_all([p1, p2, p3])
    await session.flush()
    return v1, v2, p1, p2


class TestVersionLineage:
    @pytest.mark.asyncio
    async def test_get_lineage_empty(self, db_session: AsyncSession):
        from app.models.book import Book

        session = db_session
        b = Book(id="b1", title="测试书籍", dynasty="宋")
        session.add(b)
        await session.flush()
        v = Version(book_id="b1", version_name="测试版本")
        session.add(v)
        await session.flush()

        svc = VersionComparisonService(session)
        data = await svc.get_lineage(v.id)
        assert data["version"]["version_name"] == "测试版本"
        assert len(data["ancestors"]) == 0
        assert len(data["descendants"]) == 0

    @pytest.mark.asyncio
    async def test_add_relation_and_lineage(self, db_session: AsyncSession):
        from app.models.book import Book

        session = db_session
        b = Book(id="b1", title="测试书籍", dynasty="宋")
        session.add(b)
        await session.flush()
        v_src = Version(book_id="b1", version_name="宋本")
        v_tgt = Version(book_id="b1", version_name="明本")
        session.add_all([v_src, v_tgt])
        await session.flush()

        svc = VersionComparisonService(session)
        await svc.add_relation(v_src.id, v_tgt.id, "derived_from", "明本承袭宋本")

        data = await svc.get_lineage(v_tgt.id)
        assert len(data["ancestors"]) == 1
        assert data["ancestors"][0]["relation_type"] == "derived_from"

    @pytest.mark.asyncio
    async def test_invalid_relation_type(self, db_session: AsyncSession):
        svc = VersionComparisonService(db_session)
        with pytest.raises(ValueError, match="Invalid relation_type"):
            await svc.add_relation("a", "b", "invalid_type")


class TestVersionComparison:
    @pytest.mark.asyncio
    async def test_compare_passages(self, db_session: AsyncSession):
        _, _, p1, p2 = await _seed_versions(db_session)
        svc = VersionComparisonService(db_session)
        result = await svc.compare_passages(p1.id, p2.id)

        assert result["source_passage"]["id"] == p1.id
        assert result["target_passage"]["id"] == p2.id
        assert "similarity_ratio" in result
        # The texts differ (八正 vs 八节), should have differences
        assert result["differences"] > 0

    @pytest.mark.asyncio
    async def test_compare_identical_passages(self, db_session: AsyncSession):
        from app.models.book import Book
        from app.models.chapter import Chapter

        session = db_session
        b = Book(id="b1", title="测试书籍", dynasty="宋")
        session.add(b)
        c = Chapter(id="c1", book_id="b1", title="第一章", order=1)
        session.add(c)
        await session.flush()
        v = Version(book_id="b1", version_name="Test")
        session.add(v)
        await session.flush()

        p1 = Passage(
            chapter_id="c1",
            version_id=v.id,
            content_text="黄帝问曰：针道可得闻乎？",
            order=1,
        )
        p2 = Passage(
            chapter_id="c1",
            version_id=v.id,
            content_text="黄帝问曰：针道可得闻乎？",
            order=2,
        )
        session.add_all([p1, p2])
        await session.flush()

        svc = VersionComparisonService(session)
        result = await svc.compare_passages(p1.id, p2.id)
        assert result["differences"] == 0
        assert result["similarity_ratio"] == 1.0

    @pytest.mark.asyncio
    async def test_full_version_compare(self, db_session: AsyncSession):
        v1, v2, _, _ = await _seed_versions(db_session)
        svc = VersionComparisonService(db_session)
        result = await svc.run_full_compare(v1.id, v2.id)

        assert result["source_version_id"] == v1.id
        assert result["diff_id"] is not None
        # Should have at least 1 pair (order-aligned)
        assert result["passage_pairs"] >= 1

    @pytest.mark.asyncio
    async def test_passage_not_found(self, db_session: AsyncSession):
        svc = VersionComparisonService(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.compare_passages("nonexistent-id", "nonexistent-id")


class TestPassageMapping:
    @pytest.mark.asyncio
    async def test_create_mapping(self, db_session: AsyncSession):
        _, _, p1, p2 = await _seed_versions(db_session)
        svc = VersionComparisonService(db_session)

        mapping = await svc.create_passage_mapping(p1.id, p2.id, "equivalent", "第12条")
        assert mapping.mapping_type == "equivalent"
        assert mapping.source_passage_id == p1.id

    @pytest.mark.asyncio
    async def test_invalid_mapping_type(self, db_session: AsyncSession):
        svc = VersionComparisonService(db_session)
        with pytest.raises(ValueError, match="Invalid mapping_type"):
            await svc.create_passage_mapping("a", "b", "bad_type")

    @pytest.mark.asyncio
    async def test_get_mappings(self, db_session: AsyncSession):
        _, _, p1, p2 = await _seed_versions(db_session)
        svc = VersionComparisonService(db_session)

        await svc.create_passage_mapping(p1.id, p2.id, "equivalent")

        mappings = await svc.get_passage_mappings(p1.version_id)
        assert len(mappings) >= 1
