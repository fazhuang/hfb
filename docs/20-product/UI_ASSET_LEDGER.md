# UI Asset Ledger — HFB MVP Frontend

> **状态**：WP-0 B1 只读盘点，当前 HEAD。不修改任何代码、token、依赖或组件。
> **生成依据**：`apps/frontend/src/` 目录遍历、样式 token 文件、组件文件、store 文件与依赖声明（`package.json`）。
> **下文"处置"列**：`keep` = 当前实现一致且可继续使用；`gap` = 当前缺失，B 阶段需补齐；`drift` = 多头实现/不一致，需统一。

---

## 1. 页面组覆盖

> 以下路由提取自 `apps/frontend/src/router/index.ts`，仅列研究 MVP 四页面组。

### 1.1 Workspace（项目工作台）

| 项 | 实际值 |
|---|---|
| **路由** | `/research/:projectId/workspace` (name: `research-project-workspace`) |
| **页面组件** | `pages/research/ResearchWorkspacePage.vue` |
| **布局** | `layouts/ResearchAppLayout.vue` |
| **关键子组件 (src/components/research/)** | `ProjectOverview.vue`, `ProjectNotes.vue`, `ProjectReports.vue`, `ResearchResources.vue`, `ResearchActivityList.vue`, `ResearchAssistantEntry.vue`, `ProjectListToolbar.vue`, `ContinueResearchCard.vue`, `RecentNotes.vue`, `RecentReports.vue`, `RecentResearchActivity.vue` |
| **entry guard** | `requiresAuth`（通过 `ResearchAppLayout → meta: { section: 'research', requiresAuth: true }`） |

### 1.2 Workflow / Result（研究执行与结果）

| 项 | 实际值 |
|---|---|
| **Workflow 路由** | `/research/:projectId/workflow` (name: `research-project-workflow`) |
| **Workflow 页面** | `pages/research/ResearchWorkflowPage.vue` |
| **Result 路由** | `/research/:projectId/result/:runId` (name: `research-project-result`) |
| **Result 页面** | `pages/research/ResearchResultPage.vue` |
| **布局** | 均为 `layouts/ResearchAppLayout.vue` |
| **Workflow 步骤组件** | `ResearchQuestionStep.vue`, `DocumentSelectionStep.vue`, `EvidenceReviewStep.vue`, `ResearchReportStep.vue`, `WorkflowStepNavigation.vue` |
| **Result 组件** | `EvidenceDetail.vue`, `CitationPanel.vue`, `SourceReferenceCard.vue`, `ResearchReportViewer.vue`, `ResearchResultHeader.vue`, `ResearchResultErrorState.vue`, `LineageStatusBadge.vue`, `ResearchRunSummary.vue` |
| **Citation/Evidence/SourceRef 链路** | `CitationPanel` → 点击 → `EvidenceDetail`（同 trace_id/passage_id）→ `SourceReferenceCard`（source_ref_id + Reader href）→ `router-link` 导航至 Library/Reader |
| **entry guard** | `requiresAuth` |

### 1.3 Library（文献库）

| 项 | 实际值 |
|---|---|
| **搜索路由** | `/library` (name: `library-search`) |
| **搜索页面** | `pages/library/LibrarySearchPage.vue` |
| **详情路由** | `/library/:id` (name: `library-detail`) |
| **详情页面** | `pages/library/LibraryDetailPage.vue` |
| **布局** | 均为 `layouts/ResearchAppLayout.vue` |
| **关键子组件** | `LibrarySearchBar.vue`, `LibraryDocumentCard.vue`, `LibraryDocumentStatsPanel.vue` |
| **entry guard** | `requiresAuth` |

### 1.4 Reader（独立全文阅读器 — Task 009）

