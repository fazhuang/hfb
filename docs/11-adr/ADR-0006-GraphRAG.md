---
title: "ADR-0006 GraphRAG"
version: "1.0"
status: "Accepted"
owner: "Chief Software Architect"
decision_date: "2026-06-24"
last_updated: "2026-06-24"
domain: "ai"
related:
  - "ADR-0004-Neo4j"
  - "docs/04-ai/01_RAG_GraphRAG_Architecture.md"
---

# ADR-0006: 选择 GraphRAG 作为图推理架构

---

## Status

**Accepted** — 2026-06-24

## Context

传统 RAG 只能回答"这段文本说了什么"。皇甫谧平台需要回答"谁影响了谁""这个概念怎么演变"——需要图推理。GraphRAG 结合知识图谱和图推理，回答关系型问题。需要：

- 从自然语言问题中识别实体
- 在图数据库中检索相关实体和关系
- 将推理路径转化为自然语言供 LLM 生成答案
- 可溯源到原文段落

## Decision

选择 **GraphRAG 自研 Pipeline**（不依赖现成框架）。

核心流程：NER → Entity Linking → 子图检索 → 路径排序 → LLM 生成。

## Alternatives

| 方案 | 优点 | 缺点 | 放弃原因 |
|---|---|---|---|
| 自研 Pipeline | 完全可控、可针对古籍优化、无框架约束 | 开发成本高 | — |
| Microsoft GraphRAG | 微软开源、社区热 | 偏重英文、中文古籍适配成本高、框架过重 | 不适合古籍领域 |
| LangChain Graph | LangChain 生态集成 | 抽象层过多、性能不可控、黑箱 | 不符合溯源透明性要求 |
| 纯 LLM 推理 | 无需图数据库 | 幻觉率高、无法验证推理过程、不可溯源 | 违反质量红线 |

## Consequences

### Positive

- 每一步可见、可验证、可溯源
- 可针对古籍实体和关系类型定制提示词
- 不依赖特定框架版本
- 与 Neo4j 直接通信，性能可控

### Negative

- 需要自建 NER 和 Entity Linking 模型
- 路径排序算法需持续优化
- 开发周期较长（预计 Sprint 3-4）

## Future

- V1 阶段实现基本的 1-2 hop 推理
- V2 阶段引入图算法（社区发现、中心性分析）
- 持续评估 Microsoft GraphRAG 的中文支持进展，适时评估迁移

## References

- [RAG GraphRAG Architecture](../04-ai/01_RAG_GraphRAG_Architecture.md)
- [ADR-0004 Neo4j](ADR-0004-Neo4j.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
