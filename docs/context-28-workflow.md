# Context 28: 研究全流程贯通行

> 状态：**实施完成** | 日期：2026-07-16 | 提交：36c9bac, 659e48f

---

## 一、流程概览

以下七个环节是 HFB 平台研究工作的完整链路。每个环节的**已有能力**已验证存在，本节仅描述如何将它们串成一条连续的流水线。

```
搜索 → 加入课题 → 阅读全文 → AI问答 → Citation → 保存笔记 → 报告
```

---

## 二、各环节已有能力清单

### 1. 搜索

| 维度 | 详情 |
|------|------|
| 前端页面 | `SearchView.vue` — `/search`，支持关键词搜索、类型筛选（书/版本/段落/人物/论文）、朝代facet、自动补全 |
| API | `GET /api/v1/search` — 跨实体 ILIKE 全文检索；`GET /api/v1/search/suggest` — 自动补全 |
| 后端服务 | `RetrievalService.search()` — 块级关键词搜索，含简繁异体字扩展（针→針/鍼/鐵），确定性打分 |
| 深度检索 | `POST /api/v1/search` (day2) — 文档块搜索，返回 `[doc_id:chunk_id]` 格式引用 |

**现状**：搜索结果是独立页面，搜索结果条目**没有**"加入课题"按钮或"发送到工作区"入口。

### 2. 加入课题

| 维度 | 详情 |
|------|------|
| 前端页面 | `ResearchNewView.vue` — `/research/new`，输入课题名称 + 描述，存入 Pinia store |
| 状态管理 | `useResearchStore` — `setTopic(name, description)`，持久化到 `localStorage`（key: `hfb-current-research-topic`） |
| 课题首页 | `ResearchHomeView.vue` — `/research/home`，显示当前课题，提供研究工具入口 |

**现状**：课题是**纯客户端**概念（localStorage），没有后端 Topic 表。课题与文献/搜索/阅读之间没有数据关联——课题只是一个上下文标签字符串。

### 3. 阅读全文

| 维度 | 详情 |
|------|------|
| 前端页面 | `LiteratureDetailView.vue` — `/literature/:id`，展示标题、元数据、版权合规面板、全文内容（`content_text` 以 `<pre>` 渲染） |
| API | `GET /api/v1/documents/{id}` — 返回文档详情含全文 |
| 文献列表 | `LiteratureListView.vue` — `/literature`，分页、过滤、搜索 |
| PDF 支持 | `Document.content_text`（提取文本）+ `Document.raw_pdf_blob`（原始 PDF 字节，仅存储不展示） |
| 版本阅读 | `VersionDetailView.vue` + `PassageReader.vue` — 经典文本段落阅读 |

**现状**：文献详情页是独立的阅读视图。**没有**"就此文献提问"或"加入当前课题"的按钮。

### 4. AI 问答

| 维度 | 详情 |
|------|------|
| **工作区聊天** | `WorkspaceView.vue` — SSE 流式聊天，`POST /api/v1/ai/chat`，证据门控系统提示（无证据拒绝回答），显示检索到的 evidence 块 |
| **V4 研究查询** | `V4ResearchView.vue` / `ResearchWorkspaceView.vue` — `POST /api/v4/research/query`，支持 5 种模式：report / synthesis / research / education / graph |
| **学术 RAG** | `POST /api/v1/academic-rag/query` — 基于知识图谱遍历的证据绑定问答（无 LLM，确定性） |
| **学术 V2** | `POST /api/v2/academic/report|synthesis|research|education` — 引用锚定的学术产品层 |
| **LLM 网关** | `AIService` — OpenAI 兼容 API（当前用 DeepSeek），支持流式、结构化输出、速率限制 |
| **生成管道** | `GenerationPipeline` / `ProvedGenerationPipeline` — 检索→声明提取→子串验证→提示注入检测→确定性答案 |

**现状**：AI 问答入口分散在三个地方（WorkspaceView 聊天、V4ResearchView 工作流、ResearchWorkspaceView 助手 Tab）。它们共享后端 RAG 服务，但**彼此独立**，用户需要在不同页面之间跳转。

### 5. Citation

