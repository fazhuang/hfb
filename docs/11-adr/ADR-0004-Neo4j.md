---
title: 'ADR-0004 Neo4j'
version: '1.0'
status: 'Accepted'
owner: 'Chief Software Architect'
decision_date: '2026-06-24'
last_updated: '2026-06-24'
domain: 'data'
related:
  - 'ADR-0003-PostgreSQL'
  - 'ADR-0006-GraphRAG'
  - 'docs/03-data/01_Ontology_Specification.md'
---

# ADR-0004: 选择 Neo4j 作为图数据库

---

## Status

**Accepted** — 2026-06-24

## Context

皇甫谧平台的核心价值之一是"实体关系推理"：人物之间的师承关系、文献之间的引用关系、地点的隶属关系。图数据库是完成此类查询的最自然方式。需要：

- 高效的 2-3 hop 图遍历
- 支持图算法（最短路径、社区发现）
- 支持属性图模型（实体带属性）
- 与 Python 生态集成良好

## Decision

选择 **Neo4j 5 Community Edition** 作为图数据库。

图数据是派生索引 —— 可以通过 PostgreSQL 中的实体和关系表重新构建。

## Alternatives

| 方案       | 优点                                                      | 缺点                               | 放弃原因             |
| ---------- | --------------------------------------------------------- | ---------------------------------- | -------------------- |
| Neo4j      | 最成熟的图数据库、Cypher 查询直观、社区版免费、图算法丰富 | 需要单独的运维、垂直扩展有限       | —                    |
| Apache Age | PostgreSQL 扩展，无需额外部署                             | 社区小、稳定性不如 Neo4j、图算法少 | 不适合生产级的图推理 |
| ArangoDB   | 多模型（文档+图）、单数据库                               | 图查询性能逊于 Neo4j、社区中等     | 图推理性能不如 Neo4j |
| 自研图引擎 | 完全可控                                                  | 重复造轮子、维护成本高             | V1 阶段不造轮子      |

## Consequences

### Positive

- Cypher 查询语言直观、适合表达人文领域的关系查询
- 图算法库（GDS）支持社区发现、中心性分析等人文研究常用算法
- 成熟的 Python 驱动（neo4j-driver）
- 可视化工具（Neo4j Browser）可作为内部调试工具

### Negative

- 需要独立部署和运维，增加架构复杂度
- Community Edition 缺少集群和高可用
- 图数据同步逻辑（从 PostgreSQL → Neo4j）需自建

## Future

- V1 阶段 Neo4j Community 单节点足够（实体量 < 100K）
- V2 阶段如需要高可用，升级到 Enterprise 或评估分布式图数据库
- 关注 Neo4j 5+ 的向量搜索集成（可能减少 Milvus 需求）

## References

- [Ontology Specification](../03-data/01_Ontology_Specification.md)
- [ADR-0006 GraphRAG](ADR-0006-GraphRAG.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
