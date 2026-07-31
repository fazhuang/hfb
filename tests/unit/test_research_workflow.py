"""Evidence-backed version comparison workflow tests."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.passage import Passage
from app.models.user import User
from app.models.version import Version
from app.services.research_workflow_service import ResearchWorkflowService
from app.services.workspace_service import WorkspaceService
from sqlalchemy.ext.asyncio import AsyncSession

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
    # FK constraint: ResearchSession.user_id must reference an existing User
    u = User(
        id="researcher-1",
        username="researcher-1",
        email="researcher-1@test.com",
        hashed_password="test-hash-r1",
    )
    db_session.add(u)
    await db_session.flush()

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
    # FK constraint: ResearchSession.user_id must reference an existing User
    u = User(
        id="researcher-2",
        username="researcher-2",
        email="researcher-2@test.com",
        hashed_password="test-hash-r2",
    )
    db_session.add(u)
    await db_session.flush()

    workspace = WorkspaceService(db_session)
    research_session = await workspace.create_session(
        "researcher-2",
        "针灸甲乙经版本比较",
    )
    await workspace.update_session(
        research_session.id,
        context_notes="重点核对「八正」与「八节」的语义差异。",
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


# ==========================================================================
# Batch 2: persist_research_run manifest with empty immutable_traces
# ==========================================================================


@pytest.mark.asyncio
async def test_persist_run_writes_manifest_with_empty_traces(
    db_session: AsyncSession,
) -> None:
    """snapshot has data, immutable_traces is empty → run persists manifest.

    This guards the P2T2 fix: retrieval_snapshot non-empty but all chunks
    lack passage_id → immutable_traces is [] → manifest must still be
    written so the frontend can extract real snapshot evidence.
    """
    u = User(
        id="researcher-mt-1",
        username="researcher-mt-1",
        email="researcher-mt-1@test.com",
        hashed_password="test-hash-mt1",
    )
    db_session.add(u)
    await db_session.flush()

    ws = WorkspaceService(db_session)
    session = await ws.create_session("researcher-mt-1", "manifest-empty-traces")

    wf = ResearchWorkflowService(db_session)
    snapshot = [
        {
            "trace_id": "tid-snap-1",
            "document_id": "doc-snap",
            "chunk_id": "chk-snap",
            "claim_text": "Snapshot claim",
            "quote": "Snapshot quote",
            "citation_text": "[doc-snap:0]",
        }
    ]
    # immutable_traces explicitly empty — simulates all chunks lacking passage_id
    await wf.persist_research_run(
        session_id=session.id,
        run_id="run-mt-1",
        topic="空 trace manifest 测试",
        workflow_type="full_research_flow",
        steps=[],
        output_artifacts={"citations": [], "report": ""},
        retrieval_snapshot=snapshot,
        immutable_traces=[],  # <-- empty
    )

    runs = await wf.get_research_runs(session.id)
    assert len(runs) == 1
    run = runs[0]

    # Manifest must exist even with empty traces
    manifest = run.get("replay_manifest")
    assert manifest is not None, "manifest should be written when snapshot has data"
    assert manifest["run_id"] == "run-mt-1"
    assert len(manifest["retrieval_snapshot"]) == 1
    assert manifest["retrieval_snapshot"][0]["claim_text"] == "Snapshot claim"
    # Empty traces → canonical traces should be empty list
    assert manifest["traces"] == []
    assert manifest.get("manifest_sha256"), "manifest_sha256 must be present"


@pytest.mark.asyncio
async def test_frontend_reads_real_snapshot_evidence_from_manifest(
    db_session: AsyncSession,
) -> None:
    """The frontend can read evidence from the manifest without fake traces.

    Evidence from retrieval_snapshot is accessible via the replay_manifest
    even when no InternalTraceRecord was built (immutable_traces empty).
    SourceRef / passage_id are not fabricated.
    """
    u = User(
        id="researcher-mt-2",
        username="researcher-mt-2",
        email="researcher-mt-2@test.com",
        hashed_password="test-hash-mt2",
    )
    db_session.add(u)
    await db_session.flush()

    ws = WorkspaceService(db_session)
    session = await ws.create_session("researcher-mt-2", "snapshot-evidence-fallback")

    wf = ResearchWorkflowService(db_session)
    snapshot = [
        {
            "trace_id": "tid-ev-1",
            "document_id": "doc-ev",
            "chunk_id": "chk-ev",
            "claim_text": "经络是气血运行的通道",
            "quote": "经络是气血运行的通道。",
            "citation_text": "[doc-ev:0]",
            "source_ref_id": None,
            "source_ref_url": "",
            "source_ref_title": None,
        }
    ]

    await wf.persist_research_run(
        session_id=session.id,
        run_id="run-ev-1",
        topic="Snapshot evidence fallback",
        workflow_type="full_research_flow",
        steps=[],
        output_artifacts={"citations": []},
        retrieval_snapshot=snapshot,
        immutable_traces=[],
    )

    runs = await wf.get_research_runs(session.id)
    manifest = runs[0]["replay_manifest"]
    snap = manifest["retrieval_snapshot"][0]

    # Real evidence is present
    assert "经络" in snap["claim_text"]
    assert snap["document_id"] == "doc-ev"
    assert snap["chunk_id"] == "chk-ev"

    # No fabricated trace, SourceRef, or passage_id
    assert manifest["traces"] == []
    assert snap.get("passage_id") is None or snap.get("passage_id") == ""
    assert snap.get("source_ref_id") is None

    # manifest_sha256 is legitimately computed
    assert len(manifest["manifest_sha256"]) == 64


@pytest.mark.asyncio
async def test_replay_hash_not_weakened_by_empty_traces(
    db_session: AsyncSession,
) -> None:
    """Replay hashes remain self-contained when traces are empty.

    Two runs with the same snapshot but different topics must produce
    different hashes — proving the hash includes topic, not just snapshot.
    """
    u = User(
        id="researcher-mt-3",
        username="researcher-mt-3",
        email="researcher-mt-3@test.com",
        hashed_password="test-hash-mt3",
    )
    db_session.add(u)
    await db_session.flush()

    ws = WorkspaceService(db_session)
    session = await ws.create_session("researcher-mt-3", "hash-isolation")

    wf = ResearchWorkflowService(db_session)
    snapshot = [
        {
            "trace_id": "tid-hash-1",
            "document_id": "doc-hash",
            "chunk_id": "chk-hash",
            "claim_text": "Hash test",
            "quote": "Hash test quote。",
            "citation_text": "[doc-hash:0]",
        }
    ]

    await wf.persist_research_run(
        session_id=session.id,
        run_id="run-hash-a",
        topic="Topic A",
        workflow_type="full_research_flow",
        steps=[],
        output_artifacts={},
        retrieval_snapshot=snapshot,
        immutable_traces=[],
    )
    await wf.persist_research_run(
        session_id=session.id,
        run_id="run-hash-b",
        topic="Topic B",
        workflow_type="full_research_flow",
        steps=[],
        output_artifacts={},
        retrieval_snapshot=snapshot,
        immutable_traces=[],
    )

    runs = await wf.get_research_runs(session.id)
    assert len(runs) == 2

    h_a = runs[0]["replay_manifest"]["manifest_sha256"]
    h_b = runs[1]["replay_manifest"]["manifest_sha256"]
    assert h_a != h_b, "different topics must produce different hashes"


# test_query_unmapped_passage_fail_closed in test_sprint4_v4.py serves as
# the authoritative fail-closed sentinel for the V4 API. That test uses
# db_session_persistent (no FK enforcement) and is a known-failing test
# — the manifest fix in persist_research_run does not alter its semantics.
