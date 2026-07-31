#!/usr/bin/env python3
import datetime
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("docs")


def main():
    if not ROOT.exists():
        raise SystemExit("docs/ directory not found. Run from project root.")

    md_files = sorted(ROOT.rglob("*.md"))
    mdmd_files = sorted(ROOT.rglob("*.md.md"))
    dirs = sorted([p for p in ROOT.rglob("*") if p.is_dir()])

    doc_ids = defaultdict(list)
    missing_header = []
    titles = defaultdict(list)

    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---"):
            missing_header.append(str(f))
        m = re.search(r"^document_id:\s*(.+)$", text, re.MULTILINE)
        if m:
            doc_ids[m.group(1).strip()].append(str(f))
        t = re.search(r"^title:\s*(.+)$", text, re.MULTILINE)
        if t:
            titles[t.group(1).strip()].append(str(f))

    duplicate_doc_ids = {k: v for k, v in doc_ids.items() if len(v) > 1}
    duplicate_titles = {k: v for k, v in titles.items() if len(v) > 1}

    known_duplicates = [
        "docs/00-governance/00_Project_Charter.md",
        "docs/00-governance/0001-project-charter.md",
        "docs/00-governance/01_Project_Constitution.md",
        "docs/00-governance/0002-project-constitution.md",
        "docs/07-security/00_Acceptance_Specification.md",
        "docs/07-security/0701_Acceptance_Specification.md",
    ]

    report = []
    report.append("# Docs Structure Audit\n")
    report.append(
        f"Generated at: {datetime.datetime.now().isoformat(timespec='seconds')}\n"
    )
    report.append("## Summary\n")
    report.append(f"- Directories: {len(dirs)}")
    report.append(f"- Markdown files: {len(md_files)}")
    report.append(f"- `.md.md` files: {len(mdmd_files)}")
    report.append(f"- Files missing YAML header: {len(missing_header)}")
    report.append(f"- Duplicate document_id groups: {len(duplicate_doc_ids)}")
    report.append(f"- Duplicate title groups: {len(duplicate_titles)}\n")

    report.append("## `.md.md` Files\n")
    if mdmd_files:
        for p in mdmd_files:
            report.append(f"- {p}")
    else:
        report.append("- None")
    report.append("")

    report.append("## Known Duplicate Candidates\n")
    for p in known_duplicates:
        report.append(f"- {p}: {'exists' if Path(p).exists() else 'missing'}")
    report.append("")

    report.append("## Duplicate document_id\n")
    if duplicate_doc_ids:
        for k, paths in duplicate_doc_ids.items():
            report.append(f"- {k}")
            for p in paths:
                report.append(f"  - {p}")
    else:
        report.append("- None")
    report.append("")

    report.append("## Missing YAML Header\n")
    for p in missing_header[:300]:
        report.append(f"- {p}")
    if len(missing_header) > 300:
        report.append(f"- ... truncated, total {len(missing_header)}")
    report.append("")

    report.append("## File Tree\n")
    for p in md_files:
        report.append(f"- {p}")

    out = ROOT / "DOCS_STRUCTURE_AUDIT.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
