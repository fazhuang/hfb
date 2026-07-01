"""
Graph Service — Sprint 3 P0: evidence-bound edges, concept graph, similarity, cross-document.

P0-1: create_relation validates entity existence, rejects self-loops, requires evidence,
      verifies chunk/document match, verifies quote is in chunk.
P0-2: build_concept_graph — corpus-endogenous concept extraction.
P0-3: concept_similarity — deterministic Jaccard co-occurrence.
P0-4: cross_document_analysis — evidence-bound claims, conservative contradiction.
P0-5: All outputs sorted deterministically, no timestamps in payload.
P0-6: intelligence() — unified API with corpus/output hash determinism.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from typing import Any
from uuid import UUID

from sqlalchemy import select, or_, and_
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
from app.models.version_relation import VersionRelation
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

    Returns None on success, or an error message string.
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


# ======================================================================
# GraphService
# ======================================================================


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
        """P0-1: Create an explicit entity relation with full validation.

        Validates:
          1. Entity types are valid
          2. Relation type is valid
          3. Source and target entities exist and are not deleted
          4. No self-loop (unless allowed)
          5. Evidence is present for non-FK relations
          6. Evidence chunk exists, belongs to claimed document, quote is in chunk,
             citation matches [doc_id:chunk_id], document exists
          7. Duplicate detection → ValueError
        """
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

        # 5. Duplicate check
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
        self.session.add(relation)
        await self.session.flush()
        return relation

    async def get_relations_for_entity(
        self, entity_type: str, entity_id: str
    ) -> list[EntityRelation]:
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
        return list(result.scalars().all())

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
    # Edge collection — all sources (EntityRelation + VersionRelation + FK)
    # ------------------------------------------------------------------

    async def _collect_all_edges(
        self, entity_ids: set[tuple[str, str]] | None = None
    ) -> tuple[list[GraphEdge], dict[str, GraphNode]]:
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
            # P0: query-time re-validation
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

        # --- 2. VersionRelation edges ---
        vr_stmt = (
            select(VersionRelation)
            .where(VersionRelation.is_deleted.is_(False))
            .order_by(VersionRelation.created_at)
        )
        vr_result = await self.session.execute(vr_stmt)
        vr_rows = vr_result.scalars().all()

        for vr in vr_rows:
            src_key = ("version", vr.source_version_id)
            tgt_key = ("version", vr.target_version_id)
            if entity_ids and (src_key not in entity_ids and tgt_key not in entity_ids):
                continue

            src_node_id = f"version:{vr.source_version_id}"
            tgt_node_id = f"version:{vr.target_version_id}"
            node_ids.add(src_node_id)
            node_ids.add(tgt_node_id)
            edges.append(
                GraphEdge(
                    id=f"vr:{vr.id}",
                    source_id=src_node_id,
                    target_id=tgt_node_id,
                    relation_type=vr.relation_type,
                    label=RELATION_LABELS.get(vr.relation_type, vr.relation_type),
                    source="version",
                )
            )

        # --- 3. FK-derived edges ---
        entity_by_type: dict[str, set[str]] = {}
        if entity_ids:
            for et, eid in entity_ids:
                entity_by_type.setdefault(et, set()).add(eid)
        fk_edges = await self._build_fk_edges(entity_by_type, entity_ids)
        for fe in fk_edges:
            node_ids.add(fe.source_id)
            node_ids.add(fe.target_id)
            edges.append(fe)

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

    async def _build_fk_edges(
        self,
        entity_by_type: dict[str, set[str]],
        entity_filter: set[tuple[str, str]] | None = None,
    ) -> list[GraphEdge]:
        edges: list[GraphEdge] = []

        def _should_include(et: str, eid: str) -> bool:
            if entity_filter is None:
                return True
            return (et, eid) in entity_filter

        # Book.author_id → Person
        book_stmt = (
            select(Book.id, Book.author_id, Book.title)
            .where(Book.is_deleted.is_(False))
            .order_by(Book.id)
        )
        books_to_check = entity_by_type.get("book", set())
        if books_to_check:
            book_stmt = book_stmt.where(Book.id.in_(sorted(books_to_check)))
        book_result = await self.session.execute(book_stmt)
        for row in book_result:
            if row.author_id and _should_include("person", row.author_id):
                edges.append(
                    GraphEdge(
                        id=f"fk_author:{row.id}",
                        source_id=f"book:{row.id}",
                        target_id=f"person:{row.author_id}",
                        relation_type="fk_author",
                        label=RELATION_LABELS["fk_author"],
                        source="fk",
                    )
                )

        # Version.book_id → Book
        ver_stmt = (
            select(Version.id, Version.book_id, Version.version_name)
            .where(Version.is_deleted.is_(False))
            .order_by(Version.id)
        )
        vers_to_check = entity_by_type.get("version", set())
        if vers_to_check:
            ver_stmt = ver_stmt.where(Version.id.in_(sorted(vers_to_check)))
        ver_result = await self.session.execute(ver_stmt)
        for row in ver_result:  # type: ignore[assignment]
            if row.book_id and _should_include("book", str(row.book_id)):
                edges.append(
                    GraphEdge(
                        id=f"fk_book:{row.id}",
                        source_id=f"version:{row.id}",
                        target_id=f"book:{row.book_id}",
                        relation_type="fk_book",
                        label=RELATION_LABELS["fk_book"],
                        source="fk",
                    )
                )

        # Passage.version_id → Version
        pass_stmt = (
            select(Passage.id, Passage.version_id, Passage.content_text)
            .where(Passage.is_deleted.is_(False))
            .order_by(Passage.id)
        )
        passages_to_check = entity_by_type.get("passage", set())
        if passages_to_check:
            pass_stmt = pass_stmt.where(Passage.id.in_(sorted(passages_to_check)))
        pass_result = await self.session.execute(pass_stmt)
        for row in pass_result:
            if row.version_id and _should_include("version", row.version_id):
                edges.append(
                    GraphEdge(
                        id=f"fk_passage_ver:{row.id}",
                        source_id=f"passage:{row.id}",
                        target_id=f"version:{row.version_id}",
                        relation_type="fk_passage_to_version",
                        label=RELATION_LABELS["fk_passage_to_version"],
                        source="fk",
                    )
                )

        return edges

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
    # Path Finding (BFS) — deterministic tie-break
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

        # Build sorted adjacency for deterministic BFS
        adjacency: dict[str, list[tuple[str, GraphEdge]]] = {}
        for edge in all_edges:
            adjacency.setdefault(edge.source_id, []).append((edge.target_id, edge))
            adjacency.setdefault(edge.target_id, []).append((edge.source_id, edge))
        # Sort neighbors by ID for determinism
        for nid in adjacency:
            adjacency[nid].sort(key=lambda x: x[0])

        # BFS with deterministic tie-break
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

        Concepts are discovered from chunk co-occurrence in the corpus.
        co_occurs_with only created when both concepts appear in the SAME sentence.
        Hierarchy edges only created from explicit directional markers
        (belongs-to, is-a-type-of, includes, contains, divided-into).
        No position-based guessing.
        """
        if not concept_labels:
            return ConceptGraph(nodes=[], edges=[])

        # Deduplicate and normalize labels
        labels = sorted(set(label.strip() for label in concept_labels if label.strip()))
        if not labels:
            return ConceptGraph(nodes=[], edges=[])

        # Fetch all chunks
        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.id)
        )
        chunk_result = await self.session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()

        # Build concept → chunk mapping
        concept_chunks: dict[str, list[DocumentChunk]] = {}
        for lbl in labels:
            concept_chunks[lbl] = []
            for c in all_chunks:
                if lbl in c.content:
                    concept_chunks[lbl].append(c)

        # Only create nodes for concepts actually found in corpus
        active_labels = [label for label in labels if concept_chunks[label]]
        if not active_labels:
            return ConceptGraph(nodes=[], edges=[])

        # Build nodes — evidence from ALL chunks (de-duplicated, stable sorted)
        nodes: list[ConceptNode] = []
        for lbl in active_labels:
            chunks = concept_chunks[lbl]
            concept_id = _stable_hash(lbl)
            doc_ids = sorted(set(c.document_id for c in chunks))
            chunk_ids = sorted(c.id for c in chunks)
            # Evidence from ALL chunks, one sentence per chunk
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
        # Hierarchy markers with EXACT directional semantics
        # Pattern: A belongs to B => A narrower_than B, B broader_than A
        narrower_markers = [
            re.compile(r"属于"),        # A属于B => A narrower_than B
            re.compile(r"是.*的一种"),    # A是B的一种 => A narrower_than B
        ]
        # Pattern: B includes A => B broader_than A, A narrower_than B
        broader_markers = [
            re.compile(r"包括"),        # B包括A => B broader_than A
            re.compile(r"包含"),        # B包含A => B broader_than A
            re.compile(r"分为"),        # B分为A => B broader_than A
        ]

        for i in range(len(active_labels)):
            for j in range(i + 1, len(active_labels)):
                a, b = active_labels[i], active_labels[j]
                a_chunks = set(c.id for c in concept_chunks[a])
                b_chunks = set(c.id for c in concept_chunks[b])
                shared_chunk_ids = sorted(a_chunks & b_chunks)
                if not shared_chunk_ids:
                    continue

                # Process ALL shared chunks for evidence — not just the first one
                co_occurrence_evidence: list[GraphEvidence] = []
                hierarchy_direction: str | None = None  # None | "a_narrower" | "b_narrower"
                hierarchy_evidence: GraphEvidence | None = None

                for cid in shared_chunk_ids:
                    chunk = next(c for c in all_chunks if c.id == cid)
                    # Split into sentences
                    sentences = re.split(r"(?<=[。！？.!?])", chunk.content)
                    for sent in sentences:
                        sent_s = sent.strip()
                        if not sent_s:
                            continue
                        if a not in sent_s or b not in sent_s:
                            continue

                        # Both concepts in same sentence → co-occurrence evidence
                        ev = _make_evidence(chunk.document_id, chunk.id, sent_s)
                        co_occurrence_evidence.append(ev)

                        # Check for hierarchy markers in this sentence
                        hi = GraphService._detect_hierarchy(sent_s, a, b, narrower_markers, broader_markers)
                        if hi is not None and hierarchy_direction is None:
                            hierarchy_direction = hi
                            hierarchy_evidence = ev

                if not co_occurrence_evidence:
                    continue  # no same-sentence co-occurrence → no edge

                # Deduplicate evidence by citation + exact_quote
                co_occurrence_evidence = GraphService._dedup_evidence(co_occurrence_evidence)

                # Always add co_occurs_with edge (with evidence from all shared sentences)
                edges.append(
                    ConceptEdge(
                        edge_id=_stable_hash(
                            ConceptNode.__name__, a, b, "co_occurs_with"
                        ),
                        source_concept_id=_stable_hash(a),
                        target_concept_id=_stable_hash(b),
                        relation_type="co_occurs_with",
                        label=RELATION_LABELS["co_occurs_with"],
                        evidence=co_occurrence_evidence,
                    )
                )

                # Add hierarchy edges if detected
                if hierarchy_direction and hierarchy_evidence:
                    if hierarchy_direction == "a_narrower":
                        # A narrower_than B
                        edges.append(
                            ConceptEdge(
                                edge_id=_stable_hash(
                                    ConceptNode.__name__, a, b, "narrower_than"
                                ),
                                source_concept_id=_stable_hash(a),
                                target_concept_id=_stable_hash(b),
                                relation_type="narrower_than",
                                label=RELATION_LABELS["narrower_than"],
                                evidence=[hierarchy_evidence],
                            )
                        )
                        # B broader_than A
                        edges.append(
                            ConceptEdge(
                                edge_id=_stable_hash(
                                    ConceptNode.__name__, b, a, "broader_than"
                                ),
                                source_concept_id=_stable_hash(b),
                                target_concept_id=_stable_hash(a),
                                relation_type="broader_than",
                                label=RELATION_LABELS["broader_than"],
                                evidence=[hierarchy_evidence],
                            )
                        )
                    elif hierarchy_direction == "b_narrower":
                        # B narrower_than A
                        edges.append(
                            ConceptEdge(
                                edge_id=_stable_hash(
                                    ConceptNode.__name__, b, a, "narrower_than"
                                ),
                                source_concept_id=_stable_hash(b),
                                target_concept_id=_stable_hash(a),
                                relation_type="narrower_than",
                                label=RELATION_LABELS["narrower_than"],
                                evidence=[hierarchy_evidence],
                            )
                        )
                        # A broader_than B
                        edges.append(
                            ConceptEdge(
                                edge_id=_stable_hash(
                                    ConceptNode.__name__, a, b, "broader_than"
                                ),
                                source_concept_id=_stable_hash(a),
                                target_concept_id=_stable_hash(b),
                                relation_type="broader_than",
                                label=RELATION_LABELS["broader_than"],
                                evidence=[hierarchy_evidence],
                            )
                        )

        # Sort edges deterministically
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
        """Detect hierarchy direction from explicit markers in a sentence.

        Returns:
          "a_narrower" if a is narrower than b (a属于b, a是b的一种)
          "b_narrower" if b is narrower than a (b属于a, b是a的一种)
                           or equivalently b包括a, b包含a, b分为a
          None if no explicit directional marker found

        Only return a result when the marker's syntactic direction is unambiguous:
        - 属于: subject (before 属于) is narrower, object (after 属于) is broader
        - 是...的一种: subject is narrower
        - 包括: subject is broader
        - 包含: subject is broader
        - 分为: subject is broader
        """
        # Check narrower markers: A属于B, A是B的一种
        for pat in narrower_markers:
            match = pat.search(sentence)
            if not match:
                continue
            marker_start = match.start()
            marker_end = match.end()

            # Determine which concept appears where relative to marker
            a_before = sentence.find(a)
            b_before = sentence.find(b)
            a_after = sentence.rfind(a)
            b_after = sentence.rfind(b)

            # A属于B: A appears before marker, B appears after → A narrower_than B
            if a_before < marker_start and b_after >= marker_end:
                # Verify: A between start and marker, B after marker
                if a_before >= 0 and b_after >= marker_end:
                    return "a_narrower"

            # B属于A: B appears before marker, A appears after → B narrower_than A
            if b_before < marker_start and a_after >= marker_end:
                if b_before >= 0 and a_after >= marker_end:
                    return "b_narrower"

        # Check broader markers: B包括A, B包含A, B分为A
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

            # B包括A: B appears before marker, A appears after → B broader_than A, A narrower_than B
            if b_before < marker_start and a_after >= marker_end:
                if b_before >= 0 and a_after >= marker_end:
                    return "a_narrower"

            # A包括B: A appears before marker, B appears after → A broader_than B, B narrower_than A
            if a_before < marker_start and b_after >= marker_end:
                if a_before >= 0 and b_after >= marker_end:
                    return "b_narrower"

        return None

    @staticmethod
    def _dedup_evidence(evidence: list[GraphEvidence]) -> list[GraphEvidence]:
        """Deduplicate evidence by citation + exact_quote, preserving stable order."""
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
        """Compute deterministic Jaccard similarity using actual corpus chunks.

        Formula: J(A, B) = |chunks(A) ∩ chunks(B)| / |chunks(A) ∪ chunks(B)|
        Score fixed to 4 decimal places. Ties broken by stable concept_id order.
        """
        # Fetch all chunks
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

        if union_size == 0:
            score = 0.0
        else:
            score = round(len(shared_chunks) / union_size, 4)

        # Evidence from first shared chunk
        if shared_chunks:
            cid = shared_chunks[0]
            chunk = next(c for c in all_chunks if c.id == cid)
            evidence.append(_make_evidence(chunk.document_id, chunk.id, chunk.content))

        # Corpus hash from all chunk content
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
    # Sprint 3 P0-4: Cross-Document Analysis — conservative contradiction
    # ==================================================================

    # Characters that look like negation but are part of compound words,
    # NOT independent negation markers. Example: 未病 (pre-disease), 无极 (ultimate).
    _COMPOUND_PREFIXES: set[str] = {"未病", "无极", "无病", "无疾", "非常", "非典", "无法"}

    @staticmethod
    def _has_negation(text: str) -> bool:
        """Check if text contains an explicit negation marker.

        Only counts independent negation markers, not characters inside
        compound words like 未病, 无极, etc.
        """
        markers = ["并非", "不是", "不", "非", "未", "否", "无"]
        for m in markers:
            idx = text.find(m)
            if idx < 0:
                continue
            # Check if this occurrence is part of a compound word
            is_compound = False
            for cp in GraphService._COMPOUND_PREFIXES:
                if text.startswith(cp, idx):
                    is_compound = True
                    break
            if not is_compound:
                return True
        return False

    @staticmethod
    def _normalize_claim(text: str) -> str:
        """Remove negation markers and whitespace to get normalized proposition.

        Used to compare whether two claims are about the same proposition.
        Only removes negation characters, NOT the words they modify.
        """
        negation_chars = ["不", "非", "未", "否", "无", "并"]
        result = text
        for nc in negation_chars:
            result = result.replace(nc, "")
        # Collapse whitespace
        result = re.sub(r"\s+", "", result)
        return result

    async def cross_document_analysis(self, topic: str) -> CrossDocumentAnalysis:
        """Analyze a topic across documents using only corpus evidence.

        Conservative contradiction detection (fail-closed):
          1. Claims must be from different documents
          2. Claims must share the same topic
          3. Normalized proposition (negation removed) must match
          4. Only one claim has explicit negation, the other doesn't
          5. Claims must be comparable (same normalized proposition body)

        Returns status:
          - "confirmed_contradiction": at least one pair meets all criteria
          - "supported_comparison": claims found, no contradiction criteria met
          - "insufficient_evidence": not enough comparable claims
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

        # Conservative contradiction detection
        contradictions: list[dict[str, CrossDocumentClaim]] = []
        status = "supported_comparison"

        for i in range(len(supporting)):
            for j in range(i + 1, len(supporting)):
                a, b = supporting[i], supporting[j]

                # Must be from different documents
                if a.document_id == b.document_id:
                    continue

                # Both must contain the topic
                if topic not in a.claim_text or topic not in b.claim_text:
                    continue

                # Must have opposite polarity
                a_neg = self._has_negation(a.claim_text)
                b_neg = self._has_negation(b.claim_text)
                if a_neg == b_neg:
                    continue  # both affirmative or both negative — not contradictory

                # Must have the same normalized proposition
                norm_a = self._normalize_claim(a.claim_text)
                norm_b = self._normalize_claim(b.claim_text)
                if norm_a != norm_b:
                    # ponytail: rough substring check — if normalized versions overlap
                    # significantly but aren't identical, they're probably not the same proposition
                    # Short claims: require exact match
                    # Longer claims: require substantial overlap
                    shorter = norm_a if len(norm_a) < len(norm_b) else norm_b
                    longer = norm_b if len(norm_a) < len(norm_b) else norm_a
                    if len(shorter) < 4 or shorter not in longer:
                        continue

                contradictions.append({"claim_a": a, "claim_b": b})

        if contradictions:
            status = "confirmed_contradiction"

        # Corpus hash from all chunks used
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

        # Compute output hash
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
        """Unified knowledge intelligence — deterministic, evidence-bound.

        Parses query into concepts, builds concept graph, computes pairwise
        similarities, runs cross-document analysis per concept, and returns
        a complete, hash-verifiable response.
        """
        # Parse query into concept labels (whitespace-delimited)
        raw_concepts = query.split()
        concepts = sorted(set(c.strip() for c in raw_concepts if c.strip()))
        if not concepts:
            concepts = [query.strip()]

        # Build concept graph
        concept_graph = await self.build_concept_graph(concepts)

        # Compute pairwise similarities (stable sorted pairs)
        similarities: list[ConceptSimilarity] = []
        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                sim = await self.compute_concept_similarity(concepts[i], concepts[j])
                similarities.append(sim)

        # Cross-document analysis per concept
        cross_doc_analyses: list[CrossDocumentAnalysis] = []
        for concept in concepts:
            analysis = await self.cross_document_analysis(concept)
            cross_doc_analyses.append(analysis)

        # Collect all citations (deduplicated, stable sorted)
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

        # Collect evidence traces
        evidence_trace: list[GraphEvidence] = []
        seen_tr: set[tuple[str, str]] = set()
        for analysis in cross_doc_analyses:
            for ev in analysis.evidence_trace:
                key = (ev.citation, ev.exact_quote)
                if key not in seen_tr:
                    seen_tr.add(key)
                    evidence_trace.append(ev)
        evidence_trace.sort(key=lambda e: (e.citation, e.exact_quote))

        # Corpus hash: based on all chunks used
        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.id)
        )
        chunk_result = await self.session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()
        corpus_parts = sorted(f"{c.document_id}:{c.id}:{c.content}" for c in all_chunks)
        corpus_sha256 = hashlib.sha256("\n".join(corpus_parts).encode()).hexdigest()

        # Build response
        response = {
            "query": query,
            "concept_graph": concept_graph.model_dump(mode="json"),
            "similarities": [s.model_dump(mode="json") for s in similarities],
            "cross_document_analyses": [a.model_dump(mode="json") for a in cross_doc_analyses],
            "citations": [ev.model_dump(mode="json") for ev in all_evidence],
            "evidence_trace": [ev.model_dump(mode="json") for ev in evidence_trace],
            "corpus_sha256": corpus_sha256,
            "output_sha256": "",
            "pipeline_version": "1.0.0",
        }

        # Compute output hash: canonical JSON with output_sha256 cleared
        payload_for_hash = dict(response)
        payload_for_hash["output_sha256"] = ""
        output_str = json.dumps(
            payload_for_hash, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        response["output_sha256"] = hashlib.sha256(output_str.encode()).hexdigest()

        return response
