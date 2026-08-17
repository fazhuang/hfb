#!/usr/bin/env python3
"""
Wikisource Single Strict Tail Editorial Pipeline & Full-Field Replay Cleaner (v10.0)

Implements the "Editorial Mode" (编校模式) Academic Evidence Pipeline:
1. Extracts Raw DOM Text Snapshot (16,705 chars, SHA-256: 8b8c8979...).
2. Single Strict Tail Rule: ONLY evaluates the VERY LAST non-empty line (rule-wikisource-tail-category-v1.0). Zero global text line scanning.
3. Complete Audit Trail: Records `raw_dom_start` (16691), `raw_dom_end` (16705), `stripped_text`, `input_sha256`, and `output_sha256`.
4. Full Field Offline Replay Verification: Verifies raw_dom_text, canonical_body_text, lengths, SHA-256 hashes, and applied_editorial_rules byte-by-byte.
5. Uses non-assert `if ...: raise ValueError()` checks ensuring `python -O` safety.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from html.parser import HTMLParser
import os
import ssl
import sys
import unicodedata
import urllib.request

try:
    import certifi
    DEFAULT_CAFILE = certifi.where()
except ImportError:
    DEFAULT_CAFILE = None

EXPECTED_OLDID = 794138
FIXTURE_PATH = "tests/fixtures/gold_benchmark_v03.json"

# Standard HTML5 Void Elements (never have closing tags)
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}

# Block Elements (preserve paragraph/line boundaries)
BLOCK_ELEMENTS = {
    "p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"
}


class WikisourcePureStructuralDOMCleaner(HTMLParser):
    """100% Pure Structural HTMLParser extracting raw DOM text without text blacklisting."""

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.drop_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        tag_class = attr_dict.get("class", "") or ""
        tag_id = attr_dict.get("id", "") or ""

        should_drop_container = False
        if tag in ("style", "script"):
            should_drop_container = True
        elif any(
            c in tag_class
            for c in (
                "noprint",
                "mw-jump-link",
                "navbox",
                "ws-header",
                "ws-footer",
                "headertemplate",
                "header-container",
                "licenseContainer",
                "catlinks",
                "mw-normal-catlinks",
                "mw-hidden-catlinks",
            )
        ):
            should_drop_container = True
        elif any(
            i in tag_id
            for i in ("header", "navigation", "mw-head", "catlinks", "footer", "mw-panel")
        ):
            should_drop_container = True

        if tag not in VOID_ELEMENTS:
            if should_drop_container or self.drop_stack:
                self.drop_stack.append(tag)

        if not self.drop_stack and tag in BLOCK_ELEMENTS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.drop_stack and tag in BLOCK_ELEMENTS:
            self.text_parts.append("\n")

        if tag in VOID_ELEMENTS:
            return
        if self.drop_stack and self.drop_stack[-1] == tag:
            self.drop_stack.pop()

    def handle_data(self, data: str) -> None:
        if not self.drop_stack:
            self.text_parts.append(data)


def apply_strict_tail_editorial_rules(raw_dom_text: str) -> tuple[str, list[dict]]:
    """
    Single Strict Tail Editorial Rule: ONLY evaluates the VERY LAST non-empty line.
    Returns: (canonical_editorial_text, applied_rules_log)
    """
    lines = [line.strip() for line in raw_dom_text.splitlines() if line.strip()]
    if not lines:
        return raw_dom_text, []

    applied_rules: list[dict] = []

    # Single Strict Rule: ONLY evaluate the VERY LAST non-empty line!
    last_line = lines[-1]
    is_tail_category = (
        last_line == "<子部,醫家類,鍼灸甲乙經>"
        or last_line == "&lt;子部,醫家類,鍼灸甲乙經&gt;"
        or (last_line.startswith("<子部") and last_line.endswith(">"))
        or (last_line.startswith("&lt;子部") and last_line.endswith("&gt;"))
    )

    raw_dom_nfc = unicodedata.normalize("NFC", raw_dom_text)

    if is_tail_category:
        editorial_lines = lines[:-1]
        canonical_text = "\n".join(editorial_lines)
        canonical_nfc = unicodedata.normalize("NFC", canonical_text)

        start_span = raw_dom_nfc.rfind(last_line)
        end_span = start_span + len(last_line) if start_span != -1 else len(raw_dom_nfc)

        applied_rules.append({
            "rule_id": "rule-wikisource-tail-category-v1.0",
            "description": "Strip untagged Wikisource category metadata strictly at the last non-empty line",
            "raw_dom_start": start_span,
            "raw_dom_end": end_span,
            "stripped_text": last_line,
            "input_sha256": hashlib.sha256(raw_dom_nfc.encode("utf-8")).hexdigest(),
            "output_sha256": hashlib.sha256(canonical_nfc.encode("utf-8")).hexdigest(),
        })
        return canonical_nfc, applied_rules
    else:
        canonical_text = "\n".join(lines)
        canonical_nfc = unicodedata.normalize("NFC", canonical_text)
        return canonical_nfc, applied_rules


def run_counter_example_regression_tests() -> None:
    """Regression test ensuring middle body text containing `<子部...>` is NEVER deleted."""
    test_middle_category = "鍼灸甲乙經\n正文行 <子部,醫家類,鍼灸甲乙經> 乃正文書誌注\n針灸正文\n<子部,醫家類,鍼灸甲乙經>"
    res_text, res_rules = apply_strict_tail_editorial_rules(test_middle_category)

    if "正文行 <子部,醫家類,鍼灸甲乙經> 乃正文書誌注" not in res_text:
        raise ValueError("Regression test failed: Middle text containing `<子部...>` was incorrectly deleted!")
    if res_text.endswith("<子部,醫家類,鍼灸甲乙經>"):
        raise ValueError("Regression test failed: Last line category was not stripped!")
    if len(res_rules) != 1:
        raise ValueError(f"Regression test failed: Expected 1 rule, got {len(res_rules)}")


def clean_wikisource_editorial_pipeline(raw_html: str) -> dict:
    """Run full Editorial Mode pipeline producing Raw DOM + Canonical Editorial Text + Audit Trail."""
    cleaner = WikisourcePureStructuralDOMCleaner()
    cleaner.feed(raw_html)
    extracted_raw = "".join(cleaner.text_parts)

    raw_dom_lines = [line.strip() for line in extracted_raw.splitlines() if line.strip()]
    raw_dom_text = "\n".join(raw_dom_lines)
    raw_dom_nfc = unicodedata.normalize("NFC", raw_dom_text)
    raw_dom_sha256 = hashlib.sha256(raw_dom_nfc.encode("utf-8")).hexdigest()

    canonical_editorial_nfc, applied_rules = apply_strict_tail_editorial_rules(raw_dom_nfc)
    editorial_sha256 = hashlib.sha256(canonical_editorial_nfc.encode("utf-8")).hexdigest()

    if not raw_dom_nfc.startswith("鍼灸甲乙經"):
        raise ValueError(f"Unexpected start of raw DOM text: {raw_dom_nfc[:50]!r}")
    if not canonical_editorial_nfc.startswith("鍼灸甲乙經"):
        raise ValueError(f"Unexpected start of editorial text: {canonical_editorial_nfc[:50]!r}")

    return {
        "raw_dom_text": raw_dom_nfc,
        "raw_dom_text_sha256": raw_dom_sha256,
        "raw_dom_text_length": len(raw_dom_nfc),
        "canonical_editorial_text": canonical_editorial_nfc,
        "canonical_editorial_text_sha256": editorial_sha256,
        "canonical_editorial_text_length": len(canonical_editorial_nfc),
        "applied_editorial_rules": applied_rules,
    }


def fetch_wikisource_revision(oldid: int = EXPECTED_OLDID) -> tuple[str, int]:
    """Fetch exact Wikisource revision HTML over enforced TLS."""
    url = (
        f"https://zh.wikisource.org/w/api.php?action=parse&"
        f"oldid={oldid}&prop=text|revid&format=json"
    )

    if DEFAULT_CAFILE:
        ctx = ssl.create_default_context(cafile=DEFAULT_CAFILE)
    else:
        ctx = ssl.create_default_context()

    req = urllib.request.Request(
        url, headers={"User-Agent": "HFB-Research-Agent/10.0"}
    )
    with urllib.request.urlopen(req, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if "parse" not in data or "revid" not in data["parse"]:
        raise ValueError(f"Invalid API response for oldid={oldid}: {data}")

    fetched_revid = data["parse"]["revid"]
    if fetched_revid != oldid:
        raise ValueError(f"Revision mismatch! Expected {oldid}, got {fetched_revid}")

    raw_html = data["parse"]["text"]["*"]
    return raw_html, fetched_revid


def main() -> None:
    parser = argparse.ArgumentParser(description="Wikisource Single Strict Tail Editorial Pipeline & Full Field Replay Cleaner")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write updated fixture to disk (default is read-only verification mode)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run clean verification offline using raw_html_payload stored in fixture",
    )
    args = parser.parse_args()

    run_counter_example_regression_tests()

    if args.offline:
        print(f"Running offline cleaner verification from {FIXTURE_PATH}...")
        if not os.path.exists(FIXTURE_PATH):
            print(f"ERROR: Fixture {FIXTURE_PATH} not found for offline mode!")
            sys.exit(1)
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            fixture_data = json.load(f)

        # 1. Revision Integrity Check
        if fixture_data.get("revid") != EXPECTED_OLDID:
            raise ValueError(f"Fixture revid mismatch: expected {EXPECTED_OLDID}, got {fixture_data.get('revid')}")
            
        # 2. Raw HTML Integrity Check
        raw_html = fixture_data["raw_html_payload"]
        computed_raw_sha256 = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()
        if computed_raw_sha256 != fixture_data.get("raw_html_sha256"):
            raise ValueError("Fixture raw_html_sha256 integrity check failed!")

        # 3. Full Field Pipeline Replay Verification (Verifying exact text content, lengths, hashes, and rules)
        replayed = clean_wikisource_editorial_pipeline(raw_html)

        if fixture_data.get("raw_dom_text") != replayed["raw_dom_text"]:
            raise ValueError("Fixture raw_dom_text exact text content replay mismatch!")
        if fixture_data.get("raw_dom_text_length") != replayed["raw_dom_text_length"]:
            raise ValueError("Fixture raw_dom_text_length replay mismatch!")
        if fixture_data.get("raw_dom_text_sha256") != replayed["raw_dom_text_sha256"]:
            raise ValueError("Fixture raw_dom_text_sha256 replay mismatch!")

        if fixture_data.get("canonical_body_text") != replayed["canonical_editorial_text"]:
            raise ValueError("Fixture canonical_body_text exact text content replay mismatch!")
        if fixture_data.get("canonical_body_text_length") != replayed["canonical_editorial_text_length"]:
            raise ValueError("Fixture canonical_body_text_length replay mismatch!")
        if fixture_data.get("canonical_body_text_sha256") != replayed["canonical_editorial_text_sha256"]:
            raise ValueError("Fixture canonical_body_text_sha256 replay mismatch!")

        if fixture_data.get("applied_editorial_rules") != replayed["applied_editorial_rules"]:
            raise ValueError("Fixture applied_editorial_rules audit log replay mismatch!")

        revid = fixture_data["revid"]
        print("SUCCESS: Offline Full Field Byte-for-Byte Pipeline Replay Verification Passed!")
    else:
        print(f"Fetching fixed Wikisource revision oldid={EXPECTED_OLDID} over strict TLS...")
        raw_html, revid = fetch_wikisource_revision(EXPECTED_OLDID)

    pipeline_result = clean_wikisource_editorial_pipeline(raw_html)
    raw_html_hash = hashlib.sha256(raw_html.encode("utf-8")).hexdigest()

    print(f"Fetched Revision ID: {revid}")
    print(f"Raw DOM NFC Length: {pipeline_result['raw_dom_text_length']}")
    print(f"Raw DOM NFC SHA-256: {pipeline_result['raw_dom_text_sha256']}")
    print(f"Editorial NFC Length: {pipeline_result['canonical_editorial_text_length']}")
    print(f"Editorial NFC SHA-256: {pipeline_result['canonical_editorial_text_sha256']}")
    print(f"Applied Editorial Rules Count: {len(pipeline_result['applied_editorial_rules'])}")

    if os.path.exists(FIXTURE_PATH):
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)

        existing_hash = existing.get("canonical_body_text_sha256")
        if existing_hash == pipeline_result["canonical_editorial_text_sha256"]:
            print("SUCCESS: Local fixture canonical SHA-256 matches cleaner output exactly!")
        else:
            print(f"WARNING: Hash mismatch! Local={existing_hash}, Cleaner={pipeline_result['canonical_editorial_text_sha256']}")
            if not args.write:
                sys.exit(1)

    if args.write:
        current_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        fixture = {
            "title": "鍼灸甲乙經_(四庫全書本)/卷03",
            "revid": revid,
            "fetched_at": current_utc,
            "parser_version": "hfb-single-tail-editorial-pipeline-v10.0",
            "governance_mode": "editorial_mode",
            "unicode_normalization": "NFC",
            "raw_html_sha256": raw_html_hash,
            "raw_dom_text_sha256": pipeline_result["raw_dom_text_sha256"],
            "raw_dom_text_length": pipeline_result["raw_dom_text_length"],
            "canonical_body_text_sha256": pipeline_result["canonical_editorial_text_sha256"],
            "canonical_body_text_length": pipeline_result["canonical_editorial_text_length"],
            "applied_editorial_rules": pipeline_result["applied_editorial_rules"],
            "body_text_sample": pipeline_result["canonical_editorial_text"][:200],
            "canonical_body_text": pipeline_result["canonical_editorial_text"],
            "raw_dom_text": pipeline_result["raw_dom_text"],
            "raw_html_payload": raw_html,
            "seed_bindings": {
                "document_id": "doc-jyaj-sikushu",
                "version_id": "ver-jyaj-sikushu",
                "passage_id": "pas-jyaj-v03-001",
                "source_ref_id": "sr-jyaj-sikushushu-v03",
            },
        }
        with open(FIXTURE_PATH, "w", encoding="utf-8") as f:
            json.dump(fixture, f, ensure_ascii=False, indent=2)
        print(f"FIXTURE WRITTEN TO {FIXTURE_PATH} with timestamp {current_utc}")


if __name__ == "__main__":
    main()
