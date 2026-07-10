"""
Literature metadata ingestion — search, deduplicate, and store paper metadata
from open-access sources. Never downloads full text. Always records source_url.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import httpx

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Shared result shape — all clients normalize into this
# ---------------------------------------------------------------------------

@dataclass
class LiteratureItem:
    """Normalized metadata record from any source."""

    title: str
    source_url: str
    source: str  # "openalex", "crossref", "core", "pubmed", "internet_archive"
    authors: str = ""
    year: int | None = None
    abstract: str = ""
    keywords: str = ""
    doi: str = ""
    journal: str = ""
    is_open_access: bool = False
    language: str = "en"

    def dedup_key(self) -> str:
        """Deterministic dedup: DOI if available, else normalized title+year."""
        if self.doi:
            return f"doi:{self.doi.lower().strip()}"
        norm = " ".join(self.title.lower().split())
        return f"title:{norm}|{self.year or ''}"


# ---------------------------------------------------------------------------
# Ingestion job — audit trail
# ---------------------------------------------------------------------------

@dataclass
class IngestionJob:
    """Audit log for each ingestion run."""

    id: str = field(default_factory=lambda: str(uuid4()))
    source: str = ""
    query: str = ""
    total_found: int = 0
    new_added: int = 0
    duplicates_skipped: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    success: bool = False
    started_at: str = ""
    finished_at: str = ""

    def start(self) -> None:
        self.started_at = datetime.now(timezone.utc).isoformat()

    def finish(self) -> None:
        self.finished_at = datetime.now(timezone.utc).isoformat()
        # ponytail: success = no errors at all. Partial = error_count > 0.
        self.success = self.error_count == 0


# ---------------------------------------------------------------------------
# Shared HTTP client factory
# ---------------------------------------------------------------------------

def _http_client(timeout: float = 15.0) -> httpx.AsyncClient:
    from app.core.settings import settings

    email = getattr(settings, "CONTACT_EMAIL", "") or "dev@huangfumi.org"
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        headers={
            "User-Agent": f"HuangfuMi-Platform/0.2 (mailto:{email})",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        },
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Dedup against existing DB records
# ---------------------------------------------------------------------------

async def filter_new_items(
    session: "AsyncSession",
    items: list[LiteratureItem],
) -> list[LiteratureItem]:
    """Filter out items already in the DB (by DOI or title+year match)."""
    if not items:
        return []

    from app.models.paper import Paper
    from sqlalchemy import func, or_, select

    # Collect candidate keys
    dois = [i.doi.lower().strip() for i in items if i.doi]
    conditions: list = []
    if dois:
        conditions.append(func.lower(Paper.doi).in_(dois))
    # For items without DOI, check title + year
    for i in items:
        if not i.doi:
            conditions.append(
                (Paper.title == i.title) & (Paper.year == i.year)
            )

    if not conditions:
        return items

    stmt = select(
        func.lower(Paper.doi).label("doi_lower"),
        Paper.title,
        Paper.year,
    ).where(
        Paper.is_deleted.is_(False),
        or_(*conditions),
    )
    result = await session.execute(stmt)
    rows = result.fetchall()

    existing_dois: set[str] = {row.doi_lower for row in rows if row.doi_lower}
    existing_title_years: set[tuple[str, int | None]] = {(row.title, row.year) for row in rows if not row.doi_lower}

    new_items: list[LiteratureItem] = []
    for item in items:
        if item.doi and item.doi.lower().strip() in existing_dois:
            continue
        if not item.doi and (item.title, item.year) in existing_title_years:
            continue
        new_items.append(item)
    return new_items
