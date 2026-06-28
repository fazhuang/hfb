"""
Search Service — unified search across entity types.

Per HFB-PS-1706 Unified Search Product Specification.

MVP approach (per HFB-ARC-0201 Chapter 5):
  - Full-text: PostgreSQL ILIKE (LIKE with contains) across entity fields
  - Semantic/vector: deferred to pgvector integration (schema reserved)
  - Elasticsearch: available in Docker but app-layer search works standalone
  - The service is designed so ES can be swapped in later via a
    SearchBackend abstraction.

Search entity types: person, book, version, passage, paper, document, image
"""
from __future__ import annotations

import math
from typing import Any

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.document import Document
from app.models.image import Image
from app.models.paper import Paper
from app.models.passage import Passage
from app.models.person import Person
from app.models.version import Version
from app.schemas.search import (
    SearchResultItem,
    SearchResponse,
    SuggestItem,
    SearchParams,
)

# ---------------------------------------------------------------------------
# Entity search configuration
# ---------------------------------------------------------------------------

ENTITY_CONFIG: dict[str, dict[str, Any]] = {
    "person": {
        "model": Person,
        "title_field": "name",
        "subtitle_field": "dynasty",
        "search_fields": ["name", "name_pinyin", "courtesy_name", "pseudonym", "biography", "notable_works"],
        "route_prefix": "/persons",
        "snippet_field": "biography",
        "meta_fields": ["dynasty", "birth_year", "death_year", "expertise"],
    },
    "book": {
        "model": Book,
        "title_field": "title",
        "subtitle_field": "dynasty",
        "search_fields": ["title", "title_pinyin", "title_english", "abstract", "category"],
        "route_prefix": "/books",
        "snippet_field": "abstract",
        "meta_fields": ["dynasty", "category", "year", "language"],
    },
    "version": {
        "model": Version,
        "title_field": "version_name",
        "subtitle_field": "era",
        "search_fields": ["version_name", "era", "repository", "editor", "description"],
        "route_prefix": None,  # versions are accessed via book detail
        "snippet_field": "description",
        "meta_fields": ["era", "repository", "editor", "book_id"],
    },
    "passage": {
        "model": Passage,
        "title_field": "content_text",  # first 60 chars
        "subtitle_field": "tags",
        "search_fields": ["content_text", "translation", "notes", "tags"],
        "route_prefix": None,
        "snippet_field": "content_text",
        "meta_fields": ["chapter_id", "version_id", "order"],
    },
    "paper": {
        "model": Paper,
        "title_field": "title",
        "subtitle_field": "journal",
        "search_fields": ["title", "title_english", "authors", "journal", "abstract", "keywords"],
        "route_prefix": None,
        "snippet_field": "abstract",
        "meta_fields": ["authors", "journal", "year", "doi"],
    },
    "document": {
        "model": Document,
        "title_field": "title",
        "subtitle_field": "dynasty",
        "search_fields": ["title", "title_pinyin", "title_english", "abstract", "category"],
        "route_prefix": "/documents",
        "snippet_field": "abstract",
        "meta_fields": ["dynasty", "year", "category", "author_id"],
    },
    "image": {
        "model": Image,
        "title_field": "url",
        "subtitle_field": "caption",
        "search_fields": ["caption", "url", "source"],
        "route_prefix": None,
        "snippet_field": "caption",
        "meta_fields": ["related_entity_type", "related_entity_id", "source"],
    },
}

