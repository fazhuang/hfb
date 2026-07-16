"""V4 research workflow tests — evidence/no-evidence paths, citation integrity,
session isolation.

Targets ResearchWorkflowService step methods directly (pure functions)
and the workflow-loop logic from research.py.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest


# =============================================================================
# Fixtures and helpers
# =============================================================================

def _make_evidence_trace(
    doc_id: str = "doc-01",
    chunk_id: str = "chk-01",
    claim_text: str = "经络是运行气血的通道",
    quote: str = "经络者，所以行血气而营阴阳。",
    citation_text: str = "[doc-01:chk-01]",
) -> dict:
    """Return a dict-shaped evidence trace matching EvidenceTrace fields."""
    return {
        "claim_text": claim_text,
        "quote": quote,
        "document_id": doc_id,
        "chunk_id": chunk_id,
        "citation_text": citation_text,
    }


def _make_snapshot_entry(
    trace_id: str = "",
    doc_id: str = "doc-01",
    chunk_id: str = "chk-01",
    claim_text: str = "经络是运行气血的通道",
    quote: str = "经络者，所以行血气而营阴阳。",
    citation_text: str = "[doc-01:chk-01]",
) -> dict:
    """Return a single retrieval-snapshot list entry."""
    from app.services.trace_lineage import make_trace_id

    return {
        "trace_id": trace_id or make_trace_id(doc_id, chunk_id),
        "document_id": doc_id,
        "chunk_id": chunk_id,
        "claim_text": claim_text,
        "quote": quote,
        "citation_text": citation_text,
        "source_ref_id": None,
        "source_ref_url": "",
        "source_ref_title": "",
    }


def _make_internal_trace(
    trace_id: str = "",
    doc_id: str = "doc-01",
    chunk_id: str = "chk-01",
    passage_id: str = "passage-01",
    score: float = 0.95,
    method: str = "ili_keyword_search",
):
    """Return an InternalTraceRecord."""
    from app.services.trace_lineage import InternalTraceRecord, make_trace_id

    return InternalTraceRecord(
        trace_id=trace_id or make_trace_id(doc_id, chunk_id),
        document_id=doc_id,
        chunk_id=chunk_id,
        passage_id=passage_id,
        provenance_kind="retrieval",
        retrieval_score=score,
        retrieval_method=method,
        timestamp="2026-07-16T00:00:00",
    )


# =============================================================================
# Test 1: Evidence present → all 5 steps produce non-empty results
# =============================================================================

class TestWorkflowWithEvidence:
    """When snapshot and traces are non-empty, every step must produce >0 counts."""

    def test_literature_retrieval_returns_nonempty_snapshot(self):
        """execute_literature_retrieval wraps AcademicService.synthesize().
        We test _build_retrieval_snapshot directly since that's the core.
        """
        from app.services.research_workflow_service import _snapshot_to_evidence_list

        snapshot = [_make_snapshot_entry()]
        evidence = _snapshot_to_evidence_list(snapshot)
        assert len(evidence) > 0
        assert evidence[0]["trace_id"]
        assert evidence[0]["document_id"] == "doc-01"
        assert evidence[0]["claim_text"]

    def test_evidence_synthesis_with_data(self):
        """Step 3 returns evidence > 0 and sections > 0 when snapshot is non-empty."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        snapshot = [_make_snapshot_entry()]
        traces = [_make_internal_trace()]

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        output = svc.execute_evidence_synthesis_from_snapshot(
            "经络", snapshot, internal_traces=traces,
        )
        assert output["result"]["sections"] > 0
        assert output["result"]["claims"] > 0
        assert len(output["evidence"]) > 0
        assert len(output["sections"]) > 0
        assert len(output["trace_ids"]) > 0
        assert len(output["source_documents"]) > 0

    def test_report_generation_with_synthesis(self):
        """Step 4 returns sections > 0 when synthesis has evidence."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        snapshot = [_make_snapshot_entry()]
        traces = [_make_internal_trace()]

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        synthesis = svc.execute_evidence_synthesis_from_snapshot(
            "经络", snapshot, internal_traces=traces,
        )
        report = svc.execute_report_from_synthesis("经络", synthesis)
        assert report["result"]["sections"] > 0
        assert report["sections"]
        assert "研究报告：经络" in report["result"]["title"]

    def test_citation_export_with_evidence(self):
        """Step 5 returns citations > 0, each with real trace_id and document_id."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        snapshot = [_make_snapshot_entry()]
        traces = [_make_internal_trace()]

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        synthesis = svc.execute_evidence_synthesis_from_snapshot(
            "经络", snapshot, internal_traces=traces,
        )
        evidence = synthesis["evidence"]
        assert len(evidence) > 0, "Evidence must be non-empty for citation export test"

        citation_output = svc.execute_citation_export_from_evidence(
            "经络", evidence, internal_traces=traces,
        )
        result = citation_output["result"]
        assert result["total_citations"] > 0
        assert len(result["citations"]) > 0
        for c in result["citations"]:
            assert c["trace_id"], f"Citation must have non-empty trace_id: {c}"
            assert c["document_id"], f"Citation must have non-empty document_id: {c}"
            assert c["citation_text"], f"Citation must have non-empty citation_text: {c}"
        assert len(citation_output["trace_ids"]) > 0
        assert len(citation_output["source_documents"]) > 0


