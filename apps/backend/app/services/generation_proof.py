"""
GenerationProof — validates and encapsulates canonical GenerationOutcome.

P0-1: No answer parsing. No duplicate claim construction. No continue-on-failure.
P0-2: Explicit completeness with is_complete, error_code, expected_claim_count.
P0-4: Document/chunk provenance verified against retrieval snapshot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas.generation import GroundedGenerationResponse
from app.services.generation_service import (
    CanonicalClaim,
    GenerationOutcome,
    GenerationPipeline,
    _is_substring,
)


# ======================================================================
# VerifiedClaim — immutable binding of one canonical claim
# ======================================================================


@dataclass
class VerifiedClaim:
    """One verified claim with exact citation binding.

    Mapped 1:1 from CanonicalClaim. quote is the EXACT contiguous substring
    from chunk.content, verified at generation time.
    """

    claim_text: str  # rendered text (quote + trailing punctuation)
    quote: str  # exact contiguous substring from chunk.content
    document_id: str
    chunk_id: str
    citation_str: str  # [document_id:chunk_id]
    chunk_rank: int
    quote_norm: str


def _canonical_to_verified(cc: CanonicalClaim) -> VerifiedClaim:
    """Convert one CanonicalClaim → VerifiedClaim. Pure mapping, no parsing."""
    quote = cc.quote
    claim_text = quote
    if claim_text and claim_text[-1] not in "。！？.!?）\"'":
        claim_text = claim_text + "。"
    return VerifiedClaim(
        claim_text=claim_text,
        quote=quote,
        document_id=cc.document_id,
        chunk_id=cc.chunk_id,
        citation_str=cc.citation,
        chunk_rank=cc.chunk_rank,
        quote_norm=cc.quote_norm,
    )


# ======================================================================
# GenerationProof — complete proof with explicit integrity checks
# ======================================================================

PROOF_ERROR_CODES: dict[str, str] = {
    "ACADEMIC_CLAIM_BINDING_FAILED": "ACADEMIC_CLAIM_BINDING_FAILED",
    "CLAIM_COUNT_MISMATCH": "CLAIM_COUNT_MISMATCH",
    "CITATION_COUNT_MISMATCH": "CITATION_COUNT_MISMATCH",
    "CHUNK_NOT_IN_SNAPSHOT": "CHUNK_NOT_IN_SNAPSHOT",
    "DOCUMENT_ID_MISMATCH": "DOCUMENT_ID_MISMATCH",
    "CITATION_MALFORMED": "CITATION_MALFORMED",
    "QUOTE_NOT_CONTIGUOUS_SUBSTRING": "QUOTE_NOT_CONTIGUOUS_SUBSTRING",
    "ANSWER_NOT_DETERMINISTIC": "ANSWER_NOT_DETERMINISTIC",
}


@dataclass
class GenerationProof:
    """Complete proof bundle with explicit integrity status.

    P0-2: is_complete is True ONLY when ALL integrity checks pass.
    Partial success is impossible — any failure means is_complete=False
    and verified_claims is empty.
    """

    response: GroundedGenerationResponse
    verified_claims: list[VerifiedClaim] = field(default_factory=list)
    is_complete: bool = False
    error_code: str | None = None
    expected_claim_count: int = 0

    @property
    def has_error(self) -> bool:
        """True when proof integrity failed."""
        return self.error_code is not None

    @property
    def has_no_evidence(self) -> bool:
        """P0-1: True when retrieval returned empty results — not an error, just no data."""
        return (
            not self.is_complete
            and self.error_code is None
            and self.expected_claim_count == 0
            and len(self.response.results) == 0
        )

    @property
    def has_integrity_error(self) -> bool:
        """P0-1: True when proof validation failed with an explicit error code."""
        return self.error_code is not None


# ======================================================================
# Proof builder — validates canonical outcome, produces GenerationProof
# ======================================================================


def build_and_validate_proof(outcome: GenerationOutcome) -> GenerationProof:
    """P0-1, P0-2, P0-4: Build GenerationProof from canonical outcome.

    Validates:
    1. canonical claim count == rendered answer claim count
    2. canonical claim count == response citations count
    3. Every chunk_id exists in snapshot
    4. canonical document_id == snapshot[chunk_id].document_id
    5. citation == f"[{document_id}:{chunk_id}]"
    6. quote is contiguous normalized substring of chunk content
    7. answer == deterministic re-render from canonical claims
    8. ANY failure → is_complete=False, error_code set, no partial claims

    NO: answer parsing, continue-on-failure, substring guessing, partial success.
    """
    response = outcome.response
    canonical = outcome.canonical_claims
    snapshot = outcome.snapshot

    # P0-1: Refusal outcome → empty claims, complete=false
    if "EVIDENCE_GATE_REFUSAL" in response.answer or not response.results:
        return GenerationProof(
            response=response,
            verified_claims=[],
            is_complete=False,
            error_code=None,
            expected_claim_count=0,
        )

    expected_count = len(canonical)

    # P0-2 Rule 1: canonical claim count == rendered answer claim count
    # Count citation markers in answer
    answer_citations = [
        m for m in re.finditer(r"\[([^\]]+):([^\]]+)\]", response.answer)
    ]
    answer_claim_count = len(answer_citations)

    if expected_count != answer_claim_count:
        return GenerationProof(
            response=response,
            verified_claims=[],
            is_complete=False,
            error_code=PROOF_ERROR_CODES["CLAIM_COUNT_MISMATCH"],
            expected_claim_count=expected_count,
        )

    # P0-2 Rule 2: canonical claim count == response citations count
    if expected_count != len(response.citations):
        return GenerationProof(
            response=response,
            verified_claims=[],
            is_complete=False,
            error_code=PROOF_ERROR_CODES["CITATION_COUNT_MISMATCH"],
            expected_claim_count=expected_count,
        )

    verified: list[VerifiedClaim] = []

    for i, cc in enumerate(canonical):
        # P0-2 Rule 3: chunk_id exists in snapshot
        if cc.chunk_id not in snapshot:
            return GenerationProof(
                response=response,
                verified_claims=[],
                is_complete=False,
                error_code=PROOF_ERROR_CODES["CHUNK_NOT_IN_SNAPSHOT"],
                expected_claim_count=expected_count,
            )

        chunk_result = snapshot[cc.chunk_id]

        # P0-2 Rule 4, P0-4: document_id must match snapshot
        if cc.document_id != chunk_result.document_id:
            return GenerationProof(
                response=response,
                verified_claims=[],
                is_complete=False,
                error_code=PROOF_ERROR_CODES["DOCUMENT_ID_MISMATCH"],
                expected_claim_count=expected_count,
            )

        # P0-2 Rule 5: citation exactly [document_id:chunk_id]
        expected_citation = f"[{cc.document_id}:{cc.chunk_id}]"
        if cc.citation != expected_citation:
            return GenerationProof(
                response=response,
                verified_claims=[],
                is_complete=False,
                error_code=PROOF_ERROR_CODES["CITATION_MALFORMED"],
                expected_claim_count=expected_count,
            )

        # P0-2 Rule 6: quote is contiguous substring of chunk content
        if not _is_substring(cc.quote, chunk_result.content):
            return GenerationProof(
                response=response,
                verified_claims=[],
                is_complete=False,
                error_code=PROOF_ERROR_CODES["QUOTE_NOT_CONTIGUOUS_SUBSTRING"],
                expected_claim_count=expected_count,
            )

        verified.append(_canonical_to_verified(cc))

    # P0-2 Rule 7: answer == deterministic re-render from canonical claims
    expected_answer = _render_canonical_answer(canonical)
    if expected_answer != response.answer:
        return GenerationProof(
            response=response,
            verified_claims=[],
            is_complete=False,
            error_code=PROOF_ERROR_CODES["ANSWER_NOT_DETERMINISTIC"],
            expected_claim_count=expected_count,
        )

    # All checks passed
    return GenerationProof(
        response=response,
        verified_claims=verified,
        is_complete=True,
        error_code=None,
        expected_claim_count=expected_count,
    )


def _render_canonical_answer(canonical: tuple[CanonicalClaim, ...]) -> str:
    """Deterministically render answer from canonical claims.

    Must produce the exact same output as the pipeline's _render_answer_from_canonical.
    """
    if not canonical:
        return "EVIDENCE_GATE_REFUSAL: 没有通过验证的证据。"

    lines = []
    for c in canonical:
        quote = c.quote
        if quote and quote[-1] not in "。！？.!?）\"'":
            quote = quote + "。"
        lines.append(f"{quote}{c.citation}")

    return "\n\n".join(lines)


# ======================================================================
# Backward-compat: ProvedGenerationPipeline alias
# ======================================================================


class ProvedGenerationPipeline(GenerationPipeline):
    """Backward-compatible alias — generate_with_proof() is on GenerationPipeline now.

    Kept so existing callers don't break. Delegates to parent.
    """

    async def generate_with_proof(
        self,
        query: str,
        top_k: int = 5,
    ) -> GenerationProof:
        """Run pipeline and return validated GenerationProof."""
        outcome = await self._generate_outcome(query, top_k)
        return build_and_validate_proof(outcome)
