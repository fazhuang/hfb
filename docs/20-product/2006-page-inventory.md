# Page Inventory

> **Generated**: 2026-07-17
> **Scope**: `apps/frontend/src/` — views, router, layouts, components
> **Method**: Full scan of all 25 view files, router definitions, layout, and shared components

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Router Routes** (children) | 27 |
| **Actual Page Views** (with routes) | 20 |
| **Redirect-only Routes** | 4 |
| **Internal/Embedded Views** | 1 |
| **Views with NO Route Entry** | 1 |
| **Placeholder Pages** | 1 |

---

## Page Details

### 1. Home

| Field | Value |
|-------|-------|
| **页面名称** | 首页 / Home |
| **路由** | `/` |
| **所属模块** | System |
| **对应Vue文件** | `views/HomeView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Welcome hero (auth-dependent), system health check dashboard (Backend, DB, Redis, ES, Minio status), research entry CTA |
| **调用API** | `GET /api/v1/health` (via system store) |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 2. Search

| Field | Value |
|-------|-------|
| **页面名称** | 全局搜索 / Search |
| **路由** | `/search` |
| **所属模块** | Research |
| **对应Vue文件** | `views/SearchView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Full-text search with autocomplete suggestions, entity type filter chips (person/book/passage/version/paper), dynasty facet filter, search result cards with highlighted snippets, quick-add to research topic, pagination |
| **调用API** | `GET /api/v1/search`, `GET /api/v1/search/suggest` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 3. Documents (Placeholder)

| Field | Value |
|-------|-------|
| **页面名称** | 文献 / Documents |
| **路由** | `/documents` |
| **所属模块** | Library |
| **对应Vue文件** | `views/DocumentsView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Coming-soon placeholder only — delegates to `PlaceholderPage` component |
| **调用API** | None |
| **是否已经完成** | ⚠️ Placeholder only |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ❌ No — replaced by `/literature` |

### 4. About

| Field | Value |
|-------|-------|
| **页面名称** | 关于 / About |
| **路由** | `/about` |
| **所属模块** | System |
| **对应Vue文件** | `views/AboutView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Static info: vision statement, tech stack display (FastAPI, Vue 3, PostgreSQL, Elasticsearch, Neo4j, Milvus) |
| **调用API** | None |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 5. Login

| Field | Value |
|-------|-------|
| **页面名称** | 登录 / Login |
| **路由** | `/login` |
| **所属模块** | Authentication |
| **对应Vue文件** | `views/LoginView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No (guest-only: redirects if already authed) |
| **权限要求** | Guest only (`meta: { guest: true }`) |
| **当前功能** | Username/password login form, validation, redirect after login, value-proposition sidebar |
| **调用API** | `POST /api/v1/auth/login` (via auth store) |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 6. Register

| Field | Value |
|-------|-------|
| **页面名称** | 注册 / Register |
| **路由** | `/register` |
| **所属模块** | Authentication |
| **对应Vue文件** | `views/RegisterView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No (guest-only) |
| **权限要求** | Guest only (`meta: { guest: true }`) |
| **当前功能** | Registration form (username/email/displayName/password), client-side password length validation, server-side validation errors display, auto-login after registration |
| **调用API** | `POST /api/v1/auth/register`, `POST /api/v1/auth/login` (via auth store) |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 7. Books List

| Field | Value |
|-------|-------|
| **页面名称** | 典籍列表 / Books |
| **路由** | `/books` |
| **所属模块** | Library |
| **对应Vue文件** | `views/BookListView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Paginated list using shared `EntityListPage` component, search, route to detail |
| **调用API** | `GET /api/v1/books` (via EntityListPage) |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 8. Book Detail

| Field | Value |
|-------|-------|
| **页面名称** | 典籍详情 / Book Detail |
| **路由** | `/books/:id` |
| **所属模块** | Library |
| **对应Vue文件** | `views/BookDetailView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Book metadata (title, pinyin, English name, dynasty, category, year), abstract, chapters list, versions list (clickable to version detail) |
| **调用API** | `GET /api/v1/books/:id`, `GET /api/v1/chapters`, `GET /api/v1/versions` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 9. Version Detail

