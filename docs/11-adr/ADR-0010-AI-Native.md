---
title: 'ADR-0010 AI Native'
version: '1.0'
status: 'Accepted'
owner: 'Chief Documentation Architect'
decision_date: '2026-06-24'
last_updated: '2026-06-24'
domain: 'documentation'
related:
  - 'ADR-0001-FastAPI'
  - 'ADR-0002-Vue3'
  - 'ADR-0003-PostgreSQL'
  - 'ADR-0009-Monorepo'
  - 'docs/13-machine/README.md'
  - 'docs/README.md'
---

# ADR-0010: 建立 AI Native 文档体系

---

## Status

**Accepted** — 2026-06-24

## Context

皇甫谧数字人文平台的项目文档需要被 5 种 AI 模型同时读取和理解：

| AI           | 角色        | 需要的文档格式      |
| ------------ | ----------- | ------------------- |
| Claude       | 开发执行    | Markdown（结构化）  |
| Codex        | 文档审计    | Markdown + 规则清单 |
| Gemini       | UI 学术评审 | Markdown + 设计规范 |
| GPT          | 通用协助    | Markdown            |
| DeepResearch | 文献调研    | Markdown + 引用     |

传统文档是给人读的。AI Native 文档是同时给人读和给 AI 读的——机器可解析、语义清晰、交叉引用完整。

## Decision

建立 **AI Native Documentation Repository**。核心原则：

1. **Markdown + JSON 双轨制** — 人读 Markdown，AI 读 JSON（Machine Layer）
2. **Front Matter 标准化** — 每个 Markdown 头部包含结构化元数据
3. **Context Package** — 每个 Sprint 上下文打包，AI 可一次性读取
4. **ADR 体系** — 所有技术决策归档
5. **Decision Tree** — 解释"为什么选 A 不选 B"
6. **Machine Layer** — JSON 索引供 AI 自动定位
7. **Knowledge Package** — 领域知识结构化

## Alternatives

| 方案               | 优点                                      | 缺点                                        | 放弃原因              |
| ------------------ | ----------------------------------------- | ------------------------------------------- | --------------------- |
| AI Native (本方案) | AI 可直接理解、减少上下文浪费、跨模型兼容 | 初始建设成本高                              | —                     |
| 纯 Markdown        | 简单                                      | AI 读取效率低、需多次上下文切换、无结构索引 | 不满足 5 模型协作需求 |
| 数据库存储文档     | 查询灵活                                  | 文档不可 Git 版本控制、门槛高               | 不满足 AI 透明性要求  |
| Wiki 系统          | 协作方便                                  | 不可自动化审计、不可 AI 批量读取            | 不满足 CI/CD 集成需求 |

## Consequences

### Positive

- 5 种 AI 模型可直接读取 docs/ 工作
- Machine Layer（JSON）供 AI 自动导航，不需人工描述
- Context Package 减少 AI 上下文加载时间
- 版本化 Prompt 可追溯、可测试、可复现

### Negative

- 文档创建和维护成本增加（需同时更新 Markdown 和 JSON）
- 对文档工程师的要求提高
- JSON 与 Markdown 的同步一致性需要持续维护

## Future

- 探索自动从 Markdown Front Matter 生成 Machine Layer JSON
- 建立文档 CI 检查（链接有效性、JSON 合法性）
- 评估引入 Embedding 直接索引文档供 RAG 读取

## References

- [docs/13-machine/README.md](../13-machine/README.md)
- [docs/12-context/README.md](../12-context/README.md)
- [docs/11-adr/README.md](../11-adr/README.md)

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-24
