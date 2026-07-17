# Page Disposition

> **Generated**: 2026-07-17
> **Input**: `docs/20-product/2006-page-inventory.md`
> **Scope**: All 25 view files, 27 router entries, redirects, embedded components
> **Principle**: Each asset receives exactly one disposition. No two target pages share identical responsibility.

---

## Dispositions

### KEEP — 4 pages

| # | Current Name | Current Route | Current File | Module |
|---|-------------|--------------|-------------|--------|
| 1 | 首页 / Home | `/` | `views/HomeView.vue` | System |
| 2 | 关于 / About | `/about` | `views/AboutView.vue` | System |
| 3 | 登录 / Login | `/login` | `views/LoginView.vue` | Authentication |
| 4 | 注册 / Register | `/register` | `views/RegisterView.vue` | Authentication |

---

### REBUILD — 9 pages

| # | Current Name | Current Route | Current File | Module |
|---|-------------|--------------|-------------|--------|
| 5 | 版本详情 / Version Detail | `/versions/:id` | `views/VersionDetailView.vue` | Library |
| 6 | 人物详情 / Person Detail | `/persons/:id` | `views/PersonDetailView.vue` | Library |
| 7 | 知识图谱浏览器 / Graph Explorer | `/graph` | `views/GraphExplorerView.vue` | Knowledge |
| 8 | 研究课题首页 / Research Home | `/research/home` | `views/ResearchHomeView.vue` | Research |
| 9 | 研究工作台 / Research Workspace | `/research/workspace` | `views/ResearchWorkspaceView.vue` | Research |
| 10 | 文献列表 / Literature List | `/literature` | `views/literature/LiteratureListView.vue` | Library |
| 11 | 文献详情 / Literature Detail | `/literature/:id` | `views/literature/LiteratureDetailView.vue` | Library |
| 12 | 全文审核队列 / Literature Review Queue | `/admin/literature-review` | `views/admin/LiteratureReviewQueue.vue` | Administration |
| 13 | 采集任务记录 / Ingestion Tasks | `/admin/ingestion-tasks` | `views/admin/IngestionTasksView.vue` | Administration |

---

### MERGE — 7 pages

| # | Current Name | Current Route | Current File | Module | Merge Target |
|---|-------------|--------------|-------------|--------|-------------|
| 14 | 全局搜索 / Search | `/search` | `views/SearchView.vue` | Research | Library Search |
| 15 | 典籍列表 / Books List | `/books` | `views/BookListView.vue` | Library | Library Search |
| 16 | 典籍详情 / Book Detail | `/books/:id` | `views/BookDetailView.vue` | Library | Document Detail |
| 17 | 人物列表 / Persons List | `/persons` | `views/PersonListView.vue` | Library | Knowledge Explorer |
| 18 | 创建新研究课题 / Research New | `/research/new` | `views/ResearchNewView.vue` | Research | Project List |
| 19 | V4 研究 / V4 Research | `/v4/research-internal` | `views/V4ResearchView.vue` | Research | Research Workspace + Research Result |
| 20 | 古籍版本库 / Classical Versions | `/classical-versions` | `views/classical-versions/ClassicalVersionListView.vue` | Library | Library Search |

---

### RETIRE — 4 entries

| # | Current Name | Current Route | Current File | Module |
|---|-------------|--------------|-------------|--------|
| 21 | 文献(占位) / Documents | `/documents` | `views/DocumentsView.vue` | Library |
| 22 | 工作区(旧版) / Workspace Legacy | none | `views/WorkspaceView.vue` | Research |
| — | `/v4/research-internal` route | `/v4/research-internal` | — | Research |
| — | `PlaceholderPage.vue` component | — | `components/common/PlaceholderPage.vue` | — |

---

### ADMIN_ONLY — 2 pages

| # | Current Name | Current Route | Current File | Module |
|---|-------------|--------------|-------------|--------|
| 23 | 来源白名单管理 / Source Policy | `/admin/source-policy` | `views/admin/SourcePolicyView.vue` | Administration |

And one inherited from REBUILD:
| 24 | (Dashboard system info absorbed into System Operations) | `views/DashboardView.vue` | System → Administration |

Note: `IngestionTasksView` and `LiteratureReviewQueue` are listed under REBUILD (they need restructuring into Data Quality and Document Management respectively), not ADMIN_ONLY (which would keep the page as-is).

---

### REDIRECT_ONLY — 5 routes

| # | Current Route | Redirect Target | Current File |
|---|-------------|----------------|-------------|
| 25 | `/workspace` | `/research/:projectId/workspace` | — |
| 26 | `/research` | `/research` (Project List) | — |
| 27 | `/v4/research` | `/research/:projectId/workspace` | — |
| 28 | `/v4` | `/research/:projectId/workspace` | — |
| 29 | `/dashboard` | `/` (Home) | `views/DashboardView.vue` |

---

### NEW — 4 pages (not in current codebase)

| # | Target Name | Target Route | Module |
|---|------------|-------------|--------|
| N1 | Access Denied | `/access-denied` | Authentication |
| N2 | Not Found | `/not-found` | System |
| N3 | Error State | `/error` | System |
| N4 | User and Permission Management | `/admin/users` | Administration |

---

## Detailed Disposition Records

### 1. Home

| Field | Value |
|-------|-------|
| **当前页面名称** | 首页 / Home |
| **当前路由** | `/` |
| **当前 Vue 文件** | `views/HomeView.vue` |
| **当前模块** | System |
| **处置结论** | KEEP |
| **目标页面名称** | Home |
| **目标路由** | `/` |
| **合并目标** | — |
| **保留的核心能力** | Welcome hero (auth-aware CTA), research entry card |
| **删除或隐藏的内容** | System health check dashboard (Backend/DB/Redis/ES/Minio status cards, refresh button) — moved to admin System Operations. Version info + environment tag — moved to admin System Operations. Research entry CTA de-duplicated with new Project List. |
| **处置理由** | Public landing page must exist as entry point. Health check exposes internal infrastructure detail to end users — violates product boundary. Auth-aware CTA directs to research or login. |
| **前置依赖** | Admin System Operations page must exist before removing health check. New Project List must exist before removing research CTA. |
| **风险说明** | Low. Simple content removal. Health check store (`useSystemStore`) may still be used elsewhere — verify before removing store import. |

### 2. Search

| Field | Value |
|-------|-------|
| **当前页面名称** | 全局搜索 / Search |
| **当前路由** | `/search` |
| **当前 Vue 文件** | `views/SearchView.vue` |
| **当前模块** | Research (current inventory placement) |
| **处置结论** | MERGE |
| **目标页面名称** | Library Search |
| **目标路由** | `/library/search` |
| **合并目标** | Library Search ← Search + Books List + Persons List + Classical Versions List |
| **保留的核心能力** | Full-text search with autocomplete suggestions, entity type filter chips, dynasty facet filter, search result cards with highlighted snippets, pagination. `?q=` query param for deep-linking. |
| **删除或隐藏的内容** | "Add to topic" quick-action button (research coupling — belongs in Research Workspace, not Library). Paper entity type filter (no paper detail page exists). `researchStore` dependency. |
| **处置理由** | Search is a Library function, not a Research function. Filter chips for person/book/passage/version entity types belong in a unified library search surface. Deduplicates 4 separate list pages into one search experience. |
| **前置依赖** | Unified search API must support all entity types with consistent response shape. BookListView and PersonListView currently use `EntityListPage` which wraps `GET /api/v1/books` and `GET /api/v1/persons` — these endpoints must be queryable through search. |
| **风险说明** | Medium. Merging 4 list pages into one search surface requires API alignment. Book, person, and version entities have different metadata fields — result card must handle polymorphic display. Faceted search by dynasty/category/era must be server-supported. |

