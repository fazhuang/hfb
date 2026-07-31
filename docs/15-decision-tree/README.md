---
title: 'Decision Tree Index'
version: '1.1'
status: 'Active'
owner: 'Chief Software Architect'
last_updated: '2026-06-25'
domain: 'architecture'
related:
  - 'docs/11-adr/README.md'
  - 'docs/02-architecture/0201_Technical_Blueprint.md'
  - 'docs/17-Platform-Specifications/1709_MVP_Implementation_Specification.md'
---

# 15 Decision Tree — 决策树

解释每个技术领域的决策逻辑——为什么选择当前方案，为什么放弃其它方案。供 AI 和新人理解技术选型理由。

---

> **版本:** 1.1
> **状态:** Active
> **适用范围:** 全项目 · 技术决策
> **维护者:** Chief Software Architect

## 决策树列表

| #   | 决策树                            | 核心决策                           | 候选方案数 | MVP         |
| --- | --------------------------------- | ---------------------------------- | ---------- | ----------- |
| 1   | [Architecture](Architecture.md)   | 六层架构 + Monorepo                | 3          | ✅          |
| 2   | [Database](Database.md)           | PostgreSQL + pgvector + Neo4j + ES | 4          | ✅ PG+ES    |
| 3   | [AI](AI.md)                       | RAG + GraphRAG 自研 Pipeline       | 3          | ✅ RAG only |
| 4   | [Frontend](Frontend.md)           | Vue 3 + TypeScript                 | 4          | ✅          |
| 5   | [Deployment](Deployment.md)       | Docker Compose                     | 3          | ✅          |
| 6   | [Documentation](Documentation.md) | AI Native 双轨制                   | 3          | ✅          |

## ADR 依赖

所有 Decision Tree 指向对应的 ADR，ADR 是正式决策记录，Decision Tree 是决策逻辑的解释。

## 关联目录

| 目录                                                               | 关系         | 说明                                  |
| ------------------------------------------------------------------ | ------------ | ------------------------------------- |
| [docs/11-adr/](../11-adr/)                                         | 正式决策记录 | 每项决策对应一份 ADR                  |
| [docs/02-architecture/](../02-architecture/)                       | 架构实现     | Technical Blueprint 是决策的落地      |
| [docs/17-Platform-Specifications/](../17-Platform-Specifications/) | 产品约束     | MVP 阶段技术选型以 HFB-PS-1709 为边界 |

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-25
