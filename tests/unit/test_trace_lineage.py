"""Unit tests for trace_lineage — pure functions, validators, async DB functions."""

from __future__ import annotations

import json as _json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.trace_lineage import (
    InternalTraceRecord,
    ResolvedTrace,
    TraceLineageError,
    _is_valid_score,
    _is_valid_uuidv5,
    build_internal_traces,
    build_viz_traces,
    extract_source_documents,
    extract_trace_ids,
    make_trace_id,
    passage_mapping_stats,
    resolve_time_evidence,
    resolve_trace_lineage,
)


class TestMakeTraceId:
    def test_same_inputs_same_output(self) -> None:
        a = make_trace_id("doc-1", "chk-1")
        b = make_trace_id("doc-1", "chk-1")
        assert a == b
        assert isinstance(a, str)

    def test_different_inputs_different_output(self) -> None:
        a = make_trace_id("doc-1", "chk-1")
        b = make_trace_id("doc-2", "chk-1")
        assert a != b

    def test_output_is_valid_uuid5(self) -> None:
        tid = make_trace_id("d", "c")
        assert _is_valid_uuidv5(tid)


class TestIsValidUuidV5:
    def test_valid(self) -> None:
        tid = str(uuid.uuid5(uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), "test"))
        assert _is_valid_uuidv5(tid) is True

    def test_uuid4_is_invalid(self) -> None:
        assert _is_valid_uuidv5(str(uuid.uuid4())) is False

    def test_garbage_is_invalid(self) -> None:
        assert _is_valid_uuidv5("not-a-uuid") is False
        assert _is_valid_uuidv5("") is False


class TestIsValidScore:
    def test_valid_range(self) -> None:
        assert _is_valid_score(0.0) is True
        assert _is_valid_score(0.5) is True
        assert _is_valid_score(1.0) is True

    def test_out_of_range(self) -> None:
        assert _is_valid_score(1.1) is False
        assert _is_valid_score(-0.1) is False

    def test_nan_inf(self) -> None:
        assert _is_valid_score(float("nan")) is False
        assert _is_valid_score(float("inf")) is False

    def test_non_number(self) -> None:
        assert _is_valid_score(None) is False  # type: ignore[arg-type]
        assert _is_valid_score("0.5") is False  # type: ignore[arg-type]


class TestInternalTraceRecord:
    def test_valid_retrieval_record(self) -> None:
        tid = make_trace_id("doc-1", "chk-1")
        record = InternalTraceRecord(
            trace_id=tid,
            document_id="doc-1",
            chunk_id="chk-1",
            passage_id="passage-1",
            provenance_kind="retrieval",
            retrieval_score=0.85,
            retrieval_method="ili_keyword",
            timestamp="2025-01-01T00:00:00",
        )
        assert record.trace_id == tid
        assert record.retrieval_score == 0.85

    def test_valid_graph_record(self) -> None:
        tid = make_trace_id("doc-2", "chk-2")
        record = InternalTraceRecord(
            trace_id=tid,
            document_id="doc-2",
            chunk_id="chk-2",
            passage_id="passage-2",
            provenance_kind="graph",
            retrieval_score=None,
            retrieval_method="graph_service",
            timestamp="2025-01-01T00:00:00",
        )
        assert record.provenance_kind == "graph"
        assert record.retrieval_score is None

    def test_invalid_provenance_kind_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError):
            InternalTraceRecord(
                trace_id=tid,
                document_id="d",
                chunk_id="c",
                passage_id="p",
                provenance_kind="unknown",
                retrieval_score=0.5,
                retrieval_method="m",
                timestamp="t",
            )

    def test_retrieval_with_none_score_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError):
            InternalTraceRecord(
                trace_id=tid,
                document_id="d",
                chunk_id="c",
                passage_id="p",
                provenance_kind="retrieval",
                retrieval_score=None,
                retrieval_method="m",
                timestamp="t",
            )

    def test_graph_with_score_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError):
            InternalTraceRecord(
                trace_id=tid,
                document_id="d",
                chunk_id="c",
                passage_id="p",
                provenance_kind="graph",
                retrieval_score=0.5,
                retrieval_method="m",
                timestamp="t",
            )

    def test_to_dict(self) -> None:
        tid = make_trace_id("doc-x", "chk-x")
        record = InternalTraceRecord(
            trace_id=tid,
            document_id="doc-x",
            chunk_id="chk-x",
            passage_id="passage-x",
            provenance_kind="retrieval",
            retrieval_score=0.9,
            retrieval_method="keyword",
            timestamp="2025-06-01T00:00:00",
        )
        d = record.to_dict()
        assert d["trace_id"] == tid
        assert d["retrieval_score"] == 0.9


