# C2-1: ResearchWorkspacePage 高保真收敛设计

**日期**: 2026-08-03
**状态**: 设计已确认，待 Codex PASS
**上下文**: C1-1（HfbToolbar + Reports 适配）、C1-2（Citation 编号统一 + 身份链 E2E）已完成

## 目标

优化 Workspace 页面组的信息层级、操作优先级、留白、状态反馈和响应式行为。

## 硬约束

- 禁止修改研究流程、引文逻辑、后端和 V4
- 禁止修改现有 API 端点签名与返回值结构
- 375×812 与 200% zoom 验证
- 键盘、焦点、加载/空态/错误重试
- 真实登录、真实 API、项目隔离

---

## 1. 白名单文件

所有路径以仓库根 `/Users/likeming/Sites/hfb/` 为基准。

| 操作 | 完整路径 |
|------|----------|
| 修改 | `apps/frontend/src/pages/research/ResearchWorkspacePage.vue` |
| 删除 | `apps/frontend/src/components/research/ContinueResearchCard.vue` |
| 修改 | `apps/frontend/src/components/research/RecentReports.vue` |
| 删除 | `apps/frontend/src/components/research/RecentResearchActivity.vue` |
| 修改 | `apps/frontend/src/components/research/RecentNotes.vue` |
| 修改 | `apps/frontend/src/components/research/ResearchResources.vue` |
| 修改 | `apps/frontend/src/components/research/ResearchAssistantEntry.vue` |
| 更新 | `apps/frontend/src/__tests__/research-workspace.test.ts` |
| 后续新建 | `apps/frontend/src/utils/fetchWithRetry.ts`（本卡不创建，仅预约路径） |

文件净变更: 1 删除 + 6 修改 + 0 新建（本卡不创建 fetchWithRetry）。

---

## 2. 组件职责与数据所有权

### ResearchWorkspacePage.vue — 唯一数据与状态所有者

- 拥有 session 详情的**唯一请求**（`GET /api/v1/workspace/sessions/{id}`）
- 拥有合并研究列表的**唯一请求**（并发 `runs` + `history`，归一化为 `MergedResearchItem[]`）
- 拥有笔记的**唯一请求**（`GET /api/v1/workspace/sessions/{id}/notes`）
- 拥有引文的**唯一请求**（`GET /api/v1/workspace/sessions/{id}/citations`）
- 通过 props 向下传递 data、loading、error 与 retry 回调
- 统一管理所有异步取消与过期响应防护（reqId 递增模式）

### RecentReports.vue — 受控展示组件

- Props:
  - `projectId: string`
  - `items: MergedResearchItem[]`（合并归一化后的列表）
  - `loading: boolean`
  - `error: string | null`
- Emits: `retry`
- 标题固定为"最近研究"
- **不发起任何 API 请求**
- **不持有 `onMounted` / watch 自动请求逻辑**
- 列表项展示逻辑如下:
  - `type === 'run'`：显示 topic、step_execution_trace 步骤条、"查看"链接（仅 completed 步骤）
  - `type === 'activity'`：显示 query_text、类型 badge、引用计数

### RecentNotes.vue — 受控展示组件

- Props:
  - `notes: NoteItem[]`
  - `loading: boolean`
  - `error: string | null`
- Emits: `retry`
- **不发起任何 API 请求，不持有 `onMounted` fetch**
- 移除当前 `watch(props.projectId)` 自动请求与 `fetchNotes` 内部方法
- 展示最多 5 条笔记，UI 布局不变

### ResearchResources.vue — 受控展示组件

- Props:
  - `citations: ResearchCitationSummary[]`
  - `loading: boolean`
  - `error: string | null`
- Emits: `retry`
- **不发起任何 API 请求，不持有 `onMounted` fetch**
- 移除当前 `watch(props.projectId)` 自动请求与 `fetchResources` 内部方法
- 展示最多 5 条引文，UI 布局不变

### ResearchAssistantEntry.vue — 多模式入口组件

