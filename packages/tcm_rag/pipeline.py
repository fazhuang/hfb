"""RAG pipeline — unified KG + literature search with evidence construction."""

from __future__ import annotations

import re

from tcm_kg.models import Edge
from tcm_kg.store import GraphStore
from tcm_kg.query import GraphQuery
from tcm_tei.models import Document
from tcm_rag.models import (
    KGPath,
    TextHit,
    EvidenceChain,
    CitationPath,
    SearchResult,
)


class RAGPipeline:
    """Academic RAG pipeline combining KG traversal and structured text search.

    >>> from tcm_kg.builder import KGBuilder
    >>> from tcm_tei.models import Document, TextVersion, Paragraph, Sentence
    >>> kg = KGBuilder.from_triples([...])
    >>> docs = {"zhenjiu": Document(...)}
    >>> rag = RAGPipeline(kg_store=kg, documents=docs)
    >>> result = rag.search("皇甫谧 针灸")
    >>> print(result.citation.to_inline())
    """

    def __init__(
        self,
        kg_store: GraphStore,
        documents: dict[str, Document],
    ) -> None:
        self.kg = GraphQuery(kg_store)
        self.documents = documents
        self._entity_index: dict[str, list[str]] = {}
        # ponytail: simple name→id index built on first search
        self._index_entities()

    def _index_entities(self) -> None:
        """Build a name-to-node-id index from KG nodes."""
        for node_id, node in self.kg.store._nodes.items():
            for key in ("name", "name_zh", "title", "title_zh"):
                value = node.properties.get(key)
                if value:
                    self._entity_index.setdefault(str(value), []).append(node_id)

    def search(
        self,
        query: str,
        max_kg_hops: int = 4,
        max_text_hits: int = 10,
    ) -> SearchResult:
        """Execute a combined KG + literature search.

        Args:
            query: Search query (Chinese text or entity names)
            max_kg_hops: Maximum hops for KG expansion
            max_text_hits: Maximum number of text matches to return

        Returns:
            SearchResult with evidence chains and citation paths
        """
        # Step 1: Find matching entities in KG
        entity_ids = self._resolve_entities(query)
        kg_paths: list[KGPath] = []
        text_hits: list[TextHit] = []

        # Step 2: Expand KG from matching entities
        visited_ids: set[str] = set()
        for eid in entity_ids:
            if eid in visited_ids:
                continue
            visited_ids.add(eid)
            subgraph = self.kg.expand(eid, max_hops=max_kg_hops)
            for edge in subgraph.edges:
                desc = self._describe_edge(edge)
                kg_paths.append(KGPath(edges=[edge], description=desc))

        # Step 3: Full-text search in documents
        search_terms = [t for t in re.split(r"[\s,，、]+", query) if t]
        for doc_id, doc in self.documents.items():
            for version in doc.versions:
                for para in version.paragraphs:
                    for sent in para.sentences:
                        score = self._match_score(sent.text, search_terms)
                        if score > 0:
                            text_hits.append(
                                TextHit(
                                    document_id=doc_id,
                                    paragraph_id=para.id,
                                    sentence_ids=[sent.id],
                                    text=sent.text,
                                    score=score,
                                    version_id=version.id,
                                )
                            )

        # Sort by score and limit
        text_hits.sort(key=lambda h: h.score, reverse=True)
        text_hits = text_hits[:max_text_hits]

        # Step 4: Build evidence chain
        # Deduplicate KG paths by edge identity (merging single-edge into
        # coherent multi-hop paths is O(n²) and not needed for basic RAG)
        evidence = EvidenceChain(
            claim=query,
            kg_paths=kg_paths,
            document_hits=text_hits,
        )

        # Step 5: Build citation path
        citation = self._build_citation(text_hits)

        return SearchResult(query=query, evidence=evidence, citation=citation)

    def _resolve_entities(self, query: str) -> list[str]:
        """Find entity IDs matching query terms."""
        entity_ids: set[str] = set()
        for term in re.split(r"[\s,，、]+", query):
            term = term.strip()
            if not term:
                continue
            if term in self._entity_index:
                entity_ids.update(self._entity_index[term])
        return list(entity_ids)

    @staticmethod
    def _match_score(text: str, terms: list[str]) -> float:
        """Simple keyword match score. Returns 0.0 to 1.0."""
        text_lower = text.lower()
        hits = sum(1 for t in terms if t.lower() in text_lower)
        if hits == 0:
            return 0.0
        return hits / len(terms)

    def _describe_edge(self, edge: Edge) -> str:
        """Create human-readable description of an edge traversal."""
        src = self.kg.store.get_node(edge.source_id)
        tgt = self.kg.store.get_node(edge.target_id)
        src_name = src.properties.get("name") or src.properties.get("title") or edge.source_id
        tgt_name = tgt.properties.get("name") or tgt.properties.get("title") or edge.target_id
        return f"{src_name} --[{edge.relation}]--> {tgt_name}"

    def _build_citation(self, hits: list[TextHit]) -> CitationPath:
        """Build a citation path from text hits."""
        segments: list[tuple[str, str]] = []
        seen: set[tuple[str, str, str]] = set()  # deduplicate

        for hit in hits:
            key = (hit.document_id, hit.paragraph_id, hit.text[:50])
            if key in seen:
                continue
            seen.add(key)

            doc = self.documents.get(hit.document_id)
            doc_title = doc.title if doc else hit.document_id
            ref = f"{doc_title}，{hit.paragraph_id}"
            if hit.version_id:
                ref += f"（{hit.version_id}）"
            segments.append((hit.document_id, ref))

        return CitationPath(segments=segments, format="inline")

    def build_evidence(self, result: SearchResult) -> EvidenceChain:
        """Build a structured evidence chain from a search result."""
        return result.evidence

    def cite(self, result: SearchResult) -> CitationPath:
        """Extract citation path from a search result."""
        return result.citation
