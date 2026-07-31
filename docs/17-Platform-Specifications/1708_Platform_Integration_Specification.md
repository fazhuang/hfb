---
title: Platform Integration Specification
document_id: HFB-PS-1708
version: 1.0.0
status: Approved
owner: Architecture Committee
reviewer: Chief System Architect
effective_date: 2026-06-24
scope: Platform Integration
priority: P0
related_documents:
  - HFB-PS-1702 Platform Information Architecture Specification
  - HFB-PS-1705 AI Research Workspace Specification
  - HFB-PS-1706 Unified Search & Knowledge Discovery Specification
  - HFB-PS-1707 Visualization & Knowledge Graph Specification
  - HFB-DEV-0504 API Design Standard
  - HFB-ARC-0201 Technical Blueprint
  - HFB-PS-1709 MVP Implementation Specification
---

# Platform Integration Specification

## 平台集成规格书

> 本规格书定义《皇甫谧数字人文与中医经典智能研究平台》的统一集成架构（Platform Integration Architecture）。
>
> 平台采用统一能力中心（Capability Center）架构，而非模块孤岛架构。
>
> 所有业务模块必须通过统一服务完成通信，不允许出现模块间直接依赖。

---

# 第一章 设计目标

平台不是多个系统拼接。

平台是：

> **一个统一的数据平台、知识平台、AI 平台和科研平台。**

因此：

所有模块必须：

共享数据。

共享 Graph。

共享 AI。

共享权限。

共享 Workspace。

形成统一平台。

---

# 第二章 Integration Principles

统一遵循：

## Single Source of Truth

任何对象：

只有一个数据源。

禁止：

复制数据。

---

## Service Oriented

所有能力：

通过 Service 提供。

禁止：

模块之间直接访问数据库。

---

## Event Driven

对象变化：

统一发布 Event。

其它模块：

监听 Event。

---

## AI Shared

AI：

统一调用：

AI Service。

禁止：

模块单独接入 LLM。

---

# 第三章 Capability Center

平台统一能力中心：

```text
Authentication Center

Knowledge Center

Graph Center

Search Center

Evidence Center

Citation Center

AI Center

Visualization Center

Research Center
```

所有模块：

调用能力中心。

---

# 第四章 Integration Architecture

统一架构：

```text
UI

↓

API Gateway

↓

Business Service

↓

Capability Center

↓

Database
```

禁止：

UI：

直接访问数据库。

---

# 第五章 Object Integration

统一对象：

```text
Version

Book

Passage

Person

Institution

Evidence

Citation

Project

Research
```

统一：

CRUD。

统一：

ID。

统一：

Graph。

---

# 第六章 Event Bus

统一事件：

例如：

```text
VersionCreated

↓

PassageUpdated

↓

CitationAdded

↓

EvidenceVerified

↓

ResearchPublished
```

统一广播。

统一监听。

---

# 第七章 AI Integration

AI：

统一：

AI Gateway。

包括：

LLM。

Embedding。

GraphRAG。

Translation。

Review。

统一接口。

---

# 第八章 Graph Integration

Graph：

唯一：

Graph Service。

所有模块：

不得：

自行维护 Graph。

---

# 第九章 Search Integration

统一：

Search Service。

包括：

全文。

向量。

Graph。

Evidence。

AI。

统一检索。

---

# 第十章 Workspace Integration

Workspace：

统一管理：

Research Session。

Task。

Notes。

History。

AI。

所有模块共享。

---

# 第十一章 API Integration

统一：

REST。

未来：

GraphQL。

所有接口：

OpenAPI。

自动文档。

统一版本。

---

# 第十二章 Identity Integration

统一身份：

SSO（预留）。

RBAC。

Workspace。

API Token。

统一认证。

---

# 第十三章 Data Flow

统一：

```text
User

↓

API

↓

Business

↓

Capability

↓

Database

↓

Event

↓

AI

↓

Workspace
```

全过程统一。

---

# 第十四章 External Integration

支持：

IIIF。

OpenAlex。

Crossref。

ORCID。

CIDOC CRM。

TEI。

MCP。

未来：

统一接入。

---

# 第十五章 Monitoring

统一：

Log。

Metrics。

Tracing。

Audit。

AI Log。

Research Log。

统一监控。

---

# 第十六章 Error Handling

统一：

Error Code。

Error Message。

Retry。

Fallback。

Log。

禁止：

模块自行定义错误。

---

# 第十七章 Performance

统一要求：

API。

缓存。

Graph。

Search。

AI。

全部：

可横向扩展。

---

# 第十八章 Security

统一：

权限。

Token。

日志。

审计。

Prompt 安全。

数据脱敏。

统一实现。

---

# 第十九章 验收标准

平台必须：

Capability。

Event。

Workspace。

Search。

Graph。

AI。

API。

统一。

全部通过。

---

# 第二十章 后续约束

所有新增模块：

禁止：

新建：

Search。

Graph。

AI。

Workspace。

统一复用平台能力。

---

# 修订记录

| Version | Date       | Description                                                    |
| ------- | ---------- | -------------------------------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，定义平台统一集成架构，作为所有业务模块集成开发规范。 |
