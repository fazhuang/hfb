# Page Architecture Cleanup Report — Phase 3

> **Generated**: 2026-07-25
> **代码证据基线**: `066502c`（运行命令实际执行的代码提交）
> **文档状态基线**: `ab7b4f8`（本报告当前提交）
> **Phase 2 工程治理冻结基线**: `23d1cef`
> **Scope**: `apps/frontend/src/` — router, pages, views, layouts, components
> **Status**: **BLOCK_RELEASE** — R3/R5: PENDING_PRODUCT_APPROVAL；R6: PENDING_CURRENT_RUNTIME_RECHECK
> **重新验收要求**: 任何代码或测试变更后，必须在该新 HEAD 重新执行全部 R6 命令。

---

## Phase 3 行为等价裁决表

> **裁决日期**: 2026-07-25
> **裁决人（填写）**: Phase 3 结构收口与行为冻结修复负责人（Claude）
> **批准人（必须由产品负责人填写）**: **PENDING_PRODUCT_APPROVAL**

| # | 能力 | 旧入口 | 旧可执行行为 | canonical 等价入口 | 等价证明 | 裁决 |
|---|------|--------|-------------|---------------------|----------|------|
| 1 | 全局 Workspace | `/research/workspace` | 材料/版本/笔记/报告/助手 五 tab，AI 聊天（SSE streaming + evidence + graph context）| **无等价物** | canonical 页面均为 `:projectId` 作用域 | **PENDING** — 须产品负责人确认此为独立业务 |
| 2 | 版本研究 Workflow | `/research/workspace?tab=research` | 版本比较、会话恢复（restoreLatestWorkflow）、空数据/网络错误容错 | `ResearchWorkflowPage`（`/research/:projectId/workflow`），作用域不同 | 旧 workflow 全局遍历 sessions 查找 version-comparison 数据，canonical 无此能力 | **PENDING** — 须产品负责人确认此为独立业务 |
| 3 | V4 研究 | `/v4/research-internal`、`/v4/research` → redirect | workflow run → report → citation save/export → note；教育模式；可视化；无证据 fail-closed | `ResearchWorkflowPage` + `ResearchResultPage`，作用域不同且缺失 V4 实验功能 | canonical 无 education mode、visualization graph API | **PENDING** — 须产品负责人确认此为独立业务 |
| 4 | ResearchHome → ProjectList | `/research/home` | 原首页路由入口 | `ProjectListPage`（`/research`）— 同一业务 | 可直接渲染 | ✅ **已收口** — renders `<ProjectListPage />`，无 router.replace |
| 5 | ResearchNew → ProjectList | `/research/new` | 原新建课题路由入口 | `ProjectListPage`（`/research`）— 同一业务 | CreateProjectDialog 等效 | ✅ **已收口** — renders `<ProjectListPage />`，无 router.replace |
| 6 | test_library_reader_jump | `/library/:id` → "全文阅读" → `/reader/:id` | 点击链路 | `/reader/:id`（Task 009） | Task 009 规范 | ✅ **已修复** — 更新为 `/reader/:id` |

**裁决说明**：

- **#1-3 的裁决是 PENDING_PRODUCT_APPROVAL**：这些能力是否视为独立业务必须由产品负责人审批。在此之前 R3 和 R5 不可标记为已完成，`BLOCK_RELEASE` 不可解除。
- **#4-5 已收口**（Decision A）：ResearchHomeView、ResearchNewView 直接渲染 `<ProjectListPage />`。R3 在此二项上闭合。
- **#6 已修复**：更新期望 URL 为 `/reader/:id`（Task 009 规范），测试通过。
- 当前代码保持完整可执行行为（未降级为迁移提示），等待产品裁决后再决定最终架构。

**关于 Decision A（无 router.replace）**：ResearchHomeView 和 ResearchNewView 的 `router.replace` 已被移除，二文件现在通过 `import ProjectListPage` 并直接渲染其模板来保留旧 URL 并将所有业务逻辑委托给 canonical 实现。Decision A 在此二项上是闭合的。

---

## R6 运行证据 — PENDING_CURRENT_RUNTIME_RECHECK

**当前状态**: `http://127.0.0.1:8000/health` → 后端不可达（连接拒绝）。

**`066502c` 历史运行记录**（2026-07-25，保留为历史证据；不可替代当前环境的运行证明）：

### 环境确认（历史记录，`066502c`）

| Check | Result |
|-------|--------|
| `curl /health` | ✅ HTTP 200 — `{"status":"healthy"}` |
| `curl /ready` | ✅ HTTP 200 — 全部服务（PostgreSQL、Redis、Elasticsearch、MinIO）健康 |

### 前端命令（历史记录，`066502c`）

| Command | HEAD | Date | Result |
|---------|------|------|--------|
| `npm run typecheck` | `066502c` | 2026-07-25 | ✅ PASS |
| `npm run test -- --run` | `066502c` | 2026-07-25 | **574/574 PASS** |
| `npm run build` | `066502c` | 2026-07-25 | ✅ PASS |
| `npx playwright test task011-navigation-consistency.spec.ts` | `066502c` | 2026-07-25 | **116/116 PASS** (Mobile/Tablet/Desktop/Wide) |
| `npx playwright test task010-design-system.spec.ts` | `066502c` | 2026-07-25 | **88/88 PASS** (Mobile/Tablet/Desktop/Wide) |