| Field | Value |
|-------|-------|
| **页面名称** | 版本详情 / Version Detail |
| **路由** | `/versions/:id` |
| **所属模块** | Library |
| **对应Vue文件** | `views/VersionDetailView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Version metadata (era, repository, editor, shelf_mark, year, description, source URL), fulltext passages list with order numbers, scroll-to-passage anchor support (`?passage=xxx`) |
| **调用API** | `GET /api/v1/versions/:id`, `GET /api/v1/versions/:id/passages` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 10. Persons List

| Field | Value |
|-------|-------|
| **页面名称** | 人物列表 / Persons |
| **路由** | `/persons` |
| **所属模块** | Library |
| **对应Vue文件** | `views/PersonListView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Paginated list using shared `EntityListPage` component, search, route to detail |
| **调用API** | `GET /api/v1/persons` (via EntityListPage) |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 11. Person Detail

| Field | Value |
|-------|-------|
| **页面名称** | 人物详情 / Person Detail |
| **路由** | `/persons/:id` |
| **所属模块** | Library |
| **对应Vue文件** | `views/PersonDetailView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Person metadata (name, alt names, dynasty, life span, courtesy_name, pseudonym, birthplace, biography, notable works, external reference). Uses `useEntityDetail` composable. |
| **调用API** | `GET /api/v1/persons/:id` (via useApi composable) |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 12. Graph Explorer

| Field | Value |
|-------|-------|
| **页面名称** | 知识图谱浏览器 / Graph Explorer |
| **路由** | `/graph` |
| **所属模块** | Knowledge |
| **对应Vue文件** | `views/GraphExplorerView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Sidebar entity search with type filters, graph canvas (via GraphCanvas component), neighborhood/subgraph exploration, path finding between two nodes, supports `?type=&id=` and `?trace=` query params for deep-linking |
| **调用API** | `GET /api/v1/graph/entities`, `GET /api/v1/graph/neighbors/:type/:id`, `GET /api/v1/graph/entity/:type/:id`, `GET /api/v1/graph/path` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 13. Research — New Topic

| Field | Value |
|-------|-------|
| **页面名称** | 创建新研究课题 / New Research Topic |
| **路由** | `/research/new` |
| **所属模块** | Research |
| **对应Vue文件** | `views/ResearchNewView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | ✅ Yes (`requiresAuth`) |
| **权限要求** | Authenticated |
| **当前功能** | Form to create a new research topic (name + description), sets topic in research store, redirects to research-home |
| **调用API** | None (client-side store only) |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 14. Research — Home

| Field | Value |
|-------|-------|
| **页面名称** | 研究课题首页 / Research Home |
| **路由** | `/research/home` |
| **所属模块** | Research |
| **对应Vue文件** | `views/ResearchHomeView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | ✅ Yes (`requiresAuth`) |
| **权限要求** | Authenticated |
| **当前功能** | Current topic header, tools grid (Search, Workspace, Reports, Books, Graph, Assistant), quick nav to Dashboard, end-research button, auto-redirects to home if no active research |
| **调用API** | None (client-side store only) |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 15. Research — Workspace (Tabbed)

