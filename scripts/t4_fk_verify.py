#!/usr/bin/env python3
"""T4 FK verification helper — checks if a citation ID is resolvable through the full FK chain.

Usage:
  uv run python scripts/t4_fk_verify.py <citation_id> [citation_id ...]

Output: JSON-per-line, one object per citation ID.
  {"status": "FK_OK", "citation_id": "...", "evidence_id": "...", "source_ref_id": "...", "source_url": "...", "document_title": "...", "version_name": "..."}
  {"status": "FK_MISS", "citation_id": "..."}
"""
import asyncio
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent / "apps" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import logging
logging.disable(logging.CRITICAL)

from sqlalchemy import text
from app.db.database import async_session_factory


async def verify_one(citation_id: str) -> dict:
    async with async_session_factory() as session:
        r = await session.execute(text("""
            SELECT c.id, e.id as evidence_id, sr.id as source_ref_id, sr.url,
                   d.title, v.version_name
            FROM citations c
            JOIN evidences e ON c.evidence_id = e.id AND e.is_deleted = false
            JOIN source_refs sr ON e.source_ref_id = sr.id AND sr.is_deleted = false
            LEFT JOIN documents d ON c.target_id = d.id AND d.is_deleted = false
            LEFT JOIN passages p ON e.source_passage_id = p.id AND p.is_deleted = false
            LEFT JOIN versions v ON p.version_id = v.id AND v.is_deleted = false
            WHERE c.is_deleted = false AND c.id = :cid
        """), {"cid": citation_id})
        row = r.fetchone()
        if row:
            return {
                "status": "FK_OK",
                "citation_id": str(row[0]),
                "evidence_id": str(row[1]),
                "source_ref_id": str(row[2]),
                "source_url": (row[3] or ""),
                "document_title": (row[4] or ""),
                "version_name": (row[5] or ""),
            }
        return {"status": "FK_MISS", "citation_id": citation_id}


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/t4_fk_verify.py <citation_id> [...]", file=sys.stderr)
        sys.exit(2)

    for cid in sys.argv[1:]:
        result = await verify_one(cid.strip())
        print(json.dumps(result, default=str))


if __name__ == "__main__":
    asyncio.run(main())
