"""
Tests for entity Pydantic schemas — Book, Version, Chapter, Passage, Paper, Image.
"""

import pytest
from app.schemas.entities import (
    BookCreate,
    BookUpdate,
    ChapterCreate,
    ImageCreate,
    PaperCreate,
    PassageCreate,
    VersionCreate,
)
from pydantic import ValidationError


class TestBookSchema:
    def test_create_valid(self):
        b = BookCreate(title="针灸甲乙经", dynasty="西晋")
        assert b.title == "针灸甲乙经"
        assert b.language == "zh"

    def test_update_partial(self):
        u = BookUpdate(title="New Title")
        assert u.title == "New Title"
        assert u.dynasty is None


class TestVersionSchema:
    def test_create_valid(self):
        v = VersionCreate(book_id="a" * 36, version_name="北宋刻本", era="宋")
        assert v.version_name == "北宋刻本"

    def test_create_requires_book_id(self):
        with pytest.raises(ValidationError):
            VersionCreate(book_id="", version_name="Test")


class TestChapterSchema:
    def test_create_valid(self):
        c = ChapterCreate(book_id="a" * 36, title="卷一", order=1)
        assert c.title == "卷一"
        assert c.order == 1


class TestPassageSchema:
    def test_create_valid(self):
        p = PassageCreate(chapter_id="a" * 36, content_text="凡刺之法，必候日月星辰...")
        assert p.content_text.startswith("凡刺")

    def test_create_requires_content(self):
        with pytest.raises(ValidationError):
            PassageCreate(chapter_id="a" * 36, content_text="")


class TestPaperSchema:
    def test_create_valid(self):
        p = PaperCreate(title="皇甫谧研究", year=2024, doi="10.1234/test")
        assert p.title == "皇甫谧研究"


class TestImageSchema:
    def test_create_valid(self):
        i = ImageCreate(
            related_entity_type="book",
            related_entity_id="a" * 36,
            url="https://example.com/img.jpg",
        )
        assert i.related_entity_type == "book"
