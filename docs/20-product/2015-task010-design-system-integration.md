# Task 010 — Research Design System Integration

**Status:** COMPLETE (P0 repairs applied)
**Commit:** `95630d74e2e6b53f445a85ae19d30e7fb9d5860f`
**Date:** 2026-07-21
**Verified:** 2026-07-21 03:17 UTC — 88/88 E2E PASS with real backend, real login, real data

## P0 修复 (2026-07-21)

针对 Task 010 验收报告中的四项阻断项进行修复：

### 1. Loading E2E 收紧

- 使用 `waitUntil: 'commit'` 导航到 `/reports`（该端点扫描所有 sessions/runs 自然较慢）
- 必须断言 `.loading-state[role="status"]` 及内部 `.loading-spinner` 实际可见
- 加载完成后验证内容区渲染
- 不再以「请求已完成，内容区存在」为通过条件

### 2. Reports 导出 E2E 收紧

- 必须定位 `.rrli-export-btn`（仅 `report_status === 'ready'` 时渲染）
- 若无 ready report 则测试失败（要求受控真实数据必须包含至少一条可导出报告）
- 真实点击导出按钮，抓取 download 事件
- 验证文件名以 `.md` 结尾
- 读取下载内容验证非空
- 不做 error 文本存在 / 状态徽标存在的宽松替代

### 3. Dialog 精确焦点返回 (P0-2 最终修复)

- **CreateProjectDialog** 和 **DeleteProjectDialog** 改为接收 `triggerEl` prop：
  - `ProjectListPage` 通过 `ref="createBtnRef"` 获取 "新建课题" 按钮引用，作为 `:trigger-el` 传入
  - `ProjectDetailPage` 通过 `ref="moreBtnRef"` 获取 "更多操作" 按钮引用，作为 `:trigger-el` 传入
  - Dialog 关闭时调用 `nextTick(() => props.triggerEl?.focus())` 精确恢复到触发按钮
- **不保存 menuitem 作为恢复目标**：DeleteProjectDialog 的 menuitem 在 `onDelete()` 中 `showMoreMenu = false` 后同步卸载，旧实现的 `document.activeElement` 捕获到已卸载元素
- **CreateProjectDialog 同样修复**：touch 视口（Mobile/Tablet）下按钮点击不转移焦点，旧实现的 `document.activeElement` 捕获不到按钮
- **E2E 断言改为精确相等**：`document.activeElement.getAttribute('aria-label') === '新建课题'` / `=== '更多操作'`
- 禁止 `document.body.contains(activeElement)` 宽松通过
- 禁止 `tagName` 仅检查
- 禁止 "body 也算通过" fallback

### 4. 工件清理

- `output/playwright/` 由 `.gitignore` 忽略，无根目录残留

## 变更范围

仅限 UI/Design System。无业务、API、权限、数据链路变更。

### 修改文件

| 文件                                                            | 变更                                                                       |
| --------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `apps/frontend/src/e2e/task010-design-system.spec.ts`           | Loading/Export/Dialog 测试收紧；焦点精确断言 aria-label 相等               |
| `apps/frontend/src/components/research/CreateProjectDialog.vue` | 新增 `triggerEl` prop，关闭时精确恢复到触发按钮                            |
| `apps/frontend/src/components/research/DeleteProjectDialog.vue` | 新增 `triggerEl` prop，关闭时精确恢复到触发按钮（避免捕获已卸载 menuitem） |
| `apps/frontend/src/pages/research/ProjectListPage.vue`          | 新增 `createBtnRef` template ref 并传入 CreateProjectDialog                |
| `apps/frontend/src/pages/research/ProjectDetailPage.vue`        | 新增 `moreBtnRef` template ref 并传入 DeleteProjectDialog                  |

## Design Token 来源与接入路径

