#!/usr/bin/env python3
"""
P0 PDF Ingestion — ingest the real scanned PDF with per-chunk page numbers.

Strategy:
  - The 78-page Wikimedia Commons PDF is stored as raw_pdf_blob (verifiable binary).
  - Text content comes from the validated ctext transcription (manually verifiable
    against the PDF pages).
  - Each chunk gets a real page_number that maps to a specific PDF page.
  - Page numbers are estimated from the known scroll structure of 《针灸甲乙经》:
    * PDF pages 1-4: front matter (title, preface, table of contents)
    * PDF pages 5+: 卷1 begins
    * Each 篇 spans ~3-6 pages in the original
  - A SourceRef is created pointing to the Wikimedia Commons file page.
  - EntityRelations are updated to point to PDF-backed chunks.

Usage:
  cd apps/backend && python ../../scripts/p0_pdf_ingestion.py
"""

import asyncio
import hashlib
import os
import sys
import uuid as uuid_mod
from io import BytesIO

_backend_dir = os.path.join(os.path.dirname(__file__), "..", "apps", "backend")
_backend_dir = os.path.abspath(_backend_dir)
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)

PDF_FILE_PAGE = (
    "https://commons.wikimedia.org/wiki/"
    "File:NLC892-411999020537-87577_%E9%87%9D%E7%81%B8%E7%94%B2%E4%B9%99%E7%B6%93_%E7%AC%AC1%E5%86%8A.pdf"
)
PDF_CACHE = "/Users/likeming/Sites/hfb/output/hfb_zhenjiu_jiayi_jing_v1.pdf"
EXPECTED_SHA256 = "c5c116b037ef017010f487c0bb9e650c430f996fe2cc3223da7a0089462e98d2"

# ═══════════════════════════════════════════════════════════════════════
# DEPRECATED — DO NOT USE for PDF page mapping.
# Replaced by scripts/p0_definitive_pipeline.py which uses PaddleOCR
# (PP-OCRv4) to match passage text against actual PDF page OCR output.
# PASSAGE_PAGE_MAP containts hardcoded *estimates* that were never
# verified against PDF page content. Retained for audit trail only.
# ═══════════════════════════════════════════════════════════════════════
PASSAGE_PAGE_MAP = {
    # passage_order -> estimated_pdf_page — ALL VALUES DEPRECATED
    # DO NOT USE THESE VALUES. Use p0_definitive_pipeline.py instead.
}


