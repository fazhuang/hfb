#!/usr/bin/env python3
"""
Trial-run ingestion script — v0.1.0-literature-compliance.

Default: dry-run mode. Prints what WOULD be ingested without touching the DB.
Use --live to actually persist results.

Usage:
    python scripts/trial_run_ingestion.py                # dry-run
    python scripts/trial_run_ingestion.py --live          # real ingest
    python scripts/trial_run_ingestion.py --source openalex --query "Huangfu Mi"
    python scripts/trial_run_ingestion.py --page 1        # single page per source
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# --- Path setup ---
_root = str(Path(__file__).resolve().parent.parent)
os.environ["PYTHONPATH"] = f"{_root}/apps/backend:{_root}/packages:{os.environ.get('PYTHONPATH', '')}"
sys.path.insert(0, f"{_root}/apps/backend")
sys.path.insert(0, f"{_root}/packages")


from app.db.base import Base
from app.services.literature_ingestion.orchestrator import SOURCES, ingest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ============================================================================
# Verified seed keywords — tested via live Crossref signal-check (2026-07-11).
# Each term was checked for >=5 results with reasonable precision.
# ============================================================================
TRIAL_QUERIES = [
    # Core Huangfu Mi terms (narrow, high precision)
    "Huangfu Mi",
    "Zhenjiu Jiayi Jing",
    "皇甫谧",
    "针灸甲乙经",
    # English academic variants
    "A-B Classic of Acupuncture and Moxibustion",
    "Systematic Classic of Acupuncture and Moxibustion",
    "Huangfu Mi acupuncture",
    # Chinese narrow searches
    "甲乙经 皇甫谧",
    "皇甫谧 针灸甲乙经",
    # Cross-reference — traditional Chinese medicine canon
    "黄帝内经 针灸",
    "Wang Tao Waitai Miyao acupuncture",
    "Sun Simiao Qianjin Yaofang acupuncture",
    "Zhang Zhongjing Shanghan Lun acupuncture",
    # Framing query
    "early Chinese acupuncture classics",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Trial-run Huangfu Mi literature ingestion"
    )
    p.add_argument(
        "--live", action="store_true",
        help="Actually write to the database (default: dry-run, no writes)",
    )
    p.add_argument(
        "--source", type=str, choices=list(SOURCES.keys()), default=None,
        help="Limit to a single source (default: all %d)" % len(SOURCES),
    )
    p.add_argument(
        "--query", type=str, default=None,
        help="Run a single query (default: all trial queries)",
    )
    p.add_argument(
        "--page", type=int, default=1,
        help="Pages per source per query (default: 1, for trial scope)",
    )
    p.add_argument(
        "--db-url", type=str,
        default=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///trial_ingestion.db"),
        help="Database URL (default: trial_ingestion.db SQLite)",
    )
    p.add_argument(
        "--json", dest="json_out", action="store_true",
        help="Output JSON only (machine-readable)",
    )
    return p.parse_args()


async def main() -> int:
    args = parse_args()

    queries = [args.query] if args.query else TRIAL_QUERIES
    sources = [args.source] if args.source else list(SOURCES.keys())

    if not args.live and not args.json_out:
        print("=" * 72)
        print("  TRIAL RUN — DRY MODE")
        print("  No data will be written to the database.")
        print("  Use --live to persist results.")
        print("=" * 72)
        print()
        print(f"  Sources : {', '.join(sources)}")
        print(f"  Queries : {len(queries)} terms")
        print(f"  Pages   : {args.page} per query per source")
        print(f"  Est API calls: {len(queries) * len(sources) * args.page}")
        print()
        if args.db_url.startswith("sqlite"):
            print(f"  DB      : {args.db_url} (auto-created SQLite)")
        else:
            print(f"  DB      : {args.db_url}")
        print()

    # --- Dry run: collect items without persisting ---
    if not args.live:
        return await _dry_run(queries, sources, args)

    # --- Live run: use real DB ---
    return await _live_run(queries, sources, args)


async def _dry_run(
    queries: list[str],
    sources: list[str],
    args: argparse.Namespace,
) -> int:
    """Simulate ingestion — fetch from APIs, dedup in memory, report only."""

    from app.services.literature_ingestion import (
        IngestionJob,
        LiteratureItem,
    )

    jobs: list[IngestionJob] = []
    all_unique: dict[str, LiteratureItem] = {}

    for src_name in sources:
        searcher = SOURCES.get(src_name)
        if searcher is None:
            print(f"[SKIP] Unknown source: {src_name}")
            continue

        for query in queries:
            job = IngestionJob(source=src_name, query=query)
            job.start()

            batch: list[LiteratureItem] = []
            seen_in_batch: set[str] = set()

            for page in range(1, args.page + 1):
                try:
                    items, _total = await searcher(query, page=page)
                except Exception as exc:
                    job.error_count += 1
                    job.errors.append(f"Page {page}: {type(exc).__name__}: {exc}")
                    continue

                for item in items:
                    key = item.dedup_key()
                    if key in seen_in_batch:
                        continue
                    seen_in_batch.add(key)
                    batch.append(item)

                if len(items) == 0:
                    break

            job.total_found = len(batch)
            # Cross-source dedup
            new_items = [it for it in batch if it.dedup_key() not in all_unique]
            for it in new_items:
                all_unique[it.dedup_key()] = it
            job.duplicates_skipped = len(batch) - len(new_items)
            job.new_added = len(new_items)
            job.finish()
            jobs.append(job)

            if not args.json_out:
                status = "OK" if job.success else "FAIL"
                dup_info = f"dup={job.duplicates_skipped}" if job.duplicates_skipped else ""
                print(
                    f"  [{status}] {job.source:20s} | {job.query[:45]:45s} | "
                    f"found={job.total_found:3d} new={job.new_added:3d} "
                    f"{dup_info} errs={job.error_count}"
                )

    # Summary
    total_found = sum(j.total_found for j in jobs)
    total_new = sum(j.new_added for j in jobs)
    total_dup = sum(j.duplicates_skipped for j in jobs)
    total_err = sum(1 for j in jobs if j.error_count > 0)
    ok_jobs = sum(1 for j in jobs if j.success)

    if not args.json_out:
        print()
        print("-" * 72)
        print("  DRY-RUN SUMMARY")
        print(f"  Total found    : {total_found}")
        print(f"  New (unique)   : {total_new}")
        print(f"  Duplicates     : {total_dup}")
        print(f"  Jobs OK        : {ok_jobs}/{len(jobs)}")
        print(f"  Jobs with errs : {total_err}")
        print(f"  Unique keys    : {len(all_unique)}")
        print(f"  Sources        : {len(sources)}")
        print(f"  Queries        : {len(queries)}")
        print("-" * 72)
        print()
        print("  DRY-RUN: No data was persisted. Use --live to write to DB.")
        print()

        # Show sample results
        if all_unique:
            print("  Sample items (first 10):")
            for i, (key, item) in enumerate(list(all_unique.items())[:10]):
                yr = f" ({item.year})" if item.year else ""
                print(f"    {i+1}. [{item.source}] {item.title[:80]}{yr}")
                print(f"       {item.source_url}")

        # Print errors
        errored = [j for j in jobs if j.error_count > 0]
        if errored:
            print()
            print(f"  Errors ({len(errored)} jobs):")
            for j in errored:
                for e in j.errors:
                    print(f"    [{j.source}] {j.query}: {e}")

    if args.json_out:
        print(json.dumps({
            "mode": "dry-run",
            "total_found": total_found,
            "total_new": total_new,
            "total_duplicates": total_dup,
            "jobs_ok": ok_jobs,
            "jobs_total": len(jobs),
            "jobs_with_errors": total_err,
            "unique_keys": len(all_unique),
            "sources": sources,
            "queries": queries,
            "jobs": [
                {
                    "source": j.source,
                    "query": j.query,
                    "success": j.success,
                    "total_found": j.total_found,
                    "new_added": j.new_added,
                    "duplicates_skipped": j.duplicates_skipped,
                    "error_count": j.error_count,
                    "errors": j.errors,
                }
                for j in jobs
            ],
            "sample": [
                {"title": it.title, "source": it.source, "year": it.year, "source_url": it.source_url}
                for it in list(all_unique.values())[:10]
            ],
        }, ensure_ascii=False, indent=2))

    return 0 if total_err == 0 else 1


async def _live_run(
    queries: list[str],
    sources: list[str],
    args: argparse.Namespace,
) -> int:
    """Real ingestion — creates DB tables and persists results."""
    t0 = time.monotonic()

    engine = create_async_engine(args.db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if "sqlite" in args.db_url:
            await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        jobs = await ingest(
            session,
            queries=queries,
            sources=sources,
            max_pages=args.page,
        )

        for j in jobs:
            status = "OK" if j.success else "FAIL"
            print(
                f"[{status}] {j.source:20s} | {j.query[:45]:45s} | "
                f"found={j.total_found:3d} new={j.new_added:3d} "
                f"dup={j.duplicates_skipped:3d} errs={j.error_count}"
            )
            for e in j.errors:
                print(f"       └─ {e}")

    elapsed = time.monotonic() - t0
    total_new = sum(j.new_added for j in jobs)
    ok_jobs = sum(1 for j in jobs if j.success)

    print(f"\nLive run complete: {ok_jobs}/{len(jobs)} OK, {total_new} new records in {elapsed:.1f}s")

    if args.json_out:
        print(json.dumps(
            [{
                "source": j.source, "query": j.query,
                "success": j.success, "total_found": j.total_found,
                "new_added": j.new_added, "duplicates_skipped": j.duplicates_skipped,
                "error_count": j.error_count, "errors": j.errors,
            } for j in jobs],
            ensure_ascii=False, indent=2,
        ))

    return 0 if all(j.success for j in jobs) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