| Field | Value |
|-------|-------|
| **页面名称** | 研究工作台 / Research Workspace |
| **路由** | `/research/workspace` |
| **所属模块** | Research |
| **对应Vue文件** | `views/ResearchWorkspaceView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | ✅ Yes (`requiresAuth`) |
| **权限要求** | Authenticated |
| **当前功能** | **7 tabs**: (1) Materials — literature list with search, (2) Versions — classical versions list with search, (3) Notes — notes grid with quick-note input and session filter, (4) Reports — V4 report list, detail view with citations, export, and note saving, (5) Research — embedded `ResearchWorkflowView` for version comparison, (6) V4 Research — inline V4 workflow runner with report detail, citations, export, note editor, (7) Assistant — AI chat with SSE streaming, evidence sidebar with graph preview, citation saving. Supports `?tab=`, `?run=`, `?ask=` query params |
| **调用API** | `GET /api/v1/documents`, `GET /api/classical-versions`, `GET/POST/DELETE /api/v1/workspace/sessions`, `GET/POST /api/v1/workspace/sessions/:id/notes`, `DELETE /api/v1/workspace/notes/:id`, `POST /api/v4/research/session`, `POST /api/v4/research/workflow`, `GET /api/v4/research/session/:id/runs`, `POST /api/v1/workspace/sessions/:id/citations`, `POST /api/v1/ai/chat` (SSE), `GET /api/v1/search` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 16. V4 Research (Standalone)

| Field | Value |
|-------|-------|
| **页面名称** | V4 研究 / V4 Research |
| **路由** | `/v4/research-internal` (internal; public `/v4/research` and `/v4` redirect to workspace) |
| **所属模块** | Research |
| **对应Vue文件** | `views/V4ResearchView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | ✅ Yes (`requiresAuth`) |
| **权限要求** | Authenticated |
| **当前功能** | **3 tabs**: (1) Research — full V4 workflow (topic input → 5-step pipeline → report with citations, export, note editor, replay verification), (2) Education — concept learning with difficulty levels, (3) Visualization — concept/citation/timeline/document graph generation. Supports `?run=` deep-link to load a specific run |
| **调用API** | `POST /api/v4/research/session`, `POST /api/v4/research/workflow`, `GET /api/v4/research/session/:id/runs`, `POST /api/v4/research/runs/:id/replay`, `POST /api/v4/education/learn`, `POST /api/v4/visualization/graph`, `GET/POST /api/v1/workspace/sessions`, `POST /api/v1/workspace/sessions/:id/notes` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes (primary access is via workspace, standalone is internal) |

### 17. Research — Workflow (Embedded)

| Field | Value |
|-------|-------|
| **页面名称** | 版本校勘工作流 / Version Comparison Workflow |
| **路由** | None (embedded in ResearchWorkspaceView tab) |
| **所属模块** | Research |
| **对应Vue文件** | `views/ResearchWorkflowView.vue` |
| **Layout** | Embedded (no layout of its own) |
| **是否需要登录** | Inherited from parent (requiresAuth in workspace) |
| **权限要求** | Authenticated |
| **当前功能** | 4-step workflow: (1) search passages, (2) select source/target versions, (3) run diff comparison with operation table, (4) evidence verification + save notes. Auto-restores last session on mount. Export Markdown. |
| **调用API** | `GET /api/v1/search`, `POST /api/v1/workspace/sessions`, `PUT /api/v1/research/sessions/:id/version-comparison`, `POST /api/v1/workspace/sessions/:id/notes`, `GET /api/v1/research/sessions/:id/export` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 18. Dashboard

| Field | Value |
|-------|-------|
| **页面名称** | 仪表盘 / Dashboard |
| **路由** | `/dashboard` |
| **所属模块** | System |
| **对应Vue文件** | `views/DashboardView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Entity count stats grid (persons/books/versions/passages/papers/users), dynasty distribution bar chart, category distribution bar chart, recent activity feed, system info (version, environment, research sessions, notes), onboarding step guide for new users, research entry card |
| **调用API** | `GET /api/v1/dashboard/stats`, `GET /api/v1/dashboard/overview` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 19. Literature List

| Field | Value |
|-------|-------|
| **页面名称** | 文献列表 / Literature List |
| **路由** | `/literature` |
| **所属模块** | Library |
| **对应Vue文件** | `views/literature/LiteratureListView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None |
| **当前功能** | Paginated table with search and filters (copyright status, review status, RAG enabled), clickable rows to detail, uses shared `DataTable` component |
| **调用API** | `GET /api/v1/documents` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 20. Literature Detail

| Field | Value |
|-------|-------|
| **页面名称** | 文献详情 / Literature Detail |
| **路由** | `/literature/:id` |
| **所属模块** | Library |
| **对应Vue文件** | `views/literature/LiteratureDetailView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | No |
| **权限要求** | None (admin actions require `canReviewDocuments`) |
| **当前功能** | Full detail: compliance panel (copyright, license, review status, RAG status), fulltext with expand/collapse, chapter navigation parsed from content, metadata grid, abstract, admin actions (review, RAG toggle, withdraw), "Ask AI" button that navigates to workspace assistant |
| **调用API** | `GET /api/v1/documents/:id`, `PATCH /api/v1/documents/:id/review`, `PATCH /api/v1/documents/:id`, `POST /api/v1/documents/:id/withdraw` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 21. Classical Versions List

| Field | Value |
|-------|-------|
| **页面名称** | 古籍版本库 / Classical Versions |
| **路由** | `/classical-versions` |
| **所属模块** | Library |
| **对应Vue文件** | `views/classical-versions/ClassicalVersionListView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | ✅ Yes (`requiresAuth`) |
| **权限要求** | Authenticated |
| **当前功能** | Paginated table with search and filters (review status, public domain status), uses shared `DataTable` component |
| **调用API** | `GET /api/classical-versions` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 22. Admin — Literature Review Queue

