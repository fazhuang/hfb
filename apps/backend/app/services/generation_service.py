"""
Citation-Grounded LLM Generation Pipeline — Day 4.

Adds strict citation binding on top of the existing retrieval system.
Every factual sentence MUST map to at least one cited chunk.
No hallucination. No uncited claims.

Query → Retrieve → Build Grounded Prompt → Generate → Validate Citations → Respond
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai_response import Citation
from app.schemas.generation import GenerationMetadata, GroundedGenerationResponse
from app.services.ai_service import AIService
from app.services.rag_service import RAGService

# ---------------------------------------------------------------------------
# Strict citation-grounded system prompt
# ---------------------------------------------------------------------------

GROUNDED_SYSTEM_PROMPT = """你是皇甫谧数字人文平台（Huangfu Mi Digital Humanities Platform）的AI研究助手。
你的知识领域仅限于中国古代医学文献、中医经典文本、中医人物和数字人文研究方法。

**严格规则：Citation-Grounded 回答**

1. **仅使用提供的资料**：你必须且仅能基于下方「研究上下文」中提供的资料来回答。
   绝对禁止使用任何外部知识、训练数据中的信息或你自己的知识。

2. **逐句引用**：每一个事实性陈述句的末尾必须标注出处编号，格式为 [N]，
   对应上下文中的资料编号。没有引用编号的事实陈述 = 无效输出。

3. **无证据则拒答**：如果上下文中没有任何资料与用户问题相关，你必须回答：
   "EVIDENCE_GATE_REFUSAL: 当前知识库中没有找到与您问题相关的资料。"
   不得以任何形式猜测或编造答案。

4. **禁止编造**：不得编造、猜测、推断任何未在上下文中明确出现的信息。
   不得润色或扩展上下文中的内容使其看起来更完整。
   如果信息不完整，明确指出"上下文未提供此信息"。

5. **区分事实与推断**：
   - 直接来自上下文的陈述 → 标注 [N]
   - 无法验证的推断 → 明确标注"此为推断，上下文无直接证据"
   - 上下文缺失的信息 → 明确说明"此信息在上下文中未找到"

6. **回答语言**：使用中文。

