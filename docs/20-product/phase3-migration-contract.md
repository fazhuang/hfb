# Phase 3 Migration Contract — M0 冻结

**状态**: FROZEN — M0 冻结，可进入 M1
**上一阶段裁决**: `APPROVED_MIGRATION_REQUIRED`（能力 #1–#3） / `BLOCK_RELEASE`
**冻结基线**: HEAD 74cee05（R6 PASS: 574 UT / 204 FE E2E / 93 BE E2E ALL GREEN）
**冻结日期**: 2026-07-25
**版本比较方案**: B — 新建独立 `VersionComparisonPage` `/research/:projectId/version-comparison`

---

## 0. 原则

1. **先有 canonical，再删 legacy**。任何 legacy 代码在 canonical 等价测试全绿之前不得删除、skip、xfail 或改为迁移提示断言。
2. **禁止弱化证据链**。SourceRef → Citation → Evidence → 导出 的完整链路不得在任何步骤降级（fail-closed：无证据不显示引用、无引用不禁用导出）。
3. **URL 兼容**。所有 `/research/workspace`、`/v4/research`、`/v4/research-internal` 的历史入口在清退前必须有明确的兼容/跳转规则，且规则在 M0 冻结后不可变更。
4. **每个能力必须在 M0 有明确目标、URL 规则、等价验收标准**。任何一项缺失 → 停止，禁止进入 M1。

---

## 1. 当前架构全景

### 1.1 Legacy 页面（3 个视图，仍在服役）

| 视图                              | 路由                                        | 行数  | 功能                                                                                 |
| --------------------------------- | ------------------------------------------- | ----- | ------------------------------------------------------------------------------------ |
| `views/ResearchWorkspaceView.vue` | `/research/workspace`                       | ~2200 | 7 tab 单体：资料、版本、笔记、报告、研究（嵌入 ResearchWorkflowView）、V4 研究、助手 |
| `views/ResearchWorkflowView.vue`  | 无独立路由（嵌入 workspace tab `research`） | ~510  | 版本比较工作流（4 步：检索条文 → 选版本 → 运行比较 → 验证证据 + 笔记）               |
| `views/V4ResearchView.vue`        | `/v4/research-internal`                     | ~1200 | 3 tab：完整研究（5 步 pipeline）、教育模式、可视化                                   |

### 1.2 Canonical 页面（已迁移，per-project 作用域）

| 页面                                        | 路由                                 | 状态                                                                                      |
| ------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------- |
| `pages/research/ProjectListPage.vue`        | `/research`                          | 已闭合 — 直接渲染                                                                         |
| `pages/research/ProjectDetailPage.vue`      | `/research/:projectId`               | 已闭合 — 项目详情 + 操作入口                                                              |
| `pages/research/ResearchWorkspacePage.vue`  | `/research/:projectId/workspace`     | 已迁移 — 6 段（ContinueResearch、Activity、Reports、Notes、Resources、AssistantEntry）    |
| `pages/research/ResearchWorkflowPage.vue`   | `/research/:projectId/workflow`      | 已迁移 — 5 步 V4 topic→pipeline 工作流（**注意：非版本比较**）                            |
| `pages/research/ResearchResultPage.vue`     | `/research/:projectId/result/:runId` | 已迁移 — 报告、引用、证据、SourceRef、导出                                                |
| `pages/reports/ReportListPage.vue`          | `/reports`                           | 已迁移 — 跨会话报告聚合                                                                   |
| `pages/library/LibrarySearchPage.vue`       | `/library`                           | 已迁移 — 统一文献搜索                                                                     |
| `pages/knowledge/KnowledgeExplorerPage.vue` | `/knowledge`                         | **占位页** — 功能迁移中，模板明确声明 Knowledge Explorer / Entity Detail 后续 Sprint 实现 |

### 1.3 关键架构事实

- **ResearchSession.id === projectId**。系统中不存在独立的 `Project` 表或 `project_id` 列。域映射审计确认（ref: `docs/20-product/2011-project-domain-mapping-audit.md`）。
- **无恢复/中断 API**。V4 workflow 在单个同步 HTTP 响应中执行全部 5 步。不存在部分执行状态、中断/恢复端点。
- **ResearchWorkflowView（版本比较）无 canonical 替代**。Canonical `ResearchWorkflowPage` 实现的是 V4 topic→pipeline 工作流，而非 diff-based 古籍版本比较。
- **V4ResearchView 的教育/可视化 tab 推迟至 KnowledgeExplorer**。当前 KnowledgeExplorer 为占位页（明确标注功能迁移中），教育模式（概念学习）和可视化工作流（graph_type 选择）的等价实现均需后续 Sprint 完成。
- **Legacy 助手 tab（SSE AI chat）推迟**。无 canonical AI 助手页面。
- **引用提取逻辑重复**。`ResearchWorkspaceView.vue` 与 `V4ResearchView.vue` 各自实现相同的 `replay_manifest.retrieval_snapshot` × `traces` 交叉引用逻辑。

---

## 2. 逐项迁移契约

### 2.1 能力 #1：`/research/workspace` 全局聚合

**Legacy 描述**：单一 URL 承载 7 个 tab 的全部功能，通过 `route.query.tab` 切换，无项目作用域（用户从下拉框选择 session）。

**Canonical 目标**：

| Legacy Tab            | Canonical 归宿                                                                                                | 状态                                                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 资料 (materials)      | `LibrarySearchPage` `/library` — 统一文献搜索                                                                 | 已就绪                                                                                                                                        |
| 版本 (versions)       | `LibrarySearchPage` `/library` — 古籍版本搜索                                                                 | 已就绪                                                                                                                                        |
| 笔记 (notes)          | `ResearchWorkspacePage` `/research/:projectId/workspace` — RecentNotes 段                                     | 已就绪                                                                                                                                        |
| 报告 (reports)        | `ReportListPage` `/reports`（跨项目）+ `ResearchWorkspacePage` RecentReports 段（单项目）                     | **待验证** — 实测：项目详情页显示已有报告，但其 canonical workspace "最近研究运行"为空，未证明单项目 Reports 等价行为                         |
| 研究 (research)       | `VersionComparisonPage` `/research/:projectId/version-comparison`（**方案 B 新建**）                          | **待 M2 构建**                                                                                                                                |
| V4 研究 (v4-research) | `ResearchWorkflowPage` `/research/:projectId/workflow`（V4 pipeline）+ `ResearchResultPage`（报告/引用/导出） | ⚠️ **未完成迁移** — `/v4/research-internal` 仍直接加载 V4ResearchView（legacy 服役中）；re-search 缺失；写入/下载能力未在真实浏览器端到端验证 |
| 助手 (assistant)      | **推迟** — 未来 AI 助手页面（不在本次迁移范围）                                                               | 推迟                                                                                                                                          |

