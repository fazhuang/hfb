from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .config import DOCS_ROOT, KNOWN_DUPLICATE_LEGACY_FILES
from .utils import extract_yaml_value, has_yaml_header, read_text


@dataclass
class ScanResult:
    root_exists: bool
    directories: list[Path]
    markdown_files: list[Path]
    mdmd_files: list[Path]
    duplicate_document_ids: dict[str, list[Path]]
    missing_yaml_header: list[Path]
    missing_readmes: list[Path]
    known_duplicate_candidates: list[Path]

def scan_docs(root: Path = DOCS_ROOT) -> ScanResult:
    if not root.exists():
        return ScanResult(False, [], [], [], {}, [], [], [])

    directories = sorted([p for p in root.rglob("*") if p.is_dir()])
    markdown_files = sorted(root.rglob("*.md"))
    mdmd_files = sorted(root.rglob("*.md.md"))

    doc_id_map = defaultdict(list)
    missing_yaml_header = []

    for path in markdown_files:
        text = read_text(path)
        doc_id = extract_yaml_value(text, "document_id")
        if doc_id:
            doc_id_map[doc_id].append(path)
        if not has_yaml_header(text) and path.name != "README.md":
            missing_yaml_header.append(path)

    duplicate_document_ids = {k: v for k, v in doc_id_map.items() if len(v) > 1}

    missing_readmes = []
    for directory in directories:
        try:
            rel = directory.relative_to(root)
        except ValueError:
            continue
        if len(rel.parts) <= 2 and not (directory / "README.md").exists():
            missing_readmes.append(directory)

    known_duplicate_candidates = [p for p in KNOWN_DUPLICATE_LEGACY_FILES if p.exists()]

    return ScanResult(
        True,
        directories,
        markdown_files,
        mdmd_files,
        duplicate_document_ids,
        missing_yaml_header,
        missing_readmes,
        known_duplicate_candidates,
    )
