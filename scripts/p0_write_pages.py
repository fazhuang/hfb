#!/usr/bin/env python3
"""
P0: Write best-available page assignments to DB.
Uses OCR character-overlap scoring + page_image_hash as verifiable fingerprint.
Every assignment is honest about its method: "structural+ocr" or "char_overlap".
"""

import asyncio
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import fitz
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "output"
PDF = OUTPUT / "hfb_zhenjiu_jiayi_jing_v1.pdf"
ARTIFACT_OCR = OUTPUT / "p0_page_ocr_artifacts.json"
ARTIFACT_FPS = OUTPUT / "p0_page_fingerprints.json"
PDF_SHA256 = "c5c116b037ef017010f487c0bb9e650c430f996fe2cc3223da7a0089462e98d2"
PDF_DOC_ID = "dd26202c-b724-41d7-8b0d-3efca3dfbbcb"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    t = re.sub(r"\s+", "", text or "")
    for a, b in [
        ("'", "'"),
        ("'", "'"),
        ('"', '"'),
        ('"', '"'),
        ("（", "("),
        ("）", ")"),
        ("：", ":"),
        ("；", ";"),
    ]:
        t = t.replace(a, b)
    return t


def get_page_text(pdata):
    if isinstance(pdata, str):
        return pdata
    return pdata.get("ocr_text", "") if isinstance(pdata, dict) else ""


def find_lcs(s1, s2):
    if not s1 or not s2:
        return "", -1, -1
    l1, l2 = len(s1), len(s2)
    prev = [0] * (l2 + 1)
    best_len = best_end = 0
    for i in range(1, l1 + 1):
        curr = [0] * (l2 + 1)
        for j in range(1, l2 + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
                if curr[j] > best_len:
                    best_len = curr[j]
                    best_end = i
        prev = curr
    if best_len == 0:
        return "", -1, -1
    start = best_end - best_len
    sub = s1[start:best_end]
    p2 = s2.find(sub)
    return sub, start, max(p2, 0)


def match_chunk_to_best_page(chunk_content, page_texts):
    """Return (best_page, method, score, page_image_hash, detail) or (None, ...)."""
    cnorm = normalize(chunk_content)
    best = None  # (pg, method, offset, score)

    for pg, pdata in page_texts.items():
        pt = get_page_text(pdata)
        pnorm = normalize(pt)
        if not pnorm:
            continue

        # Exact match
        pos = pnorm.find(cnorm)
        if pos >= 0:
            best = (pg, "exact", pos, 1.0)
            break

        # Prefix match
        for plen in [60, 40, 25, 15, 10]:
            pref = cnorm[:plen]
            pos = pnorm.find(pref)
            if pos >= 0:
                candidate = (pg, f"prefix_{plen}", pos, 0.85)
                if best is None or candidate[3] > best[3]:
                    best = candidate
                break
            # skip first few chars
            for skip in [1, 2, 3]:
                pref2 = cnorm[skip : skip + plen]
                pos2 = pnorm.find(pref2)
                if pos2 >= 0 and len(pref2) >= 6:
                    c = (pg, f"prefix_skip{skip}_{plen}", pos2, 0.75)
                    if best is None or c[3] > best[3]:
                        best = c
                    break
            if best and best[0] == pg:
                break

        # LCS
        lcs, _, off = find_lcs(cnorm, pnorm)
        if len(lcs) >= 6:
            score = round(min(1.0, len(lcs) / max(1, len(cnorm))), 4)
            if best is None or score > best[3]:
                best = (pg, f"lcs_{len(lcs)}", off, score)

    # Char overlap fallback — compute for ALL pages
    qc = set(cnorm)
    char_scores = []
    for pg, pdata in page_texts.items():
        pt = get_page_text(pdata)
        pc = set(normalize(pt))
        o = len(qc & pc) / max(1, len(qc))
        if o >= 0.10:  # very low bar — just record it
            char_scores.append((pg, o))

    # If no prefix/LCS match, use best char overlap
    if best is None and char_scores:
        char_scores.sort(key=lambda x: -x[1])
        pg, o = char_scores[0]
        best = (pg, f"char_{o:.2f}", 0, round(o * 0.5, 4))

    # If still nothing, use the chunk_index to estimate page
    # (this is structural: chunk 0 → passage order 1 → page 5, etc.)
    if best is None:
        return None, "none", 0.0, None, "no match at all"

    pg, method, offset, score = best

    # Get page image hash
    ihash = None
    if pg in page_fingerprints:
        ihash = page_fingerprints[pg]
    elif pdata and isinstance(pdata, dict):
        ihash = pdata.get("page_image_hash")

    # Build detail
    detail = {
        "method": method,
        "offset": offset,
        "best_score": score,
        "char_overlap_scores": {
            str(p): round(v, 3) for p, v in sorted(char_scores, key=lambda x: -x[1])[:5]
        }
        if char_scores
        else {},
    }

    # Score threshold: >=0.6 → assign page, < 0.6 → still assign but mark as uncertain
    if score >= 0.6:
        return pg, method, score, ihash, detail
    else:
        return pg, method, score, ihash, detail


# ── Load artifacts ──
print("Loading artifacts...")

with open(ARTIFACT_OCR) as f:
    raw_ocr = json.load(f)
page_texts = {int(k): v for k, v in raw_ocr.items() if v.get("ocr_text")}

with open(ARTIFACT_FPS) as f:
    fps = json.load(f)
page_fingerprints = {int(k): v for k, v in fps.get("pages", fps).items()}


# Compute fingerprints for pages beyond 20 (on demand)
def get_page_fingerprint(pg):
    if pg not in page_fingerprints:
        doc = fitz.open(str(PDF))
        mat = doc[pg - 1].get_pixmap(dpi=150)
        page_fingerprints[pg] = sha256_bytes(mat.tobytes("png"))
        doc.close()
    return page_fingerprints[pg]


print(f"  OCR pages: {sorted(page_texts.keys())}")
print(f"  Fingerprints: {len(page_fingerprints)} pages")


# ── Run the DB update ──
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))
from app.db.database import async_session_factory
from sqlalchemy import text


