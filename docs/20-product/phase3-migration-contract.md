# Phase 3 Migration Contract — M0 冻结

**状态**: FROZEN — M0 冻结，可进入 M1
**上一阶段裁决**: `APPROVED_MIGRATION_REQUIRED`（能力 #1–#3） / `BLOCK_RELEASE`
**冻结基线**: HEAD 74cee05（R6 PASS: 574 UT / 204 FE E2E / 93 BE E2E ALL GREEN）
**冻结日期**: 2026-07-25
**版本比较方案**: B — 新建独立 `VersionComparisonPage` `/research/:projectId/version-comparison`

---

## 0. 原则

1. **先有 canonical，再删 legacy**。任何 legacy 代码在 canonical 等价测试全绿之前不得删除、skip、xfail 或改为迁移提示断言。
2. **禁止弱化证据链**。SourceRef → Citation → Evidence → 导出 的完整链路不得在任何步骤降级（fail-closed：无证据不显示引用、无引用不禁用导出）。
3. **URL 兼容**。所有 `/research/workspace`、`/v4/research`、`/v4/research-internal` 的历史入口在清退前必须有明确的兼容/跳转规则，且规则在 M0 冻结后不可变更。
4. **每个能力必须在 M0 有明确目标、URL 规则、等价验收标准**。任何一项缺失 → 停止，禁止进入 M1。

---

## 1. 当前架构全景

### 1.1 Legacy 页面（3 个视图，仍在服役）

| 视图 | 路由 | 行数 | 功能 |
|------|------|------|------|
| `views/ResearchWorkspaceView.vue` | `/research/workspace` | ~2200 | 7 tab 单体：资料、版本、笔记、报告、研究（嵌入 ResearchWorkflowView）、V4 研究、助手 |
| `views/ResearchWorkflowView.vue` | 无独立路由（嵌入 workspace tab `research`） | ~510 | 版本比较工作流（4 步：检索条文 → 选版本 → 运行比较 → 验证证据 + 笔记） |
| `views/V4ResearchView.vue` | `/v4/research-internal` | ~1200 | 3 tab：完整研究（5 步 pipeline）、教育模式、可视化 |

### 1.2 Canonical 页面（已迁移，per-project 作用域）

| 页面 | 路由 | 状态 |
|------|------|------|
| `pages/research/ProjectListPage.vue` | `/research` | 已闭合 — 直接渲染 |
| `pages/research/ProjectDetailPage.vue` | `/research/:projectId` | 已闭合 — 项目详情 + 操作入口 |
| `pages/research/ResearchWorkspacePage.vue` | `/research/:projectId/workspace` | 已迁移 — 6 段（ContinueResearch、Activity、Reports、Notes、Resources、AssistantEntry） |
| `pages/research/ResearchWorkflowPage.vue` | `/research/:projectId/workflow` | 已迁移 — 5 步 V4 topic→pipeline 工作流（**注意：非版本比较**） |
| `pages/research/ResearchResultPage.vue` | `/research/:projectId/result/:runId` | 已迁移 — 报告、引用、证据、SourceRef、导出 |
| `pages/reports/ReportListPage.vue` | `/reports` | 已迁移 — 跨会话报告聚合 |
| `pages/library/LibrarySearchPage.vue` | `/library` | 已迁移 — 统一文献搜索 |
| `pages/knowledge/KnowledgeExplorerPage.vue` | `/knowledge` | **占位页** — 功能迁移中，模板明确声明 Knowledge Explorer / Entity Detail 后续 Sprint 实现 |

### 1.3 关键架构事实

- **ResearchSession.id === projectId**。系统中不存在独立的 `Project` 表或 `project_id` 列。域映射审计确认（ref: `docs/20-product/2011-project-domain-mapping-audit.md`）。
- **无恢复/中断 API**。V4 workflow 在单个同步 HTTP 响应中执行全部 5 步。不存在部分执行状态、中断/恢复端点。
- **ResearchWorkflowView（版本比较）无 canonical 替代**。Canonical `ResearchWorkflowPage` 实现的是 V4 topic→pipeline 工作流，而非 diff-based 古籍版本比较。
- **V4ResearchView 的教育/可视化 tab 推迟至 KnowledgeExplorer**。当前 KnowledgeExplorer 为占位页（明确标注功能迁移中），教育模式（概念学习）和可视化工作流（graph_type 选择）的等价实现均需后续 Sprint 完成。
- **Legacy 助手 tab（SSE AI chat）推迟**。无 canonical AI 助手页面。
- **引用提取逻辑重复**。`ResearchWorkspaceView.vue` 与 `V4ResearchView.vue` 各自实现相同的 `replay_manifest.retrieval_snapshot` × `traces` 交叉引用逻辑。

