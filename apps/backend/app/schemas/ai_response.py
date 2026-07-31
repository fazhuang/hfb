"""
Structured AI Response — answer + evidence[] + citations[] + graph_context[].

Replaces raw text streaming with a JSON envelope that the frontend renders
as a structured research card.  When no evidence is available the assistant
MUST refuse to answer ("evidence-gated").
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ============================================================
# Structured response schema
# ============================================================


class EvidenceItem(BaseModel):
    """One piece of retrieved evidence that supports the answer."""

    entity_type: str  # person, book, version, passage, paper
    entity_id: str
    title: str  # display name
    excerpt: str  # matching text excerpt (≤300 chars)
    citation: str  # human-readable citation string
    score: float = 0.0  # retrieval relevance score


class Citation(BaseModel):
    """A formal citation to a platform entity."""

    entity_type: str
    entity_id: str
    text: str  #  "《针灸甲乙经》卷三·北宋刻本"


class GraphContext(BaseModel):
    """A node + its 1-hop neighbors from the knowledge graph."""

    center: dict[str, Any]  # {id, entity_type, label}
    neighbors: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class StructuredAIResponse(BaseModel):
    """The canonical structured AI answer envelope."""

    answer: str  # natural-language answer (Markdown)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    graph_context: list[GraphContext] = Field(default_factory=list)
    ai_generated: bool = True


# ============================================================
# Evidence-gated prompt template
# ============================================================


EVIDENCE_GATED_SYSTEM_PROMPT = """你是皇甫谧数字人文平台（Huangfu Mi Digital Humanities Platform）的AI研究助手。
你的知识领域包括：
- 中国古代医学文献（《针灸甲乙经》《伤寒杂病论》《本草纲目》等）
- 中医经典文本的版本校勘与训诂
- 中国古代医学史、中医人物
- 数字人文研究方法

**核心规则：Evidence-Gated 回答**

你必须遵循以下严格规则：

1. **有证据才能回答**：你必须基于系统提供的「研究上下文」中的资料来回答。
   上下文中包含了平台检索到的相关文献、人物、版本、条文。
   每条上下文都标注了出处（citation）。

2. **无证据则拒答**：如果上下文中没有任何资料与用户问题相关，
   你必须明确拒绝回答，说：
   「抱歉，当前知识库中没有找到与您问题相关的资料，无法提供有依据的回答。」
   不得编造、猜测或使用训练数据中的信息。

3. **引用格式**：引用时必须标注来源编号，例如 [1]、[2]，
   对应上下文中的编号。

4. **区分事实与推断**：
   - 明确指出哪些结论直接来自上下文资料
   - 明确指出哪些是合理推断
   - 明确指出哪些信息缺失或不确定

5. **回答语言**：使用中文（除非用户要求其他语言）。

你是学术辅助工具，不替代专业学术判断。"""


# ============================================================
# Structured Response Builder
# ============================================================


class StructuredResponseBuilder:
    """Builds a StructuredAIResponse from RAG chunks + LLM output.

    Used by the chat endpoint to assemble the final structured envelope
    regardless of whether the LLM is available (real) or not (mock).
    """

    @staticmethod
    def build(
        answer_text: str,
        rag_chunks: list[dict[str, Any]],
    ) -> StructuredAIResponse:
        """Convert raw RAG chunks + answer into structured response."""
        evidence: list[EvidenceItem] = []
        citations: list[Citation] = []

        for chunk in rag_chunks:
            entity_type = chunk.get("entity_type", "")
            entity_id = chunk.get("entity_id", "")
            title = chunk.get("title", "")
            content = chunk.get("content", "")
            citation_text = chunk.get("citation", "")
            score = chunk.get("score", 0.0)

            if not content:
                continue

            evidence.append(
                EvidenceItem(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=title,
                    excerpt=content[:300],
                    citation=citation_text,
                    score=score,
                )
            )

            citations.append(
                Citation(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    text=citation_text,
                )
            )

        # Build graph context from evidence entities
        graph_context: list[GraphContext] = []
        seen_ids: set[str] = set()
        for ev in evidence:
            if ev.entity_id in seen_ids:
                continue
            seen_ids.add(ev.entity_id)
            graph_context.append(
                GraphContext(
                    center={
                        "id": ev.entity_id,
                        "entity_type": ev.entity_type,
                        "label": ev.title,
                    },
                    neighbors=[],
                    edges=[],
                )
            )

        return StructuredAIResponse(
            answer=answer_text,
            evidence=evidence,
            citations=citations,
            graph_context=graph_context,
        )

    @staticmethod
    def refuse(query: str) -> StructuredAIResponse:
        """Build a refusal response when no evidence is available."""
        return StructuredAIResponse(
            answer=(
                "抱歉，当前知识库中没有找到与您问题相关的资料，无法提供有依据的回答。\n\n"
                f"您的问题是：{query}\n\n"
                "建议：\n"
                "- 尝试使用不同的关键词重新提问\n"
                "- 确认相关的古籍、人物或版本是否已录入平台\n"
                "- 联系平台管理员补充数据"
            ),
            evidence=[],
            citations=[],
            graph_context=[],
        )

    @staticmethod
    def unavailable() -> StructuredAIResponse:
        """Build a response when AI service is not configured."""
        return StructuredAIResponse(
            answer="⚠️ AI 服务未配置。请设置 AI_API_KEY 环境变量以启用 AI 研究助手。",
            evidence=[],
            citations=[],
            graph_context=[],
        )
