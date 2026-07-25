# Page Architecture Cleanup Report — Phase 3

> **Generated**: 2026-07-25
> **代码证据基线**: `066502c`（运行命令实际执行的代码提交）
> **文档状态基线**: `74cee05`（本报告当前提交）
> **Phase 2 工程治理冻结基线**: `23d1cef`
> **Scope**: `apps/frontend/src/` — router, pages, views, layouts, components
> **Status**: **BLOCK_RELEASE** — R3/R5 裁决为 APPROVED_MIGRATION_REQUIRED；R6 PENDING（当前 HEAD 未复验，仅有历史证据）
> **重新验收要求**: 任何代码或测试变更后，必须在该新 HEAD 重新执行全部 R6 命令。

---

## Phase 3 行为等价裁决表

> **裁决日期**: 2026-07-25
> **裁决人（填写）**: Phase 3 结构收口与行为冻结修复负责人（Claude）

### 能力 #1–#3 统一裁决记录

| 能力编号 | 裁决状态 | 批准人 | 批准时间 | 批准依据/记录 | 后续动作 |
|----------|----------|--------|----------|---------------|----------|
| 1 — 全局 Workspace | **APPROVED_MIGRATION_REQUIRED** | 产品负责人 | 2026-07-25 | 会话裁决记录 | 迁移至 canonical :projectId 作用域后移除；保持 BLOCK_RELEASE 直至迁移验收通过 |
| 2 — 版本研究 Workflow | **APPROVED_MIGRATION_REQUIRED** | 产品负责人 | 2026-07-25 | 会话裁决记录 | 迁移至 canonical ResearchWorkflowPage 后移除；保持 BLOCK_RELEASE 直至迁移验收通过 |
| 3 — V4 研究 | **APPROVED_MIGRATION_REQUIRED** | 产品负责人 | 2026-07-25 | 会话裁决记录 | 迁移实验功能至 canonical 后移除 `/v4/research-internal`；保持 BLOCK_RELEASE 直至迁移验收通过 |

**裁决值规范**：
- `PENDING_PRODUCT_APPROVAL` — 未获得真实产品负责人确认（默认状态）
- `APPROVED_INDEPENDENT_BUSINESS` — 产品负责人批准为独立业务；R3/R5 在该能力上闭合
- `APPROVED_MIGRATION_REQUIRED` — 产品负责人批准迁移；保持 BLOCK_RELEASE 直至迁移另行验收

> ⚠️ 不得由 Claude、修复工程师或提交作者填写"已批准"。以上字段仅在获得真实产品负责人签署后才可更新。

### 能力 #4–#6（已闭合）

| # | 能力 | 旧入口 | 旧可执行行为 | canonical 等价入口 | 等价证明 | 裁决 |
|---|------|--------|-------------|---------------------|----------|------|
| 4 | ResearchHome → ProjectList | `/research/home` | 原首页路由入口 | `ProjectListPage`（`/research`）— 同一业务 | 可直接渲染 | ✅ **已收口** — renders `<ProjectListPage />`，无 router.replace |
| 5 | ResearchNew → ProjectList | `/research/new` | 原新建课题路由入口 | `ProjectListPage`（`/research`）— 同一业务 | CreateProjectDialog 等效 | ✅ **已收口** — renders `<ProjectListPage />`，无 router.replace |
| 6 | test_library_reader_jump | `/library/:id` → "全文阅读" → `/reader/:id` | 点击链路 | `/reader/:id`（Task 009） | Task 009 规范 | ✅ **已修复** — 更新为 `/reader/:id` |

**裁决说明**：

- **#1–3 已由产品负责人裁决为 APPROVED_MIGRATION_REQUIRED**：三项能力均需迁移至 canonical 实现后移除。BLOCK_RELEASE 保持，直至迁移另行验收。
- **#4–5 已收口**（Decision A）：ResearchHomeView、ResearchNewView 直接渲染 `<ProjectListPage />`。R3 在此二项上闭合。
- **#6 已修复**：更新期望 URL 为 `/reader/:id`（Task 009 规范），测试通过。
- 当前代码保持完整可执行行为（未降级为迁移提示），等待迁移实施。

