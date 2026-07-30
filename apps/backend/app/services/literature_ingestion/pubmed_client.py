"""
PubMed / Europe PMC client — metadata-only search via E-utilities & Europe PMC REST API.
https://www.ncbi.nlm.nih.gov/books/NBK25500/
https://europepmc.org/RestfulWebService
"""

from __future__ import annotations

import json
import logging

import httpx

from app.services.literature_ingestion import LiteratureItem, _http_client

logger = logging.getLogger(__name__)

_PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_EUROPE_PMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
_PAGE_SIZE = 20


async def search(
    query: str,
    page: int = 1,
    per_page: int = _PAGE_SIZE,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[list[LiteratureItem], int]:
    """Search PubMed/Europe PMC. Returns (items, total_count).

    Uses Europe PMC as primary (richer metadata, no API key required).
    Falls back to PubMed E-utilities if Europe PMC is unavailable.
    """
    client = http_client or _http_client()
    try:
        return await _search_europe_pmc(client, query, page, per_page)
    except (httpx.HTTPStatusError, httpx.ConnectError, json.JSONDecodeError):
        return await _search_pubmed(client, query, page, per_page)
    finally:
        if http_client is None:
            await client.aclose()


async def _search_europe_pmc(
    client: httpx.AsyncClient, query: str, page: int, per_page: int,
) -> tuple[list[LiteratureItem], int]:
    params = {
        "query": query,
        "resultType": "core",
        "pageSize": str(per_page),
        "cursorMark": "*",
        "page": str(page),
        "format": "json",
    }
    resp = await client.get(f"{_EUROPE_PMC_BASE}/search", params=params)
    resp.raise_for_status()
    data = resp.json()

    result_list = data.get("resultList", {})
    result = result_list.get("result", [])
    total = int(result_list.get("hitCount", 0))

    items: list[LiteratureItem] = []
    for r in result:
        doi = r.get("doi", "") or ""
        item = LiteratureItem.try_create(
            title=r.get("title", ""),
            source="pubmed",
            source_url=f"https://europepmc.org/article/MED/{r.get('id', '')}" if r.get("id") else "",
            authors=r.get("authorString", ""),
            year=int(r.get("pubYear", 0)) if r.get("pubYear") else None,
            abstract=r.get("abstractText", "") or "",
            keywords=r.get("keywordList", {}).get("keyword", []) if isinstance(r.get("keywordList"), dict) else "",
            doi=doi,
            journal=r.get("journalTitle", "") or r.get("journalInfo", {}).get("journal", {}).get("title", ""),
            is_open_access=_check_epmc_oa(r),
            language=r.get("language", "en") or "en",
        )
        if item is not None:
            items.append(item)
            # keywords may be list
            if isinstance(item.keywords, list):
                item.keywords = ", ".join(item.keywords)

    return items, total


async def _search_pubmed(
    client: httpx.AsyncClient, query: str, page: int, per_page: int,
) -> tuple[list[LiteratureItem], int]:
    # 1. ESearch — get IDs
    esearch_params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(per_page),
        "retstart": str((page - 1) * per_page),
        "retmode": "json",
        "sort": "relevance",
    }
    es_resp = await client.get(f"{_PUBMED_BASE}/esearch.fcgi", params=esearch_params)
    es_resp.raise_for_status()
    es_data = es_resp.json()
    id_list = es_data.get("esearchresult", {}).get("idlist", [])
    total = int(es_data.get("esearchresult", {}).get("count", 0))

    if not id_list:
        return [], total

    # 2. EFetch — get metadata
    efetch_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml",
        "rettype": "abstract",
    }
    ef_resp = await client.get(f"{_PUBMED_BASE}/efetch.fcgi", params=efetch_params)
    ef_resp.raise_for_status()

    items = _parse_pubmed_xml(ef_resp.text)
    return items, total


def _parse_pubmed_xml(xml_text: str) -> list[LiteratureItem]:
    """Minimal PubMed XML parser — safe against XXE/billion-laughs."""
    from defusedxml.ElementTree import fromstring

    items: list[LiteratureItem] = []
    root = fromstring(xml_text)
    for article in root.findall(".//PubmedArticle"):
        medline = article.find(".//MedlineCitation")
        if medline is None:
            continue
        art = medline.find(".//Article")
        if art is None:
            continue

        title_el = art.find(".//ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""

        abstract_el = art.find(".//Abstract/AbstractText")
        abstract = "".join(abstract_el.itertext()) if abstract_el is not None else ""

        journal_el = art.find(".//Journal/Title")
        journal = journal_el.text or "" if journal_el is not None else ""

        year_el = art.find(".//Journal/JournalIssue/PubDate/Year")
        year = int(year_el.text) if year_el is not None and year_el.text else None

        # Authors
        authors: list[str] = []
        for au in art.findall(".//AuthorList/Author"):
            last = au.findtext("LastName") or ""
            fore = au.findtext("ForeName") or ""
            authors.append(f"{fore} {last}".strip())
        author_str = ", ".join(authors)

        # DOI
        doi = ""
        for eid in article.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi" and eid.text:
                doi = eid.text

        # Keywords
        kw_list: list[str] = []
        for kw in medline.findall(".//KeywordList/Keyword"):
            if kw.text:
                kw_list.append(kw.text)

        pmid = medline.findtext("PMID") or ""
        item = LiteratureItem.try_create(
            title=title,
            source="pubmed",
            source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
            authors=author_str,
            year=year,
            abstract=abstract,
            keywords=", ".join(kw_list),
            doi=doi,
            journal=journal,
            is_open_access=False,  # PubMed doesn't tag OA directly
            language="en",
        )
        if item is not None:
            items.append(item)

    return items


def _check_epmc_oa(result: dict) -> bool:
    if result.get("isOpenAccess") == "Y":
        return True
    return result.get("openAccess") is True
