"""
OpenAlex client — metadata-only search via REST API.
https://docs.openalex.org/api-entity/works
"""

from __future__ import annotations

import httpx

from app.services.literature_ingestion import LiteratureItem, _http_client

_BASE = "https://api.openalex.org"
_PAGE_SIZE = 25


async def search(
    query: str,
    page: int = 1,
    per_page: int = _PAGE_SIZE,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[list[LiteratureItem], int]:
    """Search OpenAlex for works matching query. Returns (items, total_count)."""
    client = http_client or _http_client()
    try:
        params = {
            "search": query,
            "per_page": str(per_page),
            "page": str(page),
        }
        resp = await client.get(f"{_BASE}/works", params=params)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if http_client is None:
            await client.aclose()

    total = data.get("meta", {}).get("count", 0)
    items: list[LiteratureItem] = []
    for w in data.get("results", []):
        doi = w.get("doi", "") or ""
        if doi:
            doi = doi.removeprefix("https://doi.org/")
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in w.get("authorships", [])
        )
        kw = ", ".join(
            c.get("display_name", "") for c in w.get("concepts", [])[:10]
        )
        items.append(LiteratureItem(
            title=w.get("title", ""),
            source="openalex",
            source_url=w.get("id", ""),
            authors=authors,
            year=w.get("publication_year"),
            abstract=_first_str(w.get("abstract_inverted_index", {})),
            keywords=kw,
            doi=doi,
            journal=_host_venue_name(w),
            is_open_access=w.get("open_access", {}).get("is_oa", False),
            language=w.get("language", "en") or "en",
        ))

    return items, total


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_str(inverted: dict) -> str:
    """Reconstruct first 500 chars from OpenAlex inverted index abstract."""
    if not inverted:
        return ""
    try:
        ordered: list[tuple[int, str]] = []
        for word, positions in inverted.items():
            for pos in positions:
                ordered.append((pos, word))
        ordered.sort()
        return " ".join(w for _, w in ordered)[:500]
    except Exception:
        return ""


def _host_venue_name(work: dict) -> str:
    """Extract journal/venue name from OpenAlex work."""
    for key in ("primary_location", "locations"):
        loc = work.get(key)
        if loc and isinstance(loc, dict):
            src = loc.get("source") or {}
            name = src.get("display_name", "")
            if name:
                return name
    for loc in work.get("locations", []) or []:
        src = (loc or {}).get("source") or {}
        name = src.get("display_name", "")
        if name:
            return name
    return ""
