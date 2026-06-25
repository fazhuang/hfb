"""
Schemas for Book, Version, Chapter, Passage, Paper, Image entities.

Per HFB-DOM-0802 ~ 0805, HFB-DEV-0504 API Design Standard.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================
# Book
# ============================================================


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    title_pinyin: str | None = Field(default=None, max_length=500)
    title_english: str | None = Field(default=None, max_length=500)
    author_id: str | None = Field(default=None, max_length=36)
    dynasty: str | None = Field(default=None, max_length=100)
    year: int | None = Field(default=None)
    category: str | None = Field(default=None, max_length=200)
    abstract: str | None = Field(default=None)
    language: str = Field(default="zh", max_length=20)
    source_url: str | None = Field(default=None, max_length=2000)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    title_pinyin: str | None = None
    title_english: str | None = None
    author_id: str | None = None
    dynasty: str | None = None
    year: int | None = None
    category: str | None = None
    abstract: str | None = None
    language: str | None = None
    source_url: str | None = None


class BookBrief(BaseModel):
    id: UUID
    title: str
    dynasty: str | None
    category: str | None
    author_id: str | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class BookResponse(BookBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================
# Version
# ============================================================


class VersionBase(BaseModel):
    book_id: str = Field(..., min_length=1, max_length=36)
    version_name: str = Field(..., min_length=1, max_length=300)
    era: str | None = Field(default=None, max_length=100)
    year: int | None = Field(default=None)
    repository: str | None = Field(default=None, max_length=500)
    shelf_mark: str | None = Field(default=None, max_length=200)
    editor: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None)
    source_url: str | None = Field(default=None, max_length=2000)


class VersionCreate(VersionBase):
    pass


class VersionUpdate(BaseModel):
    book_id: str | None = None
    version_name: str | None = None
    era: str | None = None
    year: int | None = None
    repository: str | None = None
    shelf_mark: str | None = None
    editor: str | None = None
    description: str | None = None
    source_url: str | None = None


class VersionBrief(BaseModel):
    id: UUID
    book_id: str
    version_name: str
    era: str | None
    repository: str | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class VersionResponse(VersionBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================
# Chapter
# ============================================================


class ChapterBase(BaseModel):
    book_id: str = Field(..., min_length=1, max_length=36)
    parent_id: str | None = Field(default=None, max_length=36)
    title: str = Field(..., min_length=1, max_length=500)
    order: int = 0
    description: str | None = Field(default=None, max_length=2000)


class ChapterCreate(ChapterBase):
    pass


class ChapterUpdate(BaseModel):
    parent_id: str | None = None
    title: str | None = None
    order: int | None = None
    description: str | None = None


class ChapterBrief(BaseModel):
    id: UUID
    book_id: str
    parent_id: str | None
    title: str
    order: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ChapterResponse(ChapterBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================
# Passage
# ============================================================


class PassageBase(BaseModel):
    chapter_id: str = Field(..., min_length=1, max_length=36)
    version_id: str | None = Field(default=None, max_length=36)
    content_text: str = Field(..., min_length=1)
    translation: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    order: int = 0
    tags: str | None = Field(default=None, max_length=1000)


class PassageCreate(PassageBase):
    pass


class PassageUpdate(BaseModel):
    content_text: str | None = None
    translation: str | None = None
    notes: str | None = None
    order: int | None = None
    tags: str | None = None


class PassageBrief(BaseModel):
    id: UUID
    chapter_id: str
    version_id: str | None
    content_text: str
    order: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PassageResponse(PassageBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================
# Paper
# ============================================================


class PaperBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=1000)
    title_english: str | None = Field(default=None, max_length=1000)
    authors: str | None = Field(default=None)
    journal: str | None = Field(default=None, max_length=500)
    year: int | None = Field(default=None)
    doi: str | None = Field(default=None, max_length=500)
    volume: str | None = Field(default=None, max_length=50)
    issue: str | None = Field(default=None, max_length=50)
    pages: str | None = Field(default=None, max_length=50)
    abstract: str | None = Field(default=None)
    keywords: str | None = Field(default=None)
    language: str = Field(default="zh", max_length=20)
    paper_type: str | None = Field(default=None, max_length=50)
    source_url: str | None = Field(default=None, max_length=2000)
    full_text: str | None = Field(default=None)


class PaperCreate(PaperBase):
    pass


class PaperUpdate(BaseModel):
    title: str | None = None
    title_english: str | None = None
    authors: str | None = None
    journal: str | None = None
    year: int | None = None
    doi: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    abstract: str | None = None
    keywords: str | None = None
    language: str | None = None
    paper_type: str | None = None
    source_url: str | None = None
    full_text: str | None = None


class PaperBrief(BaseModel):
    id: UUID
    title: str
    authors: str | None
    journal: str | None
    year: int | None
    doi: str | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PaperResponse(PaperBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================
# Image
# ============================================================


class ImageBase(BaseModel):
    related_entity_type: str = Field(..., min_length=1, max_length=50)
    related_entity_id: str = Field(..., min_length=1, max_length=36)
    url: str = Field(..., min_length=1, max_length=2000)
    caption: str | None = Field(default=None)
    source: str | None = Field(default=None, max_length=500)
    license_info: str | None = Field(default=None, max_length=500)
    order: int | None = Field(default=None)


class ImageCreate(ImageBase):
    pass


class ImageBrief(BaseModel):
    id: UUID
    related_entity_type: str
    related_entity_id: str
    url: str
    caption: str | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ImageResponse(ImageBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
