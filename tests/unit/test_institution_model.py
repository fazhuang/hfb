
"""Unit tests for Institution model — enums, validators, checks."""

from __future__ import annotations

import pytest
from app.models.institution import (
    Institution,
    InstitutionType,
    InstitutionStatus,
)
from app.core.exceptions import ValidationException


class TestInstitutionType:
    def test_values(self) -> None:
        assert InstitutionType.research.value == "research"
        assert InstitutionType.university.value == "university"
        assert InstitutionType.archive.value == "archive"
        assert InstitutionType.institution.value == "institution"


class TestInstitutionStatus:
    def test_values(self) -> None:
        assert InstitutionStatus.draft.value == "draft"
        assert InstitutionStatus.active.value == "active"
        assert InstitutionStatus.archived.value == "archived"
        assert InstitutionStatus.deleted.value == "deleted"


class TestInstitutionModel:
    def test_create_basic(self) -> None:
        inst = Institution(name="复旦大学", type="university")
        assert inst.name == "复旦大学"
        assert inst.type == "university"
        # status has server_default="draft", not a Python default —
        # Pydantic/SQLAlchemy hybrid sets it only on DB flush

    def test_name_validator_strips(self) -> None:
        inst = Institution(name="  北京大学  ", type="university")
        assert inst.name == "北京大学"

    def test_name_validator_rejects_blank(self) -> None:
        with pytest.raises(ValidationException):
            Institution(name="   ", type="university")

    def test_name_validator_rejects_none(self) -> None:
        with pytest.raises(ValidationException):
            Institution(name=None, type="university")  # type: ignore[arg-type]

    def test_type_validator_rejects_invalid(self) -> None:
        with pytest.raises(ValidationException):
            Institution(name="test", type="invalid_type")

    def test_status_validator_rejects_unknown(self) -> None:
        with pytest.raises(ValidationException):
            Institution(name="test", type="university", status="unknown_status")

    def test_repr(self) -> None:
        inst = Institution(name="中科院", type="research")
        r = repr(inst)
        assert "Institution" in r
        assert "中科院" in r

    def test_location_default(self) -> None:
        inst = Institution(name="test", type="archive")
        assert inst.location is None

    def test_description_default(self) -> None:
        inst = Institution(name="test", type="institution")
        assert inst.description is None
