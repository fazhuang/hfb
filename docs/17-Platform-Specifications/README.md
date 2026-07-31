---
title: 'Platform Specifications Index'
version: '1.1'
status: 'Active'
owner: 'Product Committee'
last_updated: '2026-06-25'
domain: 'product'
related:
  - 'docs/00-governance/0001-project-charter.md'
  - 'docs/00-governance/0002-project-constitution.md'
  - 'docs/02-architecture/0201_Technical_Blueprint.md'
  - 'docs/16-research-framework/README.md'
---

# 17 Platform Specifications — 平台规格书

皇甫谧数字人文平台的产品规格、实施边界及上线准入标准。**本目录为产品实现最高依据。**

---

> 层级：**Level 1 — 产品实现最高依据**（仅低于 00-governance）
>
> **版本:** 1.1
> **状态:** Active
> **适用范围:** 产品 · 技术 · 设计 · AI · 测试
> **维护者:** Product Committee

## 在 00-governance 中的确立

依据 [HFB-GOV-0001 Project Charter](../00-governance/0001-project-charter.md) §6 和 [HFB-GOV-0002 Constitution](../00-governance/0002-project-constitution.md) §15：

- **本目录为产品实现的最高依据**
- 任何开发任务、Sprint 规划、AI 指令，必须以本系列文档为产品规格的唯一来源
- 任何未在本系列中定义的功能，不得进入开发

## 规格书体系

| #    | 规格书                                                                                       | document_id | 状态     | 作用               |
| ---- | -------------------------------------------------------------------------------------------- | ----------- | -------- | ------------------ |
| 1701 | [Version Center](1701_Version_Center_Product_Specification.md)                               | HFB-PS-1701 | Approved | 版本中心产品规格   |
| 1702 | [Platform Information Architecture](1702_Platform_Information_Architecture_Specification.md) | HFB-PS-1702 | Approved | 平台信息架构       |
| 1703 | [Navigation & Interaction](1703_Platform_Navigation_Interaction_Specification.md)            | HFB-PS-1703 | Approved | 导航与交互规范     |
| 1704 | [Permission & Workspace](1704_Platform_Permission_Workspace_Specification.md)                | HFB-PS-1704 | Approved | 权限与工作空间     |
| 1705 | [AI Research Workspace](1705_AI_Research_Workspace_Specification.md)                         | HFB-PS-1705 | Approved | AI 研究工作台      |
| 1706 | [Unified Search & Discovery](1706_Unified_Search_Knowledge_Discovery_Specification.md)       | HFB-PS-1706 | Approved | 统一搜索与知识发现 |
| 1707 | [Visualization & Knowledge Graph](1707_Visualization_Knowledge_Graph_Specification.md)       | HFB-PS-1707 | Approved | 可视化与知识图谱   |
| 1708 | [Platform Integration](1708_Platform_Integration_Specification.md)                           | HFB-PS-1708 | Approved | 平台集成架构       |
| 1709 | [**MVP Implementation**](1709_MVP_Implementation_Specification.md)                           | HFB-PS-1709 | Approved | **MVP 实施边界**   |
| 1710 | [**Production Readiness**](1710_Production_Readiness_Specification.md)                       | HFB-PS-1710 | Approved | **上线准入标准**   |

### 关键两份文档

```
HFB-PS-1709 (MVP) — 定义"做什么、不做什么"
    ↓
HFB-PS-1710 (Production) — 定义"做到什么标准才能上线"
```

## 关联目录

| 目录                                                     | 关系     | 说明                                                   |
| -------------------------------------------------------- | -------- | ------------------------------------------------------ |
| [docs/00-governance/](../00-governance/)                 | 治理确认 | Charter §6 + Constitution §15 确立本目录为产品最高依据 |
| [docs/02-architecture/](../02-architecture/)             | 技术实现 | Technical Blueprint 服务于本目录的产品规格             |
| [docs/03-data/](../03-data/)                             | 数据建模 | 数据规范服务于本目录的产品数据需求                     |
| [docs/04-ai/](../04-ai/)                                 | AI 实现  | AI 能力以 1705（AI Workspace）+ 1709（MVP AI）为准     |
| [docs/05-development/](../05-development/)               | 开发实现 | 所有开发以本目录为产品规格来源                         |
| [docs/06-ui/](../06-ui/)                                 | UI 实现  | UI 以 1702（IA）+ 1703（导航交互）为准                 |
| [docs/16-research-framework/](../16-research-framework/) | 研究方向 | 产品功能服务于研究框架定义的学术方向                   |

## 变更流程

修改本目录下任何文件，视为战略决策，必须：

1. 走 RFC 流程
2. 经 Chief Product Architect 批准
3. 同步更新所有受影响的文档（ADR、Blueprint、Sprint Context）

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-25
