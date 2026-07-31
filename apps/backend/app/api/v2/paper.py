"""Paper V2 API routes — Phase 2c structured academic paper generation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.services.paper_service import PaperService

router = APIRouter(prefix="/paper", tags=["Paper V2"])

guard_paper_read = require_permission("ai", "read")


class PaperGenerateRequest(BaseModel):
    """Request to generate a structured academic paper."""

    model_config = ConfigDict(extra="forbid", strict=True)

    source_type: str = Field(..., description="起始实体类型")
    source_id: str = Field(..., description="起始实体 ID")
    target_type: str | None = Field(default=None, description="目标实体类型（可选）")
    target_id: str | None = Field(default=None, description="目标实体 ID（可选）")
    min_evidence_level: int = Field(default=2, ge=2, le=4, description="最低证据等级")
    max_hops: int = Field(default=5, ge=1, le=10, description="最大跳数")
    relation_types: list[str] | None = Field(default=None, description="过滤关系类型")


class PaperEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    success: bool = Field(default=True)
    data: dict = Field(default_factory=dict)
    message: str = Field(default="ok")


# In-memory cache for generated papers (by paper_id / sha256)
_paper_cache: dict[str, dict] = {}


@router.post(
    "/generate",
    response_model=PaperEnvelope,
    dependencies=[Depends(guard_paper_read)],
)
async def generate_paper(
    body: PaperGenerateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaperEnvelope:
    """Generate a structured academic paper from KG + TEI evidence."""
    svc = PaperService(session)
    paper = await svc.generate_paper(
        source_type=body.source_type,
        source_id=body.source_id,
        target_type=body.target_type,
        target_id=body.target_id,
        min_evidence_level=body.min_evidence_level,
        max_hops=body.max_hops,
        relation_types=body.relation_types,
    )
    # Cache for retrieval
    _paper_cache[paper["paper_id"]] = paper
    return PaperEnvelope(success=True, data=paper, message="ok")


@router.get(
    "/{paper_id}",
    response_model=PaperEnvelope,
    dependencies=[Depends(guard_paper_read)],
)
async def get_paper(
    paper_id: str,
) -> PaperEnvelope:
    """Retrieve a previously generated paper by its SHA-256 ID."""
    paper = _paper_cache.get(paper_id)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found. Generate it first via POST /generate.",
        )
    return PaperEnvelope(success=True, data=paper, message="ok")


@router.get(
    "/{paper_id}/markdown",
    response_model=PaperEnvelope,
    dependencies=[Depends(guard_paper_read)],
)
async def get_paper_markdown(
    paper_id: str,
) -> PaperEnvelope:
    """Download a generated paper as Markdown."""
    paper = _paper_cache.get(paper_id)
    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found. Generate it first via POST /generate.",
        )
    return PaperEnvelope(
        success=True,
        data={"paper_id": paper_id, "markdown": paper.get("markdown", "")},
        message="ok",
    )
