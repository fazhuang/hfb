"""
Graph schemas — Sprint 3 P0: strict evidence-bound edges, concept graph, similarity.

Every GraphEdge now carries structured evidence. API responses use strict schemas,
not dict. Concept nodes/edges carry deterministic IDs and corpus evidence.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Sprint 3 P0: Structured corpus evidence
# ============================================================


class GraphEvidence(BaseModel):
    """Structured corpus evidence bound to a chunk — P0-2: full provenance chain.

    Every field carried through from EntityRelation → RAG response without loss.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    document_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)
    exact_quote: str = Field(..., min_length=1)
    citation: str = Field(..., min_length=1)  # [document_id:chunk_id]
    # P0-2: provenance chain fields — carried losslessly to citation
    version_id: str = Field(default="")
    passage_id: str = Field(default="")
    source_uri: str = Field(default="")
    claim_text: str = Field(default="")


# ============================================================
# EntityRelation
# ============================================================


class EntityRelationBase(BaseModel):
    source_entity_type: str = Field(..., min_length=1, max_length=50)
    source_entity_id: str = Field(..., min_length=1, max_length=36)
    target_entity_type: str = Field(..., min_length=1, max_length=50)
    target_entity_id: str = Field(..., min_length=1, max_length=36)
    relation_type: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    evidence: GraphEvidence | None = None


class EntityRelationCreate(EntityRelationBase):
    pass


class EntityRelationUpdate(BaseModel):
    relation_type: str | None = None
    description: str | None = None
    evidence: GraphEvidence | None = None


class EntityRelationResponse(EntityRelationBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Graph Visualization Types
# ============================================================


class GraphNode(BaseModel):
    """A node in the graph visualization."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str  # composite key: "{entity_type}:{entity_id}"
    entity_type: str
    entity_id: str
    label: str  # display name
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the graph visualization — Sprint 3 P0: evidence REQUIRED."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    source_id: str
    target_id: str
    relation_type: str
    label: str
    source: str = "explicit"  # "explicit" | "fk" | "version" | "concept"
    evidence: (
        GraphEvidence  # required — no null evidence edges allowed in knowledge graph
    )


class Subgraph(BaseModel):
    """A subgraph containing nodes and edges."""

    model_config = ConfigDict(extra="forbid", strict=True)

    nodes: list[GraphNode]
    edges: list[GraphEdge]


class PathResult(BaseModel):
    """A path between two entities."""

    model_config = ConfigDict(extra="forbid", strict=True)

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    length: int


class NeighborResult(BaseModel):
    """Neighborhood of an entity — 1-hop subgraph."""

    model_config = ConfigDict(extra="forbid", strict=True)

    center: GraphNode
    neighbors: list[GraphNode]
    edges: list[GraphEdge]


# ============================================================
# Relationship label mapping
# ============================================================

RELATION_LABELS: dict[str, str] = {
    # Explicit EntityRelation types
    "authored": "作者",
    "compiled": "编撰",
    "compiled_from": "编纂依据",
    "commented_on": "注释",
    "cited_in": "引用",
    "studied": "研究",
    "compared": "比较",
    "referenced": "参考",
    "related_to": "关联",
    "contains": "包含",
    "treats": "治疗",
    "corresponds_to": "对应",
    # VersionRelation types
    "derived_from": "承袭",
    "revised_from": "修订",
    "corrected_by": "校勘",
    "annotated_by": "注疏",
    "compared_with": "比较",
    "referenced_by": "引用",
    # FK-derived edges
    "fk_author": "作者",
    "fk_book": "所属书籍",
    "fk_chapter": "所属章节",
    "fk_version": "所属版本",
    "fk_parent": "父章节",
    "fk_passage_to_version": "关联版本",
    # Sprint 3 P0: Concept relation labels
    "co_occurs_with": "共现",
    "broader_than": "上位",
    "narrower_than": "下位",
    "related_to_concept": "概念关联",
}


# ============================================================
# Sprint 3 P0: Concept Graph
# ============================================================


class ConceptNode(BaseModel):
    """A concept node with stable ID derived from normalized label."""

    model_config = ConfigDict(extra="forbid", strict=True)

    concept_id: str = Field(
        ..., description="SHA-256 of normalized_label (first 16 hex)"
    )
    normalized_label: str = Field(..., min_length=1)
    display_label: str = Field(..., min_length=1)
    evidence: list[GraphEvidence] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)


class ConceptEdge(BaseModel):
    """A concept relationship with stable ID and corpus evidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    edge_id: str = Field(
        ..., description="SHA-256 of source+target+relation (first 16 hex)"
    )
    source_concept_id: str
    target_concept_id: str
    relation_type: str  # co_occurs_with, broader_than, narrower_than, related_to
    label: str
    evidence: list[GraphEvidence] = Field(default_factory=list, min_length=1)


class ConceptGraph(BaseModel):
    """A structured concept graph — nodes + edges with evidence."""

    model_config = ConfigDict(extra="forbid", strict=True)

    nodes: list[ConceptNode] = Field(default_factory=list)
    edges: list[ConceptEdge] = Field(default_factory=list)


# ============================================================
# Sprint 3 P0: Concept Similarity
# ============================================================


class ConceptSimilarity(BaseModel):
    """Deterministic similarity between two concepts — no ML, no randomness."""

    model_config = ConfigDict(extra="forbid", strict=True)

    concept_a: str = Field(..., min_length=1)
    concept_b: str = Field(..., min_length=1)
    score: float = Field(
        ..., description="Jaccard co-occurrence score, fixed 4 decimals"
    )
    formula: str = "jaccard_co_occurrence_v1"
    formula_version: str = "1.0.0"
    shared_document_ids: list[str] = Field(default_factory=list)
    shared_chunk_ids: list[str] = Field(default_factory=list)
    evidence: list[GraphEvidence] = Field(default_factory=list)
    corpus_sha256: str = Field(default="")


# ============================================================
# Sprint 3 P0: Cross-Document Analysis
# ============================================================


class CrossDocumentClaim(BaseModel):
    """A claim from a specific document with evidence binding."""

    model_config = ConfigDict(extra="forbid", strict=True)

    claim_text: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)
    evidence: GraphEvidence