| 维度 | 详情 |
|------|------|
| 数据模型 | `SourceRef` → `Evidence` → `Citation`（三层 FK 链） |
| 格式 | `[doc_id:chunk_id]` 统一引用格式，含 `exact_quote`、`source_uri` |
| 自动持久化 | 所有学术模块（report/synthesis/research/education）在返回前自动调用 `CitationPersistenceService` 幂等写入 |
| 前端展示 | `V4ResearchView.vue` 工作流结果中 `<details>` 列表展示 claim_text / quote / citation_text / trace_id |
| 工作区存储 | `CitationCollection` 表（session_id + trace_json + citation_text），用户可收藏引用 |
| 证据级别 | EvidenceLevel 1-4（一级出土文献 → 四级现代研究） |
| 稳定 ID | P0-4 确定性 ID（`_make_citation_id` / `_make_evidence_id`），支持重放验证 |

**现状**：引用在后端自动生成和持久化，但在前端**缺少统一的引用管理面板**。用户无法在阅读文献时手动标记引用，也无法查看自己收藏的所有引用。

### 6. 保存笔记

| 维度 | 详情 |
|------|------|
| 会话笔记 | `ResearchNote` — session_id + entity_type + entity_id + content（Markdown）+ tags |
| CRUD API | `GET/POST /api/v1/workspace/sessions/{id}/notes` + `PATCH/DELETE /api/v1/workspace/notes/{id}` |
| 上下文笔记 | `ResearchSession.context_notes` — 会话级 Markdown 文本 |
| 前端编辑 | 多个视图中以 `<textarea>` 实现（`WorkspaceView.vue`、`ResearchWorkspaceView.vue`、`V4ResearchView.vue`、`ResearchWorkflowView.vue`） |
| 无编辑器 | **没有任何 Markdown 编辑器库**（无 CodeMirror / ProseMirror / Monaco），均为纯文本输入 |

**现状**：笔记功能存在且 API 完整，但编辑体验简陋（纯 `<textarea>`）。笔记与 Citation 之间没有关联——用户无法从一条引用直接创建笔记。

### 7. 报告

| 维度 | 详情 |
|------|------|
| **V4 工作流** | `POST /api/v4/research/workflow` — 5 步流水线：选题→文献检索→证据综合→报告生成→引用导出 |
| **学术报告** | `POST /api/v2/academic/report` — 4 种报告类型：literature_review / research_summary / thematic_analysis / historical_interpretation |
| **论文生成** | `POST /api/v2/paper/generate` — 8 模块知识图谱论文（标题→摘要→文献基础→证据链→异文附录→文献综述→讨论→方法论） |
| **Markdown 导出** | `GET /api/v1/research/sessions/{id}/export` — 版本比较记录导出；前端 `V4ResearchView.vue` 通过 Blob 下载 `.md` 文件 |
| **重放** | `POST /api/v4/research/runs/{id}/replay` — 规范 SHA-256 确定性重放 |
| **前端** | `V4ResearchView.vue` 研究报告 Tab、`ResearchWorkspaceView.vue` 报告 Tab、`ResearchWorkflowView.vue` 导出按钮 |

**现状**：报告生成管道完整（检索→综合→Markdown 渲染→下载），但**不支持 PDF/Word 导出**，且报告**不包含用户手动保存的笔记**。

---

## 三、贯通行方案

### 3.1 总体思路

**不新增研究能力，仅连接已有能力。** 每个修改都是"在现有页面加一个按钮/链接，指向已有页面/API"。

### 3.2 七个连接点

#### 连接点 ①：搜索 → 加入课题

**问题**：搜索结果页没有"加入课题"入口。

**方案**（最小改动）：
- 在 `SearchView.vue` 的搜索结果条目上添加"📌 加入课题"按钮
- 点击后调用 `researchStore.setTopic(result.title, result.text)` 或在已激活课题时，将搜索结果关联到当前会话
- 由于课题是客户端概念，最简单的方式是：点击搜索结果 → 跳转到 `/research/new?title=xxx` 预填课题名

**涉及文件**：
- `apps/frontend/src/views/SearchView.vue` — 添加按钮 + 逻辑
- `apps/frontend/src/views/ResearchNewView.vue` — 支持 query param 预填

#### 连接点 ②：加入课题 → 阅读全文

**问题**：课题（客户端 localStorage）与文献（后端 Document）之间没有关联。

