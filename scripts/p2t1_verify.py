#!/usr/bin/env python3
"""P2T1 Verification Script — tests the production V4 research workflow path.

Phase A: AcademicService.synthesize()  →  production workflow path (must pass)
Phase B: Withdraw/restore version       →  citation chain integrity
Phase C: Database consistency           →  FK chain verification

Each phase has a hard timeout. Non-zero exit on failure. Phase output written
immediately to stdout (line-buffered). Final JSON written to output/.
"""
import asyncio, json, logging, os, sys, time, signal

os.chdir("/Users/likeming/Sites/hfb/apps/backend")
sys.path.insert(0, ".")

logging.disable(logging.CRITICAL)

from datetime import datetime, timezone
from sqlalchemy import text
from app.db.database import async_session_factory
from app.services.academic_service import AcademicService
from app.services.trace_lineage import build_internal_traces, TraceLineageError

PHASE_TIMEOUT = 60  # seconds per phase
QUERY = "《针灸甲乙经》的成书特点是什么？"


def with_timeout(coro, timeout=PHASE_TIMEOUT):
    """Wrap a coroutine with asyncio.wait_for."""
    return asyncio.wait_for(coro, timeout=timeout)


# =============================================================================
# Phase A: Production Workflow Path (AcademicService.synthesize + trace lineage)
# =============================================================================


async def phase_a():
    print("[A] === PHASE A: Production research workflow path ===", flush=True)
    results = {}
    async with async_session_factory() as session:
        svc = AcademicService(session)
        t0 = time.time()

        print("[A] Calling AcademicService.synthesize()...", flush=True)
        result = await svc.synthesize(query=QUERY)
        results["academic_type"] = result.academic_type
        results["n_themes"] = len(result.themes)
        results["n_evidence_traces"] = len(result.evidence_trace)
        results["n_citations"] = len(result.citations)
        print(f"[A] Synthesis: themes={results['n_themes']} evidence={results['n_evidence_traces']} citations={results['n_citations']}", flush=True)

        if result.evidence_trace:
            print("[A] Building InternalTraceRecords...", flush=True)
            traces = await build_internal_traces(
                session, result.evidence_trace,
                retrieval_snapshot=svc.last_snapshot,
            )
            results["n_traces"] = len(traces)
            print(f"[A] Built {len(traces)} InternalTraceRecords", flush=True)

            facts = []
            for t in traces[:5]:
                r = await session.execute(text(
                    "SELECT id, page_number, content, passage_id FROM document_chunks WHERE id = :cid AND is_deleted = false"
                ), {"cid": t.chunk_id})
                ch_row = r.fetchone()
                if not ch_row:
                    continue

                r = await session.execute(text(
                    "SELECT id, content_text, version_id, chapter_id FROM passages WHERE id = :pid AND is_deleted = false"
                ), {"pid": t.passage_id})
                ps_row = r.fetchone()

                ver_info = {}
                if ps_row and ps_row[2]:
                    r = await session.execute(text(
                        "SELECT v.id, v.version_name, v.repository, v.shelf_mark, v.source_url,"
                        " v.is_formal_source, v.persistent_identifier, v.withdrawn_at,"
                        " b.id, b.title"
                        " FROM versions v JOIN books b ON v.book_id = b.id"
                        " WHERE v.id = :vid AND v.is_deleted = false"
                    ), {"vid": ps_row[2]})
                    vr = r.fetchone()
                    if vr:
                        ver_info = {
                            "version_id": vr[0], "version_name": vr[1],
                            "repository": vr[2], "shelf_mark": vr[3],
                            "source_url": vr[4], "is_formal_source": vr[5],
                            "persistent_identifier": vr[6],
                            "withdrawn_at": str(vr[7]) if vr[7] else None,
                            "book_id": vr[8], "book_title": vr[9],
                        }

                r = await session.execute(text(
                    "SELECT id, title, pdf_sha256 FROM documents WHERE id = :did AND is_deleted = false"
                ), {"did": t.document_id})
                doc_row = r.fetchone()

                r = await session.execute(text(
                    "SELECT id, url, title FROM source_refs WHERE is_deleted = false AND page_location LIKE :loc"
                ), {"loc": f"%{t.passage_id}%"})
                sr_row = r.fetchone()

                facts.append({
                    "fact_index": len(facts) + 1,
                    "trace_id": t.trace_id,
                    "document_id": t.document_id,
                    "document_title": doc_row[1] if doc_row else None,
                    "pdf_sha256": doc_row[2] if doc_row else None,
                    "chunk_id": t.chunk_id,
                    "page_number": ch_row[1],
                    "passage_id": t.passage_id,
                    "passage_text": (ps_row[1][:100] if ps_row else ""),
                    "retrieval_score": t.retrieval_score,
                    "retrieval_method": t.retrieval_method,
                    **ver_info,
                    "source_ref_id": sr_row[0] if sr_row else None,
                    "source_ref_url": sr_row[1] if sr_row else None,
                })

            results["facts"] = facts
            results["n_facts"] = len(facts)
            results["all_have_page"] = all(f.get("page_number") for f in facts) if facts else False
            results["all_have_pdf"] = all(f.get("pdf_sha256") for f in facts) if facts else False
            results["all_have_version"] = all(f.get("version_id") for f in facts) if facts else False
            results["all_have_source_url"] = all(f.get("source_url") for f in facts) if facts else False
            results["all_have_document"] = all(f.get("document_title") for f in facts) if facts else False

            results["all_pass"] = (
                len(facts) >= 3
                and results["all_have_page"]
                and results["all_have_version"]
                and results["all_have_document"]
            )
        else:
            results["n_traces"] = 0
            results["facts"] = []
            results["all_pass"] = False

        elapsed = time.time() - t0
        results["elapsed_s"] = round(elapsed, 1)
        print(f"[A] PHASE A complete in {elapsed:.1f}s: all_pass={results['all_pass']}", flush=True)
    return results


