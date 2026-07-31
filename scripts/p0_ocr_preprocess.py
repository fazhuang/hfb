#!/usr/bin/env python3
"""
OCR the minimum pages needed to cover the 10 baseline passages from init_dev_baseline.py.
Uses 150 dpi for speed.
Writes page dict JSON to stdout for real-time progress.
"""

import hashlib
import json
import os
import sys
import time

PDF_PATH = "/Users/likeming/Sites/hfb/output/hfb_zhenjiu_jiayi_jing_v1.pdf"
OUT_PATH = "/Users/likeming/Sites/hfb/output/hfb_pdf_ocr_pages.json"

# Baseline passages — we need OCR text from pages that contain these
# (the scanned PDF's 卷1 corresponds to the first few dozen pages)
# We'll OCR pages 1-25 to cover 卷1 and start of 卷2
PAGES_TO_OCR = list(range(1, 26))

sys.stdout.reconfigure(line_buffering=True)

with open(PDF_PATH, "rb") as f:
    raw = f.read()
sha = hashlib.sha256(raw).hexdigest()
print(f"PDF SHA-256: {sha}")

# Check embedded text first (fast path)
from io import BytesIO

from pypdf import PdfReader

reader = PdfReader(BytesIO(raw))
texts = {}

for pg in PAGES_TO_OCR:
    try:
        t = reader.pages[pg - 1].extract_text()
    except Exception:
        t = None
    if t and len(t.strip()) > 20:
        texts[pg] = t.strip()
        print(f"  p{pg}: embedded {len(t.strip())} chars")

need_ocr = [p for p in PAGES_TO_OCR if p not in texts]
print(f"Embedded: {len(texts)}, Need OCR: {len(need_ocr)}")

if not need_ocr:
    with open(OUT_PATH, "w") as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)
    print(f"Done — saved {len(texts)} pages")
    sys.exit(0)

# Use pdftoppm for faster rendering (single pages, lower dpi)
import subprocess

tmpdir = "/Users/likeming/Sites/hfb/output/ocr_tmp"
os.makedirs(tmpdir, exist_ok=True)

for pg in sorted(need_ocr):
    t0 = time.time()
    out_prefix = os.path.join(tmpdir, f"p{pg:04d}")
    # pdftoppm is faster than pdf2image for single pages
    r = subprocess.run(
        [
            "pdftoppm",
            "-f",
            str(pg),
            "-l",
            str(pg),
            "-r",
            "200",
            "-png",
            "-singlefile",
            PDF_PATH,
            out_prefix,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    png_path = out_prefix + ".png"
    render_time = time.time() - t0

    if not os.path.exists(png_path):
        print(f"  p{pg}: render FAILED in {render_time:.1f}s — {r.stderr[:100]}")
        continue
    print(f"  p{pg}: rendered in {render_time:.1f}s")

    # OCR with tesseract
    txt_path = png_path + ".txt"
    r = subprocess.run(
        ["tesseract", png_path, png_path, "-l", "chi_sim", "--psm", "6"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    ocr_time = time.time() - t0 - render_time
    try:
        with open(txt_path, "r") as f:
            text = f.read()
    except Exception:
        text = ""

    if text and text.strip():
        texts[pg] = text.strip()
        preview = text.strip()[:80].replace("\n", " ")
        print(f"  p{pg}: OCR {len(text.strip())} chars in {ocr_time:.1f}s → {preview}")
    else:
        print(f"  p{pg}: OCR empty in {ocr_time:.1f}s")

    # Save incrementally
    with open(OUT_PATH, "w") as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)

    # Clean up temp files for this page
    for ext in [".png", ".txt"]:
        try:
            os.remove(png_path.replace(".png", ext))
        except Exception:
            pass

total = time.time() - t0 if "t0" in dir() else 0
print(f"\nDone: {len(texts)} pages in total")
print(f"Saved to {OUT_PATH}")