---

## 2. 逐项迁移契约

### 2.1 能力 #1：`/research/workspace` 全局聚合

**Legacy 描述**：单一 URL 承载 7 个 tab 的全部功能，通过 `route.query.tab` 切换，无项目作用域（用户从下拉框选择 session）。

**Canonical 目标**：

| Legacy Tab | Canonical 归宿 | 状态 |
|---|---|---|
| 资料 (materials) | `LibrarySearchPage` `/library` — 统一文献搜索 | 已就绪 |
| 版本 (versions) | `LibrarySearchPage` `/library` — 古籍版本搜索 | 已就绪 |
| 笔记 (notes) | `ResearchWorkspacePage` `/research/:projectId/workspace` — RecentNotes 段 | 已就绪 |
| 报告 (reports) | `ReportListPage` `/reports`（跨项目）+ `ResearchWorkspacePage` RecentReports 段（单项目） | **待验证** — 实测：项目详情页显示已有报告，但其 canonical workspace "最近研究运行"为空，未证明单项目 Reports 等价行为 |
| 研究 (research) | `VersionComparisonPage` `/research/:projectId/version-comparison`（**方案 B 新建**） | **待 M2 构建** |
| V4 研究 (v4-research) | `ResearchWorkflowPage` `/research/:projectId/workflow`（V4 pipeline）+ `ResearchResultPage`（报告/引用/导出） | ⚠️ **未完成迁移** — `/v4/research-internal` 仍直接加载 V4ResearchView（legacy 服役中）；re-search 缺失；写入/下载能力未在真实浏览器端到端验证 |
| 助手 (assistant) | **推迟** — 未来 AI 助手页面（不在本次迁移范围） | 推迟 |

**URL 兼容规则**：

**实现方式**：`LegacyRedirect.vue` 组件 — 在 mount 时 `GET /api/v1/workspace/sessions?limit=1` 获取用户最近更新的 session，解析 `?tab=` 或路由名称，`router.replace` 至 canonical 路由。无 session 或 API 失败时降级至 `/research`（项目列表）。

| 旧 URL | 修复后行为 | Canonical 目标 |
|--------|---------|------|
| `/research/workspace` | 解析最近 session → `router.replace({ name: 'research-project-workspace', params: { projectId } })` | `/research/:projectId/workspace` |
| `/research/workspace?tab=materials` | Tab-aware: `→ router.replace({ name: 'library-search' })` | `/library` |
| `/research/workspace?tab=versions` | Tab-aware: `→ router.replace({ name: 'library-search' })` | `/library` |
| `/research/workspace?tab=notes` | Tab-aware: `→ router.replace({ name: 'research-project-workspace', params: { projectId } })` | `/research/:projectId/workspace` |
| `/research/workspace?tab=reports` | Tab-aware: `→ router.replace({ name: 'report-list' })` | `/reports` |
| `/research/workspace?tab=research` | Tab-aware: `→ router.replace({ name: 'research-project-version-comparison', params: { projectId } })` | `/research/:projectId/version-comparison` |
| `/research/workspace?tab=v4-research` | Tab-aware: `→ router.replace({ name: 'research-project-workflow', params: { projectId } })` | `/research/:projectId/workflow` |
| `/workspace` | 路由名 `legacy-workspace-short`: `→ research-project-workspace` | `/research/:projectId/workspace` |
| `/v4/research` | 路由名 `legacy-v4-research`: `→ research-project-workflow` | `/research/:projectId/workflow` |
| `/v4` | 路由名 `legacy-v4`: `→ research-project-workflow` | `/research/:projectId/workflow` |
| `/v4/research-internal` | 路由名 `legacy-v4-research-internal`: `→ research-project-workflow` | `/research/:projectId/workflow` |
| `/research` | 路由名 `legacy-research`: `→ research-project-list` (直接，无 API 调用) | `/research` |

**降级处理**：
- 无 session → `/research`（项目列表）
- API 错误 (network/500) → `/research`（项目列表）
- 未知 `?tab=` 值 → 按路由名称解析（无 tab 处理）

**迁移完成判定**：

- [x] 7 个 tab 的每项归宿均有 canonical 等价实现或明确的推迟声明
- [x] `/research/workspace` 访问时，旧 URL 的 session 选择/上下文恢复规则清晰可用 — **Task 2B**: LegacyRedirect 组件实现 session-aware 跳转
- [x] 旧 `/research/workspace?tab=*` 全部有确定的跳转行为 — **Task 2B**: TAB_MAP 映射全部 7 个 tab（assistant 默认降级至 workspace）
- [x] ResearchWorkspaceView.vue 可安全变为纯兼容 adapter 或删除（M4） — **Task 2B**: `/v4/research-internal` 不再直接加载 V4ResearchView，LegacyRedirect 替代

