#!/usr/bin/env python3
"""
P0 Correct Import — OCR-verified PDF page-level evidence for 《针灸甲乙经》

Replaces scripts/p0_pdf_ingestion.py (hardcoded PASSAGE_PAGE_MAP estimates)
with actual OCR-backed page matching.

Pipeline:
  1. Run PaddleOCR on all 78 PDF pages (or load cached artifacts from JSON)
  2. Store PDF as raw_pdf_blob on the existing undeleted document 30c1e030...
  3. Match 10 passage texts against OCR'd page texts:
     a. Exact normalized-substring match
     b. LCS with >=0.5 ratio for sequences >=10 chars
     c. page_number=NULL where no reliable match exists
  4. UPDATE document_chunks with verified page_number, match_method, match_result
  5. UPDATE entity_relations to point to the corrected chunks on 30c1e030
  6. Print a clear audit table

Usage:
  cd apps/backend && python ../../scripts/p0_correct_import.py
"""

import asyncio
import hashlib
import json
import os
import re
import sys
import uuid as uuid_mod
from difflib import SequenceMatcher
from io import BytesIO
from typing import Any

_backend_dir = os.path.join(os.path.dirname(__file__), "..", "apps", "backend")
_backend_dir = os.path.abspath(_backend_dir)
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PDF_CACHE = "/Users/likeming/Sites/hfb/output/hfb_zhenjiu_jiayi_jing_v1.pdf"
OCR_ARTIFACTS_PATH = "/Users/likeming/Sites/hfb/output/p0_paddleocr_artifacts.json"
EXPECTED_SHA256 = "c5c116b037ef017010f487c0bb9e650c430f996fe2cc3223da7a0089462e98d2"
TARGET_DOC_ID = "30c1e030-847d-4e52-9acc-d03f7b397d1a"

PDF_SOURCE_URL = (
    "https://commons.wikimedia.org/wiki/"
    "File:NLC892-411999020537-87577_%E9%87%9D%E7%81%B8%E7%94%B2%E4%B9%99%E7%B6%93_%E7%AC%AC1%E5%86%8A.pdf"
)

# LCS matching thresholds
LCS_MIN_MATCH_CHARS = 10
LCS_MIN_RATIO = 0.5

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

# Chinese + ASCII punctuation to strip for matching
_PUNCT_RE = re.compile(
    r"[\s，。、；：！？「」『』【】《》（）\"\'\.\,\;\:\!\?\[\]\(\)　-〿＀-￯]"
)


def normalize_for_match(text: str) -> str:
    """Remove all punctuation and whitespace, leaving only raw characters."""
    return _PUNCT_RE.sub("", text)


# ---------------------------------------------------------------------------
# PaddleOCR
# ---------------------------------------------------------------------------


def _ocr_pages_with_paddle(img_array) -> str:
    """Run PaddleOCR on a single page image (numpy array), return text."""
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(lang="ch", use_angle_cls=False, show_log=False)
    result = ocr.ocr(img_array)

    if not result or result[0] is None:
        return ""

    lines: list[str] = []
    for detection in result[0]:
        rec = detection[1]  # (text, confidence)
        text = rec[0].strip()
        if text:
            lines.append(text)
    return "".join(lines)


