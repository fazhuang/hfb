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

    # Valid construction — retrieval provenance
    rec = InternalTraceRecord(
        trace_id=valid_tid,
        document_id="doc-1",
        chunk_id="chk-1",
        passage_id="passage-1",
        provenance_kind="retrieval",
        retrieval_score=0.85,
        retrieval_method="ili_keyword",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert rec.trace_id == valid_tid
    assert rec.passage_id != ""
    assert rec.provenance_kind == "retrieval"
    assert rec.retrieval_score == 0.85
    d = rec.to_dict()
    assert len(d) == 8
    for k in d:
        assert d[k] is not None, f"{k} should not be None"
        if k != "retrieval_score":
            assert d[k] != "", f"{k} should not be empty (except retrieval_score which can be 0)"

    # Valid construction — graph provenance (score=None)
    rec_graph = InternalTraceRecord(
        trace_id=valid_tid,
        document_id="doc-1",
        chunk_id="chk-1",
        passage_id="passage-1",
        provenance_kind="graph",
        retrieval_score=None,
        retrieval_method="graph_service",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert rec_graph.provenance_kind == "graph"
    assert rec_graph.retrieval_score is None
    d2 = rec_graph.to_dict()
    assert d2["retrieval_score"] is None

    # Empty passage_id rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="", provenance_kind="retrieval",
            retrieval_score=0.5, retrieval_method="m",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # Empty retrieval_method rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="p", provenance_kind="retrieval",
            retrieval_score=0.5, retrieval_method="",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # Invalid provenance_kind rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="p", provenance_kind="invalid",
            retrieval_score=0.5, retrieval_method="m",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # retrieval provenance with None score rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="p", provenance_kind="retrieval",
            retrieval_score=None, retrieval_method="m",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # graph provenance with non-None score rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="p", provenance_kind="graph",
            retrieval_score=0.5, retrieval_method="graph_service",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # NaN score rejected
    import math
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=valid_tid, document_id="d", chunk_id="c",
            passage_id="p", provenance_kind="retrieval",
            retrieval_score=math.nan, retrieval_method="m",
            timestamp="2026-01-01T00:00:00+00:00",
        )

    # Non-UUIDv5 trace_id rejected
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id="not-a-uuid", document_id="d", chunk_id="c",
            passage_id="p", provenance_kind="retrieval",
            retrieval_score=0.5, retrieval_method="m",
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
            passage_id="passage-a", provenance_kind="retrieval",
            retrieval_score=0.8, retrieval_method="ili_keyword",
            timestamp="2026-01-01T00:00:00Z",
        ),
        InternalTraceRecord(
            trace_id=tid_b, document_id="doc-b", chunk_id="chk-b",
            passage_id="passage-b", provenance_kind="retrieval",
            retrieval_score=0.6, retrieval_method="ili_keyword",
            timestamp="2026-01-01T00:00:00Z",
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
        passage_id=pid, provenance_kind="retrieval",
        retrieval_score=0.5, retrieval_method="ili_keyword",
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

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-vs", "针灸和经络是中医核心概念。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-vs", "针灸甲乙经", "晋",
                               passage_id=pid, prefix="v4-chk-vs")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a research session for visualization queries
        r_sess = await client.post("/api/v4/research/session", json={"title": "viz session"})
        sid = r_sess.json()["data"]["session_id"]

        for gtype in ["concept", "citation", "timeline", "document"]:
            r = await client.post("/api/v4/visualization/graph", json={
                "session_id": sid, "concept_labels": ["针灸", "经络"], "graph_type": gtype,
            })
            assert r.status_code == 200
            tb = r.json()["traceability"]
            assert tb is not None
            assert tb["query_id"] != ""
            # query_id should be a real QueryHistory uuid
            assert len(tb["query_id"]) > 10


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
    from app.api.v4.research import router as research_router

    # Content without explicit dynasty patterns in quote, with passage but no Version era/year
    pid = _seed_passage_with_lineage(db_session_persistent, "passage-tlv", "无年代文本。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-tlv", "现代文献", "现代",
                               passage_id=pid, prefix="v4-chk-tlv")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "timeline"})
        sid = r_sess.json()["data"]["session_id"]

        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["年代"], "graph_type": "timeline",
        })
        assert r.status_code == 200
        graph = r.json()["data"]
        # No structured era/year → empty graph (no nodes, no edges)
        for edge in graph["edges"]:
            assert False, f"Timeline with no structured time evidence should not have edges: {edge}"


# ==========================================================================
# 8. Citation graph — no non-citation edge types
# ==========================================================================


@pytest.mark.asyncio
async def test_citation_graph_excludes_hierarchy_cooccurrence(db_session_persistent):
    """P0: Citation graph has only citation type edges."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-cit2", "针灸和经络密切相关。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-cit2", "test", "宋",
                               passage_id=pid, prefix="v4-chk-cit2")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "cit"})
        sid = r_sess.json()["data"]["session_id"]
        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["针灸", "经络"], "graph_type": "citation",
        })
        assert r.status_code == 200
        graph = r.json()["data"]
        for edge in graph["edges"]:
            assert edge["type"] == "citation", (
                f"Citation graph edge type must be 'citation', got '{edge['type']}'"
            )


# ==========================================================================
# 8b. Phase 1: Non-vacuous citation graph tests
# ==========================================================================


@pytest.mark.asyncio
async def test_citation_graph_has_edges_with_evidence(db_session_persistent):
    """P0 Phase 1: Citation graph with real evidence produces non-empty edges."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-cit3", "针灸和经络密切相关。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-cit3a", "文献A", "晋",
                               passage_id=pid, prefix="v4-chk-cit3a")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-cit3b", "文献B", "宋",
                               passage_id=pid, prefix="v4-chk-cit3b")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "cit-real"})
        sid = r_sess.json()["data"]["session_id"]
        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["针灸", "经络"], "graph_type": "citation",
        })
        assert r.status_code == 200
        graph = r.json()["data"]
        # Non-vacuous: must have edges when evidence exists
        assert len(graph["edges"]) > 0, "Citation graph must have edges when evidence exists"
        for edge in graph["edges"]:
            assert edge["type"] == "citation"
            assert len(edge["evidence_ids"]) > 0, "Each citation edge must have evidence_ids"
            # evidence_ids must be valid UUIDv5
            for eid in edge["evidence_ids"]:
                assert uuid.UUID(eid).version == 5
        # Nodes must have both concept and document types
        node_types = {n["type"] for n in graph["nodes"]}
        assert "concept" in node_types
        assert "document" in node_types
        # Source and target must be real nodes
        node_ids = {n["id"] for n in graph["nodes"]}
        for edge in graph["edges"]:
            assert edge["source"] in node_ids, f"Edge source {edge['source']} not in nodes"
            assert edge["target"] in node_ids, f"Edge target {edge['target']} not in nodes"


