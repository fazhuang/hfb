---
title: Platform Permission & Workspace Specification
document_id: HFB-PS-1704
version: 1.0.0
status: Approved
owner: Product Committee
reviewer: Chief Product Architect
effective_date: 2026-06-24
scope: Platform Permission and Workspace
priority: P0
related_documents:
  - HFB-PS-1702 Platform Information Architecture Specification
  - HFB-PS-1703 Platform Navigation & Interaction Specification
  - HFB-SEC-0702 Security Standard
  - HFB-AI-0401 AI Engineering Standard
  - HFB-GOV-0001 Project Charter
  - HFB-PS-1709 MVP Implementation Specification
---

# Platform Permission & Workspace Specification

## 平台权限与科研工作台规格书

> 本规格书定义《皇甫谧数字人文与中医经典智能研究平台》的统一权限体系（Permission System）与科研工作台体系（Research Workspace）。
>
> 权限系统不仅控制访问范围，更负责管理学术数据生命周期、AI 能力边界、科研协作流程及成果发布流程。
>
> Research Workspace 是平台唯一的科研工作空间，所有研究活动均在 Workspace 内完成。

---

# 第一章 设计目标

平台不是传统 CMS。

也不是 OA 系统。

平台定位：

> **AI 驱动的数字人文科研平台。**

因此权限体系必须满足：

- 数据安全
- 学术协同
- AI 可控
- 全程可追溯
- 科研成果可管理

Workspace 必须成为平台唯一科研入口。

---

# 第二章 权限设计原则

平台遵循：

## Least Privilege

默认最小权限。

任何用户默认只拥有浏览权限。

---

## Research Driven

权限服务科研。

而不是服务管理。

---

## Everything Traceable

所有操作：

必须记录。

包括：

- AI
- 编辑
- 删除
- 导出
- 发布

全部可追溯。

---

## Human Approval

AI 永远没有发布权限。

最终成果：

必须人工确认。

---

# 第三章 用户角色

统一角色：

| 角色                   | 描述       |
| ---------------------- | ---------- |
| Platform Administrator | 平台管理员 |
| Academic Administrator | 学术管理员 |
| Research Leader        | 项目负责人 |
| Researcher             | 研究人员   |
| Reviewer               | 学术审核人 |
| Student                | 学生       |
| Visitor                | 游客       |

所有角色采用 RBAC。

---

# 第四章 权限模型

统一权限对象：

```text
User

↓

Role

↓

Permission

↓

Workspace

↓

Resource

↓

Operation
```

平台禁止：

用户直接拥有权限。

必须：

Role → Permission。

---

# 第五章 Resource 权限

统一资源：

```text
Version

Book

Passage

Person

Evidence

Citation

Research

Workspace

Project

Dataset
```

统一控制：

Create

Read

Update

Delete

Export

Publish

Review

Approve

---

# 第六章 Workspace 体系

平台 Workspace 包括：

```text
Personal Workspace

↓

Project Workspace

↓

Academic Workspace

↓

Public Workspace
```

所有研究：

必须进入 Workspace。

---

# 第七章 Personal Workspace

个人工作区包括：

- 我的研究
- 我的收藏
- 我的笔记
- 我的AI
- 我的Graph
- 我的项目
- 我的历史

默认私有。

---

# 第八章 Project Workspace

课题组工作区：

包括：

- 成员
- 数据
- Version
- Evidence
- AI
- Notes
- Tasks
- Timeline

支持多人协同。

---

# 第九章 Academic Workspace

学术委员会工作区：

支持：

- 审核
- 校勘
- 引文审核
- 数据发布
- AI审核
- 成果确认

作为正式成果发布入口。

---

# 第十章 Public Workspace

公开科研空间：

包括：

- 已发布成果
- 公共Graph
- 开放数据
- 展示页面
- 国际共享

游客仅可访问公开内容。

---

# 第十一章 Workspace 生命周期

统一生命周期：

```text
Create

↓

Research

↓

Review

↓

Revision

↓

Approval

↓

Publication

↓

Archive
```

全过程记录。

---

# 第十二章 AI 权限

AI 默认：

允许：

- 阅读
- 检索
- 比较
- 推理
- 建议

禁止：

- 删除
- 发布
- 修改正式数据
- 审核通过

所有 AI 操作保留日志。

---

# 第十三章 Collaboration

多人科研支持：

- 实时协作
- 评论
- AI讨论
- Task
- Version Control

支持科研团队。

---

# 第十四章 Workspace Layout

统一布局：

```text
Knowledge Navigator

↓

Research Canvas

↓

AI Assistant

↓

Evidence Panel

↓

Task Panel
```

所有 Workspace 保持一致。

---

# 第十五章 Task System

任务包括：

- 数据整理
- 校勘
- AI分析
- Graph
- Review
- Publish

所有任务：

支持：

负责人。

截止日期。

状态。

---

# 第十六章 审核流程

统一审核：

```text
Research

↓

AI Suggestion

↓

Peer Review

↓

Academic Review

↓

Publication
```

AI 永远不能代替：

Peer Review。

---

# 第十七章 日志体系

统一日志：

- Login
- Edit
- Delete
- AI
- Export
- Review
- Publish

全部保留。

---

# 第十八章 安全要求

包括：

- RBAC
- MFA（预留）
- API Token
- 审计日志
- 数据恢复
- Workspace 隔离

保障科研安全。

---

# 第十九章 验收标准

Workspace 必须支持：

- 多角色
- 多项目
- 多AI
- 多人协同
- 审核
- 发布
- 全日志

全部通过。

---

# 第二十章 后续模块约束

所有模块：

不得：

自行实现权限。

不得：

自行实现 Workspace。

统一调用：

Platform Workspace。

统一调用：

Permission Service。

---

# 修订记录

| Version | Date       | Description                                                                                |
| ------- | ---------- | ------------------------------------------------------------------------------------------ |
| 1.0.0   | 2026-06-24 | 首版发布，定义平台统一权限体系与科研工作台规范，为所有模块提供统一权限控制与协同研究能力。 |