### 3. Documents (Placeholder)

| Field | Value |
|-------|-------|
| **当前页面名称** | 文献(占位) / Documents |
| **当前路由** | `/documents` |
| **当前 Vue 文件** | `views/DocumentsView.vue` |
| **当前模块** | Library |
| **处置结论** | RETIRE |
| **目标页面名称** | — (deleted) |
| **目标路由** | — (removed) |
| **合并目标** | — |
| **保留的核心能力** | None. Entire file is a one-line delegation to `PlaceholderPage`. |
| **删除或隐藏的内容** | Route `/documents` removed. File `DocumentsView.vue` deleted. Component `PlaceholderPage.vue` deleted (no other consumers). |
| **处置理由** | Placeholder "coming soon" page with no functionality. Real literature list lives at `/literature` (→ REBUILD as Library Search + Document Management). The name "Documents" conflicts with "Literature" — domain concept duplicated. |
| **前置依赖** | Navbar and any hard-coded links to `/documents` must be updated to `/library/search`. |
| **风险说明** | Low. Verify no external bookmarks or links reference `/documents`. Add redirect `/documents` → `/library/search` during migration window. |

### 4. About

| Field | Value |
|-------|-------|
| **当前页面名称** | 关于 / About |
| **当前路由** | `/about` |
| **当前 Vue 文件** | `views/AboutView.vue` |
| **当前模块** | System |
| **处置结论** | KEEP |
| **目标页面名称** | About |
| **目标路由** | `/about` |
| **合并目标** | — |
| **保留的核心能力** | Vision statement. |
| **删除或隐藏的内容** | Tech stack display grid (FastAPI, Vue 3, PostgreSQL, Elasticsearch, Neo4j, Milvus) — exposes implementation detail. Replace with user-facing capability descriptions. |
| **处置理由** | Vision page is standard for research platforms. Tech stack enumeration is internal implementation detail — violates product boundary (Neo4j, Elasticsearch, Milvus are named explicitly). |
| **前置依赖** | None. Purely static content change. |
| **风险说明** | Minimal. Static page. |

### 5. Login

| Field | Value |
|-------|-------|
| **当前页面名称** | 登录 / Login |
| **当前路由** | `/login` |
| **当前 Vue 文件** | `views/LoginView.vue` |
| **当前模块** | Authentication |
| **处置结论** | KEEP |
| **目标页面名称** | Login |
| **目标路由** | `/login` |
| **合并目标** | — |
| **保留的核心能力** | Username/password form, auth store integration, redirect-after-login, value-proposition sidebar, guest-only guard (`meta: { guest: true }`). |
| **删除或隐藏的内容** | None. |
| **处置理由** | Core authentication flow. No changes needed. |
| **前置依赖** | Auth store and API remain unchanged. |
| **风险说明** | Minimal. No functional changes. May need visual rebranding alignment with new design system. |

### 6. Register

| Field | Value |
|-------|-------|
| **当前页面名称** | 注册 / Register |
| **当前路由** | `/register` |
| **当前 Vue 文件** | `views/RegisterView.vue` |
| **当前模块** | Authentication |
| **处置结论** | KEEP |
| **目标页面名称** | Register |
| **目标路由** | `/register` |
| **合并目标** | — |
| **保留的核心能力** | Registration form (username/email/displayName/password), client-side validation, server-side validation error display, auto-login after registration. |
| **删除或隐藏的内容** | None. |
| **处置理由** | Core authentication flow. No changes needed. |
| **前置依赖** | Auth store and API remain unchanged. |
| **风险说明** | Minimal. May need visual rebranding. |

### 7. Books List

| Field | Value |
|-------|-------|
| **当前页面名称** | 典籍列表 / Books |
| **当前路由** | `/books` |
| **当前 Vue 文件** | `views/BookListView.vue` |
| **当前模块** | Library |
| **处置结论** | MERGE |
| **目标页面名称** | Library Search |
| **目标路由** | `/library/search?type=book` |
| **合并目标** | Library Search ← Books List + Persons List + Classical Versions List + Search |
| **保留的核心能力** | Book title/dynasty/category listing, route to book detail (→ Document Detail). |
| **删除或隐藏的内容** | Standalone `/books` route. `EntityListPage` dependency (books become a filter in unified Library Search). `t('nav.documents')` title label (incorrect — shows "文献" for a books list). |
| **处置理由** | Book browsing is a filtered view of the library, not a separate page. `EntityListPage` is a thin wrapper with only 2 consumers — merging into Library Search eliminates the component. Title label bug ("文献" for "典籍") is fixed by removal. |
| **前置依赖** | Library Search must support `?type=book` filter with book-specific columns (title, dynasty, category). |
| **风险说明** | Low. Straightforward merge into faceted search. `EntityListPage.vue` must be verified for no other consumers before removal. |

### 8. Book Detail

| Field | Value |
|-------|-------|
| **当前页面名称** | 典籍详情 / Book Detail |
| **当前路由** | `/books/:id` |
| **当前 Vue 文件** | `views/BookDetailView.vue` |
| **当前模块** | Library |
| **处置结论** | MERGE |
| **目标页面名称** | Document Detail |
| **目标路由** | `/library/:docId` |
| **合并目标** | Document Detail ← Book Detail + Literature Detail + Version Detail (metadata portion) |
| **保留的核心能力** | Title/dynasty/category/year display, abstract, chapters list, versions list (clickable → Document Reader). |
| **删除或隐藏的内容** | Standalone `/books/:id` route. Direct `api.get` calls (replaced by unified document API). Separate chapters/versions API calls (unified in single document response). |
| **处置理由** | Book, literature, and version are all "documents" in the domain model — three nearly identical detail pages with slight field variations. A unified Document Detail with conditional sections reduces duplication and user confusion. |
| **前置依赖** | Unified document API must return book metadata + chapters + versions in single response. `GET /api/v1/documents/:id` already exists; needs extension to include chapters and versions for book-type documents. |
| **风险说明** | Medium. Chapters are fetched via `GET /api/v1/chapters?limit=100` with client-side `book_id` filter — inefficient for large datasets. Versions similarly fetched via `GET /api/v1/versions?limit=100`. These need server-side filtering by `book_id`. |

### 9. Version Detail

