#!/usr/bin/env python3
"""P0 AcademicRAG Withdraw Verification — pure output, no SQL logging."""
import asyncio, sys, os, logging
sys.path.insert(0, '.')
os.chdir('.')
logging.disable(logging.CRITICAL)  # suppress all sqlalchemy noise

from app.db.database import async_session_factory, init_database
from app.services.academic_rag_service import AcademicRAGService
from app.services.ingestion import IngestionService
from sqlalchemy import text

async def main():
    await init_database()
    async with async_session_factory() as session:
        q = "《针灸甲乙经》的成书特点是什么？"
        svc = AcademicRAGService(session)
        r = await session.execute(text(
            "SELECT id FROM documents WHERE raw_pdf_blob IS NOT NULL AND is_deleted=false LIMIT 1"))
        pdf_doc_id = r.scalar_one()
        r = await session.execute(text("SELECT id FROM users WHERE email='admin@huangfumi.org' LIMIT 1"))
        admin_id = r.scalar_one()

        # BEFORE
        print("=" * 60)
        print("BEFORE WITHDRAW")
        before = await svc.answer(q)
        print(f"refusal={before.refusal} citations={len(before.citations)} kg_paths={len(before.kg_paths)}")
        for i,c in enumerate(before.citations[:5]):
            print(f"  cit[{i}] doc={c.document_id[:20]} chunk={c.chunk_id[:20]} quote={c.exact_quote[:60]}")

        r = await session.execute(text(
            "SELECT count(*) FROM citations c JOIN evidences e ON e.id=c.evidence_id "
            "LEFT JOIN source_refs sr ON sr.id=e.source_ref_id "
            "WHERE c.is_deleted=false AND sr.id IS NULL"))
        print(f"null_sr_before={r.scalar()}")

        # WITHDRAW
        print("\nWITHDRAW document")
        ing = IngestionService(session)
        await ing.withdraw_document(pdf_doc_id, reason="P0 withdraw test", actor_id=admin_id)
        await session.commit()
        r = await session.execute(text("SELECT withdrawn_at,rag_enabled FROM documents WHERE id=:did"),{"did":pdf_doc_id})
        w,re = r.fetchone()
        print(f"withdrawn_at={w} rag_enabled={re}")

        # AFTER
        print("\nAFTER WITHDRAW")
        after = await svc.answer(q)
        print(f"refusal={after.refusal} citations={len(after.citations)} kg_paths={len(after.kg_paths)}")
        wd = [c for c in after.citations if c.document_id == pdf_doc_id]
        print(f"withdrawn_doc_citations={len(wd)}")
        print(f"VERDICT={'PASS' if (after.refusal or len(after.citations)==0 or len(wd)==0) else 'FAIL'}")

        # RESTORE
        await session.execute(text(
            "UPDATE documents SET withdrawn_at=NULL,rag_enabled=true WHERE id=:did"),{"did":pdf_doc_id})
        await session.commit()
        r = await session.execute(text(
            "SELECT count(*) FROM citations c JOIN evidences e ON e.id=c.evidence_id "
            "LEFT JOIN source_refs sr ON sr.id=e.source_ref_id "
            "WHERE c.is_deleted=false AND sr.id IS NULL"))
        print(f"\nrestored_doc withdrawn_at=NULL rag_enabled=true")
        print(f"final_null_sr={r.scalar()}")

asyncio.run(main())