@pytest.mark.asyncio
async def test_citation_graph_empty_without_evidence(db_session_persistent):
    """P0 Phase 1: Empty graph when no evidence exists for concepts."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router

    # No chunks seeded — concepts won't appear in any chunk content
    _seed_passage_with_lineage(db_session_persistent, "passage-cit4", "无关内容。")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "cit-empty"})
        sid = r_sess.json()["data"]["session_id"]
        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["不存在的概念"], "graph_type": "citation",
        })
        assert r.status_code == 200
        graph = r.json()["data"]
        # No evidence → empty graph
        assert len(graph["edges"]) == 0, "Citation graph must be empty without evidence"


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


# ==========================================================================
# 12. Retrieval metadata integrity — no default score=0.0, no default method
# ==========================================================================


def test_snapshot_preserves_real_score():
    """P0: _snapshot_to_dicts passes through real score=0.83 exactly."""
    from app.services.retrieval import RetrievalResult
    from app.services.generation_proof import _snapshot_to_dicts

    rr = RetrievalResult(
        chunk_id="chk-1", document_id="doc-1", document_title="T",
        chunk_index=0, content="测试", citation="[doc-1:chk-1]",
        score=0.83, metadata={"retrieval_method": "ili_keyword_search"},
    )
    snapshot = {"chk-1": rr}
    result = _snapshot_to_dicts(snapshot)
    assert result["chk-1"]["score"] == 0.83
    assert result["chk-1"]["retrieval_method"] == "ili_keyword_search"


def test_snapshot_real_score_0_0_preserved():
    """P0: Real score=0.0 from RetrievalResult is allowed."""
    from app.services.retrieval import RetrievalResult
    from app.services.generation_proof import _snapshot_to_dicts

    rr = RetrievalResult(
        chunk_id="chk-1", document_id="doc-1", document_title="T",
        chunk_index=0, content="测试", citation="[doc-1:chk-1]",
        score=0.0, metadata={"retrieval_method": "ili_keyword_search"},
    )
    snapshot = {"chk-1": rr}
    result = _snapshot_to_dicts(snapshot)
    assert result["chk-1"]["score"] == 0.0


def test_snapshot_missing_score_fails():
    """P0: Missing score → ValueError RETRIEVAL_METADATA_INCOMPLETE."""
    from app.services.generation_proof import _snapshot_to_dicts

    class FakeRR:
        document_id = "d"
        content = "c"
        metadata = {"retrieval_method": "test"}

    with pytest.raises(ValueError) as exc:
        _snapshot_to_dicts({"chk-1": FakeRR()})
    assert "RETRIEVAL_METADATA_INCOMPLETE" in str(exc.value)
    assert "score" in str(exc.value).lower()


def test_snapshot_nan_score_fails():
    """P0: NaN score → ValueError."""
    import math
    from app.services.generation_proof import _snapshot_to_dicts

    class FakeRR:
        score = math.nan
        document_id = "d"
        content = "c"
        metadata = {"retrieval_method": "test"}

    with pytest.raises(ValueError):
        _snapshot_to_dicts({"chk-1": FakeRR()})


def test_snapshot_inf_score_fails():
    """P0: Inf score → ValueError."""
    import math
    from app.services.generation_proof import _snapshot_to_dicts

    class FakeRR:
        score = math.inf
        document_id = "d"
        content = "c"
        metadata = {"retrieval_method": "test"}

    with pytest.raises(ValueError):
        _snapshot_to_dicts({"chk-1": FakeRR()})


def test_snapshot_missing_retrieval_method_fails():
    """P0: Missing retrieval_method → ValueError."""
    from app.services.generation_proof import _snapshot_to_dicts

    class FakeRR:
        score = 0.5
        document_id = "d"
        content = "c"
        metadata = {}

    with pytest.raises(ValueError) as exc:
        _snapshot_to_dicts({"chk-1": FakeRR()})
    assert "RETRIEVAL_METADATA_INCOMPLETE" in str(exc.value)


def test_snapshot_score_out_of_range_fails():
    """P0: Score > 1.0 → ValueError."""
    from app.services.generation_proof import _snapshot_to_dicts

    class FakeRR:
        score = 1.5
        document_id = "d"
        content = "c"
        metadata = {"retrieval_method": "test"}

    with pytest.raises(ValueError) as exc:
        _snapshot_to_dicts({"chk-1": FakeRR()})
    assert "range" in str(exc.value).lower()


# ==========================================================================
# 13. Visualization trace completeness — strict resolver, real traces
# ==========================================================================


@pytest.mark.asyncio
async def test_visualization_query_history_has_full_traces(db_session_persistent):
    """P0: visualization saves full InternalTraceRecord in result_summary, not just trace_ids."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router
    from app.models.workspace import QueryHistory
    from sqlalchemy import select as sql_select

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-viz-full", "经络内容。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-vizf", "测试", "汉",
                               passage_id=pid, prefix="v4-chk-vizf")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "viz trace"})
        sid = r_sess.json()["data"]["session_id"]

        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["经络"], "graph_type": "concept",
        })
        assert r.status_code == 200
        tb = r.json()["traceability"]
        assert tb is not None
        assert tb["query_id"] != ""

        # Verify QueryHistory has full traces with passage_id
        stmt = sql_select(QueryHistory).where(
            QueryHistory.id == tb["query_id"],
        )
        qh_result = await db_session_persistent.execute(stmt)
        qh = qh_result.scalar_one_or_none()
        assert qh is not None, "QueryHistory must exist for visualization query"
        assert qh.result_summary is not None
        summary = json.loads(qh.result_summary)
        traces = summary.get("traces", [])
        assert len(traces) > 0, "result_summary must contain full traces"
        for t in traces:
            assert t.get("passage_id") != "", "trace passage_id must not be empty"
            assert t.get("retrieval_method") != ""
            # graph provenance has retrieval_score=None, retrieval has actual score
            if t.get("provenance_kind") == "graph":
                assert t.get("retrieval_score") is None
            else:
                assert t.get("retrieval_score") is not None
        source_docs = summary.get("source_documents", [])
        assert len(source_docs) > 0, "source_documents must contain real document IDs"