# =============================================================================
# Phase B: Withdraw version
# =============================================================================


async def phase_b():
    """Test: withdrawing a version blocks trace lineage building.

    The production research workflow uses build_internal_traces() which checks
    version withdrawal. After withdraw, traces must fail. After restore, traces
    must succeed again.
    """
    print("[B] === PHASE B: Withdraw/Restore version ===", flush=True)
    results = {}
    async with async_session_factory() as session:
        # Pick the formal version that actually has chunks linked to it
        r = await session.execute(text("""
            SELECT v.id, v.version_name, count(dc.id) as n_chunks
            FROM versions v
            JOIN passages p ON p.version_id = v.id AND p.is_deleted = false
            JOIN document_chunks dc ON dc.passage_id = p.id AND dc.is_deleted = false
            WHERE v.is_formal_source = true AND v.withdrawn_at IS NULL AND v.is_deleted = false
            GROUP BY v.id, v.version_name
            ORDER BY n_chunks DESC LIMIT 1
        """))
        ver = r.fetchone()
        if not ver:
            results["pass"] = False
            results["error"] = "No formal version found"
            print("[B] SKIP: no formal version available", flush=True)
            return results

        results["version_id"] = ver[0]
        results["version_name"] = ver[1]

        # Baseline: build traces successfully
        svc = AcademicService(session)
        baseline = await svc.synthesize(query=QUERY)
        try:
            traces_before = await build_internal_traces(session, baseline.evidence_trace, retrieval_snapshot=svc.last_snapshot)
            results["traces_before_withdraw"] = len(traces_before)
            print(f"[B] Baseline: {len(traces_before)} traces built", flush=True)
        except TraceLineageError as e:
            print(f"[B] Baseline ERROR (unexpected): {e}", flush=True)
            results["traces_before_withdraw"] = 0

        # Find passages under this version
        r = await session.execute(text(
            "SELECT p.id FROM passages p WHERE p.version_id = :vid AND p.is_deleted = false"
        ), {"vid": ver[0]})
        withdrawn_passages = [row[0] for row in r.fetchall()]
        results["n_withdrawn_passages"] = len(withdrawn_passages)

        # Count chunks affected
        n_affected = 0
        if withdrawn_passages:
            r = await session.execute(text(
                "SELECT count(*) FROM document_chunks WHERE is_deleted = false AND passage_id = ANY(:pids)"
            ), {"pids": withdrawn_passages})
            n_affected = r.scalar()
        results["n_chunks_affected"] = n_affected

        # Withdraw
        now = datetime.now(timezone.utc)
        await session.execute(text(
            "UPDATE versions SET withdrawn_at = :now, withdraw_reason = 'P2T1 withdraw test' WHERE id = :vid"
        ), {"now": now, "vid": ver[0]})
        await session.commit()
        print(f"[B] Withdrawn version {ver[0][:12]} ({n_affected} chunks affected)", flush=True)

        # After withdraw: build_internal_traces must fail
        after_svc = AcademicService(session)
        after_result = await after_svc.synthesize(query=QUERY)
        withdrawn_trace_error = False
        try:
            after_traces = await build_internal_traces(session, after_result.evidence_trace, retrieval_snapshot=after_svc.last_snapshot)
            results["traces_after_withdraw"] = len(after_traces)
            print(f"[B] After withdraw: {len(after_traces)} traces (should be 0)", flush=True)
        except TraceLineageError as e:
            withdrawn_trace_error = True
            results["traces_after_withdraw"] = 0
            print(f"[B] After withdraw: TraceLineageError (correct): {e}", flush=True)

        results["withdraw_blocks_traces"] = withdrawn_trace_error

        # Restore
        await session.execute(text(
            "UPDATE versions SET withdrawn_at = NULL, withdraw_reason = NULL WHERE id = :vid"
        ), {"vid": ver[0]})
        await session.commit()
        print("[B] Restored version", flush=True)

        # After restore: traces must build again
        restore_svc = AcademicService(session)
        restore_result = await restore_svc.synthesize(query=QUERY)
        try:
            restore_traces = await build_internal_traces(session, restore_result.evidence_trace, retrieval_snapshot=restore_svc.last_snapshot)
            results["traces_after_restore"] = len(restore_traces)
            print(f"[B] After restore: {len(restore_traces)} traces built", flush=True)
        except TraceLineageError as e:
            results["traces_after_restore"] = 0
            print(f"[B] After restore ERROR: {e}", flush=True)

        results["pass"] = (
            withdrawn_trace_error
            and results["traces_before_withdraw"] > 0
            and results["traces_after_restore"] >= results["traces_before_withdraw"]
        )
        print(f"[B] PHASE B complete: pass={results['pass']}", flush=True)
    return results


