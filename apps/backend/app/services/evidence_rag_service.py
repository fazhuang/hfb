"""
Evidence-bound RAG Service — rag_enabled filter, full provenance binding, no fabrication.

Every retrieved chunk is bound to:
  document_id, source_url, page_number, paragraph_index,
  copyright_status, citation_format, ocr_confidence

Hard rules:
  - Only reads rag_enabled=true documents
  - Merges Document.copyright_status / source_url / source_name onto every chunk
  - OCR confidence < 0.7 → evidence_weight="reference" (never "primary")
  - No evidence → refusal, never fabrication
"""
from __future__ import annotations

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.evidence_rag import (
    EvidenceBoundChunk,
    EvidenceCitation,
    EvidenceRAGResponse,
)


# Threshold below which OCR content is only advisory
OCR_PRIMARY_THRESHOLD = 0.7


class EvidenceRAGService:
    """Evidence-bound retrieval — rag_enabled gating + full provenance."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def query(self, q: str, top_k: int = 5) -> EvidenceRAGResponse:
        """Answer a natural-language question with evidence-bound results.

        Hard-gated: only rag_enabled=true documents are searched.
        No evidence → refusal.
        """
        keywords = self._tokenize(q)
        if not keywords:
            return EvidenceRAGResponse(
                query=q, refusal=True,
                refusal_reason="查询词无效，无法检索",
            )

        # Fetch evidence-bound chunks
        all_chunks = await self._retrieve_evidence_chunks(keywords)
        if not all_chunks:
            return EvidenceRAGResponse(
                query=q, refusal=True,
                refusal_reason="在已启用 RAG 的文档中未找到相关内容",
            )

        # Score and rank
        scored = []
        for chunk in all_chunks:
            score = self._score(keywords, chunk.content)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda x: -x[0])
        scored = scored[:top_k]

        if not scored:
            return EvidenceRAGResponse(
                query=q, refusal=True,
                refusal_reason="未找到匹配的相关证据",
            )

        # Build response
        raw_evidence = []
        for s, c in scored:
            raw_evidence.append((s, await self._to_evidence_chunk(c, s)))
        evidence = [e for _, e in raw_evidence]
        citations = [self._to_citation(c) for c in evidence]
        answer = self._render_answer(q, evidence, citations)

        return EvidenceRAGResponse(
            query=q,
            answer=answer,
            refusal=False,
            citations=citations,
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Retrieval — rag_enabled gate + document join
    # ------------------------------------------------------------------

    async def _retrieve_evidence_chunks(
        self, keywords: list[str]
    ) -> list[DocumentChunk]:
        """Retrieve chunks ONLY from rag_enabled=true, non-deleted documents."""
        kw_filters = [
            DocumentChunk.content.ilike(f"%{kw}%") for kw in keywords
        ]

        stmt = (
            select(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.is_deleted.is_(False),
                Document.is_deleted.is_(False),
                Document.rag_enabled.is_(True),
                or_(*kw_filters),
            )
            .limit(200)  # ponytail: reasonable upper bound, tune if real-world needs more
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Evidence binding — chunk → document fields
    # ------------------------------------------------------------------

    async def _to_evidence_chunk(
        self, chunk: DocumentChunk, score: float
    ) -> EvidenceBoundChunk:
        """Bind chunk to its Document's compliance metadata.

        Fetches Document in a batch to avoid N+1 (caller batches).
        """
        # Document loaded via relationship (selectin), or fetch eagerly
        doc = chunk.document
        if doc is None:
            # Fallback: explicit fetch
            doc_stmt = select(Document).where(Document.id == chunk.document_id)
            result = await self.session.execute(doc_stmt)
            doc = result.scalar_one_or_none()

        title = getattr(doc, "title", "") if doc else ""
        source_url = getattr(doc, "source_url", "") or ""
        copyright_status = getattr(doc, "copyright_status", "unknown") if doc else "unknown"

        # Determine evidence weight: OCR confidence < 0.7 → reference only
        ocr = chunk.ocr_confidence
        evidence_weight = chunk.evidence_weight or "primary"
        if ocr is not None and ocr < OCR_PRIMARY_THRESHOLD:
            evidence_weight = "reference"

        # Build citation string
        citation = self._build_citation(title, chunk, source_url)

        return EvidenceBoundChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=title,
            source_url=source_url,
            page_number=chunk.page_number,
            paragraph_index=chunk.paragraph_index,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            score=score,
            copyright_status=copyright_status,
            citation_format=chunk.citation_format,
            evidence_weight=evidence_weight,
            ocr_confidence=ocr,
            citation=citation,
        )

    # ------------------------------------------------------------------
    # Citation builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_citation(title: str, chunk: DocumentChunk, source_url: str) -> str:
        """Build an evidence citation string.

        Format: 《title》[doc_id:chunk_id] p.{page} par.{paragraph} — {source_url}
        Omit missing fields gracefully.
        """
        parts = [f"《{title}》"] if title else []
        parts.append(f"[{chunk.document_id}:{chunk.id}]")

        locs = []
        if chunk.page_number is not None:
            locs.append(f"p.{chunk.page_number}")
        if chunk.paragraph_index is not None:
            locs.append(f"par.{chunk.paragraph_index}")
        if locs:
            parts.append(" " + ", ".join(locs))

        if chunk.ocr_confidence is not None:
            parts.append(f" OCR:{chunk.ocr_confidence:.2f}")

        return "".join(parts)

    @staticmethod
    def _to_citation(chunk: EvidenceBoundChunk) -> EvidenceCitation:
        """Convert evidence chunk to standalone citation."""
        return EvidenceCitation(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            citation=chunk.citation,
            source_url=chunk.source_url,
            quote=chunk.content[:200],
            copyright_status=chunk.copyright_status,
            evidence_weight=chunk.evidence_weight,
            ocr_confidence=chunk.ocr_confidence,
        )

    # ------------------------------------------------------------------
    # Answer rendering — deterministic, evidence-only
    # ------------------------------------------------------------------

    @staticmethod
    def _render_answer(
        query: str,
        evidence: list[EvidenceBoundChunk],
        citations: list[EvidenceCitation],
    ) -> str:
        """Render a deterministic answer from evidence only.

        No LLM — just structured evidence report.
        """
        primary = [e for e in evidence if e.evidence_weight == "primary"]
        reference = [e for e in evidence if e.evidence_weight == "reference"]

        parts = [f"关于「{query}」，共检索到 {len(evidence)} 条证据。"]
        parts.append("")

        if primary:
            parts.append(f"主要证据（{len(primary)} 条）：")
            for i, e in enumerate(primary, 1):
                parts.append(f"  [{i}] {e.citation}")
                parts.append(f"      {e.content[:150]}...")
            parts.append("")

        if reference:
            parts.append(f"参考证据（{len(reference)} 条，OCR 低可信度，不能作为强证据）：")
            for i, e in enumerate(reference, 1):
                parts.append(f"  [R{i}] {e.citation}")
                parts.append(f"       {e.content[:150]}...")
            parts.append("")

        parts.append(f"引用来源（{len(citations)} 条）：")
        for i, c in enumerate(citations, 1):
            weight_tag = "[参考]" if c.evidence_weight == "reference" else "[主要]"
            parts.append(f"  {weight_tag} {c.citation}")
            if c.source_url:
                parts.append(f"       URL: {c.source_url}")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Tokenization
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(query: str) -> list[str]:
        """Split query on whitespace into non-empty, deduplicated keywords."""
        return list(dict.fromkeys(
            kw for kw in query.strip().split() if kw
        ))

    # ------------------------------------------------------------------
    # Scoring — same deterministic formula as RetrievalService
    # ------------------------------------------------------------------

    @staticmethod
    def _score(keywords: list[str], content: str) -> float:
        """Multi-keyword scoring — hit ratio + coverage + frequency."""
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
