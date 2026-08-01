"""Passage backfill — idempotent, auditable.
Usage:
    cd apps/backend && DATABASE_URL=sqlite+aiosqlite:////tmp/test.db uv run python scripts/backfill_passage.py

Only maps chunks where:
- chunk has NO existing passage_id
- chunk text, normalized, EXACTLY matches one passage's content_text

Reports: total, mapped_before, newly_mapped, unresolved, ambiguous, orphan_passage_ids.
Repeatable: second run → newly_mapped=0.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend is on path — BACKEND_ROOT is apps/backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


async def backfill(db: AsyncSession | None = None, dry_run: bool = False) -> dict:
    """Run passage backfill. Returns stats dict."""
    close_db = db is None
    if db is None:
        database_url = os.getenv(
            "DATABASE_URL", "sqlite+aiosqlite:////tmp/hfb_backfill.db"
        )
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        session = async_session()
    else:
        session = db

    try:
        stats = await _run_backfill(session, dry_run=dry_run)
    finally:
        if close_db:
            await session.close()
            await engine.dispose()

    return stats


async def _run_backfill(session: AsyncSession, dry_run: bool = False) -> dict:
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.passage import Passage

    # Count total non-deleted chunks
    total_result = await session.execute(
        select(DocumentChunk).where(DocumentChunk.is_deleted.is_(False))
    )
    all_chunks = list(total_result.scalars().all())
    total_chunks = len(all_chunks)

    # Count already-mapped chunks
    mapped_before = sum(1 for c in all_chunks if c.passage_id and c.passage_id.strip())

    # Fetch all non-deleted passages
    p_result = await session.execute(
        select(Passage.id, Passage.content_text).where(Passage.is_deleted.is_(False))
    )
    passages: dict[str, str] = {}
    for row in p_result:
        pid, content = row[0], row[1] or ""
        if pid and content.strip():
            passages[pid] = _normalize(content)

    # Build document metadata lookup
    doc_ids = list({c.document_id for c in all_chunks})
    doc_result = await session.execute(
        select(Document.id, Document.dynasty, Document.title).where(
            Document.id.in_(doc_ids),
            Document.is_deleted.is_(False),
        )
    )
    docs: dict[str, dict] = {}
    for row in doc_result:
        docs[row[0]] = {"dynasty": row[1] or "", "title": row[2] or ""}

    newly_mapped = 0
    unresolved = 0
    ambiguous = 0
    already_mapped = 0

    for chunk in all_chunks:
        if chunk.passage_id and chunk.passage_id.strip():
            already_mapped += 1
            continue

        chunk_norm = _normalize(chunk.content or "")

        # Strategy 1: document metadata records passage_id — only for explicit mapping
        # We don't do fuzzy or heuristic matching.

        # Strategy 2: exact normalized text match against passages
        matches = []
        for pid, ptext in passages.items():
            if chunk_norm == ptext:
                matches.append(pid)

        if len(matches) == 0:
            unresolved += 1
            continue
        elif len(matches) == 1:
            if not dry_run:
                await session.execute(
                    update(DocumentChunk)
                    .where(DocumentChunk.id == chunk.id)
                    .values(passage_id=matches[0])
                )
            newly_mapped += 1
        else:
            ambiguous += 1

    if not dry_run:
        await session.flush()

    # Check orphan passage_ids
    orphan = 0
    pid_result = await session.execute(
        select(DocumentChunk.passage_id)
        .where(
            DocumentChunk.is_deleted.is_(False),
            DocumentChunk.passage_id.isnot(None),
            DocumentChunk.passage_id != "",
        )
        .distinct()
    )
    all_pids = [row[0] for row in pid_result if row[0]]
    if all_pids:
        exist_result = await session.execute(
            select(Passage.id).where(
                Passage.id.in_(all_pids),
                Passage.is_deleted.is_(False),
            )
        )
        existing = {row[0] for row in exist_result}
        orphan = len([p for p in all_pids if p not in existing])

    return {
        "total_chunks": total_chunks,
        "mapped_before": mapped_before,
        "already_mapped": already_mapped,
        "newly_mapped": newly_mapped,
        "unresolved": unresolved,
        "ambiguous": ambiguous,
        "orphan_passage_ids": orphan,
        "dry_run": dry_run,
    }


def _normalize(s: str) -> str:
    """Normalize text for exact matching: collapse whitespace, strip."""
    import re

    return re.sub(r"\s+", " ", s).strip()


if __name__ == "__main__":
    dry_run_flag = "--dry-run" in sys.argv
    stats = asyncio.run(backfill(dry_run=dry_run_flag))
    print(json.dumps(stats, ensure_ascii=False, indent=2))
