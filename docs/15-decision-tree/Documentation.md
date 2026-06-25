---
title: "Decision Tree — Documentation"
version: "1.0"
status: "Accepted"
owner: "Chief Documentation Architect"
last_updated: "2026-06-24"
related_adr: ["ADR-0010"]
---

# Decision Tree — Documentation

为什么选择 AI Native 双轨制（Markdown + JSON）而不是 Wiki 或纯 Markdown。

---

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
graph TD
  Q1["5 种 AI 需要读取文档\n怎么组织？"]
  Q1 -->|"人读 + AI 读"| A1["Markdown + JSON ✅\n双轨制"]
  Q1 -->|"人读为主"| B1["纯 Markdown ❌\nAI 读取效率低"]
  Q1 -->|"AI 读为主"| C1["纯 JSON ❌\n人不可读"]
  Q1 -->|"在线编辑"| D1["Wiki ❌\n不可 Git 版本控制"]

  Q2["AI 如何自动导航？"]
  Q2 -->|"读取 JSON 索引"| A2["Machine Layer ✅\n10 份 JSON 索引"]
  Q2 -->|"遍历目录"| B2["文件系统 ❌\n慢/不稳定"]

  Q3["AI 如何加载\nSprint 上下文？"]
  Q3 -->|"读 7 份文件"| A3["Context Package ✅\n一次加载"]
  Q3 -->|"读 N 份文件"| B3["分散文档 ❌\n多次上下文切换"]
```

## 决策路径

1. 文档同时服务人和 AI → 双轨制，不是二选一
2. Markdown → 人可读可写，Git 友好
3. JSON Machine Layer → AI 快速定位，不需要遍历目录
4. Context Package → AI 一次加载全部 Sprint 上下文，减少来回

## 相关 ADR

- ADR-0010 AI Native

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
