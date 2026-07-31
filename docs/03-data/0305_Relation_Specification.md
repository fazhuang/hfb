---
title: Relation Specification
document_id: HFB-DAT-0305
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Knowledge Layer / Graph Layer / AI Layer
priority: P0
related_documents:
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0304 Entity Specification
  - HFB-ARC-0201 Technical Blueprint
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-AI-0402 RAG Specification
---

# Relation Specification

## 关系规范

> 本文档定义平台所有实体之间关系（Relation）的统一标准。
>
> 所有数据库关联、知识图谱边（Edge）、RAG 引用链、GraphRAG 推理路径、AI 引用关系均必须遵循本规范。

---

# 第一章 编制目标

建立统一关系模型，实现：

- 数据关系统一；
- 知识图谱统一；
- AI 推理统一；
- 学术引用统一；
- 多版本关联统一；
- 后续扩展保持兼容。

---

# 第二章 Relation 定义

Relation 是两个 Entity 之间具有明确语义的连接。

每一个 Relation 必须满足：

- 有起点（Source Entity）
- 有终点（Target Entity）
- 有关系类型（Relation Type）
- 有证据（Evidence）
- 有可信度（Confidence）
- 有创建记录（Audit）

缺少任一项，不允许成为正式关系。

---

# 第三章 Relation 基本结构

所有 Relation 必须具有以下字段：

| 字段          | 类型     | 必填 |
| ------------- | -------- | ---- |
| id            | UUID     | √    |
| relation_type | String   | √    |
| source_entity | UUID     | √    |
| target_entity | UUID     | √    |
| evidence_id   | UUID     | √    |
| confidence    | Decimal  | √    |
| status        | Enum     | √    |
| created_at    | Datetime | √    |
| created_by    | UUID     |      |
| reviewed_by   | UUID     |      |
| version       | Integer  | √    |

---

# 第四章 Relation 分类

平台关系划分为六类。

## 4.1 创作关系（Creation）

包括：

- authored_by
- edited_by
- translated_by
- compiled_by
- annotated_by

例如：

皇甫谧

↓

authored_by

↓

《针灸甲乙经》

---

## 4.2 结构关系（Structure）

包括：

- belongs_to
- contains
- consists_of

例如：

Chapter

↓

belongs_to

↓

Book

---

## 4.3 学术关系（Academic）

包括：

- cites
- comments_on
- references
- studies
- critiques

例如：

论文

↓

studies

↓

皇甫谧

---

## 4.4 历史关系（Historical）

包括：

- occurred_in
- lived_in
- published_in
- inherited_from

例如：

版本

↓

inherits

↓

版本

---

## 4.5 地理关系（Spatial）

包括：

- located_in
- originated_from
- discovered_at

---

## 4.6 语义关系（Semantic）

包括：

- related_to
- equivalent_to
- influences
- derived_from

主要用于知识图谱和 AI 推理。

---

# 第五章 Relation 生命周期

统一生命周期：

```text
Draft

↓

Verified

↓

Published

↓

Deprecated

↓

Archived
```

任何 AI 自动生成关系必须处于 Draft 状态。

---

# 第六章 Evidence（证据）

所有 Relation 必须绑定至少一条 Evidence。

Evidence 来源允许：

- 古籍原文
- 学术论文
- 地方志
- 图片
- 档案
- 数据库
- 人工标注

AI 推理结果不能作为唯一证据。

---

# 第七章 Confidence（可信度）

统一评分：

| 分值       | 等级      |
| ---------- | --------- |
| ≥0.95      | High      |
| 0.80～0.94 | Medium    |
| 0.60～0.79 | Low       |
| <0.60      | Candidate |

Candidate 不允许进入正式知识库。

---

# 第八章 多证据支持

一个 Relation 可以绑定多个 Evidence。

例如：

```
Relation

↓

Evidence A（古籍）

↓

Evidence B（论文）

↓

Evidence C（碑刻）
```

Evidence 越多，可信度越高。

---

# 第九章 多版本关系

Relation 必须支持版本。

例如：

《针灸甲乙经》

宋刻本

↓

Version Relation

↓

明刻本

↓

人民卫生出版社版

版本之间关系不得丢失。

---

# 第十章 Relation 与数据库

数据库中：

Relation 独立建模。

禁止：

在 Entity 表中保存复杂关系。

例如：

禁止：

Book.author_id

推荐：

Relation：

Person

↓

authored_by

↓

Book

---

# 第十一章 Relation 与知识图谱

Graph 中：

Relation 对应：

Edge。

统一：

Edge ID = Relation UUID。

禁止：

Graph 独立生成新的关系编号。

---

# 第十二章 Relation 与 AI

AI：

只能使用：

正式 Published Relation。

AI 新发现关系：

进入：

Candidate Relation。

必须：

人工审核。

通过后：

进入正式 Relation。

---

# 第十三章 Relation 与 RAG

RAG：

利用 Relation：

扩展检索。

例如：

人物

↓

著作

↓

章节

↓

论文

↓

图片

形成：

Evidence Chain。

---

# 第十四章 Relation 与 GraphRAG

GraphRAG：

只能推理：

Ontology 中已定义的 Relation。

禁止：

AI 自行创造新的 Relation Type。

新增关系必须：

更新：

Ontology

Relation Specification

Context Package

Prompt Library

---

# 第十五章 Relation 审计

所有 Relation 必须记录：

- 创建人
- 创建时间
- 审核人
- 审核时间
- 修改历史
- Evidence 变更历史

任何修改均可追溯。

---

# 第十六章 变更流程

新增 Relation Type 必须完成：

1. 更新 Ontology；
2. 更新 Relation Specification；
3. 更新数据库；
4. 更新 Graph Schema；
5. 更新 API；
6. 更新 AI 检索配置；
7. 更新 Context Package。

未经批准不得新增。

---

# 第十七章 成功标准

平台所有：

数据库关联

Graph Edge

AI 推理链

RAG 引用链

GraphRAG 推理路径

均必须来源于统一 Relation 定义。

Relation Specification 是平台唯一关系标准。

---

# 修订记录

| Version | Date       | Description                      |
| ------- | ---------- | -------------------------------- |
| 1.1.0   | 2026-06-25 | 更新related_documents            |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台统一关系规范。 |
