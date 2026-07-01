"""Academic V2 schemas — Sprint 2 academic product layer.

Four modules: report, synthesis, research, education.
All share citation grounding from Sprint 1 GenerationPipeline.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Evidence trace — every claim traceable to source chunk
# ---------------------------------------------------------------------------


class EvidenceTrace(BaseModel):
    """One claim traced back to its source chunk."""

    claim_text: str = Field(..., description="The claim/quote text")
    document_id: str
    chunk_id: str
    quote: str = Field(..., description="Exact original text from chunk")
    citation_text: str = Field(..., description="Formatted citation string")


class CitationRef(BaseModel):
    """A citation reference."""

    document_id: str
    chunk_id: str
    text: str


# ---------------------------------------------------------------------------
# Module-specific content shapes
# ---------------------------------------------------------------------------


class ReportSection(BaseModel):
    """One section of an academic report."""

    heading: str
    body: str  # rendered claims text
    citations: list[CitationRef] = Field(default_factory=list)
    evidence: list[EvidenceTrace] = Field(default_factory=list)


class SynthesisTheme(BaseModel):
    """One thematic cluster of claims."""

    title: str
    description: str = ""
    claims: list[EvidenceTrace] = Field(default_factory=list)
    cross_document_refs: list[str] = Field(
        default_factory=list,
        description="Document IDs that appear across themes",
    )


class ResearchSubQuestion(BaseModel):
    """One decomposed research sub-question with its evidence."""

    sub_question: str
    evidence: list[EvidenceTrace] = Field(default_factory=list)
    has_gap: bool = False
    hypothesis: str | None = None


class EducationConcept(BaseModel):
    """One concept explanation at a difficulty level."""

    concept: str
    level: Literal["beginner", "intermediate"]
    paragraphs: list[str] = Field(default_factory=list)
    citations: list[CitationRef] = Field(default_factory=list)
    evidence: list[EvidenceTrace] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AcademicReportRequest(BaseModel):
    query: str = Field(..., min_length=1)
    report_type: Literal[
        "literature_review",
        "research_summary",
        "thematic_analysis",
        "historical_interpretation",
    ] = "research_summary"
    top_k: int = Field(default=5, ge=1, le=20)


class AcademicSynthesisRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class AcademicResearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class AcademicEducationRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


# ---------------------------------------------------------------------------
# Unified academic response
# ---------------------------------------------------------------------------


class AcademicMetadata(BaseModel):
    """Metadata for academic generation."""

    top_k: int = 5
    total_claims: int = 0
    total_retrievals: int = 0
    total_documents: int = 0
    model: str = "academic-grounded-v2"


class AcademicResponse(BaseModel):
    """Unified response envelope for all four academic modules."""

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

    # Shared
    citations: list[CitationRef] = Field(default_factory=list)
    evidence_trace: list[EvidenceTrace] = Field(default_factory=list)
    metadata: AcademicMetadata = Field(default_factory=AcademicMetadata)
