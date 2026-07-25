# Page Architecture Cleanup Report — Phase 3

> **Generated**: 2026-07-25
> **代码证据基线**: `066502c`（运行命令实际执行的代码提交）
> **文档状态基线**: `96d9447`（本报告当前提交）
> **Phase 2 工程治理冻结基线**: `23d1cef`
> **Scope**: `apps/frontend/src/` — router, pages, views, layouts, components
> **Status**: **BLOCK_RELEASE** — R3/R5: PENDING_PRODUCT_APPROVAL；R6: PENDING_CURRENT_RUNTIME_RECHECK
> **重新验收要求**: 任何代码或测试变更后，必须在该新 HEAD 重新执行全部 R6 命令。

---

## Phase 3 行为等价裁决表

> **裁决日期**: 2026-07-25
> **裁决人（填写）**: Phase 3 结构收口与行为冻结修复负责人（Claude）

### 能力 #1–#3 统一裁决记录

| 能力编号 | 裁决状态 | 批准人 | 批准时间 | 批准依据/记录 | 后续动作 |
|----------|----------|--------|----------|---------------|----------|
| 1 — 全局 Workspace | **PENDING_PRODUCT_APPROVAL** | — | — | — | 等待产品负责人裁决：独立业务 / 迁移后移除 |
| 2 — 版本研究 Workflow | **PENDING_PRODUCT_APPROVAL** | — | — | — | 等待产品负责人裁决：独立业务 / 迁移后移除 |
| 3 — V4 研究 | **PENDING_PRODUCT_APPROVAL** | — | — | — | 等待产品负责人裁决：独立业务 / 迁移后移除 |

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

- **#1–3 的裁决是 PENDING_PRODUCT_APPROVAL**：这些能力是否视为独立业务必须由产品负责人审批。在此之前 R3 和 R5 不可标记为已完成，`BLOCK_RELEASE` 不可解除。
- **#4–5 已收口**（Decision A）：ResearchHomeView、ResearchNewView 直接渲染 `<ProjectListPage />`。R3 在此二项上闭合。
- **#6 已修复**：更新期望 URL 为 `/reader/:id`（Task 009 规范），测试通过。
- 当前代码保持完整可执行行为（未降级为迁移提示），等待产品裁决后再决定最终架构。

**关于 Decision A（无 router.replace）**：ResearchHomeView 和 ResearchNewView 的 `router.replace` 已被移除，二文件现在通过 `import ProjectListPage` 并直接渲染其模板来保留旧 URL 并将所有业务逻辑委托给 canonical 实现。Decision A 在此二项上是闭合的。

---

## R6 运行证据 — PENDING_CURRENT_RUNTIME_RECHECK

**当前状态**: `http://127.0.0.1:8000/health` → 后端不可达（连接拒绝）。
**阻塞原因**: 当前验收环境后端不可达；必须恢复后端后才能重新运行 R6 验收命令。

### 历史运行记录（Historical evidence only — not current-environment release proof）

以下数据来自 `c9a4f5e` / `066502c` 的运行记录，保留为历史证据；**不可替代当前环境的运行证明**。

#### 环境确认（历史记录）

| Check | HEAD | Result |
|-------|------|--------|
| `curl /health` | `c9a4f5e` | ✅ HTTP 200 — `{"status":"healthy"}` |
| `curl /ready` | `c9a4f5e` | ✅ HTTP 200 — 全部服务健康 |

#### 前端命令（历史记录）

| Command | HEAD | Date | Result |
|---------|------|------|--------|
| `npm run typecheck` | `c9a4f5e` | 2026-07-25 | ✅ PASS |
| `npm run test -- --run` | `c9a4f5e` | 2026-07-25 | **574/574 PASS** |
| `npm run build` | `c9a4f5e` | 2026-07-25 | ✅ PASS |
| `npx playwright test task011-navigation-consistency.spec.ts` | `c9a4f5e` | 2026-07-25 | **116/116 PASS** (Mobile/Tablet/Desktop/Wide) |
| `npx playwright test task010-design-system.spec.ts` | `c9a4f5e` | 2026-07-25 | **88/88 PASS** (Mobile/Tablet/Desktop/Wide) |

#### 后端 E2E（历史记录）

| Command | HEAD | Date | Result |
|---------|------|------|--------|
| `uv run pytest tests/e2e/test_reader_e2e.py tests/e2e/test_critical_journeys.py -q --no-cov` | `c9a4f5e` | 2026-07-25 | **93/93 PASS** (10:37 elapsed) |

#### 后端 E2E 修复记录（`066502c` 引入，`c9a4f5e` 验证通过）

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

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
```

在当时的当前干净 HEAD 依次执行：

```bash
cd apps/frontend
npm run type-check
npm run test -- --run
npm run build
npx playwright test --config playwright.config.ts src/e2e/task011-navigation-consistency.spec.ts
npx playwright test --config playwright.config.ts src/e2e/task010-design-system.spec.ts

cd ../..
UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest \
  tests/e2e/test_reader_e2e.py \
  tests/e2e/test_critical_journeys.py \
  --browser chromium -q --no-cov
```

只有所有命令在同一干净 HEAD 产生最终全绿统计后，才允许将 R6 写为 PASS，并记录实际执行 HEAD 与时间戳。

---

## 结论

| Gate | Status |
|------|--------|
| R1 (Report truth) | ✅ — 报告使用稳定基线标识（代码证据基线 `066502c`，文档状态基线 `96d9447`）；`c9a4f5e` 历史运行记录已标注为 Historical evidence only |
| R3 (Single implementation) | **PENDING_PRODUCT_APPROVAL** — 能力 #1–#3 必须由产品负责人签署裁决；#4–#5 已收口（Decision A） |
| R5 (Behavior preservation) | **PENDING_PRODUCT_APPROVAL** — 直至能力 #1–#3 获批准；#4–#5 已收口 |
| R6 (Real evidence) | **PENDING_CURRENT_RUNTIME_RECHECK** — 当前验收环境后端不可达（127.0.0.1:8000）；后端恢复后必须重新执行全部 R6 命令并获取全绿统计 |
| Release | **BLOCK_RELEASE** — 产品裁决未签署 + R6 未在当前环境复验 |

---

## 发布状态机

```
BLOCK_RELEASE
  ├─ 产品裁决未签署 → 等待产品负责人
  └─ R6 未复验 / 非全绿 → 恢复环境并重跑

RELEASE_READY
  └─ 产品裁决已签署
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
| `research-workspace` | `/research/workspace` | ACTIVE (legacy global panel — PENDING product approval) |
| `v4-research` | `/v4/research-internal` | ACTIVE (legacy — PENDING product approval) |

## Appendix B: Layout Usage

| Layout | Routes |
|--------|--------|
| `DefaultLayout.vue` | All legacy views + ReaderPage + legacy workspace/V4 |
| `ResearchAppLayout.vue` | All canonical pages (research, library, knowledge, reports) |
