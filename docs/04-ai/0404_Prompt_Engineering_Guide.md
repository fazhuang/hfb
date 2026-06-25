---
title: Prompt Engineering Guide
document_id: HFB-AI-0404
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: AI Prompt Engineering
priority: P0
related_documents:
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-AI-0401 AI Engineering Standard
  - HFB-AI-0402 RAG Specification
  - HFB-AI-0403 GraphRAG Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Prompt Engineering Guide
## Prompt 工程规范

> 本文档规定《皇甫谧数字人文与中医经典智能研究平台》所有 Prompt 的设计、管理、版本控制、测试、发布及维护规范。
>
> **Prompt 是项目正式资产（Project Asset），与源代码具有同等重要性。**

---

# 第一章 编制目的

建立统一 Prompt 工程体系，实现：

- Prompt 可维护
- Prompt 可测试
- Prompt 可版本化
- Prompt 可回滚
- Prompt 可复用
- Prompt 可评估

所有 AI 调用必须遵循本规范。

---

# 第二章 Prompt 定位

Prompt 不是一句自然语言。

Prompt 是：

> **AI 软件工程中的业务逻辑配置（Business Logic Configuration）**

Prompt 与代码一样：

- 必须版本管理；
- 必须评审；
- 必须测试；
- 必须审计。

---

# 第三章 Prompt 分类

平台 Prompt 分为八类。

| 编号 | 类型 | 说明 |
|------|------|------|
| P01 | System Prompt | 系统角色 |
| P02 | Workflow Prompt | 工作流 |
| P03 | Retrieval Prompt | 检索 |
| P04 | Analysis Prompt | 分析 |
| P05 | Generation Prompt | 内容生成 |
| P06 | Review Prompt | 审核 |
| P07 | Evaluation Prompt | 评估 |
| P08 | Agent Prompt | 智能体 |

不得混用。

---

# 第四章 Prompt 生命周期

统一流程：

```text
需求

↓

设计

↓

评审

↓

测试

↓

发布

↓

监控

↓

优化

↓

归档
```

任何 Prompt：

不得跳过测试。

---

# 第五章 Prompt 编码规范

每个 Prompt 必须拥有唯一编号。

格式：

```
P-0404-0001
```

说明：

- P：Prompt
- 0404：所属规范
- 0001：流水号

不得重复。

---

# 第六章 Prompt 元数据

所有 Prompt 必须包含：

| 字段 | 必填 |
|------|------|
| Prompt ID | √ |
| Name | √ |
| Version | √ |
| Author | √ |
| Reviewer | √ |
| Created Date | √ |
| Updated Date | √ |
| Applicable Model | √ |
| Input Schema | √ |
| Output Schema | √ |
| Status | √ |

---

# 第七章 Prompt 目录规范

统一存放：

```text
docs/
└──09-prompts/
    ├──Claude/
    ├──Codex/
    ├──Gemini/
    ├──GPT/
    ├──Shared/
    ├──Templates/
    └──Archive/
```

禁止：

Prompt 分散在代码目录。

---

# 第八章 Prompt 结构规范

统一结构：

```text
Role

↓

Objective

↓

Context

↓

Constraints

↓

Input

↓

Workflow

↓

Output

↓

Acceptance Criteria
```

不得缺项。

---

# 第九章 Prompt 输入规范

输入必须：

- 明确
- 完整
- 可验证
- 有上下文

禁止：

依赖聊天历史。

必须引用：

- Manifest
- Context Package
- Sprint
- Blueprint

---

# 第十章 Prompt 输出规范

输出必须：

包含：

- 执行结果
- 修改内容
- 涉及文件
- 风险
- 下一步建议（如适用）

禁止：

"已完成"

但没有：

实际结果。

---

# 第十一章 Prompt 版本管理

采用：

Semantic Version。

例如：

```
1.0.0

1.1.0

1.2.0

2.0.0
```

重大修改：

必须：

更新：

Prompt History。

---

# 第十二章 Prompt 测试

每个 Prompt：

必须：

至少：

包含：

- 正常测试
- 边界测试
- 错误输入测试
- 空输入测试
- 超长输入测试

通过后：

方可发布。

---

# 第十三章 Prompt 审计

Codex：

负责：

Prompt 审计。

检查：

- 结构
- 一致性
- 可执行性
- 是否越权
- 是否偏离 Roadmap

---

# 第十四章 Prompt 安全

所有 Prompt：

必须防护：

- Prompt Injection
- Jailbreak
- 越权调用
- 敏感信息泄露
- 未授权操作

禁止：

AI 修改治理文档。

---

# 第十五章 Prompt 与 Sprint

每个 Sprint：

必须拥有：

- Claude Prompt
- Codex Audit Prompt
- Gemini Review Prompt
- GPT Approval Prompt

统一编号。

统一版本。

---

# 第十六章 Prompt 与 Context

Prompt：

不得依赖：

长期聊天上下文。

统一读取：

- repo.manifest.json
- AI_BOOTSTRAP.md
- 当前 Sprint Context
- 当前 ADR

---

# 第十七章 Prompt KPI

平台目标：

| 指标 | 标准 |
|------|------|
| 执行成功率 | ≥95% |
| 输出一致率 | ≥95% |
| Prompt 可复用率 | ≥90% |
| Prompt 覆盖率 | 100% |

---

# 第十八章 Prompt 红线

禁止：

- Prompt 硬编码路径
- Prompt 硬编码模型
- Prompt 跳过 AI Execution Protocol
- Prompt 修改超出授权范围
- Prompt 绕过 Sprint
- Prompt 绕过审计

违反任一项不得投入使用。

---

# 第十九章 Prompt 变更流程

修改 Prompt 必须：

1. 提交变更说明；
2. 更新版本号；
3. 更新 Prompt History；
4. 重新测试；
5. Codex 审计；
6. 项目负责人批准。

---

# 第二十章 成功标准

平台所有 Prompt：

- 可管理
- 可审计
- 可追溯
- 可测试
- 可复用
- 可持续维护

Prompt Library 成为平台正式资产，与代码仓库同步管理。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台 Prompt 工程最高规范。 |