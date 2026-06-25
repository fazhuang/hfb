---
title: Release Management Standard
document_id: HFB-DEV-0510
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Release & Version Management
priority: P0
related_documents:
  - HFB-DEV-0501 Development Specification
  - HFB-DEV-0506 Testing Standard
  - HFB-DEV-0507 Code Review Standard
  - HFB-DEV-0508 Git Workflow Standard
  - HFB-DEV-0509 CI_CD_Standard
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Release Management Standard
## 发布管理规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的统一发布流程。
>
> 平台发布不仅包括软件系统，还包括数据库、知识资源、AI 模型、Prompt、知识图谱及学术数据，因此采用统一发布治理体系。

---

# 第一章 发布目标

平台发布必须满足：

- 可追溯
- 可验证
- 可回滚
- 可审计
- 可复现
- 最小风险

任何版本不得直接发布至生产环境。

---

# 第二章 发布对象

平台发布包括六类对象：

| 类型 | 内容 |
|------|------|
| Application | 前后端程序 |
| Database | 数据库结构 |
| Academic Data | 学术资源 |
| AI Assets | Prompt、模型配置 |
| Search Index | Elasticsearch 索引 |
| Knowledge Graph | 图谱数据（后续） |

所有对象必须统一纳入版本管理。

---

# 第三章 发布级别

统一分为：

| 等级 | 用途 |
|------|------|
| Patch | 缺陷修复 |
| Minor | Sprint 功能发布 |
| Major | 平台重大升级 |

版本号遵循：

```text
MAJOR.MINOR.PATCH
```

例如：

```text
v0.8.3
v0.9.0
v1.0.0
```

---

# 第四章 发布流程

统一发布流程：

```text
Sprint 完成
      │
      ▼
Code Freeze
      │
      ▼
Regression Test
      │
      ▼
Security Review
      │
      ▼
Academic Review
      │
      ▼
Release Approval
      │
      ▼
Tag
      │
      ▼
Deploy
```

任何步骤失败，终止发布。

---

# 第五章 Code Freeze

进入 Release 后：

禁止：

- 新功能开发
- 数据结构变更
- Prompt 大幅调整
- API 新增

仅允许：

Bug Fix。

---

# 第六章 Release Checklist

发布前必须确认：

- 所有测试通过
- CI 全绿
- Migration 完成
- OpenAPI 更新
- Prompt 更新
- 文档更新
- Release Note 完成
- 风险评估完成

Checklist 未完成不得发布。

---

# 第七章 数据库发布

数据库发布必须：

```text
Migration
      │
      ▼
Validation
      │
      ▼
Backup
      │
      ▼
Upgrade
```

禁止：

直接修改生产数据库。

---

# 第八章 学术资源发布

学术资源包括：

- 人物
- 古籍
- 论文
- 图片
- OCR
- Metadata

发布流程：

```text
专家审核
      │
      ▼
Metadata 校验
      │
      ▼
版本确认
      │
      ▼
正式发布
```

未经审核不得公开。

---

# 第九章 AI 资源发布

AI 发布对象：

- Prompt
- RAG 配置
- 检索策略
- 模型配置

发布要求：

- 版本编号
- 回归测试
- 引文验证
- Hallucination 检测

Prompt 必须可回滚。

---

# 第十章 检索索引发布

Elasticsearch：

必须支持：

- 增量重建
- 全量重建
- Alias 切换

禁止：

在线直接覆盖索引。

---

# 第十一章 图谱发布（规划）

Graph 发布流程：

```text
Entity Validation
      │
      ▼
Relation Validation
      │
      ▼
Evidence Validation
      │
      ▼
Graph Build
      │
      ▼
Publish
```

Graph 发布必须独立版本管理。

---

# 第十二章 Release Note

每个版本必须生成：

- 新增功能
- 修复内容
- 数据变更
- AI 更新
- 已知问题
- 升级说明

Release Note 属于正式项目文档。

---

# 第十三章 Tag 管理

统一格式：

```text
v0.5.0
v0.6.2
v1.0.0
```

Tag 必须对应：

- Git Commit
- Release Note
- Sprint

---

# 第十四章 部署验证

部署完成后自动验证：

- Health Check
- API
- Database
- Search
- AI
- 日志
- 前端

任何异常立即回滚。

---

# 第十五章 回滚策略

统一支持：

- 应用回滚
- 数据库回滚
- Prompt 回滚
- 检索索引回滚
- 配置回滚

回滚必须生成事件记录。

---

# 第十六章 发布审批

发布审批流程：

```text
Claude
      │
Codex
      │
Gemini
      │
GPT
      │
Project Owner
```

生产发布必须最终由项目负责人批准。

---

# 第十七章 发布指标

目标：

| 指标 | 标准 |
|------|------|
| 发布成功率 | ≥99% |
| 回滚成功率 | 100% |
| 平均发布时间 | ≤30 分钟 |
| 发布事故 | 0 |
| 数据丢失 | 0 |

---

# 第十八章 发布红线

禁止：

- 无 Tag 发布
- 无 Release Note 发布
- 跳过测试发布
- 跳过安全审计发布
- 跳过学术审核发布
- 跳过 Migration 验证
- 跳过 AI 回归验证

违反任一项不得发布。

---

# 第十九章 发布文档归档

每次发布必须归档：

- Release Note
- Test Report
- Review Report
- Deployment Log
- Migration Log
- AI Evaluation Report

归档保存期限不少于五年。

---

# 第二十章 修订规则

修改发布规范必须同步更新：

- Git Workflow Standard
- CI/CD Standard
- Sprint Template
- Project Roadmap
- AI Execution Protocol

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台统一发布管理规范。 |