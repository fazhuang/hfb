"""
Document (文献) schemas.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Fields shared across document schemas."""

    title: str = Field(..., min_length=1, max_length=500, description="文献标题")
    title_pinyin: str | None = Field(default=None, max_length=500)
    title_english: str | None = Field(default=None, max_length=500)
    author_id: str | None = Field(default=None, max_length=36)
    dynasty: str | None = Field(default=None, max_length=100)
    year: int | None = Field(default=None)
    category: str | None = Field(default=None, max_length=200)
    abstract: str | None = Field(default=None)
    content_text: str | None = Field(default=None)
    source_url: str | None = Field(default=None, max_length=2000)
    page_count: int | None = Field(default=None)
    language: str = Field(default="zh", max_length=20)


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""

    pass


class DocumentBrief(BaseModel):
    """Minimal document info for list views."""

    id: UUID
    title: str
    dynasty: str | None
    category: str | None
    author_id: str | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentResponse(DocumentBase):
    """Full document representation returned by the API."""

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
