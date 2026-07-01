"""Academic V2 API routes — Sprint 2 academic product layer."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.schemas.academic import AcademicResponse
from app.services.academic_service import AcademicService
from app.utils.response import api_response

router = APIRouter(prefix="/academic", tags=["Academic V2"])

guard_academic_read = require_permission("ai", "read")


# ---------------------------------------------------------------------------
# 1. Academic Report
# ---------------------------------------------------------------------------


class ReportRequest(BaseModel):
    query: str = Field(..., min_length=1)
    report_type: str = Field(default="research_summary")
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/report", response_model=dict, dependencies=[Depends(guard_academic_read)])
async def academic_report(
    body: ReportRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Generate a citation-grounded academic report."""
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


class SynthesisRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/synthesis", response_model=dict, dependencies=[Depends(guard_academic_read)])
async def academic_synthesis(
    body: SynthesisRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Synthesize knowledge across multiple documents with concept clustering."""
    svc = AcademicService(session)
    result = await svc.synthesize(query=body.query, top_k=body.top_k)
    return api_response(data=result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# 3. Research Assistant
# ---------------------------------------------------------------------------


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/research", response_model=dict, dependencies=[Depends(guard_academic_read)])
async def academic_research(
    body: ResearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Research assistant — decompose question, identify gaps, suggest literature."""
    svc = AcademicService(session)
    result = await svc.research(query=body.query, top_k=body.top_k)
    return api_response(data=result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# 4. Education Mode
# ---------------------------------------------------------------------------


class EducationRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


@router.post("/education", response_model=dict, dependencies=[Depends(guard_academic_read)])
async def academic_education(
    body: EducationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Education mode — citation-backed concept explanations at multiple levels."""
    svc = AcademicService(session)
    result = await svc.educate(query=body.query, top_k=body.top_k)
    return api_response(data=result.model_dump(mode="json"))