| Field | Value |
|-------|-------|
| **页面名称** | 全文审核队列 / Literature Review Queue |
| **路由** | `/admin/literature-review` |
| **所属模块** | Administration |
| **对应Vue文件** | `views/admin/LiteratureReviewQueue.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | ✅ Yes (`requiresAuth + requiresAdmin`) |
| **权限要求** | Admin (`canReviewDocuments`) |
| **当前功能** | Paginated table filtering by review status + copyright status, clickable rows to literature detail, uses shared `DataTable` component |
| **调用API** | `GET /api/v1/documents` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 23. Admin — Ingestion Tasks

| Field | Value |
|-------|-------|
| **页面名称** | 采集任务记录 / Ingestion Tasks |
| **路由** | `/admin/ingestion-tasks` |
| **所属模块** | Administration |
| **对应Vue文件** | `views/admin/IngestionTasksView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | ✅ Yes (`requiresAuth + requiresAdmin`) |
| **权限要求** | Admin (`canReviewDocuments`) |
| **当前功能** | Paginated table filtering by action type, status, and source, uses shared `DataTable` component |
| **调用API** | `GET /api/v1/ingestion/tasks` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 24. Admin — Source Policy (Super Admin)

| Field | Value |
|-------|-------|
| **页面名称** | 来源白名单管理 / Source Policy |
| **路由** | `/admin/source-policy` |
| **所属模块** | Administration |
| **对应Vue文件** | `views/admin/SourcePolicyView.vue` |
| **Layout** | DefaultLayout |
| **是否需要登录** | ✅ Yes (`requiresAuth + requiresSuperAdmin`) |
| **权限要求** | Super Admin (`canManageSourcePolicies`) |
| **当前功能** | Add/enable/disable/delete source policies, event delegation for inline action buttons, uses shared `DataTable` component |
| **调用API** | `GET /api/v1/admin/source-policies`, `POST /api/v1/admin/source-policies`, `PATCH /api/v1/admin/source-policies/:id`, `DELETE /api/v1/admin/source-policies/:id` |
| **是否已经完成** | ✅ Yes |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ✅ Yes |

### 25. Workspace (Legacy — No Route)

| Field | Value |
|-------|-------|
| **页面名称** | 工作区 (旧版) / Workspace (Legacy) |
| **路由** | ❌ None — `/workspace` redirects to `/research/workspace` |
| **所属模块** | Research |
| **对应Vue文件** | `views/WorkspaceView.vue` |
| **Layout** | Would use DefaultLayout |
| **是否需要登录** | N/A (unreachable) |
| **权限要求** | N/A |
| **当前功能** | Three-panel layout (Knowledge Navigator / Research Canvas / AI Assistant + Evidence), sessions, notes, chat with SSE streaming. Superseded by ResearchWorkspaceView. |
| **调用API** | `GET/POST/PATCH /api/v1/workspace/sessions`, `GET/POST /api/v1/workspace/sessions/:id/notes`, `DELETE /api/v1/workspace/notes/:id`, `POST /api/v1/ai/chat` (SSE), `GET /api/v1/search` |
| **是否已经完成** | ⚠️ Abandoned (superseded) |
| **是否存在Mock数据** | No |
| **是否已经实际可用** | ❌ No — no route, unreachable |

---

## Module Statistics

