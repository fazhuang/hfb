---
title: Project Constitution
document_id: HFB-GOV-0002
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Entire Project
priority: P0
related_documents:
  - HFB-GOV-0001 Project Charter
  - HFB-GOV-0003 Governance
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
  - HFB-RF-1601 Digital Humanities Research Framework
  - HFB-ARC-0201 Technical Blueprint
---

# Project Constitution
## 皇甫谧数字人文与中医经典智能研究平台项目宪章

> 本文档是本项目最高治理文件。
>
> 除《AI Execution Protocol》外，任何文档、Prompt、Sprint、开发计划均不得与本宪章冲突。

---

# 第一章 项目定位

## 1.1 项目名称

皇甫谧数字人文与中医经典智能研究平台

英文名称：

Huangfu Mi Digital Humanities & Classical Chinese Medicine Research Platform

简称：

HFB Platform

---

## 1.2 平台定位

本项目不是：

- 企业官网
- CMS 内容管理系统
- OA 系统
- 中医诊疗系统
- AI 聊天机器人

本项目定位为：

> **数字人文基础平台 + 学术研究平台 + 中医经典知识平台 + AI 科研辅助平台**

所有建设工作必须围绕上述定位展开。

---

# 第二章 项目使命

建设一个能够长期服务于高校、科研机构和中医经典研究者的数字基础设施，实现：

1. 皇甫谧学术资源数字化；
2. 《针灸甲乙经》多版本系统化整理；
3. 学术资源统一管理；
4. AI 可追溯研究助手；
5. 知识图谱与数字人文分析；
6. 后续扩展至其他中医经典。

---

# 第三章 项目愿景

三年目标：

建成国内领先的皇甫谧数字研究平台。

五年目标：

形成中医经典数字人文平台基础框架。

十年目标：

成为开放的中医经典数字知识基础设施。

---

# 第四章 核心原则

## Principle 1：Academic First

学术价值优先。

任何技术方案不得损害学术严谨性。

---

## Principle 2：Evidence First

所有数据必须具有来源。

所有 AI 输出必须可追溯。

禁止：

- AI 幻觉；
- 无来源引用；
- 无依据结论。

---

## Principle 3：Data First

数据是平台最重要的资产。

任何业务不得绕开数据标准。

任何页面不得使用硬编码业务数据。

---

## Principle 4：Documentation First

先文档。

后开发。

任何接口、模型、数据库结构必须先形成文档。

---

## Principle 5：AI Native

平台自设计阶段即支持：

- AI
- RAG
- GraphRAG
- Agent
- Knowledge Graph

但必须按照 Roadmap 分阶段实施。

---

## Principle 6：Long-term Evolution

任何设计必须支持未来五年以上持续演进。

禁止一次性 Demo 架构。

---

# 第五章 产品边界

平台当前研究对象：

- 皇甫谧
- 《针灸甲乙经》
- 皇甫谧相关研究成果
- 皇甫谧学术传播
- 数字人文研究

当前不属于项目范围：

- 在线诊疗
- 医疗决策
- 药方推荐
- 临床辅助诊断
- 中医问诊系统

---

# 第六章 技术原则

统一遵循：

- Monorepo
- Documentation Driven Development
- Domain Driven Design
- Clean Architecture
- Repository Pattern
- Service Layer
- RESTful API
- OpenAPI
- Docker First

---

# 第七章 数据治理原则

所有数据必须：

- 唯一标识（Unique ID）
- 可追溯（Traceable）
- 可版本化（Versioned）
- 可引用（Citable）
- 可扩展（Extensible）

不得存在：

- 重复实体；
- 来源不明数据；
- 无元数据记录。

---

# 第八章 AI 治理原则

AI 是辅助研究工具。

不是研究结论来源。

AI 输出必须：

- 给出引用；
- 标注版本；
- 标注可信度；
- 保留证据链。

AI 不得：

代替学术判断。

---

# 第九章 软件工程原则

所有开发必须：

- Sprint 驱动；
- Git 管理；
- Code Review；
- 自动化测试；
- 自动化部署；
- 自动化审计。

任何功能不得直接进入主分支。

---

# 第十章 Sprint 管理

项目采用固定 Sprint 制度。

任何 Sprint：

必须定义：

- 输入；
- 输出；
- 边界；
- 验收标准；
- 风险。

未经批准不得跨 Sprint 开发。

---

# 第十一章 AI 协作机制

项目采用固定 AI 协作模型，每类 AI 有明确职责边界。

## 11.1 角色与职责

| AI | 角色 | 职责 | 禁止 |
|---|---|---|---|
| **ChatGPT** | Chief Product & Technical Architect | 产品规划、Roadmap、Sprint 拆解、架构设计、最终批准 | 越过 Roadmap 安排开发 |
| **Claude Code** | Principal Engineer | 编码实现、工程搭建、单元测试、重构、性能优化 | 自行增加需求、修改产品定位、跳过 Sprint |
| **Codex** | Chief Architecture Reviewer | 架构审计、安全审计、测试验证、代码质量检查 | 直接修改代码、降低验收标准 |
| **Gemini** | Academic & UX Reviewer | UI/UX、学术表达、数字人文体验、信息架构 | 修改业务逻辑、修改数据库结构 |

