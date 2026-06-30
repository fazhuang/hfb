"""Grounded generation response schemas — Day 4 P0 strict.

LLM MUST return structured claims JSON. Server validates each quote is an
exact substring of the corresponding chunk, then renders the final answer
deterministically. No free-form LLM text ever reaches the user.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# LLM output contract — the ONLY format the LLM may return
# ---------------------------------------------------------------------------

class LLMClaim(BaseModel):
    """A single claim the LLM asserts, bound to one chunk."""
    citation: str = Field(..., description="[document_id:chunk_id] format")
    quote: str = Field(..., description="Exact contiguous substring from chunk.content")


class LLMClaimsResponse(BaseModel):
    """Strict JSON the LLM MUST return. No other fields, no free text."""
    claims: list[LLMClaim] = Field(default_factory=list, max_length=20)


# ---------------------------------------------------------------------------
# Server-side validation error codes
# ---------------------------------------------------------------------------

VALIDATION_ERROR_CODES: dict[str, str] = {
    "INVALID_JSON": "LLM 返回的不是合法 JSON",
    "INVALID_SCHEMA": "LLM 返回的 JSON 不符合 claims schema",
    "EXTRA_FIELDS": "JSON 包含未定义的额外字段",
    "CITATION_OUTSIDE_SNAPSHOT": "citation 引用了本次检索快照之外的 chunk",
    "DOCUMENT_CHUNK_MISMATCH": "document_id 与 chunk_id 的数据库关系不正确",
    "CHUNK_DELETED": "引用的 chunk 已被删除",
    "QUOTE_EMPTY": "quote 为空",
    "QUOTE_NOT_IN_CHUNK": "quote 不是对应 chunk.content 的连续原文子串",
    "CROSS_BINDING": "同一 quote 绑定到错误的 chunk",
    "EMPTY_CLAIMS": "claims 列表为空",
    "TOO_MANY_CLAIMS": "claims 数量超过 top_k",
    "PROMPT_INJECTION_OUTPUT": "LLM 输出包含注入文本",
    "PROVIDER_ERROR": "AI 服务错误",
    "RATE_LIMITED": "请求频率限制",
}


class GenerationMetadata(BaseModel):
    """Metadata for the citation-grounded generation."""

    top_k: int = 0
    model: str = "citation-grounded-llm"
    ai_generated: bool = False
    citation_validation: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None


class GroundedGenerationResponse(BaseModel):
    """Response envelope — answer rendered server-side from verified quotes."""

    query: str
    answer: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    metadata: GenerationMetadata = Field(default_factory=GenerationMetadata)
