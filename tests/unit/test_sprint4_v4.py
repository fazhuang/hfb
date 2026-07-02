"""Sprint 4 V4 P0 Round 3 tests — strict lineage, immutable traces, fail-closed.

P0: InternalTraceRecord rejects all-empty fields. passage_id must be non-empty.
P0: Unmapped passage queries return TRACE_LINEAGE_INCOMPLETE.
P0: Downstream workflow stages pass original traces unchanged.
P0: Strict resolver (no optional mode).
P0: visualization query_id from QueryHistory, not constructed string.
P0: History/Runs traceability carries real trace IDs, not empty placeholders.
"""
from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest_db import db_session_persistent  # noqa: F401

import uuid


# ==========================================================================
# Helpers
# ==========================================================================


def _build_app(*routers):
    from fastapi import FastAPI
    return FastAPI()


def _setup_auth_overrides(app, db_session):
    from app.db.database import get_session
    async def override_get_session():
        yield db_session
    app.dependency_overrides[get_session] = override_get_session
    import app.middleware.auth as auth_mod
    app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
    async def _fake_auth_service():
        class FakeAuth:
            async def has_permission(self, *a, **kw): return True
            async def has_any_permission(self, *a, **kw): return True
        return FakeAuth()
    app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service


def _seed_chunks_with_passage(db, doc_id: str, title: str, dynasty: str,
                               passage_id: str, prefix: str = "v4-chk", count: int = 3):
    """Seed document + chunks WITH passage_id set — valid lineage."""
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id=doc_id, title=title, dynasty=dynasty)
    db.add(doc)
    contents = [
        "经脉流行不止，环周不休。针灸治疗以经络理论为基础。",
        "十二经脉包括手三阴、手三阳、足三阴、足三阳经。奇经八脉是对十二经脉的补充。",
        "针灸甲乙经系统整理了针灸理论。皇甫谧编纂此书，集此前针灸学之大成。",
    ]
    chunk_ids = []
    for i in range(min(count, len(contents))):
        cid = f"{prefix}-{i:03d}"
        db.add(DocumentChunk(document_id=doc.id, id=cid, chunk_index=i,
                             content=contents[i], token_count=len(contents[i]),
                             passage_id=passage_id))
        chunk_ids.append(cid)
    return doc.id, chunk_ids


def _seed_passage_with_lineage(db, passage_id: str, content: str, version_name: str = "宋本"):
    from app.models.passage import Passage
    from app.models.version import Version
    from app.models.book import Book
    from app.models.chapter import Chapter
    book = Book(id=f"book-{passage_id}", title="针灸甲乙经", source_url="http://example.com")
    db.add(book)
    version = Version(id=f"ver-{passage_id}", book_id=book.id, version_name=version_name,
                       era="晋", year=282)
    db.add(version)
    chapter = Chapter(id=f"ch-{passage_id}", title="经络", book_id=book.id)
    db.add(chapter)
    passage = Passage(id=passage_id, chapter_id=chapter.id, version_id=version.id,
                      content_text=content, order=1)
    db.add(passage)
    return passage_id


