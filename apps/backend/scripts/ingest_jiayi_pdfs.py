#!/usr/bin/env python3
"""Ingest the four 针灸甲乙经 source files (3 PDF + 1 HTML) into documents (文献库).

Run from apps/backend:
  python -m scripts.ingest_jiayi_pdfs                 # skip already-ingested, add missing
  python -m scripts.ingest_jiayi_pdfs --reset         # hard-delete existing 4 then re-ingest
  python -m scripts.ingest_jiayi_pdfs --dpi 200       # OCR render DPI (default 200)

Files (all at repo root):
  1. 针灸甲乙经_四库全书本.pdf            — text layer present
  2. 针灸甲乙经_四库全书本.html           — same content as HTML → strip → ingest_text
  3. 黄帝针灸甲乙经（黄龙祥校本）.pdf     — scanned, no text layer → OCR fallback
  4. 针灸甲乙经校注（上册）.pdf            — scanned, no text layer → OCR fallback

All 3 PDFs go through ingest_pdf_with_pages so every chunk carries its
source page_number — required by the strict-compliance RAG gate
(raw_pdf_blob IS NOT NULL ⇒ page_number IS NOT NULL).

Copyright: 四库全书本 = public_domain; 黄龙祥校本/校注 = modern scholarly
annotation → user_uploaded_with_permission (internal test). review_status left
at default pending_review — RAG stays disabled until an admin approves.
"""

from __future__ import annotations

import asyncio
import html
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import async_session_factory, close_database, init_database
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.ingestion import IngestionService