| 项 | 实际值 |
|---|---|
| **路由** | `/reader/:id` (name: `reader`) — standalone，不嵌套在 Library 模块下 |
| **页面组件** | `pages/reader/ReaderPage.vue` |
| **子组件** | `components/reader/PassageReader.vue` |
| **布局** | 无 ResearchAppLayout 包裹 — 直接挂载在 `DefaultLayout` 下 |
| **passage 定位** | 通过 query string `?passage=<passage_id>` 实现，无独立路由参数。**Library→Reader passage 契约已实现** — `LibraryDetailPage` 读取 `route.query.passage` 并透传至 Reader URL（`/reader/${id}?passage=${pid}`）。Reader 端消费待实现（ReaderPage 只读取 `route.params.id`，高亮/滚动至特定 passage 未实现）。 |
| **entry guard** | `requiresAuth` |
| **Library 入口** | `LibraryDetailPage.vue`: `router.push(\`/reader/${doc.value.id}?passage=${passageId}\`)`（带 `?passage` 透传）；**SourceReferenceCard → Library → Reader 链路**：`SourceReferenceCard.vue:84-86` 构建 `router-link` 指向 `/library/{docId}?passage={pid}`，`LibraryDetailPage` 读取 `route.query.passage` 后透传至 Reader。 |

**Reader 排版状态（精确）**：

| 维度 | 实际值 |
|---|---|
| 古籍衬线字体 | **无** — `ReaderPage.vue` 全文未设置 `font-family: serif` / `Songti SC` / `STSong`；`PassageReader.vue` 同样无。主体文本依赖 `--font-sans` |
| monospace 元数据 | **有** — `ReaderPage.vue:983`: `.reader-evidence-passage { font-family: monospace; }`，用于 evidence passage ID 展示；`LibraryDetailPage.vue:292`: `.lib-detail-field-value { font-family: var(--font-mono); }`，用于文献元数据字段值 |
| 原文段落渲染 | `reader-chunk-paragraph` class，无额外 font-family，继承 sans-serif |
| 引用/证据文本 | 无引文专用宋体 — `reader-citation-quote` 使用 `font-style: italic` 但未设 serif |
| 段落导航 | 使用 monospace（`reader-paragraph-label` 无 font 覆盖，继承 default） |

### 1.5 Reports（报告列表）

| 项 | 实际值 |
|---|---|
| **路由** | `/reports` (name: `report-list`) |
| **页面组件** | `pages/reports/ReportListPage.vue` |
| **布局** | `layouts/ResearchAppLayout.vue` |
| **关键子组件** | `ResearchReportList.vue`, `ResearchReportListItem.vue`, `ResearchReportStatusBadge.vue` |
| **entry guard** | `requiresAuth` |
| **最近变更 (C2-4)** | 2026-08-04 — 视觉层级优化：卡片 hover 阴影、标签 badge 并入 meta 行、按钮 44px min touch target、分页统一 HfbPagination、aria-busy/aria-live 加载态、per-item export error 作用域 |

---

## 2. Design Tokens（10 文件，纯 CSS custom properties）

**事实源**：`apps/frontend/src/styles/tokens/`

| 文件 | 覆盖领域 | 值计数 | 处置 |
|---|---|---|---|
| `typography.css` | 字体族 (`--font-sans`, `--font-mono`)、字号 (`text-xs`..`text-3xl`)、字重、行高 | ~14 tokens | keep — 无古籍衬线 token（缺口见 §4） |
| `colors.css` | 主题色 (accent)、文本、边框、hover、页面/surface 背景；完整 `html.dark` 覆盖 | ~28 tokens（亮）+ ~14 tokens（暗） | keep |
| `semantic.css` | success/warning/error/info 四色系，含 text/bg/icon-bg；完整 dark | ~24 tokens | keep |
| `components.css` | 按钮尺寸/字重/圆角、focus ring、输入框、禁用态、overlay、accent-alpha 变体 | ~20 tokens | keep |
| `spacing.css` | 4px 基网格，`space-0`..`space-20` | ~30 tokens | keep |
| `radius.css` | `radius-none`..`radius-full`/`round`，含 `space-0-25`（1px） | ~12 tokens | keep |
| `shadow.css` | sm/md/lg/toast + accent + focus + card + dropdown | ~16 tokens | keep |
| `transition.css` | 时长 (`fast`/`base`/`slow`/`spinner`/`pulse`) + easing | ~8 tokens | keep |
| `z-index.css` | dropdown/dialog/drawer/toast | 4 tokens | keep |
| `breakpoints.css` | sm/md/lg/xl（640/768/1024/1440） | 4 values | keep |

