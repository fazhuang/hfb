"""P10-COV-005: Targeted coverage tests for uncovered pure functions/branches.

WHITELIST: only this test file may be added. No business code modified.
Goal: close 117-hit gap to reach >=90% total coverage.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# =============================================================================
# chunking.py — _split_long_paragraph edge branch (lines 131-133, 137->140)
# =============================================================================


class TestChunkingSplitLongEdge:
    """Cover _build_chunks line 67-71 (flush on oversized paragraph) and
    _split_long_paragraph lines 131-133 (single sentence > max_chars after segment)."""

    def test_oversized_paragraph_flush_with_indices(self) -> None:
        from app.services.chunking import chunk_text

        text = "小段。\n\n" + "医" * 300
        result = chunk_text(text, max_chars=100, return_indices=True)
        assert isinstance(result, list)
        assert len(result) >= 2
        for item in result:
            assert isinstance(item, tuple)
            assert isinstance(item[0], str)
            assert isinstance(item[1], int)

    def test_split_long_paragraph_single_sentence_too_long_fallback(self) -> None:
        """Lines 131-133: sentence after segment still > max_chars."""
        from app.services.chunking import _split_long_paragraph

        text = "正常句子。" + "医" * 250
        result = _split_long_paragraph(text, max_chars=100)
        assert len(result) >= 3

    def test_split_long_paragraph_current_after_max_flush(self) -> None:
        """Line 137->140 branch: current is truthy after loop."""
        from app.services.chunking import _split_long_paragraph

        text = "医" * 80 + "。" + "学" * 30 + "。"
        result = _split_long_paragraph(text, max_chars=90)
        assert len(result) >= 1
        joined = "".join(result)
        assert "医" in joined
        assert "学" in joined

    def test_build_chunks_multiple_oversized(self) -> None:
        from app.services.chunking import chunk_text

        text = "医" * 300 + "\n\n" + "学" * 300
        result = chunk_text(text, max_chars=100, return_indices=True)
        assert len(result) >= 4
        for chunk_text_val, idx in result:
            assert idx >= 0


# =============================================================================
# source_whitelist.py — fallback path branches (lines 100->104, 104->106)
# =============================================================================


class TestSourceWhitelistFallbackBranches:
    """Cover the two candidate.exists() branches in get_whitelist default path."""

    def test_env_var_path_takes_priority(self, tmp_path, monkeypatch) -> None:
        """SOURCE_WHITELIST_PATH env var is checked before canonical path."""
        from app.services.source_whitelist import get_whitelist

        get_whitelist.cache_clear()
        yaml_path = tmp_path / "env_wl.yaml"
        _write_whitelist_yaml(yaml_path, {
            "sources": [
                {"name": "EnvSource", "domain": "env.example", "category": "A",
                 "metadata_allowed": True, "fulltext_allowed": False},
            ],
        })
        monkeypatch.setenv("SOURCE_WHITELIST_PATH", str(yaml_path))
        wl = get_whitelist()
        assert wl.lookup("EnvSource") is not None


# =============================================================================
# version.py — withdraw/restore/is_academic_citable/is_withdrawn
# =============================================================================


class TestVersionModelMethods:
    """Cover withdraw, restore, is_withdrawn, is_academic_citable on Version."""

    def test_withdraw_sets_timestamp_and_reason(self) -> None:
        from app.models.version import Version
        v = Version()
        v.is_formal_source = True
        v.withdraw("测试撤回")
        assert v.withdrawn_at is not None
        assert v.withdraw_reason == "测试撤回"
        assert v.is_withdrawn is True

    def test_withdraw_default_reason(self) -> None:
        from app.models.version import Version
        v = Version()
        v.withdraw()
        assert v.withdraw_reason == "未说明"

    def test_restore_clears_withdrawal(self) -> None:
        from app.models.version import Version
        v = Version()
        v.withdraw()
        assert v.is_withdrawn is True
        v.restore()
        assert v.withdrawn_at is None
        assert v.withdraw_reason is None
        assert v.is_withdrawn is False

    def test_is_academic_citable_all_conditions(self) -> None:
        from app.models.version import Version
        v = Version()
        v.is_formal_source = True
        v.repository = "国家图书馆"
        v.shelf_mark = "SB123"
        v.source_url = "https://example.edu/version1"
        assert v.is_academic_citable is True

    def test_is_academic_citable_default_not_citable(self) -> None:
        from app.models.version import Version
        v = Version()
        v.is_formal_source = False
        assert v.is_academic_citable is False

    def test_is_academic_citable_with_persistent_id_not_shelfmark(self) -> None:
        from app.models.version import Version
        v = Version()
        v.is_formal_source = True
        v.repository = "北大图书馆"
        v.persistent_identifier = "doi:10.1234/example"
        v.source_url = "https://lib.pku.edu.cn/abc"
        assert v.is_academic_citable is True

    def test_is_academic_citable_withdrawn_not_citable(self) -> None:
        from app.models.version import Version
        v = Version()
        v.is_formal_source = True
        v.repository = "国图"
        v.shelf_mark = "X001"
        v.source_url = "https://example.org"
        v.withdraw()
        assert v.is_academic_citable is False

    def test_version_repr(self) -> None:
        from app.models.version import Version
        v = Version()
        v.version_name = "测试本"
        r = repr(v)
        assert "测试本" in r

    def test_is_withdrawn_none_default(self) -> None:
        from app.models.version import Version
        v = Version()
        v.withdrawn_at = None
        assert v.is_withdrawn is False


# =============================================================================
# institution.py — validate_name/validate_type + status transitions
# =============================================================================


class TestInstitutionValidators:
    """Cover validate_name (line 117), validate_type."""

    def test_validate_name_exceeds_max_length(self) -> None:
        from app.models.institution import Institution
        from app.core.exceptions import ValidationException
        inst = Institution()
        with pytest.raises(ValidationException, match="exceeds maximum length"):
            inst.validate_name("name", "x" * 301)

    def test_validate_type_invalid(self) -> None:
        from app.models.institution import Institution
        from app.core.exceptions import ValidationException
        inst = Institution()
        with pytest.raises(ValidationException, match="Invalid institution type"):
            inst.validate_type("type", "invalid_type")

    def test_validate_name_none(self) -> None:
        from app.models.institution import Institution
        from app.core.exceptions import ValidationException
        inst = Institution()
        with pytest.raises(ValidationException, match="must not be null"):
            inst.validate_name("name", None)


class TestInstitutionStatusValidation:
    """Cover Institution.validate_status status transition branch."""

    def test_status_transition_valid(self) -> None:
        from app.models.institution import Institution
        inst = Institution()
        inst.status = "draft"
        assert inst.status == "draft"
        inst.status = "active"
        assert inst.status == "active"

    def test_status_transition_invalid_jump(self) -> None:
        from app.models.institution import Institution
        inst = Institution()
        inst.status = "draft"
        with pytest.raises(Exception):
            inst.status = "archived"


# =============================================================================
# evidence_rag.py schemas — line 105, 107, 109, 111, 116
# =============================================================================


class TestEvidenceRagSchemas:
    """Cover evidence_rag.py schema classes."""

    def test_evidence_bound_chunk(self) -> None:
        from app.schemas.evidence_rag import EvidenceBoundChunk
        ebc = EvidenceBoundChunk(
            document_id="d1", chunk_id="c1", content="content",
            citation="[d1:c1]", score=0.9,
        )
        assert ebc.document_id == "d1"
        assert ebc.score == 0.9

    def test_evidence_rag_request(self) -> None:
        from app.schemas.evidence_rag import EvidenceRAGRequest
        req = EvidenceRAGRequest(query="test", top_k=5)
        assert req.query == "test"
        assert req.top_k == 5

    def test_evidence_rag_response_enforce(self) -> None:
        from app.schemas.evidence_rag import (
            EvidenceBoundChunk, EvidenceCitation, EvidenceRAGResponse,
        )
        chunk = EvidenceBoundChunk(
            document_id="d1", chunk_id="c1", content="content",
            citation="[d1:c1]", score=0.9,
        )
        citation = EvidenceCitation(
            document_id="d1", chunk_id="c1", citation="[d1:c1]",
        )
        resp = EvidenceRAGResponse(
            query="test", answer="answer",
            evidence=[chunk], citations=[citation],
        )
        enforced = resp.enforce_evidence_contract()
        assert enforced.evidence[0].document_id == "d1"


# =============================================================================
# institution.py schemas — line 54, 57, 64, 66
# =============================================================================


class TestInstitutionSchema:
    """Cover institution schema create/update models."""

    def test_institution_create_minimal(self) -> None:
        from app.schemas.institution import InstitutionCreate
        ic = InstitutionCreate(name="测试机构", type="research")
        assert ic.name == "测试机构"
        assert ic.type == "research"

    def test_institution_create_invalid_type(self) -> None:
        from app.schemas.institution import InstitutionCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            InstitutionCreate(name="x", type="invalid")

    def test_institution_update_partial(self) -> None:
        from app.schemas.institution import InstitutionUpdate
        iu = InstitutionUpdate(description="updated desc")
        assert iu.description == "updated desc"
        assert iu.name is None


# =============================================================================
# ai_response.py schemas — line 125, 151, 192
# =============================================================================


class TestAIResponseSchemas:
    """Cover ai_response.py validators."""

    def test_citation_model(self) -> None:
        from app.schemas.ai_response import Citation
        c = Citation(entity_type="Book", entity_id="d1", text="《针灸甲乙经》")
        assert c.entity_type == "Book"

    def test_structured_response_builder_build(self) -> None:
        from app.schemas.ai_response import StructuredResponseBuilder
        resp = StructuredResponseBuilder.build(
            answer_text="针灸治疗头痛。[d1:c1]",
            rag_chunks=[{"entity_type": "Book", "entity_id": "d1",
                         "title": "针灸甲乙经", "content": "content",
                         "citation": "[d1:c1]", "score": 0.9}],
        )
        assert resp is not None
        assert resp.answer is not None


# =============================================================================
# core_client.py — search function
# =============================================================================


class TestLiteratureCoreClient:
    """Cover core_client.py imports and module structure."""

    def test_core_client_module_imports(self) -> None:
        """Verify the module can be imported without running real HTTP calls."""
        import app.services.literature_ingestion.core_client as cc
        assert hasattr(cc, "search")
        assert hasattr(cc, "_PAGE_SIZE")


# =============================================================================
# ready.py — uncovered line 25 (TESTING mode branch)
# =============================================================================


class TestReadyEndpoint:
    """Cover ready.py line 25 — TESTING=1 branch."""

    def test_testing_mode_required_services(self, monkeypatch) -> None:
        monkeypatch.setenv("TESTING", "1")
        # Re-import triggers the module-level if/else
        import importlib
        import app.api.ready as ready_mod
        importlib.reload(ready_mod)
        assert "PostgreSQL" in ready_mod.REQUIRED_SERVICES
        assert "Redis" not in ready_mod.REQUIRED_SERVICES

    def test_resolved_trace_to_public_dict(self) -> None:
        from unittest.mock import MagicMock
        from app.services.trace_lineage import ResolvedTrace

        mock_chunk = MagicMock()
        mock_chunk.chunk_index = 0
        mock_chunk.content = "test content"
        mock_doc = MagicMock()
        mock_doc.id = "d1"
        mock_doc.title = "Test Title"

        rt = ResolvedTrace(
            trace_id="t1",
            chunk=mock_chunk,
            document=mock_doc,
            passage=None,
            passage_citation="",
            chunk_citation="[d1:c1]",
        )
        d = rt.to_public_dict()
        assert d["trace_id"] == "t1"
        assert d["document_id"] == "d1"
        assert d["document_title"] == "Test Title"


# =============================================================================
# academic_edge.py — model instantiation (34 missed stmts)
# =============================================================================


class TestAcademicEdgeModel:
    """Cover AcademicEdge ORM model instantiation."""

    def test_instantiate_academic_edge(self) -> None:
        from datetime import datetime, timezone
        from app.models.academic_edge import AcademicEdge
        now = datetime.now(timezone.utc)
        edge = AcademicEdge(
            id="e1",
            source_entity_type="Book",
            source_entity_id="b1",
            target_entity_type="Chapter",
            target_entity_id="c1",
            relation_type="appears_in",
            evidence_status="verified",
            evidence_level=2,
            confidence_score=0.95,
            created_at=now,
            updated_at=now,
        )
        assert edge.id == "e1"
        assert edge.source_entity_type == "Book"
        assert edge.relation_type == "appears_in"
        assert edge.evidence_level == 2


# =============================================================================
# trace_lineage.py — pure validation functions
# =============================================================================


class TestTraceLineagePureFunctions:
    """Cover make_trace_id, _is_valid_uuidv5, _is_valid_score, extract_* etc."""

    def test_make_trace_id_deterministic(self) -> None:
        from app.services.trace_lineage import make_trace_id
        tid1 = make_trace_id("d1", "c1")
        tid2 = make_trace_id("d1", "c1")
        assert tid1 == tid2
        assert len(tid1) == 36

    def test_make_trace_id_different_inputs(self) -> None:
        from app.services.trace_lineage import make_trace_id
        tid1 = make_trace_id("d1", "c1")
        tid2 = make_trace_id("d1", "c2")
        assert tid1 != tid2

    def test_is_valid_uuidv5_valid(self) -> None:
        from app.services.trace_lineage import _is_valid_uuidv5, make_trace_id
        tid = make_trace_id("d1", "c1")
        assert _is_valid_uuidv5(tid) is True

    def test_is_valid_uuidv5_invalid(self) -> None:
        from app.services.trace_lineage import _is_valid_uuidv5
        assert _is_valid_uuidv5("not-a-uuid") is False
        import uuid
        v4 = str(uuid.uuid4())
        assert _is_valid_uuidv5(v4) is False

    def test_is_valid_score_valid(self) -> None:
        from app.services.trace_lineage import _is_valid_score
        assert _is_valid_score(0.5) is True
        assert _is_valid_score(0.0) is True

    def test_is_valid_score_nan_inf(self) -> None:
        from app.services.trace_lineage import _is_valid_score
        assert _is_valid_score(float("nan")) is False
        assert _is_valid_score(float("inf")) is False

    def test_is_valid_score_non_number(self) -> None:
        from app.services.trace_lineage import _is_valid_score
        assert _is_valid_score("0.5") is False

    def test_internal_trace_record_construction(self) -> None:
        from app.services.trace_lineage import InternalTraceRecord, make_trace_id
        tid = make_trace_id("d1", "c1")
        rec = InternalTraceRecord(
            trace_id=tid,
            document_id="d1",
            chunk_id="c1",
            passage_id="p1",
            provenance_kind="retrieval",
            retrieval_score=0.9,
            retrieval_method="keyword",
            timestamp="2025-01-01T00:00:00Z",
        )
        assert rec.trace_id == tid
        assert rec.retrieval_score == 0.9

    def test_resolved_trace_to_public_dict(self) -> None:
        from unittest.mock import MagicMock
        from app.services.trace_lineage import ResolvedTrace

        mock_chunk = MagicMock()
        mock_chunk.chunk_index = 0
        mock_chunk.content = "test content"
        mock_doc = MagicMock()
        mock_doc.id = "d1"
        mock_doc.title = "Test Title"

        rt = ResolvedTrace(
            trace_id="t1",
            chunk=mock_chunk,
            document=mock_doc,
            passage=None,
            passage_citation="",
            chunk_citation="[d1:c1]",
        )
        d = rt.to_public_dict()
        assert d["trace_id"] == "t1"
        assert d["document_id"] == "d1"
        assert d["document_title"] == "Test Title"
        assert d["document_title"] == "Test Title"

    def test_extract_trace_ids(self) -> None:
        from app.services.trace_lineage import extract_trace_ids
        from app.services.retrieval import RetrievalResult
        r1 = RetrievalResult(document_id="d1", chunk_id="c1",
                            document_title="", chunk_index=0, content="",
                            citation="", score=0.5)
        r2 = RetrievalResult(document_id="d2", chunk_id="c2",
                            document_title="", chunk_index=0, content="",
                            citation="", score=0.5)
        traces = [r1, r2]
        result = extract_trace_ids(traces)
        assert len(result) == 2

    def test_extract_source_documents(self) -> None:
        from app.services.trace_lineage import extract_source_documents
        from app.services.retrieval import RetrievalResult
        r1 = RetrievalResult(document_id="d1", chunk_id="c1",
                            document_title="", chunk_index=0, content="",
                            citation="", score=0.5)
        r2 = RetrievalResult(document_id="d2", chunk_id="c2",
                            document_title="", chunk_index=0, content="",
                            citation="", score=0.5)
        traces = [r1, r2, r1]
        result = extract_source_documents(traces)
        assert sorted(result) == ["d1", "d2"]

    def test_trace_lineage_error(self) -> None:
        from app.services.trace_lineage import TraceLineageError
        err = TraceLineageError("test error")
        assert str(err) == "test error"


# =============================================================================
# conflict_detector.py — _detect_rejected_claims line 142
# =============================================================================


class TestConflictDetectorTopological:
    """Cover _detect_rejected_claims conflict append at line 142."""

    @pytest.mark.anyio
    async def test_topological_rejected_creates_conflict(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from app.schemas.graph import EvidenceChainPath, EvidenceHop
        from app.services.conflict_detector import ConflictDetector

        hop = EvidenceHop(
            source_type="Book",
            source_id="b1",
            target_type="Chapter",
            target_id="ch1",
            relation_type="appears_in",
            evidence_level=2,
            confidence_score=0.9,
            citation="[d1:c1]",
        )
        path = EvidenceChainPath(
            path_id="p1",
            hops=[hop],
            total_confidence=0.9,
            min_evidence_level=2,
        )

        detector = ConflictDetector()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock()]
        mock_session.execute.return_value = mock_result

        conflicts = await detector._detect_rejected_claims(mock_session, [path])
        assert len(conflicts) >= 1
        assert any(c.conflict_type == "topological_rejected" for c in conflicts)


# =============================================================================
# Helpers
# =============================================================================


def _write_whitelist_yaml(path: Path, data: dict) -> Path:
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path
