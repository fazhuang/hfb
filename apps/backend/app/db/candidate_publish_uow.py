"""Candidate publish unit of work (persistence layer).

Owns a fresh session and the single top-level transaction for the Phase A0
candidate approval flow. The service facade never touches ``AsyncSession`` or
``db.begin()``; this module is the only component that does.
"""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import UTC, datetime
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pydantic import BaseModel

from app.core.exceptions import DomainException, NotFoundException
from app.models.academic_evidence import Evidence, EvidenceLevel
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.repositories.candidate_extraction import CandidateExtractionRepository
from app.repositories.source_ref import SourceRefRepository
from app.repositories.user import UserRepository
from app.repositories.version import VersionRepository
from app.services.citation_persistence import CitationPersistenceService


class GroundingDriftException(DomainException):
    """Raised when a candidate's grounding anchors no longer match the live chunk.

    The drift itself is already committed inside the transaction as
    ``DRIFT_INVALID`` + audit record; this exception is the outward signal.
    """

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message, error_code="GROUNDING_DRIFT", status_code=409
        )


class ProposedEvidencePayload(BaseModel):
    """The extracted payload schema carried in ``CandidateExtraction.extracted_payload``."""

    description: str
    evidence_level: EvidenceLevel
    quote_text: str | None = None
    note: str | None = None


async def _verify_ownership_chain(
    repo: CandidateExtractionRepository,
    candidate: CandidateExtraction,
    session_id: str,
    reviewer_id: str,
) -> DocumentChunk | None:
    """Verify Candidate → Session → reviewer AND Candidate → Chunk → Document.

    Every mutable source is read FOR UPDATE (via the repository) so ownership or
    grounding cannot change between validation and publish. Returns the locked
    ``DocumentChunk`` on success, or ``None`` when the chain is broken.
    """
    if candidate.session_id != session_id:
        return None

    session = await repo.get_session_for_update(session_id)
    if session is None or session.user_id != reviewer_id:
        return None

    chunk = await repo.get_chunk_for_update(candidate.chunk_id)
    if chunk is None:
        return None

    doc = await repo.get_document_for_update(chunk.document_id)
    if doc is None:
        return None

    if doc.session_id is not None and doc.session_id != session_id:
        return None
    if doc.uploaded_by is not None and doc.uploaded_by != reviewer_id:
        return None
    return chunk


