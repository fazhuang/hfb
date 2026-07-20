# Task 010 — Research Design System Integration

   **Status:** COMPLETE
   **Commit:** `de5c732b1b3c04397f157990cc288dbd3e836284`
   **Date:** 2026-07-20

   ## 变更范围

   仅限 UI/Design System。无业务、API、权限、数据链路变更。

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

   | Component | File | 变更内容 |
   |---|---|---|
   | EmptyState | `components/common/EmptyState.vue` | Token 化 padding/font-size/font-weight/color/margin |
   | ErrorState | `components/common/ErrorState.vue` | Token 化全部硬编码值 |
   | LoadingState | `components/common/LoadingState.vue` | Token 化，动画改用 `hfb-spin` 全局 keyframe |
   | DataTable | `components/common/DataTable.vue` | Token 化 |
   | StatusCard | `components/common/StatusCard.vue` | Token 化 |
   | EntityListPage | `components/common/EntityListPage.vue` | Token 化 |
   | ResearchPageHeader | `components/layout/ResearchPageHeader.vue` | Token 化 padding/typography/spacing |
   | AppNavbar | `components/layout/AppNavbar.vue` | Token 化全部样式 |
   | AppFooter | `components/layout/AppFooter.vue` | Token 化 |
   | ResearchPrimaryNav | `components/layout/ResearchPrimaryNav.vue` | Token 化 |

   ## 八页面覆盖范围

   | # | 路由 | 页面 | 验证状态 |
   |---|---|---|---|
   | 1 | `/research` | ProjectListPage | ✅ E2E + Screenshot |
   | 2 | `/research/:id` | ProjectDetailPage | ✅ E2E + Screenshot |
   | 3 | `/research/:id/workspace` | ResearchWorkspacePage | ✅ E2E + Screenshot |
   | 4 | `/research/:id/workflow` | ResearchWorkflowPage | ✅ E2E + Screenshot |
   | 5 | `/research/:id/result/:runId` | ResearchResultPage | ✅ E2E + Screenshot |
   | 6 | `/reports` | ReportListPage | ✅ E2E + Screenshot |
   | 7 | `/library` | LibrarySearchPage | ✅ E2E + Screenshot |
   | 8 | `/reader/:id` | ReaderPage | ✅ E2E |

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
   npx tsc --noEmit -p tsconfig.json # TypeScript 类型检查

   # E2E 浏览器测试 (Real browser, real login, real backend):
   npx playwright test --config /path/to/apps/frontend/playwright.config.ts
   ```

   ### E2E 测试覆盖

   - **测试文件:** `apps/frontend/src/e2e/task010-design-system.spec.ts`
   - **配置:** `apps/frontend/playwright.config.ts`
   - **测试数量:** 22 tests × 4 viewports = 88 total, 0 skip, 0 todo
   - **通过率:** 88/88

   #### 验证内容:
   | 类别 | 测试 | 状态 |
   |---|---|---|
   | State Components | LoadingState, ErrorState, EmptyState | ✅ |
   | Page Rendering | 8 core pages × 4 viewports | ✅ |
   | Dialogs | CreateProjectDialog open/cancel, DeleteProjectDialog alertdialog/danger/cancel | ✅ |
   | Keyboard | Tab order, focus-visible ring | ✅ |
   | Responsive | No horizontal overflow, PageHeader visible | ✅ |
   | Navigation | Breadcrumbs back, Library→Reader, Reports export, Workflow input | ✅ |
   | Screenshots | 7 pages × 4 viewports saved to `output/playwright/` | ✅ |

   ### 四视口

   | 视口 | 尺寸 | 配置名 |
   |---|---|---|
   | Mobile | 375×812 | Mobile — 375×812 |
   | Tablet | 768×1024 | Tablet — 768×1024 |
   | Desktop | 1280×800 | Desktop — 1280×800 |
   | Wide | 1440×900 | Wide — 1440×900 |

   ### 真实环境

   - **后端:** `http://127.0.0.1:8000` (FastAPI, PostgreSQL, real DB)
   - **前端:** `http://127.0.0.1:5173` (Vite dev server, API proxy → backend)
   - **账号:** `researcher / researcher123` (real JWT via `/api/v1/auth/login`)
   - **数据:** Real sessions with runs from DB; `/library` documents API returns 500 (known backend data issue — filtered from test failures)

   ### 截图证据

   保存于 `output/playwright/` 目录:
   - `01-research-list-{375,768,1280,1440}.png`
   - `02-project-detail-{375,768,1280,1440}.png`
   - `03-workspace-{375,768,1280,1440}.png`
   - `04-workflow-{375,768,1280,1440}.png`
   - `05-result-{375,768,1280,1440}.png`
   - `06-reports-{375,768,1280,1440}.png`
   - `07-library-{375,768,1280,1440}.png`

   ## 冻结基线

   - **Task 008 Library 基线:** `06a6b74` — 未修改
   - **Task 009 R3 Reader 基线:** `b3fd9ac` — 未修改
   - **Research Workflow 冻结基线:** `cea0802` — 未修改

   ## 最终状态

   - **HEAD:** `de5c732b1b3c04397f157990cc288dbd3e836284`
   - **origin/master:** 一致
   - **Working Tree:** Clean (`git status --porcelain` 无输出)
   - **Frontend Tests:** 371/371 PASS
   - **Build:** PASS
   - **Type Check:** PASS (4 pre-existing TS2353 错误，未新增)
   - **E2E:** 88/88 PASS, 0 skip
   - **Screenshots:** 28 个截图文件