class TestInternalTraceRecordValidation:
    """Additional validation edge cases."""

    def test_empty_document_id_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError, match="document_id"):
            InternalTraceRecord(
                trace_id=tid, document_id="", chunk_id="c", passage_id="p",
                provenance_kind="graph", retrieval_score=None,
                retrieval_method="graph_service", timestamp="2025-01-01T00:00:00",
            )

    def test_empty_chunk_id_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError, match="chunk_id"):
            InternalTraceRecord(
                trace_id=tid, document_id="d", chunk_id="", passage_id="p",
                provenance_kind="graph", retrieval_score=None,
                retrieval_method="graph_service", timestamp="2025-01-01T00:00:00",
            )

    def test_empty_passage_id_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError, match="passage_id"):
            InternalTraceRecord(
                trace_id=tid, document_id="d", chunk_id="c", passage_id="",
                provenance_kind="graph", retrieval_score=None,
                retrieval_method="graph_service", timestamp="2025-01-01T00:00:00",
            )

    def test_empty_retrieval_method_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError, match="retrieval_method"):
            InternalTraceRecord(
                trace_id=tid, document_id="d", chunk_id="c", passage_id="p",
                provenance_kind="graph", retrieval_score=None,
                retrieval_method="", timestamp="2025-01-01T00:00:00",
            )

    def test_empty_timestamp_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError, match="timestamp"):
            InternalTraceRecord(
                trace_id=tid, document_id="d", chunk_id="c", passage_id="p",
                provenance_kind="graph", retrieval_score=None,
                retrieval_method="graph_service", timestamp="",
            )

    def test_retrieval_with_nan_score_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError):
            InternalTraceRecord(
                trace_id=tid, document_id="d", chunk_id="c", passage_id="p",
                provenance_kind="retrieval", retrieval_score=float("nan"),
                retrieval_method="m", timestamp="t",
            )

    def test_retrieval_with_negative_score_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError):
            InternalTraceRecord(
                trace_id=tid, document_id="d", chunk_id="c", passage_id="p",
                provenance_kind="retrieval", retrieval_score=-0.1,
                retrieval_method="m", timestamp="t",
            )

    def test_retrieval_with_over_one_score_raises(self) -> None:
        tid = make_trace_id("d", "c")
        with pytest.raises(ValueError):
            InternalTraceRecord(
                trace_id=tid, document_id="d", chunk_id="c", passage_id="p",
                provenance_kind="retrieval", retrieval_score=1.1,
                retrieval_method="m", timestamp="t",
            )

    def test_graph_with_none_score_valid(self) -> None:
        tid = make_trace_id("d", "c")
        record = InternalTraceRecord(
            trace_id=tid, document_id="d", chunk_id="c", passage_id="p",
            provenance_kind="graph", retrieval_score=None,
            retrieval_method="graph_service", timestamp="2025-01-01T00:00:00",
        )
        assert record.provenance_kind == "graph"
        assert record.retrieval_score is None


class MockEvidenceTrace:
    """Minimal EvidenceTrace-like object with document_id, chunk_id."""

    def __init__(self, document_id: str, chunk_id: str) -> None:
        self.document_id = document_id
        self.chunk_id = chunk_id


def _make_iter_mock(rows):
    """Create a MagicMock that iterates over `rows`."""
    m = MagicMock()
    m.__iter__.return_value = iter(rows)
    return m


