"""Grounded generation response schemas — Day 4.

Extends the existing AI response envelope with a dedicated generation
response that includes citation validation metadata.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.ai_response import Citation


class GenerationMetadata(BaseModel):
    """Metadata for the citation-grounded generation."""

    top_k: int = 0
    model: str = "citation-grounded-llm"
    citation_validation: dict[str, Any] = Field(default_factory=dict)


class GroundedGenerationResponse(BaseModel):
    """Response envelope for the citation-grounded generation endpoint.

    Schema per Day 4 spec:
    { query, answer, results[], citations[], metadata }
    """

    query: str
    answer: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    metadata: GenerationMetadata = Field(default_factory=GenerationMetadata)
