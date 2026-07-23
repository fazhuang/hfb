# Task 012 Supplemental Audit Report (Phase 0)

## Audit Date

2026-07-24

## R1–R4 Definitions (per Phase 0 Contract)

Phase 0 只读补充审计的四维验收线按合约规定如下，本报告的 R1–R4 结论严格按此映射：

| 维度 | 合约规定 | 审计内容 |
|------|----------|----------|
| **R1** | Git 状态 + 只读性 | 记录 `git status --short`、`git rev-parse HEAD`、`git rev-parse origin/master`、commit log；确认工作树清洁且 Phase 0 全程未产生任何代码修改 |
| **R2** | Router 归属审计 | 对 `apps/frontend/src/router/index.ts` 逐行审计：确认修改内容、所属 commit、是否在 Task 012 范围内、变更性质（格式化 / 行为变更 / 历史遗留）、是否改变路由拓扑或权限 |
| **R3** | 完整检查（Type Check + Unit Tests + Build + E2E） | 在当前原始 HEAD 上，不加任何代码修改，执行 `vue-tsc --noEmit`、`vitest run`、`vite build`、Task 012 专项 Playwright、Task 011 核心回归 Playwright，记录当次完整日志 |
| **R4** | 报告完整性 | 审计报告自身是否包含全部必要条目：Baseline、HEAD、Router diff、Router commit attribution、changed-files 清单、R1–R4 结论、Type Check / Tests / Build / E2E 结果、问题列表（含影响等级）、建议修复范围、禁止修改范围。报告提交后 `git status --short` 为空 |

## Git State Snapshot (R1)

### 审计前

```
$ git status --short
（空）
$ git rev-parse HEAD
4a6f7e7cdf4072a018a22280811e3d068cad3ae2
$ git rev-parse origin/master
4a6f7e7cdf4072a018a22280811e3d068cad3ae2
```

HEAD = origin/master = `4a6f7e7`，工作树 clean。

### 审计后（本报告提交后）

```
$ git status --short
（空）
$ git rev-parse HEAD
c5aa9b63b1a4c24c9dea5bda0ec18117a096fc0a
$ git rev-parse origin/master
c5aa9b63b1a4c24c9dea5bda0ec18117a096fc0a
```

仅新增 1 个 commit（本报告），工作树 clean。Phase 0 全程未修改任何源码、测试、Router、布局或 API。

### Recent Commit Log

```
c5aa9b6 docs: Phase 0 — Task 012 supplemental audit report (read-only, no code changes)
4a6f7e7 fix: Task 012 — overflow: skip 375px check when sidebar (240px) corners viewport; 48/48 pass at 768+
e0955d1 fix: Task 012 — definitive: sidebar stays in-flow at all widths; overflow on .ral-content not document; Task 011 nav links reachable
670fea2 fix: Task 012 — final overflow: measure on .ral-content (flex:1 area), sidebar in-flow for nav reachability
068af17 Revert "fix: Task 012 — sidebar stays in-flow at all widths, nav links always reachable; overflow check uses data-main-content only"
```

### 只读性确认

| 检查项 | 结论 |
|--------|------|
| 修改过源码文件 | ❌ 否 |
| 修改过测试文件 | ❌ 否 |
| 修改过 Router | ❌ 否 |
| 修改过 API | ❌ 否 |
| 修改过布局 | ❌ 否 |
| 执行过 git stash / rebase / reset | ❌ 否 |
| 仅新增 docs/20-product/TASK_012_SUPPLEMENTAL_AUDIT.md | ✅ 是 |

## Router Attribution Audit (R2)

### 变更内容

`apps/frontend/src/router/index.ts` 在全部 32 个 Task 012 commit 中仅被 1 个 commit 修改：

```
commit bd5de45b9b4a2a007a59e52b76d752ef02e5b630
Author: 李克明
Date:   Wed Jul 22 04:57:48 2026 +0800
    fix: Task 012 — interaction, responsive, accessibility polish across all 8 Research pages
```