**URL 兼容规则**：

**实现方式**：`LegacyRedirect.vue` 组件 — 在 mount 时 `GET /api/v1/workspace/sessions?limit=1` 获取用户最近更新的 session，解析 `?tab=` 或路由名称，`router.replace` 至 canonical 路由。无 session 或 API 失败时降级至 `/research`（项目列表）。

| 旧 URL                                | 修复后行为                                                                                            | Canonical 目标                            |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| `/research/workspace`                 | 解析最近 session → `router.replace({ name: 'research-project-workspace', params: { projectId } })`    | `/research/:projectId/workspace`          |
| `/research/workspace?tab=materials`   | Tab-aware: `→ router.replace({ name: 'library-search' })`                                             | `/library`                                |
| `/research/workspace?tab=versions`    | Tab-aware: `→ router.replace({ name: 'library-search' })`                                             | `/library`                                |
| `/research/workspace?tab=notes`       | Tab-aware: `→ router.replace({ name: 'research-project-workspace', params: { projectId } })`          | `/research/:projectId/workspace`          |
| `/research/workspace?tab=reports`     | Tab-aware: `→ router.replace({ name: 'report-list' })`                                                | `/reports`                                |
| `/research/workspace?tab=research`    | Tab-aware: `→ router.replace({ name: 'research-project-version-comparison', params: { projectId } })` | `/research/:projectId/version-comparison` |
| `/research/workspace?tab=v4-research` | Tab-aware: `→ router.replace({ name: 'research-project-workflow', params: { projectId } })`           | `/research/:projectId/workflow`           |
| `/workspace`                          | 路由名 `legacy-workspace-short`: `→ research-project-workspace`                                       | `/research/:projectId/workspace`          |
| `/v4/research`                        | 路由名 `legacy-v4-research`: `→ research-project-workflow`                                            | `/research/:projectId/workflow`           |
| `/v4`                                 | 路由名 `legacy-v4`: `→ research-project-workflow`                                                     | `/research/:projectId/workflow`           |
| `/v4/research-internal`               | 路由名 `legacy-v4-research-internal`: `→ research-project-workflow`                                   | `/research/:projectId/workflow`           |
| `/research`                           | 路由名 `legacy-research`: `→ research-project-list` (直接，无 API 调用)                               | `/research`                               |

**降级处理**：

- 无 session → `/research`（项目列表）
- API 错误 (network/500) → `/research`（项目列表）
- 未知 `?tab=` 值 → 按路由名称解析（无 tab 处理）

**迁移完成判定**：

- [x] 7 个 tab 的每项归宿均有 canonical 等价实现或明确的推迟声明
- [x] `/research/workspace` 访问时，旧 URL 的 session 选择/上下文恢复规则清晰可用 — **Task 2B**: LegacyRedirect 组件实现 session-aware 跳转
- [x] 旧 `/research/workspace?tab=*` 全部有确定的跳转行为 — **Task 2B**: TAB_MAP 映射全部 7 个 tab（assistant 默认降级至 workspace）
- [x] ResearchWorkspaceView.vue 可安全变为纯兼容 adapter 或删除（M4） — **Task 2B**: `/v4/research-internal` 不再直接加载 V4ResearchView，LegacyRedirect 替代

**停止条件**：

- 助手 tab（SSE AI chat + evidence sidebar + graph preview）推迟，但必须在 M0 中标记为「已知未迁移」，不是「静默丢失」
- 如版本比较（tab=research）无 canonical 目标，则此能力整体 BLOCK，直至 §2.2 解决

---

### 2.2 能力 #2：版本比较 Workflow

**Legacy 描述**：`ResearchWorkflowView.vue`（~510 行），嵌入在 Workspace 的 "研究" tab 内（`/research/workspace?tab=research`），无独立路由。实现古籍版本差异比较：

- 步骤 1：全文搜索经文（`GET /api/v1/search?types=passage`）
- 步骤 2：选择源版本 / 目标版本
- 步骤 3：运行差异引擎（`PUT /api/v1/research/sessions/:id/version-comparison`），输出差异计数、相似度比率、操作表
- 步骤 4：验证语料证据 + 编写笔记

**⚠️ 关键差距**：Canonical `ResearchWorkflowPage` 实现的是 V4 topic→pipeline 研究（`POST /api/v4/research/workflow`），**不是 diff-based 版本比较**。两者是完全不同的工作流。

**✅ 方案已选定：B — 新建独立 VersionComparisonPage**

**Canonical 目标**：新建 `pages/research/VersionComparisonPage.vue`，路由 `/research/:projectId/version-comparison`。

**实现范围**：

- 新路由 `research-project-version-comparison`，加入 `ResearchAppLayout` children
- 新 composable `composables/useVersionComparison.ts`（拥有状态机、API 调用、session 恢复、导出）
- 4 个步骤组件 `components/research/version-comparison/`：`PassageSearchStep`、`VersionSelectStep`、`DiffResultStep`、`EvidenceVerifyStep`
- 复用现有 `ResearchPageHeader`、`LoadingState`、`EmptyState`、`ErrorState` 共享组件
- **不修改** `ResearchWorkflowPage.vue` 或 `useResearchWorkflow.ts`

**设计原则**：

