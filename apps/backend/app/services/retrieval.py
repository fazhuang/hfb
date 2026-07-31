"""
Chunk-level retrieval with citation binding.

Uses SQL ILIKE for text matching with multi-keyword tokenization.
Every result carries a citation in the format [document_id:chunk_id],
traceable back to the source document and individual chunk.

Compliance: strict_compliance=True enforces copyright_status allowlist
(public_domain, open_access, licensed, user_uploaded_with_permission)
and requires rag_enabled=True. Forbidden statuses (commercial_restricted,
metadata_only, forbidden_fulltext, pirated, unknown) are excluded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)

# Copyright statuses allowed for retrieval when strict_compliance=True
_COMPLIANT_COPYRIGHT_STATUSES = frozenset(
    {
        "public_domain",
        "open_access",
        "licensed",
        "user_uploaded_with_permission",
    }
)


def _compliance_clauses(
    *,
    rag_col,
    status_col,
    auth_col,
    license_col,
    withdrawn_col,
) -> list:
    """Return SQL WHERE clauses for the full compliance predicate.

    Used by both RetrievalService (strict_compliance) and
    EvidenceRAGService (_retrieve_evidence_chunks).

    Predicate (AND):
      1. rag_enabled is True
      2. copyright_status in compliant set
      3. (authorization_basis non-empty) OR (license_type non-empty)
      4. withdrawn_at IS NULL — guards against rows soft-deleted via withdrawal
         that still have is_deleted=False / rag_enabled=True
    """


# Simplified → traditional character variants for matching classical woodblock OCR.
# The 1601 NLC scan uses traditional/variant characters (鐵/鍼 for 针, 經 for 经).
# Without variant expansion, keyword-based retrieval returns zero candidates for
# simplified-Chinese queries and the RAG pipeline refuses to answer.
_SIMPLIFIED_TO_TRAD = {
    "针": ["針", "鍼", "鐵"],
    "经": ["經"],
    "络": ["絡"],
    "黄": ["黃"],
    "书": ["書"],
    "论": ["論"],
    "脉": ["脈", "脲"],
    "气": ["氣"],
    "脏": ["臟", "藏"],
    "腑": ["府"],
    "体": ["體"],
    "证": ["證"],
    "阴": ["陰"],
    "阳": ["陽"],
    "编": ["編"],
    "辑": ["輯"],
    "学": ["學"],
    "医": ["醫"],
    "国": ["國"],
    "门": ["門"],
    "问": ["問"],
    "为": ["為"],
    "时": ["時"],
    "会": ["會"],
    "义": ["義"],
    "头": ["頭"],
    "实": ["實"],
    "万": ["萬"],
    "与": ["與"],
    "号": ["號"],
    "无": ["無"],
    "条": ["條"],
}


def _expand_variants(keywords: list[str]) -> list[str]:
    """Add traditional variant forms of keywords for matching classical OCR text."""
    expanded: list[str] = list(keywords)
    for kw in keywords:
        variants = [""]
        for ch in kw:
            new_variants = []
            for base in variants:
                for vch in _SIMPLIFIED_TO_TRAD.get(ch, [ch]):
                    new_variants.append(base + vch)
            variants = new_variants
        for v in variants:
            if v != kw and v not in expanded:
                expanded.append(v)
    return expanded


def _compliance_clauses(
    *,
    rag_col,
    status_col,
    auth_col,
    license_col,
    withdrawn_col,
) -> list:
    """Return SQL WHERE clauses for the full compliance predicate.

    Used by both RetrievalService (strict_compliance) and
    EvidenceRAGService (_retrieve_evidence_chunks).

    Predicate (AND):
      1. rag_enabled is True
      2. copyright_status in compliant set
      3. (authorization_basis non-empty) OR (license_type non-empty)
      4. withdrawn_at IS NULL — guards against rows soft-deleted via withdrawal
         that still have is_deleted=False / rag_enabled=True

    P2T1: The compliance filter is applied to the Document model's columns.
    Version-level withdrawal is checked separately during trace lineage
    resolution (build_internal_traces validates version withdrawal).
    """
    return [
        rag_col.is_(True),
        status_col.in_(_COMPLIANT_COPYRIGHT_STATUSES),
        or_(
            auth_col.isnot(None) & (auth_col != ""),
            license_col.isnot(None) & (license_col != ""),
        ),
        withdrawn_col.is_(None),
    ]


@dataclass
class RetrievalResult:
    """A single retrieval result with citation metadata."""

    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    content: str
    citation: str  # format: [document_id:chunk_id]
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Response from the chunk search endpoint."""

    query: str
    results: list[RetrievalResult]
    total: int
    max_score: float


