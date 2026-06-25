---
title: "ADR-0001 FastAPI"
version: "1.0"
status: "Accepted"
owner: "Chief Software Architect"
decision_date: "2026-06-24"
last_updated: "2026-06-24"
domain: "architecture"
related:
  - "ADR-0003-PostgreSQL"
  - "ADR-0009-Monorepo"
  - "ADR-0010-AI-Native"
  - "docs/05-development/00_Development_Specification.md"
---

# ADR-0001: 选择 FastAPI 作为 API 框架

---

## Status

**Accepted** — 2026-06-24

## Context

皇甫谧数字人文平台需要一个高性能、自动化文档的 Python Web 框架来承载所有 REST API。需求：

- 自动生成 OpenAPI 文档（AI 可直接读取）
- 类型安全（Pydantic 原生集成）
- 异步支持（处理高并发文献检索）
- Python 生态兼容（NLP、AI 库均为 Python）

## Decision

选择 **FastAPI** 作为统一 API 框架。

## Alternatives

| 方案 | 优点 | 缺点 | 放弃原因 |
|---|---|---|---|
| FastAPI | 自动 OpenAPI、异步原生、Pydantic 集成、性能优秀 | 社区小于 Django | — |
| Django + DRF | 社区最大、插件丰富、Admin 面板 | 异步支持弱、OpenAPI 需额外配置、过重 | 不符合微服务轻量化方向 |
| Flask | 极简、灵活 | 无自动文档、无类型校验、异步支持弱 | 需要过多手动配置 |
| Django Ninja | 类型安全 + Django 生态 | 社区较小、与 Django 耦合 | FastAPI 社区更大 |

## Consequences

### Positive

- OpenAPI 文档自动生成 → AI（Codex/Gemini）可直接解析 API
- 类型安全 → 减少运行时错误
- 异步支持 → 高并发文献检索性能好
- 与 Python NLP/AI 生态无缝兼容

### Negative

- 缺少 Django Admin 式的开箱即用管理面板
- ORM 需单独选择（SQLAlchemy）
- 中间件生态不如 Django 成熟

## Future

- 如未来需要 Admin 面板，可单独引入或自建
- 性能瓶颈时可水平扩展，FastAPI 本身不构成瓶颈
- 长期关注 FastAPI 社区演进和 SQLModel 方案

## References

- [Technical Blueprint](../02-architecture/00_Technical_Blueprint.md)
- [Development Specification](../05-development/00_Development_Specification.md)
- [ADR-0009 Monorepo](ADR-0009-Monorepo.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