| Field | Value |
|-------|-------|
| **当前页面名称** | 版本详情 / Version Detail |
| **当前路由** | `/versions/:id` |
| **当前 Vue 文件** | `views/VersionDetailView.vue` |
| **当前模块** | Library |
| **处置结论** | REBUILD |
| **目标页面名称** | Document Reader |
| **目标路由** | `/library/:docId/read` |
| **合并目标** | — |
| **保留的核心能力** | Fulltext passages list with order numbers, scroll-to-passage anchor (`?passage=xxx`), passage translation display. |
| **删除或隐藏的内容** | Version metadata display (era, repository, editor, shelf_mark, year, description, source URL) — moved to Document Detail. Standalone `/versions/:id` route. Back button (inconsistent with other pages). |
| **处置理由** | Version Detail serves two distinct user needs: (1) read the full text — becomes Document Reader; (2) inspect metadata — becomes Document Detail. Current page conflates both, creating a cluttered layout. Splitting into focused pages improves the reading experience. |
| **前置依赖** | Document Detail must exist for metadata. Document Reader must receive `docId` and `passage` params. Current `GET /api/v1/versions/:id/passages?limit=500` hard-codes limit — needs pagination for large texts. |
| **风险说明** | Medium. Search results currently link to `/versions/:id?passage=xxx` — all search-to-version links must be updated. Graph Explorer entity deep-links to versions must be updated. |

### 10. Persons List

| Field | Value |
|-------|-------|
| **当前页面名称** | 人物列表 / Persons |
| **当前路由** | `/persons` |
| **当前 Vue 文件** | `views/PersonListView.vue` |
| **当前模块** | Library |
| **处置结论** | MERGE |
| **目标页面名称** | Knowledge Explorer |
| **目标路由** | `/knowledge?type=person` |
| **合并目标** | Knowledge Explorer ← Persons List + Graph Explorer (entity search) |
| **保留的核心能力** | Person name/dynasty/expertise listing, route to person detail (→ Entity Detail). |
| **删除或隐藏的内容** | Standalone `/persons` route. `EntityListPage` dependency. |
| **处置理由** | Person browsing is an entity exploration activity, not a library function. Merging into Knowledge Explorer aligns with domain model: persons are entities in the knowledge graph. `EntityListPage` is retired as a side effect (only 2 consumers, both merging). |
| **前置依赖** | Knowledge Explorer must support entity-type filtered browsing with person-specific columns. |
| **风险说明** | Low. EntityListPage abstraction is lightweight. The label "典籍" on BookListView is already broken (shows "文献") — removing the component is net positive. |

### 11. Person Detail

| Field | Value |
|-------|-------|
| **当前页面名称** | 人物详情 / Person Detail |
| **当前路由** | `/persons/:id` |
| **当前 Vue 文件** | `views/PersonDetailView.vue` |
| **当前模块** | Library |
| **处置结论** | REBUILD |
| **目标页面名称** | Entity Detail |
| **目标路由** | `/knowledge/:entityType/:entityId` |
| **合并目标** | — |
| **保留的核心能力** | Name/alt names display, dynasty/life span/expertise tags, biography with source, notable works list. `useEntityDetail` composable pattern (generic, reusable). |
| **删除或隐藏的内容** | Person-specific field layout. `birth_place`, `courtesy_name`, `pseudonym`, `external_ref` become generic metadata fields. Standalone `/persons/:id` route. |
| **处置理由** | Entity Detail generalizes Person Detail to support any knowledge graph entity type (person, book, version, passage). The `useEntityDetail` composable is already generic — the view just needs to render metadata dynamically instead of hard-coding person fields. Graph Explorer currently shows entity properties in a sidebar `<dl>` — Entity Detail provides a full-page version. |
| **前置依赖** | Generic entity detail API (`GET /api/v1/graph/entity/:type/:id`) already exists and returns properties. Must return sufficient metadata for a full detail page (currently returns graph-focused data). |
| **风险说明** | Medium. Generic rendering of unknown property keys requires a metadata display strategy (priority ordering, type-aware formatting). Book entities in the graph have different fields than person entities — the detail page must handle both without hard-coded sections. |

### 12. Graph Explorer

| Field | Value |
|-------|-------|
| **当前页面名称** | 知识图谱浏览器 / Graph Explorer |
| **当前路由** | `/graph` |
| **当前 Vue 文件** | `views/GraphExplorerView.vue` |
| **当前模块** | Knowledge |
| **处置结论** | REBUILD |
| **目标页面名称** | Knowledge Explorer |
| **目标路由** | `/knowledge` |
| **合并目标** | Knowledge Explorer ← Graph Explorer + Persons List |
| **保留的核心能力** | Entity search with type filters, graph canvas (via `GraphCanvas` component), neighborhood/subgraph exploration, path finding, `?type=&id=` and `?trace=` deep-linking, node detail sidebar. |
| **删除或隐藏的内容** | Inline path-finding panel (promote to dedicated interaction). Sidebar-only entity detail (moved to full-page Entity Detail). |
| **处置理由** | "Graph" is an implementation concept. "Knowledge Explorer" describes what the user does: explore connected knowledge. The current page is feature-complete but the sidebar entity detail is cramped — full-page Entity Detail provides a better experience. Entity browsing (persons) merges into the same tool. |
| **前置依赖** | Entity Detail page must exist for click-through from graph nodes. `GraphCanvas` component must be preserved. |
| **风险说明** | Low. Rename + route change only. GraphCanvas is a self-contained component. Deep-links with `?trace=` must be preserved. |

### 13. Research — New Topic

| Field | Value |
|-------|-------|
| **当前页面名称** | 创建新研究课题 / New Research Topic |
| **当前路由** | `/research/new` |
| **当前 Vue 文件** | `views/ResearchNewView.vue` |
| **当前模块** | Research |
| **处置结论** | MERGE |
| **迁移状态** | 已迁移到新版 ProjectListPage (2026-07-17, commit 904a42a) |
| **目标页面名称** | Project List |
| **目标路由** | `/research` |
| **合并目标** | Project List ← Research New (inline creation) + Project list (new) |
| **保留的核心能力** | Topic name + description form, research store integration, redirect to project detail. |
| **删除或隐藏的内容** | Standalone `/research/new` route. Dedicated creation page — replaced by inline creation within Project List. |
| **处置理由** | A single-input form does not justify a dedicated page. Research store currently supports only one active topic — Project List must be extended to support multiple projects. Creation becomes an inline action (modal or expandable form) within the project list. |
| **前置依赖** | Research store must support multiple projects (currently single-topic `setTopic`/`clearTopic`). Project persistence requires backend API (currently client-side only). |
| **风险说明** | High. The research store (`useResearchStore`) is a client-side singleton with no server persistence. Converting to multi-project with server-backed storage is a significant data model change. This is the highest-risk merge in the disposition. |

### 14. Research — Home