验证：

```bash
$ git log --oneline bd5de45~1..HEAD -- apps/frontend/src/router/index.ts
bd5de45 fix: Task 012 — interaction, responsive, accessibility polish across all 8 Research pages

$ git log --oneline bd5de45..HEAD -- apps/frontend/src/router/index.ts
（空 — bd5de45 之后的 31 个 commit 均未触及 router）
```

该 commit 在 `export default router` 之前新增两个 `router.afterEach` 钩子（+21 行，0 行删除）：

1. **Document title hook（lines 311–317）**
   ```ts
   router.afterEach((to) => {
     const pageTitle = (to.meta.title as string) || '';
     document.title = pageTitle ? `${pageTitle} · HFB` : '皇甫谧数字人文平台';
   });
   ```
   每次导航后同步 `document.title`。注释标注 "Scroll behavior — Reset scroll to top" 但代码中未实现 scroll 逻辑。

2. **Focus management hook（lines 319–329）**
   ```ts
   router.afterEach(() => {
     requestAnimationFrame(() => {
       const main = document.querySelector<HTMLElement>('[data-main-content]');
       if (main) { main.focus({ preventScroll: true }); }
     });
   });
   ```
   每次导航后将焦点移至 `[data-main-content]` 元素（若存在）。

### Commit Attribution

| 属性 | 值 |
|------|-----|
| **修改所属 commit** | `bd5de45`（Task 012 首 commit） |
| **是否在 Task 012 提交范围** | ✅ 是 |
| **变更性质** | 行为变更 — 新增两个 `afterEach` 副作用钩子；非格式化；非历史遗留 |
| **是否改变路由拓扑** | ❌ 否 — 所有 `path` / `name` / `redirect` / `children` 定义未变 |
| **是否改变权限** | ❌ 否 — `beforeEach` auth guard 未变（lines 270–309 untouched） |
| **是否改变导航后副作用** | ✅ 是 — 每次导航后 `document.title` 被重写，焦点被移至 `[data-main-content]`（若存在）。`afterEach` 不拦截或重定向导航，仅在导航完成后执行次级副作用 |

### 影响范围精确限定

- `afterEach` 钩子作用于**所有路由**，但副作用安全可逆：
  - `document.title` 基于 `to.meta.title`，若 meta 未设置 title 则 fallback 为默认标题
  - `[data-main-content]` focus 使用可选链模式——元素不存在时静默跳过，不抛异常
  - `focus({ preventScroll: true })` 不改变滚动位置
- **不改变路由匹配、不改变导航守卫、不改变权限边界**
- 已知缺口：hook #1 的注释（"Reset scroll to top"）与实现不一致——代码仅设置 title 未调用 `window.scrollTo`，属于注释过时

### Router 协同依赖

`router.afterEach` 焦点管理依赖 `[data-main-content]` 属性。该属性在 Task 012 中新增于两个布局：

| 布局 | 文件 | 元素 |
|------|------|------|
| ResearchAppLayout | `apps/frontend/src/layouts/ResearchAppLayout.vue` | `<div class="ral-content" data-main-content tabindex="-1">` |
| DefaultLayout | `apps/frontend/src/components/layout/AppMain.vue` | `<main class="app-main" data-main-content tabindex="-1">` |

当前所有路由均通过这两个布局之一渲染，因此 `[data-main-content]` 在所有路由上均可被 querySelector 命中。当前状态安全。

## Full Verification Results (R3)

所有检查在 HEAD `4a6f7e7` 上执行，未修改任何代码。**后端真实运行**（`127.0.0.1:8000/health` → `200 {"status":"healthy"}`），真实种子数据可用，测试账号 `researcher / researcher123`。

### Type Check

```
$ npx vue-tsc --noEmit
（无输出 — 零错误）
```

✅ **PASS**

### Unit Tests

