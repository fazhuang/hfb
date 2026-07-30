"""V4 product layer schemas — strict, extra="forbid".

Sprint 4 P0: min_length constraints on trace_ids/evidence_ids.
              V4 education strict DTO.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class V4ResearchSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str | None = Field(default=None)
    query: str | None = Field(default=None)


class V4ResearchQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    mode: Literal["report", "synthesis", "research", "education", "graph"] = Field(
        default="research"
    )


class V4ResearchWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    workflow_type: Literal["full_research_flow"] = Field(default="full_research_flow")


class V4VisualizationGraphRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str | None = Field(default=None, min_length=1, description="Research session ID for traceability; auto-created if omitted")
    concept_labels: list[str] = Field(..., min_length=1, max_length=20)
    graph_type: Literal["concept", "citation", "timeline", "document"] = Field(default="concept")


class V4EducationLearnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    level: Literal["beginner", "intermediate", "advanced"] = Field(default="beginner")


# ---------------------------------------------------------------------------
# Visualization strict schemas
# ---------------------------------------------------------------------------


class VisualizationNode(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    type: Literal["concept", "document", "entity"]
    label: str
    metadata: dict[str, str] = Field(default_factory=dict)
    trace_ids: list[str] = Field(..., min_length=1)


class VisualizationEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: str
    target: str
    type: Literal["citation", "hierarchy", "co_occurrence", "similarity", "timeline"]
    weight: float = Field(..., ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(..., min_length=1)


class VisualizationGraph(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    nodes: list[VisualizationNode] = Field(default_factory=list)
    edges: list[VisualizationEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Traceability
# ---------------------------------------------------------------------------


class V4TraceabilityBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query_id: str = Field(..., min_length=1)
    trace_ids: list[str] = Field(default_factory=list)
    citation_count: int = 0
    source_documents: list[str] = Field(default_factory=list)
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class V4WorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str
    status: Literal["pending", "running", "completed", "failed"]
    result: dict[str, Any] | None = None
    trace_ids: list[str] = Field(default_factory=list)


class V4WorkflowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    run_id: str
    session_id: str
    steps: list[V4WorkflowStep] = Field(default_factory=list)
    traceability: V4TraceabilityBlock | None = None


# ---------------------------------------------------------------------------
# V4 Education public DTO
# ---------------------------------------------------------------------------


class V4EducationConceptDTO(BaseModel):
    """V4 education concept — public DTO, never leaks internal trace fields."""
    model_config = ConfigDict(extra="forbid", strict=True)
    concept: str
    level: Literal["beginner", "intermediate"] = "beginner"
    paragraphs: list[str] = Field(default_factory=list)
    citation_count: int = 0
    evidence_count: int = 0


class V4EducationSourceComparison(BaseModel):
    """Advanced-level source comparison — from verified evidence only."""
    model_config = ConfigDict(extra="forbid", strict=True)
    document_id: str
    claim_count: int
    claims: list[dict] = Field(default_factory=list)


class V4EducationResponseData(BaseModel):
    """V4 education response data — strict DTO, not `data: Any`."""
    model_config = ConfigDict(extra="forbid", strict=True)
    academic_type: str = "education"
    applied_level: str
    topic: str
    concepts: list[V4EducationConceptDTO] = Field(default_factory=list)
    source_comparison: list[V4EducationSourceComparison] | None = None
    citation_count: int = 0
    source_count: int = 0
    level_description: str = ""


# ---------------------------------------------------------------------------
# API envelope
# ---------------------------------------------------------------------------


class V4ApiEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    success: bool = True
    data: Any
    message: str = "ok"
    traceability: V4TraceabilityBlock | None = None
