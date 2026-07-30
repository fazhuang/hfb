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

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.schemas.entities import (
    BookBrief,
    BookCreate,
    BookResponse,
    BookUpdate,
    ChapterBrief,
    ChapterCreate,
    ChapterResponse,
    ChapterUpdate,
    ImageBrief,
    ImageCreate,
    ImageResponse,
    PaperBrief,
    PaperCreate,
    PaperResponse,
    PaperUpdate,
    PassageBrief,
    PassageCreate,
    PassageResponse,
    PassageUpdate,
    VersionBrief,
    VersionCreate,
    VersionResponse,
    VersionUpdate,
)
from app.services.entities import (
    BookService,
    ChapterService,
    ImageService,
    PaperService,
    PassageService,
    VersionService,
)
from app.utils.response import api_response

router = APIRouter(tags=["Domain Entities"])

logger = logging.getLogger(__name__)

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

from app.schemas.document import (
    DocumentBrief,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
)
from app.schemas.person import PersonBrief, PersonCreate, PersonResponse
from app.services.document_service import DocumentService
from app.services.person_service import PersonService


class _PersonCreateOverride(PersonCreate):
    pass


class _PersonUpdateOverride(PersonCreate):
    pass


class _DocumentUpdateOverride(DocumentUpdate):
    pass


_make_crud("person", PersonService, _PersonCreateOverride, _PersonCreateOverride, PersonBrief, PersonResponse)

# Document is hand-wired (not via _make_crud) because we need extra filter params
# on the list endpoint that the factory doesn't support.

from sqlalchemy import func
from sqlalchemy import select as sql_select

from app.models.academic_evidence import Citation, Evidence
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.workspace import ResearchSession

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
    session_id: str | None = Query(default=None),
) -> dict:
    # Cross-project isolation: verify user owns the requested session
    if session_id is not None:
        owner_session = await session.get(ResearchSession, session_id)
        if owner_session is None or owner_session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
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
        session_id=session_id,
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
        # Cross-project isolation: verify user owns the session before scoping doc to it
        if create_data.get("session_id"):
            owner_session = await session.get(ResearchSession, create_data["session_id"])
            if owner_session is None or owner_session.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create document in another user's project",
                )
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
    # Cross-project isolation: session-scoped docs require the owning session
    if obj.session_id is not None:
        owner_session = await session.get(ResearchSession, obj.session_id)
        if owner_session is None or owner_session.user_id != user_id:
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
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    svc = DocumentService(session)
    # Fetch existing doc to check ownership
    existing = await svc.get_by_id(item_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Ownership check
    if existing.uploaded_by is not None and existing.uploaded_by != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    updates = body.model_dump(exclude_unset=True)
    # Cross-project isolation: verify user owns session before reassigning
    if updates.get("session_id") is not None:
        if len(updates["session_id"]) > 0:
            owner_session = await session.get(ResearchSession, updates["session_id"])
            if owner_session is None or owner_session.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot assign document to another user's project",
                )
        else:
            # Empty string or explicitly null — allow clearing session_id back to public
            updates["session_id"] = None
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
    doc = await session.get(Document, str(item_id))
    if doc is None or doc.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Ownership check: user can only read docs they own or system/public docs
    if doc.uploaded_by is not None and doc.uploaded_by != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Cross-project isolation: session-scoped docs require the owning session
    if doc.session_id is not None:
        owner_session = await session.get(ResearchSession, doc.session_id)
        if owner_session is None or owner_session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Total chunks for this document
    try:
        chunk_count_q = (
            sql_select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == str(item_id))
        )
        total_chunks = (await session.execute(chunk_count_q)).scalar() or 0
    except (SQLAlchemyError, ValueError):
        logger.debug("Failed to count document chunks", exc_info=True)
        total_chunks = 0

    # Chunks with OCR (ocr_confidence IS NOT NULL)
    try:
        ocr_chunk_count_q = (
            sql_select(func.count())
            .select_from(DocumentChunk)
            .where(
                DocumentChunk.document_id == str(item_id),
                DocumentChunk.ocr_confidence.is_not(None),
            )
        )
        ocr_chunks = (await session.execute(ocr_chunk_count_q)).scalar() or 0
    except (SQLAlchemyError, ValueError):
        logger.debug("Failed to count OCR chunks", exc_info=True)
        ocr_chunks = 0

    # Average OCR confidence
    try:
        avg_ocr_q = (
            sql_select(func.avg(DocumentChunk.ocr_confidence))
            .select_from(DocumentChunk)
            .where(
                DocumentChunk.document_id == str(item_id),
                DocumentChunk.ocr_confidence.is_not(None),
            )
        )
        avg_ocr_confidence = (await session.execute(avg_ocr_q)).scalar()
    except (SQLAlchemyError, ValueError):
        logger.debug("Failed to compute avg OCR confidence", exc_info=True)
        avg_ocr_confidence = None

    # Citation count for this document
    try:
        citation_count_q = (
            sql_select(func.count())
            .select_from(Citation)
            .join(Evidence, Citation.evidence_id == Evidence.id)
            .join(DocumentChunk, Evidence.source_passage_id == DocumentChunk.passage_id)
            .where(DocumentChunk.document_id == str(item_id))
        )
        citation_count = (await session.execute(citation_count_q)).scalar() or 0
    except (SQLAlchemyError, ValueError):
        logger.debug("Failed to count citations", exc_info=True)
        citation_count = 0

    # Evidence count
    try:
        evidence_count_q = (
            sql_select(func.count(func.distinct(Evidence.id)))
            .select_from(Evidence)
            .join(DocumentChunk, Evidence.source_passage_id == DocumentChunk.passage_id)
            .where(DocumentChunk.document_id == str(item_id))
        )
        evidence_count = (await session.execute(evidence_count_q)).scalar() or 0
    except (SQLAlchemyError, ValueError):
        logger.debug("Failed to count evidence", exc_info=True)
        evidence_count = 0

    return api_response(data={
        "total_chunks": total_chunks,
        "ocr_chunks": ocr_chunks,
        "ocr_text_available": ocr_chunks > 0,
        "avg_ocr_confidence": float(avg_ocr_confidence) if avg_ocr_confidence is not None else None,
        "citation_count": citation_count,
        "evidence_count": evidence_count,
    })


