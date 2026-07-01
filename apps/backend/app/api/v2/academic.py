"""Academic V2 API routes — Sprint 2 academic product layer (deep-fix).

P1-1: Strict response_model replacing dict. extra="forbid" at all levels.
P1: Reuses request models from app.schemas.academic.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.academic import (
    AcademicEducationRequest,
    AcademicReportRequest,
    AcademicResearchRequest,
    AcademicResponse,
    AcademicSynthesisRequest,
)
from app.services.academic_service import AcademicService

router = APIRouter(prefix="/academic", tags=["Academic V2"])

guard_academic_read = require_permission("ai", "read")


# ======================================================================
# P1-1: Strict API envelope — NOT dict
# ======================================================================


class AcademicApiEnvelope(BaseModel):
    """Strict API response envelope matching api_response() shape.

    P1-1: All levels use extra="forbid". No additionalProperties: true.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    success: bool = Field(default=True)
    data: AcademicResponse
    message: str = Field(default="ok")


# ---------------------------------------------------------------------------
# 1. Academic Report
# ---------------------------------------------------------------------------


@router.post(
    "/report",
    response_model=AcademicApiEnvelope,
    dependencies=[Depends(guard_academic_read)],
)
async def academic_report(
    body: AcademicReportRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AcademicApiEnvelope:
    """Generate a citation-grounded academic report."""
    svc = AcademicService(session)
    result = await svc.generate_report(
        query=body.query, report_type=body.report_type, top_k=body.top_k
    )
    return AcademicApiEnvelope(success=True, data=result, message="ok")


# ---------------------------------------------------------------------------
# 2. Knowledge Synthesis
# ---------------------------------------------------------------------------


@router.post(
    "/synthesis",
    response_model=AcademicApiEnvelope,
    dependencies=[Depends(guard_academic_read)],
)
async def academic_synthesis(
    body: AcademicSynthesisRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AcademicApiEnvelope:
    """Synthesize knowledge with source-bound claims."""
    svc = AcademicService(session)
    result = await svc.synthesize(query=body.query, top_k=body.top_k)
    return AcademicApiEnvelope(success=True, data=result, message="ok")


# ---------------------------------------------------------------------------
# 3. Research Assistant
# ---------------------------------------------------------------------------


@router.post(
    "/research",
    response_model=AcademicApiEnvelope,
    dependencies=[Depends(guard_academic_read)],
)
async def academic_research(
    body: AcademicResearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AcademicApiEnvelope:
    """Research assistant — gate-first, gap ≠ hypothesis."""
    svc = AcademicService(session)
    result = await svc.research(query=body.query, top_k=body.top_k)
    return AcademicApiEnvelope(success=True, data=result, message="ok")


# ---------------------------------------------------------------------------
# 4. Education Mode
# ---------------------------------------------------------------------------


@router.post(
    "/education",
    response_model=AcademicApiEnvelope,
    dependencies=[Depends(guard_academic_read)],
)
async def academic_education(
    body: AcademicEducationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AcademicApiEnvelope:
    """Education mode — extractive, rank-based difficulty."""
    svc = AcademicService(session)
    result = await svc.educate(query=body.query, top_k=body.top_k)
    return AcademicApiEnvelope(success=True, data=result, message="ok")
