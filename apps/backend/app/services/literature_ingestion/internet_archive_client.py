"""
Internet Archive client — metadata-only search via Internet Archive Search API.
https://archive.org/advancedsearch.php
"""

from __future__ import annotations

import httpx

from app.services.literature_ingestion import LiteratureItem, _http_client

_BASE = "https://archive.org"
_PAGE_SIZE = 25


async def search(
    query: str,
    page: int = 1,
    per_page: int = _PAGE_SIZE,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[list[LiteratureItem], int]:
    """Search Internet Archive for texts matching query. Returns (items, total_count)."""
    client = http_client or _http_client()
    try:
        params = {
            "q": f"({query}) AND mediatype:texts",
            "fl": "identifier,title,creator,year,description,subject,language,source,doi,licenseurl",
            "output": "json",
            "rows": str(per_page),
            "page": str(page),
            "sort": "relevance",
        }
        resp = await client.get(f"{_BASE}/advancedsearch.php", params=params)
        resp.raise_for_status()
        data = resp.json()
    finally:
        if http_client is None:
            await client.aclose()

    response = data.get("response", {})
    total = response.get("numFound", 0)
    docs = response.get("docs", [])

    items: list[LiteratureItem] = []
    for d in docs:
        identifier = d.get("identifier", "")
        source_url = f"https://archive.org/details/{identifier}" if identifier else ""
        doi = _extract_doi(d)
        item = LiteratureItem.try_create(
            title=d.get("title", ""),
            source="internet_archive",
            source_url=source_url,
            authors=_join_creators(d.get("creator")),
            year=int(d.get("year", 0)) if d.get("year") else None,
            abstract=" ".join(d.get("description", []) if isinstance(d.get("description"), list) else [d.get("description", "") or ""])[:1000],
            keywords=", ".join(d.get("subject", []) or []),
            doi=doi,
            journal="",
            is_open_access=_is_ia_oa(d),
            language=_first_lang(d),
        )
        if item is not None:
            items.append(item)

    return items, total


def _join_creators(creator: str | list[str] | None) -> str:
    if isinstance(creator, list):
        return ", ".join(creator)
    return creator or ""


def _extract_doi(doc: dict) -> str:
    """IA stores DOI in various fields."""
    for field in ("doi", "identifier"):
        val = doc.get(field)
        if isinstance(val, str) and val.startswith("10."):
            return val
        if isinstance(val, list):
            for v in val:
                if isinstance(v, str) and v.startswith("10."):
                    return v
    return ""


def _is_ia_oa(doc: dict) -> bool:
    """Internet Archive texts are generally public domain or open access."""
    license_url = (doc.get("licenseurl", "") or "").lower()
    if any(t in license_url for t in ("creativecommons", "publicdomain", "cc0", "cc-by")):
        return True
    return True  # ponytail: IA texts are by nature open-access


def _first_lang(doc: dict) -> str:
    lang = doc.get("language")
    if isinstance(lang, str):
        return lang[:5]
    if isinstance(lang, list) and lang:
        return str(lang[0])[:5]
    return "en"
