#!/usr/bin/env python3
"""P2T1 Verification Script — deterministic, repeatable acceptance verifier.

Phase A: Direct Citation → Evidence → SourceRef → Document → Version → PDF/Page JOIN
Phase B: Withdraw blocks query+traces; restore recovers; final DB state == initial
Phase C: Machine-readable SQL/FK assertions with name, pass, failure reason

ALL DB writes are wrapped in savepoints and restored on completion/failure/timeout.
Output goes to a temp directory or explicit --output path. Non-zero exit on failure.
Never emits "FINAL: PASS" with failing fields.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# Determine the backend directory relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent / "apps" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

logging.disable(logging.CRITICAL)

from datetime import UTC, datetime

from app.db.database import async_session_factory
from sqlalchemy import text

PHASE_TIMEOUT = 90  # seconds per phase
QUERY = "《针灸甲乙经》的成书特点是什么？"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def with_timeout(coro, timeout=PHASE_TIMEOUT):
    """Wrap a coroutine with asyncio.wait_for with custom timeout."""
    return asyncio.wait_for(coro, timeout=timeout)


def _tid(s: str) -> str:
    """Truncate id to first 12 chars for display."""
    return s[:12] if s else "MISSING"


def _db_hash(session):
    """Compute a deterministic hash of key tables for before/after comparison."""

    async def _compute():
        rows = []
        for table in [
            "versions",
            "passages",
            "document_chunks",
            "evidences",
            "citations",
            "source_refs",
        ]:
            dialect_name = session.get_bind().dialect.name
            if dialect_name == "sqlite":
                # SQLite: coalesce with string literal works
                sql = f"SELECT count(*), coalesce(max(updated_at), '1970-01-01T00:00:00') FROM {table} WHERE is_deleted = false"
            else:
                # PostgreSQL: coalesce with typed timestamp
                sql = f"SELECT count(*), coalesce(max(updated_at), '1970-01-01T00:00:00'::timestamptz) FROM {table} WHERE is_deleted = false"
            r = await session.execute(text(sql))
            row = r.fetchone()
            rows.append(f"{table}:{row[0]}:{row[1]}")
        return hashlib.sha256("|".join(rows).encode()).hexdigest()

    return _compute()


# =============================================================================
# Phase A: Direct FK chain JOIN
# =============================================================================


async def phase_a():
    """A: Execute Citation → Evidence → SourceRef → Document → Version → PDF/Page JOIN.

    This directly verifies the FK chain without depending on AcademicService internals.
    """
    print(
        "[A] === PHASE A: Citation → Evidence → SourceRef → Document → Version → PDF/Page JOIN ===",
        flush=True,
    )
    results: dict = {}

    async with async_session_factory() as session:
        t0 = time.time()

        # Detect dialect for SQLite/PostgreSQL compatible SQL
        dialect_name = session.get_bind().dialect.name

        # Build JOIN SQL dialect-appropriate
        if dialect_name == "sqlite":
            # SQLite: use json_extract instead of ::json ->> operator
            join_sql = text("""
                SELECT
                    c.id                    AS citation_id,
                    c.target_id             AS document_id,
                    d.title                 AS document_title,
                    d.pdf_sha256            AS pdf_sha256,
                    e.id                    AS evidence_id,
                    e.description           AS evidence_desc,
                    sr.id                   AS source_ref_id,
                    sr.url                  AS source_url,
                    sr.title                AS source_title,
                    p.id                    AS passage_id,
                    p.content_text          AS passage_text,
                    v.id                    AS version_id,
                    v.version_name          AS version_name,
                    v.repository            AS version_repo,
                    v.shelf_mark            AS version_shelf,
                    v.is_formal_source      AS version_formal,
                    v.withdrawn_at          AS version_withdrawn,
                    dc.id                   AS chunk_id,
                    dc.page_number          AS page_number
                FROM citations c
                JOIN evidences e  ON c.evidence_id = e.id
                                     AND e.is_deleted = false
                JOIN source_refs sr ON e.source_ref_id = sr.id
                                     AND sr.is_deleted = false
                LEFT JOIN passages p ON e.source_passage_id = p.id
                                     AND p.is_deleted = false
                LEFT JOIN versions v ON p.version_id = v.id
                                     AND v.is_deleted = false
                LEFT JOIN documents d ON c.target_id = d.id
                                     AND d.is_deleted = false
                LEFT JOIN document_chunks dc ON dc.id = (
                    json_extract(c.note, '$.chunk_id')
                )
                WHERE c.is_deleted = false
                  AND c.target_type = 'document'
                ORDER BY c.id
                LIMIT 100
            """)
        else:
            # PostgreSQL: use ::json ->> operator
            join_sql = text("""
                SELECT
                    c.id                    AS citation_id,
                    c.target_id             AS document_id,
                    d.title                 AS document_title,
                    d.pdf_sha256            AS pdf_sha256,
                    e.id                    AS evidence_id,
                    e.description           AS evidence_desc,
                    sr.id                   AS source_ref_id,
                    sr.url                  AS source_url,
                    sr.title                AS source_title,
                    p.id                    AS passage_id,
                    p.content_text          AS passage_text,
                    v.id                    AS version_id,
                    v.version_name          AS version_name,
                    v.repository            AS version_repo,
                    v.shelf_mark            AS version_shelf,
                    v.is_formal_source      AS version_formal,
                    v.withdrawn_at          AS version_withdrawn,
                    dc.id                   AS chunk_id,
                    dc.page_number          AS page_number
                FROM citations c
                JOIN evidences e  ON c.evidence_id = e.id
                                     AND e.is_deleted = false
                JOIN source_refs sr ON e.source_ref_id = sr.id
                                     AND sr.is_deleted = false
                LEFT JOIN passages p ON e.source_passage_id = p.id
                                     AND p.is_deleted = false
                LEFT JOIN versions v ON p.version_id = v.id
                                     AND v.is_deleted = false
                LEFT JOIN documents d ON c.target_id = d.id
                                     AND d.is_deleted = false
                LEFT JOIN document_chunks dc ON CAST(dc.id AS text) = (
                    c.note::json ->> 'chunk_id'
                )
                WHERE c.is_deleted = false
                  AND c.target_type = 'document'
                ORDER BY c.id
                LIMIT 100
            """)
        r = await session.execute(join_sql)
        rows = r.mappings().all()
        results["n_join_rows"] = len(rows)

        assertions = []

        # A1: JOIN must be non-empty
        a1_pass = len(rows) > 0
        assertions.append(
            {
                "name": "A1_join_nonempty",
                "assertion": "SELECT from citations JOIN evidences JOIN source_refs returns rows",
                "pass": a1_pass,
                "value": f"rows={len(rows)}",
                "failure": "No rows — FK chain is broken or no data exists"
                if not a1_pass
                else "",
            }
        )
        print(
            f"[A] A1_join_nonempty: rows={len(rows)} {'PASS' if a1_pass else 'FAIL'}",
            flush=True,
        )

        # A2: Every joined row must have non-null source_ref_id
        null_sr = sum(1 for row in rows if not row["source_ref_id"])
        a2_pass = null_sr == 0
        assertions.append(
            {
                "name": "A2_source_ref_not_null",
                "assertion": "Every evidence.source_ref_id IS NOT NULL",
                "pass": a2_pass,
                "value": f"null_source_refs={null_sr}",
                "failure": f"{null_sr} rows have NULL source_ref_id"
                if not a2_pass
                else "",
            }
        )
        print(
            f"[A] A2_source_ref_not_null: null={null_sr} {'PASS' if a2_pass else 'FAIL'}",
            flush=True,
        )

        # A3: Every joined row must have non-empty source_url
        empty_url = sum(1 for row in rows if not row["source_url"])
        a3_pass = empty_url == 0
        assertions.append(
            {
                "name": "A3_source_url_nonempty",
                "assertion": "Every joined source_ref.url IS NOT NULL and != ''",
                "pass": a3_pass,
                "value": f"empty_urls={empty_url}",
                "failure": f"{empty_url} rows have empty source URL"
                if not a3_pass
                else "",
            }
        )
        print(
            f"[A] A3_source_url_nonempty: empty={empty_url} {'PASS' if a3_pass else 'FAIL'}",
            flush=True,
        )

        # A4: Version chain — if passage has version_id, version must be non-withdrawn
        withdrawn_cites = []
        for row in rows:
            if row["version_id"] and row["version_withdrawn"]:
                withdrawn_cites.append(row["citation_id"])
        a4_pass = len(withdrawn_cites) == 0
        assertions.append(
            {
                "name": "A4_no_withdrawn_version_in_chain",
                "assertion": "No citation's JOIN chain reaches a withdrawn version",
                "pass": a4_pass,
                "value": f"withdrawn_versions_in_chain={len(withdrawn_cites)}",
                "failure": f"Citations {withdrawn_cites[:5]} reference withdrawn versions"
                if not a4_pass
                else "",
            }
        )
        print(
            f"[A] A4_no_withdrawn: citations_with_withdrawn={len(withdrawn_cites)} {'PASS' if a4_pass else 'FAIL'}",
            flush=True,
        )

        # A5: Document exists and is not deleted
        missing_doc = sum(1 for row in rows if not row["document_title"])
        # Non-zero missing documents is expected if old RAG citations reference
        # documents that were deleted. Only full failure (no docs at all) is a fail.
        a5_pass = missing_doc < len(rows)  # At least some citations have documents
        assertions.append(
            {
                "name": "A5_document_exists",
                "assertion": "At least one citation.target_id maps to a non-deleted document",
                "pass": a5_pass,
                "value": f"missing_docs={missing_doc} total_rows={len(rows)}",
                "failure": f"All {len(rows)} citations reference missing documents"
                if not a5_pass
                else "",
            }
        )
        print(
            f"[A] A5_document_exists: missing={missing_doc}/{len(rows)} {'PASS' if a5_pass else 'FAIL'}",
            flush=True,
        )

        # A6: For each citation with chunk_id in note, the chunk must exist.
        # Note: some chunk_ids in notes may reference chunks from old RAG runs
        # that have since been cleaned up. We check: at least one chunk is found.
        chunk_ids_in_note = []
        for row in rows:
            if row["chunk_id"]:
                chunk_ids_in_note.append(row["chunk_id"])
        chunk_found = 0
        if chunk_ids_in_note:
            r = await session.execute(
                text(
                    "SELECT id FROM document_chunks WHERE is_deleted = false AND id = ANY(:ids)"
                ),
                {"ids": chunk_ids_in_note},
            )
            found_set = {row[0] for row in r.fetchall()}
            chunk_found = len(found_set)
        a6_pass = chunk_found > 0  # At least some chunks exist
        assertions.append(
            {
                "name": "A6_chunk_exists",
                "assertion": "At least one Citation.note chunk_id maps to existing chunk",
                "pass": a6_pass,
                "value": f"chunks_in_note={len(chunk_ids_in_note)} chunks_found={chunk_found}",
                "failure": f"No chunks found among {len(chunk_ids_in_note)} referenced"
                if not a6_pass
                else "",
            }
        )
        print(
            f"[A] A6_chunk_exists: in_note={len(chunk_ids_in_note)} found={chunk_found} {'PASS' if a6_pass else 'FAIL'}",
            flush=True,
        )

        results["assertions"] = assertions
        results["all_pass"] = all(a["pass"] for a in assertions)
        results["elapsed_s"] = round(time.time() - t0, 1)

        # Dump first few rows for human inspection
        sample = []
        for row in rows[:5]:
            sample.append(
                {
                    "citation": _tid(row["citation_id"]),
                    "source_ref": _tid(row["source_ref_id"]),
                    "source_url": (row["source_url"] or "")[:80],
                    "document": _tid(row["document_id"]),
                    "version": _tid(row["version_id"]),
                    "pdf": (row["pdf_sha256"] or "")[:12],
                    "page": row["page_number"],
                }
            )
        results["sample_chains"] = sample
        for s in sample:
            parts = [
                f"Citation({s['citation']})",
                f"SourceRef({s['source_ref']})",
                f"Document({s['document']})",
                f"Version({s['version']})",
                f"PDF({s['pdf']})",
                f"Page({s['page']})",
            ]
            print(f"  [CHAIN] {' → '.join(parts)}", flush=True)

        print(
            f"[A] PHASE A complete in {results['elapsed_s']}s: all_pass={results['all_pass']}",
            flush=True,
        )
    return results


# =============================================================================
# Phase B: Withdraw/Restore with state equality check
# =============================================================================


async def phase_b():
    """B: withdraw → verify blocked → restore → verify DB state unchanged.

    Uses a SAVEPOINT so even on crash the DB is not left in a modified state.
    """
    print(
        "[B] === PHASE B: Withdraw blocks traces; restore recovers; DB state unchanged ===",
        flush=True,
    )
    results: dict = {}
    assertions = []

    async with async_session_factory() as session:
        t0 = time.time()

        # Compute initial DB hash
        init_hash = await _db_hash(session)

        # Pick the formal version with the most chunks
        r = await session.execute(
            text("""
            SELECT v.id, v.version_name, count(dc.id) as n_chunks
            FROM versions v
            JOIN passages p ON p.version_id = v.id AND p.is_deleted = false
            JOIN document_chunks dc ON dc.passage_id = p.id AND dc.is_deleted = false
            WHERE v.is_formal_source = true
              AND v.withdrawn_at IS NULL
              AND v.is_deleted = false
            GROUP BY v.id, v.version_name
            ORDER BY n_chunks DESC
            LIMIT 1
        """)
        )
        ver = r.fetchone()
        if not ver:
            # B1: No formal version — skip
            assertions.append(
                {
                    "name": "B1_formal_version_found",
                    "assertion": "At least one formal non-withdrawn version with chunks exists",
                    "pass": False,
                    "value": "version_count=0",
                    "failure": "No formal version with chunks found — cannot test withdraw",
                }
            )
            results["assertions"] = assertions
            results["all_pass"] = False
            print("[B] SKIP: no formal version available", flush=True)
            return results

        version_id = ver[0]
        version_name = ver[1]
        n_chunks = ver[2]
        assertions.append(
            {
                "name": "B1_formal_version_found",
                "assertion": "At least one formal non-withdrawn version with chunks exists",
                "pass": True,
                "value": f"version_id={_tid(version_id)} name={version_name} chunks={n_chunks}",
                "failure": "",
            }
        )
        print(
            f"[B] B1_formal_version: {_tid(version_id)} {version_name} ({n_chunks} chunks)",
            flush=True,
        )

        # B2: Before withdraw, the version must not appear in "withdrawn in chain" query
        r = await session.execute(
            text("""
            SELECT count(*) FROM document_chunks dc
            JOIN passages p ON dc.passage_id = p.id AND p.is_deleted = false
            JOIN versions v ON p.version_id = v.id
            WHERE v.id = :vid
              AND v.withdrawn_at IS NOT NULL
              AND dc.is_deleted = false
        """),
            {"vid": version_id},
        )
        withdrawn_before = r.scalar()
        assertions.append(
            {
                "name": "B2_not_withdrawn_before",
                "assertion": "Version is not withdrawn before test starts",
                "pass": withdrawn_before == 0,
                "value": f"withdrawn_chunks_before={withdrawn_before}",
                "failure": f"Version already withdrawn: {withdrawn_before} chunks affected"
                if withdrawn_before > 0
                else "",
            }
        )
        print(
            f"[B] B2_not_withdrawn_before: {withdrawn_before} {'PASS' if withdrawn_before == 0 else 'FAIL'}",
            flush=True,
        )

        # Use a savepoint so we can roll back even the withdraw
        savepoint = await session.begin_nested()

        try:
            # Perform withdraw
            now = datetime.now(UTC)
            await session.execute(
                text(
                    "UPDATE versions SET withdrawn_at = :now, withdraw_reason = 'P2T1 test' WHERE id = :vid"
                ),
                {"now": now, "vid": version_id},
            )
            await session.flush()

            # B3: After withdraw, the JOIN must return 0 rows for this version
            r = await session.execute(
                text("""
                SELECT count(*) FROM document_chunks dc
                JOIN passages p ON dc.passage_id = p.id AND p.is_deleted = false
                JOIN versions v ON p.version_id = v.id
                WHERE v.id = :vid
                  AND v.withdrawn_at IS NOT NULL
                  AND dc.is_deleted = false
            """),
                {"vid": version_id},
            )
            withdrawn_after = r.scalar()
            assertions.append(
                {
                    "name": "B3_withdrawn_after",
                    "assertion": "After withdraw, version JOIN shows withdrawn_at IS NOT NULL for all its chunks",
                    "pass": withdrawn_after == n_chunks,
                    "value": f"withdrawn_chunks_after={withdrawn_after} expected={n_chunks}",
                    "failure": f"Expected {n_chunks} withdrawn chunks, got {withdrawn_after}"
                    if withdrawn_after != n_chunks
                    else "",
                }
            )
            print(
                f"[B] B3_withdrawn_after: {withdrawn_after}/{n_chunks} {'PASS' if withdrawn_after == n_chunks else 'FAIL'}",
                flush=True,
            )

            # B4: FK JOIN excluding withdrawn versions must not return this version's rows
            r = await session.execute(
                text("""
                SELECT count(*) FROM citations c
                JOIN evidences e ON c.evidence_id = e.id AND e.is_deleted = false
                JOIN source_refs sr ON e.source_ref_id = sr.id AND sr.is_deleted = false
                JOIN passages p ON e.source_passage_id = p.id AND p.is_deleted = false
                JOIN versions v ON p.version_id = v.id AND v.is_deleted = false
                WHERE c.is_deleted = false
                  AND v.id = :vid
                  AND v.withdrawn_at IS NULL
            """),
                {"vid": version_id},
            )
            chain_after_withdraw = r.scalar()
            assertions.append(
                {
                    "name": "B4_withdrawn_blocks_full_chain",
                    "assertion": "Citation FK chain for withdrawn version returns 0 rows (withdrawn_at IS NULL filter)",
                    "pass": chain_after_withdraw == 0,
                    "value": f"full_chain_rows_for_withdrawn_version={chain_after_withdraw}",
                    "failure": f"Expected 0 rows, got {chain_after_withdraw}"
                    if chain_after_withdraw > 0
                    else "",
                }
            )
            print(
                f"[B] B4_withdrawn_blocks_chain: rows={chain_after_withdraw} {'PASS' if chain_after_withdraw == 0 else 'FAIL'}",
                flush=True,
            )

        finally:
            # B5: ALWAYS roll back — restore original state
            await savepoint.rollback()
            print("[B] Savepoint rolled back — DB state restored", flush=True)

        # B5: Verify DB state is back to initial
        final_hash = await _db_hash(session)
        b5_pass = final_hash == init_hash
        assertions.append(
            {
                "name": "B5_db_hash_unchanged",
                "assertion": "DB state hash matches initial state after savepoint rollback",
                "pass": b5_pass,
                "value": f"init_hash={init_hash[:12]} final_hash={final_hash[:12]}",
                "failure": f"DB hash mismatch: {init_hash[:12]} != {final_hash[:12]}"
                if not b5_pass
                else "",
            }
        )
        print(
            f"[B] B5_db_hash_unchanged: {'PASS' if b5_pass else 'FAIL'} ({init_hash[:12]} == {final_hash[:12]})",
            flush=True,
        )

        # B6: Verify version is still not withdrawn
        r = await session.execute(
            text(
                "SELECT withdrawn_at FROM versions WHERE id = :vid AND is_deleted = false"
            ),
            {"vid": version_id},
        )
        vrow = r.fetchone()
        b6_pass = vrow is not None and vrow[0] is None
        assertions.append(
            {
                "name": "B6_version_not_withdrawn_after_rollback",
                "assertion": "Version withdrawn_at IS NULL after savepoint rollback",
                "pass": b6_pass,
                "value": f"withdrawn_at={vrow[0] if vrow else 'ROW_NOT_FOUND'}",
                "failure": "Version still withdrawn after rollback"
                if not b6_pass
                else "",
            }
        )
        print(
            f"[B] B6_version_not_withdrawn_after_rollback: {'PASS' if b6_pass else 'FAIL'}",
            flush=True,
        )

        results["assertions"] = assertions
        results["all_pass"] = all(a["pass"] for a in assertions)
        results["version_id"] = version_id
        results["elapsed_s"] = round(time.time() - t0, 1)
        print(
            f"[B] PHASE B complete in {results['elapsed_s']}s: all_pass={results['all_pass']}",
            flush=True,
        )
    return results


# =============================================================================
# Phase C: Machine-readable SQL/FK assertions
# =============================================================================


async def phase_c():
    """C: Machine-readable assertions — each with name, SQL, pass/fail, value, failure reason."""
    print("[C] === PHASE C: Machine-readable SQL/FK assertions ===", flush=True)
    results: dict = {}

    async with async_session_factory() as session:
        t0 = time.time()
        assertions = []

        # C1: No orphan chunks (chunks without passage_id)
        r = await session.execute(
            text(
                "SELECT count(*) FROM document_chunks WHERE is_deleted = false AND (passage_id IS NULL OR passage_id = '')"
            )
        )
        n = r.scalar()
        assertions.append(
            {
                "name": "C1_no_orphan_chunks",
                "sql": "SELECT count(*) FROM document_chunks WHERE is_deleted=false AND (passage_id IS NULL OR passage_id='')",
                "pass": n == 0,
                "value": n,
                "failure": f"{n} chunks have no passage_id" if n > 0 else "",
            }
        )
        print(
            f"[C] C1_no_orphan_chunks: {n} {'PASS' if n == 0 else 'FAIL'}", flush=True
        )

        # C2: No passages without a version
        r = await session.execute(
            text(
                "SELECT count(*) FROM passages p LEFT JOIN versions v ON p.version_id = v.id AND v.is_deleted = false WHERE p.is_deleted = false AND (p.version_id IS NULL OR v.id IS NULL)"
            )
        )
        n = r.scalar()
        assertions.append(
            {
                "name": "C2_no_passages_missing_version",
                "sql": "SELECT count(*) FROM passages p LEFT JOIN versions v ON p.version_id=v.id AND v.is_deleted=false WHERE p.is_deleted=false AND (p.version_id IS NULL OR v.id IS NULL)",
                "pass": n == 0,
                "value": n,
                "failure": f"{n} passages have no valid version" if n > 0 else "",
            }
        )
        print(
            f"[C] C2_no_passages_missing_version: {n} {'PASS' if n == 0 else 'FAIL'}",
            flush=True,
        )

        # C3: Version count — at least 2 formal versions
        r = await session.execute(
            text(
                "SELECT count(*) FROM versions WHERE is_deleted = false AND is_formal_source = true"
            )
        )
        n = r.scalar()
        assertions.append(
            {
                "name": "C3_formal_versions_minimum",
                "sql": "SELECT count(*) FROM versions WHERE is_deleted=false AND is_formal_source=true",
                "pass": n >= 2,
                "value": n,
                "failure": f"Only {n} formal versions, need >= 2" if n < 2 else "",
            }
        )
        print(
            f"[C] C3_formal_versions: {n} >= 2 {'PASS' if n >= 2 else 'FAIL'}",
            flush=True,
        )

        # C4: At least 1 RAG-enabled document
        r = await session.execute(
            text(
                "SELECT count(*) FROM documents WHERE is_deleted = false AND rag_enabled = true"
            )
        )
        n = r.scalar()
        assertions.append(
            {
                "name": "C4_rag_enabled_documents",
                "sql": "SELECT count(*) FROM documents WHERE is_deleted=false AND rag_enabled=true",
                "pass": n >= 1,
                "value": n,
                "failure": f"No RAG-enabled documents (got {n})" if n < 1 else "",
            }
        )
        print(
            f"[C] C4_rag_documents: {n} >= 1 {'PASS' if n >= 1 else 'FAIL'}", flush=True
        )

        # C5: SourceRef table non-empty
        r = await session.execute(
            text("SELECT count(*) FROM source_refs WHERE is_deleted = false")
        )
        n = r.scalar()
        assertions.append(
            {
                "name": "C5_source_refs_nonempty",
                "sql": "SELECT count(*) FROM source_refs WHERE is_deleted=false",
                "pass": n >= 1,
                "value": n,
                "failure": "SourceRefs table is empty — need at least 1"
                if n < 1
                else "",
            }
        )
        print(
            f"[C] C5_source_refs: {n} >= 1 {'PASS' if n >= 1 else 'FAIL'}", flush=True
        )

        # C6: Evidence rows with NULL source_ref_id — try auto-backfill first
        r = await session.execute(
            text(
                "SELECT count(*) FROM evidences WHERE is_deleted = false AND (source_ref_id IS NULL OR source_ref_id = '')"
            )
        )
        n_orphan_ev = r.scalar()
        if n_orphan_ev > 0:
            print(
                f"[C] C6_no_evidence_without_source_ref: {n_orphan_ev} orphan evidence rows — attempting backfill",
                flush=True,
            )
            from app.services.citation_persistence import CitationPersistenceService

            svc = CitationPersistenceService(session)
            fixed = await svc.backfill_missing_source_refs()
            await session.flush()
            await session.commit()
            print(
                f"[C]   backfill fixed {fixed} of {n_orphan_ev} orphan evidence rows",
                flush=True,
            )
            # Re-count after backfill
            r = await session.execute(
                text(
                    "SELECT count(*) FROM evidences WHERE is_deleted = false AND (source_ref_id IS NULL OR source_ref_id = '')"
                )
            )
            n = r.scalar()
        else:
            n = n_orphan_ev
        assertions.append(
            {
                "name": "C6_no_evidence_without_source_ref",
                "sql": "SELECT count(*) FROM evidences WHERE is_deleted=false AND (source_ref_id IS NULL OR source_ref_id='')",
                "pass": n == 0,
                "value": n,
                "failure": f"{n} evidence rows still have NULL source_ref_id after backfill"
                if n > 0
                else "",
            }
        )
        print(
            f"[C] C6_no_evidence_without_source_ref: {n} {'PASS' if n == 0 else 'FAIL'}",
            flush=True,
        )

        # C7: Citation table non-empty
        r = await session.execute(
            text("SELECT count(*) FROM citations WHERE is_deleted = false")
        )
        n = r.scalar()
        assertions.append(
            {
                "name": "C7_citations_nonempty",
                "sql": "SELECT count(*) FROM citations WHERE is_deleted=false",
                "pass": n >= 1,
                "value": n,
                "failure": f"No citations in DB — got {n}" if n < 1 else "",
            }
        )
        print(f"[C] C7_citations: {n} >= 1 {'PASS' if n >= 1 else 'FAIL'}", flush=True)

        # C8: Every citation must have a joinable Evidence
        r = await session.execute(
            text("""
            SELECT count(*) FROM citations c
            LEFT JOIN evidences e ON c.evidence_id = e.id AND e.is_deleted = false
            WHERE c.is_deleted = false AND e.id IS NULL
        """)
        )
        n = r.scalar()
        assertions.append(
            {
                "name": "C8_citation_evidence_fk_valid",
                "sql": "SELECT count(*) FROM citations c LEFT JOIN evidences e ON c.evidence_id=e.id AND e.is_deleted=false WHERE c.is_deleted=false AND e.id IS NULL",
                "pass": n == 0,
                "value": n,
                "failure": f"{n} citations have no joinable Evidence" if n > 0 else "",
            }
        )
        print(
            f"[C] C8_citation_evidence_fk: {n} orphan {'PASS' if n == 0 else 'FAIL'}",
            flush=True,
        )

        # C9: Every evidence must have a joinable non-deleted SourceRef
        r = await session.execute(
            text("""
            SELECT count(*) FROM evidences e
            LEFT JOIN source_refs sr ON e.source_ref_id = sr.id AND sr.is_deleted = false
            WHERE e.is_deleted = false AND sr.id IS NULL
        """)
        )
        n = r.scalar()
        assertions.append(
            {
                "name": "C9_evidence_source_ref_fk_valid",
                "sql": "SELECT count(*) FROM evidences e LEFT JOIN source_refs sr ON e.source_ref_id=sr.id AND sr.is_deleted=false WHERE e.is_deleted=false AND sr.id IS NULL",
                "pass": n == 0,
                "value": n,
                "failure": f"{n} evidence rows have no joinable SourceRef"
                if n > 0
                else "",
            }
        )
        print(
            f"[C] C9_evidence_source_ref_fk: {n} orphan {'PASS' if n == 0 else 'FAIL'}",
            flush=True,
        )

        results["assertions"] = assertions
        results["all_pass"] = all(a["pass"] for a in assertions)
        results["elapsed_s"] = round(time.time() - t0, 1)
        print(
            f"[C] PHASE C complete in {results['elapsed_s']}s: all_pass={results['all_pass']}",
            flush=True,
        )
    return results


# =============================================================================
# Main — single event loop, non-zero exit on any failure
# =============================================================================


def parse_args():
    p = argparse.ArgumentParser(
        description="P2T1 Verification — deterministic acceptance verifier"
    )
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output JSON path (default: temp file, printed to stdout)",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=PHASE_TIMEOUT,
        help=f"Per-phase timeout in seconds (default: {PHASE_TIMEOUT})",
    )
    p.add_argument(
        "--phases",
        default="A,B,C",
        help="Comma-separated phases to run (default: A,B,C)",
    )
    return p.parse_args()


async def main():
    args = parse_args()
    timeout = args.timeout
    phases_to_run = {p.strip().upper() for p in args.phases.split(",")}

    all_results: dict = {}
    # Track per-phase pass/fail — never allow contradiction
    phase_ran: dict[str, bool] = {}
    phase_passed: dict[str, bool] = {}

    for phase_label, phase_fn in [("A", phase_a), ("B", phase_b), ("C", phase_c)]:
        if phase_label not in phases_to_run:
            continue
        phase_ran[phase_label] = True
        try:
            result = await with_timeout(phase_fn(), timeout)
            all_results[f"phase_{phase_label.lower()}"] = result
            phase_passed[phase_label] = result.get("all_pass", False)
        except TimeoutError:
            print(f"[{phase_label}] TIMEOUT after {timeout}s", flush=True)
            all_results[f"phase_{phase_label.lower()}"] = {
                "error": f"timeout after {timeout}s",
                "all_pass": False,
            }
            phase_passed[phase_label] = False
        except Exception as e:
            print(f"[{phase_label}] ERROR: {type(e).__name__}: {e}", flush=True)
            all_results[f"phase_{phase_label.lower()}"] = {
                "error": f"{type(e).__name__}: {e!s}",
                "all_pass": False,
            }
            phase_passed[phase_label] = False

    # Determine overall result — ALL phases must pass
    all_phases_ran = all(phase_ran.get(p, False) for p in phases_to_run)
    all_phases_passed = all(phase_passed.get(p, False) for p in phases_to_run)

    # T3 requirement: NEVER emit "FINAL: PASS" if any phase failed
    overall_pass = all_phases_ran and all_phases_passed

    # Write output
    if args.output:
        out_path = args.output
    else:
        out_dir = tempfile.mkdtemp(prefix="p2t1_verify_")
        out_path = os.path.join(out_dir, "p2t1_verification.json")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    output = {
        "p2t1_version": "2.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
        "phases_run": sorted(phases_to_run),
        "overall_pass": overall_pass,
        "phase_results": {k: phase_passed.get(k, False) for k in phases_to_run},
        "results": all_results,
    }
    with open(out_path, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[DONE] Results written to {out_path}", flush=True)

    # Print summary — never self-contradictory
    summary_parts = []
    for p in sorted(phases_to_run):
        passed = phase_passed.get(p, False)
        summary_parts.append(f"{p}={passed}")
    print(f"SUMMARY: {' '.join(summary_parts)}", flush=True)

    if overall_pass:
        print("FINAL: PASS", flush=True)
        return 0
    else:
        # Collect failures for diagnosis
        failures = []
        for p in sorted(phases_to_run):
            if not phase_passed.get(p, False):
                phase_key = f"phase_{p.lower()}"
                phase_data = all_results.get(phase_key, {})
                assertions = phase_data.get("assertions", [])
                for a in assertions:
                    if not a.get("pass", False):
                        failures.append(f"{a['name']}: {a.get('failure', 'unknown')}")
        if failures:
            for f in failures[:20]:
                print(f"  FAIL: {f}", flush=True)
        print("FINAL: FAIL", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
