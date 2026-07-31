---
title: 'Machine Layer README'
version: '1.1'
status: 'Active'
owner: 'Chief Documentation Architect'
last_updated: '2026-06-25'
domain: 'documentation'
related:
  - 'docs/00-governance/0005_AI_Execution_Protocol.md'
  - 'docs/09-prompts/README.md'
---

# 13 Machine — AI Machine Layer

机器可读层。所有 AI 模型进入本项目后，首先读取本目录下的 JSON 文件以理解项目全貌。

---

> 层级：**Level 6 — 执行工具与上下文**
>
> **版本:** 1.1
> **状态:** Active
> **适用范围:** 全 AI 模型
> **维护者:** Chief Documentation Architect

## 设计原理

```
AI 进入项目
  → 读取 README.json  → 理解 Machine Layer 结构
  → 读取 project.json → 理解项目和技术栈
  → 读取 document-index.json → 理解文档清单
  → 读取 architecture.json → 理解架构
  → 读取 api-index.json → 理解 API
  → 读取 prompt-index.json → 加载 Prompt
  → 读取 sprint-index.json → 了解进度
  → 开始工作
```

不需要任何人工描述。JSON 即导航。

## 文件清单

| 文件                  | 用途                |
| --------------------- | ------------------- |
| `project.json`        | 项目元数据 + 技术栈 |
| `document-index.json` | 全部文档索引        |
| `prompt-index.json`   | Prompt 版本和状态   |
| `sprint-index.json`   | Sprint 进度         |
| `architecture.json`   | 六层架构 + ADR      |
| `ontology.json`       | 知识本体            |
| `entity-types.json`   | 实体类型定义        |
| `relation-types.json` | 关系类型 + NER 标签 |
| `api-index.json`      | API 端点清单        |
| `README.json`         | 本文件              |

## 维护规则

- Markdown 文档新增/删除时 → 同步更新 `document-index.json`
- Prompt 版本变更时 → 同步更新 `prompt-index.json`
- Sprint 状态变更时 → 同步更新 `sprint-index.json`
- 架构变更时 → 同步更新 `architecture.json`

## 关联目录

| 目录                                     | 关系        | 说明                                        |
| ---------------------------------------- | ----------- | ------------------------------------------- |
| [docs/00-governance/](../00-governance/) | AI 启动依据 | 遵循 0005 AI Execution Protocol §4 启动流程 |
| [docs/09-prompts/](../09-prompts/)       | Prompt 来源 | Prompt 索引映射到 09-prompts 资产库         |

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-25