| Field | Value |
|-------|-------|
| **当前页面名称** | 研究课题首页 / Research Home |
| **当前路由** | `/research/home` |
| **当前 Vue 文件** | `views/ResearchHomeView.vue` |
| **当前模块** | Research |
| **处置结论** | REBUILD |
| **迁移状态** | 已迁移到新版 ProjectDetailPage (2026-07-17) |
| **目标页面名称** | Project Detail |
| **目标路由** | `/research/:projectId` |
| **目标 Vue 文件** | `pages/research/ProjectDetailPage.vue` |
| **合并目标** | — |
| **保留的核心能力** | Current topic header (name + description), tools grid linking to workspace/reports/books/graph/assistant, end-research action, auto-redirect guard (no active research → home). |
| **删除或隐藏的内容** | Direct links to Books and Graph (replaced by Library Search and Knowledge Explorer in global nav). Dashboard link (dashboard becomes redirect). Tools grid restructured to match new target pages: Workspace, Workflow, Reports, Notes, Library Search. |
| **处置理由** | Research Home is the project hub. Renamed to Project Detail for clarity. Tools grid must reflect the new page architecture. The auto-redirect guard is preserved but scoped to `:projectId`. |
| **前置依赖** | All linked target pages must exist (Research Workspace, Research Workflow, Report List, Notes and Evidence). Research store must support `:projectId` parameter. |
| **风险说明** | Medium. Hard-coded router links in the tools grid must all be updated. `watch` on `store.hasActiveResearch` guarding redirect must be adapted to project-scoped state. |
| **迁移备注** | 详情页已实现：课题概览、研究活动、报告、笔记四区块，含编辑/删除功能。数据源：`GET/PATCH/DELETE /api/v1/workspace/sessions/{id}` + `/api/v4/research/session/{id}/history` + `/api/v4/research/session/{id}/runs` + `/api/v1/workspace/sessions/{id}/notes`。无 status 字段，context_notes 作为课题说明。详见 `docs/20-product/2012-project-detail-migration.md`。 |

### 15. Research — Workspace

| Field | Value |
|-------|-------|
| **当前页面名称** | 研究工作台 / Research Workspace |
| **当前路由** | `/research/workspace` |
| **当前 Vue 文件** | `views/ResearchWorkspaceView.vue` |
| **当前模块** | Research |
| **处置结论** | REBUILD |
| **迁移状态** | 已迁移到新版 ResearchWorkspacePage (2026-07-17) |
| **目标页面名称** | Research Workspace |
| **目标路由** | `/research/:projectId/workspace` |
| **目标 Vue 文件** | `pages/research/ResearchWorkspacePage.vue` |
| **合并目标** | — |
| **保留的核心能力** | AI Assistant entry (question → workflow), Continue Research card (resumable run detection), Recent Activity (query history), Recent Reports (workflow runs), Recent Notes (session-scoped), Research Resources (citation collection). |
| **删除或隐藏的内容** | Materials tab → Library Search. Versions tab → Library Search. Notes tab → reduced to Recent Notes sidebar. Reports tab → reduced to Recent Reports block. Inline V4 workflow → promoted to standalone ResearchWorkflowPage. Inline version comparison → promoted to standalone ResearchWorkflowPage. 7-tab mega-component → replaced with focused single-purpose components. `?tab=` query param routing → replaced with actual routes. Inline AI chat (SSE) → deferred to future AI Assistant page. |
| **处置理由** | The 7-tab workspace is a monolithic anti-pattern. Each tab is effectively a separate page. Splitting into focused pages with proper routes improves code maintainability, URL shareability, performance (lazy-load), and user mental model (clear navigation instead of hidden tabs). |
| **前置依赖** | Continued by: AI Assistant page (chat), standalone Notes & Evidence page. |
| **风险说明** | The current backend executes workflows synchronously — no resume API exists. ContinueResearchCard defaults to "开始新研究". AI chat (SSE streaming) is deferred. Education and Visualization modes from V4ResearchView are not yet absorbed. |
| **迁移备注** | 工作区已实现：ContinueResearchCard、RecentResearchActivity (max 5 via `?limit=5`)、RecentReports (client-side sort by completed_at, max 5)、RecentNotes (max 5)、ResearchResources (citations, session_id filter, max 5)、ResearchAssistantEntry (sessionStorage → workflow)。无 AI 直接调用、无伪造数据、无跨课题泄露、无 project_id。数据源：`GET /api/v1/workspace/sessions/{id}` (page-level) + 4 独立区块 API。所有区块独立 loading/empty/error 状态，区块失败不阻断整页。详见 `docs/20-product/2013-research-workspace-migration.md`。 |

### 16. V4 Research (Standalone)

| Field | Value |
|-------|-------|
| **当前页面名称** | V4 研究 / V4 Research |
| **当前路由** | `/v4/research-internal` |
| **当前 Vue 文件** | `views/V4ResearchView.vue` |
| **当前模块** | Research |
| **处置结论** | MERGE |
| **目标页面名称** | Research Workspace + Research Workflow + Research Result + Knowledge Explorer |
| **目标路由** | `/research/:projectId/workspace` + `/research/:projectId/workflow` + `/research/:projectId/result/:runId` + `/knowledge` |
| **合并目标** | Research Workspace ← V4 Research tab. **Research Workflow ← V4 full research flow (MIGRATED → `pages/research/ResearchWorkflowPage.vue`)**. Research Result ← V4 report detail + citations + export + replay. Knowledge Explorer ← V4 Education + Visualization tabs. |
| **保留的核心能力** | Full V4 workflow (topic → 5-step pipeline → report + citations + export + note + replay). Education mode (concept learning with levels). Visualization mode (concept/citation/timeline/document graphs). |
| **删除或隐藏的内容** | Standalone `/v4/research-internal` route (unreachable by normal navigation). Duplicate workflow execution logic (already in ResearchWorkspaceView v4-research tab). Duplicate citation extraction, export, note-saving logic. `V4ResearchView.vue` file (merged, not deleted until all capabilities absorbed). |
| **处置理由** | V4 workflow is fully duplicated between V4ResearchView and ResearchWorkspaceView. Research workflow tab migrated to standalone ResearchWorkflowPage with composable architecture. Education and Visualization are knowledge exploration features — they belong in Knowledge Explorer. The standalone route is inaccessible via normal UI. |
| **前置依赖** | Knowledge Explorer must support education concept display and graph visualization rendering. ~~Research Workspace must absorb the V4 workflow tab capabilities before V4ResearchView can be retired.~~ **DONE: Research workflow migrated to `ResearchWorkflowPage.vue` at `/research/:projectId/workflow`**. |
| **风险说明** | Medium. Education and Visualization modes call `/api/v4/education/learn` and `/api/v4/visualization/graph` — these APIs are V4-specific. Knowledge Explorer currently uses `/api/v1/graph/*` endpoints. API alignment needed. Duplicate logic consolidated into `useResearchWorkflow` composable. |
| **迁移备注** | 研究流程已迁移至 `pages/research/ResearchWorkflowPage.vue`，使用 `composables/useResearchWorkflow.ts` 统一管理所有状态和请求。五步组件拆分至 `components/research/workflow/`。详见 `docs/20-product/2014-research-workflow-migration.md`。 |

### 17. Research — Workflow (Embedded)

| Field | Value |
|-------|-------|
| **当前页面名称** | 版本校勘工作流 / Version Comparison Workflow |
| **当前路由** | None (embedded in `ResearchWorkspaceView` research tab) |
| **当前 Vue 文件** | `views/ResearchWorkflowView.vue` |
| **当前模块** | Research |
| **处置结论** | KEEP (promoted to standalone route) |
| **目标页面名称** | Research Workflow |
| **目标路由** | `/research/:projectId/workflow` |
| **合并目标** | — |
| **保留的核心能力** | 4-step version comparison workflow: (1) search passages, (2) select source/target, (3) diff comparison with operation table, (4) evidence verification + notes. Auto-restore last session. Export Markdown. `researchStore` integration. |
| **删除或隐藏的内容** | Embedded rendering inside ResearchWorkspaceView → replaced by `<router-view>` or navigation. |
| **处置理由** | Version comparison is a focused research tool that deserves its own route and URL. Currently buried in a workspace tab, invisible to URL sharing. Promotion improves discoverability and enables direct linking to comparison sessions. |
| **前置依赖** | Must receive `:projectId` param. Session auto-restore must be scoped to project. |
| **风险说明** | Low. Component is already self-contained. Simply needs a route entry and project context. The embedded import in ResearchWorkspaceView (`import ResearchWorkflowView from ...`) is replaced by a `<router-link>`. |

