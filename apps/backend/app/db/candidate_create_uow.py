"""Candidate create unit of work (persistence layer).

Mirrors ``CandidatePublishUnitOfWork``: owns a fresh session and the single
top-level transaction that validates ownership + grounding and buffers an
AI/rule extraction as a PENDING candidate. The service facade never touches
``AsyncSession`` or ``db.begin()``.
"""

from __future__ import annotations

from collections.abc import Callable

from app.core.exceptions import NotFoundException, ValidationException
from app.db.grounding import is_grounding_valid
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.repositories.candidate_extraction import CandidateExtractionRepository
from app.repositories.version import VersionRepository
from app.schemas.candidate import CreateCandidateRequest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class CandidateCreateUnitOfWork:
    """Owns a fresh session and the single top-level transaction for create."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] | async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def create(
        self, request: CreateCandidateRequest, user_id: str
    ) -> CandidateExtraction:
        """Validate ownership + grounding, then buffer a PENDING candidate.

        Fail-closed on every axis:
          * Session must belong to the caller (else 404, no existence leak).
          * Chunk → Document must belong to that session and caller.
          * Chunk must have a linked Passage whose version equals ``version_id``.
          * Version must exist and not be withdrawn.
          * Grounding anchors must exactly match the live chunk bytes.
        """
        created: CandidateExtraction | None = None

        async with self._session_factory() as session:
            if session.in_transaction():
                raise RuntimeError(
                    "Candidate create requires a fresh session with no active "
                    "transaction."
                )
            repo = CandidateExtractionRepository(session)
            version_repo = VersionRepository(session)

            async with session.begin():
                # 1. Session ownership.
                session_row = await repo.get_session_for_update(request.session_id)
                if session_row is None or session_row.user_id != user_id:
                    raise NotFoundException("ResearchSession", request.session_id)

                # 2. Chunk → Document ownership.
                chunk = await repo.get_chunk_for_update(request.chunk_id)
                if chunk is None:
                    raise NotFoundException("DocumentChunk", request.chunk_id)
                doc = await repo.get_document_for_update(chunk.document_id)
                if doc is None:
                    raise NotFoundException("Document", chunk.document_id)
                if doc.session_id is not None and doc.session_id != request.session_id:
                    raise NotFoundException("DocumentChunk", request.chunk_id)
                if doc.uploaded_by is not None and doc.uploaded_by != user_id:
                    raise NotFoundException("DocumentChunk", request.chunk_id)

                # 3. Version anchoring: chunk's Passage must exist and match.
                if chunk.passage_id is None:
                    raise ValidationException(
                        "Chunk has no linked passage; cannot anchor a candidate "
                        "to a version"
                    )
                passage = await repo.get_passage_for_update(chunk.passage_id)
                if passage is None or passage.version_id != request.version_id:
                    raise ValidationException(
                        "Candidate version_id does not match the chunk's passage "
                        "version"
                    )

                # 4. Version exists and is not withdrawn.
                version_row = await version_repo.get_withdrawn_at_for_update(
                    request.version_id
                )
                if version_row is None:
                    raise ValidationException("Version does not exist or is deleted")
                if version_row[0] is not None:
                    raise ValidationException("Version is withdrawn")

                # 5. Grounding anchors must match the live chunk content.
                if not is_grounding_valid(
                    chunk_content=chunk.content,
                    expected_chunk_sha256=request.expected_chunk_sha256,
                    expected_nfc_sha256=request.expected_nfc_sha256,
                    start_char=request.start_char,
                    end_char=request.end_char,
                    exact_text=request.exact_text,
                ):
                    raise ValidationException(
                        "Grounding anchors do not match the live chunk content"
                    )

                # 6. Buffer the PENDING candidate.
                created = await repo.create(
                    session_id=request.session_id,
                    created_by=user_id,
                    chunk_id=request.chunk_id,
                    version_id=request.version_id,
                    expected_chunk_sha256=request.expected_chunk_sha256,
                    expected_nfc_sha256=request.expected_nfc_sha256,
                    unicode_normalization=request.unicode_normalization,
                    start_char=request.start_char,
                    end_char=request.end_char,
                    exact_text=request.exact_text,
                    title=request.title,
                    language=request.language,
                    abstract=request.abstract,
                    keywords=request.keywords,
                    description=request.description,
                    input_snapshot=request.input_snapshot,
                    page_image_hash=request.page_image_hash,
                    page_image_hash_alg=request.page_image_hash_alg,
                    extraction_type=request.extraction_type,
                    extracted_payload=request.extracted_payload.model_dump(mode="json"),
                    extractor_name=request.extractor_name,
                    ai_model=request.ai_model,
                    ai_version=request.ai_version,
                    prompt_version=request.prompt_version,
                    processing_time=request.processing_time,
                    prompt_hash=request.prompt_hash,
                    confidence=request.confidence,
                    status=CandidateStatus.PENDING,
                )

                # 7. Append-only audit: creation event (candidate_id non-NULL).
                await repo.create_audit_log(
                    candidate_id=created.id,
                    action="created",
                    operator_id=user_id,
                    input_snapshot=request.input_snapshot,
                    pre_payload=None,
                    post_payload=request.extracted_payload.model_dump(mode="json"),
                )

        assert created is not None
        return created