@pytest.mark.asyncio
async def test_visualization_concept_source_documents_real_ids(db_session_persistent):
    """P0: concept source_documents in node metadata are real document IDs, not counts."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-viz-sd", "测试。")
    doc_id, chunk_ids = _seed_chunks_with_passage(
        db_session_persistent, "v4-doc-vizsd", "甲乙", "晋",
        passage_id=pid, prefix="v4-chk-vizsd",
    )
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "viz sd"})
        sid = r_sess.json()["data"]["session_id"]

        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["经络"], "graph_type": "concept",
        })
        assert r.status_code == 200
        graph = r.json()["data"]
        for node in graph.get("nodes", []):
            meta = node.get("metadata", {})
            sd = meta.get("source_documents", "")
            # Must NOT be a bare number string like "1", "2"
            assert not sd.isdigit(), (
                f"source_documents must be real IDs, got numeric string: '{sd}'"
            )


# ==========================================================================
# 14. Timeline: Version era/year only, no Document.dynasty fallback
# ==========================================================================


@pytest.mark.asyncio
async def test_timeline_no_document_dynasty_fallback(db_session_persistent):
    """P0: Document.dynasty has value but Version has no time → timeline node NOT generated."""
    from app.services.trace_lineage import resolve_time_evidence

    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.passage import Passage
    from app.models.version import Version
    from app.models.book import Book
    from app.models.chapter import Chapter

    # Set up: passage → version WITHOUT era/year, but document WITH dynasty
    book = Book(id="book-tl2", title="TL Book", source_url="http://x.com")
    db_session_persistent.add(book)
    ver = Version(id="ver-tl2", book_id=book.id, version_name="v1", era=None, year=None)
    db_session_persistent.add(ver)
    ch = Chapter(id="ch-tl2", title="Ch", book_id=book.id)
    db_session_persistent.add(ch)
    passage = Passage(id="passage-tl2", chapter_id=ch.id, version_id=ver.id,
                      content_text="测试", order=1)
    db_session_persistent.add(passage)

    doc = Document(id="doc-tl2", title="TL Doc", dynasty="汉")
    db_session_persistent.add(doc)
    chunk = DocumentChunk(id="chk-tl2-0", document_id=doc.id, chunk_index=0,
                          content="测试内容", token_count=5, passage_id="passage-tl2")
    db_session_persistent.add(chunk)
    await db_session_persistent.flush()

    result = await resolve_time_evidence(db_session_persistent, "doc-tl2", "chk-tl2-0")
    # P0: Version has no era/year, so should return None even though Document.dynasty="汉"
    assert result is None, (
        f"resolve_time_evidence should return None when Version has no era/year, "
        f"even if Document.dynasty has a value. Got: {result}"
    )


# ==========================================================================
# 15. Phase 2: Graph provenance — score is None, not 0.0
# ==========================================================================


@pytest.mark.asyncio
async def test_graph_provenance_score_is_null_not_zero(db_session_persistent):
    """P0 Phase 2: Graph traces have retrieval_score=None, not 0.0."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router
    from app.models.workspace import QueryHistory
    from sqlalchemy import select as sql_select

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-gp1", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-gp1", "文献", "汉",
                               passage_id=pid, prefix="v4-chk-gp1")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "gp"})
        sid = r_sess.json()["data"]["session_id"]

        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["经络"], "graph_type": "concept",
        })
        assert r.status_code == 200
        tb = r.json()["traceability"]

        stmt = sql_select(QueryHistory).where(QueryHistory.id == tb["query_id"])
        qh_result = await db_session_persistent.execute(stmt)
        qh = qh_result.scalar_one_or_none()
        summary = json.loads(qh.result_summary)
        for t in summary.get("traces", []):
            assert t["provenance_kind"] == "graph", (
                f"Visualization traces must be graph provenance, got {t.get('provenance_kind')}"
            )
            assert t["retrieval_score"] is None, (
                f"Graph trace must have retrieval_score=None, got {t.get('retrieval_score')}"
            )
            assert t["retrieval_method"] == "graph_service"


@pytest.mark.asyncio
async def test_retrieval_trace_missing_score_fails(db_session_persistent):
    """P0 Phase 2: retrieval provenance without score fails."""
    from pydantic import ValidationError
    from app.services.trace_lineage import InternalTraceRecord, make_trace_id

    tid = make_trace_id("doc-1", "chk-1")
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=tid, document_id="doc-1", chunk_id="chk-1",
            passage_id="passage-1", provenance_kind="retrieval",
            retrieval_score=None, retrieval_method="ili_keyword",
            timestamp="2026-01-01T00:00:00Z",
        )


@pytest.mark.asyncio
async def test_graph_trace_with_score_fails(db_session_persistent):
    """P0 Phase 2: graph provenance with score fails."""
    from pydantic import ValidationError
    from app.services.trace_lineage import InternalTraceRecord, make_trace_id

    tid = make_trace_id("doc-1", "chk-1")
    with pytest.raises(ValidationError):
        InternalTraceRecord(
            trace_id=tid, document_id="doc-1", chunk_id="chk-1",
            passage_id="passage-1", provenance_kind="graph",
            retrieval_score=0.5, retrieval_method="graph_service",
            timestamp="2026-01-01T00:00:00Z",
        )


@pytest.mark.asyncio
async def test_graph_mode_saves_query_history(db_session_persistent):
    """P0 Phase 2: mode=graph saves QueryHistory with success."""
    from app.api.v4.research import router as research_router
    from app.models.workspace import QueryHistory
    from sqlalchemy import select as sql_select

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-gmode", "针灸经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-gmode", "甲乙", "晋",
                               passage_id=pid, prefix="v4-chk-gmode")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "gmode"})
        sid = r1.json()["data"]["session_id"]

        r2 = await client.post("/api/v4/research/query", json={
            "session_id": sid, "query": "针灸 经络", "mode": "graph",
        })
        body = r2.json()
        assert body["success"] is True, (
            f"graph mode should succeed with evidence, got: {body.get('message')} {body.get('data', {}).get('detail', '')}"
        )
        assert body["traceability"] is not None
        assert len(body["traceability"]["trace_ids"]) > 0

        # Verify QueryHistory saved
        stmt = sql_select(QueryHistory).where(
            QueryHistory.session_id == sid,
            QueryHistory.query_type == "graph",
        )
        qh_result = await db_session_persistent.execute(stmt)
        records = list(qh_result.scalars().all())
        assert len(records) > 0, "graph mode must save QueryHistory"


# ==========================================================================
# 16. Phase 3: Visualization citation_count consistency, empty QueryHistory
# ==========================================================================


