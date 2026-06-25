---
title: "ADR-0009 Monorepo"
version: "1.0"
status: "Accepted"
owner: "Chief Software Architect"
decision_date: "2026-06-24"
last_updated: "2026-06-24"
domain: "infrastructure"
related:
  - "ADR-0001-FastAPI"
  - "ADR-0002-Vue3"
  - "ADR-0008-Docker"
---

# ADR-0009: 选择 Monorepo 代码组织

---

## Status

**Accepted** — 2026-06-24

## Context

皇甫谧平台包含前端、后端、AI 流水线、文档四个主要模块。需要决定代码组织方式。

## Decision

选择 **Monorepo**（单一仓库）。

```
hfb/
├── docs/         # 文档
├── backend/      # Python FastAPI
├── frontend/     # Vue 3
├── ai/           # AI Pipeline (RAG/GraphRAG/NER)
├── docker/       # Docker 配置
└── .github/      # CI/CD
```

## Alternatives

| 方案 | 优点 | 缺点 | 放弃原因 |
|---|---|---|---|
| Monorepo | 统一版本、跨模块 PR 方便、AI 可访问全部代码、文档与代码同仓 | 仓库体积大 | — |
| Polyrepo | 各模块独立、权限分离 | 跨模块变更需多 PR、版本管理复杂、AI 需要跨仓库访问 | 不符合 AI Native 策略 |

## Consequences

### Positive

- AI（Claude/Codex）只需读取一个仓库即可理解全栈
- 跨模块 PR（前后端协同变更）在一个提交中完成
- 文档与代码在同一上下文
- pnpm workspaces 或 Python workspace 管理依赖

### Negative

- Clone 时间随项目增长
- CI 需要智能的变更检测以只构建受影响模块
- 权限粒度粗（全员可访问全部代码）

## Future

- 如团队扩大需要代码权限隔离，可拆分为 Polyrepo — 但 V1 不拆分
- 优化 CI 变更检测（path filter）
- 如仓库体积过大，使用 git-lfs 管理大文件

## References

- [ADR-0001 FastAPI](ADR-0001-FastAPI.md)
- [ADR-0002 Vue 3](ADR-0002-Vue3.md)
- [ADR-0008 Docker](ADR-0008-Docker.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
