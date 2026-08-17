"""CandidateExtraction — AI/rule extraction candidate buffer (Evidence-Native Phase A0).

Candidates are the single gate between the AI-extraction world and the
academically-confirmed knowledge graph. No candidate may become an ``Evidence``
without a human review that passes server-side dual-hash grounding checks inside
a single transaction.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.academic_evidence import Evidence
    from app.models.document_chunk import DocumentChunk
    from app.models.user import User
    from app.models.version import Version
    from app.models.workspace import ResearchSession


class CandidateStatus(str, enum.Enum):
    """Lifecycle of a candidate extraction."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    DRIFT_INVALID = "drift_invalid"


class CandidateExtraction(BaseModel):
    """AI/rule extraction candidate buffer with dual-hash grounding anchors.

    ``expected_chunk_sha256`` / ``expected_nfc_sha256`` pin the exact chunk
    bytes the extraction was produced from. At approval time the live chunk is
    re-hashed; any divergence marks the candidate ``DRIFT_INVALID`` rather than
    publishing it into the academic graph.
    """

    __tablename__ = "candidate_extractions"

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("versions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    expected_chunk_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    expected_nfc_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    unicode_normalization: Mapped[str] = mapped_column(
        String(10), default="NFC", nullable=False
    )
    start_char: Mapped[int] = mapped_column(Integer, nullable=False)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False)
    exact_text: Mapped[str] = mapped_column(Text, nullable=False)

    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    page_image_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_image_hash_alg: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "page_image_hash_alg IN ('sha256', 'sha512', 'phash')",
            name="ck_candidate_page_image_hash_alg",
        ),
        default="sha256",
        server_default="sha256",
        nullable=False,
    )

    extraction_type: Mapped[str] = mapped_column(
        String(50), default="proposed_evidence", nullable=False
    )
    extracted_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    extractor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[CandidateStatus] = mapped_column(
        Enum(
            CandidateStatus,
            name="candidate_status",
            values_callable=lambda e: [m.value for m in e],
            native_enum=False,
            length=50,
        ),
        default=CandidateStatus.PENDING,
        nullable=False,
    )
    reviewed_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_evidence_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("evidences.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    session: Mapped[ResearchSession] = relationship("ResearchSession", lazy="selectin")
    created_by: Mapped[User] = relationship(
        "User", foreign_keys=[created_by_user_id], lazy="selectin"
    )
    chunk: Mapped[DocumentChunk] = relationship(
        "DocumentChunk", lazy="selectin"
    )
    version: Mapped[Version] = relationship("Version", lazy="selectin")
    published_evidence: Mapped[Evidence | None] = relationship(
        "Evidence", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<CandidateExtraction id={self.id} status={self.status.value!r} "
            f"chunk={self.chunk_id}>"
        )
