"""Candidate Extraction Service — Phase A0 context-safe drift + atomic publish.

This service owns the single transaction that promotes a ``CandidateExtraction``
from the AI-extraction world into the academically-confirmed graph. It enforces:

* session ownership + ``extraction:approve`` permission (double check),
* dual-hash grounding (chunk SHA-256, NFC SHA-256, exact char-span slice),
* page-image hash/alg agreement,
* withdrawn-version and pre-existing-SourceRef guards,
* a single top-level ``db.begin()`` transaction with pessimistic row locking.

Drift is committed (not rolled back) as ``DRIFT_INVALID`` + an audit row, and the
``GroundingDriftException`` is raised only *after* the transaction context exits.
"""

from __future__ import annotations

import hashlib
import unicodedata
from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_evidence import Citation, Evidence, EvidenceLevel
from app.models.candidate_audit_log import CandidateAuditLog
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.passage import Passage
from app.models.user import User
from app.models.workspace import ResearchSession
from app.services.auth_service import AuthService
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


async def verify_full_ownership_chain(
    db: AsyncSession,
    candidate: CandidateExtraction,
    session_id: str,
    reviewer_id: str,
) -> DocumentChunk | None:
    """Verify the full resource-ownership chain; return the locked chunk.

    Chain: ``Candidate → ResearchSession → reviewer`` AND
    ``Candidate → DocumentChunk → Document``.

    Every mutable source is read with ``SELECT ... FOR UPDATE`` so a concurrent
    transaction cannot alter ownership (session.user_id, document.session_id/
    uploaded_by) or grounding (chunk content/hashes) between validation and
    publish. Returns the locked ``DocumentChunk`` on success, or ``None`` when
    the chain is broken (mapped to HTTP 404 by the caller).

    Private-document isolation: a ``Document`` bound to a specific session
    (``session_id`` set) must live in the candidate's session, and a document
    uploaded by a specific user (``uploaded_by`` set) must be that reviewer's
    own upload. Public documents (both NULL) impose no ownership restriction.
    """
    if candidate.session_id != session_id:
        return None

    session = (
        await db.execute(
            select(ResearchSession)
            .where(ResearchSession.id == session_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if session is None or session.user_id != reviewer_id:
        return None

    chunk = (
        await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.id == candidate.chunk_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if chunk is None:
        return None

    doc = (
        await db.execute(
            select(Document).where(Document.id == chunk.document_id).with_for_update()
        )
    ).scalar_one_or_none()
    if doc is None:
        return None

    if doc.session_id is not None and doc.session_id != session_id:
        return None
    if doc.uploaded_by is not None and doc.uploaded_by != reviewer_id:
        return None
    return chunk


def _mark_drift_in_tx(
    db: AsyncSession,
    candidate: CandidateExtraction,
    operator_id: str,
    reason: str,
) -> None:
    """Mark DRIFT_INVALID and write an audit row inside the current transaction."""
    candidate.status = CandidateStatus.DRIFT_INVALID
    audit = CandidateAuditLog(
        candidate_id=candidate.id,
        action="drift_flagged",
        operator_id=operator_id,
        pre_payload=candidate.extracted_payload,
        post_payload={"reason": reason},
    )
    db.add(audit)


async def approve_and_publish_candidate(
    db: AsyncSession,
    candidate_id: str,
    reviewer: User,
    session_id: str,
) -> Evidence:
    """Approve and atomically publish a candidate as Evidence + Citation.

    Follows the single-transaction contract: drift is committed inside
    ``async with db.begin()`` and the drift exception is raised after the block
    exits normally. Guard failures (403/404) and SourceRef/version failures
    propagate inside the block and therefore roll back fully.
    """
    pending_drift_exception: GroundingDriftException | None = None

    # The single-transaction contract requires a clean session. If the caller
    # already started a transaction (e.g. by running auth checks on the same
    # session), db.begin() would raise InvalidRequestError — fail loudly here
    # with an actionable message instead.
    if db.in_transaction():
        raise RuntimeError(
            "approve_and_publish_candidate requires a fresh session with no "
            "active transaction; call it on a dedicated session."
        )

    async with db.begin():
        # --- double check 1: permission (403) ---
        auth = AuthService(db)
        if not await auth.has_permission(reviewer.id, "extraction", "approve"):
            raise HTTPException(
                status_code=403, detail="Insufficient permission: extraction.approve"
            )

        # --- pessimistic lock ---
        stmt = (
            select(CandidateExtraction)
            .where(CandidateExtraction.id == candidate_id)
            .with_for_update()
        )
        candidate = (await db.execute(stmt)).scalar_one_or_none()

        if not candidate or candidate.status != CandidateStatus.PENDING:
            raise HTTPException(
                status_code=404, detail="Candidate not found or not pending"
            )

        # --- double check 2: session ownership + full chain (404) ---
        # Locks ResearchSession, DocumentChunk, and Document FOR UPDATE and
        # returns the locked chunk so grounding is validated against a stable
        # snapshot of the source text.
        chunk = await verify_full_ownership_chain(db, candidate, session_id, reviewer.id)
        if chunk is None:
            raise HTTPException(
                status_code=404, detail="Candidate not found or access denied"
            )

        if not chunk.passage_id:
            _mark_drift_in_tx(db, candidate, reviewer.id, "Missing valid passage_id")
            pending_drift_exception = GroundingDriftException("Missing valid passage_id")

        if not pending_drift_exception:
            passage = (
                await db.execute(
                    select(Passage).where(Passage.id == chunk.passage_id).with_for_update()
                )
            ).scalar_one_or_none()
            if not passage or passage.version_id != candidate.version_id:
                _mark_drift_in_tx(db, candidate, reviewer.id, "Version mismatch with Passage")
                pending_drift_exception = GroundingDriftException(
                    "Version mismatch between Candidate and Passage"
                )

        if not pending_drift_exception and candidate.page_image_hash:
            if (
                chunk.page_image_hash != candidate.page_image_hash
                or chunk.page_image_hash_alg != candidate.page_image_hash_alg
            ):
                _mark_drift_in_tx(db, candidate, reviewer.id, "Page image hash/alg mismatch")
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
                _mark_drift_in_tx(db, candidate, reviewer.id, "Text/Hash drift detected")
                pending_drift_exception = GroundingDriftException(
                    "Text/Hash drift detected"
                )

        if not pending_drift_exception:
            # Fails closed: raises RuntimeError on missing SourceRef or withdrawn
            # version → propagates inside db.begin() → full rollback.
            source_ref_id = await CitationPersistenceService.verify_and_resolve_source_ref(
                db,
                doc_id=chunk.document_id,
                source_uri=candidate.input_snapshot.get("source_uri"),
                version_id=candidate.version_id,
            )

            payload = ProposedEvidencePayload(**candidate.extracted_payload)
            evidence = Evidence(
                description=payload.description,
                evidence_level=payload.evidence_level,
                source_ref_id=source_ref_id,
                source_passage_id=chunk.passage_id,
                creator_id=reviewer.id,
            )
            db.add(evidence)
            await db.flush()

            citation = Citation(
                target_type="Passage",
                target_id=chunk.passage_id,
                evidence_id=evidence.id,
                quote_text=payload.quote_text or candidate.exact_text,
                note=payload.note,
            )
            db.add(citation)

            candidate.status = CandidateStatus.APPROVED
            candidate.published_evidence_id = evidence.id
            candidate.reviewed_by_user_id = reviewer.id
            candidate.reviewed_at = datetime.now(UTC)

            audit = CandidateAuditLog(
                candidate_id=candidate.id,
                action="approved",
                operator_id=reviewer.id,
                input_snapshot=candidate.input_snapshot,
                pre_payload=candidate.extracted_payload,
                post_payload={"published_evidence_id": evidence.id},
                published_evidence_id=evidence.id,
            )
            db.add(audit)

    if pending_drift_exception:
        raise pending_drift_exception

    return evidence
