"""
Version Center services — comparison, lineage, diff, passage mapping.

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
from app.repositories.entities import VersionRepository, PassageRepository


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
        valid_types = {"derived_from", "revised_from", "corrected_by", "annotated_by", "compared_with", "referenced_by"}
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
                operations.append({
                    "op": tag,  # replace, delete, insert
                    "source_start": i1,
                    "source_end": i2,
                    "source_text": text1[i1:i2],
                    "target_start": j1,
                    "target_end": j2,
                    "target_text": text2[j1:j2],
                })

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
        stmt_src = select(Passage).where(
            Passage.version_id == str(source_version_id),
            Passage.is_deleted.is_(False),
        ).order_by(Passage.order)
        stmt_tgt = select(Passage).where(
            Passage.version_id == str(target_version_id),
            Passage.is_deleted.is_(False),
        ).order_by(Passage.order)

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
                sp = next((p for p in src_passages if p.id == m.source_passage_id), None)
                tp = next((p for p in tgt_passages if p.id == m.target_passage_id), None)
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
                    "operations": [{"op": "delete", "source_text": sp.content_text, "target_text": ""}],
                    "similarity_ratio": 0,
                }
            elif tp:
                diff = {
                    "source_passage": None,
                    "target_passage": {"id": tp.id, "text": tp.content_text},
                    "differences": 1,
                    "operations": [{"op": "insert", "source_text": "", "target_text": tp.content_text}],
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
