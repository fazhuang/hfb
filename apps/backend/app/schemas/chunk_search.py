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
    """Plain-text ingestion request."""
    model_config = {"extra": "forbid"}

    title: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1)
    dynasty: str | None = None
    category: str | None = None
    max_chunk_chars: int = Field(default=1000, ge=100, le=5000)