## 11.2 Sprint 协作流程

```
ChatGPT 批准
  ↓
Claude 开发
  ↓
Codex 审计
  ↓
Gemini 评审
  ↓
ChatGPT 批准进入下一 Sprint
```

任何阶段不得跳过。任何环节失败，Sprint 不得结束。

> 详细 AI 职责边界与禁止事项，参见 [HFB-GOV-0005 AI Execution Protocol](0005_AI_Execution_Protocol.md)。

---

# 第十二章 文档体系

项目所有文档按以下层级管理：

Level 0：

Governance

Level 1：

Architecture

Level 2：

Development

Level 3：

Sprint

Level 4：

Prompt

Level 5：

Knowledge

任何新增文档必须归属上述体系。

---

# 第十三章 质量红线

以下情况一票否决：

1. 文档与实现不一致；
2. AI 输出无来源；
3. 架构偏离 Roadmap；
4. 新增未批准模块；
5. 测试未通过；
6. CI 未通过；
7. 高危安全漏洞；
8. 无法追溯的数据；
9. 未更新文档；
10. 未完成审计。

---

# 第十四章 项目成功标准

项目成功不以代码量衡量。

而以以下指标衡量：

- 学术价值；
- 数据质量；
- AI 可解释性；
- 可维护性；
- 可持续演进能力；
- 高校与科研机构可实际应用。

---

# 第十五章 产品实现最高依据

本宪章明确：

## 15.1 产品规格最高依据

**docs/17-Platform-Specifications/** 为产品实现的最高依据。

任何 Sprint 的输入必须来源于 17-Platform-Specifications 系列文档，包括：

- [HFB-PS-1701](../17-Platform-Specifications/1701_Version_Center_Product_Specification.md) — Version Center
- [HFB-PS-1702](../17-Platform-Specifications/1702_Platform_Information_Architecture_Specification.md) — 平台信息架构
- [HFB-PS-1703](../17-Platform-Specifications/1703_Platform_Navigation_Interaction_Specification.md) — 导航与交互
- [HFB-PS-1704](../17-Platform-Specifications/1704_Platform_Permission_Workspace_Specification.md) — 权限与工作空间
- [HFB-PS-1705](../17-Platform-Specifications/1705_AI_Research_Workspace_Specification.md) — AI 研究工作台
- [HFB-PS-1706](../17-Platform-Specifications/1706_Unified_Search_Knowledge_Discovery_Specification.md) — 统一搜索
- [HFB-PS-1707](../17-Platform-Specifications/1707_Visualization_Knowledge_Graph_Specification.md) — 可视化与知识图谱
- [HFB-PS-1708](../17-Platform-Specifications/1708_Platform_Integration_Specification.md) — 平台集成
- [HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) — MVP 实施边界
- [HFB-PS-1710](../17-Platform-Specifications/1710_Production_Readiness_Specification.md) — 上线准入标准

任何未在 17 系列中定义的功能，不得进入开发。

## 15.2 研究框架最高依据

**docs/16-research-framework/** 为学术研究方向的最高依据。

所有产品功能必须服务于 16 系列研究框架定义的研究方向。

---

# 第十六章 MVP 边界

本文档明确：**MVP 以 HFB-PS-1709 为边界。**

MVP 第一阶段仅建设 HFB-PS-1709 定义的模块列表。任何未列入 MVP 范围的功能，不得进入第一阶段开发。

**违反 MVP 边界的开发，视为 Architecture Drift，必须立即纠正。**

---

# 第十七章 上线准入标准

本文档明确：**上线以 HFB-PS-1710 为准入标准。**

平台进入生产环境前，必须通过 HFB-PS-1710 定义的全部 Go-Live Criteria：

- 产品 — 所有 MVP 功能完整上线
- 数据 — 来源明确、版本清晰、Citation 完整
- AI — Evidence、Citation、GraphRAG、Explain 就绪
- 性能 — 首屏 ≤2s、API ≤500ms
- 安全 — RBAC、JWT、输入校验、Prompt Injection 防护
- 测试 — 单元、集成、E2E 全部通过

**任何未满足 HFB-PS-1710 要求的版本，不得进入生产环境。**

---

# 第十八章 宪章修订规则

本宪章属于一级治理文件。

任何修改必须满足：

1. 提出修订说明；
2. 更新 ADR；
3. 更新版本号；
4. 更新修订记录；
5. 经项目总负责人批准。

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 新增第十五章(产品实现最高依据)、第十六章(MVP边界)、第十七章(上线准入标准)；重写第十一章(AI协作机制)明确四个AI角色职责边界 |
| 1.0.0 | 2026-06-24 | 首版发布，作为项目最高治理文件。 |