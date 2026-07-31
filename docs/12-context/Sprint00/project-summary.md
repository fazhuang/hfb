---
title: 'Sprint 00 Context Package'
version: '1.0'
status: 'Active'
sprint: 'Sprint 00'
theme: '文档奠基'
dates: '2026-06-24 → 2026-06-28'
owner: 'Chief Documentation Architect'
ai_models: ['Claude', 'Codex', 'Gemini']
---

# Sprint 00 — Context Package

AI 进入 Sprint 00 的完整上下文。读取本文件即理解项目全貌。

---

## 1. 项目当前状态

**阶段：** 文档奠基。零代码。

**已完成：**

- V1 文档体系（22 份 Markdown）
- Mermaid 架构图 + ER 图
- Prompt 工程指令（3 份）
- 模板体系（12 份）

**升级中：**

- AI Native Documentation Repository 升级
- ADR 体系建立
- Context Package 建立
- Machine Layer (JSON) 建立

## 2. 技术栈

| 层         | 选型                        |
| ---------- | --------------------------- |
| 后端       | Python 3.12 + FastAPI       |
| 前端       | Vue 3 + TypeScript + Vite   |
| 主数据库   | PostgreSQL 16 + pgvector    |
| 图数据库   | Neo4j 5 Community           |
| 搜索引擎   | Elasticsearch 8 + IK        |
| 向量数据库 | pgvector (V1) → Milvus (V2) |
| LLM        | Claude / GPT / Qwen         |
| 部署       | Docker Compose              |
| 代码组织   | Monorepo                    |

## 3. 架构总览

六层架构：L1 接入层 → L2 应用层 → L3 领域层 → L4 AI 层 → L5 数据层 → L6 基础设施层

详细见 [System Architecture](../../10-diagrams/00_System_Architecture.md)

## 4. 数据模型

9 个核心实体：Person, Book, Version, Chapter, Passage, Paper, Entity, Relation, User

详细见 [Database ER](../../10-diagrams/01_Database_ER.md)

## 5. 质量红线

1. 文档通过 Codex 审计
2. UI 通过 Gemini 学术评审
3. API 有完整文档
4. DB 变更附 ER 图
5. AI 输出可溯源

## 6. 当前 Sprint 0.1 任务

1. ADR 体系 — 10 份 ADR
2. Context Package — 17 个 Sprint 上下文
3. Machine Layer — 10 份 JSON
4. Prompt Version — 版本管理
5. Knowledge Package — 8 个领域
6. Decision Tree — 6 个决策树
7. Cross Reference — 全仓互链
8. README 升级 — 8 张 Map
9. Mermaid — 9 张新图
10. 质量统一 — Front Matter 标准化

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
