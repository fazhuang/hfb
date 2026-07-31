"""TEI V2 API routes — Phase 2b commentary, version_tree, variants."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.commentary import (
    CommentaryChainResponse,
    CommentaryCreate,
    CommentaryEnvelope,
    CommentaryGraphResponse,
)
from app.services.version_center import (
    compute_version_tree,
    create_commentary,
    get_commentaries_for_passage,
    get_commentary_chain,
    get_commentary_graph,
)

router = APIRouter(prefix="/tei", tags=["TEI V2"])

guard_tei_read = require_permission("ai", "read")
guard_tei_write = require_permission("graph", "review")


class VersionTreeEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    success: bool = Field(default=True)
    data: dict = Field(default_factory=dict)
    message: str = Field(default="ok")


@router.get(
    "/passage/{passage_id}/commentaries",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def passage_commentaries(
    passage_id: str,
    layer: Annotated[str | None, Query(description="年代层过滤")] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> CommentaryEnvelope:
    """Get all commentaries for a passage, optionally by layer."""
    result = await get_commentaries_for_passage(session, passage_id, layer=layer)
    return CommentaryEnvelope(success=True, data=result, message="ok")


@router.get(
    "/commentary/{commentary_id}/chain",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def commentary_chain(
    commentary_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Trace full commentary chain from root to this commentary."""
    chain = await get_commentary_chain(session, commentary_id)
    return CommentaryEnvelope(
        success=True,
        data=CommentaryChainResponse(chain=chain, depth=len(chain)),
        message="ok",
    )


@router.post(
    "/commentary",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_write)],
)
async def create_commentary_endpoint(
    body: CommentaryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Create a new commentary annotation."""
    result = await create_commentary(session, body)
    return CommentaryEnvelope(success=True, data=result, message="ok")


@router.get(
    "/commentary-graph",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def commentary_graph(
    passage_id: Annotated[str, Query(description="段落 ID")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Get the commentary debate/supplement graph for a passage."""
    graph = await get_commentary_graph(session, passage_id)
    return CommentaryEnvelope(
        success=True,
        data=CommentaryGraphResponse(nodes=graph["nodes"], edges=graph["edges"]),
        message="ok",
    )


# ---------------------------------------------------------------------------
# Phase 2b: Version Tree, Variants & Apparatus
# ---------------------------------------------------------------------------


@router.get(
    "/version-tree/{version_id}",
    response_model=VersionTreeEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def version_tree(
    version_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionTreeEnvelope:
    """Get version lineage tree, distance matrix, and divergence points."""
    data = await compute_version_tree(session, version_id)
    return VersionTreeEnvelope(success=True, data=data, message="ok")


@router.get(
    "/passage/{passage_id}/variants",
    response_model=VersionTreeEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def passage_variants(
    passage_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionTreeEnvelope:
    """Get all variants for a passage across all versions, grouped by apparatus."""
    from app.models.tei import TextualVariant

    stmt = select(TextualVariant).where(
        (
            (TextualVariant.source_passage_id == passage_id)
            | (TextualVariant.target_passage_id == passage_id)
        ),
        TextualVariant.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    variants = result.scalars().all()

    groups: dict[str, list] = defaultdict(list)
    for v in variants:
        key = v.lemma or v.location or "unknown"
        groups[key].append(
            {
                "id": v.id,
                "source_version_id": v.source_version_id,
                "target_version_id": v.target_version_id,
                "lemma": v.lemma,
                "reading": v.reading,
                "variant_type": v.variant_type,
                "apparatus": v.apparatus,
                "verification_status": v.verification_status,
            }
        )
    data = {"passage_id": passage_id, "groups": dict(groups)}
    return VersionTreeEnvelope(success=True, data=data, message="ok")


@router.get(
    "/version/{source_id}/variants",
    response_model=VersionTreeEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def version_variants(
    source_id: str,
    target_version: Annotated[str | None, Query(description="目标版本 ID")] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> VersionTreeEnvelope:
    """Get all variants between a source version and optionally a target version."""
    from app.models.tei import TextualVariant

    stmt = select(TextualVariant).where(
        TextualVariant.source_version_id == source_id,
        TextualVariant.is_deleted.is_(False),
    )
    if target_version:
        stmt = stmt.where(TextualVariant.target_version_id == target_version)
    result = await session.execute(stmt)
    variants = result.scalars().all()
    data = {
        "source_version_id": source_id,
        "target_version_id": target_version,
        "variant_count": len(variants),
        "variants": [
            {
                "id": v.id,
                "target_version_id": v.target_version_id,
                "passage_id": v.source_passage_id or v.target_passage_id,
                "lemma": v.lemma,
                "reading": v.reading,
                "variant_type": v.variant_type,
                "apparatus": v.apparatus,
            }
            for v in variants
        ],
    }
    return VersionTreeEnvelope(success=True, data=data, message="ok")


@router.get(
    "/apparatus",
    response_model=VersionTreeEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def tei_apparatus(
    passage_id: Annotated[str, Query(description="段落 ID")],
    source_version: Annotated[str, Query(description="源版本 ID")],
    target_version: Annotated[str, Query(description="目标版本 ID")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VersionTreeEnvelope:
    """Generate TEI XML critical apparatus for a passage between two versions."""
    from app.models.passage import Passage
    from app.models.tei import TextualVariant

    stmt = select(TextualVariant).where(
        (
            (TextualVariant.source_version_id == source_version)
            & (TextualVariant.target_version_id == target_version)
        )
        | (
            (TextualVariant.source_version_id == target_version)
            & (TextualVariant.target_version_id == source_version)
        ),
        (
            (TextualVariant.source_passage_id == passage_id)
            | (TextualVariant.target_passage_id == passage_id)
        ),
        TextualVariant.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    variants = result.scalars().all()

    # All version IDs are UUIDs — structurally cannot contain quotes or markup.
    # Defense-in-depth: reject anything not matching the UUID pattern.
    import re as _re

    if not _re.match(r"^[0-9a-f-]{36}$", source_version) or not _re.match(
        r"^[0-9a-f-]{36}$", target_version
    ):
        raise HTTPException(status_code=400, detail="Invalid version ID format")

    pass_stmt = select(Passage).where(
        Passage.id == passage_id, Passage.is_deleted.is_(False)
    )
    pass_result = await session.execute(pass_stmt)
    _passage = (
        pass_result.scalar_one_or_none()
    )  # ponytail: fetch for existence, text not needed for XML

    from xml.sax.saxutils import escape

    apps_xml = ""
    for v in variants:
        lemma = escape(v.lemma or "")
        reading = escape(v.reading or "")
        apps_xml += f'<app><lem wit="#{escape(source_version)}">{lemma}</lem><rdg wit="#{escape(target_version)}">{reading}</rdg></app>\n'

    tei_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<TEI xmlns="http://www.tei-c.org/ns/1.0">\n<text>\n<body>\n<div type="apparatus">\n{apps_xml}</div>\n</body>\n</text>\n</TEI>'

    data = {
        "passage_id": passage_id,
        "source_version_id": source_version,
        "target_version_id": target_version,
        "tei_xml": tei_xml,
        "variant_count": len(variants),
    }
    return VersionTreeEnvelope(success=True, data=data, message="ok")
