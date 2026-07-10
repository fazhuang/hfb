"""
Schemas for ClassicalVersion (古籍版本目录).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

PUBLIC_DOMAIN_STATUSES = frozenset({
    "confirmed_public_domain",
    "copyright_claimed",
    "unknown",
    "not_applicable",
})

REVIEW_STATUSES = frozenset({
    "pending_review",
    "under_review",
    "approved",
    "rejected",
})

EDITION_TYPES = frozenset({
    "刻本", "抄本", "石印本", "排印本", "影印本", "其他",
})


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------


class ClassicalVersionCreate(BaseModel):
    work_title: str = Field(..., min_length=1, max_length=500, description="著作名称")
    version_name: str = Field(..., min_length=1, max_length=300, description="版本名称")
    dynasty: str | None = Field(default=None, max_length=100, description="朝代")
    edition_type: str | None = Field(default=None, max_length=100, description="版本类型")
    volume_count: int | None = Field(default=None, ge=0, description="卷数")
    repository: str | None = Field(default=None, max_length=500, description="收藏机构")
    source_url: str = Field(..., min_length=1, max_length=2000, description="来源链接 — 必填")
    image_url: str | None = Field(default=None, max_length=2000, description="书影链接")
    public_domain_status: str = Field(..., max_length=50, description="公共领域状态 — 必填")
    ocr_text_available: bool = Field(default=False, description="是否有 OCR 文本")
    citation_note: str | None = Field(default=None, description="引用说明")
    academic_note: str | None = Field(default=None, description="学术备注")
    review_status: str = Field(default="pending_review", max_length=50, description="审核状态")


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------


class ClassicalVersionUpdate(BaseModel):
    work_title: str | None = Field(default=None, min_length=1, max_length=500)
    version_name: str | None = Field(default=None, min_length=1, max_length=300)
    dynasty: str | None = None
    edition_type: str | None = None
    volume_count: int | None = None
    repository: str | None = None
    source_url: str | None = Field(default=None, min_length=1, max_length=2000)
    image_url: str | None = None
    public_domain_status: str | None = None
    ocr_text_available: bool | None = None
    citation_note: str | None = None
    academic_note: str | None = None
    review_status: str | None = None


# ------------------------------------------------------------------
# Brief (list items)
# ------------------------------------------------------------------


class ClassicalVersionBrief(BaseModel):
    id: UUID
    work_title: str
    version_name: str
    dynasty: str | None
    edition_type: str | None
    repository: str | None
    public_domain_status: str
    review_status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Full response
# ------------------------------------------------------------------


class ClassicalVersionResponse(ClassicalVersionCreate):
    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