**关于 Decision A（无 router.replace）**：ResearchHomeView 和 ResearchNewView 的 `router.replace` 已被移除，二文件现在通过 `import ProjectListPage` 并直接渲染其模板来保留旧 URL 并将所有业务逻辑委托给 canonical 实现。Decision A 在此二项上是闭合的。

---

## R6 验证命令（需在当前 HEAD 执行后方可判定）

以下命令需在目标 HEAD 逐一执行，结果不得臆造：

### 当前环境确认

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
```

### 前端命令（`apps/frontend`）

```bash
npm run typecheck
npm run test -- --run
npm run build
npx playwright test task011-navigation-consistency.spec.ts
npx playwright test task010-design-system.spec.ts
```

### 后端 E2E（repo root，`--browser chromium`）

```bash
uv run pytest tests/e2e/test_reader_e2e.py tests/e2e/test_critical_journeys.py -q --no-cov --browser chromium
```

### 历史运行记录（Historical evidence only — not current-environment release proof）

以下数据来自 `c9a4f5e` / `066502c` 的历史运行记录，保留为参考：

#### 后端 E2E 修复记录（`066502c` 引入，`c9a4f5e` / `74cee05` 均验证通过）

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
| R1 (Report truth) | ✅ — 报告使用稳定基线标识（代码证据基线 `066502c`，文档状态基线 `74cee05`）；历史运行记录已标注为 Historical evidence only |
| R3 (Single implementation) | **CONDITIONAL** — 能力 #1–#3 已由产品负责人裁决为 APPROVED_MIGRATION_REQUIRED（迁移后闭合）；#4–#5 已收口（Decision A） |
| R5 (Behavior preservation) | **CONDITIONAL** — 能力 #1–#3 迁移验收通过后闭合；#4–#5 已收口 |
| R6 (Real evidence) | **PENDING** — 需在当前 HEAD 执行全部 R6 验证命令；现有数据来自 `74cee05` 历史运行记录，不是当前 HEAD 的实时证据 |
| Release | **BLOCK_RELEASE** — 能力 #1–#3 迁移另行验收 + R6 当前 HEAD 未复验 + 未完成项待解决 |

**未完成项（当前 HEAD）**：

1. `/v4/research-internal` 内部入口仍对开发环境开放（Phase 3 未公开入口验收）
2. Knowledge 占位页（教育模式/可视化工作流等价实现）推迟，未完成
3. API 契约未收口（V4 内部路由兼容行为未声明为最终状态）
4. M5 发布验收命令尚未在当前 HEAD 运行

---

## 发布状态机

```
BLOCK_RELEASE
  ├─ 产品裁决未签署 → 等待产品负责人
  ├─ R6 未复验 / 非全绿 → 在当前 HEAD 重新运行全部 R6
  └─ 能力 #1–#3 迁移未验收 → 迁移验收通过后闭合

RELEASE_READY
  └─ 产品裁决已签署（APPROVED_INDEPENDENT_BUSINESS 或 APPROVED_MIGRATION_REQUIRED）
     + 迁移已验收（如适用）
     + R6 当前 HEAD 全绿
     + git status 干净
     + HEAD == origin/master
```

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
| `research-workspace` | `/research/workspace` | ACTIVE (legacy — APPROVED_MIGRATION_REQUIRED) |
| `v4-research` | `/v4/research-internal` | ACTIVE (legacy — APPROVED_MIGRATION_REQUIRED) |

## Appendix B: Layout Usage

| Layout | Routes |
|--------|--------|
| `DefaultLayout.vue` | All legacy views + ReaderPage + legacy workspace/V4 |
| `ResearchAppLayout.vue` | All canonical pages (research, library, knowledge, reports) |