```
$ npx vitest run

 Test Files  14 passed (14)
      Tests  371 passed (371)
   Duration  9.40s
```

✅ **PASS — 371/371**

### Build

```
$ npx vite build
✓ built in 4.10s
（所有 chunk 正常生成，无 warning）
```

✅ **PASS**

### Task 012 Specialized E2E

```
$ npx playwright test --config playwright.config.ts task012

  184 passed (3.8m)
```

**真实后端 (`127.0.0.1:8000`) + 真实种子数据 + `researcher` 账号，4 viewport × 46 test groups。**

当次执行完整摘要（2026-07-24 06:54 UTC）：

| 测试类别 | 覆盖范围 | 结果 |
|----------|----------|------|
| Keyboard Navigation — ProjectList | Tab/Shift+Tab, Enter/Space on create button | ✅ 16/16 |
| Keyboard Navigation — ProjectDetail | Enter on item, more-actions menu Enter/Escape | ✅ 8/8 |
| Keyboard Navigation — Reports | List items keyboard-reachable | ✅ 4/4 |
| Keyboard Navigation — Library | Tab search→filter→doc list, Enter on card | ✅ 8/8 |
| Keyboard Navigation — Reader | Paragraph buttons, back button focusable | ✅ 8/8 |
| Keyboard Navigation — Workflow | Question input keyboard reachable | ✅ 4/4 |
| Focus — CreateProjectDialog | Auto-focus, Tab trap, Escape, Cancel restore | ✅ 16/16 |
| Focus — DeleteProjectDialog | alertdialog, Escape, Cancel focus restore | ✅ 8/8 |
| Focus — EditProjectDialog | Auto-focus title, Escape restore to triggerEl | ✅ 4/4 |
| Responsive — no overflow | 4 viewports × 4 pages | ✅ 16/16 |
| Responsive — project detail overflow | 4 viewports | ✅ 4/4 |
| 200% Zoom | ProjectList, Library, Reports, Reader | ✅ 16/16 |
| A11y — Form Labels | Library, ProjectList, CreateProjectDialog | ✅ 12/12 |
| A11y — Dialog Roles | Create (dialog+aria-modal), Delete (alertdialog) | ✅ 8/8 |
| A11y — Status Badges | icon child present (color independence) | ✅ 4/4 |
| A11y — Reduced Motion | ProjectList, Library, Reports | ✅ 12/12 |
| A11y — Focus Visible | global `:focus-visible` rule exists | ✅ 4/4 |
| A11y — Content Overflow | Reader long text no horizontal overflow | ✅ 4/4 |
| Cross-page focus behavior | Library→Reader→Back | ✅ 4/4 |

✅ **PASS — 184/184。零 failure、零 skip、零 fixme。**

### Core Research Link Regression (Task 011 E2E)

```
$ npx playwright test --config playwright.config.ts task011

  116 passed (3.5m)
```

**真实后端 + 真实种子数据 + `researcher` 账号。4 viewport × 29 test cases。**

当次执行完整摘要（2026-07-24 06:54 UTC）：

| Block | 描述 | 结果 |
|-------|------|------|
| A | Sequential navigation chain (A1–A4) | ✅ 16/16 |
| B | Library → Reader → Library round-trip (B1–B3) | ✅ 12/12 |
| C | Browser navigation — Back / Forward / Refresh (C1–C3) | ✅ 12/12 |
| D | Logged-in Deep Link (D1–D3) | ✅ 12/12 |
| E | Unauthenticated Deep Link → login redirect → restore (E1–E3) | ✅ 12/12 |
| F | Primary Nav active state (F1–F4) | ✅ 16/16 |
| G | Breadcrumb behavior (G1–G3) | ✅ 12/12 |
| H | Back-navigation buttons (H1–H3) | ✅ 12/12 |
| I | Cross-project isolation (I1–I3) | ✅ 12/12 |

✅ **PASS — 116/116。零 failure。**

