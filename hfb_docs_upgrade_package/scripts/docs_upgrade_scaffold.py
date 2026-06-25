#!/usr/bin/env python3
"""
Docs upgrade scaffold for 皇甫谧数字人文平台.

This script does NOT rewrite all documents automatically.
It performs safe normalization helpers:
1. Creates docs/_archive/legacy/
2. Renames known .md.md file if present
3. Moves known duplicate legacy files into archive with timestamp
4. Writes placeholder upgrade report/changelog if absent
5. Runs inventory report
"""

from pathlib import Path
import shutil, datetime, subprocess, sys

ROOT = Path("docs")
ARCHIVE = ROOT / "_archive" / "legacy"

KNOWN_ARCHIVE = [
    ROOT / "00-governance" / "00_Project_Charter.md",
    ROOT / "00-governance" / "01_Project_Constitution.md",
    ROOT / "07-security" / "00_Acceptance_Specification.md",
]

RENAME = {
    ROOT / "03-data" / "0302_Ontology_Specification.md.md":
    ROOT / "03-data" / "0302_Ontology_Specification.md"
}

def archive_file(path: Path, actions):
    if not path.exists():
        return
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    target = ARCHIVE / f"{path.parent.name}__{path.stem}__{ts}{path.suffix}"
    shutil.move(str(path), str(target))
    actions.append(f"Archived {path} -> {target}")

def main():
    if not ROOT.exists():
        raise SystemExit("docs/ directory not found. Run from project root.")

    actions = []
    ARCHIVE.mkdir(parents=True, exist_ok=True)

    for src, dst in RENAME.items():
        if src.exists():
            if dst.exists():
                archive_file(src, actions)
            else:
                src.rename(dst)
                actions.append(f"Renamed {src} -> {dst}")

    for p in KNOWN_ARCHIVE:
        archive_file(p, actions)

    report = ROOT / "UPGRADE_REPORT.md"
    if not report.exists():
        report.write_text("# Docs Upgrade Report\n\n## Actions\n\n" + "\n".join(f"- {a}" for a in actions) + "\n", encoding="utf-8")
    else:
        with report.open("a", encoding="utf-8") as f:
            f.write("\n## Scaffold Actions\n\n")
            for a in actions:
                f.write(f"- {a}\n")

    changelog = ROOT / "DOCS_CHANGELOG.md"
    if not changelog.exists():
        changelog.write_text("# Docs Changelog\n\n## Initial Upgrade Scaffold\n\n" + "\n".join(f"- {a}" for a in actions) + "\n", encoding="utf-8")

    inv = Path("scripts/docs_inventory.py")
    if inv.exists():
        subprocess.run([sys.executable, str(inv)], check=False)

    print("Completed scaffold actions:")
    for a in actions:
        print("-", a)

if __name__ == "__main__":
    main()
