"""Grounded generation response schemas — Day 4 P0.

Response envelope: { query, answer, results[], citations[], metadata }
All citations use [document_id:chunk_id] format, traceable to DocumentChunk records.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerationMetadata(BaseModel):
    """Metadata for the citation-grounded generation."""

    top_k: int = 0
    model: str = "citation-grounded-llm"
    citation_validation: dict[str, Any] = Field(default_factory=dict)


class GroundedGenerationResponse(BaseModel):
    """Response envelope for the citation-grounded generation endpoint.

    Schema per Day 4 spec:
    { query, answer, results[], citations[], metadata {
        top_k, model, citation_validation
    }}
    """

    query: str
    answer: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    metadata: GenerationMetadata = Field(default_factory=GenerationMetadata)
