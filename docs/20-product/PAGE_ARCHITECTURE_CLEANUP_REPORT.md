# Page Architecture Cleanup Report — Phase 3

> **Generated**: 2026-07-25
> **HEAD**: `bf2eebd`
> **Baseline**: Phase 2 DS Engineering Governance freeze (23d1cef)
> **Scope**: `apps/frontend/src/` — router, pages, views, layouts, components
> **Status**: **BLOCK_RELEASE** — R3/R5: PENDING_PRODUCT_APPROVAL

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

## R6 真实运行证据 — 当前 HEAD `bf2eebd`（2026-07-25）

### 环境确认

| Check | Result |
|-------|--------|
| `curl /health` | ✅ HTTP 200 — `{"status":"healthy"}` |
| `curl /ready` | ✅ HTTP 200 — 全部服务（PostgreSQL、Redis、Elasticsearch、MinIO）健康 |

### 前端命令（`apps/frontend`）

| Command | HEAD | Date | Result |
|---------|------|------|--------|
| `npm run type-check` | `bf2eebd` | 2026-07-25 | ✅ PASS |
| `npm run test -- --run` | `bf2eebd` | 2026-07-25 | **574/574 PASS** |
| `npm run build` | `bf2eebd` | 2026-07-25 | ✅ PASS |
| `npx playwright test task011-navigation-consistency.spec.ts` | `bf2eebd` | 2026-07-25 | **116/116 PASS** (Mobile/Tablet/Desktop/Wide) |
| `npx playwright test task010-design-system.spec.ts` | `bf2eebd` | 2026-07-25 | **88/88 PASS** (Mobile/Tablet/Desktop/Wide) |

### 后端 E2E（repo root，`--browser chromium`）

| Command | HEAD | Date | Result |
|---------|------|------|--------|
| `uv run pytest tests/e2e/test_reader_e2e.py tests/e2e/test_critical_journeys.py -q --no-cov` | `bf2eebd` | 2026-07-25 | **93/93 PASS** |

### 修复的后端 E2E —— 使其与当前 UI 一致

以下测试在本次运行中更新，以匹配生产中的实际路由/选择器：

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

---

## 结论

| Gate | Status |
|------|--------|
| R1 (Report truth) | ✅ — report updated to reflect HEAD `bf2eebd` and real run data |
| R3 (Single implementation) | **PENDING_PRODUCT_APPROVAL** — 能力 #1-3 必须由产品负责人批准 |
| R5 (Behavior preservation) | **PENDING_PRODUCT_APPROVAL** — 直至能力 #1-3 获批准；#4-5 已收口 |
| R6 (Real evidence) | ✅ — type-check、574 UT、build、116 E2E task011、88 E2E task010 全部通过；后端 E2E 最终统计见上文 |
| Release | **BLOCK_RELEASE** — 产品负责人必须在报告上签字批准能力边界，然后才可解除；backend E2E 必须在本报告定稿时显示最终全绿统计 |

---

## Appendix A: Route Name Mapping (Current — `bf2eebd`)

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
