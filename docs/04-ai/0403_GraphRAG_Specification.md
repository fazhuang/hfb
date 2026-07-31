---
title: GraphRAG Specification
document_id: HFB-AI-0403
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: AI Knowledge Retrieval Layer
priority: P1
related_documents:
  - HFB-AI-0401 AI Engineering Standard
  - HFB-AI-0402 RAG Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# GraphRAG Specification

## GraphRAG 技术规范

> 本文档定义平台第二代 AI 检索架构——GraphRAG（Graph Retrieval-Augmented Generation）。
>
> GraphRAG 建立在 RAG、Ontology、Entity、Relation 四大基础之上，为复杂学术研究、多跳推理、知识发现提供统一技术规范。

> **注意：本规范属于架构规划文档。GraphRAG 不属于 MVP，不得在基础平台未完成前提前开发。**

---

# 第一章 建设目标

GraphRAG 的目标不是替代 RAG。

而是解决 RAG 无法解决的问题：

- 多跳知识推理
- 人物关系网络
- 文献引用网络
- 多版本演化分析
- 学术传播路径分析
- 知识发现

---

# 第二章 GraphRAG 定位

平台 AI 架构分三层：

```text
Keyword Search

↓

RAG

↓

GraphRAG
```

说明：

Keyword Search

负责：

全文检索。

RAG

负责：

语义检索。

GraphRAG

负责：

知识推理。

三者：

长期共存。

---

# 第三章 Graph 数据来源

Graph 不允许人工维护。

Graph 只能来源于：

Ontology

↓

Entity

↓

Relation

↓

Evidence

↓

Graph

Graph 是知识层的映射。

不是：

业务数据库。

---

# 第四章 Graph Node

所有 Node：

来源于：

Entity。

Node ID：

统一：

Entity UUID。

支持：

- Person
- Book
- Version
- Chapter
- Passage
- Paper
- Institution
- Place
- Event
- Image

不得建立：

匿名 Node。

---

# 第五章 Graph Edge

所有 Edge：

来源于：

Relation。

Edge ID：

统一：

Relation UUID。

支持：

- authored_by
- belongs_to
- studies
- cites
- comments_on
- translated_by
- influences
- related_to

新增 Edge：

必须：

更新：

Ontology。

---

# 第六章 Evidence Layer

Graph 中：

任何 Edge

必须拥有：

Evidence。

Evidence 可以是：

- 古籍
- 论文
- 图片
- 档案
- 地方志
- 人工审核记录

禁止：

AI 推理结果直接成为正式 Evidence。

---

# 第七章 Graph Construction

Graph 建设流程：

```text
Metadata

↓

Ontology

↓

Entity

↓

Relation

↓

Evidence

↓

Graph Build

↓

Validation

↓

Publish
```

任何 Graph：

不得绕过 Validation。

---

# 第八章 Graph Retrieval

GraphRAG：

采用：

Entity First。

流程：

```text
Question

↓

Entity Recognition

↓

Relation Expansion

↓

Subgraph Retrieval

↓

Evidence Ranking

↓

Context Builder

↓

LLM
```

Graph 不直接生成答案。

---

# 第九章 Multi-hop 推理

GraphRAG：

支持：

2~6 跳。

例如：

皇甫谧

↓

著作

↓

章节

↓

论文

↓

研究者

↓

研究机构

形成：

完整推理链。

---

# 第十章 Citation

GraphRAG：

所有回答：

必须返回：

完整推理路径。

例如：

```text
皇甫谧

↓

《针灸甲乙经》

↓

卷三

↓

第十二节

↓

论文A

↓

研究观点B
```

禁止：

隐藏推理过程。

---

# 第十一章 Explainability

GraphRAG：

必须支持：

Explain。

包括：

- Node 来源
- Relation 来源
- Evidence 来源
- Ranking 原因
- Prompt Version
- Model Version

任何回答：

均可追溯。

---

# 第十二章 图数据库

图数据库属于实现细节。

本规范不绑定具体产品。

允许：

- Neo4j
- Memgraph
- NebulaGraph
- ArangoDB

最终采用何种产品，由 ADR 决定。

不得在规范中写死厂商。

---

# 第十三章 Graph 更新

Graph 更新：

统一：

增量更新。

流程：

新增 Entity

↓

新增 Relation

↓

Validation

↓

Graph Merge

↓

Rebuild Index

禁止：

全量重建。

---

# 第十四章 Graph Quality

要求：

| 指标              | 标准 |
| ----------------- | ---- |
| 孤立 Node         | <1%  |
| 无 Evidence Edge  | 0    |
| 重复 Node         | 0    |
| 重复 Edge         | 0    |
| Citation Accuracy | ≥99% |

---

# 第十五章 Graph Security

Graph：

必须支持：

- 权限控制
- 查询审计
- 敏感关系过滤
- AI 调用日志
- 推理记录保存

禁止：

开放全部 Graph。

---

# 第十六章 Roadmap

GraphRAG：

进入条件：

- Ontology 完成
- Entity 完成
- Relation 完成
- Metadata 完成
- RAG 稳定

满足以上条件后：

方可进入 GraphRAG Sprint。

---

# 第十七章 GraphRAG 红线

禁止：

- Graph 独立维护
- 无 Evidence Edge
- AI 自创建 Node
- AI 自创建 Relation
- 无审计推理
- 无引用回答

违反任一项不得上线。

---

# 第十八章 修订规则

新增：

Graph Schema

Edge Type

Traversal Strategy

Ranking

必须同步更新：

- AI Engineering Standard
- Ontology Specification
- Relation Specification
- ADR
- Context Package

---

# 修订记录

| Version | Date       | Description                                |
| ------- | ---------- | ------------------------------------------ |
| 1.1.0   | 2026-06-25 | 更新related_documents；明确MVP阶段禁止引入 |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台 GraphRAG 技术规范。     |
