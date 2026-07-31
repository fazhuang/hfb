---
title: AI Execution Protocol
document_id: HFB-GOV-0005
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: All AI Participants
priority: P0
related_documents:
  - HFB-GOV-0001 Project Charter
  - HFB-GOV-0002 Project Constitution
  - HFB-GOV-0003 Governance
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# AI Execution Protocol

## （AI 执行协议）

> 本文档是《皇甫谧数字人文与中医经典智能研究平台》的最高 AI 执行规范。
>
> 所有参与本项目的软件、AI Agent、LLM、自动化工具及开发人员，必须遵守本协议。
>
> 本协议优先级高于 Prompt，高于 Sprint，高于个人决策。

---

# 1. 目标

建立统一的 AI 软件工程协作机制，确保：

- 项目始终沿着既定 Roadmap 前进；
- 所有 AI 输出保持一致性；
- 防止架构漂移（Architecture Drift）；
- 防止需求膨胀（Scope Creep）；
- 保证代码、文档、数据长期可维护。

---

# 2. 适用范围

本协议适用于：

- Claude Code
- Codex
- Gemini
- ChatGPT
- Deep Research Agent
- Documentation Agent
- 后续新增 AI Agent
- 人工开发成员

---

# 3. 项目唯一可信源（Single Source of Truth）

任何 AI 不得以聊天记录作为最终依据。

所有决策必须来源于以下文档：

1. [Project Constitution](0002-project-constitution.md) — HFB-GOV-0002
2. [Project Charter](0001-project-charter.md) — HFB-GOV-0001
3. [AI Execution Protocol](0005_AI_Execution_Protocol.md) — HFB-GOV-0005
4. [17-Platform-Specifications](../17-Platform-Specifications/) — 产品实现最高依据
   - [MVP Implementation Specification](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) — HFB-PS-1709
   - [Production Readiness Specification](../17-Platform-Specifications/1710_Production_Readiness_Specification.md) — HFB-PS-1710
5. [16-Research Framework](../16-research-framework/) — 学术研究方向最高依据
6. [Technical Blueprint](../02-architecture/0201_Technical_Blueprint.md) — HFB-ARC-0201
7. [Data Standard Specification](../03-data/0301_Data_Standard_Specification.md) — HFB-DAT-0301
8. [Documentation Index](../documentation-index.md) — HFB-DOC-INDEX

若上述内容发生冲突，以编号靠前者为准。

---

# 4. AI 启动流程（Bootstrap）

任何 AI 接手项目时，必须按以下顺序读取：

1. [docs/README.md](../README.md) — Documentation Center
2. [Project Constitution](0002-project-constitution.md) — HFB-GOV-0002
3. [AI Execution Protocol](0005_AI_Execution_Protocol.md) — HFB-GOV-0005（本文档）
4. [Project Charter](0001-project-charter.md) — HFB-GOV-0001
5. [17-Platform-Specifications](../17-Platform-Specifications/) — 产品实现最高依据
   - 特别是 [MVP Implementation](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) 和 [Production Readiness](../17-Platform-Specifications/1710_Production_Readiness_Specification.md)
6. [16-Research Framework](../16-research-framework/) — 学术研究方向
7. [Technical Blueprint](../02-architecture/0201_Technical_Blueprint.md)
8. [Data Standard Specification](../03-data/0301_Data_Standard_Specification.md)
9. [Documentation Index](../documentation-index.md)

完成阅读前，不得开始工作。

---

# 5. AI 角色分工

## 5.1 ChatGPT（Chief Product & Technical Architect）

职责：

- 产品规划
- Roadmap
- Sprint 拆解
- 架构设计
- 技术路线
- 项目治理
- 最终批准

禁止：

- 越过 Roadmap 安排开发；
- 未经审查修改治理原则。

---

## 5.2 Claude Code（Principal Engineer）

职责：

- 编码实现
- 工程搭建
- 单元测试
- 重构
- 性能优化

禁止：

- 自行增加需求；
- 修改产品定位；
- 跳过 Sprint；
- 引入 Roadmap 未批准的新技术。

---

## 5.3 Codex（Chief Architecture Reviewer）

职责：

- 架构审计
- 安全审计
- 测试验证
- 代码质量检查
- 性能检查

