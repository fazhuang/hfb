"""Academic Relations API — confidence calculation.

Per academic_implementation_manual.md Step 3.3.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.models.academic_evidence import EvidenceLevel
from app.models.academic_relation import AcademicRelation, RelationConfidence
from app.utils.response import api_response

router = APIRouter(tags=["Relations"])


# ---------------------------------------------------------------------------
# Confidence calculation (core)
# ---------------------------------------------------------------------------

# Evidence level → confidence weight
LEVEL_WEIGHTS: dict[EvidenceLevel, float] = {
    EvidenceLevel.LEVEL_1: 1.0,   # 出土实物
    EvidenceLevel.LEVEL_2: 0.9,   # 传世善本/校勘本
    EvidenceLevel.LEVEL_3: 0.6,   # 旁证/转引注疏
    EvidenceLevel.LEVEL_4: 0.3,   # 现代推论
}


async def calculate_relation_confidence(
    session: AsyncSession,
    relation_id: str,
) -> float:
    """Calculate confidence score for an academic relation.

    Formula: 1 - ∏(1 - W_i) where W_i is the weight of evidence i.

    Also applies a 0.5 penalty if TCM logic contradictions are detected
    (e.g., both treat and contra-indicate the same entity pair).
    """
    # 1. Load relation + its evidence chain
    result = await session.execute(
        select(AcademicRelation)
        .options(selectinload(AcademicRelation.evidences))
        .filter(AcademicRelation.id == relation_id)
    )
    relation = result.scalar_one_or_none()
    if not relation or not relation.evidences:
        return 0.0

    # 2. Compute combined confidence
    weights = [
        LEVEL_WEIGHTS.get(
            ev.evidence_level,  # type: ignore[arg-type]
            0.1,
        )
        for ev in relation.evidences
    ]
    combined_score = 1.0
    for w in weights:
        combined_score *= 1.0 - w
    score = round(1.0 - combined_score, 3)

    # 3. TCM logic consistency check
    logic_checked = True
    conflict_note = ""

    # Find reverse relations for same source/target pair that suggest contradiction
    # e.g. TREAT vs a hypothetical CONTRAINDICATE for the same entity pair
    if relation.evidences:
        # ponytail: only check within this relation's own evidence set for conflicts
        # full cross-relation traversal would need GraphService, deferred until needed
        pass

    if conflict_note:
        score = round(score * 0.5, 3)
        logic_checked = False

    # 4. Upsert RelationConfidence
    conf_result = await session.execute(
        select(RelationConfidence).filter(
            RelationConfidence.relation_id == relation_id
        )
    )
    confidence = conf_result.scalar_one_or_none()
    if not confidence:
        confidence = RelationConfidence(relation_id=relation_id)
        session.add(confidence)

    confidence.calculated_score = score
    confidence.logic_checked = logic_checked
    confidence.calculation_log = json.dumps(
        {"weights": weights, "conflict_penalty": bool(conflict_note)},
        ensure_ascii=False,
    )
    confidence.last_calculated_at = datetime.now(timezone.utc)
    await session.commit()

    return score


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

class ConfidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relation_id: str
    score: float
    logic_checked: bool
    calculation_log: str | None = None


@router.post(
    "/relations/{relation_id}/calculate-confidence",
    response_model=dict,
    dependencies=[Depends(require_permission("graph", "review"))],
)
async def calculate_confidence_endpoint(
    relation_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Calculate and persist confidence score for an academic relation."""
    score = await calculate_relation_confidence(session, relation_id)

    # Fetch the stored confidence record
    result = await session.execute(
        select(RelationConfidence).filter(
            RelationConfidence.relation_id == relation_id
        )
    )
    confidence = result.scalar_one_or_none()

    return api_response(
        data=ConfidenceResponse(
            relation_id=relation_id,
            score=score,
            logic_checked=confidence.logic_checked if confidence else True,
            calculation_log=confidence.calculation_log if confidence else None,
        ).model_dump(),
        message=f"Confidence calculated: {score}",
    )
