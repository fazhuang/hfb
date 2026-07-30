"""Academic Evidence API routes.

Per academic_implementation_manual.md Step 3.2.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.models.academic_evidence import Evidence, EvidenceLevel, SourceRef
from app.utils.response import api_response

router = APIRouter(tags=["Evidences"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SourceRefPayload(BaseModel):
    """Optional SourceRef payload embedded in evidence creation."""

    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., max_length=500)
    author: str | None = Field(default=None, max_length=200)
    edition_info: str | None = Field(default=None, max_length=500)
    page_location: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=1000)


class EvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(...)
    evidence_level: str = Field(..., description="LEVEL_1 | LEVEL_2 | LEVEL_3 | LEVEL_4")
    source_ref: SourceRefPayload | None = None
    source_passage_id: str | None = None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    description: str
    evidence_level: str
    source_ref_id: str | None = None
    source_passage_id: str | None = None
    creator_id: str | None = None


@router.post(
    "/evidences",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("evidence", "create"))],
)
async def create_evidence(
    body: EvidenceCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Create an academic evidence record, optionally with a SourceRef."""
    source_ref_id: str | None = None

    # 1. Create SourceRef if provided
    if body.source_ref:
        ref = SourceRef(
            title=body.source_ref.title,
            author=body.source_ref.author,
            edition_info=body.source_ref.edition_info,
            page_location=body.source_ref.page_location,
            url=body.source_ref.url,
        )
        session.add(ref)
        await session.flush()
        source_ref_id = ref.id

    # 2. Validate evidence_level
    try:
        level = EvidenceLevel[body.evidence_level]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid evidence_level: {body.evidence_level}. Must be LEVEL_1, LEVEL_2, LEVEL_3, or LEVEL_4.",
        )

    # 3. Validate source_passage exists if provided
    if body.source_passage_id:
        from sqlalchemy import select as _select

        from app.models.passage import Passage

        pass_stmt = _select(Passage).where(
            Passage.id == body.source_passage_id,
            Passage.is_deleted.is_(False),
        )
        pass_result = await session.execute(pass_stmt)
        if pass_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Passage {body.source_passage_id} not found",
            )

    # 4. Create Evidence
    evidence = Evidence(
        description=body.description,
        evidence_level=level,
        source_ref_id=source_ref_id,
        source_passage_id=body.source_passage_id,
    )
    session.add(evidence)
    await session.flush()
    await session.refresh(evidence)

    return api_response(
        data=EvidenceResponse.model_validate(evidence).model_dump(mode="json"),
        message="Evidence created",
    )
