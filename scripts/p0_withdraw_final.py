#!/usr/bin/env python3
"""P0 AcademicRAG Withdraw test — output to /tmp/p0-out/."""
import asyncio
import logging
import os
import sys

os.chdir("/Users/likeming/Sites/hfb/apps/backend")
sys.path.insert(0, ".")
logging.disable(logging.CRITICAL)

from app.db.database import async_session_factory, init_database
from app.services.academic_rag_service import AcademicRAGService
from app.services.ingestion import IngestionService
from sqlalchemy import text


async def main():
    await init_database()
    async with async_session_factory() as session:
        q = "针灸甲乙经的成书特点是什么"
        svc = AcademicRAGService(session)
        r = await session.execute(text(
            "SELECT id FROM documents WHERE raw_pdf_blob IS NOT NULL AND is_deleted=false LIMIT 1"
        ))
        pdf_doc_id = r.scalar_one()
        r = await session.execute(text(
            "SELECT id FROM users WHERE email='admin@huangfumi.org' LIMIT 1"
        ))
        admin_id = r.scalar_one()

        # BEFORE
        print("--- BEFORE ---")
        b = await svc.answer(q)
        print(f"REFUSAL={b.refusal}")
        print(f"CITATIONS={len(b.citations)}")
        print(f"KG_PATHS={len(b.kg_paths)}")
        for i, c in enumerate(b.citations[:5]):
            print(f"  CIT[{i}]: doc={c.document_id[:20] if c.document_id else '?'} "
                  f"chunk={c.chunk_id[:20] if c.chunk_id else '?'} "
                  f"q={c.exact_quote[:40] if c.exact_quote else '?'}")

        # null_sr before
        r = await session.execute(text(
            "SELECT count(*) FROM citations c "
            "JOIN evidences e ON e.id = c.evidence_id "
            "LEFT JOIN source_refs sr ON sr.id = e.source_ref_id "
            "WHERE c.is_deleted = false AND sr.id IS NULL"
        ))
        print(f"NULL_SR_BEFORE={r.scalar()}")

        # WITHDRAW
        print("--- WITHDRAW ---")
        ing = IngestionService(session)
        await ing.withdraw_document(pdf_doc_id, reason="P0 withdraw test", actor_id=admin_id)
        await session.commit()
        r = await session.execute(text(
            "SELECT withdrawn_at FROM documents WHERE id = :did"
        ), {"did": pdf_doc_id})
        wa = r.scalar_one()
        print(f"WITHDRAWN_AT={wa}")

        # AFTER
        print("--- AFTER ---")
        a = await svc.answer(q)
        print(f"REFUSAL={a.refusal}")
        print(f"CITATIONS={len(a.citations)}")
        wd = [c for c in a.citations if c.document_id == pdf_doc_id]
        print(f"WITHDRAWN_DOC_CITATIONS={len(wd)}")
        verdict = "PASS" if (a.refusal or len(a.citations) == 0 or len(wd) == 0) else "FAIL"
        print(f"VERDICT={verdict}")

        if not a.refusal and a.citations:
            for i, c in enumerate(a.citations[:5]):
                print(f"  AFTER_CIT[{i}]: doc={c.document_id[:20] if c.document_id else '?'} "
                      f"q={c.exact_quote[:40] if c.exact_quote else '?'}")

        # RESTORE
        await session.execute(text(
            "UPDATE documents SET withdrawn_at = NULL, rag_enabled = true WHERE id = :did"
        ), {"did": pdf_doc_id})
        await session.commit()
        print("--- RESTORED ---")

        # Final check
        r = await session.execute(text(
            "SELECT count(*) FROM citations c "
            "JOIN evidences e ON e.id = c.evidence_id "
            "LEFT JOIN source_refs sr ON sr.id = e.source_ref_id "
            "WHERE c.is_deleted = false AND sr.id IS NULL"
        ))
        print(f"FINAL_NULL_SR={r.scalar()}")
        print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
