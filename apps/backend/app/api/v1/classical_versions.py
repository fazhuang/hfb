"""
Classical Version Catalogue API (古籍版本目录).

GET    /api/classical-versions           — authenticated users (read)
GET    /api/classical-versions/{id}      — authenticated users (read)
POST   /api/admin/classical-versions     — admin (create)
PATCH  /api/admin/classical-versions/{id} — admin (update)
DELETE /api/admin/classical-versions/{id} — superuser only (soft delete)
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, get_auth_service
from app.models.classical_version import ClassicalVersion
from app.repositories.base import BaseRepository
from app.schemas.classical_version import (
    ClassicalVersionBrief,
    ClassicalVersionCreate,
    ClassicalVersionResponse,
    ClassicalVersionUpdate,
    EDITION_TYPES,
    PUBLIC_DOMAIN_STATUSES,
    REVIEW_STATUSES,
)
from app.services.auth_service import AuthService
from app.services.base import BaseService
from app.utils.response import api_response

router = APIRouter(tags=["Classical Versions"])

# ------------------------------------------------------------------
# Repository & Service (inline — single-model, nothing to abstract)
# ------------------------------------------------------------------


class ClassicalVersionRepo(BaseRepository[ClassicalVersion]):
    model = ClassicalVersion

    async def search_query(self, query: str, page: int = 1, limit: int = 20):
        return await self.search(
            search_fields=["work_title", "version_name", "dynasty", "repository", "edition_type"],
            query=query,
            page=page,
            limit=limit,
        )


class ClassicalVersionService(BaseService[ClassicalVersionRepo, ClassicalVersionCreate, ClassicalVersionResponse]):
    repository_class = ClassicalVersionRepo

    async def _validate_create(self, data: dict) -> None:
        if not data.get("work_title", "").strip():
            raise ValueError("work_title is required")
        if not data.get("version_name", "").strip():
            raise ValueError("version_name is required")
        if not data.get("source_url", "").strip():
            raise ValueError("source_url is required")
        pd = data.get("public_domain_status", "unknown")
        if pd not in PUBLIC_DOMAIN_STATUSES:
            raise ValueError(f"public_domain_status must be one of: {sorted(PUBLIC_DOMAIN_STATUSES)}")
        rs = data.get("review_status", "pending_review")
        if rs not in REVIEW_STATUSES:
            raise ValueError(f"review_status must be one of: {sorted(REVIEW_STATUSES)}")
        et = data.get("edition_type")
        if et is not None and et not in EDITION_TYPES:
            raise ValueError(f"edition_type must be one of: {sorted(EDITION_TYPES)}")

    async def _validate_update(self, id: UUID, data: dict) -> None:
        pd = data.get("public_domain_status")
        if pd is not None and pd not in PUBLIC_DOMAIN_STATUSES:
            raise ValueError(f"public_domain_status must be one of: {sorted(PUBLIC_DOMAIN_STATUSES)}")
        rs = data.get("review_status")
        if rs is not None and rs not in REVIEW_STATUSES:
            raise ValueError(f"review_status must be one of: {sorted(REVIEW_STATUSES)}")
        et = data.get("edition_type")
        if et is not None and et not in EDITION_TYPES:
            raise ValueError(f"edition_type must be one of: {sorted(EDITION_TYPES)}")

    async def search(self, query: str, page: int = 1, limit: int = 20):
        return await self.repo.search_query(query, page=page, limit=limit)


# ------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------


async def require_superuser(
    user_id: Annotated[str, Depends(get_current_user)],
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    """Dependency: only superusers pass."""
    from app.repositories.user import UserRepository

    user = await UserRepository(auth_svc.session).get_by_id(user_id)
    if user is None or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser required",
        )
    return user_id


async def require_admin_create(
    user_id: Annotated[str, Depends(get_current_user)],
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    """Dependency: user must have classical_version.create or be superuser."""
    if not await auth_svc.has_permission(user_id, "classical_version", "create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin create permission required",
        )
    return user_id


async def require_admin_update(
    user_id: Annotated[str, Depends(get_current_user)],
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    """Dependency: user must have classical_version.update or be superuser."""
    if not await auth_svc.has_permission(user_id, "classical_version", "update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin update permission required",
        )
    return user_id


# ------------------------------------------------------------------
# Public read endpoints (any authenticated user)
# ------------------------------------------------------------------


@router.get("/api/classical-versions", response_model=dict)
async def list_classical_versions(
    session: Annotated[AsyncSession, Depends(get_session)],
    _user_id: Annotated[str, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    q: str = Query(default="", description="Search query"),
    review_status: str | None = Query(default=None, description="Filter by review status"),
    public_domain_status: str | None = Query(default=None, description="Filter by public domain status"),
) -> dict:
    svc = ClassicalVersionService(session)
    if q.strip():
        items, total = await svc.search(q, page=page, limit=limit)
    else:
        items, total = await svc.list(page=page, limit=limit)

    # In-memory filtering for optional query params (# ponytail: SQL filter if perf matters)
    if review_status:
        items = [i for i in items if i.review_status == review_status]
    if public_domain_status:
        items = [i for i in items if i.public_domain_status == public_domain_status]

    results = [ClassicalVersionBrief.model_validate(i).model_dump(mode="json") for i in items]
    return api_response(data={"items": results, "total": total})


@router.get("/api/classical-versions/{version_id}", response_model=dict)
async def get_classical_version(
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    svc = ClassicalVersionService(session)
    obj = await svc.get_by_id(version_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classical version not found")
    return api_response(data=ClassicalVersionResponse.model_validate(obj).model_dump(mode="json"))


# ------------------------------------------------------------------
# Admin write endpoints
# ------------------------------------------------------------------


@router.post(
    "/api/admin/classical-versions",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def create_classical_version(
    body: ClassicalVersionCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[str, Depends(require_admin_create)],
) -> dict:
    svc = ClassicalVersionService(session)
    try:
        obj = await svc.create(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return api_response(
        data=ClassicalVersionResponse.model_validate(obj).model_dump(mode="json"),
        message="Created",
    )


@router.patch("/api/admin/classical-versions/{version_id}", response_model=dict)
async def update_classical_version(
    version_id: UUID,
    body: ClassicalVersionUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: Annotated[str, Depends(require_admin_update)],
) -> dict:
    svc = ClassicalVersionService(session)
    obj = await svc.get_by_id(version_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classical version not found")
    try:
        data = body.model_dump(exclude_unset=True)
        await svc._validate_update(version_id, data)
        updated = await svc.repo.update(version_id, **data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return api_response(
        data=ClassicalVersionResponse.model_validate(updated).model_dump(mode="json"),
        message="Updated",
    )


@router.delete("/api/admin/classical-versions/{version_id}", response_model=dict)
async def delete_classical_version(
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _superuser: Annotated[str, Depends(require_superuser)],
) -> dict:
    svc = ClassicalVersionService(session)
    obj = await svc.get_by_id(version_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classical version not found")
    await svc.soft_delete(version_id)
    return api_response(data=None, message="Deleted")
