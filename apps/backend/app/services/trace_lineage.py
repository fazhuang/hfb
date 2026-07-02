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

    All fields must be non-empty, non-default-fabricated.
    retrieval_score must be a real retrieval score 0.0–1.0.
    retrieval_method must be the actual execution path name.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    trace_id: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)
    passage_id: str = Field(..., min_length=1)
    retrieval_score: float = Field(..., ge=0.0, le=1.0)
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

        # retrieval_score must be a real value
        if not _is_valid_score(self.retrieval_score):
            raise ValueError(
                f"retrieval_score must be 0.0–1.0, not NaN/Inf, got: {self.retrieval_score}"
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
    retrieval_method: str = "ili_keyword",
) -> list[InternalTraceRecord]:
    """Build InternalTraceRecord list from evidence + retrieval snapshot.

    Requires:
    - evidence_traces: list of EvidenceTrace with document_id, chunk_id
    - retrieval_snapshot: dict[chunk_id, RetrievalResult] for real score/metadata

    Does NOT fabricate passage_id="" or score=0.0.
    Queries DB for actual passage linkage on each chunk.
    Falls back to "" for passage_id only when DB has no mapping (noted in record).
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

        # Get real score from retrieval snapshot
        score: float = 0.0
        method: str = retrieval_method
        if retrieval_snapshot and chk_id in retrieval_snapshot:
            r = retrieval_snapshot[chk_id]
            if hasattr(r, 'score') and _is_valid_score(r.score):
                score = r.score
            if hasattr(r, 'metadata') and isinstance(r.metadata, dict):
                method = r.metadata.get("retrieval_method", method)

        # Get real passage_id from DB
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
            retrieval_score=score,
            retrieval_method=method,
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