### 18. Dashboard

| Field | Value |
|-------|-------|
| **当前页面名称** | 仪表盘 / Dashboard |
| **当前路由** | `/dashboard` |
| **当前 Vue 文件** | `views/DashboardView.vue` |
| **当前模块** | System |
| **处置结论** | REDIRECT_ONLY |
| **目标页面名称** | — (redirect to Home) |
| **目标路由** | `/` |
| **合并目标** | Dashboard components absorbed by: Home (research entry card), Knowledge Explorer (dynasty/category charts), System Operations admin (system info, entity counts, activity feed). |
| **保留的核心能力** | Entity count stats → System Operations. Dynasty/category distribution charts → Knowledge Explorer. Research entry card → Home (already present). Onboarding step guide → Home. |
| **删除或隐藏的内容** | Standalone `/dashboard` route (becomes redirect). Public-facing stats dashboard. `GET /api/v1/dashboard/stats` and `GET /api/v1/dashboard/overview` calls from public context. |
| **处置理由** | Public dashboard with entity counts and system info exposes operational data to end users. Research users do not need to see "users: N" or "environment: production". Entity distribution charts are knowledge exploration, not a dashboard. System info belongs in admin-only System Operations. |
| **前置依赖** | System Operations admin page must exist. Knowledge Explorer must render dynasty/category charts. |
| **风险说明** | Low. Content is redistributed, not lost. DashboardView.vue is preserved until all consumers of its data are migrated. |

### 19. Literature List

| Field | Value |
|-------|-------|
| **当前页面名称** | 文献列表 / Literature List |
| **当前路由** | `/literature` |
| **当前 Vue 文件** | `views/literature/LiteratureListView.vue` |
| **当前模块** | Library |
| **处置结论** | REBUILD (split into two) |
| **目标页面名称** | Library Search (public) + Document Management (admin) |
| **目标路由** | `/library/search` + `/admin/documents` |
| **合并目标** | — |
| **保留的核心能力** | Public: search + paginated list. Admin: copyright status filter, review status filter, RAG enabled filter, withdrawn status, click-through to document detail. |
| **删除或隐藏的内容** | Public-facing review status, copyright status, and RAG columns (admin-only data). Admin actions exposed in public list. `DataTable` dependency (admin path keeps it; public path uses Library Search result cards). |
| **处置理由** | Literature list currently exposes admin columns (copyright, review, RAG, withdrawn) to all users — data that should only be visible to reviewers. Splitting into public Library Search (discovery) and admin Document Management (governance) enforces the administration isolation boundary. |
| **前置依赖** | Library Search must support document-type results. Document Management admin page must replicate the review queue filtering. |
| **风险说明** | Medium. Two paths diverge from one API endpoint (`GET /api/v1/documents`). Admin path can keep current `DataTable`; public path needs result-card rendering consistent with Library Search. |

### 20. Literature Detail

| Field | Value |
|-------|-------|
| **当前页面名称** | 文献详情 / Literature Detail |
| **当前路由** | `/literature/:id` |
| **当前 Vue 文件** | `views/literature/LiteratureDetailView.vue` |
| **当前模块** | Library |
| **处置结论** | REBUILD |
| **目标页面名称** | Document Detail |
| **目标路由** | `/library/:docId` |
| **合并目标** | Document Detail ← Literature Detail + Book Detail |
| **保留的核心能力** | Compliance panel (copyright, license, review status), fulltext with expand/collapse + chapter navigation, metadata grid, abstract, admin actions (review, RAG toggle, withdraw), "Ask AI" button. |
| **删除或隐藏的内容** | Admin actions section — moved to Document Management (admin-only). Compliance panel — visible only to authenticated users with review permission. `content_text` fulltext display — moved to Document Reader for focused reading. Chapter navigation — preserved in Document Reader. Direct `PATCH /api/v1/documents/:id/review` and `POST .../withdraw` calls — moved to admin context. |
| **处置理由** | Literature Detail mixes public reading, metadata inspection, and admin governance in one page. Splitting into Document Detail (metadata + compliance for auth users) and Document Reader (fulltext reading for all) creates focused, permission-appropriate experiences. Admin actions are extracted to Document Management. |
| **前置依赖** | Document Reader must exist for fulltext + chapter navigation. Document Management must expose review/RAG/withdraw actions. Unified document API (`GET /api/v1/documents/:id`) must return book-type fields when applicable. |
| **风险说明** | Medium. `content_text` reading and chapter navigation are tightly coupled in the current expand/collapse + scroll-to-offset implementation. Decoupling into Document Reader requires preserving the scroll behavior. `parseChapterNav()` regex is specific to 四庫全書 format — must be generalized for any document. |

### 21. Classical Versions List

| Field | Value |
|-------|-------|
| **当前页面名称** | 古籍版本库 / Classical Versions |
| **当前路由** | `/classical-versions` |
| **当前 Vue 文件** | `views/classical-versions/ClassicalVersionListView.vue` |
| **当前模块** | Library |
| **处置结论** | MERGE |
| **目标页面名称** | Library Search |
| **目标路由** | `/library/search?type=version` |
| **合并目标** | Library Search ← Classical Versions List + Books List + Persons List + Search |
| **保留的核心能力** | Version search by work title/version name/repository, public domain status + review status filters (admin-only in merged view), paginated table. |
| **删除或隐藏的内容** | Standalone `/classical-versions` route. `DataTable` dependency (replaced by Library Search result cards). Public domain and review status columns hidden for non-admin users. Requires-auth guard (`requiresAuth`) — classical versions browsing should be public. |
| **处置理由** | Version browsing is library discovery. The current `requiresAuth` guard is inconsistent with Books (`/books` is public) and Literature (`/literature` is public). Merging into Library Search fixes the permission inconsistency. Admin-only columns (review, public domain status) are conditionally shown. |
| **前置依赖** | Library Search must support `?type=version` filter. API endpoint differs from other library endpoints (`/api/classical-versions` vs `/api/v1/documents`) — needs alignment. |
| **风险说明** | Low. DataTable to result-card conversion is straightforward. Permission relaxation from `requiresAuth` to public is intentional — versions are published scholarly resources. |

### 22. Admin — Literature Review Queue