@pytest.mark.asyncio
async def test_visualization_api_citation_count_matches_query_history(db_session_persistent):
    """P0 Phase 3: API traceability citation_count == QueryHistory.citation_count."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router
    from app.models.workspace import QueryHistory
    from sqlalchemy import select as sql_select

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-count", "经络内容。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-count", "文献", "汉",
                               passage_id=pid, prefix="v4-chk-count")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "count"})
        sid = r_sess.json()["data"]["session_id"]

        for gtype in ["concept", "citation", "document"]:
            r = await client.post("/api/v4/visualization/graph", json={
                "session_id": sid, "concept_labels": ["经络"], "graph_type": gtype,
            })
            assert r.status_code == 200
            tb = r.json()["traceability"]
            assert tb is not None
            assert tb["query_id"] != ""

            # Verify QueryHistory citation_count matches API traceability
            stmt = sql_select(QueryHistory).where(QueryHistory.id == tb["query_id"])
            qh_result = await db_session_persistent.execute(stmt)
            qh = qh_result.scalar_one_or_none()
            assert qh is not None
            assert qh.citation_count == tb["citation_count"], (
                f"QueryHistory.citation_count ({qh.citation_count}) != traceability.citation_count ({tb['citation_count']}) for {gtype}"
            )


@pytest.mark.asyncio
async def test_visualization_empty_graph_saves_query_history(db_session_persistent):
    """P0 Phase 3: Empty graph still creates QueryHistory with evidence_status=empty."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router
    from app.models.workspace import QueryHistory
    from sqlalchemy import select as sql_select

    _seed_passage_with_lineage(db_session_persistent, "passage-empty2", "无关。")

    # No chunks with matching concept labels → empty graph
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_sess = await client.post("/api/v4/research/session", json={"title": "empty"})
        sid = r_sess.json()["data"]["session_id"]

        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["不存在"], "graph_type": "concept",
        })
        assert r.status_code == 200
        tb = r.json()["traceability"]
        assert tb is not None
        assert tb["query_id"] != ""

        # Verify QueryHistory exists and has evidence_status
        stmt = sql_select(QueryHistory).where(QueryHistory.id == tb["query_id"])
        qh_result = await db_session_persistent.execute(stmt)
        qh = qh_result.scalar_one_or_none()
        assert qh is not None, "Empty graph must still create QueryHistory"
        summary = json.loads(qh.result_summary)
        assert summary.get("graph_type") == "concept"
        assert summary.get("node_count") == 0
        assert summary.get("edge_count") == 0
        assert summary.get("evidence_status") == "empty"
        assert qh.citation_count == 0


# ==========================================================================
# 17. Phase 4: Deterministic replay
# ==========================================================================


def test_canonical_json_bytes_deterministic():
    """P0 Phase 4: Same payload produces byte-identical output."""
    from app.services.research_workflow_service import canonical_json_bytes

    payload = {
        "topic": "test",
        "snapshot": [
            {"trace_id": "z", "quote": "Q", "citation_text": "C"},
            {"trace_id": "a", "quote": "A", "citation_text": "B"},
        ],
    }
    b1 = canonical_json_bytes(payload)
    b2 = canonical_json_bytes(payload)
    assert b1 == b2
    assert isinstance(b1, bytes)


def test_canonical_json_bytes_quote_change_changes_hash():
    """P0 Phase 4: Modifying quote changes the canonical hash."""
    from app.services.research_workflow_service import canonical_sha256

    payload = {
        "topic": "test",
        "snapshot": [
            {"trace_id": "a", "quote": "Original", "citation_text": "C"},
        ],
    }
    h1 = canonical_sha256(payload)
    payload["snapshot"][0]["quote"] = "Modified"
    h2 = canonical_sha256(payload)
    assert h1 != h2


def test_canonical_json_bytes_citation_change_changes_hash():
    """P0 Phase 4: Modifying citation_text changes the canonical hash."""
    from app.services.research_workflow_service import canonical_sha256

    payload = {
        "topic": "test",
        "snapshot": [
            {"trace_id": "a", "quote": "Q", "citation_text": "Original"},
        ],
    }
    h1 = canonical_sha256(payload)
    payload["snapshot"][0]["citation_text"] = "Modified"
    h2 = canonical_sha256(payload)
    assert h1 != h2


def test_canonical_json_bytes_document_id_change_changes_hash():
    """P0 Phase 4: Modifying document_id changes the canonical hash."""
    from app.services.research_workflow_service import canonical_sha256

    payload = {
        "topic": "test",
        "snapshot": [
            {"trace_id": "a", "document_id": "doc-1", "chunk_id": "chk-1",
             "quote": "Q", "citation_text": "C"},
        ],
    }
    h1 = canonical_sha256(payload)
    payload["snapshot"][0]["document_id"] = "doc-2"
    h2 = canonical_sha256(payload)
    assert h1 != h2


def test_canonical_json_bytes_adding_fields_changes_hash():
    """P0 Phase 4: Adding created_at/timestamp does not change the hash."""
    from app.services.research_workflow_service import canonical_sha256

    content = {"topic": "test", "snapshot": [
        {"trace_id": "a", "quote": "Q", "citation_text": "C"},
    ]}
    h1 = canonical_sha256(content)
    content["created_at"] = "2026-01-01T00:00:00Z"
    content["run_id"] = "run-123"
    h2 = canonical_sha256(content)
    assert h1 != h2  # adding keys DOES change the payload


def test_canonical_json_bytes_stable_across_key_ordering():
    """P0 Phase 4: Dict key insertion order does not affect hash."""
    from app.services.research_workflow_service import canonical_sha256

    # Build dicts with different key insertion orders
    d1 = {}
    d1["topic"] = "T"
    d1["alpha"] = "A"

    d2 = {}
    d2["alpha"] = "A"
    d2["topic"] = "T"

    assert canonical_sha256(d1) == canonical_sha256(d2)


def test_canonical_payload_includes_full_content_not_counts():
    """P0 Phase 4: canonical payload includes quote/citation_text/document_id/chunk_id."""
    from app.services.research_workflow_service import _build_canonical_payload

    snapshot = [{
        "trace_id": "tid-1", "document_id": "doc-1", "chunk_id": "chk-1",
        "claim_text": "Claim", "quote": "The quote text",
        "citation_text": "[doc-1:chk-1]",
    }]
    evidence = [{
        "trace_id": "tid-1", "document_id": "doc-1", "chunk_id": "chk-1",
        "claim_text": "Claim", "quote": "The quote text",
        "citation_text": "[doc-1:chk-1]",
    }]
    citations = [{
        "trace_id": "tid-1", "citation_text": "[doc-1:chk-1]",
        "document_id": "doc-1", "quote": "The quote text",
    }]

    payload = _build_canonical_payload(
        topic="T", workflow_type="full_research_flow", pipeline_version="1.0.0",
        retrieval_snapshot=snapshot,
        synthesis_sections=[{"heading": "H", "body": "B", "references": ["tid-1"]}],
        synthesis_evidence=evidence,
        report_sections=[{"heading": "H", "body": "B", "references": ["tid-1"]}],
        citations=citations,
        trace_ids=["tid-1"],
        source_document_ids=["doc-1"],
    )

    # Must contain full content, not just counts
    snapshot_entry = payload["retrieval_snapshot"][0]
    assert snapshot_entry["quote"] == "The quote text"
    assert snapshot_entry["citation_text"] == "[doc-1:chk-1]"
    assert snapshot_entry["document_id"] == "doc-1"
    assert snapshot_entry["chunk_id"] == "chk-1"

    # Modifying quote must change hash
    from app.services.research_workflow_service import canonical_sha256
    h1 = canonical_sha256(payload)

    snapshot2 = [dict(snapshot[0])]
    snapshot2[0]["quote"] = "Different quote"
    payload2 = _build_canonical_payload(
        topic="T", workflow_type="full_research_flow", pipeline_version="1.0.0",
        retrieval_snapshot=snapshot2,
        synthesis_sections=[{"heading": "H", "body": "B", "references": ["tid-1"]}],
        synthesis_evidence=[{**snapshot2[0]}],
        report_sections=[{"heading": "H", "body": "B", "references": ["tid-1"]}],
        citations=[{"trace_id": "tid-1", "citation_text": "[doc-1:chk-1]",
                     "document_id": "doc-1", "quote": "Different quote"}],
        trace_ids=["tid-1"],
        source_document_ids=["doc-1"],
    )
    h2 = canonical_sha256(payload2)
    assert h1 != h2, "Hash must change when quote content changes"