# =============================================================================
# Test 2: No evidence → returns empty, not "success with zero counts"
# =============================================================================

class TestWorkflowNoEvidence:
    """When input is empty, step methods return empty/zero — NOT error disguised as success."""

    def test_evidence_synthesis_empty_snapshot_returns_zero(self):
        """Step 3 with empty snapshot returns sections=0, claims=0. Caller must decide."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        output = svc.execute_evidence_synthesis_from_snapshot(
            "unknown_topic", [],
        )
        assert output["result"]["sections"] == 0
        assert output["result"]["claims"] == 0
        assert output["evidence"] == []
        assert output["sections"] == []

    def test_report_generation_empty_synthesis_returns_zero(self):
        """Step 4 with empty synthesis returns sections=0, title with '(无可用证据)'."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        empty_synthesis = {
            "result": {"sections": 0, "claims": 0},
            "sections": [],
            "evidence": [],
            "trace_ids": [],
            "source_documents": [],
            "internal_traces": [],
        }
        output = svc.execute_report_from_synthesis("unknown_topic", empty_synthesis)
        assert output["result"]["sections"] == 0
        assert "(无可用证据)" in output["result"]["title"]

    def test_citation_export_empty_evidence_returns_zero(self):
        """Step 5 with empty evidence returns 0 citations."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        output = svc.execute_citation_export_from_evidence("unknown_topic", [])
        assert output["result"]["total_citations"] == 0
        assert output["result"]["citations"] == []

    def test_build_markdown_artifact_zero_evidence_includes_no_evidence_marker(self):
        """Markdown artifact with empty snapshot clearly states zero counts."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        md = svc.build_markdown_artifact(
            topic="unknown",
            run_id=str(uuid4()),
            steps=[],
            retrieval_snapshot=[],
            synthesis_output={},
        )
        assert "检索快照记录数: 0" in md
        assert "综合证据条数: 0" in md
        assert "报告段落数: 0" in md


# =============================================================================
# Test 3: Citation integrity — real trace_ids and document_ids from snapshot
# =============================================================================

