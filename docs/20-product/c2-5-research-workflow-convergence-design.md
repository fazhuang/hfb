# C2-5: Research Workflow 高保真收敛 — 设计规约

**日期:** 2026-08-04
**分支:** master（当前 HEAD: 5c6ab5d）
**前置:** C2-4 PASS

## 目标

优化 Research Workflow 页面组的信息层级、步骤导航、主操作优先级、进度与状态反馈、响应式行为。不得改变研究流程状态机、任务触发语义或证据链。

## 白名单

- `apps/frontend/src/pages/research/ResearchWorkflowPage.vue`
- `apps/frontend/src/components/research/workflow/ResearchQuestionStep.vue`
- `apps/frontend/src/components/research/workflow/DocumentSelectionStep.vue`
- `apps/frontend/src/components/research/workflow/EvidenceReviewStep.vue`
- `apps/frontend/src/components/research/workflow/ResearchReportStep.vue`
- `apps/frontend/src/components/research/workflow/AnalysisPendingState.vue`
- `apps/frontend/src/components/research/workflow/WorkflowStepNavigation.vue`
- `apps/frontend/src/__tests__/research-workflow-page.test.ts`
- `docs/20-product/UI_ASSET_LEDGER.md`（仅新增/修改 UI 资产记录）

## 禁止

- 修改后端接口、数据持久化、路由定义、RBAC 权限策略及 V4 API 契约
- 修改 Workspace、Reports、Library、Reader、Result/Evidence/SourceRef、Knowledge Explorer 相关非 Workflow 专用组件或全局 Store
- 改变 Pinia Store 中的 Workflow 状态机推进逻辑、API 触发函数
- 使用本地缓存、Mock 伪造或 URL 串改替代真实后端会话

## 必须保持

- 真实项目上下文、研究会话、步骤状态与 API 数据的双向同步
- 完整交互节点：研究问题输入、键盘提交、文档多选、分析等待、失败重试、空状态及完成态
- 既有的 Workflow → Result / Reports 跨页面导航语义与路由参数传递

---

## Section 1: Bug 修复（Priority 2）

### 1.1 AnalysisPendingState — timer 泄漏

**问题:** `setInterval` 在 `active` 变为 false 后仍运行（仅不增量），组件卸载时也未清理。

**修复:**

- `watch(() => props.active, (val) => { if (!val) stopTimer() })`
- `onUnmounted(() => stopTimer())`
- `stopTimer()` 清 interval 并设 `timer = null`

**文件:** `AnalysisPendingState.vue`

### 1.2 WorkflowStepNavigation — submitting guard

**问题:** `submitting` prop 已声明但 `isStepClickable()` 未使用。提交中用户可通过鼠标点击或键盘 Enter/Space 触发 step-change。

**修复:**

- `isStepClickable(idx)` 增加 `if (props.submitting) return false` 作为第一行
- 按钮元素已有 `:disabled`，但额外在函数层防御，覆盖键盘路径

**文件:** `WorkflowStepNavigation.vue`

### 1.3 EvidenceReviewStep — 序号颜色

**问题:** `.ers-item-index` 使用 `--color-error-light-text`（红色），但序号不是错误。

**修复:** 改为 `var(--color-text-secondary)`

**文件:** `EvidenceReviewStep.vue`

---

## Section 2: 响应式行为（Priority 1）

### 统一断点: 640px

新增 `@media (max-width: 640px)` 到各 step 组件，与 WorkflowStepNavigation 已有断点一致。

### 2.1 ResearchQuestionStep

- 提交按钮 `width: 100%` (<=640px)

### 2.2 DocumentSelectionStep

- 操作按钮行（返回 + 提交）由 `flex-direction: row` 切换为 `column`
- 两个按钮 `width: 100%`，提交按钮在前（视觉优先级），返回按钮在后

### 2.3 AnalysisPendingState

- 内容已居中 `max-width: 480px`，375px 下安全
- 仅减少左右 padding

### 2.4 EvidenceReviewStep

- 摘要栏（证据计数 + CTA）切换为纵向排列
- 证据条目内边距减半
- 引用代码块：`overflow-wrap: anywhere`（不用 `word-break: break-all`，保留可读性）
- `<pre>` 已有 `white-space: pre-wrap`，补充 `overflow-x: auto`

### 2.5 ResearchReportStep

- 统计行（evidence count / citation count / artifact ID）添加 `flex-wrap: wrap; gap: var(--space-2)`
- 操作按钮行已有 `flex-wrap: wrap`，验证 gap 间距
- `<pre>` 报告预览：`overflow-wrap: anywhere; overflow-x: auto`

### 2.6 ResearchWorkflowPage — 错误横幅

- <=640px 时切换为纵向排列（当前仅 <=768px 处理）
- 错误消息与操作按钮上下堆叠，按钮 `width: 100%`

### 2.7 200% Zoom 验证

在 1280px 视口 200% 缩放下实测：

- ResearchWorkflowPage 及所有 step 的 `scrollWidth <= clientWidth`
- 所有按钮可点击，焦点环可见
- Tab 键顺序正确
- 如 overflow: hidden 需添加到 body 包装器则添加（参考 C2-4 Reports 页修复）

---

## Section 3: Design Token 一致性（Priority 3）