| Module | Count | Pages |
|--------|-------|-------|
| **Research** | 7 | Search, ResearchNew, ResearchHome, ResearchWorkspace, V4Research, ResearchWorkflow (embedded), WorkspaceView (legacy) |
| **Library** | 7 | Books List, Book Detail, Version Detail, Persons List, Person Detail, Literature List, Literature Detail, Classical Versions List |
| **Knowledge** | 1 | Graph Explorer |
| **Reports** | 0 | (Reports are inline-tab in ResearchWorkspace) |
| **Administration** | 3 | Literature Review Queue, Ingestion Tasks, Source Policy |
| **Authentication** | 2 | Login, Register |
| **System** | 3 | Home, About, Dashboard |
| **Other** | 1 | Documents (placeholder) |

**Total actual pages**: 24 (including 1 legacy unreachable, 1 placeholder, 1 embedded)

---

## Duplicate Pages

### 功能重复页面

| # | Pages | Issue |
|---|-------|-------|
| 1 | **V4ResearchView** vs **ResearchWorkspaceView (v4-research tab)** | Both implement the full V4 workflow (run workflow, report detail, citations, export, note saving). V4ResearchView also has Education and Visualization tabs not present in the workspace. V4 research functionality is duplicated across two views. |
| 2 | **DocumentsView** vs **LiteratureListView** | `/documents` is a placeholder "coming soon" page, but `/literature` is the real working literature list. Both routes point at different concepts of "文献". |
| 3 | **ResearchWorkspaceView (assistant tab)** vs **WorkspaceView (legacy)** | Both implement AI chat with SSE streaming + evidence sidebar. ResearchWorkspaceView is the active one; WorkspaceView is abandoned. |
| 4 | **ResearchWorkflowView (embedded in workspace tab)** vs **ResearchWorkspaceView (research tab)** | The "research" tab literally renders `<ResearchWorkflowView />` inline — this is by design, but the workflow is also the only content of this view file. |

### 废弃页面

| # | Page | Reason |
|---|------|--------|
| 1 | **WorkspaceView.vue** | No router entry. Superseded by ResearchWorkspaceView. Contains duplicate session/note/chat logic. |
| 2 | **DocumentsView.vue** | Placeholder "coming soon" only. Real functionality lives in LiteratureListView. |

### 未使用页面

| # | Page | Status |
|---|------|--------|
| 1 | **V4ResearchView.vue (`/v4/research-internal`)** | Has a route but users cannot navigate to it via normal UI — all `/v4` and `/v4/research` paths redirect to workspace tabs. Only reachable by manually typing the URL. |

### Router存在但无法进入页面

| # | Route | Issue |
|---|-------|-------|
| 1 | `/v4/research-internal` (name: `v4-research`) | No navbar link, no in-app navigation points to this route. Users must know the URL. |
| 2 | `/documents` (name: `documents`) | Links to a placeholder. No navbar link present for this route (not confirmed — may exist). |

### 没有Router引用页面

| # | Vue File | Issue |
|---|----------|-------|
| 1 | `views/WorkspaceView.vue` | Not imported or referenced in router or any other component |
| 2 | `views/ResearchWorkflowView.vue` | Not a standalone route — only used as inline component inside ResearchWorkspaceView |

---

## UI Debt

### 命名混乱

| # | Issue | Location |
|---|-------|----------|
| 1 | `DocumentsView` placeholder vs `LiteratureListView` — two different names for same domain concept "文献". Router path `/documents` vs `/literature`. | `DocumentsView.vue`, `LiteratureListView.vue`, router |
| 2 | `ResearchWorkspaceView` vs `WorkspaceView` — two workspace views coexisting with overlapping functionality | `ResearchWorkspaceView.vue`, `WorkspaceView.vue` |
| 3 | `ResearchWorkflowView` implements version comparison, but is named "Workflow" — confused with V4 workflow | `ResearchWorkflowView.vue` |
| 4 | BookListView title shows `t('nav.documents')` ("文献") but it lists books ("典籍") | `BookListView.vue` |
| 5 | CSS class naming inconsistency: `rw-*` (workspace), `rh-*` (research home), `v4-*` (V4), `.search-*`, `.lit-*`, `.cv-*`, `.sp-*` — no shared prefix convention | Across all views |

### 布局不统一

