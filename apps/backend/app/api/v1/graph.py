"""
Graph API — knowledge graph exploration endpoints.

Per HFB-PS-1707 Knowledge Graph Product Specification.
Sprint 3 P0: Strict response schemas replacing response_model=dict.

Endpoints:
  GET  /api/v1/graph/entities       — Search graph entities
  GET  /api/v1/graph/neighbors/{entity_type}/{id}  — 1-hop neighborhood
  GET  /api/v1/graph/path           — BFS path between two entities
  GET  /api/v1/graph/entity/{entity_type}/{id}     — Entity subgraph (2-hop)
  POST /api/v1/graph/relations      — Create explicit EntityRelation
  GET  /api/v1/graph/relations/{entity_type}/{id}  — List relations for entity
  DELETE /api/v1/graph/relations/{relation_id}     — Delete entity relation
  POST /api/v1/graph/intelligence   — Unified knowledge intelligence
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import (
    get_current_user,
    require_any_permission,
    require_permission,
)
from app.schemas.graph import (
    EntityRelationCreate,
    EntityRelationResponse,
    GraphCreateRelationEnvelope,
    GraphDeleteEnvelope,
    GraphEntitiesEnvelope,
    GraphNeighborsEnvelope,
    GraphPathEnvelope,
    GraphRelationsEnvelope,
    GraphSubgraphEnvelope,
    IntelligenceEnvelope,
    IntelligenceRequest,
    IntelligenceResponse,
    VerifyRelationEnvelope,
    VerifyRelationRequest,
)
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])

guard_read = require_permission("graph", "read")
guard_create = require_permission("graph", "create")
guard_delete = require_permission("graph", "delete")
guard_verify = require_any_permission(("graph", "review"), ("graph", "approve"))


# ============================================================
# Search entities
# ============================================================


@router.get(
    "/entities",
    response_model=GraphEntitiesEnvelope,
    dependencies=[Depends(guard_read)],
)
async def search_graph_entities(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str = Query(default="", description="Search query"),
    types: str = Query(
        default="",
        description="Comma-separated entity types: person,book,version,passage",
    ),
    limit: int = Query(default=50, ge=1, le=100),
) -> GraphEntitiesEnvelope:
    """Search for entities available in the knowledge graph."""
    entity_types: list[str] | None = None
    if types.strip():
        entity_types = [t.strip() for t in types.split(",") if t.strip()]

    svc = GraphService(session)
    nodes = await svc.search_entities(
        entity_types=entity_types, query=q.strip(), limit=limit
    )
    return GraphEntitiesEnvelope(success=True, data=nodes, message="ok")


# ============================================================
# Neighborhood
# ============================================================


@router.get(
    "/neighbors/{entity_type}/{entity_id}",
    response_model=GraphNeighborsEnvelope,
    dependencies=[Depends(guard_read)],
)
async def get_neighbors(
    entity_type: str,
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GraphNeighborsEnvelope:
    """Get the 1-hop neighborhood around an entity."""
    svc = GraphService(session)
    try:
        result = await svc.get_neighbors(entity_type, entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return GraphNeighborsEnvelope(success=True, data=result, message="ok")


# ============================================================
# Path finding
# ============================================================


@router.get(
    "/path",
    response_model=GraphPathEnvelope,
    dependencies=[Depends(guard_read)],
)
async def find_path(
    session: Annotated[AsyncSession, Depends(get_session)],
    source_type: str = Query(..., description="Source entity type"),
    source_id: str = Query(..., description="Source entity ID"),
    target_type: str = Query(..., description="Target entity type"),
    target_id: str = Query(..., description="Target entity ID"),
    max_depth: int = Query(default=6, ge=1, le=10),
    relation_filter: str | None = Query(
        default=None, description="Filter edges by relation type"
    ),
) -> GraphPathEnvelope:
    """Find the shortest path between two entities using BFS."""
    svc = GraphService(session)
    result = await svc.find_path(
        source_type,
        source_id,
        target_type,
        target_id,
        max_depth,
        relation_filter=relation_filter,
    )
    if result is None:
        return GraphPathEnvelope(
            success=True,
            data=None,
            message=f"No path found between {source_type}:{source_id} and {target_type}:{target_id}",
        )
    return GraphPathEnvelope(success=True, data=result, message="ok")


# ============================================================
# Entity subgraph (2-hop)
# ============================================================


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=GraphSubgraphEnvelope,
    dependencies=[Depends(guard_read)],
)
async def get_entity_subgraph(
    entity_type: str,
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GraphSubgraphEnvelope:
    """Get the 2-hop subgraph centered on an entity."""
    svc = GraphService(session)
    try:
        result = await svc.get_entity_subgraph(entity_type, entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return GraphSubgraphEnvelope(success=True, data=result, message="ok")


# ============================================================
# EntityRelation CRUD
# ============================================================


@router.post(
    "/relations",
    response_model=GraphCreateRelationEnvelope,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(guard_create)],
)
async def create_relation(
    body: EntityRelationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GraphCreateRelationEnvelope:
    """Create an explicit relationship between two graph entities."""
    svc = GraphService(session)
    try:
        relation = await svc.create_relation(
            source_entity_type=body.source_entity_type,
            source_entity_id=body.source_entity_id,
            target_entity_type=body.target_entity_type,
            target_entity_id=body.target_entity_id,
            relation_type=body.relation_type,
            description=body.description,
            evidence=body.evidence,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    resp = EntityRelationResponse(
        id=UUID(relation.id),
        source_entity_type=relation.source_entity_type,
        source_entity_id=relation.source_entity_id,
        target_entity_type=relation.target_entity_type,
        target_entity_id=relation.target_entity_id,
        relation_type=relation.relation_type,
        description=relation.description,
        evidence=(GraphService._relation_evidence(relation)),
        created_at=relation.created_at,
        updated_at=relation.updated_at,
    )
    return GraphCreateRelationEnvelope(
        success=True, data=resp, message="Relation created"
    )


@router.get(
    "/relations/{entity_type}/{entity_id}",
    response_model=GraphRelationsEnvelope,
    dependencies=[Depends(guard_read)],
)
async def list_entity_relations(
    entity_type: str,
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GraphRelationsEnvelope:
    """List all explicit relations involving an entity (validated only)."""
    svc = GraphService(session)
    validated = await svc.get_validated_relations_for_entity(entity_type, entity_id)
    resp = [
        EntityRelationResponse(
            id=UUID(r.id),
            source_entity_type=r.source_entity_type,
            source_entity_id=r.source_entity_id,
            target_entity_type=r.target_entity_type,
            target_entity_id=r.target_entity_id,
            relation_type=r.relation_type,
            description=r.description,
            evidence=ev,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r, ev in validated
    ]
    return GraphRelationsEnvelope(success=True, data=resp, message="ok")


@router.delete(
    "/relations/{relation_id}",
    response_model=GraphDeleteEnvelope,
    dependencies=[Depends(guard_delete)],
)
async def delete_relation(
    relation_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GraphDeleteEnvelope:
    """Soft-delete an entity relation."""
    svc = GraphService(session)
    ok = await svc.delete_relation(relation_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Relation not found"
        )
    return GraphDeleteEnvelope(success=True, data=None, message="Relation deleted")


# ============================================================
# P0-2: Verify Relation — single entry point for verified status
# ============================================================


@router.post(
    "/relations/{relation_id}/verify",
    response_model=VerifyRelationEnvelope,
    dependencies=[Depends(guard_verify)],
)
async def verify_relation(
    relation_id: UUID,
    body: VerifyRelationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[str, Depends(get_current_user)],
) -> VerifyRelationEnvelope:
    """Verify a relation — the only path to evidence_status='verified'.

    Requires graph.review or graph.approve permission.
    verified_by is taken from the authenticated user, NOT the request body.
    """
    svc = GraphService(session)
    try:
        verified = await svc.verify_relation(
            relation_id=str(relation_id),
            claim_text=body.claim_text,
            evidence_document_id=body.evidence_document_id,
            evidence_version_id=body.evidence_version_id,
            evidence_passage_id=body.evidence_passage_id,
            evidence_chunk_id=body.evidence_chunk_id,
            evidence_quote=body.evidence_quote,
            evidence_source_uri=body.evidence_source_uri,
            verified_by=current_user,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    ev = GraphService._relation_evidence(verified)
    resp = EntityRelationResponse(
        id=UUID(verified.id),
        source_entity_type=verified.source_entity_type,
        source_entity_id=verified.source_entity_id,
        target_entity_type=verified.target_entity_type,
        target_entity_id=verified.target_entity_id,
        relation_type=verified.relation_type,
        description=verified.description,
        evidence=ev,
        created_at=verified.created_at,
        updated_at=verified.updated_at,
    )
    return VerifyRelationEnvelope(success=True, data=resp, message="Relation verified")


# ============================================================
# Sprint 3 P0: Unified Knowledge Intelligence
# ============================================================


@router.post(
    "/intelligence",
    response_model=IntelligenceEnvelope,
    dependencies=[Depends(guard_read)],
)
async def graph_intelligence(
    body: IntelligenceRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IntelligenceEnvelope:
    """Unified knowledge intelligence — deterministic, evidence-bound.

    Parses query into concepts, builds concept graph, computes pairwise
    similarities, runs cross-document analysis, and returns a complete
    hash-verifiable response.
    """
    svc = GraphService(session)
    result = await svc.intelligence(body.query)

    # Build IntelligenceResponse from the raw dict
    from app.schemas.graph import (
        ConceptGraph,
        ConceptSimilarity,
        CrossDocumentAnalysis,
        GraphEvidence,
    )

    cg = ConceptGraph(**result["concept_graph"])
    sims = [ConceptSimilarity(**s) for s in result["similarities"]]
    analyses = [CrossDocumentAnalysis(**a) for a in result["cross_document_analyses"]]
    citations = [GraphEvidence(**c) for c in result["citations"]]
    traces = [GraphEvidence(**t) for t in result["evidence_trace"]]

    resp = IntelligenceResponse(
        query=result["query"],
        concept_graph=cg,
        similarities=sims,
        cross_document_analyses=analyses,
        citations=citations,
        evidence_trace=traces,
        research_hypotheses=[],
        corpus_sha256=result["corpus_sha256"],
        output_sha256=result["output_sha256"],
        pipeline_version=result["pipeline_version"],
    )
    return IntelligenceEnvelope(success=True, data=resp, message="ok")
