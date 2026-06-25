---
title: "ADR-0002 Vue 3"
version: "1.0"
status: "Accepted"
owner: "Chief Software Architect"
decision_date: "2026-06-24"
last_updated: "2026-06-24"
domain: "architecture"
related:
  - "ADR-0009-Monorepo"
  - "docs/06-ui/00_Design_System.md"
---

# ADR-0002: 选择 Vue 3 作为前端框架

---

## Status

**Accepted** — 2026-06-24

## Context

皇甫谧数字人文平台的 UI 核心是古籍阅读面板——信息密度高、交互以阅读和检索为主、不需要复杂的实时协作。需要选择一个能够：

- 渐进式增强（可在传统 HTML 上逐步添加交互）
- 与学术 UI 风格匹配（组件化、设计系统友好）
- AI 可理解其组件结构（单文件组件 .vue 语义清晰）

## Decision

选择 **Vue 3** （Composition API + TypeScript）作为前端框架。

## Alternatives

| 方案 | 优点 | 缺点 | 放弃原因 |
|---|---|---|---|
| Vue 3 | 渐进式、学习曲线平缓、SFC 语义清晰、中文社区活跃 | 企业级生态小于 React | — |
| React | 生态最大、社区最活跃、TypeScript 支持好 | JSX 可读性不如模版、Hook 心智负担 | 学术平台交互复杂度不需要 React 级别的抽象能力 |
| HTMX | 极简、零构建、古典 Web | 交互受限、无组件化、不适合复杂 UI | 版本对比、实体关系可视化等需要 SPA 式交互 |
| Svelte | 编译时、无虚拟 DOM、代码量少 | 社区小、中文生态弱、稳定性待验证 | 长期维护风险 |

## Consequences

### Positive

- .vue 单文件组件 AI 可直接解析（模版 + 脚本 + 样式分离清晰）
- Pinia 状态管理简单直观
- Vite 构建工具快速
- 渐进式：可在不重写全部页面的情况下逐步替换

### Negative

- 企业招聘市场 React 需求更大（人文计算领域影响小）
- 第三方组件库选择少于 React
- SSR 方案（Nuxt）成熟度低于 Next.js

## Future

- 如交互复杂度显著增加，可评估迁移 React — 但 V1-V2 阶段不切换
- 关注 Vue 生态中 SSG（静态站点生成）方案用于文档站
- UI 组件库使用 Naive UI 或自建学术组件

## References

- [Design System](../06-ui/00_Design_System.md)
- [ADR-0009 Monorepo](ADR-0009-Monorepo.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
