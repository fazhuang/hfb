"""
Person (人物) schemas.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PersonBase(BaseModel):
    """Fields shared across person schemas."""

    name: str = Field(..., min_length=1, max_length=200)
    name_pinyin: str | None = Field(default=None, max_length=200)
    name_zh: str | None = Field(default=None, max_length=200)
    courtesy_name: str | None = Field(default=None, max_length=200)
    pseudonym: str | None = Field(default=None, max_length=200)
    dynasty: str | None = Field(default=None, max_length=100)
    birth_year: int | None = Field(default=None)
    death_year: int | None = Field(default=None)
    birth_place: str | None = Field(default=None, max_length=300)
    biography: str | None = Field(default=None)
    biography_source: str | None = Field(default=None, max_length=500)
    notable_works: str | None = Field(default=None)
    expertise: str | None = Field(default=None, max_length=500)
    external_ref: str | None = Field(default=None, max_length=500)


class PersonCreate(PersonBase):
    """Schema for creating a new person."""



class PersonBrief(BaseModel):
    """Minimal person info for list views."""

    id: UUID
    name: str
    name_zh: str | None
    dynasty: str | None
    birth_year: int | None
    death_year: int | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PersonResponse(PersonBase):
    """Full person representation returned by the API."""

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
