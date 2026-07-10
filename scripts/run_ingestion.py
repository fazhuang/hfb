#!/usr/bin/env python3
"""Run literature ingestion — one-off script.

Default: dry-run (fetch only, no DB writes). Use --live to persist.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
os.environ["PYTHONPATH"] = f"{_root}/apps/backend:{_root}/packages:{os.environ.get('PYTHONPATH', '')}"
sys.path.insert(0, f"{_root}/apps/backend")
sys.path.insert(0, f"{_root}/packages")

# noqa: E402 — sys.path manipulation must precede imports
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.services.literature_ingestion.orchestrator import ingest, SOURCES  # noqa: E402

# Verified seed keywords — tested via live Crossref signal-check (2026-07-11).
# Keep 14 terms; each was checked for >=5 results with reasonable precision.
TRIAL_QUERIES = [
    "Huangfu Mi",
    "Zhenjiu Jiayi Jing",
    "皇甫谧",
    "针灸甲乙经",
    "A-B Classic of Acupuncture and Moxibustion",
    "Systematic Classic of Acupuncture and Moxibustion",
    "Huangfu Mi acupuncture",
    "甲乙经 皇甫谧",
    "皇甫谧 针灸甲乙经",
    "黄帝内经 针灸",
    "Wang Tao Waitai Miyao acupuncture",
    "Sun Simiao Qianjin Yaofang acupuncture",
    "Zhang Zhongjing Shanghan Lun acupuncture",
    "early Chinese acupuncture classics",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run literature ingestion")
    p.add_argument("--live", action="store_true",
                   help="Actually write to DB (default: dry-run, no writes)")
    p.add_argument("--source", type=str, choices=list(SOURCES.keys()), default=None)
    p.add_argument("--query", type=str, default=None)
    p.add_argument("--page", type=int, default=1,
                   help="Pages per source per query (default: 1)")
    p.add_argument("--db-url", type=str,
                   default=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///ingestion_run.db"))
    p.add_argument("--json", dest="json_out", action="store_true")
    return p.parse_args()


async def main() -> int:
    args = parse_args()
    queries = [args.query] if args.query else TRIAL_QUERIES
    sources = [args.source] if args.source else list(SOURCES.keys())

    if not args.live:
        return await _dry_run(queries, sources, args)

    engine = create_async_engine(args.db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        jobs = await ingest(session, queries=queries, sources=sources, max_pages=args.page)

        for j in jobs:
            status = "OK" if j.success else "FAIL"
            print(f"[{status}] {j.source:20s} | {j.query[:45]:45s} | "
                  f"found={j.total_found:3d} new={j.new_added:3d} "
                  f"dup={j.duplicates_skipped:3d} errs={j.error_count}")
            for e in j.errors:
                print(f"       └─ {e}")

    if args.json_out:
        print(json.dumps(
            [{"source": j.source, "query": j.query, "success": j.success,
              "total_found": j.total_found, "new_added": j.new_added,
              "duplicates_skipped": j.duplicates_skipped, "error_count": j.error_count,
              "errors": j.errors} for j in jobs],
            ensure_ascii=False, indent=2,
        ))
    return 0


async def _dry_run(queries, sources, args):
    """Fetch from APIs, dedup in memory, report — no DB writes."""
    # noqa: E402 — deferred imports for dry-run path
    from app.services.literature_ingestion import LiteratureItem, IngestionJob  # noqa: E402

    jobs = []
    all_unique: dict[str, LiteratureItem] = {}

    for src_name in sources:
        searcher = SOURCES.get(src_name)
        if searcher is None:
            print(f"[SKIP] Unknown source: {src_name}")
            continue

        for query in queries:
            job = IngestionJob(source=src_name, query=query)
            job.start()

            batch = []
            seen: set[str] = set()

            for page in range(1, args.page + 1):
                try:
                    items, _total = await searcher(query, page=page)
                except Exception as exc:
                    job.error_count += 1
                    job.errors.append(f"Page {page}: {type(exc).__name__}: {exc}")
                    continue

                for item in items:
                    key = item.dedup_key()
                    if key in seen:
                        continue
                    seen.add(key)
                    batch.append(item)

                if len(items) == 0:
                    break

            job.total_found = len(batch)
            new_items = [it for it in batch if it.dedup_key() not in all_unique]
            for it in new_items:
                all_unique[it.dedup_key()] = it
            job.duplicates_skipped = len(batch) - len(new_items)
            job.new_added = len(new_items)
            job.finish()
            jobs.append(job)

            print(f"[{'OK' if job.success else 'FAIL'}] {job.source:20s} | "
                  f"{job.query[:45]:45s} | found={job.total_found:3d} "
                  f"new={job.new_added:3d} dup={job.duplicates_skipped:3d} "
                  f"errs={job.error_count}")

    total_found = sum(j.total_found for j in jobs)
    total_new = sum(j.new_added for j in jobs)
    ok_jobs = sum(1 for j in jobs if j.success)

    print(f"\nDRY-RUN: {ok_jobs}/{len(jobs)} OK, {total_new} unique / {total_found} found. "
          "No data written. Use --live to persist.")

    if args.json_out:
        print(json.dumps({
            "mode": "dry-run", "total_found": total_found, "total_new": total_new,
            "jobs_ok": ok_jobs, "jobs_total": len(jobs),
            "jobs": [{"source": j.source, "query": j.query, "success": j.success,
                      "total_found": j.total_found, "new_added": j.new_added,
                      "duplicates_skipped": j.duplicates_skipped, "error_count": j.error_count,
                      "errors": j.errors} for j in jobs],
            "sample": [{"title": it.title, "source": it.source, "year": it.year,
                        "source_url": it.source_url} for it in list(all_unique.values())[:10]],
        }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