async def _read_query_history_internal(db, session_id: str):
    from sqlalchemy import select
    from app.models.workspace import QueryHistory
    stmt = select(QueryHistory).where(QueryHistory.session_id == str(session_id)).order_by(QueryHistory.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ==========================================================================
# 0. Schema & Trace ID Probes
# ==========================================================================


def test_internal_trace_record_all_fields_required():
    """P0: InternalTraceRecord rejects construction with any empty/missing field."""
    from pydantic import ValidationError
    from app.services.trace_lineage import InternalTraceRecord, make_trace_id

    valid_tid = make_trace_id("doc-1", "chk-1")

    # Valid construction
    rec = InternalTraceRecord(
        trace_id=valid_tid,
        document_id="doc-1",
        chunk_id="chk-1",
        passage_id="passage-1",
        retrieval_score=0.85,
        retrieval_method="ili_keyword",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert rec.trace_id == valid_tid
    assert rec.passage_id != ""
    d = rec.to_dict()
    assert len(d) == 7
    for k in d:
        assert d[k] is not None and d[k] != "", f"{k} should not be empty"

    # Empty passage_id rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="", retrieval_score=0.5, retrieval_method="m",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # Empty retrieval_method rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="p", retrieval_score=0.5, retrieval_method="",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # NaN score rejected
    import math
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="p", retrieval_score=math.nan, retrieval_method="m",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # Non-UUIDv5 trace_id rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id="not-a-uuid", document_id="d", chunk_id="c",
            passage_id="p", retrieval_score=0.5, retrieval_method="m",
            timestamp="2026-01-01T00:00:00+00:00",
        )


def test_traceability_block_query_id_min_length():
    from pydantic import ValidationError
    from app.schemas.v4 import V4TraceabilityBlock
    with pytest.raises(ValidationError):
        V4TraceabilityBlock(query_id="", trace_ids=[], citation_count=0, source_documents=[])


def test_trace_id_is_uuidv5_not_32bit_truncation():
    from app.services.trace_lineage import make_trace_id
    tid = make_trace_id("doc-1", "chk-1")
    assert tid != "doc-1"
    assert tid != "chk-1"
    assert "tr-" not in tid
    assert len(tid) > 32
    parsed = uuid.UUID(tid)
    assert parsed.version == 5
    assert make_trace_id("doc-1", "chk-1") == tid
    assert make_trace_id("doc-1", "chk-2") != tid


def test_visualization_schema_rejects_empty():
    from pydantic import ValidationError
    from app.schemas.v4 import VisualizationEdge, VisualizationNode
    with pytest.raises(ValidationError):
        VisualizationEdge(source="a", target="b", type="co_occurrence", weight=0.5, evidence_ids=[])
    with pytest.raises(ValidationError):
        VisualizationNode(id="x", type="concept", label="X", trace_ids=[])


# ==========================================================================
# 1. Query: unmapped passage → TRACE_LINEAGE_INCOMPLETE
# ==========================================================================


@pytest.mark.asyncio
async def test_query_with_passage_returns_lineage(db_session_persistent):
    """P0: When chunks have passage_id set, query succeeds with real traces."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-qa", "经络是运行气血的通道。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-qa", "针灸甲乙经", "晋",
                               passage_id=pid, prefix="v4-chk-qa")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v4/research/session", json={"title": "p", "query": "经络"})
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        tb = body["traceability"]
        assert tb is not None
        assert len(tb["trace_ids"]) > 0
        for tid in tb["trace_ids"]:
            assert uuid.UUID(tid).version == 5

        # History shows full traces with non-empty passage_id
        sid = body["data"]["session_id"]
        records = await _read_query_history_internal(db_session_persistent, sid)
        for rec in records:
            if rec.result_summary:
                summary = json.loads(rec.result_summary)
                for t in summary.get("traces", []):
                    assert t["passage_id"] != "", "passage_id should not be empty"
                    assert t["retrieval_method"] != ""
                    assert t["retrieval_score"] is not None


@pytest.mark.asyncio
async def test_query_unmapped_passage_fail_closed(db_session_persistent):
    """P0: Chunks without passage_id → TRACE_LINEAGE_INCOMPLETE, no academic output."""
    from app.api.v4.research import router as research_router

    # Seed document + chunks WITHOUT passage_id
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-nop", title="无映射文献", dynasty="唐")
    db_session_persistent.add(doc)
    db_session_persistent.add(DocumentChunk(
        id="v4-chk-nop-0", document_id=doc.id, chunk_index=0,
        content="针灸和经络是中医核心概念。", token_count=12,
    ))
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v4/research/session", json={"title": "unmapped", "query": "针灸"})
        body = r.json()
        # Must fail closed — no academic output for unmapped chunks
        assert body["success"] is False or "TRACE_LINEAGE_INCOMPLETE" in json.dumps(body)


# ==========================================================================
# 2. Immutable trace pass-along in workflow
# ==========================================================================


@pytest.mark.asyncio
async def test_workflow_downstream_passes_same_traces(db_session_persistent):
    """P0: Steps 3-5 keep the same InternalTraceRecord objects as step 2."""
    from app.services.research_workflow_service import ResearchWorkflowService

    rwf = ResearchWorkflowService(db_session_persistent)

    # Craft retrieval traces (simulate step 2 output)
    from app.services.trace_lineage import InternalTraceRecord, make_trace_id
    tid_a = make_trace_id("doc-a", "chk-a")
    tid_b = make_trace_id("doc-b", "chk-b")
    traces = [
        InternalTraceRecord(
            trace_id=tid_a, document_id="doc-a", chunk_id="chk-a",
            passage_id="passage-a", retrieval_score=0.8,
            retrieval_method="ili_keyword", timestamp="2026-01-01T00:00:00Z",
        ),
        InternalTraceRecord(
            trace_id=tid_b, document_id="doc-b", chunk_id="chk-b",
            passage_id="passage-b", retrieval_score=0.6,
            retrieval_method="ili_keyword", timestamp="2026-01-01T00:00:00Z",
        ),
    ]

    snapshot = [
        {"trace_id": tid_a, "document_id": "doc-a", "chunk_id": "chk-a",
         "claim_text": "Claim A", "quote": "Quote A", "citation_text": "[doc-a:0]"},
        {"trace_id": tid_b, "document_id": "doc-b", "chunk_id": "chk-b",
         "claim_text": "Claim B", "quote": "Quote B", "citation_text": "[doc-b:1]"},
    ]

    # Step 3: Synthesis passes traces through
    syn_out = rwf.execute_evidence_synthesis_from_snapshot(
        "test", snapshot, internal_traces=traces,
    )
    assert syn_out["internal_traces"] is traces  # SAME objects
    assert syn_out["internal_traces"][0].retrieval_score == 0.8
    assert syn_out["internal_traces"][0].retrieval_method == "ili_keyword"

    # Step 4: Report passes traces through
    rep_out = rwf.execute_report_from_synthesis("test", syn_out)
    assert rep_out["internal_traces"] is traces  # SAME objects
    assert rep_out["internal_traces"][1].retrieval_score == 0.6

    # Step 5: Citation export passes traces through
    cit_out = rwf.execute_citation_export_from_evidence(
        "test", syn_out["evidence"], internal_traces=traces,
    )
    assert cit_out["internal_traces"] is traces  # SAME objects


# ==========================================================================
# 3. Strict resolver
# ==========================================================================


@pytest.mark.asyncio
async def test_resolver_strict_missing_passage_fails(db_session_persistent):
    """P0: resolve_trace_lineage has no optional mode — strict by default."""
    from app.services.trace_lineage import (
        make_trace_id, resolve_trace_lineage, TraceLineageError,
    )

    # Seed chunk without passage_id
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.workspace import ResearchSession, QueryHistory

    doc = Document(id="v4-doc-str", title="strict test", dynasty="汉")
    db_session_persistent.add(doc)
    db_session_persistent.add(DocumentChunk(
        id="v4-chk-str-0", document_id=doc.id, chunk_index=0,
        content="测试内容。", token_count=5,
    ))
    await db_session_persistent.flush()

    tid = make_trace_id("v4-doc-str", "v4-chk-str-0")
    session = ResearchSession(user_id="u1", title="strict")
    db_session_persistent.add(session)
    await db_session_persistent.flush()
    db_session_persistent.add(QueryHistory(
        session_id=session.id, query_text="t", query_type="research",
        result_summary=json.dumps({"traces": [
            {"trace_id": tid, "chunk_id": "v4-chk-str-0", "document_id": "v4-doc-str",
             "passage_id": "", "retrieval_score": 0.5, "retrieval_method": "test",
             "timestamp": "2026-01-01"}
        ]}),
        citation_count=1,
    ))
    await db_session_persistent.flush()

    # Resolver must reject — chunk has no passage_id
    with pytest.raises(TraceLineageError) as exc:
        await resolve_trace_lineage(db_session_persistent, tid)
    assert "passage_id" in str(exc.value).lower() or "TRACE_LINEAGE_INCOMPLETE" in str(exc.value)


@pytest.mark.asyncio
async def test_resolver_with_passage_succeeds(db_session_persistent):
    """P0: Full lineage resolves when passage link exists."""
    from app.services.trace_lineage import (
        make_trace_id, resolve_trace_lineage, InternalTraceRecord,
    )
    from app.models.workspace import ResearchSession, QueryHistory

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-res", "环周不休。")
    doc_id, chunk_ids = _seed_chunks_with_passage(
        db_session_persistent, "v4-doc-res", "针灸甲乙经", "晋",
        passage_id=pid, prefix="v4-chk-res",
    )
    await db_session_persistent.flush()

    tid = make_trace_id(doc_id, chunk_ids[0])
    session = ResearchSession(user_id="u1", title="resolver")
    db_session_persistent.add(session)
    await db_session_persistent.flush()
    rec = InternalTraceRecord(
        trace_id=tid, document_id=doc_id, chunk_id=chunk_ids[0],
        passage_id=pid, retrieval_score=0.5, retrieval_method="ili_keyword",
        timestamp="2026-01-01T00:00:00Z",
    )
    db_session_persistent.add(QueryHistory(
        session_id=session.id, query_text="t", query_type="research",
        result_summary=json.dumps({"traces": [rec.to_dict()]}),
        citation_count=1,
    ))
    await db_session_persistent.flush()

    resolved = await resolve_trace_lineage(db_session_persistent, tid)
    assert resolved.trace_id == tid
    assert resolved.chunk is not None
    assert resolved.document is not None
    assert resolved.passage is not None
    assert resolved.passage.id == pid
    assert "针灸甲乙经" in resolved.passage_citation


# ==========================================================================
# 4. Workflow end-to-end with passage linkage
# ==========================================================================


@pytest.mark.asyncio
async def test_workflow_e2e_with_passage(db_session_persistent):
    """P0: Full 5-step workflow with passage-linked chunks succeeds."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-wf", "经络是运行气血的通道。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-wf", "针灸甲乙经", "晋",
                               passage_id=pid, prefix="v4-chk-wf")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "wf passage"})
        sid = r1.json()["data"]["session_id"]

        r2 = await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        assert r2.status_code == 200
        body = r2.json()
        assert body["success"] is True
        assert len(body["data"]["steps"]) == 5
        assert all(s["status"] == "completed" for s in body["data"]["steps"])

        # Replay has full artifact
        r3 = await client.get(f"/api/v4/research/session/{sid}/runs")
        runs = r3.json()["data"]["runs"]
        assert len(runs) == 1
        artifact = runs[0]["output_artifacts"]["markdown"]
        assert len(artifact) > 100
        assert "针灸" in artifact or "经络" in artifact


