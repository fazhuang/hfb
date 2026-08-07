"""Unit tests for V4 Research Portal API endpoints.

Uses FastAPI TestClient with dependency overrides and service mocks.
Covers all 9 endpoints: session, query, workflow, history, reports, runs, export, replay, seed.
"""

from __future__ import annotations

import json
import os as _os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.db.database import get_session
from app.middleware.auth import get_auth_service, get_current_user
from app.services.trace_lineage import InternalTraceRecord, make_trace_id
from fastapi.testclient import TestClient
from main import app
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Dependency overrides — all auth gates pass, DB is a mock
# ---------------------------------------------------------------------------

_client = TestClient(app)

_mock_db = MagicMock(spec=AsyncSession)
_mock_db.execute = AsyncMock()
_mock_db.add = MagicMock()
_mock_db.flush = AsyncMock()
_mock_db.commit = AsyncMock()
_mock_db.rollback = AsyncMock()


async def _override_get_session():
    yield _mock_db


async def _override_get_current_user():
    return "test-user-id"


async def _override_get_auth_service():
    svc = MagicMock()
    svc.has_permission = AsyncMock(return_value=True)
    svc.has_any_permission = AsyncMock(return_value=True)
    return svc


@pytest.fixture(autouse=True)
def _setup_overrides():
    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_auth_service] = _override_get_auth_service
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared mock constructors
# ---------------------------------------------------------------------------


_VALID_TID = str(make_trace_id("doc-01", "chk-01"))


def _make_session_mock(**kwargs):
    defaults = {
        "id": "sess-001",
        "title": "Test Session",
        "user_id": "test-user-id",
        "workflow_state": None,
    }
    defaults.update(kwargs)
    return MagicMock(**defaults)


