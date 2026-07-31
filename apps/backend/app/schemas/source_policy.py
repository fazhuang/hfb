"""
SourcePolicy schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SourcePolicyCreate(BaseModel):
    source_name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True


class SourcePolicyUpdate(BaseModel):
    source_name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None


class SourcePolicyResponse(BaseModel):
    id: UUID
    source_name: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
