"""
Graph Service — Sprint 3 P0: evidence-bound edges, concept graph, similarity, cross-document.

P0-1: create_relation validates entity existence, rejects self-loops, requires evidence,
      verifies chunk/document match, verifies quote is in chunk.
P0-2: build_concept_graph — corpus-endogenous concept extraction.
P0-3: concept_similarity — deterministic Jaccard co-occurrence.
P0-4: cross_document_analysis — evidence-bound claims, template-based contradiction.
P0-5: All outputs sorted deterministically, no timestamps in payload.
P0-6: intelligence() — unified API with corpus/output hash determinism.
P0-7: FK/VersionRelation edges excluded unless corpus evidence exists.
P0-8: get_relations_for_entity with full validation.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from collections import deque
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.graph import (
    GRAPH_ENTITY_TYPES,
    GRAPH_RELATION_TYPES,
    SELF_LOOP_ALLOWED_TYPES,
    EntityRelation,
)
from app.models.passage import Passage  # noqa: F401
from app.models.person import Person
from app.models.version import Version
from app.schemas.graph import (
    RELATION_LABELS,
    ConceptEdge,
    ConceptGraph,
    ConceptNode,
    ConceptSimilarity,
    CrossDocumentAnalysis,
    CrossDocumentClaim,
    GraphEdge,
    GraphEvidence,
    GraphNode,
    NeighborResult,
    PathResult,
    Subgraph,
)
from app.services.generation_service import _is_substring

# --- Entity model map ---

ENTITY_MODEL_MAP: dict[str, Any] = {
    "person": Person,
    "book": Book,
    "version": Version,
    "passage": Passage,
}


# ======================================================================
# Helpers
# ======================================================================


async def _fetch_node(
    session: AsyncSession, entity_type: str, entity_id: str
) -> GraphNode | None:
    """Fetch a single entity and convert to a GraphNode."""
    model_cls = ENTITY_MODEL_MAP.get(entity_type)
    if model_cls is None:
        return None
    stmt = select(model_cls).where(model_cls.id == entity_id, model_cls.is_deleted.is_(False))
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        return None
    return _entity_to_node(obj, entity_type)


def _entity_to_node(obj: Any, entity_type: str) -> GraphNode:
    """Convert an ORM entity to a GraphNode."""
    node_id = f"{entity_type}:{obj.id}"
    label = _make_label(obj, entity_type)
    props: dict[str, Any] = {"id": obj.id, "entity_type": entity_type}
    if entity_type == "person":
        props["name"] = getattr(obj, "name", "")
        props["dynasty"] = getattr(obj, "dynasty", "")
        props["courtesy_name"] = getattr(obj, "courtesy_name", "")
    elif entity_type == "book":
        props["title"] = getattr(obj, "title", "")
        props["dynasty"] = getattr(obj, "dynasty", "")
        props["category"] = getattr(obj, "category", "")
    elif entity_type == "version":
        props["version_name"] = getattr(obj, "version_name", "")
        props["era"] = getattr(obj, "era", "")
        props["repository"] = getattr(obj, "repository", "")
    elif entity_type == "passage":
        content = getattr(obj, "content_text", "")
        props["content_preview"] = (
            content[:80] + "..." if len(content) > 80 else content
        )
        props["order"] = getattr(obj, "order", 0)
    return GraphNode(
        id=node_id,
        entity_type=entity_type,
        entity_id=obj.id,
        label=label,
        properties=props,
    )


def _make_label(obj: Any, entity_type: str) -> str:
    if entity_type == "person":
        name = getattr(obj, "name", "")
        dynasty = getattr(obj, "dynasty", "")
        return f"{name} ({dynasty})" if dynasty else name
    elif entity_type == "book":
        title = getattr(obj, "title", "")
        dynasty = getattr(obj, "dynasty", "")
        return f"《{title}》" + (f" ({dynasty})" if dynasty else "")
    elif entity_type == "version":
        vn = getattr(obj, "version_name", "")
        era = getattr(obj, "era", "")
        return vn + (f" ({era})" if era else "")
    elif entity_type == "passage":
        content = getattr(obj, "content_text", "")
        order = getattr(obj, "order", 0)
        preview = content[:40] + "..." if len(content) > 40 else content
        return f"#{order} {preview}"
    return str(obj.id)


def _stable_hash(*parts: str) -> str:
    """Stable hex digest from deterministic inputs — no UUID randomness."""
    return hashlib.sha256(":".join(parts).encode()).hexdigest()[:16]


def _make_evidence(
    document_id: str, chunk_id: str, exact_quote: str, citation: str | None = None
) -> GraphEvidence:
    if citation is None:
        citation = f"[{document_id}:{chunk_id}]"
    return GraphEvidence(
        document_id=document_id,
        chunk_id=chunk_id,
        exact_quote=exact_quote,
        citation=citation,
    )


# ======================================================================
# Evidence validation — Sprint 3 P0 hardened
# ======================================================================


async def _validate_graph_evidence(
    session: AsyncSession,
    document_id: str,
    chunk_id: str,
    exact_quote: str,
    citation: str,
) -> str | None:
    """Validate evidence comprehensively.

    Checks:
      1. Chunk exists and is not deleted
      2. Chunk.document_id matches provided document_id
      3. Document exists and is not deleted
      4. exact_quote is a normalized contiguous substring of chunk.content
      5. citation strictly equals [document_id:chunk_id]
    """
    # 1. Chunk exists and not deleted
    chunk_stmt = select(DocumentChunk).where(
        DocumentChunk.id == chunk_id, DocumentChunk.is_deleted.is_(False)
    )
    chunk_result = await session.execute(chunk_stmt)
    chunk = chunk_result.scalar_one_or_none()
    if chunk is None:
        return f"Chunk {chunk_id} not found or deleted"

    # 2. Chunk belongs to claimed document
    if chunk.document_id != document_id:
        return (
            f"Chunk {chunk_id} belongs to document {chunk.document_id}, "
            f"not claimed document {document_id}"
        )

    # 3. Document exists and not deleted
    doc_stmt = select(Document).where(
        Document.id == document_id, Document.is_deleted.is_(False)
    )
    doc_result = await session.execute(doc_stmt)
    if doc_result.scalar_one_or_none() is None:
        return f"Document {document_id} not found or deleted"

    # 4. exact_quote is contiguous substring (normalized) of chunk.content
    if not _is_substring(exact_quote, chunk.content):
        return f"Quote is not a contiguous substring of chunk {chunk_id} content"

    # 5. Citation must strictly equal [document_id:chunk_id]
    expected_citation = f"[{document_id}:{chunk_id}]"
    if citation != expected_citation:
        return f"Citation '{citation}' does not match expected '{expected_citation}'"

    return None


async def _entity_exists(
    session: AsyncSession, entity_type: str, entity_id: str
) -> bool:
    """Check an entity exists and is not deleted."""
    model_cls = ENTITY_MODEL_MAP.get(entity_type)
    if model_cls is None:
        return False
    stmt = select(model_cls).where(model_cls.id == entity_id, model_cls.is_deleted.is_(False))
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


# Sprint 3 P0-4: Cross-Document Analysis — parsed proposition, template-based
# ==================================================================


@dataclasses.dataclass(frozen=True)
class ParsedProposition:
    """A strictly-parsed proposition from a claim text.

    Only exact template matches are accepted. No substring inference.
    A claim that cannot be parsed into one of the 8 supported templates
    returns None from _parse_proposition.
    """

    family: str  # "是", "属于", "能", "可"
    subject: str
    predicate: str
    polarity: Literal["affirmative", "negative"]


# Ordered: negative patterns first so 不是 is tried before 是, 不能 before 能, etc.
_PROPOSITION_TEMPLATES: list[tuple[str, str, bool]] = [
    # (regex_pattern, family, is_negative)
    (r"^(.+)不是(.+)$", "是", True),
    (r"^(.+)不属于(.+)$", "属于", True),
    (r"^(.+)不能(.+)$", "能", True),
    (r"^(.+)不可(.+)$", "可", True),
    (r"^(.+)是(.+)$", "是", False),
    (r"^(.+)属于(.+)$", "属于", False),
    (r"^(.+)能(.+)$", "能", False),
    (r"^(.+)可(.+)$", "可", False),
]

# Compile once
_COMPILED_TEMPLATES: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(p), fam, neg) for p, fam, neg in _PROPOSITION_TEMPLATES
]


def _strip_trailing_punctuation(text: str) -> str:
    """Remove trailing punctuation and whitespace."""
    return re.sub(r"[\s。！？.!?，,；;：:、]+$", "", text.strip())


def _parse_proposition(text: str) -> ParsedProposition | None:
    """Parse text into a ParsedProposition using only exact template matching.

    Rules:
      1. Negative templates are tried first.
      2. A negated sentence must not be captured by an affirmative template.
      3. Leading/trailing whitespace and trailing punctuation are stripped.
      4. Subject and predicate must both be non-empty.
      5. No substring inference.
      6. No synonym or fuzzy-word inference.
      7. Extra clauses that prevent a clean parse → return None.

    Returns None if the text does not match any supported template.
    """
    clean = _strip_trailing_punctuation(text)
    if not clean:
        return None

    for pat, family, is_negative in _COMPILED_TEMPLATES:
        m = pat.match(clean)
        if not m:
            continue
        subject = m.group(1).strip()
        predicate = m.group(2).strip()
        if not subject or not predicate:
            return None

        # Reject if the matched region contains sentence boundaries or
        # complex clause markers that suggest this is not a clean match
        matched_text = m.group(0)
        # Reject if the matched text contains punctuation that suggests
        # additional clauses (commas, semicolons, mid-sentence punctuation)
        if re.search(r"[，,；;：:]", matched_text) or re.search(r"但|而|且|却|还|也|都", matched_text):
            return None
        # Reject if there are sentence breaks within the match
        if re.search(r"[。！？.!?]", matched_text):
            return None

        return ParsedProposition(
            family=family,
            subject=subject,
            predicate=predicate,
            polarity="negative" if is_negative else "affirmative",
        )

    return None


def _propositions_comparable(
    a: ParsedProposition, b: ParsedProposition
) -> bool:
    """Two propositions are comparable iff family, subject, and predicate match."""
    return (
        a.family == b.family
        and a.subject == b.subject
        and a.predicate == b.predicate
    )


class GraphService:
    """Application-layer graph traversals — Sprint 3 P0 hardened."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # P0-1: Entity Relations CRUD with full evidence validation
    # ------------------------------------------------------------------

    async def create_relation(
        self,
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        relation_type: str,
        description: str | None = None,
        evidence: GraphEvidence | None = None,
    ) -> EntityRelation:
        """P0-1: Create an explicit entity relation with full validation."""
        sid = str(source_entity_id)
        tid = str(target_entity_id)

        # 1-2. Type validation
        if source_entity_type not in GRAPH_ENTITY_TYPES:
            raise ValueError(f"Invalid source_entity_type: {source_entity_type}")
        if target_entity_type not in GRAPH_ENTITY_TYPES:
            raise ValueError(f"Invalid target_entity_type: {target_entity_type}")
        if relation_type not in GRAPH_RELATION_TYPES:
            raise ValueError(f"Invalid relation_type: {relation_type}")

        # 3. Entity existence
        if not await _entity_exists(self.session, source_entity_type, sid):
            raise ValueError(
                f"Source entity {source_entity_type}:{sid} not found or deleted"
            )
        if not await _entity_exists(self.session, target_entity_type, tid):
            raise ValueError(
                f"Target entity {target_entity_type}:{tid} not found or deleted"
            )

        # 4. Self-loop check
        if (
            source_entity_type == target_entity_type
            and sid == tid
            and relation_type not in SELF_LOOP_ALLOWED_TYPES
        ):
            raise ValueError(
                f"Self-loop not allowed for relation type '{relation_type}'"
            )

        # 6. Evidence validation
        if evidence is None:
            raise ValueError("Evidence is required to create an explicit relation")

        err = await _validate_graph_evidence(
            self.session,
            evidence.document_id,
            evidence.chunk_id,
            evidence.exact_quote,
            evidence.citation,
        )
        if err is not None:
            raise ValueError(f"Evidence validation failed: {err}")

        # 5. Duplicate check — now handled by DB unique constraint too
        existing = await self.session.execute(
            select(EntityRelation).where(
                EntityRelation.source_entity_type == source_entity_type,
                EntityRelation.source_entity_id == sid,
                EntityRelation.target_entity_type == target_entity_type,
                EntityRelation.target_entity_id == tid,
                EntityRelation.relation_type == relation_type,
                EntityRelation.is_deleted.is_(False),
            )
        )
        dup = existing.scalar_one_or_none()
        if dup is not None:
            raise ValueError(
                f"Duplicate relation: {source_entity_type}:{sid[:8]} "
                f"--[{relation_type}]--> {target_entity_type}:{tid[:8]} already exists"
            )

        relation = EntityRelation(
            source_entity_type=source_entity_type,
            source_entity_id=sid,
            target_entity_type=target_entity_type,
            target_entity_id=tid,
            relation_type=relation_type,
            description=description,
            evidence_document_id=evidence.document_id,
            evidence_chunk_id=evidence.chunk_id,
            evidence_quote=evidence.exact_quote,
            evidence_citation=evidence.citation,
        )
        try:
            self.session.add(relation)
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise ValueError(
                f"Duplicate relation: {source_entity_type}:{sid[:8]} "
                f"--[{relation_type}]--> {target_entity_type}:{tid[:8]} already exists"
            )
        return relation

    # ------------------------------------------------------------------
    # P0-8: Validated relation retrieval for API
    # ------------------------------------------------------------------

    async def get_validated_relations_for_entity(
        self, entity_type: str, entity_id: str
    ) -> list[tuple[EntityRelation, GraphEvidence]]:
        """Return only relations that pass full evidence + entity validation.

        Each result is (EntityRelation, GraphEvidence) — the evidence is
        guaranteed non-None because invalid relations are filtered out.
        """
        eid = str(entity_id)
        stmt = (
            select(EntityRelation)
            .where(
                or_(
                    and_(
                        EntityRelation.source_entity_type == entity_type,
                        EntityRelation.source_entity_id == eid,
                    ),
                    and_(
                        EntityRelation.target_entity_type == entity_type,
                        EntityRelation.target_entity_id == eid,
                    ),
                ),
                EntityRelation.is_deleted.is_(False),
            )
            .order_by(EntityRelation.created_at)
        )
        result = await self.session.execute(stmt)
        relations = result.scalars().all()

        validated: list[tuple[EntityRelation, GraphEvidence]] = []
        for er in relations:
            ev = await self._validate_explicit_relation(er)
            if ev is not None:
                validated.append((er, ev))
        return validated

    # ------------------------------------------------------------------
    # EntityRelation → GraphEvidence conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _relation_evidence(er: EntityRelation) -> GraphEvidence | None:
        """Convert an EntityRelation's structured evidence to GraphEvidence."""
        if er.evidence_document_id and er.evidence_chunk_id and er.evidence_quote:
            return _make_evidence(
                er.evidence_document_id,
                er.evidence_chunk_id,
                er.evidence_quote,
                er.evidence_citation
                or f"[{er.evidence_document_id}:{er.evidence_chunk_id}]",
            )
        return None

    # ------------------------------------------------------------------
    # P0: Query-time re-validation of explicit relations
    # ------------------------------------------------------------------

    async def _validate_explicit_relation(
        self, er: EntityRelation
    ) -> GraphEvidence | None:
        """Query-time re-validation of an explicit relation.

        Verifies:
          - source/target entities exist and are not deleted
          - evidence four fields are all present
          - citation, chunk, document, quote all valid
        Returns the evidence if valid, None if the relation should be excluded.
        """
        # Check entities exist
        if not await _entity_exists(self.session, er.source_entity_type, er.source_entity_id):
            return None
        if not await _entity_exists(self.session, er.target_entity_type, er.target_entity_id):
            return None

        # Check evidence four fields
        if not (
            er.evidence_document_id
            and er.evidence_chunk_id
            and er.evidence_quote
            and er.evidence_citation
        ):
            return None

        # Full evidence re-validation
        err = await _validate_graph_evidence(
            self.session,
            er.evidence_document_id,
            er.evidence_chunk_id,
            er.evidence_quote,
            er.evidence_citation,
        )
        if err is not None:
            return None

        return _make_evidence(
            er.evidence_document_id,
            er.evidence_chunk_id,
            er.evidence_quote,
            er.evidence_citation,
        )

    # ------------------------------------------------------------------
    # Edge collection — Evidence-required: only explicit EntityRelation with valid evidence
    # ------------------------------------------------------------------

    async def _collect_all_edges(
        self, entity_ids: set[tuple[str, str]] | None = None
    ) -> tuple[list[GraphEdge], dict[str, GraphNode]]:
        """Collect all knowledge graph edges.

        Only explicit EntityRelation edges with validated corpus evidence
        enter the graph. FK-derived and VersionRelation edges are EXCLUDED
        unless they have corpus-level sentence evidence.

        Every returned GraphEdge has non-null evidence.
        """
        edges: list[GraphEdge] = []
        node_ids: set[str] = set()

        # --- 1. EntityRelation edges (only with valid re-validated evidence) ---
        er_stmt = (
            select(EntityRelation)
            .where(EntityRelation.is_deleted.is_(False))
            .order_by(EntityRelation.created_at)
        )
        er_result = await self.session.execute(er_stmt)
        er_rows = er_result.scalars().all()

        for er in er_rows:
            ev = await self._validate_explicit_relation(er)
            if ev is None:
                continue

            src_key = (er.source_entity_type, er.source_entity_id)
            tgt_key = (er.target_entity_type, er.target_entity_id)
            if entity_ids and (src_key not in entity_ids and tgt_key not in entity_ids):
                continue

            src_node_id = f"{er.source_entity_type}:{er.source_entity_id}"
            tgt_node_id = f"{er.target_entity_type}:{er.target_entity_id}"
            node_ids.add(src_node_id)
            node_ids.add(tgt_node_id)
            edges.append(
                GraphEdge(
                    id=f"er:{er.id}",
                    source_id=src_node_id,
                    target_id=tgt_node_id,
                    relation_type=er.relation_type,
                    label=RELATION_LABELS.get(er.relation_type, er.relation_type),
                    source="explicit",
                    evidence=ev,
                )
            )

        # ponytail: FK and VersionRelation edges excluded — they are database
        # schema metadata, not corpus-evidenced knowledge. If a FK-derived edge
        # like "author" needs to appear in the graph, create an explicit
        # EntityRelation with a real corpus sentence as evidence.

        # --- Fetch all referenced nodes ---
        node_lookup: dict[str, GraphNode] = {}
        nodes_by_type: dict[str, set[str]] = {}
        for nid in node_ids:
            et, eid = nid.split(":", 1)
            nodes_by_type.setdefault(et, set()).add(eid)

        for entity_type, eids in sorted(nodes_by_type.items()):
            model_cls = ENTITY_MODEL_MAP.get(entity_type)
            if model_cls is None:
                continue
            stmt = (
                select(model_cls)
                .where(model_cls.id.in_(sorted(eids)), model_cls.is_deleted.is_(False))
                .order_by(model_cls.id)
            )
            result = await self.session.execute(stmt)
            for obj in result.scalars().all():
                node = _entity_to_node(obj, entity_type)
                node_lookup[node.id] = node

        return edges, node_lookup

    # ------------------------------------------------------------------
    # Neighborhood
    # ------------------------------------------------------------------

    async def get_neighbors(
        self, entity_type: str, entity_id: str, max_depth: int = 1
    ) -> NeighborResult:
        center = await _fetch_node(self.session, entity_type, str(entity_id))
        if center is None:
            raise ValueError(f"Entity {entity_type}:{entity_id} not found")

        all_edges, node_lookup = await self._collect_all_edges()
        center_id = center.id
        neighborhood_edges: list[GraphEdge] = []
        neighbor_ids: set[str] = set()

        for edge in all_edges:
            if edge.source_id == center_id or edge.target_id == center_id:
                neighborhood_edges.append(edge)
                if edge.source_id != center_id:
                    neighbor_ids.add(edge.source_id)
                if edge.target_id != center_id:
                    neighbor_ids.add(edge.target_id)

        neighbors = sorted(
            [node_lookup[nid] for nid in neighbor_ids if nid in node_lookup],
            key=lambda n: n.id,
        )

        return NeighborResult(
            center=center, neighbors=neighbors, edges=neighborhood_edges
        )

    # ------------------------------------------------------------------
    # Path Finding (BFS)
    # ------------------------------------------------------------------

    async def find_path(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        max_depth: int = 6,
    ) -> PathResult | None:
        source_node_id = f"{source_type}:{source_id}"
        target_node_id = f"{target_type}:{target_id}"

        if source_node_id == target_node_id:
            src_node = await _fetch_node(self.session, source_type, str(source_id))
            if src_node is None:
                return None
            return PathResult(nodes=[src_node], edges=[], length=0)

        all_edges, node_lookup = await self._collect_all_edges()

        adjacency: dict[str, list[tuple[str, GraphEdge]]] = {}
        for edge in all_edges:
            adjacency.setdefault(edge.source_id, []).append((edge.target_id, edge))
            adjacency.setdefault(edge.target_id, []).append((edge.source_id, edge))
        for nid in adjacency:
            adjacency[nid].sort(key=lambda x: x[0])

        queue: deque[tuple[str, list[str], list[str]]] = deque()
        queue.append((source_node_id, [source_node_id], []))
        visited: set[str] = {source_node_id}

        while queue:
            current, path_nodes, path_edges = queue.popleft()
            if len(path_nodes) > max_depth:
                continue
            for neighbor_id, edge in adjacency.get(current, []):
                if neighbor_id == target_node_id:
                    final_nodes = list(path_nodes) + [neighbor_id]
                    final_edges = list(path_edges) + [edge.id]
                    return self._build_path_result(
                        final_nodes, final_edges, node_lookup, all_edges
                    )
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(
                        (
                            neighbor_id,
                            list(path_nodes) + [neighbor_id],
                            list(path_edges) + [edge.id],
                        )
                    )

        return None

    def _build_path_result(
        self,
        node_ids: list[str],
        edge_ids: list[str],
        node_lookup: dict[str, GraphNode],
        all_edges: list[GraphEdge],
    ) -> PathResult:
        edge_map: dict[str, GraphEdge] = {e.id: e for e in all_edges}
        nodes = [node_lookup[nid] for nid in node_ids if nid in node_lookup]
        edges = [edge_map[eid] for eid in edge_ids if eid in edge_map]
        return PathResult(nodes=nodes, edges=edges, length=len(edges))

    # ------------------------------------------------------------------
    # Entity Subgraph
    # ------------------------------------------------------------------

    async def get_entity_subgraph(self, entity_type: str, entity_id: str) -> Subgraph:
        center = await _fetch_node(self.session, entity_type, str(entity_id))
        if center is None:
            raise ValueError(f"Entity {entity_type}:{entity_id} not found")

        neighbor_result = await self.get_neighbors(entity_type, str(entity_id))
        all_node_ids: set[str] = {center.id}
        for n in neighbor_result.neighbors:
            all_node_ids.add(n.id)
        all_edge_ids: set[str] = {e.id for e in neighbor_result.edges}

        all_edges, node_lookup = await self._collect_all_edges()
        subgraph_edges: list[GraphEdge] = []
        for edge in all_edges:
            if edge.source_id in all_node_ids and edge.target_id in all_node_ids:
                if edge.id not in all_edge_ids:
                    subgraph_edges.append(edge)
                    all_edge_ids.add(edge.id)

        all_edges_out = neighbor_result.edges + subgraph_edges
        subgraph_nodes = sorted(
            [node_lookup[nid] for nid in all_node_ids if nid in node_lookup],
            key=lambda n: n.id,
        )

        return Subgraph(nodes=subgraph_nodes, edges=all_edges_out)

    # ------------------------------------------------------------------
    # Search entities
    # ------------------------------------------------------------------

    async def search_entities(
        self, entity_types: list[str] | None = None, query: str = "", limit: int = 50
    ) -> list[GraphNode]:
        if entity_types is None:
            entity_types = sorted(GRAPH_ENTITY_TYPES)

        nodes: list[GraphNode] = []
        for et in sorted(entity_types):
            model_cls = ENTITY_MODEL_MAP.get(et)
            if model_cls is None:
                continue
            stmt = select(model_cls).where(model_cls.is_deleted.is_(False)).order_by(model_cls.id)
            if query:
                if et == "person":
                    stmt = stmt.where(
                        or_(
                            Person.name.contains(query),
                            Person.courtesy_name.contains(query),
                        )
                    )
                elif et in ("book", "version"):
                    title_field = getattr(model_cls, "title", None) or getattr(
                        model_cls, "version_name", None
                    )
                    if title_field is not None:
                        stmt = stmt.where(title_field.contains(query))
                elif et == "passage":
                    stmt = stmt.where(Passage.content_text.contains(query))
            stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            for obj in result.scalars().all():
                nodes.append(_entity_to_node(obj, et))
                if len(nodes) >= limit:
                    break
            if len(nodes) >= limit:
                break
        return nodes[:limit]

    # ------------------------------------------------------------------
    # Delete relation
    # ------------------------------------------------------------------

    async def delete_relation(self, relation_id: UUID | str) -> bool:
        stmt = select(EntityRelation).where(
            EntityRelation.id == str(relation_id), EntityRelation.is_deleted.is_(False)
        )
        result = await self.session.execute(stmt)
        relation = result.scalar_one_or_none()
        if relation is None:
            return False
        from datetime import datetime, timezone

        relation.is_deleted = True  # type: ignore[assignment]
        relation.deleted_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()
        return True

    # ==================================================================
    # Sprint 3 P0-2: Concept Graph — corpus-endogenous, same-sentence only
    # ==================================================================

    async def build_concept_graph(self, concept_labels: list[str]) -> ConceptGraph:
        """Build a concept graph for the given normalized concept labels.

        co_occurs_with only created when both concepts appear in the SAME sentence.
        Hierarchy edges only from explicit directional markers.
        No position-based guessing.
        """
        if not concept_labels:
            return ConceptGraph(nodes=[], edges=[])

        labels = sorted(set(label.strip() for label in concept_labels if label.strip()))
        if not labels:
            return ConceptGraph(nodes=[], edges=[])

        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.id)
        )
        chunk_result = await self.session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()

        concept_chunks: dict[str, list[DocumentChunk]] = {}
        for lbl in labels:
            concept_chunks[lbl] = []
            for c in all_chunks:
                if lbl in c.content:
                    concept_chunks[lbl].append(c)

        active_labels = [label for label in labels if concept_chunks[label]]
        if not active_labels:
            return ConceptGraph(nodes=[], edges=[])

        # Build nodes
        nodes: list[ConceptNode] = []
        for lbl in active_labels:
            chunks = concept_chunks[lbl]
            concept_id = _stable_hash(lbl)
            doc_ids = sorted(set(c.document_id for c in chunks))
            chunk_ids = sorted(c.id for c in chunks)
            evidence: list[GraphEvidence] = []
            for c in chunks:
                sentences = re.split(r"(?<=[。！？.!?])", c.content)
                for sent in sentences:
                    if lbl in sent:
                        evidence.append(
                            _make_evidence(c.document_id, c.id, sent.strip())
                        )
                        break
            nodes.append(
                ConceptNode(
                    concept_id=concept_id,
                    normalized_label=lbl,
                    display_label=lbl,
                    evidence=evidence,
                    source_document_ids=doc_ids,
                    source_chunk_ids=chunk_ids,
                )
            )

        # Build edges from same-sentence co-occurrence
        edges: list[ConceptEdge] = []
        narrower_markers = [
            re.compile(r"属于"),
            re.compile(r"是.*的一种"),
        ]
        broader_markers = [
            re.compile(r"包括"),
            re.compile(r"包含"),
            re.compile(r"分为"),
        ]

        for i in range(len(active_labels)):
            for j in range(i + 1, len(active_labels)):
                a, b = active_labels[i], active_labels[j]
                a_chunks = set(c.id for c in concept_chunks[a])
                b_chunks = set(c.id for c in concept_chunks[b])
                shared_chunk_ids = sorted(a_chunks & b_chunks)
                if not shared_chunk_ids:
                    continue

                co_occurrence_evidence: list[GraphEvidence] = []
                hierarchy_direction: str | None = None
                hierarchy_evidence: GraphEvidence | None = None

                for cid in shared_chunk_ids:
                    chunk = next(c for c in all_chunks if c.id == cid)
                    sentences = re.split(r"(?<=[。！？.!?])", chunk.content)
                    for sent in sentences:
                        sent_s = sent.strip()
                        if not sent_s:
                            continue
                        if a not in sent_s or b not in sent_s:
                            continue

                        ev = _make_evidence(chunk.document_id, chunk.id, sent_s)
                        co_occurrence_evidence.append(ev)

                        hi = GraphService._detect_hierarchy(
                            sent_s, a, b, narrower_markers, broader_markers
                        )
                        if hi is not None and hierarchy_direction is None:
                            hierarchy_direction = hi
                            hierarchy_evidence = ev

                if not co_occurrence_evidence:
                    continue

                co_occurrence_evidence = GraphService._dedup_evidence(co_occurrence_evidence)

                edges.append(
                    ConceptEdge(
                        edge_id=_stable_hash(ConceptNode.__name__, a, b, "co_occurs_with"),
                        source_concept_id=_stable_hash(a),
                        target_concept_id=_stable_hash(b),
                        relation_type="co_occurs_with",
                        label=RELATION_LABELS["co_occurs_with"],
                        evidence=co_occurrence_evidence,
                    )
                )

                if hierarchy_direction and hierarchy_evidence:
                    if hierarchy_direction == "a_narrower":
                        edges.append(
                            ConceptEdge(
                                edge_id=_stable_hash(ConceptNode.__name__, a, b, "narrower_than"),
                                source_concept_id=_stable_hash(a),
                                target_concept_id=_stable_hash(b),
                                relation_type="narrower_than",
                                label=RELATION_LABELS["narrower_than"],
                                evidence=[hierarchy_evidence],
                            )
                        )
                        edges.append(
                            ConceptEdge(
                                edge_id=_stable_hash(ConceptNode.__name__, b, a, "broader_than"),
                                source_concept_id=_stable_hash(b),
                                target_concept_id=_stable_hash(a),
                                relation_type="broader_than",
                                label=RELATION_LABELS["broader_than"],
                                evidence=[hierarchy_evidence],
                            )
                        )
                    elif hierarchy_direction == "b_narrower":
                        edges.append(
                            ConceptEdge(
                                edge_id=_stable_hash(ConceptNode.__name__, b, a, "narrower_than"),
                                source_concept_id=_stable_hash(b),
                                target_concept_id=_stable_hash(a),
                                relation_type="narrower_than",
                                label=RELATION_LABELS["narrower_than"],
                                evidence=[hierarchy_evidence],
                            )
                        )
                        edges.append(
                            ConceptEdge(
                                edge_id=_stable_hash(ConceptNode.__name__, a, b, "broader_than"),
                                source_concept_id=_stable_hash(a),
                                target_concept_id=_stable_hash(b),
                                relation_type="broader_than",
                                label=RELATION_LABELS["broader_than"],
                                evidence=[hierarchy_evidence],
                            )
                        )

        edges.sort(
            key=lambda e: (e.source_concept_id, e.target_concept_id, e.relation_type)
        )
        return ConceptGraph(nodes=nodes, edges=edges)

    @staticmethod
    def _detect_hierarchy(
        sentence: str,
        a: str,
        b: str,
        narrower_markers: list[re.Pattern],
        broader_markers: list[re.Pattern],
    ) -> str | None:
        """Detect hierarchy direction from explicit markers in a sentence."""
        for pat in narrower_markers:
            match = pat.search(sentence)
            if not match:
                continue
            marker_start = match.start()
            marker_end = match.end()

            a_before = sentence.find(a)
            b_before = sentence.find(b)
            a_after = sentence.rfind(a)
            b_after = sentence.rfind(b)

            if a_before < marker_start and b_after >= marker_end:
                if a_before >= 0 and b_after >= marker_end:
                    return "a_narrower"
            if b_before < marker_start and a_after >= marker_end:
                if b_before >= 0 and a_after >= marker_end:
                    return "b_narrower"

        for pat in broader_markers:
            match = pat.search(sentence)
            if not match:
                continue
            marker_start = match.start()
            marker_end = match.end()

            a_before = sentence.find(a)
            b_before = sentence.find(b)
            a_after = sentence.rfind(a)
            b_after = sentence.rfind(b)

            if b_before < marker_start and a_after >= marker_end:
                if b_before >= 0 and a_after >= marker_end:
                    return "a_narrower"
            if a_before < marker_start and b_after >= marker_end:
                if a_before >= 0 and b_after >= marker_end:
                    return "b_narrower"

        return None

    @staticmethod
    def _dedup_evidence(evidence: list[GraphEvidence]) -> list[GraphEvidence]:
        seen: set[tuple[str, str]] = set()
        result: list[GraphEvidence] = []
        for ev in evidence:
            key = (ev.citation, ev.exact_quote)
            if key not in seen:
                seen.add(key)
                result.append(ev)
        return result

    # ==================================================================
    # Sprint 3 P0-3: Deterministic Concept Similarity
    # ==================================================================

    async def compute_concept_similarity(
        self, concept_a: str, concept_b: str
    ) -> ConceptSimilarity:
        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.id)
        )
        chunk_result = await self.session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()

        a_chunks: set[str] = set()
        b_chunks: set[str] = set()
        a_docs: set[str] = set()
        b_docs: set[str] = set()
        evidence: list[GraphEvidence] = []

        for c in all_chunks:
            if concept_a in c.content:
                a_chunks.add(c.id)
                a_docs.add(c.document_id)
            if concept_b in c.content:
                b_chunks.add(c.id)
                b_docs.add(c.document_id)

        shared_chunks = sorted(a_chunks & b_chunks)
        shared_docs = sorted(a_docs & b_docs)
        union_size = len(a_chunks | b_chunks)

        score = round(len(shared_chunks) / union_size, 4) if union_size else 0.0

        if shared_chunks:
            cid = shared_chunks[0]
            chunk = next(c for c in all_chunks if c.id == cid)
            evidence.append(_make_evidence(chunk.document_id, chunk.id, chunk.content))

        corpus_parts = sorted(f"{c.document_id}:{c.id}:{c.content}" for c in all_chunks)
        corpus_sha = hashlib.sha256("\n".join(corpus_parts).encode()).hexdigest()

        return ConceptSimilarity(
            concept_a=concept_a,
            concept_b=concept_b,
            score=score,
            formula="jaccard_co_occurrence_v1",
            formula_version="1.0.0",
            shared_document_ids=shared_docs,
            shared_chunk_ids=shared_chunks,
            evidence=evidence,
            corpus_sha256=corpus_sha,
        )

    # ==================================================================
    # Sprint 3 P0-4: Cross-Document Analysis — parsed-proposition based
    # ==================================================================

    async def cross_document_analysis(self, topic: str) -> CrossDocumentAnalysis:
        """Analyze a topic across documents using parsed propositions.

        Status rules:
          - <2 documents → insufficient_evidence
          - ≥2 documents, no same proposition across docs → insufficient_evidence
          - ≥2 documents, same proposition, same polarity → supported_comparison
          - ≥2 documents, same proposition, opposite polarity → confirmed_contradiction

        Only claims that parse into one of the 8 supported templates
        (X是/不是Y, X属于/不属于Y, X能/不能P, X可/不可P) are used
        for comparison. Unparseable claims are silently ignored.
        """
        chunk_stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.is_deleted.is_(False),
                DocumentChunk.content.contains(topic),
            )
            .order_by(DocumentChunk.document_id, DocumentChunk.id)
        )
        chunk_result = await self.session.execute(chunk_stmt)
        chunks = chunk_result.scalars().all()

        if not chunks:
            return CrossDocumentAnalysis(topic=topic, status="insufficient_evidence")

        supporting: list[CrossDocumentClaim] = []
        doc_ids = sorted(set(c.document_id for c in chunks))
        evidence_traces: list[GraphEvidence] = []

        for c in chunks:
            sentences = re.split(r"(?<=[。！？.!?])", c.content)
            for sent in sentences:
                if topic in sent:
                    sent = sent.strip()
                    if not sent:
                        continue
                    ev = _make_evidence(c.document_id, c.id, sent)
                    evidence_traces.append(ev)
                    supporting.append(
                        CrossDocumentClaim(
                            claim_text=sent,
                            document_id=c.document_id,
                            chunk_id=c.id,
                            evidence=ev,
                        )
                    )

        # Status: need at least 2 documents
        if len(doc_ids) < 2:
            return CrossDocumentAnalysis(
                topic=topic,
                status="insufficient_evidence",
                supporting_claims=supporting,
                source_document_ids=doc_ids,
                evidence_trace=evidence_traces,
            )

        # Parse every claim into propositions. Only parseable claims are used.
        # Claims that cannot be parsed are silently skipped.
        parsed_pairs: list[tuple[CrossDocumentClaim, ParsedProposition]] = []
        for claim in supporting:
            prop = _parse_proposition(claim.claim_text)
            if prop is not None:
                parsed_pairs.append((claim, prop))

        # Try to find contradictions: same proposition, opposite polarity
        contradictions: list[dict[str, CrossDocumentClaim]] = []
        seen_comparable_docs: set[tuple[str, str]] = set()

        for i in range(len(parsed_pairs)):
            for j in range(i + 1, len(parsed_pairs)):
                a_claim, a_prop = parsed_pairs[i]
                b_claim, b_prop = parsed_pairs[j]

                if a_claim.document_id == b_claim.document_id:
                    continue

                if not _propositions_comparable(a_prop, b_prop):
                    continue

                # Same proposition, same document pair
                doc_pair = (a_claim.document_id, b_claim.document_id)
                seen_comparable_docs.add(doc_pair)

                if a_prop.polarity != b_prop.polarity:
                    # Opposite polarity → confirmed contradiction
                    contradictions.append({"claim_a": a_claim, "claim_b": b_claim})
                # ponytail: same-polarity comparable pairs already tracked via seen_comparable_docs

        if contradictions:
            status = "confirmed_contradiction"
        elif seen_comparable_docs:
            status = "supported_comparison"
        else:
            status = "insufficient_evidence"

        corpus_parts = sorted(f"{c.document_id}:{c.id}:{c.content}" for c in chunks)
        corpus_sha = hashlib.sha256("\n".join(corpus_parts).encode()).hexdigest()

        analysis = CrossDocumentAnalysis(
            topic=topic,
            status=status,
            supporting_claims=supporting,
            differing_claims=[],
            contradictions=contradictions,
            source_document_ids=doc_ids,
            evidence_trace=evidence_traces,
            corpus_sha256=corpus_sha,
        )

        payload = analysis.model_dump(mode="json")
        payload["output_sha256"] = ""
        output_str = json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        analysis.output_sha256 = hashlib.sha256(output_str.encode()).hexdigest()

        return analysis

    # ==================================================================
    # Sprint 3 P0-5: Unified Intelligence API
    # ==================================================================

    async def intelligence(self, query: str) -> dict[str, Any]:
        """Unified knowledge intelligence — deterministic, evidence-bound."""
        raw_concepts = query.split()
        concepts = sorted(set(c.strip() for c in raw_concepts if c.strip()))
        if not concepts:
            concepts = [query.strip()]

        concept_graph = await self.build_concept_graph(concepts)

        similarities: list[ConceptSimilarity] = []
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                sim = await self.compute_concept_similarity(concepts[i], concepts[j])
                similarities.append(sim)

        cross_doc_analyses: list[CrossDocumentAnalysis] = []
        for concept in concepts:
            analysis = await self.cross_document_analysis(concept)
            cross_doc_analyses.append(analysis)

        # Collect citations (deduplicated, stable sorted)
        all_evidence: list[GraphEvidence] = []
        seen_ev: set[tuple[str, str]] = set()
        for node in concept_graph.nodes:
            for ev in node.evidence:
                key = (ev.citation, ev.exact_quote)
                if key not in seen_ev:
                    seen_ev.add(key)
                    all_evidence.append(ev)
        for edge in concept_graph.edges:
            for ev in edge.evidence:
                key = (ev.citation, ev.exact_quote)
                if key not in seen_ev:
                    seen_ev.add(key)
                    all_evidence.append(ev)
        all_evidence.sort(key=lambda e: (e.citation, e.exact_quote))

        evidence_trace: list[GraphEvidence] = []
        seen_tr: set[tuple[str, str]] = set()
        for analysis in cross_doc_analyses:
            for ev in analysis.evidence_trace:
                key = (ev.citation, ev.exact_quote)
                if key not in seen_tr:
                    seen_tr.add(key)
                    evidence_trace.append(ev)
        evidence_trace.sort(key=lambda e: (e.citation, e.exact_quote))

        # Corpus hash: based on all chunks
        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.id)
        )
        chunk_result = await self.session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()
        corpus_parts = sorted(f"{c.document_id}:{c.id}:{c.content}" for c in all_chunks)
        corpus_sha256 = hashlib.sha256("\n".join(corpus_parts).encode()).hexdigest()

        response = {
            "query": query,
            "concept_graph": concept_graph.model_dump(mode="json"),
            "similarities": [s.model_dump(mode="json") for s in similarities],
            "cross_document_analyses": [a.model_dump(mode="json") for a in cross_doc_analyses],
            "citations": [ev.model_dump(mode="json") for ev in all_evidence],
            "evidence_trace": [ev.model_dump(mode="json") for ev in evidence_trace],
            "research_hypotheses": [],
            "corpus_sha256": corpus_sha256,
            "output_sha256": "",
            "pipeline_version": "1.0.0",
        }

        payload_for_hash = dict(response)
        payload_for_hash["output_sha256"] = ""
        output_str = json.dumps(
            payload_for_hash, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        response["output_sha256"] = hashlib.sha256(output_str.encode()).hexdigest()

        return response