class CrossDocumentAnalysis(BaseModel):
    """Cross-document comparison — only what the corpus directly supports."""

    model_config = ConfigDict(extra="forbid", strict=True)

    topic: str = Field(..., min_length=1)
    status: str = Field(
        default="insufficient_evidence",
        description="supported_comparison | confirmed_contradiction | insufficient_evidence",
    )
    supporting_claims: list[CrossDocumentClaim] = Field(default_factory=list)
    differing_claims: list[CrossDocumentClaim] = Field(default_factory=list)
    contradictions: list[dict[str, CrossDocumentClaim]] = Field(
        default_factory=list,
        description="Pairs of opposing claims with evidence. Empty if insufficient evidence.",
    )
    source_document_ids: list[str] = Field(default_factory=list)
    evidence_trace: list[GraphEvidence] = Field(default_factory=list)
    corpus_sha256: str = Field(default="")
    output_sha256: str = Field(default="")


# ============================================================
# Sprint 3 P0: Intelligence unified API
# ============================================================


class IntelligenceRequest(BaseModel):
    """Unified knowledge intelligence request."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(
        ..., min_length=1, description="Whitespace-separated concept keywords"
    )


class IntelligenceResponse(BaseModel):
    """Unified knowledge intelligence response — deterministic, evidence-bound."""

    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(..., min_length=1)
    concept_graph: ConceptGraph
    similarities: list[ConceptSimilarity] = Field(default_factory=list)
    cross_document_analyses: list[CrossDocumentAnalysis] = Field(default_factory=list)
    citations: list[GraphEvidence] = Field(default_factory=list)
    evidence_trace: list[GraphEvidence] = Field(default_factory=list)
    research_hypotheses: list[GraphEvidence] = Field(default_factory=list)
    corpus_sha256: str = Field(default="")
    output_sha256: str = Field(default="")
    pipeline_version: str = Field(default="1.0.0")


# ============================================================
# Sprint 3 P0: Strict API envelopes (replacing response_model=dict)
# ============================================================


class GraphApiEnvelope(BaseModel):
    """Strict API envelope for Graph endpoints — no dict schema."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: object | None = None
    message: str = Field(default="ok")


class GraphNeighborsEnvelope(BaseModel):
    """Envelope for neighbor response."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: NeighborResult | None = None
    message: str = Field(default="ok")


class GraphPathEnvelope(BaseModel):
    """Envelope for path response."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: PathResult | None = None
    message: str = Field(default="ok")


class GraphSubgraphEnvelope(BaseModel):
    """Envelope for subgraph response."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: Subgraph | None = None
    message: str = Field(default="ok")


class GraphEntitiesEnvelope(BaseModel):
    """Envelope for entity search response."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: list[GraphNode] = Field(default_factory=list)
    message: str = Field(default="ok")


class GraphRelationsEnvelope(BaseModel):
    """Envelope for entity relations list response."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: list[EntityRelationResponse] = Field(default_factory=list)
    message: str = Field(default="ok")


class GraphCreateRelationEnvelope(BaseModel):
    """Envelope for create relation response (201)."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: EntityRelationResponse | None = None
    message: str = Field(default="ok")


class GraphDeleteEnvelope(BaseModel):
    """Envelope for delete response."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: None = None
    message: str = Field(default="ok")


class IntelligenceEnvelope(BaseModel):
    """Envelope for /intelligence response."""

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: IntelligenceResponse | None = None
    message: str = Field(default="ok")