class TestBuildInternalTraces:
    """Tests for build_internal_traces."""

    @pytest.mark.asyncio
    async def test_missing_retrieval_snapshot_raises(self) -> None:
        db = AsyncMock()
        traces = [MockEvidenceTrace("d1", "c1")]
        with pytest.raises(TraceLineageError, match="retrieval_snapshot"):
            await build_internal_traces(db, traces, retrieval_snapshot=None)

    @pytest.mark.asyncio
    async def test_chunk_not_in_snapshot_raises(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([])
        db.execute = AsyncMock(return_value=chunk_result)
        traces = [MockEvidenceTrace("d1", "c1")]
        snapshot = {}
        with pytest.raises(TraceLineageError, match="not in retrieval_snapshot"):
            await build_internal_traces(db, traces, retrieval_snapshot=snapshot)

    @pytest.mark.asyncio
    async def test_invalid_score_raises(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "p1")])
        db.execute = AsyncMock(return_value=chunk_result)
        traces = [MockEvidenceTrace("d1", "c1")]
        snapshot = {"c1": {"score": "bad", "retrieval_method": "keyword"}}
        with pytest.raises(TraceLineageError, match="invalid score"):
            await build_internal_traces(db, traces, retrieval_snapshot=snapshot)

    @pytest.mark.asyncio
    async def test_empty_method_raises(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "p1")])
        db.execute = AsyncMock(return_value=chunk_result)
        traces = [MockEvidenceTrace("d1", "c1")]
        snapshot = {"c1": {"score": 0.5, "retrieval_method": ""}}
        with pytest.raises(TraceLineageError, match="retrieval_method"):
            await build_internal_traces(db, traces, retrieval_snapshot=snapshot)

    @pytest.mark.asyncio
    async def test_missing_passage_id_skips_chunk(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "")])
        db.execute = AsyncMock(return_value=chunk_result)
        traces = [MockEvidenceTrace("d1", "c1")]
        snapshot = {"c1": {"score": 0.5, "retrieval_method": "keyword"}}
        result = await build_internal_traces(db, traces, retrieval_snapshot=snapshot)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_withdrawn_version_raises(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "p1")])
        ver_result = MagicMock()
        ver_result.one_or_none.return_value = ("2025-01-01",)
        db.execute = AsyncMock(side_effect=[chunk_result, ver_result])
        traces = [MockEvidenceTrace("d1", "c1")]
        snapshot = {"c1": {"score": 0.5, "retrieval_method": "keyword"}}
        with pytest.raises(TraceLineageError, match="withdrawn"):
            await build_internal_traces(db, traces, retrieval_snapshot=snapshot)

    @pytest.mark.asyncio
    async def test_successful_trace_building(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "p1")])
        ver_result = MagicMock()
        ver_result.one_or_none.return_value = (None,)
        db.execute = AsyncMock(side_effect=[chunk_result, ver_result])
        traces = [MockEvidenceTrace("d1", "c1")]
        snapshot = {"c1": {"score": 0.5, "retrieval_method": "keyword"}}
        result = await build_internal_traces(db, traces, retrieval_snapshot=snapshot)
        assert len(result) == 1
        assert result[0].trace_id == make_trace_id("d1", "c1")
        assert result[0].passage_id == "p1"
        assert result[0].retrieval_score == 0.5

    @pytest.mark.asyncio
    async def test_nan_score_in_snapshot_raises(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "p1")])
        db.execute = AsyncMock(return_value=chunk_result)
        traces = [MockEvidenceTrace("d1", "c1")]
        snapshot = {"c1": {"score": float("nan"), "retrieval_method": "keyword"}}
        with pytest.raises(TraceLineageError, match="invalid score"):
            await build_internal_traces(db, traces, retrieval_snapshot=snapshot)


class TestBuildVizTraces:
    """Tests for build_viz_traces."""

    @pytest.mark.asyncio
    async def test_missing_passage_id_raises(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "")])
        db.execute = AsyncMock(return_value=chunk_result)
        traces = [MockEvidenceTrace("d1", "c1")]
        with pytest.raises(TraceLineageError, match="no passage_id"):
            await build_viz_traces(db, traces)

    @pytest.mark.asyncio
    async def test_successful_viz_trace(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "p1")])
        db.execute = AsyncMock(return_value=chunk_result)
        traces = [MockEvidenceTrace("d1", "c1")]
        result = await build_viz_traces(db, traces)
        assert len(result) == 1
        assert result[0].trace_id == make_trace_id("d1", "c1")
        assert result[0].provenance_kind == "graph"
        assert result[0].retrieval_score is None
        assert result[0].retrieval_method == "graph_service"

    @pytest.mark.asyncio
    async def test_deduplicates_traces(self) -> None:
        db = AsyncMock()
        chunk_result = _make_iter_mock([("c1", "p1")])
        db.execute = AsyncMock(return_value=chunk_result)
        traces = [MockEvidenceTrace("d1", "c1"), MockEvidenceTrace("d1", "c1")]
        result = await build_viz_traces(db, traces)
        assert len(result) == 1


class MockTrace:
    """Minimal EvidenceTrace-like object for testing extractors."""

    def __init__(self, document_id: str, chunk_id: str) -> None:
        self.document_id = document_id
        self.chunk_id = chunk_id


