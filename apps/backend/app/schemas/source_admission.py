"""Source admission schemas — online 0306 §3 checklist entry payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.source_admission import SourceAdmissionStatus


class SourceAdmissionEntryUpsert(BaseModel):
    """One row filled by the Research Lead (entry_key is in the path)."""

    source_uri: str = Field(..., min_length=1, max_length=2000)
    authorization_basis: str = Field(..., min_length=1, max_length=500)
    version_label: str = Field(..., min_length=1, max_length=500)
    import_scope: str = Field(..., min_length=1, max_length=500)
    binding_plan: str = Field(..., min_length=1)
    risk_note: str = Field(..., min_length=1)


class SourceAdmissionEntryResponse(BaseModel):
    """A filled row (or an empty placeholder row)."""

    id: str | None
    entry_key: str
    source_type: str
    source_uri: str | None
    authorization_basis: str | None
    version_label: str | None
    import_scope: str | None
    binding_plan: str | None
    risk_note: str | None
    status: str  # "empty" | "submitted" | "approved" | "rejected"
    submitted_by: str | None
    submitted_at: datetime | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None

    model_config = {"from_attributes": True}


class SourceAdmissionSummary(BaseModel):
    total_rows: int
    filled: int
    submitted: int
    approved: int
    rejected: int
    complete: bool  # all 13 rows approved


class SourceAdmissionListResponse(BaseModel):
    items: list[SourceAdmissionEntryResponse]
    summary: SourceAdmissionSummary


class SourceAdmissionReviewRequest(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=2000)


class SourceAdmissionReviewResponse(BaseModel):
    success: bool
    entry_key: str
    status: SourceAdmissionStatus
    message: str
