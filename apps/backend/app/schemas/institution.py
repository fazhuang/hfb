"""
Institution Pydantic schemas — Create, Update, Response.

Type field validated against InstitutionType enum.
Name field requires non-empty, non-whitespace content.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.institution import InstitutionType, InstitutionStatus

_VALID_TYPES = frozenset(t.value for t in InstitutionType)


class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    type: str = Field(..., min_length=1, max_length=50)
    location: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None)

    @field_validator("name", mode="after")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Institution name must not be empty or whitespace-only")
        return stripped

    @field_validator("type", mode="after")
    @classmethod
    def type_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_TYPES:
            raise ValueError(
                f"Invalid institution type '{v}'. Must be one of: {sorted(_VALID_TYPES)}"
            )
        return v


class InstitutionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    type: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None)

    @field_validator("name", mode="after")
    @classmethod
    def name_must_not_be_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Institution name must not be empty or whitespace-only")
        return stripped

    @field_validator("type", mode="after")
    @classmethod
    def type_must_be_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in _VALID_TYPES:
            raise ValueError(
                f"Invalid institution type '{v}'. Must be one of: {sorted(_VALID_TYPES)}"
            )
        return v


class InstitutionResponse(BaseModel):
    id: UUID
    name: str
    type: str
    location: str | None = None
    description: str | None = None
    status: str = InstitutionStatus.draft.value
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class InstitutionBrief(BaseModel):
    id: UUID
    name: str
    type: str
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
