# Context 29 — 前端去技术化语言审计报告

**日期**: 2026-07-16
**范围**: `apps/frontend/src/**` 全部 `.vue` / `.ts` / `.js` + i18n 双语文件
**原则**: 后台 API 字段名 / 数据库列名保持不变；仅改前端面向用户的显示文字

---

## 概览：六项术语命中矩阵

| 术语 | 命中页面数 | 严重程度 | 说明 |
|------|-----------|---------|------|
| **RAG** | 7 | 🔴 高 | 遍布文献管理、研究工作台、管理后台 |
| **Vector (向量)** | 1 | 🟡 中 | 仅 About 页技术栈卡片 |
| **Chunk (分块)** | 1 | 🟡 中 | 管理后台采集动作标签 |
| **Embedding** | 0 | 🟢 无 | 前端源码无命中 |
| **Evidence (证据)** | 7 | 🔴 高 | 大量使用，含 technical sense 和 domain sense |
| **Groundedness** | 1 | 🟢 低 | 仅英文 i18n 中 1 处 "grounded" |

---

## 逐页详细审计

### 1. AboutView.vue — 关于页面

**命中术语**: RAG, Vector

| 行号 | 原文 | 问题 | 建议替换 |
|------|------|------|---------|
| 12 | `构建知识图谱、语义检索与 AI 辅助研究平台` | "语义检索" 是技术术语 | `全文检索与 AI 辅助研究平台` |
| 47 | `向量检索 + RAG` | 两个技术术语连用 | `智能文献检索` |

**备注**: 第 12 行的 "语义检索" 不算在本次六项中，但属于同类去技术化范围。

---

### 2. LiteratureListView.vue — 文献列表页

**命中术语**: RAG

| 行号 | 原文 | 问题 | 建议替换 |
|------|------|------|---------|
| 21–25 | `<select v-model="ragFilter">…RAG 状态…RAG 已启用…RAG 未启用` | 筛选下拉框全部显示 RAG | 替换为 `智能检索`：`— 智能检索 —` / `已启用` / `未启用` |
| 100 | `{ key: 'rag_enabled', label: 'RAG', … }` | 表格列头显示 RAG | label 改为 `智能检索` |

**变量名**: `ragFilter` 无需改名（JS 内部变量，用户不可见）。

---

### 3. LiteratureDetailView.vue — 文献详情页

**命中术语**: RAG

| 行号 | 原文 | 问题 | 建议替换 |
|------|------|------|---------|
| 54 | `RAG 状态` | 字段标签 | `智能检索` |
| 55 | `✅ 已启用` / `⛔ 未启用` | — | 保持不变 |
| 119 | `<h4>RAG</h4>` | 管理面板区块标题 | `智能检索` |
| 121 | `启用 RAG` | 按钮文字 | `启用智能检索` |
| 122 | `禁用 RAG` | 按钮文字 | `停用智能检索` |
| 252 | `'RAG 已启用'` / `'RAG 已禁用'` | 操作反馈消息 | `智能检索已启用` / `智能检索已停用` |

**变量名**: `ragLoading`, `ragMsg`, `ragOk`, `toggleRag()` 无需改名。

---

### 4. LiteratureReviewQueue.vue — 全文审核队列

**命中术语**: RAG

| 行号 | 原文 | 问题 | 建议替换 |
|------|------|------|---------|
| 86 | `{ key: 'rag_enabled', label: 'RAG', … }` | 表格列头 | label 改为 `智能检索` |

---

### 5. IngestionTasksView.vue — 采集任务管理

**命中术语**: RAG, Chunk

| 行号 | 原文 | 问题 | 建议替换 |
|------|------|------|---------|
| 63 | `'chunk_delete'` | Action 常量（面向前端 label） | 对应 label 见下行 |
| 65 | `chunk_delete: '分块删除'` | "分块" 即 Chunk | `删除已处理片段` |
| 65 | `rag_disabled: 'RAG 禁用'` | RAG 技术术语 | `停用智能检索` |

---

### 6. WorkspaceView.vue — 旧版工作台

**命中术语**: RAG, Evidence (domain sense)

| 行号 | 原文 | 问题 | 建议替换 |
|------|------|------|---------|
| 103 | `<!-- Right Panel: AI Assistant + Evidence -->` | 注释 | 注释无需改动 |
| 142–151 | `evidence` / `证据面板` / `evidenceHint` / `evidence-item` 等 | "证据面板" 在中文中可接受，但偏学术/法律腔 | 中文 `引用来源` 更平实 |
| 267 | `use_rag: true` | JS 请求体字段 | **不改**（后台 API 字段） |

