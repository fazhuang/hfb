---
title: Governance
document_id: HFB-GOV-0003
version: 1.0.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Entire Project
priority: P0
related_documents:
  - HFB-GOV-0001 Project Charter
  - HFB-GOV-0002 Project Constitution
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Governance

## 项目治理制度

> 本文档定义《皇甫谧数字人文与中医经典智能研究平台》的统一治理制度。
>
> 它是 Constitution 的执行层 — Constitution 说「什么」，Governance 说「怎么做」。
>
> 本文件为二级治理文件。

---

## 目录

- [1. 决策机制](#1-决策机制)
- [2. 角色与权限](#2-角色与权限)
- [3. 会议节奏](#3-会议节奏)
- [4. 变更流程](#4-变更流程)
- [5. 文档生命周期](#5-文档生命周期)
- [6. 强制与豁免](#6-强制与豁免)
- [7. MVP 范围控制](#7-mvp-范围控制)
- [8. 上线准入控制](#8-上线准入控制)
- [9. AI 职责边界执行](#9-ai-职责边界执行)

---

## 1. 决策机制

### 1.1 决策类型

| 类型         | 范围                         | 谁决定            | 需要什么    |
| ------------ | ---------------------------- | ----------------- | ----------- |
| **战略决策** | 产品方向、技术栈、架构       | 负责人 + 团队评审 | RFC 或 ADR  |
| **战术决策** | 实现方式、工具选择、具体设计 | 执行人            | TL 知情即可 |
| **紧急决策** | 生产事故、阻止性问题         | 任何在岗成员      | 事后补文档  |

### 1.2 ADR（Architecture Decision Record）

- 影响系统架构或技术方向的决策，必须产出 ADR
- 模板：[templates/adr.md](../templates/adr.md)
- 状态流：`proposed → accepted → superseded`
- ADR 编号全局唯一，存放于 [`docs/11-adr/`](../11-adr/)

### 1.3 RFC（Request for Comments）

- 跨系统或影响多人的变更，必须产出 RFC
- 模板：[templates/rfc.md](../templates/rfc.md)
- 状态流：`draft → review → accepted → implemented → retired`

---

## 2. 角色与权限

| 角色                 | 对文档           | 对代码   | 对架构   |
| -------------------- | ---------------- | -------- | -------- |
| **负责人 (Owner)**   | 写、改、废       | —        | —        |
| **技术负责人 (TL)**  | 评审 ADR/RFC     | 合并批准 | 架构决定 |
| **成员 (Member)**    | 写、改（需评审） | PR 提交  | 建议     |
| **访问者 (Visitor)** | 只读             | 无       | 无       |

### AI 角色权限

| AI              | 对文档       | 对代码 | 对架构     | 对产品   |
| --------------- | ------------ | ------ | ---------- | -------- |
| **ChatGPT**     | 写、改、批准 | 不写   | 设计、决策 | 决定     |
| **Claude Code** | 同步更新     | 写、改 | 不得偏离   | 不得修改 |
| **Codex**       | 审计报告     | 不写   | 审计、验证 | 不得修改 |
| **Gemini**      | UI/UX 评审   | 不写   | 不得修改   | 不得修改 |

---

## 3. 会议节奏

| 会议     | 频率      | 时长   | 参与者          | 产出           |
| -------- | --------- | ------ | --------------- | -------------- |
| 站会     | 每日      | 15 min | 全员            | —              |
| 迭代计划 | 每 Sprint | 1 h    | 全员            | Sprint Note    |
| 回顾     | 每 Sprint | 1 h    | 全员            | Retro          |
| 架构评审 | 按需      | 1 h    | TL + 架构相关者 | ADR / RFC 更新 |

---

## 4. 变更流程

### 4.1 文档变更

```
写 → PR → 评审 → 合并 → 归档
```

- 小改动（typo、格式）— 负责人自审即可合并
- 新增文档 — 至少 1 人评审
- 修改 Constitution 或 Project Charter — 团队评审 + TL 批准

### 4.2 代码变更

```
写 → 自测 → PR → CI → 评审 → 合并
```

- CI 必须通过
- 至少 1 人评审
- 禁止 force push 到共享分支

### 4.3 17-Platform-Specifications 变更

修改 docs/17-Platform-Specifications/ 下任何文件，视为战略决策，必须：

1. 走 RFC 流程
2. 经 Chief Product Architect 批准
3. 同步更新所有受影响的 Sprint 文档

---

## 5. 文档生命周期

每份文档从创建到废弃经历以下状态：

```
Draft → Review → Accepted → Implemented → Retired
```

- **Draft** — 初稿，仍在编写
- **Review** — 等待评审
- **Accepted** — 评审通过，已生效
- **Implemented** — 已落实为代码或行动
- **Retired** — 已失效，保留作为历史记录

负责人负责推动文档在状态之间流转。

---

## 6. 强制与豁免

- Constitution 中的规则对所有人生效（包括 AI），没有例外
- 紧急情况下可绕过流程，事后必须在 48 小时内补齐文档
- 豁免请求走 RFC 流程，注明原因和期限

---

## 7. MVP 范围控制

依据 [HFB-PS-1709 MVP Implementation Specification](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)：

- MVP 第一阶段仅建设 HFB-PS-1709 定义的模块列表
- 任何未列入 MVP 范围的功能，**不得进入第一阶段开发**
- 任何 AI 或开发者新增超出 MVP 范围的功能，视为 **Architecture Drift**，必须立即停止并输出 Architecture Alignment Report
- 正常的功能建议记录为 Backlog，进入后续阶段评估

### 范围控制流程

```
发现需求/想法
  ↓
检查是否在 HFB-PS-1709 范围内
  ↓ 是 → 纳入当前 Sprint 规划
  ↓ 否 → 记录 Backlog → 进入后续阶段评估
```

---

## 8. 上线准入控制

依据 [HFB-PS-1710 Production Readiness Specification](../17-Platform-Specifications/1710_Production_Readiness_Specification.md)：

- 任何版本进入生产环境前，必须通过 HFB-PS-1710 定义的全部 Go-Live Criteria
- 上线审批由 Chief Product Architect 执行
- 未满足 HFB-PS-1710 任何一条要求的版本，**一票否决**

### 上线审批流程

```
开发完成
  ↓
自检 HFB-PS-1710 全部要求
  ↓
Codex 安全审计
  ↓
Gemini UI/UX 审查
  ↓
Chief Product Architect 批准
  ↓
上线
```

---

## 9. AI 职责边界执行

依据 [HFB-GOV-0005 AI Execution Protocol](0005_AI_Execution_Protocol.md)：

- ChatGPT — 唯一有权决定产品方向和 Sprint 规划的 AI
- Claude Code — 唯一有权编写业务代码的 AI
- Codex — 唯一有权执行安全性审计的 AI
- Gemini — 唯一有权评审 UI/UX 和学术表达的 AI

### 越权处置

任何 AI 超越职责边界时：

1. 立即停止当前工作
2. 输出 Architecture Alignment Report
3. 回到自己的职责范围

人类 TL 和 Product Owner 有最终解释权。

---

## Changelog

| 版本   | 日期       | 变更                                                                                                       |
| ------ | ---------- | ---------------------------------------------------------------------------------------------------------- |
| v1.0.0 | 2026-06-25 | 正式发布 — 新增MVP范围控制(§7)、上线准入控制(§8)、AI职责边界执行(§9)；新增AI角色权限表；明确17系列变更流程 |
| v0.1.0 | 2026-06-24 | 框架初稿                                                                                                   |