async def _publish_in_transaction(
    repo: CandidateExtractionRepository,
    source_ref_repo: SourceRefRepository,
    version_repo: VersionRepository,
    candidate_id: str,
    reviewer: User,
    session_id: str,
) -> tuple[Evidence | None, GroundingDriftException | None]:
    """Core publish logic, running inside the UoW's single transaction.

    Returns ``(evidence, None)`` on success, or ``(None, drift_exception)`` when
    drift was committed inside the transaction (the caller re-raises it).
    """
    pending_drift_exception: GroundingDriftException | None = None

    candidate = await repo.get_for_update(candidate_id)
    if not candidate or candidate.status != CandidateStatus.PENDING:
        raise NotFoundException("Candidate", candidate_id)

    chunk = await _verify_ownership_chain(repo, candidate, session_id, reviewer.id)
    if chunk is None:
        raise NotFoundException("Candidate", candidate_id)

    passage_id = chunk.passage_id
    if passage_id is None:
        await repo.mark_drift(candidate, reviewer.id, "Missing valid passage_id")
        pending_drift_exception = GroundingDriftException("Missing valid passage_id")

    if not pending_drift_exception:
        assert passage_id is not None
        passage = await repo.get_passage_for_update(passage_id)
        if not passage or passage.version_id != candidate.version_id:
            await repo.mark_drift(
                candidate, reviewer.id, "Version mismatch with Passage"
            )
            pending_drift_exception = GroundingDriftException(
                "Version mismatch between Candidate and Passage"
            )

    if not pending_drift_exception and candidate.page_image_hash:
        if (
            chunk.page_image_hash != candidate.page_image_hash
            or chunk.page_image_hash_alg != candidate.page_image_hash_alg
        ):
            await repo.mark_drift(
                candidate, reviewer.id, "Page image hash/alg mismatch"
            )
            pending_drift_exception = GroundingDriftException(
                "Page image hash/alg mismatch"
            )

    if not pending_drift_exception:
        real_chunk_sha256 = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
        normalized_chunk = unicodedata.normalize("NFC", chunk.content)
        normalized_exact = unicodedata.normalize("NFC", candidate.exact_text)
        real_nfc_sha256 = hashlib.sha256(normalized_chunk.encode("utf-8")).hexdigest()

        is_grounding_valid = (
            real_chunk_sha256 == candidate.expected_chunk_sha256
            and real_nfc_sha256 == candidate.expected_nfc_sha256
            and 0 <= candidate.start_char < candidate.end_char <= len(normalized_chunk)
            and (candidate.end_char - candidate.start_char) == len(normalized_exact)
            and normalized_chunk[candidate.start_char : candidate.end_char]
            == normalized_exact
        )

        if not is_grounding_valid:
            await repo.mark_drift(candidate, reviewer.id, "Text/Hash drift detected")
            pending_drift_exception = GroundingDriftException(
                "Text/Hash drift detected"
            )

    if not pending_drift_exception:
        # Fails closed: raises RuntimeError on missing/soft-deleted SourceRef
        # or a missing/soft-deleted/withdrawn Version → rollback.
        source_ref_id = await CitationPersistenceService.verify_and_resolve_source_ref(
            source_ref_repo,
            version_repo,
            doc_id=chunk.document_id,
            source_uri=candidate.input_snapshot.get("source_uri"),
            version_id=candidate.version_id,
        )

        payload = ProposedEvidencePayload(**candidate.extracted_payload)
        evidence = await repo.create_evidence(
            description=payload.description,
            evidence_level=payload.evidence_level,
            source_ref_id=source_ref_id,
            source_passage_id=chunk.passage_id,
            creator_id=reviewer.id,
        )
        await repo.create_citation(
            target_type="Passage",
            target_id=chunk.passage_id,
            evidence_id=evidence.id,
            quote_text=payload.quote_text or candidate.exact_text,
            note=payload.note,
        )

        candidate.status = CandidateStatus.APPROVED
        candidate.published_evidence_id = evidence.id
        candidate.reviewed_by_user_id = reviewer.id
        candidate.reviewed_at = datetime.now(UTC)

        await repo.create_audit_log(
            candidate_id=candidate.id,
            action="approved",
            operator_id=reviewer.id,
            input_snapshot=candidate.input_snapshot,
            pre_payload=candidate.extracted_payload,
            post_payload={"published_evidence_id": evidence.id},
            published_evidence_id=evidence.id,
        )

    if pending_drift_exception:
        return None, pending_drift_exception
    return evidence, None


class CandidatePublishUnitOfWork:
    """Owns a fresh session and the single top-level transaction for publishing."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] | async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def publish(
        self, candidate_id: str, reviewer_id: str, session_id: str
    ) -> Evidence:
        pending_drift: GroundingDriftException | None = None
        evidence: Evidence | None = None

        async with self._session_factory() as session:
            if session.in_transaction():
                raise RuntimeError(
                    "Candidate publish requires a fresh session with no active "
                    "transaction."
                )
            candidate_repo = CandidateExtractionRepository(session)
            source_ref_repo = SourceRefRepository(session)
            version_repo = VersionRepository(session)

            async with session.begin():
                reviewer = await UserRepository(session).get_by_id(reviewer_id)
                if reviewer is None:
                    raise DomainException(
                        message="User not found",
                        error_code="USER_NOT_FOUND",
                        status_code=401,
                    )
                evidence, pending_drift = await _publish_in_transaction(
                    candidate_repo,
                    source_ref_repo,
                    version_repo,
                    candidate_id,
                    reviewer,
                    session_id,
                )

        if pending_drift is not None:
            raise pending_drift
        assert evidence is not None
        return evidence