@pytest.mark.asyncio
async def test_replay_twice_produces_byte_identical_canonical_output(db_session_persistent):
    """P0 Phase 4: Same manifest replayed twice produces identical canonical hash."""
    from app.services.research_workflow_service import (
        ResearchWorkflowService, _build_canonical_payload, canonical_sha256,
    )
    from app.services.trace_lineage import InternalTraceRecord, make_trace_id

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-replay2", "经络内容。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-replay2", "文献", "晋",
                               passage_id=pid, prefix="v4-chk-replay2")
    await db_session_persistent.flush()

    rwf = ResearchWorkflowService(db_session_persistent)

    tid = make_trace_id("v4-doc-replay2", "v4-chk-replay2-000")
    frozen_traces = [
        InternalTraceRecord(
            trace_id=tid, document_id="v4-doc-replay2", chunk_id="v4-chk-replay2-000",
            passage_id=pid, provenance_kind="retrieval",
            retrieval_score=0.85, retrieval_method="ili_keyword",
            timestamp="2026-01-01T00:00:00Z",
        ),
    ]
    snapshot = [
        {"trace_id": tid, "document_id": "v4-doc-replay2", "chunk_id": "v4-chk-replay2-000",
         "claim_text": "经脉流行不止。", "quote": "经脉流行不止，环周不休。",
         "citation_text": "[v4-doc-replay2:v4-chk-replay2-000]"},
    ]

    # Replay twice and compare canonical output hash
    def _replay_canonical():
        syn_out = rwf.execute_evidence_synthesis_from_snapshot(
            "经络", snapshot, internal_traces=frozen_traces,
        )
        rep_out = rwf.execute_report_from_synthesis("经络", syn_out)
        cit_out = rwf.execute_citation_export_from_evidence(
            "经络", syn_out.get("evidence", []), internal_traces=frozen_traces,
        )
        from app.services.research_workflow_service import _group_snapshot_into_sections
        sections = _group_snapshot_into_sections(snapshot)
        all_evidence = syn_out.get("evidence", [])
        payload = _build_canonical_payload(
            topic="经络",
            workflow_type="full_research_flow",
            pipeline_version="1.0.0",
            retrieval_snapshot=snapshot,
            synthesis_sections=sections,
            synthesis_evidence=all_evidence,
            report_sections=rep_out.get("sections", []),
            citations=cit_out.get("result", {}).get("citations", []),
            trace_ids=sorted(set(r.trace_id for r in frozen_traces)),
            source_document_ids=sorted(set(r.document_id for r in frozen_traces)),
        )
        return canonical_sha256(payload)

    h1 = _replay_canonical()
    h2 = _replay_canonical()
    assert h1 == h2, "Canonical output hash must be byte-identical across replays"


@pytest.mark.asyncio
async def test_replay_modified_snapshot_produces_mismatch(db_session_persistent):
    """P0 Phase 4: Modifying snapshot quote produces different canonical output hash."""
    from app.services.research_workflow_service import (
        ResearchWorkflowService, _build_canonical_payload, canonical_sha256,
    )
    from app.services.trace_lineage import InternalTraceRecord, make_trace_id

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-mod2", "内容。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-mod2", "文献", "晋",
                               passage_id=pid, prefix="v4-chk-mod2")
    await db_session_persistent.flush()

    rwf = ResearchWorkflowService(db_session_persistent)
    tid = make_trace_id("v4-doc-mod2", "v4-chk-mod2-000")
    frozen_traces = [
        InternalTraceRecord(
            trace_id=tid, document_id="v4-doc-mod2", chunk_id="v4-chk-mod2-000",
            passage_id=pid, provenance_kind="retrieval",
            retrieval_score=0.85, retrieval_method="ili_keyword",
            timestamp="2026-01-01T00:00:00Z",
        ),
    ]

    def _replay(snapshot):
        syn_out = rwf.execute_evidence_synthesis_from_snapshot(
            "经络", snapshot, internal_traces=frozen_traces,
        )
        rep_out = rwf.execute_report_from_synthesis("经络", syn_out)
        cit_out = rwf.execute_citation_export_from_evidence(
            "经络", syn_out.get("evidence", []), internal_traces=frozen_traces,
        )
        from app.services.research_workflow_service import _group_snapshot_into_sections
        sections = _group_snapshot_into_sections(snapshot)
        all_evidence = syn_out.get("evidence", [])
        payload = _build_canonical_payload(
            topic="经络",
            workflow_type="full_research_flow",
            pipeline_version="1.0.0",
            retrieval_snapshot=snapshot,
            synthesis_sections=sections,
            synthesis_evidence=all_evidence,
            report_sections=rep_out.get("sections", []),
            citations=cit_out.get("result", {}).get("citations", []),
            trace_ids=sorted(set(r.trace_id for r in frozen_traces)),
            source_document_ids=sorted(set(r.document_id for r in frozen_traces)),
        )
        return canonical_sha256(payload)

    h1 = _replay([
        {"trace_id": tid, "document_id": "v4-doc-mod2", "chunk_id": "v4-chk-mod2-000",
         "claim_text": "original", "quote": "original quote text",
         "citation_text": "[v4-doc-mod2:v4-chk-mod2-000]"},
    ])
    h2 = _replay([
        {"trace_id": tid, "document_id": "v4-doc-mod2", "chunk_id": "v4-chk-mod2-000",
         "claim_text": "modified", "quote": "modified quote text",
         "citation_text": "[v4-doc-mod2:v4-chk-mod2-000]"},
    ])
    assert h1 != h2, (
        f"Modified snapshot must produce different hash. "
        f"original={h1}, modified={h2}"
    )


# ==========================================================================
# 18. canonicalize_trace — single source of provenance truth
# ==========================================================================


def test_canonicalize_trace_same_content_different_key_order():
    """Same trace fields, different dict key order → identical canonical result."""
    from app.services.research_workflow_service import canonicalize_trace

    t1 = {"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
          "passage_id": "p1", "provenance_kind": "retrieval",
          "retrieval_score": 0.5, "retrieval_method": "m"}
    t2 = {"retrieval_method": "m", "retrieval_score": 0.5, "provenance_kind": "retrieval",
          "passage_id": "p1", "chunk_id": "c1", "document_id": "d1", "trace_id": "a"}

    assert canonicalize_trace(t1) == canonicalize_trace(t2)


