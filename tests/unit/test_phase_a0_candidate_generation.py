"""Phase A0 — candidate generation service tests (AI + rule fallback)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.candidate_create_uow import CandidateCreateUnitOfWork
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.services.ai_service import AIService
from app.services.candidate_generation import CandidateGenerationService

from tests.conftest_db import db_session  # noqa: F401
from tests.unit.test_phase_a0_candidate_pipeline import (
    CANON,
    EXACT,
    OWNER_ID,
    build_world,
)

GOLD_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "gold_benchmark_v03.json"
GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def _make_service(session: AsyncSession, ai: AIService) -> CandidateGenerationService:
    factory = async_sessionmaker(
        session.bind, class_=AsyncSession, expire_on_commit=False
    )
    return CandidateGenerationService(
        factory, ai, CandidateCreateUnitOfWork(factory)
    )


class _FakeAI:
    """Fake AIService that always returns a valid JSON extraction."""

    available = True
    last_prompt: str | None = None

    async def complete_structured(self, **kwargs: object) -> str:
        self.last_prompt = str(kwargs.get("system_prompt", ""))
        return json.dumps(
            {
                "description": "卷三腧穴定位证据（AI 抽取）",
                "evidence_level": 3,
                "quote_text": EXACT,
                "note": "generation test",
            },
            ensure_ascii=False,
        )


class TestCandidateGeneration:
    @pytest.mark.asyncio
    async def test_rule_fallback_generates_pending_candidate(
        self, db_session: AsyncSession
    ) -> None:
        await build_world(db_session)
        await db_session.commit()

        # No API key configured → available=False → rule fallback.
        ai = AIService()
        service = _make_service(db_session, ai)

        created = await service.generate("sess-a0", "chunk-a0", "ver-a0", OWNER_ID)

        assert created.status == CandidateStatus.PENDING
        assert created.ai_model == "rule-fallback-extractor"
        assert created.exact_text == CANON[:80]

        async with db_session as session:
            cand = await session.get(CandidateExtraction, created.id)
            assert cand.status == CandidateStatus.PENDING

    @pytest.mark.asyncio
    async def test_ai_path_locates_verbatim_quote(
        self, db_session: AsyncSession
    ) -> None:
        await build_world(db_session)
        await db_session.commit()

        fake = _FakeAI()
        service = _make_service(db_session, fake)  # type: ignore[arg-type]

        created = await service.generate("sess-a0", "chunk-a0", "ver-a0", OWNER_ID)

        assert created.ai_model != "rule-fallback-extractor"
        assert created.exact_text == EXACT
        assert created.start_char == 0
        assert created.end_char == len(EXACT)
        payload = created.extracted_payload
        assert payload["description"] == "卷三腧穴定位证据（AI 抽取）"

    @pytest.mark.asyncio
    async def test_ai_quote_not_verbatim_falls_back_to_prefix(
        self, db_session: AsyncSession
    ) -> None:
        await build_world(db_session)
        await db_session.commit()

        class _BadQuoteAI(_FakeAI):
            async def complete_structured(self, **kwargs: object) -> str:
                return json.dumps(
                    {
                        "description": "x",
                        "evidence_level": 3,
                        "quote_text": "这段不在原文里",
                        "note": None,
                    },
                    ensure_ascii=False,
                )

        service = _make_service(db_session, _BadQuoteAI())  # type: ignore[arg-type]
        created = await service.generate("sess-a0", "chunk-a0", "ver-a0", OWNER_ID)

        # Non-verbatim quote is discarded; span falls back to the prefix.
        assert created.exact_text == CANON[:80]
        assert created.start_char == 0

    @pytest.mark.asyncio
    async def test_generate_cross_session_404(self, db_session: AsyncSession) -> None:
        await build_world(db_session)
        await db_session.commit()

        service = _make_service(db_session, AIService())

        from app.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await service.generate("other-session", "chunk-a0", "ver-a0", OWNER_ID)
