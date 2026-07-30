"""PaperService — assemble 8-module structured academic papers.

Phase 2c: Zero-LLM paper generation. All text comes from template filling
or raw data. Every claim traces to a source citation + evidence_level.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.conflict_detector import ConflictDetector
from app.services.graph_service import GraphService


class PaperService:
    """Generate structured academic papers from KG + TEI data."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.graph_svc = GraphService(session)

    async def generate_paper(
        self,
        source_type: str,
        source_id: str,
        target_type: str | None = None,
        target_id: str | None = None,
        relation_types: list[str] | None = None,
        min_evidence_level: int = 2,
        max_hops: int = 5,
    ) -> dict:
        """Generate a full 8-module academic paper.

        Returns:
            dict with keys: paper_id, generated_at, query, modules (JSON),
            markdown (str)
        """
        # Phase 1: Evidence collection
        paths = await self.graph_svc.multi_hop_query(
            source_type=source_type, source_id=source_id,
            target_type=target_type, target_id=target_id,
            min_evidence_level=min_evidence_level, max_hops=max_hops,
            relation_types=relation_types,
        )

        # Collect all unique version IDs
        all_version_ids: set[str] = set()
        for path in paths:
            for hop in path.hops:
                all_version_ids.add(hop.source_id if hop.source_type == "version" else "")
                all_version_ids.add(hop.target_id if hop.target_type == "version" else "")

        all_version_ids.discard("")

        # Phase 2: TEI enrichment (placeholder)
        for path in paths:
            for hop in path.hops:
                if hop.evidence_level >= 3:
                    # Collect variants and commentaries for all passage refs
                    # (evidence_passage_id is inside the citation, extract if needed)
                    pass

        # Phase 3: Conflict detection
        conflicts = await ConflictDetector.detect(self.session, paths)

        # Phase 4: Assemble 8 modules
        modules = self._assemble_modules(
            source_type=source_type, source_id=source_id,
            target_type=target_type, target_id=target_id,
            paths=paths, version_ids=all_version_ids,
            conflicts=conflicts, min_evidence_level=min_evidence_level,
            max_hops=max_hops, relation_types=relation_types,
        )

        # Phase 5: Generate output
        paper_data = {
            "source_type": source_type,
            "source_id": source_id,
            "target_type": target_type,
            "target_id": target_id,
            "min_evidence_level": min_evidence_level,
            "max_hops": max_hops,
            "relation_types": relation_types,
        }
        paper_json = json.dumps(paper_data, ensure_ascii=False, sort_keys=True, default=str)
        paper_id = hashlib.sha256(paper_json.encode()).hexdigest()

        markdown = self._render_markdown(modules, source_type, source_id, target_type, target_id)

        return {
            "paper_id": paper_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "query": {
                "source_type": source_type,
                "source_id": source_id,
                "target_type": target_type,
                "target_id": target_id,
            },
            "modules": modules,
            "markdown": markdown,
        }

    def _assemble_modules(
        self, source_type, source_id, target_type, target_id,
        paths, version_ids, conflicts, min_evidence_level, max_hops,
        relation_types,
    ) -> dict:
        """Assemble 8 paper modules from evidence data."""
        # Module 1: Title
        title = f"{source_type}:{source_id} 的学术证据链分析"
        if target_type and target_id:
            title = f"{source_type}:{source_id} 与 {target_type}:{target_id}：基于证据链的学术分析"

        # Module 2: Abstract (data summary)
        max_level = max((p.min_evidence_level for p in paths), default=0)
        avg_confidence = sum(p.total_confidence for p in paths) / max(len(paths), 1)

        # Collect unique versions
        unique_versions: set[str] = set()
        for p in paths:
            for h in p.hops:
                unique_versions.add(h.citation)

        abstract = {
            "path_count": len(paths),
            "version_count": len(unique_versions),
            "variant_count": 0,  # populated by TEI enricher
            "commentary_count": 0,
            "max_evidence_level": max_level,
            "avg_confidence": round(avg_confidence, 4),
        }

        # Module 3: Literature basis
        literature_basis = []
        for vid in sorted(version_ids):
            literature_basis.append({"version_id": vid, "name": vid})

        # Module 4: Evidence chains
        evidence_chains = []
        for path in paths:
            chain = {"path_id": path.path_id, "hops": [], "total_confidence": path.total_confidence}
            for hop in path.hops:
                chain["hops"].append({
                    "source": f"{hop.source_type}:{hop.source_id}",
                    "target": f"{hop.target_type}:{hop.target_id}",
                    "relation": hop.relation_type,
                    "evidence_level": hop.evidence_level,
                    "confidence_score": hop.confidence_score,
                    "citation": hop.citation,
                    "exact_quote": hop.exact_quote,
                    "source_uri": hop.source_uri,
                })
            evidence_chains.append(chain)

        # Module 5: Variant appendix (placeholder — filled by TEI enricher)
        variant_appendix: list[dict] = []

        # Module 6: Literature review (co-occurrence from KG)
        literature_review = {"nodes": [], "edges": []}

        # Module 7: Discussion (conflicts)
        discussion = {
            "conflicts": [
                {
                    "type": c.conflict_type,
                    "description": c.description,
                    "severity": c.severity,
                    "affected_path_ids": c.affected_path_ids,
                }
                for c in conflicts
            ]
        }

        # Module 8: Methodology
        methodology = {
            "query_parameters": {
                "source_type": source_type, "source_id": source_id,
                "target_type": target_type, "target_id": target_id,
                "min_evidence_level": min_evidence_level,
                "max_hops": max_hops,
                "relation_types": relation_types,
            },
            "generated_at": datetime.now(UTC).isoformat(),
            "evidence_level_distribution": {
                "L2": sum(1 for p in paths for h in p.hops if h.evidence_level == 2),
                "L3": sum(1 for p in paths for h in p.hops if h.evidence_level == 3),
                "L4": sum(1 for p in paths for h in p.hops if h.evidence_level == 4),
            },
            "filters_applied": [],
        }

        return {
            "title": title,
            "abstract": abstract,
            "literature_basis": literature_basis,
            "evidence_chains": evidence_chains,
            "variant_appendix": variant_appendix,
            "literature_review": literature_review,
            "discussion": discussion,
            "methodology": methodology,
        }

    @staticmethod
    def _render_markdown(
        modules: dict,
        source_type: str,
        source_id: str,
        target_type: str | None,
        target_id: str | None,
    ) -> str:
        """Render 8 modules as Markdown."""
        lines: list[str] = []

        # Title
        lines.append(f"# {modules['title']}")
        lines.append("")

        # Abstract
        a = modules["abstract"]
        lines.append("## 摘要")
        lines.append(f"共发现 **{a['path_count']}** 条证据路径，涉及 **{a['version_count']}** 个文献版本。")
        lines.append(f"最高证据等级 **L{a['max_evidence_level']}**，平均置信度 **{a['avg_confidence']:.4f}**。")
        lines.append("")

        # Literature Basis
        lines.append("## 文献基础")
        for v in modules.get("literature_basis", []):
            lines.append(f"- {v['name']}")
        lines.append("")

        # Evidence Chains
        lines.append("## 证据链")
        for i, chain in enumerate(modules.get("evidence_chains", []), 1):
            lines.append(f"### 路径 {i} (置信度: {chain['total_confidence']:.4f})")
            for j, hop in enumerate(chain["hops"], 1):
                lines.append(f"**跳步 {j}**: {hop['source']} --[{hop['relation']}]--> {hop['target']}")
                lines.append(f"- 证据等级: L{hop['evidence_level']} (置信度: {hop['confidence_score']})")
                lines.append(f"- 引用: {hop['citation']}")
                if hop["exact_quote"]:
                    lines.append(f"- 原文: 「{hop['exact_quote']}」")
                if hop["source_uri"]:
                    lines.append(f"- 来源: {hop['source_uri']}")
                lines.append("")
            lines.append("")

        # Variant Appendix
        lines.append("## 异文附录")
        lines.append("（无 L4 级别异文证据）" if not modules.get("variant_appendix") else "")
        lines.append("")

        # Literature Review
        lines.append("## 学术史回顾")
        lines.append("（共现图谱数据见 JSON 输出）")
        lines.append("")

        # Discussion
        lines.append("## 讨论与冲突检测")
        discussion = modules.get("discussion", {})
        for c in discussion.get("conflicts", []):
            lines.append(f"- **[{c['type']}]** {c['description']} (严重度: {c['severity']})")
        if not discussion.get("conflicts"):
            lines.append("未检测到证据冲突。")
        lines.append("")

        # Methodology
        lines.append("## 方法论附注")
        m = modules["methodology"]
        lines.append(f"- 查询时间: {m['generated_at']}")
        lines.append(f"- 最低证据等级: L{m['query_parameters']['min_evidence_level']}")
        lines.append(f"- 最大跳数: {m['query_parameters']['max_hops']}")
        dist = m.get("evidence_level_distribution", {})
        lines.append(f"- 证据等级分布: L2={dist.get('L2', 0)}, L3={dist.get('L3', 0)}, L4={dist.get('L4', 0)}")
        lines.append("")

        return "\n".join(lines)