# =============================================================================
# Phase C: Database consistency
# =============================================================================


async def phase_c():
    print("[C] === PHASE C: DB consistency check ===", flush=True)
    results = {}
    async with async_session_factory() as session:
        checks = {}

        r = await session.execute(text(
            "SELECT count(*) FROM document_chunks WHERE is_deleted = false AND (passage_id IS NULL OR passage_id = '')"
        ))
        checks["orphan_chunks"] = r.scalar()
        print(f"[C] Orphan chunks (no passage_id): {checks['orphan_chunks']}", flush=True)

        r = await session.execute(text(
            "SELECT count(*) FROM passages p LEFT JOIN versions v ON p.version_id = v.id AND v.is_deleted = false WHERE p.is_deleted = false AND (p.version_id IS NULL OR v.id IS NULL)"
        ))
        checks["passages_missing_version"] = r.scalar()
        print(f"[C] Passages missing version: {checks['passages_missing_version']}", flush=True)

        r = await session.execute(text(
            "SELECT count(*), count(*) FILTER (WHERE is_formal_source = true) FROM versions WHERE is_deleted = false"
        ))
        row = r.fetchone()
        checks["total_versions"] = row[0]
        checks["formal_versions"] = row[1]
        print(f"[C] Versions: {row[0]} total, {row[1]} formal", flush=True)

        r = await session.execute(text(
            "SELECT count(*), count(*) FILTER (WHERE rag_enabled = true) FROM documents WHERE is_deleted = false"
        ))
        row = r.fetchone()
        checks["total_documents"] = row[0]
        checks["rag_enabled_documents"] = row[1]
        print(f"[C] Documents: {row[0]} total, {row[1]} rag_enabled", flush=True)

        r = await session.execute(text("SELECT count(*) FROM source_refs WHERE is_deleted = false"))
        checks["source_refs"] = r.scalar()
        print(f"[C] SourceRefs: {checks['source_refs']}", flush=True)

        r = await session.execute(text(
            "SELECT count(*) FROM entity_relations WHERE is_deleted = false AND evidence_status = 'verified'"
        ))
        checks["verified_relations"] = r.scalar()
        print(f"[C] Verified relations: {checks['verified_relations']}", flush=True)

        r = await session.execute(text("SELECT count(*) FROM citations WHERE is_deleted = false"))
        checks["db_citations"] = r.scalar()
        print(f"[C] DB Citations: {checks['db_citations']}", flush=True)

        results["checks"] = checks
        results["all_pass"] = (
            checks["orphan_chunks"] == 0
            and checks["passages_missing_version"] == 0
            and checks["formal_versions"] >= 2
            and checks["rag_enabled_documents"] >= 1
        )
        print(f"[C] PHASE C complete: all_pass={results['all_pass']}", flush=True)
    return results