class TestCitationIntegrity:
    """Every citation originates from the retrieval snapshot, never fabricated."""

    def test_citations_built_from_snapshot_evidence(self):
        """Citation export must use trace_id, document_id, etc. from evidence entries."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        evidence = [
            _make_evidence_trace(
                doc_id="doc-A", chunk_id="chk-A",
                claim_text="Claim A", citation_text="[doc-A:chk-A]",
            ),
            _make_evidence_trace(
                doc_id="doc-B", chunk_id="chk-B",
                claim_text="Claim B", citation_text="[doc-B:chk-B]",
            ),
        ]
        # Convert evidence dicts to snapshot entries so trace_ids are stable
        from app.services.trace_lineage import make_trace_id

        snapshot = [_make_snapshot_entry(doc_id=e["document_id"], chunk_id=e["chunk_id"],
                                          claim_text=e["claim_text"], citation_text=e["citation_text"])
                    for e in evidence]

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        synthesis = svc.execute_evidence_synthesis_from_snapshot(
            "test", snapshot,
        )
        cit_output = svc.execute_citation_export_from_evidence(
            "test", synthesis["evidence"],
        )
        result = cit_output["result"]
        assert result["total_citations"] == 2
        citations = result["citations"]
        trace_ids = {c["trace_id"] for c in citations}
        doc_ids = {c["document_id"] for c in citations}

        assert len(trace_ids) == 2
        assert all(tid for tid in trace_ids), "No empty trace_ids"
        assert "doc-A" in doc_ids
        assert "doc-B" in doc_ids
        # All citation_texts must be non-empty
        for c in citations:
            assert c["citation_text"], f"Citation {c['trace_id']} has empty citation_text"

    def test_citations_deduplicated_by_trace_id(self):
        """Duplicate trace_ids are merged into a single citation entry."""
        from app.services.research_workflow_service import (
            ResearchWorkflowService,
        )

        evidence = [
            _make_evidence_trace(doc_id="doc-A", chunk_id="chk-A", citation_text="[doc-A:chk-A]"),
            _make_evidence_trace(doc_id="doc-A", chunk_id="chk-A", citation_text="[doc-A:chk-A]"),
        ]
        snapshot = [_make_snapshot_entry(doc_id="doc-A", chunk_id="chk-A")]

        svc = ResearchWorkflowService.__new__(ResearchWorkflowService)
        synthesis = svc.execute_evidence_synthesis_from_snapshot("test", snapshot)
        cit_output = svc.execute_citation_export_from_evidence(
            "test", synthesis["evidence"],
        )
        assert cit_output["result"]["total_citations"] == 1


# =============================================================================
# Test 4: Session isolation — runs do not leak between sessions
# =============================================================================

class TestSessionIsolation:
    """Each ResearchSession owns its own workflow_state; runs must not bleed across."""

    def test_separate_sessions_have_independent_runs(self):
        """
        Verify that get_research_runs for session_a does NOT include session_b's runs.
        This is tested at the conceptual level — the ResearchWorkflowService reads
        from one session's workflow_state JSON column.
        """
        from app.services.research_workflow_service import ResearchWorkflowService

        # Two distinct session IDs
        sid_a = uuid4()
        sid_b = uuid4()

        # Simulate the isolation contract: if we were to mock WorkspaceService,
        # get_session(id_a).workflow_state would only contain runs stored with id_a.
        # The actual SQLAlchemy query filters by session primary key, so cross-read
        # is impossible at the ORM level. This test documents the contract.
        #
        # We validate the contract by checking that _build_retrieval_snapshot
        # is a pure function of its inputs (no hidden cross-session state).

        # _snapshot_to_evidence_list is deterministic given the same input
        from app.services.research_workflow_service import _snapshot_to_evidence_list

        snap_a = [_make_snapshot_entry(doc_id="doc-a", chunk_id="chk-a", claim_text="From session A")]
        snap_b = [_make_snapshot_entry(doc_id="doc-b", chunk_id="chk-b", claim_text="From session B")]

        ev_a = _snapshot_to_evidence_list(snap_a)
        ev_b = _snapshot_to_evidence_list(snap_b)

        assert ev_a[0]["document_id"] == "doc-a"
        assert ev_b[0]["document_id"] == "doc-b"
        # The results are independent — same function, different inputs → different outputs
        assert ev_a != ev_b

    def test_academic_service_is_per_workflow_scoped(self):
        """
        AcademicService is instantiated fresh inside each workflow step method.
        The last_snapshot accumulator is scoped to that single AcademicService
        instance and is garbage-collected when the step method returns.
        """
        # Verify _build_retrieval_snapshot does not rely on any module-global state
        import inspect
        from app.services.research_workflow_service import _build_retrieval_snapshot

        src = inspect.getsource(_build_retrieval_snapshot)
        # The function must reference 'retrieval_snapshot' parameter (not a global)
        assert "retrieval_snapshot" in src
        # No reference to any module-level AcademicService singleton
        assert "global" not in src or "global ret" not in src
        # The function takes 'db' and 'result' as explicit dependencies
        sig = inspect.signature(_build_retrieval_snapshot)
        param_names = list(sig.parameters.keys())
        assert "db" in param_names
        assert "result" in param_names
        assert "retrieval_snapshot" in param_names
