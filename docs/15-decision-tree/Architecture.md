---
title: 'Decision Tree — Architecture'
version: '1.0'
status: 'Accepted'
owner: 'Chief Software Architect'
last_updated: '2026-06-24'
related_adr: ['ADR-0001', 'ADR-0009']
---

# Decision Tree — Architecture

为什么选择六层架构 + Monorepo。

---

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
graph TD
  Q1["前端 + 后端 + AI Pipeline + 文档\n如何组织代码？"]
  Q1 -->|"统一版本\nAI 跨层读取"| A1["Monorepo ✅"]
  Q1 -->|"独立版本\n权限分离"| B1["Polyrepo ❌\nAI 无法跨仓读取"]
  Q1 -->|"微服务仓库"| C1["多仓库 ❌\n过度设计"]

  Q2["六层架构\n为什么不是三层？"]
  Q2 -->|"AI 层独立\n数据多引擎"| A2["六层 ✅\nL1-L6 清晰"]
  Q2 -->|"重量级\n适合简单"| B2["三层 (MVC) ❌\nAI 和数据分不开"]
  Q2 -->|"适合微服务"| C2["微内核 ❌\nV1 不需要"]
```

## 决策路径

1. 项目包含 4 个独立模块（前后端+AI+文档）→ Monorepo 是最优解
2. AI 层和数据层需要独立扩展 → 六层架构提供了清晰的边界
3. 六层不是一开始就全部构建 — V1 重点是 L2/L3/L5

## 相关 ADR

- ADR-0001 FastAPI
- ADR-0009 Monorepo

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