| # | Issue | Location |
|---|-------|----------|
| 1 | Page max-width varies: 520px (ResearchNew), 640px (Home), 800px (BookDetail, PersonDetail, About), 840px (ResearchHome), 860px (VersionDetail), 900px (Search, LiteratureDetail, SourcePolicy), 1000px (Dashboard), 1100px (ResearchWorkspace), 1200px (LiteratureList, ClassicalVersions, LiteratureReviewQueue, IngestionTasks, V4Research) | Across all views |
| 2 | Padding varies: `24px 20px 60px`, `32px 24px`, `48px 24px`, `80px auto`, `28px 20px 60px` — no consistent page padding | Across all views |
| 3 | Some pages use `<section class="panel">` card pattern (LiteratureDetail), others use bare `<div>` with border (SearchView), others use no card at all | Mixed across module |
| 4 | Back navigation: some use `<router-link>` (ResearchWorkspace), some use `<button @click="$router.back()">` (VersionDetail), some have no back nav | Inconsistent |
| 5 | Header hierarchy: some use `<h1>` + `<p class="subtitle">`, some use `<h1>` + `<div class="header-meta">`, some use `<div class="page-header"><h1>` | Across all views |

### 重复组件

| # | Pattern | Instances | Locations |
|---|---------|-----------|-----------|
| 1 | **自定义分页控件** | 5 | SearchView, LiteratureListView, LiteratureReviewQueue, IngestionTasksView, ClassicalVersionListView |
| 2 | **搜索框 + 搜索按钮** | 4 | SearchView, LiteratureListView, ClassicalVersionListView, ResearchWorkflowView |
| 3 | **筛选下拉框行 (filter-bar)** | 5 | LiteratureListView, ClassicalVersionListView, LiteratureReviewQueue, IngestionTasksView, SourcePolicyView |
| 4 | **自定义 Loading/Error/Empty 状态** | 10+ | BookDetailView, VersionDetailView, PersonDetailView, SearchView, ResearchWorkspaceView (materials/versions/notes/reports), LiteratureDetailView, DashboardView |
| 5 | **EntityListPage (shared)** | 2 (correct usage) | BookListView, PersonListView |
| 6 | **DataTable (shared)** | 5 (correct usage) | LiteratureListView, ClassicalVersionListView, LiteratureReviewQueue, IngestionTasksView, SourcePolicyView |

### 重复表格

| # | Issue | Locations |
|---|-------|-----------|
| 1 | `DataTable` component is used in 5 pages — this is good reuse. However, `EntityListPage` wraps different API patterns and has its own internal table layout. Two different list abstractions. | `DataTable.vue`, `EntityListPage.vue` |
| 2 | Pagination HTML/CSS is copy-pasted between LiteratureListView, LiteratureReviewQueue, IngestionTasksView, ClassicalVersionListView — identical structure with different class names | 4 files |

### 重复Card

| # | Card Pattern | Locations |
|---|-------------|-----------|
| 1 | `stat-card` (icon + value + label) | DashboardView |
| 2 | `result-card` (search result with badge + title + snippet + meta) | SearchView |
| 3 | `rw-report-card` (report header + steps + actions) | ResearchWorkspaceView (defined twice: once in report list, once in v4-research tab) |
| 4 | `rw-note-card` (note with meta + content + delete) | ResearchWorkspaceView |
| 5 | `rh-tool-card` (icon + name + description) | ResearchHomeView |
| 6 | `note-card` (different style from rw-note-card) | WorkspaceView (legacy) |
| 7 | `version-item` (clickable version card) | BookDetailView |
| 8 | Entity result cards in GraphExplorerView sidebar | GraphExplorerView |

**8 distinct card styles with zero shared abstraction.**

### 重复Dialog

| # | Issue | Locations |
|---|-------|-----------|
| 1 | No formal `<dialog>` or modal component exists. Inline note editors are implemented ad-hoc in multiple places. | ResearchWorkspaceView (note editor in v4-research tab), V4ResearchView (note editor) |
| 2 | `window.confirm()` used for confirmation ("覆盖当前研究课题?") | SearchView |
| 3 | `window.prompt()` used for note content input | WorkspaceView (legacy) |

### 重复Toolbar