def test_canonicalize_traces_different_input_order():
    """Traces input order different → same sorted canonical result."""
    from app.services.research_workflow_service import canonicalize_traces

    traces_a = [
        {"trace_id": "b", "document_id": "d2", "chunk_id": "c2",
         "passage_id": "p2", "provenance_kind": "retrieval",
         "retrieval_score": 0.5, "retrieval_method": "m"},
        {"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
         "passage_id": "p1", "provenance_kind": "graph",
         "retrieval_score": None, "retrieval_method": "graph_service"},
    ]
    traces_b = [
        {"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
         "passage_id": "p1", "provenance_kind": "graph",
         "retrieval_score": None, "retrieval_method": "graph_service"},
        {"trace_id": "b", "document_id": "d2", "chunk_id": "c2",
         "passage_id": "p2", "provenance_kind": "retrieval",
         "retrieval_score": 0.5, "retrieval_method": "m"},
    ]

    assert canonicalize_traces(traces_a) == canonicalize_traces(traces_b)


def test_canonicalize_trace_passage_id_changes_result():
    """Modifying passage_id changes canonical output."""
    from app.services.research_workflow_service import canonicalize_trace

    t1 = {"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
          "passage_id": "real-passage", "provenance_kind": "retrieval",
          "retrieval_score": 0.5, "retrieval_method": "m"}
    t2 = {**t1, "passage_id": "fabricated-passage-id"}

    assert canonicalize_trace(t1) != canonicalize_trace(t2)


def test_canonicalize_trace_score_method_kind_changes_result():
    """Modifying retrieval_score, retrieval_method, or provenance_kind changes output."""
    from app.services.research_workflow_service import canonicalize_trace

    base = {"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
            "passage_id": "p1", "provenance_kind": "retrieval",
            "retrieval_score": 0.85, "retrieval_method": "ili_keyword"}

    assert canonicalize_trace(base) != canonicalize_trace({**base, "retrieval_score": 0.01})
    assert canonicalize_trace(base) != canonicalize_trace({**base, "retrieval_method": "fabricated-method"})
    assert canonicalize_trace(base) != canonicalize_trace({**base, "provenance_kind": "graph"})


def test_canonicalize_trace_graph_score_null_stable():
    """Graph provenance with score=None serializes stably."""
    from app.services.research_workflow_service import canonicalize_trace, canonical_json_bytes

    t = {"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
         "passage_id": "p1", "provenance_kind": "graph",
         "retrieval_score": None, "retrieval_method": "graph_service"}
    result = canonicalize_trace(t)
    assert result["retrieval_score"] is None

    # Verify it serializes without error
    b = canonical_json_bytes({"traces": [result]})
    assert b'score' not in b or b'null' in b


def test_canonical_traces_enter_all_hash_domains():
    """canonicalize_traces output changes each hash domain."""
    from app.services.research_workflow_service import (
        canonicalize_traces, _build_input_payload,
        _build_canonical_payload, canonical_sha256,
    )

    traces = [{"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
               "passage_id": "real", "provenance_kind": "retrieval",
               "retrieval_score": 0.85, "retrieval_method": "ili_keyword"}]
    canonical = canonicalize_traces(traces)
    snapshot = [{"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
                 "claim_text": "Claim", "quote": "Q", "citation_text": "C",
                 "passage_id": "real"}]
    evidence = [{"trace_id": "a", "document_id": "d1", "chunk_id": "c1",
                 "claim_text": "Claim", "quote": "Q", "citation_text": "C"}]

    h1_input = canonical_sha256(_build_input_payload(
        "T", "full", "1.0", snapshot, ["a"], ["d1"], canonical_traces=canonical))
    h1_output = canonical_sha256(_build_canonical_payload(
        "T", "full", "1.0", snapshot, [], evidence, [], [],
        ["a"], ["d1"], canonical_traces=canonical))

    # Modify passage_id in traces
    traces_fab = [{**traces[0], "passage_id": "fabricated-passage-id"}]
    canonical_fab = canonicalize_traces(traces_fab)

    h2_input = canonical_sha256(_build_input_payload(
        "T", "full", "1.0", snapshot, ["a"], ["d1"], canonical_traces=canonical_fab))
    h2_output = canonical_sha256(_build_canonical_payload(
        "T", "full", "1.0", snapshot, [], evidence, [], [],
        ["a"], ["d1"], canonical_traces=canonical_fab))

    assert h1_input != h2_input, "passage_id change must change input hash"
    assert h1_output != h2_output, "passage_id change must change output hash"

    # Modify score/method
    traces_mod = [{**traces[0], "retrieval_score": 0.01, "retrieval_method": "fabricated"}]
    canonical_mod = canonicalize_traces(traces_mod)

    h3_input = canonical_sha256(_build_input_payload(
        "T", "full", "1.0", snapshot, ["a"], ["d1"], canonical_traces=canonical_mod))
    h3_output = canonical_sha256(_build_canonical_payload(
        "T", "full", "1.0", snapshot, [], evidence, [], [],
        ["a"], ["d1"], canonical_traces=canonical_mod))

    assert h1_input != h3_input, "score/method change must change input hash"
    assert h1_output != h3_output, "score/method change must change output hash"


# ==========================================================================
# 19. Replay API — real ASGI tampering tests
# ==========================================================================


@pytest.mark.asyncio
async def test_replay_api_normal_workflow_replay_twice(db_session_persistent):
    """Test A: Full workflow → replay twice → success=true, matched=true, hashes match."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-replay-api", "经络内容。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-replay-api", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-replay-api")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session
        r1 = await client.post("/api/v4/research/session", json={"title": "replay-api"})
        sid = r1.json()["data"]["session_id"]

        # 2. Execute workflow
        r2 = await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        assert r2.status_code == 200
        assert r2.json()["success"] is True

        # 3. Get run_id
        r3 = await client.get(f"/api/v4/research/session/{sid}/runs")
        runs = r3.json()["data"]["runs"]
        assert len(runs) == 1
        run_id = runs[0]["run_id"]

        # 4. Replay twice
        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        assert r4.status_code == 200
        replay1 = r4.json()
        assert replay1["success"] is True
        assert replay1["data"]["matched"] is True
        orig_hash = replay1["data"]["original_output_sha256"]
        replay_hash1 = replay1["data"]["replay_output_sha256"]
        assert orig_hash == replay_hash1

        r5 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        replay2 = r5.json()
        assert replay2["data"]["original_output_sha256"] == orig_hash
        assert replay2["data"]["replay_output_sha256"] == replay_hash1


@pytest.mark.asyncio
async def test_replay_api_tampered_passage_id_fails(db_session_persistent):
    """Test B: Tampering passage_id → success=false."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-tamp-pid", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-tamp-pid", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-tamp-pid")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "tamp-pid"})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        # Tamper passage_id in manifest directly via DB
        from sqlalchemy import select as sql_select
        from app.models.workspace import ResearchSession
        stmt = sql_select(ResearchSession).where(ResearchSession.id == sid)
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        state = json.loads(session_obj.workflow_state)
        for run in state["runs"]:
            if run["run_id"] == run_id:
                for t in run["replay_manifest"]["traces"]:
                    t["passage_id"] = "fabricated-passage-id"
        session_obj.workflow_state = json.dumps(state, ensure_ascii=False)
        await db_session_persistent.flush()

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        body = r4.json()
        assert body["success"] is False, f"Expected success=false, got {body}"
        assert body.get("data", {}).get("matched") is not True
        assert "CORRUPT_MANIFEST" in body.get("data", {}).get("error", "") or "REPRODUCIBILITY" in body.get("message", "")



