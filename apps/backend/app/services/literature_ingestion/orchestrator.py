"""
Literature ingestion orchestrator — query all sources, deduplicate, persist.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.paper import Paper
from app.services.literature_ingestion import (
    IngestionJob,
    LiteratureItem,
    core_client,
    crossref_client,
    filter_new_items,
    internet_archive_client,
    openalex_client,
    pubmed_client,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SOURCES = {
    "openalex": openalex_client.search,
    "crossref": crossref_client.search,
    "core": core_client.search,
    "pubmed": pubmed_client.search,
    "internet_archive": internet_archive_client.search,
}

QUERIES = [
    "皇甫谧",
    "针灸甲乙经",
    "甲乙经",
    "Huangfu Mi",
    "Zhenjiu Jiayi Jing",
    "A-B Classic of Acupuncture and Moxibustion",
    "Systematic Classic of Acupuncture and Moxibustion",
]

DEFAULT_SOURCES = ["openalex", "crossref", "core", "pubmed", "internet_archive"]
MAX_PAGES = 3  # ponytail: cap pages to avoid runaway API bills


async def ingest(
    session: AsyncSession,
    queries: list[str] | None = None,
    sources: list[str] | None = None,
    max_pages: int = MAX_PAGES,
    enforce_whitelist: bool = True,
) -> list[IngestionJob]:
    """Run ingestion across all queries and sources.

    Args:
        session: DB session.
        queries: Custom search queries (default: pre-defined Huangfu Mi keywords).
        sources: Which sources to query (default: all 5).
        max_pages: Pages per query per source.
        enforce_whitelist: If True (default), reject sources not in the approved
            source_whitelist.yaml. Set False only for dry-run inspection.

    Returns:
        List of IngestionJob logs, one per (source, query) combination.
    """
    queries = queries or QUERIES
    sources = sources or DEFAULT_SOURCES

    # ── Source whitelist runtime gate ──────────────────────────────────────
    gate_jobs: list[IngestionJob] = []
    if enforce_whitelist:
        try:
            from app.services.source_whitelist import get_whitelist

            wl = get_whitelist()
        except (OSError, ValueError):
            # ponytail: if whitelist file is missing, default-deny everything.
            # This guards against accidental production runs without policy.
            wl = None

        filtered: list[str] = []
        for s in sources:
            if wl is None:
                job = IngestionJob(source=s, query="<whitelist gate>")
                job.error_count += 1
                job.errors.append(
                    "SourceWhitelistNotFound: runtime policy unavailable, denying all sources"
                )
                job.finish()
                gate_jobs.append(job)
                continue
            if not wl.is_source_allowed(s, metadata=True):
                job = IngestionJob(source=s, query="<whitelist gate>")
                job.error_count += 1
                job.errors.append(
                    f"SourceNotWhitelisted: {s} is not in the approved source whitelist"
                )
                job.finish()
                gate_jobs.append(job)
                continue
            filtered.append(s)
        sources = filtered
    # ────────────────────────────────────────────────────────────────────────

    jobs: list[IngestionJob] = []

    jobs.extend(gate_jobs)

    for query in queries:
        for src_name in sources:
            job = IngestionJob(source=src_name, query=query)
            job.start()
            try:
                searcher = SOURCES.get(src_name)
                if searcher is None:
                    job.error_count += 1
                    job.errors.append(f"Unknown source: {src_name}")
                    job.finish()
                    jobs.append(job)
                    continue

                await _run_one_source(session, searcher, query, max_pages, job)
            except (SQLAlchemyError, ValueError, RuntimeError) as e:
                job.error_count += 1
                job.errors.append(f"{type(e).__name__}: {e}")
            job.finish()
            jobs.append(job)

    return jobs


async def _run_one_source(
    session: AsyncSession,
    searcher,
    query: str,
    max_pages: int,
    job: IngestionJob,
) -> None:
    all_items: list[LiteratureItem] = []
    seen_keys: set[str] = set()

    for page in range(1, max_pages + 1):
        try:
            items, _total = await searcher(query, page=page)
        except (httpx.HTTPStatusError, httpx.ConnectError, RuntimeError) as e:
            job.error_count += 1
            job.errors.append(f"Page {page}: {type(e).__name__}: {e}")
            continue

        for item in items:
            key = item.dedup_key()
            if key in seen_keys:
                continue
            seen_keys.add(key)
            all_items.append(item)

        if len(items) == 0:
            break

    job.total_found = len(all_items)
    # Filter against existing DB records
    new_items = await filter_new_items(session, all_items)
    job.duplicates_skipped = job.total_found - len(new_items)

    # Persist new items
    await _save_items(session, new_items, job)


async def _save_items(
    session: AsyncSession,
    items: list[LiteratureItem],
    job: IngestionJob,
) -> None:
    added = 0
    for item in items:
        try:
            # Reject items with empty or non-URL source_url
            if not item.source_url.strip():
                job.error_count += 1
                job.errors.append(f"Save {item.title[:80]}: empty source_url")
                continue

            # Check DOI uniqueness again (race-safe within transaction)
            if item.doi:
                stmt = select(Paper.id).where(
                    Paper.doi == item.doi,
                    Paper.is_deleted.is_(False),
                )
                existing = await session.execute(stmt)
                if existing.scalar_one_or_none():
                    continue
            else:
                # Check normalized title+year for non-DOI records
                norm_title = LiteratureItem.normalized_title(item.title)
                stmt = select(Paper.id).where(
                    Paper.is_deleted.is_(False),
                    Paper.year == item.year,
                )
                rows = await session.execute(stmt)
                existing = rows.scalars().all()
                # ponytail: O(n) in-memory check for small result sets
                duplicate = False
                for pid in existing:
                    # Fetch title to compare normalized
                    title_stmt = select(Paper.title).where(Paper.id == pid)
                    title_result = await session.execute(title_stmt)
                    db_title = title_result.scalar_one()
                    if LiteratureItem.normalized_title(db_title) == norm_title:
                        duplicate = True
                        break
                if duplicate:
                    continue

            paper = Paper(
                title=item.title,
                authors=item.authors or None,
                year=item.year,
                abstract=item.abstract or None,
                keywords=item.keywords or None,
                doi=item.doi or None,
                source_url=item.source_url,
                journal=item.journal or None,
                language=item.language,
            )
            session.add(paper)
            added += 1
        except (SQLAlchemyError, ValueError) as e:
            job.error_count += 1
            job.errors.append(f"Save {item.title[:80]}: {type(e).__name__}: {e}")

    try:
        await session.flush()
    except SQLAlchemyError as e:
        job.error_count += 1
        job.errors.append(f"Flush failed: {type(e).__name__}: {e}")
    job.new_added = added