新增 `mode` prop，定义三种呈现契约：

```typescript
type RAEIMode = 'inline' | 'sidebar' | 'sheet';
```

| mode | 触发条件 | 布局行为 |
|------|----------|----------|
| `'inline'` | 空项目（全局空态） | 嵌入引导卡内部，不渲染独立侧边栏 |
| `'sidebar'` | 桌面端非空项目 (width >= 769px) | 可折叠 300px 侧边栏，默认折叠 |
| `'sheet'` | 移动端非空项目 (width <= 768px) | 底部 slide-up panel，toggle 打开，带 backdrop |

Props:
- `projectId: string`
- `mode: RAEIMode`

组件自行根据 `mode` 切换呈现。不保留独立的 `onMounted` 请求逻辑（现有 `sessionStorage` 读写保留）。

### 职责边界图

```
ResearchWorkspacePage (唯一数据所有者)
├── session: fetch once (404/403 gate)
├── runs + history: Promise.allSettled → MergedResearchItem[]
├── notes: Promise.allSettled → NoteItem[]
├── citations: Promise.allSettled → ResearchCitationSummary[]
│
├── Header (actions slot) — CTA 由 emptiness 决定显隐
├── WelcomeCard (空项目时) — 内嵌 ResearchAssistantEntry[mode='inline']
│
├── RecentReports (受控) ← items, loading, error props
├── RecentNotes (受控) ← notes, loading, error props
├── ResearchResources (受控) ← citations, loading, error props
└── ResearchAssistantEntry[mode='sidebar'|'sheet'] (非空项目时)
```

### 不变更

- 所有 API 端点签名、返回值结构不变
- 研究流程逻辑不变
- 引文逻辑不变
- V4 路由不变

---

## 3. CTA 规则

### 空项目 CTA

**判定**：全局空态 = `MergedResearchItem[]` 为空 **AND** `notes[]` 为空 **AND** `citations[]` 为空 **AND** 三个 section 均无未解决 error。

空项目时:

1. **Header 中"开始新研究"按钮隐藏**。
2. **Header 中"查看课题详情"按钮保留**。
3. **主内容区显示引导卡**（WelcomeCard），作为唯一主行动入口:
   ```
   🚀 开始您的研究
   提出研究问题，系统将自动检索古籍文献并生成循证报告。
   [输入您的研究问题...] [开始研究]       ← ResearchAssistantEntry mode='inline'
   或
   [进入完整工作流]                       ← router-link /research/{id}/workflow
   ```
4. 引导卡内"开始研究"按钮: 将问题写入 sessionStorage → 导航到 `/research/{id}/workflow`（与现有 ResearchAssistantEntry 行为一致）。
5. 引导卡内"进入完整工作流": 次级样式（outline button），直接导航到 `/research/{id}/workflow`。

### 非空项目 CTA

非空项目时:

1. **Header 恢复"开始新研究"主 CTA**（router-link 到 `/research/{id}/workflow`）。
2. 引导卡不渲染。
3. 侧边栏 ResearchAssistantEntry 以 `mode='sidebar'`（桌面）或 `mode='sheet'`（移动）呈现。

### CTA 互斥表

| 全局空态 | Header "开始新研究" | 引导卡 | 侧边栏 AI 助手 |
|----------|---------------------|--------|----------------|
| true | 隐藏 | 显示 (mode='inline') | 隐藏 |
| false | 显示 | 隐藏 | 显示 (mode='sidebar' 或 'sheet') |

---

## 4. 合并研究列表数据契约

### MergedResearchItem

```typescript
interface MergedResearchItem {
  id: string;            // run.run_id 或 activity.query_id
  type: 'run' | 'activity';
  title: string;         // run.topic 或 activity.query_text
  timestamp: string;     // ISO 8601，归一化排序键
  // type === 'run' 专属:
  stepTrace?: Array<{ name: string; status: string }>;
  runId?: string;        // 用于构造查看链接
  // type === 'activity' 专属:
  queryType?: string;
  citationCount?: number;
}
```

