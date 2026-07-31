---
title: 'ADR-0003 PostgreSQL'
version: '1.0'
status: 'Accepted'
owner: 'Chief Software Architect'
decision_date: '2026-06-24'
last_updated: '2026-06-24'
domain: 'data'
related:
  - 'ADR-0004-Neo4j'
  - 'ADR-0005-Elasticsearch'
  - 'ADR-0007-Milvus'
  - 'docs/03-data/00_Data_Standard.md'
---

# ADR-0003: 选择 PostgreSQL 作为主数据库

---

## Status

**Accepted** — 2026-06-24

## Context

皇甫谧平台的核心数据是古籍文献、实体、关系。需要一个能够：

- 可靠存储结构化数据（文献、实体、版本）
- 支持 JSON 字段（实体属性多变、古典籍元数据不统一）
- 支持全文搜索（中文古文搜索）
- 支持向量扩展（为 RAG 服务，减少组件数量）
- ACID 事务（文献导入不能丢数据）

## Decision

选择 **PostgreSQL 16** 作为主数据库。关键扩展：`pg_trgm`（中文模糊搜索）、`pgvector`（初期向量存储）。

## Alternatives

| 方案        | 优点                                      | 缺点                                           | 放弃原因                       |
| ----------- | ----------------------------------------- | ---------------------------------------------- | ------------------------------ |
| PostgreSQL  | ACID、JSONB、pgvector、成熟稳定、文档丰富 | 垂直扩展为主、水平扩展需 Citus                 | —                              |
| MySQL       | 简单、查询快                              | JSON 支持弱、无向量扩展、中文全文搜索差        | 不满足 JSONB 和向量需求        |
| MongoDB     | Schema-less、灵活                         | 无 ACID 事务（文档级）、关系查询弱、无向量扩展 | 核心数据是关系型，文档型不适合 |
| CockroachDB | 分布式、兼容 PG 协议                      | 社区小、运维复杂                               | V1 不需要分布式                |

## Consequences

### Positive

- 一个数据库满足关系 + JSON + 全文 + 向量 四种需求
- JSONB 完美适配古籍元数据的不确定性
- pgvector 初期可替代专用的向量数据库，减少运维复杂度
- 成熟的备份、恢复、迁移工具链

### Negative

- pgvector 性能在大规模（>10M 向量）时逊于 Milvus — 届时切换
- 中文全文搜索需要 pg_jieba 或 zhparser 扩展
- 垂直扩展有上限

## Future

- V1 阶段 pgvector 足够的向量存储
- V2 阶段如向量量超 10M，迁移到 Milvus（见 ADR-0007）
- 关注 PostgreSQL 17+ 的原生向量支持进展

## References

- [Data Standard](../03-data/00_Data_Standard.md)
- [ADR-0004 Neo4j](ADR-0004-Neo4j.md)
- [ADR-0007 Milvus](ADR-0007-Milvus.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