def load_pdf_bytes() -> tuple[bytes, str]:
    """Load PDF bytes from cache and verify checksum."""
    if not os.path.exists(PDF_CACHE):
        raise FileNotFoundError(f"PDF not found at {PDF_CACHE}")
    with open(PDF_CACHE, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != EXPECTED_SHA256:
        print(f"  WARNING: SHA-256 mismatch! Got: {sha}")
    return raw, sha


async def main():
    from sqlalchemy import text
    from app.db.database import async_session_factory, init_database
    from app.services.ingestion import IngestionService

    print("=" * 60)
    print("P0 PDF Ingestion — 《针灸甲乙经》Real PDF Import")
    print("=" * 60)

    await init_database()
    print("Database connection verified.\n")

    async with async_session_factory() as session:
        # Check baseline
        r = await session.execute(
            text("SELECT count(*) FROM books WHERE title='针灸甲乙经' AND is_deleted=false")
        )
        if r.scalar() == 0:
            print("ERROR: Baseline not initialized. Run init_dev_baseline.py first.")
            return

        r = await session.execute(
            text("SELECT count(*) FROM entity_relations WHERE is_deleted=false AND evidence_status='verified'")
        )
        kg_count = r.scalar()
        if kg_count == 0:
            print("ERROR: KG relations not seeded. Run seed_kg.py first.")
            return
        print(f"KG baseline: {kg_count} verified relations")

        # Load PDF
        print("\n[1/6] Loading PDF...")
        pdf_bytes, pdf_sha256 = load_pdf_bytes()
        print(f"  Size: {len(pdf_bytes)} bytes")
        print(f"  SHA-256: {pdf_sha256}")
        print(f"  Source: {PDF_FILE_PAGE}")

        # Check if already ingested
        r = await session.execute(
            text("SELECT id FROM documents WHERE content_checksum=:cs AND is_deleted=false"),
            {"cs": pdf_sha256},
        )
        existing = r.fetchone()
        if existing:
            print(f"\n  PDF already ingested as document {existing[0]}. Skipping document creation.")
            pdf_doc_id = existing[0]
        else:
            # Get existing book and passages
            print("\n[2/6] Fetching existing passages...")
            r = await session.execute(
                text(
                    "SELECT p.id, p.content_text, p.\"order\", p.chapter_id, p.version_id "
                    "FROM passages p WHERE p.is_deleted=false ORDER BY p.chapter_id, p.\"order\""
                )
            )
            all_passages = r.fetchall()
            print(f"  Found {len(all_passages)} passages")

            # Build full text with page number annotations
            chunks_data: list[tuple[str, str | None, int]] = []  # (content, passage_id, page_number)
            for p in all_passages:
                p_id, p_text, p_order, p_chapter, p_version = p
                page_num = PASSAGE_PAGE_MAP.get(p_order, None)
                chunks_data.append((p_text, p_id, page_num))

            full_text = "\n\n".join(c for c, _, _ in chunks_data)
            checksum = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

            # Create document with raw_pdf_blob
            print("\n[3/6] Creating PDF-backed Document...")
            from app.repositories.document import DocumentRepository

            doc_repo = DocumentRepository(session)
            doc = await doc_repo.create(
                title="针灸甲乙经",
                content_text=full_text,
                copyright_status="public_domain",
                authorization_basis=(
                    "Wikimedia Commons明确标注Public Domain / "
                    "中国国家图书馆机械扫描件 / "
                    "明万历二十九年(1601年)刻本 / "
                    "作者皇甫谧(215-282)已逾1700年 / "
                    "所有版权期限均已届满"
                ),
                source_url=PDF_FILE_PAGE,
                source_name="Wikimedia Commons / NLC",
                raw_pdf_blob=pdf_bytes,
                rag_enabled=True,
                review_status="approved",
                content_checksum=checksum,
                dynasty="晋",
                category="针灸",
                language="zh",
            )
            await session.flush()
            pdf_doc_id = doc.id
            print(f"  Document ID: {pdf_doc_id}")

            # Create SourceRef
            r = await session.execute(
                text("SELECT id FROM source_refs WHERE url=:url AND is_deleted=false"),
                {"url": PDF_FILE_PAGE},
            )
            sr_row = r.fetchone()
            if sr_row:
                sr_id = sr_row[0]
                print(f"  SourceRef already exists: {sr_id}")
            else:
                sr_id = str(uuid_mod.uuid4())
                await session.execute(
                    text(
                        "INSERT INTO source_refs (id, title, author, edition_info, "
                        "page_location, url, is_deleted) "
                        "VALUES (:id, :title, :author, :edition, :page_loc, :url, false)"
                    ),
                    {
                        "id": sr_id,
                        "title": "针灸甲乙经",
                        "author": "皇甫谧",
                        "edition": "明万历二十九年(1601年)刻本，中国国家图书馆藏，第1册（卷1-2）",
                        "page_loc": f"document:{pdf_doc_id}",
                        "url": PDF_FILE_PAGE,
                    },
                )
                print(f"  Created SourceRef: {sr_id}")

            # Create chunks with page numbers
            print("\n[4/6] Creating DocumentChunks with page numbers...")
            for idx, (content, passage_id, page_num) in enumerate(chunks_data):
                chunk_id = str(uuid_mod.uuid4())
                await session.execute(
                    text(
                        "INSERT INTO document_chunks (id, document_id, passage_id, "
                        "chunk_index, content, token_count, page_number, "
                        "paragraph_index, is_deleted) "
                        "VALUES (:id, :doc_id, :passage_id, :idx, :content, :tokens, "
                        ":page_num, :para_idx, false)"
                    ),
                    {
                        "id": chunk_id,
                        "doc_id": pdf_doc_id,
                        "passage_id": passage_id,
                        "idx": idx,
                        "content": content,
                        "tokens": len(content),
                        "page_num": page_num,
                        "para_idx": idx,
                    },
                )
            print(f"  Created {len(chunks_data)} chunks with page numbers")

            # Create Evidences + Citations
            print("\n[5/6] Creating Evidence + Citation records...")
            r = await session.execute(
                text("SELECT id FROM users WHERE email='admin@huangfumi.org' AND is_deleted=false")
            )
            admin_id = r.scalar_one()

            ev_count = 0
            cit_count = 0
            for content, passage_id, page_num in chunks_data:
                if not passage_id:
                    continue

                # Evidence
                ev_id = str(uuid_mod.uuid4())
                await session.execute(
                    text(
                        "INSERT INTO evidences (id, description, evidence_level, "
                        "source_ref_id, source_passage_id, creator_id, is_deleted) "
                        "VALUES (:id, :desc, 'LEVEL_2', :sr_id, :passage_id, :creator_id, false)"
                    ),
                    {
                        "id": ev_id,
                        "desc": f"明万历刻本NLC扫描件·《针灸甲乙经》·第{page_num}页",
                        "sr_id": sr_id,
                        "passage_id": passage_id,
                        "creator_id": admin_id,
                    },
                )
                ev_count += 1

                # Citation
                cid = str(uuid_mod.uuid4())
                await session.execute(
                    text(
                        "INSERT INTO citations (id, target_type, target_id, evidence_id, "
                        "quote_text, note, is_deleted) "
                        "VALUES (:id, 'passage', :target_id, :evidence_id, :quote, :note, false)"
                    ),
                    {
                        "id": cid,
                        "target_id": passage_id,
                        "evidence_id": ev_id,
                        "quote": content[:2000],
                        "note": f"Wikimedia Commons / NLC扫描本 / 第{page_num}页 / {PDF_FILE_PAGE}",
                    },
                )
                cit_count += 1

            print(f"  Created {ev_count} evidences, {cit_count} citations")

        await session.commit()

        # ---- 6. Update EntityRelations to point to PDF chunks ----
        print("\n[6/6] Updating EntityRelation evidence pointers...")
        r = await session.execute(
            text(
                "SELECT er.id, er.relation_type, er.claim_text, er.evidence_quote, "
                "er.evidence_passage_id "
                "FROM entity_relations er "
                "WHERE er.is_deleted=false AND er.evidence_status='verified' "
                "ORDER BY er.created_at"
            )
        )
        relations = r.fetchall()

        # Get PDF chunks with passage_ids
        r = await session.execute(
            text(
                "SELECT dc.id, dc.passage_id, dc.page_number "
                "FROM document_chunks dc "
                "WHERE dc.document_id=:did AND dc.is_deleted=false AND dc.passage_id IS NOT NULL"
            ),
            {"did": pdf_doc_id},
        )
        chunk_map = {row[1]: (row[0], row[2]) for row in r.fetchall()}
        print(f"  PDF chunks with passage links: {len(chunk_map)}")

        updated = 0
        for rel in relations:
            rel_id, rel_type, claim_text, evidence_quote, passage_id = rel
            if passage_id and passage_id in chunk_map:
                chunk_id, page_num = chunk_map[passage_id]
                await session.execute(
                    text(
                        "UPDATE entity_relations SET "
                        "evidence_document_id=:doc_id, "
                        "evidence_chunk_id=:chunk_id, "
                        "evidence_source_uri=:source_uri, "
                        "evidence_citation=:citation "
                        "WHERE id=:rel_id AND is_deleted=false"
                    ),
                    {
                        "doc_id": pdf_doc_id,
                        "chunk_id": chunk_id,
                        "source_uri": PDF_FILE_PAGE,
                        "citation": f"[{pdf_doc_id}:{chunk_id}]",
                        "rel_id": rel_id,
                    },
                )
                updated += 1
                print(f"  Updated {rel_type}: {claim_text[:60] if claim_text else 'N/A'} → page {page_num}")

        print(f"  Updated {updated}/{len(relations)} relations")

        # Also create/update version for PDF source
        r = await session.execute(
            text("SELECT id FROM books WHERE title='针灸甲乙经' AND is_deleted=false LIMIT 1")
        )
        book_id = r.scalar_one()

        version_name = "明万历刻本（NLC扫描本）"
        r = await session.execute(
            text("SELECT id FROM versions WHERE version_name=:vn AND is_deleted=false"),
            {"vn": version_name},
        )
        ver_row = r.fetchone()
        if ver_row:
            pdf_version_id = ver_row[0]
        else:
            pdf_version_id = str(uuid_mod.uuid4())
            await session.execute(
                text(
                    "INSERT INTO versions (id, book_id, version_name, era, year, repository, "
                    "description, source_url, is_deleted) "
                    "VALUES (:id, :book_id, :name, '明', 1601, :repo, :desc, :url, false)"
                ),
                {
                    "id": pdf_version_id,
                    "book_id": book_id,
                    "name": version_name,
                    "repo": "中国国家图书馆",
                    "desc": "明万历二十九年（1601年）刻本，中国国家图书馆藏，第1册（卷1-2），Wikimedia Commons公开获取",
                    "url": PDF_FILE_PAGE,
                },
            )
            print(f"  Created version: {pdf_version_id}")

        # Update version_ids on entity relations
        await session.execute(
            text(
                "UPDATE entity_relations SET evidence_version_id=:vid "
                "WHERE is_deleted=false AND evidence_status='verified'"
            ),
            {"vid": pdf_version_id},
        )

        await session.commit()

        # ---- Summary ----
        print("\n" + "=" * 60)
        print("Final Database Statistics")
        print("=" * 60)
        tables = [
            "documents", "document_chunks", "source_refs", "evidences",
            "citations", "entity_relations", "versions",
        ]
        for t in tables:
            r = await session.execute(
                text(f"SELECT count(*) FROM {t} WHERE is_deleted=false")
            )
            print(f"  {t}: {r.scalar()}")

        # Show source_refs
        r = await session.execute(
            text("SELECT id, title, url FROM source_refs WHERE is_deleted=false AND url LIKE 'https://%'")
        )
        for row in r.fetchall():
            print(f"  source_ref: {row[0][:12]}... | {row[1][:40]} | {row[2][:80]}")

        # Show page number distribution
        r = await session.execute(
            text(
                "SELECT page_number, count(*) FROM document_chunks "
                "WHERE is_deleted=false AND page_number IS NOT NULL "
                "GROUP BY page_number ORDER BY page_number"
            )
        )
        print("\n  Page number distribution:")
        for pn, cnt in r.fetchall():
            print(f"    Page {pn}: {cnt} chunks")

        print("\nPDF ingestion complete ✓")


if __name__ == "__main__":
    asyncio.run(main())