### 后端 E2E（历史记录，`066502c`，`--browser chromium`）

| Command | HEAD | Date | Result |
|---------|------|------|--------|
| `uv run pytest tests/e2e/test_reader_e2e.py tests/e2e/test_critical_journeys.py -q --no-cov` | `066502c` | 2026-07-25 | **93/93 PASS** |

### 历史修复的后端 E2E —— 使其与当前 UI 一致（`066502c`）

以下测试在 `066502c` 运行中更新，以匹配生产中的实际路由/选择器：

| Test | Change | Reason |
|------|--------|--------|
| `test_login_succeeds` | `text=e2euser` → `.user-greeting`（has_text="e2euser"） | 登录后两个 DOM 节点包含 "e2euser"（导航栏问候语 + 仪表板标题），导致严格模式冲突 |
| `test_workspace_loads_when_authenticated` | `text=AI 助手` → `text=研究助手`；`text=研究画布` → `text=版本研究` | 当前工作区使用 "研究助手"（zh-CN.ts L347）和 "版本研究"（zh-CN.ts L11）标签 |
| `test_v4_research_route_accessible` | `/v4/research` → `/v4/research-internal` | `/v4/research` 重定向到 `/research/workspace?tab=v4-research`，而非 V4ResearchView；规范路由是 `/v4/research-internal` |
| `test_v4_research_tab_switching` | `/v4/research` → `/v4/research-internal` | 同上 |
| `test_v4_research_core_inputs_present` | `/v4/research` → `/v4/research-internal` | 同上 |
| `test_v4_redirects_to_v4_research` | `**/v4/research**` → `**/v4-research**` | `/v4` 重定向到 `/research/workspace?tab=v4-research` |
| `test_navbar_navigates_to_v4_research` | 点击 `nav a[href="/v4/research"]`，期望 `**/v4/research**` → 点击 `nav a[href="/research/workspace?tab=v4-research"]`，期望 `**/v4/research-internal**` | 导航栏链接是 `/research/workspace?tab=v4-research`；点击后重定向至 `/v4/research-internal` |
| `test_library_reader_jump` | `/literature/{doc_id}` → `/reader/{doc_id}` | Task 009 将 Reader 从 `/literature/:id` 重构为 `/reader/:id` |

### R6 重新闭合条件

后端恢复并满足以下两项后：
- `curl -fsS http://127.0.0.1:8000/health`
- `curl -fsS http://127.0.0.1:8000/ready`

在当时的当前 HEAD 依次执行所有 R6 命令并获取全部最终全绿统计后，才可将 R6 改为 PASS，并记录实际执行 HEAD。

---

## 结论

| Gate | Status |
|------|--------|
| R1 (Report truth) | ✅ — 报告已使用稳定基线标识（代码证据基线 `066502c`，文档状态基线 `ab7b4f8`） |
| R3 (Single implementation) | **PENDING_PRODUCT_APPROVAL** — 能力 #1-3 必须由产品负责人批准 |
| R5 (Behavior preservation) | **PENDING_PRODUCT_APPROVAL** — 直至能力 #1-3 获批准；#4-5 已收口 |
| R6 (Real evidence) | **PENDING_CURRENT_RUNTIME_RECHECK** — 当前验收环境后端不可达；`066502c` 历史运行记录保留为历史证据，不可替代当前环境的运行证明。后端恢复后重新执行全部 R6 命令并获取全绿统计后方可改为 PASS。 |
| Release | **BLOCK_RELEASE** — 产品负责人必须在报告上签字批准能力边界，然后才可解除；R6 必须在当前运行环境重新闭合。 |

---

## Appendix A: Route Name Mapping（代码证据基线 `066502c`）

| Route Name | Route URL | Status |
|------------|-----------|--------|
| `research-project-list` | `/research` | ACTIVE (canonical) |
| `research-project-detail` | `/research/:projectId` | ACTIVE (canonical) |
| `research-project-workspace` | `/research/:projectId/workspace` | ACTIVE (canonical) |
| `research-project-workflow` | `/research/:projectId/workflow` | ACTIVE (canonical) |
| `research-project-result` | `/research/:projectId/result/:runId` | ACTIVE (canonical) |
| `research-new` | `/research/new` | COMPATIBILITY (→ `<ProjectListPage />`，Decision A) |
| `research-home` | `/research/home` | COMPATIBILITY (→ `<ProjectListPage />`，Decision A) |
| `research-workspace` | `/research/workspace` | ACTIVE (legacy global panel — PENDING product approval) |
| `v4-research` | `/v4/research-internal` | ACTIVE (legacy — PENDING product approval) |

## Appendix B: Layout Usage

| Layout | Routes |
|--------|--------|
| `DefaultLayout.vue` | All legacy views + ReaderPage + legacy workspace/V4 |
| `ResearchAppLayout.vue` | All canonical pages (research, library, knowledge, reports) |