SEARCHABLE_TYPES = list(ENTITY_CONFIG.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snippet(text: str | None, query: str, max_length: int = 200) -> str | None:
    """Extract a snippet around the first query match in text."""
    if not text or not query:
        return text[:max_length] if text else None

    q_lower = query.lower()
    text_lower = text.lower()
    idx = text_lower.find(q_lower)

    if idx == -1:
        return text[:max_length]

    start = max(0, idx - 60)
    end = min(len(text), idx + len(query) + 60)
    snippet = text[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


def _compute_score(match_count: int, total_fields: int, title_match: bool) -> float:
    """Compute a simple relevance score (0-1)."""
    if match_count == 0:
        return 0.0
    score = 0.3 * (match_count / total_fields)
    if title_match:
        score += 0.5
    score = min(score, 1.0)
    return round(score, 3)


# ---------------------------------------------------------------------------
# SearchService
# ---------------------------------------------------------------------------


class SearchService:
    """Unified search orchestrator.

    Searches across entity types using PostgreSQL ILIKE, scores results,
    returns paginated results with snippets.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Unified Search
    # ------------------------------------------------------------------

    async def search(self, params: SearchParams) -> SearchResponse:
        """Execute a unified search across all requested entity types.

        Returns paginated results sorted by relevance score.
        """
        query = params.q.strip()
        all_results: list[SearchResultItem] = []
        facets: dict[str, list[dict[str, Any]]] = {"entity_type": [], "dynasty": []}

        entity_type_counts: dict[str, int] = {}

        for entity_type in params.entity_types:
            if entity_type not in ENTITY_CONFIG:
                continue

            config = ENTITY_CONFIG[entity_type]
            results = await self._search_entity_type(entity_type, config, query, params)
            all_results.extend(results)
            if results:
                entity_type_counts[entity_type] = len(results)

        # Build facets
        for et, count in entity_type_counts.items():
            facets["entity_type"].append({"value": et, "count": count})

        facet_dynasties: dict[str, int] = {}
        for r in all_results:
            dyn = r.metadata.get("dynasty") or r.metadata.get("era")
            if dyn:
                facet_dynasties[dyn] = facet_dynasties.get(dyn, 0) + 1
        facets["dynasty"] = [
            {"value": d, "count": c}
            for d, c in sorted(facet_dynasties.items(), key=lambda x: -x[1])[:10]
        ]

        # Sort by score descending
        all_results.sort(key=lambda r: r.score, reverse=True)

        # Paginate
        total = len(all_results)
        total_pages = max(1, math.ceil(total / params.limit))
        start = (params.page - 1) * params.limit
        end = start + params.limit
        page_items = all_results[start:end]

        return SearchResponse(
            items=page_items,
            total=total,
            page=params.page,
            limit=params.limit,
            total_pages=total_pages,
            query=query,
            entity_types=params.entity_types,
            facets=facets,
        )

    async def _search_entity_type(
        self,
        entity_type: str,
        config: dict[str, Any],
        query: str,
        params: SearchParams,
    ) -> list[SearchResultItem]:
        """Search one entity type and return scored, snippet-wrapped results."""
        model = config["model"]
        title_field = config["title_field"]
        subtitle_field = config["subtitle_field"]
        search_fields: list[str] = config["search_fields"]
        snippet_field: str | None = config.get("snippet_field")
        meta_fields: list[str] = config.get("meta_fields", [])
        route_prefix: str | None = config.get("route_prefix")

        # Build ILIKE conditions
        conditions = []
        getattr(model, title_field, None)

        for field_name in search_fields:
            col = getattr(model, field_name, None)
            if col is not None:
                conditions.append(col.ilike(f"%{query}%"))

        if not conditions:
            return []

        # Build query
        stmt = select(model).where(
            or_(*conditions),
            model.is_deleted.is_(False),
        )

        # Apply filters
        if params.dynasty:
            dynasty_col = getattr(model, "dynasty", None) or getattr(model, "era", None)
            if dynasty_col is not None:
                stmt = stmt.where(dynasty_col == params.dynasty)

        if params.category and entity_type == "book":
            cat_col = getattr(model, "category", None)
            if cat_col is not None:
                stmt = stmt.where(cat_col == params.category)

        stmt = stmt.limit(50)  # per-type cap before global sort

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        items: list[SearchResultItem] = []
        q_lower = query.lower()

        for obj in rows:
            # Build title
            title_val = getattr(obj, title_field, "")
            if entity_type == "passage":
                title_val = str(title_val)[:60] + ("…" if len(str(title_val)) > 60 else "")

            # Build snippet
            snippet = None
            if snippet_field:
                snippet_val = getattr(obj, snippet_field, None)
                snippet = _make_snippet(str(snippet_val) if snippet_val else None, query)

            # Build subtitle
            subtitle = None
            if subtitle_field:
                subtitle = str(getattr(obj, subtitle_field, "") or "") or None

            # Build metadata
            metadata: dict[str, Any] = {}
            for mf in meta_fields:
                val = getattr(obj, mf, None)
                if val is not None and val != "":
                    metadata[mf] = str(val) if not isinstance(val, (int, float)) else val
            if entity_type == "passage":
                version = getattr(obj, "version", None)
                chapter = getattr(obj, "chapter", None)
                if version is not None:
                    metadata.update(
                        {
                            "version_name": version.version_name,
                            "repository": version.repository,
                            "shelf_mark": version.shelf_mark,
                            "source_url": version.source_url,
                        }
                    )
                if chapter is not None:
                    metadata["chapter_title"] = chapter.title

            # Build URL
            url = None
            if route_prefix:
                url = f"{route_prefix}/{obj.id}"

            # Compute score
            match_count = 0
            title_match = False
            for field_name in search_fields:
                col_val = str(getattr(obj, field_name, "") or "").lower()
                if q_lower in col_val:
                    match_count += 1
                    if field_name in (title_field,) or field_name in ("name", "title"):
                        title_match = True

            score = _compute_score(match_count, len(search_fields), title_match)

            items.append(
                SearchResultItem(
                    id=obj.id,
                    entity_type=entity_type,
                    title=str(title_val),
                    subtitle=subtitle,
                    snippet=snippet,
                    url=url,
                    metadata=metadata,
                    score=score,
                )
            )

        return items

    # ------------------------------------------------------------------
    # Autocomplete / Suggest
    # ------------------------------------------------------------------

    async def suggest(self, q: str, limit: int = 5) -> list[SuggestItem]:
        """Return autocomplete suggestions across entity types."""
        if not q.strip():
            return []

        suggestions: list[SuggestItem] = []
        q_norm = q.strip()

        # Priority order: person names, book titles, then everything else
        priority_types = ["person", "book", "version", "passage"]

        for entity_type in priority_types:
            if len(suggestions) >= limit:
                break
            config = ENTITY_CONFIG.get(entity_type)
            if not config:
                continue

            model = config["model"]
            title_field = config["title_field"]
            title_col = getattr(model, title_field, None)
            if title_col is None:
                continue

            stmt = (
                select(model.id, title_col)
                .where(
                    title_col.ilike(f"{q_norm}%"),
                    model.is_deleted.is_(False),
                )
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            for row in result:
                if len(suggestions) >= limit:
                    break
                text = row[1]
                if entity_type == "passage":
                    text = str(text)[:50]
                suggestions.append(
                    SuggestItem(
                        text=str(text),
                        entity_type=entity_type,
                        entity_id=row[0],
                    )
                )

        return suggestions[:limit]

    # ------------------------------------------------------------------
    # Reindex (placeholder — MVP uses on-the-fly queries)
    # ------------------------------------------------------------------

    async def reindex(self) -> dict[str, Any]:
        """Reindex all searchable entities.

        In the MVP, 'reindex' triggers a check that all searchable models
        are queryable. When ES/pgvector are wired, this will rebuild indices.
        """
        total = 0
        for entity_type, config in ENTITY_CONFIG.items():
            model = config["model"]
            stmt = select(func.count()).select_from(
                select(model.id).where(model.is_deleted.is_(False)).subquery()
            )
            result = await self.session.execute(stmt)
            count = result.scalar_one()
            total += count

        return {
            "status": "completed",
            "entities_indexed": total,
            "errors": [],
        }