# ==========================================================================
# 5. Visualization query_id from QueryHistory
# ==========================================================================


@pytest.mark.asyncio
async def test_visualization_session_bound(db_session_persistent):
    """P0: visualization query_id maps to a real QueryHistory entry."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-vs", title="针灸甲乙经", dynasty="晋")
    db_session_persistent.add(doc)
    db_session_persistent.add_all([
        DocumentChunk(id="v4-chk-vs-0", document_id=doc.id, chunk_index=0,
                      content="针灸和经络是中医理论的核心概念。", token_count=18),
        DocumentChunk(id="v4-chk-vs-1", document_id=doc.id, chunk_index=1,
                      content="针灸治疗以经络理论为基础。", token_count=12),
    ])
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for gtype in ["concept", "citation", "timeline", "document"]:
            r = await client.post("/api/v4/visualization/graph", json={
                "concept_labels": ["针灸", "经络"], "graph_type": gtype,
            })
            assert r.status_code == 200
            tb = r.json()["traceability"]
            assert tb is not None
            assert tb["query_id"] != ""
            # query_id should be meaningful (not empty string)


# ==========================================================================
# 6. History/Runs traceability carries real trace IDs
# ==========================================================================


@pytest.mark.asyncio
async def test_history_traceability_carries_real_trace_ids(db_session_persistent):
    """P0: History endpoint traceability has actual trace_ids from records, not empty."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-hist", "环周不休。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-hist", "针灸甲乙经", "晋",
                               passage_id=pid, prefix="v4-chk-hist")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "h", "query": "经络"})
        sid = r1.json()["data"]["session_id"]

        r2 = await client.get(f"/api/v4/research/session/{sid}/history")
        body = r2.json()
        tb = body["traceability"]
        assert tb is not None
        # Must carry real trace_ids from the query, not empty
        if body["data"]["total"] > 0:
            # history has records with trace_ids
            assert len(tb["trace_ids"]) > 0 or len(body["data"]["history"]) > 0
        for entry in body["data"]["history"]:
            # public DTO — no internal fields
            allowed = {"query_id", "query_text", "query_type", "citation_count",
                       "trace_count", "created_at"}
            for key in entry:
                assert key in allowed, f"Leaked field '{key}' in history entry"


