"""
Evidence-bound RAG schemas — every chunk carries full provenance.

Response contract:
  refusal=True → no evidence found, answer explains, citations/evidence empty
  refusal=False → answer is evidence-bound, every claim has a citation
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================
# Request
# ============================================================


class EvidenceRAGRequest(BaseModel):
    """Evidence-bound RAG query."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1, description="Natural-language Chinese question")
    top_k: int = Field(default=5, ge=1, le=50, description="Max chunks to retrieve")


# ============================================================
# Evidence-bound chunk — one per retrieved segment
# ============================================================


class EvidenceBoundChunk(BaseModel):
    """A single retrieved chunk with full evidence provenance."""

    model_config = ConfigDict(extra="forbid", strict=True)

    chunk_id: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    document_title: str = Field(default="")
    source_url: str = Field(default="")
    page_number: int | None = Field(default=None)
    paragraph_index: int | None = Field(default=None)
    chunk_index: int = 0
    content: str = Field(default="")
    score: float = 0.0

    # Copyright & evidence weight
    copyright_status: str = Field(default="unknown")
    citation_format: str | None = Field(default=None)
    evidence_weight: str = Field(default="primary")
    ocr_confidence: float | None = Field(default=None)

    # Built citation string
    citation: str = Field(default="")


# ============================================================
# Citation — the formatted reference
# ============================================================


class EvidenceCitation(BaseModel):
    """A formatted citation with source data."""

    model_config = ConfigDict(extra="forbid", strict=True)

    chunk_id: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    citation: str = Field(..., min_length=1, description="Formatted citation string")
    source_url: str = Field(default="")
    quote: str = Field(default="", description="Excerpt from the evidence chunk")
    copyright_status: str = Field(default="unknown")
    evidence_weight: str = Field(default="primary")
    ocr_confidence: float | None = Field(default=None)


# ============================================================
# Response
# ============================================================


class EvidenceRAGResponse(BaseModel):
    """Evidence-bound RAG response.

    refusal=True → no evidence found.
    refusal=False → answer + citations with provenance.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1)
    answer: str = Field(default="")
    refusal: bool = Field(default=False)
    refusal_reason: str = Field(default="")
    citations: list[EvidenceCitation] = Field(default_factory=list)
    evidence: list[EvidenceBoundChunk] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_evidence_contract(self) -> "EvidenceRAGResponse":
        if not self.refusal:
            errors: list[str] = []
            if not self.answer:
                errors.append("answer must be non-empty when refusal=False")
            if not self.citations:
                errors.append("citations must be non-empty when refusal=False")
            if not self.evidence:
                errors.append("evidence must be non-empty when refusal=False")
            if errors:
                raise ValueError("refusal=False contract violated: " + "; ".join(errors))
        else:
            if self.citations or self.evidence:
                raise ValueError("citations and evidence must be empty when refusal=True")
        return self