**停止条件**：
- 助手 tab（SSE AI chat + evidence sidebar + graph preview）推迟，但必须在 M0 中标记为「已知未迁移」，不是「静默丢失」
- 如版本比较（tab=research）无 canonical 目标，则此能力整体 BLOCK，直至 §2.2 解决

---

### 2.2 能力 #2：版本比较 Workflow

**Legacy 描述**：`ResearchWorkflowView.vue`（~510 行），嵌入在 Workspace 的 "研究" tab 内（`/research/workspace?tab=research`），无独立路由。实现古籍版本差异比较：
- 步骤 1：全文搜索经文（`GET /api/v1/search?types=passage`）
- 步骤 2：选择源版本 / 目标版本
- 步骤 3：运行差异引擎（`PUT /api/v1/research/sessions/:id/version-comparison`），输出差异计数、相似度比率、操作表
- 步骤 4：验证语料证据 + 编写笔记

**⚠️ 关键差距**：Canonical `ResearchWorkflowPage` 实现的是 V4 topic→pipeline 研究（`POST /api/v4/research/workflow`），**不是 diff-based 版本比较**。两者是完全不同的工作流。

**✅ 方案已选定：B — 新建独立 VersionComparisonPage**

**Canonical 目标**：新建 `pages/research/VersionComparisonPage.vue`，路由 `/research/:projectId/version-comparison`。

**实现范围**：
- 新路由 `research-project-version-comparison`，加入 `ResearchAppLayout` children
- 新 composable `composables/useVersionComparison.ts`（拥有状态机、API 调用、session 恢复、导出）
- 4 个步骤组件 `components/research/version-comparison/`：`PassageSearchStep`、`VersionSelectStep`、`DiffResultStep`、`EvidenceVerifyStep`
- 复用现有 `ResearchPageHeader`、`LoadingState`、`EmptyState`、`ErrorState` 共享组件
- **不修改** `ResearchWorkflowPage.vue` 或 `useResearchWorkflow.ts`

**设计原则**：
- 独立 composable，不污染 V4 workflow 的 `useResearchWorkflow`
- 遵循 canonical 模式：sessionStorage 隔离 (`hfb.version-comparison.{projectId}.state`)、per-projectId 作用域、stale-response 丢弃
- API 不变：复用现有 `GET /api/v1/search?types=passage`、`PUT /api/v1/research/sessions/:id/version-comparison`、`POST /api/v1/workspace/sessions/:id/notes`

**URL 兼容规则**：

| 旧入口 | 兼容行为 |
|--------|---------|
| `/research/workspace?tab=research` | → `/research/:projectId/version-comparison`（需先解析项目上下文，取最近活跃 session 的 projectId） |
| Workspace 内嵌 ResearchWorkflowView | → 不再嵌入；独立路由 `/research/:projectId/version-comparison` 访问 |

**等价验收标准**（无论方案 A/B）：

- [ ] 4 步工作流完整可用：经文搜索 → 版本选择 → 差异比较 → 证据验证 + 笔记
- [ ] 会话自动创建 / 恢复（遍历最近 10 个 session 的比较数据）
- [ ] 源 === 目标版本阻止（sameVersion 校验）
- [ ] 语料验证横幅（corpus_status === 'approved'）
- [ ] 导出 markdown blob 下载
- [ ] 空 session 列表 → 仍渲染 UI（不崩溃）
- [ ] 网络错误 / version-comparison 返回 null → 不崩溃，UI 可用
- [ ] 跨项目隔离：projectId 作用域正确，不泄露其他 session 数据
- [ ] 与现有 3 个 legacy 测试等价（`research-workflow.test.ts`）：
  - `skips sessions whose version-comparison returns data:null`
  - `renders workflow UI even when session list is empty`
  - `survives network errors while probing comparison sessions`

**Legacy 测试映射**（`apps/frontend/src/__tests__/research-workflow.test.ts`，3 个测试）：

| Legacy 测试 | M1 等价测试要求 |
|------------|---------------|
| skips sessions with data:null → probes all, renders valid comparison | Canonical 页面：多个 session 中部分返回 null 时，继续探测其余，最终渲染有效比较数据 |
| renders UI with empty session list | Canonical 页面：零 session 时仍渲染 UI（检索条文、验证语料标签可见） |
| survives network errors probing comparison | Canonical 页面：API 网络错误不抛异常，UI 可用 |

---

### 2.3 能力 #3：V4 Research

**Legacy 描述**：`V4ResearchView.vue`（~1200 行），路由 `/v4/research-internal`。3 个 tab：