你是学术辅助工具，不是聊天机器人。所有输出必须可追溯到具体来源。
每一个事实句必须有一个 [N] 引用。这是强制性要求，不可例外。"""

# ---------------------------------------------------------------------------
# Generation Pipeline
# ---------------------------------------------------------------------------


class GenerationPipeline:
    """Citation-grounded generation pipeline.

    Wraps retrieval + LLM generation + citation validation into a single
    non-streaming call.  Does NOT modify the retrieval layer — it consumes
    RAGService as-is.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._rag: RAGService | None = None
        self._ai: AIService | None = None

    @property
    def rag(self) -> RAGService:
        if self._rag is None:
            self._rag = RAGService(self.session)
        return self._rag

    @property
    def ai(self) -> AIService:
        if self._ai is None:
            self._ai = AIService()
        return self._ai

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        query: str,
        top_k: int = 5,
        entity_types: list[str] | None = None,
    ) -> GroundedGenerationResponse:
        """Run the full citation-grounded generation pipeline."""

        # Step 1 — Retrieve (unchanged retrieval layer)
        chunks = await self.rag.retrieve(query, entity_types=entity_types, top_k=top_k)
        context = await self.rag.assemble_context(query, top_k=top_k)

        if not chunks or not context.strip():
            return self._refuse(query)

        # Step 2 — Build grounded prompt
        system_prompt, user_messages = self._build_prompt(query, context)

        # Step 3 — Generate (non-streaming)
        raw_answer = await self._generate(system_prompt, user_messages)

        # Step 4 — Validate citations
        validation = self._validate_citations(raw_answer, len(chunks))

        # Step 5 — Compose structured response
        return self._compose(query, raw_answer, chunks, validation)

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_prompt(
        self, query: str, context: str
    ) -> tuple[str, list[dict[str, str]]]:
        """Build a strict citation-grounded prompt.

        Returns (system_prompt, user_messages) so the caller can inject
        the system prompt separately.
        """
        system_prompt = (
            GROUNDED_SYSTEM_PROMPT
            + f"\n\n研究上下文（每条资料标注了编号 [N]，引用时必须使用这些编号）：\n\n{context}"
        )

        user_messages = [{"role": "user", "content": query}]

        return system_prompt, user_messages

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    async def _generate(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> str:
        """Call the LLM, falling back to mock when no API key is configured."""
        if not self.ai.available:
            return self._mock_generate(system_prompt, messages)

        if not self.ai.check_rate_limit():
            return "⚠️ 请求过于频繁，请稍后重试。"

        return await self.ai.complete(messages, system_prompt=system_prompt)

    def _mock_generate(
        self, system_prompt: str, messages: list[dict[str, str]]
    ) -> str:
        """Deterministic mock answer that cites all available chunks.

        Used when no LLM API key is configured.  Produces minimal but
        citation-compliant output for testing.
        """
        query = messages[-1]["content"] if messages else ""

        # Extract available chunk numbers from the context embedded in system_prompt
        chunk_refs = sorted(set(int(n) for n in re.findall(r"\[(\d+)\]", system_prompt)))

        if not chunk_refs:
            return f"EVIDENCE_GATE_REFUSAL: 当前知识库中没有找到与您问题「{query}」相关的资料。"

        lines = [
            f"根据知识库中的 {len(chunk_refs)} 条相关资料，针对您的问题「{query}」回复如下：",
            "",
        ]
        for n in chunk_refs:
            lines.append(f"相关资料 [{n}] 提供了相关信息。[{n}]")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Citation validation
    # ------------------------------------------------------------------

    def _validate_citations(
        self, answer: str, num_chunks: int
    ) -> dict[str, Any]:
        """Validate citation binding in the generated answer.

        Checks:
        - Answer contains [N] references
        - All [N] references map to valid chunk numbers (1..num_chunks)
        - No fabricated references

        This is a BEST-EFFORT validation — it warns but does not block.
        """
        if "EVIDENCE_GATE_REFUSAL" in answer:
            return {
                "has_citations": False,
                "cited_chunks": [],
                "invalid_refs": [],
                "uncited": True,
                "total_chunks": num_chunks,
                "is_valid": True,  # refusal is valid
            }

        cited = set(int(n) for n in re.findall(r"\[(\d+)\]", answer))
        valid = sorted(n for n in cited if 1 <= n <= num_chunks)
        invalid = sorted(cited - set(valid))
        uncited = num_chunks > 0 and len(valid) == 0

        return {
            "has_citations": len(valid) > 0,
            "cited_chunks": valid,
            "invalid_refs": invalid,
            "uncited": uncited,
            "total_chunks": num_chunks,
            "is_valid": len(valid) > 0 and len(invalid) == 0,
        }

    # ------------------------------------------------------------------
    # Response composition
    # ------------------------------------------------------------------

    def _compose(
        self,
        query: str,
        answer: str,
        chunks: list[dict[str, Any]],
        validation: dict[str, Any],
    ) -> GroundedGenerationResponse:
        """Compose the final grounded response envelope."""
        return GroundedGenerationResponse(
            query=query,
            answer=answer,
            results=[
                {
                    "entity_type": c.get("entity_type", ""),
                    "entity_id": c.get("entity_id", ""),
                    "title": c.get("title", ""),
                    "excerpt": (c.get("content", "") or "")[:300],
                    "citation": c.get("citation", ""),
                    "score": c.get("score", 0.0),
                }
                for c in chunks
            ],
            citations=[
                Citation(
                    entity_type=c.get("entity_type", ""),
                    entity_id=c.get("entity_id", ""),
                    text=c.get("citation", ""),
                )
                for c in chunks
            ],
            metadata=GenerationMetadata(
                top_k=len(chunks),
                model="citation-grounded-llm",
                citation_validation=validation,
            ),
        )

    def _refuse(self, query: str) -> GroundedGenerationResponse:
        """Build a refusal response when no evidence is available."""
        return GroundedGenerationResponse(
            query=query,
            answer=(
                "EVIDENCE_GATE_REFUSAL: 当前知识库中没有找到与您问题相关的资料。\n\n"
                f"您的问题是：{query}\n\n"
                "建议：尝试使用不同的关键词重新提问，或确认相关文献已录入平台。"
            ),
            results=[],
            citations=[],
            metadata=GenerationMetadata(
                top_k=0,
                model="citation-grounded-llm",
                citation_validation={
                    "has_citations": False,
                    "cited_chunks": [],
                    "invalid_refs": [],
                    "uncited": True,
                    "total_chunks": 0,
                    "is_valid": True,
                },
            ),
        )