**中文 i18n 涉及条目** (zh-CN.ts):

| 行号 | key | 原文 | 建议 |
|------|-----|------|------|
| 156 | `workspace.evidence` | `证据面板` | `引用来源` |
| 157 | `workspace.evidenceHint` | `AI 回答后将在此显示引用来源` | 已够平实，可保留 |

**CSS class**: `.evidence-item`, `.evidence-type`, `.evidence-text` 等无需改名（用户不可见）。

---

### 7. ResearchWorkspaceView.vue — 统一研究主页（主力页面）

**命中术语**: RAG, Evidence (大量)

#### 模板层

| 行号 | 原文 | 问题 | 建议替换 |
|------|------|------|---------|
| 291–298 | `section.evidence_ids` / `evidence-label` / `evidence-pill` / `openEvidenceInGraph` | 关联证据标签和按钮 | CSS 类名不改；按钮提示文字用中文 |
| 463–501 | `evidence` / `evidenceHint` / `evidence-item` / `evidence-graph-link` / `evidenceGraphData` / `evidenceGraph` / `evidence links` | 证据面板全链路 | 见下方 i18n 替换 |

#### 中文 i18n (zh-CN.ts)

| 行号 | key | 原文 | 建议替换 |
|------|-----|------|------|
| 363 | `researchWorkspace.linkedEvidence` | `关联证据` | `引用来源` |
| 364 | `researchWorkspace.evidenceGraph` | `证据图谱` | `引用关系图` |

#### 英文 i18n (en.ts)

| 行号 | key | 原文 | 建议替换 |
|------|-----|------|------|
| 361 | `researchWorkspace.linkedEvidence` | `Linked evidence` | `Cited sources` |
| 362 | `researchWorkspace.evidenceGraph` | `Evidence graph` | `Citation graph` |

#### 脚本层
- 行 567: `interface EvidenceItem` — 类型名，不改
- 行 576–578: `GraphPreview`, `evidenceGraphData` — 变量名，不改
- 行 620: `const evidence` — 变量名，不改
- 行 846–852: `openEvidenceInGraph()` — 函数名，不改
- 行 902: `use_rag: true` — API 字段，**不改**

**CSS class**: `.rw-evidence-*` 系列无需改名。

---

### 8. ResearchWorkflowView.vue — 版本比较工作流

**命中术语**: Evidence (domain sense)

#### 模板层 + i18n

| 行号 (zh-CN.ts) | key | 原文 | 建议替换 |
|------|-----|------|------|
| 166 | `research.stepEvidence` | `核验证据` | `核验来源` |
| 193 | `research.verifyEvidence` | `来源与证据` | `出处与来源` |

| 行号 (en.ts) | key | 原文 | 建议替换 |
|------|-----|------|------|
| 159 | `research.title` | `Evidence-backed Version Comparison` | `Source-based Version Comparison` |
| 164 | `research.stepEvidence` | `Verify evidence` | `Verify sources` |
| 191 | `research.verifyEvidence` | `Sources and evidence` | `Provenance and sources` |

#### 脚本层
- 行 281–298: `EvidenceSnapshot` interface, `evidence_complete` 字段 — 类型名和字段名，不改（后台数据字段）

---

### 9. V4ResearchView.vue — V4 研究视图

**命中术语**: Evidence (domain sense)

#### 中文 i18n (zh-CN.ts)

| 行号 | key | 原文 | 建议替换 |
|------|-----|------|------|
| 261 | `v4.stepSynthesis` | `证据综合` | `资料汇总` |
| 273 | `v4.noEvidence` | `无证据 — 此概念在当前语料中无匹配` | `未找到相关资料` |
| 276 | `v4.evidenceCount` | `证据条数` | `引用条数` |

#### 英文 i18n (en.ts)

| 行号 | key | 原文 | 建议替换 |
|------|-----|------|------|
| 259 | `v4.stepSynthesis` | `Evidence Synthesis` | `Source Synthesis` |
| 271 | `v4.noEvidence` | `No evidence — concept has no match in the corpus` | `No matching sources found` |
| 274 | `v4.evidenceCount` | `Evidence Items` | `Source references` |
| 319 | `researchEntry.toolResearchDesc` | `Evidence-driven version comparison` | `Source-based version comparison` |