| Field | Value |
|-------|-------|
| **当前页面名称** | 全文审核队列 / Literature Review Queue |
| **当前路由** | `/admin/literature-review` |
| **当前 Vue 文件** | `views/admin/LiteratureReviewQueue.vue` |
| **当前模块** | Administration |
| **处置结论** | REBUILD |
| **目标页面名称** | Document Management |
| **目标路由** | `/admin/documents` |
| **合并目标** | Document Management ← Literature Review Queue + Literature Detail (admin actions) |
| **保留的核心能力** | Review queue with review status + copyright status filters, paginated table, click-through to document detail, `DataTable` usage. |
| **删除或隐藏的内容** | Admin actions currently scattered in Literature Detail (review, RAG toggle, withdraw) — consolidated into Document Management. Hard-coded Chinese labels (not i18n). Duplicate `COPYRIGHT_STATUSES`/`REVIEW_STATUSES` constants (also defined in LiteratureListView and LiteratureDetailView). |
| **处置理由** | Review queue is one function of document management. Consolidating review/govemance actions from Literature Detail into Document Management creates a single admin surface for all document operations. Extracted constants (copyright/review statuses) into shared config. |
| **前置依赖** | Document Management page must include inline review/RAG/withdraw actions (currently in LiteratureDetailView). Shared constants extracted to `constants/documents.ts`. |
| **风险说明** | Low. The review queue page is a thin wrapper around `DataTable` with filters. Adding inline actions requires modal or expandable row pattern. |

### 23. Admin — Ingestion Tasks

| Field | Value |
|-------|-------|
| **当前页面名称** | 采集任务记录 / Ingestion Tasks |
| **当前路由** | `/admin/ingestion-tasks` |
| **当前 Vue 文件** | `views/admin/IngestionTasksView.vue` |
| **当前模块** | Administration |
| **处置结论** | REBUILD |
| **目标页面名称** | Data Quality |
| **目标路由** | `/admin/data-quality` |
| **合并目标** | — |
| **保留的核心能力** | Task log with action/status/source filters, paginated table, `DataTable` usage, action type labels. |
| **删除或隐藏的内容** | Hard-coded Chinese labels. Technical implementation labels exposed to admin UI: `chunk_delete`, `rag_disabled`, `fulltext_ingest` — replaced with user-facing descriptions. |
| **处置理由** | "Ingestion Tasks" is a pipeline implementation name. "Data Quality" describes the admin's concern: is the data pipeline healthy? Rebuilding around data quality adds: success/failure rates, source coverage metrics, recent errors summary. The task log becomes one tab/section within Data Quality. |
| **前置依赖** | API must provide aggregated quality metrics in addition to raw task log. `GET /api/v1/ingestion/tasks` currently returns flat list — needs companion stats endpoint. |
| **风险说明** | Low. Page is a thin `DataTable` wrapper. Extension to quality dashboard is additive. |

### 24. Admin — Source Policy

| Field | Value |
|-------|-------|
| **当前页面名称** | 来源白名单管理 / Source Policy |
| **当前路由** | `/admin/source-policy` |
| **当前 Vue 文件** | `views/admin/SourcePolicyView.vue` |
| **当前模块** | Administration |
| **处置结论** | REBUILD |
| **目标页面名称** | System Operations |
| **目标路由** | `/admin/system` |
| **合并目标** | System Operations ← Source Policy + Dashboard (system info) |
| **保留的核心能力** | Source policy CRUD (add/enable/disable/delete), event delegation for inline actions, `DataTable` usage. |
| **删除或隐藏的内容** | Inline HTML button rendering via `render()` (vulnerable to XSS — replace with slot-based actions). Event delegation on `.data-table-wrapper` (fragile, breaks if wrapper class changes). Hard-coded Chinese labels. |
| **处置理由** | "Source Policy" is one system configuration concern. System Operations consolidates all operational config: source policies, system health (from HomeView), version/environment info (from DashboardView), and other system-level settings. |
| **前置依赖** | System health check (`GET /api/v1/health`) and system info APIs must be accessible in admin context. Dashboard system info data must be migrated. |
| **风险说明** | Medium. Inline HTML rendering with event delegation is fragile — replacing with proper Vue event handling requires component restructuring. The `data-id`/`data-action` attribute pattern must be replaced with `@click` handlers. |

### 25. Workspace (Legacy)

| Field | Value |
|-------|-------|
| **当前页面名称** | 工作区 (旧版) / Workspace (Legacy) |
| **当前路由** | None (unreachable) |
| **当前 Vue 文件** | `views/WorkspaceView.vue` |
| **当前模块** | Research |
| **处置结论** | RETIRE |
| **目标页面名称** | — (file deleted) |
| **目标路由** | — |
| **合并目标** | — |
| **保留的核心能力** | None. All functionality superseded by ResearchWorkspaceView. |
| **删除或隐藏的内容** | Entire file. Three-panel layout, session management, notes CRUD, AI chat with SSE, evidence panel — all duplicated in ResearchWorkspaceView. `window.prompt()` for note input (accessibility anti-pattern). |
| **处置理由** | Abandoned code with no route. All capabilities exist in ResearchWorkspaceView. No migration needed — nothing references this file. |
| **前置依赖** | None. Verify zero imports: `grep -r "WorkspaceView" apps/frontend/src/` should return only the file itself. |
| **风险说明** | Low. File is already dead code. The only risk is an undiscovered dynamic import. |

---

## Final Route Map

```
# Public
/                                           → Home (System)
/about                                      → About (System)
/login                                      → Login (Authentication)
/register                                   → Register (Authentication)
/access-denied                              → Access Denied (Authentication)        [NEW]
/not-found                                  → Not Found (System)                    [NEW]
/error                                      → Error State (System)                  [NEW]

# Library (public)
/library/search                             → Library Search (Library)
/library/:docId                             → Document Detail (Library)
/library/:docId/read                        → Document Reader (Library)
/library/:docId/citation/:citId             → Citation Detail (Library)             [NEW]

# Knowledge (public)
/knowledge                                  → Knowledge Explorer (Knowledge)
/knowledge/:entityType/:entityId            → Entity Detail (Knowledge)

# Research (authenticated)
/research                                   → Project List (Research)
/research/:projectId                        → Project Detail (Research)
/research/:projectId/workspace              → Research Workspace (Research)
/research/:projectId/workflow               → Research Workflow (Research)
/research/:projectId/result/:runId          → Research Result (Research)

# Reports (authenticated)
/reports                                    → Report List (Reports)
/reports/:runId                             → Report Detail (Reports)
/notes                                      → Notes and Evidence (Reports)

# Administration (authenticated + admin)
/admin/documents                            → Document Management (Administration)
/admin/data-quality                         → Data Quality (Administration)
/admin/users                                → User and Permission Management (Admin) [NEW]
/admin/system                               → System Operations (Administration)

# Redirects (legacy → new)
/workspace          → /research/:projectId/workspace       [REDIRECT_ONLY]
/research           → /research                             [REDIRECT_ONLY — already matches, remove old redirect logic]
/v4/research        → /research/:projectId/workspace       [REDIRECT_ONLY]
/v4                 → /research/:projectId/workspace       [REDIRECT_ONLY]
/dashboard          → /                                     [REDIRECT_ONLY]
/search             → /library/search                       [REDIRECT_ONLY, temporary migration redirect]
/books              → /library/search?type=book             [REDIRECT_ONLY, temporary migration redirect]
/books/:id          → /library/:id                          [REDIRECT_ONLY, temporary migration redirect]
/versions/:id       → /library/:id/read                     [REDIRECT_ONLY, temporary migration redirect]
/persons            → /knowledge?type=person                [REDIRECT_ONLY, temporary migration redirect]
/persons/:id        → /knowledge/person/:id                 [REDIRECT_ONLY, temporary migration redirect]
/graph              → /knowledge                            [REDIRECT_ONLY, temporary migration redirect]
/literature         → /library/search                       [REDIRECT_ONLY, temporary migration redirect]
/literature/:id     → /library/:id                          [REDIRECT_ONLY, temporary migration redirect]
/classical-versions → /library/search?type=version          [REDIRECT_ONLY, temporary migration redirect]
/documents          → /library/search                       [REDIRECT_ONLY, temporary migration redirect]
```

