"""
Source whitelist loader — runtime enforcement of source_whitelist.yaml.

Usage:
    from app.services.source_whitelist import get_whitelist
    wl = get_whitelist()
    if not wl.is_source_allowed("crossref", metadata=True):
        raise SourceNotAllowed(...)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


class SourcePolicyEntry:
    """One entry from source_whitelist.yaml."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.name: str = data["name"]
        self.domain: str = data["domain"]
        self.category: str = data["category"]
        self.metadata_allowed: bool = data.get("metadata_allowed", False)
        self.fulltext_allowed: bool = data.get("fulltext_allowed", False)
        self.requires_manual_review: bool = data.get("requires_manual_review", False)


class SourceWhitelist:
    """Runtime source whitelist checker."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.entries: list[SourcePolicyEntry] = [
            SourcePolicyEntry(e) for e in data.get("sources", [])
        ]
        default = data.get("default_policy", {})
        self.default_metadata: bool = default.get("metadata_allowed", False)
        self.default_fulltext: bool = default.get("fulltext_allowed", False)

        # Build lookup by source name — both insertion and lookup use _normalize
        self._by_name: dict[str, SourcePolicyEntry] = {}
        for e in self.entries:
            self._by_name[self._normalize(e.name)] = e

    @staticmethod
    def _normalize(name: str) -> str:
        """Collapse underscores/spaces so both 'Internet Archive' and 'internet_archive' match."""
        return name.lower().replace("_", " ")

    def lookup(self, source_name: str) -> SourcePolicyEntry | None:
        """Return the policy entry for a source, or None if not whitelisted."""
        return self._by_name.get(self._normalize(source_name))

    def is_source_allowed(self, source_name: str, metadata: bool = True) -> bool:
        """Check whether a source is allowed for metadata (or full-text) access.

        Default-deny: unlisted sources are rejected.
        D-category sources are always rejected.
        """
        entry = self.lookup(source_name)
        if entry is None:
            return self.default_metadata if metadata else self.default_fulltext
        if entry.category == "D":
            return False
        if metadata:
            return entry.metadata_allowed
        return entry.fulltext_allowed

    def allowed_sources(self) -> list[str]:
        """Return source names that are allowed for metadata ingestion."""
        return [
            e.name for e in self.entries if e.category != "D" and e.metadata_allowed
        ]


@lru_cache(maxsize=1)
def get_whitelist(config_path: str | None = None) -> SourceWhitelist:
    """Load and cache the source whitelist.

    Looks for source_whitelist.yaml in:
      1. Explicit config_path argument
      2. SOURCE_WHITELIST_PATH env var
      3. backend/app/config/source_whitelist.yaml (relative to this file)
      4. Current working directory
    """
    if config_path:
        path = Path(config_path)
    elif os.environ.get("SOURCE_WHITELIST_PATH"):
        path = Path(os.environ["SOURCE_WHITELIST_PATH"])
    else:
        # Try the canonical location relative to this file
        this_dir = Path(__file__).resolve().parent
        # Walk up: .../services/ -> .../app/ -> .../backend/
        app_dir = this_dir.parent
        candidate = app_dir / "config" / "source_whitelist.yaml"
        if not candidate.exists():
            # Alternative: backend/app/config/ at repo root
            backend_dir = app_dir.parent
            candidate = backend_dir / "app" / "config" / "source_whitelist.yaml"
        if not candidate.exists():
            candidate = Path("backend/app/config/source_whitelist.yaml").resolve()
        path = candidate

    if not path.exists():
        raise FileNotFoundError(
            f"source_whitelist.yaml not found at {path}. "
            "Set SOURCE_WHITELIST_PATH env var or place the file in backend/app/config/"
        )

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return SourceWhitelist(data)
