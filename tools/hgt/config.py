from pathlib import Path

DOCS_ROOT = Path("docs")
ARCHIVE_DIR = DOCS_ROOT / "_archive" / "legacy"

KNOWN_DUPLICATE_LEGACY_FILES = [
    DOCS_ROOT / "00-governance" / "00_Project_Charter.md",
    DOCS_ROOT / "00-governance" / "01_Project_Constitution.md",
    DOCS_ROOT / "07-security" / "00_Acceptance_Specification.md",
]

KNOWN_RENAMES = {
    DOCS_ROOT / "03-data" / "0302_Ontology_Specification.md.md": DOCS_ROOT
    / "03-data"
    / "0302_Ontology_Specification.md",
}

REPORT_FILES = {
    "audit": DOCS_ROOT / "DOCS_STRUCTURE_AUDIT.md",
    "upgrade": DOCS_ROOT / "UPGRADE_REPORT.md",
    "changelog": DOCS_ROOT / "DOCS_CHANGELOG.md",
}