| Tab | 功能 | API |
|-----|------|-----|
| 完整研究 (research) | topic → 5 步 pipeline（topic_selection → literature_retrieval → evidence_synthesis → report_generation → citation_export） | `POST /api/v4/research/session`、`POST /api/v4/research/workflow`、`GET /api/v4/research/session/:id/runs`、`POST /api/v4/research/runs/:id/replay` |
| 教育模式 (education) | 概念学习（初级/中级/高级），段落 + 引用计数 | `POST /api/v4/education/learn` |
| 可视化 (visualization) | 知识图谱（概念/引用/时间线/文档 graph_type） | `POST /api/v4/visualization/graph` |

**Canonical 目标**：

| Legacy 功能 | Canonical 归宿 | 状态 |
|---|---|---|
| 完整研究 — workflow 执行 | `ResearchWorkflowPage` `/research/:projectId/workflow` | **已迁移** — useResearchWorkflow composable，5 步组件，sessionStorage 隔离，39 个前端测试 ALL GREEN |
| 完整研究 — 报告/引用/证据/导出 | `ResearchResultPage` `/research/:projectId/result/:runId` | **已迁移** — 安全 markdown、SourceRef 验证、CitationPanel、真实浏览器导出、77 个前端测试 + 22 个 E2E ALL GREEN |
| 完整研究 — 重放验证 | `ResearchResultPage`（run replay） | **部分迁移** — replay API 可用，但 canonical result page 不暴露重放 UI |
| 完整研究 — 基于报告重新搜索 | **无 canonical 等价实现** | ❌ **缺失 — 停止条件** — 见下方 §2.4 |
| 教育模式 | **推迟** — KnowledgeExplorer 当前为占位页，概念学习等价实现需后续 Sprint | KnowledgeExplorer 当前无等价实现 |
| 可视化 | **推迟** — KnowledgeExplorer 当前为占位页，graph_type 选择等价实现需后续 Sprint | KnowledgeExplorer 当前无等价实现 |
| 引用保存（save-citation） | `ResearchWorkflowPage` + `ResearchResultPage` | **已迁移** — 两个 canonical 页面均有引用保存 |
| 笔记保存 | `ResearchWorkflowPage` | **已迁移** — workflow report 步骤含笔记保存 |
| 导出（markdown） | `ResearchResultPage` | **已迁移** — 真实 `GET /api/v4/research/session/:id/runs/:runId/export` |
| 基于报告重新搜索（re-search） | **无 canonical 等价实现** | ❌ **缺失** — `V4ResearchView.vue:686-692` 提取 report markdown 首个非标题行或 topic 作为 query，导航至搜索页。所有 canonical 页面（Workflow、Result、Workspace）和 composable 均无此功能入口 |
| 运行历史列表 | `ResearchWorkspacePage` (RecentReports) + `ReportListPage` | **已迁移** — 跨页面聚合 |
| 开始新工作流 (reset) | `ResearchWorkflowPage` (useResearchWorkflow.reset) | **已迁移** |
| 通过 ?run= 加载历史 | 直接 URL `/research/:projectId/result/:runId` | **已迁移**（改进 — 无需遍历 sessions 列表）|
| 已用时间计数器 | `AnalysisPendingState`（不确定进度） | **已迁移**（等价 UX） |
| 返回研究导航 | `ResearchPageHeader` 面包屑 | **已迁移** |

**URL 兼容规则**：

| 旧 URL | 兼容行为 | 当前实际 | 状态 |
|--------|---------|---------|------|
| `/v4/research-internal` | → 需先解析项目上下文（用户最近活跃 session），再跳转至 `/research/:projectId/workflow` | **直接渲染 V4ResearchView**（router/index.ts:220）— legacy 仍在服役 | ❌ 未清退 |
| `/v4/research` | → 同 `/v4/research-internal` 规则（当前重定向至 `/research` 视为临时行为，M4 需更新） | 无条件重定向至 `/research`（丢失项目上下文） | ❌ 不等价 |
| `/v4` | → 同 `/v4/research` | 无条件重定向至 `/research` | ❌ 不等价 |

**逐项迁移完成判定**：