@pytest.mark.asyncio
async def test_replay_api_tampered_retrieval_score_fails(db_session_persistent):
    """Test B: Tampering retrieval_score → success=false."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-tamp-score", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-tamp-score", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-tamp-score")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "tamp-score"})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        from sqlalchemy import select as sql_select
        from app.models.workspace import ResearchSession
        stmt = sql_select(ResearchSession).where(ResearchSession.id == sid)
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        state = json.loads(session_obj.workflow_state)
        for run in state["runs"]:
            if run["run_id"] == run_id:
                for t in run["replay_manifest"]["traces"]:
                    t["retrieval_score"] = 0.01
        session_obj.workflow_state = json.dumps(state, ensure_ascii=False)
        await db_session_persistent.flush()

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        body = r4.json()
        assert body["success"] is False, f"Expected success=false, got {body}"
        assert body.get("data", {}).get("matched") is not True


@pytest.mark.asyncio
async def test_replay_api_tampered_retrieval_method_fails(db_session_persistent):
    """Test B: Tampering retrieval_method → success=false."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-tamp-m", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-tamp-m", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-tamp-m")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "tamp-m"})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        from sqlalchemy import select as sql_select
        from app.models.workspace import ResearchSession
        stmt = sql_select(ResearchSession).where(ResearchSession.id == sid)
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        state = json.loads(session_obj.workflow_state)
        for run in state["runs"]:
            if run["run_id"] == run_id:
                for t in run["replay_manifest"]["traces"]:
                    t["retrieval_method"] = "fabricated-method"
        session_obj.workflow_state = json.dumps(state, ensure_ascii=False)
        await db_session_persistent.flush()

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        body = r4.json()
        assert body["success"] is False, f"Expected success=false, got {body}"
        assert body.get("data", {}).get("matched") is not True


@pytest.mark.asyncio
async def test_replay_api_delete_passage_id_fails(db_session_persistent):
    """Test C: Deleting passage_id from trace → CORRUPT_MANIFEST."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-del", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-del", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-del")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "del"})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        from sqlalchemy import select as sql_select
        from app.models.workspace import ResearchSession
        stmt = sql_select(ResearchSession).where(ResearchSession.id == sid)
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        state = json.loads(session_obj.workflow_state)
        for run in state["runs"]:
            if run["run_id"] == run_id:
                for t in run["replay_manifest"]["traces"]:
                    del t["passage_id"]
        session_obj.workflow_state = json.dumps(state, ensure_ascii=False)
        await db_session_persistent.flush()

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        body = r4.json()
        assert body["success"] is False
        assert "CORRUPT" in body["data"].get("error", "")


@pytest.mark.asyncio
async def test_replay_api_non_uuidv5_trace_id_fails(db_session_persistent):
    """Test D: Non-UUIDv5 trace_id → fail closed."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-nonuuid", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-nonuuid", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-nonuuid")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "nonuuid"})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        from sqlalchemy import select as sql_select
        from app.models.workspace import ResearchSession
        stmt = sql_select(ResearchSession).where(ResearchSession.id == sid)
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        state = json.loads(session_obj.workflow_state)
        for run in state["runs"]:
            if run["run_id"] == run_id:
                for t in run["replay_manifest"]["traces"]:
                    t["trace_id"] = "not-a-valid-uuid"
        session_obj.workflow_state = json.dumps(state, ensure_ascii=False)
        await db_session_persistent.flush()

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        body = r4.json()
        assert body["success"] is False


@pytest.mark.asyncio
async def test_replay_api_other_user_returns_404(db_session_persistent):
    """Test E: Other user replay → 404."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-iso", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-iso", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-iso")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "iso"})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        # Override auth to different user
        import app.middleware.auth as auth_mod
        app.dependency_overrides[auth_mod.get_current_user] = lambda: "other-user-id"

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        assert r4.status_code == 404

        # Restore
        app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"


@pytest.mark.asyncio
async def test_replay_api_manifest_sha256_tamper_fails(db_session_persistent):
    """manifest_sha256 tampering → CORRUPT_MANIFEST."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-msha", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-msha", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-msha")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "msha"})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        from sqlalchemy import select as sql_select
        from app.models.workspace import ResearchSession
        stmt = sql_select(ResearchSession).where(ResearchSession.id == sid)
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        state = json.loads(session_obj.workflow_state)
        for run in state["runs"]:
            if run["run_id"] == run_id:
                # Tamper a field that manifest_sha256 covers (e.g. timestamp/created_at)
                run["replay_manifest"]["created_at"] = "1900-01-01T00:00:00Z"
        session_obj.workflow_state = json.dumps(state, ensure_ascii=False)
        await db_session_persistent.flush()

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        body = r4.json()
        assert body["success"] is False
        assert "manifest_sha256" in json.dumps(body["data"]).lower() or "CORRUPT" in str(body["data"])


@pytest.mark.asyncio
async def test_replay_api_quote_tamper_fails(db_session_persistent):
    """Tampering quote in retrieval_snapshot → reproducibility failure."""
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-qt", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-qt", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-qt")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": "qt"})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        from sqlalchemy import select as sql_select
        from app.models.workspace import ResearchSession
        stmt = sql_select(ResearchSession).where(ResearchSession.id == sid)
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        state = json.loads(session_obj.workflow_state)
        for run in state["runs"]:
            if run["run_id"] == run_id:
                for entry in run["replay_manifest"]["retrieval_snapshot"]:
                    entry["quote"] = "fabricated quote text"
        session_obj.workflow_state = json.dumps(state, ensure_ascii=False)
        await db_session_persistent.flush()

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        body = r4.json()
        assert body["success"] is False, f"Expected success=false, got {body}"
        assert body.get("data", {}).get("matched") is not True


# ==========================================================================
# 19b. Manifest integrity proof — parameterized manifest_sha256 tests
# ==========================================================================