#### 脚本层
- 行 432, 449: `evidence_synthesis` — 后台工作流 step name，**不改**
- 行 783: `evidence_ids` — 后台数据字段，**不改**
- 行 241–242: `concept.paragraphs`, `citation_count` — 数据字段，不改

---

### 10. GraphExplorerView.vue — 知识图谱

**命中术语**: Evidence (仅在注释中)

| 行号 | 原文 | 说明 |
|------|------|------|
| 199 | `fall back to loading evidence subgraph` | JS 注释，无需改动 |

---

### 11. en.ts — "grounded" 命中

| 行号 | key | 原文 | 建议替换 |
|------|-----|------|------|
| 351 | `researchWorkspace.assistantHint` | `answers are grounded in the knowledge base` | `answers draw from the knowledge base` |

这是 "Groundedness" 的唯一近似命中。

---

## 汇总：需修改清单

### 必须修改（用户可见文字，18 处）

#### A. RAG → 智能检索（7 处）

| # | 文件 | 位置 | 修改内容 |
|---|------|------|---------|
| 1 | `LiteratureListView.vue` | 行 22–24 | 下拉选项 `RAG 状态/RAG 已启用/RAG 未启用` → `智能检索/已启用/未启用` |
| 2 | `LiteratureListView.vue` | 行 100 | 列头 label `'RAG'` → `'智能检索'` |
| 3 | `LiteratureDetailView.vue` | 行 54 | 字段标签 `RAG 状态` → `智能检索` |
| 4 | `LiteratureDetailView.vue` | 行 119 | 区块标题 `<h4>RAG</h4>` → `<h4>智能检索</h4>` |
| 5 | `LiteratureDetailView.vue` | 行 121–122 | 按钮文字 `启用 RAG/禁用 RAG` → `启用智能检索/停用智能检索` |
| 6 | `LiteratureDetailView.vue` | 行 252 | Toast `RAG 已启用/RAG 已禁用` → `智能检索已启用/智能检索已停用` |
| 7 | `LiteratureReviewQueue.vue` | 行 86 | 列头 label `'RAG'` → `'智能检索'` |

#### B. RAG + Chunk → 管理后台（2 处）

| # | 文件 | 位置 | 修改内容 |
|---|------|------|---------|
| 8 | `IngestionTasksView.vue` | 行 65 | `chunk_delete: '分块删除'` → `'删除已处理片段'` |
| 9 | `IngestionTasksView.vue` | 行 65 | `rag_disabled: 'RAG 禁用'` → `'停用智能检索'` |

#### C. Vector → 智能检索（1 处）

| # | 文件 | 位置 | 修改内容 |
|---|------|------|---------|
| 10 | `AboutView.vue` | 行 47 | `向量检索 + RAG` → `智能文献检索` |

#### D. Evidence → 引用/来源（6 处）

| # | 文件 | 位置 | key | 原文 → 建议 |
|---|------|------|-----|------|
| 11 | `zh-CN.ts` | 行 156 | `workspace.evidence` | `证据面板` → `引用来源` |
| 12 | `zh-CN.ts` | 行 166 | `research.stepEvidence` | `核验证据` → `核验来源` |
| 13 | `zh-CN.ts` | 行 193 | `research.verifyEvidence` | `来源与证据` → `出处与来源` |
| 14 | `zh-CN.ts` | 行 261 | `v4.stepSynthesis` | `证据综合` → `资料汇总` |
| 15 | `zh-CN.ts` | 行 273 | `v4.noEvidence` | `无证据 — …` → `未找到相关资料` |
| 16 | `zh-CN.ts` | 行 276 | `v4.evidenceCount` | `证据条数` → `引用条数` |

#### E. Evidence + Groundedness → 英文 i18n（8 处）

| # | 文件 | 位置 | key | 原文 → 建议 |
|---|------|------|-----|------|
| 17 | `en.ts` | 行 159 | `research.title` | `Evidence-backed Version Comparison` → `Source-based Version Comparison` |
| 18 | `en.ts` | 行 164 | `research.stepEvidence` | `Verify evidence` → `Verify sources` |
| 19 | `en.ts` | 行 191 | `research.verifyEvidence` | `Sources and evidence` → `Provenance and sources` |
| 20 | `en.ts` | 行 259 | `v4.stepSynthesis` | `Evidence Synthesis` → `Source Synthesis` |
| 21 | `en.ts` | 行 271 | `v4.noEvidence` | `No evidence — …` → `No matching sources found` |
| 22 | `en.ts` | 行 274 | `v4.evidenceCount` | `Evidence Items` → `Source references` |
| 23 | `en.ts` | 行 319 | `researchEntry.toolResearchDesc` | `Evidence-driven version comparison` → `Source-based version comparison` |
| 24 | `en.ts` | 行 351 | `researchWorkspace.assistantHint` | `grounded in the knowledge base` → `draw from the knowledge base` |

