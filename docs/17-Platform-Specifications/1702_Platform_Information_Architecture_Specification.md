---
title: Platform Information Architecture Specification
document_id: HFB-PS-1702
version: 1.0.0
status: Approved
owner: Product Committee
reviewer: Chief Product Architect
effective_date: 2026-06-24
scope: Platform Information Architecture
priority: P0
related_documents:
  - HFB-PS-1701 Version Center Product Specification
  - HFB-RF-1601 Digital Humanities Research Framework
  - HFB-DOM-0809 Master Knowledge Graph Model
  - HFB-UI-0601 Design System
  - HFB-GOV-0001 Project Charter
  - HFB-PS-1709 MVP Implementation Specification
---

# Platform Information Architecture Specification

## 平台信息架构规格书

> 本规格书定义《皇甫谧数字人文与中医经典智能研究平台》的整体信息架构（Information Architecture，IA）。
>
> Information Architecture 是平台产品设计、UI 设计、数据库设计、知识图谱设计及 AI 工作流设计的统一基础。
>
> 平台所有页面、模块、数据对象及 AI 服务均应遵循本规格书。

---

# 第一章 设计目标

平台不是传统意义上的网站。

平台是：

> **数字人文智能科研平台（Digital Humanities Research Platform）**

因此平台信息架构必须满足：

- 学术研究
- 数据管理
- AI 协同
- 知识图谱
- 国际传播

五类业务统一运行。

平台任何新增功能均不得破坏整体 IA。

---

# 第二章 IA 设计原则

平台遵循：

## Object First

围绕知识对象组织系统。

而不是围绕菜单组织系统。

---

## Research First

所有功能服务科研。

避免形成资料展示网站。

---

## AI Native

所有模块默认支持 AI。

而不是后期增加 AI。

---

## Graph Native

所有对象默认进入知识图谱。

Graph 为平台统一数据中心。

---

## Global First

所有对象支持：

- 中文
- English

未来支持：

- 日本语
- 한국어

国际化作为默认能力。

---

# 第三章 平台总体架构

平台采用四层架构：

```text
Presentation Layer

↓

Business Layer

↓

Knowledge Layer

↓

Infrastructure Layer
```

---

## 第一层

Presentation

包括：

- Web
- Mobile
- Digital Exhibition
- AI Workspace

---

## 第二层

Business

包括：

- Version
- Research
- Search
- Graph
- Dashboard

---

## 第三层

Knowledge

包括：

- Knowledge Graph
- Vector
- Documents
- Metadata
- Citation
- Evidence

---

## 第四层

Infrastructure

包括：

- PostgreSQL
- Object Storage
- Elasticsearch
- Graph Database
- Vector Database
- AI Services

---

# 第四章 一级导航

平台统一一级导航：

```text
首页

研究中心

知识中心

版本中心

人物中心

文献中心

AI工作台

数据中心

系统管理
```

一级导航固定。

不得增加超过九项。

---

# 第五章 二级导航

研究中心：

- Research Workspace
- Research Projects
- Notes
- Publications

知识中心：

- Knowledge Graph
- Concepts
- Evidence
- Citation

版本中心：

- Version Library
- Compare
- Timeline
- Genealogy

人物中心：

- Huangfu Mi
- Historical Figures
- Academic Network

文献中心：

- Books
- Passages
- Images
- Archives

AI 工作台：

- Academic Chat
- AI Research
- AI Review
- AI Translation

数据中心：

- Import
- Export
- Statistics
- Visualization

系统管理：

- Users
- Roles
- Permissions
- Configuration

---

# 第六章 页面组织原则

平台页面统一划分：

```text
Dashboard

↓

List

↓

Detail

↓

Workspace

↓

Visualization

↓

Settings
```

所有模块保持一致。

禁止每个模块采用不同页面逻辑。

---

# 第七章 Knowledge Object 架构

平台统一对象。

一级对象：

```text
Version

Book

Passage

Person

Institution

Concept

Evidence

Citation

Research
```

所有对象：

具有唯一ID。

统一生命周期。

统一权限。

统一 Graph。

---

# 第八章 Workspace 架构

平台所有科研均在 Workspace 完成。

Workspace 固定四栏：

```text
Knowledge Navigator

↓

Document Viewer

↓

AI Assistant

↓

Evidence Panel
```

所有研究模块统一。

避免不同模块不同布局。

---

# 第九章 Graph 架构

Graph 不属于某个模块。

Graph 属于平台。

统一提供：

- Entity Graph
- Relation Graph
- Timeline Graph
- Citation Graph
- Evidence Graph

所有模块共享。

---

# 第十章 Search 架构

平台只有一个 Search。

支持：

统一搜索：

- 文献
- 人物
- 版本
- Passage
- 引文
- 证据
- 图片
- AI回答

搜索结果统一展示。

---

# 第十一章 Dashboard 架构

Dashboard 分三级：

系统 Dashboard

↓

研究 Dashboard

↓

对象 Dashboard

每一级保持一致设计。

---

# 第十二章 Navigation Flow

平台默认流程：

```text
Dashboard

↓

Search

↓

Knowledge Object

↓

Workspace

↓

Research

↓

Export
```

任何研究均可回到 Dashboard。

---

# 第十三章 数据组织

平台统一采用：

```text
Entity

↓

Metadata

↓

Relations

↓

Evidence

↓

Citation

↓

AI Layer
```

所有模块保持一致。

---

# 第十四章 AI Integration

AI 默认集成：

每个页面。

包括：

- Summary
- QA
- Citation
- Evidence
- Compare
- Translate

无需单独进入 AI。

---

# 第十五章 国际化

所有对象支持：

- Unicode
- 多语言标题
- 多语言描述
- 多语言引用
- 多语言检索

默认支持国际化。

---

# 第十六章 UI 一致性

所有页面统一：

Header

↓

Breadcrumb

↓

Toolbar

↓

Content

↓

AI Panel

↓

Footer

禁止模块自定义布局。

---

# 第十七章 可扩展性

任何新增模块必须：

符合：

- IA
- Graph
- Workspace
- Search
- Permission

否则不得上线。

---

# 第十八章 非功能要求

要求：

- 响应式设计
- 深色模式
- 国际化
- 无障碍访问
- 全局快捷键
- 全局搜索
- AI 常驻

统一体验。

---

# 第十九章 验收标准

平台 IA 验收包括：

- 导航一致
- Workspace 一致
- Graph 一致
- Search 一致
- Dashboard 一致
- Object 一致
- 权限一致

全部通过。

---

# 第二十章 后续规范引用

所有后续产品规格书必须遵循本 IA。

包括：

- 页面设计
- API
- 数据模型
- Graph
- AI
- 权限

不得违反本规格。

---

# 修订记录

| Version | Date       | Description                                                      |
| ------- | ---------- | ---------------------------------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，定义平台统一信息架构，作为所有产品模块开发的基础规范。 |