| # | Pattern | Locations |
|---|---------|-----------|
| 1 | `filter-bar` with inline `<select>` elements | LiteratureListView, LiteratureReviewQueue, IngestionTasksView, ClassicalVersionListView |
| 2 | `search-box` with `<input>` + `<button>` | LiteratureListView, ClassicalVersionListView |
| 3 | `type-filters` chip bar | SearchView, GraphExplorerView |
| 4 | `.rw-panel-header` + `.rw-panel-actions` (toolbar per tab) | ResearchWorkspaceView (used in materials, versions, notes, reports, assistant) |

### 重复搜索框

| # | Pattern | Locations |
|---|---------|-----------|
| 1 | `<input>` + `<button>搜索</button>` with `.search-box` | LiteratureListView, ClassicalVersionListView |
| 2 | `<input>` + `<button>搜索</button>` with `.search-input-wrapper` | SearchView |
| 3 | `<input>` + `<button>搜索</button>` with `.search-row` | ResearchWorkflowView |
| 4 | `<input>` with `.rw-search-input` (no button) | ResearchWorkspaceView |
| 5 | `<input>` + `<button>搜索</button>` with `.search-section` | GraphExplorerView |

**5 different search input implementations.**

### 重复分页

| # | Pattern | Locations |
|---|---------|-----------|
| 1 | Identical pagination HTML structure: `<button>上一页</button> <span>X / Y</span> <button>下一页</button>` | LiteratureListView, LiteratureReviewQueue, IngestionTasksView, ClassicalVersionListView |
| 2 | Similar pagination in SearchView (slightly different class names) | SearchView |
| 3 | `.rw-pagination` with same structure but different CSS | ResearchWorkspaceView (used in materials and versions tabs) |

### 重复Loading

| # | Pattern | Locations |
|---|---------|-----------|
| 1 | `<div class="loading-state">{{ t('common.loading') }}</div>` | BookDetailView, VersionDetailView, PersonDetailView, DashboardView (implicit) |
| 2 | `<div class="rw-loading">{{ t('common.loading') }}</div>` | ResearchWorkspaceView (materials, versions, notes, reports) |
| 3 | `<div class="table-state">{{ t('common.loading') }}</div>` | DataTable (shared — good reuse) |
| 4 | Inline spinner: `<span class="spinner"></span>` | HomeView, LoginView, RegisterView (3 different `.spinner` CSS definitions) |

### 重复Empty State

| # | Pattern | Locations |
|---|---------|-----------|
| 1 | Empty state with icon + message + hint + action link | SearchView |
| 2 | Empty state with message + hint only | ResearchWorkspaceView (materials, versions, notes, reports — each tab has its own empty state) |
| 3 | `<p class="empty-state">` with message | ClassicalVersionListView, ResearchWorkflowView |
| 4 | `<div class="table-state">{{ t('common.noData') }}</div>` | DataTable (shared — good reuse) |

---

## Layout & Component Architecture

### Shared Components (good reuse)

| Component | Used By | Status |
|-----------|---------|--------|
| `DataTable.vue` | LiteratureListView, ClassicalVersionListView, LiteratureReviewQueue, IngestionTasksView, SourcePolicyView | ✅ Good reuse |
| `EntityListPage.vue` | BookListView, PersonListView | ✅ Good reuse (but only 2 consumers) |
| `PlaceholderPage.vue` | DocumentsView | ⚠️ Only 1 consumer |
| `StatusCard.vue` | HomeView | ⚠️ Only 1 consumer |
| `GraphCanvas.vue` | GraphExplorerView | ⚠️ Only 1 consumer |
| `PassageReader.vue` | No consumer found in views | ❌ Unused? |

### Layout Structure

```
DefaultLayout
├── AppNavbar
├── AppMain (router-view)
└── AppFooter
```

All 27 routes use `DefaultLayout`. No alternative layouts exist.

### Stores

| Store | Used By |
|-------|---------|
| `auth` | LoginView, RegisterView, HomeView, ResearchWorkspaceView, WorkspaceView, LiteratureDetailView, DashboardView, router guard |
| `research` | HomeView, ResearchHomeView, ResearchNewView, ResearchWorkspaceView, ResearchWorkflowView, V4ResearchView, WorkspaceView, SearchView, DashboardView, LiteratureDetailView |
| `system` | HomeView |

### Composables

| Composable | Used By |
|------------|---------|
| `useApi` (useEntityDetail) | PersonDetailView |
| `useTheme` | (not found in scanned views) |
