---
title: 'Decision Tree — Deployment'
version: '1.0'
status: 'Accepted'
owner: 'Chief Software Architect'
last_updated: '2026-06-24'
related_adr: ['ADR-0008']
---

# Decision Tree — Deployment

为什么选择 Docker Compose 而不是 K8s 或直接部署。

---

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'fontFamily': 'system-ui' }}}%%
graph TD
  Q1["5+ 服务需要部署\n怎么做？"]
  Q1 -->|"一键启动\n环境一致"| A1["Docker Compose ✅"]
  Q1 -->|"生产级\nV1 过度"| B1["Kubernetes ❌\n复杂度太高"]
  Q1 -->|"无容器"| C1["直接部署 ❌\n环境不一致"]

  Q2["为什么不是 K8s？"]
  Q2 -->|"V1 阶段\n5 个服务"| A2["Compose 足够 ✅\nV2 再评估"]
  Q2 -->|"现在上 K8s"| B2["运维成本 > 收益 ❌"]
```

## 决策路径

1. V1 阶段 5+ 服务：Docker Compose 一键启动 → 新成员 15 分钟上手
2. K8s 运维成本远高于当前需求 → V2 阶段再评估
3. 容器化确保开发/生产环境一致

## 相关 ADR

- ADR-0008 Docker

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
