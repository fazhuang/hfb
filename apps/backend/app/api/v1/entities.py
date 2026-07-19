"""
Entity CRUD API — Books, Versions, Chapters, Passages, Papers, Images, Persons, Documents.

Implements full RESTful CRUD per HFB-DEV-0504 API Design Standard.

GET    /api/v1/{resource}
POST   /api/v1/{resource}
GET    /api/v1/{resource}/{id}
PATCH  /api/v1/{resource}/{id}
DELETE /api/v1/{resource}/{id}
"""
# Do not enable deferred annotations in this module. The dynamic CRUD factory
# binds concrete Pydantic classes through closure annotations; deferring them
# turns ``body`` into an unresolved string and FastAPI treats it as a query
# parameter instead of a JSON request body.

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission, get_current_user
from app.schemas.entities import (
    BookCreate, BookUpdate, BookBrief, BookResponse,
    VersionCreate, VersionUpdate, VersionBrief, VersionResponse,
    ChapterCreate, ChapterUpdate, ChapterBrief, ChapterResponse,
    PassageCreate, PassageUpdate, PassageBrief, PassageResponse,
    PaperCreate, PaperUpdate, PaperBrief, PaperResponse,
    ImageCreate, ImageBrief, ImageResponse,
)
from app.services.entities import (
    BookService, VersionService, ChapterService,
    PassageService, PaperService, ImageService,
)
from app.utils.response import api_response

router = APIRouter(tags=["Domain Entities"])

# ============================================================
# CRUD helper factory
# ============================================================


