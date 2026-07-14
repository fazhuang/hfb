"""Unified trace builder and resolver for Sprint 4 V4 product layer.

Centralizes trace_id generation, InternalTraceRecord construction, and
lineage resolution (trace → chunk → document → passage → citation).

All V4 routes (research, education, workflow, visualization) use this module.
No per-file _make_trace_id copies.
"""
from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.passage import Passage
from app.models.version import Version

# =============================================================================
# Trace ID generation — 128-bit stable identifier (UUIDv5)
# =============================================================================

_TRACE_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace


def make_trace_id(document_id: str, chunk_id: str) -> str:
    """Generate a stable, 128-bit trace identifier (UUIDv5).

    Format: UUID string, derived from document_id + chunk_id.
    NOT a 32-bit SHA-256 truncation. NOT equal to chunk_id.
    """
    raw = f"{document_id}:{chunk_id}"
    return str(uuid.uuid5(_TRACE_NAMESPACE, raw))


def _is_valid_uuidv5(value: str) -> bool:
    try:
        parsed = uuid.UUID(value)
        return parsed.version == 5
    except (ValueError, AttributeError):
        return False


def _is_valid_score(value: float) -> bool:
    if not isinstance(value, (int, float)):
        return False
    if math.isnan(value) or math.isinf(value):
        return False
    if value < 0.0 or value > 1.0:
        return False
    return True


# =============================================================================
# InternalTraceRecord — strict Pydantic model, all fields validated
# =============================================================================


