"""Candidate Extraction Service — Phase A0 context-safe drift + atomic publish.

This service owns the single transaction that promotes a ``CandidateExtraction``
from the AI-extraction world into the academically-confirmed graph. It enforces:

* session ownership (permission is enforced by the controller's
  ``require_permission("extraction", "approve")``),
* dual-hash grounding (chunk SHA-256, NFC SHA-256, exact char-span slice),
* page-image hash/alg agreement,
* withdrawn / soft-deleted Version and pre-existing-SourceRef guards,
* a single top-level ``db.begin()`` transaction with pessimistic row locking.

All data access is routed through ``CandidateExtractionRepository`` — the service
does not call ``db.execute`` / ``db.add`` / ``db.flush`` directly.

Drift is committed (not rolled back) as ``DRIFT_INVALID`` + an audit row, and the
``GroundingDriftException`` is raised only *after* the transaction context exits.
"""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_evidence import Evidence, EvidenceLevel
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.repositories.candidate_extraction import CandidateExtractionRepository
from app.services.citation_persistence import CitationPersistenceService

class GroundingDriftException(Exception):
    """Raised when a candidate's grounding anchors no longer match the live chunk.

    The drift itself is already committed inside the transaction as
    ``DRIFT_INVALID`` + audit record; this exception is the outward signal.
    """


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


async def approve_and_publish_candidate(
    db: AsyncSession,
    candidate_id: str,
    reviewer: User,
    session_id: str,
) -> Evidence:
    """Approve and atomically publish a candidate as Evidence + Citation.

    RBAC authorization (``extraction:approve``) is enforced by the controller;
    this service owns ownership + grounding + atomic publish inside one
    top-level transaction.
    """
    pending_drift_exception: GroundingDriftException | None = None

    # The single-transaction contract requires a clean session. If the caller
    # already started a transaction (e.g. by running auth checks on the same
    # session), db.begin() would raise InvalidRequestError — fail loudly here.
    if db.in_transaction():
        raise RuntimeError(
            "approve_and_publish_candidate requires a fresh session with no "
            "active transaction; call it on a dedicated session."
        )

    async with db.begin():
        repo = CandidateExtractionRepository(db)

        candidate = await repo.get_for_update(candidate_id)
        if not candidate or candidate.status != CandidateStatus.PENDING:
            raise HTTPException(
                status_code=404, detail="Candidate not found or not pending"
            )

        # Ownership chain — returns the FOR UPDATE-locked chunk.
        chunk = await _verify_ownership_chain(repo, candidate, session_id, reviewer.id)
        if chunk is None:
            raise HTTPException(
                status_code=404, detail="Candidate not found or access denied"
            )

        if not chunk.passage_id:
            await repo.mark_drift(candidate, reviewer.id, "Missing valid passage_id")
            pending_drift_exception = GroundingDriftException("Missing valid passage_id")

        if not pending_drift_exception:
            passage = await repo.get_passage_for_update(chunk.passage_id)
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
                await repo.mark_drift(
                    candidate, reviewer.id, "Text/Hash drift detected"
                )
                pending_drift_exception = GroundingDriftException(
                    "Text/Hash drift detected"
                )

        if not pending_drift_exception:
            # Fails closed: raises RuntimeError on missing/soft-deleted SourceRef
            # or a missing/soft-deleted/withdrawn Version → rollback.
            source_ref_id = await CitationPersistenceService.verify_and_resolve_source_ref(
                db,
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
        raise pending_drift_exception

    return evidence


class CandidateExtractionService:
    """Controller-facing service facade for candidate approval.

    Owns the session and transaction boundaries so the controller never
    touches a session or repository directly.
    """

    async def approve(
        self, candidate_id: str, reviewer_id: str, session_id: str
    ) -> Evidence:
        from app.db.database import async_session_factory

        # Validate the reviewer exists (short-lived session), then publish on a
        # fresh session so the single-transaction db.begin() contract holds.
        async with async_session_factory() as review_session:
            reviewer = await review_session.get(User, reviewer_id)
        if reviewer is None:
            raise HTTPException(
                status_code=401, detail="User not found"
            )

        async with async_session_factory() as session:
            return await approve_and_publish_candidate(
                session, candidate_id, reviewer, session_id
            )