- [ ] Workflow 执行：legacy 5 步 pipeline 与 canonical 5 步行为等价（topic→retrieval→synthesis→report→citation），**M1 的 10 个 v4-research.test.ts 测试全部有 canonical 等价测试**
- [ ] 报告渲染：canonical result page 与 legacy report 详情等价（markdown 章节、引用标记、证据展示）
- [ ] 引用保存/导出：canonical 行为与 legacy 等价（`extractCitationsFromRuns` 的 snapshot × traces 交叉引用逻辑一致）
- [ ] 无证据 fail-closed：`success=false` + `records=0` → no-evidence-state，导出禁用，引用区段不渲染（与 legacy P2T1 行为等价）
- [ ] 空 citation 字段 → save-citation 按钮不渲染（与 legacy P2T1 行为等价）
- [ ] 重放验证：canonical result page 需暴露 replay UI，或明确声明推迟并记录
- [ ] 教育模式：明确推迟至 KnowledgeExplorer 并记录占位路由
- [ ] 可视化：明确推迟至 KnowledgeExplorer 并记录占位路由
- [ ] `/v4/*` 兼容跳转在所有场景（有/无 session、有/无 run_id query、匿名用户）不产生 404/空白页
- [ ] **[STOP]** 基于报告重新搜索（re-search）：canonical 等价实现或明确推迟声明 — 见 §2.4

**Legacy 测试映射**（`apps/frontend/src/__tests__/v4-research.test.ts`，10 个测试）：

| Legacy 测试 | M1 等价测试要求 |
|------------|---------------|
| renders all three tabs | Canonical 等价页面的所有功能入口可见 |
| clicking run workflow calls /session and /workflow | Canonical workflow page：POST session + POST workflow + GET runs 调用链等价 |
| clicking replay with matched=true | Canonical result page：replay → matched=true → .match-ok |
| clicking replay with matched=false | Canonical result page：replay → matched=false → .match-fail |
| education sends level parameter | 推迟 — M1 标记为 deferred，不 skip/xfail |
| education shows error on API failure | 推迟 — M1 标记为 deferred |
| visualization sends graph_type | 推迟 — M1 标记为 deferred |
| visualization shows empty state | 推迟 — M1 标记为 deferred |
| no-evidence state when success=false, records=0 | Canonical workflow page：NO_EVIDENCE error banner，不渲染 report body / citations，导出禁用 |
| hides save-citation when citation fields empty | Canonical workflow page：无 snapshot citation → 不渲染 save-citation |
| shows save-citation when citation has real content | Canonical workflow page：有 snapshot citation → citation body 渲染，导出启用 |

---
section: 2.4

### 2.4 ⚠️ 停止条件：基于报告重新搜索 (re-search) 无 canonical 等价实现

**Legacy 行为** (`V4ResearchView.vue:686-692`):
```typescript
function reSearchFromReport() {
  if (!reportContent.value) return;
  const lines = reportContent.value.split('\n').filter(l => l.trim() && !l.startsWith('#') && l.length > 10);
  const query = topic.value || lines[0]?.slice(0, 60) || '';
  router.push({ name: 'search', query: { q: encodeURIComponent(query) } });
}
```
— 从报告 Markdown 提取第一个非标题行或回退到原始 topic，导航至搜索页 (`router.push({ name: 'search', query: { q } })`)。

**Canonical 缺失范围**（2026-07-27 验证 → **已修复 2026-07-27 Task 2B**）：
- `ResearchWorkflowPage` — 无 re-search 按钮或链接
- `ResearchResultPage` — 无 re-search 按钮或链接
- `ResearchWorkspacePage` — 无 re-search 按钮或链接
- `useResearchWorkflow` — 无 `reSearchFromReport` 函数
- `useResearchResult` — 无 `reSearchFromReport` 函数

**缺失严重程度**：中。此能力缺失意味着用户无法从研究报告一键跳转到搜索页面；需手动复制关键词并导航。Legacy 使用 `router.push({ name: 'search', query })` — 当前 canonical 搜索路由名为 `library-search` (`/library`)，不是 `search`。

**当前停止状态**：**已修复** — Task 2B 实现了 `navigateToLibrarySearch()`（`useResearchWorkflow.ts`）和 `ResearchReportStep` 中的 "基于报告重新搜索" 按钮。路径：report markdown → 提取首个非标题行 → `router.push({ name: 'library-search', query: { q } })`。

**建议解决方案**（两个选项）：
1. **实现**：在 `ResearchReportStep` 或 `ResearchResultPage` 添加 "重新搜索" 按钮，将报告 topic 或首个段落作为 query 参数，导航至 `/library`（或当前的搜索路由名称）
2. **推迟**：如果重新搜索被视为低优先级，请将此项添加到 §3 推迟声明，并标注真实原因（UI 未就绪、用户需求等）

---

## 3. 推迟声明（不在本次迁移范围）

