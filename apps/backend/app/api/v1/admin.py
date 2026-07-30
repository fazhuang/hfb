"""
Admin API — document review, withdraw, ingestion audit, source policies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel as _PydanticBaseModel
from sqlalchemy import func
from sqlalchemy import select as sql_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.models.document import Document
from app.models.fulltext_ingestion_audit import FulltextIngestionAudit
from app.schemas.document import (
    REVIEW_STATUSES,
    DocumentReviewRequest,
    DocumentWithdrawRequest,
)
from app.services.ingestion import IngestionService
from app.utils.response import api_response

router = APIRouter(tags=["Admin"])

document_review_guard = require_permission("document", "review")
document_update_guard = require_permission("document", "update")
source_policy_read_guard = require_permission("source_policy", "read")
source_policy_create_guard = require_permission("source_policy", "create")
source_policy_update_guard = require_permission("source_policy", "update")
source_policy_delete_guard = require_permission("source_policy", "delete")


# ============================================================
# Document review
# ============================================================


@router.patch(
    "/documents/{document_id}/review",
    response_model=dict,
    dependencies=[Depends(document_review_guard)],
)
async def review_document(
    document_id: UUID,
    body: DocumentReviewRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    if body.review_status not in REVIEW_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"review_status must be one of: {sorted(REVIEW_STATUSES)}",
        )

    doc = await session.get(Document, str(document_id))
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    now = datetime.now(UTC)
    doc.review_status = body.review_status
    doc.reviewed_by = user_id
    doc.reviewed_at = now

    # Auto-enable RAG on approve unless explicitly set
    rag_enabled = body.rag_enabled
    if rag_enabled is None:
        rag_enabled = body.review_status == "approved"
    doc.rag_enabled = rag_enabled

    # P0: Create SourceRef on approve if doc has source_url (Codex requirement)
    if rag_enabled and doc.source_url:
        try:
            from app.services.ingestion import IngestionService as _IngSvc

            await _IngSvc._ensure_source_ref(
                session=session,
                title=doc.title,
                url=doc.source_url,
                author=doc.source_name,
                page_location=f"document:{doc.id}",
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Failed to create SourceRef on review for doc %s", document_id
            )

    await session.commit()
    await session.refresh(doc)

    from app.schemas.document import DocumentResponse

    return api_response(
        data=DocumentResponse.model_validate(doc).model_dump(mode="json"),
        message="Review updated",
    )


# ============================================================
# Document withdraw
# ============================================================


@router.post(
    "/documents/{document_id}/withdraw",
    response_model=dict,
    dependencies=[Depends(document_update_guard)],
)
async def withdraw_document(
    document_id: UUID,
    body: DocumentWithdrawRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    doc = await session.get(Document, str(document_id))
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    if doc.withdrawn_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document already withdrawn",
        )

    svc = IngestionService(session)
    await svc.withdraw_document(str(document_id), reason=body.reason, actor_id=user_id)
    await session.commit()

    return api_response(data=None, message="Document withdrawn")


# ============================================================
# Ingestion audit tasks
# ============================================================


@router.get(
    "/ingestion/tasks",
    response_model=dict,
    dependencies=[Depends(require_permission("document", "read"))],
)
async def list_ingestion_tasks(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    source_name: str | None = Query(default=None),
) -> dict:
    query = sql_select(FulltextIngestionAudit)

    if action:
        query = query.where(FulltextIngestionAudit.action == action)
    if status_filter:
        query = query.where(FulltextIngestionAudit.status == status_filter)
    if source_name:
        query = query.where(FulltextIngestionAudit.source_name == source_name)

    # Total
    count_q = sql_select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(FulltextIngestionAudit.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    rows = (await session.execute(query)).scalars().all()

    items = []
    for r in rows:
        items.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "action": r.action,
                "status": r.status,
                "source_url": r.source_url,
                "source_name": r.source_name,
                "copyright_status": r.copyright_status,
                "authorization_basis": r.authorization_basis,
                "license_type": r.license_type,
                "review_status": r.review_status,
                "reviewed_by": r.reviewed_by,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                "checksum": r.checksum,
                "result_entity_type": r.result_entity_type,
                "result_entity_id": r.result_entity_id,
                "reject_reason": r.reject_reason,
                "skipped_reason": r.skipped_reason,
                "actor_id": r.actor_id,
                "details": r.details,
            }
        )

    return api_response(data={"items": items, "total": total})


# ============================================================
# Source Policies
# ============================================================

from app.models.source_policy import SourcePolicy
from app.schemas.source_policy import (
    SourcePolicyCreate,
    SourcePolicyResponse,
    SourcePolicyUpdate,
)


@router.get(
    "/admin/source-policies",
    response_model=dict,
    dependencies=[Depends(source_policy_read_guard)],
)
async def list_source_policies(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    stmt = sql_select(SourcePolicy).order_by(SourcePolicy.source_name)
    rows = (await session.execute(stmt)).scalars().all()
    items = [
        SourcePolicyResponse.model_validate(r).model_dump(mode="json") for r in rows
    ]
    return api_response(data={"items": items, "total": len(items)})


@router.post(
    "/admin/source-policies",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(source_policy_create_guard)],
)
async def create_source_policy(
    body: SourcePolicyCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    existing = (
        await session.execute(
            sql_select(SourcePolicy).where(SourcePolicy.source_name == body.source_name)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Source policy for '{body.source_name}' already exists",
        )

    sp = SourcePolicy(
        id=str(uuid4()),
        source_name=body.source_name,
        enabled=body.enabled,
    )
    session.add(sp)
    await session.commit()
    await session.refresh(sp)
    return api_response(
        data=SourcePolicyResponse.model_validate(sp).model_dump(mode="json"),
        message="Created",
    )


@router.patch(
    "/admin/source-policies/{policy_id}",
    response_model=dict,
    dependencies=[Depends(source_policy_update_guard)],
)
async def update_source_policy(
    policy_id: UUID,
    body: SourcePolicyUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    sp = await session.get(SourcePolicy, str(policy_id))
    if sp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source policy not found"
        )

    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(sp, k, v)
    await session.commit()
    await session.refresh(sp)
    return api_response(
        data=SourcePolicyResponse.model_validate(sp).model_dump(mode="json"),
        message="Updated",
    )


@router.delete(
    "/admin/source-policies/{policy_id}",
    response_model=dict,
    dependencies=[Depends(source_policy_delete_guard)],
)
async def delete_source_policy(
    policy_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    sp = await session.get(SourcePolicy, str(policy_id))
    if sp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source policy not found"
        )

    await session.delete(sp)
    await session.commit()
    return api_response(data=None, message="Deleted")


# ============================================================
# Version withdraw / restore (P2T1)
# ============================================================


class VersionWithdrawRequest(_PydanticBaseModel):
    reason: str = "未说明"


@router.post(
    "/versions/{version_id}/withdraw",
    response_model=dict,
    dependencies=[Depends(document_update_guard)],
)
async def withdraw_version(
    version_id: UUID,
    body: VersionWithdrawRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    """Withdraw a version — marks it as non-academic-citable."""
    from app.models.version import Version

    ver = await session.get(Version, str(version_id))
    if ver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )

    # Ownership check: admin-only action via RBAC; verify version → book is reachable
    if not ver.book_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Version has no associated book — cannot verify ownership",
        )
    # The admin guard (document_update_guard) already requires admin RBAC;
    # explicit check that the version record is accessible and undeleted.
    if ver.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )
    if ver.withdrawn_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Version already withdrawn",
        )
    ver.withdraw(reason=body.reason)
    await session.commit()
    await session.refresh(ver)
    return api_response(
        data={
            "id": ver.id,
            "version_name": ver.version_name,
            "withdrawn_at": ver.withdrawn_at.isoformat() if ver.withdrawn_at else None,
            "withdraw_reason": ver.withdraw_reason,
        },
        message="Version withdrawn",
    )


@router.post(
    "/versions/{version_id}/restore",
    response_model=dict,
    dependencies=[Depends(document_update_guard)],
)
async def restore_version(
    version_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    """Restore a previously withdrawn version."""
    from app.models.version import Version

    ver = await session.get(Version, str(version_id))
    if ver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Version not found"
        )
    if ver.withdrawn_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Version is not withdrawn",
        )
    ver.restore()
    await session.commit()
    await session.refresh(ver)
    return api_response(
        data={
            "id": ver.id,
            "version_name": ver.version_name,
            "is_formal_source": ver.is_formal_source,
        },
        message="Version restored",
    )
