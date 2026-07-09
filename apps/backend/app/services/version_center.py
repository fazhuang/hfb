"""
Version Center services — comparison, lineage, diff, passage mapping, commentary.

Per HFB-PS-1701 Version Center Product Specification.
Per HFB-DOM-0803 Version Knowledge Model Ch.8-13.
"""

from __future__ import annotations

import difflib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.version import Version
from app.models.version_relation import VersionRelation, PassageMapping, VersionDiff
from app.models.passage import Passage
from app.models.commentary import Commentary
from app.repositories.entities import VersionRepository, PassageRepository
from app.schemas.commentary import CommentaryCreate, CommentaryResponse


class VersionComparisonService:
    """Handles version comparison, lineage, and diff operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.version_repo = VersionRepository(session)
        self.passage_repo = PassageRepository(session)

    # ------------------------------------------------------------------
    # Lineage / Tree
    # ------------------------------------------------------------------

    async def get_lineage(self, version_id: UUID | str) -> dict:
        """Return the version lineage tree for a given version.

        Returns the version node plus all its relations (parent + children),
        forming a tree suitable for frontend rendering.
        """
        version = await self.version_repo.get_by_id(version_id)
        if version is None:
            raise ValueError("Version not found")

        # Find all relations involving this version
        stmt = select(VersionRelation).where(
            (VersionRelation.source_version_id == str(version_id))
            | (VersionRelation.target_version_id == str(version_id)),
            VersionRelation.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        relations = result.scalars().all()

        ancestors = [r for r in relations if r.target_version_id == str(version_id)]
        descendants = [r for r in relations if r.source_version_id == str(version_id)]

        # Fetch related versions
        related_ids: set[str] = set()
        for r in relations:
            related_ids.add(r.source_version_id)
            related_ids.add(r.target_version_id)
        related_ids.discard(str(version_id))

        related_versions: dict[str, dict] = {}
        if related_ids:
            stmt = select(Version).where(
                Version.id.in_(related_ids),
                Version.is_deleted.is_(False),
            )
            result = await self.session.execute(stmt)
            for v in result.scalars().all():
                related_versions[v.id] = {
                    "id": v.id,
                    "version_name": v.version_name,
                    "era": v.era,
                    "repository": v.repository,
                }

        return {
            "version": {
                "id": version.id,
                "version_name": version.version_name,
                "era": version.era,
                "repository": version.repository,
            },
            "ancestors": [
                {
                    "relation_type": r.relation_type,
                    "description": r.description,
                    "source": related_versions.get(r.source_version_id),
                }
                for r in ancestors
            ],
            "descendants": [
                {
                    "relation_type": r.relation_type,
                    "description": r.description,
                    "target": related_versions.get(r.target_version_id),
                }
                for r in descendants
            ],
        }

    async def add_relation(
        self,
        source_version_id: UUID | str,
        target_version_id: UUID | str,
        relation_type: str,
        description: str | None = None,
        evidence: str | None = None,
    ) -> VersionRelation:
        """Create a VersionRelation."""
        valid_types = {
            "derived_from",
            "revised_from",
            "corrected_by",
            "annotated_by",
            "compared_with",
            "referenced_by",
        }
        if relation_type not in valid_types:
            raise ValueError(f"Invalid relation_type. Must be one of: {valid_types}")

        relation = VersionRelation(
            source_version_id=str(source_version_id),
            target_version_id=str(target_version_id),
            relation_type=relation_type,
            description=description,
            evidence=evidence,
        )
        self.session.add(relation)
        await self.session.flush()
        return relation

    # ------------------------------------------------------------------
    # Comparison / Diff
    # ------------------------------------------------------------------

    async def compare_passages(
        self,
        passage_id_1: UUID | str,
        passage_id_2: UUID | str,
    ) -> dict:
        """Generate a word/character-level diff between two passages."""
        p1 = await self.passage_repo.get_by_id(passage_id_1)
        p2 = await self.passage_repo.get_by_id(passage_id_2)

        if p1 is None:
            raise ValueError(f"Passage {passage_id_1} not found")
        if p2 is None:
            raise ValueError(f"Passage {passage_id_2} not found")

        text1 = p1.content_text
        text2 = p2.content_text

        # Character-level diff
        matcher = difflib.SequenceMatcher(None, text1, text2)
        operations: list[dict[str, Any]] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                operations.append(
                    {
                        "op": tag,  # replace, delete, insert
                        "source_start": i1,
                        "source_end": i2,
                        "source_text": text1[i1:i2],
                        "target_start": j1,
                        "target_end": j2,
                        "target_text": text2[j1:j2],
                    }
                )

        return {
            "source_passage": {
                "id": str(p1.id),
                "text": text1,
            },
            "target_passage": {
                "id": str(p2.id),
                "text": text2,
            },
            "differences": len(operations),
            "operations": operations,
            "similarity_ratio": round(matcher.ratio(), 4),
        }

    async def run_full_compare(
        self,
        source_version_id: UUID | str,
        target_version_id: UUID | str,
    ) -> dict:
        """Run a full passage-by-passage comparison of two versions.

        Uses PassageMapping to find equivalent passages, then diffs each pair.
        Falls back to order-based alignment if no mappings exist.
        """
        # Fetch all passages for each version
        stmt_src = (
            select(Passage)
            .where(
                Passage.version_id == str(source_version_id),
                Passage.is_deleted.is_(False),
            )
            .order_by(Passage.order)
        )
        stmt_tgt = (
            select(Passage)
            .where(
                Passage.version_id == str(target_version_id),
                Passage.is_deleted.is_(False),
            )
            .order_by(Passage.order)
        )

        src_result = await self.session.execute(stmt_src)
        tgt_result = await self.session.execute(stmt_tgt)
        src_passages = src_result.scalars().all()
        tgt_passages = tgt_result.scalars().all()

        # Check for explicit mappings
        mapped_pairs: list[tuple[Passage, Passage]] = []
        unmapped_src: list[Passage] = list(src_passages)
        unmapped_tgt: list[Passage] = list(tgt_passages)

        if src_passages and tgt_passages:
            src_ids = [p.id for p in src_passages]
            tgt_ids = [p.id for p in tgt_passages]

            stmt_map = select(PassageMapping).where(
                PassageMapping.source_passage_id.in_(src_ids),
                PassageMapping.target_passage_id.in_(tgt_ids),
                PassageMapping.is_deleted.is_(False),
            )
            map_result = await self.session.execute(stmt_map)
            mappings = map_result.scalars().all()

            mapped_src_ids: set[str] = set()
            mapped_tgt_ids: set[str] = set()
            for m in mappings:
                sp = next(
                    (p for p in src_passages if p.id == m.source_passage_id), None
                )
                tp = next(
                    (p for p in tgt_passages if p.id == m.target_passage_id), None
                )
                if sp and tp:
                    mapped_pairs.append((sp, tp))
                    mapped_src_ids.add(m.source_passage_id)
                    mapped_tgt_ids.add(m.target_passage_id)

            unmapped_src = [p for p in src_passages if p.id not in mapped_src_ids]
            unmapped_tgt = [p for p in tgt_passages if p.id not in mapped_tgt_ids]

        # Diff mapped pairs
        comparisons: list[dict] = []
        total_diffs = 0
        for sp, tp in mapped_pairs:
            diff = await self.compare_passages(sp.id, tp.id)
            comparisons.append(diff)
            total_diffs += diff["differences"]

        # Diff remaining by order alignment
        max_len = max(len(unmapped_src), len(unmapped_tgt))
        for i in range(max_len):
            sp = unmapped_src[i] if i < len(unmapped_src) else None
            tp = unmapped_tgt[i] if i < len(unmapped_tgt) else None
            if sp and tp:
                diff = await self.compare_passages(sp.id, tp.id)
            elif sp:
                diff = {
                    "source_passage": {"id": sp.id, "text": sp.content_text},
                    "target_passage": None,
                    "differences": 1,
                    "operations": [
                        {
                            "op": "delete",
                            "source_text": sp.content_text,
                            "target_text": "",
                        }
                    ],
                    "similarity_ratio": 0,
                }
            elif tp:
                diff = {
                    "source_passage": None,
                    "target_passage": {"id": tp.id, "text": tp.content_text},
                    "differences": 1,
                    "operations": [
                        {
                            "op": "insert",
                            "source_text": "",
                            "target_text": tp.content_text,
                        }
                    ],
                    "similarity_ratio": 0,
                }
            else:
                continue
            comparisons.append(diff)
            total_diffs += diff["differences"]

        # Store the computed diff
        diff_record = VersionDiff(
            source_version_id=str(source_version_id),
            target_version_id=str(target_version_id),
            diff_data=json.dumps(comparisons, ensure_ascii=False),
            diff_summary=f"{len(comparisons)} passages compared, {total_diffs} differences found",
            total_differences=total_diffs,
        )
        self.session.add(diff_record)
        await self.session.flush()

        return {
            "source_version_id": str(source_version_id),
            "target_version_id": str(target_version_id),
            "passage_pairs": len(comparisons),
            "total_differences": total_diffs,
            "comparisons": comparisons,
            "diff_id": str(diff_record.id),
        }

    async def get_saved_diff(self, diff_id: UUID | str) -> dict | None:
        """Retrieve a previously saved VersionDiff."""
        stmt = select(VersionDiff).where(
            VersionDiff.id == str(diff_id),
            VersionDiff.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        diff = result.scalar_one_or_none()
        if diff is None:
            return None
        return {
            "id": str(diff.id),
            "source_version_id": diff.source_version_id,
            "target_version_id": diff.target_version_id,
            "diff_data": json.loads(diff.diff_data),
            "diff_summary": diff.diff_summary,
            "total_differences": diff.total_differences,
            "created_at": diff.created_at.isoformat() if diff.created_at else None,
        }

    # ------------------------------------------------------------------
    # Passage Mapping
    # ------------------------------------------------------------------

    async def create_passage_mapping(
        self,
        source_passage_id: UUID | str,
        target_passage_id: UUID | str,
        mapping_type: str = "equivalent",
        description: str | None = None,
    ) -> PassageMapping:
        """Create a passage mapping between two versions."""
        valid_types = {"equivalent", "variant", "missing", "added"}
        if mapping_type not in valid_types:
            raise ValueError(f"Invalid mapping_type. Must be one of: {valid_types}")

        mapping = PassageMapping(
            source_passage_id=str(source_passage_id),
            target_passage_id=str(target_passage_id),
            mapping_type=mapping_type,
            description=description,
        )
        self.session.add(mapping)
        await self.session.flush()
        return mapping

    async def get_passage_mappings(
        self,
        version_id: UUID | str,
    ) -> list[dict]:
        """Get all passage mappings for a given version."""
        from app.models.passage import Passage

        # Find all passages in this version
        stmt = select(Passage).where(
            Passage.version_id == str(version_id),
            Passage.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        passage_ids = [p.id for p in result.scalars().all()]

        if not passage_ids:
            return []

        stmt = select(PassageMapping).where(
            (PassageMapping.source_passage_id.in_(passage_ids))
            | (PassageMapping.target_passage_id.in_(passage_ids)),
            PassageMapping.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        mappings = result.scalars().all()

        return [
            {
                "id": str(m.id),
                "source_passage_id": m.source_passage_id,
                "target_passage_id": m.target_passage_id,
                "mapping_type": m.mapping_type,
                "description": m.description,
                "is_verified": m.is_verified,
            }
            for m in mappings
        ]


# ======================================================================
# Phase 2b: Commentary (注疏链) CRUD
# ======================================================================


async def create_commentary(
    session: AsyncSession,
    data: CommentaryCreate,
) -> CommentaryResponse:
    """Create a commentary annotation."""
    c = Commentary(
        passage_id=data.passage_id,
        version_id=data.version_id,
        author_id=data.author_id,
        commentary_type=data.commentary_type,
        layer=data.layer,
        content_text=data.content_text,
        target_position_start=data.target_position_start,
        target_position_end=data.target_position_end,
        parent_id=data.parent_id,
        relation_type=data.relation_type,
    )
    session.add(c)
    await session.flush()
    await session.refresh(c)
    return CommentaryResponse(
        id=c.id,
        passage_id=c.passage_id,
        version_id=c.version_id,
        author_id=c.author_id,
        commentary_type=c.commentary_type,
        layer=c.layer,
        content_text=c.content_text,
        target_position_start=c.target_position_start,
        target_position_end=c.target_position_end,
        parent_id=c.parent_id,
        relation_type=c.relation_type,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


async def get_commentaries_for_passage(
    session: AsyncSession,
    passage_id: str,
    layer: str | None = None,
) -> list[CommentaryResponse]:
    """Get all commentaries for a passage, optionally filtered by layer."""
    stmt = select(Commentary).where(
        Commentary.passage_id == passage_id,
        Commentary.is_deleted.is_(False),
    )
    if layer:
        stmt = stmt.where(Commentary.layer == layer)
    stmt = stmt.order_by(Commentary.created_at)
    result = await session.execute(stmt)
    commentaries = result.scalars().all()
    return [
        CommentaryResponse(
            id=c.id,
            passage_id=c.passage_id,
            version_id=c.version_id,
            author_id=c.author_id,
            commentary_type=c.commentary_type,
            layer=c.layer,
            content_text=c.content_text,
            target_position_start=c.target_position_start,
            target_position_end=c.target_position_end,
            parent_id=c.parent_id,
            relation_type=c.relation_type,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in commentaries
    ]


async def get_commentary_chain(
    session: AsyncSession,
    commentary_id: str,
) -> list[CommentaryResponse]:
    """Trace the full commentary chain from root to the given node."""
    chain: list[CommentaryResponse] = []
    current_id: str | None = commentary_id
    visited: set[str] = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        stmt = select(Commentary).where(
            Commentary.id == current_id,
            Commentary.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        c = result.scalar_one_or_none()
        if not c:
            break
        chain.append(
            CommentaryResponse(
                id=c.id,
                passage_id=c.passage_id,
                version_id=c.version_id,
                author_id=c.author_id,
                commentary_type=c.commentary_type,
                layer=c.layer,
                content_text=c.content_text,
                target_position_start=c.target_position_start,
                target_position_end=c.target_position_end,
                parent_id=c.parent_id,
                relation_type=c.relation_type,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
        current_id = c.parent_id

    chain.reverse()  # root first
    return chain


# ======================================================================
# Phase 2b: Version Tree & Distance Matrix
# ======================================================================


async def compute_distance_matrix(
    session: AsyncSession,
    version_ids: list[str],
) -> dict[str, float]:
    """Compute Jaccard distance matrix for a set of versions.

    Jaccard distance = lines_changed / total_lines, derived from
    pre-computed VersionDiff records. Missing pairs return 1.0 (max distance).
    """
    from itertools import combinations

    matrix: dict[str, float] = {}
    for va_id, vb_id in combinations(version_ids, 2):
        stmt = select(VersionDiff).where(
            (
                (VersionDiff.source_version_id == va_id)
                & (VersionDiff.target_version_id == vb_id)
            )
            | (
                (VersionDiff.source_version_id == vb_id)
                & (VersionDiff.target_version_id == va_id)
            ),
            VersionDiff.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        diff = result.scalar_one_or_none()

        if diff and diff.diff_data:
            diff_data = (
                json.loads(diff.diff_data)
                if isinstance(diff.diff_data, str)
                else diff.diff_data
            )
            lines_changed = diff_data.get("lines_changed", 0)
            total_lines = diff_data.get("total_lines", 1)
            distance = lines_changed / max(total_lines, 1)
        else:
            distance = 1.0

        matrix[f"{va_id}-{vb_id}"] = round(min(distance, 1.0), 4)

    return matrix


async def compute_version_tree(
    session: AsyncSession,
    version_id: str,
) -> dict:
    """Build a version lineage tree rooted at or including the given version.

    Exhaustive BFS in both directions — visited node and visited edge sets
    control termination and prevent infinite loops, not an arbitrary depth
    cap.  Every reachable version and relation is included.

    Returns: root_version info, tree edges, distance matrix, closest versions,
    and divergence points.
    """
    from collections import defaultdict, deque

    from app.models.tei import TextualVariant

    stmt = select(Version).where(
        Version.id == version_id, Version.is_deleted.is_(False)
    )
    result = await session.execute(stmt)
    root = result.scalar_one_or_none()
    if not root:
        raise ValueError(f"Version {version_id} not found")

    version_set: set[str] = {version_id}
    relations_raw: list[VersionRelation] = []
    visited_edges: set[tuple[str, str, str]] = set()  # (source, target, relation_type)

    # --- Upward BFS (ancestors) — exhaust until closure ---
    up_queue: deque[str] = deque()
    up_queue.append(version_id)
    up_visited: set[str] = {version_id}
    while up_queue:
        current_id = up_queue.popleft()
        stmt = (
            select(VersionRelation)
            .where(
                VersionRelation.target_version_id == current_id,
                VersionRelation.is_deleted.is_(False),
            )
            .order_by(VersionRelation.source_version_id)
        )
        result = await session.execute(stmt)
        for rel in result.scalars().all():
            edge_key = (
                rel.source_version_id,
                rel.target_version_id,
                rel.relation_type,
            )
            if edge_key in visited_edges:
                continue
            visited_edges.add(edge_key)
            relations_raw.append(rel)
            version_set.add(rel.source_version_id)
            if rel.source_version_id not in up_visited:
                up_visited.add(rel.source_version_id)
                up_queue.append(rel.source_version_id)

    # --- Downward BFS (descendants) — exhaust until closure ---
    # Dynamically expands as newly discovered versions enter version_set.
    down_visited: set[str] = set()
    # Seed with versions known so far
    for vid in sorted(version_set):
        if vid not in down_visited:
            down_visited.add(vid)
    down_queue: deque[str] = deque(sorted(version_set))
    while down_queue:
        current_id = down_queue.popleft()
        stmt = (
            select(VersionRelation)
            .where(
                VersionRelation.source_version_id == current_id,
                VersionRelation.is_deleted.is_(False),
            )
            .order_by(VersionRelation.target_version_id)
        )
        result = await session.execute(stmt)
        for rel in result.scalars().all():
            edge_key = (
                rel.source_version_id,
                rel.target_version_id,
                rel.relation_type,
            )
            if edge_key in visited_edges:
                continue
            visited_edges.add(edge_key)
            relations_raw.append(rel)
            version_set.add(rel.target_version_id)
            if rel.target_version_id not in down_visited:
                down_visited.add(rel.target_version_id)
                down_queue.append(rel.target_version_id)

    all_versions: dict[str, Version] = {}
    if version_set:
        stmt = select(Version).where(
            Version.id.in_(version_set), Version.is_deleted.is_(False)
        )
        result = await session.execute(stmt)
        all_versions = {v.id: v for v in result.scalars().all()}

    # Build tree edges — deterministic order
    tree_edges = []
    for rel in sorted(
        relations_raw,
        key=lambda r: (r.source_version_id, r.target_version_id, r.relation_type),
    ):
        distance = 1.0
        diff_stmt = select(VersionDiff).where(
            (
                (VersionDiff.source_version_id == rel.source_version_id)
                & (VersionDiff.target_version_id == rel.target_version_id)
            ),
            VersionDiff.is_deleted.is_(False),
        )
        diff_result = await session.execute(diff_stmt)
        diff = diff_result.scalar_one_or_none()
        if diff and diff.diff_data:
            diff_data = (
                json.loads(diff.diff_data)
                if isinstance(diff.diff_data, str)
                else diff.diff_data
            )
            lines_changed = diff_data.get("lines_changed", 0)
            total_lines = diff_data.get("total_lines", 1)
            distance = lines_changed / max(total_lines, 1)

        tree_edges.append(
            {
                "parent_id": rel.source_version_id,
                "child_id": rel.target_version_id,
                "relation_type": rel.relation_type,
                "distance": round(min(distance, 1.0), 4),
            }
        )

    # Distance matrix
    version_list = sorted(version_set)
    distance_matrix = await compute_distance_matrix(session, version_list)

    # Closest versions to root — construct lookup keys from known IDs,
    # NEVER parse UUIDs via split("-") which fragments UUID hyphens.
    closest = []
    root_distances: dict[str, float] = {}
    for other_id in sorted(version_set - {version_id}):
        key_a = f"{version_id}-{other_id}"
        key_b = f"{other_id}-{version_id}"
        dist = distance_matrix.get(key_a, distance_matrix.get(key_b))
        if dist is not None:
            root_distances[other_id] = dist

    for other_id in sorted(root_distances, key=lambda k: root_distances[k]):
        v_obj = all_versions.get(other_id)
        closest.append(
            {
                "version_id": other_id,
                "name": v_obj.version_name if v_obj else other_id,
                "distance": root_distances[other_id],
            }
        )

    # Divergence points
    divergence_points = []
    for other_id in sorted(version_set - {version_id}):
        variant_stmt = select(TextualVariant).where(
            (
                (TextualVariant.source_version_id == version_id)
                & (TextualVariant.target_version_id == other_id)
            )
            | (
                (TextualVariant.source_version_id == other_id)
                & (TextualVariant.target_version_id == version_id)
            ),
            TextualVariant.is_deleted.is_(False),
        )
        variant_result = await session.execute(variant_stmt)
        variants = variant_result.scalars().all()

        passage_counts: dict[str, list] = defaultdict(list)
        for v in variants:
            pid = v.source_passage_id or v.target_passage_id
            if pid:
                passage_counts[pid].append(v)

        for pid, vlist in passage_counts.items():
            if len(vlist) >= 1:
                pass_stmt = select(Passage).where(
                    Passage.id == pid, Passage.is_deleted.is_(False)
                )
                pass_result = await session.execute(pass_stmt)
                passage = pass_result.scalar_one_or_none()
                divergence_points.append(
                    {
                        "passage_id": pid,
                        "passage_text": passage.content_text[:200] if passage else "",
                        "diff_summary": f"{len(vlist)} variants between {version_id} and {other_id}",
                        "variant_count": len(vlist),
                    }
                )

    return {
        "root_version": {
            "id": root.id,
            "name": root.version_name,
            "era": root.era or "",
            "year": root.year or 0,
        },
        "tree": tree_edges,
        "distance_matrix": distance_matrix,
        "closest_to": closest,
        "divergence_points": divergence_points[:20],
    }


async def get_commentary_graph(
    session: AsyncSession,
    passage_id: str,
) -> dict:
    """Get the commentary debate/supplement graph for a passage."""
    stmt = select(Commentary).where(
        Commentary.passage_id == passage_id,
        Commentary.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    commentaries = result.scalars().all()

    nodes = [
        CommentaryResponse(
            id=c.id,
            passage_id=c.passage_id,
            version_id=c.version_id,
            author_id=c.author_id,
            commentary_type=c.commentary_type,
            layer=c.layer,
            content_text=c.content_text,
            target_position_start=c.target_position_start,
            target_position_end=c.target_position_end,
            parent_id=c.parent_id,
            relation_type=c.relation_type,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in commentaries
    ]

    edges = [
        {"parent_id": c.parent_id, "child_id": c.id, "relation_type": c.relation_type}
        for c in commentaries
        if c.parent_id
    ]

    return {"nodes": nodes, "edges": edges}
