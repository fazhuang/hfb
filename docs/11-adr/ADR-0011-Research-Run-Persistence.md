---
title: "ADR-0011 Research Run Persistence"
document_id: HFB-ADR-0011
version: "0.1"
status: "Proposed"
owner: "HFB 产品与架构负责人（待指定）"
decision_date: "2026-07-27"
last_updated: "2026-07-27"
domain: "research-workflow"
related:
  - "ADR-0001-FastAPI"
  - "ADR-0003-PostgreSQL"
  - "ADR-0008-Docker"
  - "docs/02-architecture/rfc/RFC-0001-Research-Passport-and-Quality-Gates.md"
  - "docs/20-product/2023-academic-research-skills-benchmark.md"
---

# ADR-0011：以独立持久化模块管理 ResearchRun 与 ResearchPassport

## Status

**Proposed** — 等待 RFC-0001 的产品、后端、安全和数据治理评审。本文不选择异步执行器或消息队列。

## Context

当前 run 与 replay manifest 写入 `ResearchSession.workflow_state` JSON。该实现适合一次性五步工作流与确定性回放，但不适合长期人工关口、并发控制、Passport 版本、对象 payload、追加式审计和可恢复的异步执行。

HFB 需要保持现有 `trace_id → document_id → chunk` 的事实链，并新增可验证、可迁移的运行治理。该变化影响 FastAPI、PostgreSQL、部署对象存储与前端状态呈现。

## Decision

在 RFC-0001 被接受后，建立一个 **ResearchRunLifecycle 模块** 作为唯一的外部 seam。该模块负责合法状态转换、Passport 版本验证、Gate 决定、审计事件、幂等键和后台任务调度；调用方不得直接写 run 状态或 Passport。

运行元数据、Passport 索引、Gate 决定和审计事件使用 PostgreSQL 的独立持久化模型；大 payload 使用现有或经批准的对象存储。对象 payload 以 hash 固定，关系元数据保存对象键及 hash。静态报告按报告/项目 ACL 保存；在线证据穿透按当前 RBAC 鉴权。

迁移采用“解析旧 JSON → 回填 → 双写 → 验证 → 切读 → 收敛”的可回滚序列。旧记录不能形成完整 Passport 时标记为 legacy，不得伪造 provenance 或 hash。异步执行器保持未决，由 RFC 的实施评审选择。

## Consequences

### Positive

- 将生命周期与复杂状态从各个 API/前端调用者集中到一个深模块，增强一致性、测试性和审计 locality。
- 支持人工关口、幂等恢复、长 payload 治理和版本绑定的审批。
- 保留既有 replay manifest，同时为 Passport 与动态 RBAC 提供明确迁移路径。

### Negative

- 需要数据库迁移、对象存储生命周期、双写监控、回填和回滚演练。
- 数据读取与前端状态会经历兼容窗口，实施复杂度高于维持 JSON。
- 对象存储 hash 和审计保留带来额外成本与运维责任。

## Alternatives

| 方案 | 优点 | 缺点 | 结论 |
| --- | --- | --- | --- |
| 继续写 `workflow_state` JSON | 无迁移 | 无稳定并发、审计、版本与大 payload 管理 | 放弃 |
| 仅为 JSON 外包对象 payload | 改动有限 | 状态/审计/权限仍分散在调用者 | 放弃 |
| 独立持久化模块（本决策） | 清晰 seam、可验证迁移、支持未来关口 | 迁移和运维成本 | 推荐 |
| 立即选定 Temporal/Celery | 可加速原型 | 在规模、SLO、运维约束未评估前过早锁定 | 延后 |

## Future

- RFC 接受后固化表结构、JSON Schema、迁移与回滚脚本，并以真实三身份 RBAC 和浏览器流验收。
- 若后续并发、恢复和 SLA 证据显示需要特定调度器，以新的 ADR 选择执行器；不得修改本 ADR 的历史决策。
- 历史 JSON 读路径的移除应由新的 ADR 或实施记录确认，而非静默删除。

## References

- [RFC-0001](../02-architecture/rfc/RFC-0001-Research-Passport-and-Quality-Gates.md)
- [ARS benchmark](../20-product/2023-academic-research-skills-benchmark.md)
- [ADR-0003 PostgreSQL](ADR-0003-PostgreSQL.md)
- [System architecture](../architecture/system-architecture.md)

---

> **创建日期：** 2026-07-27  
> **最后更新：** 2026-07-27