### 归一化规则

**runs 归一化** (`history` 端点数据优先于 `runs` 端点):

1. 从 `runs` 端点取 `run_id`, `topic`, `started_at`, `completed_at`, `step_execution_trace`。
2. 若同一条 `run_id` 在 history 中也出现，以 history 中的 `created_at` 覆盖 timestamp。
3. `timestamp` 取值优先级: `history.created_at` > `run.completed_at` > `run.started_at` > 空字符串。

**history 归一化**:

1. 从 history 端点取 `query_id`, `query_text`, `query_type`, `citation_count`, `created_at`。
2. `timestamp` 取值优先级: `created_at` > 空字符串。

**无有效时间戳处理**：`timestamp` 为空字符串的条目排到列表末尾（`DESC` 排序中空字符串排最后）。

**合并排序**：

```typescript
const merged = [...runItems, ...activityItems]
  .sort((a, b) => {
    if (!a.timestamp && !b.timestamp) return 0;
    if (!a.timestamp) return 1;   // 空排最后
    if (!b.timestamp) return -1;
    return b.timestamp.localeCompare(a.timestamp);  // DESC
  })
  .slice(0, 5);
```

RecentReports.vue 通过 `items` prop 接收已合并排序截断的列表，**不在组件内部再次排序或过滤**。

**标题固定**：RecentReports section 标题固定为"最近研究"（替换现有"最近研究运行"）。

---

## 5. Feedback-First：加载、错误、重试

### 5.1 加载流程

```
route.params.projectId 变化
  │
  ├─ 1. 取消所有进行中请求 (reqId 递增)
  ├─ 2. 重置所有 section 状态为 { data: [], loading: true, error: null }
  ├─ 3. 显示全页面骨架屏 (hfb-skeleton)
  │
  ├─ 4. 发起 session 请求 (gate)
  │     ├─ 404 → 停止，显示 EmptyState "课题不存在"
  │     ├─ 403 → 停止，显示 ErrorState "权限不足"
  │     └─ 200 → 继续
  │
  ├─ 5. session gate 通过后，并发发起:
  │     Promise.allSettled([
  │       fetchRuns(),        // GET /api/v4/research/session/{id}/runs
  │       fetchHistory(),     // GET /api/v4/research/session/{id}/history?limit=5
  │       fetchNotes(),       // GET /api/v1/workspace/sessions/{id}/notes
  │       fetchCitations(),   // GET /api/v1/workspace/sessions/{id}/citations
  │     ])
  │
  ├─ 6. 所有 Promise settled (resolve 或 reject)
  │     ├─ 骨架屏已显示 >= 300ms → 立即显示内容
  │     └─ 骨架屏显示 < 300ms → 继续显示直到满 300ms，再显示内容
  │
  └─ 7. 判断全局空态 → 引导卡或分区内容
```

**关键原则**:
- 骨架屏最短时长 **不得延迟首个请求发起**。请求在步骤 4、5 立即发出，与骨架屏渲染并行。步骤 6 的"满 300ms"仅在内容切换时机生效。
- Session gate 失败（404/403）时**不发起**步骤 5 的任何请求。

### 5.2 骨架屏 (Skeleton)

使用现有 `hfb-skeleton` CSS 组件体系（`apps/frontend/src/styles/base/skeleton.css`）。

**桌面端 (>= 769px)**:

