"""Academic V2 API routes — Sprint 2 academic product layer (P0 remediated).

P1: Reuses request models from app.schemas.academic (no duplicate loose models).
P1: extra="forbid" on all models, explicit strict response model.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.academic import (
    AcademicEducationRequest,
    AcademicReportRequest,
    AcademicResearchRequest,
    AcademicSynthesisRequest,
)
from app.services.academic_service import AcademicService
from app.utils.response import api_response

router = APIRouter(prefix="/academic", tags=["Academic V2"])

guard_academic_read = require_permission("ai", "read")


# ---------------------------------------------------------------------------
# 1. Academic Report
# ---------------------------------------------------------------------------


@router.post(
    "/report", response_model=dict, dependencies=[Depends(guard_academic_read)]
)
async def academic_report(
    body: AcademicReportRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Generate a citation-grounded academic report. P0-2: reproducibility metadata."""
    svc = AcademicService(session)
    result = await svc.generate_report(
        query=body.query,
        report_type=body.report_type,
        top_k=body.top_k,
    )
    return api_response(data=result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# 2. Knowledge Synthesis
# ---------------------------------------------------------------------------


@router.post(
    "/synthesis", response_model=dict, dependencies=[Depends(guard_academic_read)]
)
async def academic_synthesis(
    body: AcademicSynthesisRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Synthesize knowledge with source-bound claims. P0-3: no manufactured facts."""
    svc = AcademicService(session)
    result = await svc.synthesize(query=body.query, top_k=body.top_k)
    return api_response(data=result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# 3. Research Assistant
# ---------------------------------------------------------------------------


@router.post(
    "/research", response_model=dict, dependencies=[Depends(guard_academic_read)]
)
async def academic_research(
    body: AcademicResearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Research assistant — P0-4: gaps are gaps, hypotheses require evidence."""
    svc = AcademicService(session)
    result = await svc.research(query=body.query, top_k=body.top_k)
    return api_response(data=result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# 4. Education Mode
# ---------------------------------------------------------------------------


@router.post(
    "/education", response_model=dict, dependencies=[Depends(guard_academic_read)]
)
async def academic_education(
    body: AcademicEducationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Education mode — P0-5: extractive presentation only, no invented prose."""
    svc = AcademicService(session)
    result = await svc.educate(query=body.query, top_k=body.top_k)
    return api_response(data=result.model_dump(mode="json"))