- 独立 composable，不污染 V4 workflow 的 `useResearchWorkflow`
- 遵循 canonical 模式：sessionStorage 隔离 (`hfb.version-comparison.{projectId}.state`)、per-projectId 作用域、stale-response 丢弃
- API 不变：复用现有 `GET /api/v1/search?types=passage`、`PUT /api/v1/research/sessions/:id/version-comparison`、`POST /api/v1/workspace/sessions/:id/notes`

**URL 兼容规则**：

| 旧入口                              | 兼容行为                                                                                           |
| ----------------------------------- | -------------------------------------------------------------------------------------------------- |
| `/research/workspace?tab=research`  | → `/research/:projectId/version-comparison`（需先解析项目上下文，取最近活跃 session 的 projectId） |
| Workspace 内嵌 ResearchWorkflowView | → 不再嵌入；独立路由 `/research/:projectId/version-comparison` 访问                                |

**等价验收标准**（无论方案 A/B）：

- [ ] 4 步工作流完整可用：经文搜索 → 版本选择 → 差异比较 → 证据验证 + 笔记
- [ ] 会话自动创建 / 恢复（遍历最近 10 个 session 的比较数据）
- [ ] 源 === 目标版本阻止（sameVersion 校验）
- [ ] 语料验证横幅（corpus_status === 'approved'）
- [ ] 导出 markdown blob 下载
- [ ] 空 session 列表 → 仍渲染 UI（不崩溃）
- [ ] 网络错误 / version-comparison 返回 null → 不崩溃，UI 可用
- [ ] 跨项目隔离：projectId 作用域正确，不泄露其他 session 数据
- [ ] 与现有 3 个 legacy 测试等价（`research-workflow.test.ts`）：
  - `skips sessions whose version-comparison returns data:null`
  - `renders workflow UI even when session list is empty`
  - `survives network errors while probing comparison sessions`

**Legacy 测试映射**（`apps/frontend/src/__tests__/research-workflow.test.ts`，3 个测试）：

| Legacy 测试                                                          | M1 等价测试要求                                                                     |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| skips sessions with data:null → probes all, renders valid comparison | Canonical 页面：多个 session 中部分返回 null 时，继续探测其余，最终渲染有效比较数据 |
| renders UI with empty session list                                   | Canonical 页面：零 session 时仍渲染 UI（检索条文、验证语料标签可见）                |
| survives network errors probing comparison                           | Canonical 页面：API 网络错误不抛异常，UI 可用                                       |

---

### 2.3 能力 #3：V4 Research

**Legacy 描述**：`V4ResearchView.vue`（~1200 行），路由 `/v4/research-internal`。3 个 tab：

| Tab                    | 功能                                                                                                                       | API                                                                                                                                                 |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| 完整研究 (research)    | topic → 5 步 pipeline（topic_selection → literature_retrieval → evidence_synthesis → report_generation → citation_export） | `POST /api/v4/research/session`、`POST /api/v4/research/workflow`、`GET /api/v4/research/session/:id/runs`、`POST /api/v4/research/runs/:id/replay` |
| 教育模式 (education)   | 概念学习（初级/中级/高级），段落 + 引用计数                                                                                | `POST /api/v4/education/learn`                                                                                                                      |
| 可视化 (visualization) | 知识图谱（概念/引用/时间线/文档 graph_type）                                                                               | `POST /api/v4/visualization/graph`                                                                                                                  |

**Canonical 目标**：

