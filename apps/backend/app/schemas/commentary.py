"""Commentary schemas — Phase 2b 注疏链."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentaryCreate(BaseModel):
    """Request to create a commentary."""

    model_config = ConfigDict(extra="forbid", strict=True)

    passage_id: str = Field(..., description="所注段落 ID")
    version_id: str | None = Field(default=None, description="所注版本 ID")
    author_id: str | None = Field(default=None, description="注者 ID")
    commentary_type: str = Field(
        default="end_of_passage",
        description="interlinear_gloss | end_of_passage | sub_commentary | commentary_work | critique",
    )
    layer: str = Field(default="modern", description="年代层")
    content_text: str = Field(..., description="注文内容")
    target_position_start: int | None = Field(
        default=None, description="段落中起始字符偏移"
    )
    target_position_end: int | None = Field(
        default=None, description="段落中结束字符偏移"
    )
    parent_id: str | None = Field(default=None, description="自引用 — 回应另一条注疏")
    relation_type: str | None = Field(
        default=None,
        description="supplements | refutes | expands | annotates | interprets",
    )


class CommentaryResponse(BaseModel):
    """Commentary as returned to API consumers."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    passage_id: str
    version_id: str | None = None
    author_id: str | None = None
    commentary_type: str
    layer: str
    content_text: str
    target_position_start: int | None = None
    target_position_end: int | None = None
    parent_id: str | None = None
    relation_type: str | None = None
    created_at: datetime
    updated_at: datetime


class CommentaryChainResponse(BaseModel):
    """A full commentary chain from root to leaf."""

    model_config = ConfigDict(extra="forbid", strict=True)

    chain: list[CommentaryResponse] = Field(default_factory=list)
    depth: int = Field(default=0)


class CommentaryGraphResponse(BaseModel):
    """Commentary debate/supplement graph for a passage."""

    model_config = ConfigDict(extra="forbid", strict=True)

    nodes: list[CommentaryResponse] = Field(default_factory=list)
    edges: list[dict] = Field(
        default_factory=list
    )  # {parent_id, child_id, relation_type}


class CommentaryEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    success: bool = Field(default=True)
    data: (
        CommentaryResponse
        | CommentaryChainResponse
        | CommentaryGraphResponse
        | list[CommentaryResponse]
    )
    message: str = Field(default="ok")