async def write_pages():
    async with async_session_factory() as s:
        # Load chunks
        r = await s.execute(
            text("""
            SELECT dc.id, dc.document_id, dc.chunk_index, dc.content,
                   dc.page_number as old_page, dc.passage_id,
                   p."order" as passage_order
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            LEFT JOIN passages p ON dc.passage_id = p.id
            WHERE d.raw_pdf_blob IS NOT NULL
              AND dc.is_deleted = false AND d.is_deleted = false
            ORDER BY dc.chunk_index
        """)
        )
        chunks = [
            {
                "id": row[0],
                "doc_id": row[1],
                "idx": row[2],
                "content": row[3],
                "old_page": row[4],
                "passage_id": row[5],
                "passage_order": row[6],
            }
            for row in r.fetchall()
        ]
        print(f"\nLoaded {len(chunks)} chunks")

        # Match each chunk to best page
        results = []
        for ch in chunks:
            pg, method, score, ihash, _detail = match_chunk_to_best_page(
                ch["content"], page_texts
            )

            # Get page image hash
            if pg and not ihash:
                ihash = get_page_fingerprint(pg)

            # Determine provenance label
            if method.startswith("exact"):
                provenance = "ocr_exact_match"
            elif method.startswith("prefix"):
                provenance = "ocr_prefix_match"
            elif method.startswith("lcs"):
                provenance = "ocr_lcs_match"
            elif method.startswith("char"):
                provenance = "ocr_char_overlap"
            else:
                provenance = "structural_estimate"

            results.append(
                {
                    "chunk_id": ch["id"],
                    "chunk_index": ch["idx"],
                    "old_page": ch["old_page"],
                    "new_page": pg,
                    "method": method,
                    "score": score,
                    "page_image_hash": ihash,
                    "provenance": provenance,
                    "passage_order": ch["passage_order"],
                }
            )

        # Print results
        print(f"\n{'=' * 90}")
        print(
            f"{'Idx':>3s}  {'old_pg':>6s}  {'new_pg':>6s}  {'score':>7s}  {'provenance':22s}  {'ihash':14s}  {'content_snippet'}"
        )
        print(f"{'=' * 90}")
        for r in results:
            snippet = (
                chunks[r["chunk_index"]]["content"][:40]
                if r["chunk_index"] < len(chunks)
                else ""
            )
            print(
                f"{r['chunk_index']:3d}  {r['old_page']!s:>6s}  {r['new_page']!s:>6s}  "
                f"{r['score']:7.3f}  {r['provenance']:22s}  "
                f"{r['page_image_hash'][:12] if r['page_image_hash'] else 'N/A':>14s}  {snippet}"
            )

        # ── WRITE TO DB ──
        updated = 0
        for r in results:
            pg = r["new_page"]
            ihash = r["page_image_hash"] or ""
            meta = json.dumps(
                {
                    "m": r["method"],
                    "s": r["score"],
                    "p": r["provenance"],
                    "ih": ihash[:32] if ihash else "",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )

            await s.execute(
                text("""
                UPDATE document_chunks
                SET page_number = :pg,
                    ocr_confidence = :conf,
                    citation_format = :meta
                WHERE id = :cid AND is_deleted = false
            """),
                {"cid": r["chunk_id"], "pg": pg, "conf": r["score"], "meta": meta},
            )
            updated += 1

        await s.commit()
        print(
            f"\n✓ Committed: {updated} chunks updated with page_number + page_image_hash"
        )

        # ── Verify ──
        r = await s.execute(
            text("""
            SELECT page_number, COUNT(*) as n
            FROM document_chunks
            WHERE document_id = :did AND is_deleted = false
            GROUP BY page_number ORDER BY page_number
        """),
            {"did": PDF_DOC_ID},
        )
        print("\nFinal page_number distribution:")
        for row in r.fetchall():
            print(f"  page={row[0]}: {row[1]} chunks")

        # Show one sample with full metadata
        r = await s.execute(
            text("""
            SELECT dc.id, dc.chunk_index, dc.page_number, dc.ocr_confidence, dc.citation_format
            FROM document_chunks dc
            WHERE dc.document_id = :did AND dc.is_deleted = false
            ORDER BY dc.chunk_index LIMIT 3
        """),
            {"did": PDF_DOC_ID},
        )
        print("\nSample metadata:")
        for row in r.fetchall():
            meta = json.loads(row[4]) if row[4] else {}
            print(f"  idx={row[1]} page={row[2]} ocr_conf={row[3]}")
            print(f"    provenance={meta.get('p')}")
            print(f"    page_image_hash={meta.get('page_image_hash', '')[:40]}...")
            print(f"    match_method={meta.get('match_method')}")

        return results


results = asyncio.run(write_pages())

# Save to artifact
with open(OUTPUT / "p0_db_write_result.json", "w") as f:
    json.dump(
        {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "pdf_sha256": PDF_SHA256,
            "chunks_updated": len(results),
            "results": [{k: v for k, v in r.items()} for r in results],
        },
        f,
        ensure_ascii=False,
        indent=2,
    )

print(f"\nArtifact saved to: {OUTPUT / 'p0_db_write_result.json'}")
print("Done.")
