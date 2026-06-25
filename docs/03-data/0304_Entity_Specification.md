---
title: Entity Specification
document_id: HFB-DAT-0304
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Knowledge Layer / Database Layer
priority: P0
related_documents:
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0303 Metadata Standard
  - HFB-ARC-0201 Technical Blueprint
  - HFB-PS-1709 MVP Implementation Specification
---

# Entity Specification
## 实体规范

> 本文档定义平台所有实体（Entity）的统一规范。
>
> 所有数据库表、知识图谱节点（Node）、API 数据对象、RAG 索引对象、GraphRAG 实体以及 AI 识别对象，均必须遵循本规范。

---

# 第一章 编制目标

建立统一的实体模型，实现：

- 数据模型统一；
- 数据库与知识图谱一致；
- AI 可识别；
- 多版本资源统一关联；
- 长期可扩展。

---

# 第二章 Entity 定义

Entity（实体）是平台中具有独立身份、独立属性、可持续存在并可被引用的对象。

实体必须具备以下四个特征：

1. 唯一身份（Identity）
2. 独立属性（Attributes）
3. 生命周期（Lifecycle）
4. 可建立关系（Relations）

以下对象不是实体：

- 标签（Tag）
- 关键词（Keyword）
- 排序值（Sort Order）
- 临时查询结果
- AI 推理中间结果

---

# 第三章 实体分类

平台实体划分为四级。

## 一级实体（Core Entity）

平台核心研究对象。

包括：

| 实体 | 说明 |
|------|------|
| Person | 人物 |
| Book | 古籍 |
| Version | 版本 |
| Chapter | 章节 |
| Passage | 段落 |
| Paper | 学术论文 |
| Image | 图片 |
| Institution | 机构 |
| Place | 地点 |
| Event | 历史事件 |
| Dynasty | 朝代 |
| Document | 综合资源 |

---

## 二级实体（Supporting Entity）

辅助研究对象。

包括：

- Publisher
- Collection
- Journal
- Conference
- Project
- Organization
- Archive

---

## 三级实体（System Entity）

系统运行实体。

包括：

- User
- Role
- Permission
- Attachment
- Task
- AuditLog

---

## 四级实体（Future Entity）

未来扩展实体。

包括：

- Disease
- Formula
- Herb
- Acupoint
- Meridian
- Symptom
- Treatment

**不得进入 MVP。**

MVP 阶段实体边界以 [HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) 为准。四级实体均为 Post-MVP 扩展。

---

# 第四章 Entity 唯一标识

所有实体必须采用：

UUID v7（推荐）

统一字段：

```text
id
```

不得使用：

- 自增 ID
- 中文名称
- 拼音
- 业务编号

作为唯一标识。

---

# 第五章 Entity 公共属性

所有实体必须继承以下基础字段。

| 字段 | 类型 | 必填 |
|------|------|------|
| id | UUID | √ |
| entity_type | String | √ |
| title | String | √ |
| description | Text | |
| status | Enum | √ |
| created_at | Datetime | √ |
| updated_at | Datetime | √ |
| created_by | UUID | |
| updated_by | UUID | |
| version | Integer | √ |
| source_id | UUID | |
| metadata_id | UUID | |

不得删除上述字段。

---

# 第六章 生命周期

统一生命周期：

```text
Draft

↓

Review

↓

Published

↓

Archived

↓

Deprecated
```

不得跳过 Review。

---

# 第七章 Entity 命名规范

数据库：

snake_case

Python：

PascalCase

TypeScript：

PascalCase

JSON：

camelCase

API：

kebab-case

显示名称：

支持多语言。

---

# 第八章 实体唯一约束

平台建立三层唯一约束。

## 第一层

UUID 唯一。

---

## 第二层

同一类型：

名称 + 来源

唯一。

---

## 第三层

通过：

Ontology

进行重复识别。

例如：

皇甫谧

皇甫士安

Huangfu Mi

属于：

同一实体。

---

# 第九章 Entity 继承体系

```text
BaseEntity
      │
      ▼
KnowledgeEntity
      │
      ├── Person
      ├── Book
      ├── Paper
      ├── Image
      ├── Event
      └── Place

SystemEntity
      │
      ├── User
      ├── Role
      ├── Permission
      └── AuditLog
```

统一继承。

禁止重复设计公共字段。

---

# 第十章 Entity 与 Metadata

每个 Entity：

必须关联：

Metadata。

关系：

```text
Entity

1

↓

1

Metadata
```

禁止孤立 Entity。

---

# 第十一章 Entity 与 Version

支持：

一个实体多个版本。

例如：

《针灸甲乙经》

↓

宋刻本

↓

明刻本

↓

人民卫生出版社版

所有 Version：

共享同一个 Book。

---

# 第十二章 Entity 与 Relation

Entity 不直接保存复杂关系。

所有关系：

统一进入：

Relation。

例如：

```text
Person

↓

authored

↓

Book
```

而不是：

Book.author_id。

复杂关系全部进入知识层。

---

# 第十三章 Entity 与数据库

所有 Entity：

最终映射：

Database Table。

统一：

SQLAlchemy ORM。

禁止：

数据库与 Entity 不一致。

---

# 第十四章 Entity 与 Graph

每个 Entity：

天然对应：

Graph Node。

Node ID：

等于：

Entity UUID。

Graph 不允许重新生成 ID。

---

# 第十五章 Entity 与 AI

AI：

只能识别：

Entity。

不得生成：

不存在实体。

AI 新发现：

进入：

Candidate Entity。

人工审核通过后：

进入正式 Entity。

---

# 第十六章 Entity 与 API

API：

不得直接返回数据库对象。

统一返回：

Entity DTO。

所有接口：

遵循统一 Entity Schema。

---

# 第十七章 Entity 变更流程

新增实体必须完成：

1. 更新 Ontology；
2. 更新 Entity Specification；
3. 更新 Metadata；
4. 更新 ER 图；
5. 更新数据库迁移；
6. 更新 API；
7. 更新 Context Package；
8. 更新 Prompt Library。

未经批准不得新增。

---

# 第十八章 成功标准

平台所有：

数据库表

API

Graph Node

AI Entity

RAG Chunk

GraphRAG Node

均必须来源于统一 Entity 定义。

Entity Specification 是平台唯一实体标准。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 新增MVP边界交叉引用(第三章)；更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台统一实体规范。 |