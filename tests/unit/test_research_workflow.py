"""Evidence-backed version comparison workflow tests."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.passage import Passage
from app.models.version import Version
from app.services.research_workflow_service import ResearchWorkflowService
from app.services.workspace_service import WorkspaceService

from tests.conftest_db import db_session  # noqa: F401


async def _seed_comparable_passages(
    session: AsyncSession,
) -> tuple[Passage, Passage]:
    book = Book(title="针灸甲乙经（流程验证）", dynasty="西晋")
    session.add(book)
    await session.flush()

    chapter = Chapter(book_id=book.id, title="流程验证章节", order=1)
    source_version = Version(
        book_id=book.id,
        version_name="验证本 A",
        repository="流程验证资料库",
        shelf_mark="VALIDATION-A",
    )
    target_version = Version(
        book_id=book.id,
        version_name="验证本 B",
        repository="流程验证资料库",
        shelf_mark="VALIDATION-B",
    )
    session.add_all([chapter, source_version, target_version])
    await session.flush()

    source = Passage(
        chapter_id=chapter.id,
        version_id=source_version.id,
        content_text="凡刺之法，必候日月星辰，四时八正之气。",
        order=1,
    )
    target = Passage(
        chapter_id=chapter.id,
        version_id=target_version.id,
        content_text="凡刺之法，必候日月星辰，四时八节之气。",
        order=1,
    )
    session.add_all([source, target])
    await session.flush()
    return source, target


@pytest.mark.asyncio
async def test_configure_version_comparison_persists_evidence_snapshot(
    db_session: AsyncSession,
) -> None:
    source, target = await _seed_comparable_passages(db_session)
    research_session = await WorkspaceService(db_session).create_session(
        "researcher-1",
        "针灸甲乙经版本比较",
    )

    workflow = ResearchWorkflowService(db_session)
    result = await workflow.configure_version_comparison(
        UUID(research_session.id),
        UUID(source.id),
        UUID(target.id),
    )

    assert result["workflow_type"] == "evidence_backed_version_comparison"
    assert result["corpus_status"] == "validation"
    assert result["comparison"]["differences"] == 1
    assert result["source"]["citation"].startswith("《针灸甲乙经（流程验证）》")
    assert "验证本 A" in result["source"]["citation"]
    assert "VALIDATION-A" in result["source"]["citation"]

    restored = await workflow.get_version_comparison(research_session.id)
    assert restored == result


@pytest.mark.asyncio
async def test_export_markdown_contains_citations_diff_and_research_notes(
    db_session: AsyncSession,
) -> None:
    source, target = await _seed_comparable_passages(db_session)
    workspace = WorkspaceService(db_session)
    research_session = await workspace.create_session(
        "researcher-2",
        "针灸甲乙经版本比较",
    )
    await workspace.update_session(
        research_session.id,
        context_notes="重点核对“八正”与“八节”的语义差异。",
    )
    await workspace.create_note(
        research_session.id,
        "此处可能反映节气术语的版本演变。",
        entity_type="version_comparison",
        tags="待复核",
    )

    workflow = ResearchWorkflowService(db_session)
    await workflow.configure_version_comparison(
        research_session.id,
        source.id,
        target.id,
    )
    markdown = await workflow.export_markdown(research_session.id)

    assert "验证语料" in markdown
    assert "不得作为正式学术引用" in markdown
    assert "凡刺之法" in markdown
    assert "验证本 A" in markdown
    assert "验证本 B" in markdown
    assert "差异数量：1" in markdown
    assert "重点核对" in markdown
    assert "此处可能反映" in markdown