class InternalTraceRecord(BaseModel):
    """Full-fidelity internal trace record. Every field required and validated.

    NEVER exposed through API. Stored in QueryHistory.result_summary.

    provenance_kind: 'retrieval' | 'graph'
      - retrieval: scored via real retrieval, score must be 0.0–1.0, method required
      - graph: evidence from graph analysis, score must be None, method is graph operation name

    All fields must be non-empty, non-default-fabricated.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)
    passage_id: str = Field(..., min_length=1)
    provenance_kind: str = Field(..., min_length=1)  # 'retrieval' | 'graph'
    retrieval_score: float | None = None  # 0.0–1.0 for retrieval, None for graph
    retrieval_method: str = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_all(self) -> "InternalTraceRecord":
        # trace_id must be valid UUIDv5
        if not _is_valid_uuidv5(self.trace_id):
            raise ValueError(f"trace_id must be UUIDv5, got: {self.trace_id}")

        # document_id and chunk_id must not be empty string
        if not self.document_id.strip():
            raise ValueError("document_id must not be empty")
        if not self.chunk_id.strip():
            raise ValueError("chunk_id must not be empty")
        if not self.passage_id.strip():
            raise ValueError("passage_id must not be empty")

        # provenance_kind must be 'retrieval' or 'graph'
        if self.provenance_kind not in ("retrieval", "graph"):
            raise ValueError(
                f"provenance_kind must be 'retrieval' or 'graph', got: {self.provenance_kind}"
            )

        # retrieval_score semantics
        if self.provenance_kind == "retrieval":
            if self.retrieval_score is None:
                raise ValueError("retrieval provenance requires a retrieval_score (0.0–1.0), got None")
            if not _is_valid_score(self.retrieval_score):
                raise ValueError(
                    f"retrieval_score must be 0.0–1.0, not NaN/Inf, got: {self.retrieval_score}"
                )
        elif self.provenance_kind == "graph":
            if self.retrieval_score is not None:
                raise ValueError(
                    f"graph provenance must have retrieval_score=None, got: {self.retrieval_score}"
                )

        # retrieval_method must be a real method name, not empty placeholder
        if not self.retrieval_method.strip():
            raise ValueError("retrieval_method must not be empty")

        # timestamp must be non-empty
        if not self.timestamp.strip():
            raise ValueError("timestamp must not be empty")

        return self

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "document_id": self.document_id,
            "chunk_id": self.chunk_id,
            "passage_id": self.passage_id,
            "provenance_kind": self.provenance_kind,
            "retrieval_score": self.retrieval_score,
            "retrieval_method": self.retrieval_method,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Trace builder — async, queries passage linkage + retrieval metadata in real time
# =============================================================================


async def build_internal_traces(
    db: AsyncSession,
    evidence_traces: list,
    retrieval_snapshot: dict | None = None,
) -> list[InternalTraceRecord]:
    """Build InternalTraceRecord list from evidence + retrieval snapshot.

    Sprint 4 P0: REQUIRES retrieval_snapshot with real score/method per chunk.
    Fails with TraceLineageError if snapshot missing or incomplete.
    Never fabricates default score=0.0 or method="ili_keyword".
    """
    if retrieval_snapshot is None:
        raise TraceLineageError(
            "TRACE_LINEAGE_INCOMPLETE: retrieval_snapshot is required — "
            "cannot construct InternalTraceRecord with fabricated defaults"
        )

    now = datetime.now(timezone.utc).isoformat()
    records: list[InternalTraceRecord] = []
    seen: set[str] = set()

    # P2T1: Cache version withdrawal checks per passage_id
    checked_withdrawn: dict[str, bool] = {}

    # Batch-query all chunk passage_ids
    chunk_ids = list({t.chunk_id for t in evidence_traces if hasattr(t, 'chunk_id')})
    passage_map: dict[str, str] = {}
    if chunk_ids:
        stmt = select(DocumentChunk.id, DocumentChunk.passage_id).where(
            DocumentChunk.id.in_(chunk_ids),
            DocumentChunk.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        for row in result:
            pid = row[1] if row[1] and row[1].strip() else ""
            passage_map[row[0]] = pid

    for t in evidence_traces:
        doc_id = t.document_id if hasattr(t, 'document_id') else ""
        chk_id = t.chunk_id if hasattr(t, 'chunk_id') else ""
        if not doc_id or not chk_id:
            continue

        tid = make_trace_id(doc_id, chk_id)
        if tid in seen:
            continue
        seen.add(tid)

        # Sprint 4 P0: require real score/method from snapshot
        if chk_id not in retrieval_snapshot:
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: chunk {chk_id} not in retrieval_snapshot — "
                f"cannot construct InternalTraceRecord for trace {tid}"
            )

        snap_entry = retrieval_snapshot[chk_id]
        score = snap_entry.get("score", None)
        if not _is_valid_score(score):
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: chunk {chk_id} has invalid score "
                f"({score}) in snapshot — cannot construct trace {tid}"
            )
        method = snap_entry.get("retrieval_method", "")
        if not method or not method.strip():
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: chunk {chk_id} has empty retrieval_method "
                f"in snapshot — cannot construct trace {tid}"
            )

        # Get real passage_id from DB
        passage_id = passage_map.get(chk_id, "")

        if not passage_id:
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: chunk {chk_id} has no passage_id — "
                f"cannot construct InternalTraceRecord for trace {tid}"
            )

        # P2T1: Reject chunks whose passage version is withdrawn
        if passage_id not in checked_withdrawn:
            v_stmt = select(Version.withdrawn_at).join(
                Passage, Passage.version_id == Version.id
            ).where(
                Passage.id == passage_id,
                Passage.is_deleted.is_(False),
                Version.is_deleted.is_(False),
            )
            v_result = await db.execute(v_stmt)
            v_row = v_result.one_or_none()
            checked_withdrawn[passage_id] = bool(v_row and v_row[0] is not None)
        if checked_withdrawn[passage_id]:
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: passage {passage_id} belongs to "
                f"a withdrawn version — cannot construct InternalTraceRecord for trace {tid}"
            )

        records.append(InternalTraceRecord(
            trace_id=tid,
            document_id=doc_id,
            chunk_id=chk_id,
            passage_id=passage_id,
            provenance_kind="retrieval",
            retrieval_score=score,
            retrieval_method=method,
            timestamp=now,
        ))

    return records


async def build_viz_traces(
    db: AsyncSession,
    evidence_traces: list,
) -> list[InternalTraceRecord]:
    """Build InternalTraceRecord list for visualization evidence.

    Visualization evidence (GraphEvidence, CrossDocumentClaim) carries
    document_id + chunk_id but NOT retrieval score/method. Traces are built
    by resolving passage_id from DB. Score defaults to 0.0 (not retrieval
    scored). Method is 'graph_service' (evidence is graph-derived).

    Sprint 4 P0: Fails if any chunk has no passage_id.
    """
    now = datetime.now(timezone.utc).isoformat()
    records: list[InternalTraceRecord] = []
    seen: set[str] = set()

    # Batch-query all chunk passage_ids
    chunk_ids = list({t.chunk_id for t in evidence_traces if hasattr(t, 'chunk_id')})
    passage_map: dict[str, str] = {}
    if chunk_ids:
        stmt = select(DocumentChunk.id, DocumentChunk.passage_id).where(
            DocumentChunk.id.in_(chunk_ids),
            DocumentChunk.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        for row in result:
            pid = row[1] if row[1] and row[1].strip() else ""
            passage_map[row[0]] = pid

    for t in evidence_traces:
        doc_id = t.document_id if hasattr(t, 'document_id') else ""
        chk_id = t.chunk_id if hasattr(t, 'chunk_id') else ""
        if not doc_id or not chk_id:
            continue

        tid = make_trace_id(doc_id, chk_id)
        if tid in seen:
            continue
        seen.add(tid)

        passage_id = passage_map.get(chk_id, "")
        if not passage_id:
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: chunk {chk_id} has no passage_id — "
                f"cannot construct InternalTraceRecord for trace {tid}"
            )

        records.append(InternalTraceRecord(
            trace_id=tid,
            document_id=doc_id,
            chunk_id=chk_id,
            passage_id=passage_id,
            provenance_kind="graph",
            retrieval_score=None,  # graph-derived, not retrieval-scored
            retrieval_method="graph_service",
            timestamp=now,
        ))

    return records


def extract_trace_ids(evidence_traces: list) -> list[str]:
    """Extract stable trace_ids from EvidenceTrace list. Deduplicated."""
    seen: set[str] = set()
    ids: list[str] = []
    for t in evidence_traces:
        doc_id = t.document_id if hasattr(t, 'document_id') else ""
        chk_id = t.chunk_id if hasattr(t, 'chunk_id') else ""
        if not doc_id or not chk_id:
            continue
        tid = make_trace_id(doc_id, chk_id)
        if tid not in seen:
            seen.add(tid)
            ids.append(tid)
    return ids


def extract_source_documents(evidence_traces: list) -> list[str]:
    """Extract deduplicated, sorted document IDs from evidence traces."""
    return sorted(set(
        t.document_id for t in evidence_traces
        if hasattr(t, 'document_id') and t.document_id
    ))


# =============================================================================
# Lineage resolver — strict by default
# =============================================================================


class TraceLineageError(Exception):
    """Raised when trace lineage resolution fails."""
    pass


@dataclass(frozen=True, slots=True)
class ResolvedTrace:
    """Fully resolved trace lineage."""
    trace_id: str
    chunk: DocumentChunk
    document: Document
    passage: Passage | None
    passage_citation: str
    chunk_citation: str

    def to_public_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "document_id": self.document.id,
            "document_title": self.document.title,
            "chunk_index": self.chunk.chunk_index,
            "passage_id": self.passage.id if self.passage else None,
            "citation": self.passage_citation or self.chunk_citation,
        }


async def resolve_trace_lineage(
    db: AsyncSession,
    trace_id: str,
) -> ResolvedTrace:
    """Resolve a trace_id to full lineage. Strict: missing passage → error.

    Chain: trace_id → chunk → document → passage → citation.
    Resolves by brute-force scanning chunks since UUIDv5 is one-way.
    Also checks QueryHistory as a fast path.
    Raises TraceLineageError if any link is broken.
    """
    from app.models.workspace import QueryHistory

    chunk_id: str | None = None

    # Fast path: look up trace_id in QueryHistory for chunk_id
    qh_stmt = (
        select(QueryHistory)
        .where(QueryHistory.result_summary.contains(trace_id))
        .order_by(QueryHistory.created_at.desc())
        .limit(1)
    )
    qh_result = await db.execute(qh_stmt)
    qh = qh_result.scalar_one_or_none()
    if qh and qh.result_summary:
        try:
            summary = json.loads(qh.result_summary)
            for t in summary.get("traces", []):
                if t.get("trace_id") == trace_id:
                    chunk_id = t.get("chunk_id")
                    break
        except (json.JSONDecodeError, TypeError):
            pass

    # Slow path: brute-force scan all chunks for matching UUIDv5 hash
    if not chunk_id:
        all_chunks_stmt = select(DocumentChunk.id, DocumentChunk.document_id).where(
            DocumentChunk.is_deleted.is_(False),
        )
        all_chunks_result = await db.execute(all_chunks_stmt)
        for row in all_chunks_result:
            cid, did = row[0], row[1]
            if make_trace_id(did, cid) == trace_id:
                chunk_id = cid
                break

    if not chunk_id:
        raise TraceLineageError(
            f"TRACE_LINEAGE_INCOMPLETE: trace_id {trace_id} not found in any chunk or QueryHistory"
        )

    # Resolve chunk
    chunk_stmt = select(DocumentChunk).where(
        DocumentChunk.id == chunk_id,
        DocumentChunk.is_deleted.is_(False),
    )
    chunk_result = await db.execute(chunk_stmt)
    chunk = chunk_result.scalar_one_or_none()
    if chunk is None:
        raise TraceLineageError(
            f"TRACE_LINEAGE_INCOMPLETE: chunk {chunk_id} not found for trace {trace_id}"
        )

    # Resolve document
    doc_stmt = select(Document).where(
        Document.id == chunk.document_id,
        Document.is_deleted.is_(False),
    )
    doc_result = await db.execute(doc_stmt)
    document = doc_result.scalar_one_or_none()
    if document is None:
        raise TraceLineageError(
            f"TRACE_LINEAGE_INCOMPLETE: document {chunk.document_id} not found"
        )

    # Resolve passage — strict: must exist
    if not chunk.passage_id or not chunk.passage_id.strip():
        raise TraceLineageError(
            f"TRACE_LINEAGE_INCOMPLETE: chunk {chunk_id} has no passage_id"
        )

    passage_stmt = (
        select(Passage, Version, Book, Chapter)
        .join(Version, Passage.version_id == Version.id, isouter=True)
        .join(Book, Version.book_id == Book.id, isouter=True)
        .join(Chapter, Passage.chapter_id == Chapter.id, isouter=True)
        .where(
            Passage.id == chunk.passage_id,
            Passage.is_deleted.is_(False),
        )
    )
    passage_result = await db.execute(passage_stmt)
    row = passage_result.one_or_none()
    if row is None:
        raise TraceLineageError(
            f"TRACE_LINEAGE_INCOMPLETE: passage {chunk.passage_id} not found"
        )

    passage, version, book, chapter = row
    parts = []
    if book:
        parts.append(f"《{book.title}》")
    if version:
        parts.append(version.version_name)
    if chapter:
        parts.append(f"{chapter.title} §{passage.order}")
    passage_citation = "·".join(parts)
    chunk_citation = f"[{document.id}:{chunk.chunk_index}]"

    return ResolvedTrace(
        trace_id=trace_id,
        chunk=chunk,
        document=document,
        passage=passage,
        passage_citation=passage_citation,
        chunk_citation=chunk_citation,
    )


# =============================================================================
# Passage mapping diagnostics
# =============================================================================


async def passage_mapping_stats(db: AsyncSession) -> dict:
    """Return chunk-to-passage mapping statistics."""
    total_stmt = select(DocumentChunk).where(DocumentChunk.is_deleted.is_(False))
    total_result = await db.execute(total_stmt)
    total = len(total_result.scalars().all())

    mapped_stmt = select(DocumentChunk).where(
        DocumentChunk.is_deleted.is_(False),
        DocumentChunk.passage_id.isnot(None),
        DocumentChunk.passage_id != "",
    )
    mapped_result = await db.execute(mapped_stmt)
    chunks_with_passage = len(mapped_result.scalars().all())

    # Orphan: passage_ids that point to non-existent passages
    orphan_count = 0
    if chunks_with_passage > 0:
        all_passage_ids_stmt = (
            select(DocumentChunk.passage_id)
            .where(
                DocumentChunk.is_deleted.is_(False),
                DocumentChunk.passage_id.isnot(None),
                DocumentChunk.passage_id != "",
            )
            .distinct()
        )
        pid_result = await db.execute(all_passage_ids_stmt)
        all_pids = [row[0] for row in pid_result if row[0]]

        existing_stmt = select(Passage.id).where(
            Passage.id.in_(all_pids),
            Passage.is_deleted.is_(False),
        )
        exist_result = await db.execute(existing_stmt)
        existing_pids = {row[0] for row in exist_result}

        for pid in all_pids:
            if pid not in existing_pids:
                orphan_count += 1

    return {
        "total_chunks": total,
        "chunks_with_passage": chunks_with_passage,
        "chunks_without_passage": total - chunks_with_passage,
        "orphan_passage_ids": orphan_count,
    }


# =============================================================================
# Time evidence resolution — chunk → passage → version.era/year
# =============================================================================


async def resolve_time_evidence(
    db: AsyncSession, document_id: str, chunk_id: str,
) -> dict | None:
    """Resolve era/year from Version for a chunk. Uses DB schema, not regex.

    Sprint 4 P0: Returns None when no structured time evidence available.
    Does NOT regex-scan citation text for dynasty names.
    """
    # Try chunk → passage → version path
    stmt = select(DocumentChunk.passage_id).where(
        DocumentChunk.id == chunk_id,
        DocumentChunk.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row and row[0]:
        p_stmt = select(Passage.version_id).where(
            Passage.id == row[0],
            Passage.is_deleted.is_(False),
        )
        p_result = await db.execute(p_stmt)
        p_row = p_result.one_or_none()
        if p_row:
            v_stmt = select(Version.era, Version.year).where(
                Version.id == p_row[0],
                Version.is_deleted.is_(False),
            )
            v_result = await db.execute(v_stmt)
            v_row = v_result.one_or_none()
            if v_row:
                meta = {}
                if v_row[0]:
                    meta["era"] = v_row[0]
                if v_row[1]:
                    meta["year"] = str(v_row[1])
                if meta:
                    return meta

    # Sprint 4 P0: NO Document.dynasty fallback.
    # timeline nodes require chunk → passage → version.era/year.
    # If Version has no structured time evidence, return None.
    return None