# ------------------------------------------------------------------
# HTML → text (block tags emit newlines)
# ------------------------------------------------------------------
class _TextExtract(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in ("p", "h1", "h2", "h3", "h4", "li", "section", "br", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip > 0:
            self._skip -= 1
        elif tag in ("p", "h1", "h2", "h3", "h4", "li", "section", "tr"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip == 0:
            self._parts.append(data)

    def text(self) -> str:
        raw = html.unescape("".join(self._parts))
        return "\n".join(line.strip() for line in raw.split("\n") if line.strip())


def html_to_text(raw: str) -> str:
    p = _TextExtract()
    p.feed(raw)
    return p.text()


# ------------------------------------------------------------------
# Per-file definitions
# ------------------------------------------------------------------
def _pdf_meta(kind: str) -> dict:
    if kind == "public_domain":
        return {
            "copyright_status": "public_domain",
            "authorization_basis": "清乾隆《四库全书》影印本，公有领域",
        }
    return {
        "copyright_status": "user_uploaded_with_permission",
        "authorization_basis": "用户上传，内部测试用（黄龙祥现代校注，非公版）",
    }


ENTRIES = [
    {
        "title": "针灸甲乙经（四库全书本）",
        "path": ROOT / "针灸甲乙经_四库全书本.pdf",
        "kind": "pdf",
        "source_name": "识典古籍(shidianguji.com)",
        "meta": _pdf_meta("public_domain"),
    },
    {
        "title": "针灸甲乙经（四库全书本·HTML）",
        "path": ROOT / "针灸甲乙经_四库全书本.html",
        "kind": "html",
        "source_name": "识典古籍(shidianguji.com)",
        "meta": _pdf_meta("public_domain"),
    },
    {
        "title": "黄帝针灸甲乙经（黄龙祥校本）",
        "path": ROOT / "黄帝针灸甲乙经  （黄龙祥校本）.pdf",
        "kind": "pdf",
        "source_name": "黄龙祥校注本",
        "meta": _pdf_meta("modern"),
    },
    {
        "title": "针灸甲乙经校注（上册）",
        "path": ROOT / "针灸甲乙经校注（上册）.pdf",
        "kind": "pdf",
        "source_name": "黄龙祥校注本",
        "meta": _pdf_meta("modern"),
    },
    {
        "title": "针灸甲乙经（古今医统正脉全书本）",
        "path": ROOT / "针灸甲乙经.十二卷.晋.皇甫谧.编.明万历二十九年吴勉学刊.古今医统正脉全书本.pdf",
        "kind": "pdf",
        "source_name": "古今医统正脉全书本",
        "meta": _pdf_meta("public_domain"),
        "store_raw": False,  # 1GB hi-res scan — do not store blob in DB
    },
]


async def _reset(session) -> int:
    """Hard-delete the 4 fixture docs (and their chunks) so re-ingest is clean."""
    r = await session.execute(
        select(Document.id).where(
            Document.source_name.in_(["识典古籍(shidianguji.com)", "黄龙祥校注本"]),
            Document.is_deleted.is_(False),
        )
    )
    ids = list(r.scalars())
    for did in ids:
        await session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == did)
        )
        await session.execute(delete(Document).where(Document.id == did))
    await session.commit()
    return len(ids)


async def _exists(session, title: str, source_name: str) -> bool:
    r = await session.execute(
        select(Document.id).where(
            Document.title == title,
            Document.source_name == source_name,
            Document.is_deleted.is_(False),
        )
    )
    return r.first() is not None


async def main(dpi: int, dry_run: bool, reset: bool, only: str | None) -> None:
    await init_database()
    results: list[dict] = []
    try:
        async with async_session_factory() as session:
            if reset:
                n = await _reset(session)
                print(f"RESET: hard-deleted {n} prior fixture doc(s)", flush=True)

            entries = ENTRIES
            if only:
                entries = [e for e in ENTRIES if only in e["title"]]

            for entry in entries:
                title = entry["title"]
                path = entry["path"]
                meta = dict(entry["meta"])
                meta["source_name"] = entry["source_name"]
                meta["dynasty"] = "西晋"
                meta["category"] = "针灸"
                meta["source_url"] = f"file://{path}"

                if await _exists(session, title, entry["source_name"]):
                    print(f"SKIP (exists): {title}", flush=True)
                    continue
                if not path.exists():
                    print(f"MISSING FILE: {path}", flush=True)
                    results.append({"title": title, "status": "missing"})
                    continue
                if dry_run:
                    print(
                        f"DRY-RUN would ingest: {title} ({path.stat().st_size} bytes)",
                        flush=True,
                    )
                    continue

                svc = IngestionService(session)
                t0 = time.time()
                try:
                    if entry["kind"] == "html":
                        text = html_to_text(path.read_text(encoding="utf-8"))
                        if not text.strip():
                            raise ValueError("empty HTML text")
                        r = await svc.ingest_text(title=title, text=text, metadata=meta)
                    else:  # pdf — per-page chunking so page_number is set
                        with open(path, "rb") as f:
                            r = await svc.ingest_pdf_with_pages(
                                title=title,
                                file=f,
                                metadata=meta,
                                store_raw_pdf=entry.get("store_raw", True),
                                ocr_dpi=dpi,
                            )
                    await session.commit()
                    print(
                        f"OK: {title} — doc={r.document_id} chunks={r.chunk_count} "
                        f"chars={r.total_chars} ({time.time()-t0:.1f}s)",
                        flush=True,
                    )
                    results.append(
                        {
                            "title": title,
                            "status": "ok",
                            "chunks": r.chunk_count,
                            "chars": r.total_chars,
                        }
                    )
                except Exception as e:  # noqa: BLE001
                    await session.rollback()
                    print(f"FAIL: {title} — {type(e).__name__}: {e}", flush=True)
                    results.append({"title": title, "status": "fail", "error": str(e)})
    finally:
        await close_database()

    print("\n=== SUMMARY ===", flush=True)
    for r in results:
        print(r, flush=True)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--only", type=str, default=None, help="substring match on title")
    args = ap.parse_args()
    asyncio.run(main(args.dpi, args.dry_run, args.reset, args.only))
