---
title: 'ADR-0007 Milvus'
version: '1.0'
status: 'Accepted'
owner: 'Chief Software Architect'
decision_date: '2026-06-24'
last_updated: '2026-06-24'
domain: 'ai'
related:
  - 'ADR-0003-PostgreSQL'
  - 'docs/04-ai/01_RAG_GraphRAG_Architecture.md'
---

# ADR-0007: 选择 Milvus 作为向量数据库

---

## Status

**Accepted** — 2026-06-24

## Context

RAG 流水线的核心是向量检索。需要一个向量数据库来存储古籍段落的 Embedding 向量，并支持高效的相似度检索。需要：

- 支持百万级以上向量（长期目标百万段落）
- 支持混合检索（向量相似度 + 标量过滤：按文献、版本、章节）
- 与 Python AI 生态集成

## Decision

选择 **pgvector (V1) → Milvus (V2)** 的两阶段策略。

- V1 阶段：使用 pgvector（PostgreSQL 扩展），向量量 < 100K
- V2 阶段：向量量增长后迁移到 Milvus

## Alternatives

| 方案     | 优点                                      | 缺点                          | 选择时机 |
| -------- | ----------------------------------------- | ----------------------------- | -------- |
| pgvector | 零额外部署、PostgreSQL 原生、足够 V1 使用 | 性能 < 1M 向量、缺少高级索引  | V1 阶段  |
| Milvus   | 性能优秀、混合检索、分布式、10M+ 向量     | 需要独立部署、运维复杂        | V2 阶段  |
| Qdrant   | Rust 实现、性能好、API 优雅               | 社区规模、生产案例少于 Milvus | 备选     |
| Weaviate | GraphQL API、自动向量化                   | 中文 Embedding 适配差、社区小 | 不选     |

## Consequences

### Positive

- V1 阶段降低架构复杂度（PostgreSQL 一站式）
- V2 切换路径清晰（pgvector 数据可导出 → Milvus 导入）
- Milvus 中文生态友好（中国开源社区活跃）

### Negative

- 两阶段策略意味着未来有数据迁移成本
- pgvector 性能在大规模时是瓶颈 — V2 必须按时迁移

## Future

- V1 阶段上限：100K 向量，pgvector 足够
- V2 阶段：>100K 向量时迁移到 Milvus Standalone
- 迁移策略：pgvector 导出 → 脚本转换 → Milvus 导入 → 验证 → 切换

## References

- [RAG GraphRAG Architecture](../04-ai/01_RAG_GraphRAG_Architecture.md)
- [ADR-0003 PostgreSQL](ADR-0003-PostgreSQL.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