**证据**：`design-tokens.test.ts`（478 行）对 token 存在性、HSLA 格式、contrast ratio 进行契约验证。

---

## 3. Hfb 基础组件（`components/common/`）

**事实源**：`apps/frontend/src/components/common/`

| 组件 | 文件 | 状态 | CSS | 关键特性 | 处置 |
|---|---|---|---|---|---|
| **HfbButton** | `HfbButton.vue` | ✓ | `base/button.css` | variant (primary/secondary/ghost/danger), size, loading, disabled, icon slots, aria-busy | keep |
| **HfbInput** | `HfbInput.vue` | ✓ | `base/input.css` | label, placeholder, error, disabled, helper text | keep |
| **HfbSelect** | `HfbSelect.vue` | ✓ | `base/select.css` | options, placeholder, disabled | keep |
| **HfbTextarea** | `HfbTextarea.vue` | ✓ | （内联 scoped style） | label, rows, placeholder | keep |
| **HfbDialog** | `HfbDialog.vue` | ✓ | `base/dialog.css` | title, content, footer slots, close button, trap focus | keep |
| **HfbDrawer** | `HfbDrawer.vue` | ✓ | `base/drawer.css` | left/right, title, close, overlay | keep |
| **HfbDropdown** | `HfbDropdown.vue` | ✓ | `base/dropdown.css` | trigger slot, items, keyboard | keep |
| **HfbTabs** | `HfbTabs.vue` | ✓ | `base/tabs.css` | tab list, active indicator | keep |
| **HfbTable** | `HfbTable.vue` | ✓ | `base/table.css` | columns, sort, empty | keep |
| **HfbPagination** | `HfbPagination.vue` | ✓ | `base/pagination.css` | page, prev/next, total | keep |
| **HfbBadge** | `HfbBadge.vue` | ✓ | `base/badge.css` | variant, dot | keep |
| **HfbAlert** | `HfbAlert.vue` | ✓ | `base/alert.css` | variant (info/success/warning/error), icon, title, dismissible | keep |
| **HfbToastProvider** | `HfbToastProvider.vue` | ✓ | `base/toast.css` | position, auto-dismiss, queue | keep |
| **HfbSkeleton** | `HfbSkeleton.vue` | ✓ | `base/skeleton.css` | pulse animation, width/height | keep |
| **EmptyState** | `EmptyState.vue` | ✓ | （内联 scoped style） | icon, title, description, action slot | keep |
| **ErrorState** | `ErrorState.vue` | ✓ | （内联 scoped style） | message, retry action | keep |
| **LoadingState** | `LoadingState.vue` | ✓ | （内联 scoped style） | spinner, label | keep |
| **StatusCard** | `StatusCard.vue` | ✓ | （内联 scoped style） | status label, icon, detail | keep |
| **DataTable** | `DataTable.vue` | ✓ | （内联 scoped style） | sort, pagination, columns | keep |
| **EntityListPage** | `EntityListPage.vue` | ✓ | （内联 scoped style） | title, search, create, list slot | keep |
| **PlaceholderPage** | `PlaceholderPage.vue` | ✓ | （内联 scoped style） | icon, title, description | keep |
| **LegacyRedirect** | `LegacyRedirect.vue` | ✓ | — | 旧路由兼容重定向 | keep |

### 3.1 状态组件闭环

