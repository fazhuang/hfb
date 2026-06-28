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
from app.middleware.auth import require_permission
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
):
    """Generate standard CRUD routes for an entity."""

    guard_create = require_permission(entity_name, "create")
    guard_read = require_permission(entity_name, "read")
    guard_update = require_permission(entity_name, "update")
    guard_delete = require_permission(entity_name, "delete")

    @router.get(
        f"/{entity_name}s",
        response_model=dict,
        dependencies=[Depends(guard_read)],
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
        dependencies=[Depends(guard_read)],
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
        obj = await svc.update(item_id, **updates)
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

_make_crud("book", BookService, BookCreate, BookUpdate, BookBrief, BookResponse)
_make_crud("version", VersionService, VersionCreate, VersionUpdate, VersionBrief, VersionResponse)
_make_crud("chapter", ChapterService, ChapterCreate, ChapterUpdate, ChapterBrief, ChapterResponse)
_make_crud("passage", PassageService, PassageCreate, PassageUpdate, PassageBrief, PassageResponse)
_make_crud("paper", PaperService, PaperCreate, PaperUpdate, PaperBrief, PaperResponse)
_make_crud("image", ImageService, ImageCreate, ImageCreate, ImageBrief, ImageResponse)


# ============================================================
# Person & Document — wire existing models to API
# ============================================================

from app.schemas.person import PersonCreate, PersonBrief, PersonResponse  # noqa: E402
from app.schemas.document import DocumentCreate, DocumentBrief, DocumentResponse  # noqa: E402
from app.services.person_service import PersonService  # noqa: E402
from app.services.document_service import DocumentService  # noqa: E402


class _PersonCreateOverride(PersonCreate):
    pass


class _PersonUpdateOverride(PersonCreate):
    pass


class _DocumentCreateOverride(DocumentCreate):
    pass


class _DocumentUpdateOverride(DocumentCreate):
    pass


_make_crud("person", PersonService, _PersonCreateOverride, _PersonCreateOverride, PersonBrief, PersonResponse)
_make_crud("document", DocumentService, _DocumentCreateOverride, _DocumentCreateOverride, DocumentBrief, DocumentResponse)
