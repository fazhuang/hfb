from .config import DOCS_ROOT, ARCHIVE_DIR, KNOWN_RENAMES, KNOWN_DUPLICATE_LEGACY_FILES
from .utils import archive_file

def scaffold_docs(root=DOCS_ROOT) -> list[str]:
    actions = []
    if not root.exists():
        return [f"Docs root not found: {root}"]

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    for src, dst in KNOWN_RENAMES.items():
        if src.exists():
            if dst.exists():
                archived = archive_file(src, ARCHIVE_DIR)
                actions.append(f"Archived duplicate rename source: {src} -> {archived}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                src.rename(dst)
                actions.append(f"Renamed malformed file: {src} -> {dst}")

    for path in KNOWN_DUPLICATE_LEGACY_FILES:
        if path.exists():
            archived = archive_file(path, ARCHIVE_DIR)
            actions.append(f"Archived known legacy duplicate: {path} -> {archived}")

    return actions