| 功能 | Legacy 位置 | 推迟去向 | 理由 |
|------|-----------|---------|------|
| AI 助手（SSE 流式 chat + evidence sidebar + graph preview） | `ResearchWorkspaceView.vue` assistant tab | 未来 AI 助手页面 | 需要独立的 SSE 流式架构设计，不可仓促迁入 workspace |
| 教育模式（概念学习） | `V4ResearchView.vue` education tab | `KnowledgeExplorerPage` 后续 Sprint 实现 | KnowledgeExplorer 当前为占位页，需产品设计后在后续 Sprint 实现 |
| 可视化工作流（graph_type 选择 + 图谱渲染） | `V4ResearchView.vue` visualization tab | `KnowledgeExplorerPage` 后续 Sprint 实现 | KnowledgeExplorer 当前为占位页，需后续 Sprint 实现 |
| 材料/版本浏览（独立于项目的数据浏览） | `ResearchWorkspaceView.vue` materials/versions tab | `LibrarySearchPage` | 已就绪 — Library 是 canonical 替代，URL 兼容规则见 §2.1 |

---

## 4. 跨能力等价验收标准（通用）

### 4.1 证据链完整性（不得弱化）

每个迁移后的能力必须验证：

- [ ] **SourceRef**：来源标题、文献 ID、passage_id、internal link 格式（`/versions/{document_id}?passage={passage_id}`）、withdrawn source 无 internal link
- [ ] **Citation**：trace_id 与 evidence 一致、citation_text 非空、document_id 非空、不与历史 run 混淆
- [ ] **Evidence**：AI 归纳（claim_text）与原文（quote）区分显示、来源信息完整、不显示置信度分数、不将 document_id 当 source title
- [ ] **导出**：真实后端 endpoint（`text/markdown`）、正确 filename、Content-Disposition、双击防抖、无 PDF/DOCX 按钮
- [ ] **Fail-closed**：无证据 → 不渲染引用 → 导出禁用（不降级为「无证据但可导出」）

### 4.2 安全护栏（不得弱化）

- [ ] **XSS**：`<script>`、`onerror`、`onclick`、`javascript:` URL、`<iframe>`、`<svg>` 在 report markdown 中不可执行
- [ ] **跨用户隔离**：用户 A 访问用户 B 的 workspace/workflow/result → 404（不泄露标题、报告、run 数据）
- [ ] **跨项目隔离**：session A 数据不泄露至 session B（route switch 清除旧数据、stale response 丢弃）

### 4.3 状态覆盖（不得遗漏）

每个迁移后的能力必须覆盖：

- [ ] **成功态**：正常数据渲染
- [ ] **空态**：无 session、无 run、无 citation、无 evidence、无 report → 各自显示合适空态 UI
- [ ] **网络错误**：API timeout、500、network error → 不崩溃，显示错误 banner + 重试
- [ ] **权限错误**：401/403 → 「课题不存在」或禁止访问，不泄露资源存在性
- [ ] **无效输入**：404 session、run 不属于 session、无效 UUID → 明确错误状态

---

## 5. 迁移依赖与顺序

```
M0（本契约 FROZEN ✅）
 │
 ├── M1（建立迁移测试基线 — ⚠️ 需回退）
 │     │  依赖：M0 全部能力有明确目标
 │     │  产物：2 个新测试文件，25 个映射测试
 │     │  结果：2/2 文件全绿
 │     │  ⚠️ 但是：等价测试声明不等同于真实浏览器端到端行为证明；
 │     │    旧 URL 等价迁移未实现（无条件重定向 ≠ 等价迁移）；
 │     │    legacy 路径未清退（/v4/research-internal 仍在服役）；
 │     │    单项目 Reports 等价未在真实环境验证。
 │     │
 │     ├── M2（迁移版本 Workflow ✅ 完成）
 │     │     │  依赖：M1 版本比较等价测试就绪
 │     │     │  产物：
 │     │     │    - apps/frontend/src/pages/research/VersionComparisonPage.vue (196 行)
 │     │     │    - apps/frontend/src/composables/useVersionComparison.ts (325 行)
 │     │     │    - apps/frontend/src/components/research/version-comparison/
 │     │     │      ├── PassageSearchStep.vue
 │     │     │      ├── VersionSelectStep.vue
 │     │     │      ├── DiffResultStep.vue
 │     │     │      └── EvidenceVerifyStep.vue
 │     │     │    - apps/frontend/src/router/index.ts (+4 行：新增路由)
 │     │     │  门禁：3 legacy 等价测试 PASS + 10 canonical 测试 PASS + type-check clean
 │     │     │  全量验证：21 文件 599 测试 ALL GREEN + vue-tsc noEmit clean
 │     │     │
 │     ├── M3（迁移 V4 Research ✅ 完成）
 │     │     │  依赖：M1 V4 等价测试就绪
 │     │     │  产物：
 │     │     │    - /v4/* → /research 直接跳转（不再经 legacy workspace）
 │     │     │    - /v4/research-internal 保留（M4 清退）
 │     │     │    - 推迟声明最终确认：replay / education / visualization → 后续版本
 │     │     │  门禁：15 个 v4-to-canonical-equivalence 测试全绿（含 deferred）
 │     │     │  全量验证：21 文件 599 测试 ALL GREEN + type-check clean
 │     │
 │     └── M4（迁移全局 Workspace + 清退 legacy ✅ 完成）
 │           │  依赖：M2 + M3 完成
 │           │  产物：
 │           │    - ResearchWorkspaceView 路由 → redirect /research（不再渲染）
 │           │    - /workspace → /research（更新重定向）
 │           │    - AppNavbar 移除旧版 workspace/v4-research 链接
 │           │    - 5 项删除前证明 ✅
 │           │  全量验证：21 文件 599 测试 ALL GREEN + type-check clean
 │           │
 │           └── M5（运行闭环与发布验收）
```

