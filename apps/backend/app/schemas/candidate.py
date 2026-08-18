"""Candidate extraction schemas — Phase A0 create / list / detail payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.academic_evidence import EvidenceLevel
from app.models.candidate_extraction import CandidateStatus


class ExtractedEvidencePayload(BaseModel):
    """The extracted payload carried in ``CandidateExtraction.extracted_payload``.

    This is the single source of truth for the payload shape shared by the
    candidate-create request and the publish unit of work, so the two can never
    drift apart.
    """

    description: str = Field(..., min_length=1)
    evidence_level: EvidenceLevel
    quote_text: str | None = Field(default=None)
    note: str | None = Field(default=None)


class CreateCandidateRequest(BaseModel):
    """AI/rule extraction result to buffer as a PENDING candidate.

    Grounding anchors (``expected_chunk_sha256`` / ``expected_nfc_sha256`` /
    ``start_char`` / ``end_char`` / ``exact_text``) are validated server-side
    against the live chunk bytes before the candidate is accepted. A candidate
    whose anchors do not match the chunk is rejected at creation time — it can
    never enter the review queue un-grounded.
    """

    # Ownership + grounding anchors
    session_id: str = Field(..., min_length=1, max_length=36)
    chunk_id: str = Field(..., min_length=1, max_length=36)
    version_id: str = Field(..., min_length=1, max_length=36)
    expected_chunk_sha256: str = Field(..., min_length=64, max_length=64)
    expected_nfc_sha256: str = Field(..., min_length=64, max_length=64)
    start_char: int = Field(..., ge=0)
    end_char: int = Field(..., ge=1)
    exact_text: str = Field(..., min_length=1)
    unicode_normalization: str = Field(default="NFC", min_length=1, max_length=10)

    # Extraction content
    extracted_payload: ExtractedEvidencePayload
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    extractor_name: str = Field(..., min_length=1, max_length=100)

    # AI metadata (required for provenance; rules-based extractors fill the
    # extractor identifier as ai_model per the model column comment).
    ai_model: str = Field(..., min_length=1, max_length=200)
    ai_version: str = Field(..., min_length=1, max_length=100)
    prompt_version: str = Field(..., min_length=1, max_length=100)
    processing_time: float = Field(..., ge=0, le=1e12)
    confidence: float = Field(..., ge=0, le=1)
    prompt_hash: str | None = Field(default=None, max_length=64)

    # HFB-DAT-0303 core metadata (optional, defaults filled server-side).
    title: str = Field(default="", max_length=500)
    language: str = Field(default="zh", max_length=20)
    abstract: str = Field(default="")
    keywords: str = Field(default="", max_length=500)
    description: str = Field(default="")

    # Page-image grounding (optional).
    page_image_hash: str | None = Field(default=None, max_length=64)
    page_image_hash_alg: str = Field(default="sha256", max_length=20)
    extraction_type: str = Field(default="proposed_evidence", max_length=50)


class CandidateResponse(BaseModel):
    """Full candidate representation returned by the API."""

    id: str
    session_id: str
    created_by: str
    chunk_id: str
    version_id: str
    start_char: int
    end_char: int
    exact_text: str
    extracted_payload: dict[str, Any]
    input_snapshot: dict[str, Any]
    extractor_name: str
    ai_model: str
    ai_version: str
    prompt_version: str
    processing_time: float
    confidence: float
    status: CandidateStatus
    title: str
    reviewed_by_user_id: str | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    published_evidence_id: str | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class CandidateListResponse(BaseModel):
    """Paginated candidate list."""

    items: list[CandidateResponse]
    total: int
    page: int
    limit: int