---

## Migration Matrix

| 当前路由 | 当前文件 | 目标路由 | 目标页面 | 处置结论 |
|---------|---------|---------|---------|---------|
| `/` | `views/HomeView.vue` | `/` | Home | KEEP |
| `/search` | `views/SearchView.vue` | `/library/search` | Library Search | MERGE |
| `/documents` | `views/DocumentsView.vue` | — | — | RETIRE |
| `/about` | `views/AboutView.vue` | `/about` | About | KEEP |
| `/login` | `views/LoginView.vue` | `/login` | Login | KEEP |
| `/register` | `views/RegisterView.vue` | `/register` | Register | KEEP |
| `/books` | `views/BookListView.vue` | `/library/search?type=book` | Library Search | MERGE |
| `/books/:id` | `views/BookDetailView.vue` | `/library/:docId` | Document Detail | MERGE |
| `/versions/:id` | `views/VersionDetailView.vue` | `/library/:docId/read` | Document Reader | REBUILD |
| `/persons` | `views/PersonListView.vue` | `/knowledge?type=person` | Knowledge Explorer | MERGE |
| `/persons/:id` | `views/PersonDetailView.vue` | `/knowledge/person/:entityId` | Entity Detail | REBUILD |
| `/graph` | `views/GraphExplorerView.vue` | `/knowledge` | Knowledge Explorer | REBUILD |
| `/research/new` | `views/ResearchNewView.vue` | `/research` | Project List | MERGE |
| `/research/home` | `views/ResearchHomeView.vue` | `/research/:projectId` | Project Detail | REBUILD |
| `/research/workspace` | `views/ResearchWorkspaceView.vue` | `/research/:projectId/workspace` + `/reports` + `/notes` | Research Workspace + Report List + Notes and Evidence | REBUILD |
| `/v4/research-internal` | `views/V4ResearchView.vue` | `/research/:projectId/workspace` + `/research/:projectId/result/:runId` + `/knowledge` | Research Workspace + Research Result + Knowledge Explorer | MERGE |
| (no route) | `views/ResearchWorkflowView.vue` | `/research/:projectId/workflow` | Research Workflow | KEEP |
| `/dashboard` | `views/DashboardView.vue` | `/` (redirect) | Home + Knowledge Explorer + System Operations | REDIRECT_ONLY |
| `/literature` | `views/literature/LiteratureListView.vue` | `/library/search` + `/admin/documents` | Library Search + Document Management | REBUILD |
| `/literature/:id` | `views/literature/LiteratureDetailView.vue` | `/library/:docId` | Document Detail | REBUILD |
| `/classical-versions` | `views/classical-versions/ClassicalVersionListView.vue` | `/library/search?type=version` | Library Search | MERGE |
| `/admin/literature-review` | `views/admin/LiteratureReviewQueue.vue` | `/admin/documents` | Document Management | REBUILD |
| `/admin/ingestion-tasks` | `views/admin/IngestionTasksView.vue` | `/admin/data-quality` | Data Quality | REBUILD |
| `/admin/source-policy` | `views/admin/SourcePolicyView.vue` | `/admin/system` | System Operations | REBUILD |
| `/workspace` (redirect) | — | `/research/:projectId/workspace` | Research Workspace | REDIRECT_ONLY |
| `/research` (redirect) | — | `/research` | Project List | REDIRECT_ONLY |
| `/v4/research` (redirect) | — | `/research/:projectId/workspace` | Research Workspace | REDIRECT_ONLY |
| `/v4` (redirect) | — | `/research/:projectId/workspace` | Research Workspace | REDIRECT_ONLY |
| (no route) | `views/WorkspaceView.vue` | — | — | RETIRE |
| — | `components/common/PlaceholderPage.vue` | — | — | RETIRE |
| — | — | `/access-denied` | Access Denied | NEW |
| — | — | `/not-found` | Not Found | NEW |
| — | — | `/error` | Error State | NEW |
| — | — | `/admin/users` | User and Permission Management | NEW |
| — | — | `/library/:docId/citation/:citId` | Citation Detail | NEW |

---

## Removal Candidates

### 页面文件 (delete after migration complete)

| 文件 | 理由 |
|------|------|
| `views/DocumentsView.vue` | Placeholder, replaced by Library Search |
| `views/WorkspaceView.vue` | Abandoned legacy, superseded by ResearchWorkspaceView |

### 路由 (remove after redirect window)

| 路由 | 理由 |
|------|------|
| `/documents` | Placeholder, replaced by `/library/search` |
| `/v4/research-internal` | Internal route, V4ResearchView merged into workspace |
| `/search` | Merged into `/library/search` |
| `/books` | Merged into `/library/search?type=book` |
| `/books/:id` | Merged into `/library/:docId` |
| `/versions/:id` | Rebuilt as `/library/:docId/read` |
| `/persons` | Merged into `/knowledge?type=person` |
| `/persons/:id` | Rebuilt as `/knowledge/person/:entityId` |
| `/graph` | Rebuilt as `/knowledge` |
| `/research/new` | Merged into `/research` (Project List) |
| `/research/home` | Rebuilt as `/research/:projectId` |
| `/research/workspace` | Rebuilt as `/research/:projectId/workspace` |
| `/literature` | Split into `/library/search` + `/admin/documents` |
| `/literature/:id` | Rebuilt as `/library/:docId` |
| `/classical-versions` | Merged into `/library/search?type=version` |
| `/dashboard` | Redirect to `/` |
| `/workspace` (redirect) | Update target to `/research/:projectId/workspace` |
| `/v4/research` (redirect) | Update target |
| `/v4` (redirect) | Update target |

### 重复组件 (consolidate during rebuild)

| 组件/模式 | 当前实例数 | 目标 |
|-----------|----------|------|
| Pagination HTML/CSS | 6 copies | Single `<Pagination>` shared component |
| Search input + button | 5 variants | Single `<SearchInput>` shared component |
| Filter bar with `<select>` | 5 copies | Single `<FilterBar>` shared component |
| Loading state | 4+ variants | Single `<LoadingState>` shared component |
| Empty state | 4 variants | Single `<EmptyState>` shared component |
| Card patterns | 8 distinct | Unified card system (3-4 variants max) |
| Spinner CSS | 3 definitions | Single shared spinner component |
| `COPYRIGHT_STATUSES` / `REVIEW_STATUSES` constants | 3 files | `constants/documents.ts` |

### 无引用资源 (verify then delete)

| 资源 | 状态 |
|------|------|
| `components/common/PlaceholderPage.vue` | No consumers after DocumentsView retirement |
| `components/reader/PassageReader.vue` | No consumer found in any view |
| `composables/useTheme.ts` | Not imported in any scanned view (verify before deletion) |

---

## Blocking Issues

### API 不一致

