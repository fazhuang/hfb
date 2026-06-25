"""
Graph schemas — EntityRelation, GraphNode, GraphEdge, and API response models.

Per HFB-PS-1707 Knowledge Graph Product Specification.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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
    evidence: str | None = None


class EntityRelationCreate(EntityRelationBase):
    pass


class EntityRelationUpdate(BaseModel):
    relation_type: str | None = None
    description: str | None = None
    evidence: str | None = None


class EntityRelationResponse(EntityRelationBase):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================
# Graph Visualization Types
# ============================================================


class GraphNode(BaseModel):
    """A node in the graph visualization."""
    id: str  # composite key: "{entity_type}:{entity_id}"
    entity_type: str
    entity_id: str
    label: str  # display name
    properties: dict[str, Any] = Field(default_factory=dict)  # extra metadata


class GraphEdge(BaseModel):
    """An edge in the graph visualization."""
    id: str  # composite key
    source_id: str  # node id of source
    target_id: str  # node id of target
    relation_type: str  # authored, compiled, derived_from, etc.
    label: str  # human-readable relation label
    source: str = "explicit"  # "explicit" | "fk" | "version" — origin of edge


class Subgraph(BaseModel):
    """A subgraph containing nodes and edges."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class PathResult(BaseModel):
    """A path between two entities."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    length: int


class NeighborResult(BaseModel):
    """Neighborhood of an entity — 1-hop subgraph."""
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
    "commented_on": "注释",
    "cited_in": "引用",
    "studied": "研究",
    "compared": "比较",
    "referenced": "参考",
    "related_to": "关联",
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
}
