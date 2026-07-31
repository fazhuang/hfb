---
title: Product Roadmap
document_id: HFB-PRD-0001
version: 0.2.0
status: Draft
owner: Product Owner
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-25
scope: Product Planning
priority: P0
related_documents:
  - HFB-GOV-0001 Project Charter
  - HFB-ARC-0201 Technical Blueprint
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Product Roadmap — 产品路线图

> 本文档为产品路线图概览。详细产品规格以 **17-Platform-Specifications** 为准。
>
> **MVP 边界见 HFB-PS-1709，上线准入标准见 HFB-PS-1710。**

---

> **版本:** v0.2.0
> **状态:** Draft
> **适用范围:** 产品 · 技术 · 设计
> **维护者:** 产品负责人

## 1. 产品最高依据

本路线图受以下治理文档约束：

| 依据                                                                                             | document_id  | 作用                        |
| ------------------------------------------------------------------------------------------------ | ------------ | --------------------------- |
| [MVP Implementation](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)     | HFB-PS-1709  | MVP 边界 — 做什么、不做什么 |
| [Production Readiness](../17-Platform-Specifications/1710_Production_Readiness_Specification.md) | HFB-PS-1710  | 上线准入标准                |
| [Project Charter](../00-governance/0001-project-charter.md)                                      | HFB-GOV-0001 | 使命、愿景、范围            |
| [Technical Blueprint](../02-architecture/0201_Technical_Blueprint.md)                            | HFB-ARC-0201 | 技术架构                    |

## 2. MVP Sprint 规划

以 HFB-PS-1709 为边界，MVP 建设 11 个模块：

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

**GraphRAG 不属于 MVP。** Neo4j、Milvus、GraphRAG 仅在 Roadmap 对应 Sprint 引入，MVP 阶段仅预留接口。

## 3. MVP 非建设范围

第一阶段不建设（详见 HFB-PS-1709 第四章）：

- APP、微信小程序
- VR/AR 展示、数字博物馆
- 自动论文生成、多 Agent 自主科研
- 大规模数据开放接口

## 4. 路线图总览

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
gantt
  title 皇甫谧数字人文平台 · 路线图
  dateFormat  YYYY-MM-DD
  tickInterval 1month
  axisFormat  %m月

  section Sprint 0 — 文档奠基
  项目章程与宪法       :done, s0a, 2026-06-24, 2026-06-28
  全栈文档体系         :done, s0b, 2026-06-24, 2026-06-28
  Prompt 工程体系      :active, s0c, 2026-06-26, 2026-06-28

  section Sprint 1 — 基础骨架
  项目初始化与 CI       :s1a, 2026-06-29, 2026-07-05
  数据库设计与迁移      :s1b, 2026-06-29, 2026-07-05
  API 框架搭建          :s1c, 2026-07-03, 2026-07-12
  用户认证与授权        :s1d, 2026-07-06, 2026-07-12

  section Sprint 2 — Version Center
  Version Center 实现   :s2a, 2026-07-13, 2026-07-26

  section Sprint 3 — Person + Book Center
  Person Center 实现    :s3a, 2026-07-27, 2026-08-09
  Book Center 实现      :s3b, 2026-07-27, 2026-08-09

  section Sprint 4 — Passage Center
  Passage Center 实现   :s4a, 2026-08-10, 2026-08-23

  section Sprint 5 — Knowledge Graph
  Knowledge Graph 基础  :s5a, 2026-08-24, 2026-09-06

  section Sprint 6 — Unified Search
  Unified Search 实现   :s6a, 2026-09-07, 2026-09-20

  section Sprint 7 — AI Research Workspace
  AI Research Workspace :s7a, 2026-09-21, 2026-10-04

  section Sprint 8 — Dashboard
  Dashboard + Admin     :s8a, 2026-10-05, 2026-10-18

  section Sprint 9 — Integration
  平台集成与测试        :s9a, 2026-10-19, 2026-11-01

  section Sprint 10 — Production Readiness
  HFB-PS-1710 上线验收  :milestone, s10a, 2026-11-08, 0d
```

## 5. 上线准入

**上线以 HFB-PS-1710 为准入标准。** 任何未满足 HFB-PS-1710 全部 Go-Live Criteria 的版本，不得进入生产环境。

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-25