def generate_ocr_artifacts(pdf_path: str, output_path: str) -> dict[int, str]:
    """Run PaddleOCR on all pages of the PDF. Returns {page_number: ocr_text}."""

    from pdf2image import convert_from_bytes
    from paddleocr import PaddleOCR

    print("\n" + "=" * 60)
    print("Running PaddleOCR on all 78 pages (this will take several minutes)...")
    print("=" * 60)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    images = convert_from_bytes(pdf_bytes, dpi=300, fmt="png", thread_count=2)
    total = len(images)
    print(f"  Rendered {total} pages at 300 DPI")

    ocr = PaddleOCR(lang="ch", use_angle_cls=False, show_log=False)
    page_texts: dict[int, str] = {}

    for i, img in enumerate(images):
        pg = i + 1  # 1-based page number
        print(f"  OCR page {pg}/{total} ...", end=" ", flush=True)
        try:
            result = ocr.ocr(img)
            if result and result[0] is not None:
                lines: list[str] = []
                for detection in result[0]:
                    rec_text = detection[1][0].strip()
                    if rec_text:
                        lines.append(rec_text)
                text = "".join(lines)
                page_texts[pg] = text
                print(f"{len(text)} chars")
            else:
                page_texts[pg] = ""
                print("no text detected")
        except Exception as exc:
            page_texts[pg] = ""
            print(f"ERROR: {exc}")

    # Save artifacts
    # Convert to serializable format: {str(page): text}
    serializable = {str(k): v for k, v in page_texts.items()}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {"pdf_path": pdf_path, "total_pages": total, "pages": serializable},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\n  OCR artifacts saved to {output_path}")
    print(f"  Pages with text: {sum(1 for v in page_texts.values() if v)}/{total}")

    return page_texts