| 状态 | 组件 | 覆盖页面组 |
|---|---|---|
| **Empty** | `EmptyState` + `PlaceholderPage` | 全部 |
| **Loading** | `LoadingState` + `HfbSkeleton` | 全部 |
| **Error** | `ErrorState` + `HfbAlert` + `ResearchResultErrorState` | 全部 |
| **Success/Completeness** | `StatusCard` + `HfbBadge` + `LineageStatusBadge` | Workflow/Result |

**证据**：基础组件各有独立 CSS（`styles/base/`），每个 variant/size/disabled/loading 状态均有视觉差异。组件通过 scoped style 引用 token 变量。

### 3.2 Base CSS 文件清单

**事实源**：`apps/frontend/src/styles/base/`

| 文件 | 对应组件 | 处置 |
|---|---|---|
| `button.css` | HfbButton | keep |
| `input.css` | HfbInput | keep |
| `select.css` | HfbSelect | keep |
| `dialog.css` | HfbDialog | keep |
| `drawer.css` | HfbDrawer | keep |
| `dropdown.css` | HfbDropdown | keep |
| `tabs.css` | HfbTabs | keep |
| `table.css` | HfbTable | keep |
| `pagination.css` | HfbPagination | keep |
| `badge.css` | HfbBadge | keep |
| `alert.css` | HfbAlert | keep |
| `toast.css` | HfbToastProvider | keep |
| `skeleton.css` | HfbSkeleton | keep |

---

## 4. 古籍 / 中西文混排 Typography

### 4.1 Token 层

> **事实源**：`apps/frontend/src/styles/tokens/typography.css`

- `--font-sans`：`-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif`
- `--font-mono`：`'SF Mono', 'Fira Code', 'Fira Mono', 'Roboto Mono', monospace`
- **缺失**：全局 `--font-serif` / `--font-classical` token。

### 4.2 实际古籍衬线使用（硬编码，4 处）

> **事实源**：grep `font-family.*serif|Songti|STSong`

| 位置 | 字体栈 | 用途 | 处置 |
|---|---|---|---|
| `CitationPanel.vue:178` | `'Songti SC', 'STSong', 'Noto Serif CJK SC', serif` | 引用卡片古籍原文展示 | drift |
| `EvidenceDetail.vue:112` | `'Songti SC', 'STSong', 'Noto Serif CJK SC', serif` | 证据详情古籍原文展示 | drift |
| `EvidenceReviewStep.vue:319` | `'Songti SC', 'STSong', 'Noto Serif CJK SC', serif` | 证据审核步骤古籍原文展示 | drift |
| `ResearchWorkflowView.vue:855` | `'Songti SC', 'STSong', serif` | 工作流视图某区域（不一致 — 缺少 `Noto Serif CJK SC` fallback） | drift |

### 4.3 中西文混排

- 当前**无** `lang` 属性驱动的中西文混排规则（`lang="zh"` / `lang="en"` 无样式差异）。
- 无 `text-spacing` / `word-break` / 竖排（`writing-mode`）支持。
- 引用文本混排（古文 + 现代标点）依赖浏览器默认渲染，无额外归一化。

**处置**：B 阶段需引入 `--font-serif` token，统一 4 处硬编码，在 `CitationPanel` / `EvidenceDetail` / `EvidenceReviewStep` 中提供中西文混排基线（`lang` 感知行高/字间距）。

---

## 5. 图标现状与替换缺口

### 5.1 当前实现

> **事实源**：grep `icon` across all `.vue` files, `apps/frontend/package.json`

- **无图标库依赖**。`package.json` 中没有 `@iconify`、`lucide-vue-next`、`@phosphor-icons/vue`、`@heroicons/vue` 或 `font-awesome`。
- 图标通过 **Unicode 文字符号内联渲染**：
  - `HfbAlert`：`ℹ` `✓` `⚠` `✕`
  - `EmptyState`：`📭`（默认，可通过 prop 覆盖）
  - `HfbTable`、`HfbToastProvider`、`StatusCard`、`PlaceholderPage`、`ErrorState`：通过 prop 或默认值传入 Unicode
  - `ResearchPrimaryNav`、`AppNavbar`：路由导航 emoji（`🏠` `🔍` `📚` `⚙️` `🏛️`）
  - 按钮 icon slot：调用方自行传入任意内容（当前多为 Unicode）