class TestExtractTraceIds:
    def test_deduplicated(self) -> None:
        traces = [MockTrace("d1", "c1"), MockTrace("d1", "c1"), MockTrace("d2", "c2")]
        ids = extract_trace_ids(traces)  # type: ignore[arg-type]
        assert len(ids) == 2

    def test_skips_empty(self) -> None:
        traces = [MockTrace("", "c1"), MockTrace("d1", "")]
        ids = extract_trace_ids(traces)  # type: ignore[arg-type]
        assert len(ids) == 0


class TestExtractSourceDocuments:
    def test_sorted_deduplicated(self) -> None:
        traces = [MockTrace("b", "c1"), MockTrace("a", "c2"), MockTrace("b", "c3")]
        docs = extract_source_documents(traces)  # type: ignore[arg-type]
        assert docs == ["a", "b"]

    def test_skips_empty(self) -> None:
        traces = [MockTrace("", "c1")]
        docs = extract_source_documents(traces)  # type: ignore[arg-type]
        assert docs == []


class TestTraceLineageError:
    def test_is_exception(self) -> None:
        exc = TraceLineageError("test")
        assert isinstance(exc, Exception)


class TestResolvedTrace:
    """Tests for ResolvedTrace.to_public_dict."""

    def test_to_public_dict_with_passage(self) -> None:
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk
        from app.models.passage import Passage

        chunk = DocumentChunk(id="c1", document_id="d1", chunk_index=0, content="test")
        doc = Document(id="d1", title="Test Doc")
        passage = Passage(id="p1", content_text="passage text")
        rt = ResolvedTrace(
            trace_id="tid1", chunk=chunk, document=doc, passage=passage,
            passage_citation="《Test Doc》·v1", chunk_citation="[d1:0]",
        )
        d = rt.to_public_dict()
        assert d["trace_id"] == "tid1"
        assert d["document_id"] == "d1"
        assert d["document_title"] == "Test Doc"
        assert d["chunk_index"] == 0
        assert d["passage_id"] == "p1"
        assert d["citation"] == "《Test Doc》·v1"

    def test_to_public_dict_without_passage(self) -> None:
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk

        chunk = DocumentChunk(id="c1", document_id="d1", chunk_index=0, content="test")
        doc = Document(id="d1", title="Test Doc")
        rt = ResolvedTrace(
            trace_id="tid1", chunk=chunk, document=doc, passage=None,
            passage_citation="", chunk_citation="[d1:0]",
        )
        d = rt.to_public_dict()
        assert d["passage_id"] is None
        assert d["citation"] == "[d1:0]"


class TestResolveTraceLineage:
    """Tests for resolve_trace_lineage."""

    @pytest.mark.asyncio
    async def test_trace_not_found_raises(self) -> None:
        db = AsyncMock()
        qh_result = MagicMock()
        qh_result.scalar_one_or_none.return_value = None
        # brute force: chunks iteration
        chunks_iter = _make_iter_mock([])
        db.execute = AsyncMock(side_effect=[qh_result, chunks_iter])
        with pytest.raises(TraceLineageError, match="not found"):
            await resolve_trace_lineage(db, "nonexistent-tid")

    @pytest.mark.asyncio
    async def test_chunk_not_found_raises(self) -> None:
        db = AsyncMock()
        tid = make_trace_id("d1", "c1")

        qh = MagicMock()
        qh.result_summary = _json.dumps({"traces": [{"trace_id": tid, "chunk_id": "c1"}]})
        qh_result = MagicMock()
        qh_result.scalar_one_or_none.return_value = qh

        # chunk query returns None
        chunk_result = MagicMock()
        chunk_result.scalar_one_or_none.return_value = None

        db.execute = AsyncMock(side_effect=[qh_result, chunk_result])
        with pytest.raises(TraceLineageError, match="not found"):
            await resolve_trace_lineage(db, tid)


