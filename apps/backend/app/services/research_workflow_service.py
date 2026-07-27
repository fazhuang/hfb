"""Evidence-backed research workflow orchestration.

Sprint 4 P0: step-to-step pipeline with immutable trace passing.
Synthesis/report/citation-export never re-retrieve, never reconstruct traces.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.academic_service import AcademicService
from app.services.trace_lineage import (
    InternalTraceRecord,
    build_internal_traces,
    extract_trace_ids,
    extract_source_documents,
    make_trace_id,
)
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


class ResearchWorkflowService:
    """Coordinates evidence-backed research workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace = WorkspaceService(session)

    # =========================================================================
    # Step 1: Topic Selection
    # =========================================================================

    async def execute_topic_selection(self, topic: str) -> dict[str, Any]:
        academic = AcademicService(self.session)
        result = await academic.research(query=topic)
        return await _pack_academic_step(
            self.session, result, topic,
            retrieval_snapshot=academic.last_snapshot,
        )

    # =========================================================================
    # Step 2: Literature Retrieval — produces immutable snapshot + traces
    # =========================================================================

    async def execute_literature_retrieval(self, topic: str) -> dict[str, Any]:
        academic = AcademicService(self.session)
        result = await academic.synthesize(query=topic)
        snapshot, internal_traces = await _build_retrieval_snapshot(
            self.session, result,
            retrieval_snapshot=academic.last_snapshot,
        )
        # Immutable traces — downstream steps pass these exact records
        return {
            "result": {"themes": len(result.themes), "records": len(snapshot)},
            "snapshot": snapshot,
            "trace_ids": [r.trace_id for r in internal_traces],
            "source_documents": sorted(set(r.document_id for r in internal_traces)),
            "internal_traces": internal_traces,
        }

    # =========================================================================
    # Step 3: Evidence Synthesis — consumes snapshot, passes traces thru
    # =========================================================================

    def execute_evidence_synthesis_from_snapshot(
        self, topic: str, snapshot: list[dict],
        internal_traces: list[InternalTraceRecord] | None = None,
    ) -> dict[str, Any]:
        """Build evidence synthesis from a retrieval snapshot.

        Returns an empty synthesis (0 sections / 0 claims) when the snapshot is
        empty, so the workflow can complete a no-evidence report instead of
        aborting the entire workflow with WORKFLOW_STEP_FAILED.
        """
        if not snapshot:
            return {
                "result": {"sections": 0, "claims": 0},
                "sections": [],
                "evidence": [],
                "trace_ids": [],
                "source_documents": [],
                "internal_traces": internal_traces or [],
            }
        sections = _group_snapshot_into_sections(snapshot)
        evidence = _snapshot_to_evidence_list(snapshot)
        # Pass traces through unchanged — no reconstruction
        traces = internal_traces or []
        return {
            "result": {"sections": len(sections), "claims": len(evidence)},
            "sections": sections,
            "evidence": evidence,
            "trace_ids": [r.trace_id for r in traces],
            "source_documents": sorted(set(r.document_id for r in traces)),
            "internal_traces": traces,
        }

    # =========================================================================
    # Step 4: Report — consumes synthesis, passes traces thru
    # =========================================================================

    def execute_report_from_synthesis(
        self, topic: str, synthesis_output: dict,
    ) -> dict[str, Any]:
        evidence = synthesis_output.get("evidence", [])
        sections = synthesis_output.get("sections", [])
        traces = synthesis_output.get("internal_traces", [])
        if not evidence and not sections:
            return {
                "result": {"sections": 0, "title": f"研究报告：{topic} (无可用证据)"},
                "sections": [],
                "evidence": [],
                "trace_ids": [],
                "source_documents": [],
                "internal_traces": traces,
            }
        report_sections = _build_report_sections(topic, evidence, sections)
        return {
            "result": {"sections": len(report_sections), "title": f"研究报告：{topic}"},
            "sections": report_sections,
            "evidence": evidence,
            "trace_ids": [r.trace_id for r in traces],
            "source_documents": sorted(set(r.document_id for r in traces)),
            "internal_traces": traces,
        }

    # =========================================================================
    # Step 5: Citation Export — consumes evidence, passes traces thru
    # =========================================================================

    def execute_citation_export_from_evidence(
        self, topic: str, evidence: list[dict],
        internal_traces: list[InternalTraceRecord] | None = None,
    ) -> dict[str, Any]:
        if not evidence:
            return {
                "result": {"total_citations": 0, "citations": []},
                "trace_ids": [],
                "source_documents": [],
                "internal_traces": internal_traces or [],
            }
        traces = internal_traces or []
        seen: set[str] = set()
        citations: list[dict] = []
        for ev in evidence:
            tid = ev.get("trace_id", "")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            citations.append({
                "trace_id": tid,
                "citation_text": ev.get("citation_text", ""),
                "document_id": ev.get("document_id", ""),
                "quote": ev.get("quote", ""),
            })
        return {
            "result": {"total_citations": len(citations), "citations": citations},
            "trace_ids": [c["trace_id"] for c in citations],
            "source_documents": sorted(set(c["document_id"] for c in citations)),
            "internal_traces": traces,
        }

    # =========================================================================
    # Markdown artifact
    # =========================================================================

    def build_markdown_artifact(
        self, topic: str, run_id: str, steps: list[Any],
        retrieval_snapshot: list[dict], synthesis_output: dict,
    ) -> str:
        now = datetime.now(timezone.utc).isoformat()
        evidence = synthesis_output.get("evidence", [])
        sections = synthesis_output.get("sections", [])
        artifact_id = hashlib.sha256(
            f"{run_id}:{topic}:{now}".encode()
        ).hexdigest()[:16]

        lines = [
            f"# 研究报告：{topic}",
            "",
            f"> **Run ID**: `{run_id}`",
            f"> **Artifact ID**: `{artifact_id}`",
            f"> **生成时间**: {now}",
            "> **工作流类型**: full_research_flow",
            "",
            "---",
            "",
            "## 执行步骤",
            "",
        ]
        for step in steps:
            s = step if isinstance(step, dict) else step.model_dump() if hasattr(step, 'model_dump') else {}
            icon = "✅" if s.get("status") == "completed" else "❌"
            lines.append(f"- {icon} **{s.get('name', 'unknown')}**")

        lines.extend(["", "---", "", "## 文献检索快照", ""])
        if retrieval_snapshot:
            for i, rec in enumerate(retrieval_snapshot[:20], 1):
                lines.append(f"### {i}. {rec.get('claim_text', 'N/A')[:80]}")
                lines.append(f"> {rec.get('quote', '')[:200]}")
                lines.append(f"- 文献: `{rec.get('document_id', '')}`")
                tid = rec.get('trace_id', '')
                lines.append(f"- 引用标记: [{tid}]")
                lines.append("")
        else:
            lines.append("_暂无检索快照_")

        lines.extend(["", "---", "", "## 证据综合", ""])
        if sections:
            for sec in sections:
                lines.append(f"### {sec.get('heading', 'Untitled')}")
                lines.append(sec.get("body", ""))
                for ref in sec.get("references", []):
                    lines.append(f"- 引用标记: [{ref}]")
                lines.append("")
        elif evidence:
            for i, ev in enumerate(evidence[:20], 1):
                lines.append(f"### {i}. {ev.get('claim_text', 'N/A')[:80]}")
                lines.append(f"- 引用: `{ev.get('citation_text', '')}`")
                tid = ev.get('trace_id', '')
                lines.append(f"- 引用标记: [{tid}]")
                lines.append("")

        # Compute content hash
        body_text = "\n".join(lines)
        content_sha256 = hashlib.sha256(body_text.encode()).hexdigest()

        lines.extend([
            "", "---", "",
            "## 证据状态", "",
            f"- 检索快照记录数: {len(retrieval_snapshot)}",
            f"- 综合证据条数: {len(evidence)}",
            f"- 报告段落数: {len(sections)}",
            f"- 内容哈希: `{content_sha256}`",
            f"- Artifact ID: `{artifact_id}`",
            "", "---", "",
            "*本报告由 HFB V4 研究门户自动生成。*",
        ])
        return "\n".join(lines)

    # =========================================================================
    # ResearchRun persistence
    # =========================================================================

    async def persist_research_run(
        self, session_id: UUID | str, run_id: str, topic: str,
        workflow_type: str = "full_research_flow",
        steps: list[Any] | None = None,
        output_artifacts: dict[str, Any] | None = None,
        query_history_ids: list[str] | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
        retrieval_snapshot: list[dict] | None = None,
        immutable_traces: list | None = None,
    ) -> None:
        session = await self.workspace.get_session(session_id)
        if session is None:
            raise ValueError("Research session not found")

        existing: dict[str, Any] = {}
        if session.workflow_state:
            try:
                existing = json.loads(session.workflow_state)
            except (json.JSONDecodeError, TypeError):
                existing = {}

        now = datetime.now(timezone.utc).isoformat()
        runs: list[dict] = existing.get("runs", [])

        run_entry: dict[str, Any] = {
            "run_id": run_id,
            "session_id": str(session_id),
            "workflow_type": workflow_type,
            "topic": topic,
            "query_history_binding": query_history_ids or [],
            "started_at": started_at or now,
            "completed_at": completed_at or now,
            "step_execution_trace": [
                _step_to_record(s)
                for s in (steps or [])
            ],
            "output_artifacts": output_artifacts or {},
        }

        # Build replay manifest — frozen snapshot for deterministic replay
        # P2T2: Build manifest whenever retrieval_snapshot has data, even if
        # immutable_traces is empty (e.g. all chunks lack passage_id on ingest).
        if retrieval_snapshot:
            trace_dicts = []
            for tr in immutable_traces:
                if hasattr(tr, 'to_dict'):
                    trace_dicts.append(tr.to_dict())
            trace_ids = sorted(set(
                r.trace_id for r in immutable_traces if hasattr(r, 'trace_id')
            ))
            source_doc_ids = sorted(set(
                r.document_id for r in immutable_traces if hasattr(r, 'document_id')
            ))

            # Build canonical traces from immutable trace dicts — single source of truth
            canonical_traces = canonicalize_traces(trace_dicts)
            # Build snapshot with passage_id merged from traces for corpus hash
            trace_passage_map = {ct["trace_id"]: ct["passage_id"] for ct in canonical_traces}
            snapshot_for_corpus = []
            for r in retrieval_snapshot:
                entry = dict(r)
                tid = entry.get("trace_id", "")
                if tid in trace_passage_map:
                    entry.setdefault("passage_id", trace_passage_map[tid])
                snapshot_for_corpus.append(entry)

            # Compute self-contained hashes for the frozen manifest — all include canonical traces
            corpus_hash = canonical_sha256(_build_corpus_payload(snapshot_for_corpus))
            input_hash = canonical_sha256(_build_input_payload(
                topic=topic,
                workflow_type=workflow_type,
                pipeline_version="1.0.0",
                retrieval_snapshot=retrieval_snapshot,
                trace_ids=trace_ids,
                source_document_ids=source_doc_ids,
                canonical_traces=canonical_traces,
            ))

            # Build output payload from synthesis/report/citation
            synthesis_sections = _group_snapshot_into_sections(retrieval_snapshot)
            synthesis_evidence = _snapshot_to_evidence_list(retrieval_snapshot)
            synthesis_output_for_hash = self.execute_evidence_synthesis_from_snapshot(
                topic, retrieval_snapshot, internal_traces=list(immutable_traces),
            )
            report_output_for_hash = self.execute_report_from_synthesis(
                topic, synthesis_output_for_hash,
            )
            all_evidence = synthesis_output_for_hash.get("evidence", [])
            citation_output_for_hash = self.execute_citation_export_from_evidence(
                topic, all_evidence, internal_traces=list(immutable_traces),
            )
            # Build report sections deterministically from evidence
            report_sections_for_hash = _build_report_sections(
                topic, all_evidence,
                report_output_for_hash.get("sections", []),
            )

            output_payload = _build_canonical_payload(
                topic=topic,
                workflow_type=workflow_type,
                pipeline_version="1.0.0",
                retrieval_snapshot=retrieval_snapshot,
                synthesis_sections=synthesis_sections,
                synthesis_evidence=synthesis_evidence,
                report_sections=report_sections_for_hash,
                citations=citation_output_for_hash.get("result", {}).get("citations", []),
                trace_ids=trace_ids,
                source_document_ids=source_doc_ids,
                canonical_traces=canonical_traces,
            )
            output_hash = canonical_sha256(output_payload)

            # Build manifest — compute self-integrity hash over all fields except manifest_sha256 itself
            manifest = {
                "manifest_version": CANONICAL_VERSION,
                "run_id": run_id,
                "session_id": str(session_id),
                "workflow_type": workflow_type,
                "topic": topic,
                "pipeline_version": "1.0.0",
                "workflow_steps": ["topic_selection", "literature_retrieval", "evidence_synthesis", "report_generation", "citation_export"],
                "retrieval_snapshot": retrieval_snapshot,
                "traces": trace_dicts,
                "query_history_binding": query_history_ids or [],
                "corpus_sha256": corpus_hash,
                "canonical_input_sha256": input_hash,
                "canonical_output_sha256": output_hash,
                "canonicalization_version": CANONICAL_VERSION,
                "created_at": completed_at or datetime.now(timezone.utc).isoformat(),
            }
            manifest_hash = canonical_sha256(manifest)
            manifest["manifest_sha256"] = manifest_hash

            run_entry["replay_manifest"] = manifest

        runs.append(run_entry)
        existing["runs"] = runs
        session.workflow_state = json.dumps(existing, ensure_ascii=False)
        session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()

    async def get_research_runs(self, session_id: UUID | str) -> list[dict]:
        session = await self.workspace.get_session(session_id)
        if session is None or not session.workflow_state:
            return []
        try:
            state = json.loads(session.workflow_state)
        except (json.JSONDecodeError, TypeError):
            return []
        return state.get("runs", [])

    # =========================================================================
    # Sprint 3 compat — version comparison
    # =========================================================================

    async def configure_version_comparison(
        self, session_id: UUID | str,
        source_passage_id: UUID | str, target_passage_id: UUID | str,
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
        comparison = await comparisons.compare_passages(source_passage_id, target_passage_id)
        # P2T1: corpus_status = "approved" only when both versions are formal sources
        both_formal = source.get("is_formal_source", False) and target.get("is_formal_source", False)
        state: dict[str, Any] = {
            "workflow_type": "evidence_backed_version_comparison",
            "corpus_status": "approved" if both_formal else "validation",
            "source": source, "target": target,
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

    async def get_version_comparison(self, session_id: UUID | str) -> dict | None:
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
        source, target = state["source"], state["target"]
        comparison = state["comparison"]
        is_formal = state["source"].get("is_formal_source", False) and state["target"].get("is_formal_source", False)
        validation_notice = "" if is_formal else "> 验证语料：非生产验证数据，不得作为正式学术引用。"
        lines = [
            f"# {research_session.title}", "",
            validation_notice, "",
            "## 比较对象", "",
            f"### 底本：{source['version']['name']}", "",
            source["text"], "", f"引用：{source['citation']}", "",
            f"### 对校本：{target['version']['name']}", "",
            target["text"], "", f"引用：{target['citation']}", "",
            "## 差异摘要", "",
            f"- 差异数量：{comparison['differences']}",
            f"- 文本相似度：{comparison['similarity_ratio']:.2%}",
        ]
        if comparison.get("operations"):
            lines.extend(["", "| 类型 | 底本文字 | 对校本文字 |", "|---|---|---|"])
            for op in comparison["operations"]:
                lines.append(f"| {op['op']} | {self._escape_md(op.get('source_text',''))} | {self._escape_md(op.get('target_text',''))} |")
        lines.extend(["", "## 研究笔记", ""])
        if research_session.context_notes:
            lines.extend([research_session.context_notes, ""])
        if notes:
            for note in reversed(notes):
                tag = f" [{note.tags}]" if note.tags else ""
                lines.append(f"-{tag} {note.content}")
        elif not research_session.context_notes:
            lines.append("暂无研究笔记。")
        lines.extend(["", "## 证据状态", "",
            f"- 底本来源完整：{'是' if source['evidence_complete'] else '否'}",
            f"- 对校本来源完整：{'是' if target['evidence_complete'] else '否'}",
            f"- 正式学术来源：{'是' if is_formal else '否（验证流程）'}",
            f"- 学术审核状态：{'已审核（正式引用）' if is_formal else '未审核（验证流程）'}", "",
            f"生成时间：{datetime.now(timezone.utc).isoformat()}", ""])
        return "\n".join(lines)

    @staticmethod
    def _escape_md(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    async def _load_evidence(self, passage_id: UUID | str) -> dict[str, Any]:
        from sqlalchemy import select as sql_select
        from app.models.book import Book as B
        from app.models.chapter import Chapter as Ch
        from app.models.passage import Passage as P
        from app.models.version import Version as V
        stmt = (
            sql_select(P, V, B, Ch)
            .join(V, P.version_id == V.id).join(B, V.book_id == B.id)
            .join(Ch, P.chapter_id == Ch.id)
            .where(P.id == str(passage_id), P.is_deleted.is_(False),
                   V.is_deleted.is_(False), B.is_deleted.is_(False),
                   Ch.is_deleted.is_(False),
                   V.withdrawn_at.is_(None))
        )
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            raise ValueError(f"Passage {passage_id} not found")
        passage, version, book, chapter = row
        # P2T1: Use is_academic_citable to determine formal scholarly status
        is_formal = getattr(version, 'is_academic_citable', False)
        loc_parts = [p for p in [version.repository, version.shelf_mark] if p]
        loc = "，".join(loc_parts)
        citation = f"《{book.title}》·{version.version_name}，{chapter.title}，第{passage.order}条"
        if loc:
            citation += f"（{loc}）"
        return {
            "passage_id": passage.id, "text": passage.content_text,
            "translation": passage.translation, "notes": passage.notes,
            "order": passage.order,
            "chapter": {"id": chapter.id, "title": chapter.title},
            "version": {"id": version.id, "name": version.version_name,
                        "era": version.era, "year": version.year,
                        "repository": version.repository,
                        "shelf_mark": version.shelf_mark,
                        "source_url": version.source_url,
                        "is_formal_source": getattr(version, 'is_formal_source', False),
                        "rights_statement": getattr(version, 'rights_statement', None),
                        "persistent_identifier": getattr(version, 'persistent_identifier', None),
                        "is_withdrawn": bool(getattr(version, 'withdrawn_at', None)),
                        },
            "book": {"id": book.id, "title": book.title, "source_url": book.source_url},
            "citation": citation,
            "evidence_complete": is_formal,
            "is_formal_source": is_formal,
        }


# =============================================================================
# Helpers
# =============================================================================


def _step_to_record(step: Any) -> dict:
    if isinstance(step, dict):
        return {
            "step_name": step.get("name", ""),
            "status": step.get("status", ""),
            "started_at": step.get("started_at", ""),
            "completed_at": step.get("completed_at", ""),
            "trace_ids": step.get("trace_ids", []),
        }
    return {
        "step_name": getattr(step, "name", ""),
        "status": getattr(step, "status", ""),
        "started_at": getattr(step, "started_at", getattr(step, "completed_at", "")),
        "completed_at": getattr(step, "completed_at", ""),
        "trace_ids": getattr(step, "trace_ids", []),
    }


async def _build_retrieval_snapshot(
    db: AsyncSession, result,
    retrieval_snapshot: dict[str, dict] | None = None,
) -> tuple[list[dict], list[InternalTraceRecord]]:
    """Build immutable retrieval snapshot + traces from AcademicService result.

    Sprint 4 P0: Uses real retrieval_snapshot (score + method) from GenerationProof.
    Falls back to TraceLineageError if no snapshot available.
    """
    if retrieval_snapshot is None:
        from app.services.trace_lineage import TraceLineageError
        raise TraceLineageError(
            "TRACE_LINEAGE_INCOMPLETE: retrieval_snapshot is required for workflow"
        )

    snapshot: list[dict] = []
    seen: set[str] = set()
    # Pre-load source_ref map for all involved documents
    doc_ids = set()
    for t in result.evidence_trace:
        if t.document_id:
            doc_ids.add(t.document_id)
    source_ref_by_doc: dict[str, dict[str, str]] = {}
    if doc_ids:
        from sqlalchemy import select as sql_select
        from app.models.academic_evidence import SourceRef
        sr_stmt = sql_select(SourceRef).where(
            SourceRef.is_deleted.is_(False),
            SourceRef.page_location.in_([f"document:{did}" for did in doc_ids]),
        )
        sr_result = await db.execute(sr_stmt)
        for sr in sr_result.scalars().all():
            doc_id = sr.page_location.replace("document:", "") if sr.page_location else ""
            if doc_id:
                source_ref_by_doc[doc_id] = {
                    "source_ref_id": sr.id,
                    "source_ref_url": sr.url or "",
                    "source_ref_title": sr.title,
                }

        # Task 2B BLOCK_RELEASE: when no SourceRef rows match the
        # document: prefix (e.g. only passage:-scoped SourceRefs exist),
        # fall back to Document table for title + source_url so
        # retrieval_snapshot entries carry a visible source_ref_title
        # and SourceReferenceCard renders a navigable link instead of
        # "此证据缺少文献来源信息".
        unmatched = doc_ids - set(source_ref_by_doc.keys())
        if unmatched:
            from app.models.document import Document as Doc
            doc_stmt = sql_select(Doc.id, Doc.title, Doc.source_url).where(
                Doc.is_deleted.is_(False),
                Doc.id.in_(list(unmatched)),
            )
            doc_result = await db.execute(doc_stmt)
            for row in doc_result.all():
                did, d_title, d_url = row[0], row[1], row[2]
                if did and did not in source_ref_by_doc:
                    source_ref_by_doc[did] = {
                        "source_ref_id": did,
                        "source_ref_url": d_url or "",
                        "source_ref_title": d_title or "",
                    }

    for t in result.evidence_trace:
        tid = make_trace_id(t.document_id, t.chunk_id)
        key = f"{t.document_id}:{t.chunk_id}"
        if key in seen:
            continue
        seen.add(key)
        sr_info = source_ref_by_doc.get(t.document_id, {})
        snapshot.append({
            "trace_id": tid,
            "document_id": t.document_id,
            "chunk_id": t.chunk_id,
            "claim_text": t.claim_text,
            "quote": t.quote,
            "citation_text": t.citation_text,
            "source_ref_id": sr_info.get("source_ref_id"),
            "source_ref_url": sr_info.get("source_ref_url"),
            "source_ref_title": sr_info.get("source_ref_title"),
        })

    # Build InternalTraceRecords from real snapshot
    from app.services.trace_lineage import TraceLineageError, make_trace_id as _make_tid
    now = datetime.now(timezone.utc).isoformat()
    internal_traces: list[InternalTraceRecord] = []
    seen_tids: set[str] = set()
    for rec in snapshot:
        tid = rec["trace_id"]
        if tid in seen_tids:
            continue
        seen_tids.add(tid)
        chk_id = rec["chunk_id"]

        # Require real score/method from snapshot
        snap_entry = retrieval_snapshot.get(chk_id)
        if snap_entry is None:
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: chunk {chk_id} not in retrieval_snapshot"
            )
        score = snap_entry.get("score", None)
        if not isinstance(score, (int, float)) or score != score:
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: invalid score {score} for chunk {chk_id}"
            )
        method = snap_entry.get("retrieval_method", "")
        if not method or not method.strip():
            raise TraceLineageError(
                f"TRACE_LINEAGE_INCOMPLETE: empty retrieval_method for chunk {chk_id}"
            )

        # Query DB for passage_id
        from sqlalchemy import select as sql_select
        from app.models.document_chunk import DocumentChunk as DC
        chk_stmt = sql_select(DC.passage_id).where(
            DC.id == chk_id,
            DC.is_deleted.is_(False),
        )
        chk_result = await db.execute(chk_stmt)
        row = chk_result.one_or_none()
        passage_id = ""
        if row and row[0] and row[0].strip():
            passage_id = row[0]

        # P2T1: Chunks without passage_id still contribute to snapshot/evidence
        # pipeline — downstream steps (synthesis/report/citation) only need
        # trace_id/document_id/claim_text/quote/citation_text.
        # Skipping them here preserves retrieval output without blocking the
        # entire workflow on unmapped chunks.
        if not passage_id:
            logger.warning(
                "Chunk %s has no passage_id — skipping from InternalTraceRecords "
                "(still included in retrieval snapshot for evidence pipeline)",
                chk_id,
            )
            continue

        internal_traces.append(InternalTraceRecord(
            trace_id=tid,
            document_id=rec["document_id"],
            chunk_id=chk_id,
            passage_id=passage_id,
            provenance_kind="retrieval",
            retrieval_score=float(score),
            retrieval_method=method,
            timestamp=now,
        ))
    return snapshot, internal_traces


async def _pack_academic_step(
    db: AsyncSession, result, topic: str,
    retrieval_snapshot: dict[str, dict] | None = None,
) -> dict[str, Any]:
    traces = await build_internal_traces(db, result.evidence_trace, retrieval_snapshot=retrieval_snapshot)
    return {
        "result": {"topic": topic, "sub_questions": len(result.decomposition)},
        "trace_ids": extract_trace_ids(result.evidence_trace),
        "source_documents": extract_source_documents(result.evidence_trace),
        "internal_traces": traces,
    }


def _group_snapshot_into_sections(snapshot: list[dict]) -> list[dict]:
    sections: dict[str, dict] = {}
    for r in snapshot:
        did = r["document_id"]
        if did not in sections:
            sections[did] = {"heading": f"来源文献: {did}", "body": "", "references": []}
        sections[did]["body"] += f"- {r['claim_text']}\n"
        sections[did]["references"].append(r["trace_id"])
    return list(sections.values())


def _snapshot_to_evidence_list(snapshot: list[dict]) -> list[dict]:
    return [{
        "trace_id": r["trace_id"], "document_id": r["document_id"],
        "chunk_id": r["chunk_id"], "claim_text": r["claim_text"],
        "quote": r["quote"], "citation_text": r["citation_text"],
    } for r in snapshot]


def _build_report_sections(
    topic: str, evidence: list[dict], sections: list[dict],
) -> list[dict]:
    if sections:
        return sections
    doc_groups: dict[str, list[dict]] = {}
    for ev in evidence:
        doc_groups.setdefault(ev.get("document_id", "unknown"), []).append(ev)
    report = []
    for did, evs in doc_groups.items():
        body = []
        refs = []
        for ev in evs:
            body.append(f"- {ev.get('claim_text','')}")
            if ev.get('citation_text'):
                body.append(f"  引用: {ev['citation_text']}")
            refs.append(ev.get("trace_id", ""))
        report.append({"heading": f"文献 {did}", "body": "\n".join(body),
                        "references": [r for r in refs if r]})
    return report


# =============================================================================
# Canonical artifact — pure functions for deterministic replay verification
# =============================================================================

CANONICAL_VERSION = "2.0.0"


def canonical_json_bytes(payload: dict) -> bytes:
    """Stable, sorted, deterministic JSON byte representation.

    Uses sort_keys=True, ASCII-safe encoding, fixed separators.
    """
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(payload: dict) -> str:
    """SHA-256 of canonical_json_bytes."""
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


# =============================================================================
# canonicalize_trace — single source of truth for provenance fields in hashes
# =============================================================================

_PROVENANCE_FIELDS = [
    "trace_id",
    "document_id",
    "chunk_id",
    "passage_id",
    "provenance_kind",
    "retrieval_score",
    "retrieval_method",
]


def canonicalize_trace(trace: dict) -> dict:
    """Extract canonical provenance fields from a trace dict.

    Protects invariant: academic output = content + citations + source identity + retrieval method.
    Every field here must enter all three hash domains (corpus, input, output).
    """
    return {k: trace[k] for k in _PROVENANCE_FIELDS}


def canonicalize_traces(traces: list[dict]) -> list[dict]:
    """Sort traces by trace_id, extract canonical provenance fields.

    Stable across dict key ordering and input list ordering.
    retrieval_score preserved as real float; None for graph provenance.
    """
    return sorted(
        [canonicalize_trace(t) for t in traces],
        key=lambda t: t["trace_id"],
    )


def _build_canonical_payload(
    topic: str,
    workflow_type: str,
    pipeline_version: str,
    retrieval_snapshot: list[dict],
    synthesis_sections: list[dict],
    synthesis_evidence: list[dict],
    report_sections: list[dict],
    citations: list[dict],
    trace_ids: list[str],
    source_document_ids: list[str],
    canonical_traces: list[dict] | None = None,
) -> dict:
    """Construct canonical payload for deterministic replay verification.

    Includes FULL content — quotes, citation_text, document_id, chunk_id,
    AND full canonical traces — passage_id, provenance_kind, retrieval_score, retrieval_method.
    Modifying any of these fields must change the output hash and fail replay.
    """
    sorted_snapshot = sorted(retrieval_snapshot, key=lambda r: r.get("trace_id", ""))
    sorted_evidence = sorted(synthesis_evidence, key=lambda e: e.get("trace_id", ""))
    sorted_citations = sorted(citations, key=lambda c: c.get("trace_id", ""))

    payload = {
        "topic": topic,
        "workflow_type": workflow_type,
        "pipeline_version": pipeline_version,
        "canonical_version": CANONICAL_VERSION,
        "retrieval_snapshot": [
            {
                "trace_id": r["trace_id"],
                "document_id": r["document_id"],
                "chunk_id": r["chunk_id"],
                "claim_text": r["claim_text"],
                "quote": r["quote"],
                "citation_text": r["citation_text"],
            }
            for r in sorted_snapshot
        ],
        "synthesis_sections": [
            {
                "heading": s["heading"],
                "body": s["body"],
                "references": sorted(s.get("references", [])),
            }
            for s in sorted(synthesis_sections, key=lambda s: s.get("heading", ""))
        ],
        "synthesis_evidence": [
            {
                "trace_id": e["trace_id"],
                "document_id": e["document_id"],
                "chunk_id": e["chunk_id"],
                "claim_text": e["claim_text"],
                "quote": e["quote"],
                "citation_text": e["citation_text"],
            }
            for e in sorted_evidence
        ],
        "report_sections": [
            {
                "heading": s["heading"],
                "body": s["body"],
                "references": sorted(s.get("references", [])),
            }
            for s in sorted(report_sections, key=lambda s: s.get("heading", ""))
        ],
        "citation_export": [
            {
                "trace_id": c["trace_id"],
                "citation_text": c["citation_text"],
                "document_id": c["document_id"],
                "quote": c["quote"],
            }
            for c in sorted_citations
        ],
        "trace_ids": sorted(trace_ids),
        "source_document_ids": sorted(source_document_ids),
    }
    if canonical_traces is not None:
        payload["traces"] = canonical_traces
    return payload


def _build_corpus_payload(retrieval_snapshot: list[dict]) -> dict:
    """Build corpus payload for corpus_sha256 — covers provenance identity + quote/content/citation_text.

    Includes canonical traces with full provenance: passage_id, provenance_kind, retrieval_score, retrieval_method.
    Modifying any of these to a fabricated value must change the hash and fail replay.
    """
    sorted_snapshot = sorted(retrieval_snapshot, key=lambda r: r.get("trace_id", ""))
    return {
        "corpus_entries": [
            {
                "document_id": r["document_id"],
                "chunk_id": r["chunk_id"],
                "passage_id": r.get("passage_id", ""),
                "quote": r["quote"],
                "citation_text": r["citation_text"],
            }
            for r in sorted_snapshot
        ],
        "canonical_version": CANONICAL_VERSION,
    }


def _build_input_payload(
    topic: str,
    workflow_type: str,
    pipeline_version: str,
    retrieval_snapshot: list[dict],
    trace_ids: list[str],
    source_document_ids: list[str],
    canonical_traces: list[dict] | None = None,
) -> dict:
    """Build input payload for canonical_input_sha256.

    Includes full canonical traces — passage_id, provenance_kind, retrieval_score, retrieval_method.
    Modifying any provenance field must change this hash and fail replay.
    """
    payload = {
        "topic": topic,
        "workflow_type": workflow_type,
        "pipeline_version": pipeline_version,
        "retrieval_snapshot": [
            {
                "trace_id": r["trace_id"],
                "document_id": r["document_id"],
                "chunk_id": r["chunk_id"],
                "claim_text": r["claim_text"],
                "quote": r["quote"],
                "citation_text": r["citation_text"],
            }
            for r in sorted(retrieval_snapshot, key=lambda r: r.get("trace_id", ""))
        ],
        "trace_ids": sorted(trace_ids),
        "source_document_ids": sorted(source_document_ids),
        "canonical_version": CANONICAL_VERSION,
    }
    if canonical_traces is not None:
        payload["traces"] = canonical_traces
    return payload
