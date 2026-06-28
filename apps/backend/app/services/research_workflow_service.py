"""Evidence-backed research workflow orchestration."""
from __future__ import annotations

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
from app.services.version_center import VersionComparisonService
from app.services.workspace_service import WorkspaceService


class ResearchWorkflowService:
    """Coordinates a complete evidence-backed version comparison."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace = WorkspaceService(session)
        self.comparisons = VersionComparisonService(session)

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
