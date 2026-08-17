"""CandidateExtractionMetadata — candidate-specific 1:1 metadata (HFB-DEV-0505 §7/§11).

Phase A0 keeps metadata candidate-specific rather than a generic polymorphic
table: the owning candidate is a real foreign key, so the 1:1 relationship is
verifiable at the database level (no ``entity_type``/``entity_id`` string
association).
"""

from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class CandidateExtractionMetadata(BaseModel):
    """1:1 metadata record owned by exactly one candidate extraction."""

    __tablename__ = "candidate_extraction_metadata"

    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_extractions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="所属候选 ID (1:1 真实 FK)",
    )
    payload: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="元数据 JSON 载荷"
    )

    # Common business-table fields (HFB-DEV-0505 §7).
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        server_default="active",
        nullable=False,
        comment="元数据状态",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
        comment="模型修订版本号",
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="创建人 user ID",
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="最后修改人 user ID",
    )

    def __repr__(self) -> str:
        return f"<CandidateExtractionMetadata id={self.id} candidate={self.candidate_id}>"