- **HfbButton** 有 `icon` 和 `icon-after` 两个 slot，但无图标类型约束。

### 5.2 缺口

| 缺口 | 影响 | 处置 |
|---|---|---|
| 无统一图标库 | 每个使用点自行选择 Unicode/emoji，视觉不一致 | gap — B2 选包后统一 |
| 无 SVG 图标组件 | 无法控制尺寸、颜色、stroke-width；无 tree-shaking | gap |
| 无无障碍 icon label | Unicode 字符的 `aria-hidden="true"` 用法不一致 | gap |
| 按钮 icon slot 无类型 | 调用方可传任意 HTML，设计偏离风险管理为零 | gap |
| 古籍相关图标缺失 | 卷/页/版本/校勘/异文无专属图标 | gap — 需 B2 评估候选包是否覆盖 CJK 古籍 icon |

---

## 6. Pinia UI 状态持久化

**事实源**：`apps/frontend/src/stores/`

| Store | 文件 | 职责 | 持久化方式 | 处置 |
|---|---|---|---|---|
| **auth** | `stores/auth.ts` | access_token, refresh_token, currentUser, roles, login/logout/refresh | localStorage：`hfb-access-token` + `hfb-refresh-token`（`loadTokens()` at init）+ token refresh 定时器 | keep |
| **system** | `stores/system.ts` | backendConnected, dbConnected, redisConnected, esConnected, minioConnected, version, environment | 内存 (ref) — 每次页面加载重新探测 | keep |
| **research** | `stores/research.ts` | currentTopic (name, description, createdAt) | localStorage (`hfb-current-research-topic`) | keep |
| **theme** | `composables/useTheme.ts` | theme (light/dark/auto) | localStorage (`hfb-theme`) + `prefers-color-scheme` 监听 | keep |
| **i18n** | `i18n/index.ts` | locale (zh-CN/en) | localStorage (`hfb-locale`) + 浏览器语言检测 | keep |

### 6.1 缺口

| 缺口 | 详情 | 处置 |
|---|---|---|
| 无 `pinia-plugin-persistedstate` | 当前各 store 自行实现 localStorage 读写（try/catch + key 管理），无统一插件 | gap — 代码重复但无功能缺陷 |
| 无跨标签页同步 | `research` store topic 变更不同步到其他标签页 | gap |
| 无过期/迁移策略 | localStorage 中旧 schema 无版本号、无迁移路径 | gap |

---

## 7. Pattern 资产（按功能横切）

### 7.1 Search / Filter（C1-1 已收敛）

**收敛日期**：2026-08-02

**统一基础组件**：`HfbToolbar.vue`（`components/common/`）— 单一 Search / Filter / Toolbar 模式，使用 B3 已审批的基础组件（HfbInput、HfbSelect、HfbButton、HfbIcon）。

**收敛目标**：Reports 页面组。

#### 收敛实现

| 组件 | 使用页面组 | 技术特征 | 处置 |
|---|---|---|---|
| **`HfbToolbar`** | **Reports**（已适配） | HfbInput（搜索）+ HfbSelect（筛选下拉）+ HfbButton（清除全部）。防抖 300ms、键盘 Enter 即时搜索、响应式布局。类型安全的 `ToolbarFilter[]` 配置 + `ToolbarSearchPayload` 事件。 | **统一模式** |
| `LibrarySearchBar` | Library | 原始 input + select。下一阶段收敛目标。 | keep（待 C1-2 收敛） |
| `ProjectListToolbar` | Workspace | 原始 input + clear 按钮。下一阶段收敛目标。 | keep（待 C1-2 收敛） |
| `ResearchReportsToolbar` | Reports（旧） | **已被 HfbToolbar 替代**。保留为未使用引用，供 C1-2 参考。 | **已淘汰（C1-1）** |

