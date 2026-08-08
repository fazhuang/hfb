"""Unit tests for generation_proof.py — VerifiedClaim, GenerationProof, _render_canonical_answer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.schemas.generation import GroundedGenerationResponse
from app.services.generation_proof import (
    PROOF_ERROR_CODES,
    GenerationProof,
    VerifiedClaim,
    _render_canonical_answer,
    _snapshot_to_dicts,
    build_and_validate_proof,
)
from app.services.generation_service import CanonicalClaim, GenerationOutcome


def _make_retrieval_result(
    document_id="d1", chunk_id="c1", content="经络者。", score=0.9
):
    from app.services.retrieval import RetrievalResult

    return RetrievalResult(
        document_id=document_id,
        document_title="Test Doc",
        chunk_id=chunk_id,
        chunk_index=0,
        content=content,
        citation=f"[{document_id}:{chunk_id}]",
        score=score,
        metadata={"retrieval_method": "keyword"},
    )


class TestVerifiedClaim:
    def test_fields(self) -> None:
        vc = VerifiedClaim(
            claim_text="经络者，所以行血气而营阴阳。",
            quote="经络者，所以行血气而营阴阳",
            document_id="d1",
            chunk_id="c1",
            citation_str="[d1:c1]",
            chunk_rank=0,
            quote_norm="经络者所以行血气而营阴阳",
        )
        assert vc.claim_text.endswith("。")
        assert vc.citation_str == "[d1:c1]"


class TestGenerationProof:
    def test_default_is_not_complete(self) -> None:
        resp = GroundedGenerationResponse(
            query="test", answer="", results=[], citations=[]
        )
        proof = GenerationProof(response=resp)
        assert proof.is_complete is False

    def test_has_error_property(self) -> None:
        resp = GroundedGenerationResponse(
            query="test", answer="", results=[], citations=[]
        )
        proof = GenerationProof(response=resp, error_code="CLAIM_COUNT_MISMATCH")
        assert proof.has_error is True

    def test_has_no_evidence(self) -> None:
        resp = GroundedGenerationResponse(
            query="test", answer="", results=[], citations=[]
        )
        proof = GenerationProof(response=resp)
        assert proof.has_no_evidence is True

    def test_has_integrity_error(self) -> None:
        resp = GroundedGenerationResponse(
            query="test", answer="", results=[], citations=[]
        )
        proof = GenerationProof(response=resp, error_code="CITATION_MALFORMED")
        assert proof.has_integrity_error is True


class TestErrorCodes:
    def test_all_known_codes(self) -> None:
        expected = [
            "ACADEMIC_CLAIM_BINDING_FAILED",
            "CLAIM_COUNT_MISMATCH",
            "CITATION_COUNT_MISMATCH",
            "CHUNK_NOT_IN_SNAPSHOT",
            "DOCUMENT_ID_MISMATCH",
            "CITATION_MALFORMED",
            "QUOTE_NOT_CONTIGUOUS_SUBSTRING",
            "ANSWER_NOT_DETERMINISTIC",
            "RETRIEVAL_METADATA_INCOMPLETE",
        ]
        for code in expected:
            assert code in PROOF_ERROR_CODES.values()


class TestRenderCanonicalAnswer:
    def test_empty(self) -> None:
        result = _render_canonical_answer(())
        assert "EVIDENCE_GATE_REFUSAL" in result

    def test_single_claim(self) -> None:
        cc = CanonicalClaim(
            quote="经络者",
            document_id="d1",
            chunk_id="c1",
            citation="[d1:c1]",
            chunk_rank=0,
            start_pos=0,
            quote_norm="经络者",
        )
        result = _render_canonical_answer((cc,))
        assert "经络者" in result
        assert "[d1:c1]" in result

    def test_punctuation_appended(self) -> None:
        cc = CanonicalClaim(
            quote="无标点文字",
            document_id="d2",
            chunk_id="c2",
            citation="[d2:c2]",
            chunk_rank=1,
            start_pos=5,
            quote_norm="无标点文字",
        )
        result = _render_canonical_answer((cc,))
        assert result.startswith("无标点文字。")


class TestBuildAndValidateProofRefusal:
    def test_evidence_gate_refusal(self) -> None:
        resp = GroundedGenerationResponse(
            query="test",
            answer="EVIDENCE_GATE_REFUSAL: no data",
            results=[],
            citations=[],
        )
        outcome = GenerationOutcome(
            response=resp, canonical_claims=(), snapshot={}, chunk_rank={}
        )
        proof = build_and_validate_proof(outcome)
        assert proof.is_complete is False
        assert proof.error_code is None
        assert proof.expected_claim_count == 0

    def test_claim_count_mismatch(self) -> None:
        cc = CanonicalClaim(
            quote="经络者。",
            document_id="d1",
            chunk_id="c1",
            citation="[d1:c1]",
            chunk_rank=0,
            start_pos=0,
            quote_norm="经络者",
        )
        resp = GroundedGenerationResponse(
            query="test",
            answer="no citation markers here",
            results=[
                {
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "chunk_index": 0,
                    "content": "经络者。",
                    "citation": "[d1:c1]",
                    "score": 0.9,
                    "source_url": "",
                    "copyright_status": "public_domain",
                }
            ],
            citations=[{"document_id": "d1", "chunk_id": "c1", "text": "[d1:c1]"}],
        )
        outcome = GenerationOutcome(
            response=resp, canonical_claims=(cc,), snapshot={}, chunk_rank={}
        )
        proof = build_and_validate_proof(outcome)
        assert proof.error_code == "CLAIM_COUNT_MISMATCH"

    def test_citation_count_mismatch(self) -> None:
        cc = CanonicalClaim(
            quote="经络者。",
            document_id="d1",
            chunk_id="c1",
            citation="[d1:c1]",
            chunk_rank=0,
            start_pos=0,
            quote_norm="经络者",
        )
        resp = GroundedGenerationResponse(
            query="test",
            answer="经络者。[d1:c1]",
            results=[
                {
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "chunk_index": 0,
                    "content": "经络者。",
                    "citation": "[d1:c1]",
                    "score": 0.9,
                    "source_url": "",
                    "copyright_status": "public_domain",
                }
            ],
            citations=[],  # mismatch
        )
        outcome = GenerationOutcome(
            response=resp, canonical_claims=(cc,), snapshot={}, chunk_rank={}
        )
        proof = build_and_validate_proof(outcome)
        assert proof.error_code == "CITATION_COUNT_MISMATCH"

    def test_chunk_not_in_snapshot(self) -> None:
        cc = CanonicalClaim(
            quote="经络者。",
            document_id="d1",
            chunk_id="c1",
            citation="[d1:c1]",
            chunk_rank=0,
            start_pos=0,
            quote_norm="经络者",
        )
        resp = GroundedGenerationResponse(
            query="test",
            answer="经络者。[d1:c1]",
            results=[
                {
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "chunk_index": 0,
                    "content": "经络者。",
                    "citation": "[d1:c1]",
                    "score": 0.9,
                    "source_url": "",
                    "copyright_status": "public_domain",
                }
            ],
            citations=[{"document_id": "d1", "chunk_id": "c1", "text": "[d1:c1]"}],
        )
        outcome = GenerationOutcome(
            response=resp, canonical_claims=(cc,), snapshot={}, chunk_rank={}
        )
        proof = build_and_validate_proof(outcome)
        assert proof.error_code == "CHUNK_NOT_IN_SNAPSHOT"


class TestBuildAndValidateProofErrors:
    """Error paths: document_id_mismatch, citation_malformed, etc."""

    def test_document_id_mismatch(self) -> None:
        cc = CanonicalClaim(
            quote="经络者。",
            document_id="d1",
            chunk_id="c1",
            citation="[d1:c1]",
            chunk_rank=0,
            start_pos=0,
            quote_norm="经络者",
        )
        rr = _make_retrieval_result(document_id="d2", chunk_id="c1")
        resp = GroundedGenerationResponse(
            query="test",
            answer="经络者。[d1:c1]",
            results=[
                {
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "chunk_index": 0,
                    "content": "经络者。",
                    "citation": "[d1:c1]",
                    "score": 0.9,
                    "source_url": "",
                    "copyright_status": "public_domain",
                }
            ],
            citations=[{"document_id": "d1", "chunk_id": "c1", "text": "[d1:c1]"}],
        )
        outcome = GenerationOutcome(
            response=resp, canonical_claims=(cc,), snapshot={"c1": rr}, chunk_rank={}
        )
        proof = build_and_validate_proof(outcome)
        assert proof.error_code == "DOCUMENT_ID_MISMATCH"

    def test_citation_malformed(self) -> None:
        cc = CanonicalClaim(
            quote="经络者。",
            document_id="d1",
            chunk_id="c1",
            citation="[d2:c1]",  # wrong doc in citation
            chunk_rank=0,
            start_pos=0,
            quote_norm="经络者",
        )
        rr = _make_retrieval_result(document_id="d1", chunk_id="c1")
        resp = GroundedGenerationResponse(
            query="test",
            answer="经络者。[d2:c1]",
            results=[
                {
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "chunk_index": 0,
                    "content": "经络者。",
                    "citation": "[d1:c1]",
                    "score": 0.9,
                    "source_url": "",
                    "copyright_status": "public_domain",
                }
            ],
            citations=[{"document_id": "d1", "chunk_id": "c1", "text": "[d1:c1]"}],
        )
        outcome = GenerationOutcome(
            response=resp, canonical_claims=(cc,), snapshot={"c1": rr}, chunk_rank={}
        )
        proof = build_and_validate_proof(outcome)
        assert proof.error_code == "CITATION_MALFORMED"

    def test_quote_not_contiguous_substring(self) -> None:
        cc = CanonicalClaim(
            quote="不存在的文字",
            document_id="d1",
            chunk_id="c1",
            citation="[d1:c1]",
            chunk_rank=0,
            start_pos=0,
            quote_norm="不存在的文字",
        )
        rr = _make_retrieval_result(document_id="d1", chunk_id="c1", content="经络者。")
        resp = GroundedGenerationResponse(
            query="test",
            answer="不存在的文字[d1:c1]",
            results=[
                {
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "chunk_index": 0,
                    "content": "经络者。",
                    "citation": "[d1:c1]",
                    "score": 0.9,
                    "source_url": "",
                    "copyright_status": "public_domain",
                }
            ],
            citations=[{"document_id": "d1", "chunk_id": "c1", "text": "[d1:c1]"}],
        )
        outcome = GenerationOutcome(
            response=resp, canonical_claims=(cc,), snapshot={"c1": rr}, chunk_rank={}
        )
        proof = build_and_validate_proof(outcome)
        assert proof.error_code == "QUOTE_NOT_CONTIGUOUS_SUBSTRING"

    def test_answer_not_deterministic(self) -> None:
        cc = CanonicalClaim(
            quote="经络者。",
            document_id="d1",
            chunk_id="c1",
            citation="[d1:c1]",
            chunk_rank=0,
            start_pos=0,
            quote_norm="经络者",
        )
        rr = _make_retrieval_result(document_id="d1", chunk_id="c1")
        resp = GroundedGenerationResponse(
            query="test",
            answer="different text [d1:c1]",
            results=[
                {
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "chunk_index": 0,
                    "content": "经络者。",
                    "citation": "[d1:c1]",
                    "score": 0.9,
                    "source_url": "",
                    "copyright_status": "public_domain",
                }
            ],
            citations=[{"document_id": "d1", "chunk_id": "c1", "text": "[d1:c1]"}],
        )
        outcome = GenerationOutcome(
            response=resp, canonical_claims=(cc,), snapshot={"c1": rr}, chunk_rank={}
        )
        proof = build_and_validate_proof(outcome)
        assert proof.error_code == "ANSWER_NOT_DETERMINISTIC"

    def test_complete_proof(self) -> None:
        cc = CanonicalClaim(
            quote="经络者。",
            document_id="d1",
            chunk_id="c1",
            citation="[d1:c1]",
            chunk_rank=0,
            start_pos=0,
            quote_norm="经络者",
        )
        rr = _make_retrieval_result(document_id="d1", chunk_id="c1")
        resp = GroundedGenerationResponse(
            query="test",
            answer="经络者。[d1:c1]",
            results=[
                {
                    "document_id": "d1",
                    "chunk_id": "c1",
                    "chunk_index": 0,
                    "content": "经络者。",
                    "citation": "[d1:c1]",
                    "score": 0.9,
                    "source_url": "",
                    "copyright_status": "public_domain",
                }
            ],
            citations=[{"document_id": "d1", "chunk_id": "c1", "text": "[d1:c1]"}],
        )
        outcome = GenerationOutcome(
            response=resp,
            canonical_claims=(cc,),
            snapshot={"c1": rr},
            chunk_rank={"c1": 0},
        )
        proof = build_and_validate_proof(outcome)
        assert proof.is_complete is True
        assert proof.error_code is None
        assert proof.expected_claim_count == 1
        assert len(proof.verified_claims) == 1


class TestSnapshotToDicts:
    """Tests for _snapshot_to_dicts validation."""

    def test_missing_score_raises(self) -> None:
        class BadResult:
            pass

        with pytest.raises(ValueError, match="missing score"):
            _snapshot_to_dicts({"c1": BadResult()})

    def test_nan_score_raises(self) -> None:
        class NanResult:
            score = float("nan")
            document_id = "d1"
            content = "test"
            metadata = {"retrieval_method": "keyword"}

        with pytest.raises(ValueError, match="NaN"):
            _snapshot_to_dicts({"c1": NanResult()})

    def test_inf_score_raises(self) -> None:
        class InfResult:
            score = float("inf")
            document_id = "d1"
            content = "test"
            metadata = {"retrieval_method": "keyword"}

        with pytest.raises(ValueError, match="Inf"):
            _snapshot_to_dicts({"c1": InfResult()})

    def test_out_of_range_score_raises(self) -> None:
        class BadResult:
            score = 1.5
            document_id = "d1"
            content = "test"
            metadata = {"retrieval_method": "keyword"}

        with pytest.raises(ValueError, match="out of range"):
            _snapshot_to_dicts({"c1": BadResult()})

    def test_negative_score_raises(self) -> None:
        class BadResult:
            score = -0.5
            document_id = "d1"
            content = "test"
            metadata = {"retrieval_method": "keyword"}

        with pytest.raises(ValueError, match="out of range"):
            _snapshot_to_dicts({"c1": BadResult()})

    def test_missing_retrieval_method_raises(self) -> None:
        class BadResult:
            score = 0.5
            document_id = "d1"
            content = "test"
            metadata = {}

        with pytest.raises(ValueError, match="retrieval_method"):
            _snapshot_to_dicts({"c1": BadResult()})

    def test_empty_retrieval_method_raises(self) -> None:
        class BadResult:
            score = 0.5
            document_id = "d1"
            content = "test"
            metadata = {"retrieval_method": ""}

        with pytest.raises(ValueError, match="retrieval_method"):
            _snapshot_to_dicts({"c1": BadResult()})

    def test_non_number_score_raises(self) -> None:
        """Score that is not int or float raises ValueError."""
        class BadResult:
            score = "not-a-number"
            document_id = "d1"
            content = "test"
            metadata = {"retrieval_method": "keyword"}

        with pytest.raises(ValueError, match="not a number"):
            _snapshot_to_dicts({"c1": BadResult()})


# =============================================================================
# _canonical_to_verified — pure mapping
# =============================================================================


class TestCanonicalToVerified:
    def test_quote_ends_with_punctuation_stays_unchanged(self) -> None:
        """Quote ending with 。stays as-is, no extra 。appended."""
        from app.services.generation_proof import _canonical_to_verified

        cc = MagicMock()
        cc.quote = "针灸治疗哮喘。"
        cc.document_id = "d1"
        cc.chunk_id = "c1"
        cc.citation = "cite1"
        cc.chunk_rank = 1
        cc.quote_norm = "针灸治疗哮喘"
        result = _canonical_to_verified(cc)
        assert result.claim_text == "针灸治疗哮喘。"

    def test_quote_without_punctuation_appends_period(self) -> None:
        """Quote ending without punctuation gets 。appended."""
        from app.services.generation_proof import _canonical_to_verified

        cc = MagicMock()
        cc.quote = "针灸治疗哮喘"
        cc.document_id = "d1"
        cc.chunk_id = "c1"
        cc.citation = "cite1"
        cc.chunk_rank = 1
        cc.quote_norm = "针灸治疗哮喘"
        result = _canonical_to_verified(cc)
        assert result.claim_text == "针灸治疗哮喘。"

    def test_empty_quote_returns_empty(self) -> None:
        """Empty quote stays empty — no modification."""
        from app.services.generation_proof import _canonical_to_verified

        cc = MagicMock()
        cc.quote = ""
        cc.document_id = "d1"
        cc.chunk_id = "c1"
        cc.citation = "cite1"
        cc.chunk_rank = 1
        cc.quote_norm = ""
        result = _canonical_to_verified(cc)
        assert result.claim_text == ""