```
┌──────────────────────────────────────────────────────┐
│ ████████████████████  ██████████                      │  ← header 行
├──────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────┐ │
│ │ ██████████████████████████████                    │ │  ← section 1 标题
│ │ ┌──────────────────────────────────────────────┐ │ │
│ │ │ ████████████████████████                      │ │ │  ← 卡片 1
│ │ │ ██████████████                                │ │ │
│ │ └──────────────────────────────────────────────┘ │ │
│ │ ┌──────────────────────────────────────────────┐ │ │
│ │ │ ██████████████████████████████                │ │ │  ← 卡片 2
│ │ │ ██████████                                    │ │ │
│ │ └──────────────────────────────────────────────┘ │ │
│ │ ┌──────────────────────────────────────────────┐ │ │
│ │ │ ██████████████████                            │ │ │  ← 卡片 3
│ │ └──────────────────────────────────────────────┘ │ │
│ └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

**移动端 (375px)**:
- 骨架屏使用 `var(--space-4)` 水平内边距
- 卡片宽度 100%，不对最小宽度作假设
- 侧边栏区域不渲染骨架（始终隐藏）

**200% zoom**:
- 骨架屏不设固定宽度，以 `%` 或 flex 填充
- 文本行高度用 `em`，随 zoom 等比例缩放
- 卡片间距用 `var(--space-*)` token

### 5.3 并发与过期响应防护

**reqId 递增模式**（页面级）:

```typescript
let pageReqId = 0;

async function loadAll() {
  const myReqId = ++pageReqId;
  // ... 发起 session 请求 ...
  // 每个 .then() / catch() 中检查: if (myReqId !== pageReqId) return;
}

// 路由切换时:
watch(() => route.params.projectId, () => {
  pageReqId++;    // 使旧请求的所有回调失效
  loadAll();
});

// 组件卸载时:
onBeforeUnmount(() => {
  pageReqId += 1_000_000;  // 使所有回调永久失效
});
```

**子组件过期防护**: 由于子组件不再自行请求，过期响应防护集中在页面层。子组件仅在 props 变化时被动重渲染。

### 5.4 局部失败与重试

**允许局部失败**: `Promise.allSettled` 后，每个 section 独立判断。

| 场景 | 行为 |
|------|------|
| 某个 section rejected | 该 section 显示 error banner + "重试"按钮；其他成功 section 正常展示 |
| 所有 section rejected | 显示全页错误状态（非引导卡），含汇总错误消息 + "重新加载"按钮 |
| 某个 section 返回空数据 | 视为成功，参与全局空态判定 |

**重试范围**: 重试仅作用于**幂等 GET 读取请求**。不重试 session gate 失败（session 404/403 为终止条件）。

**重试策略** (per-section):

```
maxRetries = 3
delays = [1000ms, 2000ms, 4000ms]  // 指数退避

retry(section):
  attempt++
  await sleep(delays[attempt - 1])
  re-fetch that section's endpoint
  if success → merge data, clear error
  if fail && attempt < 3 → retry again
  if fail && attempt === 3 → show persistent error + "联系支持"
