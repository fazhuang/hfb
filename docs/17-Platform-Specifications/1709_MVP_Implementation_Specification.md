---
title: MVP Implementation Specification
document_id: HFB-PS-1709
version: 1.1.0
status: Approved
owner: Product Committee
reviewer: Chief Product Architect
effective_date: 2026-06-24
scope: Minimum Viable Product (MVP)
priority: P0
related_documents:
  - HFB-PS-1701 Version Center Product Specification
  - HFB-PS-1705 AI Research Workspace Specification
  - HFB-PS-1708 Platform Integration Specification
  - HFB-ARC-0201 Technical Blueprint
  - HFB-GOV-0001 Project Charter
  - HFB-GOV-0002 Project Constitution
  - HFB-PS-1710 Production Readiness Specification
---

# MVP Implementation Specification

## MVP 实施规格书

> 本规格书定义《皇甫谧数字人文与中医经典智能研究平台》第一阶段（MVP）的建设范围、实施原则、模块边界、验收目标及非目标（Out of Scope）。
>
> 本规格书是整个项目开发阶段最重要的产品控制文档。
>
> **任何未列入 MVP 范围的功能，不得进入第一阶段开发。**

---

# 第一章 MVP 建设目标

MVP 的目标不是建设完整平台。

而是建设：

> **可投入科研试运行的数字人文研究平台。**

MVP 必须满足：

- 能开展真实科研
- 能支撑课程教学
- 能支撑课题研究
- 能展示平台能力
- 能持续迭代

而不是一次完成全部规划。

---

# 第二章 MVP 建设原则

平台统一遵循：

## Core First

先完成核心能力。

再扩展外围能力。

---

## Research First

优先科研价值。

不追求功能数量。

---

## Reuse First

优先复用已有能力。

禁止重复开发。

---

## Evidence First

所有 AI 能力必须建立在：

Evidence + Citation + GraphRAG

基础之上。

---

## Production Ready

所有进入 MVP 的功能：

均应达到可持续维护标准。

禁止 Demo 代码。

---

# 第三章 MVP 范围

MVP 第一阶段仅建设：

```text
用户与权限

Version Center

Passage Center

Person Center

Book Center

Knowledge Graph

Unified Search

AI Research Workspace

Research Workspace

Dashboard

System Management
```

以上构成 MVP 最小闭环。

---

# 第四章 MVP 非建设范围

第一阶段不建设：

- APP
- 微信小程序
- VR 展示
- AR 展示
- 数字博物馆
- 国际开放平台
- 自动论文生成
- 多 Agent 自动科研
- 大规模数据开放接口

以上功能全部延期。

---

# 第五章 MVP 数据范围

首批数据控制：

```text
皇甫谧

↓

《针灸甲乙经》

↓

主要版本

↓

代表人物

↓

代表论文

↓

代表馆藏
```

禁止：

一次导入全部历史资料。

采用：

滚动建设。

---

# 第六章 MVP AI 能力

MVP AI 包括：

- 学术问答
- Passage 检索
- Version 比较
- 自动引文
- 自动摘要
- 学术翻译
- Evidence 检索

暂不支持：

自主科研。

---

# 第七章 MVP Graph

Graph 第一阶段：

包括：

- Person
- Version
- Book
- Passage
- Evidence
- Citation

后续逐步扩展。

---

# 第八章 MVP UI

统一页面：

首页。

Dashboard。

Workspace。

Knowledge。

Search。

Admin。

保持：

简洁。

一致。

科研优先。

---

# 第九章 MVP API

必须完成：

全部核心 API。

统一：

OpenAPI。

Swagger。

权限。

日志。

测试。

达到生产标准。

---

# 第十章 MVP 数据质量

所有数据：

必须：

- 来源明确
- 可追溯
- 有 Citation
- 有 Evidence
- 有审核

禁止：

AI 编造数据。

---

# 第十一章 MVP 测试要求

必须完成：

单元测试。

API 测试。

E2E。

权限测试。

AI 测试。

Graph 测试。

Search 测试。

覆盖核心流程。

---

# 第十二章 MVP 安全要求

必须完成：

RBAC。

JWT。

输入校验。

操作日志。

Prompt Injection 防护。

权限隔离。

数据备份。

达到上线要求。

---

# 第十三章 MVP 性能要求

平台目标：

- 首屏 ≤2 秒
- API ≤500ms（常规查询）
- Search ≤2 秒
- Graph 流畅
- AI 流式输出
- 支持十万级知识对象

---

# 第十四章 MVP 验收流程

统一流程：

```text
开发完成

↓

单元测试

↓

集成测试

↓

产品验收

↓

学术验收

↓

试运行

↓

正式上线
```

任何阶段失败：

不得进入下一阶段。

---

# 第十五章 MVP 成功标准

平台应能够完成：

研究者登录。

↓

检索资料。

↓

阅读版本。

↓

查看 Passage。

↓

查看 Graph。

↓

AI 分析。

↓

生成研究笔记。

↓

导出成果。

形成完整科研闭环。

---

# 第十六章 Claude 开发原则

Claude Code：

仅开发：

MVP 范围。

禁止：

自行增加模块。

禁止：

修改平台架构。

禁止：

跳过产品规格。

所有开发：

必须遵循：

17 系列规格。

---

# 第十七章 Codex 验收原则

Codex：

重点审查：

产品一致性。

权限。

API。

AI。

Graph。

Workspace。

Evidence。

不允许：

实现偏离规格。

---

# 第十八章 Gemini 产品评审原则

Gemini：

负责：

产品体验。

科研流程。

UI。

交互。

信息架构。

国际化。

提供产品优化建议。

---

# 第十九章 MVP 完成标准

满足：

功能完整。

架构统一。

数据可信。

AI 可解释。

Graph 完整。

测试通过。

文档齐全。

方可宣布：

MVP 完成。

---

# 第二十章 第二阶段规划

MVP 完成后：

进入 V2。

重点建设：

- 国际平台
- 多 Agent
- IIIF
- 数字博物馆
- AI 科研助手
- 开放平台
- 国际合作

不纳入 MVP。

---

# 修订记录

| Version | Date       | Description                                                                         |
| ------- | ---------- | ----------------------------------------------------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，定义平台 MVP 建设范围、实施边界及验收标准，作为第一阶段开发唯一产品依据。 |
