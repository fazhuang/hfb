---
title: Research Passport and Quality Gates
document_id: HFB-ARC-RFC-0001
version: 0.1.0
status: Draft
owner: HFB 产品与架构负责人
reviewer: —
effective_date: 2026-07-27
scope: Research run persistence, evidence governance, quality gates
priority: P0
related_documents:
  - docs/20-product/2023-academic-research-skills-benchmark.md
  - docs/11-adr/ADR-0011-Research-Run-Persistence.md
  - docs/architecture/system-architecture.md
  - apps/backend/app/services/research_workflow_service.py
---

# RFC-0001：ResearchPassport 与研究质量关口

> **状态：** Draft
> **版本：** v0.1.0
> **日期：** 2026-07-27
> **作者：** Codex（基于 HFB 评估基线起草）
> **负责人：** HFB 产品与架构负责人（待指定）

## 1. 摘要

本 RFC 将当前 `ResearchSession.workflow_state` 内的 run JSON 演进为可版本化、可审计、可恢复的研究运行。它引入 `ResearchPassport`、两个不可绕过的人工关口，以及声明—证据审计；不引入 ARS 的提示词、Agent 编排或任何外部运行时依赖。

## 2. 背景与动机

当前工作流已在同一请求中生成检索快照、不可变 trace、报告和 replay manifest。其事实链可重放，但 run 仍存于 `research_sessions.workflow_state` JSON，不能表达长期暂停、逐项审批、追加式审计或受控的异步恢复。

目标是把 HFB 自有的 `trace_id → document_id → chunk` 链提升为产品契约。质量门必须由后端执行，前端只负责展示和提交操作；LLM 只能输出风险信号，不能成为事实或发布的唯一裁决者。

### 2.1 目标

- 让每个研究运行拥有可验证的 Passport 版本、hash 与对象 payload 引用。
- 在证据综合前和发布/当前视图导出前提供可审计的人工关口。
- 对每条证据执行确定性锚点、漂移与权限检查。
- 保留静态归档的完整性，同时为在线原文穿透执行实时 RBAC。
- 支持安全迁移、幂等恢复和可验证回滚。

### 2.2 非目标

- 不在本 RFC 选择 Celery、Temporal、Redis 或新的队列产品。
- 不实现 GraphRAG、向量检索或 ARS 的多 Agent 工作流。
- 不把 LLM 评分阈值视为学术真值或自动批准。
- 不修改既有静态报告的正文以响应后续源文献失权。

## 3. 术语与不变量

| 术语             | 定义                                                    |
| ---------------- | ------------------------------------------------------- |
| ResearchRun      | 一次以锁定检索快照为输入的研究执行记录。                |
| ResearchPassport | 绑定一个 run 与版本的、可验证的事实和 provenance 契约。 |
| Gate 1           | 证据集确认：决定哪些 evidence 可进入综合。              |
| Gate 2           | 声明完整性确认：决定报告是否可发布或导出当前视图。      |
| 静态归档         | 已定稿的报告工件，受报告/项目 ACL 保护，正文不可变。    |
| 在线穿透         | Citation/Evidence 到原文的交互导航，必须重新鉴权。      |

不变量：

1. 下游不得接受未通过 schema 与 hash 校验的 Passport。
2. Gate 的决定必须绑定 Passport 版本；旧决定不能批准新版本。
3. 任何身份都不能借由 API 绕过 Gate 进入发布或当前视图导出。
4. `chunk_hash`、字符 offset、`document_id` 或权限校验失败的 evidence 不能支持声明。
5. 静态归档不被源权限变化改写；在线穿透和重新导出则使用当前 RBAC。

## 4. 提案

### 4.1 持久化模型与对象存储

新增独立的持久化模块，而不是继续膨胀 `workflow_state` JSON。模块的外部接口应集中在一个深模块中，例如：`ResearchRunLifecycle` 接收命令、验证前置条件、写入状态/审计并调度后台任务；调用方不得自行更新状态或拼装 Passport。

建议的关系型元数据模型如下。实际表名、迁移号和索引由实施 ADR 固化。

| 记录                 | 最小字段                                                                       | 用途                     |
| -------------------- | ------------------------------------------------------------------------------ | ------------------------ |
| ResearchRun          | `id`、`session_id`、`state`、`passport_version`、`idempotency_key`、时间戳     | 生命周期与并发控制       |
| ResearchPassport     | `run_id`、`version`、`content_hash`、`payload_key`、`payload_hash`             | 不可变 Passport 版本索引 |
| ResearchGateDecision | `run_id`、`passport_version`、`gate`、`decision`、`actor_id`、`reason`、时间戳 | Gate 1/2 追加式决定记录  |
| ResearchAuditEvent   | `run_id`、事件类型、旧/新状态、actor、请求关联 ID、时间戳                      | 追加式审计轨迹           |