#### 统一接口

```ts
// HfbToolbar props
searchable?: boolean;          // 是否显示搜索输入框
searchPlaceholder?: string;    // 搜索占位文本
filters?: ToolbarFilter[];     // 筛选下拉定义
filterValues?: Record<string, string | number | null>; // 当前筛选值
loading?: boolean;             // 加载状态
loadingLabel?: string;         // 加载提示文本
showClearButton?: boolean;    // 是否显示"清除筛选"按钮

// HfbToolbar emits
@search: ToolbarSearchPayload;      // { query: string, filters: Record }
@update:filterValues: Record;       // 筛选值变更
```

#### 已适配页面

- **ReportListPage**（`pages/reports/`）：`searchable=false`，1 个状态筛选下拉（`status`），与 `useResearchReports` composable 共享 `filterValues` ref。
- **useResearchReports** composable：导出 `REPORT_TOOLBAR_FILTERS` 常量 + `ToolbarFilterValues` 类型的 `filterValues` ref，取代旧的 `statusFilter`/`setStatusFilter`。导出 `onSearch(payload: ToolbarSearchPayload)` 供页面连接工具栏事件。

**证据**：18 项 HfbToolbar vitest + 20 项 Reports 页面 vitest（更新后的契约）。678 项全量测试套件 + type-check 零错误。

### 7.2 列表 / Card / Pagination

**事实源**：`ProjectListItem.vue`、`LibraryDocumentCard.vue`、`ResearchReportList.vue`、`ResearchReportListItem.vue`、`HfbPagination.vue`、`DataTable.vue`、`HfbTable.vue`、`EntityListPage.vue`、`ResearchActivityList.vue`

| Pattern | 实现 | 处置 |
|---|---|---|
| 实体列表页 | `EntityListPage` 通用模板（Workspace/Reports 使用） | keep |
| 卡片列表 | `LibraryDocumentCard`、`ProjectListItem`、`ResearchReportListItem` — 各自独立实现 | drift — 3 种卡片无共享基础 |
| 表格 | `HfbTable` + `DataTable` — 两个表格实现并存 | drift — `DataTable` 有更多功能但使用较少 |
| 分页 | `HfbPagination` 统一 — 所有列表页引用同一组件 | keep |
| 活动列表 | `ResearchActivityList` — Workspace 专用 | keep |

### 7.3 Detail Header

**事实源**：`ResearchResultHeader.vue`、`ProjectOverview.vue`、Research session 的 `ResearchPageHeader.vue`

| 组件 | 使用场景 | 处置 |
|---|---|---|
| `ResearchResultHeader` | Workflow 结果页顶部 | keep |
| `ProjectOverview` | Workspace 详情头部 | keep |
| `ResearchPageHeader` | 研究布局通用头部 | keep |

### 7.4 Citation / Evidence / SourceRef

**事实源**：`CitationPanel.vue`、`EvidenceDetail.vue`、`SourceReferenceCard.vue`、`LineageStatusBadge.vue`、`ResearchResultErrorState.vue`

| 组件 | 核心职责 | 关键数据绑定 | 用古籍衬线 | 处置 |
|---|---|---|---|---|
| `CitationPanel` | 引用列表（`.rcp-citation-item`），点击展开 Evidence | trace_id 前缀展示、passage_id 传递 | ✓ (Songti SC) | keep |
| `EvidenceDetail` | 证据详情卡片（`.eed-card`、`.eed-meta-row`） | trace_id、passage_id、claim、quote、citation | ✓ (Songti SC) | keep |
| `SourceReferenceCard` | 来源文献卡片（`.esrc-card`、`.esrc-link`） | source_ref_id、title、Reader href (`/library/{did}?passage={pid}`) | — | keep |
| `LineageStatusBadge` | 来源完整性徽章 | lineage 状态 | — | keep |
| `ResearchResultErrorState` | 无证据/错误状态 | 错误信息 + 重试 | — | keep |