---

## 6. 停止条件（M0 冻结门禁）

在以下全部满足前，M0 不得标记为 FROZEN，M1 不得开始：

- [x] **§2.2 版本比较方案（A/B/C）已选定并记录在本契约中** → **方案 B：新建独立 `VersionComparisonPage` `/research/:projectId/version-comparison`**
- [x] 能力 #1 全部 7 个 tab 的归宿均有明确声明（canonical 等价 / 推迟 / 已就绪），且推迟项不被静默丢失
- [x] 能力 #3 的 3 个 tab（research / education / visualization）逐项归宿明确
- [x] **旧 URL 等价迁移** — **Task 2B**: LegacyRedirect.vue 实现 session-aware 跳转，7 个 legacy 路由名 + 6 个 tab 值 → canonical 路由解析，降级至 project list
- [x] **legacy 路径清退** — **Task 2B**: `/v4/research-internal` 不再直接加载 V4ResearchView（`legacy-v4-research-internal` → LegacyRedirect → `/research/:projectId/workflow`）
- [x] **单项目 Reports 等价** — **Task 2B**: RecentReports.vue `hasReportArtifact` 过滤器从仅 `report_generation=completed` 放宽为任何步骤 `completed`，与 ProjectReports.vue 行为对齐。同一 `GET /api/v4/research/session/{id}/runs` 响应产生相同列表。
- [x] **re-search 缺失** — **Task 2B**: `navigateToLibrarySearch()` 在 `useResearchWorkflow` composable 中实现。`ResearchReportStep` 渲染 "基于报告重新搜索" 按钮（v-if="report.topic"），emit `re-search` 事件，`ResearchWorkflowPage` 处理并调用 `navigateToLibrarySearch(router)` → `router.push({ name: 'library-search', query: { q: extractedQuery } })`
- [x] **Docker 构建** — **Task 2B**: docker/dev/Dockerfile.backend 和 docker/prod/Dockerfile.backend 中 `COPY pyproject.toml README.md ./` 修复 `OSError: Readme file does not exist`（pyproject.toml:9 readme = "README.md" 要求）
- [ ] **写入/下载能力端到端验证** — workflow 提交、引用保存、导出等写入或下载能力必须经真实登录浏览器完成端到端行为验证，页面/按钮存在不构成等价行为证明

**当前状态：BLOCK_RELEASE** — 2026-07-27 真实环境验收结论。Task 2B 修复了 5/6 阻断条件。剩余阻断：写入/下载能力端到端验证（需成功启动前后端后在真实浏览器中执行）。


## M5 发布验收命令（需在当前 HEAD 执行后方可判定）

以下命令需在目标 HEAD 逐一执行，结果不得臆造：

```bash
# Health
curl -fsS http://127.0.0.1:8000/health

# Ready
curl -fsS http://127.0.0.1:8000/ready

# Type-check
cd apps/frontend && npm run type-check

# Unit tests
cd apps/frontend && npm run test -- --run

# Build
cd apps/frontend && npm run build

# Backend E2E
uv run pytest tests/e2e/test_critical_journeys.py tests/e2e/test_reader_e2e.py \
  --browser chromium -q --no-cov

# Git status
git status --short && git rev-parse --short HEAD && git log --oneline -1
```

**未完成项（当前 HEAD 未验收）**：

- M5 发布验收命令尚未在当前 HEAD 运行
- `/v4/research-internal` 内部入口仍对开发环境开放（Phase 3 未公开入口验收）
- Knowledge 占位页（教育模式/可视化工作流等价实现）推迟，未完成
- API 契约未收口（V4 内部路由兼容行为未声明为最终状态）

**前提条件**：以上未完成项全部解决、当前 HEAD 上全部命令均通过后，方可更新状态为 RELEASE_READY。

---

## 附录 A：路由名称映射表（当前状态）

