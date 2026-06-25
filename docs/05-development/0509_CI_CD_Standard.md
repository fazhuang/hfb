---
title: CI/CD Standard
document_id: HFB-DEV-0509
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Continuous Integration & Continuous Deployment
priority: P0
related_documents:
  - HFB-DEV-0501 Development Specification
  - HFB-DEV-0506 Testing Standard
  - HFB-DEV-0507 Code Review Standard
  - HFB-DEV-0508 Git Workflow Standard
  - HFB-SEC-0701 Acceptance Specification
  - HFB-PS-1710 Production Readiness Specification
---

# CI/CD Standard
## 持续集成与持续部署规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的持续集成（CI）与持续部署（CD）标准。
>
> CI/CD 是平台质量控制的自动化执行体系，是代码进入生产环境的唯一合法通道。

---

# 第一章 建设目标

建立统一 CI/CD 流程，实现：

- 自动构建
- 自动测试
- 自动审计
- 自动安全扫描
- 自动发布
- 自动回滚
- 全程可追溯

任何代码不得绕过 CI/CD 流程。

---

# 第二章 总体架构

统一流水线：

```text
Git Push
    │
    ▼
GitHub Actions
    │
    ├── Code Quality
    ├── Test
    ├── Security
    ├── Build
    ├── Package
    ├── Release
    └── Deploy
```

所有流水线均以 GitHub Actions 为执行平台。

---

# 第三章 流水线分类

平台定义五类流水线：

| 类型 | 作用 |
|------|------|
| CI | 持续集成 |
| CD | 持续部署 |
| Docs Pipeline | 文档检查 |
| Security Pipeline | 安全扫描 |
| Release Pipeline | 发布流程 |

---

# 第四章 CI 流程

每次 Push 或 Pull Request 自动执行：

```text
Checkout
    ↓
Install Dependencies
    ↓
Lint
    ↓
Type Check
    ↓
Unit Test
    ↓
Integration Test
    ↓
Build
```

任一步失败，流水线立即终止。

---

# 第五章 Lint 阶段

Backend：

- Ruff
- MyPy

Frontend：

- ESLint
- Prettier

要求：

零 Error。

Warning 必须持续减少。

---

# 第六章 测试阶段

自动执行：

- Unit Test
- API Test
- Integration Test
- Database Test
- Frontend Test

未来增加：

- AI Test
- RAG Test
- GraphRAG Test

所有测试必须生成报告。

---

# 第七章 安全扫描

自动执行：

- Secret Scan
- Dependency Audit
- SAST（静态分析）
- License Check
- Docker Image Scan

发现 Critical 漏洞：

立即阻断合并。

---

# 第八章 Build 阶段

Backend：

生成 Python Package。

Frontend：

生成静态资源。

Docker：

构建镜像。

要求：

Build 可重复、可验证。

---

# 第九章 文档检查

自动验证：

- Markdown 格式
- 文档引用
- Front Matter
- Mermaid 语法
- 文档编号
- 交叉引用

治理文档不允许出现断链。

---

# 第十章 数据库检查

自动验证：

- Alembic Migration
- Migration 回滚
- Schema 一致性
- ORM 映射

禁止：

直接修改数据库结构。

---

# 第十一章 API 检查

自动验证：

- OpenAPI
- DTO
- Response Schema
- HTTP Status
- 路由冲突

OpenAPI 文档必须自动生成。

---

# 第十二章 AI 检查（规划）

AI 模块上线后自动验证：

- Prompt Version
- Prompt 格式
- Citation
- Hallucination Dataset
- Explainability
- Context Package

AI 不通过不得发布。

---

# 第十三章 Docker 检查

自动验证：

- Dockerfile
- Compose
- 镜像大小
- 多阶段构建
- Root User
- Health Check

禁止：

生产镜像使用 Root 用户。

---

# 第十四章 Release Pipeline

Release 流程：

```text
Release Branch
        │
Regression Test
        │
Security Audit
        │
Version Tag
        │
Release Package
        │
Deploy
```

Release 前必须冻结代码。

---

# 第十五章 Deployment

环境划分：

| 环境 | 用途 |
|------|------|
| Local | 本地开发 |
| Dev | 集成开发 |
| Test | 测试环境 |
| Staging | 预发布 |
| Production | 正式环境 |

任何部署不得跨环境。

---

# 第十六章 回滚机制

每次部署必须支持：

- 应用回滚
- 数据库回滚
- 配置回滚
- AI Prompt 回滚
- 索引回滚

回滚时间目标：

≤10 分钟。

---

# 第十七章 通知机制

流水线结果自动通知：

- GitHub
- 企业微信（规划）
- 邮件（规划）

通知内容：

- 状态
- 耗时
- 失败阶段
- 日志链接

---

# 第十八章 CI/CD 指标

目标：

| 指标 | 标准 |
|------|------|
| CI 成功率 | ≥95% |
| Build 时间 | ≤10 分钟 |
| 自动测试通过率 | ≥95% |
| 回滚成功率 | 100% |
| 部署成功率 | ≥99% |

---

# 第十九章 CI/CD 红线

禁止：

- 跳过 CI
- 跳过安全扫描
- 跳过测试
- 手工修改生产环境
- 未打 Tag 发布
- 未生成 Release Note
- 未验证 Migration

违反任一项不得发布。

---

# 第二十章 修订规则

修改 CI/CD 规范必须同步更新：

- Git Workflow Standard
- Testing Standard
- Release Management Standard
- GitHub Actions
- Deployment Scripts

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台持续集成与持续部署统一规范。 |