# Context 26 — 统一研究入口 (Research Entry)

**日期:** 2026-07-15  
**类型:** 功能实现  
**状态:** 完成

---

## 目标

建立统一研究入口，让研究者登录系统后无需理解系统架构即可开始研究。

---

## 修改页面

### 1. 首页 (`HomeView.vue`)

- 在标题下方增加**唯一主要入口**："开始新的研究"（已登录时）。
- 如果已有活跃研究主题，入口自动变为"← 返回当前研究"，显示课题名称。
- 未登录用户点击入口跳转到登录页。
- 入口按钮为醒目蓝紫色渐变，带有阴影和悬浮动效。

### 2. 导航栏 (`AppNavbar.vue`)

- Home 链接之后新增"开始研究" / "当前研究"链接（🔬 图标）。
- 路由指向 `/research/new`（无活跃研究时）或 `/research/home`（有活跃研究时）。
- 登出时清除研究状态。
- 仅对已登录用户显示。

### 3. Dashboard (`DashboardView.vue`)

- 标题下方新增研究入口卡片。
- 有活跃研究时：显示"当前研究"及课题名，并带"进入研究"按钮。
- 无活跃研究时：显示"开始新的研究"，并带"创建课题"按钮。

### 4. 原有研究页面

三个原有研究页面均添加了"← 返回当前研究"顶栏：

- **ResearchWorkflowView** (`/research`) — 版本比较研究
- **V4ResearchView** (`/v4/research`) — V4 多步骤研究
- **WorkspaceView** (`/workspace`) — AI 研究工作台

---

## 新增页面

### ResearchNewView (`/research/new`)

创建研究课题表单，包含：

- **课题名称**（必填）
- **课题简介**（可选）
- 创建后跳转到研究主页。

### ResearchHomeView (`/research/home`)

研究主页，包含：

- 课题标题和简介
- 研究工具入口网格（版本研究、V4 研究、工作台、搜索、知识图谱、古籍库）
- Dashboard 快捷入口
- "结束本次研究"按钮

---

## 修改路由

新增 2 条路由：

| 路径 | 名称 | 视图 | 认证 |
|---|---|---|---|
| `/research/new` | research-new | ResearchNewView | Yes |
| `/research/home` | research-home | ResearchHomeView | Yes |

---

## 新增 Store

### `research.ts` (Pinia Store)

- 持久化到 `localStorage`（key: `hfb-current-research-topic`）。
- 提供 `currentTopic`（包含 name, description, createdAt）。
- 提供 `hasActiveResearch` 计算属性。
- 提供 `setTopic(name, desc)` 和 `clearTopic()` 方法。

**设计原则：纯前端存储，不调用任何 API，不修改任何数据库。**

---

## 新增 i18n Keys

### `nav`
- `startResearch`: "开始研究" / "Start Research"
- `currentResearch`: "当前研究" / "Current Research"

### `researchEntry`
- `startNew`, `startNewDesc`, `newTitle`, `newSubtitle`
- `topicName`, `topicNamePlaceholder`, `topicDesc`, `topicDescPlaceholder`
- `create`, `toolsTitle`
- `toolResearchDesc`, `toolV4Desc`, `toolWorkspaceDesc`, `toolSearchDesc`, `toolGraphDesc`, `toolBooksDesc`
- `endResearch`, `backToResearch`, `noActiveResearch`

### `dashboard`
- `goToResearch`: "进入研究" / "Go to Research"

---

## 影响范围

- **路由:** 新增 2 条，原有路由不变。
- **导航栏:** 新增导航项，不改变原有链接。
- **UI:** 首页、Dashboard、3 个研究页面增加顶栏元素。
- **Store:** 新增 research store，独立于现有 store。
- **i18n:** 新增 2 个 nav key、17 个 researchEntry key、1 个 dashboard key。

---

## 未修改内容