# =============================================================================
# Main — single event loop
# =============================================================================


async def main():
    all_results = {}
    failed = False

    try:
        result_a = await with_timeout(phase_a(), PHASE_TIMEOUT)
        all_results["phase_a"] = result_a
    except asyncio.TimeoutError:
        print("[A] TIMEOUT", flush=True)
        all_results["phase_a"] = {"error": "timeout", "all_pass": False}
        failed = True
    except Exception as e:
        print(f"[A] ERROR: {type(e).__name__}: {e}", flush=True)
        all_results["phase_a"] = {"error": str(e), "all_pass": False}
        failed = True

    try:
        result_b = await with_timeout(phase_b(), PHASE_TIMEOUT)
        all_results["phase_b"] = result_b
    except asyncio.TimeoutError:
        print("[B] TIMEOUT", flush=True)
        all_results["phase_b"] = {"error": "timeout", "pass": False}
        failed = True
    except Exception as e:
        print(f"[B] ERROR: {type(e).__name__}: {e}", flush=True)
        all_results["phase_b"] = {"error": str(e), "pass": False}
        failed = True

    try:
        result_c = await with_timeout(phase_c(), PHASE_TIMEOUT)
        all_results["phase_c"] = result_c
    except asyncio.TimeoutError:
        print("[C] TIMEOUT", flush=True)
        all_results["phase_c"] = {"error": "timeout", "all_pass": False}
        failed = True
    except Exception as e:
        print(f"[C] ERROR: {type(e).__name__}: {e}", flush=True)
        all_results["phase_c"] = {"error": str(e), "all_pass": False}
        failed = True

    # Write output
    out_path = "output/p2t1_verification.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[DONE] Results written to {out_path}", flush=True)

    a_pass = all_results.get("phase_a", {}).get("all_pass", False)
    b_pass = all_results.get("phase_b", {}).get("pass", False)
    c_pass = all_results.get("phase_c", {}).get("all_pass", False)

    print(f"SUMMARY: A={a_pass} B={b_pass} C={c_pass}", flush=True)
    if failed:
        print("FINAL: FAIL (timeout or error)", flush=True)
        return 1
    elif not (a_pass and b_pass and c_pass):
        print("FINAL: FAIL (checks not all passing)", flush=True)
        return 1
    else:
        print("FINAL: PASS", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
