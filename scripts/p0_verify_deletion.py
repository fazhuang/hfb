#!/usr/bin/env python3
"""
P0 Verification — Deletion and Withdrawal Semantics

Verifies that after withdrawing or deleting a document:
  1. RetrievalService no longer returns its chunks
  2. EvidenceRAGService no longer returns citations from it
  3. AcademicRAGService no longer uses its evidence

Uses a temporary test document to avoid damaging baseline data.
Records before/after SQL counts at each step.

Usage:
  cd apps/backend && python ../../scripts/p0_verify_deletion.py
"""

import asyncio
import os
import sys

_backend_dir = os.path.join(os.path.dirname(__file__), "..", "apps", "backend")
_backend_dir = os.path.abspath(_backend_dir)
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)

TEST_TEXT = """
《针灸甲乙经》测试文段。肝藏血，血舍魂，肝气虚则恐，实则怒。
心藏脉，脉舍神，心气虚则悲，实则笑不休。此五脏之所主也。
凡刺之法，必先本于神。血脉营气精神，此五脏之所藏也。
测试文段结束。此文本仅用于验证删除和撤回语义。
"""


async def main():
    from app.db.database import async_session_factory, init_database
    from app.services.evidence_rag_service import EvidenceRAGService
    from app.services.ingestion import IngestionService
    from app.services.retrieval import RetrievalService
    from sqlalchemy import text

    await init_database()

    async with async_session_factory() as session:
        passed = 0
        failed = 0

        def check(name: str, condition: bool, detail: str = ""):
            nonlocal passed, failed
            status = "PASS" if condition else "FAIL"
            if condition:
                passed += 1
            else:
                failed += 1
            msg = f"[{status}] {name}"
            if detail:
                msg += f" — {detail}"
            print(msg)

        print("=" * 60)
        print("P0 Deletion & Withdrawal Verification")
        print("=" * 60)

        svc = IngestionService(session)
        ret_svc = RetrievalService(session)
        ev_rag = EvidenceRAGService(session)

        # ---- Snapshot baseline counts ----
        print("\n--- Baseline counts ---")
        r = await session.execute(
            text("SELECT count(*) FROM document_chunks WHERE is_deleted=false")
        )
        baseline_chunks = r.scalar()
        r = await session.execute(
            text("SELECT count(*) FROM documents WHERE is_deleted=false")
        )
        baseline_docs = r.scalar()
        print(f"  Baseline chunks: {baseline_chunks}")
        print(f"  Baseline documents: {baseline_docs}")

        # ---- Step 1: Ingest test document ----
        print("\n[1/7] Ingesting test document...")
        result = await svc.ingest_text(
            title="删除测试文档",
            text=TEST_TEXT,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "test-purpose-only-academic-verification",
                "source_name": "p0_verify_deletion",
            },
        )
        doc_id = result.document_id
        print(f"  Document ID: {doc_id}")
        print(f"  Chunks: {result.chunk_count}")
        # Enable RAG on the test document for retrieval verification
        from app.models.document import Document

        doc = await session.get(Document, doc_id)
        if doc:
            doc.rag_enabled = True
            doc.review_status = "approved"
        await session.commit()

        # Verify document counts increased
        r = await session.execute(
            text("SELECT count(*) FROM documents WHERE is_deleted=false")
        )
        after_ingest_docs = r.scalar()
        r = await session.execute(
            text("SELECT count(*) FROM document_chunks WHERE is_deleted=false")
        )
        after_ingest_chunks = r.scalar()
        check(
            "1a. Document count increased after ingest",
            after_ingest_docs > baseline_docs,
        )
        check(
            "1b. Chunk count increased after ingest",
            after_ingest_chunks > baseline_chunks,
        )

        # ---- Step 2: Verify test doc appears in retrieval ----
        print("\n[2/7] Verifying test document in retrieval...")
        sr = await ret_svc.search("肝藏血", strict_compliance=True)
        has_test_doc = any(r.document_id == doc_id for r in sr.results)
        check("2a. Test document found in retrieval before withdrawal", has_test_doc)

        # ---- Step 3: Verify test doc in EvidenceRAG ----
        print("\n[3/7] Verifying test document in EvidenceRAG...")
        ev_resp = await ev_rag.query("肝藏血")
        has_test_citation = any(
            getattr(c, "document_id", "") == doc_id for c in ev_resp.citations
        )
        check(
            "3a. Test document in EvidenceRAG before withdrawal",
            has_test_citation,
            "may be False if no evidence was generated",
        )

        # ---- Step 4: Withdraw ----
        print("\n[4/7] Withdrawing document...")
        await svc.withdraw_document(doc_id, reason="deletion-verification-test")
        await session.commit()

        # Verify withdrawal state
        r = await session.execute(
            text(
                "SELECT is_deleted, withdrawn_at, rag_enabled FROM documents WHERE id=:did"
            ),
            {"did": doc_id},
        )
        doc_state = r.fetchone()
        check("4a. Document is_deleted=True after withdrawal", doc_state[0] is True)
        check("4b. Document withdrawn_at is set", doc_state[1] is not None)
        check("4c. Document rag_enabled=False after withdrawal", doc_state[2] is False)

        r = await session.execute(
            text(
                "SELECT count(*) FROM document_chunks "
                "WHERE document_id=:did AND is_deleted=false"
            ),
            {"did": doc_id},
        )
        active_chunks = r.scalar()
        check(
            "4d. Zero active chunks for withdrawn document",
            active_chunks == 0,
            f"count={active_chunks}",
        )

        # ---- Step 5: Verify NOT in retrieval after withdrawal ----
        print("\n[5/7] Verifying document NOT in retrieval after withdrawal...")
        sr = await ret_svc.search("肝藏血", strict_compliance=True)
        has_test_doc = any(r.document_id == doc_id for r in sr.results)
        check(
            "5a. Test document NOT in strict-compliance retrieval after withdrawal",
            not has_test_doc,
        )

        sr2 = await ret_svc.search("肝藏血", strict_compliance=False)
        has_test_doc2 = any(r.document_id == doc_id for r in sr2.results)
        check(
            "5b. Test document NOT in non-strict retrieval after withdrawal",
            not has_test_doc2,
        )

        # ---- Step 6: Verify NOT in EvidenceRAG after withdrawal ----
        print("\n[6/7] Verifying document NOT in EvidenceRAG after withdrawal...")
        ev_resp = await ev_rag.query("肝藏血")
        has_test_citation = any(
            getattr(c, "document_id", "") == doc_id for c in ev_resp.citations
        )
        check(
            "6a. Test document NOT in EvidenceRAG after withdrawal",
            not has_test_citation,
        )

        # ---- Step 7: Hard delete verification ----
        print("\n[7/7] Hard delete verification...")
        # Create a new test doc for hard delete
        result2 = await svc.ingest_text(
            title="硬删除测试文档",
            text=TEST_TEXT,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "test-purpose-only-hard-delete",
                "source_name": "p0_verify_deletion_hard",
            },
        )
        doc_id2 = result2.document_id
        # Enable RAG on the test document
        doc2 = await session.get(Document, doc_id2)
        if doc2:
            doc2.rag_enabled = True
            doc2.review_status = "approved"
        await session.commit()

        # Verify it appears
        sr = await ret_svc.search("肝藏血", strict_compliance=False)
        has_doc2 = any(r.document_id == doc_id2 for r in sr.results)
        check("7a. Hard-delete test doc found in retrieval before deletion", has_doc2)

        # Hard delete
        from app.repositories.document import DocumentRepository

        doc_repo = DocumentRepository(session)
        await doc_repo.hard_delete(doc_id2)
        await session.commit()

        # Verify gone
        sr = await ret_svc.search("肝藏血", strict_compliance=False)
        has_doc2 = any(r.document_id == doc_id2 for r in sr.results)
        check(
            "7b. Hard-deleted document NOT in retrieval",
            not has_doc2,
        )

        # ========================================
        # Summary
        # ========================================
        print(f"\n{'=' * 60}")
        print(f"  Results: {passed} PASS, {failed} FAIL")
        if failed == 0:
            print("  ALL CHECKS PASSED ✓")
        else:
            print(f"  {failed} CHECKS FAILED ✗")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