#### F. 关联证据 → 中文 i18n 补充（2 处）

| # | 文件 | 位置 | key | 原文 → 建议 |
|---|------|------|-----|------|
| 25 | `zh-CN.ts` | 行 363 | `researchWorkspace.linkedEvidence` | `关联证据` → `引用来源` |
| 26 | `zh-CN.ts` | 行 364 | `researchWorkspace.evidenceGraph` | `证据图谱` → `引用关系图` |

---

### 不改清单（后台 / 内部 / 非用户可见）

| 位置 | 内容 | 原因 |
|------|------|------|
| `WorkspaceView.vue:267` | `use_rag: true` | API 请求体字段，后台协议 |
| `ResearchWorkspaceView.vue:902` | `use_rag: true` | 同上 |
| `ResearchWorkspaceView.vue:567` | `interface EvidenceItem` | TypeScript 类型名 |
| `ResearchWorkspaceView.vue:578` | `evidenceGraphData` | JS 变量名 |
| `ResearchWorkspaceView.vue:620` | `const evidence` | JS 变量名 |
| `ResearchWorkspaceView.vue:852` | `openEvidenceInGraph()` | JS 函数名 |
| `ResearchWorkspaceView.vue` 全篇 | `.rw-evidence-*` CSS class | 样式类名 |
| `ResearchWorkflowView.vue:281` | `interface EvidenceSnapshot` | TypeScript 类型名 |
| `ResearchWorkflowView.vue:285` | `evidence_complete` | 后台数据字段 |
| `V4ResearchView.vue:432,449` | `evidence_synthesis` | 后台工作流 step name |
| `V4ResearchView.vue:783` | `evidence_ids` | 后台数据字段 |
| `V4ResearchView.vue:290` | `edge.evidence_ids?.length` | 模板中读取后台数据 |
| `GraphExplorerView.vue:199` | `evidence subgraph` | 代码注释 |
| `LiteratureDetailView.vue:174` | `rag_enabled: boolean` | TS 类型定义 |
| `LiteratureDetailView.vue:202-204` | `ragLoading/ragMsg/ragOk` | JS 变量名 |
| `LiteratureListView.vue:63,89,114` | `rag_enabled/ragFilter` | TS 类型 + JS 变量 |
| `LiteratureReviewQueue.vue:53` | `rag_enabled: boolean` | TS 类型定义 |
| `IngestionTasksView.vue:63` | `'chunk_delete', 'rag_disabled'` | Action 常量字符串（后台 API 值） |
| 所有测试文件 (`__tests__/`) | 全部 | 测试代码，非用户可见 |
| `AboutView.vue:12` | `语义检索` | 不在本次六项术语中，可后续单独处理 |

---

## 建议实施顺序

1. **优先**: 中文 i18n（`zh-CN.ts`）— 9 处，影响面最广
2. **其次**: 英文 i18n（`en.ts`）— 8 处
3. **再次**: 文献管理页面（`LiteratureDetailView.vue`, `LiteratureListView.vue`）— 直接硬编码中文
4. **然后**: 管理后台（`IngestionTasksView.vue`, `LiteratureReviewQueue.vue`）
5. **最后**: 关于页（`AboutView.vue`）

---

## 附录：术语对照表

| 技术术语 | 推荐中文替换 | 推荐英文替换 |
|---------|------------|------------|
| RAG | 智能检索 | Intelligent Search |
| Vector Search | 智能检索 | (同上，合并为一个概念) |
| Chunk | 文本片段 / 已处理片段 | Processed segment |
| Embedding | （前端无命中，无需替换） | — |
| Evidence | 引用来源 / 出处 / 资料 | Cited source / Source |
| Evidence Graph | 引用关系图 | Citation graph |
| Evidence Synthesis | 资料汇总 | Source synthesis |
| Grounded / Groundedness | 基于知识库 | Draws from knowledge base |