**方案**（最小改动）：
- 在 `ResearchHomeView.vue` 和 `ResearchWorkspaceView.vue` 的 Materials Tab 中，为每条文献增加"📖 阅读全文"链接
- 链接指向 `/literature/{id}` — **这已经存在**（`router-link` 已指向文献详情）
- **仅需添加**：在 `LiteratureDetailView.vue` 顶部显示当前活跃课题上下文（`researchStore.currentTopic?.name`），让用户感知阅读是课题的一部分

**涉及文件**：
- `apps/frontend/src/views/literature/LiteratureDetailView.vue` — 添加课题上下文 banner

#### 连接点 ③：阅读全文 → AI 问答

**问题**：阅读文献时无法直接就该文献提问。

**方案**（最小改动）：
- 在 `LiteratureDetailView.vue` 添加"🤖 就此文献提问"按钮
- 点击后导航到工作区，自动创建会话（标题 = 文献标题），并在聊天框中预填"请分析《{文献标题}》"
- 或者：点击后打开侧边面板，直接在该页面上发起 AI 问答（复用已有的 `POST /api/v1/ai/chat` SSE 端点）

**推荐方案**（最简）：添加按钮 → 跳转 `WorkspaceView.vue` 并传递文献 ID 作为上下文 → WorkspaceView 自动创建以该文献为上下文的会话。

**涉及文件**：
- `apps/frontend/src/views/literature/LiteratureDetailView.vue` — 添加按钮 + 导航
- `apps/frontend/src/views/WorkspaceView.vue` — 支持从 URL param 初始化会话上下文

#### 连接点 ④：AI 问答 → Citation

**问题**：AI 回答中生成的引用没有"保存到我的引用集"按钮。

**方案**（最小改动）：
- 在 `WorkspaceView.vue` 聊天消息的 evidence 展示区添加"💾 保存引用"按钮
- 点击后调用已有的 CitationCollection 创建逻辑（目前 `workspace_service.py` 已支持 citation collection CRUD，但前端未暴露）
- 需要新增一个轻量 API：`POST /api/v1/workspace/sessions/{id}/citations`（如果尚未暴露）

**涉及文件**：
- `apps/frontend/src/views/WorkspaceView.vue` — 添加保存按钮
- `apps/backend/app/api/v1/ai.py` — 暴露 citation collection 端点（检查是否已存在）

#### 连接点 ⑤：Citation → 保存笔记

**问题**：引用集与笔记之间没有关联。

**方案**（最小改动）：
- 在引用详情/列表旁添加"📝 记笔记"按钮
- 点击后以该引用为上下文创建 `ResearchNote`（entity_type = "citation", entity_id = citation_id）
- 复用已有的 `POST /api/v1/workspace/sessions/{id}/notes` API

**涉及文件**：
- `apps/frontend/src/views/WorkspaceView.vue` 或 `V4ResearchView.vue` — 添加按钮

#### 连接点 ⑥：保存笔记 → 报告

**问题**：V4 工作流生成的报告不包含用户手动保存的笔记。

**方案**（最小改动）：
- 在 `POST /api/v4/research/workflow` 的报告生成步骤（Step 4）中，附加从 `ResearchNote` 中查询到的该会话笔记
- 在 `build_markdown_artifact()` 中追加"## 研究笔记"章节，列出所有笔记内容
- 或者更简单：在前端导出报告时，由前端拼接笔记内容到 Markdown 中

**推荐方案**（改动最小）：**前端拼接**——在 `V4ResearchView.vue` 的 `exportRecord()` 函数中，导出前从会话获取笔记列表并追加到报告末尾。

**涉及文件**：
- `apps/frontend/src/views/V4ResearchView.vue` — exportRecord 时获取并追加笔记

#### 连接点 ⑦：报告 → 回到搜索（闭环）

**问题**：报告生成后，用户可能需要基于报告发现的新关键词重新搜索。

**方案**（最小改动）：
- 在报告展示页添加"🔍 基于报告关键词重新搜索"按钮
- 提取报告中的关键概念，跳转到 `/search?q=关键词`

**涉及文件**：
- `apps/frontend/src/views/V4ResearchView.vue` — 添加重新搜索按钮

### 3.3 连接总览