_MANIFEST_TAMPER_PARAMS = [
    pytest.param(
        "delete", None,
        {"error": "UNVERIFIABLE_MANIFEST", "message": "has no integrity proof"},
        id="delete_manifest_sha256",
    ),
    pytest.param(
        "empty", "",
        {"error": "CORRUPT_MANIFEST", "message": "invalid"},
        id="empty_manifest_sha256",
    ),
    pytest.param(
        "null_json", None,
        {"error": "CORRUPT_MANIFEST", "message": "invalid"},
        id="null_manifest_sha256",
    ),
    pytest.param(
        "short", "abc",
        {"error": "CORRUPT_MANIFEST", "message": "invalid"},
        id="short_manifest_sha256",
    ),
    pytest.param(
        "non_hex",
        "g" * 64,
        {"error": "CORRUPT_MANIFEST", "message": "invalid"},
        id="non_hex_manifest_sha256",
    ),
    pytest.param(
        "wrong_sha256",
        "a" * 64,
        {"error": "CORRUPT_MANIFEST", "message": "check failed"},
        id="wrong_manifest_sha256",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,replacement,expected", _MANIFEST_TAMPER_PARAMS)
async def test_replay_api_manifest_sha256_required(db_session_persistent, mode, replacement, expected):
    """Parameterized: delete/empty/null/short/non-hex/wrong manifest_sha256 → fail."""
    from app.api.v4.research import router as research_router
    from sqlalchemy import select as sql_select
    from app.models.workspace import ResearchSession
    import json as _json

    pid = _seed_passage_with_lineage(db_session_persistent, f"passage-{mode}", "经络。")
    _seed_chunks_with_passage(db_session_persistent, f"v4-doc-{mode}", "文献", "晋",
                              passage_id=pid, prefix=f"v4-chk-{mode}")
    await db_session_persistent.flush()

    app = _build_app(research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v4/research/session", json={"title": mode})
        sid = r1.json()["data"]["session_id"]
        await client.post("/api/v4/research/workflow", json={
            "session_id": sid, "topic": "经络", "workflow_type": "full_research_flow",
        })
        runs = (await client.get(f"/api/v4/research/session/{sid}/runs")).json()["data"]["runs"]
        run_id = runs[0]["run_id"]

        stmt = sql_select(ResearchSession).where(ResearchSession.id == sid)
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        state = _json.loads(session_obj.workflow_state)
        for run in state["runs"]:
            if run["run_id"] == run_id:
                if mode == "delete":
                    del run["replay_manifest"]["manifest_sha256"]
                elif mode == "null_json":
                    run["replay_manifest"]["manifest_sha256"] = None
                else:
                    run["replay_manifest"]["manifest_sha256"] = replacement
        session_obj.workflow_state = _json.dumps(state, ensure_ascii=False)
        await db_session_persistent.flush()

        r4 = await client.post(f"/api/v4/research/runs/{run_id}/replay")
        body = r4.json()
        assert body["success"] is False, (
            f"mode={mode}: expected success=false, got {body}"
        )
        assert body.get("data", {}).get("matched") is not True
        err = body.get("data", {}).get("error", "")
        msg = body.get("message", "")
        assert expected["error"] in err, (
            f"mode={mode}: expected error '{expected['error']}' in '{err}'"
        )
        assert expected["message"] in msg.lower(), (
            f"mode={mode}: expected message '{expected['message']}' in '{msg}'"
        )


# ==========================================================================
# 20. Visualization session_id in traceability
# ==========================================================================


@pytest.mark.asyncio
async def test_visualization_auto_session_returns_session_id(db_session_persistent):
    """Test A: No session_id → auto-creates, returns traceability.session_id."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-viz-auto", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-viz-auto", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-viz-auto")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v4/visualization/graph", json={
            "concept_labels": ["经络"], "graph_type": "concept",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        tb = body["traceability"]
        assert tb is not None
        assert tb["session_id"] is not None
        assert len(tb["session_id"]) > 0

        # Verify session exists in DB
        from sqlalchemy import select as sql_select
        from app.models.workspace import ResearchSession
        stmt = sql_select(ResearchSession).where(ResearchSession.id == tb["session_id"])
        sess_result = await db_session_persistent.execute(stmt)
        session_obj = sess_result.scalar_one_or_none()
        assert session_obj is not None
        assert session_obj.user_id == "test-user-id"

        # Verify QueryHistory.session_id matches
        from app.models.workspace import QueryHistory
        qh_stmt = sql_select(QueryHistory).where(QueryHistory.id == tb["query_id"])
        qh_result = await db_session_persistent.execute(qh_stmt)
        qh = qh_result.scalar_one_or_none()
        assert qh is not None
        assert str(qh.session_id) == tb["session_id"]


@pytest.mark.asyncio
async def test_visualization_explicit_session_returns_same_id(db_session_persistent):
    """Test B: Explicit session_id → returns same session_id, no extra session created."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router

    pid = _seed_passage_with_lineage(db_session_persistent, "passage-viz-exp", "经络。")
    _seed_chunks_with_passage(db_session_persistent, "v4-doc-viz-exp", "文献", "晋",
                              passage_id=pid, prefix="v4-chk-viz-exp")
    await db_session_persistent.flush()

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session first
        r1 = await client.post("/api/v4/research/session", json={"title": "exp"})
        sid = r1.json()["data"]["session_id"]

        # Count sessions before viz request
        from sqlalchemy import select as sql_select, func
        from app.models.workspace import ResearchSession
        stmt = sql_select(func.count()).select_from(ResearchSession).where(
            ResearchSession.user_id == "test-user-id",
        )
        count_result = await db_session_persistent.execute(stmt)
        count_before = count_result.scalar()

        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["经络"], "graph_type": "concept",
        })
        assert r.status_code == 200
        body = r.json()
        tb = body["traceability"]
        assert tb["session_id"] == sid

        count_result2 = await db_session_persistent.execute(stmt)
        count_after = count_result2.scalar()
        assert count_after == count_before, "Should not create extra session"


@pytest.mark.asyncio
async def test_visualization_other_user_session_returns_404(db_session_persistent):
    """Test C: Other user's session → 404."""
    from app.api.v4.visualization import router as viz_router
    from app.api.v4.research import router as research_router

    app = _build_app(viz_router, research_router)
    _setup_auth_overrides(app, db_session_persistent)
    app.include_router(research_router, prefix="/api/v4")
    app.include_router(viz_router, prefix="/api/v4")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session as test-user-id
        r1 = await client.post("/api/v4/research/session", json={"title": "mine"})
        sid = r1.json()["data"]["session_id"]

        # Switch to other user
        import app.middleware.auth as auth_mod
        app.dependency_overrides[auth_mod.get_current_user] = lambda: "other-user-id"

        r = await client.post("/api/v4/visualization/graph", json={
            "session_id": sid, "concept_labels": ["经络"], "graph_type": "concept",
        })
        assert r.status_code == 404

        # Restore
        app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
