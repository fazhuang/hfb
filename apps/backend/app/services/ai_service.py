"""
AI Gateway Service — LLM access with evidence-gated structured responses.

Per HFB-PS-1705 AI Research Workspace Product Specification.

Core rule: NO evidence → refuse to answer.  Every response is wrapped in
StructuredAIResponse { answer, evidence[], citations[], graph_context[] }.
"""
from __future__ import annotations

import json
import time
from collections import deque
from typing import Any, AsyncGenerator

import httpx

from app.core.config import settings

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """Sliding-window rate limiter."""

    def __init__(self, max_per_minute: int = 20) -> None:
        self._max = max_per_minute
        self._timestamps: deque[float] = deque()

    def _prune(self) -> None:
        cutoff = time.monotonic() - 60
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def allow(self) -> bool:
        self._prune()
        if len(self._timestamps) < self._max:
            self._timestamps.append(time.monotonic())
            return True
        return False

    @property
    def remaining(self) -> int:
        self._prune()
        return self._max - len(self._timestamps)


_rate_limiter = RateLimiter(max_per_minute=settings.AI_RATE_LIMIT_PER_MINUTE)


# ---------------------------------------------------------------------------
# Evidence-gated system prompt
# ---------------------------------------------------------------------------

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
   你必须明确用以下格式拒绝回答：
   "EVIDENCE_GATE_REFUSAL: <简短说明为何无法回答>"
   不得编造、猜测或使用训练数据中的信息。

3. **引用格式**：引用时必须标注来源编号，例如 [1]、[2]，
   对应上下文中的编号。

4. **区分事实与推断**：
   - 明确指出哪些结论直接来自上下文资料
   - 明确指出哪些是合理推断
   - 明确指出哪些信息缺失或不确定

5. **回答语言**：使用中文（除非用户要求其他语言）。