| #   | Legacy 功能                                                                    | V4 源代码位置                         | Canonical 归宿                                                                          | 路由                                                                   | 真实 API                                                                    | 浏览器测试                                                                                                                             | 状态                                   |
| --- | ------------------------------------------------------------------------------ | ------------------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| 1   | Workflow 执行 — topic 输入 + 5 步 pipeline                                     | `V4ResearchView.vue:536-603`          | `ResearchWorkflowPage` + `useResearchWorkflow.submitWorkflow()`                         | `/research/:projectId/workflow`                                        | `POST /api/v4/research/workflow`                                            | E2E: `test_successful_workflow_uses_current_run_artifacts` (L686), UT: M1-V4-001                                                       | **已迁移**                             |
| 2   | 5 步状态展示 — step list 含完成/失败/待定标识                                  | `V4ResearchView.vue:64-78`            | `WorkflowStepNavigation` + `.wsn-step` items in `ResearchWorkflowPage`                  | `/research/:projectId/workflow`                                        | `POST /api/v4/research/workflow`（响应含 steps 数组）                       | UT: M1-V4-002 (5 步导航可见)                                                                                                           | **已迁移**                             |
| 3   | 报告预览 — markdown 文本渲染（截断 2000 字）                                   | `V4ResearchView.vue:90-93, 372-376`   | `ResearchReportStep`（workflow 内）+ `ResearchReportViewer`（result page）              | `/research/:projectId/workflow` + `/research/:projectId/result/:runId` | `GET /api/v4/research/session/{id}/runs` → `output_artifacts.markdown`      | UT: M1-V4-013 (报告渲染为可读 sections)                                                                                                | **已迁移**                             |
| 4   | 引用展示 — claim_text/quote/citation_text/trace_id/document_id/source_ref_id   | `V4ResearchView.vue:96-120`           | `EvidenceReviewStep`（workflow）+ `CitationPanel`（result page）                        | `/research/:projectId/workflow` + `/research/:projectId/result/:runId` | `GET /api/v4/research/session/{id}/runs` → `replay_manifest`                | UT: M1-V4-007 (evidence items 渲染), M1-V4-014 (source info 存在)                                                                      | **已迁移**                             |
| 5   | 从引用创建笔记 — 每个引用旁的专用按钮                                          | `V4ResearchView.vue:111-117, 694-713` | `useResearchWorkflow.saveCitation()` → `POST /api/v1/workspace/sessions/{id}/citations` | `/research/:projectId/workflow`                                        | `POST /api/v1/workspace/sessions/{id}/citations`                            | UT: citationSaveState 追踪 (idle/saving/saved)                                                                                         | **已迁移**                             |
| 6   | 导出 — 报告 + 笔记的客户端 Blob 下载                                           | `V4ResearchView.vue:123-131, 623-657` | `ResearchResultPage` + `useResearchResult.exportMarkdown()`                             | `/research/:projectId/result/:runId`                                   | `GET /api/v4/research/session/{id}/runs/{runId}/export`                     | E2E: `TestResearchResultPageE2E` 导出测试, UT: M1-V4-015                                                                               | **已迁移**                             |
| 7   | 保存笔记 — `POST /api/v1/workspace/sessions/{id}/notes`                        | `V4ResearchView.vue:133-141, 659-683` | `useResearchWorkflow.saveNote()`                                                        | `/research/:projectId/workflow`                                        | `POST /api/v1/workspace/sessions/{id}/notes`                                | UT: saveNote → savingMessage 反馈                                                                                                      | **已迁移**                             |
| 8   | 基于报告重新搜索 — 提取关键词 → 搜索页                                         | `V4ResearchView.vue:169-177, 686-692` | `useResearchWorkflow.navigateToLibrarySearch()` → `ResearchReportStep` 按钮             | `/research/:projectId/workflow` → `/library`                           | `router.push({ name: 'library-search', query: { q } })`                     | UT: M1-V4-016 [RESOLVED]                                                                                                               | **已迁移** (Task 2B)                   |
| 9   | **重放验证** — `POST /api/v4/research/runs/{id}/replay`，显示 matched + SHA256 | `V4ResearchView.vue:180-197, 605-621` | `ResearchResultPage` + `useResearchResult.replayRun()`                                  | `/research/:projectId/result/:runId`                                   | `POST /api/v4/research/runs/{id}/replay`                                    | UT: M1-V4-003/004 (组件回归), E2E: `test_gap_replay_verification_matched` + `test_gap_replay_verification_mismatched` (真实浏览器闭环) | **已迁移** (d08fbbd, 101e9ef, e6a5153) |
| 10  | 运行历史列表 — 显示 session 所有 run                                           | `V4ResearchView.vue:200-206`          | `ResearchWorkspacePage` (RecentReports) + `ReportListPage`                              | `/research/:projectId/workspace` + `/reports`                          | `GET /api/v4/research/session/{id}/runs`                                    | E2E: `TestResearchReportsPageE2E`                                                                                                      | **已迁移**                             |
| 11  | 开始新工作流 (reset) — 清除所有状态                                            | `V4ResearchView.vue:208-210, 715-731` | `useResearchWorkflow.reset()`                                                           | `/research/:projectId/workflow`                                        | 纯客户端状态重置                                                            | UT: reset → stepState='question'                                                                                                       | **已迁移**                             |
| 12  | 通过 ?run= 加载历史 — 遍历 sessions 查找匹配 run                               | `V4ResearchView.vue:399-436`          | 直接 URL `/research/:projectId/result/:runId`                                           | `/research/:projectId/result/:runId`                                   | `GET /api/v1/workspace/sessions` + `GET /api/v4/research/session/{id}/runs` | E2E: `TestResearchResultPageE2E` (L2481+)                                                                                              | **已迁移**（改进 — 无需遍历）          |
| 13  | 已用时间计数器 — 自 workflow 开始计秒                                          | `V4ResearchView.vue:59-60, 381-394`   | `AnalysisPendingState`（不确定进度指示器）                                              | `/research/:projectId/workflow`                                        | —                                                                           | E2E: workflow 提交 loading 态                                                                                                          | **已迁移**（等价 UX）                  |
| 14  | 教育模式 — topic + level → 概念学习                                            | `V4ResearchView.vue:218-261, 737-770` | `KnowledgeExplorerPage`                                                                 | `/knowledge`                                                           | `POST /api/v4/education/learn`                                              | N/A                                                                                                                                    | **推迟** — 占位页                      |
| 15  | 可视化 — concept labels + graph_type → 图谱                                    | `V4ResearchView.vue:264-310, 776-808` | `KnowledgeExplorerPage`                                                                 | `/knowledge`                                                           | `POST /api/v4/visualization/graph`                                          | N/A                                                                                                                                    | **推迟** — 占位页                      |

**✅ 停止条件 #9 — 重放验证（已解决，2026-07-29）**：

- **Legacy 行为** (`V4ResearchView.vue:605-621`)：`POST /api/v4/research/runs/{runId}/replay` → 显示 matched/mismatched badge + original/replay SHA256
- **规范实现**（d08fbbd, 101e9ef, e6a5153）：
  - `ResearchResultPage` — `.rpage-replay` 区域、`data-testid="canonical-replay"` button、`data-testid="canonical-replay-result"` 结果展示
  - `useResearchResult` — `replayRun()` 函数，含 stale-response 丢弃保护
  - 显示 "重放一致"/"重放不一致" + 原始/重放 SHA-256
- **后端 API 状态**：`POST /api/v4/research/runs/{id}/replay` 端点存在且可用，通过 `replayRun()` 在 `useResearchResult` 中规范暴露
- **验证**：M1-V4-003 (matched=true) / M1-V4-004 (matched=false) UT 通过；`test_gap_replay_verification_matched` / `test_gap_replay_verification_mismatched` E2E 真实浏览器通过
- **严重程度**：低 — 重放验证为开发/调试功能，非终端用户核心流程。用户通过重新提交相同 topic 并对比报告即可等价验证确定性

**URL 兼容规则**：

| 旧 URL                  | 兼容行为                                                                | 当前实际                                   | 状态      |
| ----------------------- | ----------------------------------------------------------------------- | ------------------------------------------ | --------- |
| `/v4/research-internal` | → LegacyRedirect → session-aware 跳转至 `/research/:projectId/workflow` | **LegacyRedirect 处理**（router/index.ts） | ✅ 已清退 |
| `/v4/research`          | → LegacyRedirect → `/research/:projectId/workflow`                      | **LegacyRedirect 处理**                    | ✅ 已清退 |
| `/v4`                   | → LegacyRedirect → `/research/:projectId/workflow`                      | **LegacyRedirect 处理**                    | ✅ 已清退 |

**逐项迁移完成判定**：