| # | 问题 | 影响 | 阻塞的处置 |
|---|------|------|----------|
| B1 | Library entities use different API prefixes: `GET /api/v1/books`, `GET /api/v1/persons`, `GET /api/v1/versions`, `GET /api/v1/documents`, `GET /api/classical-versions` — no unified library endpoint | Library Search merge cannot proceed without a single faceted search API that covers all entity types | MERGE: Search + Books + Persons + Classical Versions → Library Search |
| B2 | Book detail fetches chapters via `GET /api/v1/chapters?limit=100` with client-side `book_id` filter — O(n) filtering for potentially thousands of chapters | Document Detail merge blocked until server-side filtering by `book_id` is available | MERGE: Book Detail → Document Detail |
| B3 | V4 APIs (`/api/v4/*`) use different auth/session model than V1 APIs (`/api/v1/*`) | Education and Visualization tab absorption into Knowledge Explorer blocked until API parity | MERGE: V4ResearchView → Knowledge Explorer |
| B4 | `GET /api/v1/versions/:id/passages?limit=500` hard-codes limit — no pagination for large texts | Document Reader must support paginated passage loading for texts with 500+ passages | REBUILD: Version Detail → Document Reader |

### 权限不一致

| # | 问题 | 影响 | 阻塞的处置 |
|---|------|------|----------|
| B5 | `/classical-versions` requires auth but `/books` and `/literature` are public — no consistent rule for library access | Library Search merge must decide: public or authenticated? | MERGE: Classical Versions → Library Search |
| B6 | Literature Detail admin actions (review, RAG, withdraw) are rendered inline, gated by `v-if="auth.canReviewDocuments"` — admin controls embedded in public page | Extracting admin actions to Document Management requires the admin page to have equivalent API access | REBUILD: Literature Detail → Document Detail |
| B7 | Admin guard uses `canReviewDocuments` for both literature review AND ingestion tasks — same permission gates different admin functions | Splitting admin into Document Management and Data Quality requires permission granularity review | REBUILD: Literature Review Queue + Ingestion Tasks |

### 状态模型不一致

| # | 问题 | 影响 | 阻塞的处置 |
|---|------|------|----------|
| B8 | Research store (`useResearchStore`) is client-only singleton with `setTopic`/`clearTopic` — no server persistence, no multi-project support | All research page rebuilds blocked until store supports multiple server-persisted projects with `:projectId` routing | REBUILD: Research Home → Project Detail; MERGE: Research New → Project List |
| B9 | Sessions belong to workspace but are global (`GET /api/v1/workspace/sessions` returns all user sessions) — no project scoping | Splitting workspace into focused pages requires project-scoped sessions | REBUILD: Research Workspace → split pages |
| B10 | V4 workflow runs are keyed by `{session_id}/{run_id_node}` but sessions are not project-scoped — orphaned runs possible | Research Result page needs reliable run→project mapping | MERGE: V4ResearchView → Research Result |

### 数据字段缺失

| # | 问题 | 影响 | 阻塞的处置 |
|---|------|------|----------|
| B11 | `GET /api/v1/documents/:id` returns document metadata but not chapters or versions — Book Detail separately calls chapters + versions endpoints | Unified Document Detail for book-type documents requires chapters + versions in the document response | MERGE: Book Detail → Document Detail |
| B12 | `GET /api/v1/graph/entity/:type/:id` returns graph-focused data (nodes, edges) — insufficient for full Entity Detail page (biography, works, external refs) | Entity Detail page for person entities needs person-specific fields not present in graph entity response | REBUILD: Person Detail → Entity Detail |

### 路由依赖

| # | 问题 | 影响 | 阻塞的处置 |
|---|------|------|----------|
| B13 | Search results navigate to entity-specific routes: `/books/:id`, `/persons/:id`, `/versions/:id` — all being renamed | All search result navigation logic must be updated atomically across SearchView and GraphExplorerView | Multiple MERGE/REBUILD dispositions |
| B14 | Graph Explorer accepts `?type=&id=` and `?trace=` deep-link params — these params reference old entity type names and routes | Deep-link compatibility must be maintained during Knowledge Explorer rebuild | REBUILD: Graph Explorer → Knowledge Explorer |
| B15 | ResearchWorkspaceView accepts `?tab=`, `?run=`, `?ask=` query params — these route to in-component tabs that are being split into separate pages | All deep-link params must map to new route structure | REBUILD: Research Workspace → split pages |
| B16 | Navbar has 13 hard-coded links — all must be updated to new route structure | Navbar update must happen atomically with route changes to avoid broken links | All dispositions affecting navbar-linked routes |

### 组件耦合

| # | 问题 | 影响 | 阻塞的处置 |
|---|------|------|----------|
| B17 | `ResearchWorkflowView` is imported and rendered directly inside `ResearchWorkspaceView` — component coupling, not route-based | Promoting to standalone route requires decoupling the import and replacing with `<router-view>` or navigation | KEEP (promoted): Research Workflow |
| B18 | `EntityListPage` is used by both BookListView and PersonListView — both are being merged into different targets (Library Search and Knowledge Explorer) | EntityListPage must be verified for zero consumers before removal | MERGE: Books List, Persons List |
| B19 | V4 citation extraction logic is duplicated in ResearchWorkspaceView (lines 917-985) and V4ResearchView (lines 475-525) — near-identical code | Must extract into shared composable before either view can be refactored | MERGE: V4ResearchView → Research Workspace |

### 测试缺失

| # | 问题 | 影响 | 阻塞的处置 |
|---|------|------|----------|
| B20 | No page-level tests exist for any view — all testing is manual verification | Any page rebuild or merge has zero regression safety net | All dispositions |
| B21 | No test for auth guard behavior (requiresAuth, requiresAdmin, requiresSuperAdmin, guest redirect) | Admin isolation enforcement has no automated verification | REBUILD: admin pages |
| B22 | No test for router redirect chains (`/workspace` → `/research/workspace`, `/v4` → workspace) | Redirect updates have no verification that old URLs still resolve correctly | REDIRECT_ONLY dispositions |

---

## Disposition Summary

| 处置结论 | 数量 | 页面 |
|---------|------|------|
| **KEEP** | 5 | Home, About, Login, Register, Research Workflow (promoted) |
| **REBUILD** | 9 | Version Detail → Document Reader, Person Detail → Entity Detail, Graph Explorer → Knowledge Explorer, Research Home → Project Detail, Research Workspace → split, Literature List → split, Literature Detail → Document Detail, Literature Review Queue → Document Management, Ingestion Tasks → Data Quality |
| **MERGE** | 7 | Search, Books List, Book Detail, Persons List, Research New, V4 Research, Classical Versions List |
| **RETIRE** | 4 | Documents placeholder, WorkspaceView legacy, `/v4/research-internal` route, PlaceholderPage component |
| **ADMIN_ONLY** | 1 | Source Policy → System Operations (restructured) |
| **REDIRECT_ONLY** | 5 (routes) | `/workspace`, `/research` (old), `/v4/research`, `/v4`, `/dashboard` |
| **NEW** | 6 | Access Denied, Not Found, Error State, User and Permission Management, Citation Detail, Document Reader (from rebuild) |

**Total current assets disposed**: 29 (25 views + 4 redirect-only routes)
**Target page count**: 26 (22 rebuilt/kept/merged + 4 new)
**Reduction**: 25 views → 22 target pages (net -3, with significantly reduced duplication)
