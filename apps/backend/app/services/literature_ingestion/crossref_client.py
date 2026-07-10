"""
Crossref client — metadata-only search via REST API.
https://api.crossref.org/swagger-ui/index.html
"""

from __future__ import annotations

import httpx

from app.services.literature_ingestion import LiteratureItem, _http_client

_BASE = "https://api.crossref.org"
_PAGE_SIZE = 20


async def search(
    query: str,
    page: int = 1,
    per_page: int = _PAGE_SIZE,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[list[LiteratureItem], int]:
    """Search Crossref for works matching query. Returns (items, total_count)."""
    client = http_client or _http_client()
    try:
        offset = (page - 1) * per_page
        params = {
            "query": query,
            "rows": str(per_page),
            "offset": str(offset),
        }
        resp = await client.get(f"{_BASE}/works", params=params)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if http_client is None:
            await client.aclose()

    msg = data.get("message", {})
    total = msg.get("total-results", 0)
    items: list[LiteratureItem] = []
    for w in msg.get("items", []):
        doi = w.get("DOI", "")
        authors = ", ".join(
            a.get("given", "") + " " + a.get("family", "")
            for a in w.get("author", [])
        )
        kw_list = w.get("subject", []) or []
        is_oa = _check_crossref_oa(w)
        item = LiteratureItem.try_create(
            title=" ".join((w.get("title", []) or [""])[0].split()),
            source="crossref",
            source_url=f"https://doi.org/{doi}" if doi else w.get("URL", ""),
            authors=authors.strip(),
            year=w.get("published-print", {}).get("date-parts", [[None]])[0][0]
                 or w.get("created", {}).get("date-parts", [[None]])[0][0],
            abstract=_first_abstract(w),
            keywords=", ".join(kw_list),
            doi=doi,
            journal=" ".join((w.get("container-title", []) or [""])[0].split()),
            is_open_access=is_oa,
            language=w.get("language", "en") or "en",
        )
        if item is not None:
            items.append(item)

    return items, total


def _first_abstract(work: dict) -> str:
    raw = work.get("abstract", "")
    if not raw:
        return ""
    # Strip HTML tags ponytail-style — just remove <…> and trim
    import re
    return re.sub(r"<[^>]+>", "", raw).strip()[:1000]


def _check_crossref_oa(work: dict) -> bool:
    """Crossref doesn't have a direct OA flag; check license field."""
    for li in work.get("license", []) or []:
        url = (li.get("URL", "") or "").lower()
        if any(tag in url for tag in ("creativecommons", "open-access", "cc-by")):
            return True
    return False