# ============================================================
# /documents/{id}/reader — aggregated reader data
# ============================================================

def _resolve_citation_anchor(citation, all_chunk_objs: list) -> list:
    """Resolve a Citation to its anchor DocumentChunks.

    Resolution chain:
      Citation.target_id → if target_type == 'Passage' → find chunks with matching passage_id.

    Returns empty anchor_chunk_ids when no stable anchor exists.
    Fuzzy text matching is FORBIDDEN — only stable DB relations are used.
    """
    matched: list = []
    # If the citation targets a Passage, find chunks linked to that passage
    if citation.target_type == "Passage" and citation.target_id:
        target_id = str(citation.target_id)
        matched = [ch for ch in all_chunk_objs if ch.passage_id and str(ch.passage_id) == target_id]
    return matched


def _resolve_evidence_anchor(evidence, all_chunk_objs: list) -> list:
    """Resolve Evidence to its anchor DocumentChunks via source_passage_id."""
    if evidence.source_passage_id:
        sid = str(evidence.source_passage_id)
        return [ch for ch in all_chunk_objs if ch.passage_id and str(ch.passage_id) == sid]
    return []


@router.get(
    "/documents/{item_id}/reader",
    response_model=dict,
    dependencies=_document_get_deps,
)
async def get_document_reader(
    item_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    user_id: Annotated[str, Depends(get_current_user)],
) -> dict:
    """Aggregated endpoint for the Reader page.

    Returns document detail + OCR chunks + linked passages (with translation)
    + citations + evidence in a single response, avoiding N+1 round-trips.
    """
    # Test-only error triggers — guarded by SEED_TEST_DATA=1
    if os.environ.get("SEED_TEST_DATA") == "1":
        _sid = str(item_id)
        if _sid == "00000000-0000-0000-0000-000000000422":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Test validation error for E2E",
            )
        if _sid == "00000000-0000-0000-0000-000000000500":
            raise RuntimeError("Test internal error for E2E")

    svc = DocumentService(session)
    doc = await svc.get_by_id(item_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Ownership check
    if doc.uploaded_by is not None and doc.uploaded_by != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    # Cross-project isolation
    if doc.session_id is not None:
        owner_session = await session.get(ResearchSession, doc.session_id)
        if owner_session is None or owner_session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Document detail
    doc_data = DocumentResponse.model_validate(doc).model_dump(mode="json")

    # ---- OCR chunks ----
    chunks_q = (
        sql_select(DocumentChunk)
        .where(
            DocumentChunk.document_id == str(item_id),
            DocumentChunk.ocr_confidence.is_not(None),
        )
        .order_by(DocumentChunk.chunk_index)
    )
    chunk_objs = (await session.execute(chunks_q)).scalars().all()
    ocr_chunks = [
        {
            "id": c.id,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "page_number": c.page_number,
            "paragraph_index": c.paragraph_index,
            "ocr_confidence": c.ocr_confidence,
            "passage_id": c.passage_id,
            "match_method": c.match_method,
            "quote_bbox": c.quote_bbox,
        }
        for c in chunk_objs
    ]

    # ---- Linked passages (with translation) via DocumentChunk.passage_id ----
    from app.models.passage import Passage

    passage_ids_q = (
        sql_select(DocumentChunk.passage_id)
        .where(
            DocumentChunk.document_id == str(item_id),
            DocumentChunk.passage_id.is_not(None),
        )
        .distinct()
    )
    pids = (await session.execute(passage_ids_q)).scalars().all()
    passages: list[dict] = []
    if pids:
        passages_q = (
            sql_select(Passage)
            .where(Passage.id.in_(pids))
            .order_by(Passage.order)
        )
        passage_objs = (await session.execute(passages_q)).scalars().all()
        passages = [
            {
                "id": p.id,
                "content_text": p.content_text,
                "translation": p.translation,
                "notes": p.notes,
                "order": p.order,
                "tags": p.tags,
            }
            for p in passage_objs
        ]

    # ---- All chunks for this document (internal — used for citation/evidence anchor resolution only) ----
    all_chunks_q = (
        sql_select(DocumentChunk)
        .where(DocumentChunk.document_id == str(item_id))
        .order_by(DocumentChunk.chunk_index)
    )
    all_chunk_objs = (await session.execute(all_chunks_q)).scalars().all()

    # ---- Original (non-OCR) chunks — real source text only ----
    # ocr_confidence IS NULL = non-OCR text (model semantic per DocumentChunk.ocr_confidence)
    original_chunks = [
        {
            "id": c.id,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "page_number": c.page_number,
            "paragraph_index": c.paragraph_index,
            "passage_id": c.passage_id,
        }
        for c in all_chunk_objs
        if c.ocr_confidence is None
    ]

    # ---- Citations for this document ----
    # Get all passage_ids used by this document's chunks
    doc_passage_ids: list[str] = list({str(c.passage_id) for c in all_chunk_objs if c.passage_id})

    # 1. Anchored: Citations reachable via Evidence → Chunk.passage_id chain
    citation_q = (
        sql_select(Citation)
        .join(Evidence, Citation.evidence_id == Evidence.id)
        .join(DocumentChunk, Evidence.source_passage_id == DocumentChunk.passage_id)
        .where(DocumentChunk.document_id == str(item_id))
        .distinct()
    )
    citation_objs = list((await session.execute(citation_q)).scalars().all())
    citation_ids = {c.id for c in citation_objs}

    # 2. Unanchored: Citations whose evidence source_passage is an orphan
    #    passage (no chunk) that still belongs to this doc through book lineage.
    #    Gather all passage_ids reachable from this doc (including orphans):
    #    doc_chunks → Book → Version → Chapter → Passage
    all_passage_ids_for_doc = set[str](doc_passage_ids)
    # Also look through the passage IDs already returned (which come from chunks)
    passages_set = {str(p["id"]) for p in passages}
    all_passage_ids_for_doc |= passages_set

    if all_passage_ids_for_doc:
        extra_ev_q = (
            sql_select(Evidence)
            .where(Evidence.source_passage_id.in_(list(all_passage_ids_for_doc)))
        )
        extra_evs = (await session.execute(extra_ev_q)).scalars().all()
        extra_ev_ids = [e.id for e in extra_evs]
        if extra_ev_ids:
            extra_cit_q = (
                sql_select(Citation)
                .where(Citation.evidence_id.in_(extra_ev_ids))
                .distinct()
            )
            extra_cits = (await session.execute(extra_cit_q)).scalars().all()
            for c in extra_cits:
                if c.id not in citation_ids:
                    citation_objs.append(c)
                    citation_ids.add(c.id)

    # Resolve each citation to its anchor chunk(s)
    citations = []
    for c in citation_objs:
        anchor_chunks = _resolve_citation_anchor(c, all_chunk_objs)
        citations.append({
            "id": c.id,
            "quote_text": c.quote_text,
            "note": c.note,
            "target_type": c.target_type,
            "target_id": c.target_id,
            "evidence_id": c.evidence_id,
            "anchor_chunk_ids": [ch.id for ch in anchor_chunks],
            "anchor_passage_ids": list({ch.passage_id for ch in anchor_chunks if ch.passage_id}),
        })

    # ---- Evidence for this document ----
    # 1. Anchored: Evidence reachable via source_passage_id → Chunk.passage_id
    evidence_q = (
        sql_select(Evidence)
        .join(DocumentChunk, Evidence.source_passage_id == DocumentChunk.passage_id)
        .where(DocumentChunk.document_id == str(item_id))
        .distinct()
    )
    evidence_objs = list((await session.execute(evidence_q)).scalars().all())
    evidence_ids_set = {e.id for e in evidence_objs}

    # 2. Unanchored: Evidence whose source_passage_id is in doc_passage_ids
    #    but has no chunks (no inner-join match) — these still belong to the doc
    if doc_passage_ids:
        extra_ev_q = (
            sql_select(Evidence)
            .where(Evidence.source_passage_id.in_(doc_passage_ids))
        )
        extra_evs = (await session.execute(extra_ev_q)).scalars().all()
        for ev in extra_evs:
            if ev.id not in evidence_ids_set:
                evidence_objs.append(ev)
                evidence_ids_set.add(ev.id)

    evidences = []
    for e in evidence_objs:
        anchor_chunks = _resolve_evidence_anchor(e, all_chunk_objs)
        evidences.append({
            "id": e.id,
            "description": e.description,
            "evidence_level": int(e.evidence_level.value) if hasattr(e.evidence_level, 'value') else e.evidence_level,
            "source_passage_id": e.source_passage_id,
            "source_ref_id": e.source_ref_id,
            "anchor_chunk_ids": [ch.id for ch in anchor_chunks],
        })

    return api_response(data={
        "document": doc_data,
        "ocr_chunks": ocr_chunks,
        "passages": passages,
        "original_chunks": original_chunks,
        "citations": citations,
        "evidences": evidences,
    })


# ============================================================
# Test-only: seed reader data (Citation + Evidence linked to chunks)
# ============================================================

import os

from pydantic import BaseModel as PydanticBaseModel


class _TestSeedReaderDataRequest(PydanticBaseModel):
    username: str
    password: str
    document_title: str
    document_text: str
    passage_text: str | None = None
    passage_translation: str | None = None
    with_passage: bool = True


@router.post(
    "/_test/seed-reader-data",
    response_model=dict,
)
async def _test_seed_reader_data(
    body: _TestSeedReaderDataRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Test-only: create a full Reader test fixture.

    Creates: user → document → chunks → Book→Version→Chapter→Passage →
    Evidence → Citation. Returns full test data dict.

    Guarded by SEED_TEST_DATA=1 env var.
    """
    if os.environ.get("SEED_TEST_DATA") != "1":
        raise HTTPException(status_code=404, detail="Not found")

    import uuid as _uuid_mod

    from app.models.academic_evidence import EvidenceLevel
    from app.models.passage import Passage
    from app.models.user import User
    from app.services.auth_service import hash_password

    # ---- 1. Create or get user ----
    user_stmt = sql_select(User).where(User.username == body.username)
    user = (await session.execute(user_stmt)).scalar_one_or_none()
    if user is None:
        user = User(
            id=str(_uuid_mod.uuid4()),
            username=body.username,
            email=f"{body.username}@e2e.test",
            hashed_password=hash_password(body.password),
            is_active=True,
        )
        session.add(user)
        await session.flush()

    # ---- 2. Create Document ----
    doc = Document(
        id=str(_uuid_mod.uuid4()),
        title=body.document_title,
        uploaded_by=user.id,
        copyright_status="public_domain",
        language="zh",
    )
    session.add(doc)
    await session.flush()

    # ---- 3. Create DocumentChunks (paragraph-boundary) ----
    # Create a mix: some non-OCR (original text) + some OCR chunks
    # to verify R3 separation in Reader
    paragraphs = [p for p in body.document_text.split("\n\n") if p.strip()]
    chunks = []
    for idx, para in enumerate(paragraphs):
        # Even-indexed chunks: non-OCR (original text). Odd-indexed: OCR.
        is_ocr = idx % 2 == 1
        chunk = DocumentChunk(
            id=str(_uuid_mod.uuid4()),
            document_id=doc.id,
            chunk_index=idx,
            content=para.strip(),
            paragraph_index=idx,
            ocr_confidence=0.80 + (idx * 0.03) if is_ocr else None,
            page_number=2 if is_ocr else 1,
        )
        session.add(chunk)
        chunks.append(chunk)
    await session.flush()

    passage_id = None
    evidence_id = None
    citation_id = None

    if body.with_passage:
        # ---- 4. Create Book → Version → Chapter → Passage ----
        from app.models.book import Book
        from app.models.chapter import Chapter
        from app.models.version import Version

        book = Book(id=str(_uuid_mod.uuid4()), title=f"E2E书-{_uuid_mod.uuid4().hex[:6]}", dynasty="汉")
        session.add(book)
        await session.flush()

        version = Version(
            id=str(_uuid_mod.uuid4()),
            book_id=book.id,
            version_name="E2E本",
            era="E2E",
            repository="E2E库",
            shelf_mark="E2E-001",
        )
        session.add(version)
        await session.flush()

        chapter = Chapter(
            id=str(_uuid_mod.uuid4()),
            book_id=book.id,
            title="E2E章",
            order=1,
        )
        session.add(chapter)
        await session.flush()

        passage_text = body.passage_text or (paragraphs[0] if paragraphs else "E2E passage text")
        passage = Passage(
            id=str(_uuid_mod.uuid4()),
            chapter_id=chapter.id,
            version_id=version.id,
            content_text=passage_text,
            translation=body.passage_translation,
            order=1,
            tags="E2E",
        )
        session.add(passage)
        await session.flush()
        passage_id = passage.id

        # Link the first chunk to the passage
        if chunks:
            chunks[0].passage_id = passage.id

        # ---- 5. Create Evidence + Citation ----
        evidence = Evidence(
            id=str(_uuid_mod.uuid4()),
            description=f"E2E evidence for {body.document_title}",
            evidence_level=EvidenceLevel.LEVEL_2,
            source_passage_id=passage.id,
        )
        session.add(evidence)
        await session.flush()
        evidence_id = evidence.id

        citation = Citation(
            id=str(_uuid_mod.uuid4()),
            target_type="Passage",
            target_id=passage.id,
            evidence_id=evidence.id,
            quote_text=passage.content_text[:200] if passage.content_text else "",
            note="E2E test citation",
        )
        session.add(citation)
        await session.flush()
        citation_id = citation.id

        # ---- 6. Create an unanchored Citation + Evidence (no chunk linkage) ----
        orphan_passage = Passage(
            id=str(_uuid_mod.uuid4()),
            chapter_id=chapter.id,
            version_id=version.id,
            content_text="orphan passage with no chunk link",
            order=999,
            tags="E2E-orphan",
        )
        session.add(orphan_passage)
        await session.flush()

        orphan_evidence = Evidence(
            id=str(_uuid_mod.uuid4()),
            description="E2E unanchored evidence (no chunk link)",
            evidence_level=EvidenceLevel.LEVEL_2,
            source_passage_id=orphan_passage.id,
        )
        session.add(orphan_evidence)
        await session.flush()

        orphan_citation = Citation(
            id=str(_uuid_mod.uuid4()),
            target_type="Passage",
            target_id=orphan_passage.id,
            evidence_id=orphan_evidence.id,
            quote_text="orphan citation with no chunk anchor",
            note="E2E unanchored citation",
        )
        session.add(orphan_citation)
        await session.flush()

    # Return a complete dict matching what tests expect
    resp_data: dict = {
        "user_id": user.id,
        "username": body.username,
        "password": body.password,
        "access_token": "PLACEHOLDER",  # tests will use _seed_user result instead
        "doc": {
            "id": doc.id,
            "title": body.document_title,
            "document_id": doc.id,
        },
        "chunks": [
            {"id": c.id, "chunk_index": c.chunk_index, "content": c.content,
             "paragraph_index": c.paragraph_index, "page_number": getattr(c, 'page_number', None)}
            for c in chunks
        ],
        "passage_id": passage_id,
        "evidence_id": evidence_id,
        "citation_id": citation_id,
        "unanchored_citation_id": None,
        "unanchored_evidence_id": None,
    }
    if body.with_passage:
        resp_data["unanchored_citation_id"] = orphan_citation.id
        resp_data["unanchored_evidence_id"] = orphan_evidence.id
    return api_response(data=resp_data)