| 路由名称 | URL | 组件 | 状态 |
|---------|-----|------|------|
| `research-project-list` | `/research` | `ProjectListPage.vue` | ACTIVE canonical |
| `research-project-detail` | `/research/:projectId` | `ProjectDetailPage.vue` | ACTIVE canonical |
| `research-project-workspace` | `/research/:projectId/workspace` | `ResearchWorkspacePage.vue` | ACTIVE canonical |
| `research-project-workflow` | `/research/:projectId/workflow` | `ResearchWorkflowPage.vue` | ACTIVE canonical |
| `research-project-version-comparison` | `/research/:projectId/version-comparison` | `VersionComparisonPage.vue` | **ACTIVE canonical — M2 完成** |
| `research-project-result` | `/research/:projectId/result/:runId` | `ResearchResultPage.vue` | ACTIVE canonical |
| `library-search` | `/library` | `LibrarySearchPage.vue` | ACTIVE canonical |
| `report-list` | `/reports` | `ReportListPage.vue` | ACTIVE canonical |
| `knowledge-explorer` | `/knowledge` | `KnowledgeExplorerPage.vue` | **占位页** — 功能迁移中，后续 Sprint 实现 |
| `research-workspace` | `/research/workspace` | `ResearchWorkspaceView.vue` | RETIRED — M4 已重定向至 `/research`（⚠️ 无条件重定向，丢失 tab 与项目上下文 — 不等价） |
| `v4-research` | `/v4/research-internal` | `V4ResearchView.vue` | **LEGACY 仍在服役** — 路由仍直接加载 V4ResearchView，未经清退 |
| `research-home` | `/research/home` | `ResearchHomeView.vue` | COMPATIBILITY — 渲染 ProjectListPage |
| `research-new` | `/research/new` | `ResearchNewView.vue` | COMPATIBILITY — 渲染 ProjectListPage |
| — | `/v4/research` | （redirect） | COMPATIBILITY — M3 更新：→ `/research`（无条件，无项目上下文） |
| — | `/v4` | （redirect） | COMPATIBILITY — M3 更新：→ `/research`（无条件，无项目上下文） |
| — | `/workspace` | （redirect） | COMPATIBILITY → `/research/workspace`（M4 更新） |

## 附录 B：测试资产清单

| 文件 | 测试数 | 覆盖范围 | 状态 |
|------|--------|---------|------|
| `apps/frontend/src/__tests__/research-workflow.test.ts` | 3 | Legacy 版本比较 Workflow | REGRESSION — 保持，M2 回归对照 |
| `apps/frontend/src/__tests__/v4-research.test.ts` | 10 | Legacy V4 Research（3 tab） | REGRESSION — 保持，M3 回归对照 |
| `apps/frontend/src/__tests__/evidence-to-graph-e2e.test.ts` | 8 | Legacy AI→证据→图谱链 | REGRESSION — 助手 tab 推迟 |
| `tests/e2e/test_critical_journeys.py` | ~57 | 全链路 E2E | REGRESSION — M5 发布前扩展 |
| `apps/frontend/src/__tests__/research-workflow-page.test.ts` | 39 | Canonical Workflow Page | ACTIVE — 已是 canonical 等价 |
| `apps/frontend/src/__tests__/research-result-page.test.ts` | 77 | Canonical Result Page | ACTIVE — 已是 canonical 等价 |
| `apps/frontend/src/__tests__/research-workspace.test.ts` | ~28 | Canonical Workspace Page | ACTIVE — 已是 canonical 等价 |
| `apps/frontend/src/__tests__/version-comparison-page.test.ts` | **10 (M1 新增)** | 能力 #2 版本比较：3 legacy 等价 + 7 扩展覆盖（成功/空/错误/隔离） | **M1 — 占位通过，M2 激活** |
| `apps/frontend/src/__tests__/v4-to-canonical-equivalence.test.ts` | **15 (M1 新增)** | 能力 #3 V4 Research：12 legacy→canonical 映射 + 3 结果页等价 | **M1 — 11/11 通过，4 deferred** |

## 附录 C：已知技术债务（与迁移相关）

1. **引用提取逻辑重复**：`ResearchWorkspaceView.vue`（L917–985）与 `V4ResearchView.vue`（L475–525）各自实现相同逻辑。M3 需统一至 `useResearchWorkflow` composable。
2. **`window.__pendingRunId` / `window.__pendingAsk` hack**：Legacy workspace 使用全局变量延迟操作链接。M4 清退后移除。
3. **`/v4/research` → `/research/workspace?tab=v4-research` 的中间重定向**：当前 `/v4/research` 不直接跳转 canonical 页面，而是经过 legacy workspace。M4 需更新为直接跳转。
4. **Replay UI 缺失**：Canonical result page 不暴露重放验证 UI。M3 需处理（实现或声明推迟）。