```
┌──────────────────────────────────────────────────────────────┐
│                    研究全流程贯通行                              │
│                                                              │
│  ┌────────┐   ①   ┌────────┐   ②   ┌────────┐   ③   ┌────────┐ │
│  │ 搜索    │ ───→ │ 课题    │ ───→ │ 阅读    │ ───→ │ AI问答  │ │
│  │ Search  │ 按钮 │ Topic   │ 链接 │ Detail  │ 按钮 │ Chat    │ │
│  └────────┘      └────────┘      └────────┘      └────────┘ │
│       ↑                                               │      │
│       │                                              ④      │
│       │ ⑦ 重新搜索                                    ↓      │
│  ┌────────┐   ⑥   ┌────────┐   ⑤   ┌────────┐              │
│  │ 报告    │ ←─── │ 笔记    │ ←─── │ Citation│              │
│  │ Report  │ 拼接 │ Notes   │ 按钮 │ Save    │              │
│  └────────┘      └────────┘      └────────┘              │
│       │                                                    │
│       └── Markdown 下载 / 重放                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 四、实施状态

| 优先级 | 连接点 | 状态 | 提交 | 说明 |
|--------|--------|------|------|------|
| **P0** | ③ 阅读→AI问答 | ✅ 完成 | 36c9bac | LiteratureDetailView "🤖 就此文献提问" → ResearchWorkspace Assistant tab `?ask=` 自动发送 |
| **P0** | ④ AI问答→Citation | ✅ 完成 | 36c9bac | CitationCollection CRUD API (GET/POST/DELETE) + 证据面板 💾 保存按钮 + IDOR 防护 |
| **P1** | ⑥ 笔记→报告 | ✅ 完成 | 36c9bac | V4ResearchView exportRecord 导出前 fetch 会话笔记并拼接 "## 研究笔记" 章节 |
| **P1** | ① 搜索→课题 | ✅ 完成 | 36c9bac | SearchView 搜索结果条目 "📌 加入课题" 按钮，setTopic + 跳转 research-home |
| **P1** | ⑦ 报告→搜索 | ✅ 完成 | 36c9bac | V4ResearchView "🔍 基于报告重新搜索" 按钮 → SearchView `?q=` 自动搜索 |
| **P2** | ⑤ Citation→笔记 | ✅ 完成 | 659e48f | 报告引用列表每条 "📝 从引用记笔记" → 创建 ResearchNote (entity_type=citation) |
| **P2** | ② 课题→阅读 | ✅ 完成 | 659e48f | LiteratureDetailView 顶部课题上下文 banner "🔬 当前研究: [课题名]" |

---

## 五、实施统计

| 指标 | 数值 |
|------|------|
| 改动文件 | 9 个 |
| 新增代码行 | ~720 行 |
| 前端视图修改 | 4 个 (SearchView, LiteratureDetailView, ResearchWorkspaceView, V4ResearchView) |
| 后端 API 新增 | 3 个端点 (GET/POST/DELETE /workspace/sessions/{id}/citations) |
| 后端服务新增方法 | 1 个 (WorkspaceService.get_citation) |
| i18n 新增键 | 6 个 (addToTopic, askAI, saveCitation, citationSaved, reSearch, noteFromCitation) |
| 破坏性变更 | 0 |
| 新增依赖 | 0 |
| ruff | ✓ All checks passed |
| vue-tsc | ✓ 0 errors |
| mypy | 14 errors — 全部为预存错误，新增代码无新问题 |

---

## 六、不变更原则（红线）

1. **不新增数据库表** — 课题仍为客户端概念，不创建 Topic 表
2. **不新增 AI 能力** — 不增加新的 LLM 调用类型或 RAG 模式
3. **不引入新的第三方库** — 不做 Markdown 编辑器集成（CodeMirror 等）
4. **不动现有 API 签名** — 所有 API 端点保持不变，仅可能新增 1-2 个轻量端点暴露已有能力
5. **不修改核心生成管道** — `GenerationPipeline` / `AcademicService` / `ResearchWorkflowService` 不动

---

## 七、关键文件索引

### 前端页面（按流程顺序）

| 环节 | 文件 | 路由 |
|------|------|------|
| 搜索 | `apps/frontend/src/views/SearchView.vue` | `/search` |
| 课题（新建） | `apps/frontend/src/views/ResearchNewView.vue` | `/research/new` |
| 课题（首页） | `apps/frontend/src/views/ResearchHomeView.vue` | `/research/home` |
| 阅读全文 | `apps/frontend/src/views/literature/LiteratureDetailView.vue` | `/literature/:id` |
| 工作区 + AI 聊天 | `apps/frontend/src/views/WorkspaceView.vue` | `/workspace` (→ `/research/workspace`) |
| 研究工作区 | `apps/frontend/src/views/ResearchWorkspaceView.vue` | `/research/workspace` |
| V4 研究 + 报告 | `apps/frontend/src/views/V4ResearchView.vue` | `/v4/research-internal` |
| 课题 Store | `apps/frontend/src/stores/research.ts` | Pinia |

### 后端 API（按流程顺序）

| 环节 | 端点 | 文件 |
|------|------|------|
| 搜索 | `GET /api/v1/search`, `/suggest` | `apps/backend/app/api/v1/search.py` |
| 深度检索 | `POST /api/v1/search` | `apps/backend/app/api/v1/day2_search.py` |
| 文献详情 | `GET /api/v1/documents/{id}` | `apps/backend/app/api/v1/entities.py` |
| AI 聊天 | `POST /api/v1/ai/chat` | `apps/backend/app/api/v1/ai.py` |
| 会话/笔记 CRUD | `GET/POST /workspace/sessions`, `/notes` | `apps/backend/app/api/v1/ai.py` |
| 学术 V2 | `POST /api/v2/academic/*` | `apps/backend/app/api/v2/academic.py` |
| 学术 RAG | `POST /api/v1/academic-rag/query` | `apps/backend/app/api/v1/academic_rag.py` |
| V4 工作流 | `POST /api/v4/research/workflow` | `apps/backend/app/api/v4/research.py` |
| 报告导出 | `GET /api/v1/research/sessions/{id}/export` | `apps/backend/app/api/v1/research.py` |
| 论文生成 | `POST /api/v2/paper/generate` | `apps/backend/app/api/v2/paper.py` |

### 后端服务

| 服务 | 文件 | 职责 |
|------|------|------|
| `AIService` | `apps/backend/app/services/ai_service.py` | LLM 网关（流式聊天、翻译、摘要） |
| `RAGService` | `apps/backend/app/services/rag_service.py` | RAG 上下文构建 |
| `RetrievalService` | `apps/backend/app/services/retrieval.py` | 块级关键词检索 |
| `EvidenceRAGService` | `apps/backend/app/services/evidence_rag_service.py` | 证据绑定 RAG |
| `AcademicRAGService` | `apps/backend/app/services/academic_rag_service.py` | 学术 KG 证据链 QA |
| `AcademicService` | `apps/backend/app/services/academic_service.py` | 报告/综合/研究/教育 |
| `GenerationPipeline` | `apps/backend/app/services/generation_service.py` | 严格基础生成 |
| `ProvedGenerationPipeline` | `apps/backend/app/services/generation_proof.py` | 可证明生成 |
| `ResearchWorkflowService` | `apps/backend/app/services/research_workflow_service.py` | 5 步工作流编排 |
| `CitationPersistenceService` | `apps/backend/app/services/citation_persistence.py` | 引用持久化 |
| `WorkspaceService` | `apps/backend/app/services/workspace_service.py` | 会话/笔记/引用集 CRUD |
| `PaperService` | `apps/backend/app/services/paper_service.py` | 8 模块论文生成 |

---

## 八、验证方案

贯通行实现后，以下端到端场景应可在一个浏览器会话中完成（无需手动切换 URL）：

1. 在 `/search` 搜索"针灸甲乙经"
2. 点击搜索结果旁的"📌 加入课题" → 创建课题"针灸甲乙经研究"
3. 在课题首页点击文献 → 进入 `/literature/{id}` 阅读全文
4. 在文献详情页点击"🤖 提问" → 打开工作区，AI 回答关于该文献的问题
5. 在 AI 回答中点击"💾 保存引用" → 引用存入当前会话
6. 在引用旁点击"📝 记笔记" → 创建笔记
7. 在 V4 研究 Tab 运行工作流 → 生成报告
8. 导出报告（Markdown），报告中包含用户笔记章节
9. 点击"🔍 重新搜索" → 带回搜索结果页