完整检索快照、Trace Matrix、PromptSnapshot、拒绝日志和运行日志保存到对象存储；数据库只保存索引与加密校验所需的 hash。未变 evidence 在 Passport 新版本中引用上一版本，不重复复制。读取 payload 时必须复算 `payload_hash`；不一致则进入 `DRAFT` 并写入审计事件。

### 4.2 ResearchPassport 最小 JSON 契约

```json
{
  "schema_version": "1.0.0",
  "run_id": "uuid",
  "version": 1,
  "research_question": "string",
  "retrieval": { "executed_at": "RFC3339", "snapshot_hash": "sha256" },
  "evidence": [
    {
      "trace_id": "string",
      "document_id": "uuid",
      "chunk_hash": "sha256",
      "start_offset": 0,
      "end_offset": 0,
      "inclusion_reason": "string"
    }
  ],
  "provenance": { "model_version": "string", "prompt_version": "string" },
  "payload_ref": { "object_key": "string", "content_hash": "sha256" }
}
```

`tenant_id` 不属于当前 HFB 已验证模型，不能作为 v1 必填字段。对外互操作使用由 Passport 投影出的 CSL-JSON；Schema.org `ScholarlyArticle` 是后续适配层，不能取代内部 trace 定位。

### 4.3 状态机与恢复

| 状态                      | 允许进入         | 允许离开                                    | 说明                                      |
| ------------------------- | ---------------- | ------------------------------------------- | ----------------------------------------- |
| CREATED                   | 创建命令         | SEARCH_COMPLETED, DRAFT                     | 尚未锁定证据快照。                        |
| SEARCH_COMPLETED          | 检索完成         | EVIDENCE_PENDING_APPROVAL, DRAFT            | 快照和 Passport v1 已锁定。               |
| EVIDENCE_PENDING_APPROVAL | Gate 1 请求      | EVIDENCE_APPROVED, EVIDENCE_REVISION, DRAFT | 等待有权研究员决定。                      |
| EVIDENCE_APPROVED         | Gate 1 批准      | REPORT_GENERATING                           | 仅短暂转换状态。                          |
| EVIDENCE_REVISION         | Gate 1 驳回      | SEARCH_COMPLETED                            | 可调整范围、补充受权 locator 或重新检索。 |
| REPORT_GENERATING         | 后台任务         | INTEGRITY_CHECKING, DRAFT                   | 只使用指定 Passport 版本。                |
| INTEGRITY_CHECKING        | Gate 2 请求      | PUBLISHED, REPORT_REVISION, DRAFT           | 显示硬失败和风险信号。                    |
| REPORT_REVISION           | Gate 2 驳回      | REPORT_GENERATING                           | 生成并处理 R&R 问题单。                   |
| DRAFT                     | 超时或可恢复失败 | 原中断状态的合法后继                        | 不自动批准；需原快照与幂等键恢复。        |
| PUBLISHED / REJECTED      | 终态             | 无                                          | 分别为归档完成、取消且有理由。            |

审批超时阈值、通知渠道和取消权限属于产品策略，必须在实施前单独批准；超时默认进入 `DRAFT`，绝不自动批准。重复请求使用同一 `idempotency_key` 返回同一运行或确定性冲突，不得重复生成报告或推进状态。

### 4.4 关口、权限与前端契约

Gate 1 展示候选来源、匹配度、摘要及纳入/排除理由。批准生成新的 Passport 版本；驳回进入 `EVIDENCE_REVISION`。

Gate 2 展示未锚定声明、漂移 chunk、低置信度声明和冲突引文。任何硬失败阻断发布和当前视图导出；人工接受可处理的风险时必须写入理由。

前端必须提供声明—证据对比、行内风险批注、冲突 evidence 并列视图、退回理由、等待/恢复状态。前端不得从本地状态推断批准，也不得隐藏 Gate 阻断错误。

定稿 PDF/Markdown 是不可变静态归档，按报告/项目 ACL 读取。Citation/Evidence 在线穿透、原文高亮、P2 审计及重新导出的当前视图须按 `document_id` 重做实时 RBAC；拒绝时仅返回 `[Access Denied: Resource Restricted]`，不返回摘录、裸 locator 或可推断内容。

### 4.5 声明—证据审计