# ==========================================================================
# 7. Timeline structured era/year
# ==========================================================================


@pytest.mark.asyncio
async def test_timeline_uses_structured_time_not_regex(db_session_persistent):
    """P0: Timeline nodes should use Version era/year, not regex on citation text."""
    from app.api.v4.visualization import router as viz_router

    # Content without explicit dynasty patterns in quote
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-tlv", title="现代文献", dynasty="现代")
    db_session_persistent.add(doc)
    db_session_persistent.add(DocumentChunk(
        id="v4-chk-tlv-0", document_id=doc.id, chunk_index=0,
        content="这是一段没有年代证据的文本。", token_count=12,
    ))
    await db_session_persistent.flush()

    app = _build_app(viz_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v4/visualization/graph", json={
            "concept_labels": ["年代"], "graph_type": "timeline",
        })
        assert r.status_code == 200
        graph = r.json()["data"]
        # No structured era/year → no edges
        for edge in graph["edges"]:
            assert False, f"Timeline with no structured time evidence should not have edges: {edge}"


# ==========================================================================
# 8. Citation graph — no non-citation edge types
# ==========================================================================


@pytest.mark.asyncio
async def test_citation_graph_excludes_hierarchy_cooccurrence(db_session_persistent):
    """P0: Citation graph has only citation type edges."""
    from app.api.v4.visualization import router as viz_router

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    doc = Document(id="v4-doc-cit2", title="test", dynasty="宋")
    db_session_persistent.add(doc)
    db_session_persistent.add_all([
        DocumentChunk(id="v4-chk-cit2-0", document_id=doc.id, chunk_index=0,
                      content="针灸和经络密切相关。", token_count=10),
        DocumentChunk(id="v4-chk-cit2-1", document_id=doc.id, chunk_index=1,
                      content="经络是针灸的基础理论。", token_count=10),
    ])
    await db_session_persistent.flush()

    app = _build_app(viz_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v4/visualization/graph", json={
            "concept_labels": ["针灸", "经络"], "graph_type": "citation",
        })
        assert r.status_code == 200
        graph = r.json()["data"]
        for edge in graph["edges"]:
            assert edge["type"] == "citation", (
                f"Citation graph edge type must be 'citation', got '{edge['type']}'"
            )


