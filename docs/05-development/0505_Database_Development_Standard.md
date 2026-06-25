---
title: Database Development Standard
document_id: HFB-DEV-0505
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Database Architecture
priority: P0
related_documents:
  - HFB-ARC-0201 Technical Blueprint
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-DEV-0504 API Design Standard
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Database Development Standard
## 数据库开发规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》数据库设计、开发、迁移、维护及演进的统一标准。
>
> 数据库不仅是业务数据存储系统，更是数字人文知识基础设施（Knowledge Infrastructure）的核心组成部分。

---

# 第一章 建设目标

数据库必须满足以下目标：

- 学术数据长期保存
- 多版本文献管理
- 数据可追溯
- 知识关系可扩展
- AI 检索友好
- 图谱映射一致
- 长期稳定演进

---

# 第二章 总体架构

平台采用多存储架构：

```text
PostgreSQL
        │
        ├── Core Data
        ├── Metadata
        ├── User
        └── Audit

Redis
        │
        └── Cache

Elasticsearch
        │
        └── Full Text Search

MinIO
        │
        └── Object Storage

Graph Database（Roadmap）
        │
        └── Knowledge Graph
```

MVP 阶段：

仅 PostgreSQL 为主数据库。

---

# 第三章 数据库原则

遵循：

- Single Source of Truth
- Normalization First
- Metadata Driven
- Version First
- Audit First

禁止：

重复存储业务数据。

---

# 第四章 Schema 划分

统一 Schema：

```text
core

academic

system

audit

ai（预留）
```

说明：

| Schema | 内容 |
|---------|------|
| core | 基础实体 |
| academic | 学术资源 |
| system | 用户权限 |
| audit | 日志 |
| ai | AI 运行数据（后续） |

---

# 第五章 核心实体

数据库 MVP 核心实体：

```text
Person

Book

Version

Chapter

Passage

Paper

Image

Document

Institution

Place

Event
```

全部来源于：

Entity Specification。

禁止新增未批准实体。

---

# 第六章 主键规范

统一：

UUID v7。

字段：

```text
id UUID
```

禁止：

自增主键作为业务标识。

---

# 第七章 公共字段

所有业务表必须继承：

```text
id

status

version

created_at

updated_at

created_by

updated_by

deleted_at（软删除）

metadata_id
```

统一继承：

BaseEntity。

---

# 第八章 命名规范

数据库：

snake_case。

表名：

单数。

例如：

```text
person

book

version

paper
```

禁止：

复数表名。

---

# 第九章 外键规范

统一：

UUID。

必须：

建立外键约束。

禁止：

字符串关联。

---

# 第十章 Version 设计

Version：

一级实体。

禁止：

直接覆盖历史版本。

必须：

永久保存历史。

例如：

```
Book

↓

Version

↓

Version History
```

---

# 第十一章 Metadata

Metadata：

独立表。

所有资源：

1:1

关联：

Metadata。

禁止：

Metadata 写入业务表。

---

# 第十二章 Relation

复杂关系：

统一：

Relation 表。

禁止：

大量：

Many-to-Many

中间表泛滥。

统一采用：

Entity + Relation。

---

# 第十三章 审计

所有业务表：

记录：

- 创建
- 修改
- 删除
- 审核

Audit：

独立 Schema。

不得删除。

---

# 第十四章 Migration

统一：

Alembic。

任何数据库修改：

必须：

Migration。

禁止：

直接修改生产数据库。

---

# 第十五章 Index

必须建立：

- UUID
- Foreign Key
- Metadata
- Version
- Status

全文：

交由 Elasticsearch。

禁止：

数据库全文搜索。

---

# 第十六章 数据完整性

统一：

Constraint。

包括：

- Unique
- Foreign Key
- Check
- Not Null

禁止：

依赖程序保证一致性。

---

# 第十七章 AI 数据

AI 数据：

独立存储。

包括：

- Prompt
- Retrieval
- Embedding（后续）
- Citation
- Confidence

不得污染业务表。

---

# 第十八章 数据备份

必须支持：

- 每日备份
- PITR（Point-in-Time Recovery）
- 每周全量
- 每小时 WAL

保留策略：

依据部署环境确定。

---

# 第十九章 数据质量

目标：

| 指标 | 标准 |
|------|------|
| Referential Integrity | 100% |
| Metadata 完整率 | 100% |
| UUID 覆盖率 | 100% |
| Version 完整率 | 100% |
| Audit 覆盖率 | 100% |

---

# 第二十章 数据库红线

禁止：

- 删除历史版本
- 修改主键
- 无 Migration
- 字符串外键
- Metadata 缺失
- ORM 自动建表替代 Migration
- AI 写正式业务数据

违反任一项不得上线。

---

# 第二十一章 数据演进路线

Sprint 1~3：

基础数据库。

Sprint 4~6：

学术实体。

Sprint 7：

OCR 数据。

Sprint 8：

RAG 数据。

Sprint 9：

知识图谱映射。

Sprint 10：

Graph 数据同步。

---

# 第二十二章 修订规则

修改数据库规范必须同步更新：

- Entity Specification
- Relation Specification
- Metadata Standard
- ER Diagram
- Migration
- Context Package

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台数据库开发统一规范。 |