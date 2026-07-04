"""
Tests for entity repositories — CRUD + search for Phase 3 models.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.version import Version
from app.repositories.entities import (
    BookRepository,
    VersionRepository,
    PassageRepository,
    PaperRepository,
    ImageRepository,
)

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


class TestBookRepository:
    @pytest.mark.asyncio
    async def test_create_and_search(self, db_session: AsyncSession):
        repo = BookRepository(db_session)
        await repo.create(title="针灸甲乙经", dynasty="西晋")
        await repo.create(title="伤寒杂病论", dynasty="东汉")
        await repo.create(title="本草纲目", dynasty="明")

        items, total = await repo.search_query("针灸")
        assert total == 1
        assert items[0].title == "针灸甲乙经"

    @pytest.mark.asyncio
    async def test_count(self, db_session: AsyncSession):
        repo = BookRepository(db_session)
        for i in range(3):
            await repo.create(title=f"Book {i}")
        assert await repo.count() == 3


class TestVersionRepository:
    @pytest.mark.asyncio
    async def test_create(self, db_session: AsyncSession):
        # FK constraint: Version.book_id must reference an existing Book
        book = Book(title="测试书籍", dynasty="宋")
        db_session.add(book)
        await db_session.flush()

        repo = VersionRepository(db_session)
        v = await repo.create(book_id=book.id, version_name="北宋刻本", era="宋")
        assert v.version_name == "北宋刻本"
        assert v.id is not None


class TestPassageRepository:
    @pytest.mark.asyncio
    async def test_search(self, db_session: AsyncSession):
        # FK constraint: Passage needs Book → Chapter → Version chain
        book = Book(title="测试书籍2", dynasty="汉")
        db_session.add(book)
        await db_session.flush()

        chapter1 = Chapter(book_id=book.id, title="章节1", order=1)
        chapter2 = Chapter(book_id=book.id, title="章节2", order=2)
        db_session.add_all([chapter1, chapter2])
        await db_session.flush()

        version = Version(book_id=book.id, version_name="测试版本", era="宋")
        db_session.add(version)
        await db_session.flush()

        repo = PassageRepository(db_session)
        await repo.create(
            chapter_id=chapter1.id,
            version_id=version.id,
            content_text="凡刺之法，必候日月星辰",
        )
        await repo.create(
            chapter_id=chapter2.id,
            version_id=version.id,
            content_text="黄帝问曰：针道可得闻乎",
        )

        items, total = await repo.search_query("黄帝")
        assert total == 1
        assert "黄帝问" in items[0].content_text


class TestPaperRepository:
    @pytest.mark.asyncio
    async def test_create_and_get(self, db_session: AsyncSession):
        repo = PaperRepository(db_session)
        p = await repo.create(title="皇甫谧生平考略", year=2023, doi="10.1234/x")
        fetched = await repo.get_by_id(p.id)
        assert fetched is not None
        assert fetched.title == "皇甫谧生平考略"


class TestImageRepository:
    @pytest.mark.asyncio
    async def test_create(self, db_session: AsyncSession):
        repo = ImageRepository(db_session)
        img = await repo.create(
            related_entity_type="book",
            related_entity_id="b1",
            url="https://example.com/a.jpg",
            caption="Test image",
        )
        assert img.url == "https://example.com/a.jpg"