- **来源文件:** `apps/frontend/src/assets/main.css`
- **接入方式:** CSS Custom Properties 定义于 `:root`，所有 Research 模块组件通过 `scoped` 样式块中的 `var(--token, fallback)` 引用
- **Token 类别:**
  - Typography: `--text-xs` / `--text-sm` / `--text-base` / `--text-lg` / `--text-xl` / `--text-2xl` / `--text-3xl`
  - Font weight: `--font-normal` / `--font-medium` / `--font-semibold` / `--font-bold`
  - Spacing: `--space-1` 至 `--space-15`
  - Color: `--color-accent` / `--color-accent-hover` / `--color-accent-light`, `--color-text-{primary,secondary,muted}`, `--color-border` / `--color-hover` / `--color-active`, `--color-surface`, `--color-{success,warning,error,info}-{text,bg,icon-bg}`
  - Radius: `--radius-sm` / `--radius-md` / `--radius-lg` / `--radius-xl` / `--radius-2xl`
  - Shadow: `--shadow-sm` / `--shadow-md` / `--shadow-lg` / `--shadow-toast`
  - Transition: `--transition-fast` / `--transition-base` / `--transition-slow`
  - Button: `--btn-padding-{sm,md,lg}` / `--btn-font-{sm,md,lg}` / `--btn-radius`
  - Focus: `--focus-ring` / `--focus-ring-sm`
  - Light/Dark 模式均支持

## 涉及的通用组件

| Component          | File                                       | 变更内容                                            |
| ------------------ | ------------------------------------------ | --------------------------------------------------- |
| EmptyState         | `components/common/EmptyState.vue`         | Token 化 padding/font-size/font-weight/color/margin |
| ErrorState         | `components/common/ErrorState.vue`         | Token 化全部硬编码值                                |
| LoadingState       | `components/common/LoadingState.vue`       | Token 化，动画改用 `hfb-spin` 全局 keyframe         |
| DataTable          | `components/common/DataTable.vue`          | Token 化                                            |
| StatusCard         | `components/common/StatusCard.vue`         | Token 化                                            |
| EntityListPage     | `components/common/EntityListPage.vue`     | Token 化                                            |
| ResearchPageHeader | `components/layout/ResearchPageHeader.vue` | Token 化 padding/typography/spacing                 |
| AppNavbar          | `components/layout/AppNavbar.vue`          | Token 化全部样式                                    |
| AppFooter          | `components/layout/AppFooter.vue`          | Token 化                                            |
| ResearchPrimaryNav | `components/layout/ResearchPrimaryNav.vue` | Token 化                                            |

## 八页面覆盖范围

| #   | 路由                          | 页面                  | 验证状态            |
| --- | ----------------------------- | --------------------- | ------------------- |
| 1   | `/research`                   | ProjectListPage       | ✅ E2E + Screenshot |
| 2   | `/research/:id`               | ProjectDetailPage     | ✅ E2E + Screenshot |
| 3   | `/research/:id/workspace`     | ResearchWorkspacePage | ✅ E2E + Screenshot |
| 4   | `/research/:id/workflow`      | ResearchWorkflowPage  | ✅ E2E + Screenshot |
| 5   | `/research/:id/result/:runId` | ResearchResultPage    | ✅ E2E + Screenshot |
| 6   | `/reports`                    | ReportListPage        | ✅ E2E + Screenshot |
| 7   | `/library`                    | LibrarySearchPage     | ✅ E2E + Screenshot |
| 8   | `/reader/:id`                 | ReaderPage            | ✅ E2E              |

## 无业务/API/权限/数据链路变更声明

- 未修改任何 `.py` 后端文件
- 未修改任何 API 路由、endpoint、请求参数、返回映射
- 未修改任何 Repository / Service / Domain Model / RBAC / OCR / Citation / Evidence / AI Workflow / Report Engine
- 未修改 `ReaderPage.vue`、Reader API、Reader Tests、Reader E2E（冻结基线 `b3fd9ac`）
- 未修改 Library 数据链路（冻结基线 `06a6b74`）
- 未修改 Research Workflow 冻结基线 `cea0802`
- 未新增任何页面、业务组件、状态流、功能入口

## E2E / 浏览器 / 响应式 / 无障碍验收

### 测试命令

```bash
# 在 apps/frontend 目录执行:
npm run test -- --run            # Vitest 前端单元测试 (371 tests)
npm run build                     # Vite 生产构建
npm run type-check               # TypeScript 类型检查

# E2E 浏览器测试 (Real browser, real login, real backend):
npm run test:e2e
```

### E2E 测试覆盖

