"""
Tests for Pydantic schemas — validation edge cases (Sprint 3 scope).
"""

import pytest
from app.schemas.common import PaginationParams
from app.schemas.document import DocumentCreate
from app.schemas.person import PersonBrief, PersonCreate
from pydantic import ValidationError


class TestDocumentSchema:
    """Test Document schemas."""

    def test_create_valid(self):
        d = DocumentCreate(title="针灸甲乙经", dynasty="西晋")
        assert d.title == "针灸甲乙经"
        assert d.language == "zh"

    def test_create_title_too_long(self):
        with pytest.raises(ValidationError):
            DocumentCreate(title="x" * 501)

    def test_create_empty_title(self):
        with pytest.raises(ValidationError):
            DocumentCreate(title="")


class TestPersonSchema:
    """Test Person schemas."""

    def test_create_valid(self):
        p = PersonCreate(name="皇甫谧", dynasty="西晋", birth_year=215)
        assert p.name == "皇甫谧"

    def test_create_name_required(self):
        with pytest.raises(ValidationError):
            PersonCreate(name="")

    def test_brief_from_attributes(self):
        p = PersonBrief.model_validate(
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "测试",
                "name_zh": None,
                "dynasty": "汉",
                "birth_year": None,
                "death_year": None,
            }
        )
        assert p.name == "测试"


class TestPaginationParams:
    """Test pagination schema."""

    def test_defaults(self):
        p = PaginationParams()
        assert p.page == 1
        assert p.limit == 20

    def test_page_min_1(self):
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_limit_max_100(self):
        with pytest.raises(ValidationError):
            PaginationParams(limit=101)