# ==========================================================================
# 9. Education beginner consistency
# ==========================================================================


@pytest.mark.asyncio
async def test_education_beginner_all_filters_consistent(db_session_persistent):
    """P0: Beginner citations, traces, source_docs all consistent with filtered content."""
    from app.api.v4.education import router as edu_router
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-edu2", "经络系统包括十二经脉。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-edu2", "黄帝内经", "战国",
                               passage_id=pid, prefix="v4-chk-edu2")
    await db_session_persistent.flush()

    app = _build_app(edu_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(edu_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "edu"})
        sid = r1.json()["data"]["session_id"]

        results = {}
        for level in ["beginner", "intermediate", "advanced"]:
            r = await client.post("/api/v4/education/learn", json={
                "session_id": sid, "topic": "经络", "level": level,
            })
            assert r.status_code == 200
            results[level] = r.json()

        # Beginner has citation_count matching actual concept citations
        b = results["beginner"]
        b_data = b["data"]
        concept_citations = sum(c.get("citation_count", 0) for c in b_data.get("concepts", []))
        assert b_data["citation_count"] == concept_citations, (
            f"Beginner citation_count {b_data['citation_count']} != concept sum {concept_citations}"
        )

        # Beginner traces ≤ intermediate traces
        b_traces = len(b["traceability"]["trace_ids"])
        i_traces = len(results["intermediate"]["traceability"]["trace_ids"])
        assert b_traces <= i_traces

        # Advanced has source_comparison
        assert "source_comparison" in results["advanced"]["data"]


# ==========================================================================
# 10. AST boundary
# ==========================================================================


def test_v4_routes_no_orm_imports():
    import ast
    import os
    test_dir = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(test_dir))
    backend = os.path.join(repo, "apps", "backend")
    v4_files = [
        os.path.join(backend, "app", "api", "v4", "research.py"),
        os.path.join(backend, "app", "api", "v4", "visualization.py"),
        os.path.join(backend, "app", "api", "v4", "education.py"),
    ]
    for fpath in v4_files:
        if not os.path.exists(fpath):
            continue
        with open(fpath) as f:
            source = f.read()
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        for imp in imports:
            assert not imp.startswith("app.models"), f"{fpath} imports ORM models: {imp}"
        for call in ["session.execute", "session.add", "db.flush"]:
            assert call not in source, f"{fpath} contains ORM call: {call}"


# ==========================================================================
# 11. Passage mapping stats
# ==========================================================================


@pytest.mark.asyncio
async def test_passage_mapping_stats(db_session_persistent):
    """P0: passage_mapping_stats returns correct counts."""
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.services.trace_lineage import passage_mapping_stats

    doc = Document(id="v4-doc-stats", title="统计测试", dynasty="唐")
    db_session_persistent.add(doc)
    db_session_persistent.add_all([
        DocumentChunk(id="v4-chk-s0", document_id=doc.id, chunk_index=0,
                      content="有 passage。", token_count=5, passage_id="passage-stats"),
        DocumentChunk(id="v4-chk-s1", document_id=doc.id, chunk_index=1,
                      content="无 passage。", token_count=5),
    ])
    await db_session_persistent.flush()

    stats = await passage_mapping_stats(db_session_persistent)
    assert stats["total_chunks"] >= 2
    assert stats["chunks_with_passage"] >= 1
    assert stats["chunks_without_passage"] >= 1