def load_ocr_artifacts(path: str) -> dict[int, str]:
    """Load cached OCR artifacts. Returns {page_number: ocr_text}."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {int(k): v for k, v in data["pages"].items()}


# ---------------------------------------------------------------------------
# Page matching logic
# ---------------------------------------------------------------------------


def match_passage_to_page(
    passage_text: str, ocr_pages: dict[int, str]
) -> tuple[int | None, str, str]:
    """Match a passage text against OCR'd page texts.

    Returns (page_number | None, match_method, match_result_json).

    Strategy:
      1. Normalize both passage and per-page OCR text (strip punctuation/whitespace).
      2. Try exact normalized-substring match.
      3. If no exact match, try LCS: find the longest common substring >=10 chars
         with ratio >=0.5 relative to the passage length.
      4. If still no match, return (None, "no_match", {...}).
    """
    norm_passage = normalize_for_match(passage_text)

    if len(norm_passage) < 5:
        return (None, "too_short", json.dumps({"reason": "passage too short"}))

    # Pre-normalize all pages once
    norm_pages: dict[int, str] = {}
    for pg, text in ocr_pages.items():
        norm_pages[pg] = normalize_for_match(text)

    # ---- Step 1: Exact normalized-substring match ----
    for pg, norm_page_text in norm_pages.items():
        if norm_passage in norm_page_text:
            result = json.dumps(
                {
                    "method": "exact_normalized_substring",
                    "page": pg,
                    "passage_len": len(norm_passage),
                    "page_text_len": len(norm_page_text),
                },
                ensure_ascii=False,
            )
            return (pg, "exact_normalized_substring", result)

    # ---- Step 2: LCS matching ----
    best_pg: int | None = None
    best_ratio: float = 0.0
    best_match_len: int = 0
    best_details: dict[str, Any] = {}

    for pg, norm_page_text in norm_pages.items():
        sm = SequenceMatcher(None, norm_passage, norm_page_text)
        match = sm.find_longest_match(0, len(norm_passage), 0, len(norm_page_text))

        if match.size < LCS_MIN_MATCH_CHARS:
            continue

        ratio = match.size / len(norm_passage)
        if ratio > best_ratio:
            best_ratio = ratio
            best_pg = pg
            best_match_len = match.size
            best_details = {
                "method": "lcs",
                "page": pg,
                "lcs_len": match.size,
                "passage_len": len(norm_passage),
                "ratio": round(ratio, 4),
                "passage_pos": match.a,
                "page_pos": match.b,
            }

    if best_pg is not None and best_ratio >= LCS_MIN_RATIO:
        return (best_pg, "lcs", json.dumps(best_details, ensure_ascii=False))

    # ---- Step 3: No reliable match ----
    return (
        None,
        "no_match",
        json.dumps(
            {
                "method": "no_match",
                "best_ratio": round(best_ratio, 4),
                "best_lcs_len": best_match_len,
                "passage_len": len(norm_passage),
                "threshold_ratio": LCS_MIN_RATIO,
                "threshold_chars": LCS_MIN_MATCH_CHARS,
            },
            ensure_ascii=False,
        ),
    )


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


async def ensure_columns(session) -> None:
    """Columns are created by rag_evidence_binding_v2 migration — no DDL needed here.
    If the migration hasn't been run, report and exit."""
    from sqlalchemy import text

    r = await session.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='document_chunks' AND column_name='match_method'"
        )
    )
    if r.fetchone() is None:
        print("\n  ERROR: rag_evidence_binding_v2 migration not applied.")
        print("  Run: cd apps/backend && alembic upgrade head")
        print("  Then re-run this script.")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    from sqlalchemy import text
    from app.db.database import async_session_factory, init_database

    print("=" * 60)
    print("P0 Correct Import — OCR-verified PDF page-level evidence")
    print("《针灸甲乙经》明万历刻本 NLC 扫描件")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 0. Init database + ensure schema
    # ------------------------------------------------------------------
    await init_database()
    print("Database connection verified.\n")

    # Check migration applied
    async with async_session_factory() as ddl_session:
        await ensure_columns(ddl_session)

    # ------------------------------------------------------------------
    # 1. Load or generate OCR artifacts
    # ------------------------------------------------------------------
    if os.path.exists(OCR_ARTIFACTS_PATH):
        print(f"[1/6] Loading cached OCR artifacts from {OCR_ARTIFACTS_PATH}")
        ocr_pages = load_ocr_artifacts(OCR_ARTIFACTS_PATH)
        print(f"  Loaded {len(ocr_pages)} pages, {sum(1 for v in ocr_pages.values() if v)} with text")
    else:
        print("[1/6] Generating PaddleOCR artifacts (first run only)")
        ocr_pages = generate_ocr_artifacts(PDF_CACHE, OCR_ARTIFACTS_PATH)

    # ------------------------------------------------------------------
    # 2. Verify PDF checksum & store blob on target document
    # ------------------------------------------------------------------
    print("\n[2/6] Loading PDF and storing raw_pdf_blob...")
    with open(PDF_CACHE, "rb") as f:
        pdf_bytes = f.read()

    pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    print(f"  PDF size: {len(pdf_bytes)} bytes")
    print(f"  SHA-256:  {pdf_sha256}")
    if pdf_sha256 != EXPECTED_SHA256:
        print(f"  WARNING: SHA-256 mismatch! Expected: {EXPECTED_SHA256}")

    async with async_session_factory() as session:
        # Check target document exists and is not deleted
        r = await session.execute(
            text(
                "SELECT id, title, is_deleted, "
                "octet_length(raw_pdf_blob) as blob_octets "
                "FROM documents WHERE id=:did"
            ),
            {"did": TARGET_DOC_ID},
        )
        doc_row = r.fetchone()
        if not doc_row:
            print(f"\n  ERROR: Target document {TARGET_DOC_ID} not found.")
            return
        if doc_row[2]:
            print(f"\n  ERROR: Target document {TARGET_DOC_ID} is soft-deleted.")
            return

        existing_blob_len = doc_row[3]
        if existing_blob_len and existing_blob_len > 0:
            print(f"  raw_pdf_blob already stored ({existing_blob_len} octets), skipping")
        else:
            await session.execute(
                text("UPDATE documents SET raw_pdf_blob=:blob WHERE id=:did"),
                {"blob": pdf_bytes, "did": TARGET_DOC_ID},
            )
            await session.flush()
            print("  raw_pdf_blob stored successfully")

        # Store content_checksum if null
        r = await session.execute(
            text("SELECT content_checksum FROM documents WHERE id=:did"),
            {"did": TARGET_DOC_ID},
        )
        existing_cs = r.scalar()
        if not existing_cs:
            r = await session.execute(
                text("SELECT content_text FROM documents WHERE id=:did"),
                {"did": TARGET_DOC_ID},
            )
            doc_text = r.scalar() or ""
            cs = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()
            await session.execute(
                text("UPDATE documents SET content_checksum=:cs WHERE id=:did"),
                {"cs": cs, "did": TARGET_DOC_ID},
            )
            await session.flush()
            print(f"  content_checksum set: {cs[:16]}...")

        # Also set source_url if missing
        r = await session.execute(
            text("SELECT source_url FROM documents WHERE id=:did"),
            {"did": TARGET_DOC_ID},
        )
        existing_url = r.scalar()
        if not existing_url:
            await session.execute(
                text("UPDATE documents SET source_url=:url, copyright_status=:cs WHERE id=:did"),
                {
                    "url": PDF_SOURCE_URL,
                    "cs": "public_domain",
                    "did": TARGET_DOC_ID,
                },
            )
            await session.flush()
            print("  source_url + copyright_status set")

    # ------------------------------------------------------------------
    # 3. Fetch passages with chunks on the target document
    # ------------------------------------------------------------------
    async with async_session_factory() as session:
        print("\n[3/6] Fetching passages and chunks on target document...")
        r = await session.execute(
            text(
                "SELECT dc.id AS chunk_id, dc.passage_id, dc.chunk_index, "
                "dc.content AS chunk_content, dc.page_number AS current_pg, "
                "p.content_text AS passage_text, p.\"order\" AS passage_order, "
                "p.chapter_id "
                "FROM document_chunks dc "
                "JOIN passages p ON dc.passage_id = p.id AND p.is_deleted = false "
                "WHERE dc.document_id = :did AND dc.is_deleted = false "
                "ORDER BY dc.chunk_index"
            ),
            {"did": TARGET_DOC_ID},
        )
        chunk_rows = r.fetchall()
        print(f"  Found {len(chunk_rows)} chunks with passage links")

        if len(chunk_rows) == 0:
            print("  ERROR: No chunks found on target document.")
            return

    # ------------------------------------------------------------------
    # 4. Match each passage against OCR'd pages
    # ------------------------------------------------------------------
    print("\n[4/6] Matching passage texts against OCR'd pages...")
    print(f"  Match strategy: exact normalized-substring -> LCS (ratio>={LCS_MIN_RATIO}, len>={LCS_MIN_MATCH_CHARS}) -> NULL")
    print()

    # Collect unique passages (some may have multiple chunks, but here it's 1:1)
    match_results: dict[str, dict] = {}  # passage_id -> match info

    seen_passages: set[str] = set()
    for row in chunk_rows:
        chunk_id, passage_id, chunk_idx, chunk_content, current_pg, passage_text, passage_order, chapter_id = row

        if passage_id in seen_passages:
            continue
        seen_passages.add(passage_id)

        page_num, method, result_json = match_passage_to_page(passage_text or chunk_content or "", ocr_pages)

        # Re-match using chunk_content if passage_text differs (unlikely but safe)
        if page_num is None and chunk_content and chunk_content != (passage_text or ""):
            page_num, method, result_json = match_passage_to_page(chunk_content, ocr_pages)

        match_results[str(passage_id)] = {
            "page_number": page_num,
            "match_method": method,
            "match_result": result_json,
            "chunk_id": str(chunk_id),
            "passage_order": passage_order,
            "passage_preview": (passage_text or chunk_content or "")[:60],
        }

        status = "MATCH" if page_num else "NULL "
        page_display = str(page_num) if page_num else "-"
        print(f"  [{status}] passage order={passage_order:>3} pg={page_display:>3} | {(passage_text or chunk_content or '')[:60]}")

    # ------------------------------------------------------------------
    # 5. Update document_chunks with verified page numbers
    # ------------------------------------------------------------------
    async with async_session_factory() as session:
        print("\n[5/6] Updating document_chunks...")
        updated_chunks = 0
        for row in chunk_rows:
            chunk_id, passage_id, chunk_idx, chunk_content, current_pg, passage_text, passage_order, chapter_id = row
            mr = match_results.get(str(passage_id))
            if mr is None:
                continue

            new_pg = mr["page_number"]
            method = mr["match_method"]
            result_json = mr["match_result"]

            # Assign OCR confidence based on match quality
            if method == "exact_normalized_substring":
                ocr_conf = 0.85
                evidence_w = "primary"
            elif method == "lcs":
                ocr_conf = 0.65
                evidence_w = "primary"
            else:
                ocr_conf = None
                evidence_w = "reference"

            await session.execute(
                text(
                    "UPDATE document_chunks SET "
                    "page_number=:pg, match_method=:method, quote_bbox=CAST(:bbox AS json), "
                    "ocr_confidence=:ocr, evidence_weight=:weight "
                    "WHERE id=:cid AND is_deleted=false"
                ),
                {
                    "pg": new_pg,
                    "method": method,
                    "bbox": result_json,
                    "ocr": ocr_conf,
                    "weight": evidence_w,
                    "cid": chunk_id,
                },
            )
            updated_chunks += 1

        print(f"  Updated {updated_chunks} chunks")

        # ------------------------------------------------------------------
        # 6. Update entity_relations to point to new chunks
        # ------------------------------------------------------------------
        print("\n[6/6] Updating entity_relations...")

        # Get all verified entity_relations
        r = await session.execute(
            text(
                "SELECT er.id, er.evidence_passage_id, er.evidence_chunk_id, "
                "er.evidence_document_id, er.relation_type, er.claim_text "
                "FROM entity_relations er "
                "WHERE er.is_deleted=false AND er.evidence_status='verified' "
                "ORDER BY er.created_at"
            )
        )
        relations = r.fetchall()
        print(f"  Found {len(relations)} verified entity_relations")

        # Build map: passage_id -> chunk_id on target document
        chunk_by_passage: dict[str, tuple[str, int | None]] = {}
        for row in chunk_rows:
            chunk_id, passage_id, chunk_idx, chunk_content, current_pg, passage_text, passage_order, chapter_id = row
            mr = match_results.get(str(passage_id))
            pg = mr["page_number"] if mr else None
            chunk_by_passage[str(passage_id)] = (str(chunk_id), pg)

        # Get or create source_ref
        r = await session.execute(
            text("SELECT id FROM source_refs WHERE url=:url AND is_deleted=false"),
            {"url": PDF_SOURCE_URL},
        )
        sr_row = r.fetchone()
        source_ref_id = sr_row[0] if sr_row else None
        if not source_ref_id:
            source_ref_id = str(uuid_mod.uuid4())
            await session.execute(
                text(
                    "INSERT INTO source_refs (id, title, author, edition_info, "
                    "page_location, url, is_deleted) "
                    "VALUES (:id, :title, :author, :edition, :loc, :url, false)"
                ),
                {
                    "id": source_ref_id,
                    "title": "针灸甲乙经",
                    "author": "皇甫谧",
                    "edition": "明万历二十九年(1601年)刻本，中国国家图书馆藏，第1册（卷1-2）",
                    "loc": f"document:{TARGET_DOC_ID}",
                    "url": PDF_SOURCE_URL,
                },
            )
            print(f"  Created SourceRef: {source_ref_id[:12]}...")

        er_updated = 0
        for rel in relations:
            rel_id, er_passage_id, old_chunk_id, old_doc_id, rel_type, claim = rel
            passage_key = str(er_passage_id)

            if passage_key not in chunk_by_passage:
                print(f"  SKIP {rel_type}: passage {passage_key[:12]} has no chunk on target doc")
                continue

            new_chunk_id, new_pg = chunk_by_passage[passage_key]

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
                    "doc_id": TARGET_DOC_ID,
                    "chunk_id": new_chunk_id,
                    "source_uri": PDF_SOURCE_URL,
                    "citation": f"[{TARGET_DOC_ID}:{new_chunk_id}]",
                    "rel_id": rel_id,
                },
            )
            er_updated += 1
            pg_str = str(new_pg) if new_pg else "NULL"
            print(f"  [OK] {rel_type}: {claim[:60] if claim else 'N/A'} -> chunk pg={pg_str}")

        print(f"  Updated {er_updated}/{len(relations)} entity_relations")

        await session.commit()
        print("\n  All changes committed.")

    # ------------------------------------------------------------------
    # 7. Audit summary
    # ------------------------------------------------------------------
    async with async_session_factory() as session:
        print("\n" + "=" * 60)
        print("AUDIT TABLE — OCR Page Matching Results")
        print("=" * 60)

        print(f"\n{'Order':>5} {'Page':>5} {'Method':<28} {'LCS/Ratio':>10} {'Passage Preview'}")
        print("-" * 95)

        for row in chunk_rows:
            chunk_id, passage_id, chunk_idx, chunk_content, current_pg, passage_text, passage_order, chapter_id = row
            mr = match_results.get(str(passage_id))
            if mr is None:
                continue

            pg = mr["page_number"]
            method = mr["match_method"]
            result_json = mr["match_result"]
            preview = mr["passage_preview"]

            pg_str = str(pg) if pg else "NULL"

            # Extract LCS info from result JSON
            lcs_info = "-"
            try:
                rd = json.loads(result_json)
                if rd.get("method") == "lcs":
                    lcs_info = f"{rd.get('lcs_len',0)}/{rd.get('ratio',0):.2f}"
                elif rd.get("method") == "no_match":
                    lcs_info = f"best={rd.get('best_ratio',0):.2f}"
                else:
                    lcs_info = "exact"
            except Exception:
                pass

            print(f"{passage_order:>5} {pg_str:>5} {method:<28} {lcs_info:>10} {preview}")

        print("-" * 95)

        # Chunk page distribution
        r = await session.execute(
            text(
                "SELECT page_number, count(*) FROM document_chunks "
                "WHERE document_id=:did AND is_deleted=false "
                "AND page_number IS NOT NULL "
                "GROUP BY page_number ORDER BY page_number"
            ),
            {"did": TARGET_DOC_ID},
        )
        print("\nPage number distribution (document_chunks on target doc):")
        for pn, cnt in r.fetchall():
            print(f"  Page {pn}: {cnt} chunks")

        # NULL page chunks
        r = await session.execute(
            text(
                "SELECT count(*) FROM document_chunks "
                "WHERE document_id=:did AND is_deleted=false "
                "AND page_number IS NULL"
            ),
            {"did": TARGET_DOC_ID},
        )
        null_count = r.scalar()
        if null_count:
            print(f"  NULL (no match): {null_count} chunks")

        # Entity relation summary
        r = await session.execute(
            text(
                "SELECT er.id, er.claim_text, dc.page_number "
                "FROM entity_relations er "
                "LEFT JOIN document_chunks dc ON er.evidence_chunk_id = dc.id "
                "WHERE er.is_deleted=false AND er.evidence_status='verified' "
                "ORDER BY er.created_at"
            )
        )
        print("\nEntity Relations (verified) — evidence pointers:")
        for rel_row in r.fetchall():
            pg_str = str(rel_row[2]) if rel_row[2] else "NULL"
            print(f"  pg={pg_str} | {rel_row[1][:70] if rel_row[1] else 'N/A'}")

        print("\n" + "=" * 60)
        print("Correction complete.")
        print(f"  Document:     {TARGET_DOC_ID}")
        print(f"  Chunks:       {updated_chunks} updated")
        print(f"  ER pointers:  {er_updated} updated")
        print(f"  OCR cache:    {OCR_ARTIFACTS_PATH}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