def _make_crud(
    entity_name: str,
    service_cls,
    create_schema,
    update_schema,
    brief_schema,
    response_schema,
    public_read: bool = False,
):
    """Generate standard CRUD routes for an entity.

    When public_read=True, list and get endpoints allow anonymous access
    (no JWT required). Mutations (create/update/delete) always require auth.
    """

    guard_create = require_permission(entity_name, "create")
    guard_read = require_permission(entity_name, "read")
    guard_update = require_permission(entity_name, "update")
    guard_delete = require_permission(entity_name, "delete")

    # For public-read entities, no auth dependency on GET routes
    _list_deps: list = [] if public_read else [Depends(guard_read)]
    _get_deps: list = [] if public_read else [Depends(guard_read)]

    @router.get(
        f"/{entity_name}s",
        response_model=dict,
        dependencies=_list_deps,
    )
    async def list_items(
        session: Annotated[AsyncSession, Depends(get_session)],
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        q: str = Query(default="", description="Search query"),
        svc_cls=service_cls,
        brief_cls=brief_schema,
    ) -> dict:
        svc = svc_cls(session)
        if q.strip():
            items, total = await svc.search(q, page=page, limit=limit)
        else:
            items, total = await svc.list(page=page, limit=limit)
        results = [brief_cls.model_validate(i).model_dump(mode="json") for i in items]
        return api_response(data={"items": results, "total": total})

    @router.post(
        f"/{entity_name}s",
        response_model=dict,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(guard_create)],
    )
    async def create_item(
        body: create_schema,
        session: Annotated[AsyncSession, Depends(get_session)],
        svc_cls=service_cls,
        resp_cls=response_schema,
    ) -> dict:
        svc = svc_cls(session)
        try:
            obj = await svc.create(body)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
        return api_response(data=resp_cls.model_validate(obj).model_dump(mode="json"), message="Created")

    @router.get(
        f"/{entity_name}s/{{item_id}}",
        response_model=dict,
        dependencies=_get_deps,
    )
    async def get_item(
        item_id: UUID,
        session: Annotated[AsyncSession, Depends(get_session)],
        svc_cls=service_cls,
        resp_cls=response_schema,
    ) -> dict:
        svc = svc_cls(session)
        obj = await svc.get_by_id(item_id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity_name} not found")
        return api_response(data=resp_cls.model_validate(obj).model_dump(mode="json"))

    @router.patch(
        f"/{entity_name}s/{{item_id}}",
        response_model=dict,
        dependencies=[Depends(guard_update)],
    )
    async def update_item(
        item_id: UUID,
        body: update_schema,
        session: Annotated[AsyncSession, Depends(get_session)],
        svc_cls=service_cls,
        resp_cls=response_schema,
    ) -> dict:
        svc = svc_cls(session)
        updates = body.model_dump(exclude_unset=True)
        # BaseService.update expects (id, schema), not (id, **kwargs).
        # Construct a minimal schema instance with only the fields to update.
        partial = update_schema(**updates)
        obj = await svc.update(item_id, partial)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity_name} not found")
        return api_response(data=resp_cls.model_validate(obj).model_dump(mode="json"), message="Updated")

    @router.delete(
        f"/{entity_name}s/{{item_id}}",
        response_model=dict,
        dependencies=[Depends(guard_delete)],
    )
    async def delete_item(
        item_id: UUID,
        session: Annotated[AsyncSession, Depends(get_session)],
        svc_cls=service_cls,
    ) -> dict:
        svc = svc_cls(session)
        ok = await svc.soft_delete(item_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{entity_name} not found")
        return api_response(data=None, message="Deleted")


# ============================================================
# Register CRUD routes for each entity
# ============================================================

_make_crud("book", BookService, BookCreate, BookUpdate, BookBrief, BookResponse, public_read=True)
_make_crud("version", VersionService, VersionCreate, VersionUpdate, VersionBrief, VersionResponse, public_read=True)
_make_crud("chapter", ChapterService, ChapterCreate, ChapterUpdate, ChapterBrief, ChapterResponse, public_read=True)
_make_crud("passage", PassageService, PassageCreate, PassageUpdate, PassageBrief, PassageResponse, public_read=True)
_make_crud("paper", PaperService, PaperCreate, PaperUpdate, PaperBrief, PaperResponse)
_make_crud("image", ImageService, ImageCreate, ImageCreate, ImageBrief, ImageResponse)


# ============================================================
# Person & Document — wire existing models to API
# ============================================================

from app.schemas.person import PersonCreate, PersonBrief, PersonResponse  # noqa: E402
from app.schemas.document import DocumentCreate, DocumentBrief, DocumentResponse, DocumentUpdate  # noqa: E402
from app.services.person_service import PersonService  # noqa: E402
from app.services.document_service import DocumentService  # noqa: E402


class _PersonCreateOverride(PersonCreate):
    pass


class _PersonUpdateOverride(PersonCreate):
    pass


class _DocumentUpdateOverride(DocumentUpdate):
    pass


_make_crud("person", PersonService, _PersonCreateOverride, _PersonCreateOverride, PersonBrief, PersonResponse)

# Document is hand-wired (not via _make_crud) because we need extra filter params
# on the list endpoint that the factory doesn't support.

from sqlalchemy import select as sql_select, func  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.document_chunk import DocumentChunk  # noqa: E402
from app.models.academic_evidence import Citation, Evidence  # noqa: E402

document_guard_read = require_permission("document", "read")
document_guard_create = require_permission("document", "create")
document_guard_update = require_permission("document", "update")
document_guard_delete = require_permission("document", "delete")


_document_list_deps: list = [Depends(document_guard_read)]
_document_get_deps: list = [Depends(document_guard_read)]


@router.get(
    "/documents",
    response_model=dict,
    dependencies=_document_list_deps,
)
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    q: str = Query(default="", description="Search query"),
    copyright_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    rag_enabled: bool | None = Query(default=None),
    source_name: str | None = Query(default=None),
    dynasty: str | None = Query(default=None),
    category: str | None = Query(default=None),
) -> dict:
    svc = DocumentService(session)
    items, total = await svc.search(
        q,
        page=page,
        limit=limit,
        copyright_status=copyright_status,
        review_status=review_status,
        rag_enabled=rag_enabled,
        source_name=source_name,
        dynasty=dynasty,
        category=category,
        user_id=user_id,
    )

    results = [DocumentBrief.model_validate(i).model_dump(mode="json") for i in items]
    return api_response(data={"items": results, "total": total})


