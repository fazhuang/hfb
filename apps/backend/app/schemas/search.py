"""
Unified Search schemas — request, response, and result models.

Per HFB-PS-1706 Unified Search Product Specification.

Search entity types: book, version, passage, person, paper, image, document
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    """Search query parameters."""
    q: str = Field(default="", description="Search query string")
    entity_types: list[str] = Field(
        default_factory=lambda: ["book", "version", "passage", "person", "paper"],
        description="Entity types to search across",
    )
    dynasty: str | None = Field(default=None, description="Filter by dynasty")
    category: str | None = Field(default=None, description="Filter by category (books)")
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class SearchResultItem(BaseModel):
    """A single search result."""
    id: str
    entity_type: str
    title: str  # display title/name
    subtitle: str | None = None  # secondary info line
    snippet: str | None = None  # matching text excerpt
    url: str | None = None  # frontend link path
    metadata: dict[str, Any] = Field(default_factory=dict)  # type-specific fields (dynasty, etc.)
    score: float = 0.0  # relevance score (0-1)


class SuggestParams(BaseModel):
    """Autocomplete / suggestion query."""
    q: str = Field(..., min_length=1, description="Partial query")
    limit: int = Field(default=5, ge=1, le=20)


class SuggestItem(BaseModel):
    """An autocomplete suggestion."""
    text: str  # the completed text
    entity_type: str
    entity_id: str | None = None


class SearchResponse(BaseModel):
    """Unified search response."""
    items: list[SearchResultItem]
    total: int
    page: int
    limit: int
    total_pages: int
    query: str
    entity_types: list[str]
    facets: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)  # facet counts


class ReindexResponse(BaseModel):
    """Reindex job status."""
    status: str  # "started" | "completed" | "failed"
    entities_indexed: int = 0
    errors: list[str] = Field(default_factory=list)