你是学术辅助工具，不替代专业学术判断。"""


# ---------------------------------------------------------------------------
# AIService
# ---------------------------------------------------------------------------


class AIService:
    """AI Gateway — single entry point for all LLM interactions."""

    def __init__(self) -> None:
        self._provider = settings.AI_PROVIDER
        self._api_key = settings.AI_API_KEY
        self._model = settings.AI_MODEL
        self._base_url = settings.AI_BASE_URL or (
            "https://api.openai.com/v1"
            if self._provider in ("openai", "local")
            else "https://api.anthropic.com/v1"
        )
        self._max_tokens = settings.AI_MAX_TOKENS
        self._temperature = settings.AI_TEMPERATURE

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def check_rate_limit(self) -> bool:
        return _rate_limiter.allow()

    @property
    def rate_limit_remaining(self) -> int:
        return _rate_limiter.remaining

    # ------------------------------------------------------------------
    # Chat (streaming — now evidence-gated)
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        context: str = "",
        model: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming AI chat with evidence-gated system prompt.

        If context is empty, yields a refusal marker instead of calling the LLM.
        """
        if not self.available:
            yield "EVIDENCE_GATE_UNAVAILABLE"
            return

        if not self.check_rate_limit():
            yield "EVIDENCE_GATE_RATE_LIMITED"
            return

        # Evidence gate: refuse if no context provided
        if not context.strip():
            yield "EVIDENCE_GATE_REFUSAL: 当前知识库中没有找到与您问题相关的资料。"
            return

        full_messages = [
            {"role": "system", "content": EVIDENCE_GATED_SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"研究上下文（引用时请标注编号 [N]）：\n{context}",
            },
        ]
        full_messages.extend(messages)

        async for chunk in self._stream_openai(full_messages, model or self._model):
            yield chunk

        # Append AI marker for academic integrity
        yield "\n\n---\n*🤖 AI 生成内容，请以学术标准核实*"

    async def _stream_openai(
        self, messages: list[dict[str, str]], model: str
    ) -> AsyncGenerator[str, None]:
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    yield f"⚠️ AI 服务错误 (HTTP {resp.status_code}): {body.decode()[:200]}"
                    return

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    # ------------------------------------------------------------------
    # Summarize
    # ------------------------------------------------------------------

    async def summarize(self, text: str, max_words: int = 200) -> str:
        if not self.available:
            return _mock_summarize(text, max_words)
        if not self.check_rate_limit():
            return "⚠️ 请求过于频繁"

        messages = [
            {"role": "user", "content": f"请用不超过{max_words}字概括以下文本的核心内容：\n\n{text}"},
        ]
        return await self._complete(messages)

    # ------------------------------------------------------------------
    # Translate
    # ------------------------------------------------------------------

    async def translate(self, text: str, target_lang: str = "现代汉语") -> str:
        if not self.available:
            return _mock_translate(text, target_lang)
        if not self.check_rate_limit():
            return "⚠️ 请求过于频繁"

        messages = [
            {"role": "user", "content": f"请将以下文言文翻译为{target_lang}，保留原文的学术术语和结构：\n\n{text}"},
        ]
        return await self._complete(messages)

    # ------------------------------------------------------------------
    # AI Compare
    # ------------------------------------------------------------------

    async def ai_compare(
        self, source_text: str, target_text: str, source_label: str = "源版本", target_label: str = "目标版本"
    ) -> str:
        if not self.available:
            return _mock_compare(source_text, target_text, source_label, target_label)
        if not self.check_rate_limit():
            return "⚠️ 请求过于频繁"

        messages = [
            {
                "role": "user",
                "content": (
                    f"请比较以下两个版本的文本差异，从学术角度分析差异的性质（异文、衍文、脱文、倒文等），"
                    f"并评估差异对文意的影响。\n\n"
                    f"【{source_label}】\n{source_text}\n\n"
                    f"【{target_label}】\n{target_text}"
                ),
            },
        ]
        return await self._complete(messages)

    # ------------------------------------------------------------------
    # Non-streaming completion (legacy)
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> str:
        """Non-streaming completion with optional custom system prompt.

        temperature=0 for deterministic generation.
        seed sets OpenAI-compatible seed for reproducible outputs.
        """
        prompt = system_prompt or EVIDENCE_GATED_SYSTEM_PROMPT
        full_messages = [{"role": "system", "content": prompt}, *messages]
        return await self._call_api(full_messages, temperature=temperature, seed=seed)

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> str | None:
        """Non-streaming completion for structured LLM output (claims JSON).

        Does NOT append AI marker text. Returns None on provider error.
        Used by GenerationPipeline for strict grounded generation.
        """
        prompt = system_prompt or EVIDENCE_GATED_SYSTEM_PROMPT
        full_messages = [{"role": "system", "content": prompt}, *messages]

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": full_messages,
            "max_tokens": self._max_tokens,
            "temperature": temperature if temperature is not None else self._temperature,
            "stream": False,
        }
        if seed is not None:
            payload["seed"] = seed

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    return None
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if not content or not content.strip():
                    return None
                return content.strip()
        except Exception:
            return None

    async def _complete(self, messages: list[dict[str, str]]) -> str:
        """Legacy wrapper — uses the hardcoded evidence-gated prompt."""
        return await self.complete(messages)

    async def _call_api(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        seed: int | None = None,
    ) -> str:
        """Raw API call — no prompt injection."""

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": temperature if temperature is not None else self._temperature,
            "stream": False,
        }
        if seed is not None:
            payload["seed"] = seed

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                return f"⚠️ AI 服务错误 (HTTP {resp.status_code})"
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            # ponytail: AI marker is metadata on the response envelope, not in the text
            return content + "\n\n---\n*🤖 AI 生成内容*"


# ---------------------------------------------------------------------------
# Mock fallbacks
# ---------------------------------------------------------------------------


def _mock_summarize(text: str, max_words: int) -> str:
    preview = text[:max_words // 2] + ("…" if len(text) > max_words // 2 else "")
    return f"[摘要] {preview}\n\n---\n*🤖 AI 服务未配置，以上为文本截取*"


def _mock_translate(text: str, target_lang: str) -> str:
    return f"[翻译至{target_lang}] {text[:200]}{'…' if len(text) > 200 else ''}\n\n---\n*🤖 AI 服务未配置，以上为原文截取*"


def _mock_compare(source_text: str, target_text: str, src_label: str, tgt_label: str) -> str:
    from difflib import SequenceMatcher

    sm = SequenceMatcher(None, source_text, target_text)
    ratio = sm.ratio()
    changes = 0
    report = [
        f"【{src_label}】与【{tgt_label}】文字相似度: {ratio:.1%}",
        f"【{src_label}】共 {len(source_text)} 字",
        f"【{tgt_label}】共 {len(target_text)} 字",
    ]
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            report.append(f"  - 替换: 「{source_text[i1:i2]}」→「{target_text[j1:j2]}」")
            changes += 1
        elif tag == "delete":
            report.append(f"  - 删除: 「{source_text[i1:i2]}」")
            changes += 1
        elif tag == "insert":
            report.append(f"  - 新增: 「{target_text[j1:j2]}」")
            changes += 1

    report.append(f"共发现 {changes} 处差异")
    report.append("\n---\n*🤖 AI 服务未配置，以上为自动文字比对*")
    return "\n".join(report)