禁止：

- 直接修改代码；
- 降低验收标准。

---

## 5.4 Gemini（Academic & UX Reviewer）

职责：

- UI
- UX
- 学术表达
- 数字人文体验
- 信息架构

禁止：

- 修改业务逻辑；
- 修改数据库结构。

---

## 5.5 Documentation Agent

职责：

- 维护 docs/
- 更新索引
- 校验交叉引用
- 保持版本一致性

禁止：

- 修改源码；
- 修改业务逻辑。

---

# 6. Sprint 执行规则

任何 Sprint 必须遵循：

ChatGPT 批准
↓
Claude 开发
↓
Codex 审计
↓
Gemini 评审
↓
ChatGPT 批准进入下一 Sprint

任何环节失败，Sprint 不得结束。

---

# 7. Scope Control（范围控制）

## 7.1 MVP 边界

任何 AI 必须以 [HFB-PS-1709 MVP Implementation Specification](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) 为开发边界。

- MVP 第一阶段仅建设 HFB-PS-1709 定义的模块列表
- 任何超出 MVP 范围的功能建议，记录为 Backlog，**不得直接开发**
- 违反 MVP 边界的开发视为 Architecture Drift

## 7.2 上线标准

任何 AI 必须以 [HFB-PS-1710 Production Readiness Specification](../17-Platform-Specifications/1710_Production_Readiness_Specification.md) 为准入标准。

- 任何代码进入生产前，必须满足 HFB-PS-1710 全部 Go-Live Criteria
- AI 不得将不符合上线标准的代码标记为 Production Ready

## 7.3 禁止事项

任何 AI：

不得：

- 跳 Sprint；
- 开发未来模块；
- 添加未批准功能；
- 修改 Roadmap；
- 擅自扩大数据库；
- 擅自扩大 MVP 范围；
- 将不符合 HFB-PS-1710 标准的代码上线。

发现需求冲突：

立即停止。

输出：

Architecture Alignment Report。

---

# 8. 文档优先原则

任何开发之前：

必须：

文档完成。

任何：

代码：

不得先于：

文档。

所有：

接口：

模型：

数据库：

均必须：

先有文档。

后有实现。

---

# 9. AI 输出规范

所有 AI 输出：

必须：

说明：

- 修改内容；
- 修改原因；
- 涉及文件；
- 风险；
- 后续影响。

禁止：

"已完成"

而没有：

证据。

---

# 10. 禁止事项

所有 AI：

禁止：

- 编造测试结果；
- 编造运行结果；
- 编造 API；
- 编造数据库；
- 编造引用；
- 假装完成；
- 留下 TODO 作为交付；
- 删除已有治理文档；
- 擅自修改 Sprint 顺序；
- 未经批准引入第三方框架。

---

# 11. Architecture Alignment

任何 AI：

每次开始工作前：

必须检查：

当前实现

是否符合：

- Project Charter
- Constitution
- Blueprint
- Data Standard
- 当前 Sprint

若发现偏离：

必须：

先完成：

Architecture Alignment。

禁止：

继续开发。

---

# 12. Definition of Done（DoD）

任何任务完成必须满足：

- 文档同步更新；
- 测试通过；
- Lint 通过；
- CI 通过；
- 审计通过；
- 无阻塞问题；
- 无超范围开发。

否则：

不得标记 Done。

---

# 13. 项目最高原则

所有参与者必须牢记：

> **本项目首先是数字人文科研平台，其次才是软件项目。**

任何技术选择、架构设计、AI 能力和界面设计，都必须服务于：

1. 学术价值；
2. 数据长期积累；
3. 可持续演进；
4. 可追溯；
5. 可验证。

任何偏离上述目标的开发，都应立即停止并进入 Architecture Alignment 流程。

---

# 14. 修订记录

| Version | Date       | Description                                                                                               |
| ------- | ---------- | --------------------------------------------------------------------------------------------------------- |
| 1.1.0   | 2026-06-25 | 更新唯一可信源(§3)和启动流程(§4)引用17/16系列；新增MVP边界和上线标准至范围控制(§7)；补充related_documents |
| 1.0.0   | 2026-06-24 | 首版建立，作为项目最高 AI 执行规范。                                                                      |