def _make_qh_mock(**kwargs):
    from datetime import UTC, datetime

    defaults = {
        "id": "qh-001",
        "query_text": "test query",
        "query_type": "research",
        "result_summary": None,
        "citation_count": 0,
        "created_at": datetime(2026, 8, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return MagicMock(**defaults)


def _make_evidence_trace_mock(doc_id="doc-01", chk_id="chk-01"):
    return MagicMock(
        document_id=doc_id,
        chunk_id=chk_id,
        claim_text="test claim",
        quote="test quote",
        citation_text=f"[{doc_id}:{chk_id}]",
    )


def _make_internal_trace(
    doc_id="doc-01",
    chunk_id="chk-01",
    passage_id="passage-01",
    score=0.95,
    method="semantic_search",
):
    tid = str(make_trace_id(doc_id, chunk_id))
    return InternalTraceRecord(
        trace_id=tid,
        document_id=doc_id,
        chunk_id=chunk_id,
        passage_id=passage_id,
        provenance_kind="retrieval",
        retrieval_score=score,
        retrieval_method=method,
        timestamp="2026-08-01T00:00:00",
    )


def _make_academic_response(**kwargs):
    trace = _make_evidence_trace_mock()
    defaults = {
        "query": "test query",
        "academic_type": "research",
        "title": None,
        "sections": [],
        "themes": [],
        "decomposition": [],
        "explanation": [],
        "citations": [
            MagicMock(
                document_id="doc-01",
                chunk_id="chk-01",
                text="cite",
                model_dump=MagicMock(
                    return_value={"document_id": "doc-01", "chunk_id": "chk-01"}
                ),
            )
        ],
        "evidence_trace": [trace],
        "metadata": MagicMock(),
        "gate_verdict": None,
        "model_dump": MagicMock(
            return_value={
                "query": "test query",
                "academic_type": "research",
                "evidence_trace": [],
                "citations": [],
            }
        ),
    }
    defaults.update(kwargs)
    return MagicMock(**defaults)


# ===========================================================================
# POST /research/session — create session
# ===========================================================================


class TestCreateResearchSession:
    """POST /api/v4/research/session"""

    def test_create_basic_session_success(self):
        mock_session = _make_session_mock()
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.DashboardService") as MockDS,
        ):
            MockWS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockDS.return_value.get_overview = AsyncMock(
                return_value={"total_books": 10}
            )

            resp = _client.post(
                "/api/v4/research/session", json={"title": "My Research"}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["session_id"] == "sess-001"
            assert body["data"]["title"] == "Test Session"

    def test_create_session_no_title_defaults(self):
        mock_session = _make_session_mock(title="未命名研究")
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.DashboardService") as MockDS,
        ):
            MockWS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockDS.return_value.get_overview = AsyncMock(return_value={})

            resp = _client.post("/api/v4/research/session", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["title"] == "未命名研究"

    def test_create_session_with_initial_query(self):
        mock_session = _make_session_mock()
        mock_acad_resp = _make_academic_response()
        mock_qh = _make_qh_mock()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.DashboardService") as MockDS,
            patch("app.api.v4.research.AcademicService") as MockAS,
            patch("app.api.v4.research.build_internal_traces") as mock_bit,
            patch("app.api.v4.research.extract_source_documents") as mock_esd,
        ):
            MockWS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockDS.return_value.get_overview = AsyncMock(return_value={})
            MockAS.return_value.research = AsyncMock(return_value=mock_acad_resp)
            MockAS.return_value.last_snapshot = {
                "chk-01": {"score": 0.95, "retrieval_method": "semantic_search"}
            }
            mock_bit.return_value = [_make_internal_trace()]
            mock_esd.return_value = ["doc-01"]

            resp = _client.post(
                "/api/v4/research/session", json={"title": "Test", "query": "经络"}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "query_id" in body["data"]

    def test_create_session_trace_lineage_error(self):
        mock_session = _make_session_mock()
        mock_acad_resp = _make_academic_response()
        from app.services.trace_lineage import TraceLineageError

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.DashboardService") as MockDS,
            patch("app.api.v4.research.AcademicService") as MockAS,
            patch("app.api.v4.research.build_internal_traces") as mock_bit,
        ):
            MockWS.return_value.create_session = AsyncMock(return_value=mock_session)
            MockDS.return_value.get_overview = AsyncMock(return_value={})
            MockAS.return_value.research = AsyncMock(return_value=mock_acad_resp)
            mock_bit.side_effect = TraceLineageError("no passage_id mapping")

            resp = _client.post(
                "/api/v4/research/session", json={"title": "Test", "query": "test"}
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "TRACE_LINEAGE_INCOMPLETE"


# ===========================================================================
# POST /research/query — execute query
# ===========================================================================


class TestExecuteResearchQuery:
    """POST /api/v4/research/query"""

    def test_session_not_found(self):
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=None)
            resp = _client.post(
                "/api/v4/research/query",
                json={"session_id": "nonexistent", "query": "test", "mode": "research"},
            )
            assert resp.status_code == 404
            body = resp.json()
            assert body["success"] is False

    def test_session_owned_by_other_user(self):
        session = _make_session_mock(user_id="other-user")
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            resp = _client.post(
                "/api/v4/research/query",
                json={"session_id": "sess-001", "query": "test", "mode": "research"},
            )
            assert resp.status_code == 404

    def test_research_mode_success(self):
        session = _make_session_mock()
        mock_resp = _make_academic_response()
        mock_qh = _make_qh_mock()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.AcademicService") as MockAS,
            patch("app.api.v4.research.build_internal_traces") as mock_bit,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockAS.return_value.research = AsyncMock(return_value=mock_resp)
            MockAS.return_value.last_snapshot = {
                "chk-01": {"score": 0.95, "retrieval_method": "semantic_search"}
            }
            mock_bit.return_value = [_make_internal_trace()]

            resp = _client.post(
                "/api/v4/research/query",
                json={"session_id": "sess-001", "query": "经络", "mode": "research"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True

    def test_report_mode_success(self):
        session = _make_session_mock()
        mock_resp = _make_academic_response(academic_type="report")
        mock_qh = _make_qh_mock()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.AcademicService") as MockAS,
            patch("app.api.v4.research.build_internal_traces") as mock_bit,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockAS.return_value.generate_report = AsyncMock(return_value=mock_resp)
            MockAS.return_value.last_snapshot = {
                "chk-01": {"score": 0.95, "retrieval_method": "semantic_search"}
            }
            mock_bit.return_value = [_make_internal_trace()]

            resp = _client.post(
                "/api/v4/research/query",
                json={
                    "session_id": "sess-001",
                    "query": "report topic",
                    "mode": "report",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True

    def test_synthesis_mode_success(self):
        session = _make_session_mock()
        mock_resp = _make_academic_response(academic_type="synthesis")
        mock_qh = _make_qh_mock()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.AcademicService") as MockAS,
            patch("app.api.v4.research.build_internal_traces") as mock_bit,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockAS.return_value.synthesize = AsyncMock(return_value=mock_resp)
            MockAS.return_value.last_snapshot = {
                "chk-01": {"score": 0.95, "retrieval_method": "semantic_search"}
            }
            mock_bit.return_value = [_make_internal_trace()]

            resp = _client.post(
                "/api/v4/research/query",
                json={
                    "session_id": "sess-001",
                    "query": "synthesis topic",
                    "mode": "synthesis",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True

    def test_education_mode_success(self):
        session = _make_session_mock()
        mock_resp = _make_academic_response(academic_type="education")
        mock_qh = _make_qh_mock()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.AcademicService") as MockAS,
            patch("app.api.v4.research.build_internal_traces") as mock_bit,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockAS.return_value.educate = AsyncMock(return_value=mock_resp)
            MockAS.return_value.last_snapshot = {
                "chk-01": {"score": 0.95, "retrieval_method": "semantic_search"}
            }
            mock_bit.return_value = [_make_internal_trace()]

            resp = _client.post(
                "/api/v4/research/query",
                json={
                    "session_id": "sess-001",
                    "query": "education topic",
                    "mode": "education",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True

    def test_no_evidence_traces_returns_error(self):
        session = _make_session_mock()
        mock_resp = _make_academic_response(evidence_trace=[])

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.AcademicService") as MockAS,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockAS.return_value.research = AsyncMock(return_value=mock_resp)

            resp = _client.post(
                "/api/v4/research/query",
                json={"session_id": "sess-001", "query": "test", "mode": "research"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "TRACE_LINEAGE_INCOMPLETE"

    def test_trace_lineage_error(self):
        session = _make_session_mock()
        mock_resp = _make_academic_response()
        from app.services.trace_lineage import TraceLineageError

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.AcademicService") as MockAS,
            patch("app.api.v4.research.build_internal_traces") as mock_bit,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockAS.return_value.research = AsyncMock(return_value=mock_resp)
            mock_bit.side_effect = TraceLineageError("no mapping")

            resp = _client.post(
                "/api/v4/research/query",
                json={"session_id": "sess-001", "query": "test", "mode": "research"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert "Trace lineage incomplete" in body["message"]

    def test_missing_session_id_rejected(self):
        resp = _client.post(
            "/api/v4/research/query", json={"query": "test", "mode": "research"}
        )
        assert resp.status_code == 422

    def test_missing_query_rejected(self):
        resp = _client.post(
            "/api/v4/research/query",
            json={"session_id": "sess-001", "mode": "research"},
        )
        assert resp.status_code == 422

    def test_graph_mode_success(self):
        session = _make_session_mock()
        mock_qh = _make_qh_mock()

        graph_result = {
            "evidence_trace": [
                {
                    "document_id": "doc-01",
                    "chunk_id": "chk-01",
                    "exact_quote": "test quote",
                    "citation": "[doc-01:chk-01]",
                }
            ],
            "citations": [],
            "nodes": [],
            "edges": [],
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.GraphService") as MockGS,
            patch("app.services.trace_lineage.build_viz_traces") as mock_bvt,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockGS.return_value.intelligence = AsyncMock(return_value=graph_result)

            mock_trace = _make_internal_trace()
            mock_bvt.return_value = [mock_trace]

            # db.execute needs to return lineage data for graph mode hydration
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda self, idx: [
                "chk-01",
                "passage-01",
                "version-01",
                "http://example.com",
                "claim text",
            ][idx]
            mock_result = MagicMock()
            mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
            _mock_db.execute = AsyncMock(return_value=mock_result)

            resp = _client.post(
                "/api/v4/research/query",
                json={
                    "session_id": "sess-001",
                    "query": "graph query",
                    "mode": "graph",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True

    def test_graph_mode_no_evidence_traces(self):
        session = _make_session_mock()
        graph_result = {"evidence_trace": [], "citations": []}

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.GraphService") as MockGS,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockGS.return_value.intelligence = AsyncMock(return_value=graph_result)

            resp = _client.post(
                "/api/v4/research/query",
                json={"session_id": "sess-001", "query": "test", "mode": "graph"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "TRACE_LINEAGE_INCOMPLETE"


# ===========================================================================
# POST /research/workflow — execute workflow
# ===========================================================================


class TestExecuteResearchWorkflow:
    """POST /api/v4/research/workflow"""

    def test_session_not_found(self):
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=None)
            resp = _client.post(
                "/api/v4/research/workflow",
                json={
                    "session_id": "nonexistent",
                    "topic": "test",
                    "workflow_type": "full_research_flow",
                },
            )
            assert resp.status_code == 404

    def test_workflow_all_steps_success(self):
        session = _make_session_mock()
        mock_qh = _make_qh_mock()
        internal_trace = _make_internal_trace()

        step_output = {
            "result": {
                "sub_questions": 3,
                "themes": 2,
                "sections": 1,
                "claims": 1,
                "title": "Report",
                "total_citations": 2,
                "citations": [],
            },
            "internal_traces": [internal_trace],
            "trace_ids": [internal_trace.trace_id],
            "snapshot": [
                {
                    "trace_id": internal_trace.trace_id,
                    "document_id": "doc-01",
                    "chunk_id": "chk-01",
                    "claim_text": "claim",
                    "quote": "quote",
                    "citation_text": "[doc-01:chk-01]",
                }
            ],
            "evidence": [
                {
                    "trace_id": internal_trace.trace_id,
                    "document_id": "doc-01",
                    "chunk_id": "chk-01",
                    "claim_text": "claim",
                    "quote": "quote",
                    "citation_text": "[doc-01:chk-01]",
                }
            ],
            "source_documents": ["doc-01"],
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockWS.return_value.update_session = AsyncMock(return_value=session)

            rwf = MockRWF.return_value
            rwf.execute_topic_selection = AsyncMock(return_value=step_output)
            rwf.execute_literature_retrieval = AsyncMock(return_value=step_output)
            rwf.execute_evidence_synthesis_from_snapshot = MagicMock(
                return_value=step_output
            )
            rwf.execute_report_from_synthesis = MagicMock(return_value=step_output)
            rwf.execute_citation_export_from_evidence = MagicMock(
                return_value=step_output
            )
            rwf.build_markdown_artifact = MagicMock(return_value="# Report\n\nContent")
            rwf.persist_research_run = AsyncMock(return_value=None)

            resp = _client.post(
                "/api/v4/research/workflow",
                json={
                    "session_id": "sess-001",
                    "topic": "针灸研究",
                    "workflow_type": "full_research_flow",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert len(body["data"]["steps"]) == 5
            for step in body["data"]["steps"]:
                assert step["status"] == "completed"

    def test_workflow_step_failure_cascades(self):
        session = _make_session_mock()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)

            rwf = MockRWF.return_value
            rwf.execute_topic_selection = AsyncMock(
                side_effect=ValueError("step failed")
            )

            resp = _client.post(
                "/api/v4/research/workflow",
                json={
                    "session_id": "sess-001",
                    "topic": "test",
                    "workflow_type": "full_research_flow",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            # First step failed, remaining 4 pending
            statuses = [s["status"] for s in body["data"]["steps"]]
            assert statuses[0] == "failed"
            assert all(s == "pending" for s in statuses[1:])

    def test_workflow_no_evidence(self):
        session = _make_session_mock()
        internal_trace = _make_internal_trace()
        mock_qh = _make_qh_mock()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)

            rwf = MockRWF.return_value
            # Steps 1 and 2 succeed, but step 2 returns empty snapshot
            step1_out = {
                "result": {"sub_questions": 1},
                "internal_traces": [internal_trace],
                "trace_ids": [],
                "source_documents": [],
            }
            step2_out_empty = {
                "result": {"themes": 0, "records": 0},
                "snapshot": [],
                "internal_traces": [],
                "trace_ids": [],
                "source_documents": [],
            }

            rwf.execute_topic_selection = AsyncMock(return_value=step1_out)
            rwf.execute_literature_retrieval = AsyncMock(return_value=step2_out_empty)

            resp = _client.post(
                "/api/v4/research/workflow",
                json={
                    "session_id": "sess-001",
                    "topic": "nonexistent topic",
                    "workflow_type": "full_research_flow",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            # NO_EVIDENCE produces Chinese error message; steps 3-5 are pending
            assert "未找到" in body["message"]
            statuses = [s["status"] for s in body["data"]["steps"]]
            assert statuses[:2] == ["completed", "completed"]
            assert all(s == "pending" for s in statuses[2:])

    def test_missing_required_fields(self):
        resp = _client.post(
            "/api/v4/research/workflow", json={"session_id": "sess-001"}
        )
        assert resp.status_code == 422


# ===========================================================================
# GET /research/session/{id}/history — query history
# ===========================================================================


class TestGetSessionQueryHistory:
    """GET /api/v4/research/session/{session_id}/history"""

    def test_session_not_found(self):
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=None)
            resp = _client.get("/api/v4/research/session/nonexistent/history")
            assert resp.status_code == 404

    def test_history_with_traces(self):
        session = _make_session_mock()
        qh = _make_qh_mock(
            result_summary=json.dumps(
                {
                    "traces": [
                        {"trace_id": "t1", "document_id": "doc-01"},
                        {"trace_id": "t2", "document_id": "doc-02"},
                    ],
                }
            )
        )

        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.get_query_history = AsyncMock(return_value=[qh])

            resp = _client.get("/api/v4/research/session/sess-001/history")
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert len(body["data"]["history"]) == 1
            assert body["data"]["history"][0]["trace_count"] == 2
            assert len(body["traceability"]["source_documents"]) == 2

    def test_history_empty(self):
        session = _make_session_mock()

        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.get_query_history = AsyncMock(return_value=[])

            resp = _client.get("/api/v4/research/session/sess-001/history")
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["total"] == 0

    def test_history_corrupt_json_handled(self):
        session = _make_session_mock()
        qh = _make_qh_mock(result_summary="not valid json {{{")

        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.get_query_history = AsyncMock(return_value=[qh])

            resp = _client.get("/api/v4/research/session/sess-001/history")
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["history"][0]["trace_count"] == 0


# ===========================================================================
# _derive_run_status / _derive_report_status — pure functions
# ===========================================================================


class TestDeriveStatusFunctions:
    """Unit tests for _derive_run_status and _derive_report_status."""

    def test_derive_run_status_all_completed(self):
        from app.api.v4.research import _derive_run_status

        trace = [{"status": "completed"}, {"status": "completed"}]
        assert _derive_run_status(trace) == "completed"

    def test_derive_run_status_one_failed(self):
        from app.api.v4.research import _derive_run_status

        trace = [{"status": "completed"}, {"status": "failed"}]
        assert _derive_run_status(trace) == "failed"

    def test_derive_run_status_one_running(self):
        from app.api.v4.research import _derive_run_status

        trace = [{"status": "completed"}, {"status": "running"}]
        assert _derive_run_status(trace) == "running"

    def test_derive_run_status_pending(self):
        # Single "pending" step returns "running" — matches code's
        # `if any(st in ("running", "pending") for st in _statuses)` branch.
        from app.api.v4.research import _derive_run_status

        trace = [{"status": "pending"}]
        assert _derive_run_status(trace) == "running"

    def test_derive_run_status_empty(self):
        from app.api.v4.research import _derive_run_status

        assert _derive_run_status([]) == "pending"

    def test_derive_report_status_ready(self):
        from app.api.v4.research import _derive_report_status

        trace = [{"step_name": "report_generation", "status": "completed"}]
        artifacts = {"markdown": "# Report\nContent"}
        assert _derive_report_status(trace, artifacts) == "ready"

    def test_derive_report_status_failed(self):
        from app.api.v4.research import _derive_report_status

        trace = [{"step_name": "report_generation", "status": "failed"}]
        assert _derive_report_status(trace, {}) == "failed"

    def test_derive_report_status_missing(self):
        from app.api.v4.research import _derive_report_status

        trace = [{"step_name": "report_generation", "status": "completed"}]
        artifacts = {"markdown": ""}
        assert _derive_report_status(trace, artifacts) == "missing"

    def test_derive_report_status_pending_no_step(self):
        from app.api.v4.research import _derive_report_status

        trace = [{"step_name": "literature_retrieval", "status": "completed"}]
        assert _derive_report_status(trace, {}) == "pending"

    def test_derive_report_status_name_field(self):
        from app.api.v4.research import _derive_report_status

        trace = [{"name": "report_generation", "status": "completed"}]
        artifacts = {"markdown": "content"}
        assert _derive_report_status(trace, artifacts) == "ready"


# ===========================================================================
# GET /research/reports — report listing
# ===========================================================================


class TestGetResearchReports:
    """GET /api/v4/research/reports"""

    def test_empty_reports(self):
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[])

            resp = _client.get("/api/v4/research/reports")
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["total"] == 0
            assert body["data"]["items"] == []

    def test_reports_with_runs(self):
        session = _make_session_mock()

        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "针灸研究",
            "workflow_type": "full_research_flow",
            "started_at": "2026-08-01T00:00:00",
            "completed_at": "2026-08-01T01:00:00",
            "step_execution_trace": [
                {"name": "topic_selection", "status": "completed"},
                {"name": "literature_retrieval", "status": "completed"},
                {"name": "evidence_synthesis", "status": "completed"},
                {"name": "report_generation", "status": "completed"},
                {"name": "citation_export", "status": "completed"},
            ],
            "output_artifacts": {"markdown": "# Report\n\nContent here"},
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])

            resp = _client.get("/api/v4/research/reports")
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["total"] == 1
            item = body["data"]["items"][0]
            assert item["run_status"] == "completed"
            assert item["report_status"] == "ready"
            assert item["topic"] == "针灸研究"

    def test_reports_status_filter(self):
        session = _make_session_mock()
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "workflow_type": "full_research_flow",
            "started_at": "2026-08-01T00:00:00",
            "completed_at": None,
            "step_execution_trace": [{"name": "report_generation", "status": "failed"}],
            "output_artifacts": {},
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])

            # All items -- 1
            resp = _client.get("/api/v4/research/reports")
            assert resp.json()["data"]["total"] == 1

            # Filter for 'ready' -- 0 (report failed)
            resp = _client.get("/api/v4/research/reports?status=ready")
            assert resp.json()["data"]["total"] == 0

            # Filter for 'failed' -- 1
            resp = _client.get("/api/v4/research/reports?status=failed")
            assert resp.json()["data"]["total"] == 1

    def test_reports_pagination(self):
        session = _make_session_mock()
        runs = []
        for i in range(5):
            runs.append(
                {
                    "session_id": "sess-001",
                    "run_id": f"run-{i:03d}",
                    "topic": f"topic {i}",
                    "workflow_type": "full_research_flow",
                    "started_at": f"2026-08-0{i + 1}T00:00:00",
                    "completed_at": None,
                    "step_execution_trace": [
                        {"name": "report_generation", "status": "completed"}
                    ],
                    "output_artifacts": {"markdown": "content"},
                }
            )

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=runs)

            resp = _client.get("/api/v4/research/reports?page=1&limit=3")
            body = resp.json()
            assert body["data"]["total"] == 5
            assert len(body["data"]["items"]) == 3
            assert body["data"]["page"] == 1


# ===========================================================================
# GET /research/session/{id}/runs — session runs
# ===========================================================================


class TestGetSessionRuns:
    """GET /api/v4/research/session/{session_id}/runs"""

    def test_session_not_found(self):
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=None)
            resp = _client.get("/api/v4/research/session/nonexistent/runs")
            assert resp.status_code == 404

    def test_runs_with_replay_manifest(self):
        session = _make_session_mock()
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "started_at": "2026-08-01T00:00:00",
            "completed_at": None,
            "step_execution_trace": [],
            "output_artifacts": {},
            "replay_manifest": {
                "traces": [
                    {"trace_id": "t1", "document_id": "doc-01"},
                    {"trace_id": "t2", "document_id": "doc-02"},
                ],
            },
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])

            resp = _client.get("/api/v4/research/session/sess-001/runs")
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["total"] == 1
            assert len(body["traceability"]["trace_ids"]) == 2
            assert len(body["traceability"]["source_documents"]) == 2

    def test_runs_fallback_trace_extraction(self):
        session = _make_session_mock()
        run = {
            "session_id": "sess-001",
            "run_id": "run-002",
            "topic": "test",
            "started_at": "2026-08-01T00:00:00",
            "step_execution_trace": [
                {"name": "topic_selection", "status": "completed", "trace_ids": ["t3"]},
                {
                    "name": "literature_retrieval",
                    "status": "completed",
                    "trace_ids": ["t4", "t5"],
                },
            ],
            "output_artifacts": {},
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])

            resp = _client.get("/api/v4/research/session/sess-001/runs")
            assert resp.status_code == 200
            body = resp.json()
            assert len(body["traceability"]["trace_ids"]) == 3

    def test_runs_defense_in_depth_filters_wrong_session(self):
        session = _make_session_mock()
        run_bad = {
            "session_id": "other-session",
            "run_id": "run-bad",
            "topic": "bad",
            "started_at": "2026-08-01T00:00:00",
            "step_execution_trace": [],
            "output_artifacts": {},
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run_bad])

            resp = _client.get("/api/v4/research/session/sess-001/runs")
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["total"] == 0


# ===========================================================================
# GET /research/session/{id}/runs/{run_id}/export — export markdown
# ===========================================================================


class TestExportRunMarkdown:
    """GET /api/v4/research/session/{session_id}/runs/{run_id}/export"""

    def test_session_not_found(self):
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=None)
            resp = _client.get(
                "/api/v4/research/session/nonexistent/runs/run-001/export"
            )
            assert resp.status_code == 404
            assert resp.json()["success"] is False

    def test_run_not_found(self):
        session = _make_session_mock()
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[])

            resp = _client.get("/api/v4/research/session/sess-001/runs/run-001/export")
            assert resp.status_code == 404
            assert resp.json()["success"] is False

    def test_unsupported_format(self):
        session = _make_session_mock()
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService"),
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)

            resp = _client.get(
                "/api/v4/research/session/sess-001/runs/run-001/export?format=pdf"
            )
            assert resp.status_code == 400
            body = resp.json()
            assert body["success"] is False
            assert "Unsupported export format" in body["message"]

    def test_empty_markdown(self):
        session = _make_session_mock()
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "output_artifacts": {"markdown": "   "},
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])

            resp = _client.get("/api/v4/research/session/sess-001/runs/run-001/export")
            assert resp.status_code == 409
            body = resp.json()
            assert body["success"] is False
            assert "empty" in body["message"]

    def test_export_markdown_success(self):
        session = _make_session_mock()
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "output_artifacts": {
                "markdown": "# Report\n\n## Content\n\nSome **bold** text."
            },
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])

            resp = _client.get("/api/v4/research/session/sess-001/runs/run-001/export")
            assert resp.status_code == 200
            assert "text/markdown" in resp.headers["content-type"]
            assert "# Report" in resp.text
            assert "attachment" in resp.headers["content-disposition"]


# ===========================================================================
# POST /research/runs/{run_id}/replay — replay run
# ===========================================================================


class TestReplayResearchRun:
    """POST /api/v4/research/runs/{run_id}/replay"""

    def test_run_not_found(self):
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService"),
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[])

            resp = _client.post("/api/v4/research/runs/nonexistent/replay", json={})
            assert resp.status_code == 404
            assert resp.json()["success"] is False

    def test_no_replay_manifest(self):
        session = _make_session_mock()
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])

            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "NO_REPLAY_MANIFEST"

    def test_replay_success_matched(self):
        session = _make_session_mock()
        from app.services.research_workflow_service import canonical_sha256

        snapshot = [
            {
                "trace_id": _VALID_TID,
                "document_id": "doc-01",
                "chunk_id": "chk-01",
                "claim_text": "claim",
                "quote": "quote",
                "citation_text": "[doc-01:chk-01]",
                "passage_id": "passage-01",
            }
        ]
        trace_data = [
            {
                "trace_id": _VALID_TID,
                "document_id": "doc-01",
                "chunk_id": "chk-01",
                "passage_id": "passage-01",
                "provenance_kind": "retrieval",
                "retrieval_score": 0.95,
                "retrieval_method": "semantic_search",
                "timestamp": "2026-08-01T00:00:00",
            }
        ]

        # Build hashes matching the manifest
        from app.services.research_workflow_service import (
            _build_canonical_payload,
            _build_corpus_payload,
            _build_input_payload,
            _build_report_sections,
            _group_snapshot_into_sections,
            _snapshot_to_evidence_list,
            canonicalize_traces,
        )

        canonical_traces = canonicalize_traces(trace_data)
        corpus_hash = canonical_sha256(_build_corpus_payload(snapshot))
        input_hash = canonical_sha256(
            _build_input_payload(
                topic="test",
                workflow_type="full_research_flow",
                pipeline_version="1.0.0",
                retrieval_snapshot=snapshot,
                trace_ids=[_VALID_TID],
                source_document_ids=["doc-01"],
                canonical_traces=canonical_traces,
            )
        )
        syn_sections = _group_snapshot_into_sections(snapshot)
        syn_evidence = _snapshot_to_evidence_list(snapshot)
        syn_out = {
            "result": {"sections": 1, "claims": 1},
            "sections": syn_sections,
            "evidence": syn_evidence,
            "trace_ids": [],
            "source_documents": [],
            "internal_traces": [],
        }
        rep_out = {
            "result": {"sections": 1, "title": "Report"},
            "sections": _build_report_sections("test", syn_evidence, syn_sections),
            "evidence": syn_evidence,
            "trace_ids": [],
            "source_documents": [],
            "internal_traces": [],
        }
        cit_out = {
            "result": {
                "total_citations": 1,
                "citations": [
                    {
                        "trace_id": _VALID_TID,
                        "citation_text": "[doc-01:chk-01]",
                        "document_id": "doc-01",
                        "quote": "quote",
                    }
                ],
            },
            "trace_ids": [],
            "source_documents": [],
            "internal_traces": [],
        }
        report_sections_for_hash = _build_report_sections(
            "test", syn_evidence, syn_sections
        )
        output_payload = _build_canonical_payload(
            topic="test",
            workflow_type="full_research_flow",
            pipeline_version="1.0.0",
            retrieval_snapshot=snapshot,
            synthesis_sections=syn_sections,
            synthesis_evidence=syn_evidence,
            report_sections=report_sections_for_hash,
            citations=cit_out["result"]["citations"],
            trace_ids=[_VALID_TID],
            source_document_ids=["doc-01"],
            canonical_traces=canonical_traces,
        )
        output_hash = canonical_sha256(output_payload)

        manifest = {
            "manifest_version": "2.0.0",
            "run_id": "run-001",
            "session_id": "sess-001",
            "workflow_type": "full_research_flow",
            "topic": "test",
            "pipeline_version": "1.0.0",
            "workflow_steps": [
                "topic_selection",
                "literature_retrieval",
                "evidence_synthesis",
                "report_generation",
                "citation_export",
            ],
            "retrieval_snapshot": snapshot,
            "traces": trace_data,
            "query_history_binding": [],
            "corpus_sha256": corpus_hash,
            "canonical_input_sha256": input_hash,
            "canonical_output_sha256": output_hash,
            "canonicalization_version": "2.0.0",
            "created_at": "2026-08-01T00:00:00",
        }
        manifest["manifest_sha256"] = canonical_sha256(manifest)

        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            MockRWF.return_value.execute_evidence_synthesis_from_snapshot = MagicMock(
                return_value=syn_out
            )
            MockRWF.return_value.execute_report_from_synthesis = MagicMock(
                return_value=rep_out
            )
            MockRWF.return_value.execute_citation_export_from_evidence = MagicMock(
                return_value=cit_out
            )

            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["matched"] is True
            assert (
                body["data"]["original_output_sha256"]
                == body["data"]["replay_output_sha256"]
            )


