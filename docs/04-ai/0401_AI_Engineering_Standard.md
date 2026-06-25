---
title: AI Engineering Standard
document_id: HFB-AI-0401
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: AI Architecture
priority: P0
related_documents:
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-GOV-0002 Project Constitution
  - HFB-ARC-0201 Technical Blueprint
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-PS-1705 AI Research Workspace Specification
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# AI Engineering Standard
## AI 工程规范

> 本文档定义《皇甫谧数字人文与中医经典智能研究平台》AI 子系统的总体工程规范。
>
> 它是所有 AI 服务、RAG、GraphRAG、Agent、Prompt、模型管理、推理服务和 AI 应用开发的最高技术标准。

---

# 第一章 建设目标

AI 系统建设目标不是构建聊天机器人。

平台 AI 的定位是：

> **面向数字人文研究的智能研究基础设施（AI Research Infrastructure）**

AI 的职责包括：

- 学术辅助研究
- 古籍智能检索
- 文献知识发现
- 多版本比对
- 文献引用分析
- 人物关系分析
- 学术传播辅助
- 研究成果生成辅助

AI 不参与医学诊断，不提供临床建议。

---

# 第二章 AI 总体架构

平台采用四层 AI 架构。

```text
Application Layer
        │
Inference Layer
        │
Knowledge Layer
        │
Model Layer
```

---

## 2.1 Application Layer

负责：

- AI 助手
- 学术问答
- 智能检索
- 多版本比较
- 自动摘要
- 文献推荐

---

## 2.2 Inference Layer

负责：

- Prompt 编排
- Workflow
- RAG
- GraphRAG
- Agent
- Citation Engine

---

## 2.3 Knowledge Layer

负责：

- Ontology
- Entity
- Relation
- Metadata
- Vector Index
- Knowledge Package

---

## 2.4 Model Layer

负责：

统一管理：

- LLM
- Embedding Model
- Reranker
- OCR
- NLP

不得直接由业务调用模型。

---

# 第三章 AI 服务划分

平台 AI 服务统一划分为：

| 服务 | 职责 |
|------|------|
| Chat Service | 学术问答 |
| Search Service | 智能检索 |
| Citation Service | 引文生成 |
| Summarization Service | 自动摘要 |
| Comparison Service | 多版本比对 |
| Recommendation Service | 文献推荐 |
| Extraction Service | 信息抽取 |
| Annotation Service | AI 标注 |

所有 AI 服务均为独立 Service。

---

# 第四章 模型管理规范

平台支持多模型。

统一通过 Model Registry 管理。

每个模型必须记录：

- model_name
- provider
- version
- capability
- context_window
- cost
- status

不得在代码中写死模型名称。

---

# 第五章 Prompt 管理规范

Prompt 属于项目资产。

统一版本管理。

必须记录：

- Prompt ID
- Version
- Author
- Applicable Model
- Last Updated
- Change Log

禁止直接在代码中编写 Prompt。

所有 Prompt 必须存放于：

```text
docs/09-prompts/
```

---

# 第六章 AI 调用规范

所有 AI 调用必须经过统一 AI Gateway。

调用流程：

```text
Application

↓

AI Gateway

↓

Model Router

↓

LLM

↓

Citation Check

↓

Response
```

禁止业务模块直接调用模型 API。

---

# 第七章 RAG 规范

RAG 是平台默认检索方式。

统一流程：

```text
Question

↓

Query Rewrite

↓

Retriever

↓

Reranker

↓

Context Builder

↓

LLM

↓

Citation

↓

Answer
```

所有回答必须携带引用来源。

---

# 第八章 GraphRAG 规范

GraphRAG 不是 MVP。

仅在 Roadmap 指定 Sprint 引入。

GraphRAG 必须依赖：

- Ontology
- Entity
- Relation
- Evidence

不得脱离知识体系独立运行。

---

# 第九章 Agent 规范

Agent 不属于当前阶段。

未来 Agent 必须：

- 可配置
- 可审计
- 可回溯
- 可终止
- 可权限控制

禁止 Agent 直接修改正式数据。

---

# 第十章 AI 输出规范

所有 AI 输出必须包含：

- Answer
- Citation
- Confidence
- Evidence
- Model Version
- Prompt Version
- Generated Time

禁止仅输出自然语言结论。

---

# 第十一章 AI 审核机制

AI 输出统一分三级：

Draft

↓

Human Review

↓

Published

未经人工审核的数据不得进入正式知识库。

---

# 第十二章 AI 安全规范

所有 AI 服务必须：

- 权限验证
- Prompt 注入防护
- 输出过滤
- 敏感信息过滤
- 调用日志
- Token 限流
- 成本统计

---

# 第十三章 AI 可解释性

平台所有 AI 输出必须支持：

- 来源追踪
- 推理路径
- 引文定位
- Prompt 版本
- 模型版本

任何回答都必须可以追溯。

---

# 第十四章 AI 性能指标

平台目标：

| 指标 | 标准 |
|------|------|
| 首次响应 | ≤3 秒 |
| 检索成功率 | ≥95% |
| 引文准确率 | ≥99% |
| AI 可追溯率 | 100% |
| Prompt 版本记录 | 100% |

---

# 第十五章 AI 生命周期

AI 能力上线流程：

需求

↓

设计

↓

开发

↓

测试

↓

学术验证

↓

上线

↓

持续评估

任何 AI 能力均不得跳过学术验证。

---

# 第十六章 AI 工程红线

禁止：

- AI 直接修改知识库
- 无引用回答
- 无证据推理
- 使用未登记模型
- Prompt 硬编码
- 跳过 AI Gateway
- 跳过审核流程

违反任一项不得上线。

---

# 第十七章 AI 技术演进路线

依据 [HFB-PS-1709 MVP](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)：

| Phase | Sprint | 内容 | 状态 |
|---|---|---|---|
| Phase 1 | Sprint 1~5 | 预留 AI 能力接口 | MVP |
| Phase 2 | Sprint 6 | Embedding | MVP |
| Phase 3 | Sprint 7 | OCR | MVP |
| Phase 4 | Sprint 8 | RAG 第一版 | MVP |
| Phase 5 | Sprint 9 | Knowledge Graph 基础 | MVP |
| Phase 6 | Sprint 10 | GraphRAG | Post-MVP |
| Phase 7 | Sprint 11 | Research Agent | Post-MVP |
| Phase 8 | 后续 | Multi-Agent | Post-MVP |

MVP AI 能力范围参见 [HFB-PS-1705 AI Research Workspace](../17-Platform-Specifications/1705_AI_Research_Workspace_Specification.md)。

# 第十八章 MVP 与上线约束

## 18.1 MVP AI 边界

MVP 阶段 AI 能力以 [HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) 第六章为边界：

- 学术问答、Passage 检索、Version 比较、自动引文、自动摘要、学术翻译、Evidence 检索
- **不包含**：自主科研、GraphRAG、Neo4j、Milvus

## 18.2 AI 上线标准

所有 AI 服务上线必须满足 [HFB-PS-1710](../17-Platform-Specifications/1710_Production_Readiness_Specification.md) 第五章 AI 要求：

- 支持 Evidence、Citation、GraphRAG、Explain、History
- 禁止编造文献、人物、版本、引用

---

# 第十九章 修订规则

新增：

模型

Prompt

AI 服务

推理流程

Agent

必须同步更新：

- AI Engineering Standard
- Technical Blueprint
- Context Package
- Prompt Library
- ADR

未经批准不得实施。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 新增第十八章(MVP与上线约束)；更新第十七章为分阶段表格式；更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台 AI 工程最高规范。 |