class RetrievalService:
    """Retrieve document chunks by keyword search with citation binding.

    Every result carries a citation string that links back to the
    source document and chunk — traceable and verifiable.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        top_k: int = 10,
        document_id: str | None = None,
        year: int | None = None,
        author_id: str | None = None,
        strict_compliance: bool = False,
    ) -> SearchResponse:
        """Search document chunks by keywords (ILIKE per tokenized keyword).

        Tokenizes the query on whitespace to get individual keywords,
        matches chunks containing any keyword, then scores by hit count,
        coverage ratio, and keyword frequency.

        Filters:
          - document_id: restrict to a single document
          - year: restrict to documents from a specific year
          - author_id: restrict to documents authored by a specific person

        When strict_compliance=True (RAG/generation path):
          - Only rag_enabled=True documents
          - Only compliant copyright_status values
          - Enhanced provenance metadata

        Stable sort: score descending, then document_id, then chunk_index.
        """
        keywords = self._tokenize(query)
        if not keywords:
            return SearchResponse(query=query, results=[], total=0, max_score=0.0)

        # Fetch candidate chunks: ILIKE any keyword
        # Context 21: filter BOTH DocumentChunk.is_deleted AND Document.is_deleted
        # Context 22: optional strict_compliance adds rag_enabled + copyright gate
        stmt = (
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.is_deleted.is_(False),
                Document.is_deleted.is_(False),
            )
        )
        if strict_compliance:
            stmt = stmt.where(
                *_compliance_clauses(
                    rag_col=Document.rag_enabled,
                    status_col=Document.copyright_status,
                    auth_col=Document.authorization_basis,
                    license_col=Document.license_type,
                    withdrawn_col=Document.withdrawn_at,
                )
            )
            # Page-level evidence quality gate: PDF-backed documents MUST
            # have a verified page_number on the chunk. Non-PDF documents
            # (ctext, etc.) pass through freely (raw_pdf_blob IS NULL).
            stmt = stmt.where(
                or_(
                    Document.raw_pdf_blob.is_(None),
                    DocumentChunk.page_number.isnot(None),
                )
            )
            logger.debug(
                "strict_compliance filter active: PDF chunks require page_number IS NOT NULL"
            )
        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        if year is not None:
            stmt = stmt.where(Document.year == year)
        if author_id is not None:
            stmt = stmt.where(Document.author_id == author_id)

        # Build OR of keyword ILIKE conditions
        keyword_filters = [DocumentChunk.content.ilike(f"%{kw}%") for kw in keywords]
        stmt = stmt.where(or_(*keyword_filters))

        # Fetch ALL candidate chunks matching any keyword
        result = await self.session.execute(stmt)
        all_chunks = result.scalars().all()

        # Collect document titles and compliance data in one query to avoid N+1
        doc_ids = list({c.document_id for c in all_chunks})
        doc_titles: dict[str, str] = {}
        doc_compliance: dict[str, dict[str, Any]] = {}
        if doc_ids:
            doc_result = await self.session.execute(
                select(
                    Document.id,
                    Document.title,
                    Document.source_url,
                    Document.copyright_status,
                    Document.rag_enabled,
                ).where(Document.id.in_(doc_ids))
            )
            for row in doc_result:
                doc_titles[row[0]] = row[1]
                doc_compliance[row[0]] = {
                    "source_url": row[2] or "",
                    "copyright_status": row[3] or "unknown",
                    "rag_enabled": bool(row[4]),
                }

        # Build results with citation
        items: list[RetrievalResult] = []
        for chunk in all_chunks:
            title = doc_titles.get(chunk.document_id, "Unknown")
            score = self._score_chunk(keywords, chunk.content)
            # Citation format: [document_id:chunk_id]
            citation = f"[{chunk.document_id}:{chunk.id}]"

            compliance = doc_compliance.get(chunk.document_id, {})
            metadata: dict[str, Any] = {
                "token_count": chunk.token_count or 0,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "retrieval_method": "ili_keyword_search",
            }
            # Provenance fields for compliance / generation
            if chunk.page_number is not None:
                metadata["page_number"] = chunk.page_number
            if chunk.paragraph_index is not None:
                metadata["paragraph_index"] = chunk.paragraph_index
            metadata["source_url"] = compliance.get("source_url", "")
            metadata["copyright_status"] = compliance.get("copyright_status", "unknown")
            if chunk.evidence_weight:
                metadata["evidence_weight"] = chunk.evidence_weight
            if chunk.ocr_confidence is not None:
                metadata["ocr_confidence"] = chunk.ocr_confidence

            items.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=title,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    citation=citation,
                    score=score,
                    metadata=metadata,
                )
            )

        # Stable sort: score desc, document_id asc, chunk_index asc, chunk_id asc
        items.sort(key=lambda r: (-r.score, r.document_id, r.chunk_index, r.chunk_id))
        items = items[:top_k]

        max_score = max((r.score for r in items), default=0.0)

        return SearchResponse(
            query=query,
            results=items,
            total=len(items),
            max_score=max_score,
        )

    # ------------------------------------------------------------------
    # Tokenization
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(query: str) -> list[str]:
        """Split query into searchable keywords with variant expansion.

        Uses a local fallback bigram/trigram tokenizer for Chinese text so
        that natural-language questions actually hit document chunk content.
        White-space split queries (already tokenized by the caller) pass
        through unchanged.

        Applies simplified→traditional variant expansion so that OCR text
        with 鐵/鍼/經/etc matches simplified-Chinese queries.
        """
        import re

        # If query already contains spaces (pre-tokenized), split on whitespace
        if " " in query.strip():
            terms = list(
                dict.fromkeys(kw for kw in query.strip().split() if kw and len(kw) >= 2)
            )
            # P2T1: Apply variant expansion even for pre-tokenized queries.
            # build_academic_retrieval_query inserts spaces between keyword
            # segments, which would otherwise bypass simplified→traditional
            # expansion and cause ILIKE misses on classical OCR text.
            return _expand_variants(terms)
        else:
            # Strip question markers
            clean = re.sub(
                r"(是否|能否|是不是|有没有|可不|是什么|什么是|如何|怎么|怎样|为何|为什么|是谁)",
                " ",
                query,
            )
            clean = re.sub(r"\s+", " ", clean).strip()

            # Segment Chinese text: keep only Chinese chars, build bigrams+trigrams
            chinese = re.findall(r"[一-鿿]", clean)
            terms = []
            for i in range(len(chinese) - 1):
                terms.append("".join(chinese[i : i + 2]))
            for i in range(len(chinese) - 2):
                terms.append("".join(chinese[i : i + 3]))
            terms = list(dict.fromkeys(terms))

            if not terms:
                return list(dict.fromkeys(kw for kw in clean.split() if kw))

        return _expand_variants(terms)

    # ------------------------------------------------------------------
    # Scoring — multi-keyword, deterministic, stable
    # ------------------------------------------------------------------

    @staticmethod
    def _score_chunk(keywords: list[str], content: str) -> float:
        """Score a chunk by keyword hit count + coverage + frequency.

        Deterministic formula:
          - hit_ratio: fraction of keywords that appear in content (0-1, weight 0.5)
          - coverage: total keyword occurrences / content length (weight 0.3)
          - frequency: total keyword occurrences normalized (weight 0.2)

        Returns a float 0.0–1.0, rounded to 3 decimal places.
        """
        if not content:
            return 0.0

        c_lower = content.lower()
        content_len = len(c_lower)
        hits = 0
        total_occurrences = 0

        for kw in keywords:
            kw_lower = kw.lower()
            count = c_lower.count(kw_lower)
            if count > 0:
                hits += 1
                total_occurrences += count

        if hits == 0:
            return 0.0

        hit_ratio = hits / len(keywords)
        coverage = min(total_occurrences / max(content_len, 1), 1.0)
        frequency = min(total_occurrences / max(content_len / 100, 1), 1.0)

        score = 0.5 * hit_ratio + 0.3 * coverage + 0.2 * frequency
        return round(min(score, 1.0), 3)
