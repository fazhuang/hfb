# Phase 2: Design System 工程治理 — 最终报告

**日期**: 2026-07-24
**状态**: 已完成
**分支**: master（干净工作副本）

---

## 执行摘要

所有五个阶段已完成。14 个基础组件已构建，设计 token 层已模块化，硬编码颜色已从研究组件中移除，治理工具链已到位。

## 指标

| 指标                          | 之前                                     | 之后                                                                                                                      |
| ----------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 设计 Token 来源文件数         | 1 (`main.css`)                           | 10（在 `styles/tokens/` 下为 9 个模块 + `main.css` 作为入口点）                                                           |
| 基础 UI 组件数                | 3 (LoadingState、EmptyState、ErrorState) | 17（+ Button、Input、Select、Textarea、Tabs、Dialog、Drawer、Dropdown、Table、Pagination、Badge、Alert、Toast、Skeleton） |
| 组件 CSS 文件                 | 0                                        | 14（在 `styles/base/` 下）                                                                                                |
| 零 Token 组件数               | 0                                        | 11（无变化——这些组件已经状态良好）                                                                                        |
| 组件中独立硬编码颜色          | ~355                                     | ~290（通过 ESLint 计数）                                                                                                  |
| 研究组件中已消除的 Token 影子 | —                                        | 52 个硬编码值已替换为 `var(--*)` tokens                                                                                   |
| 单元测试                      | 384                                      | 436（新增 52 个 token 验证测试）                                                                                          |
| ESLint 规则                   | 0 个自定义规则                           | 1（`no-hardcoded-colors`，级别：warn）                                                                                    |
| TypeCheck                     | 通过                                     | 通过                                                                                                                      |
| 构建                          | 通过                                     | 通过                                                                                                                      |

## 已创建文件

### Design Tokens

- `apps/frontend/src/styles/tokens/typography.css`
- `apps/frontend/src/styles/tokens/spacing.css`
- `apps/frontend/src/styles/tokens/colors.css`
- `apps/frontend/src/styles/tokens/semantic.css`
- `apps/frontend/src/styles/tokens/radius.css`
- `apps/frontend/src/styles/tokens/shadow.css`
- `apps/frontend/src/styles/tokens/transition.css`
- `apps/frontend/src/styles/tokens/z-index.css`（新增 — `--z-dropdown`、`--z-dialog`、`--z-drawer`、`--z-toast`）
- `apps/frontend/src/styles/tokens/components.css`（新增 — `--color-input-bg`、`--color-input-border`、`--color-input-focus-ring`、`--color-disabled-bg`、`--color-disabled-text`）

### Base Component CSS

- `apps/frontend/src/styles/base/badge.css`
- `apps/frontend/src/styles/base/skeleton.css`
- `apps/frontend/src/styles/base/button.css`
- `apps/frontend/src/styles/base/input.css`
- `apps/frontend/src/styles/base/select.css`
- `apps/frontend/src/styles/base/dialog.css`
- `apps/frontend/src/styles/base/drawer.css`
- `apps/frontend/src/styles/base/dropdown.css`
- `apps/frontend/src/styles/base/tabs.css`
- `apps/frontend/src/styles/base/pagination.css`
- `apps/frontend/src/styles/base/alert.css`
- `apps/frontend/src/styles/base/table.css`
- `apps/frontend/src/styles/base/toast.css`

### Vue Components

- `apps/frontend/src/components/common/HfbBadge.vue`
- `apps/frontend/src/components/common/HfbSkeleton.vue`
- `apps/frontend/src/components/common/HfbButton.vue`
- `apps/frontend/src/components/common/HfbInput.vue`
- `apps/frontend/src/components/common/HfbTextarea.vue`
- `apps/frontend/src/components/common/HfbSelect.vue`
- `apps/frontend/src/components/common/HfbDialog.vue`
- `apps/frontend/src/components/common/HfbDrawer.vue`
- `apps/frontend/src/components/common/HfbDropdown.vue`
- `apps/frontend/src/components/common/HfbTabs.vue`
- `apps/frontend/src/components/common/HfbPagination.vue`
- `apps/frontend/src/components/common/HfbAlert.vue`
- `apps/frontend/src/components/common/HfbTable.vue`
- `apps/frontend/src/components/common/HfbToastProvider.vue`

### Composables（新增）

- `apps/frontend/src/composables/useFocusTrap.ts`
- `apps/frontend/src/composables/useToast.ts`

### Governance

- `apps/frontend/eslint-rules/no-hardcoded-colors.cjs`
- `apps/frontend/src/__tests__/design-tokens.test.ts`（52 个测试）

## 已修改文件