**关键链路**：`CitationPanel` → 点击 → `EvidenceDetail`（同 trace_id/passage_id）→ `SourceReferenceCard`（source_ref_id + Reader href）→ 真实 click → Library Reader。

### 7.5 Empty / Loading / Error / Skeleton 状态

**事实源**：`EmptyState.vue`、`LoadingState.vue`、`ErrorState.vue`、`HfbSkeleton.vue`、`HfbAlert.vue`、`ResearchResultErrorState.vue`、`AnalysisPendingState.vue`

| 状态 | 通用组件 | 页面专用变体 | 处置 |
|---|---|---|---|
| Empty | `EmptyState`、`PlaceholderPage` | — | keep |
| Loading | `LoadingState`、`HfbSkeleton` | `AnalysisPendingState`（Workflow） | keep |
| Error | `ErrorState`、`HfbAlert` | `ResearchResultErrorState`（Workflow 无证据） | keep |
| 分析中 | — | `AnalysisPendingState`（Workflow 等待 LLM） | keep |

---

## 8. `@hfb/ui` 共享包

**事实源**：`packages/ui/src/index.ts`

```ts
/**
 * @hfb/ui — Shared UI Component Library
 * This package will contain shared Vue 3 components.
 * Components will be built out during Sprint 7.
 */
export {};
```

**状态**：空壳。无组件、无 token、无导出。B 阶段若启用需规划搬迁。

---

## 9. 依赖与工具链

**事实源**：`apps/frontend/package.json`

| 类别 | 依赖 | 版本 |
|---|---|---|
| 框架 | `vue` | ^3.5.0 |
| 路由 | `vue-router` | ^4.5.0 |
| 状态 | `pinia` | ^2.3.0 |
| HTTP | `axios` | ^1.7.0 |
| i18n | `vue-i18n` | ^10.0.0 |
| 图谱 | `vis-network` / `vis-data` | ^10.1.0 / ^8.0.3 |
| 构建 | `vite` | ^6.0.0 |
| TypeScript | `typescript` | ^5.7.0 |
| 测试 | `vitest`、`@vue/test-utils`、`jsdom`、`playwright` | 见 package.json |
| 类型检查 | `vue-tsc` | ^2.2.0 |
| **图标库** | **无** | — |
| **CSS 框架** | **无**（纯 CSS custom properties） | — |
| **CSS utility** | **无**（Tailwind/UnoCSS/Windi 均未安装） | — |

---

## 10. 汇总 — B 阶段处置清单（仅记录，不修改）

| 序号 | 项 | 类别 | 优先级 |
|---|---|---|---|
| 1 | 引入 `--font-serif` / `--font-classical` token | 古籍 typography token | B3 |
| 2 | 统一 4 处硬编码宋体为 token 引用 | drift 消除 | B3 |
| 3 | `lang` 感知中西文混排（行高/字间距） | 古籍 typography | B3 |
| 4 | 图标库选型（B2 决策文档） | 图标 | B2 |
| 5 | 图标组件封装 + 无障碍 label | 图标 | B3 |
| 6 | 按钮 icon slot 类型约束 | 组件契约 | B3 |
| 7 | 统一 Search/Filter 基础组件 | pattern 统一 | **C1-1 ✓**（HfbToolbar + Reports 已适配） |
| 8 | 统一 Card 基础组件（3→1） | pattern 统一 | C1-2 |
| 9 | 统一 Table 实现（HfbTable vs DataTable） | drift 消除 | C1-2 |
| 10 | `pinia-plugin-persistedstate` 替代手写 | 状态持久化 | 可选 |
| 11 | 跨标签页 store 同步 | 状态持久化 | 可选 |
| 12 | 古籍图标集（卷/页/版本/校勘/异文） | 图标 | B2/B3 |
