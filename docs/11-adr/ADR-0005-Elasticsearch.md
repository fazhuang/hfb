---
title: 'ADR-0005 Elasticsearch'
version: '1.0'
status: 'Accepted'
owner: 'Chief Software Architect'
decision_date: '2026-06-24'
last_updated: '2026-06-24'
domain: 'data'
related:
  - 'ADR-0003-PostgreSQL'
  - 'docs/03-data/00_Data_Standard.md'
---

# ADR-0005: 选择 Elasticsearch 作为搜索引擎

---

## Status

**Accepted** — 2026-06-24

## Context

古籍中文文本需要高效的全文搜索，特别是：

- 文言文 + 现代翻译混合搜索
- 模糊匹配（异体字、通假字）
- 按文献、版本、章节范围过滤
- 高亮显示搜索结果

PostgreSQL 全文搜索对中文支持弱，需要专门的搜索引擎。

## Decision

选择 **Elasticsearch 8** + IK 中文分词器作为搜索引擎。

## Alternatives

| 方案                | 优点                                     | 缺点                       | 放弃原因                 |
| ------------------- | ---------------------------------------- | -------------------------- | ------------------------ |
| Elasticsearch       | 成熟、生态丰富、中文分词插件、高亮、聚合 | 内存消耗大、运维复杂       | —                        |
| MeiliSearch         | 轻量、易部署、中文支持好                 | 社区小、高级查询能力弱     | 缺少模糊搜索和聚合深度   |
| Typesense           | 速度快、即时搜索                         | 中文分词不如 ES、社区更小  | 不满足文言文搜索精度要求 |
| PostgreSQL 全文搜索 | 无需额外部署                             | 中文支持极弱、无相关性调优 | 不满足核心搜索需求       |

## Consequences

### Positive

- IK 分词器对中文支持成熟
- 高亮和相关性排序开箱即用
- REST API 可与 FastAPI 直接集成
- 聚合查询方便文献统计

### Negative

- 内存消耗大（建议 2GB+ heap）
- 索引更新逻辑需自建（PostgreSQL → ES 同步）
- 运维复杂度增加一个组件
- 文言文分词准确度需定制词典

## Future

- 索引同步通过应用层事件驱动（POST/PUT/DELETE → 更新 ES）
- 建立文言文医学专属词典，提升分词精度
- V2 阶段评估是否可降级为 PostgreSQL 内置搜索（若 ES 运维成本过高）

## References

- [Data Standard](../03-data/00_Data_Standard.md)
- [Development Specification](../05-development/00_Development_Specification.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
