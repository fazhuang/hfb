"""
Admin domain admission audit script.

Scans persons and graph entities in the database, verifying whether each entity has a valid trace path
starting from anchor 'person:huangfu_mi' ('ENTITY-PER-0001') with step count N <= 3.

Rules:
1. Legacy data is NOT automatically marked as verified.
2. Entities whose path cannot be proven are set to or kept as 'pending'.
3. Outputs detailed statistics (total, verified, pending, untraceable list, evidence paths).
4. Generates CLI Markdown report and writes audit JSON to apps/backend/reports/domain_admission_audit_report.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import deque
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure app package is importable when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import close_database, init_database, get_session, async_session_factory
from app.models.person import Person
from app.models.graph import EntityRelation
from app.services.domain_admission import verify_domain_anchor_path, VALID_START_NODES


def _format_node_id(entity_type: str, entity_id: str) -> str:
    return f"{entity_type}:{entity_id}"


async def run_audit(session: AsyncSession, fix: bool = True) -> dict[str, Any]:
    """Execute domain admission audit over persons and graph entities.

    If fix is True, updates unprovable entities in DB to 'pending' status.
    """
    timestamp = datetime.now(UTC).isoformat()

    # 1. Fetch all Person records
    person_stmt = select(Person).where(Person.is_deleted.is_(False))
    person_result = await session.execute(person_stmt)
    persons: list[Person] = list(person_result.scalars().all())

    # 2. Fetch all EntityRelation records
    er_stmt = select(EntityRelation).where(EntityRelation.is_deleted.is_(False))
    er_result = await session.execute(er_stmt)
    entity_relations: list[EntityRelation] = list(er_result.scalars().all())

    # Build adjacency graph for path finding
    # Graph maps node_id -> list of (neighbor_node_id, relation_type)
    adjacency: dict[str, list[tuple[str, str]]] = {}
    for er in entity_relations:
        src = _format_node_id(er.source_entity_type, er.source_entity_id)
        tgt = _format_node_id(er.target_entity_type, er.target_entity_id)
        adjacency.setdefault(src, []).append((tgt, er.relation_type))
        adjacency.setdefault(tgt, []).append((src, er.relation_type))

    # Identify anchor nodes
    anchor_nodes: set[str] = set(VALID_START_NODES)
    for p in persons:
        if p.id == "ENTITY-PER-0001" or p.name == "皇甫谧":
            anchor_nodes.add(f"person:{p.id}")
            anchor_nodes.add(p.id)

    # BFS to pre-calculate all shortest paths from anchor nodes up to 3 hops (N <= 3)
    # path_map: target_node -> path list of nodes/relations
    shortest_paths: dict[str, list[str]] = {}
    queue: deque[tuple[str, list[str]]] = deque()

    for anchor in anchor_nodes:
        queue.append((anchor, [anchor]))
        shortest_paths[anchor] = [anchor]

    while queue:
        curr_node, path = queue.popleft()
        # Hop count N = (len(nodes_and_rels) - 1) // 2 or len(nodes) - 1
        # Each step in our path alternates node, rel, node
        nodes_in_path = [item for item in path if not item.startswith("rel:")]
        step_count = len(nodes_in_path) - 1

        if step_count >= 3:
            continue

        for neighbor, rel_type in adjacency.get(curr_node, []):
            if neighbor not in shortest_paths:
                new_path = list(path) + [f"rel:{rel_type}", neighbor]
                shortest_paths[neighbor] = new_path
                queue.append((neighbor, new_path))

    # Audit Persons
    total_persons = len(persons)
    verified_persons = 0
    pending_persons = 0
    demoted_persons = 0
    untraceable_list: list[dict[str, Any]] = []
    evidence_paths: dict[str, list[str]] = {}

    for p in persons:
        node_key = f"person:{p.id}"
        prev_status = p.domain_status
        proven_path: list[str] | None = None

        # Check 1: Is this an anchor node itself?
        if p.id in anchor_nodes or node_key in anchor_nodes or p.name == "皇甫谧":
            proven_path = ["person:huangfu_mi"]
        # Check 2: Does it have an existing valid anchor_path?
        elif p.anchor_path:
            try:
                if verify_domain_anchor_path(p.anchor_path, "verified"):
                    parsed = json.loads(p.anchor_path) if isinstance(p.anchor_path, str) else p.anchor_path
                    proven_path = [str(x) for x in parsed]
            except ValueError:
                proven_path = None

        # Check 3: Can BFS find a path N <= 3?
        if proven_path is None:
            if node_key in shortest_paths:
                proven_path = shortest_paths[node_key]
            elif p.id in shortest_paths:
                proven_path = shortest_paths[p.id]

        if proven_path is not None:
            # Valid path proven!
            evidence_paths[p.id] = proven_path
            # Only keep verified if it was verified, or if fixing and path is solid
            if p.domain_status == "verified":
                verified_persons += 1
            else:
                # Rule: Do not automatically promote old data to verified without explicit review
                pending_persons += 1
            if fix and not p.anchor_path:
                p.anchor_path = json.dumps(proven_path)
        else:
            # Path unprovable!
            pending_persons += 1
            if prev_status == "verified":
                demoted_persons += 1
                if fix:
                    p.domain_status = "pending"
                    p.anchor_path = None

            untraceable_list.append({
                "id": p.id,
                "name": p.name,
                "entity_type": "person",
                "previous_status": prev_status,
                "current_status": "pending" if fix else prev_status,
                "reason": "No valid anchor path originating from person:huangfu_mi within N <= 3 steps",
            })

    # Audit EntityRelations
    total_relations = len(entity_relations)
    verified_relations = 0
    pending_relations = 0
    demoted_relations = 0

    for er in entity_relations:
        src_key = _format_node_id(er.source_entity_type, er.source_entity_id)
        tgt_key = _format_node_id(er.target_entity_type, er.target_entity_id)
        prev_status = er.domain_status

        src_reachable = src_key in shortest_paths or er.source_entity_id in anchor_nodes
        tgt_reachable = tgt_key in shortest_paths or er.target_entity_id in anchor_nodes

        if src_reachable or tgt_reachable:
            if er.domain_status == "verified":
                verified_relations += 1
            else:
                pending_relations += 1
        else:
            pending_relations += 1
            if prev_status == "verified":
                demoted_relations += 1
                if fix:
                    er.domain_status = "pending"
            untraceable_list.append({
                "id": er.id,
                "name": f"{er.source_entity_type}:{er.source_entity_id} -> {er.target_entity_type}:{er.target_entity_id}",
                "entity_type": "entity_relation",
                "previous_status": prev_status,
                "current_status": "pending" if fix else prev_status,
                "reason": "Neither source nor target entity connected to anchor within N <= 3 steps",
            })

    if fix:
        await session.commit()

    report_data: dict[str, Any] = {
        "timestamp": timestamp,
        "summary": {
            "total_persons": total_persons,
            "verified_persons": verified_persons,
            "pending_persons": pending_persons,
            "demoted_persons": demoted_persons,
            "total_entity_relations": total_relations,
            "verified_relations": verified_relations,
            "pending_relations": pending_relations,
            "demoted_relations": demoted_relations,
            "total_untraceable": len(untraceable_list),
        },
        "evidence_paths": evidence_paths,
        "untraceable_entities": untraceable_list,
    }

    return report_data


def generate_markdown_report(report: dict[str, Any]) -> str:
    """Format audit results as CLI Markdown report."""
    s = report["summary"]
    lines: list[str] = [
        "# 域准入历史数据审计报告 (Domain Admission Audit Report)",
        f"**审计时间**: {report['timestamp']}",
        "",
        "## 统计概要",
        f"- **人物实体总数**: {s['total_persons']}",
        f"  - **已验证 (Verified)**: {s['verified_persons']}",
        f"  - **待审核/降级 (Pending)**: {s['pending_persons']} (其中降级 {s['demoted_persons']} 个)",
        f"- **图关系总数**: {s['total_entity_relations']}",
        f"  - **已验证关系**: {s['verified_relations']}",
        f"  - **待审核/降级关系**: {s['pending_relations']} (其中降级 {s['demoted_relations']} 个)",
        f"- **无法追溯实体总数**: {s['total_untraceable']}",
        "",
        "## 证据路径样例 (Evidence Paths)",
    ]

    paths = list(report.get("evidence_paths", {}).items())[:10]
    if paths:
        for entity_id, path in paths:
            lines.append(f"- **{entity_id}**: `{' -> '.join(path)}`")
    else:
        lines.append("- (无可用的追溯路径)")

    lines.extend([
        "",
        "## 未追溯与降级列表 (Untraceable / Demoted List)",
    ])

    untraceable = report.get("untraceable_entities", [])
    if untraceable:
        lines.append("| 类型 | ID | 名称 | 原状态 | 现状态 | 原因 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in untraceable[:30]:  # Limit top 30 in CLI view
            lines.append(
                f"| {item['entity_type']} | {item['id']} | {item['name']} | "
                f"{item['previous_status']} | {item['current_status']} | {item['reason']} |"
            )
        if len(untraceable) > 30:
            lines.append(f"\n*注: 仅显示前 30 条记录，完整 {len(untraceable)} 条记录详见 JSON 审计报告。*")
    else:
        lines.append("- (所有实体与关系均满足 3 步锚点可达性要求)")

    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Domain Admission Invariants for HFB Database")
    parser.add_argument("--no-fix", action="store_true", help="Run audit in dry-run mode without mutating DB")
    parser.add_argument("--json-out", type=str, default="apps/backend/reports/domain_admission_audit_report.json")
    args = parser.parse_args()

    await init_database()
    try:
        async for session in get_session():
            report = await run_audit(session, fix=not args.no_fix)
            break

        md = generate_markdown_report(report)
        print("\n" + md + "\n")

        # Save JSON report
        output_path = os.path.abspath(args.json_out)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Audit report saved to: {output_path}")

    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
