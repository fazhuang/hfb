---
title: 'Decision Tree — Frontend'
version: '1.0'
status: 'Accepted'
owner: 'Chief Software Architect'
last_updated: '2026-06-24'
related_adr: ['ADR-0002']
---

# Decision Tree — Frontend

为什么选择 Vue 3 而不是 React 或 HTMX。

---

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
graph TD
  Q1["学术平台\n前端需要什么？"]
  Q1 -->|"组件化\n渐进增强"| A1["Vue 3 ✅\n.SFC 语义清晰"]
  Q1 -->|"生态最大"| B1["React ❌\nJSX 可读性不如模版\n交互复杂度不需要"]
  Q1 -->|"极简"| C1["HTMX ❌\n版本对比/关系图\n需要 SPA"]
  Q1 -->|"编译时"| D1["Svelte ❌\n社区太小\n中文弱"]

  Q2["组件库选什么？"]
  Q2 -->|"学术定制"| A2["自建学术组件 ✅"]
  Q2 -->|"开箱即用"| B2["Naive UI ⏸️\n备选"]
  Q2 -->|"Material"| C2["Vuetify ❌\n风格不匹配"]
```

## 决策路径

1. 学术平台交互复杂度中等 → 不需要 React 级别的抽象
2. 古籍阅读面板是核心 → 需要 SPA 式的状态管理 → HTMX 不够
3. .vue 单文件组件 AI 可直接解析 → SFC 语义清晰
4. UI 组件库：优先自建学术组件，备选 Naive UI

## 相关 ADR

- ADR-0002 Vue 3

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
