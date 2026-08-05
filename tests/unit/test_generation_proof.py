
"""Unit tests for generation_proof.py — VerifiedClaim, GenerationProof, _render_canonical_answer."""

from __future__ import annotations

import pytest
from app.schemas.generation import GroundedGenerationResponse
from app.services.generation_proof import (
    GenerationProof,
    PROOF_ERROR_CODES,
    VerifiedClaim,
    build_and_validate_proof,
    _render_canonical_answer,
)
from app.services.generation_service import CanonicalClaim, GenerationOutcome


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
            query="test", answer="EVIDENCE_GATE_REFUSAL: no data", results=[], citations=[]
        )
        outcome = GenerationOutcome(
            response=resp,
            canonical_claims=(),
            snapshot={},
            chunk_rank={},
        )
        proof = build_and_validate_proof(outcome)
        assert proof.is_complete is False
        assert proof.error_code is None
        assert proof.expected_claim_count == 0
