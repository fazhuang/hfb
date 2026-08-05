
"""Unit tests for trace_lineage — pure functions: make_trace_id, _is_valid_uuidv5, _is_valid_score."""

from __future__ import annotations

import math
import uuid

import pytest
from app.services.trace_lineage import (
    make_trace_id,
    _is_valid_uuidv5,
    _is_valid_score,
    InternalTraceRecord,
    extract_trace_ids,
    extract_source_documents,
    TraceLineageError,
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