# Create, get, update, delete — use factory pattern inline
@router.post(
    "/documents",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(document_guard_create)],
)
async def create_document(
    body: DocumentCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    svc = DocumentService(session)
    try:
        create_data = body.model_dump(exclude_unset=False)
        create_data["uploaded_by"] = user_id
        await svc._validate_create(create_data)
        obj = await svc.repo.create(**create_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return api_response(data=DocumentResponse.model_validate(obj).model_dump(mode="json"), message="Created")


@router.get(
    "/documents/{item_id}",
    response_model=dict,
    dependencies=_document_get_deps,
)
async def get_document(
    item_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    svc = DocumentService(session)
    obj = await svc.get_by_id(item_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Ownership check: user can only read docs they own or system/public docs
    if obj.uploaded_by is not None and obj.uploaded_by != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return api_response(data=DocumentResponse.model_validate(obj).model_dump(mode="json"))


@router.patch(
    "/documents/{item_id}",
    response_model=dict,
    dependencies=[Depends(document_guard_update)],
)
async def update_document(
    item_id: UUID,
    body: DocumentUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    svc = DocumentService(session)
    updates = body.model_dump(exclude_unset=True)
    obj = await svc.update(item_id, **updates)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return api_response(data=DocumentResponse.model_validate(obj).model_dump(mode="json"), message="Updated")


@router.delete(
    "/documents/{item_id}",
    response_model=dict,
    dependencies=[Depends(document_guard_delete)],
)
async def delete_document(
    item_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    svc = DocumentService(session)
    ok = await svc.soft_delete(item_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return api_response(data=None, message="Deleted")


@router.get(
    "/documents/{item_id}/stats",
    response_model=dict,
    dependencies=_document_get_deps,
)
async def get_document_stats(
    item_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    """Get citation, evidence, chunk, and OCR stats for a document."""
    doc = await session.get(Document, item_id)
    if doc is None or doc.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Ownership check: user can only read docs they own or system/public docs
    if doc.uploaded_by is not None and doc.uploaded_by != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Total chunks for this document
    chunk_count_q = (
        sql_select(func.count())
        .select_from(DocumentChunk)
        .where(DocumentChunk.document_id == str(item_id))
    )
    total_chunks = (await session.execute(chunk_count_q)).scalar() or 0

    # Chunks with OCR (ocr_confidence IS NOT NULL)
    ocr_chunk_count_q = (
        sql_select(func.count())
        .select_from(DocumentChunk)
        .where(
            DocumentChunk.document_id == str(item_id),
            DocumentChunk.ocr_confidence.is_not(None),
        )
    )
    ocr_chunks = (await session.execute(ocr_chunk_count_q)).scalar() or 0

    # Average OCR confidence
    avg_ocr_q = (
        sql_select(func.avg(DocumentChunk.ocr_confidence))
        .select_from(DocumentChunk)
        .where(
            DocumentChunk.document_id == str(item_id),
            DocumentChunk.ocr_confidence.is_not(None),
        )
    )
    avg_ocr_confidence = (await session.execute(avg_ocr_q)).scalar()

    # Citation count for this document (via chunk citations with target_type='document_chunk' or via passage chain)
    # Count citations where evidence links to a passage that belongs to a chunk of this document
    citation_count_q = (
        sql_select(func.count())
        .select_from(Citation)
        .join(Evidence, Citation.evidence_id == Evidence.id)
        .join(DocumentChunk, Evidence.source_passage_id == DocumentChunk.passage_id)
        .where(DocumentChunk.document_id == str(item_id))
    )
    citation_count = (await session.execute(citation_count_q)).scalar() or 0

    # Evidence count (distinct evidences linked to this document's chunks via source_passage)
    evidence_count_q = (
        sql_select(func.count(func.distinct(Evidence.id)))
        .select_from(Evidence)
        .join(DocumentChunk, Evidence.source_passage_id == DocumentChunk.passage_id)
        .where(DocumentChunk.document_id == str(item_id))
    )
    evidence_count = (await session.execute(evidence_count_q)).scalar() or 0

    return api_response(data={
        "total_chunks": total_chunks,
        "ocr_chunks": ocr_chunks,
        "ocr_text_available": ocr_chunks > 0,
        "avg_ocr_confidence": float(avg_ocr_confidence) if avg_ocr_confidence is not None else None,
        "citation_count": citation_count,
        "evidence_count": evidence_count,
    })
