#!/usr/bin/env python3
"""P0 AcademicRAG Withdraw verification — one-shot script, no intermediate files."""
import asyncio, json, os, sys

_backend_dir = os.path.join(os.path.dirname(__file__), "..", "apps", "backend")
_backend_dir = os.path.abspath(_backend_dir)
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)


async def run_rag(session, query: str) -> dict:
    from app.services.academic_rag_service import AcademicRAGService
    svc = AcademicRAGService(session)
    resp = await svc.answer(query)
    return {
        "refusal": resp.refusal,
        "citations": [
            {
                "citation_id": c.citation_id,
                "document_id": c.document_id,
                "chunk_id": c.chunk_id,
                "evidence_id": c.evidence_id,
                "exact_quote": c.exact_quote[:200],
                "source_uri": c.source_uri,
            }
            for c in resp.citations
        ],
        "kg_path_count": len(resp.kg_paths),
    }


async def main():
    from sqlalchemy import text
    from app.db.database import async_session_factory, init_database

    await init_database()

    async with async_session_factory() as session:
        query = "《针灸甲乙经》的成书特点是什么？"

        # ---- BEFORE ----
        print("=" * 60)
        print("1. BEFORE WITHDRAW — AcademicRAG")
        print("=" * 60)
        before = await run_rag(session, query)
        print(f"  refusal: {before['refusal']}")
        print(f"  citations: {len(before['citations'])}")
        for i, c in enumerate(before["citations"][:10]):
            print(f"  [{i+1}] {c['citation_id'][:16]} doc={c['document_id'][:16]}... quote={c['exact_quote'][:60]}")

        # Get current DB counts
        r = await session.execute(text("SELECT count(*) FROM citations WHERE is_deleted=false"))
        db_before = r.scalar()
        print(f"  DB active citations: {db_before}")

        # Check the zero-source_ref invariant
        r = await session.execute(text(
            "SELECT count(*) FROM citations c JOIN evidences e ON e.id = c.evidence_id "
            "LEFT JOIN source_refs sr ON sr.id = e.source_ref_id "
            "WHERE c.is_deleted = false AND sr.id IS NULL"
        ))
        null_sr = r.scalar()
        print(f"  DB citations with NULL source_ref_id: {null_sr}")

        # ---- WITHDRAW: get target document ----
        r = await session.execute(text(
            "SELECT id FROM documents WHERE raw_pdf_blob IS NOT NULL AND is_deleted=false LIMIT 1"
        ))
        pdf_doc_id = r.scalar_one()
        print(f"\n  Target document for withdraw: {pdf_doc_id}")

        # ---- WITHDRAW ACTION ----
        print("\n" + "=" * 60)
        print("2. WITHDRAW DOCUMENT")
        print("=" * 60)

        from app.services.ingestion import IngestionService
        r = await session.execute(text(
            "SELECT id FROM users WHERE email='admin@huangfumi.org' LIMIT 1"
        ))
        admin_id = r.scalar_one()

        svc = IngestionService(session)
        await svc.withdraw_document(pdf_doc_id, reason="P0 AcademicRAG withdraw test", actor_id=admin_id)
        await session.commit()
        print(f"  Withdrawn document {pdf_doc_id}")

        # Verify document state
        r = await session.execute(text(
            "SELECT withdrawn_at, rag_enabled FROM documents WHERE id=:did"
        ), {"did": pdf_doc_id})
        doc_state = r.fetchone()
        print(f"  withdrawn_at: {doc_state[0]}")
        print(f"  rag_enabled: {doc_state[1]}")

        # ---- AFTER ----
        print("\n" + "=" * 60)
        print("3. AFTER WITHDRAW — AcademicRAG")
        print("=" * 60)
        after = await run_rag(session, query)
        print(f"  refusal: {after['refusal']}")
        print(f"  citations: {len(after['citations'])}")

        # Must have zero citations from the withdrawn document
        withdrawn_citations = [
            c for c in after["citations"]
            if c["document_id"] == pdf_doc_id
        ]
        print(f"  citations from withdrawn doc: {len(withdrawn_citations)}")

        if after["refusal"] or len(after["citations"]) == 0:
            print("  ✓ AcademicRAG refuses or returns empty after withdraw")
        elif len(withdrawn_citations) == 0:
            print("  ✓ No citations reference the withdrawn document")
        else:
            print(f"  ✗ {len(withdrawn_citations)} citations still reference withdrawn doc!")
            for c in withdrawn_citations:
                print(f"    {c['citation_id'][:16]} chunk={c['chunk_id']} quote={c['exact_quote'][:60]}")

        # ---- RESTORE (undo withdraw for subsequent tests) ----
        await session.execute(text(
            "UPDATE documents SET withdrawn_at=NULL, rag_enabled=true WHERE id=:did"
        ), {"did": pdf_doc_id})
        await session.commit()
        print("\n  Restored document (undo withdraw)")

        # ---- FINAL INVARIANT CHECK ----
        r = await session.execute(text(
            "SELECT count(*) FROM citations c JOIN evidences e ON e.id = c.evidence_id "
            "LEFT JOIN source_refs sr ON sr.id = e.source_ref_id "
            "WHERE c.is_deleted = false AND sr.id IS NULL"
        ))
        print(f"\n  Final null source_ref_id count: {r.scalar()} (must be 0)")

        print("\n" + "=" * 60)
        print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