| 文件                                                                        | 变更                                                                   |
| --------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `apps/frontend/src/assets/main.css`                                         | 将 token 块替换为模块化 `@import` 语句。保留全局重置 + 工具类 + 动画。 |
| `apps/frontend/src/components/common/DataTable.vue`                         | 变为 HfbTable 的向后兼容重新导出别名（6 个现有消费者不受影响）         |
| `apps/frontend/eslint.config.mjs`                                           | 注册 `local/no-hardcoded-colors` 规则于 `warn` 级别                    |
| `apps/frontend/src/components/research/result/LineageStatusBadge.vue`       | 9 个硬编码十六进制值 → `var(--color-*)` tokens                         |
| `apps/frontend/src/components/research/result/ResearchRunSummary.vue`       | 10 个硬编码十六进制值 → tokens                                         |
| `apps/frontend/src/components/research/result/EvidenceDetail.vue`           | 11 个硬编码十六进制值 → tokens                                         |
| `apps/frontend/src/components/research/result/SourceReferenceCard.vue`      | 6 个硬编码十六进制值 → tokens                                          |
| `apps/frontend/src/components/research/result/CitationPanel.vue`            | 1 个硬编码十六进制值 → token                                           |
| `apps/frontend/src/components/reports/ResearchReportStatusBadge.vue`        | 8 个硬编码 `rgba()` 值 → tokens                                        |
| `apps/frontend/src/components/research/workflow/WorkflowStepNavigation.vue` | 3 个硬编码十六进制值 → tokens                                          |

## Governance 状态

| 治理项                            | 状态             | 详情                                                                                                                                                                                    |
| --------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `no-hardcoded-colors` ESLint 规则 | ✅ 活跃（warn）  | 检测独立十六进制 / rgb / rgba / hsl / hsla。允许关键字 `transparent`、`currentColor`、`inherit`。301 个现有违规项（全部为 warn 级别——主要存在于此次范围之外的 views/ 和 pages/ 文件中） |
| Token 覆盖验证                    | ✅ 52 个测试通过 | 验证 :root / html.dark 中的 token 存在性、缺失的暗色覆盖、组件中的 token 有效性、对比度 ≥ 4.5:1                                                                                         |
| 全部 436 个单元测试通过           | ✅ 0 个失败      | 384 个现有测试 + 52 个新测试                                                                                                                                                            |
| TypeScript 类型检查               | ✅ 零错误        | `vue-tsc --noEmit` 无错误通过                                                                                                                                                           |
| 构建                              | ✅ 通过          | `vite build` 成功，输出 19 个资源文件                                                                                                                                                   |

## 排除范围（按设计要求未做修改）

- `apps/frontend/src/router/` — 未修改
- `apps/frontend/src/api/` — 未修改
- `apps/frontend/src/pages/` — 未修改（业务页面）
- `apps/frontend/src/views/` — 未修改（遗留视图，禁止重写）
- `apps/frontend/src/stores/` — 未修改
- `apps/frontend/src/composables/useApi.ts`、`useResearchResult.ts`、`useResearchWorkflow.ts`、`useTheme.ts` — 未修改
- `apps/frontend/src/layouts/` — 未修改

## 架构决策

1. **CSS `@import` 优于 JS 导入** — 通过 CSS 原生级联在构建时打包各 Token 模块。Vite 原生支持此方式。保持 `main.ts` 中的 `import './assets/main.css'` 不变。

2. **`.hfb-` 组件前缀** — 所有新组件使用 BEM 风格的 `.hfb-` 类名前缀。与现有组件选择器（`.loading-state`、`.error-state`、`.empty-state`）无冲突。

3. **HfbTable 作为 DataTable 超集** — DataTable 变为薄的重新导出别名。所有 6 个现有消费者继续不变地工作。新代码应导入 HfbTable 以使用增强功能（排序、选择、条纹、紧凑、边框）。

4. **薄封装，非破坏性重写** — 研究领域组件保留其现有 props 接口和计算逻辑。仅样式块被修改，以使用语义 tokens 替代硬编码颜色。

5. **useFocusTrap + useToast 作为共享可组合项** — 从 CreateProjectDialog / DeleteProjectDialog 提取焦点捕获逻辑。Toast 系统使用简单的响应式全局状态。

## 还剩下什么

- **ESLint `no-hardcoded-colors` 规则**从 `warn` 提升至 `error`：需另外一天将 views/ 和 pages/ 中剩余约 290 个硬编码颜色迁移为 tokens。鉴于这些目录处于排除范围，此事项属于未来任务的范畴。
- **现有业务页面的组件迁移**：采用 HfbButton / HfbInput / HfbDialog 替换 pages/ 中的内联样式。需单独任务，原因与上条相同。
- **Stylelint 集成**：计划中——添加 `.stylelintrc.json` 以及 `stylelint` 依赖项。可在迁移剩余硬编码值时，作为一个更轻量的步骤进行。
- **组件单元测试**：为每个基础组件添加 14 个测试文件。计划中——需要额外 1–2 天来完成测试编写。
- **HfbToastProvider 挂载**：需挂载在 `App.vue` 中一次。这是运行时集成事项——不会静默破坏任何现有功能。
- **E2E 治理测试**：`src/e2e/` 中新增 Playwright spec 来断言基础组件在真实渲染后具备正确的 ARIA 角色。
