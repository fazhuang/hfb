"""
Academic RAG schemas — strict response contract for evidence-bound QA.

Response contract:
  query, answer, refusal, citations, kg_paths, evidence_chain,
  corpus_sha256, output_sha256
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Request
# ============================================================


class AcademicRAGRequest(BaseModel):
    """Academic RAG query — accepts natural Chinese questions."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1, description="Natural-language Chinese question")


# ============================================================
# Citation
# ============================================================


class AcademicCitation(BaseModel):
    """A single citation with full provenance."""

    model_config = ConfigDict(extra="forbid", strict=True)

    document_id: str = Field(..., min_length=1)
    version_id: str = Field(default="")
    chunk_id: str = Field(..., min_length=1)
    passage_id: str = Field(default="")
    exact_quote: str = Field(..., min_length=1)
    citation: str = Field(..., min_length=1)
    source_uri: str = Field(default="")


# ============================================================
# KG Path
# ============================================================


class AcademicKGNode(BaseModel):
    """A node in an academic KG path."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    entity_type: str
    label: str


class AcademicKGEdge(BaseModel):
    """An edge in an academic KG path."""

    model_config = ConfigDict(extra="forbid", strict=True)

    relation_type: str
    label: str
    evidence_quote: str = Field(default="")
    evidence_citation: str = Field(default="")


class AcademicKGPath(BaseModel):
    """A continuous multi-hop path through the knowledge graph."""

    model_config = ConfigDict(extra="forbid", strict=True)

    nodes: list[AcademicKGNode] = Field(default_factory=list)
    edges: list[AcademicKGEdge] = Field(default_factory=list)
    hop_count: int = 0


# ============================================================
# Evidence Chain
# ============================================================


class AcademicEvidenceLink(BaseModel):
    """A claim bound to specific evidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    claim: str = Field(..., min_length=1)
    path_id: str = Field(default="")
    evidence_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


# ============================================================
# Response
# ============================================================


class AcademicRAGResponse(BaseModel):
    """Strict evidence-bound RAG response.

    Refusal path: refusal=True, answer explains why, all lists empty.
    Success path: refusal=False, answer non-empty, citations/kg_paths/evidence_chain non-empty.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1)
    answer: str = Field(default="")
    refusal: bool = Field(default=False)
    citations: list[AcademicCitation] = Field(default_factory=list)
    kg_paths: list[AcademicKGPath] = Field(default_factory=list)
    evidence_chain: list[AcademicEvidenceLink] = Field(default_factory=list)
    corpus_sha256: str = Field(default="")
    output_sha256: str = Field(default="")


# ============================================================
# API Envelope
# ============================================================


class AcademicRAGEnvelope(BaseModel):
    """Standard API envelope for academic RAG."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: AcademicRAGResponse | None = None
    message: str = Field(default="ok")
