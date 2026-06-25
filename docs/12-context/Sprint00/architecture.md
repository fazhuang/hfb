---
title: "Sprint 00 Architecture Status"
version: "1.0"
status: "Draft"
sprint: "Sprint 00"
last_updated: "2026-06-24"
related: ["../../02-architecture/00_Technical_Blueprint.md", "../../11-adr/README.md"]
---

# Sprint 00 — Architecture Status

## 当前架构状态

**阶段：** 架构设计完成，待实现。

## 六层拓扑

```
L1 Nginx → L2 FastAPI → L3 Domain Services → L4 AI Pipeline → L5 PostgreSQL/Neo4j/ES → L6 Docker
```

## 技术决策一览

| ADR | 决策 | 状态 |
|---|---|---|
| ADR-0001 | FastAPI | Accepted |
| ADR-0002 | Vue 3 | Accepted |
| ADR-0003 | PostgreSQL + pgvector | Accepted |
| ADR-0004 | Neo4j 5 | Accepted |
| ADR-0005 | Elasticsearch 8 | Accepted |
| ADR-0006 | GraphRAG 自研 | Accepted |
| ADR-0007 | Milvus (V2) | Accepted |
| ADR-0008 | Docker Compose | Accepted |
| ADR-0009 | Monorepo | Accepted |
| ADR-0010 | AI Native Docs | Accepted |

## 待定事项

- 前端 UI 组件库（Naive UI / 自建）
- 具体 LLM 提供商
- NER 模型选型
- CI/CD 流水线详细设计

## 下一 Sprint (Sprint 01) 架构任务

- 项目脚手架搭建
- 数据库 Schema 创建
- API 框架骨架
- 认证模块

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
