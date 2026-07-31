---
title: Git Workflow Standard
document_id: HFB-DEV-0508
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Git Workflow / Branch Management
priority: P0
related_documents:
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-DEV-0501 Development Specification
  - HFB-DEV-0507 Code Review Standard
  - HFB-PS-1709 MVP Implementation Specification
---

# Git Workflow Standard

## Git 工作流规范

> 本规范定义项目 Git 分支、提交、合并、发布、回滚及审计流程。
>
> 所有开发人员与 AI Agent 必须遵守本规范。

---

# 第一章 目标

建立统一 Git 工作流，确保：

- 代码变更可追溯
- Sprint 边界清晰
- PR 审查完整
- 发布可回滚
- AI 修改可审计

---

# 第二章 分支模型

项目采用简化 Git Flow。

```text
main
  ↑
develop
  ↑
feature/*
hotfix/*
release/*
docs/*
```

---

# 第三章 主分支

## main

代表稳定发布版本。

要求：

- 永远可部署
- 不允许直接提交
- 只允许 PR 合并
- 必须通过全部 CI

---

## develop

代表当前开发版本。

要求：

- Sprint 开发合并目标
- 保持可运行
- 不得合并未完成代码

---

# 第四章 功能分支

命名：

```text
feature/sprint-04-person-module
```

规则：

- 一个功能一个分支
- 一个 Sprint 可有多个 feature 分支
- 不得跨 Sprint 开发

---

# 第五章 修复分支

命名：

```text
hotfix/security-auth-bypass
```

适用：

- 安全漏洞
- 生产阻塞
- 数据损坏
- CI 阻塞

Hotfix 必须同步回 develop。

---

# 第六章 发布分支

命名：

```text
release/v0.4.0
```

用于：

- Sprint 发布候选
- 回归测试
- 文档冻结
- 版本标记

---

# 第七章 文档分支

命名：

```text
docs/update-data-standard
```

治理文档修改必须使用 docs 分支。

不得在业务开发分支中混入治理文档重写。

---

# 第八章 Commit 规范

统一采用 Conventional Commits。

格式：

```text
type(scope): message
```

示例：

```text
feat(person): add person repository
fix(api): handle invalid uuid
docs(data): update entity specification
test(book): add version relation test
refactor(service): simplify passage service
```

---

# 第九章 Commit Type

允许类型：

| Type     | 用途   |
| -------- | ------ |
| feat     | 新功能 |
| fix      | 修复   |
| docs     | 文档   |
| test     | 测试   |
| refactor | 重构   |
| chore    | 杂项   |
| ci       | CI     |
| build    | 构建   |
| perf     | 性能   |
| security | 安全   |

禁止使用：

```text
update
change
modify
temp
final
wip
```

---

# 第十章 Pull Request 规范

每个 PR 必须包含：

- 变更摘要
- 涉及 Sprint
- 涉及文档
- 测试结果
- 风险说明
- 回滚方案

无 PR 不得合并。

---

# 第十一章 PR 标题规范

格式：

```text
[Sprint-04] feat(person): implement person base module
```

必须包含 Sprint 编号。

---

# 第十二章 PR 检查清单

必须确认：

- 是否符合 Roadmap
- 是否超出 Sprint 范围
- 是否更新文档
- 是否通过测试
- 是否通过 CI
- 是否通过 Codex 审计
- 是否通过 Gemini 评审（如涉及 UI/学术表达）

---

# 第十三章 AI 修改标记

AI 参与的提交必须在 PR 中注明：

```text
Generated/Modified by: Claude Code
Reviewed by: Codex
Approved by: GPT
```

AI 修改不得绕过 Review。

---

# 第十四章 禁止直接提交

以下分支禁止直接提交：

- main
- develop
- release/\*

必须 PR 合并。

---

# 第十五章 Tag 规范

发布版本使用：

```text
v0.1.0
v0.2.0
v1.0.0
```

格式遵循 Semantic Versioning。

---

# 第十六章 版本号规则

```text
MAJOR.MINOR.PATCH
```

- MAJOR：重大架构变化
- MINOR：Sprint 功能发布
- PATCH：修复发布

---

# 第十七章 回滚规则

任何发布必须可回滚。

回滚必须记录：

- 回滚原因
- 涉及 Commit
- 数据库影响
- 是否影响 AI 索引
- 是否影响知识库

---

# 第十八章 冲突处理

发生冲突时：

优先级：

```text
Project Constitution
↓
Technical Blueprint
↓
Data Standard
↓
Current Sprint
↓
Implementation
```

不得以代码现状反向修改治理规则。

---

# 第十九章 Git 红线

禁止：

- 直接提交 main
- 无 PR 合并
- 无测试合并
- 无 Review 合并
- 跨 Sprint 提交
- 大量无意义提交
- 删除历史记录
- 强推 main/develop

违反任一项必须回滚。

---

# 第二十章 修订规则

修改 Git 工作流必须同步更新：

- Development Specification
- Code Review Standard
- CI/CD Standard
- PR Template
- AI Execution Protocol

---

# 修订记录

| Version | Date       | Description                             |
| ------- | ---------- | --------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，作为项目 Git 工作流统一规范。 |