class TestPassageMappingStats:
    """Tests for passage_mapping_stats."""

    @pytest.mark.asyncio
    async def test_all_chunks_with_passage(self) -> None:
        db = AsyncMock()
        total_result = MagicMock()
        total_result.scalars.return_value.all.return_value = ["c1", "c2", "c3"]
        mapped_result = MagicMock()
        mapped_result.scalars.return_value.all.return_value = ["c1", "c2", "c3"]
        # chunks_with_passage > 0 triggers orphan check path
        # distinct passage_ids: pids have all(id,pid) tuples
        pids_result = MagicMock()
        pids_result.all.return_value = [("p1",), ("p2",), ("p3",)]
        # Passage exists — all found, 0 orphans
        exist_result = _make_iter_mock([("p1",), ("p2",), ("p3",)])
        db.execute = AsyncMock(side_effect=[total_result, mapped_result, pids_result, exist_result])
        stats = await passage_mapping_stats(db)
        assert stats["total_chunks"] == 3
        assert stats["chunks_with_passage"] == 3
        assert stats["chunks_without_passage"] == 0
        assert stats["orphan_passage_ids"] == 0

    @pytest.mark.asyncio
    async def test_orphan_passage_ids(self) -> None:
        db = AsyncMock()
        total_result = MagicMock()
        total_result.scalars.return_value.all.return_value = ["c1", "c2"]
        mapped_result = MagicMock()
        mapped_result.scalars.return_value.all.return_value = ["c1", "c2"]
        # distinct passage_ids — iterable
        pids_result = _make_iter_mock([("p1",), ("p2",)])
        # Passage exists check — iterable
        exist_result = _make_iter_mock([("p1",)])
        db.execute = AsyncMock(side_effect=[total_result, mapped_result, pids_result, exist_result])
        stats = await passage_mapping_stats(db)
        assert stats["orphan_passage_ids"] == 1


class TestResolveTimeEvidence:
    """Tests for resolve_time_evidence."""

    @pytest.mark.asyncio
    async def test_chunk_not_found_returns_none(self) -> None:
        db = AsyncMock()
        result = MagicMock()
        result.one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)
        r = await resolve_time_evidence(db, "d1", "c1")
        assert r is None

    @pytest.mark.asyncio
    async def test_passage_not_found_returns_none(self) -> None:
        db = AsyncMock()
        chunk_result = MagicMock()
        chunk_result.one_or_none.return_value = ("p1",)
        passage_result = MagicMock()
        passage_result.one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[chunk_result, passage_result])
        r = await resolve_time_evidence(db, "d1", "c1")
        assert r is None

    @pytest.mark.asyncio
    async def test_version_with_era_and_year(self) -> None:
        db = AsyncMock()
        chunk_result = MagicMock()
        chunk_result.one_or_none.return_value = ("p1",)
        passage_result = MagicMock()
        passage_result.one_or_none.return_value = ("v1",)
        version_result = MagicMock()
        version_result.one_or_none.return_value = ("宋", 960)
        db.execute = AsyncMock(side_effect=[chunk_result, passage_result, version_result])
        r = await resolve_time_evidence(db, "d1", "c1")
        assert r == {"era": "宋", "year": "960"}

    @pytest.mark.asyncio
    async def test_version_with_era_only(self) -> None:
        db = AsyncMock()
        chunk_result = MagicMock()
        chunk_result.one_or_none.return_value = ("p1",)
        passage_result = MagicMock()
        passage_result.one_or_none.return_value = ("v1",)
        version_result = MagicMock()
        version_result.one_or_none.return_value = ("宋", None)
        db.execute = AsyncMock(side_effect=[chunk_result, passage_result, version_result])
        r = await resolve_time_evidence(db, "d1", "c1")
        assert r == {"era": "宋"}

    @pytest.mark.asyncio
    async def test_version_with_year_only(self) -> None:
        db = AsyncMock()
        chunk_result = MagicMock()
        chunk_result.one_or_none.return_value = ("p1",)
        passage_result = MagicMock()
        passage_result.one_or_none.return_value = ("v1",)
        version_result = MagicMock()
        version_result.one_or_none.return_value = (None, 960)
        db.execute = AsyncMock(side_effect=[chunk_result, passage_result, version_result])
        r = await resolve_time_evidence(db, "d1", "c1")
        assert r == {"year": "960"}

    @pytest.mark.asyncio
    async def test_version_with_no_time_evidence_returns_none(self) -> None:
        db = AsyncMock()
        chunk_result = MagicMock()
        chunk_result.one_or_none.return_value = ("p1",)
        passage_result = MagicMock()
        passage_result.one_or_none.return_value = ("v1",)
        version_result = MagicMock()
        version_result.one_or_none.return_value = (None, None)
        db.execute = AsyncMock(side_effect=[chunk_result, passage_result, version_result])
        r = await resolve_time_evidence(db, "d1", "c1")
        assert r is None