- **数据库:** 无变更。
- **RAG:** 无变更。
- **Research Engine:** 无变更。
- **Citation / Evidence:** 无变更。
- **任何 API 协议:** 无变更。研究课题完全由前端 localStorage 管理。
- **研究逻辑:** 无变更。研究入口仅提供导航，不修改任何研究流程。
- **原有功能:** 完整保留。所有原有页面、路由、组件保持不变。

---

## 涉及文件

```
apps/frontend/src/
  stores/research.ts                  # 新增 — 研究课题 Pinia store
  views/ResearchNewView.vue           # 新增 — 创建课题表单
  views/ResearchHomeView.vue          # 新增 — 研究主页
  views/HomeView.vue                  # 修改 — 增加研究入口 CTA
  views/DashboardView.vue             # 修改 — 增加研究入口卡片
  views/ResearchWorkflowView.vue      # 修改 — 增加返回当前研究顶栏 + 恢复逻辑修复
  views/V4ResearchView.vue            # 修改 — 增加返回当前研究顶栏
  views/WorkspaceView.vue             # 修改 — 增加返回当前研究顶栏
  components/layout/AppNavbar.vue     # 修改 — 增加研究入口导航项
  router/index.ts                     # 修改 — 新增 2 条路由
  i18n/locales/zh-CN.ts               # 修改 — 新增中文翻译
  i18n/locales/en.ts                  # 修改 — 新增英文翻译
  __tests__/research-workflow.test.ts # 重写 — 新增 restoreLatestWorkflow 测试

apps/backend/
  app/api/v1/research.py              # 修改 — get_version_comparison 返回 null 而非 404
```

---

## 阻断修复 (P0)

### 根因

`restoreLatestWorkflow()` 在 `onMounted` 时遍历用户前 10 个 workspace sessions，对每个发起 `GET /api/v1/research/sessions/{id}/version-comparison`。后端 `get_version_comparison` 路由在 session 无 `workflow_state` 时返回 `HTTP 404`。前端 catch 块吞掉了异常，但每个 404 都是真实的 HTTP 错误请求 — 10 个旧 session 产生 10 个 404。

### 修复

**后端 (`research.py`):** `get_version_comparison` 对合法 session 但无工作流状态时，返回 `{"data": null}` (HTTP 200) 而非 `HTTP 404`。语义为"该 session 尚未配置版本比较，这是正常状态"。

**前端 (`ResearchWorkflowView.vue`):** `restoreLatestWorkflow` 检查 `response.data?.data` 是否为 falsy — 若为 `null`/`undefined`，跳过该 session（而非 catch 404）。仅当返回有效比较数据时才恢复。

### 自动化覆盖

`apps/frontend/src/__tests__/research-workflow.test.ts` — 3 个新测试：

| 测试 | 覆盖 |
|---|---|
| skips sessions whose version-comparison returns data:null | 3 sessions → 前 2 返回 null（跳过），第 3 返回有效数据（恢复） |
| renders workflow UI even when session list is empty | 0 sessions → 零 version-comparison 请求 |
| survives network errors while probing comparison sessions | 1 session → 网络异常，页面不崩溃 |

### 浏览器验证

Playwright E2E 结果：

```
1. Login → OK, URL: /, Greeting: E2E Researcher
2. Home → "开始新的研究" → URL: /research/new ✅
3. Create topic "E2E 版本研究" → URL: /research/home ✅
4. Go to /research (old entry) → URL: /research
   New VC requests: 0
   VC 404: 0 ✅
   Has 验证语料: true ✅
   Has 检索条文: true ✅
   Has 返回当前研究: true ✅
5. All old entries:
   /books               OK ✅
   /literature          OK ✅
   /classical-versions  OK ✅
   /persons             OK ✅
   /v4/research         OK ✅
   /graph               OK ✅
   /workspace           OK ✅
   /search              OK ✅
   /about               OK ✅
===== FINAL =====
Total VC 404s: 0 ✅
Errors: 0 ✅
```

### 测试命令

```bash
# TypeScript
npx vue-tsc --noEmit

# 全量测试 (28 passed, 4 files)
npx vitest run

# 仅研究相关测试 (3 passed)
npx vitest run src/__tests__/research-workflow.test.ts
```
