"""
Academic RAG schemas — strict response contract for evidence-bound QA.

Response contract:
  query, answer, refusal, citations, kg_paths, evidence_chain,
  corpus_sha256, output_sha256

P0-1: refusal state machine — model_validator enforces:
  - refusal=False → answer/citations/kg_paths/evidence_chain all non-empty
    and at least one path with hop_count >= 2
  - refusal=True → citations/kg_paths/evidence_chain all empty

P0-4: stable ID association — citations, edges, evidence_links carry
  citation_id, evidence_id, relation_id for deterministic cross-referencing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================
# Request
# ============================================================


class AcademicRAGRequest(BaseModel):
    """Academic RAG query — accepts natural Chinese questions."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(
        ..., min_length=1, description="Natural-language Chinese question"
    )


# ============================================================
# Citation — P0-4: stable ID fields
# ============================================================


class AcademicCitation(BaseModel):
    """A single citation with full provenance and stable ID."""

    model_config = ConfigDict(extra="forbid", strict=True)

    citation_id: str = Field(default="")
    document_id: str = Field(..., min_length=1)
    version_id: str = Field(default="")
    chunk_id: str = Field(..., min_length=1)
    passage_id: str = Field(default="")
    exact_quote: str = Field(..., min_length=1)
    citation: str = Field(..., min_length=1)
    source_uri: str = Field(default="")
    evidence_id: str = Field(default="")


# ============================================================
# KG Path — P0-4: stable edge IDs
# ============================================================


class AcademicKGNode(BaseModel):
    """A node in an academic KG path."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    entity_type: str
    label: str


class AcademicKGEdge(BaseModel):
    """An edge in an academic KG path — P0-4: stable ID fields, lossless provenance."""

    model_config = ConfigDict(extra="forbid", strict=True)

    edge_id: str = Field(default="")
    relation_id: str = Field(default="")
    relation_type: str
    label: str
    evidence_quote: str = Field(default="")
    evidence_citation: str = Field(default="")
    evidence_id: str = Field(default="")
    claim_text: str = Field(default="")
    # P0-2: provenance fields carried losslessly from EntityRelation
    version_id: str = Field(default="")
    passage_id: str = Field(default="")
    source_uri: str = Field(default="")


class AcademicKGPath(BaseModel):
    """A continuous multi-hop path through the knowledge graph."""

    model_config = ConfigDict(extra="forbid", strict=True)

    nodes: list[AcademicKGNode] = Field(default_factory=list)
    edges: list[AcademicKGEdge] = Field(default_factory=list)
    hop_count: int = 0


# ============================================================
# Evidence Chain — P0-4: stable cross-reference IDs
# ============================================================


class AcademicEvidenceLink(BaseModel):
    """A claim bound to specific evidence — P0-4: stable IDs."""

    model_config = ConfigDict(extra="forbid", strict=True)

    claim_id: str = Field(default="")
    claim: str = Field(..., min_length=1)
    path_id: str = Field(default="")
    edge_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


# ============================================================
# Response — P0-1: refusal state machine validator
# ============================================================


class AcademicRAGResponse(BaseModel):
    """Strict evidence-bound RAG response.

    P0-1: Refusal state machine enforced by model_validator.
    Refusal path: refusal=True, answer explains why, all lists empty.
    Success path: refusal=False, answer non-empty, citations/kg_paths/evidence_chain non-empty,
                  at least one kg_path with hop_count >= 2.
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

    @model_validator(mode="after")
    def enforce_refusal_state_machine(self) -> "AcademicRAGResponse":
        """P0-1: Hard state machine — no shortcut success detection.

        refusal=False REQUIRES:
          1. answer non-empty
          2. citations non-empty
          3. kg_paths non-empty
          4. evidence_chain non-empty
          5. At least one kg_path with hop_count >= 2

        refusal=True REQUIRES:
          1. citations empty
          2. kg_paths empty
          3. evidence_chain empty
        """
        if not self.refusal:
            # Success path — all must be non-empty
            errors: list[str] = []
            if not self.answer:
                errors.append("answer must be non-empty when refusal=False")
            if not self.citations:
                errors.append("citations must be non-empty when refusal=False")
            if not self.kg_paths:
                errors.append("kg_paths must be non-empty when refusal=False")
            if not self.evidence_chain:
                errors.append("evidence_chain must be non-empty when refusal=False")

            # Must have at least one path with hop_count >= 2
            multi_hop = [p for p in self.kg_paths if p.hop_count >= 2]
            if not multi_hop:
                errors.append(
                    "At least one kg_path must have hop_count >= 2 when refusal=False"
                )

            if errors:
                raise ValueError(
                    "refusal=False contract violated: " + "; ".join(errors)
                )
        else:
            # Refusal path — all lists must be empty
            errors: list[str] = []
            if self.citations:
                errors.append("citations must be empty when refusal=True")
            if self.kg_paths:
                errors.append("kg_paths must be empty when refusal=True")
            if self.evidence_chain:
                errors.append("evidence_chain must be empty when refusal=True")
            if errors:
                raise ValueError("refusal=True contract violated: " + "; ".join(errors))
        return self


# ============================================================
# API Envelope
# ============================================================


class AcademicRAGEnvelope(BaseModel):
    """Standard API envelope for academic RAG."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: AcademicRAGResponse | None = None
    message: str = Field(default="ok")
