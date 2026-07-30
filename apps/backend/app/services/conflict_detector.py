"""ConflictDetector — topological & TCM semantic conflict detection.

Phase 2c: Detects two classes of conflicts in evidence chains:
  1. Topological: reverse relations, same claim with rejected edges
  2. TCM Semantic: 十八反/十九畏 herb incompatibility, acupuncture contraindication
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph import EntityRelation
from app.schemas.graph import EvidenceChainPath

# TCM incompatibility pairs: herbs that must not be combined
_EIGHTEEN_ANTAGONISMS: set[frozenset[str]] = frozenset({
    frozenset({"甘草", "甘遂"}),
    frozenset({"甘草", "大戟"}),
    frozenset({"甘草", "海藻"}),
    frozenset({"甘草", "芫花"}),
    frozenset({"乌头", "贝母"}),
    frozenset({"乌头", "瓜蒌"}),
    frozenset({"乌头", "半夏"}),
    frozenset({"乌头", "白蔹"}),
    frozenset({"乌头", "白及"}),
    frozenset({"藜芦", "人参"}),
    frozenset({"藜芦", "沙参"}),
    frozenset({"藜芦", "丹参"}),
    frozenset({"藜芦", "玄参"}),
    frozenset({"藜芦", "细辛"}),
    frozenset({"藜芦", "芍药"}),
})

# Acupuncture contraindication keywords
_ACUPUNCTURE_CONTRA_KEYWORDS: dict[str, str] = {
    "禁针": "prohibits needling",
    "禁灸": "prohibits moxibustion",
    "不可刺": "must not be needled",
    "不可灸": "must not be moxibusted",
    "禁刺": "prohibits needling",
}


@dataclass
class Conflict:
    """A detected conflict in evidence chains."""

    conflict_type: str  # "topological_reverse" | "topological_rejected" | "tcm_herb_incompatibility" | "tcm_acupuncture_contra"
    description: str
    affected_path_ids: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    severity: str = "warning"  # "warning" | "error"


class ConflictDetector:
    """Detect conflicts in evidence chain paths."""

    @staticmethod
    async def detect(
        session: AsyncSession,
        paths: list[EvidenceChainPath],
    ) -> list[Conflict]:
        """Run all conflict detectors against evidence paths."""
        conflicts: list[Conflict] = []

        # 1. Topological: reverse relation pairs
        conflicts.extend(ConflictDetector._detect_reverse_relations(paths))

        # 2. Topological: same claim has rejected sibling edges
        conflicts.extend(await ConflictDetector._detect_rejected_claims(session, paths))

        # 3. TCM: herb incompatibility (十八反/十九畏)
        conflicts.extend(ConflictDetector._detect_herb_incompatibility(paths))

        # 4. TCM: acupuncture contraindication conflicts
        conflicts.extend(ConflictDetector._detect_acupuncture_contra(paths))

        return conflicts

    @staticmethod
    def _detect_reverse_relations(paths: list[EvidenceChainPath]) -> list[Conflict]:
        """Detect A->B and B->A in different paths."""
        conflicts: list[Conflict] = []
        edges_seen: dict[tuple[str, str, str, str, str], str] = {}
        # key: (source_type, source_id, target_type, target_id) -> path_id

        for path in paths:
            for hop in path.hops:
                forward = (hop.source_type, hop.source_id, hop.target_type, hop.target_id)
                reverse = (hop.target_type, hop.target_id, hop.source_type, hop.source_id)

                if reverse in edges_seen:
                    conflicts.append(Conflict(
                        conflict_type="topological_reverse",
                        description=f"反向关系: {hop.source_type}:{hop.source_id} <-> {hop.target_type}:{hop.target_id} "
                                    f"(路径 {edges_seen[reverse]} 与 {path.path_id})",
                        affected_path_ids=[edges_seen[reverse], path.path_id],
                        related_entities=[hop.source_id, hop.target_id],
                    ))
                edges_seen[forward] = path.path_id
        return conflicts

    @staticmethod
    async def _detect_rejected_claims(
        session: AsyncSession,
        paths: list[EvidenceChainPath],
    ) -> list[Conflict]:
        """Detect evidence paths whose claim has rejected peers."""
        conflicts: list[Conflict] = []
        for path in paths:
            for hop in path.hops:
                # Look for rejected edges with same claim pattern
                stmt = select(EntityRelation).where(
                    EntityRelation.source_entity_type == hop.source_type,
                    EntityRelation.source_entity_id == hop.source_id,
                    EntityRelation.target_entity_type == hop.target_type,
                    EntityRelation.target_entity_id == hop.target_id,
                    EntityRelation.relation_type == hop.relation_type,
                    EntityRelation.evidence_status == "rejected",
                    EntityRelation.is_deleted.is_(False),
                )
                result = await session.execute(stmt)
                rejected = result.scalars().all()
                if rejected:
                    conflicts.append(Conflict(
                        conflict_type="topological_rejected",
                        description=f"发现 {len(rejected)} 条被驳回的关系与路径 {path.path_id} 中的边对应同一 claim",
                        affected_path_ids=[path.path_id],
                        related_entities=[hop.source_id, hop.target_id],
                        severity="error",
                    ))
        return conflicts

    @staticmethod
    def _detect_herb_incompatibility(paths: list[EvidenceChainPath]) -> list[Conflict]:
        """Detect 十八反/十九畏 in herb entities across paths."""
        conflicts: list[Conflict] = []
        # Collect all herb entity names mentioned across paths
        herb_names: set[str] = set()
        for path in paths:
            for hop in path.hops:
                for etype in [hop.source_type, hop.target_type]:
                    if etype == "herb" and hop.citation:
                        herb_names.add(hop.citation)

        # Check for incompatibility pairs
        for pair in _EIGHTEEN_ANTAGONISMS:
            found = [h for h in herb_names if any(p in h for p in pair)]
            if len(found) >= 2:
                conflicts.append(Conflict(
                    conflict_type="tcm_herb_incompatibility",
                    description=f"配伍禁忌: {', '.join(found)} 可能存在十八反/十九畏冲突",
                    related_entities=found,
                    severity="error",
                ))
        return conflicts

    @staticmethod
    def _detect_acupuncture_contra(paths: list[EvidenceChainPath]) -> list[Conflict]:
        """Detect conflicting acupuncture indications across versions."""
        conflicts: list[Conflict] = []
        for path in paths:
            quotes = [h.exact_quote for h in path.hops if h.exact_quote]
            contra_found: list[str] = []
            for quote in quotes:
                for keyword, desc in _ACUPUNCTURE_CONTRA_KEYWORDS.items():
                    if keyword in quote:
                        contra_found.append(f"{keyword}({desc})")

            if len(contra_found) >= 2:
                conflicts.append(Conflict(
                    conflict_type="tcm_acupuncture_contra",
                    description=f"针灸禁忌冲突: 路径 {path.path_id} 中同时出现 {' 和 '.join(contra_found)}",
                    affected_path_ids=[path.path_id],
                ))
        return conflicts
