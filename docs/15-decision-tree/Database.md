---
title: 'Decision Tree — Database'
version: '1.0'
status: 'Accepted'
owner: 'Chief Software Architect'
last_updated: '2026-06-24'
related_adr: ['ADR-0003', 'ADR-0004', 'ADR-0005', 'ADR-0007']
---

# Decision Tree — Database

为什么需要四个数据库，而不是一个。

---

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
graph TD
  Q1["古籍数据需要什么存储？"]
  Q1 -->|"结构化实体\nACID 事务"| DB1["PostgreSQL ✅\n主数据库"]
  Q1 -->|"文档灵活"| DBX["MongoDB ❌\n核心数据是关系型"]

  Q2["向量检索\nEmbedding 存在哪？"]
  Q2 -->|"V1 少组件"| DB2["pgvector ✅\n和 PG 在一起"]
  Q2 -->|"独立引擎"| DB2X["Milvus → V2 ⏸️\nV1 不需要"]

  Q3["实体关系推理\n图遍历需求？"]
  Q3 -->|"Cypher 查询\n图算法"| DB3["Neo4j ✅\n专业图数据库"]
  Q3 -->|"PG 扩展"| DB3X["Apache Age ❌\n不够成熟"]

  Q4["全文搜索\n文言文？"]
  Q4 -->|"IK 分词\n高亮"| DB4["Elasticsearch ✅"]
  Q4 -->|"PG 内置"| DB4X["PostgreSQL FTS ❌\n中文支持弱"]
```

## 决策路径

1. 主数据库必须是关系型 → PostgreSQL（ACID + JSONB + pgvector）
2. 向量存储 V1 不引入新组件 → pgvector
3. 图查询需求明确 → Neo4j（Cypher 直观 + 图算法）
4. 中文全文搜索 PG 不够 → Elasticsearch + IK 分词

## 相关 ADR

- ADR-0003 PostgreSQL
- ADR-0004 Neo4j
- ADR-0005 Elasticsearch
- ADR-0007 Milvus

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
