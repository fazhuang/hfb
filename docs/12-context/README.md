---
title: 'Context Package Index'
version: '1.1'
status: 'Active'
owner: 'Chief Documentation Architect'
last_updated: '2026-06-25'
domain: 'documentation'
related:
  - 'docs/README.md'
  - 'docs/00-governance/0005_AI_Execution_Protocol.md'
  - 'docs/17-Platform-Specifications/1709_MVP_Implementation_Specification.md'
---

# 12 Context — AI 上下文包

每个 Sprint 的完整上下文的一次性打包。AI 在进入该 Sprint 时，直接读取对应 Sprint 目录下的全部文件，一次性加载全部上下文。

---

> 层级：**Level 6 — 执行工具与上下文**
>
> **版本:** 1.1
> **状态:** Active
> **适用范围:** 全项目 · AI 协作
> **维护者:** Chief Documentation Architect

## 设计原理

传统文档：分散在多个文件，AI 需要多次切换上下文才能理解全貌。
Context Package：每个 Sprint 一个目录，7 份文件覆盖全部维度，AI 一次性加载。

## AI 启动流程

依据 [HFB-GOV-0005 AI Execution Protocol](../00-governance/0005_AI_Execution_Protocol.md) §4：

```
1. 读取 project-summary.md → 理解项目当前状态
2. 读取 architecture.md → 理解技术架构
3. 读取 database.md → 理解数据模型
4. 读取 api.md → 理解接口现状
5. 读取 prompt.md → 加载可用 Prompt
6. 读取 review.md → 了解质量状况
7. 读取 todo.md → 获取待办任务
→ 开始工作
```

## Sprint 列表

| Sprint                    | 主题     | 状态    |
| ------------------------- | -------- | ------- |
| [Sprint 00](Sprint00/)    | 文档奠基 | Active  |
| [Sprint 01](Sprint01/)    | 基础骨架 | Pending |
| [Sprint 02](Sprint02/)    | 核心领域 | Pending |
| [Sprint 03](Sprint03/)    | AI 集成  | Pending |
| [Sprint 04](Sprint04/)    | UI 完善  | Pending |
| [Sprint 05](Sprint05/)    | 验收上线 | Pending |
| [Sprint 06–16](Sprint06/) | 后续     | Pending |

## 每 Sprint 的文件结构

```
SprintNN/
├── project-summary.md   # 项目当前状态摘要
├── architecture.md      # 架构状态
├── database.md          # 数据库状态
├── api.md               # API 状态
├── prompt.md            # Prompt 状态
├── review.md            # 审查状态
└── todo.md              # 待办事项
```

## MVP 上下文约束

依据 [HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)：

- Sprint 1–10 为 MVP 阶段，上下文包聚焦于 HFB-PS-1709 定义的 11 个模块
- 超出 MVP 范围的功能不进入当前 Sprint Context

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-25