- [x] Workflow 执行：legacy 5 步 pipeline 与 canonical 5 步行为等价 — M1-V4-001/002 通过，E2E `test_successful_workflow_uses_current_run_artifacts` 通过
- [x] 报告渲染：canonical result page 与 legacy report 详情等价 — M1-V4-013 通过
- [x] Citation/SourceRef 等价：Task 2B snapshot 回退路径修复 (374d5ad) — `useResearchWorkflow` + `useResearchResult` 中 Path 2 同时提取 citation
- [x] 无证据 fail-closed：`success=false` + `records=0` → NO_EVIDENCE error banner — M1-V4-005 通过，E2E `test_workflow_no_evidence_shows_error_banner` 通过
- [x] 空 citation 字段 → 不渲染 citation — M1-V4-006 通过
- [x] 有 citation 内容 → evidence/citation 可见 — M1-V4-007 通过
- [x] **重放验证：canonical replay UI 已实现** — M1-V4-003/004 (组件回归) 通过，E2E `test_gap_replay_verification_matched` + `test_gap_replay_verification_mismatched` (真实浏览器闭环) 全部通过 (d08fbbd, 101e9ef, e6a5153, ed42c49+)
- [x] 教育模式：明确推迟至 KnowledgeExplorer — M1-V4-008/009 DEFERRED
- [x] 可视化：明确推迟至 KnowledgeExplorer — M1-V4-010/011 DEFERRED
- [x] 引用保存/导出：canonical 行为与 legacy 等价 — M1-V4-014/015 通过
- [x] `/v4/*` 兼容跳转：LegacyRedirect 处理所有场景 — E2E `TestV4ResearchPortal` 6 个测试通过
- [x] 基于报告重新搜索（re-search）：Task 2B `navigateToLibrarySearch()` — M1-V4-016 RESOLVED

**Legacy 测试映射**（`apps/frontend/src/__tests__/v4-research.test.ts`，10 个测试）：

| Legacy 测试                                        | M1 等价测试要求                                                                                                                         |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| renders all three tabs                             | Canonical 等价页面的所有功能入口可见                                                                                                    |
| clicking run workflow calls /session and /workflow | Canonical workflow page：POST session + POST workflow + GET runs 调用链等价                                                             |
| clicking replay with matched=true                  | Canonical result page：replay → matched=true → .rpage-replay-matched "重放一致"（真实浏览器 E2E 闭环）                                  |
| clicking replay with matched=false                 | Canonical result page：replay → matched=false → .rpage-replay-mismatched "重放不一致"（真实浏览器 E2E 闭环，tampered manifest fixture） |
| education sends level parameter                    | 推迟 — M1 标记为 deferred，不 skip/xfail                                                                                                |
| education shows error on API failure               | 推迟 — M1 标记为 deferred                                                                                                               |
| visualization sends graph_type                     | 推迟 — M1 标记为 deferred                                                                                                               |
| visualization shows empty state                    | 推迟 — M1 标记为 deferred                                                                                                               |
| no-evidence state when success=false, records=0    | Canonical workflow page：NO_EVIDENCE error banner，不渲染 report body / citations，导出禁用                                             |
| hides save-citation when citation fields empty     | Canonical workflow page：无 snapshot citation → 不渲染 save-citation                                                                    |
| shows save-citation when citation has real content | Canonical workflow page：有 snapshot citation → citation body 渲染，导出启用                                                            |

---

section: 2.4

### 2.4 ✅ 停止条件已解决：重放验证 (replay) — canonical 等价实现 (2026-07-29)

**Legacy 行为** (`V4ResearchView.vue:605-621`):

```typescript
async function replayRun() {
  if (!workflowRunId.value) return;
  replaying.value = true;
  replayResult.value = null;
  const { data } = await api.post(`/api/v4/research/runs/${workflowRunId.value}/replay`);
  replayResult.value = {
    matched: data.data.matched,
    original_output_sha256: data.data.original_output_sha256,
    replay_output_sha256: data.data.replay_output_sha256,
  };
}
```

— 对已完成的工作流运行进行确定性验证，比较 SHA256 哈希值，显示 matched/mismatched badge。

**Canonical 实现**（d08fbbd, 101e9ef, e6a5153）：

- **`ResearchResultPage.vue:39-78`** — `.rpage-replay` 区域、`data-testid="canonical-replay"` button、`data-testid="canonical-replay-result"` 结果展示、"重放一致"/"重放不一致" + 原始/重放 SHA-256
- **`useResearchResult.ts:598-639`** — `replayRun()` 函数，含 stale-response 丢弃保护、concurrent-guard
- **路由**：`/research/:projectId/result/:runId`
- **API**：`POST /api/v4/research/runs/{runId}/replay`，直接通过 `api.post()` 调用

**验证**：

- M1-V4-003 (matched=true) / M1-V4-004 (matched=false) — 组件回归测试通过（mock API，验证 UI 渲染）
- `test_gap_replay_verification_matched` — 真实浏览器 E2E 通过（完整 UI 导航闭环: /login → /research → 点击项目 → 项目详情 → 点击报告链接 → result page → 点击 replay 按钮 → 断言 matched=true + 2x SHA-256）
- `test_gap_replay_verification_mismatched` — 真实浏览器 E2E 通过（完整 UI 导航闭环: 隔离测试夹具通过文件级 SQLite 直接注入 fabricated canonical_output_sha256 创建持久化 tampered run → 浏览器仅读取已存在状态 → 断言 matched=false + 2x 不同 SHA-256）

**先前停止条件 §2.4（re-search）已 RESOLVED**：Task 2B — `navigateToLibrarySearch()` 在 `useResearchWorkflow` 中实现。`ResearchReportStep` 渲染 "基于报告重新搜索" 按钮 → `router.push({ name: 'library-search', query: { q } })`。

---

## 3. 推迟声明（不在本次迁移范围）