```

**重试取消**: 用户切换项目、手动刷新页面、或组件卸载时，所有进行中的退避计时器必须取消（`clearTimeout`），新的加载周期重置所有 attempt 计数器。

### 5.5 fetchWithRetry helper（后续实施）

预约路径: `apps/frontend/src/utils/fetchWithRetry.ts`

预期签名:
```typescript
function fetchWithRetry(
  fetcher: () => Promise<AxiosResponse>,
  options?: { maxRetries?: number; delays?: number[]; signal?: AbortSignal }
): Promise<AxiosResponse>
```

本设计卡**不创建该文件**。实施卡中按需创建。

---

## 6. 错误与空态规则

### 6.1 终止 gate

- Session 404 → 停止一切后续请求，显示 EmptyState "课题不存在"
- Session 403 → 停止一切后续请求，显示 ErrorState "权限不足"

### 6.2 全局空态判定

**判定时机**: 所有 section 请求完成（`Promise.allSettled` settled）**且**骨架最短时长已满足后。

**判定条件**（三个条件必须同时满足）:
1. `MergedResearchItem[]` 为空（合并归一化后）
2. `notes[]` 为空
3. `citations[]` 为空

**且**三个 section 均无未解决 error（若某个 section 有 error 但其他有数据，不触发全局空态）。

**全局空态 → 引导卡**（见第 3 章）。

**非全局空态 → 分区布局**，含数据的 section 正常展示，全空的 section 可显示各 section 内置 empty 提示。

### 6.3 全失败 ≠ 引导卡

若所有 section 请求均失败（全部 rejected），**不得**将失败伪装为引导空态。

全失败时:
- 不渲染引导卡
- 不渲染分区 section
- 显示全页错误状态: 汇总错误消息 + "重新加载"按钮（重新触发完整加载流程）

---

## 7. 测试策略

### 测试文件

`apps/frontend/src/__tests__/research-workspace.test.ts`

### 需新增的测试用例

**Batch A — CTA 互斥**:
1. 全局空态: Header "开始新研究" 不渲染
2. 非空项目: Header "开始新研究" 渲染
3. 全局空态: 引导卡渲染，内嵌 ResearchAssistantEntry mode='inline'
4. 非空项目: 引导卡不渲染
5. 引导卡"进入完整工作流"链接指向正确路由

**Batch B — 受控子组件契约**:
6. RecentNotes 不自行发起 API 请求（mock API，验证调用次数为 0）
7. ResearchResources 不自行发起 API 请求
8. RecentNotes 通过 props 接收 loading/error/data，响应 props 变化
9. ResearchResources 通过 props 接收 loading/error/data，响应 props 变化
10. RecentNotes emit retry 事件触发页面级重试

**Batch C — 归一化排序与截断**:
11. MergedResearchItem 合并 runs + activities，最多 5 条
12. 时间戳 DESC 排序，无时间戳条目排最后
13. run 类型与 activity 类型字段归一化正确

**Batch D — 并发与过期响应防护**:
14. session 404 后不再发起 section 请求
15. session 403 后不再发起 section 请求
16. 路由切换时旧请求回调不覆盖新页面数据
17. 组件卸载后无状态写入

**Batch E — 骨架屏与最短时长**:
18. 骨架屏在初始加载时渲染
19. 请求在 300ms 内完成时骨架仍显示满 300ms
20. 请求超过 300ms 时完成后立即切换内容

**Batch F — 局部失败与重试**:
21. 单个 section 失败不影响其他 section 展示
22. per-section 重试按钮可见且可触发
23. 3 次重试失败后显示持久错误
24. 用户切换项目后重试计数器重置
25. 全失败场景显示汇总错误而非引导卡

**Batch G — 删除组件残留引用**:
26. ContinueResearchCard 不再被导入或渲染
27. RecentResearchActivity 不再被导入或渲染
28. ResearchWorkspacePage 不再渲染已删除组件的标签

### 需保留/修改的现有测试

- 合并截面测试（`projectId === ResearchSession.id`、类型映射等）保留原逻辑
- AI assistant 的 sessionStorage 隔离测试保留，适配 mode prop

### 需删除的测试

- ContinueResearchCard 独立测试（合并到页级测试 Batch A）
- RecentResearchActivity 独立测试（合并到页级测试 Batch C）

### E2E 验收要求（不可 mock）

以下场景必须以真实登录、真实 API、真实项目隔离方式验证：
- 空项目引导卡显示 → 输入问题 → 导航到 workflow
- 非空项目 → 引导卡隐藏 → 内容 section 显示
- 375×812 竖屏 → 侧边栏模式切换
- 200% zoom → 内容不溢出、可读
- 键盘 Tab 遍历所有交互元素 → Enter/Space 激活
- 错误模拟或真实断网 → section error + retry → 恢复后内容显示
- 项目 A/B 切换 → 数据隔离、无交叉污染

---

## 8. 不纳入范围

- `ProjectNotes.vue` — 非 Workspace 子组件
- `ResearchWorkspaceView.vue` — 旧 tab-based workspace，非本次优化目标
- `formatDate` 提取为共享 util — 触及 8+ 个非 workspace 文件
- 后端 API 修改、V4 路由、研究流程逻辑
- 国际化的新 i18n key（用内联中文，后续统一提取）
- `apps/frontend/src/utils/fetchWithRetry.ts` 创建（本卡仅预约路径）
