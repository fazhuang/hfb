---
title: Project Charter
document_id: HFB-GOV-0001
version: 1.0.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Entire Project
priority: P0
related_documents:
  - HFB-GOV-0002 Project Constitution
  - HFB-GOV-0003 Governance
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
  - HFB-RF-1601 Digital Humanities Research Framework
  - HFB-PS-1702 Platform Information Architecture Specification
---

# Project Charter

## 皇甫谧数字人文与中医经典智能研究平台 — 项目章程

> 本文档是《皇甫谧数字人文与中医经典智能研究平台》的项目章程。
>
> 它回答：**为什么做这个项目、做什么、不做什么、谁是决策者、怎样算成功。**
>
> 本文件为二级治理文件，效力仅次于 Constitution（HFB-GOV-0002）。

---

## 目录

- [1. 使命](#1-使命)
- [2. 愿景](#2-愿景)
- [3. 范围](#3-范围)
- [4. 利益相关者与 AI 角色](#4-利益相关者与-ai-角色)
- [5. 成功定义](#5-成功定义)
- [6. 产品实现最高依据](#6-产品实现最高依据)
- [7. MVP 边界](#7-mvp-边界)
- [8. 上线准入标准](#8-上线准入标准)
- [9. 研究框架关系](#9-研究框架关系)

---

## 1. 使命

建设一个能够长期服务于高校、科研机构和中医经典研究者的数字基础设施，使古籍整理为结构化数据，使人文研究可计算、可验证、可复现。

平台以皇甫谧（215–282）命名，致敬其"述而不作，信而好古"的精神 — 系统整理前人医学文献，使之可传承、可检索、可应用。

---

## 2. 愿景

| 时间             | 目标                                                         |
| ---------------- | ------------------------------------------------------------ |
| 近期（0–6 个月） | MVP 上线，支撑真实科研试运行                                 |
| 中期（1–3 年）   | 建成国内领先的皇甫谧数字研究平台                             |
| 长期（3–10 年）  | 形成中医经典数字人文平台基础框架，成为开放的数字知识基础设施 |

---

## 3. 范围

### 在范围内

- 皇甫谧生平、著作、学术传播、研究成果的数字化管理
- 《针灸甲乙经》多版本系统化整理与研究
- 数字人文研究工具：知识图谱、版本校勘、引文网络、AI 辅助分析
- 面向高校与科研机构的学术研究平台
- AI 能力：RAG、GraphRAG、Evidence、Citation、Explain
- 平台产品实现，参见 [HFB-PS-1709 MVP Implementation Specification](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)

### 不在范围内

- 在线诊疗、医疗决策、药方推荐、临床辅助诊断、中医问诊系统
- APP、微信小程序、VR/AR 展示、数字博物馆
- 自动论文生成、多 Agent 自主科研
- 大规模数据开放接口（第一阶段延期）

---

## 4. 利益相关者与 AI 角色

### 人类角色

| 角色                    | 职责                               |
| ----------------------- | ---------------------------------- |
| Product Owner           | 产品方向、Roadmap、优先级决策      |
| Tech Lead               | 架构决策、技术路线、代码质量       |
| Design Lead             | 信息架构、UI/UX、学术交互设计      |
| AI Lead                 | AI 能力规划、Prompt 工程、模型评估 |
| Research Lead           | 学术方向、研究框架、数据质量       |
| Documentation Committee | 文档体系维护、审计、版本一致性     |

### AI 角色与职责边界

| AI              | 角色                                | 职责                                               | 禁止                                    |
| --------------- | ----------------------------------- | -------------------------------------------------- | --------------------------------------- |
| **ChatGPT**     | Chief Product & Technical Architect | 产品规划、Roadmap、Sprint 拆解、架构设计、最终批准 | 越过 Roadmap 安排开发                   |
| **Claude Code** | Principal Engineer                  | 编码实现、工程搭建、单元测试、重构、性能优化       | 自行增加需求、修改产品定位、跳过 Sprint |
| **Codex**       | Chief Architecture Reviewer         | 架构审计、安全审计、测试验证、代码质量检查         | 直接修改代码、降低验收标准              |
| **Gemini**      | Academic & UX Reviewer              | UI/UX、学术表达、数字人文体验、信息架构            | 修改业务逻辑、修改数据库结构            |

> 详细 AI 职责边界参见 [HFB-GOV-0005 AI Execution Protocol](0005_AI_Execution_Protocol.md)。

---

## 5. 成功定义

项目成功不以代码量衡量，而以以下指标衡量：

1. **学术价值** — 平台能否支撑真实科研与教学
2. **数据质量** — 所有数据来源明确、可追溯、有 Citation、有 Evidence
3. **AI 可解释性** — AI 输出可追溯、可验证、不编造
4. **可维护性** — 代码与文档可持续演进，不产生技术债务
5. **可持续演进** — 架构支撑五年以上持续迭代
6. **实际应用** — 高校与科研机构可实际使用

---

## 6. 产品实现最高依据

本项目的产品实现以 **docs/17-Platform-Specifications/** 为最高依据。

任何开发任务、Sprint 规划、AI 指令，必须以 17-Platform-Specifications 系列文档为产品规格的唯一来源：

| 文档                                                                                                                       | document_id | 作用               |
| -------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------ |
| [Platform Information Architecture](../17-Platform-Specifications/1702_Platform_Information_Architecture_Specification.md) | HFB-PS-1702 | 平台信息架构       |
| [Platform Navigation & Interaction](../17-Platform-Specifications/1703_Platform_Navigation_Interaction_Specification.md)   | HFB-PS-1703 | 导航与交互规范     |
| [Platform Permission & Workspace](../17-Platform-Specifications/1704_Platform_Permission_Workspace_Specification.md)       | HFB-PS-1704 | 权限与工作空间     |
| [AI Research Workspace](../17-Platform-Specifications/1705_AI_Research_Workspace_Specification.md)                         | HFB-PS-1705 | AI 研究工作台      |
| [Unified Search & Discovery](../17-Platform-Specifications/1706_Unified_Search_Knowledge_Discovery_Specification.md)       | HFB-PS-1706 | 统一搜索与知识发现 |
| [Visualization & Knowledge Graph](../17-Platform-Specifications/1707_Visualization_Knowledge_Graph_Specification.md)       | HFB-PS-1707 | 可视化与知识图谱   |
| [Platform Integration](../17-Platform-Specifications/1708_Platform_Integration_Specification.md)                           | HFB-PS-1708 | 平台集成           |
| [MVP Implementation](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)                               | HFB-PS-1709 | MVP 实施边界       |
| [Production Readiness](../17-Platform-Specifications/1710_Production_Readiness_Specification.md)                           | HFB-PS-1710 | 上线准入标准       |

任何 17 系列文档的变更，必须走 RFC 流程并经 Chief Product Architect 批准。

---

## 7. MVP 边界

本文档明确：**MVP 以 HFB-PS-1709 为边界。**

MVP 第一阶段仅建设：

- 用户与权限
- Version Center
- Passage Center
- Person Center
- Book Center
- Knowledge Graph
- Unified Search
- AI Research Workspace
- Research Workspace
- Dashboard
- System Management

任何未列入 HFB-PS-1709 MVP 范围的功能，**不得进入第一阶段开发。**

违反此边界的开发，视为 Architecture Drift，必须立即纠正。

---

## 8. 上线准入标准

本文档明确：**上线以 HFB-PS-1710 为准入标准。**

平台进入生产环境前，必须通过 HFB-PS-1710 定义的全部 Go-Live Criteria，包括：

- 产品要求 — 所有 MVP 功能完整上线
- 数据要求 — 来源明确、版本清晰、Citation 完整
- AI 要求 — Evidence、Citation、GraphRAG、Explain 全部就绪
- 性能要求 — 首屏 ≤2s、API ≤500ms
- 安全要求 — RBAC、JWT、输入校验、Prompt Injection 防护
- 测试要求 — 单元、集成、E2E 全部通过

**任何未满足 HFB-PS-1710 要求的版本，不得进入生产环境。**

---

## 9. 研究框架关系

平台的学术方向以 **docs/16-research-framework/** 为最高研究依据。

| 框架                                                                                                                 | document_id | 研究方向           |
| -------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------ |
| [Digital Humanities Research Framework](../16-research-framework/1601_Digital_Humanities_Research_Framework.md)      | HFB-RF-1601 | 数字人文研究总框架 |
| [Huangfu Mi Studies](../16-research-framework/1602_Huangfu_Mi_Studies_Framework.md)                                  | HFB-RF-1602 | 皇甫谧研究         |
| [Acupuncture A-B Classic](../16-research-framework/1603_Acupuncture_A-B_Classic_Research_Framework.md)               | HFB-RF-1603 | 《针灸甲乙经》研究 |
| [Versionology](../16-research-framework/1604_Versionology_Research_Framework.md)                                     | HFB-RF-1604 | 版本学             |
| [Regional Transmission](../16-research-framework/1605_Regional_Transmission_Research_Framework.md)                   | HFB-RF-1605 | 地域传播           |
| [AI-Assisted Academic Research](../16-research-framework/1606_AI-Assisted_Academic_Research_Framework.md)            | HFB-RF-1606 | AI 辅助学术研究    |
| [Knowledge Evolution](../16-research-framework/1607_Knowledge_Evolution_Research_Framework.md)                       | HFB-RF-1607 | 知识演化           |
| [Digital Textual Criticism](../16-research-framework/1608_Digital_Textual_Criticism_Research_Framework.md)           | HFB-RF-1608 | 数字校勘学         |
| [Academic Citation Network](../16-research-framework/1609_Academic_Citation_Network_Research_Framework.md)           | HFB-RF-1609 | 学术引文网络       |
| [Academic Evidence](../16-research-framework/1610_Academic_Evidence_Research_Framework.md)                           | HFB-RF-1610 | 学术证据框架       |
| [Knowledge Discovery](../16-research-framework/1611_Knowledge_Discovery_Research_Framework.md)                       | HFB-RF-1611 | 知识发现           |
| [Intelligent Digital Humanities](../16-research-framework/1612_Intelligent_Digital_Humanities_Research_Framework.md) | HFB-RF-1612 | 智能数字人文       |

产品功能必须服务于研究框架定义的研究方向，不得开发无研究价值的展示功能。

---

## Changelog

| 版本   | 日期       | 变更                                                                                                          |
| ------ | ---------- | ------------------------------------------------------------------------------------------------------------- |
| v1.0.0 | 2026-06-25 | 正式发布 — 填充使命/愿景/范围/成功定义；新增产品实现依据、MVP边界、上线标准、研究框架关系；明确AI角色职责边界 |
| v0.1.0 | 2026-06-24 | 框架初稿                                                                                                      |
