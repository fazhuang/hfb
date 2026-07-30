"""
Academic V2 schemas — Sprint 2 academic product layer (P0 remediated).

Four modules: report, synthesis, research, education.
All share citation grounding from Sprint 1 GenerationPipeline.

P0-1: EvidenceTrace now maps 1:1 to output claims, not retrieval results.
P1: extra="forbid" on all request/response models.
P0-6: UnsupportedClaimGate classification.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Evidence trace — every output claim traceable to source chunk (P0-1)
# ---------------------------------------------------------------------------


class EvidenceTrace(BaseModel):
    """One output claim traced back to its exact source quote in a chunk.

    P0-1: claim_text and quote are the EXACT text rendered to the user.
    quote must be a normalized substring of the cited chunk's content.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    claim_text: str = Field(
        ..., min_length=1, description="Exact claim text rendered in output"
    )
    quote: str = Field(
        ..., min_length=1, description="Exact normalized substring from chunk content"
    )
    document_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)
    citation_text: str = Field(
        default="", description="Formatted citation [document_id:chunk_id]"
    )


class CitationRef(BaseModel):
    """A citation reference."""

    model_config = ConfigDict(extra="forbid", strict=True)

    document_id: str
    chunk_id: str
    text: str


# ---------------------------------------------------------------------------
# Reproducibility metadata (P0-2)
# ---------------------------------------------------------------------------


class ReproducibilityMetadata(BaseModel):
    """Deterministic metadata enabling byte-identical reproduction.

    P0-2: No timestamps, no runtime-dependent values.
    Identical corpus + request → identical payload.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    output_sha256: str = Field(
        default="", description="SHA-256 of deterministic output payload"
    )
    corpus_sha256: str = Field(
        default="", description="SHA-256 of ordered retrieval snapshot content"
    )
    ordered_cited_chunk_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    pipeline_version: str = "academic-grounded-v2-p0"


# ---------------------------------------------------------------------------
# Module-specific content shapes
# ---------------------------------------------------------------------------


class ReportSection(BaseModel):
    """One section of an academic report. Every non-structural sentence has a citation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    heading: str  # structural label, no citation needed
    body: str  # rendered claims text, every factual sentence cites its source
    citations: list[CitationRef] = Field(default_factory=list)
    evidence: list[EvidenceTrace] = Field(default_factory=list)


class SynthesisTheme(BaseModel):
    """One thematic cluster of source-bound claims."""

    model_config = ConfigDict(extra="forbid", strict=True)

    title: str  # deterministic label
    description: str = ""  # structural label only, no factual assertions
    claims: list[EvidenceTrace] = Field(default_factory=list)
    cross_document_refs: list[str] = Field(
        default_factory=list,
        description="Document IDs contributing to this theme (only when ≥2)",
    )


class ResearchSubQuestion(BaseModel):
    """One decomposed research sub-question with evidence or gap."""

    model_config = ConfigDict(extra="forbid", strict=True)

    sub_question: str
    evidence: list[EvidenceTrace] = Field(default_factory=list)
    has_gap: bool = False
    hypothesis: str | None = Field(
        default=None, description="Null unless supported by evidence"
    )


class EducationConcept(BaseModel):
    """One concept explanation at a difficulty level."""

    model_config = ConfigDict(extra="forbid", strict=True)

    concept: str
    level: Literal["beginner", "intermediate"]
    paragraphs: list[str] = Field(default_factory=list)
    citations: list[CitationRef] = Field(default_factory=list)
    evidence: list[EvidenceTrace] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Unsupported-claim gate result (P0-6)
# ---------------------------------------------------------------------------


class UnsupportedClaimVerdict(BaseModel):
    """Deterministic unsupported-claim gate result."""

    model_config = ConfigDict(extra="forbid", strict=True)

    is_supported: bool = Field(
        description="Whether the proposition is supported by evidence"
    )
    proposition_type: str = Field(default="", description="Classified proposition type")
    matched_keywords: list[str] = Field(default_factory=list)
    reason: str = Field(default="", description="Why the gate accepted or refused")


# ---------------------------------------------------------------------------
# Request models — reuse from schemas, extra="forbid" (P1)
# ---------------------------------------------------------------------------


class AcademicReportRequest(BaseModel):
    """Report generation request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1)
    report_type: Literal[
        "literature_review",
        "research_summary",
        "thematic_analysis",
        "historical_interpretation",
    ] = Field(...)
    top_k: int = Field(default=5, ge=1, le=20)


class AcademicSynthesisRequest(BaseModel):
    """Synthesis request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class AcademicResearchRequest(BaseModel):
    """Research assistant request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class AcademicEducationRequest(BaseModel):
    """Education mode request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


# ---------------------------------------------------------------------------
# Academic metadata
# ---------------------------------------------------------------------------


class AcademicMetadata(BaseModel):
    """Metadata for academic generation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    top_k: int = 5
    total_claims: int = 0
    total_retrievals: int = 0
    total_documents: int = 0
    model: str = "academic-grounded-v2-p0"
    reproducibility: ReproducibilityMetadata = Field(
        default_factory=ReproducibilityMetadata
    )


# ---------------------------------------------------------------------------
# Unified academic response (P1: strict, extra="forbid")
# ---------------------------------------------------------------------------


class AcademicResponse(BaseModel):
    """Unified response envelope for all four academic modules. P1: strict."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str
    academic_type: Literal["report", "synthesis", "research", "education"]

    # Report fields
    title: str | None = None
    sections: list[ReportSection] = Field(default_factory=list)

    # Synthesis fields
    themes: list[SynthesisTheme] = Field(default_factory=list)

    # Research fields
    decomposition: list[ResearchSubQuestion] = Field(default_factory=list)

    # Education fields
    explanation: list[EducationConcept] = Field(default_factory=list)

    # Shared — always present
    citations: list[CitationRef] = Field(default_factory=list)
    evidence_trace: list[EvidenceTrace] = Field(default_factory=list)
    metadata: AcademicMetadata = Field(default_factory=AcademicMetadata)

    # Unsupported-claim gate result (P0-6)
    gate_verdict: UnsupportedClaimVerdict | None = None
