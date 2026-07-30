"""
Tests for Phase 3 entity models — Book, Version, Chapter, Passage, Paper, Image.
"""

from app.db.base import BaseModel
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.image import Image
from app.models.paper import Paper
from app.models.passage import Passage
from app.models.version import Version


class TestBookModel:
    def test_tablename(self):
        assert Book.__tablename__ == "books"

    def test_inherits_base_model(self):
        assert issubclass(Book, BaseModel)

    def test_has_expected_columns(self):
        cols = {c.name for c in Book.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "title", "title_pinyin", "title_english",
            "author_id", "dynasty", "year", "category",
            "abstract", "language", "source_url",
        }
        assert expected.issubset(cols)


class TestVersionModel:
    def test_tablename(self):
        assert Version.__tablename__ == "versions"

    def test_has_expected_columns(self):
        cols = {c.name for c in Version.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "book_id", "version_name", "era", "year",
            "repository", "shelf_mark", "editor", "description", "source_url",
        }
        assert expected.issubset(cols)


class TestChapterModel:
    def test_tablename(self):
        assert Chapter.__tablename__ == "chapters"

    def test_has_expected_columns(self):
        cols = {c.name for c in Chapter.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "book_id", "parent_id", "title", "order", "description",
        }
        assert expected.issubset(cols)


class TestPassageModel:
    def test_tablename(self):
        assert Passage.__tablename__ == "passages"

    def test_has_expected_columns(self):
        cols = {c.name for c in Passage.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "chapter_id", "version_id", "content_text",
            "translation", "notes", "order", "tags",
        }
        assert expected.issubset(cols)


class TestPaperModel:
    def test_tablename(self):
        assert Paper.__tablename__ == "papers"

    def test_has_expected_columns(self):
        cols = {c.name for c in Paper.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "title", "title_english", "authors", "journal", "year",
            "doi", "volume", "issue", "pages", "abstract", "keywords",
            "language", "paper_type", "source_url", "full_text",
        }
        assert expected.issubset(cols)


class TestImageModel:
    def test_tablename(self):
        assert Image.__tablename__ == "images"

    def test_has_expected_columns(self):
        cols = {c.name for c in Image.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "related_entity_type", "related_entity_id",
            "url", "caption", "source", "license_info", "order",
        }
        assert expected.issubset(cols)
