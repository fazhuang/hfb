"""
Chunk search schemas — request/response models for the Day 2 search API.

Response contract:
  POST /api/v1/search → { chunks: [...], citations: [...], metadata: {...} }
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request for document chunk retrieval."""
    query: str = Field(..., min_length=1, description="Search query text, whitespace-separated keywords")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")
    document_id: str | None = Field(default=None, description="Optional filter to a specific document")
    year: int | None = Field(default=None, description="Optional filter: document year")
    author_id: str | None = Field(default=None, description="Optional filter: document author (entity)")


class ChunkResult(BaseModel):
    """A single chunk result with citation."""
    document_id: str
    chunk_id: str
    content: str
    score: float
    citation: str  # format: [document_id:chunk_id]
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response contract for POST /api/v1/search.

    chunks:    ranked list of matching document chunks.
    citations: one citation string per chunk, in same order.
    metadata:  query, total, top_k.
    """
    chunks: list[ChunkResult]
    citations: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestTextRequest(BaseModel):
    """Plain-text ingestion request."""
    title: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1)
    dynasty: str | None = None
    category: str | None = None
    max_chunk_chars: int = Field(default=1000, ge=100, le=5000)