对每个 evidence 先执行确定性检查：Citation 存在、`document_id` 与 chunk 存在、`chunk_hash` 相同、`start_offset/end_offset` 有效、用户有当前访问权。任一 hash 或 offset 不符，标记 `CHUNK_DRIFTED`，不得作为支持性证据。

高影响声明必须全量执行语义支持评估；其余声明按版本化、可记录的抽样策略处理。LLM 仅输出风险信号：初始评分 `< 0.70` 或冲突为 `RISK_WARNING` / `LOW_CONFIDENCE_CLAIM`，回到 Gate 2。阈值变更前必须以人工金标准集记录误报率与漏报率。

### 4.6 接口与错误模型

接口路径由实现阶段定义；至少需要以下命令语义：创建/恢复 run、提交 Gate 1、提交 Gate 2、请求报告生成、读取当前状态、读取静态归档、请求在线 evidence 穿透。所有写命令要求身份、权限、Passport 版本和幂等键。

稳定错误码至少包含：`PASSPORT_HASH_MISMATCH`、`INVALID_STATE_TRANSITION`、`PASSPORT_VERSION_CONFLICT`、`GATE_REQUIRED`、`CHUNK_DRIFTED`、`ACCESS_DENIED`、`IDEMPOTENCY_CONFLICT`。错误响应不得泄露失权 document 或 chunk 内容。

## 5. 迁移计划

1. **准备**：定义 schema、状态迁移表、对象 key 命名及审计事件；为现有 `workflow_state` run 建立只读解析器。
2. **回填**：从现有 run/replay manifest 生成初始 Passport；无法形成完整 hash 的旧记录标记为 legacy，不伪造完整性。
3. **双写**：新 run 同时写旧 JSON 与新模块；比对 run、trace 集合、hash 与读权限的等价性。
4. **切读**：仅在回填覆盖、双写一致性和回滚演练通过后，读取新模块；旧 JSON 保留只读兼容窗口。
5. **收敛**：经批准删除旧写路径。保留导出和回放所需的历史只读数据及迁移审计。

回滚仅允许回到经验证的旧读路径；已经发布的静态工件不被回滚改写。若新 payload/hash 损坏，则停止新写、将受影响 run 置为 `DRAFT`，并从对象存储版本或旧只读数据恢复。

## 6. 影响

- **数据模型：** 新增 run/passport/gate/audit 的独立持久化记录与对象存储生命周期策略。
- **后端：** `ResearchWorkflowService` 保留研究步骤实现；`ResearchRunLifecycle` 成为状态、审计与调度的唯一 seam。
- **API：** 写命令增加版本、权限和幂等前置条件；现有同步调用需兼容迁移。
- **UI：** 新增两个关口、冲突/风险呈现及恢复体验。
- **安全：** 区分静态报告 ACL 与实时源文献 RBAC；审计记录需追加式、最小化敏感内容。
- **性能与成本：** 大 payload 转对象存储，避免行级 JSON 膨胀；需评估对象读取、hash 计算、审计保留与队列成本。

## 7. 备选方案

| 方案                                          | 优点                     | 缺点                                      | 结论              |
| --------------------------------------------- | ------------------------ | ----------------------------------------- | ----------------- |
| 保持 `workflow_state` JSON                    | 改动最小                 | 无并发/审计/大 payload 治理，难以长期暂停 | 放弃              |
| 只增加前端关口                                | 交付快                   | 可被 API 绕过，不具备治理效力             | 放弃              |
| 本提案：关系元数据 + 对象 payload +后端状态机 | 可审计、可恢复、扩展性好 | 有迁移与运维成本                          | 推荐，待 ADR 接受 |
| 直接引入 ARS/多 Agent 运行时                  | 复用表面流程             | 许可证、产品模型、RBAC 与复杂度不匹配     | 放弃              |

## 8. 验收与审查清单

- [ ] schema 校验、hash 校验与 legacy 回填测试。
- [ ] 所有非法状态转换、旧 Passport 批准新版本、重复回调均被拒绝或幂等处理。
- [ ] Gate 1/2 在匿名、普通、审批、管理员身份下的真实 API 探针。
- [ ] `CHUNK_DRIFTED`、无锚点、失权 evidence 均阻断当前视图导出。
- [ ] 静态归档不因源权限变化改写；在线穿透不泄露失权内容。
- [ ] 浏览器验证关口、退回理由、恢复和 Citation/Evidence 点击链。
- [ ] 数据模型、对象存储、成本、安全和无障碍评审完成。

## Changelog

| 版本   | 日期       | 变更                      |
| ------ | ---------- | ------------------------- |
| v0.1.0 | 2026-07-27 | 基于 ARS 对标基线创建初稿 |
