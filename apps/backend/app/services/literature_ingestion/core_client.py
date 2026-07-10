"""
CORE client — metadata-only search via CORE API.
https://api.core.ac.uk/docs/v3
Requires CORE_API_KEY in settings for authenticated requests.
"""

from __future__ import annotations

import httpx

from app.core.settings import settings
from app.services.literature_ingestion import LiteratureItem, _http_client

_BASE = "https://api.core.ac.uk/v3"
_PAGE_SIZE = 10


async def search(
    query: str,
    page: int = 1,
    per_page: int = _PAGE_SIZE,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[list[LiteratureItem], int]:
    """Search CORE for works matching query. Returns (items, total_count)."""
    client = http_client or _http_client()
    try:
        headers = {}
        api_key = getattr(settings, "CORE_API_KEY", "") or ""
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        params = {
            "q": query,
            "limit": str(per_page),
            "offset": str((page - 1) * per_page),
        }
        resp = await client.get(f"{_BASE}/search/works", params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if http_client is None:
            await client.aclose()

    total = data.get("totalHits", 0)
    items: list[LiteratureItem] = []
    for w in data.get("results", []):
        authors = ", ".join(
            a.get("name", "") for a in w.get("authors", [])
        )
        kw = ", ".join(w.get("subjects", []) or [])
        doi = w.get("doi", "") or ""
        items.append(LiteratureItem(
            title=w.get("title", ""),
            source="core",
            source_url=w.get("downloadUrl", "") or f"https://core.ac.uk/works/{w.get('id', '')}",
            authors=authors,
            year=w.get("yearPublished"),
            abstract=w.get("abstract", "") or "",
            keywords=kw,
            doi=doi,
            journal=w.get("publisher", "") or "",
            is_open_access=bool(w.get("downloadUrl")),
            language=w.get("language", {}).get("code", "en") if isinstance(w.get("language"), dict) else "en",
        ))

    return items, total
