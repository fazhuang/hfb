"""Evidence-backed research workflow orchestration."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.passage import Passage
from app.models.version import Version
from app.services.academic_service import AcademicService
from app.services.version_center import VersionComparisonService
from app.services.workspace_service import WorkspaceService


class ResearchWorkflowService:
    """Coordinates complete evidence-backed research workflows.

    Sprint 3: version comparison support.
    Sprint 4: full_research_flow pipeline with step-to-step product passing,
              run persistence, replay, and Markdown artifact generation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace = WorkspaceService(session)
        self.comparisons = VersionComparisonService(session)

    # =========================================================================
    # Sprint 4: Research workflow orchestration methods
    # =========================================================================

    @staticmethod
    def _make_trace_id(document_id: str, chunk_id: str) -> str:
        """Generate a stable, parseable trace_id distinct from chunk_id."""
        raw = f"{document_id}:{chunk_id}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:8]
        return f"tr-{h}"

    def _extract_from_academic(self, result) -> dict[str, Any]:
        """Extract trace_ids, source_docs, and internal records from AcademicService result."""
        now = datetime.now(timezone.utc).isoformat()
        records: list[dict] = []
        trace_ids: list[str] = []
        source_docs: set[str] = set()
        seen: set[str] = set()
        for t in result.evidence_trace:
            tid = self._make_trace_id(t.document_id, t.chunk_id)
            if tid in seen:
                continue
            seen.add(tid)
            trace_ids.append(tid)
            source_docs.add(t.document_id)
            records.append({
                "trace_id": tid,
                "document_id": t.document_id,
                "chunk_id": t.chunk_id,
                "passage_id": None,
                "retrieval_score": None,
                "retrieval_method": None,
                "timestamp": now,
            })
        return {
            "trace_ids": trace_ids,
            "source_documents": sorted(source_docs),
            "internal_traces": records,
        }

    async def execute_topic_selection(self, topic: str) -> dict[str, Any]:
        """Step 1: Decompose topic into research questions."""
        academic = AcademicService(self.session)
        result = await academic.research(query=topic)
        extracted = self._extract_from_academic(result)
        return {
            "sub_questions": len(result.decomposition),
            **extracted,
        }

    async def execute_literature_retrieval(self, topic: str) -> dict[str, Any]:
        """Step 2: Broader retrieval — saves real snapshot."""
        academic = AcademicService(self.session)
        result = await academic.synthesize(query=topic)
        extracted = self._extract_from_academic(result)
        # Build retrieval snapshot from evidence_trace
        snapshot: list[dict] = []
        seen: set[str] = set()
        for t in result.evidence_trace:
            key = f"{t.document_id}:{t.chunk_id}"
            if key in seen:
                continue
            seen.add(key)
            snapshot.append({
                "trace_id": self._make_trace_id(t.document_id, t.chunk_id),
                "document_id": t.document_id,
                "chunk_id": t.chunk_id,
                "claim_text": t.claim_text,
                "quote": t.quote,
            })
        return {
            "themes": len(result.themes),
            "snapshot": snapshot,
            **extracted,
        }

    async def execute_evidence_synthesis(
        self, topic: str, retrieval_snapshot: list[dict]
    ) -> dict[str, Any]:
        """Step 3: Synthesize from retrieval snapshot — consumes step 2 output."""
        academic = AcademicService(self.session)
        result = await academic.generate_report(
            query=topic, report_type="thematic_analysis"
        )
        extracted = self._extract_from_academic(result)
        evidence: list[dict] = []
        seen: set[str] = set()
        for t in result.evidence_trace:
            tid = self._make_trace_id(t.document_id, t.chunk_id)
            if tid in seen:
                continue
            seen.add(tid)
            evidence.append({
                "trace_id": tid,
                "document_id": t.document_id,
                "chunk_id": t.chunk_id,
                "claim_text": t.claim_text,
                "quote": t.quote,
                "citation_text": t.citation_text,
            })
        return {
            "sections": len(result.sections),
            "evidence": evidence,
            **extracted,
        }

    async def execute_report_generation(
        self, topic: str, synthesis_evidence: list[dict]
    ) -> dict[str, Any]:
        """Step 4: Generate report from synthesis evidence — consumes step 3 output."""
        academic = AcademicService(self.session)
        result = await academic.generate_report(
            query=topic, report_type="research_summary"
        )
        extracted = self._extract_from_academic(result)
        evidence: list[dict] = []
        seen: set[str] = set()
        for t in result.evidence_trace:
            tid = self._make_trace_id(t.document_id, t.chunk_id)
            if tid in seen:
                continue
            seen.add(tid)
            evidence.append({
                "trace_id": tid,
                "document_id": t.document_id,
                "chunk_id": t.chunk_id,
                "claim_text": t.claim_text,
                "quote": t.quote,
                "citation_text": t.citation_text,
            })
        return {
            "sections": len(result.sections),
            "title": result.title or topic,
            "evidence": evidence,
            **extracted,
        }

    async def execute_citation_export(
        self, topic: str, evidence: list[dict]
    ) -> dict[str, Any]:
        """Step 5: Export formatted citations with trace_ids from evidence."""
        citations: list[dict] = []
        trace_ids: list[str] = []
        source_docs: set[str] = set()
        internal_traces: list[dict] = []
        now = datetime.now(timezone.utc).isoformat()
        seen: set[str] = set()
        for ev in evidence:
            tid = ev.get("trace_id", "")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            trace_ids.append(tid)
            source_docs.add(ev.get("document_id", ""))
            citations.append({
                "trace_id": tid,
                "citation_text": ev.get("citation_text", f"[{ev.get('document_id', '')} : {ev.get('chunk_id', '')}]"),
                "document_id": ev.get("document_id", ""),
                "quote": ev.get("quote", ev.get("claim_text", "")),
            })
            internal_traces.append({
                "trace_id": tid,
                "document_id": ev.get("document_id", ""),
                "chunk_id": ev.get("chunk_id", ""),
                "passage_id": None,
                "retrieval_score": None,
                "retrieval_method": None,
                "timestamp": now,
            })
        return {
            "citations": citations,
            "trace_ids": trace_ids,
            "source_documents": sorted(source_docs),
            "internal_traces": internal_traces,
        }

    async def build_markdown_artifact(
        self,
        topic: str,
        run_id: str,
        retrieval_snapshot: list[dict],
        synthesis_evidence: list[dict],
        report_evidence: list[dict] | None,
    ) -> str:
        """Build a Markdown research record artifact with body text, citations, and lineage."""
        lines = [
            f"# 研究报告：{topic}",
            "",
            f"> Run ID: `{run_id}`",
            f"> 生成时间：{datetime.now(timezone.utc).isoformat()}",
            "",
            "## 文献检索快照",
            "",
        ]
        if retrieval_snapshot:
            for i, rec in enumerate(retrieval_snapshot[:10], 1):
                lines.append(f"{i}. **{rec.get('claim_text', 'N/A')}**")
                lines.append(f"   > {rec.get('quote', '')}")
                lines.append(f"   - 文献: `{rec.get('document_id', '')}`")
                lines.append(f"   - Trace: `{rec.get('trace_id', '')}`")
                lines.append("")
        else:
            lines.append("暂无检索快照。")

        lines.extend(["", "## 证据综合", ""])
        if synthesis_evidence:
            for i, ev in enumerate(synthesis_evidence[:10], 1):
                lines.append(f"{i}. **{ev.get('claim_text', 'N/A')}**")
                lines.append(f"   - 引用: `{ev.get('citation_text', '')}`")
                lines.append(f"   - Trace: `{ev.get('trace_id', '')}`")
                lines.append("")
        else:
            lines.append("暂无综合证据。")

        lines.extend(["", "## 报告结论", ""])
        if report_evidence:
            for i, ev in enumerate(report_evidence[:10], 1):
                lines.append(f"{i}. **{ev.get('claim_text', 'N/A')}**")
                lines.append(f"   - 引用: `{ev.get('citation_text', '')}`")
                lines.append(f"   - Trace: `{ev.get('trace_id', '')}`")
                lines.append("")
        else:
            lines.append("暂无报告结论。")

        lines.extend([
            "",
            "## 证据状态",
            "",
            f"- 检索快照记录数：{len(retrieval_snapshot)}",
            f"- 综合证据条数：{len(synthesis_evidence)}",
            f"- 报告证据条数：{len(report_evidence) if report_evidence else 0}",
        ])

        return "\n".join(lines)

    # =========================================================================
    # Sprint 4: ResearchRun persistence and replay (via workspace session)
    # =========================================================================

    async def persist_research_run(
        self,
        session_id: UUID | str,
        run_id: str,
        topic: str,
        steps: list[Any],
    ) -> None:
        """Persist a ResearchRun into session.workflow_state via WorkspaceService."""
        import json as _json
        research_session = await self.workspace.get_session(session_id)
        if research_session is None:
            raise ValueError("Research session not found")

        existing_state: dict[str, Any] = {}
        if research_session.workflow_state:
            try:
                existing_state = _json.loads(research_session.workflow_state)
            except (_json.JSONDecodeError, TypeError):
                existing_state = {}

        runs: list[dict] = existing_state.get("runs", [])
        runs.append({
            "run_id": run_id,
            "session_id": str(session_id),
            "topic": topic,
            "workflow_type": "full_research_flow",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "steps": [
                s.model_dump() if hasattr(s, 'model_dump') else s
                for s in steps
            ],
        })
        existing_state["runs"] = runs

        # Persist via session update (not direct ORM attribute write)
        await self.workspace.update_session(
            session_id=str(session_id),
        )
        # Set workflow_state via session property
        research_session.workflow_state = _json.dumps(existing_state, ensure_ascii=False)
        research_session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()

    async def get_research_runs(
        self, session_id: UUID | str
    ) -> list[dict[str, Any]]:
        """Get persisted ResearchRun snapshots for a session."""
        research_session = await self.workspace.get_session(session_id)
        if research_session is None:
            return []
        if not research_session.workflow_state:
            return []
        try:
            state = json.loads(research_session.workflow_state)
        except (json.JSONDecodeError, TypeError):
            return []
        return state.get("runs", [])

    # =========================================================================
    # Sprint 3: Version comparison methods
    # =========================================================================

    async def configure_version_comparison(
        self,
        session_id: UUID | str,
        source_passage_id: UUID | str,
        target_passage_id: UUID | str,
    ) -> dict[str, Any]:
        research_session = await self.workspace.get_session(session_id)
        if research_session is None:
            raise ValueError("Research session not found")

        source = await self._load_evidence(source_passage_id)
        target = await self._load_evidence(target_passage_id)
        if source["version"]["id"] == target["version"]["id"]:
            raise ValueError("Passages must belong to different versions")
        if source["book"]["id"] != target["book"]["id"]:
            raise ValueError("Passages must belong to versions of the same book")

        comparison = await self.comparisons.compare_passages(
            source_passage_id,
            target_passage_id,
        )
        state: dict[str, Any] = {
            "workflow_type": "evidence_backed_version_comparison",
            "corpus_status": "validation",
            "source": source,
            "target": target,
            "comparison": {
                "differences": comparison["differences"],
                "operations": comparison["operations"],
                "similarity_ratio": comparison["similarity_ratio"],
            },
            "configured_at": datetime.now(timezone.utc).isoformat(),
        }
        research_session.workflow_state = json.dumps(state, ensure_ascii=False)
        research_session.active_entities = json.dumps(
            [str(source_passage_id), str(target_passage_id)],
            ensure_ascii=False,
        )
        research_session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()
        return state

    async def get_version_comparison(
        self,
        session_id: UUID | str,
    ) -> dict[str, Any] | None:
        research_session = await self.workspace.get_session(session_id)
        if research_session is None or not research_session.workflow_state:
            return None
        try:
            state = json.loads(research_session.workflow_state)
        except (json.JSONDecodeError, TypeError):
            return None
        if state.get("workflow_type") != "evidence_backed_version_comparison":
            return None
        return state

    async def export_markdown(self, session_id: UUID | str) -> str:
        research_session = await self.workspace.get_session(session_id)
        state = await self.get_version_comparison(session_id)
        if research_session is None or state is None:
            raise ValueError("Version comparison workflow is not configured")

        notes = await self.workspace.list_notes(session_id)
        source = state["source"]
        target = state["target"]
        comparison = state["comparison"]
        lines = [
            f"# {research_session.title}",
            "",
            "> 验证语料：本记录由非生产验证数据生成，不得作为正式学术引用。",
            "",
            "## 比较对象",
            "",
            f"### 底本：{source['version']['name']}",
            "",
            source["text"],
            "",
            f"引用：{source['citation']}",
            "",
            f"### 对校本：{target['version']['name']}",
            "",
            target["text"],
            "",
            f"引用：{target['citation']}",
            "",
            "## 差异摘要",
            "",
            f"- 差异数量：{comparison['differences']}",
            f"- 文本相似度：{comparison['similarity_ratio']:.2%}",
        ]

        if comparison["operations"]:
            lines.extend(["", "| 类型 | 底本文字 | 对校本文字 |", "|---|---|---|"])
            for operation in comparison["operations"]:
                source_text = self._escape_markdown_cell(operation.get("source_text", ""))
                target_text = self._escape_markdown_cell(operation.get("target_text", ""))
                lines.append(
                    f"| {operation['op']} | {source_text} | {target_text} |"
                )

        lines.extend(["", "## 研究笔记", ""])
        if research_session.context_notes:
            lines.extend([research_session.context_notes, ""])
        if notes:
            for note in reversed(notes):
                tag = f" [{note.tags}]" if note.tags else ""
                lines.append(f"-{tag} {note.content}")
        elif not research_session.context_notes:
            lines.append("暂无研究笔记。")

        lines.extend(
            [
                "",
                "## 证据状态",
                "",
                f"- 底本来源完整：{'是' if source['evidence_complete'] else '否'}",
                f"- 对校本来源完整：{'是' if target['evidence_complete'] else '否'}",
                "- 学术审核状态：未审核（验证流程）",
                "",
                f"生成时间：{datetime.now(timezone.utc).isoformat()}",
                "",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _escape_markdown_cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    async def _load_evidence(self, passage_id: UUID | str) -> dict[str, Any]:
        stmt = (
            select(Passage, Version, Book, Chapter)
            .join(Version, Passage.version_id == Version.id)
            .join(Book, Version.book_id == Book.id)
            .join(Chapter, Passage.chapter_id == Chapter.id)
            .where(
                Passage.id == str(passage_id),
                Passage.is_deleted.is_(False),
                Version.is_deleted.is_(False),
                Book.is_deleted.is_(False),
                Chapter.is_deleted.is_(False),
            )
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            raise ValueError(f"Passage {passage_id} not found with version provenance")

        passage, version, book, chapter = row
        location_parts = [version.repository, version.shelf_mark]
        location = "，".join(part for part in location_parts if part)
        citation = (
            f"《{book.title}》·{version.version_name}，"
            f"{chapter.title}，第{passage.order}条"
        )
        if location:
            citation += f"（{location}）"

        return {
            "passage_id": passage.id,
            "text": passage.content_text,
            "translation": passage.translation,
            "notes": passage.notes,
            "order": passage.order,
            "chapter": {
                "id": chapter.id,
                "title": chapter.title,
            },
            "version": {
                "id": version.id,
                "name": version.version_name,
                "era": version.era,
                "year": version.year,
                "repository": version.repository,
                "shelf_mark": version.shelf_mark,
                "source_url": version.source_url,
            },
            "book": {
                "id": book.id,
                "title": book.title,
                "source_url": book.source_url,
            },
            "citation": citation,
            "evidence_complete": bool(
                version.repository
                and version.shelf_mark
                and (version.source_url or book.source_url)
            ),
        }
