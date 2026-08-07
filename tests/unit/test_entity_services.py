"""
Tests for entity service validation hooks — Book, Version, Chapter, Passage, Paper, Image.
"""

import pytest
from app.schemas.entities import (
    BookCreate,
    ChapterCreate,
    ImageCreate,
    PaperCreate,
    PassageCreate,
    VersionCreate,
)
from app.services.entities import (
    BookService,
    ChapterService,
    ImageService,
    PaperService,
    PassageService,
    VersionService,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session  # noqa: F401


class TestBookService:
    """BookService: title required, search delegation."""

    @pytest.mark.asyncio
    async def test_create_empty_title_raises(self, db_session: AsyncSession):
        svc = BookService(db_session)
        with pytest.raises(ValueError, match="Book title"):
            await svc._validate_create({"title": ""})
        with pytest.raises(ValueError, match="Book title"):
            await svc._validate_create({"title": "   "})

    @pytest.mark.asyncio
    async def test_create_valid(self, db_session: AsyncSession):
        svc = BookService(db_session)
        book = await svc.create(BookCreate(title="Test Book"))
        assert book.title == "Test Book"

    @pytest.mark.asyncio
    async def test_search_delegates(self, db_session: AsyncSession):
        svc = BookService(db_session)
        await svc.create(BookCreate(title="针灸甲乙经"))
        results, total = await svc.search("针灸")
        assert total >= 1


class TestVersionService:
    """VersionService: version_name + book_id required, search."""

    @pytest.mark.asyncio
    async def test_create_empty_version_name_raises(self, db_session: AsyncSession):
        svc = VersionService(db_session)
        with pytest.raises(ValueError, match="Version name"):
            await svc._validate_create({"version_name": "", "book_id": "x"})
        with pytest.raises(ValueError, match="Version name"):
            await svc._validate_create({"version_name": "   ", "book_id": "x"})

    @pytest.mark.asyncio
    async def test_create_empty_book_id_raises(self, db_session: AsyncSession):
        svc = VersionService(db_session)
        with pytest.raises(ValueError, match="book_id"):
            await svc._validate_create({"version_name": "v1", "book_id": ""})

    @pytest.mark.asyncio
    async def test_create_valid(self, db_session: AsyncSession):
        svc = VersionService(db_session)
        version = await svc.create(
            VersionCreate(book_id="test-book-1", version_name="宋刻本")
        )
        assert version.version_name == "宋刻本"

    @pytest.mark.asyncio
    async def test_search_delegates(self, db_session: AsyncSession):
        svc = VersionService(db_session)
        await svc.create(VersionCreate(book_id="test-book-1", version_name="宋刻本"))
        results, total = await svc.search("宋刻")
        assert total >= 1


class TestChapterService:
    """ChapterService: title + book_id required, search."""

    @pytest.mark.asyncio
    async def test_create_empty_title_raises(self, db_session: AsyncSession):
        svc = ChapterService(db_session)
        with pytest.raises(ValueError, match="Chapter title"):
            await svc._validate_create({"title": "", "book_id": "x"})
        with pytest.raises(ValueError, match="Chapter title"):
            await svc._validate_create({"title": "   ", "book_id": "x"})

    @pytest.mark.asyncio
    async def test_create_empty_book_id_raises(self, db_session: AsyncSession):
        svc = ChapterService(db_session)
        with pytest.raises(ValueError, match="book_id"):
            await svc._validate_create({"title": "Ch1", "book_id": ""})

    @pytest.mark.asyncio
    async def test_create_valid(self, db_session: AsyncSession):
        svc = ChapterService(db_session)
        chapter = await svc.create(
            ChapterCreate(book_id="test-book-1", title="卷一")
        )
        assert chapter.title == "卷一"

    @pytest.mark.asyncio
    async def test_search_delegates(self, db_session: AsyncSession):
        svc = ChapterService(db_session)
        await svc.create(ChapterCreate(book_id="test-book-1", title="卷一"))
        results, total = await svc.search("卷一")
        assert total >= 1


class TestPassageService:
    """PassageService: content_text + chapter_id required, search."""

    @pytest.mark.asyncio
    async def test_create_empty_content_text_raises(self, db_session: AsyncSession):
        svc = PassageService(db_session)
        with pytest.raises(ValueError, match="Passage content_text"):
            await svc._validate_create({"content_text": "", "chapter_id": "x"})
        with pytest.raises(ValueError, match="Passage content_text"):
            await svc._validate_create({"content_text": "   ", "chapter_id": "x"})

    @pytest.mark.asyncio
    async def test_create_empty_chapter_id_raises(self, db_session: AsyncSession):
        svc = PassageService(db_session)
        with pytest.raises(ValueError, match="chapter_id"):
            await svc._validate_create({"content_text": "text", "chapter_id": ""})

    @pytest.mark.asyncio
    async def test_create_valid(self, db_session: AsyncSession):
        svc = PassageService(db_session)
        passage = await svc.create(
            PassageCreate(chapter_id="test-chapter-1", content_text="凡刺之要")
        )
        assert passage.content_text == "凡刺之要"

    @pytest.mark.asyncio
    async def test_search_delegates(self, db_session: AsyncSession):
        svc = PassageService(db_session)
        await svc.create(
            PassageCreate(chapter_id="test-chapter-1", content_text="凡刺之要")
        )
        results, total = await svc.search("凡刺")
        assert total >= 1


class TestPaperService:
    """PaperService: title required, search."""

    @pytest.mark.asyncio
    async def test_create_empty_title_raises(self, db_session: AsyncSession):
        svc = PaperService(db_session)
        with pytest.raises(ValueError, match="Paper title"):
            await svc._validate_create({"title": ""})
        with pytest.raises(ValueError, match="Paper title"):
            await svc._validate_create({"title": "   "})

    @pytest.mark.asyncio
    async def test_create_valid(self, db_session: AsyncSession):
        svc = PaperService(db_session)
        paper = await svc.create(PaperCreate(title="针灸研究"))
        assert paper.title == "针灸研究"

    @pytest.mark.asyncio
    async def test_search_delegates(self, db_session: AsyncSession):
        svc = PaperService(db_session)
        await svc.create(PaperCreate(title="针灸研究"))
        results, total = await svc.search("针灸")
        assert total >= 1


class TestImageService:
    """ImageService: url + related_entity_type + related_entity_id required."""

    @pytest.mark.asyncio
    async def test_create_empty_url_raises(self, db_session: AsyncSession):
        svc = ImageService(db_session)
        with pytest.raises(ValueError, match="Image URL"):
            await svc._validate_create(
                {"url": "", "related_entity_type": "book", "related_entity_id": "x"}
            )
        with pytest.raises(ValueError, match="Image URL"):
            await svc._validate_create(
                {"url": "   ", "related_entity_type": "book", "related_entity_id": "x"}
            )

    @pytest.mark.asyncio
    async def test_create_empty_entity_type_raises(self, db_session: AsyncSession):
        svc = ImageService(db_session)
        with pytest.raises(ValueError, match="related_entity_type"):
            await svc._validate_create(
                {"url": "http://x", "related_entity_type": "", "related_entity_id": "x"}
            )

    @pytest.mark.asyncio
    async def test_create_empty_entity_id_raises(self, db_session: AsyncSession):
        svc = ImageService(db_session)
        with pytest.raises(ValueError, match="related_entity_id"):
            await svc._validate_create(
                {"url": "http://x", "related_entity_type": "book", "related_entity_id": ""}
            )

    @pytest.mark.asyncio
    async def test_create_valid(self, db_session: AsyncSession):
        svc = ImageService(db_session)
        image = await svc.create(
            ImageCreate(
                url="http://example.com/img.jpg",
                related_entity_type="book",
                related_entity_id="test-book-1",
            )
        )
        assert image.url == "http://example.com/img.jpg"

    # ImageService has no search() — omitted by design