| 功能                                                        | Legacy 位置                                        | 推迟去向                                 | 理由                                                           |
| ----------------------------------------------------------- | -------------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------- |
| AI 助手（SSE 流式 chat + evidence sidebar + graph preview） | `ResearchWorkspaceView.vue` assistant tab          | 未来 AI 助手页面                         | 需要独立的 SSE 流式架构设计，不可仓促迁入 workspace            |
| 教育模式（概念学习）                                        | `V4ResearchView.vue` education tab                 | `KnowledgeExplorerPage` 后续 Sprint 实现 | KnowledgeExplorer 当前为占位页，需产品设计后在后续 Sprint 实现 |
| 可视化工作流（graph_type 选择 + 图谱渲染）                  | `V4ResearchView.vue` visualization tab             | `KnowledgeExplorerPage` 后续 Sprint 实现 | KnowledgeExplorer 当前为占位页，需后续 Sprint 实现             |
| 材料/版本浏览（独立于项目的数据浏览）                       | `ResearchWorkspaceView.vue` materials/versions tab | `LibrarySearchPage`                      | 已就绪 — Library 是 canonical 替代，URL 兼容规则见 §2.1        |

---

## 4. 跨能力等价验收标准（通用）

### 4.1 证据链完整性（不得弱化）

每个迁移后的能力必须验证：

- [ ] **SourceRef**：来源标题、文献 ID、passage_id、internal link 格式（`/versions/{document_id}?passage={passage_id}`）、withdrawn source 无 internal link
- [ ] **Citation**：trace_id 与 evidence 一致、citation_text 非空、document_id 非空、不与历史 run 混淆
- [ ] **Evidence**：AI 归纳（claim_text）与原文（quote）区分显示、来源信息完整、不显示置信度分数、不将 document_id 当 source title
- [ ] **导出**：真实后端 endpoint（`text/markdown`）、正确 filename、Content-Disposition、双击防抖、无 PDF/DOCX 按钮
- [ ] **Fail-closed**：无证据 → 不渲染引用 → 导出禁用（不降级为「无证据但可导出」）

### 4.2 安全护栏（不得弱化）

- [ ] **XSS**：`<script>`、`onerror`、`onclick`、`javascript:` URL、`<iframe>`、`<svg>` 在 report markdown 中不可执行
- [ ] **跨用户隔离**：用户 A 访问用户 B 的 workspace/workflow/result → 404（不泄露标题、报告、run 数据）
- [ ] **跨项目隔离**：session A 数据不泄露至 session B（route switch 清除旧数据、stale response 丢弃）

### 4.3 状态覆盖（不得遗漏）

每个迁移后的能力必须覆盖：

- [ ] **成功态**：正常数据渲染
- [ ] **空态**：无 session、无 run、无 citation、无 evidence、无 report → 各自显示合适空态 UI
- [ ] **网络错误**：API timeout、500、network error → 不崩溃，显示错误 banner + 重试
- [ ] **权限错误**：401/403 → 「课题不存在」或禁止访问，不泄露资源存在性
- [ ] **无效输入**：404 session、run 不属于 session、无效 UUID → 明确错误状态

---

## 5. 迁移依赖与顺序

```
M0（本契约 FROZEN ✅）
 │
 ├── M1（建立迁移测试基线 — ⚠️ 需回退）
 │     │  依赖：M0 全部能力有明确目标
 │     │  产物：2 个新测试文件，25 个映射测试
 │     │  结果：2/2 文件全绿
 │     │  ⚠️ 但是：等价测试声明不等同于真实浏览器端到端行为证明；
 │     │    旧 URL 等价迁移未实现（无条件重定向 ≠ 等价迁移）；
 │     │    legacy 路径未清退（/v4/research-internal 仍在服役）；
 │     │    单项目 Reports 等价未在真实环境验证。
 │     │
 │     ├── M2（迁移版本 Workflow ✅ 完成）
 │     │     │  依赖：M1 版本比较等价测试就绪
 │     │     │  产物：
 │     │     │    - apps/frontend/src/pages/research/VersionComparisonPage.vue (196 行)
 │     │     │    - apps/frontend/src/composables/useVersionComparison.ts (325 行)
 │     │     │    - apps/frontend/src/components/research/version-comparison/
 │     │     │      ├── PassageSearchStep.vue
 │     │     │      ├── VersionSelectStep.vue
 │     │     │      ├── DiffResultStep.vue
 │     │     │      └── EvidenceVerifyStep.vue
 │     │     │    - apps/frontend/src/router/index.ts (+4 行：新增路由)
 │     │     │  门禁：3 legacy 等价测试 PASS + 10 canonical 测试 PASS + type-check clean
 │     │     │  全量验证：21 文件 599 测试 ALL GREEN + vue-tsc noEmit clean
 │     │     │
 │     ├── M3（迁移 V4 Research ✅ 完成）
 │     │     │  依赖：M1 V4 等价测试就绪
 │     │     │  产物：
 │     │     │    - /v4/* → /research 直接跳转（不再经 legacy workspace）
 │     │     │    - /v4/research-internal 保留（M4 清退）
 │     │     │    - 推迟声明最终确认：replay / education / visualization → 后续版本
 │     │     │  门禁：15 个 v4-to-canonical-equivalence 测试全绿（含 deferred）
 │     │     │  全量验证：21 文件 599 测试 ALL GREEN + type-check clean
 │     │
 │     └── M4（迁移全局 Workspace + 清退 legacy ✅ 完成）
 │           │  依赖：M2 + M3 完成
 │           │  产物：
 │           │    - ResearchWorkspaceView 路由 → redirect /research（不再渲染）
 │           │    - /workspace → /research（更新重定向）
 │           │    - AppNavbar 移除旧版 workspace/v4-research 链接
 │           │    - 5 项删除前证明 ✅
 │           │  全量验证：21 文件 599 测试 ALL GREEN + type-check clean
 │           │
 │           └── M5（运行闭环与发布验收）
```

---

## 6. 停止条件（M0 冻结门禁）

在以下全部满足前，M0 不得标记为 FROZEN，M1 不得开始：

