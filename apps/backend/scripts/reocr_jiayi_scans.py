#!/usr/bin/env python3
"""Re-OCR the two scanned 针灸甲乙经 fixtures in place (PaddleOCR).

The initial ingest ran tesseract `--psm 6` on vertical classical-Chinese
scans, producing unreadable garbage. This script re-runs OCR through
IngestionService._ocr_pdf_pages (now PaddleOCR-first with reading-order
reordering) and replaces each document's content_text + chunks in place,
keeping the SAME document id so reader URLs stay valid.

Targets (scanned, no text layer — skip the 四库全书本 which has a text layer):
  1. 针灸甲乙经校注（上册）     — a7ee077e (1101 pages)
  2. 黄帝针灸甲乙经（黄龙祥校本） — 2360717d (573 pages)

Run from apps/backend with the system python (has paddleocr + pdf2image):
  /usr/local/bin/python3 -m scripts.reocr_jiayi_scans --dpi 200
  /usr/local/bin/python3 -m scripts.reocr_jiayi_scans --only 校注 --limit 5
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
import time
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import async_session_factory, close_database, init_database  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.document_chunk import DocumentChunk  # noqa: E402
from app.services.chunking import chunk_text  # noqa: E402
from app.services.ingestion import IngestionService  # noqa: E402

TARGETS = [
    {"title": "针灸甲乙经校注（上册）", "path": ROOT / "针灸甲乙经校注（上册）.pdf"},
    {
        "title": "黄帝针灸甲乙经（黄龙祥校本）",
        "path": ROOT / "黄帝针灸甲乙经  （黄龙祥校本）.pdf",
    },
]


def _page_image_hashes(path: Path, page_numbers: list[int]) -> dict[int, str]:
    """SHA-256 of each page's embedded scan image bytes (1-based page -> hash).

    Uses the raw embedded image (not a re-render) so the digest is stable and
    locates the exact source image in raw_pdf_blob for later visual proof.
    Pages with no image (or extraction failure) are omitted.
    """
    import fitz

    doc = fitz.open(str(path))
    hashes: dict[int, str] = {}
    try:
        for pg in page_numbers:
            page = doc[pg - 1]
            images = page.get_images(full=True)
            if not images:
                continue
            xref = images[0][0]
            try:
                info = doc.extract_image(xref)
            except Exception:  # noqa: BLE001
                continue
            if info and info.get("image"):
                hashes[pg] = hashlib.sha256(info["image"]).hexdigest()
    finally:
        doc.close()
    return hashes


async def _reocr_one(
    session, svc: IngestionService, doc: Document, path: Path, dpi: int, limit: int
) -> dict:
    raw = path.read_bytes()
    reader = PdfReader(path)
    n_pages = len(reader.pages)
    page_numbers = list(range(1, n_pages + 1))
    if limit:
        page_numbers = page_numbers[:limit]

    print(
        f"  {doc.title}: {n_pages} pages, OCR {len(page_numbers)} @ {dpi}dpi",
        flush=True,
    )
    t0 = time.time()

    ocr_texts = IngestionService._ocr_pdf_pages(
        raw, page_numbers, dpi=dpi, batch_size=30
    )
    page_data = sorted(ocr_texts.items())
    if not page_data:
        return {"title": doc.title, "status": "empty"}

    full_text = "\n\n".join(t for _, t in page_data)
    checksum = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

    # Page image hashes for visual provenance / OCR correction. Hash the
    # embedded scan image bytes directly (not a re-render) so the digest is
    # stable and can later locate the exact source image from raw_pdf_blob.
    page_hashes = _page_image_hashes(path, [pg for pg, _ in page_data])

    # Chunk per page (same shape as ingest_pdf_with_pages).
    all_chunk_data: list[tuple[str, int]] = []
    all_page_numbers: list[int | None] = []
    all_page_image_hashes: list[str | None] = []
    for pg, text in page_data:
        pc = chunk_text(text, max_chars=1000, return_indices=True)
        pairs = [(t, -1) for t in pc] if pc and isinstance(pc[0], str) else pc
        for txt, para in pairs:
            all_chunk_data.append((txt, para))
            all_page_numbers.append(pg)
            all_page_image_hashes.append(page_hashes.get(pg))

    # Replace in place: wipe old chunks, write new, update document.
    # ocr_confidence=None so re-OCR'd text lands in the reader's 原文 section
    # (original_chunks filters on ocr_confidence IS NULL), not the OCR section.
    await session.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    )
    await svc._store_chunks(
        document_id=doc.id,
        chunks=all_chunk_data,
        ocr_confidence=None,
        page_numbers=all_page_numbers,
        page_image_hashes=all_page_image_hashes,
    )
    doc.content_text = full_text
    doc.content_checksum = checksum
    await session.commit()

    return {
        "title": doc.title,
        "status": "ok",
        "chunks": len(all_chunk_data),
        "chars": len(full_text),
        "seconds": round(time.time() - t0, 1),
    }


async def main(dpi: int, only: str | None, limit: int) -> None:
    await init_database()
    results: list[dict] = []
    try:
        async with async_session_factory() as session:
            for t in TARGETS:
                if only and only not in t["title"]:
                    continue
                r = await session.execute(
                    select(Document).where(
                        Document.title == t["title"],
                        Document.is_deleted.is_(False),
                    )
                )
                doc = r.scalars().first()
                if doc is None:
                    print(f"MISSING DOC: {t['title']}", flush=True)
                    results.append({"title": t["title"], "status": "missing"})
                    continue
                svc = IngestionService(session)
                try:
                    res = await _reocr_one(session, svc, doc, t["path"], dpi, limit)
                    print(f"  -> {res}", flush=True)
                    results.append(res)
                except Exception as e:  # noqa: BLE001
                    await session.rollback()
                    print(f"FAIL: {t['title']} — {type(e).__name__}: {e}", flush=True)
                    results.append(
                        {"title": t["title"], "status": "fail", "error": str(e)}
                    )
    finally:
        await close_database()

    print("\n=== SUMMARY ===", flush=True)
    for r in results:
        print(r, flush=True)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--only", type=str, default=None, help="substring match on title")
    ap.add_argument(
        "--limit", type=int, default=0, help="OCR only first N pages (smoke test)"
    )
    args = ap.parse_args()
    asyncio.run(main(args.dpi, args.only, args.limit))
