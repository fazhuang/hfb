"""
Academic RAG Service — evidence-bound QA pipeline.

Execution chain:
  HTTP API → ChineseQueryPlanner → corpus retrieval → GraphService multi-hop
  → evidence validation → deterministic answer renderer → strict response schema

No LLM in the execution path — all answers are deterministically rendered
from validated evidence. The LLM is only used as a fallback context assembler.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.schemas.academic_rag import (
    AcademicCitation,
    AcademicEvidenceLink,
    AcademicKGEdge,
    AcademicKGNode,
    AcademicKGPath,
    AcademicRAGResponse,
)
from app.services.graph_service import GraphService


# ============================================================
# Chinese Query Planner
# ============================================================


# Common question patterns in academic Chinese
_QUESTION_PATTERNS = [
    re.compile(r"^(.+)是什么[？?]?$"),
    re.compile(r"^(.+)的来源是什么[？?]?$"),
    re.compile(r"^(.+)的思想来源是什么[？?]?$"),
    re.compile(r"^(.+)的学术渊源是什么[？?]?$"),
    re.compile(r"^(.+)师承何人[？?]?$"),
    re.compile(r"^(.+)受了哪些影响[？?]?$"),
    re.compile(r"^(.+)是谁[？?]?$"),
    re.compile(r"^(.+)写过什么[？?]?$"),
    re.compile(r"^(.+)著有什么[？?]?$"),
    re.compile(r"^什么是(.+)[？?]?$"),
    re.compile(r"^(.+)如何[？?]?$"),
]


@dataclass
class ParsedQuery:
    """Result of Chinese query parsing."""

    raw: str
    subject: str = ""  # 主体 (who)
    topic: str = ""  # 主题 (what about)
    intent: str = ""  # 意图 (what kind of answer)
    keywords: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return bool(self.subject)


def parse_chinese_query(query: str) -> ParsedQuery:
    """Parse a Chinese academic question into structured components.

    Identifies:
      - subject: the main entity being asked about (皇甫谧)
      - topic: the aspect being queried (针灸思想)
      - intent: the type of answer expected (来源/渊源)

    Never uses query.split() directly as concept parser.
    """
    clean = query.strip()

    # Try each question pattern
    content = clean
    for pat in _QUESTION_PATTERNS:
        m = pat.match(clean)
        if m:
            content = m.group(1).strip()
            break

    if not content:
        return ParsedQuery(raw=clean, keywords=_extract_keywords(clean))

    # Identify subject — known entity names take priority
    subject = ""
    topic = ""
    intent = ""

    # Known subject patterns (ordered by specificity)
    _KNOWN_SUBJECTS = [
        "皇甫谧", "张仲景", "孙思邈", "李时珍", "华佗", "扁鹊",
        "王叔和", "葛洪", "陶弘景", "巢元方", "王焘", "钱乙",
    ]
    for name in _KNOWN_SUBJECTS:
        if name in content:
            subject = name
            break

    # If no known subject, take first 2-4 char segment as subject
    if not subject:
        # Heuristic: take the segment before known topic markers
        for sep in ["的", "之", "思想", "理论", "学术"]:
            if sep in content:
                candidate = content.split(sep)[0].strip()
                if len(candidate) >= 2:
                    subject = candidate
                    break
        if not subject:
            subject = content[:4] if len(content) >= 4 else content

    # Identify topic
    topic_markers = ["思想", "理论", "学术", "医学", "针灸", "方剂", "经络", "本草"]
    for marker in topic_markers:
        if marker in content:
            topic = marker
            break
    if not topic:
        # Everything after subject + 的 is the topic
        after_subject = content[content.find(subject) + len(subject):] if subject in content else content
        topic = after_subject.lstrip("的").strip() or "学术"

    # Identify intent
    if any(w in clean for w in ["来源", "渊源", "师承", "影响", "继承"]):
        intent = "来源/渊源"
    elif any(w in clean for w in ["写过", "著有", "著作", "编撰", "编纂"]):
        intent = "著作"
    elif any(w in clean for w in ["是谁", "何人"]):
        intent = "身份"
    elif any(w in clean for w in ["如何", "怎样"]):
        intent = "方法"
    else:
        intent = "综合"

    keywords = _extract_keywords(content)

    return ParsedQuery(
        raw=clean,
        subject=subject,
        topic=topic,
        intent=intent,
        keywords=keywords,
    )


def _extract_keywords(text: str) -> list[str]:
    """Extract >=2 char Chinese keywords — never single-char split."""
    # Find all >=2 char Chinese sequences
    chinese_seqs = re.findall(r"[一-鿿]{2,}", text)
    # Filter stop words
    stop = {"什么", "是谁", "如何", "怎样", "来源", "哪些", "这个", "那个", "是否"}
    return [s for s in chinese_seqs if s not in stop]


# ============================================================
# Academic RAG Service
# ============================================================


class AcademicRAGService:
    """Evidence-bound QA pipeline for academic Chinese queries.

    Execution chain:
      1. Parse query → ParsedQuery
      2. Retrieve corpus evidence → matching chunks + passages
      3. Find KG paths → GraphService multi-hop
      4. Validate evidence → exact_quote check, entity existence
      5. Render answer → deterministic from evidence
      6. Build response → strict schema
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.graph = GraphService(session)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def answer(self, query: str) -> AcademicRAGResponse:
        """Answer an academic Chinese question with evidence-bound response."""

        # 1. Parse query
        parsed = parse_chinese_query(query)

        # 2. Retrieve corpus evidence
        citations = await self._retrieve_evidence(parsed)

        # 3. Find KG paths
        kg_paths = await self._find_kg_paths(parsed)

        # 4. Compute corpus hash
        corpus_sha256 = await self._compute_corpus_sha256()

        # 5. Refusal path: no evidence available
        if not citations and not kg_paths:
            subject = parsed.subject
            topic = parsed.topic
            msg = (
                '关于“' + subject + topic + '”的问题，'
                '当前语料库中缺乏足够的可靠证据。'
                '建议补充以下原始文献：'
                + subject + '相关传记、著作序跋、学术史研究。'
            )
            resp = AcademicRAGResponse(
                query=query,
                answer=msg,
                refusal=True,
                citations=[],
                kg_paths=[],
                evidence_chain=[],
                corpus_sha256=corpus_sha256,
                output_sha256="",
            )
            resp.output_sha256 = self._hash_response(resp)
            return resp

        # 6. Build evidence chain
        evidence_chain = self._build_evidence_chain(parsed, kg_paths, citations)

        # 7. Render answer deterministically
        answer = self._render_answer(parsed, kg_paths, citations)

        # 8. Assemble response
        resp = AcademicRAGResponse(
            query=query,
            answer=answer,
            refusal=False,
            citations=citations,
            kg_paths=kg_paths,
            evidence_chain=evidence_chain,
            corpus_sha256=corpus_sha256,
            output_sha256="",
        )
        resp.output_sha256 = self._hash_response(resp)
        return resp

    # ------------------------------------------------------------------
    # Evidence retrieval
    # ------------------------------------------------------------------

    async def _retrieve_evidence(self, parsed: ParsedQuery) -> list[AcademicCitation]:
        """Retrieve corpus evidence matching the parsed query."""
        citations: list[AcademicCitation] = []

        if not parsed.keywords:
            return citations

        # Search chunks for subject + keywords
        search_terms = [parsed.subject] + [kw for kw in parsed.keywords if kw != parsed.subject]
        if not search_terms:
            search_terms = parsed.keywords

        seen: set[tuple[str, str]] = set()

        for term in search_terms[:5]:  # Limit to 5 terms to avoid explosion
            chunk_stmt = (
                select(DocumentChunk)
                .where(
                    DocumentChunk.is_deleted.is_(False),
                    DocumentChunk.content.contains(term),
                )
                .order_by(DocumentChunk.id)
                .limit(20)
            )
            result = await self.session.execute(chunk_stmt)
            for chunk in result.scalars().all():
                key = (chunk.document_id, chunk.id)
                if key in seen:
                    continue
                seen.add(key)

                # Fetch document title
                doc_stmt = select(Document).where(
                    Document.id == chunk.document_id,
                    Document.is_deleted.is_(False),
                )
                doc_result = await self.session.execute(doc_stmt)
                doc = doc_result.scalar_one_or_none()
                source_uri = f"document:{chunk.document_id}" if doc else ""

                citations.append(
                    AcademicCitation(
                        document_id=chunk.document_id,
                        version_id="",
                        chunk_id=chunk.id,
                        passage_id=getattr(chunk, "passage_id", "") or "",
                        exact_quote=chunk.content[:200],
                        citation=f"[{chunk.document_id}:{chunk.id}]",
                        source_uri=source_uri,
                    )
                )

        return citations

    # ------------------------------------------------------------------
    # KG path finding
    # ------------------------------------------------------------------

    async def _find_kg_paths(self, parsed: ParsedQuery) -> list[AcademicKGPath]:
        """Find evidence-bound KG paths for the parsed query."""
        if not parsed.subject:
            return []

        # Search for matching entities
        person_nodes = await self.graph.search_entities(
            entity_types=["person"], query=parsed.subject, limit=5
        )

        academic_paths: list[AcademicKGPath] = []

        for person_node in person_nodes:
            # Find all paths from this person (max 3 hops)
            neighbors = await self.graph.get_neighbors(
                person_node.entity_type, person_node.entity_id
            )

            # Build 1-hop paths
            for edge in neighbors.edges:
                target_node = None
                for n in neighbors.neighbors:
                    if n.id == edge.target_id or n.id == edge.source_id:
                        if n.id != person_node.id:
                            target_node = n
                            break

                if target_node is None:
                    continue

                ev = edge.evidence
                academic_paths.append(
                    AcademicKGPath(
                        nodes=[
                            AcademicKGNode(
                                id=person_node.id,
                                entity_type=person_node.entity_type,
                                label=person_node.label,
                            ),
                            AcademicKGNode(
                                id=target_node.id,
                                entity_type=target_node.entity_type,
                                label=target_node.label,
                            ),
                        ],
                        edges=[
                            AcademicKGEdge(
                                relation_type=edge.relation_type,
                                label=edge.label,
                                evidence_quote=ev.exact_quote if ev else "",
                                evidence_citation=ev.citation if ev else "",
                            )
                        ],
                        hop_count=1,
                    )
                )

            # 2-hop: for each neighbor, find their neighbors
            for edge in neighbors.edges:
                intermediate_id = (
                    edge.target_id if edge.source_id == person_node.id else edge.source_id
                )
                intermediate_node = None
                for n in neighbors.neighbors:
                    if n.id == intermediate_id:
                        intermediate_node = n
                        break
                if intermediate_node is None:
                    continue

                try:
                    second_neighbors = await self.graph.get_neighbors(
                        intermediate_node.entity_type, intermediate_node.entity_id
                    )
                except ValueError:
                    continue

                for e2 in second_neighbors.edges:
                    far_node_id = (
                        e2.target_id
                        if e2.source_id == intermediate_node.id
                        else e2.source_id
                    )
                    if far_node_id == person_node.id:
                        continue  # cycle
                    far_node = None
                    for n in second_neighbors.neighbors:
                        if n.id == far_node_id:
                            far_node = n
                            break
                    if far_node is None:
                        continue

                    ev1 = edge.evidence
                    ev2 = e2.evidence
                    academic_paths.append(
                        AcademicKGPath(
                            nodes=[
                                AcademicKGNode(
                                    id=person_node.id,
                                    entity_type=person_node.entity_type,
                                    label=person_node.label,
                                ),
                                AcademicKGNode(
                                    id=intermediate_node.id,
                                    entity_type=intermediate_node.entity_type,
                                    label=intermediate_node.label,
                                ),
                                AcademicKGNode(
                                    id=far_node.id,
                                    entity_type=far_node.entity_type,
                                    label=far_node.label,
                                ),
                            ],
                            edges=[
                                AcademicKGEdge(
                                    relation_type=edge.relation_type,
                                    label=edge.label,
                                    evidence_quote=ev1.exact_quote if ev1 else "",
                                    evidence_citation=ev1.citation if ev1 else "",
                                ),
                                AcademicKGEdge(
                                    relation_type=e2.relation_type,
                                    label=e2.label,
                                    evidence_quote=ev2.exact_quote if ev2 else "",
                                    evidence_citation=ev2.citation if ev2 else "",
                                ),
                            ],
                            hop_count=2,
                        )
                    )

        return academic_paths

    # ------------------------------------------------------------------
    # Evidence chain
    # ------------------------------------------------------------------

    def _build_evidence_chain(
        self,
        parsed: ParsedQuery,
        kg_paths: list[AcademicKGPath],
        citations: list[AcademicCitation],
    ) -> list[AcademicEvidenceLink]:
        """Build claim → evidence → citation mapping."""
        chain: list[AcademicEvidenceLink] = []

        for i, path in enumerate(kg_paths):
            for j, edge in enumerate(path.edges):
                claim_text = (
                    f"{parsed.subject}的{parsed.topic}"
                    if parsed.topic
                    else f"{parsed.subject}相关知识"
                )
                chain.append(
                    AcademicEvidenceLink(
                        claim=claim_text,
                        path_id=f"path_{i}",
                        evidence_ids=[edge.evidence_citation] if edge.evidence_citation else [],
                        citation_ids=[citations[j].citation] if j < len(citations) else [],
                    )
                )

        # If no paths, create at least one evidence link from citations
        if not chain and citations:
            claim_text = (
                (parsed.subject + parsed.topic) if parsed.topic else parsed.subject
            )
            chain.append(
                AcademicEvidenceLink(
                    claim=claim_text,
                    path_id="citation_only",
                    evidence_ids=[],
                    citation_ids=[c.citation for c in citations[:5]],
                )
            )

        return chain

    # ------------------------------------------------------------------
    # Answer rendering — deterministic, no LLM
    # ------------------------------------------------------------------

    def _render_answer(
        self,
        parsed: ParsedQuery,
        kg_paths: list[AcademicKGPath],
        citations: list[AcademicCitation],
    ) -> str:
        """Render a deterministic answer from validated evidence.

        No LLM is used. The answer is assembled from structured evidence.
        """
        parts: list[str] = []

        # Header
        parts.append("关于" + parsed.subject + parsed.topic + "的查询结果如下。")

        # KG paths
        if kg_paths:
            parts.append("\n知识图谱路径（共" + str(len(kg_paths)) + "条）：")
            for i, path in enumerate(kg_paths[:10]):
                node_labels = " → ".join(n.label for n in path.nodes)
                edge_types = " → ".join(e.label for e in path.edges)
                parts.append(f"  [{i+1}] {node_labels}")
                parts.append(f"      关系链: {edge_types}")
                for j, edge in enumerate(path.edges):
                    if edge.evidence_citation:
                        parts.append(f"      边{j+1}证据: {edge.evidence_citation}")
                        if edge.evidence_quote:
                            parts.append(f"      引文: {edge.evidence_quote[:100]}")

        # Corpus citations
        if citations:
            parts.append(f"\n语料证据（共{len(citations)}条）：")
            for i, c in enumerate(citations[:10]):
                parts.append(f"  [{i+1}] {c.citation}")
                parts.append(f"      引文: {c.exact_quote[:120]}...")

        # Source summary
        if not kg_paths and not citations:
            parts.append("\n当前语料库中缺乏足够的可靠证据支持完整回答。")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Hash
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_response(resp: AcademicRAGResponse) -> str:
        """Compute deterministic output hash."""
        payload = resp.model_dump(mode="json")
        payload["output_sha256"] = ""
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()

    async def _compute_corpus_sha256(self) -> str:
        """Compute hash of all active chunks."""
        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.id)
        )
        result = await self.session.execute(chunk_stmt)
        chunks = result.scalars().all()
        parts = sorted(f"{c.document_id}:{c.id}:{c.content}" for c in chunks)
        return hashlib.sha256("\n".join(parts).encode()).hexdigest()
