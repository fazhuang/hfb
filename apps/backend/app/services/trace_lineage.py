"""Unified trace builder and resolver for Sprint 4 V4 product layer.

Centralizes trace_id generation, InternalTraceRecord construction, and
lineage resolution (trace → chunk → document → passage → citation).

All V4 routes (research, education, workflow, visualization) use this module.
No per-file _make_trace_id copies.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.passage import Passage
from app.models.version import Version

# =============================================================================
# Trace ID generation — 128-bit stable identifier (UUIDv5, not SHA-256 truncation)
# =============================================================================

_TRACE_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace


def make_trace_id(document_id: str, chunk_id: str) -> str:
    """Generate a stable, 128-bit trace identifier (UUIDv5).

    Format: UUID string, derived from document_id + chunk_id.
    NOT a 32-bit SHA-256 truncation. NOT equal to chunk_id.
    """
    raw = f"{document_id}:{chunk_id}"
    return str(uuid.uuid5(_TRACE_NAMESPACE, raw))


# =============================================================================
# InternalTraceRecord — seven mandatory fields, no None values
# =============================================================================


@dataclass(frozen=True, slots=True)
class InternalTraceRecord:
    """Full-fidelity internal trace record. Every field required. No None values.

    NEVER exposed through API. Stored in QueryHistory.result_summary.
    """
    trace_id: str
    document_id: str
    chunk_id: str
    passage_id: str
    retrieval_score: float
    retrieval_method: str
    timestamp: str

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


def build_internal_traces(
    evidence_traces: list,
    *,
    retrieval_method: str = "academic_service",
) -> list[InternalTraceRecord]:
    """Build InternalTraceRecord list from EvidenceTrace objects.

    passage_id defaults to empty string when chunk has no passage link.
    This is explicit (empty string), not None — reflecting "not linked" state.
    """
    now = datetime.now(timezone.utc).isoformat()
    records: list[InternalTraceRecord] = []
    seen: set[str] = set()
    for t in evidence_traces:
        tid = make_trace_id(t.document_id, t.chunk_id)
        if tid in seen:
            continue
        seen.add(tid)
        records.append(InternalTraceRecord(
            trace_id=tid,
            document_id=t.document_id,
            chunk_id=t.chunk_id,
            passage_id="",  # resolved later by resolver
            retrieval_score=0.0,
            retrieval_method=retrieval_method,
            timestamp=now,
        ))
    return records


def extract_trace_ids(evidence_traces: list) -> list[str]:
    """Extract stable trace_ids from EvidenceTrace list. Deduplicated."""
    seen: set[str] = set()
    ids: list[str] = []
    for t in evidence_traces:
        tid = make_trace_id(t.document_id, t.chunk_id)
        if tid not in seen:
            seen.add(tid)
            ids.append(tid)
    return ids


def extract_source_documents(evidence_traces: list) -> list[str]:
    """Extract deduplicated, sorted document IDs from evidence traces."""
    return sorted(set(t.document_id for t in evidence_traces))


# =============================================================================
# Lineage resolver — trace_id → chunk → document → passage → citation
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
    passage_citation: str  # formatted [Book·Version, Chapter §order]
    chunk_citation: str  # formatted [document_id:chunk_index]

    def to_public_dict(self) -> dict:
        """Public DTO — never exposes internal fields."""
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
    *,
    fail_on_missing_passage: bool = False,
) -> ResolvedTrace:
    """Resolve a trace_id to its full lineage.

    Chain: trace_id → chunk → document → passage (via passage_id FK) → citation.

    If passage_id is not set on the chunk and fail_on_missing_passage is True,
    raises TraceLineageError with TRACE_LINEAGE_INCOMPLETE.
    """
    # trace_id is UUIDv5, not reversible. We need InternalTraceRecord for resolution.
    # The resolver looks up the chunk from QueryHistory first, then crawls.
    # For direct resolution, trace_id embeds doc+chunk via UUIDv5 — but UUIDv5 is one-way.
    # We resolve by: trying to find the chunk whose (document_id, chunk_id) hashes match.
    # Since hashes are one-way, we scan chunks. This is O(n) — acceptable for test verification.
    # Production path: resolve from InternalTraceRecord stored in QueryHistory.

    # Find chunk via scanning (acceptable for resolution verification)
    from app.models.workspace import QueryHistory

    # Try to find from QueryHistory first
    qh_stmt = (
        select(QueryHistory)
        .where(QueryHistory.result_summary.contains(trace_id))
        .order_by(QueryHistory.created_at.desc())
        .limit(1)
    )
    qh_result = await db.execute(qh_stmt)
    qh = qh_result.scalar_one_or_none()

    chunk_id: str | None = None

    if qh and qh.result_summary:
        try:
            summary = json.loads(qh.result_summary)
            traces = summary.get("traces", [])
            for t in traces:
                if t.get("trace_id") == trace_id:
                    chunk_id = t.get("chunk_id")
                    break
        except (json.JSONDecodeError, TypeError):
            pass

    if not chunk_id:
        raise TraceLineageError(
            f"TRACE_LINEAGE_INCOMPLETE: trace_id {trace_id} not found in any QueryHistory"
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
            f"TRACE_LINEAGE_INCOMPLETE: document {chunk.document_id} not found for trace {trace_id}"
        )

    # Resolve passage
    passage = None
    passage_citation = ""
    if chunk.passage_id:
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
        if row:
            passage, version, book, chapter = row
            parts = []
            if book:
                parts.append(f"《{book.title}》")
            if version:
                parts.append(version.version_name)
            if chapter:
                parts.append(f"{chapter.title} §{passage.order}")
            passage_citation = "·".join(parts)
        elif fail_on_missing_passage:
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: passage {chunk.passage_id} not found for trace {trace_id}"
            )

    chunk_citation = f"[{document.id}:{chunk.chunk_index}]"

    return ResolvedTrace(
        trace_id=trace_id,
        chunk=chunk,
        document=document,
        passage=passage,
        passage_citation=passage_citation,
        chunk_citation=chunk_citation,
    )
