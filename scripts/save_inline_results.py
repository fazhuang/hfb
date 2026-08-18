#!/usr/bin/env python3
"""Save all inline scrapling results to JSON files, then rebuild PDF."""

import json
import os
import re
import html as html_mod
from collections import OrderedDict

RAW_DIR = "/Users/likeming/.claude/projects/-Users-likeming-Sites-hfb/53c0911e-9899-4014-a2d4-d5caeffb742f/tool-results/"
OUT_HTML = "/Users/likeming/Sites/hfb/针灸甲乙经_四库全书本.html"
OUT_PDF = "/Users/likeming/Sites/hfb/针灸甲乙经_四库全书本.pdf"
OUT_JSON = os.path.join(RAW_DIR, "all_chapters.json")

# Load from persisted files
all_chapters = {}

for fname in sorted(os.listdir(RAW_DIR)):
    if not fname.startswith("call_00_") or not fname.endswith(".txt"):
        continue
    fpath = os.path.join(RAW_DIR, fname)
    with open(fpath, "r") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        continue
    for item in data.get("result", []):
        content = item.get("content", [""])[0]
        url = item.get("url", "")
        ch_id = url.split("/chapter/")[-1] if "/chapter/" in url else ""
        if ch_id and ch_id not in all_chapters:
            all_chapters[ch_id] = {"content": content, "url": url}

print(f"Loaded {len(all_chapters)} unique chapters from persisted files")
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(all_chapters, f, ensure_ascii=False, indent=2)
print(f"Saved to {OUT_JSON}")
