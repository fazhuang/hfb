
"""Unit tests for app.schemas.institution — InstitutionCreate, InstitutionUpdate, InstitutionResponse."""

from __future__ import annotations

from app.schemas.institution import (
    InstitutionCreate,
    InstitutionResponse,
    InstitutionUpdate,
)


class TestInstitutionCreate:
    def test_minimal(self) -> None:
        inst = InstitutionCreate(name="北京中医药大学", type="university")
        assert inst.name == "北京中医药大学"
        assert inst.type == "university"
        assert inst.description is None

    def test_with_description(self) -> None:
        inst = InstitutionCreate(name="北大", type="university", description="北京大学")
        assert inst.description == "北京大学"


class TestInstitutionUpdate:
    def test_partial_update(self) -> None:
        inst = InstitutionUpdate(name="新名称")
        assert inst.name == "新名称"
        assert inst.type is None
        assert inst.description is None

    def test_all_fields(self) -> None:
        inst = InstitutionUpdate(name="A", type="university", description="desc")
        assert inst.name == "A"
        assert inst.description == "desc"


class TestInstitutionResponse:
    def test_basic(self) -> None:
        resp = InstitutionResponse(id="00000000-0000-0000-0000-000000000001", name="中科院", type="research")
        assert resp.name == "中科院"
        assert resp.type == "research"

    def test_none_description(self) -> None:
        resp = InstitutionResponse(id="00000000-0000-0000-0000-000000000002", name="Fudan", type="university")
        assert resp.description is None