- **测试文件:** `apps/frontend/src/e2e/task010-design-system.spec.ts`
- **配置:** `apps/frontend/playwright.config.ts`
- **测试数量:** 22 tests × 4 viewports = 88 total, 0 failed, 0 skipped, 0 todo
- **通过率:** 88/88 PASS (real backend, real DB, real login, real JWT)

#### 验证内容:

| 类别                       | 测试                                                                                                                                                                                                   | 状态 |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---- |
| State Components           | LoadingState (spinner 必须出现 + role=status), ErrorState (role=alert + retry), EmptyState (role=status)                                                                                               | ✅   |
| Page Rendering             | 8 core pages × 4 viewports — all with console error assertions                                                                                                                                         | ✅   |
| Dialogs                    | CreateProjectDialog open/cancel, DeleteProjectDialog alertdialog/danger/cancel                                                                                                                         | ✅   |
| Dialog 精确焦点返回 (P0-2) | CreateProjectDialog: Escape→focus="新建课题" button, Cancel→focus="新建课题" button; DeleteProjectDialog: Escape→focus="更多操作" button, Cancel→focus="更多操作" button — 精确 aria-label 相等断言    | ✅   |
| Keyboard                   | Tab order (interactive elements), focus-visible ring (computed outline/box-shadow; touch: confirmed absence is expected)                                                                               | ✅   |
| Responsive                 | No horizontal overflow (7 routes), PageHeader visible                                                                                                                                                  | ✅   |
| Navigation                 | Breadcrumbs back, Library→detail→全文阅读→Reader (SPA navigation + page validation), Reports export (real download event, .md filename, non-empty content), Workflow step advance (question→selection) | ✅   |
| Screenshots                | 8 pages × 4 viewports saved to `output/playwright/`                                                                                                                                                    | ✅   |

### 四视口

| 视口    | 尺寸     | 配置名             |
| ------- | -------- | ------------------ |
| Mobile  | 375×812  | Mobile — 375×812   |
| Tablet  | 768×1024 | Tablet — 768×1024  |
| Desktop | 1280×800 | Desktop — 1280×800 |
| Wide    | 1440×900 | Wide — 1440×900    |

### 真实环境

- **后端:** `http://127.0.0.1:8000` (FastAPI, PostgreSQL, real DB, SEED_TEST_DATA=1)
- **前端:** `http://127.0.0.1:5173` (Vite dev server, API proxy → backend)
- **账号:** `researcher / researcher123` (real JWT via `/api/v1/auth/login`)
- **数据:** Real sessions with runs from DB; real documents via `/api/v1/documents`

### 截图证据

保存于 `output/playwright/` 目录:

- `01-research-list-{375,768,1280,1440}.png`
- `02-project-detail-{375,768,1280,1440}.png`
- `03-workspace-{375,768,1280,1440}.png`
- `04-workflow-{375,768,1280,1440}.png`
- `05-result-{375,768,1280,1440}.png`
- `06-reports-{375,768,1280,1440}.png`
- `07-library-{375,768,1280,1440}.png`
- `08-reader-{375,768,1280,1440}.png`

## 冻结基线

- **Task 008 Library 基线:** `06a6b74` — 未修改
- **Task 009 R3 Reader 基线:** `b3fd9ac` — 未修改
- **Research Workflow 冻结基线:** `cea0802` — 未修改

## 最终状态

- **HEAD:** `95630d74e2e6b53f445a85ae19d30e7fb9d5860f`
- **Frontend Tests:** 371/371 PASS
- **Build:** PASS
- **Type Check:** PASS (0 errors)
- **E2E:** 88/88 PASS, 0 failed, 0 skipped
- **Screenshots:** 32 个截图文件 (8 pages × 4 viewports)
- **HTML Report:** `output/playwright/report/index.html`
- **Playwright Artifacts:** `output/playwright/test-artifacts/` (no root pollution)
- **无 mock、无 localStorage 注入、无 dispatchEvent、无 skip/todo/only**
- **Dialog 焦点精确返回验证：CreateProjectDialog → "新建课题" button, DeleteProjectDialog → "更多操作" button — 精确 aria-label 相等**
- **禁止保存已卸载 menuitem 作为恢复目标；由父页面通过 ref 显式传入稳定触发按钮引用**
