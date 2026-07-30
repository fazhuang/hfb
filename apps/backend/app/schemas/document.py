"""
Document (文献) schemas.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

COPYRIGHT_STATUSES = frozenset({
    "public_domain",
    "open_access",
    "licensed",
    "user_uploaded_with_permission",
    "unknown",
    "metadata_only",
    "forbidden_fulltext",
    "commercial_restricted",
    "pirated",
})

REVIEW_STATUSES = frozenset({
    "pending_review",
    "under_review",
    "approved",
    "rejected",
})


class DocumentBase(BaseModel):
    """Fields shared across document schemas."""

    title: str = Field(..., min_length=1, max_length=500)
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
    session_id: str | None = Field(default=None, max_length=36)


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""



class DocumentUpdate(BaseModel):
    """Schema for updating a document — all fields optional."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
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
    language: str | None = Field(default=None, max_length=20)
    session_id: str | None = Field(default=None, max_length=36)
    copyright_status: str | None = Field(default=None, max_length=50)
    license_type: str | None = Field(default=None, max_length=100)
    authorization_basis: str | None = Field(default=None, max_length=200)
    rag_enabled: bool | None = Field(default=None)


class DocumentBrief(BaseModel):
    """Minimal document info for list views — includes compliance fields."""

    id: UUID
    title: str
    dynasty: str | None
    category: str | None
    author_id: str | None
    copyright_status: str
    review_status: str
    rag_enabled: bool
    source_name: str | None
    session_id: str | None = None
    uploaded_by: str | None = None
    withdrawn_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentResponse(DocumentBase):
    """Full document representation returned by the API."""

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    copyright_status: str
    license_type: str | None
    authorization_basis: str | None
    review_status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    rag_enabled: bool
    content_checksum: str | None
    source_name: str | None
    session_id: str | None = None
    uploaded_by: str | None = None
    withdrawn_at: datetime | None
    withdraw_reason: str | None

    model_config = {"from_attributes": True}


class DocumentReviewRequest(BaseModel):
    """Request body for reviewing a document."""

    review_status: str = Field(..., max_length=50)
    rag_enabled: bool | None = Field(default=None)


class DocumentWithdrawRequest(BaseModel):
    """Request body for withdrawing a document."""

    reason: str = Field(default="", max_length=1000)
