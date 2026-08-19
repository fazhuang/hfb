"""SourceAdmissionEntry — online source-admission checklist entry (HFB-DAT-0306).

Digitizes the manual §3 checklist (13 rows: CV-01..05, DOC-01..05, HOLD-01..03)
into an auditable, reviewable record. The Research Lead fills each row; the
Steering Committee reviews and approves/rejects. Approval here records the
governance decision but does NOT auto-open the SOURCE_ADMISSION_OPEN deploy
flag — that stays a manual deploy-layer flip (0306 §6.3: no auto-release).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel

# The 13 fixed rows from HFB-DAT-0306 §3, in order.
ENTRY_KEYS: tuple[str, ...] = (
    "CV-01",
    "CV-02",
    "CV-03",
    "CV-04",
    "CV-05",
    "DOC-01",
    "DOC-02",
    "DOC-03",
    "DOC-04",
    "DOC-05",
    "HOLD-01",
    "HOLD-02",
    "HOLD-03",
)

SOURCE_TYPES: tuple[str, ...] = (
    "classical_version",
    "research_literature",
    "collection",
)

ENTRY_KEY_TO_TYPE: dict[str, str] = {
    **{k: "classical_version" for k in ENTRY_KEYS if k.startswith("CV-")},
    **{k: "research_literature" for k in ENTRY_KEYS if k.startswith("DOC-")},
    **{k: "collection" for k in ENTRY_KEYS if k.startswith("HOLD-")},
}


class SourceAdmissionStatus(str, enum.Enum):
    """Lifecycle of a source-admission entry."""

    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class SourceAdmissionEntry(BaseModel):
    """One row of the 0306 §3 checklist, filled by the Research Lead."""

    __tablename__ = "source_admission_entries"
    __table_args__ = (
        Index("idx_sae_entry_key", "entry_key", unique=True),
        Index("idx_sae_status", "status"),
    )

    entry_key: Mapped[str] = mapped_column(String(20), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # The 6 Research-Lead-filled fields (0306 §3.4).
    source_uri: Mapped[str] = mapped_column(String(2000), nullable=False)
    authorization_basis: Mapped[str] = mapped_column(String(500), nullable=False)
    version_label: Mapped[str] = mapped_column(String(500), nullable=False)
    import_scope: Mapped[str] = mapped_column(String(500), nullable=False)
    binding_plan: Mapped[str] = mapped_column(Text, nullable=False)
    risk_note: Mapped[str] = mapped_column(Text, nullable=False)

    # Review state.
    status: Mapped[SourceAdmissionStatus] = mapped_column(
        Enum(
            SourceAdmissionStatus,
            name="source_admission_status",
            values_callable=lambda e: [m.value for m in e],
            native_enum=False,
            length=20,
        ),
        default=SourceAdmissionStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    submitted_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SourceAdmissionEntry {self.entry_key} {self.status.value!r}>"