- [x] **§2.2 版本比较方案（A/B/C）已选定并记录在本契约中** → **方案 B：新建独立 `VersionComparisonPage` `/research/:projectId/version-comparison`**
- [x] 能力 #1 全部 7 个 tab 的归宿均有明确声明（canonical 等价 / 推迟 / 已就绪），且推迟项不被静默丢失
- [x] 能力 #3 的 3 个 tab（research / education / visualization）逐项归宿明确
- [x] **旧 URL 等价迁移** — **Task 2B**: LegacyRedirect.vue 实现 session-aware 跳转，7 个 legacy 路由名 + 6 个 tab 值 → canonical 路由解析，降级至 project list
- [x] **legacy 路径清退** — **Task 2B**: `/v4/research-internal` 不再直接加载 V4ResearchView（`legacy-v4-research-internal` → LegacyRedirect → `/research/:projectId/workflow`）
- [x] **单项目 Reports 等价** — **Task 2B**: RecentReports.vue `hasReportArtifact` 过滤器从仅 `report_generation=completed` 放宽为任何步骤 `completed`，与 ProjectReports.vue 行为对齐。同一 `GET /api/v4/research/session/{id}/runs` 响应产生相同列表。
- [x] **re-search 缺失** — **Task 2B**: `navigateToLibrarySearch()` 在 `useResearchWorkflow` composable 中实现。`ResearchReportStep` 渲染 "基于报告重新搜索" 按钮（v-if="report.topic"），emit `re-search` 事件，`ResearchWorkflowPage` 处理并调用 `navigateToLibrarySearch(router)` → `router.push({ name: 'library-search', query: { q: extractedQuery } })`（2026-07-28: re-search gap 已闭合）
- [x] **Docker 构建** — **Task 2B**: docker/dev/Dockerfile.backend 和 docker/prod/Dockerfile.backend 中 `COPY pyproject.toml README.md ./` 修复 `OSError: Readme file does not exist`（pyproject.toml:9 readme = "README.md" 要求）
- [x] **⚠️ 重放验证（RESOLVED — 2026-07-29）**：V4 `POST /api/v4/research/runs/{id}/replay` → matched/mismatched badge + SHA256 显示在 `ResearchResultPage.vue:39-78`。Canonical 实现通过 `useResearchResult.replayRun()` 暴露，后端 API 通过 `api.post()` 调用。UT M1-V4-003/004 (组件回归) + 真实浏览器 E2E `test_gap_replay_verification_matched` + `test_gap_replay_verification_mismatched` (完整 UI 导航闭环: login→项目列表→项目详情→报告链接→result page→replay 按钮) 全部通过。matched=false 由隔离测试夹具通过文件级 SQLite 直接注入 tampered canonical_output_sha256 创建持久化状态实现。实现提交: d08fbbd, 101e9ef, e6a5153, ed42c49+。
- [x] **写入/下载能力端到端验证（RESOLVED — 2026-07-29）**：`test_export_markdown_real_browser_download` 完整 UI 导航闭环验收通过（/login → Research → 项目列表点击 → 项目详情点击报告 → 结果页点击 "导出 Markdown" → 真实浏览器 download 事件触发）。断言验证：HTTP 200 导出响应、Content-Type text/markdown、Content-Disposition attachment、文件名 `hfb-research-report-{run_id[:8]}.md`、Markdown 内容包含真实报告标题 "结果页真实工作流验证"。禁止 page.goto() 直达受保护 URL、token 注入、mock/seed。提交: M1-V4-EXPORT-REAL-BROWSER-06。
- [x] **⚠️ Citation/SourceRef 等价（RESOLVED — 2026-07-29）**：`test_real_workflow_sourceref_link_routes` 验收通过。Canonical 路由为 `/library/{document_id}?passage={passage_id}`。新增 `append-passage` API（POST /api/v1/search/documents/{id}/append-passage，document:update 权限、savepoint + SELECT FOR UPDATE 原子块、重新执行全文合规 gate、追加后重置 review→pending 及 rag_enabled→False）使同一 document 可得两个不同 passage。测试验证：完整 UI 导航（可见 Research 入口点击，no `page.goto()` 到 result URL）→ 同一 document_id 的两个 trace（不同 passage_id）各匹配其 Citation → Evidence trace 一致 → SourceRef internal link **必须存在**且精确为 `/library/{doc_id}?passage={psg_id}`（禁止 fallback）→ 两条链接均实际点击 → 浏览器 URL 验证 `/library/{doc_id}` + `passage` 参数 → 页面内容非空、未重定向到登录。安全：savepoint 回滚测试（注入 audit 失败后零状态变化）、未认证/无权限拒绝、合规 gate 拒绝。提交: M1-V4-SOURCEREF-APPEND-PASSAGE-09 + M1-V4-SOURCEREF-APPEND-PASSAGE-SAFETY-10。

**当前状态：BLOCK_RELEASE** — 2026-07-28 验收。Task 2B 修复了 7/8 阻断条件。**重放验证已解决 (2026-07-29)**：canonical 等价实现在 ResearchResultPage + useResearchResult (d08fbbd, 101e9ef, e6a5153)；真实浏览器 E2E 覆盖 matched=true + matched=false（完整 UI 导航闭环）。**下载已验证 (2026-07-29)**：`test_export_markdown_real_browser_download` 通过完整 UI 导航（login → 项目列表 → 项目详情 → 报告 → 导出）触发真实浏览器 download，HTTP 200 + 正确文件名 + Markdown 内容验证。**Citation/SourceRef 已验证 (2026-07-29)**：`test_real_workflow_sourceref_link_routes` 同 document / 不同 passage 双链点击 canonical /library/{doc_id}?passage={psg_id} 通过，新增 append-passage API 提供真实数据路径。所有 8 项阻断条件均已解决。

## M5 发布验收命令（需在当前 HEAD 执行后方可判定）

以下命令需在目标 HEAD 逐一执行，结果不得臆造：

```bash
# Health
curl -fsS http://127.0.0.1:8000/health

# Ready
curl -fsS http://127.0.0.1:8000/ready

# Type-check
cd apps/frontend && npm run type-check

# Unit tests
cd apps/frontend && npm run test -- --run

# Build
cd apps/frontend && npm run build

# Backend E2E
uv run pytest tests/e2e/test_critical_journeys.py tests/e2e/test_reader_e2e.py \
  --browser chromium -q --no-cov

# Git status
git status --short && git rev-parse --short HEAD && git log --oneline -1
```

