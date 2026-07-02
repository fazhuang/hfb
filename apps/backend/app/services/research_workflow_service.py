"""Evidence-backed research workflow orchestration.

Sprint 4 P0: Deterministic step-to-step pipeline. Synthesis consumes retrieval
snapshot. Report consumes synthesis output. No re-retrieval after step 2.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.academic_service import AcademicService
from app.services.trace_lineage import (
    InternalTraceRecord,
    build_internal_traces,
    extract_source_documents,
    extract_trace_ids,
    make_trace_id,
)
from app.services.workspace_service import WorkspaceService


class ResearchWorkflowService:
    """Coordinates evidence-backed research workflows.

    Sprint 4 P0: step-to-step pipeline with deterministic composition.
    Steps 3-5 consume prior step output, never re-retrieve.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace = WorkspaceService(session)

    # =========================================================================
    # Step 1: Topic Selection
    # =========================================================================

    async def execute_topic_selection(self, topic: str) -> dict[str, Any]:
        """Step 1: Decompose topic into research questions via AcademicService."""
        academic = AcademicService(self.session)
        result = await academic.research(query=topic)
        return await _pack_academic_step(result, topic)

    # =========================================================================
    # Step 2: Literature Retrieval — produces immutable snapshot
    # =========================================================================

    async def execute_literature_retrieval(self, topic: str) -> dict[str, Any]:
        """Step 2: Build immutable retrieval snapshot from AcademicService.

        This snapshot is the sole evidence source for all downstream steps.
        """
        academic = AcademicService(self.session)
        result = await academic.synthesize(query=topic)
        snapshot, internal_traces = _build_retrieval_snapshot(result)
        return {
            "result": {"themes": len(result.themes), "records": len(snapshot)},
            "snapshot": snapshot,
            "trace_ids": _snapshot_trace_ids(snapshot),
            "source_documents": _snapshot_source_docs(snapshot),
            "internal_traces": internal_traces,
        }

    # =========================================================================
    # Step 3: Evidence Synthesis — purely from snapshot, NO re-retrieval
    # =========================================================================

    def execute_evidence_synthesis_from_snapshot(
        self, topic: str, snapshot: list[dict]
    ) -> dict[str, Any]:
        """Step 3: Synthesize evidence purely from the retrieval snapshot.

        Does NOT call AcademicService. Uses deterministic claim grouping.
        Only uses verified claims, quotes, and citations already in the snapshot.
        """
        if not snapshot:
            raise ValueError("Empty retrieval snapshot — cannot synthesize")

        # Group claims by shared concept keywords
        sections = _group_snapshot_into_sections(snapshot)
        evidence = _snapshot_to_evidence_list(snapshot)

        now = datetime.now(timezone.utc).isoformat()
        internal_traces = [
            InternalTraceRecord(
                trace_id=r["trace_id"],
                document_id=r["document_id"],
                chunk_id=r["chunk_id"],
                passage_id="",
                retrieval_score=0.0,
                retrieval_method="deterministic_synthesis_from_snapshot",
                timestamp=now,
            )
            for r in snapshot
        ]

        return {
            "result": {"sections": len(sections), "claims": len(evidence)},
            "sections": sections,
            "evidence": evidence,
            "trace_ids": _snapshot_trace_ids(snapshot),
            "source_documents": _snapshot_source_docs(snapshot),
            "internal_traces": internal_traces,
        }

    # =========================================================================
    # Step 4: Report Generation — purely from synthesis, NO re-retrieval
    # =========================================================================

    def execute_report_from_synthesis(
        self, topic: str, synthesis_output: dict
    ) -> dict[str, Any]:
        """Step 4: Generate report purely from synthesis evidence.

        Does NOT call AcademicService. Composes sections from synthesis evidence.
        """
        evidence = synthesis_output.get("evidence", [])
        sections = synthesis_output.get("sections", [])
        if not evidence and not sections:
            raise ValueError("Empty synthesis evidence — cannot generate report")

        report_sections = _build_report_sections(topic, evidence, sections)

        now = datetime.now(timezone.utc).isoformat()
        internal_traces = [
            InternalTraceRecord(
                trace_id=r["trace_id"],
                document_id=r["document_id"],
                chunk_id=r["chunk_id"],
                passage_id="",
                retrieval_score=0.0,
                retrieval_method="deterministic_report_from_synthesis",
                timestamp=now,
            )
            for r in evidence
        ]

        trace_ids = list({r["trace_id"] for r in evidence})
        source_docs = sorted(set(r["document_id"] for r in evidence))

        return {
            "result": {
                "sections": len(report_sections),
                "title": f"研究报告：{topic}",
            },
            "sections": report_sections,
            "evidence": evidence,
            "trace_ids": trace_ids,
            "source_documents": source_docs,
            "internal_traces": internal_traces,
        }

    # =========================================================================
    # Step 5: Citation Export — from evidence list
    # =========================================================================

    def execute_citation_export_from_evidence(
        self, topic: str, evidence: list[dict]
    ) -> dict[str, Any]:
        """Step 5: Export formatted citations from evidence list."""
        if not evidence:
            raise ValueError("No evidence to export citations from")

        citations: list[dict] = []
        trace_ids: list[str] = []
        source_docs: set[str] = set()
        now = datetime.now(timezone.utc).isoformat()
        internal_traces: list[InternalTraceRecord] = []
        seen: set[str] = set()

        for ev in evidence:
            tid = ev.get("trace_id", "")
            doc_id = ev.get("document_id", "")
            chk_id = ev.get("chunk_id", "")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            trace_ids.append(tid)
            source_docs.add(doc_id)
            citation_text = ev.get("citation_text", ev.get("quote", f"[{doc_id}:{chk_id}]"))
            citations.append({
                "trace_id": tid,
                "citation_text": citation_text,
                "document_id": doc_id,
                "quote": ev.get("quote", ev.get("claim_text", "")),
            })
            internal_traces.append(InternalTraceRecord(
                trace_id=tid,
                document_id=doc_id,
                chunk_id=chk_id,
                passage_id="",
                retrieval_score=0.0,
                retrieval_method="deterministic_citation_export",
                timestamp=now,
            ))

        return {
            "result": {"total_citations": len(citations), "citations": citations},
            "trace_ids": trace_ids,
            "source_documents": sorted(source_docs),
            "internal_traces": internal_traces,
        }

    # =========================================================================
    # Markdown artifact — full, not truncated
    # =========================================================================

    def build_markdown_artifact(
        self,
        topic: str,
        run_id: str,
        steps: list[Any],
        retrieval_snapshot: list[dict],
        synthesis_output: dict,
    ) -> str:
        """Build complete Markdown research record artifact."""
        now = datetime.now(timezone.utc).isoformat()
        lines = [
            f"# 研究报告：{topic}",
            "",
            f"> **Run ID**: `{run_id}`",
            f"> **生成时间**: {now}",
            "> **工作流类型**: full_research_flow",
            "",
            "---",
            "",
            "## 执行步骤",
            "",
        ]

        for step in steps:
            status_icon = "✅" if getattr(step, 'status', None) == "completed" else "❌"
            name = getattr(step, 'name', 'unknown')
            lines.append(f"- {status_icon} **{name}**")

        lines.extend(["", "---", "", "## 文献检索快照", ""])

        if retrieval_snapshot:
            for i, rec in enumerate(retrieval_snapshot[:20], 1):
                lines.append(f"### {i}. {rec.get('claim_text', 'N/A')[:80]}")
                lines.append(f"> {rec.get('quote', '')[:200]}")
                lines.append(f"- 文献: `{rec.get('document_id', '')}`")
                lines.append(f"- Trace: `{rec.get('trace_id', '')}`")
                lines.append("")
        else:
            lines.append("_暂无检索快照_")

        lines.extend(["", "---", "", "## 证据综合", ""])

        evidence = synthesis_output.get("evidence", [])
        sections = synthesis_output.get("sections", [])
        if sections:
            for section in sections:
                lines.append(f"### {section.get('heading', 'Untitled')}")
                lines.append(section.get("body", ""))
                lines.append("")
                for ref in section.get("references", []):
                    lines.append(f"- Trace: `{ref}`")
                lines.append("")
        elif evidence:
            for i, ev in enumerate(evidence[:20], 1):
                lines.append(f"### {i}. {ev.get('claim_text', 'N/A')[:80]}")
                lines.append(f"- 引用: `{ev.get('citation_text', '')}`")
                lines.append(f"- Trace: `{ev.get('trace_id', '')}`")
                lines.append("")

        lines.extend([
            "",
            "---",
            "",
            "## 证据状态",
            "",
            f"- 检索快照记录数: {len(retrieval_snapshot)}",
            f"- 综合证据条数: {len(evidence)}",
            f"- 报告段落数: {len(sections)}",
            "",
            "---",
            "",
            "*本报告由 HFB V4 研究门户自动生成。所有内容均来源于已索引语料。*",
        ])

        return "\n".join(lines)

    # =========================================================================
    # ResearchRun persistence and replay
    # =========================================================================

    async def persist_research_run(
        self,
        session_id: UUID | str,
        run_id: str,
        topic: str,
        workflow_type: str = "full_research_flow",
        steps: list[Any] | None = None,
        output_artifacts: dict[str, Any] | None = None,
    ) -> None:
        """Persist a complete ResearchRun in session.workflow_state."""
        research_session = await self.workspace.get_session(session_id)
        if research_session is None:
            raise ValueError("Research session not found")

        existing_state: dict[str, Any] = {}
        if research_session.workflow_state:
            try:
                existing_state = json.loads(research_session.workflow_state)
            except (json.JSONDecodeError, TypeError):
                existing_state = {}

        runs: list[dict] = existing_state.get("runs", [])

        run_record = {
            "run_id": run_id,
            "session_id": str(session_id),
            "workflow_type": workflow_type,
            "topic": topic,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "step_execution_trace": [
                {
                    "step_name": s.name if hasattr(s, 'name') else s.get("name", ""),
                    "status": s.status if hasattr(s, 'status') else s.get("status", ""),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "trace_ids": (
                        s.trace_ids if hasattr(s, 'trace_ids')
                        else s.get("trace_ids", [])
                    ),
                }
                for s in (steps or [])
            ],
            "output_artifacts": output_artifacts or {},
        }
        runs.append(run_record)
        existing_state["runs"] = runs

        research_session.workflow_state = json.dumps(existing_state, ensure_ascii=False)
        research_session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()

    async def get_research_runs(
        self, session_id: UUID | str
    ) -> list[dict[str, Any]]:
        """Get persisted ResearchRun snapshots (immutable replay)."""
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
    # Sprint 3 compat — version comparison (restored from 6eaafa5)
    # =========================================================================

    async def configure_version_comparison(
        self,
        session_id: UUID | str,
        source_passage_id: UUID | str,
        target_passage_id: UUID | str,
    ) -> dict[str, Any]:
        from app.services.version_center import VersionComparisonService
        comparisons = VersionComparisonService(self.session)
        research_session = await self.workspace.get_session(session_id)
        if research_session is None:
            raise ValueError("Research session not found")

        source = await self._load_evidence(source_passage_id)
        target = await self._load_evidence(target_passage_id)
        if source["version"]["id"] == target["version"]["id"]:
            raise ValueError("Passages must belong to different versions")
        if source["book"]["id"] != target["book"]["id"]:
            raise ValueError("Passages must belong to versions of the same book")

        comparison = await comparisons.compare_passages(
            source_passage_id, target_passage_id,
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
            [str(source_passage_id), str(target_passage_id)], ensure_ascii=False,
        )
        research_session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()
        return state

    async def get_version_comparison(
        self, session_id: UUID | str,
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
                lines.append(f"| {operation['op']} | {source_text} | {target_text} |")

        lines.extend(["", "## 研究笔记", ""])
        if research_session.context_notes:
            lines.extend([research_session.context_notes, ""])
        if notes:
            for note in reversed(notes):
                tag = f" [{note.tags}]" if note.tags else ""
                lines.append(f"-{tag} {note.content}")
        elif not research_session.context_notes:
            lines.append("暂无研究笔记。")

        lines.extend([
            "",
            "## 证据状态",
            "",
            f"- 底本来源完整：{'是' if source['evidence_complete'] else '否'}",
            f"- 对校本来源完整：{'是' if target['evidence_complete'] else '否'}",
            "- 学术审核状态：未审核（验证流程）",
            "",
            f"生成时间：{datetime.now(timezone.utc).isoformat()}",
            "",
        ])
        return "\n".join(lines)

    @staticmethod
    def _escape_markdown_cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    async def _load_evidence(self, passage_id: UUID | str) -> dict[str, Any]:
        from sqlalchemy import select as sql_select
        from app.models.book import Book
        from app.models.chapter import Chapter
        from app.models.passage import Passage as PassageModel
        from app.models.version import Version as VersionModel
        stmt = (
            sql_select(PassageModel, VersionModel, Book, Chapter)
            .join(VersionModel, PassageModel.version_id == VersionModel.id)
            .join(Book, VersionModel.book_id == Book.id)
            .join(Chapter, PassageModel.chapter_id == Chapter.id)
            .where(
                PassageModel.id == str(passage_id),
                PassageModel.is_deleted.is_(False),
                VersionModel.is_deleted.is_(False),
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
            "chapter": {"id": chapter.id, "title": chapter.title},
            "version": {
                "id": version.id, "name": version.version_name,
                "era": version.era, "year": version.year,
                "repository": version.repository, "shelf_mark": version.shelf_mark,
                "source_url": version.source_url,
            },
            "book": {
                "id": book.id, "title": book.title,
                "source_url": book.source_url,
            },
            "citation": citation,
            "evidence_complete": bool(
                version.repository and version.shelf_mark
                and (version.source_url or book.source_url)
            ),
        }


# =============================================================================
# Deterministic composition helpers — no AcademicService dependency
# =============================================================================


def _build_retrieval_snapshot(result) -> tuple[list[dict], list[InternalTraceRecord]]:
    """Build immutable retrieval snapshot from AcademicService result."""
    snapshot: list[dict] = []
    internal_traces: list[InternalTraceRecord] = []
    seen: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()

    for t in result.evidence_trace:
        tid = make_trace_id(t.document_id, t.chunk_id)
        key = f"{t.document_id}:{t.chunk_id}"
        if key in seen:
            continue
        seen.add(key)
        entry = {
            "trace_id": tid,
            "document_id": t.document_id,
            "chunk_id": t.chunk_id,
            "claim_text": t.claim_text,
            "quote": t.quote,
            "citation_text": t.citation_text,
        }
        snapshot.append(entry)
        internal_traces.append(InternalTraceRecord(
            trace_id=tid,
            document_id=t.document_id,
            chunk_id=t.chunk_id,
            passage_id="",
            retrieval_score=0.0,
            retrieval_method="academic_service",
            timestamp=now,
        ))

    return snapshot, internal_traces


def _snapshot_trace_ids(snapshot: list[dict]) -> list[str]:
    return sorted(set(r["trace_id"] for r in snapshot))


def _snapshot_source_docs(snapshot: list[dict]) -> list[str]:
    return sorted(set(r["document_id"] for r in snapshot))


def _group_snapshot_into_sections(snapshot: list[dict]) -> list[dict]:
    """Deterministic grouping: one section per document."""
    sections: dict[str, dict] = {}
    for r in snapshot:
        doc_id = r["document_id"]
        if doc_id not in sections:
            sections[doc_id] = {
                "heading": f"来源文献: {doc_id}",
                "body": "",
                "references": [],
            }
        sections[doc_id]["body"] += f"- {r['claim_text']}\n"
        sections[doc_id]["references"].append(r["trace_id"])
    return list(sections.values())


def _snapshot_to_evidence_list(snapshot: list[dict]) -> list[dict]:
    """Convert snapshot entries to evidence dicts. Pure transform, no retrieval."""
    return [
        {
            "trace_id": r["trace_id"],
            "document_id": r["document_id"],
            "chunk_id": r["chunk_id"],
            "claim_text": r["claim_text"],
            "quote": r["quote"],
            "citation_text": r["citation_text"],
        }
        for r in snapshot
    ]


def _build_report_sections(
    topic: str, evidence: list[dict], sections: list[dict]
) -> list[dict]:
    """Build report sections from synthesis evidence. Pure composition."""
    if sections:
        return sections

    # Fallback: build sections from evidence
    doc_groups: dict[str, list[dict]] = {}
    for ev in evidence:
        doc_id = ev.get("document_id", "unknown")
        doc_groups.setdefault(doc_id, []).append(ev)

    report = []
    for doc_id, evs in doc_groups.items():
        body_lines = []
        refs = []
        for ev in evs:
            body_lines.append(f"- {ev.get('claim_text', '')}")
            if ev.get('citation_text'):
                body_lines.append(f"  引用: {ev['citation_text']}")
            refs.append(ev.get("trace_id", ""))
        report.append({
            "heading": f"文献 {doc_id}",
            "body": "\n".join(body_lines),
            "references": [r for r in refs if r],
        })

    return report


async def _pack_academic_step(result, topic: str) -> dict[str, Any]:
    """Pack AcademicService result into step output dict."""
    traces = build_internal_traces(result.evidence_trace)
    return {
        "result": {
            "topic": topic,
            "sub_questions": len(result.decomposition),
        },
        "trace_ids": extract_trace_ids(result.evidence_trace),
        "source_documents": extract_source_documents(result.evidence_trace),
        "internal_traces": traces,
    }
