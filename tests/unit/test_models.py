"""
Tests for Document and Person models (Sprint 3 scope).
"""

from app.db.base import BaseModel, SoftDeleteMixin, TimestampMixin
from app.models.document import Document
from app.models.person import Person


class TestDocumentModel:
    """Test Document (文献) model."""

    def test_document_tablename(self):
        assert Document.__tablename__ == "documents"

    def test_document_inherits_base_model(self):
        assert issubclass(Document, BaseModel)
        assert issubclass(Document, TimestampMixin)
        assert issubclass(Document, SoftDeleteMixin)

    def test_document_has_expected_columns(self):
        cols = {c.name for c in Document.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "title", "title_pinyin", "title_english",
            "author_id", "dynasty", "year", "category",
            "abstract", "content_text", "source_url",
            "page_count", "language",
        }
        assert expected.issubset(cols)

    def test_document_default_language(self):
        doc = Document(title="Test Document")
        assert doc.language == "zh"


class TestPersonModel:
    """Test Person (人物) model."""

    def test_person_tablename(self):
        assert Person.__tablename__ == "persons"

    def test_person_inherits_base_model(self):
        assert issubclass(Person, BaseModel)

    def test_person_has_expected_columns(self):
        cols = {c.name for c in Person.__table__.columns}
        expected = {
            "id", "created_at", "updated_at", "deleted_at", "is_deleted",
            "name", "name_pinyin", "name_zh",
            "courtesy_name", "pseudonym",
            "dynasty", "birth_year", "death_year", "birth_place",
            "biography", "biography_source",
            "notable_works", "expertise", "external_ref",
        }
        assert expected.issubset(cols)

    def test_person_repr(self):
        p = Person(name="皇甫谧")
        assert "皇甫谧" in repr(p)
