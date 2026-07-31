"""
Version Center API — lineage, comparison, diff, passage mapping.

Per HFB-PS-1701 Version Center Product Specification Ch.15.
Per HFB-DOM-0803 Version Knowledge Model Ch.8-13.

GET    /api/v1/versions/{id}/lineage
POST   /api/v1/versions/relations
POST   /api/v1/versions/compare
GET    /api/v1/versions/diffs/{diff_id}
POST   /api/v1/passages/mappings
GET    /api/v1/versions/{id}/mappings
GET    /api/v1/passages/{id1}/diff/{id2}
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.services.version_center import VersionComparisonService
from app.utils.response import api_response

router = APIRouter(tags=["Version Center"])


# ------------------------------------------------------------------
# Request schemas
# ------------------------------------------------------------------


class VersionRelationCreate(BaseModel):
    source_version_id: UUID
    target_version_id: UUID
    relation_type: str = Field(
        ...,
        description="derived_from, revised_from, corrected_by, annotated_by, compared_with, referenced_by",
    )
    description: str | None = None
    evidence: str | None = None


class VersionCompareRequest(BaseModel):
    source_version_id: UUID
    target_version_id: UUID


class PassageMappingCreate(BaseModel):
    source_passage_id: UUID
    target_passage_id: UUID
    mapping_type: str = Field(
        default="equivalent", description="equivalent, variant, missing, added"
    )
    description: str | None = None


# ------------------------------------------------------------------
# Lineage
# ------------------------------------------------------------------


@router.get(
    "/versions/{version_id}/lineage",
    response_model=dict,
    dependencies=[Depends(require_permission("version", "read"))],
)
async def get_version_lineage(
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Return the version lineage tree."""
    svc = VersionComparisonService(session)
    try:
        data = await svc.get_lineage(version_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return api_response(data=data)


# ------------------------------------------------------------------
# Version Relations (CRUD for version_relations table)
# ------------------------------------------------------------------


@router.post(
    "/versions/relations",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("version", "create"))],
)
async def create_version_relation(
    body: VersionRelationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Create a relation between two versions."""
    svc = VersionComparisonService(session)
    try:
        relation = await svc.add_relation(
            source_version_id=body.source_version_id,
            target_version_id=body.target_version_id,
            relation_type=body.relation_type,
            description=body.description,
            evidence=body.evidence,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    return api_response(
        data={
            "id": str(relation.id),
            "source_version_id": relation.source_version_id,
            "target_version_id": relation.target_version_id,
            "relation_type": relation.relation_type,
        },
        message="Version relation created",
    )


# ------------------------------------------------------------------
# Comparison / Diff
# ------------------------------------------------------------------


@router.post(
    "/versions/compare",
    response_model=dict,
    dependencies=[Depends(require_permission("version", "read"))],
)
async def compare_versions(
    body: VersionCompareRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Run a full passage-by-passage comparison between two versions."""
    svc = VersionComparisonService(session)
    try:
        result = await svc.run_full_compare(
            source_version_id=body.source_version_id,
            target_version_id=body.target_version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return api_response(data=result, message="Comparison complete")


@router.get(
    "/versions/diffs/{diff_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("version", "read"))],
)
async def get_saved_diff(
    diff_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Retrieve a previously saved version diff."""
    svc = VersionComparisonService(session)
    diff = await svc.get_saved_diff(diff_id)
    if diff is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Diff not found"
        )
    return api_response(data=diff)


@router.get(
    "/passages/{passage_id_1}/diff/{passage_id_2}",
    response_model=dict,
    dependencies=[Depends(require_permission("passage", "read"))],
)
async def diff_passages(
    passage_id_1: UUID,
    passage_id_2: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Generate a word-level diff between two specific passages."""
    svc = VersionComparisonService(session)
    try:
        result = await svc.compare_passages(passage_id_1, passage_id_2)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return api_response(data=result)


# ------------------------------------------------------------------
# Passage Mappings
# ------------------------------------------------------------------


@router.post(
    "/passages/mappings",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("passage", "create"))],
)
async def create_passage_mapping(
    body: PassageMappingCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Create a passage mapping between two versions."""
    svc = VersionComparisonService(session)
    try:
        mapping = await svc.create_passage_mapping(
            source_passage_id=body.source_passage_id,
            target_passage_id=body.target_passage_id,
            mapping_type=body.mapping_type,
            description=body.description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    return api_response(
        data={
            "id": str(mapping.id),
            "source_passage_id": mapping.source_passage_id,
            "target_passage_id": mapping.target_passage_id,
            "mapping_type": mapping.mapping_type,
        },
        message="Passage mapping created",
    )


@router.get(
    "/versions/{version_id}/mappings",
    response_model=dict,
    dependencies=[Depends(require_permission("version", "read"))],
)
async def get_version_passage_mappings(
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Get all passage mappings for a version."""
    svc = VersionComparisonService(session)
    mappings = await svc.get_passage_mappings(version_id)
    return api_response(data={"items": mappings})
