#!/usr/bin/env python3
"""
Data Admission Check — read-only audit of a target database.

Performs a statistical scan and threshold check against known core-object
tables without importing, seeding, generating, or mutating any data.

Usage:
  uv run python scripts/data_admission_check.py --database-url sqlite:////path/to/db.sqlite
  uv run python scripts/data_admission_check.py --database-url postgresql://user:pass@host/db

Exit codes:
  0  PASS              — all thresholds met, all model bindings expressible
  1  FAIL_THRESHOLD    — model bindings are expressible but one or more thresholds not met
  2  BLOCKED_SCHEMA_GAP — the current model cannot express a required binding

The script outputs a stable JSON object to stdout.  All database access is
read-only (SELECT only).  SQLite connections use read-only URI mode.
PostgreSQL connections run in a read-only transaction.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse, parse_qs


# ---------------------------------------------------------------------------
# JSON output helpers
# ---------------------------------------------------------------------------


def _emit(result: dict) -> None:
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------


def _connect(database_url: str):
    """Return a read-only DB-API 2.0 connection.

    SQLite: open with mode=ro + immutable=1 URI query params.
    PostgreSQL: psycopg2 connection with read-only session.
    """
    parsed = urlparse(database_url)

    if parsed.scheme in ("sqlite",):
        # Force read-only URI mode
        qs = parse_qs(parsed.query)
        existing_mode = qs.get("mode", [None])[0]
        if existing_mode and existing_mode != "ro":
            raise SystemExit(
                f"SQLite URI mode={existing_mode!r} — refusing to open as writable. "
                f"Use mode=ro or omit the mode parameter."
            )
        if "mode" not in database_url:
            sep = "&" if parsed.query else ""
            database_url = f"{database_url}{sep}mode=ro"
        # immutable=1 prevents journal/commit files
        if "immutable" not in database_url:
            sep = "&" if ("?" in database_url) else "?"
            database_url = f"{database_url}{sep}immutable=1"

        import sqlite3

        # Remove scheme prefix for file path
        db_path = database_url
        for prefix in ("sqlite:///", "sqlite://"):
            if db_path.startswith(prefix):
                db_path = db_path[len(prefix) :]
                break
        # Strip query params from path
        if "?" in db_path:
            db_path = db_path[: db_path.index("?")]
        conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn

    if parsed.scheme in ("postgresql", "postgres"):
        try:
            import psycopg2  # type: ignore[import-untyped]
        except ImportError:
            raise SystemExit(
                "PostgreSQL support requires psycopg2. Install with: pip install psycopg2-binary"
            )
        conn = psycopg2.connect(database_url)
        conn.set_session(readonly=True, autocommit=False)
        return conn

    raise SystemExit(f"Unsupported database scheme: {parsed.scheme}")


# ---------------------------------------------------------------------------
# Schema gap detection
# ---------------------------------------------------------------------------


def _check_schema_gaps(
    conn,
) -> List[Dict[str, str]]:
    """Return a list of schema gaps — required bindings the current model
    cannot express.
    """
    gaps: List[Dict[str, str]] = []

    # Passage → Citation → Evidence → SourceRef chain:
    #   Evidence.source_passage_id → Passage.id  ✓ (Foreign Key exists)
    #   Evidence.source_ref_id → SourceRef.id    ✓ (Foreign Key exists)
    #   Citation.evidence_id → Evidence.id       ✓ (Foreign Key exists)
    #   SourceRef.url                             ✓ (nullable String(1000))
    #
    # Person   lacks review_status column        ← GAP
    cur = conn.execute("SELECT * FROM persons LIMIT 0")
    person_cols = {d[0].lower() for d in cur.description}
    if "review_status" not in person_cols:
        gaps.append(
            {
                "entity": "Person",
                "missing_field": "review_status",
                "impact": "Person records cannot be filtered by review status; "
                "the 'approved_classical_versions' threshold similarly requires "
                "review_status=approved — Persons have no equivalent quality gate.",
                "workaround": "Persons are counted only (no review/Citation/Evidence "
                "requirements) per 3A contract.",
            }
        )

    return gaps


# ---------------------------------------------------------------------------
# Count queries
# ---------------------------------------------------------------------------


def _counts(conn) -> Dict[str, Any]:
    """Execute all read-only SELECT count queries and return results."""
    counts: Dict[str, Any] = {}

    # Persons — raw count only
    cur = conn.execute("SELECT COUNT(*) AS n FROM persons")
    counts["persons"] = cur.fetchone()[0]

    # ClassicalVersions — approved with source_url
    cur = conn.execute(
        "SELECT COUNT(*) AS n FROM classical_versions "
        "WHERE review_status = 'approved' AND source_url IS NOT NULL AND source_url != ''"
    )
    counts["approved_classical_versions"] = cur.fetchone()[0]

    # Documents — approved, with source_url, rag_enabled
    cur = conn.execute(
        "SELECT COUNT(*) AS n FROM documents "
        "WHERE review_status = 'approved' "
        "AND source_url IS NOT NULL AND source_url != '' "
        "AND rag_enabled = 1"
    )
    counts["approved_rag_documents"] = cur.fetchone()[0]

    # Chapters (for chapter threshold)
    cur = conn.execute("SELECT COUNT(*) AS n FROM chapters")
    counts["chapters"] = cur.fetchone()[0]

    # Passages — total
    cur = conn.execute("SELECT COUNT(*) AS n FROM passages")
    counts["passages_total"] = cur.fetchone()[0]

    # Alignable passages: have a real Passage record with content
    cur = conn.execute(
        "SELECT COUNT(*) AS n FROM passages "
        "WHERE content_text IS NOT NULL AND content_text != ''"
    )
    counts["alignable_passages"] = cur.fetchone()[0]

    # Literature/Documents — total count (for literature_or_collections threshold)
    cur = conn.execute("SELECT COUNT(*) AS n FROM documents")
    counts["documents_total"] = cur.fetchone()[0]

    # Literature or Collections: Documents with source_url
    cur = conn.execute(
        "SELECT COUNT(*) AS n FROM documents "
        "WHERE source_url IS NOT NULL AND source_url != ''"
    )
    counts["documents_with_source_url"] = cur.fetchone()[0]

    # Evidence-bound Passages: Passage must have Citation → Evidence → SourceRef
    # with Evidence.source_passage_id matching Passage.id,
    # Evidence.source_ref_id not null, SourceRef.url not null.
    cur = conn.execute(
        "SELECT COUNT(DISTINCT p.id) AS n "
        "FROM passages p "
        "JOIN evidences e ON e.source_passage_id = p.id "
        "JOIN source_refs sr ON sr.id = e.source_ref_id "
        "JOIN citations c ON c.evidence_id = e.id "
        "WHERE sr.url IS NOT NULL AND sr.url != ''"
    )
    counts["evidence_bound_passages"] = cur.fetchone()[0]

    # Derived: literature_or_collections = documents with source_url
    counts["literature_or_collections"] = counts["documents_with_source_url"]

    return counts


# ---------------------------------------------------------------------------
# Threshold evaluation
# ---------------------------------------------------------------------------


def _evaluate(counts: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate counts against thresholds and return verdict + details."""
    thresholds = {
        "approved_classical_versions": {
            "min": 2,
            "actual": counts["approved_classical_versions"],
        },
        "chapters_or_alignable_passages": {
            "description": "chapters >= 3 OR alignable_passages >= 100",
            "chapters": counts["chapters"],
            "alignable_passages": counts["alignable_passages"],
            "met": counts["chapters"] >= 3 or counts["alignable_passages"] >= 100,
        },
        "persons": {"min": 10, "actual": counts["persons"]},
        "literature_or_collections": {
            "min": 20,
            "actual": counts["literature_or_collections"],
        },
    }

    all_met = True
    failures: List[Dict[str, Any]] = []

    cv = thresholds["approved_classical_versions"]
    if cv["actual"] < cv["min"]:
        all_met = False
        failures.append(
            {
                "threshold": "approved_classical_versions",
                "required": cv["min"],
                "actual": cv["actual"],
                "filter": "review_status=approved, source_url non-empty",
            }
        )

    coa = thresholds["chapters_or_alignable_passages"]
    if not coa["met"]:
        all_met = False
        failures.append(
            {
                "threshold": "chapters_or_alignable_passages",
                "description": "chapters >= 3 OR alignable_passages >= 100",
                "chapters": coa["chapters"],
                "alignable_passages": coa["alignable_passages"],
            }
        )

    p = thresholds["persons"]
    if p["actual"] < p["min"]:
        all_met = False
        failures.append(
            {
                "threshold": "persons",
                "required": p["min"],
                "actual": p["actual"],
                "note": "Person count only — no Citation/Evidence/review_status gate "
                "applied (schema limitation).",
            }
        )

    lc = thresholds["literature_or_collections"]
    if lc["actual"] < lc["min"]:
        all_met = False
        failures.append(
            {
                "threshold": "literature_or_collections",
                "required": lc["min"],
                "actual": lc["actual"],
                "filter": "Documents with source_url",
            }
        )

    # Evidence-bound passages — informational only (not a threshold)
    evidence_bound_info = {
        "evidence_bound_passages": counts["evidence_bound_passages"],
        "note": "Passages with Citation → Evidence → SourceRef chain. "
        "Informational only — not a threshold gate.",
    }

    return {
        "all_met": all_met,
        "thresholds": thresholds,
        "failures": failures if not all_met else [],
        "evidence_bound": evidence_bound_info,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Data Admission Check — read-only audit of target database."
    )
    parser.add_argument(
        "--database-url",
        required=True,
        help="Database connection URL (SQLite or PostgreSQL).",
    )
    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: --database-url is required.", file=sys.stderr)
        sys.exit(2)

    # Connect read-only
    try:
        conn = _connect(args.database_url)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"ERROR: Cannot connect: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        # 1. Schema gap detection
        gaps = _check_schema_gaps(conn)

        # 2. Counts
        counts = _counts(conn)

        # 3. Threshold evaluation
        result = _evaluate(counts)

        # 4. Verdict
        checked_at = datetime.now(timezone.utc).isoformat()

        if gaps:
            verdict = "BLOCKED_SCHEMA_GAP"
            exit_code = 2
        elif not result["all_met"]:
            verdict = "FAIL_THRESHOLD"
            exit_code = 1
        else:
            verdict = "PASS"
            exit_code = 0

        output = {
            "verdict": verdict,
            "counts": counts,
            "thresholds": result["thresholds"],
            "gaps": gaps,
            "failures": result.get("failures", []),
            "evidence_bound": result["evidence_bound"],
            "checked_at": checked_at,
        }
        _emit(output)
        sys.exit(exit_code)

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
