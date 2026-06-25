---
title: Development Specification
document_id: HFB-DEV-0501
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Software Development
priority: P0
related_documents:
  - HFB-GOV-0002 Project Constitution
  - HFB-GOV-0003 Governance
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-ARC-0201 Technical Blueprint
  - HFB-AI-0401 AI Engineering Standard
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Development Specification
## 软件开发规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的统一软件开发标准。
>
> 所有开发人员、AI Agent、自动化工具必须遵守本规范。
>
> **本规范是项目唯一的软件工程执行标准。**

---

# 第一章 开发原则

平台开发遵循以下原则：

- Documentation Driven Development（DDD）
- Domain Driven Design（DDD）
- Clean Architecture
- SOLID
- Repository Pattern
- Service Layer
- Test First（关键模块）
- Continuous Integration

任何实现不得违反上述原则。

---

# 第二章 项目结构

统一采用 Monorepo。

```text
apps/
    backend/
    frontend/

packages/
    config/
    types/
    ui/
    utils/

docs/

tests/

docker/

scripts/

infra/
```

未经 ADR，不得修改项目结构。

---

# 第三章 技术栈

| 模块 | 技术 |
|------|------|
| Backend | FastAPI |
| Frontend | Vue3 + TypeScript |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| Database | PostgreSQL |
| Cache | Redis |
| Search | Elasticsearch |
| Object Storage | MinIO |
| Container | Docker Compose |
| CI | GitHub Actions |

任何技术替换必须建立 ADR。

---

# 第四章 Backend 架构

统一目录：

```text
app/
 ├── api/
 ├── core/
 ├── db/
 ├── middleware/
 ├── models/
 ├── repositories/
 ├── schemas/
 ├── services/
 ├── startup/
 └── utils/
```

禁止：

Controller 编写业务逻辑。

---

# 第五章 Frontend 架构

统一目录：

```text
src/

components/

pages/

layouts/

router/

stores/

services/

types/

utils/

assets/
```

业务逻辑不得写入组件。

统一放入：

Service。

---

# 第六章 Repository Pattern

统一流程：

```text
API

↓

Service

↓

Repository

↓

Database
```

禁止：

API

↓

Database

直接访问。

---

# 第七章 Service Layer

Service：

负责：

- 业务规则
- 权限判断
- 数据组合
- Workflow

不得：

直接写 SQL。

---

# 第八章 Model 规范

统一：

SQLAlchemy ORM。

所有 Model：

继承：

BaseEntity。

必须拥有：

- UUID
- created_at
- updated_at
- version
- status

不得重复定义。

---

# 第九章 API 规范

RESTful。

统一返回：

```json
{
  "success": true,
  "message": "",
  "data": {},
  "timestamp": ""
}
```

错误：

统一异常处理中间件。

---

# 第十章 Schema 规范

数据库对象：

不得直接返回。

统一：

DTO。

Schema：

Input

↓

Service

↓

Output

禁止：

ORM 泄露到 API。

---

# 第十一章 配置管理

所有配置：

统一：

Environment。

禁止：

代码硬编码：

- 密钥
- Token
- 数据库地址
- 模型名称
- API Key

---

# 第十二章 日志规范

统一：

Structured Logging。

记录：

- Request ID
- User ID
- API
- Duration
- Status
- Exception

日志不得记录敏感数据。

---

# 第十三章 Git 规范

采用：

Git Flow。

主分支：

```text
main
```

开发：

```text
develop
```

功能：

```text
feature/*
```

修复：

```text
hotfix/*
```

禁止直接提交 main。

---

# 第十四章 Commit 规范

统一：

Conventional Commits。

例如：

```text
feat:

fix:

refactor:

docs:

test:

chore:
```

不得使用：

update

modify

change

等无意义提交。

---

# 第十五章 Code Review

所有 PR：

至少检查：

- 架构
- 安全
- 测试
- 文档
- 性能
- 命名

Codex：

负责最终审计。

---

# 第十六章 测试规范

Backend：

pytest。

Frontend：

Vitest。

覆盖率：

Backend ≥90%。

Frontend ≥80%。

所有 Sprint：

必须：

测试通过。

---

# 第十七章 Lint

统一：

Python：

ruff

mypy

Frontend：

eslint

prettier

CI：

全部通过。

---

# 第十八章 Docker

所有服务：

必须：

Docker 化。

开发环境：

一键启动。

生产环境：

独立配置。

---

# 第十九章 CI/CD

GitHub Actions：

统一执行：

- Lint
- Test
- Build
- Security
- Documentation

任何失败：

禁止合并。

---

# 第二十章 Sprint 开发流程

统一流程：

```text
Project Charter

↓

Blueprint

↓

Sprint Design

↓

Claude Development

↓

Codex Audit

↓

Gemini Review

↓

GPT Approval

↓

Merge
```

禁止跳过任何环节。

---

# 第二十一章 开发红线

禁止：

- 无文档开发
- 无测试提交
- 无审计上线
- Controller 写业务逻辑
- Service 写 SQL
- Repository 写业务规则
- ORM 直接返回前端
- 未经批准新增模块

违反任一项不得合并。

---

# 第二十二章 修订规则

修改开发规范必须：

1. 建立 ADR；
2. 更新 Blueprint；
3. 更新 Context；
4. 更新 Sprint；
5. 项目负责人批准。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台统一软件开发规范。 |