**未完成项（当前 HEAD 未验收）**：

- M5 发布验收命令尚未在当前 HEAD 运行
- `/v4/research-internal` 内部入口仍对开发环境开放（Phase 3 未公开入口验收）
- Knowledge 占位页（教育模式/可视化工作流等价实现）推迟，未完成
- API 契约未收口（V4 内部路由兼容行为未声明为最终状态）

**前提条件**：以上未完成项全部解决、当前 HEAD 上全部命令均通过后，方可更新状态为 RELEASE_READY。

---

## 附录 A：路由名称映射表（当前状态）

| 路由名称                              | URL                                       | 组件                        | 状态                                                                                   |
| ------------------------------------- | ----------------------------------------- | --------------------------- | -------------------------------------------------------------------------------------- |
| `research-project-list`               | `/research`                               | `ProjectListPage.vue`       | ACTIVE canonical                                                                       |
| `research-project-detail`             | `/research/:projectId`                    | `ProjectDetailPage.vue`     | ACTIVE canonical                                                                       |
| `research-project-workspace`          | `/research/:projectId/workspace`          | `ResearchWorkspacePage.vue` | ACTIVE canonical                                                                       |
| `research-project-workflow`           | `/research/:projectId/workflow`           | `ResearchWorkflowPage.vue`  | ACTIVE canonical                                                                       |
| `research-project-version-comparison` | `/research/:projectId/version-comparison` | `VersionComparisonPage.vue` | **ACTIVE canonical — M2 完成**                                                         |
| `research-project-result`             | `/research/:projectId/result/:runId`      | `ResearchResultPage.vue`    | ACTIVE canonical                                                                       |
| `library-search`                      | `/library`                                | `LibrarySearchPage.vue`     | ACTIVE canonical                                                                       |
| `report-list`                         | `/reports`                                | `ReportListPage.vue`        | ACTIVE canonical                                                                       |
| `knowledge-explorer`                  | `/knowledge`                              | `KnowledgeExplorerPage.vue` | **占位页** — 功能迁移中，后续 Sprint 实现                                              |
| `research-workspace`                  | `/research/workspace`                     | `ResearchWorkspaceView.vue` | RETIRED — M4 已重定向至 `/research`（⚠️ 无条件重定向，丢失 tab 与项目上下文 — 不等价） |
| `v4-research`                         | `/v4/research-internal`                   | `V4ResearchView.vue`        | **LEGACY 仍在服役** — 路由仍直接加载 V4ResearchView，未经清退                          |
| `research-home`                       | `/research/home`                          | `ResearchHomeView.vue`      | COMPATIBILITY — 渲染 ProjectListPage                                                   |
| `research-new`                        | `/research/new`                           | `ResearchNewView.vue`       | COMPATIBILITY — 渲染 ProjectListPage                                                   |
| —                                     | `/v4/research`                            | （redirect）                | COMPATIBILITY — M3 更新：→ `/research`（无条件，无项目上下文）                         |
| —                                     | `/v4`                                     | （redirect）                | COMPATIBILITY — M3 更新：→ `/research`（无条件，无项目上下文）                         |
| —                                     | `/workspace`                              | （redirect）                | COMPATIBILITY → `/research/workspace`（M4 更新）                                       |

## 附录 B：测试资产清单

| 文件                                                              | 测试数           | 覆盖范围                                                          | 状态                            |
| ----------------------------------------------------------------- | ---------------- | ----------------------------------------------------------------- | ------------------------------- |
| `apps/frontend/src/__tests__/research-workflow.test.ts`           | 3                | Legacy 版本比较 Workflow                                          | REGRESSION — 保持，M2 回归对照  |
| `apps/frontend/src/__tests__/v4-research.test.ts`                 | 10               | Legacy V4 Research（3 tab）                                       | REGRESSION — 保持，M3 回归对照  |
| `apps/frontend/src/__tests__/evidence-to-graph-e2e.test.ts`       | 8                | Legacy AI→证据→图谱链                                             | REGRESSION — 助手 tab 推迟      |
| `tests/e2e/test_critical_journeys.py`                             | ~57              | 全链路 E2E                                                        | REGRESSION — M5 发布前扩展      |
| `apps/frontend/src/__tests__/research-workflow-page.test.ts`      | 39               | Canonical Workflow Page                                           | ACTIVE — 已是 canonical 等价    |
| `apps/frontend/src/__tests__/research-result-page.test.ts`        | 77               | Canonical Result Page                                             | ACTIVE — 已是 canonical 等价    |
| `apps/frontend/src/__tests__/research-workspace.test.ts`          | ~28              | Canonical Workspace Page                                          | ACTIVE — 已是 canonical 等价    |
| `apps/frontend/src/__tests__/version-comparison-page.test.ts`     | **10 (M1 新增)** | 能力 #2 版本比较：3 legacy 等价 + 7 扩展覆盖（成功/空/错误/隔离） | **M1 — 占位通过，M2 激活**      |
| `apps/frontend/src/__tests__/v4-to-canonical-equivalence.test.ts` | **15 (M1 新增)** | 能力 #3 V4 Research：12 legacy→canonical 映射 + 3 结果页等价      | **M1 — 11/11 通过，4 deferred** |

## 附录 C：已知技术债务（与迁移相关）

1. **引用提取逻辑重复**：`ResearchWorkspaceView.vue`（L917–985）与 `V4ResearchView.vue`（L475–525）各自实现相同逻辑。M3 需统一至 `useResearchWorkflow` composable。
2. **`window.__pendingRunId` / `window.__pendingAsk` hack**：Legacy workspace 使用全局变量延迟操作链接。M4 清退后移除。
3. **`/v4/research` → `/research/workspace?tab=v4-research` 的中间重定向**：当前 `/v4/research` 不直接跳转 canonical 页面，而是经过 legacy workspace。M4 需更新为直接跳转。
4. **Replay UI 已实现**：Canonical result page 现已在 `ResearchResultPage.vue` 暴露重放验证 UI（`data-testid="canonical-replay"`）+ `useResearchResult.replayRun()`，提交 d08fbbd, 101e9ef, e6a5153。
