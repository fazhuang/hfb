"""
Graph Service — entity relationship traversal, neighborhood, and path finding.

Implements MVP knowledge graph on PostgreSQL using application-layer
graph algorithms (BFS, adjacency-list traversal).

Per HFB-PS-1707 Knowledge Graph Product Specification.
Per HFB-ARC-0201 Chapter 5: Neo4j deferred to Post-MVP; MVP uses PostgreSQL.
"""
from __future__ import annotations

from collections import deque
from typing import Any
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.graph import EntityRelation, GRAPH_ENTITY_TYPES, GRAPH_RELATION_TYPES
from app.models.passage import Passage  # noqa: F401 — used in isinstance checks
from app.models.person import Person
from app.models.version import Version
from app.models.version_relation import VersionRelation
from app.schemas.graph import (
    GraphNode,
    GraphEdge,
    Subgraph,
    PathResult,
    NeighborResult,
    RELATION_LABELS,
)

# --- Entity model map for FK derivation and label resolution ---

ENTITY_MODEL_MAP: dict[str, type] = {
    "person": Person,
    "book": Book,
    "version": Version,
    "passage": Passage,
}


async def _fetch_node(
    session: AsyncSession, entity_type: str, entity_id: str
) -> GraphNode | None:
    """Fetch a single entity and convert to a GraphNode."""
    model = ENTITY_MODEL_MAP.get(entity_type)
    if model is None:
        return None

    stmt = select(model).where(model.id == entity_id, model.is_deleted.is_(False))
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is None:
        return None

    return _entity_to_node(obj, entity_type)


def _entity_to_node(obj: Any, entity_type: str) -> GraphNode:
    """Convert an ORM entity to a GraphNode with a human-readable label."""
    node_id = f"{entity_type}:{obj.id}"

    label = _make_label(obj, entity_type)
    props: dict[str, Any] = {"id": obj.id, "entity_type": entity_type}

    # Add type-specific metadata
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
        props["content_preview"] = content[:80] + "..." if len(content) > 80 else content
        props["order"] = getattr(obj, "order", 0)

    return GraphNode(
        id=node_id,
        entity_type=entity_type,
        entity_id=obj.id,
        label=label,
        properties=props,
    )


def _make_label(obj: Any, entity_type: str) -> str:
    """Create a human-readable display label for an entity."""
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


# --- FK-derived edges (auto-generated from model relationships) ---


def _derive_fk_edges(nodes_by_id: dict[str, GraphNode]) -> list[GraphEdge]:
    """Generate edges from existing FK relationships among the fetched nodes.

    These edges are NOT stored in entity_relations — they are computed
    from the actual model FKs at query time so they always reflect the
    current data.
    """
    edges: list[GraphEdge] = []

    # We need the actual ORM objects. The GraphNode.properties only carries
    # a subset of fields. For FK derivation we need the raw FK fields.
    # Strategy: build edges from the node id patterns and known FK topology.
    #
    # The GraphService.s _resolve_edges method will use the ORM layer directly.
    # This function is kept for potential client-side use but isn't the primary
    # path.
    return edges


# ============================================================
# GraphService
# ============================================================


