"""
Chunk search schemas — request/response models for the Search API.

Response contract (frozen):
  POST /api/v1/search → { query, results, metadata }
  metadata: { top_k, model: "retrieval-only" }
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request for document chunk retrieval."""
    model_config = {"extra": "forbid"}

    query: str = Field(..., min_length=1, description="Search query text, whitespace-separated keywords")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    document_id: str | None = Field(default=None, description="Optional filter to a specific document")
    year: int | None = Field(default=None, description="Optional filter: document year")
    author_id: str | None = Field(default=None, description="Optional filter: document author (entity)")


class SearchResult(BaseModel):
    """A single search result with citation. Frozen — no extra fields allowed."""
    model_config = {"extra": "forbid"}

    chunk_id: str
    document_id: str
    content: str
    score: float
    citation: str  # format: [document_id:chunk_id]


class Metadata(BaseModel):
    """Search response metadata. Frozen — no runtime leaks, no timestamps."""
    model_config = {"extra": "forbid"}

    top_k: int
    model: Literal["retrieval-only"]


class SearchResponse(BaseModel):
    """Response contract for POST /api/v1/search. Frozen — no extra fields."""
    model_config = {"extra": "forbid"}

    query: str
    results: list[SearchResult]
    metadata: Metadata


# Legacy schemas — retained for compatibility with /chunks, /ingest endpoints

class ChunkResult(BaseModel):
    """A single chunk result with citation (compat)."""
    model_config = {"extra": "forbid"}

    document_id: str
    chunk_id: str
    content: str
    score: float
    citation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestTextRequest(BaseModel):
    """Plain-text ingestion request with compliance fields (Context 21)."""
    model_config = {"extra": "forbid"}

    title: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1)
    dynasty: str | None = None
    category: str | None = None
    max_chunk_chars: int = Field(default=1000, ge=100, le=5000)
    passage_id: str | None = Field(default=None, description="Optional Passage ID for V4 lineage")

    # Context 21: full-text compliance fields
    copyright_status: str = Field(
        default="unknown",
        description="版权状态: public_domain|open_access|licensed|user_uploaded_with_permission|unknown|metadata_only|forbidden_fulltext|commercial_restricted|pirated",
    )
    license_type: str | None = Field(default=None, description="许可类型: CC-BY|CC-BY-NC|CC-BY-SA|CC0|custom")
    authorization_basis: str | None = Field(default=None, description="授权依据 URL / 协议引用 / 依据声明")
    source_url: str | None = Field(default=None, description="来源 URL")
    source_name: str | None = Field(default=None, description="摄入来源名称")
    metadata_only: bool = Field(default=False, description="仅元数据，不保存全文")
    forbidden_fulltext: bool = Field(default=False, description="明确禁止全文入库")


# ---- Append-passage schemas ----

class AppendPassageRequest(BaseModel):
    """Append a new passage's text chunks to an existing document."""
    model_config = {"extra": "forbid"}

    text: str = Field(..., min_length=1, description="Text content for the new passage")
    passage_id: str = Field(..., min_length=1, description="Passage UUID this text belongs to")
    max_chunk_chars: int = Field(default=1000, ge=100, le=5000)


class AppendPassageResponse(BaseModel):
    """Result of appending passage chunks to an existing document."""
    model_config = {"extra": "forbid"}

    document_id: str
    passage_id: str
    appended_chunk_count: int
    appended_chunk_ids: list[str]
    first_chunk_index: int
    last_chunk_index: int
    content_checksum: str
