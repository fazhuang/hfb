---
title: Code Review Standard
document_id: HFB-DEV-0507
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Code Review & Technical Audit
priority: P0
related_documents:
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-DEV-0501 Development Specification
  - HFB-DEV-0506 Testing Standard
  - HFB-SEC-0701 Acceptance Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Code Review Standard
## 代码审查规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的统一代码审查标准。
>
> 本平台采用 **AI + 人工** 双重审查机制，确保所有代码满足软件工程规范、数字人文规范及学术研究规范。

---

# 第一章 编制目标

建立统一代码审查体系，实现：

- 保证代码质量
- 保证架构一致性
- 保证数据安全
- 保证 AI 输出可信
- 保证文档同步
- 保证长期可维护

任何代码未经 Review，不得进入主分支。

---

# 第二章 审查原则

代码审查遵循：

- Architecture First
- Security First
- Academic First
- Documentation First
- Test First

任何违反项目治理文档的代码，一律退回。

---

# 第三章 审查流程

统一执行流程：

```text
开发完成

↓

Claude 自检

↓

Codex 技术审计

↓

Gemini 学术/UI评审

↓

GPT 最终审批

↓

Merge
```

任何环节失败：

不得进入下一阶段。

---

# 第四章 Claude 自检

Claude 必须完成：

- 编译检查
- 类型检查
- 单元测试
- Lint
- 文档同步
- 自查报告

Claude 不得声明：

"全部完成"

而没有运行测试。

---

# 第五章 Codex 技术审计

Codex 是：

平台首席技术审计 AI。

负责：

- 架构一致性
- 代码规范
- 数据库
- API
- 安全
- 性能
- 测试质量
- Roadmap 一致性

重点检查：

是否发生 Architecture Drift。

---

# 第六章 Gemini 学术评审

Gemini：

负责：

- UI
- UX
- 数字人文展示
- 学术表达
- 引文格式
- 信息层级
- 可读性

Gemini 不修改代码。

只提出评审意见。

---

# 第七章 GPT 最终审批

GPT：

负责：

- Sprint 范围
- 产品目标
- Roadmap
- 模块边界
- 文档一致性

只有 GPT 批准：

才能：

进入下一 Sprint。

---

# 第八章 审查内容

统一检查：

## 架构

- 是否符合 Blueprint
- 是否符合 ADR
- 是否跨 Sprint

---

## 数据

- Entity
- Relation
- Metadata
- Version

---

## API

- RESTful
- OpenAPI
- DTO

---

## AI

- Prompt
- Citation
- Evidence

---

## UI

- Design System
- Accessibility

---

## 测试

- 覆盖率
- Fixture
- Regression

---

# 第九章 Review Checklist

每个 PR 必须检查：

- 文档更新
- Migration
- API
- Security
- Test
- AI
- Citation
- Metadata
- Context Package

缺一项不得通过。

---

# 第十章 Review 等级

统一：

| 等级 | 含义 |
|------|------|
| P0 | 阻塞上线 |
| P1 | 必须修复 |
| P2 | 建议修复 |
| P3 | 优化建议 |

Merge 前：

P0 = 0

P1 = 0

---

# 第十一章 架构一致性检查

检查：

当前实现

是否符合：

- Project Charter
- Constitution
- Blueprint
- Data Standard
- Sprint

发现偏离：

立即停止开发。

进入：

Architecture Alignment。

---

# 第十二章 文档一致性检查

验证：

代码

↓

文档

↓

Prompt

↓

Context

↓

README

全部一致。

不得：

代码领先文档。

---

# 第十三章 学术一致性检查

验证：

- 引文
- 来源
- Metadata
- Evidence
- 多版本

不得：

AI 编造。

---

# 第十四章 安全审计

验证：

- JWT
- RBAC
- SQL Injection
- XSS
- Upload
- Secret

高危漏洞：

不得上线。

---

# 第十五章 AI 专项审计

验证：

- Prompt
- Model
- Citation
- Hallucination
- Explainability

AI：

必须：

可解释。

---

# 第十六章 Review 报告

统一模板：

```text
Summary

Architecture

Security

Performance

Testing

Documentation

Risks

Blocking Issues

Score
```

统一评分：

100 分制。

---

# 第十七章 Merge 条件

Merge 前必须满足：

- 全部测试通过
- 全部 CI 通过
- P0 = 0
- P1 = 0
- 文档同步
- Sprint 范围一致

否则：

禁止 Merge。

---

# 第十八章 Sprint 验收

每个 Sprint：

必须：

输出：

- Sprint Report
- Review Report
- Test Report
- Architecture Report

永久保存。

---

# 第十九章 Code Review 红线

禁止：

- 无 Review Merge
- 无测试 Merge
- 无文档 Merge
- 跳过 Codex
- 跳过 Gemini
- 跳过 GPT
- 修改治理文档绕过规范

违反任一项：

立即回滚。

---

# 第二十章 修订规则

修改 Code Review Standard 必须同步更新：

- AI Execution Protocol
- Development Specification
- Sprint Template
- Review Template
- Context Package

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台统一代码审查规范。 |