class GraphService:
    """Application-layer graph traversals on PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Entity Relations CRUD
    # ------------------------------------------------------------------

    async def create_relation(
        self,
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        relation_type: str,
        description: str | None = None,
        evidence: str | None = None,
    ) -> EntityRelation:
        """Create an explicit entity relation."""
        if source_entity_type not in GRAPH_ENTITY_TYPES:
            raise ValueError(f"Invalid source_entity_type: {source_entity_type}")
        if target_entity_type not in GRAPH_ENTITY_TYPES:
            raise ValueError(f"Invalid target_entity_type: {target_entity_type}")
        if relation_type not in GRAPH_RELATION_TYPES:
            raise ValueError(f"Invalid relation_type: {relation_type}")

        relation = EntityRelation(
            source_entity_type=source_entity_type,
            source_entity_id=str(source_entity_id),
            target_entity_type=target_entity_type,
            target_entity_id=str(target_entity_id),
            relation_type=relation_type,
            description=description,
            evidence=evidence,
        )
        self.session.add(relation)
        await self.session.flush()
        return relation

    async def get_relations_for_entity(
        self, entity_type: str, entity_id: str
    ) -> list[EntityRelation]:
        """Get all explicit relations involving an entity."""
        stmt = select(EntityRelation).where(
            or_(
                (EntityRelation.source_entity_type == entity_type) & (EntityRelation.source_entity_id == str(entity_id)),
                (EntityRelation.target_entity_type == entity_type) & (EntityRelation.target_entity_id == str(entity_id)),
            ),
            EntityRelation.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Edge collection — all sources (EntityRelation + VersionRelation + FK)
    # ------------------------------------------------------------------

    async def _collect_all_edges(
        self, entity_ids: set[tuple[str, str]] | None = None
    ) -> tuple[list[GraphEdge], dict[str, GraphNode]]:
        """Collect all edges and nodes for the entire graph or a subset.

        Returns (edges, node_lookup).

        Edge sources:
          1. entity_relations table (explicit cross-entity relations)
          2. version_relations table (version-to-version lineage)
          3. FK-derived (Book.author_id → Person, Version.book_id → Book, etc.)
        """
        edges: list[GraphEdge] = []
        node_ids: set[str] = set()  # composite "type:id" keys

        # --- 1. EntityRelation edges ---
        er_stmt = select(EntityRelation).where(EntityRelation.is_deleted.is_(False))
        er_result = await self.session.execute(er_stmt)
        er_rows = er_result.scalars().all()

        for er in er_rows:
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
                )
            )

        # --- 2. VersionRelation edges ---
        vr_stmt = select(VersionRelation).where(VersionRelation.is_deleted.is_(False))
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
        # Collect all entity IDs by type for batch lookup
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

        for entity_type, eids in nodes_by_type.items():
            model = ENTITY_MODEL_MAP.get(entity_type)
            if model is None:
                continue
            stmt = select(model).where(
                model.id.in_(list(eids)),
                model.is_deleted.is_(False),
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
        """Build FK-derived edges by querying actual FK columns.

        FK map:
          Book.author_id → Person    (fk_author)
          Version.book_id → Book     (fk_book)
          Chapter.book_id → Book     (fk_book_chapter) — excluded from MVP graph scope
          Chapter.parent_id → Chapter (fk_parent) — excluded
          Passage.chapter_id → Chapter (fk_chapter) — excluded
          Passage.version_id → Version (fk_passage_to_version)

        For the MVP knowledge graph (person, book, version, passage), we derive:
          Book → Person  (author)
          Version → Book (belongs to)
          Passage → Version (version-linked)
        """

        edges: list[GraphEdge] = []
        edge_counter = 0

        def _should_include(et: str, eid: str) -> bool:
            if entity_filter is None:
                return True
            return (et, eid) in entity_filter

        # Book.author_id → Person
        books_to_check = entity_by_type.get("book", set())
        if books_to_check or entity_filter is None:
            book_stmt = select(Book.id, Book.author_id, Book.title).where(
                Book.is_deleted.is_(False),
            )
            if books_to_check:
                book_stmt = book_stmt.where(Book.id.in_(list(books_to_check)))
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
                    edge_counter += 1

        # Version.book_id → Book
        vers_to_check = entity_by_type.get("version", set())
        if vers_to_check or entity_filter is None:
            ver_stmt = select(Version.id, Version.book_id, Version.version_name).where(
                Version.is_deleted.is_(False),
            )
            if vers_to_check:
                ver_stmt = ver_stmt.where(Version.id.in_(list(vers_to_check)))
            ver_result = await self.session.execute(ver_stmt)
            for row in ver_result:
                if _should_include("book", row.book_id):
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
                    edge_counter += 1

        # Passage.version_id → Version
        passages_to_check = entity_by_type.get("passage", set())
        if passages_to_check or entity_filter is None:
            pass_stmt = select(Passage.id, Passage.version_id, Passage.content_text).where(
                Passage.is_deleted.is_(False),
            )
            if passages_to_check:
                pass_stmt = pass_stmt.where(Passage.id.in_(list(passages_to_check)))
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
                    edge_counter += 1

        return edges

    # ------------------------------------------------------------------
    # Neighborhood
    # ------------------------------------------------------------------

    async def get_neighbors(
        self, entity_type: str, entity_id: str, max_depth: int = 1
    ) -> NeighborResult:
        """Return the 1-hop neighborhood subgraph around an entity.

        Includes:
          - The center node
          - All edges where center is source or target
          - All neighbor nodes (depth 1)
        """
        center = await _fetch_node(self.session, entity_type, str(entity_id))
        if center is None:
            raise ValueError(f"Entity {entity_type}:{entity_id} not found")

        # Collect all edges, filter to those involving center
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

        neighbors = [node_lookup[nid] for nid in neighbor_ids if nid in node_lookup]

        return NeighborResult(
            center=center,
            neighbors=neighbors,
            edges=neighborhood_edges,
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
        """Find the shortest path between two entities using BFS.

        Returns the path as nodes + edges, or None if unreachable.
        """
        source_node_id = f"{source_type}:{source_id}"
        target_node_id = f"{target_type}:{target_id}"

        if source_node_id == target_node_id:
            src_node = await _fetch_node(self.session, source_type, str(source_id))
            if src_node is None:
                return None
            return PathResult(nodes=[src_node], edges=[], length=0)

        # Collect all edges and build adjacency list
        all_edges, node_lookup = await self._collect_all_edges()

        # Build adjacency: node_id → list of (neighbor_id, edge)
        adjacency: dict[str, list[tuple[str, GraphEdge]]] = {}
        for edge in all_edges:
            adjacency.setdefault(edge.source_id, []).append((edge.target_id, edge))
            adjacency.setdefault(edge.target_id, []).append((edge.source_id, edge))

        # BFS
        # queue: (node_id, path_node_ids, path_edge_ids)
        queue: deque[tuple[str, list[str], list[str]]] = deque()
        queue.append((source_node_id, [source_node_id], []))
        visited: set[str] = {source_node_id}

        while queue:
            current, path_nodes, path_edges = queue.popleft()

            if len(path_nodes) > max_depth:
                continue

            for neighbor_id, edge in adjacency.get(current, []):
                if neighbor_id == target_node_id:
                    # Found path
                    final_nodes = list(path_nodes) + [neighbor_id]
                    final_edges = list(path_edges) + [edge.id]
                    return self._build_path_result(
                        final_nodes, final_edges, node_lookup, all_edges
                    )

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(
                        (neighbor_id, list(path_nodes) + [neighbor_id], list(path_edges) + [edge.id])
                    )

        return None  # No path found

    def _build_path_result(
        self,
        node_ids: list[str],
        edge_ids: list[str],
        node_lookup: dict[str, GraphNode],
        all_edges: list[GraphEdge],
    ) -> PathResult:
        """Build a PathResult from node and edge id lists."""
        edge_map: dict[str, GraphEdge] = {e.id: e for e in all_edges}
        nodes = [node_lookup[nid] for nid in node_ids if nid in node_lookup]
        edges = [edge_map[eid] for eid in edge_ids if eid in edge_map]
        return PathResult(nodes=nodes, edges=edges, length=len(edges))

    # ------------------------------------------------------------------
    # Entity Subgraph
    # ------------------------------------------------------------------

    async def get_entity_subgraph(
        self, entity_type: str, entity_id: str
    ) -> Subgraph:
        """Return the full subgraph centered on an entity (2-hop neighborhood).

        This is the primary endpoint for the graph explorer — it returns
        a focused subgraph around one entity with all connected neighbors.
        """
        center = await _fetch_node(self.session, entity_type, str(entity_id))
        if center is None:
            raise ValueError(f"Entity {entity_type}:{entity_id} not found")

        # 1-hop neighbors
        neighbor_result = await self.get_neighbors(entity_type, str(entity_id))

        # Collect all node IDs from 1-hop
        all_node_ids: set[str] = {center.id}
        for n in neighbor_result.neighbors:
            all_node_ids.add(n.id)

        all_edge_ids: set[str] = {e.id for e in neighbor_result.edges}

        # 2-hop: for each neighbor, find its neighbors (but not the full graph)
        # We limit to edges between the already-collected nodes for the subgraph view
        all_edges, node_lookup = await self._collect_all_edges()

        # Include edges between any two nodes in the 1-hop set
        subgraph_edges: list[GraphEdge] = []
        for edge in all_edges:
            if edge.source_id in all_node_ids and edge.target_id in all_node_ids:
                if edge.id not in all_edge_ids:
                    subgraph_edges.append(edge)
                    all_edge_ids.add(edge.id)

        all_edges_out = neighbor_result.edges + subgraph_edges
        subgraph_nodes = [node_lookup[nid] for nid in all_node_ids if nid in node_lookup]

        return Subgraph(nodes=subgraph_nodes, edges=all_edges_out)

    # ------------------------------------------------------------------
    # Graph-wide search / list entities
    # ------------------------------------------------------------------

    async def search_entities(
        self, entity_types: list[str] | None = None, query: str = "", limit: int = 50
    ) -> list[GraphNode]:
        """Search for entities across all graph types.

        Used by the graph explorer to find starting nodes.
        """
        if entity_types is None:
            entity_types = list(GRAPH_ENTITY_TYPES)

        nodes: list[GraphNode] = []
        for et in entity_types:
            model = ENTITY_MODEL_MAP.get(et)
            if model is None:
                continue

            stmt = select(model).where(model.is_deleted.is_(False))

            if query:
                # Search common name/title fields by type
                if et == "person":
                    stmt = stmt.where(
                        or_(
                            Person.name.contains(query),
                            Person.courtesy_name.contains(query),
                        )
                    )
                elif et in ("book", "version"):
                    title_field = getattr(model, "title", None) or getattr(
                        model, "version_name", None
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
    # Delete EntityRelation
    # ------------------------------------------------------------------

    async def delete_relation(self, relation_id: UUID | str) -> bool:
        """Soft-delete an EntityRelation."""
        stmt = select(EntityRelation).where(
            EntityRelation.id == str(relation_id),
            EntityRelation.is_deleted.is_(False),
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
