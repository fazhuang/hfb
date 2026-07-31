#!/usr/bin/env python3
"""Ingest new OCR pages (26-50) as chunks on the PDF-backed document."""

import asyncio
import json
import os
import sys
import uuid as uuid_mod

PROJECT_ROOT = "/Users/likeming/Sites/hfb"
sys.path.insert(0, f"{PROJECT_ROOT}/apps/backend")
os.chdir(f"{PROJECT_ROOT}/apps/backend")

from app.db.database import async_session_factory, init_database
from sqlalchemy import text

OCR_CACHE = f"{PROJECT_ROOT}/output/p0_paddleocr_artifacts.json"
TARGET_DOC_ID = "30c1e030-847d-4e52-9acc-d03f7b397d1a"


async def main():
    await init_database()

    with open(OCR_CACHE) as f:
        ocr_data = json.load(f)

    async with async_session_factory() as s:
        r = await s.execute(
            text(
                "SELECT page_number FROM document_chunks WHERE document_id=:did AND is_deleted=false AND page_number IS NOT NULL"
            ),
            {"did": TARGET_DOC_ID},
        )
        existing_pages = {row[0] for row in r.fetchall() if row[0] is not None}
        print(
            f"Existing chunk pages: {sorted(existing_pages)} ({len(existing_pages)} chunks)"
        )

        new_chunks = 0
        for pg_str, data in sorted(ocr_data.items(), key=lambda x: int(x[0])):
            pg = int(pg_str)
            if pg in existing_pages:
                continue
            if not isinstance(data, dict) or not data.get("ocr_text", "").strip():
                continue

            ocr_text = data["ocr_text"]
            avg_conf = data.get("ocr_avg_confidence", 0.0)
            ihash = data.get("page_image_hash", "")
            chash = data.get("page_content_hash", "")

            chunk_id = str(uuid_mod.uuid4())
            bbox_info = json.dumps(
                {
                    "page": pg,
                    "page_image_hash": ihash,
                    "page_content_hash": chash,
                    "match_method": "ocr_page_full",
                    "ocr_engine": "paddleocr-PP-OCRv4",
                    "ocr_confidence": avg_conf,
                },
                ensure_ascii=False,
            )

            await s.execute(
                text(
                    "INSERT INTO document_chunks (id, document_id, chunk_index, content, "
                    "token_count, page_number, paragraph_index, ocr_confidence, "
                    "evidence_weight, page_image_hash, ocr_engine_version, "
                    "match_method, quote_bbox, is_deleted) "
                    "VALUES (:id, :did, :idx, :content, :tokens, :pg, :para, :ocr, "
                    ":weight, :ihash, :engine, :method, CAST(:bbox AS json), false)"
                ),
                {
                    "id": chunk_id,
                    "did": TARGET_DOC_ID,
                    "idx": pg - 1,
                    "content": ocr_text,
                    "tokens": len(ocr_text),
                    "pg": pg,
                    "para": pg - 1,
                    "ocr": avg_conf,
                    "weight": "primary",
                    "ihash": ihash[:128] if ihash else None,
                    "engine": "paddleocr-PP-OCRv4",
                    "method": "ocr_page_full",
                    "bbox": bbox_info,
                },
            )
            new_chunks += 1
            print(f"  Page {pg}: {len(ocr_text)} chars, conf={avg_conf:.3f}")

        await s.commit()
        print(f"\nCreated {new_chunks} new chunks")

        r = await s.execute(
            text(
                "SELECT count(*) FROM document_chunks WHERE document_id=:did AND is_deleted=false AND page_number IS NOT NULL"
            ),
            {"did": TARGET_DOC_ID},
        )
        print(f"Total PDF-backed chunks: {r.scalar()}")


asyncio.run(main())