### 规则

仅替换有精确等值 token 的硬编码值。不强制映射不等值。

### 字体尺寸映射

| 硬编码 | Token         | 等值?       |
| ------ | ------------- | ----------- |
| `12px` | `--text-xs`   | 精确 (12px) |
| `13px` | `--text-sm`   | 精确 (13px) |
| `14px` | `--text-base` | 精确 (14px) |
| `16px` | `--text-lg`   | 精确 (16px) |
| `20px` | `--text-xl`   | 精确 (20px) |
| `22px` | `--text-2xl`  | 精确 (22px) |
| `24px` | `--text-3xl`  | 精确 (24px) |

**保留不替换：** `11px`、`15px`、`18px` — 无精确 token。标注 `# ponytail: add --text-2xs (11px), --text-md (15px), --text-2xl (18px) when typography token grid fills out`。

### 间距映射

所有硬编码 margin/padding px 均有精确 `--space-*` token：

| px   | Token          |
| ---- | -------------- |
| 4px  | `--space-1`    |
| 5px  | `--space-1-25` |
| 6px  | `--space-1-5`  |
| 8px  | `--space-2`    |
| 10px | `--space-2-5`  |
| 12px | `--space-3`    |
| 14px | `--space-3-5`  |
| 16px | `--space-4`    |
| 18px | `--space-4-5`  |
| 20px | `--space-5`    |
| 24px | `--space-6`    |

### 保留不替换

- `border-width`: 1px / 2px / 3px
- `width` / `height` 尺寸: 24px circle
- `max-width` / `max-height`
- 定位值

### 新增 Token: `--font-serif`

```css
--font-serif: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
```

添加到 `apps/frontend/src/styles/tokens/typography.css`，与已有 `--font-sans` / `--font-mono` 并列。

### 字体族引用修复

- `.ers-quote-text`: 硬编码 serif stack → `var(--font-serif)`
- `.ers-item-source`: `font-family: monospace` → `var(--font-mono)`

---

## Section 4: Icon 一致性（Priority 4）

替换 emoji 为 `@lucide/vue` 图标。项目已有 `^1.24.0`。

| 数量 | Emoji | Lucide          | 文件                  | 位置                   |
| ---- | ----- | --------------- | --------------------- | ---------------------- |
| 1    | ℹ️    | `Info`          | DocumentSelectionStep | 系统提示               |
| 1    | ⚠️    | `AlertTriangle` | EvidenceReviewStep    | 空证据警告             |
| 1    | ⚠️    | `AlertTriangle` | EvidenceReviewStep    | 世系不完整警告         |
| 1    | ⚠️    | `AlertTriangle` | ResearchReportStep    | 未持久化报告警告       |
| 1    | 🔍    | `Search`        | ResearchReportStep    | "基于报告重新搜索"按钮 |
| 1    | 📄    | `FileText`      | ResearchReportStep    | 报告卡片               |

**跳过:** ResearchWorkflowPage 传给 EmptyState 的 `icon="🔍"` — EmptyState 组件不在白名单内。

**规范:**

- `:size` 匹配周围文字 (16px / 18px)
- `aria-hidden="true"`
- 颜色通过 CSS `color` 继承或显式设置为 `var(--color-text-secondary)` / `var(--color-warning-text)`

---

## Section 5: Step 过渡动画（Priority 5）

### CSS-only fade transition

```css
.step-fade-enter-active,
.step-fade-leave-active {
  transition: opacity var(--transition-base) var(--ease-out);
}

.step-fade-enter-from,
.step-fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .step-fade-enter-active,
  .step-fade-leave-active {
    transition: none;
  }
}
```

### 实现

- 在 ResearchWorkflowPage.vue 中用 `<Transition name="step-fade" mode="out-in">` 包裹 `v-if`/`v-else-if` step 链
- `mode="out-in"` 不影响焦点管理：`watch` + `nextTick` 焦点在 step 挂载后执行

### Token

- `--transition-base`: 0.15s（已有）
- `--ease-out`: ease-out（已有）

---

## 验收标准

### 自动化

```bash
cd apps/frontend
npx eslint                    # 零错误
npx vue-tsc --noEmit          # 零新错误
npx vitest run                # 42 workflow 测试全部通过
```

### 手动浏览器验证

| 断点                | 验收项                                                 |
| ------------------- | ------------------------------------------------------ |
| 375×812 (移动端)    | 无溢出/截断/重叠，所有按钮可点击                       |
| 1280×800 (桌面端)   | 正常布局，无退化                                       |
| 1280×800, 200% zoom | `scrollWidth <= clientWidth`，焦点环可见，Tab 顺序正确 |

### 状态节点验证

- 研究问题输入 + 键盘提交
- 文档多选提交
- 分析等待（elapsed time 递增，离开页面后停止，组件卸载后清理）
- 错误横幅（纵向排列，数据取自 API 错误）
- 证据审查（空状态、证据展示、引用保存、世系警告）
- 报告（预览、导航按钮、未持久化警告）

### 代码规范

- 无直接 hex 色值
- 无新增 `any` 类型
- 提交中 submitting guard 覆盖鼠标 + 键盘

---

## 提交约束

- 一个原子提交
- 不推送
- 不改写历史
