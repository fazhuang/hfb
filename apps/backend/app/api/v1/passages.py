"""Passage detail API — eager-load sentences, tokens, and variants.

Per academic_implementation_manual.md Step 3.1.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.models.passage import Passage

router = APIRouter(tags=["Passages"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class _TokenBrief(BaseModel):
    """Minimal token representation to avoid recursion on base_token/compare_token."""

    model_config = ConfigDict(from_attributes=True)
    id: str
    char_text: str
    position: int


class _VariantBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    base_token_id: str
    compare_token_id: str | None = None
    variant_type: str
    description: str | None = None
    base_token: _TokenBrief | None = None
    compare_token: _TokenBrief | None = None


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    char_text: str
    position: int
    variants_as_base: list[_VariantBrief] = Field(default_factory=list)
    variants_as_compare: list[_VariantBrief] = Field(default_factory=list)


class SentenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    content_text: str
    order: int
    tokens: list[TokenResponse] = Field(default_factory=list)


class PassageDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    chapter_id: str
    version_id: str | None = None
    content_text: str
    translation: str | None = None
    notes: str | None = None
    order: int
    tags: str | None = None
    sentences: list[SentenceResponse] = Field(default_factory=list)


@router.get(
    "/passages/{passage_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("passage", "read"))],
)
async def get_passage_detail(
    passage_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Get passage with fully eager-loaded sentences, tokens and variants."""
    from app.models.version_criticism import Sentence, Token, Variant
    from app.utils.response import api_response

    stmt = (
        select(Passage)
        .options(
            selectinload(Passage.sentences)
            .selectinload(Sentence.tokens)
            .selectinload(Token.variants_as_base)
            .selectinload(Variant.compare_token),
        )
        .options(
            selectinload(Passage.sentences)
            .selectinload(Sentence.tokens)
            .selectinload(Token.variants_as_compare)
            .selectinload(Variant.base_token),
        )
        .where(Passage.id == passage_id, Passage.is_deleted.is_(False))
    )

    result = await session.execute(stmt)
    passage = result.scalar_one_or_none()

    if passage is None:
        raise HTTPException(status_code=404, detail="Passage not found")

    detail = PassageDetailResponse.model_validate(passage)
    return api_response(data=detail.model_dump(mode="json"))
