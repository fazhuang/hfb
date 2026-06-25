---
title: API Design Standard
document_id: HFB-DEV-0504
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Backend API
priority: P0
related_documents:
  - HFB-DEV-0501 Development Specification
  - HFB-DEV-0502 Backend Development Standard
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-PS-1708 Platform Integration Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# API Design Standard
## API 设计规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》所有 API 的统一设计标准。
>
> API 不仅服务于 Web 前端，还服务于 AI、知识图谱、RAG、第三方科研平台及未来开放平台。

---

# 第一章 设计原则

平台 API 必须遵循：

- Resource First（资源优先）
- RESTful First
- Version First
- Documentation First
- Security First
- Academic First

API 必须围绕学术资源设计，而不是数据库表。

---

# 第二章 API 资源模型

平台 API 按领域划分。

## 学术资源

```text
/persons
/books
/versions
/chapters
/passages
/papers
/images
/documents
```

---

## 学术关系

```text
/relations
/citations
/evidence
/timeline
```

---

## AI

```text
/ai/search
/ai/chat
/ai/retrieve
/ai/compare
```

---

## 系统

```text
/auth
/users
/roles
/settings
/health
/version
```

---

# 第三章 URL 规范

统一：

```text
/api/v1/
```

例如：

```text
GET /api/v1/persons

GET /api/v1/books

GET /api/v1/passages

GET /api/v1/papers
```

禁止：

```text
/getPerson

/queryBook

/findPaper
```

---

# 第四章 HTTP 方法

统一：

| Method | 用途 |
|---------|------|
| GET | 查询 |
| POST | 创建 |
| PUT | 全量更新 |
| PATCH | 部分更新 |
| DELETE | 删除（逻辑删除） |

禁止：

GET 修改数据。

---

# 第五章 Person API

统一接口：

```text
GET /persons

GET /persons/{id}

POST /persons

PATCH /persons/{id}

DELETE /persons/{id}
```

扩展接口：

```text
/persons/{id}/books

/persons/{id}/papers

/persons/{id}/timeline

/persons/{id}/relations
```

---

# 第六章 Book API

统一：

```text
/books

/books/{id}

/books/{id}/versions

/books/{id}/chapters

/books/{id}/passages

/books/{id}/citations
```

一本古籍拥有多个版本。

不得设计多个重复接口。

---

# 第七章 Version API

Version 为一级资源。

例如：

```text
/versions

/versions/{id}

/versions/{id}/compare

/versions/{id}/passages
```

支持：

版本比较。

---

# 第八章 Passage API

Passage 为平台最小知识单元。

统一：

```text
/passages

/passages/{id}

/passages/search

/passages/compare
```

AI 默认检索 Passage。

---

# 第九章 Paper API

支持：

```text
/papers

/papers/{id}

/papers/search

/papers/citations

/papers/authors
```

论文必须支持 DOI 检索。

---

# 第十章 Image API

统一：

```text
/images

/images/{id}

/images/{id}/metadata
```

支持：

IIIF（International Image Interoperability Framework）扩展（规划）。

---

# 第十一章 Search API

统一：

```text
/search
```

参数：

- keyword
- entity
- version
- dynasty
- author
- source

不得建立多个重复搜索接口。

---

# 第十二章 AI API

AI 服务统一入口：

```text
POST /ai/chat

POST /ai/search

POST /ai/compare

POST /ai/retrieve
```

AI 服务不得直接暴露底层模型。

---

# 第十三章 Response 规范

统一结构：

```json
{
  "success": true,
  "message": "",
  "data": {},
  "pagination": {},
  "metadata": {},
  "timestamp": ""
}
```

禁止：

接口返回结构不一致。

---

# 第十四章 分页规范

统一：

```text
page

page_size

total

total_pages
```

默认：

20。

最大：

100。

---

# 第十五章 排序规范

统一：

```text
sort_by

order=asc|desc
```

不得：

多个排序参数混乱。

---

# 第十六章 Filtering

统一：

```text
author

dynasty

version

year

institution

language
```

Filter 必须标准化。

---

# 第十七章 错误码

统一：

| Code | 说明 |
|------|------|
| 400 | 参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 数据冲突 |
| 422 | 校验失败 |
| 500 | 系统错误 |

不得自定义 HTTP 状态码。

---

# 第十八章 OpenAPI

所有接口：

自动生成：

OpenAPI。

Swagger。

ReDoc。

文档必须实时更新。

---

# 第十九章 API 生命周期

统一：

```text
Draft

↓

Review

↓

Published

↓

Deprecated

↓

Archived
```

废弃接口至少保留两个版本周期。

---

# 第二十章 API 安全

必须支持：

- JWT
- RBAC
- Rate Limit
- Request ID
- 审计日志
- 参数校验

AI API：

必须增加：

Prompt 审计。

---

# 第二十一章 API 红线

禁止：

- RPC 风格接口
- Controller 写 SQL
- 返回 ORM
- 不分页查询
- 无版本接口
- 无 OpenAPI
- 无权限控制

违反任一项不得上线。

---

# 第二十二章 修订规则

修改 API 规范必须同步更新：

- OpenAPI
- Backend
- Frontend
- Context Package
- AI Prompt Library

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台 API 统一设计规范。 |