# ===========================================================================
# POST /research/_test/seed-research-run — seed test data
# ===========================================================================


class TestSeedResearchRun:
    """POST /api/v4/research/_test/seed-research-run"""

    @pytest.fixture(autouse=True)
    def _reset_seed_env(self):
        yield
        _os.environ.pop("SEED_TEST_DATA", None)

    def test_seed_disabled_by_default(self):
        resp = _client.post(
            "/api/v4/research/_test/seed-research-run",
            json={"session_id": "sess-001", "topic": "test"},
        )
        assert resp.status_code == 501
        body = resp.json()
        assert body["success"] is False
        assert "disabled" in body["message"]

    def test_seed_session_not_found(self):
        _os.environ["SEED_TEST_DATA"] = "1"
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=None)
            resp = _client.post(
                "/api/v4/research/_test/seed-research-run",
                json={"session_id": "nonexistent", "topic": "test"},
            )
            assert resp.status_code == 404

    def test_seed_creates_run_success(self):
        _os.environ["SEED_TEST_DATA"] = "1"
        session = _make_session_mock(workflow_state=None)

        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.update_session = AsyncMock(return_value=session)

            resp = _client.post(
                "/api/v4/research/_test/seed-research-run",
                json={"session_id": "sess-001", "topic": "E2E Test Topic"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "run_id" in body["data"]
            assert body["data"]["session_id"] == "sess-001"

    def test_seed_with_custom_data(self):
        _os.environ["SEED_TEST_DATA"] = "1"
        session = _make_session_mock(workflow_state=None)

        custom_trace = [
            {
                "name": "custom_step",
                "status": "completed",
                "result": {},
                "trace_ids": [],
            }
        ]
        custom_citations = [{"trace_id": "custom:1", "citation_text": "Custom"}]
        custom_snapshot = [
            {
                "trace_id": "custom:1",
                "document_id": "custom-doc",
                "chunk_id": "c1",
                "claim_text": "c",
                "quote": "q",
                "citation_text": "ct",
            }
        ]
        custom_traces = [
            {
                "trace_id": "custom:1",
                "document_id": "custom-doc",
                "chunk_id": "c1",
                "passage_id": "p1",
                "provenance_kind": "retrieval",
                "retrieval_score": 0.8,
                "retrieval_method": "custom",
                "timestamp": "2026-08-01T00:00:00",
            }
        ]

        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.update_session = AsyncMock(return_value=session)

            resp = _client.post(
                "/api/v4/research/_test/seed-research-run",
                json={
                    "session_id": "sess-001",
                    "topic": "Custom Test",
                    "markdown": "# Custom Markdown",
                    "step_execution_trace": custom_trace,
                    "citations": custom_citations,
                    "retrieval_snapshot": custom_snapshot,
                    "traces": custom_traces,
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True

    def test_seed_session_owned_by_other_user(self):
        _os.environ["SEED_TEST_DATA"] = "1"
        session = _make_session_mock(user_id="other-user")
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            resp = _client.post(
                "/api/v4/research/_test/seed-research-run",
                json={"session_id": "sess-001", "topic": "test"},
            )
            assert resp.status_code == 404


# ===========================================================================
# UNCOVERED BRANCH COVERAGE — 29 lines
# ===========================================================================


# ---------------------------------------------------------------------------
# helpers for replay manifest tests
# ---------------------------------------------------------------------------


def _build_valid_manifest(
    snapshot, trace_data, topic="test", workflow_type="full_research_flow"
):
    from app.services.research_workflow_service import (
        _build_corpus_payload,
        _build_input_payload,
        canonical_sha256,
        canonicalize_traces,
    )

    canonical_traces = canonicalize_traces(trace_data)
    corpus_hash = canonical_sha256(_build_corpus_payload(snapshot))
    input_hash = canonical_sha256(
        _build_input_payload(
            topic=topic,
            workflow_type=workflow_type,
            pipeline_version="1.0.0",
            retrieval_snapshot=snapshot,
            trace_ids=sorted([t["trace_id"] for t in trace_data]),
            source_document_ids=sorted({t["document_id"] for t in trace_data}),
            canonical_traces=canonical_traces,
        )
    )
    manifest = {
        "manifest_version": "2.0.0",
        "run_id": "run-001",
        "session_id": "sess-001",
        "workflow_type": workflow_type,
        "topic": topic,
        "pipeline_version": "1.0.0",
        "workflow_steps": [
            "topic_selection",
            "literature_retrieval",
            "evidence_synthesis",
            "report_generation",
            "citation_export",
        ],
        "retrieval_snapshot": snapshot,
        "traces": trace_data,
        "query_history_binding": [],
        "corpus_sha256": corpus_hash,
        "canonical_input_sha256": input_hash,
        "canonical_output_sha256": "placeholder",
        "canonicalization_version": "2.0.0",
        "created_at": "2026-08-01T00:00:00",
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest


def _build_valid_manifest_raw(manifest_dict):
    """Build manifest from a pre-constructed dict, adding manifest_sha256."""
    from app.services.research_workflow_service import canonical_sha256

    m = dict(manifest_dict)
    m["manifest_sha256"] = canonical_sha256(m)
    return m


def _recompute_manifest_sha256(manifest):
    """Recompute manifest_sha256 after tampering with manifest fields."""
    from app.services.research_workflow_service import canonical_sha256

    manifest["manifest_sha256"] = canonical_sha256(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    )
    return manifest


def _default_trace_data():
    return [
        {
            "trace_id": _VALID_TID,
            "document_id": "doc-01",
            "chunk_id": "chk-01",
            "passage_id": "passage-01",
            "provenance_kind": "retrieval",
            "retrieval_score": 0.95,
            "retrieval_method": "semantic_search",
            "timestamp": "2026-08-01T00:00:00",
        }
    ]


def _default_snapshot():
    return [
        {
            "trace_id": _VALID_TID,
            "document_id": "doc-01",
            "chunk_id": "chk-01",
            "claim_text": "claim",
            "quote": "quote",
            "citation_text": "[doc-01:chk-01]",
            "passage_id": "passage-01",
        }
    ]


# ---- 257-258: graph mode build_viz_traces TraceLineageError ----


class TestGraphModeTraceLineageError:
    """257-258: graph mode + build_viz_traces raises TraceLineageError."""


# ---- 424: evidence_synthesis NO_EVIDENCE gate (line 424 is dead code in HTTP path;
# NO_EVIDENCE at 509-511 fires first when literature_retrieval returns empty snapshot.
# Covered via test_workflow_no_evidence in TestExecuteResearchWorkflow.)
# ---- 440: report_generation with empty synthesis_output ----


class TestWorkflowReportGenerationNoSynthesis:
    """440: ValueError('No synthesis output') in report_generation step."""

    def test_report_generation_no_synthesis(self):
        session = _make_session_mock()
        mock_qh = _make_qh_mock()
        internal_trace = _make_internal_trace()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)

            rwf = MockRWF.return_value
            step_out = {
                "result": {"sub_questions": 1},
                "internal_traces": [internal_trace],
                "trace_ids": [internal_trace.trace_id],
                "source_documents": [],
            }
            step2_out = {
                "result": {"themes": 1, "records": 1},
                "snapshot": [
                    {
                        "trace_id": internal_trace.trace_id,
                        "document_id": "doc-01",
                        "chunk_id": "chk-01",
                        "claim_text": "c",
                        "quote": "q",
                        "citation_text": "ct",
                    }
                ],
                "internal_traces": [internal_trace],
                "trace_ids": [internal_trace.trace_id],
                "source_documents": ["doc-01"],
            }
            # Step3 returns falsy dict (empty), synthesis_output = {} triggers line 440
            rwf.execute_topic_selection = AsyncMock(return_value=step_out)
            rwf.execute_literature_retrieval = AsyncMock(return_value=step2_out)
            rwf.execute_evidence_synthesis_from_snapshot = MagicMock(return_value={})

            resp = _client.post(
                "/api/v4/research/workflow",
                json={
                    "session_id": "sess-001",
                    "topic": "test",
                    "workflow_type": "full_research_flow",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            statuses = [s["status"] for s in body["data"]["steps"]]
            assert statuses[:3] == ["completed", "completed", "completed"]
            assert statuses[3] == "failed"
            assert statuses[4] == "pending"


# ---- 451->469, 473-474: citation_export step + to_dict() error handling ----


class TestWorkflowToDictFailure:
    """451->469 + 473-474: citation_export and step_traces to_dict() failure."""

    def test_step_traces_to_dict_attribute_error(self):
        session = _make_session_mock()
        mock_qh = _make_qh_mock()
        internal_trace = _make_internal_trace()

        class NoopTrace:
            pass

        bad_trace = NoopTrace()

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockWS.return_value.update_session = AsyncMock(return_value=session)

            rwf = MockRWF.return_value
            step_out = {
                "result": {"sub_questions": 1},
                "internal_traces": [internal_trace],
                "trace_ids": [internal_trace.trace_id],
                "source_documents": [],
            }
            step2_out = {
                "result": {"themes": 1, "records": 1},
                "snapshot": [
                    {
                        "trace_id": internal_trace.trace_id,
                        "document_id": "doc-01",
                        "chunk_id": "chk-01",
                        "claim_text": "c",
                        "quote": "q",
                        "citation_text": "ct",
                    }
                ],
                "internal_traces": [internal_trace],
                "trace_ids": [internal_trace.trace_id],
                "source_documents": ["doc-01"],
            }
            step3_out = {
                "result": {"sections": 1, "claims": 1},
                "evidence": [
                    {
                        "trace_id": internal_trace.trace_id,
                        "document_id": "doc-01",
                        "chunk_id": "chk-01",
                        "claim_text": "c",
                        "quote": "q",
                        "citation_text": "ct",
                    }
                ],
                "internal_traces": [internal_trace],
                "trace_ids": [internal_trace.trace_id],
                "source_documents": ["doc-01"],
            }
            step4_out = {
                "result": {"sections": 1, "title": "Report"},
                "internal_traces": [internal_trace],
                "trace_ids": [internal_trace.trace_id],
                "source_documents": [],
            }
            step5_out = {
                "result": {"total_citations": 1},
                "internal_traces": [bad_trace],  # no to_dict() -> AttributeError
                "trace_ids": [internal_trace.trace_id],
                "source_documents": ["doc-01"],
            }

            rwf.execute_topic_selection = AsyncMock(return_value=step_out)
            rwf.execute_literature_retrieval = AsyncMock(return_value=step2_out)
            rwf.execute_evidence_synthesis_from_snapshot = MagicMock(
                return_value=step3_out
            )
            rwf.execute_report_from_synthesis = MagicMock(return_value=step4_out)
            rwf.execute_citation_export_from_evidence = MagicMock(
                return_value=step5_out
            )
            rwf.build_markdown_artifact = MagicMock(return_value="# Report")
            rwf.persist_research_run = AsyncMock(return_value=None)

            resp = _client.post(
                "/api/v4/research/workflow",
                json={
                    "session_id": "sess-001",
                    "topic": "test",
                    "workflow_type": "full_research_flow",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert len(body["data"]["steps"]) == 5


# ---- 593->596: immutable_traces aggregation into source_docs ----


class TestWorkflowImmutableTraceAggregation:
    """593->596: immutable_traces contributes to traceability source_documents."""

    def test_workflow_immutable_traces_aggregation(self):
        session = _make_session_mock()
        mock_qh = _make_qh_mock()
        internal_trace = _make_internal_trace(doc_id="doc-from-step")
        immutable_trace = _make_internal_trace(
            doc_id="doc-from-immutable", chunk_id="chk-immutable"
        )

        step_out = {
            "result": {"sub_questions": 1},
            "internal_traces": [internal_trace],
            "trace_ids": [internal_trace.trace_id],
            "source_documents": ["doc-from-step"],
        }
        step2_out = {
            "result": {"themes": 1, "records": 1},
            "snapshot": [
                {
                    "trace_id": immutable_trace.trace_id,
                    "document_id": "doc-from-immutable",
                    "chunk_id": "chk-immutable",
                    "claim_text": "c",
                    "quote": "q",
                    "citation_text": "ct",
                }
            ],
            "internal_traces": [immutable_trace],
            "trace_ids": [immutable_trace.trace_id],
            "source_documents": ["doc-from-immutable"],
        }
        step3_out = {
            "result": {"sections": 1, "claims": 1},
            "evidence": [
                {
                    "trace_id": immutable_trace.trace_id,
                    "document_id": "doc-from-immutable",
                    "chunk_id": "chk-immutable",
                    "claim_text": "c",
                    "quote": "q",
                    "citation_text": "ct",
                }
            ],
            "internal_traces": [immutable_trace],
            "trace_ids": [immutable_trace.trace_id],
            "source_documents": ["doc-from-immutable"],
        }
        step4_out = {
            "result": {"sections": 1, "title": "Report"},
            "internal_traces": [immutable_trace],
            "trace_ids": [immutable_trace.trace_id],
            "source_documents": [],
        }
        step5_out = {
            "result": {"total_citations": 1},
            "internal_traces": [],
            "trace_ids": [immutable_trace.trace_id],
            "source_documents": [],
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.create_query_history = AsyncMock(return_value=mock_qh)
            MockWS.return_value.update_session = AsyncMock(return_value=session)

            rwf = MockRWF.return_value
            rwf.execute_topic_selection = AsyncMock(return_value=step_out)
            rwf.execute_literature_retrieval = AsyncMock(return_value=step2_out)
            rwf.execute_evidence_synthesis_from_snapshot = MagicMock(
                return_value=step3_out
            )
            rwf.execute_report_from_synthesis = MagicMock(return_value=step4_out)
            rwf.execute_citation_export_from_evidence = MagicMock(
                return_value=step5_out
            )
            rwf.build_markdown_artifact = MagicMock(return_value="# Report")
            rwf.persist_research_run = AsyncMock(return_value=None)

            resp = _client.post(
                "/api/v4/research/workflow",
                json={
                    "session_id": "sess-001",
                    "topic": "针灸研究",
                    "workflow_type": "full_research_flow",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert "doc-from-immutable" in body["traceability"]["source_documents"]


# ---- 657->673: query history trace parsing with empty IDs ----


class TestHistoryEmptyTraceIdAndDocId:
    """657->673, 662->660, 666->660: empty trace_id and document_id skipped."""

    def test_history_trace_id_empty_skipped(self):
        session = _make_session_mock()
        qh = _make_qh_mock(
            result_summary=json.dumps(
                {
                    "traces": [
                        {"trace_id": "", "document_id": "doc-01"},
                        {"trace_id": "t1", "document_id": "doc-02"},
                    ],
                }
            )
        )

        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.get_query_history = AsyncMock(return_value=[qh])

            resp = _client.get("/api/v4/research/session/sess-001/history")
            assert resp.status_code == 200
            body = resp.json()
            assert body["data"]["history"][0]["trace_count"] == 1

    def test_history_document_id_empty_skipped(self):
        session = _make_session_mock()
        qh = _make_qh_mock(
            result_summary=json.dumps(
                {
                    "traces": [
                        {"trace_id": "t1", "document_id": ""},
                        {"trace_id": "t2", "document_id": "doc-02"},
                    ],
                }
            )
        )

        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.get_query_history = AsyncMock(return_value=[qh])

            resp = _client.get("/api/v4/research/session/sess-001/history")
            assert resp.status_code == 200
            body = resp.json()
            assert len(body["traceability"]["source_documents"]) == 1


# ---- 720: _derive_run_status unknown statuses fallback ----


class TestDeriveRunStatusUnknown:
    """720: _derive_run_status returns 'pending' when no known status matches."""

    def test_derive_run_status_unknown_status(self):
        from app.api.v4.research import _derive_run_status

        trace = [{"status": "unknown"}, {"status": "initialized"}]
        assert _derive_run_status(trace) == "pending"


# ---- 880->882, 883->878: runs manifest traces without trace_id/doc_id ----


class TestSessionRunsManifestEdgeCases:
    """880->882 + 883->878: manifest traces missing trace_id or document_id."""

    def test_runs_manifest_trace_no_trace_id(self):
        session = _make_session_mock()
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "started_at": "2026-08-01T00:00:00",
            "step_execution_trace": [],
            "output_artifacts": {},
            "replay_manifest": {
                "traces": [
                    {"document_id": "doc-01"},
                    {"trace_id": "t1", "document_id": "doc-02"},
                ],
            },
        }
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.get("/api/v4/research/session/sess-001/runs")
            assert resp.status_code == 200
            body = resp.json()
            assert body["traceability"]["trace_ids"] == ["t1"]

    def test_runs_manifest_trace_no_document_id(self):
        session = _make_session_mock()
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "started_at": "2026-08-01T00:00:00",
            "step_execution_trace": [],
            "output_artifacts": {},
            "replay_manifest": {
                "traces": [
                    {"trace_id": "t1"},
                    {"trace_id": "t2", "document_id": ""},
                    {"trace_id": "t3", "document_id": "doc-01"},
                ],
            },
        }
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.get("/api/v4/research/session/sess-001/runs")
            assert resp.status_code == 200
            body = resp.json()
            assert body["traceability"]["source_documents"] == ["doc-01"]


# ---- 965: export run session_id mismatch ----


class TestExportRunSessionMismatch:
    """965: run session_id doesn't match URL session_id (defense-in-depth)."""

    def test_export_run_session_id_mismatch(self):
        session = _make_session_mock()
        run = {
            "session_id": "other-session",
            "run_id": "run-001",
            "output_artifacts": {"markdown": "# Report"},
        }
        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.get("/api/v4/research/session/sess-001/runs/run-001/export")
            assert resp.status_code == 404
            assert resp.json()["success"] is False


# ---- 1071-1078: UNVERIFIABLE_MANIFEST ----


class TestReplayUnverifiableManifest:
    """1071-1078: UNVERIFIABLE_MANIFEST when manifest_sha256 missing."""

    def test_replay_unverifiable_manifest(self):
        session = _make_session_mock()
        snapshot = _default_snapshot()
        trace_data = _default_trace_data()
        manifest = _build_valid_manifest(snapshot, trace_data)
        del manifest["manifest_sha256"]
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "UNVERIFIABLE_MANIFEST"


# ---- 1093: invalid manifest_sha256 format ----


class TestReplayInvalidManifestHashFormat:
    """1093: manifest_sha256 must be 64-char lowercase hex."""

    def test_replay_invalid_hash_too_short(self):
        session = _make_session_mock()
        snapshot = _default_snapshot()
        trace_data = _default_trace_data()
        manifest = _build_valid_manifest(snapshot, trace_data)
        manifest["manifest_sha256"] = "abc123"
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "CORRUPT_MANIFEST"

    def test_replay_invalid_hash_non_hex(self):
        session = _make_session_mock()
        snapshot = _default_snapshot()
        trace_data = _default_trace_data()
        manifest = _build_valid_manifest(snapshot, trace_data)
        manifest["manifest_sha256"] = "g" + "a" * 63
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "CORRUPT_MANIFEST"


# ---- 1106: manifest_sha256 mismatch ----


class TestReplayManifestHashMismatch:
    """1106: recomputed manifest_sha256 doesn't match stored value."""

    def test_replay_manifest_hash_mismatch(self):
        session = _make_session_mock()
        snapshot = _default_snapshot()
        trace_data = _default_trace_data()
        manifest = _build_valid_manifest(snapshot, trace_data)
        manifest["topic"] = "tampered-topic"  # hash mismatches stored manifest_sha256
        # Do NOT recompute — the point is that manifest_sha256 is now wrong
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "CORRUPT_MANIFEST"
            assert "integrity check failed" in body["message"]


# ---- 1143: trace missing required fields ----


class TestReplayTraceMissingFields:
    """1143: trace missing required fields."""


# ---- 1155: invalid provenance_kind ----


class TestReplayInvalidProvenanceKind:
    """1155: trace provenance_kind not in ('retrieval', 'graph')."""

    def test_replay_invalid_provenance_kind(self):
        session = _make_session_mock()
        snapshot = _default_snapshot()
        trace_data = _default_trace_data()
        trace_data[0]["provenance_kind"] = "invalid"
        manifest = _build_valid_manifest(snapshot, trace_data)
        _recompute_manifest_sha256(manifest)
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "CORRUPT_MANIFEST"
            assert "invalid provenance_kind" in body["data"]["detail"]


# ---- 1165: retrieval provenance missing retrieval_score ----


class TestReplayRetrievalMissingScore:
    """1165: retrieval provenance_kind without retrieval_score."""


# ---- 1187-1188: InternalTraceRecord construction fails ----


class TestReplayInternalTraceRecordInvalid:
    """1187-1188: InternalTraceRecord validation rejects malformed trace."""

    def test_replay_trace_invalid_construction(self):
        session = _make_session_mock()
        snapshot = _default_snapshot()
        trace_data = _default_trace_data()
        trace_data[0]["trace_id"] = "not-a-valid-uuid"  # validator rejects
        manifest = _build_valid_manifest(snapshot, trace_data)
        _recompute_manifest_sha256(manifest)
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "CORRUPT_MANIFEST"
            assert "invalid" in body["data"]["detail"]


# ---- 1199: empty frozen_traces ----


class TestReplayEmptyFrozenTraces:
    """1199: no valid traces remain after validation."""


# ---- 1214->1216: tid not in trace_passage_map ----


class TestReplayTidNotInPassageMap:
    """1214->1216: snapshot entry tid not found in trace_passage_map."""

    def test_replay_snapshot_tid_not_mapped(self):
        session = _make_session_mock()
        snapshot = _default_snapshot()
        trace_data = _default_trace_data()
        from app.services.trace_lineage import make_trace_id

        extra_tid = str(make_trace_id("extra-doc", "extra-chk"))
        snapshot.append(
            {
                "trace_id": extra_tid,
                "document_id": "extra-doc",
                "chunk_id": "extra-chk",
                "claim_text": "extra claim",
                "quote": "extra quote",
                "citation_text": "[extra-doc:extra-chk]",
            }
        )

        from app.services.research_workflow_service import (
            _build_canonical_payload,
            _build_corpus_payload,
            _build_input_payload,
            _build_report_sections,
            _group_snapshot_into_sections,
            _snapshot_to_evidence_list,
            canonical_sha256,
            canonicalize_traces,
        )

        canonical_traces = canonicalize_traces(trace_data)
        snap_for_corpus = [dict(r) for r in snapshot]
        corpus_hash = canonical_sha256(_build_corpus_payload(snap_for_corpus))
        input_hash = canonical_sha256(
            _build_input_payload(
                topic="test",
                workflow_type="full_research_flow",
                pipeline_version="1.0.0",
                retrieval_snapshot=snapshot,
                trace_ids=sorted({t["trace_id"] for t in trace_data}),
                source_document_ids=sorted({t["document_id"] for t in trace_data}),
                canonical_traces=canonical_traces,
            )
        )
        syn_sections = _group_snapshot_into_sections(snapshot)
        syn_evidence = _snapshot_to_evidence_list(snapshot)
        rep_sections = _build_report_sections("test", syn_evidence, syn_sections)
        cit_citations = [
            {
                "trace_id": _VALID_TID,
                "citation_text": "[doc-01:chk-01]",
                "document_id": "doc-01",
                "quote": "quote",
            }
        ]
        output_hash = canonical_sha256(
            _build_canonical_payload(
                topic="test",
                workflow_type="full_research_flow",
                pipeline_version="1.0.0",
                retrieval_snapshot=snapshot,
                synthesis_sections=syn_sections,
                synthesis_evidence=syn_evidence,
                report_sections=rep_sections,
                citations=cit_citations,
                trace_ids=sorted({_VALID_TID}),
                source_document_ids=["doc-01"],
                canonical_traces=canonical_traces,
            )
        )
        manifest = {
            "manifest_version": "2.0.0",
            "run_id": "run-001",
            "session_id": "sess-001",
            "workflow_type": "full_research_flow",
            "topic": "test",
            "pipeline_version": "1.0.0",
            "workflow_steps": [
                "topic_selection",
                "literature_retrieval",
                "evidence_synthesis",
                "report_generation",
                "citation_export",
            ],
            "retrieval_snapshot": snapshot,
            "traces": trace_data,
            "query_history_binding": [],
            "corpus_sha256": corpus_hash,
            "canonical_input_sha256": input_hash,
            "canonical_output_sha256": output_hash,
            "canonicalization_version": "2.0.0",
            "created_at": "2026-08-01T00:00:00",
        }
        manifest["manifest_sha256"] = canonical_sha256(manifest)
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        syn_out = {
            "result": {"sections": 1, "claims": 1},
            "sections": syn_sections,
            "evidence": syn_evidence,
            "trace_ids": [],
            "source_documents": [],
            "internal_traces": [],
        }
        rep_out = {
            "result": {"sections": 1, "title": "Report"},
            "sections": rep_sections,
            "evidence": syn_evidence,
            "trace_ids": [],
            "source_documents": [],
            "internal_traces": [],
        }
        cit_out = {
            "result": {"total_citations": 1, "citations": cit_citations},
            "trace_ids": [],
            "source_documents": [],
            "internal_traces": [],
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            MockRWF.return_value.execute_evidence_synthesis_from_snapshot = MagicMock(
                return_value=syn_out
            )
            MockRWF.return_value.execute_report_from_synthesis = MagicMock(
                return_value=rep_out
            )
            MockRWF.return_value.execute_citation_export_from_evidence = MagicMock(
                return_value=cit_out
            )

            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["matched"] is True


# ---- 1235: corpus_sha256 mismatch ----


class TestReplayCorpusHashMismatch:
    """1235: recomputed corpus_sha256 doesn't match manifest."""


# ---- 1246: canonical_input_sha256 mismatch ----


class TestReplayInputHashMismatch:
    """1246: recomputed canonical_input_sha256 doesn't match manifest."""


# ---- 1269-1270: RuntimeError during replay execution ----


class TestReplayExecutionRuntimeError:
    """1269-1270: RuntimeError during replay execution."""

    def test_replay_execution_runtime_error(self):
        session = _make_session_mock()
        snapshot = _default_snapshot()
        trace_data = _default_trace_data()
        manifest = _build_valid_manifest(snapshot, trace_data)
        run = {
            "session_id": "sess-001",
            "run_id": "run-001",
            "topic": "test",
            "replay_manifest": manifest,
        }

        with (
            patch("app.api.v4.research.WorkspaceService") as MockWS,
            patch("app.api.v4.research.ResearchWorkflowService") as MockRWF,
        ):
            MockWS.return_value.list_sessions = AsyncMock(return_value=[session])
            MockRWF.return_value.get_research_runs = AsyncMock(return_value=[run])
            MockRWF.return_value.execute_evidence_synthesis_from_snapshot = MagicMock(
                side_effect=RuntimeError("synthesis crash")
            )
            resp = _client.post("/api/v4/research/runs/run-001/replay", json={})
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is False
            assert body["data"]["error"] == "REPLAY_EXECUTION_FAILED"


# ---- 1284-1286: report_sections_for_hash fallback ----


class TestReplayReportSectionsFallback:
    """1284-1286: _build_report_sections fallback when syn_out sections are empty."""


# ---- 1526-1529: corrupt workflow_state in seed ----


class TestSeedWorkflowStateCorrupt:
    """1526-1529: corrupt workflow_state JSON handled gracefully."""

    @pytest.fixture(autouse=True)
    def _reset_seed_env(self):
        yield
        _os.environ.pop("SEED_TEST_DATA", None)

    def test_seed_corrupt_json_state(self):
        _os.environ["SEED_TEST_DATA"] = "1"
        session = _make_session_mock(workflow_state="not valid json {{{")
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.update_session = AsyncMock(return_value=session)
            resp = _client.post(
                "/api/v4/research/_test/seed-research-run",
                json={"session_id": "sess-001", "topic": "E2E Test Topic"},
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True

    def test_seed_workflow_state_none(self):
        _os.environ["SEED_TEST_DATA"] = "1"
        session = _make_session_mock(workflow_state=None)
        with patch("app.api.v4.research.WorkspaceService") as MockWS:
            MockWS.return_value.get_session = AsyncMock(return_value=session)
            MockWS.return_value.update_session = AsyncMock(return_value=session)
            resp = _client.post(
                "/api/v4/research/_test/seed-research-run",
                json={"session_id": "sess-001", "topic": "E2E Test Topic"},
            )
            assert resp.status_code == 200
            assert resp.json()["success"] is True
