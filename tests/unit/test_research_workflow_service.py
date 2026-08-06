"""Unit tests for research_workflow_service pure functions and class-method branches.

Covers: _step_to_record, _group_snapshot_into_sections, _snapshot_to_evidence_list,
_build_report_sections, canonical_json_bytes, canonical_sha256, canonicalize_trace,
canonicalize_traces, _build_canonical_payload, _build_corpus_payload,
_build_input_payload, build_markdown_artifact (with-snapshot/evidence-only branches),
_escape_md, execute_* class methods, citation dedup.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.trace_lineage import InternalTraceRecord, make_trace_id

import pytest

from app.services.research_workflow_service import (
    _build_canonical_payload,
    _build_corpus_payload,
    _build_input_payload,
    _build_report_sections,
    _build_retrieval_snapshot,
    _group_snapshot_into_sections,
    _pack_academic_step,
    _snapshot_to_evidence_list,
    _step_to_record,
    ResearchWorkflowService,
    canonical_json_bytes,
    canonical_sha256,
    canonicalize_trace,
    canonicalize_traces,
)


# =============================================================================
# Helpers
# =============================================================================


def _snap(trace_id="trace-001", doc_id="doc-01", chunk_id="chk-01",
          claim="经络是运行气血的通道", quote="经络者，所以行血气而营阴阳。",
          citation="[doc-01:chk-01]") -> dict:
    return {
        "trace_id": trace_id,
        "document_id": doc_id,
        "chunk_id": chunk_id,
        "claim_text": claim,
        "quote": quote,
        "citation_text": citation,
    }


def _snap_with_extra(**kwargs) -> dict:
    base = {
        "trace_id": "trace-001",
        "document_id": "doc-01",
        "chunk_id": "chk-01",
        "claim_text": "Claim",
        "quote": "Quote text",
        "citation_text": "[doc-01:chk-01]",
    }
    # Normalize convenience aliases to canonical keys
    if "doc_id" in kwargs:
        kwargs["document_id"] = kwargs.pop("doc_id")
    if "claim" in kwargs:
        kwargs["claim_text"] = kwargs.pop("claim")
    if "citation" in kwargs:
        kwargs["citation_text"] = kwargs.pop("citation")
    base.update(kwargs)
    return base


def _make_mock_trace(tid="t1", did="doc-01", cid="chk-01",
                     pid="p1", score=0.95, method="kw"):
    """Create an object with .trace_id, .document_id, .to_dict() for trace passthrough."""
    class MockTrace:
        pass

    mt = MockTrace()
    mt.trace_id = tid
    mt.document_id = did
    mt.chunk_id = cid
    mt.passage_id = pid
    mt.provenance_kind = "retrieval"
    mt.retrieval_score = score
    mt.retrieval_method = method

    def to_dict():
        return {
            "trace_id": mt.trace_id,
            "document_id": mt.document_id,
            "chunk_id": mt.chunk_id,
            "passage_id": mt.passage_id,
            "provenance_kind": mt.provenance_kind,
            "retrieval_score": mt.retrieval_score,
            "retrieval_method": mt.retrieval_method,
        }

    mt.to_dict = to_dict
    return mt


# =============================================================================
# _step_to_record
# =============================================================================


class TestStepToRecord:
    """Cover dict branch and object branch including edge cases."""

    def test_dict_step(self):
        step = {
            "name": "literature_retrieval",
            "status": "completed",
            "started_at": "2026-01-01T00:00:00",
            "completed_at": "2026-01-01T00:01:00",
            "trace_ids": ["t1", "t2"],
            "extra_field": "ignored",
        }
        record = _step_to_record(step)
        assert record["step_name"] == "literature_retrieval"
        assert record["status"] == "completed"
        assert record["started_at"] == "2026-01-01T00:00:00"
        assert record["completed_at"] == "2026-01-01T00:01:00"
        assert record["trace_ids"] == ["t1", "t2"]
        assert "extra_field" not in record

    def test_dict_step_partial(self):
        step = {"name": "step-1"}
        record = _step_to_record(step)
        assert record["step_name"] == "step-1"
        assert record["status"] == ""
        assert record["started_at"] == ""
        assert record["completed_at"] == ""
        assert record["trace_ids"] == []

    def test_object_step_all_attrs(self):
        @dataclass
        class StepObj:
            name: str = "evidence_synthesis"
            status: str = "completed"
            started_at: str = "2026-01-02T00:00:00"
            completed_at: str = "2026-01-02T00:02:00"
            trace_ids: list = ("t3", "t4")

        step = StepObj()
        record = _step_to_record(step)
        assert record["step_name"] == "evidence_synthesis"
        assert record["status"] == "completed"
        assert record["started_at"] == "2026-01-02T00:00:00"
        assert record["completed_at"] == "2026-01-02T00:02:00"
        assert record["trace_ids"] == ("t3", "t4")

    def test_object_step_no_started_at_falls_back_to_completed_at(self):
        @dataclass
        class StepObj:
            name: str = "report_generation"
            status: str = "completed"
            completed_at: str = "2026-01-03T00:00:00"
            trace_ids: list = ()

        step = StepObj()
        record = _step_to_record(step)
        assert record["step_name"] == "report_generation"
        assert record["started_at"] == "2026-01-03T00:00:00"  # fallback
        assert record["completed_at"] == "2026-01-03T00:00:00"

    def test_object_step_no_timestamps(self):
        @dataclass
        class StepObj:
            name: str = "citation_export"
            status: str = "failed"
            trace_ids: list = ()

        step = StepObj()
        record = _step_to_record(step)
        assert record["step_name"] == "citation_export"
        assert record["status"] == "failed"
        assert record["started_at"] == ""  # no started_at, no completed_at
        assert record["completed_at"] == ""


# =============================================================================
# _group_snapshot_into_sections
# =============================================================================


class TestGroupSnapshotIntoSections:
    """Cover section grouping logic."""

    def test_single_entry(self):
        snapshot = [_snap(doc_id="doc-A", trace_id="t1")]
        sections = _group_snapshot_into_sections(snapshot)
        assert len(sections) == 1
        assert sections[0]["heading"] == "来源文献: doc-A"
        assert "- 经络是运行气血的通道" in sections[0]["body"]
        assert sections[0]["references"] == ["t1"]

    def test_multiple_entries_same_doc_merged(self):
        snapshot = [
            _snap(doc_id="doc-A", trace_id="t1", claim="Claim A"),
            _snap(doc_id="doc-A", trace_id="t2", claim="Claim B"),
        ]
        sections = _group_snapshot_into_sections(snapshot)
        assert len(sections) == 1
        assert sections[0]["heading"] == "来源文献: doc-A"
        assert "- Claim A" in sections[0]["body"]
        assert "- Claim B" in sections[0]["body"]
        assert sections[0]["references"] == ["t1", "t2"]

    def test_multiple_entries_different_docs(self):
        snapshot = [
            _snap(doc_id="doc-A", trace_id="t1", claim="Claim A"),
            _snap(doc_id="doc-B", trace_id="t2", claim="Claim B"),
            _snap(doc_id="doc-A", trace_id="t3", claim="Claim C"),
        ]
        sections = _group_snapshot_into_sections(snapshot)
        assert len(sections) == 2
        headings = {s["heading"] for s in sections}
        assert headings == {"来源文献: doc-A", "来源文献: doc-B"}

        # doc-A has both claims
        doc_a = next(s for s in sections if s["heading"] == "来源文献: doc-A")
        assert "- Claim A" in doc_a["body"]
        assert "- Claim C" in doc_a["body"]
        assert doc_a["references"] == ["t1", "t3"]

    def test_empty_snapshot(self):
        sections = _group_snapshot_into_sections([])
        assert sections == []


# =============================================================================
# _snapshot_to_evidence_list
# =============================================================================


class TestSnapshotToEvidenceList:
    """Cover evidence list transposition."""

    def test_single_entry(self):
        snapshot = [_snap()]
        evidence = _snapshot_to_evidence_list(snapshot)
        assert len(evidence) == 1
        e = evidence[0]
        assert e["trace_id"] == "trace-001"
        assert e["document_id"] == "doc-01"
        assert e["chunk_id"] == "chk-01"
        assert e["claim_text"] == "经络是运行气血的通道"
        assert e["quote"] == "经络者，所以行血气而营阴阳。"
        assert e["citation_text"] == "[doc-01:chk-01]"
        # Should NOT contain snapshot-only fields
        assert "source_ref_id" not in e

    def test_multiple_entries(self):
        snapshot = [
            _snap(trace_id="t1", doc_id="doc-A"),
            _snap(trace_id="t2", doc_id="doc-B"),
            _snap(trace_id="t3", doc_id="doc-C"),
        ]
        evidence = _snapshot_to_evidence_list(snapshot)
        assert len(evidence) == 3
        trace_ids = {e["trace_id"] for e in evidence}
        assert trace_ids == {"t1", "t2", "t3"}

    def test_empty_snapshot(self):
        evidence = _snapshot_to_evidence_list([])
        assert evidence == []


# =============================================================================
# _build_report_sections
# =============================================================================


class TestBuildReportSections:
    """Cover both branches: when sections is non-empty (pass-through) and
    when sections is empty (build from evidence)."""

    def test_sections_passthrough(self):
        existing = [
            {"heading": "Section 1", "body": "Body 1", "references": ["t1"]},
        ]
        result = _build_report_sections("topic", [], existing)
        assert result == existing

    def test_build_from_evidence(self):
        evidence = [
            _snap(trace_id="t1", doc_id="doc-A", claim="Claim A",
                  citation="[doc-A]"),
            _snap(trace_id="t2", doc_id="doc-A", claim="Claim B",
                  citation="[doc-A]"),
            _snap(trace_id="t3", doc_id="doc-B", claim="Claim C",
                  citation="[doc-B]"),
        ]
        result = _build_report_sections("topic", evidence, [])
        assert len(result) == 2  # two docs

        headings = {r["heading"] for r in result}
        assert headings == {"文献 doc-A", "文献 doc-B"}

        doc_a = next(r for r in result if r["heading"] == "文献 doc-A")
        assert "- Claim A" in doc_a["body"]
        assert "- Claim B" in doc_a["body"]
        assert "引用: [doc-A]" in doc_a["body"]
        assert set(doc_a["references"]) == {"t1", "t2"}

    def test_build_from_evidence_missing_doc_id(self):
        """When document_id is empty string, heading uses empty string."""
        evidence = [
            {"trace_id": "t1", "document_id": "", "claim_text": "Claim"},
        ]
        result = _build_report_sections("topic", evidence, [])
        assert len(result) == 1
        # document_id is "" so .get default is never reached
        assert result[0]["heading"] == "文献 "

    def test_build_from_evidence_no_citation_text(self):
        evidence = [
            _snap(trace_id="t1", doc_id="doc-A", claim="Claim A"),
        ]
        # remove citation_text
        evidence[0].pop("citation_text", None)
        result = _build_report_sections("topic", evidence, [])
        assert len(result) == 1
        body = result[0]["body"]
        assert "- Claim A" in body
        # no citation line since citation_text is missing
        assert "引用:" not in body

    def test_build_from_evidence_empty_trace_id_filtered(self):
        evidence = [
            _snap(trace_id="t1", doc_id="doc-A", claim="Claim A"),
            _snap(trace_id="", doc_id="doc-A", claim="Claim B"),
        ]
        result = _build_report_sections("topic", evidence, [])
        assert len(result) == 1
        # empty trace_id should be filtered out of references
        assert result[0]["references"] == ["t1"]

    def test_build_from_evidence_empty(self):
        result = _build_report_sections("topic", [], [])
        assert result == []


# =============================================================================
# canonical_json_bytes + canonical_sha256
# =============================================================================


class TestCanonicalJsonBytes:
    """Cover deterministic JSON byte encoding."""

    def test_deterministic_output(self):
        payload = {"b": 2, "a": 1}
        b1 = canonical_json_bytes(payload)
        b2 = canonical_json_bytes(payload)
        assert b1 == b2
        # keys should be sorted
        assert b1.index(b'"a"') < b1.index(b'"b"')

    def test_utf8_content(self):
        payload = {"text": "经络"}
        b = canonical_json_bytes(payload)
        assert "经络".encode("utf-8") in b

    def test_nested_structure(self):
        payload = {"outer": {"inner": [3, 1, 2], "z": 0, "a": 1}}
        b = canonical_json_bytes(payload)
        decoded = json.loads(b.decode("utf-8"))
        assert decoded == payload

    def test_separators_no_extra_whitespace(self):
        payload = {"a": 1, "b": "text"}
        b = canonical_json_bytes(payload)
        s = b.decode("utf-8")
        # no spaces after : or ,
        assert ": " not in s
        assert ", " not in s

    def test_no_special_float_encoding(self):
        payload = {"score": 0.95}
        b = canonical_json_bytes(payload)
        decoded = json.loads(b)
        assert decoded["score"] == 0.95


class TestCanonicalSha256:
    """Cover canonical_sha256 deterministic hashing."""

    def test_deterministic(self):
        h1 = canonical_sha256({"a": 1, "b": 2})
        h2 = canonical_sha256({"b": 2, "a": 1})  # different key order, same data
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_different_payloads_different_hashes(self):
        h1 = canonical_sha256({"a": 1})
        h2 = canonical_sha256({"a": 2})
        assert h1 != h2

    def test_empty_payload(self):
        h = canonical_sha256({})
        assert len(h) == 64
        assert h == hashlib.sha256(canonical_json_bytes({})).hexdigest()


# =============================================================================
# canonicalize_trace + canonicalize_traces
# =============================================================================


class TestCanonicalizeTrace:
    """Cover single-trace canonicalization to provenance fields only."""

    def test_extracts_only_provenance_fields(self):
        trace = {
            "trace_id": "t1",
            "document_id": "doc-A",
            "chunk_id": "chk-1",
            "passage_id": "p1",
            "provenance_kind": "retrieval",
            "retrieval_score": 0.95,
            "retrieval_method": "keyword",
            "extra_field": "should be dropped",
            "another_extra": 42,
        }
        result = canonicalize_trace(trace)
        assert set(result.keys()) == {
            "trace_id", "document_id", "chunk_id", "passage_id",
            "provenance_kind", "retrieval_score", "retrieval_method",
        }
        assert result["trace_id"] == "t1"
        assert result["retrieval_score"] == 0.95
        assert "extra_field" not in result

    def test_retrieval_score_none_preserved(self):
        trace = {
            "trace_id": "g1",
            "document_id": "doc-G",
            "chunk_id": "chk-g",
            "passage_id": "pg",
            "provenance_kind": "graph",
            "retrieval_score": None,
            "retrieval_method": "graph_traversal",
        }
        result = canonicalize_trace(trace)
        assert result["retrieval_score"] is None
        assert result["provenance_kind"] == "graph"


class TestCanonicalizeTraces:
    """Cover multi-trace canonicalization: extract + sort."""

    def test_sorts_by_trace_id(self):
        traces = [
            {"trace_id": "c", "document_id": "d1", "chunk_id": "ck1",
             "passage_id": "p1", "provenance_kind": "retrieval",
             "retrieval_score": 0.5, "retrieval_method": "kw"},
            {"trace_id": "a", "document_id": "d2", "chunk_id": "ck2",
             "passage_id": "p2", "provenance_kind": "retrieval",
             "retrieval_score": 0.8, "retrieval_method": "sem"},
            {"trace_id": "b", "document_id": "d3", "chunk_id": "ck3",
             "passage_id": "p3", "provenance_kind": "graph",
             "retrieval_score": None, "retrieval_method": "graph_walk"},
        ]
        result = canonicalize_traces(traces)
        assert len(result) == 3
        assert result[0]["trace_id"] == "a"
        assert result[1]["trace_id"] == "b"
        assert result[2]["trace_id"] == "c"

    def test_empty_list(self):
        assert canonicalize_traces([]) == []

    def test_extra_fields_stripped(self):
        traces = [
            {"trace_id": "t1", "document_id": "d1", "chunk_id": "c1",
             "passage_id": "p1", "provenance_kind": "retrieval",
             "retrieval_score": 1.0, "retrieval_method": "sem",
             "garbage": "yes", "timestamp": "2026-01-01"},
        ]
        result = canonicalize_traces(traces)
        assert len(result) == 1
        assert "garbage" not in result[0]
        assert "timestamp" not in result[0]


# =============================================================================
# _build_corpus_payload
# =============================================================================


class TestBuildCorpusPayload:
    """Cover corpus payload construction for corpus_sha256."""

    def test_single_entry(self):
        snapshot = [_snap_with_extra(passage_id="p-001")]
        payload = _build_corpus_payload(snapshot)
        assert "corpus_entries" in payload
        assert len(payload["corpus_entries"]) == 1
        entry = payload["corpus_entries"][0]
        assert entry["document_id"] == "doc-01"
        assert entry["chunk_id"] == "chk-01"
        assert entry["passage_id"] == "p-001"
        assert entry["quote"] == "Quote text"
        assert entry["citation_text"] == "[doc-01:chk-01]"
        assert payload["canonical_version"] == "2.0.0"

    def test_sorted_by_trace_id(self):
        snapshot = [
            _snap_with_extra(trace_id="z", doc_id="doc-Z", chunk_id="ck-z",
                             passage_id="p-z"),
            _snap_with_extra(trace_id="a", doc_id="doc-A", chunk_id="ck-a",
                             passage_id="p-a"),
        ]
        payload = _build_corpus_payload(snapshot)
        assert payload["corpus_entries"][0]["document_id"] == "doc-A"
        assert payload["corpus_entries"][1]["document_id"] == "doc-Z"

    def test_missing_passage_id_defaults_to_empty(self):
        snapshot = [_snap_with_extra()]  # no passage_id
        snapshot[0].pop("passage_id", None)
        payload = _build_corpus_payload(snapshot)
        assert payload["corpus_entries"][0]["passage_id"] == ""

    def test_deterministic_across_runs(self):
        snapshot = [_snap_with_extra(trace_id="t1", passage_id="p1")]
        p1 = _build_corpus_payload(snapshot)
        p2 = _build_corpus_payload(snapshot)
        assert p1 == p2

    def test_empty_snapshot(self):
        payload = _build_corpus_payload([])
        assert payload["corpus_entries"] == []
        assert payload["canonical_version"] == "2.0.0"


# =============================================================================
# _build_input_payload
# =============================================================================


class TestBuildInputPayload:
    """Cover input payload construction with/without canonical_traces."""

    def test_without_canonical_traces(self):
        snapshot = [_snap_with_extra(trace_id="t1")]
        payload = _build_input_payload(
            topic="经络",
            workflow_type="full_research_flow",
            pipeline_version="1.0.0",
            retrieval_snapshot=snapshot,
            trace_ids=["t1"],
            source_document_ids=["doc-01"],
            canonical_traces=None,
        )
        assert payload["topic"] == "经络"
        assert payload["workflow_type"] == "full_research_flow"
        assert payload["pipeline_version"] == "1.0.0"
        assert payload["trace_ids"] == ["t1"]
        assert payload["source_document_ids"] == ["doc-01"]
        assert len(payload["retrieval_snapshot"]) == 1
        assert "traces" not in payload

    def test_with_canonical_traces(self):
        snapshot = [_snap_with_extra(trace_id="t1")]
        canonical_traces = canonicalize_traces([
            {"trace_id": "t1", "document_id": "doc-01", "chunk_id": "chk-01",
             "passage_id": "p-001", "provenance_kind": "retrieval",
             "retrieval_score": 0.95, "retrieval_method": "kw"},
        ])
        payload = _build_input_payload(
            topic="经络",
            workflow_type="full_research_flow",
            pipeline_version="1.0.0",
            retrieval_snapshot=snapshot,
            trace_ids=["t1"],
            source_document_ids=["doc-01"],
            canonical_traces=canonical_traces,
        )
        assert "traces" in payload
        assert payload["traces"] == canonical_traces

    def test_deterministic(self):
        snapshot = [_snap_with_extra(trace_id="t1")]
        kwargs = {
            "topic": "x", "workflow_type": "wf", "pipeline_version": "1.0",
            "retrieval_snapshot": snapshot, "trace_ids": ["t1"],
            "source_document_ids": ["d1"],
        }
        p1 = _build_input_payload(**kwargs)
        # flipping trace_ids order shouldn't matter
        kwargs2 = {**kwargs, "trace_ids": ["t1"]}
        p2 = _build_input_payload(**kwargs2)
        assert p1 == p2

    def test_empty_inputs(self):
        payload = _build_input_payload(
            topic="", workflow_type="", pipeline_version="",
            retrieval_snapshot=[], trace_ids=[], source_document_ids=[],
        )
        assert payload["topic"] == ""
        assert payload["retrieval_snapshot"] == []
        assert payload["trace_ids"] == []


# =============================================================================
# _build_canonical_payload
# =============================================================================


class TestBuildCanonicalPayload:
    """Cover canonical output payload with/without canonical_traces."""

    def _make_inputs(self):
        snapshot = [_snap_with_extra(trace_id="t1", doc_id="doc-A",
                                     chunk_id="ck-a", claim="Claim A")]
        synthesis_sections = _group_snapshot_into_sections(snapshot)
        synthesis_evidence = _snapshot_to_evidence_list(snapshot)
        citations = [
            {"trace_id": "t1", "citation_text": "[doc-A:ck-a]",
             "document_id": "doc-A", "quote": "Quote text"},
        ]
        return snapshot, synthesis_sections, synthesis_evidence, citations

    def test_without_canonical_traces(self):
        snapshot, s_sec, s_ev, citations = self._make_inputs()
        payload = _build_canonical_payload(
            topic="经络",
            workflow_type="full_research_flow",
            pipeline_version="1.0.0",
            retrieval_snapshot=snapshot,
            synthesis_sections=s_sec,
            synthesis_evidence=s_ev,
            report_sections=s_sec,
            citations=citations,
            trace_ids=["t1"],
            source_document_ids=["doc-A"],
            canonical_traces=None,
        )
        assert "traces" not in payload
        assert len(payload["retrieval_snapshot"]) == 1
        assert len(payload["synthesis_sections"]) == 1
        assert len(payload["synthesis_evidence"]) == 1
        assert len(payload["citation_export"]) == 1
        assert payload["trace_ids"] == ["t1"]

    def test_with_canonical_traces(self):
        snapshot, s_sec, s_ev, citations = self._make_inputs()
        ct = canonicalize_traces([
            {"trace_id": "t1", "document_id": "doc-A", "chunk_id": "ck-a",
             "passage_id": "p1", "provenance_kind": "retrieval",
             "retrieval_score": 0.95, "retrieval_method": "kw"},
        ])
        payload = _build_canonical_payload(
            topic="经络",
            workflow_type="full_research_flow",
            pipeline_version="1.0.0",
            retrieval_snapshot=snapshot,
            synthesis_sections=s_sec,
            synthesis_evidence=s_ev,
            report_sections=s_sec,
            citations=citations,
            trace_ids=["t1"],
            source_document_ids=["doc-A"],
            canonical_traces=ct,
        )
        assert "traces" in payload
        assert payload["traces"] == ct

    def test_deterministic(self):
        snapshot, s_sec, s_ev, citations = self._make_inputs()
        kwargs = {
            "topic": "经络", "workflow_type": "wf", "pipeline_version": "1.0",
            "retrieval_snapshot": snapshot, "synthesis_sections": s_sec,
            "synthesis_evidence": s_ev, "report_sections": s_sec,
            "citations": citations, "trace_ids": ["t1"],
            "source_document_ids": ["doc-A"],
        }
        p1 = _build_canonical_payload(**kwargs)
        p2 = _build_canonical_payload(**kwargs)
        assert p1 == p2

    def test_multiple_entries_sorted(self):
        snapshot = [
            _snap_with_extra(trace_id="b", doc_id="doc-B", chunk_id="ck-b"),
            _snap_with_extra(trace_id="a", doc_id="doc-A", chunk_id="ck-a"),
        ]
        s_sec = _group_snapshot_into_sections(snapshot)
        s_ev = _snapshot_to_evidence_list(snapshot)
        citations = [
            {"trace_id": "a", "citation_text": "[doc-A]", "document_id": "doc-A",
             "quote": "q"},
            {"trace_id": "b", "citation_text": "[doc-B]", "document_id": "doc-B",
             "quote": "q"},
        ]
        payload = _build_canonical_payload(
            topic="x", workflow_type="wf", pipeline_version="1.0",
            retrieval_snapshot=snapshot, synthesis_sections=s_sec,
            synthesis_evidence=s_ev, report_sections=s_sec,
            citations=citations, trace_ids=["a", "b"],
            source_document_ids=["doc-A", "doc-B"],
        )
        # All sorted by trace_id: 'a' before 'b'
        assert payload["retrieval_snapshot"][0]["trace_id"] == "a"
        assert payload["retrieval_snapshot"][1]["trace_id"] == "b"
        assert payload["citation_export"][0]["trace_id"] == "a"
        assert payload["citation_export"][1]["trace_id"] == "b"
        assert payload["trace_ids"] == ["a", "b"]
        assert payload["source_document_ids"] == ["doc-A", "doc-B"]

    def test_empty_inputs(self):
        payload = _build_canonical_payload(
            topic="", workflow_type="", pipeline_version="",
            retrieval_snapshot=[], synthesis_sections=[], synthesis_evidence=[],
            report_sections=[], citations=[], trace_ids=[],
            source_document_ids=[],
        )
        assert payload["retrieval_snapshot"] == []
        assert payload["synthesis_sections"] == []
        assert payload["citation_export"] == []


# =============================================================================
# build_markdown_artifact — with-snapshot and evidence-only branches
# =============================================================================


_SVC = ResearchWorkflowService.__new__(ResearchWorkflowService)


class TestBuildMarkdownArtifact:
    """Cover build_markdown_artifact branches beyond the basic empty path."""

    def test_empty_snapshot_empty_synthesis(self):
        md = _SVC.build_markdown_artifact(
            topic="test", run_id=str(uuid4()), steps=[],
            retrieval_snapshot=[], synthesis_output={},
        )
        assert "# 研究报告：test" in md
        assert "检索快照记录数: 0" in md
        assert "综合证据条数: 0" in md
        assert "报告段落数: 0" in md
        assert "暂无检索快照" in md
        assert "内容哈希:" in md
        assert "Artifact ID:" in md

    def test_with_retrieval_snapshot(self):
        snapshot = [
            _snap_with_extra(trace_id="t1", claim="经络是运行气血的通道",
                             quote="经络者", citation="[doc-01:chk-01]"),
        ]
        md = _SVC.build_markdown_artifact(
            topic="经络", run_id=str(uuid4()), steps=[],
            retrieval_snapshot=snapshot, synthesis_output={"evidence": [], "sections": []},
        )
        assert "文献检索快照" in md
        assert "经络是运行气血的通道" in md
        assert "经络者" in md
        assert "doc-01" in md
        assert "[t1]" in md
        assert "检索快照记录数: 1" in md

    def test_with_sections_in_synthesis(self):
        sections = [
            {"heading": "文献 doc-A", "body": "Evidence body text.",
             "references": ["t1", "t2"]},
        ]
        md = _SVC.build_markdown_artifact(
            topic="测试", run_id=str(uuid4()), steps=[],
            retrieval_snapshot=[], synthesis_output={"evidence": [], "sections": sections},
        )
        assert "证据综合" in md
        assert "文献 doc-A" in md
        assert "Evidence body text." in md
        assert "[t1]" in md
        assert "[t2]" in md

    def test_with_evidence_only_no_sections(self):
        evidence = [
            _snap(trace_id="t1", doc_id="doc-A", claim="Claim A",
                  citation="[doc-A]"),
        ]
        md = _SVC.build_markdown_artifact(
            topic="测试", run_id=str(uuid4()), steps=[],
            retrieval_snapshot=[], synthesis_output={"evidence": evidence, "sections": []},
        )
        assert "证据综合" in md
        assert "Claim A" in md
        assert "[doc-A]" in md
        assert "[t1]" in md

    def test_with_steps_completed_and_failed(self):
        steps = [
            {"name": "topic_selection", "status": "completed"},
            {"name": "literature_retrieval", "status": "completed"},
            {"name": "evidence_synthesis", "status": "failed"},
        ]
        md = _SVC.build_markdown_artifact(
            topic="测试", run_id=str(uuid4()), steps=steps,
            retrieval_snapshot=[], synthesis_output={},
        )
        assert "✅" in md
        assert "❌" in md

    def test_with_object_steps(self):
        @dataclass
        class StepModel:
            name: str = "my_step"
            status: str = "completed"

            def model_dump(self):
                return {"name": self.name, "status": self.status}

        steps = [StepModel()]
        md = _SVC.build_markdown_artifact(
            topic="测试", run_id=str(uuid4()), steps=steps,
            retrieval_snapshot=[], synthesis_output={},
        )
        assert "my_step" in md
        assert "✅" in md

    def test_has_content_sha256(self):
        md = _SVC.build_markdown_artifact(
            topic="test", run_id=str(uuid4()), steps=[],
            retrieval_snapshot=[], synthesis_output={},
        )
        # content hash should be present and 64 hex chars
        import re
        match = re.search(r"内容哈希: `([a-f0-9]+)`", md)
        assert match is not None
        assert len(match.group(1)) == 64

    def test_retrieval_snapshot_truncated_at_20(self):
        snapshot = [
            _snap_with_extra(trace_id=f"t{i}", claim=f"Claim {i}")
            for i in range(25)
        ]
        md = _SVC.build_markdown_artifact(
            topic="test", run_id=str(uuid4()), steps=[],
            retrieval_snapshot=snapshot, synthesis_output={},
        )
        # Claims 0-19 should be in output, 20-24 should not
        for i in range(20):
            assert f"Claim {i}" in md, f"Claim {i} should be present"
        for i in range(20, 25):
            assert f"Claim {i}" not in md, f"Claim {i} should NOT be present"


# =============================================================================
# _escape_md
# =============================================================================


class TestEscapeMd:
    """Cover the _escape_md static method."""

    def test_escape_pipe(self):
        result = ResearchWorkflowService._escape_md("a|b")
        assert result == "a\\|b"

    def test_escape_newline(self):
        result = ResearchWorkflowService._escape_md("line1\nline2")
        assert result == "line1 line2"

    def test_escape_both(self):
        result = ResearchWorkflowService._escape_md("col|a\ncol|b")
        assert result == "col\\|a col\\|b"

    def test_no_escaping_needed(self):
        result = ResearchWorkflowService._escape_md("plain text")
        assert result == "plain text"

    def test_empty_string(self):
        result = ResearchWorkflowService._escape_md("")
        assert result == ""


# =============================================================================
# execute_evidence_synthesis_from_snapshot — additional branches
# =============================================================================


class TestEvidenceSynthesis:
    """Cover branches not exercised by existing test_v4_workflow tests."""

    def test_empty_snapshot_no_traces_passed(self):
        """Empty snapshot: returns empty output with empty internal_traces."""
        output = _SVC.execute_evidence_synthesis_from_snapshot("test", [])
        assert output["result"]["sections"] == 0
        assert output["result"]["claims"] == 0
        assert output["evidence"] == []
        assert output["sections"] == []
        assert output["trace_ids"] == []
        assert output["source_documents"] == []
        assert output["internal_traces"] == []

    def test_empty_snapshot_with_traces_passed_through(self):
        """Empty snapshot: passes internal_traces through unchanged."""
        output = _SVC.execute_evidence_synthesis_from_snapshot(
            "test", [], internal_traces=[MagicMock()],
        )
        assert output["internal_traces"] is not None
        assert len(output["internal_traces"]) == 1

    def test_nonempty_snapshot_without_traces(self):
        """Non-empty snapshot, no traces → empty trace_ids/source_documents."""
        snapshot = [_snap_with_extra(trace_id="t1", doc_id="doc-A")]
        output = _SVC.execute_evidence_synthesis_from_snapshot(
            "test", snapshot, internal_traces=None,
        )
        assert output["result"]["sections"] == 1
        assert output["result"]["claims"] == 1
        assert output["trace_ids"] == []
        assert output["source_documents"] == []

    def test_multiple_docs_multiple_sections(self):
        snapshot = [
            _snap_with_extra(trace_id="t1", doc_id="doc-A", claim="A1"),
            _snap_with_extra(trace_id="t2", doc_id="doc-A", claim="A2"),
            _snap_with_extra(trace_id="t3", doc_id="doc-B", claim="B1"),
        ]
        output = _SVC.execute_evidence_synthesis_from_snapshot("test", snapshot)
        assert output["result"]["sections"] == 2
        assert output["result"]["claims"] == 3
        assert len(output["evidence"]) == 3
        assert len(output["sections"]) == 2


# =============================================================================
# execute_report_from_synthesis — additional branches
# =============================================================================


class TestReportFromSynthesis:
    """Cover branches beyond basic empty/non-empty."""

    def test_no_evidence_no_sections_no_traces(self):
        """Empty synthesis without any internal_traces."""
        empty = {
            "result": {"sections": 0, "claims": 0},
            "sections": [], "evidence": [], "trace_ids": [],
            "source_documents": [], "internal_traces": [],
        }
        output = _SVC.execute_report_from_synthesis("x", empty)
        assert "(无可用证据)" in output["result"]["title"]
        assert output["evidence"] == []
        assert output["trace_ids"] == []

    def test_passes_traces_through(self):
        """Traces from synthesis pass through to report output."""
        mt1 = _make_mock_trace(tid="t1", did="doc-01")
        mt2 = _make_mock_trace(tid="t2", did="doc-02")
        synthesis = {
            "result": {"sections": 1, "claims": 1},
            "sections": [{"heading": "H", "body": "B", "references": ["t1"]}],
            "evidence": [_snap_with_extra(trace_id="t1")],
            "trace_ids": ["t1"],
            "source_documents": ["doc-01"],
            "internal_traces": [mt1, mt2],
        }
        output = _SVC.execute_report_from_synthesis("经络", synthesis)
        assert output["result"]["sections"] == 1
        assert "研究报告：经络" in output["result"]["title"]
        assert len(output["internal_traces"]) == 2
        assert output["trace_ids"] == ["t1", "t2"]  # trace_ids derived from traces, not synthesis keys

    def test_sections_passthrough_to_report_sections(self):
        """When sections exist, _build_report_sections returns them as-is."""
        sections_in = [{"heading": "Custom", "body": "Custom body",
                         "references": ["r1"]}]
        synthesis = {
            "result": {"sections": 1, "claims": 0},
            "sections": sections_in,
            "evidence": [],
            "trace_ids": [],
            "source_documents": [],
            "internal_traces": [],
        }
        output = _SVC.execute_report_from_synthesis("test", synthesis)
        assert output["sections"] == sections_in


# =============================================================================
# execute_citation_export_from_evidence — additional branches
# =============================================================================


class TestCitationExport:
    """Cover citation export branches not covered by existing tests."""

    def test_empty_evidence_no_traces(self):
        """Empty evidence returns zero with empty internal_traces when None."""
        output = _SVC.execute_citation_export_from_evidence("test", [])
        assert output["result"]["total_citations"] == 0
        assert output["result"]["citations"] == []
        assert output["trace_ids"] == []
        assert output["source_documents"] == []
        assert output["internal_traces"] == []

    def test_empty_evidence_with_traces(self):
        """Empty evidence passes internal_traces through."""
        output = _SVC.execute_citation_export_from_evidence(
            "test", [], internal_traces=[MagicMock()],
        )
        assert output["internal_traces"] is not None
        assert len(output["internal_traces"]) == 1

    def test_nonempty_evidence_no_traces(self):
        """Non-empty evidence with internal_traces=None."""
        evidence = [_snap_with_extra(trace_id="t1", doc_id="doc-A")]
        output = _SVC.execute_citation_export_from_evidence(
            "test", evidence, internal_traces=None,
        )
        assert output["result"]["total_citations"] == 1
        assert output["internal_traces"] == []

    def test_dedup_by_trace_id(self):
        """Duplicate trace_ids across evidence entries → single citation."""
        evidence = [
            _snap_with_extra(trace_id="t1", doc_id="doc-A"),
            _snap_with_extra(trace_id="t1", doc_id="doc-A"),  # duplicate tid
            _snap_with_extra(trace_id="t2", doc_id="doc-B"),
        ]
        output = _SVC.execute_citation_export_from_evidence("test", evidence)
        assert output["result"]["total_citations"] == 2
        citations = output["result"]["citations"]
        tids = {c["trace_id"] for c in citations}
        assert tids == {"t1", "t2"}

    def test_skip_empty_trace_id(self):
        """Evidence entries with empty trace_id are skipped."""
        evidence = [
            _snap_with_extra(trace_id="", doc_id="doc-A"),
            _snap_with_extra(trace_id="t2", doc_id="doc-B"),
        ]
        output = _SVC.execute_citation_export_from_evidence("test", evidence)
        assert output["result"]["total_citations"] == 1
        assert output["result"]["citations"][0]["trace_id"] == "t2"

    def test_citation_fields_populated_correctly(self):
        """Each citation carries trace_id, citation_text, document_id, quote."""
        evidence = [
            _snap_with_extra(trace_id="t1", doc_id="doc-A",
                             claim="Claim A", quote="Quote A",
                             citation="[doc-A]"),
        ]
        output = _SVC.execute_citation_export_from_evidence("test", evidence)
        c = output["result"]["citations"][0]
        assert c["trace_id"] == "t1"
        assert c["citation_text"] == "[doc-A]"
        assert c["document_id"] == "doc-A"
        assert c["quote"] == "Quote A"

    def test_dedup_preserves_first_occurrence(self):
        """When deduplicating, the first citation_text is preserved."""
        evidence = [
            _snap_with_extra(trace_id="t1", doc_id="doc-A", citation="[first]"),
            _snap_with_extra(trace_id="t1", doc_id="doc-A", citation="[second]"),
        ]
        output = _SVC.execute_citation_export_from_evidence("test", evidence)
        assert output["result"]["total_citations"] == 1
        assert output["result"]["citations"][0]["citation_text"] == "[first]"

    def test_source_documents_and_trace_ids_from_citations(self):
        """trace_ids and source_documents come from the citation list, not input."""
        evidence = [
            _snap_with_extra(trace_id="t1", doc_id="doc-A"),
            _snap_with_extra(trace_id="t2", doc_id="doc-A"),  # same doc
            _snap_with_extra(trace_id="t3", doc_id="doc-B"),
        ]
        output = _SVC.execute_citation_export_from_evidence("test", evidence)
        assert set(output["trace_ids"]) == {"t1", "t2", "t3"}
        assert set(output["source_documents"]) == {"doc-A", "doc-B"}


# =============================================================================
# Integration: canonical payload round-trip hashing
# =============================================================================


class TestCanonicalRoundTrip:
    """End-to-end canonical hash consistency."""

    def test_input_output_hashes_different(self):
        """input and output payloads must produce different hashes."""
        snapshot = [_snap_with_extra(trace_id="t1", doc_id="doc-A",
                                     chunk_id="ck-a", claim="C")]
        s_sec = _group_snapshot_into_sections(snapshot)
        s_ev = _snapshot_to_evidence_list(snapshot)
        citations = [{"trace_id": "t1", "citation_text": "[doc-A]",
                       "document_id": "doc-A", "quote": "Q"}]
        ct = canonicalize_traces([
            {"trace_id": "t1", "document_id": "doc-A", "chunk_id": "ck-a",
             "passage_id": "p1", "provenance_kind": "retrieval",
             "retrieval_score": 0.95, "retrieval_method": "kw"},
        ])

        corpus_payload = _build_corpus_payload(snapshot)
        input_payload = _build_input_payload(
            topic="test", workflow_type="wf", pipeline_version="1.0",
            retrieval_snapshot=snapshot, trace_ids=["t1"],
            source_document_ids=["doc-A"], canonical_traces=ct,
        )
        output_payload = _build_canonical_payload(
            topic="test", workflow_type="wf", pipeline_version="1.0",
            retrieval_snapshot=snapshot, synthesis_sections=s_sec,
            synthesis_evidence=s_ev, report_sections=s_sec,
            citations=citations, trace_ids=["t1"],
            source_document_ids=["doc-A"], canonical_traces=ct,
        )

        corpus_h = canonical_sha256(corpus_payload)
        input_h = canonical_sha256(input_payload)
        output_h = canonical_sha256(output_payload)

        assert corpus_h != input_h
        assert corpus_h != output_h
        assert input_h != output_h

    def test_same_input_same_hash(self):
        """Identical inputs produce identical hashes."""
        snapshot = [_snap_with_extra(trace_id="t1")]
        kwargs = {
            "topic": "test", "workflow_type": "wf", "pipeline_version": "1.0",
            "retrieval_snapshot": snapshot, "trace_ids": ["t1"],
            "source_document_ids": ["doc-01"],
        }
        h1 = canonical_sha256(_build_input_payload(**kwargs))
        h2 = canonical_sha256(_build_input_payload(**kwargs))
        assert h1 == h2

    def test_different_trace_changes_hash(self):
        """A single provenace field change must change the hash."""
        snapshot = [_snap_with_extra(trace_id="t1", doc_id="doc-A",
                                     chunk_id="ck-a")]
        ct1 = canonicalize_traces([
            {"trace_id": "t1", "document_id": "doc-A", "chunk_id": "ck-a",
             "passage_id": "p1", "provenance_kind": "retrieval",
             "retrieval_score": 0.95, "retrieval_method": "kw"},
        ])
        ct2 = canonicalize_traces([
            {"trace_id": "t1", "document_id": "doc-A", "chunk_id": "ck-a",
             "passage_id": "p1", "provenance_kind": "retrieval",
             "retrieval_score": 0.80, "retrieval_method": "kw"},  # score changed
        ])

        h1 = canonical_sha256(_build_input_payload(
            topic="test", workflow_type="wf", pipeline_version="1.0",
            retrieval_snapshot=snapshot, trace_ids=["t1"],
            source_document_ids=["doc-A"], canonical_traces=ct1,
        ))
        h2 = canonical_sha256(_build_input_payload(
            topic="test", workflow_type="wf", pipeline_version="1.0",
            retrieval_snapshot=snapshot, trace_ids=["t1"],
            source_document_ids=["doc-A"], canonical_traces=ct2,
        ))
        assert h1 != h2, "Different retrieval_score must produce different hash"

    def test_no_traces_vs_with_traces_different(self):
        """Payload with traces vs without must differ."""
        snapshot = [_snap_with_extra(trace_id="t1")]
        ct = canonicalize_traces([
            {"trace_id": "t1", "document_id": "doc-A", "chunk_id": "ck-a",
             "passage_id": "p1", "provenance_kind": "retrieval",
             "retrieval_score": 0.95, "retrieval_method": "kw"},
        ])
        base_kwargs = {
            "topic": "test", "workflow_type": "wf", "pipeline_version": "1.0",
            "retrieval_snapshot": snapshot, "trace_ids": ["t1"],
            "source_document_ids": ["doc-A"],
        }
        h_no_traces = canonical_sha256(_build_input_payload(**base_kwargs,
                                                             canonical_traces=None))
        h_with_traces = canonical_sha256(_build_input_payload(**base_kwargs,
                                                               canonical_traces=ct))
        assert h_no_traces != h_with_traces


# =============================================================================
# Async DB-dependent methods — full coverage of all 83 uncovered lines
# =============================================================================


# --- Mock helpers for _build_retrieval_snapshot queries ---

def _make_evidence_trace(doc_id="doc-1", chk_id="chk-1",
                         claim="Claim A", quote="Quote A",
                         citation="[doc-1:chk-1]"):
    """Create an EvidenceTrace-like mock for _build_retrieval_snapshot."""
    t = MagicMock()
    t.document_id = doc_id
    t.chunk_id = chk_id
    t.claim_text = claim
    t.quote = quote
    t.citation_text = citation
    return t


def _make_sourceref_mock(sr_id="sr-1", url="http://ex.com", title="SR Title",
                          location="passage:p1"):
    """Create a SourceRef-like mock with scalars-compatible fields."""
    sr = MagicMock()
    sr.id = sr_id
    sr.url = url
    sr.title = title
    sr.page_location = location
    return sr


def _chunk_row(did, cid, pid):
    """Create a DB row mock for chunk query (id, document_id, passage_id)."""
    row = [cid, did, pid]
    mock = MagicMock()
    mock.__getitem__ = lambda self, i, r=row: r[i]
    mock.__iter__ = lambda self, r=row: iter(r)
    return mock


def _passage_row(pid):
    """Create a DB row mock for single-chunk passage_id query."""
    row = [pid]
    mock = MagicMock()
    mock.__getitem__ = lambda self, i, r=row: r[i]
    mock.__iter__ = lambda self, r=row: iter(r)
    return mock


# =============================================================================
# execute_topic_selection — line 66
# =============================================================================


@pytest.mark.asyncio
class TestExecuteTopicSelection:
    """Cover execute_topic_selection — mocks AcademicService.research."""

    async def test_execute_topic_selection_mocks_academic_service(self):
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_result = MagicMock()
        mock_result.decomposition = []
        mock_result.evidence_trace = []

        with patch(
            "app.services.research_workflow_service.AcademicService"
        ) as MockAcSvc:
            mock_inst = MockAcSvc.return_value
            mock_inst.research = AsyncMock(return_value=mock_result)
            mock_inst.last_snapshot = {"chk-1": {"score": 0.95, "retrieval_method": "kw"}}

            with patch(
                "app.services.research_workflow_service._pack_academic_step",
                new_callable=AsyncMock,
            ) as mock_pack:
                mock_pack.return_value = {
                    "result": {"topic": "经络", "sub_questions": 3},
                    "trace_ids": [],
                    "source_documents": [],
                    "internal_traces": [],
                }

                output = await svc.execute_topic_selection("经络研究")

            MockAcSvc.assert_called_once()
            mock_inst.research.assert_awaited_once_with(query="经络研究")
            mock_pack.assert_awaited_once()
            assert output["result"]["topic"] == "经络"
            assert output["result"]["sub_questions"] == 3


# =============================================================================
# execute_literature_retrieval — lines 57-72 (entire method)
# =============================================================================


@pytest.mark.asyncio
class TestExecuteLiteratureRetrieval:
    """Cover execute_literature_retrieval — mocks AcademicService.synthesize."""

    async def test_execute_literature_retrieval_mocks_synthesize(self):
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_result = MagicMock()
        mock_result.themes = [MagicMock(), MagicMock()]  # 2 themes
        mock_result.evidence_trace = []

        with patch(
            "app.services.research_workflow_service.AcademicService"
        ) as MockAcSvc:
            mock_inst = MockAcSvc.return_value
            mock_inst.synthesize = AsyncMock(return_value=mock_result)
            mock_inst.last_snapshot = {
                "chk-1": {"score": 0.95, "retrieval_method": "kw"}
            }

            with patch(
                "app.services.research_workflow_service._build_retrieval_snapshot",
                new_callable=AsyncMock,
            ) as mock_build:
                tid = make_trace_id("doc-1", "chk-1")
                fake_trace = InternalTraceRecord(
                    trace_id=tid,
                    document_id="doc-1",
                    chunk_id="chk-1",
                    passage_id="p1",
                    provenance_kind="retrieval",
                    retrieval_score=0.95,
                    retrieval_method="kw",
                    timestamp="2026-01-01T00:00:00",
                )
                mock_build.return_value = (
                    [{"claim_text": "C", "trace_id": "t1"}],
                    [fake_trace],
                )

                output = await svc.execute_literature_retrieval("经络")

            mock_inst.synthesize.assert_awaited_once_with(query="经络")
            mock_build.assert_awaited_once()
            assert output["result"]["themes"] == 2
            assert output["result"]["records"] == 1
            assert output["trace_ids"] == [tid]
            assert output["source_documents"] == ["doc-1"]
            assert len(output["internal_traces"]) == 1


# =============================================================================
# persist_research_run — lines 282-440
# =============================================================================


@pytest.mark.asyncio
class TestPersistResearchRun:
    """Cover persist_research_run: session not found (298), JSON error
    fallback (304-305), retrieval_snapshot + manifest path (325-436),
    trace to_dict path (328-329), entry.setdefault (348)."""

    async def test_session_not_found_raises_valueerror(self):
        """Line 298: session is None raises ValueError."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with pytest.raises(ValueError, match="Research session not found"):
                await svc.persist_research_run(
                    session_id="s1",
                    run_id="r1",
                    topic="test",
                )

    async def test_json_decode_error_fallback_to_empty(self):
        """Lines 304-305: JSONDecodeError → existing = {}."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = "not-valid-json{{{"
        mock_rs.id = "s1"

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            await svc.persist_research_run(
                session_id="s1",
                run_id="r1",
                topic="test",
            )

        # Should not raise; flush should be called with corrected state
        mock_session.flush.assert_awaited_once()
        # The workflow_state should now be valid JSON with the new run
        saved = json.loads(mock_rs.workflow_state)
        assert "runs" in saved
        assert len(saved["runs"]) == 1

    async def test_with_retrieval_snapshot_manifest_path(self):
        """Lines 325-436: retrieval_snapshot present builds replay manifest.
        Also covers 328-329 (to_dict path) and 348 (entry.setdefault)."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = None
        mock_rs.id = "s1"

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            tr1 = _make_mock_trace(tid="t1", did="doc-A", cid="ck-a", pid="p-001",
                                   score=0.95, method="kw")
            tr2 = _make_mock_trace(tid="t2", did="doc-B", cid="ck-b", pid="p-002",
                                   score=0.88, method="sem")

            snapshot = [
                {
                    "trace_id": "t1",
                    "document_id": "doc-A",
                    "chunk_id": "ck-a",
                    "claim_text": "Claim A",
                    "quote": "Quote A",
                    "citation_text": "[doc-A:ck-a]",
                },
                {
                    "trace_id": "t2",
                    "document_id": "doc-B",
                    "chunk_id": "ck-b",
                    "claim_text": "Claim B",
                    "quote": "Quote B",
                    "citation_text": "[doc-B:ck-b]",
                },
            ]

            await svc.persist_research_run(
                session_id="s1",
                run_id="r1",
                topic="test",
                retrieval_snapshot=snapshot,
                immutable_traces=[tr1, tr2],
                steps=[
                    {"name": "topic_selection", "status": "completed",
                     "started_at": "2026-01-01T00:00:00",
                     "completed_at": "2026-01-01T00:01:00",
                     "trace_ids": []},
                ],
            )

        mock_session.flush.assert_awaited_once()
        saved = json.loads(mock_rs.workflow_state)
        assert "runs" in saved
        run = saved["runs"][0]
        assert "replay_manifest" in run
        manifest = run["replay_manifest"]
        assert manifest["manifest_version"] == "2.0.0"
        assert manifest["run_id"] == "r1"
        assert "manifest_sha256" in manifest
        assert manifest["corpus_sha256"]
        assert manifest["canonical_input_sha256"]
        assert manifest["canonical_output_sha256"]
        # Lines 328-329: hasattr + to_dict — traces dicts should be in manifest
        assert len(manifest["traces"]) == 2

    async def test_with_retrieval_snapshot_empty_traces(self):
        """Lines 325->436: retrieval_snapshot present but immutable_traces
        is empty — still enters manifest path."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = None
        mock_rs.id = "s1"

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            snapshot = [{
                "trace_id": "t1",
                "document_id": "doc-A",
                "chunk_id": "ck-a",
                "claim_text": "C",
                "quote": "Q",
                "citation_text": "[doc-A:ck-a]",
            }]

            await svc.persist_research_run(
                session_id="s1",
                run_id="r1",
                topic="test",
                retrieval_snapshot=snapshot,
                immutable_traces=[],
            )

        mock_session.flush.assert_awaited_once()
        saved = json.loads(mock_rs.workflow_state)
        run = saved["runs"][0]
        assert "replay_manifest" in run
        assert run["replay_manifest"]["traces"] == []

    async def test_with_retrieval_snapshot_no_to_dict(self):
        """Lines 328-329: immutable_traces objects without to_dict —
        trace_dicts stays empty."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = None
        mock_rs.id = "s1"

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            # Object with trace_id/document_id but NO to_dict method
            class NoDict:
                trace_id = "t1"
                document_id = "doc-A"

            tr_no_dict = NoDict()

            snapshot = [{
                "trace_id": "t1",
                "document_id": "doc-A",
                "chunk_id": "ck-a",
                "claim_text": "C",
                "quote": "Q",
                "citation_text": "[doc-A:ck-a]",
            }]

            await svc.persist_research_run(
                session_id="s1",
                run_id="r1",
                topic="test",
                retrieval_snapshot=snapshot,
                immutable_traces=[tr_no_dict],
            )

        mock_session.flush.assert_awaited_once()
        saved = json.loads(mock_rs.workflow_state)
        run = saved["runs"][0]
        assert "replay_manifest" in run
        assert run["replay_manifest"]["traces"] == []

    async def test_with_retrieval_snapshot_passage_id_setdefault(self):
        """Line 348: entry.setdefault — existing passage_id not overwritten."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = None
        mock_rs.id = "s1"

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            tr = _make_mock_trace(tid="t1", did="doc-A", cid="ck-a", pid="existing",
                                  score=0.95, method="kw")

            snapshot = [{
                "trace_id": "t1",
                "document_id": "doc-A",
                "chunk_id": "ck-a",
                "claim_text": "C",
                "quote": "Q",
                "citation_text": "[doc-A:ck-a]",
                "passage_id": "already-here",
            }]

            await svc.persist_research_run(
                session_id="s1",
                run_id="r1",
                topic="test",
                retrieval_snapshot=snapshot,
                immutable_traces=[tr],
            )

        mock_session.flush.assert_awaited_once()
        saved = json.loads(mock_rs.workflow_state)
        manifest = saved["runs"][0]["replay_manifest"]
        snap_in_manifest = manifest["retrieval_snapshot"][0]
        assert snap_in_manifest["passage_id"] == "already-here"


# =============================================================================
# get_research_runs — lines 442-450
# =============================================================================


@pytest.mark.asyncio
class TestGetResearchRuns:
    """Cover get_research_runs: session not found (445), JSON error
    (448-449), empty state, with data."""

    async def test_session_not_found_returns_empty(self):
        """Line 445: session is None → return []."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await svc.get_research_runs("s1")

        assert result == []

    async def test_session_without_workflow_state_returns_empty(self):
        """Line 445: session exists but workflow_state is None → return []."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = None

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            result = await svc.get_research_runs("s1")

        assert result == []

    async def test_json_decode_error_returns_empty(self):
        """Lines 448-449: JSONDecodeError in workflow_state → return []."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = "invalid-json[[["

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            result = await svc.get_research_runs("s1")

        assert result == []

    async def test_valid_state_returns_runs(self):
        """Valid workflow_state with runs → returns runs list."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = json.dumps({
            "runs": [{"run_id": "r1", "topic": "test"},
                     {"run_id": "r2", "topic": "test2"}]
        })

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            result = await svc.get_research_runs("s1")

        assert len(result) == 2
        assert result[0]["run_id"] == "r1"
        assert result[1]["run_id"] == "r2"


# =============================================================================
# configure_version_comparison — lines 456-500
# =============================================================================


@pytest.mark.asyncio
class TestConfigureVersionComparison:
    """Cover configure_version_comparison: session not found (467), same
    version error (471), different book error (473), success path."""

    async def test_session_not_found_raises_valueerror(self):
        """Line 467: research_session is None → ValueError."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with pytest.raises(ValueError, match="Research session not found"):
                await svc.configure_version_comparison(
                    session_id="s1",
                    source_passage_id="sp1",
                    target_passage_id="tp1",
                )

    async def test_same_version_raises_valueerror(self):
        """Line 471: source version == target version → ValueError."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.id = "s1"

        same_version = {"id": "v1", "name": "Version One"}

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            with patch.object(
                svc, "_load_evidence", new_callable=AsyncMock
            ) as mock_load:
                mock_load.side_effect = [
                    {"version": same_version, "book": {"id": "b1"}},
                    {"version": same_version, "book": {"id": "b1"}},
                ]

                with pytest.raises(ValueError, match="different versions"):
                    await svc.configure_version_comparison(
                        session_id="s1",
                        source_passage_id="sp1",
                        target_passage_id="tp1",
                    )

    async def test_different_book_raises_valueerror(self):
        """Line 473: source book != target book → ValueError."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.id = "s1"

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            with patch.object(
                svc, "_load_evidence", new_callable=AsyncMock
            ) as mock_load:
                mock_load.side_effect = [
                    {"version": {"id": "v1"}, "book": {"id": "b1"}},
                    {"version": {"id": "v2"}, "book": {"id": "b2"}},
                ]

                with pytest.raises(ValueError, match="same book"):
                    await svc.configure_version_comparison(
                        session_id="s1",
                        source_passage_id="sp1",
                        target_passage_id="tp1",
                    )

    async def test_success_workflow_state_persisted(self):
        """Configure successfully stores comparison state."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.id = "s1"
        mock_rs.workflow_state = None

        source_evidence = {
            "passage_id": "sp1",
            "text": "Source text",
            "translation": None,
            "notes": None,
            "order": 1,
            "chapter": {"id": "ch1", "title": "Chapter 1"},
            "version": {"id": "v1", "name": "V1", "era": "唐", "year": 800,
                        "repository": "Repo", "shelf_mark": "A1",
                        "source_url": None, "is_formal_source": False,
                        "rights_statement": None,
                        "persistent_identifier": None,
                        "is_withdrawn": False},
            "book": {"id": "b1", "title": "Book One", "source_url": None},
            "citation": "《Book One》·V1，Chapter 1，第1条",
            "evidence_complete": False,
            "is_formal_source": False,
        }
        target_evidence = {
            "passage_id": "tp1",
            "text": "Target text",
            "translation": None,
            "notes": None,
            "order": 1,
            "chapter": {"id": "ch2", "title": "Chapter 2"},
            "version": {"id": "v2", "name": "V2", "era": "宋", "year": 1000,
                        "repository": "Repo2", "shelf_mark": "B1",
                        "source_url": None, "is_formal_source": False,
                        "rights_statement": None,
                        "persistent_identifier": None,
                        "is_withdrawn": False},
            "book": {"id": "b1", "title": "Book One", "source_url": None},
            "citation": "《Book One》·V2，Chapter 2，第1条",
            "evidence_complete": False,
            "is_formal_source": False,
        }

        comparison_result = {
            "differences": 3,
            "operations": [
                {"op": "replace", "source_text": "A", "target_text": "B"},
            ],
            "similarity_ratio": 0.85,
        }

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            with patch.object(
                svc, "_load_evidence", new_callable=AsyncMock
            ) as mock_load:
                mock_load.side_effect = [source_evidence, target_evidence]

                with patch(
                    "app.services.version_center.VersionComparisonService"
                ) as MockVCS:
                    mock_vcs_inst = MockVCS.return_value
                    mock_vcs_inst.compare_passages = AsyncMock(
                        return_value=comparison_result
                    )

                    state = await svc.configure_version_comparison(
                        session_id="s1",
                        source_passage_id="sp1",
                        target_passage_id="tp1",
                    )

        assert state["workflow_type"] == "evidence_backed_version_comparison"
        assert state["corpus_status"] == "validation"
        assert state["source"]["passage_id"] == "sp1"
        assert state["target"]["passage_id"] == "tp1"
        assert state["comparison"]["differences"] == 3
        mock_session.flush.assert_awaited_once()
        assert mock_rs.workflow_state is not None

    async def test_success_both_formal_sources(self):
        """When both passages are formal sources → corpus_status = 'approved'."""
        mock_session = AsyncMock()
        mock_session.flush = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.id = "s1"

        source_formal = {
            "passage_id": "p1",
            "text": "Text",
            "translation": None,
            "notes": None,
            "order": 1,
            "chapter": {"id": "ch1", "title": "Ch"},
            "version": {"id": "v1", "name": "V1", "era": "", "year": 0,
                        "repository": "", "shelf_mark": "",
                        "source_url": None, "is_formal_source": True,
                        "rights_statement": None,
                        "persistent_identifier": None,
                        "is_withdrawn": False},
            "book": {"id": "b1", "title": "Book", "source_url": None},
            "citation": "C",
            "evidence_complete": True,
            "is_formal_source": True,
        }
        target_formal = {
            "passage_id": "p2",
            "text": "Text 2",
            "translation": None,
            "notes": None,
            "order": 2,
            "chapter": {"id": "ch2", "title": "Ch2"},
            "version": {"id": "v2", "name": "V2", "era": "", "year": 0,
                        "repository": "", "shelf_mark": "",
                        "source_url": None, "is_formal_source": True,
                        "rights_statement": None,
                        "persistent_identifier": None,
                        "is_withdrawn": False},
            "book": {"id": "b1", "title": "Book", "source_url": None},
            "citation": "C2",
            "evidence_complete": True,
            "is_formal_source": True,
        }

        comparison_result = {
            "differences": 0,
            "operations": [],
            "similarity_ratio": 1.0,
        }

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            with patch.object(
                svc, "_load_evidence", new_callable=AsyncMock
            ) as mock_load:
                mock_load.side_effect = [source_formal, target_formal]

                with patch(
                    "app.services.version_center.VersionComparisonService"
                ) as MockVCS:
                    mock_vcs_inst = MockVCS.return_value
                    mock_vcs_inst.compare_passages = AsyncMock(
                        return_value=comparison_result
                    )

                    state = await svc.configure_version_comparison(
                        session_id="s1",
                        source_passage_id="sp1",
                        target_passage_id="tp1",
                    )

        assert state["corpus_status"] == "approved"


# =============================================================================
# get_version_comparison — lines 502-512
# =============================================================================


@pytest.mark.asyncio
class TestGetVersionComparison:
    """Cover get_version_comparison: session not found (505), JSON error
    (508-509), workflow_type mismatch (511), success."""

    async def test_session_not_found_returns_none(self):
        """Line 505: session is None → return None."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            result = await svc.get_version_comparison("s1")

        assert result is None

    async def test_no_workflow_state_returns_none(self):
        """Line 505: session exists but workflow_state is empty → None."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = None

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            result = await svc.get_version_comparison("s1")

        assert result is None

    async def test_json_error_returns_none(self):
        """Lines 508-509: JSONDecodeError → return None."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = "not-json{{{{"

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            result = await svc.get_version_comparison("s1")

        assert result is None

    async def test_workflow_type_mismatch_returns_none(self):
        """Line 511: workflow_type is not 'evidence_backed_version_comparison'
        → return None."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.workflow_state = json.dumps({
            "workflow_type": "full_research_flow",
            "runs": [],
        })

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            result = await svc.get_version_comparison("s1")

        assert result is None

    async def test_success_returns_state(self):
        """Valid comparison state → returns the state dict."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        expected_state = {
            "workflow_type": "evidence_backed_version_comparison",
            "corpus_status": "validation",
            "source": {"passage_id": "sp1"},
            "target": {"passage_id": "tp1"},
            "comparison": {"differences": 1, "operations": [],
                           "similarity_ratio": 0.9},
        }
        mock_rs = MagicMock()
        mock_rs.workflow_state = json.dumps(expected_state)

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            result = await svc.get_version_comparison("s1")

        assert result is not None
        assert result["workflow_type"] == "evidence_backed_version_comparison"
        assert result["corpus_status"] == "validation"


# =============================================================================
# export_markdown — lines 514-581
# =============================================================================


@pytest.mark.asyncio
class TestExportMarkdown:
    """Cover export_markdown: session not found (518), operations table
    (552->558), context_notes (559->561), empty notes (565-566)."""

    async def test_session_not_found_raises_valueerror(self):
        """Line 518: session/state is None → ValueError."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch.object(
                svc, "get_version_comparison", new_callable=AsyncMock
            ) as mock_gvc:
                mock_gvc.return_value = None

                with pytest.raises(ValueError, match="not configured"):
                    await svc.export_markdown("s1")

    async def test_state_is_none_raises_valueerror(self):
        """Line 518: research_session exists but state is None."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.title = "Test"

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            with patch.object(
                svc, "get_version_comparison", new_callable=AsyncMock
            ) as mock_gvc:
                mock_gvc.return_value = None

                with pytest.raises(ValueError, match="not configured"):
                    await svc.export_markdown("s1")

    async def test_with_operations_table(self):
        """Lines 552->558: comparison has operations → markdown table."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.title = "版本比较：黄帝内经"
        mock_rs.context_notes = None

        state = {
            "workflow_type": "evidence_backed_version_comparison",
            "source": {
                "passage_id": "sp1",
                "text": "Source passage text",
                "citation": "《黄帝内经》·V1，Chapter 1，第1条",
                "version": {"id": "v1", "name": "宋本",
                            "is_formal_source": False},
                "is_formal_source": False,
                "evidence_complete": False,
            },
            "target": {
                "passage_id": "tp1",
                "text": "Target passage text",
                "citation": "《黄帝内经》·V2，Chapter 1，第1条",
                "version": {"id": "v2", "name": "明本",
                            "is_formal_source": False},
                "is_formal_source": False,
                "evidence_complete": False,
            },
            "comparison": {
                "differences": 2,
                "similarity_ratio": 0.85,
                "operations": [
                    {"op": "replace", "source_text": "气", "target_text": "炁"},
                    {"op": "insert", "source_text": "", "target_text": "也"},
                ],
            },
        }

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            with patch.object(
                svc, "get_version_comparison", new_callable=AsyncMock
            ) as mock_gvc:
                mock_gvc.return_value = state

                with patch.object(
                    svc.workspace, "list_notes", new_callable=AsyncMock
                ) as mock_notes:
                    mock_notes.return_value = []

                    md = await svc.export_markdown("s1")

        assert "# 版本比较：黄帝内经" in md
        assert "## 比较对象" in md
        assert "## 差异摘要" in md
        assert "差异数量：2" in md
        assert "文本相似度：85.00%" in md
        # Operations table (lines 552->558)
        assert "| 类型 | 底本文字 | 对校本文字 |" in md
        assert "| replace | 气 | 炁 |" in md
        assert "| insert |  | 也 |" in md
        # No notes and no context_notes → "暂无研究笔记。" (line 565-566)
        assert "暂无研究笔记。" in md

    async def test_with_context_notes_and_notes(self):
        """Lines 559->561: context_notes rendered, notes list rendered."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.title = "版本比较"
        mock_rs.context_notes = "一些研究笔记上下文。\n第二行。"

        mock_note1 = MagicMock()
        mock_note1.content = "第一条笔记"
        mock_note1.tags = "标签A"
        mock_note2 = MagicMock()
        mock_note2.content = "第二条笔记"
        mock_note2.tags = None

        state = {
            "workflow_type": "evidence_backed_version_comparison",
            "source": {
                "passage_id": "sp1",
                "text": "Source text",
                "citation": "Citation S",
                "version": {"id": "v1", "name": "V1",
                            "is_formal_source": False},
                "is_formal_source": False,
                "evidence_complete": False,
            },
            "target": {
                "passage_id": "tp1",
                "text": "Target text",
                "citation": "Citation T",
                "version": {"id": "v2", "name": "V2",
                            "is_formal_source": False},
                "is_formal_source": False,
                "evidence_complete": False,
            },
            "comparison": {
                "differences": 0,
                "similarity_ratio": 1.0,
                "operations": [],
            },
        }

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            with patch.object(
                svc, "get_version_comparison", new_callable=AsyncMock
            ) as mock_gvc:
                mock_gvc.return_value = state

                with patch.object(
                    svc.workspace, "list_notes", new_callable=AsyncMock
                ) as mock_notes:
                    mock_notes.return_value = [mock_note1, mock_note2]

                    md = await svc.export_markdown("s1")

        assert "一些研究笔记上下文" in md
        assert "第一条笔记" in md
        assert "第二条笔记" in md
        assert "[标签A]" in md

    async def test_formal_source_adds_no_validation_notice(self):
        """When both sources are formal, no validation notice rendered."""
        mock_session = AsyncMock()
        svc = ResearchWorkflowService(mock_session)

        mock_rs = MagicMock()
        mock_rs.title = "正式比较"
        mock_rs.context_notes = None

        state = {
            "workflow_type": "evidence_backed_version_comparison",
            "source": {
                "passage_id": "sp1",
                "text": "Source",
                "citation": "C",
                "version": {"id": "v1", "name": "V1",
                            "is_formal_source": True},
                "is_formal_source": True,
                "evidence_complete": True,
            },
            "target": {
                "passage_id": "tp1",
                "text": "Target",
                "citation": "C",
                "version": {"id": "v2", "name": "V2",
                            "is_formal_source": True},
                "is_formal_source": True,
                "evidence_complete": True,
            },
            "comparison": {
                "differences": 1,
                "similarity_ratio": 0.95,
                "operations": [],
            },
        }

        with patch.object(
            svc.workspace, "get_session", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_rs

            with patch.object(
                svc, "get_version_comparison", new_callable=AsyncMock
            ) as mock_gvc:
                mock_gvc.return_value = state

                with patch.object(
                    svc.workspace, "list_notes", new_callable=AsyncMock
                ) as mock_notes:
                    mock_notes.return_value = []

                    md = await svc.export_markdown("s1")

        assert "验证语料" not in md


# =============================================================================
# _load_evidence — lines 587-646
# =============================================================================


@pytest.mark.asyncio
class TestLoadEvidence:
    """Cover _load_evidence: passage not found (611), success with/without
    loc (618->620), withdrawn flag."""

    async def test_passage_not_found_raises_valueerror(self):
        """Line 611: no row found → ValueError."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = ResearchWorkflowService(mock_session)

        with pytest.raises(ValueError, match="Passage.*not found"):
            await svc._load_evidence("p-nonexistent")

    async def test_success_returns_evidence_dict(self):
        """Successfully loads evidence with loc in citation."""
        mock_session = AsyncMock()

        mock_passage = MagicMock()
        mock_passage.id = "p-1"
        mock_passage.content_text = "经文内容"
        mock_passage.translation = None
        mock_passage.notes = None
        mock_passage.order = 5
        mock_passage.chapter_id = "ch-1"

        mock_version = MagicMock()
        mock_version.id = "v-1"
        mock_version.version_name = "宋本"
        mock_version.era = "宋"
        mock_version.year = 1027
        mock_version.repository = "北京图书馆"
        mock_version.shelf_mark = "善本12345"
        mock_version.source_url = "http://example.com/book"
        mock_version.is_formal_source = True
        mock_version.is_academic_citable = True
        mock_version.rights_statement = "CC0"
        mock_version.persistent_identifier = "doi:10.1234/abc"
        mock_version.withdrawn_at = None
        mock_version.book_id = "b-1"

        mock_book = MagicMock()
        mock_book.id = "b-1"
        mock_book.title = "黄帝内经"
        mock_book.source_url = "http://example.com/book"

        mock_chapter = MagicMock()
        mock_chapter.id = "ch-1"
        mock_chapter.title = "素问篇"

        mock_row = (mock_passage, mock_version, mock_book, mock_chapter)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_row
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = ResearchWorkflowService(mock_session)

        evidence = await svc._load_evidence("p-1")

        assert evidence["passage_id"] == "p-1"
        assert evidence["text"] == "经文内容"
        assert evidence["order"] == 5
        assert evidence["chapter"]["id"] == "ch-1"
        assert evidence["chapter"]["title"] == "素问篇"
        assert evidence["version"]["id"] == "v-1"
        assert evidence["version"]["name"] == "宋本"
        assert evidence["version"]["repository"] == "北京图书馆"
        assert evidence["version"]["shelf_mark"] == "善本12345"
        assert evidence["version"]["is_formal_source"] is True
        assert evidence["version"]["rights_statement"] == "CC0"
        assert evidence["version"]["persistent_identifier"] == "doi:10.1234/abc"
        assert evidence["version"]["is_withdrawn"] is False
        assert evidence["book"]["id"] == "b-1"
        assert evidence["book"]["title"] == "黄帝内经"
        assert evidence["evidence_complete"] is True
        assert evidence["is_formal_source"] is True
        # Lines 618->620: loc_parts non-empty → loc in citation
        assert "北京图书馆" in evidence["citation"]
        assert "善本12345" in evidence["citation"]

    async def test_citation_without_loc(self):
        """Lines 618->620: when repository/shelf_mark empty, no loc."""
        mock_session = AsyncMock()

        mock_passage = MagicMock()
        mock_passage.id = "p-2"
        mock_passage.content_text = "内容"
        mock_passage.translation = None
        mock_passage.notes = None
        mock_passage.order = 1
        mock_passage.chapter_id = "ch-2"

        mock_version = MagicMock()
        mock_version.id = "v-2"
        mock_version.version_name = "通行本"
        mock_version.era = ""
        mock_version.year = 0
        mock_version.repository = ""
        mock_version.shelf_mark = ""
        mock_version.source_url = None
        mock_version.is_formal_source = False
        mock_version.is_academic_citable = False
        mock_version.rights_statement = None
        mock_version.persistent_identifier = None
        mock_version.withdrawn_at = None
        mock_version.book_id = "b-2"

        mock_book = MagicMock()
        mock_book.id = "b-2"
        mock_book.title = "针灸甲乙经"
        mock_book.source_url = None

        mock_chapter = MagicMock()
        mock_chapter.id = "ch-2"
        mock_chapter.title = "卷一"

        mock_row = (mock_passage, mock_version, mock_book, mock_chapter)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_row
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = ResearchWorkflowService(mock_session)

        evidence = await svc._load_evidence("p-2")

        assert evidence["citation"] == "《针灸甲乙经》·通行本，卷一，第1条"
        assert "（" not in evidence["citation"]

    async def test_withdrawn_version_flag(self):
        """is_withdrawn is True when withdrawn_at is set."""
        mock_session = AsyncMock()

        mock_passage = MagicMock()
        mock_passage.id = "p-3"
        mock_passage.content_text = "content"
        mock_passage.translation = None
        mock_passage.notes = None
        mock_passage.order = 1
        mock_passage.chapter_id = "ch-3"

        mock_version = MagicMock()
        mock_version.id = "v-3"
        mock_version.version_name = "V3"
        mock_version.era = ""
        mock_version.year = 0
        mock_version.repository = ""
        mock_version.shelf_mark = ""
        mock_version.source_url = None
        mock_version.is_formal_source = False
        mock_version.is_academic_citable = False
        mock_version.rights_statement = None
        mock_version.persistent_identifier = None
        mock_version.withdrawn_at = "2025-06-01"
        mock_version.book_id = "b-3"

        mock_book = MagicMock()
        mock_book.id = "b-3"
        mock_book.title = "Book"
        mock_book.source_url = None

        mock_chapter = MagicMock()
        mock_chapter.id = "ch-3"
        mock_chapter.title = "Ch"

        mock_row = (mock_passage, mock_version, mock_book, mock_chapter)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_row
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = ResearchWorkflowService(mock_session)

        evidence = await svc._load_evidence("p-3")

        assert evidence["version"]["is_withdrawn"] is True


# =============================================================================
# _build_retrieval_snapshot — lines 672-870
# =============================================================================


@pytest.mark.asyncio
class TestBuildRetrievalSnapshot:
    """Cover _build_retrieval_snapshot: snapshot=None TraceLineageError
    (683-685), happy path with DB mocks (696-870)."""

    async def test_snapshot_none_raises_trace_lineage_error(self):
        """Lines 683-685: retrieval_snapshot is None → TraceLineageError."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.evidence_trace = []

        from app.services.trace_lineage import TraceLineageError

        with pytest.raises(TraceLineageError,
                           match="TRACE_LINEAGE_INCOMPLETE"):
            await _build_retrieval_snapshot(
                mock_session, mock_result,
                retrieval_snapshot=None,
            )

    async def test_full_happy_path_with_source_refs(self):
        """Lines 696-870: complete pipeline with evidence traces, SourceRefs,
        and InternalTraceRecord construction."""
        mock_session = AsyncMock()

        trace1 = _make_evidence_trace(doc_id="doc-1", chk_id="chk-1",
                                      claim="Claim 1", quote="Quote 1")
        trace2 = _make_evidence_trace(doc_id="doc-1", chk_id="chk-2",
                                      claim="Claim 2", quote="Quote 2")
        mock_result = MagicMock()
        mock_result.evidence_trace = [trace1, trace2]

        retrieval_snapshot = {
            "chk-1": {"score": 0.95, "retrieval_method": "keyword"},
            "chk-2": {"score": 0.88, "retrieval_method": "semantic"},
        }

        execute_returns = []

        # Query 1: chunk_stmt → all() returns [(cid, did, pid)]
        chunk_row1 = _chunk_row("doc-1", "chk-1", "p-001")
        chunk_row2 = _chunk_row("doc-1", "chk-2", "p-002")
        r1 = MagicMock()
        r1.all.return_value = [chunk_row1, chunk_row2]
        execute_returns.append(r1)

        # Query 2: passage-scope SourceRef → scalars().all()
        sr1 = _make_sourceref_mock(sr_id="sr-1", location="passage:p-001",
                                    title="Source One", url="http://ex.com/1")
        r2 = MagicMock()
        r2_scalars = MagicMock()
        r2_scalars.all.return_value = [sr1]
        r2.scalars.return_value = r2_scalars
        execute_returns.append(r2)

        # Query 3: document-scope SourceRef → scalars().all()
        sr_doc = _make_sourceref_mock(
            sr_id="sr-doc-1", location="document:doc-1",
            title="Doc Source", url="http://ex.com/doc",
        )
        r3 = MagicMock()
        r3_scalars = MagicMock()
        r3_scalars.all.return_value = [sr_doc]
        r3.scalars.return_value = r3_scalars
        execute_returns.append(r3)

        # Query 4+5: chunk passage_id queries
        r4 = MagicMock()
        r4.one_or_none.return_value = _passage_row("p-001")
        execute_returns.append(r4)

        r5 = MagicMock()
        r5.one_or_none.return_value = _passage_row("p-002")
        execute_returns.append(r5)

        mock_session.execute = AsyncMock(side_effect=execute_returns)

        snapshot, internal_traces = await _build_retrieval_snapshot(
            mock_session, mock_result,
            retrieval_snapshot=retrieval_snapshot,
        )

        assert len(snapshot) == 2
        assert snapshot[0]["document_id"] == "doc-1"
        assert snapshot[0]["chunk_id"] == "chk-1"
        assert "trace_id" in snapshot[0]
        assert snapshot[0]["source_ref_id"] == "sr-1"
        assert snapshot[0]["source_ref_url"] == "http://ex.com/1"

        assert snapshot[1]["source_ref_id"] is None

        assert len(internal_traces) == 2
        assert internal_traces[0].passage_id == "p-001"
        assert internal_traces[0].provenance_kind == "retrieval"
        assert internal_traces[0].retrieval_score == 0.95
        assert internal_traces[0].retrieval_method == "keyword"
        assert internal_traces[1].passage_id == "p-002"
        assert internal_traces[1].retrieval_score == 0.88
        assert internal_traces[1].retrieval_method == "semantic"

    async def test_dedup_duplicate_chunks(self):
        """Duplicate (document_id, chunk_id) → only one snapshot entry."""
        mock_session = AsyncMock()

        trace1 = _make_evidence_trace(doc_id="doc-1", chk_id="chk-1")
        trace2 = _make_evidence_trace(doc_id="doc-1", chk_id="chk-1")
        mock_result = MagicMock()
        mock_result.evidence_trace = [trace1, trace2]

        retrieval_snapshot = {
            "chk-1": {"score": 0.95, "retrieval_method": "keyword"},
        }

        chunk_row = _chunk_row("doc-1", "chk-1", "p-001")
        r1 = MagicMock()
        r1.all.return_value = [chunk_row]

        r2 = MagicMock()
        r2_scalars = MagicMock()
        r2_scalars.all.return_value = []
        r2.scalars.return_value = r2_scalars

        r3 = MagicMock()
        r3_scalars = MagicMock()
        r3_scalars.all.return_value = []
        r3.scalars.return_value = r3_scalars

        r4 = MagicMock()
        r4.one_or_none.return_value = _passage_row("p-001")

        mock_session.execute = AsyncMock(side_effect=[r1, r2, r3, r4])

        snapshot, internal_traces = await _build_retrieval_snapshot(
            mock_session, mock_result,
            retrieval_snapshot=retrieval_snapshot,
        )

        assert len(snapshot) == 1
        assert len(internal_traces) == 1

    async def test_chunk_without_passage_id_skipped_from_traces(self):
        """Lines 850-856: chunk without passage_id → in snapshot but not
        in internal_traces."""
        mock_session = AsyncMock()

        trace = _make_evidence_trace(doc_id="doc-1", chk_id="chk-1")
        mock_result = MagicMock()
        mock_result.evidence_trace = [trace]

        retrieval_snapshot = {
            "chk-1": {"score": 0.95, "retrieval_method": "keyword"},
        }

        chunk_row = _chunk_row("doc-1", "chk-1", "")
        r1 = MagicMock()
        r1.all.return_value = [chunk_row]

        r2 = MagicMock()
        r2_scalars = MagicMock()
        r2_scalars.all.return_value = []
        r2.scalars.return_value = r2_scalars

        r3 = MagicMock()
        r3_scalars = MagicMock()
        r3_scalars.all.return_value = []
        r3.scalars.return_value = r3_scalars

        r4 = MagicMock()
        r4.one_or_none.return_value = None

        mock_session.execute = AsyncMock(side_effect=[r1, r2, r3, r4])

        snapshot, internal_traces = await _build_retrieval_snapshot(
            mock_session, mock_result,
            retrieval_snapshot=retrieval_snapshot,
        )

        assert len(snapshot) == 1
        assert len(internal_traces) == 0

    async def test_document_scoped_source_ref_fallback(self):
        """When chunk has no passage_id, document-scoped SourceRef is used
        as fallback."""
        mock_session = AsyncMock()

        trace = _make_evidence_trace(doc_id="doc-1", chk_id="chk-1")
        mock_result = MagicMock()
        mock_result.evidence_trace = [trace]

        retrieval_snapshot = {
            "chk-1": {"score": 0.95, "retrieval_method": "keyword"},
        }

        chunk_row = _chunk_row("doc-1", "chk-1", "")
        r1 = MagicMock()
        r1.all.return_value = [chunk_row]

        r2 = MagicMock()
        r2_scalars = MagicMock()
        r2_scalars.all.return_value = []
        r2.scalars.return_value = r2_scalars

        sr_doc = _make_sourceref_mock(
            sr_id="sr-doc-fb", location="document:doc-1",
            title="Doc Fallback",
        )
        r3 = MagicMock()
        r3_scalars = MagicMock()
        r3_scalars.all.return_value = [sr_doc]
        r3.scalars.return_value = r3_scalars

        r4 = MagicMock()
        r4.one_or_none.return_value = None

        mock_session.execute = AsyncMock(side_effect=[r1, r2, r3, r4])

        snapshot, internal_traces = await _build_retrieval_snapshot(
            mock_session, mock_result,
            retrieval_snapshot=retrieval_snapshot,
        )

        assert len(snapshot) == 1
        assert snapshot[0]["source_ref_id"] == "sr-doc-fb"
        assert snapshot[0]["source_ref_url"] == "http://ex.com"
        assert len(internal_traces) == 0


# =============================================================================
# _pack_academic_step — line 882
# =============================================================================


@pytest.mark.asyncio
class TestPackAcademicStep:
    """Cover _pack_academic_step — mocks build_internal_traces (line 882)."""

    async def test_pack_academic_step_mocks_traces(self):
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.decomposition = [MagicMock(), MagicMock(), MagicMock()]
        mock_result.evidence_trace = []

        tid_pack = make_trace_id("doc-pack", "chk-pack")
        fake_trace = InternalTraceRecord(
            trace_id=tid_pack,
            document_id="doc-pack",
            chunk_id="chk-pack",
            passage_id="p-pack",
            provenance_kind="retrieval",
            retrieval_score=0.9,
            retrieval_method="semantic",
            timestamp="2026-01-01T00:00:00",
        )

        with patch(
            "app.services.research_workflow_service.build_internal_traces",
            new_callable=AsyncMock,
        ) as mock_build:
            mock_build.return_value = [fake_trace]

            result = await _pack_academic_step(
                mock_session,
                mock_result,
                topic="经络",
                retrieval_snapshot={"chk-pack": {"score": 0.9,
                                                  "retrieval_method": "semantic"}},
            )

        mock_build.assert_awaited_once()
        assert result["result"]["topic"] == "经络"
        assert result["result"]["sub_questions"] == 3
        assert result["trace_ids"] is not None
        assert result["source_documents"] is not None
        assert len(result["internal_traces"]) == 1
        assert result["internal_traces"][0].trace_id == tid_pack

    async def test_pack_academic_step_no_snapshot(self):
        """_pack_academic_step with retrieval_snapshot=None."""
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.decomposition = []
        mock_result.evidence_trace = []

        with patch(
            "app.services.research_workflow_service.build_internal_traces",
            new_callable=AsyncMock,
        ) as mock_build:
            mock_build.return_value = []

            result = await _pack_academic_step(
                mock_session,
                mock_result,
                topic="test",
                retrieval_snapshot=None,
            )

        mock_build.assert_awaited_once()
        assert result["result"]["sub_questions"] == 0
        assert result["internal_traces"] == []