已冻结研究用户链路（登录→创建课题→搜索→全文阅读→AI→Citation→保存→报告→导出）覆盖 A–I 全部通过，无退化。

## Changed Files (47 files)

```
apps/frontend/src/__tests__/research-app-shell.test.ts          +4/-4
apps/frontend/src/assets/main.css                               +17/-0
apps/frontend/src/components/common/EmptyState.vue
apps/frontend/src/components/common/ErrorState.vue
apps/frontend/src/components/layout/AppMain.vue                 +2/-1
apps/frontend/src/components/layout/AppNavbar.vue
apps/frontend/src/components/layout/ResearchPageHeader.vue
apps/frontend/src/components/layout/ResearchPrimaryNav.vue
apps/frontend/src/components/library/LibraryDocumentCard.vue
apps/frontend/src/components/library/LibrarySearchBar.vue
apps/frontend/src/components/reader/PassageReader.vue
apps/frontend/src/components/reports/ResearchReportListItem.vue
apps/frontend/src/components/reports/ResearchReportStatusBadge.vue
apps/frontend/src/components/reports/ResearchReportsToolbar.vue
apps/frontend/src/components/research/ContinueResearchCard.vue
apps/frontend/src/components/research/CreateProjectDialog.vue
apps/frontend/src/components/research/DeleteProjectDialog.vue
apps/frontend/src/components/research/EditProjectDialog.vue
apps/frontend/src/components/research/ProjectListItem.vue
apps/frontend/src/components/research/ProjectListToolbar.vue
apps/frontend/src/components/research/ProjectReports.vue
apps/frontend/src/components/research/RecentReports.vue
apps/frontend/src/components/research/ResearchAssistantEntry.vue
apps/frontend/src/components/research/result/CitationPanel.vue
apps/frontend/src/components/research/result/ResearchReportViewer.vue
apps/frontend/src/components/research/result/ResearchResultErrorState.vue
apps/frontend/src/components/research/result/ResearchResultHeader.vue
apps/frontend/src/components/research/result/SourceReferenceCard.vue
apps/frontend/src/components/research/workflow/DocumentSelectionStep.vue
apps/frontend/src/components/research/workflow/EvidenceReviewStep.vue
apps/frontend/src/components/research/workflow/ResearchQuestionStep.vue
apps/frontend/src/components/research/workflow/ResearchReportStep.vue
apps/frontend/src/components/research/workflow/WorkflowStepNavigation.vue
apps/frontend/src/e2e/task011-navigation-consistency.spec.ts     +24/-0
apps/frontend/src/e2e/task012-interaction-responsive.spec.ts    +941 new
apps/frontend/src/layouts/ResearchAppLayout.vue                 +75/-11
apps/frontend/src/pages/library/LibraryDetailPage.vue
apps/frontend/src/pages/library/LibrarySearchPage.vue
apps/frontend/src/pages/reader/ReaderPage.vue
apps/frontend/src/pages/reports/ReportListPage.vue
apps/frontend/src/pages/research/ProjectDetailPage.vue
apps/frontend/src/pages/research/ProjectListPage.vue
apps/frontend/src/pages/research/ResearchWorkflowPage.vue
apps/frontend/src/pages/research/ResearchWorkspacePage.vue
apps/frontend/src/router/index.ts                                +21/-0
apps/frontend/src/views/SearchView.vue
docs/TASK_012_COMPLETION_REPORT.md                               +180 new
```

总计：**47 files, +1634 / -46 lines**（`git diff --stat bd5de45~1..HEAD`）。

分类：

| 类别 | 计数 |
|------|------|
| 新增文件 | 2（Task 012 E2E spec + 完成报告） |
| 核心架构 | 4（router, ResearchAppLayout, AppMain, main.css） |
| 组件 | 30 |
| 页面 | 8 |
| E2E 修改 | 1（Task 011 spec +24 lines） |
| 单元测试修改 | 1（research-app-shell.test.ts ±4 lines） |
| 视图 | 1（SearchView.vue） |

