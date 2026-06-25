---
title: "ADR-0008 Docker"
version: "1.0"
status: "Accepted"
owner: "Chief Software Architect"
decision_date: "2026-06-24"
last_updated: "2026-06-24"
domain: "infrastructure"
related:
  - "ADR-0009-Monorepo"
  - "docs/05-development/00_Development_Specification.md"
---

# ADR-0008: 选择 Docker 作为部署方案

---

## Status

**Accepted** — 2026-06-24

## Context

皇甫谧平台包含多个服务（FastAPI、PostgreSQL、Neo4j、Elasticsearch、Milvus），需要一个统一的部署方案。需求：

- 开发环境和生产环境一致
- 新成员 15 分钟内启动全套服务
- 支持 CI/CD 自动化构建
- 中文友好（国内镜像可用）

## Decision

选择 **Docker Compose（开发/测试）+ Docker（生产）** 作为部署方案。

## Alternatives

| 方案 | 优点 | 缺点 | 放弃原因 |
|---|---|---|---|
| Docker Compose | 简单、一键启动、适合中小规模 | 单机限制、不如 K8s 灵活 | — |
| Kubernetes | 生产级、自动扩展 | 复杂度过高、V1 阶段不需要 | 过度设计 |
| 直接部署 | 零容器开销 | 环境不一致、新成员上手慢、多版本管理困难 | 不符合 AI Native 要求 |
| Podman | 无守护进程、Red Hat 生态 | 社区生态小于 Docker、Compose 兼容性不完全 | Docker 更通用 |

## Consequences

### Positive

- 开发环境与生产一致 → 减少"我机器上能跑"问题
- Docker Compose 一键启动 5+ 服务
- CI/CD 集成简单（GitHub Actions + Docker）
- 新成员入职成本低

### Negative

- Docker Desktop 许可证成本（改用 Colima 或直接 Linux 部署可规避）
- 容器内调试略有不便（可配置 volume 挂载解决）
- 镜像构建和拉取需要网络（国内可用镜像加速器）

## Future

- V1 阶段 Docker Compose 足够
- V2 阶段如需要高可用和水平扩展，迁移到 K8s
- 镜像仓库使用 GitHub Container Registry (ghcr.io)

## References

- [Development Specification](../05-development/00_Development_Specification.md)
- [ADR-0009 Monorepo](ADR-0009-Monorepo.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
