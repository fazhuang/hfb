import datetime

from .config import REPORT_FILES
from .utils import write_text


def render_audit_report(result) -> str:
    lines = []
    lines.append("# Docs Structure Audit")
    lines.append("")
    lines.append(f"Generated at: {datetime.datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    lines.append(f"- Docs root exists: {result.root_exists}")
    lines.append(f"- Directories: {len(result.directories)}")
    lines.append(f"- Markdown files: {len(result.markdown_files)}")
    lines.append(f"- `.md.md` files: {len(result.mdmd_files)}")
    lines.append(f"- Missing YAML header: {len(result.missing_yaml_header)}")
    lines.append(f"- Duplicate document_id groups: {len(result.duplicate_document_ids)}")
    lines.append(f"- Missing README directories: {len(result.missing_readmes)}")
    lines.append(f"- Known duplicate candidates: {len(result.known_duplicate_candidates)}")
    lines.append("")

    sections = [
        ("2. `.md.md` Files", result.mdmd_files),
        ("3. Missing YAML Header", result.missing_yaml_header),
        ("4. Missing README Directories", result.missing_readmes),
        ("5. Known Duplicate Candidates", result.known_duplicate_candidates),
    ]
    for title, items in sections:
        lines.append(f"## {title}")
        lines.append("")
        if items:
            for item in items:
                lines.append(f"- `{item}`")
        else:
            lines.append("- None")
        lines.append("")

    lines.append("## 6. Duplicate document_id")
    lines.append("")
    if result.duplicate_document_ids:
        for doc_id, paths in result.duplicate_document_ids.items():
            lines.append(f"- `{doc_id}`")
            for path in paths:
                lines.append(f"  - `{path}`")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## 7. Markdown File Tree")
    lines.append("")
    for path in result.markdown_files:
        lines.append(f"- `{path}`")
    lines.append("")
    return "\n".join(lines)

def write_audit_report(result):
    out = REPORT_FILES["audit"]
    write_text(out, render_audit_report(result))
    return out

def append_report(kind: str, title: str, actions: list[str]):
    out = REPORT_FILES[kind]
    now = datetime.datetime.now().isoformat(timespec="seconds")
    old = out.read_text(encoding="utf-8", errors="ignore") if out.exists() else f"# {title}\n"
    lines = [old.rstrip(), "", f"## Run: {now}", ""]
    lines.extend([f"- {a}" for a in actions] or ["- No changes."])
    write_text(out, "\n".join(lines) + "\n")
    return out
