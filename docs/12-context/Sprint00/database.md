---
title: "Sprint 00 Database Status"
version: "1.0"
status: "Draft"
sprint: "Sprint 00"
last_updated: "2026-06-24"
related: ["../../03-data/00_Data_Standard.md", "../../10-diagrams/01_Database_ER.md"]
---

# Sprint 00 — Database Status

## 当前数据库状态

**阶段：** 数据模型设计完成，待建表。

## 核心实体

| 实体 | 表名 | 状态 |
|---|---|---|
| Person | `persons` | 已设计 |
| Book | `books` | 已设计 |
| Version | `versions` | 已设计 |
| Chapter | `chapters` | 已设计 |
| Passage | `passages` | 已设计 |
| Paper | `papers` | 已设计 |
| Entity | `entities` | 已设计 |
| Relation | `relations` | 已设计 |
| User | `users` | 已设计 |

## 数据库选型

| 组件 | 选型 |
|---|---|
| 主库 | PostgreSQL 16 |
| 向量 | pgvector (V1) |
| 图 | Neo4j 5 (L2 阶段使用) |
| 搜索 | Elasticsearch 8 |

## Sprint 01 数据库任务

- 创建 Alembic 迁移脚本
- 执行首次迁移
- 建立种子数据（1 部古籍）
- 配置 pgvector 扩展

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
