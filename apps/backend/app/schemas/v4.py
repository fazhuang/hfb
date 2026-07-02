"""V4 product layer schemas — strict, extra="forbid"."""
from __future__ import annotations

from typing import Literal, Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class V4ResearchSessionRequest(BaseModel):
    """Create/initialize a research session."""
    model_config = ConfigDict(extra="forbid", strict=True)
    title: str | None = Field(default=None)
    query: str | None = Field(default=None)


class V4ResearchQueryRequest(BaseModel):
    """Execute a research query within a session."""
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    mode: Literal["report", "synthesis", "research", "education", "graph"] = Field(
        default="research"
    )


class V4ResearchWorkflowRequest(BaseModel):
    """Execute a structured research workflow."""
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    workflow_type: Literal["full_research_flow"] = Field(
        default="full_research_flow"
    )


class V4VisualizationGraphRequest(BaseModel):
    """Generate visualization data."""
    model_config = ConfigDict(extra="forbid", strict=True)
    concept_labels: list[str] = Field(..., min_length=1, max_length=20)
    graph_type: Literal["concept", "citation", "timeline", "document"] = Field(
        default="concept"
    )


class V4EducationLearnRequest(BaseModel):
    """Education mode — grounded explanations only."""
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    level: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner"
    )


# ---------------------------------------------------------------------------
# Visualization strict schemas — no free-form, every edge carries evidence
# ---------------------------------------------------------------------------


class VisualizationNode(BaseModel):
    """Strict visualization node — no free-form fields."""
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str
    type: Literal["concept", "document", "entity"]
    label: str
    metadata: dict[str, str] = Field(default_factory=dict)
    trace_ids: list[str] = Field(default_factory=list)


class VisualizationEdge(BaseModel):
    """Strict visualization edge — every edge carries evidence backlinks."""
    model_config = ConfigDict(extra="forbid", strict=True)
    source: str
    target: str
    type: Literal["citation", "hierarchy", "co_occurrence", "similarity", "timeline"]
    weight: float
    evidence_ids: list[str] = Field(default_factory=list)


class VisualizationGraph(BaseModel):
    """Full graph output — no untyped structures."""
    model_config = ConfigDict(extra="forbid", strict=True)
    nodes: list[VisualizationNode] = Field(default_factory=list)
    edges: list[VisualizationEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Traceability — stable IDs only, internal fields never exposed
# ---------------------------------------------------------------------------


class V4TraceabilityBlock(BaseModel):
    """API-visible traceability — stable IDs only."""
    model_config = ConfigDict(extra="forbid", strict=True)
    query_id: str
    trace_ids: list[str] = Field(default_factory=list)
    citation_count: int = 0
    source_documents: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Workflow step
# ---------------------------------------------------------------------------


class V4WorkflowStep(BaseModel):
    """One step in a ResearchRun execution trace."""
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str
    status: Literal["pending", "running", "completed", "failed"]
    result: dict[str, Any] | None = None
    trace_ids: list[str] = Field(default_factory=list)


class V4WorkflowResponse(BaseModel):
    """Full workflow response with ResearchRun data."""
    model_config = ConfigDict(extra="forbid", strict=True)
    run_id: str
    session_id: str
    steps: list[V4WorkflowStep] = Field(default_factory=list)
    traceability: V4TraceabilityBlock | None = None


# ---------------------------------------------------------------------------
# API envelope
# ---------------------------------------------------------------------------


class V4ApiEnvelope(BaseModel):
    """V4 API response envelope — always includes traceability."""
    model_config = ConfigDict(extra="forbid", strict=True)
    success: bool = True
    data: Any
    message: str = "ok"
    traceability: V4TraceabilityBlock | None = None
