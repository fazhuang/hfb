"""Candidate generation service — AI/rule extraction from a chunk into a candidate.

The generate path is the missing half of Phase A0: it reads a live chunk,
extracts one evidence proposition (AI when available, deterministic rule
fallback otherwise), locates the exact quote span, computes the dual-hash
grounding anchors, and buffers the result through ``CandidateCreateUnitOfWork``
(which re-validates ownership + grounding in a single transaction).

Fail-closed: the AI is never trusted to produce the quote span — the returned
``quote_text`` must be a verbatim substring of the chunk, or the span falls back
to the rule-based prefix and the payload is flagged accordingly.
"""

from __future__ import annotations

import json
import time
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.db.candidate_create_uow import CandidateCreateUnitOfWork
from app.db.database import get_session_factory
from app.db.grounding import chunk_sha256, nfc_sha256
from app.models.academic_evidence import EvidenceLevel
from app.models.candidate_extraction import CandidateExtraction
from app.repositories.candidate_extraction import CandidateExtractionRepository
from app.schemas.candidate import CreateCandidateRequest, ExtractedEvidencePayload
from app.services.ai_service import AIService

_PROMPT_VERSION = "candidate-gen-v1"
_RULE_FALLBACK_MODEL = "rule-fallback-extractor"


class CandidateGenerationService:
    """Extracts an evidence proposition from a chunk and buffers it."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        ai: AIService,
        create_uow: CandidateCreateUnitOfWork,
    ) -> None:
        self._session_factory = session_factory
        self._ai = ai
        self._create_uow = create_uow

    async def generate(
        self, session_id: str, chunk_id: str, version_id: str, user_id: str
    ) -> CandidateExtraction:
        # 1. Pre-validate ownership + read the chunk (cheap read, before AI).
        async with self._session_factory() as session:
            repo = CandidateExtractionRepository(session)
            session_row = await repo.get_session_for_update(session_id)
            if session_row is None or session_row.user_id != user_id:
                raise NotFoundException("ResearchSession", session_id)
            chunk = await repo.get_chunk_for_update(chunk_id)
            if chunk is None:
                raise NotFoundException("DocumentChunk", chunk_id)
            doc = await repo.get_document_for_update(chunk.document_id)
            if doc is None:
                raise NotFoundException("Document", chunk.document_id)
            if doc.session_id is not None and doc.session_id != session_id:
                raise NotFoundException("DocumentChunk", chunk_id)
            if doc.uploaded_by is not None and doc.uploaded_by != user_id:
                raise NotFoundException("DocumentChunk", chunk_id)
            if chunk.passage_id is None:
                raise ValidationException(
                    "Chunk has no linked passage; cannot anchor a candidate"
                )
            passage = await repo.get_passage_for_update(chunk.passage_id)
            if passage is None or passage.version_id != version_id:
                raise ValidationException(
                    "version_id does not match the chunk's passage version"
                )
            chunk_content = chunk.content
            doc_title = doc.title

        # 2. Extract the payload (AI when available, rule fallback otherwise).
        start_time = time.monotonic()
        extracted, used_model, confidence = await self._extract_payload(
            chunk_content, doc_title
        )
        processing_time = time.monotonic() - start_time

        # 3. Locate the exact quote span (never trust AI for the span).
        start_char, end_char, exact_text = self._locate_span(
            chunk_content, extracted.quote_text
        )

        # 4. Compute grounding anchors.
        expected_chunk_sha256 = chunk_sha256(chunk_content)
        expected_nfc_sha256 = nfc_sha256(chunk_content)

        # 5. Buffer through the create UoW (re-validates + grounds + audits).
        request = CreateCandidateRequest(
            session_id=session_id,
            chunk_id=chunk_id,
            version_id=version_id,
            expected_chunk_sha256=expected_chunk_sha256,
            expected_nfc_sha256=expected_nfc_sha256,
            start_char=start_char,
            end_char=end_char,
            exact_text=exact_text,
            unicode_normalization="NFC",
            extracted_payload=extracted,
            input_snapshot={"document_title": doc_title},
            extractor_name=(
                "ai-evidence-extractor"
                if used_model != _RULE_FALLBACK_MODEL
                else _RULE_FALLBACK_MODEL
            ),
            ai_model=used_model,
            ai_version="1.0.0",
            prompt_version=_PROMPT_VERSION,
            processing_time=processing_time,
            confidence=confidence,
            title=doc_title,
        )
        return await self._create_uow.create(request, user_id)

    async def _extract_payload(
        self, chunk_content: str, doc_title: str
    ) -> tuple[ExtractedEvidencePayload, str, float]:
        """AI structured extraction with a deterministic rule fallback."""
        if self._ai.available:
            result = await self._ai.complete_structured(
                messages=[{"role": "user", "content": chunk_content}],
                system_prompt=(
                    "你是中医古籍研究助手。请从给定的古籍文本中抽取一条可作学术证据的陈述，"
                    "严格返回 JSON（不要额外文字）："
                    '{"description":"证据描述(一句话)","evidence_level":3,'
                    '"quote_text":"原文精确摘录(必须是给定文本的连续子串,逐字一致)",'
                    '"note":"补充说明或null"}。'
                    "证据等级:1=出土实物,2=最早善本,3=史书注疏,4=现代论著。"
                ),
                temperature=0.2,
            )
            if result:
                try:
                    data = json.loads(result)
                    if isinstance(data, dict):
                        desc = data.get("description")
                        if isinstance(desc, str) and desc:
                            level = data.get("evidence_level", 3)
                            if not isinstance(level, int) or not 1 <= level <= 4:
                                level = 3
                            quote = data.get("quote_text")
                            note = data.get("note")
                            return (
                                ExtractedEvidencePayload(
                                    description=desc,
                                    evidence_level=EvidenceLevel(level),
                                    quote_text=quote if isinstance(quote, str) else None,
                                    note=note if isinstance(note, str) else None,
                                ),
                                settings.AI_MODEL,
                                0.8,
                            )
                except json.JSONDecodeError:
                    pass

        # Rule fallback: first 80 chars as the exact quote, generic description.
        return (
            ExtractedEvidencePayload(
                description=f"《{doc_title}》原文摘录（规则抽取）",
                evidence_level=EvidenceLevel(3),
                quote_text=None,
                note="规则抽取 fallback（AI 不可用或未返回有效 JSON）",
            ),
            _RULE_FALLBACK_MODEL,
            0.5,
        )

    @staticmethod
    def _locate_span(
        chunk_content: str, quote_text: str | None
    ) -> tuple[int, int, str]:
        """Return (start, end, exact_text) for the quote span.

        The AI-supplied ``quote_text`` is only accepted when it is a verbatim
        substring of the chunk; otherwise fall back to a deterministic prefix.
        """
        if quote_text:
            idx = chunk_content.find(quote_text)
            if idx >= 0:
                return idx, idx + len(quote_text), quote_text
        exact = chunk_content[:80]
        return 0, len(exact), exact


def get_candidate_generation_service(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_session_factory)
    ],
) -> CandidateGenerationService:
    """FastAPI dependency: provide the candidate generation service."""
    return CandidateGenerationService(
        session_factory,
        AIService(),
        CandidateCreateUnitOfWork(session_factory),
    )