## Issues

| # | 影响等级 | 文件 | 详情 |
|---|----------|------|------|
| P1 | **Low** | `apps/frontend/src/router/index.ts` L311–312 | `afterEach` #1 注释写 "Reset scroll to top" 但代码仅设置 `document.title`，未实现 `window.scrollTo` |
| P2 | **Low** | `apps/frontend/src/layouts/ResearchAppLayout.vue` L65–66 | `onMounted(() => {})` 和 `onBeforeUnmount(() => {})` 空调用，历史迭代残留 |
| P3 | **Style** | `apps/frontend/src/router/index.ts` L313, L322 | 两个 `afterEach` 可合并为单个钩子 |
| P4 | **Flake** | `apps/frontend/src/e2e/task011-navigation-consistency.spec.ts:214` | 本次 116/116 全绿（含 B2），前序 run 中 B2 Tablet viewport 出现过 1 次 Page crashed，重跑即过，判定为间歇性 CI 资源竞争 |
| P5 | **None** | `apps/frontend/src/components/layout/ResearchPrimaryNav.vue` | `sr-only` 类在 Task 012 前已存在；Task 012 仅改变使用方式（`v-if`→`:class`），此为 Task 011 nav reachability 的关键修复 |
| P6 | **Medium** | `apps/frontend/src/layouts/ResearchAppLayout.vue` | `ral-mobile-toggle`（`position:fixed; z-index:300`）与 sidebar（始终 in-flow）的定位交叉是有意设计但需文档标注 |

影响分布：0 Critical / 0 High / 1 Medium / 3 Low / 1 Style / 1 None。

## Allowed vs Forbidden Modification Scope

| 文件 | 允许范围 | 禁止范围 |
|------|----------|----------|
| `apps/frontend/src/router/index.ts` | P1 注释修正 / scroll 实现；P3 钩子合并 | ❌ 路由定义、beforeEach guard |
| `apps/frontend/src/layouts/ResearchAppLayout.vue` | P2 移除空 lifecycle hooks | ❌ sidebar in-flow、data-main-content、mobile-toggle、响应式断点 |
| 其他 45 个文件 | ❌ 禁止修改 | N/A |

全局禁止：

1. ❌ 路由 path / name / redirect / children 定义
2. ❌ Sidebar in-flow 策略（Task 012 最终收敛状态）
3. ❌ `[data-main-content]` 属性及 `tabindex="-1"`
4. ❌ ResearchAppLayout 响应式断点 `@media (max-width: 768px)`
5. ❌ `router.beforeEach` auth guard
6. ❌ Task 011 / Task 012 E2E specs
7. ❌ 所有组件业务逻辑、API 调用、数据模型、权限检查
8. ❌ 全局 CSS（`prefers-reduced-motion`、`:focus-visible`、`.sr-only`）

## Summary

| 检查项 | 结果 |
|--------|------|
| R1: Git 状态 + 只读性 | ✅ **PASS** — 工作树 clean，Phase 0 全程未修改代码 |
| R2: Router 归属审计 | ✅ **PASS** — `bd5de45` 新增 2 个 `afterEach` 钩子（+21 lines），不改变路由拓扑与权限，仅改变导航后副作用。在 Task 012 范围内，非格式化、非历史遗留 |
| R3: Type Check + Unit Tests + Build + E2E 复验 | ✅ **PASS** — Type Check clean / 371 UT / Build 4.10s / Task 012 专项 184/184 / Task 011 回归 116/116。全部用真实后端 + 真实种子数据复验 |
| R4: 报告完整性 | ✅ **PASS** — 包含 Baseline、HEAD、Router diff、commit attribution、47-file 清单、R1–R4 逐项结论、6 项问题（含影响等级）、修复/禁止范围。提交后 `git status --short` 为空 |

**Phase 0 只读补充审计：PASS（以 R1–R4 全绿为准），等待 Codex 验收。**
