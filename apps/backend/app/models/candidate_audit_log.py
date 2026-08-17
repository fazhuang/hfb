"""CandidateAuditLog — append-only, tamper-evident audit trail for candidate review.

The table is protected by database-level DDL triggers (see
``app.db.audit_triggers``) that forbid DELETE and any UPDATE other than the
single sanctioned ``candidate_id`` de-linking transition.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Postgres ``json`` has no equality operator, but the append-only DDL trigger
# compares these columns with ``IS NOT DISTINCT FROM``. Use jsonb on Postgres
# (falls back to JSON on SQLite) so the trigger's null-safe comparison works.
_AUDIT_JSON = JSON().with_variant(JSONB(), "postgresql")


class CandidateAuditLog(Base):
    """Immutable append-only audit record.

    Extends ``Base`` (not ``BaseModel``) deliberately: this table carries no
    soft-delete/updated_at columns, matching the append-only DDL trigger
    contract that permits only the ``candidate_id`` NULL transition.
    """

    __tablename__ = "candidate_audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidate_extractions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    operator_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    input_snapshot: Mapped[dict | None] = mapped_column(_AUDIT_JSON, nullable=True)
    pre_payload: Mapped[dict | None] = mapped_column(_AUDIT_JSON, nullable=True)
    post_payload: Mapped[dict | None] = mapped_column(_AUDIT_JSON, nullable=True)
    published_evidence_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<CandidateAuditLog id={self.id} action={self.action!r}>"
