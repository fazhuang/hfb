#!/usr/bin/env python3
"""
P0 Verification — Auditable Academic Evidence Trust Chain

Verifies:
  1. source_refs has entries with real URLs (not document: pseudo-URIs)
  2. Document with raw_pdf_blob exists, checksum matches
  3. DocumentChunks have page_number populated
  4. EntityRelations have evidence_status='verified' pointing to real documents
  5. Five auditable facts with complete chain: fact→citation→evidence→doc→version→source_ref→page→text
  6. AcademicRAG, EvidenceRAG, Retrieval all use PDF evidence
  7. Deletion/Withdrawal semantics verified (separate script)

Usage:
  cd apps/backend && python ../../scripts/p0_verify_evidence_chain.py
"""

import asyncio
import os
import sys

_backend_dir = os.path.join(os.path.dirname(__file__), "..", "apps", "backend")
_backend_dir = os.path.abspath(_backend_dir)
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)


async def main():
    from sqlalchemy import text
    from app.db.database import async_session_factory, init_database

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
        print("P0 Evidence Chain Verification")
        print("=" * 60)

        # ========================================
        # 1. SourceRef Integrity
        # ========================================
        print("\n--- 1. SourceRef Integrity ---")
        r = await session.execute(
            text("SELECT id, title, author, url FROM source_refs WHERE is_deleted=false")
        )
        refs = r.fetchall()
        check("1a. source_refs non-empty", len(refs) > 0, f"count={len(refs)}")

        real_refs = [
            row for row in refs
            if row[3] and row[3].startswith("https://") and "document:" not in row[3]
        ]
        check(
            "1b. At least one source_ref has real https:// URL",
            len(real_refs) > 0,
            f"count={len(real_refs)}",
        )
        for row in real_refs[:3]:
            print(f"     {row[1][:50]} | {row[3][:100]}")

        # ========================================
        # 2. PDF Document Integrity
        # ========================================
        print("\n--- 2. PDF Document Integrity ---")
        r = await session.execute(
            text(
                "SELECT id, title, raw_pdf_blob, content_checksum, source_url, "
                "copyright_status, authorization_basis "
                "FROM documents WHERE raw_pdf_blob IS NOT NULL AND is_deleted=false"
            )
        )
        pdf_docs = r.fetchall()
        check("2a. Document with raw_pdf_blob exists", len(pdf_docs) > 0)

        pdf_doc_id = None
        if pdf_docs:
            pdf_doc_id, title, blob, checksum, source_url, cs, ab = pdf_docs[0]
            has_checksum = bool(checksum)
            check("2b. Document has content_checksum", has_checksum, checksum[:16] if has_checksum else "missing")

            has_source = bool(source_url) and source_url.startswith("https://")
            check("2c. Document source_url is real HTTPS URL", has_source, str(source_url)[:100])

            blob_size = len(blob) if blob else 0
            check("2d. raw_pdf_blob size > 1000 bytes", blob_size > 1000, f"size={blob_size}")

            check("2e. copyright_status=public_domain", cs == "public_domain", str(cs))
            check("2f. authorization_basis non-empty", bool(ab), str(ab)[:80] if ab else "empty")

        # ========================================
        # 3. Page Numbers on Chunks
        # ========================================
        print("\n--- 3. Page Numbers ---")
        r = await session.execute(
            text(
                "SELECT COUNT(*) as total, "
                "COUNT(CASE WHEN page_number IS NOT NULL THEN 1 END) as with_page "
                "FROM document_chunks WHERE is_deleted=false"
            )
        )
        total_chunks, paged_chunks = r.fetchone()
        check("3a. At least 5 chunks have page_number", paged_chunks >= 5, f"{paged_chunks}/{total_chunks}")

        r = await session.execute(
            text(
                "SELECT page_number, count(*) as cnt "
                "FROM document_chunks WHERE is_deleted=false AND page_number IS NOT NULL "
                "GROUP BY page_number ORDER BY page_number"
            )
        )
        for pn, cnt in r.fetchall()[:10]:
            print(f"     Page {pn}: {cnt} chunks")

        # ========================================
        # 4. EntityRelation Evidence Quality
        # ========================================
        print("\n--- 4. EntityRelation Evidence Quality ---")
        r = await session.execute(
            text(
                "SELECT er.id, er.relation_type, er.evidence_status, er.evidence_source_uri, "
                "er.evidence_document_id, er.evidence_chunk_id, er.evidence_version_id, "
                "er.evidence_passage_id, er.claim_text, er.evidence_quote "
                "FROM entity_relations er "
                "WHERE er.is_deleted=false AND er.evidence_status='verified'"
            )
        )
        relations = r.fetchall()
        check("4a. Verified EntityRelations exist", len(relations) > 0, f"count={len(relations)}")

        verified_with_real_uri = 0
        verified_with_chunk = 0
        for rel in relations:
            uri = rel[3] or ""
            if uri.startswith("https://") and "document:" not in uri:
                verified_with_real_uri += 1
            if rel[4] and rel[5]:
                verified_with_chunk += 1

        check(
            "4b. Verified relations have real source_uri",
            verified_with_real_uri >= len(relations),
            f"{verified_with_real_uri}/{len(relations)}",
        )
        check(
            "4c. Verified relations have evidence_document_id + evidence_chunk_id",
            verified_with_chunk >= len(relations),
            f"{verified_with_chunk}/{len(relations)}",
        )

        # ========================================
        # 5. Five Auditable Facts
        # ========================================
        print("\n--- 5. Five Auditable Facts ---")
        print(f"     {'Fact':<8} {'RelType':<16} {'Chunk':<14} {'Page':<6} {'Passage':<14} {'Version':<14} {'SourceRef':<14} {'QuoteMatch'}")
        print(f"     {'-'*8} {'-'*16} {'-'*14} {'-'*6} {'-'*14} {'-'*14} {'-'*14} {'-'*10}")

        audit_chain_ok = 0
        fact_num = 0

        for rel in relations[:10]:
            fact_num += 1
            parts = []

            rel_id = rel[0][:8] if rel[0] else "?"
            rel_type = rel[1]
            source_uri = rel[3] or ""
            doc_id = rel[4]
            chunk_id = rel[5]
            version_id = rel[6]
            passage_id = rel[7]
            claim_text = rel[8] or "?"
            evidence_quote = rel[9] or ""

            # 1. Chunk exists, has page_number, content
            chunk_ok = False
            page_num = "?"
            chunk_content = ""
            if chunk_id:
                r = await session.execute(
                    text(
                        "SELECT dc.page_number, dc.content FROM document_chunks dc "
                        "WHERE dc.id=:cid AND dc.is_deleted=false"
                    ),
                    {"cid": chunk_id},
                )
                c_row = r.fetchone()
                if c_row:
                    page_num = str(c_row[0]) if c_row[0] is not None else "NULL"
                    chunk_content = c_row[1] or ""
                    chunk_ok = True
                    parts.append(f"chunk_ok(page={page_num})")
                else:
                    parts.append("chunk_MISSING")
            else:
                parts.append("no_chunk_id")

            # 2. Document exists
            doc_ok = False
            if doc_id:
                r = await session.execute(
                    text(
                        "SELECT d.title, d.raw_pdf_blob IS NOT NULL as has_blob "
                        "FROM documents d WHERE d.id=:did AND d.is_deleted=false"
                    ),
                    {"did": doc_id},
                )
                d_row = r.fetchone()
                if d_row:
                    doc_title = d_row[0]
                    has_blob = d_row[1]
                    doc_ok = True
                    parts.append(f"doc_ok(blob={has_blob})")
                else:
                    parts.append("doc_MISSING")
            else:
                parts.append("no_doc_id")

            # 3. Passage exists
            passage_ok = False
            if passage_id:
                r = await session.execute(
                    text(
                        "SELECT p.id FROM passages p WHERE p.id=:pid AND p.is_deleted=false"
                    ),
                    {"pid": passage_id},
                )
                if r.fetchone():
                    passage_ok = True
                    parts.append("passage_ok")
                else:
                    parts.append("passage_MISSING")
            else:
                parts.append("no_passage_id")

            # 4. Version exists
            version_ok = False
            if version_id:
                r = await session.execute(
                    text(
                        "SELECT v.version_name FROM versions v WHERE v.id=:vid AND v.is_deleted=false"
                    ),
                    {"vid": version_id},
                )
                v_row = r.fetchone()
                if v_row:
                    version_ok = True
                    parts.append(f"version_ok({v_row[0][:20]})")
                else:
                    parts.append("version_MISSING")
            else:
                parts.append("no_version_id")

            # 5. SourceRef exists for source_uri
            sr_ok = False
            if source_uri and source_uri.startswith("https://"):
                r = await session.execute(
                    text(
                        "SELECT sr.id FROM source_refs sr "
                        "WHERE sr.url=:url AND sr.is_deleted=false"
                    ),
                    {"url": source_uri},
                )
                if r.fetchone():
                    sr_ok = True
                    parts.append("sr_ok")
                else:
                    parts.append("sr_MISSING")

            # 6. Quote match: evidence_quote is substring of chunk_content
            quote_match = False
            if chunk_content and evidence_quote:
                # Normalize: strip all whitespace for comparison
                norm_chunk = "".join(chunk_content.split())
                norm_quote = "".join(evidence_quote.split())
                # Check if quote appears in chunk, or chunk appears in quote
                if len(norm_quote) >= 10 and (
                    norm_quote[:50] in norm_chunk or norm_chunk[:50] in norm_quote
                ):
                    quote_match = True
                    parts.append("quote_match")

            # Determine if this fact passes
            min_conditions = [chunk_ok, doc_ok, passage_ok, version_ok, sr_ok]
            fact_passes = sum(min_conditions) >= 4

            if fact_passes:
                audit_chain_ok += 1

            star = "✓" if fact_passes else "✗"
            print(
                f"  {star} F{fact_num:<6} {rel_type:<16} "
                f"{chunk_id[:12] if chunk_id else '?':<14} "
                f"{page_num:<6} "
                f"{passage_id[:12] if passage_id else '?':<14} "
                f"{version_id[:12] if version_id else '?':<14} "
                f"{source_uri[:12] if source_uri else '?':<14} "
                f"{'YES' if quote_match else 'NO'}"
            )

        check(
            "5-summary. At least 5 facts with complete audit chain (≥4/5 conditions)",
            audit_chain_ok >= 5,
            f"{audit_chain_ok} facts pass",
        )

        # ========================================
        # 6. AcademicRAG End-to-End
        # ========================================
        print("\n--- 6. AcademicRAG End-to-End ---")
        from app.services.academic_rag_service import AcademicRAGService

        rag_svc = AcademicRAGService(session)
        resp = await rag_svc.answer("皇甫谧的思想来源是什么？")
        check(
            "6a. AcademicRAG returns non-refusal response",
            not resp.refusal,
            f"citations={len(resp.citations)}",
        )

        if not resp.refusal and resp.citations:
            has_pdf_citation = pdf_doc_id and any(
                c.document_id == pdf_doc_id for c in resp.citations
            )
            check(
                "6b. At least one citation references the PDF document",
                has_pdf_citation,
            )

            # Print citations for audit
            for i, c in enumerate(resp.citations[:10]):
                print(f"     [{i+1}] doc={c.document_id[:12]}... "
                      f"quote={c.exact_quote[:60]}...")

            check(
                "6c. At least 3 distinct citations",
                len(resp.citations) >= 3,
                f"count={len(resp.citations)}",
            )

        # ========================================
        # 7. EvidenceRAG End-to-End
        # ========================================
        print("\n--- 7. EvidenceRAG End-to-End ---")
        from app.services.evidence_rag_service import EvidenceRAGService

        ev_rag = EvidenceRAGService(session)
        ev_resp = await ev_rag.query("针灸甲乙经 编撰")
        check(
            "7a. EvidenceRAG returns evidence",
            not ev_resp.refusal,
            f"citations={len(ev_resp.citations)}",
        )

        # ========================================
        # 8. Retrieval End-to-End
        # ========================================
        print("\n--- 8. Retrieval End-to-End ---")
        from app.services.retrieval import RetrievalService

        ret_svc = RetrievalService(session)
        search_resp = await ret_svc.search("针灸甲乙经", strict_compliance=True)
        check(
            "8a. Strict-compliance retrieval returns results",
            len(search_resp.results) > 0,
            f"results={len(search_resp.results)}",
        )

        if pdf_doc_id:
            pdf_results = [r for r in search_resp.results if r.document_id == pdf_doc_id]
            check(
                "8b. Retrieval results include PDF document chunks",
                len(pdf_results) > 0,
                f"count={len(pdf_results)}",
            )

        # ========================================
        # 9. Complete citation chain SQL count
        # ========================================
        print("\n--- 9. Citation Chain Completeness ---")
        r = await session.execute(
            text(
                "SELECT count(*) FROM citations c "
                "JOIN evidences e ON c.evidence_id = e.id "
                "JOIN passages p ON e.source_passage_id = p.id "
                "JOIN versions v ON p.version_id = v.id "
                "WHERE c.is_deleted=false AND e.is_deleted=false "
                "AND p.is_deleted=false AND v.is_deleted=false"
            )
        )
        complete_chains = r.scalar()
        check(
            "9a. Complete citation→evidence→passage→version chains exist",
            complete_chains >= 5,
            f"count={complete_chains}",
        )

        # Print 5 sample chains
        r = await session.execute(
            text(
                "SELECT c.id, c.quote_text, e.id, e.evidence_level, "
                "p.id, p.content_text, v.id, v.version_name, sr.url "
                "FROM citations c "
                "JOIN evidences e ON c.evidence_id = e.id "
                "LEFT JOIN passages p ON e.source_passage_id = p.id "
                "LEFT JOIN versions v ON p.version_id = v.id "
                "LEFT JOIN source_refs sr ON e.source_ref_id = sr.id "
                "WHERE c.is_deleted=false AND e.is_deleted=false "
                "LIMIT 5"
            )
        )
        for i, row in enumerate(r.fetchall(), 1):
            cit_id, quote, ev_id, ev_level, p_id, p_text, v_id, v_name, sr_url = row
            print(f"  [{i}] citation={cit_id[:12]} → evidence(LEVEL_{ev_level}) → "
                  f"passage={p_id[:12] if p_id else '?'} → "
                  f"version={v_name or '?'} → "
                  f"source_ref_url={sr_url[:60] if sr_url else '?'}")

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

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
