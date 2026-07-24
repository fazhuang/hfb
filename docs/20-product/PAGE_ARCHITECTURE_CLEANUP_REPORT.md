# Page Architecture Cleanup Report — Phase 3 (Decision A)

> **Generated**: 2026-07-25
> **Decision**: A — 兼容优先（Compatibility-first）
> **Baseline**: Phase 2 DS Engineering Governance freeze (23d1cef)
> **Scope**: `apps/frontend/src/` — router, pages, views, layouts, components
> **Constraint**: R5 URL/auth/API/flow preservation; no legacy URL changed

---

## 0. Executive Summary — Post-Decision A

| Metric | Count |
|--------|-------|
| Router Routes (total) | 30 |
| pages/ files (canonical) | 10 |
| views/ files (legacy) | 24 (1 removed: WorkspaceView.vue) |
| layouts/ files | 2 |
| ACTIVE — pages/ (canonical) | 10 |
| ACTIVE — views/ (standalone, no overlap) | 18 |
| COMPATIBILITY — views/ (adapter, delegates to pages/) | 2 |
| DEPRECATED — views/ (retained for backward compat) | 4 |
| REMOVE (safe to delete) | 0 (WorkspaceView.vue already deleted) |
| Duplicate business implementations | 0 (adapters are thin wrappers, not duplicate logic) |

---

## 1. Full Router → Page → Layout → Components → API Mapping

Source: extracted from current `apps/frontend/src/router/index.ts` (commit HEAD).

### 1.1 Canonical System: pages/ (ResearchAppLayout)

#### P1. Research: ProjectListPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/research` |
| **Route Name** | `research-project-list` |
| **File** | `pages/research/ProjectListPage.vue` |
| **Layout** | ResearchAppLayout (section: research, requiresAuth) |
| **Components** | ResearchPageHeader, LoadingState, EmptyState, ErrorState, ProjectListToolbar, ProjectListItem, CreateProjectDialog |
| **API** | `GET /api/v1/workspace/sessions`, `POST /api/v1/workspace/sessions` (via CreateProjectDialog) |
| **Supersedes** | `ResearchHomeView.vue` + `ResearchNewView.vue` (now COMPATIBILITY adapters) |
| **Tested by** | E2E task011-navigation-consistency (A1), E2E task010 DS (Page 1) |

#### P2. Research: ProjectDetailPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/research/:projectId` |
| **Route Name** | `research-project-detail` |
| **File** | `pages/research/ProjectDetailPage.vue` |
| **Layout** | ResearchAppLayout (section: research, requiresAuth) |
| **Components** | ResearchPageHeader, LoadingState, EmptyState, ErrorState, ProjectOverview, ResearchActivityList, ProjectReports, ProjectNotes, EditProjectDialog, DeleteProjectDialog |
| **API** | `GET /api/v1/workspace/sessions/{id}`, `PATCH /api/v1/workspace/sessions/{id}`, `DELETE /api/v1/workspace/sessions/{id}`, `GET /api/v4/research/session/{id}/history`, `GET /api/v4/research/session/{id}/runs`, `GET /api/v1/workspace/sessions/{id}/notes` |
| **Tested by** | E2E task011-navigation-consistency (A1, A2) |

#### P3. Research: ResearchWorkspacePage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/research/:projectId/workspace` |
| **Route Name** | `research-project-workspace` |
| **File** | `pages/research/ResearchWorkspacePage.vue` |
| **Layout** | ResearchAppLayout (section: research, requiresAuth) |
| **Components** | ResearchPageHeader, LoadingState, EmptyState, ErrorState, ContinueResearchCard, RecentResearchActivity, RecentReports, RecentNotes, ResearchResources, ResearchAssistantEntry |
| **API** | `GET /api/v1/workspace/sessions/{id}`, `GET /api/v4/research/session/{id}/runs`, `GET /api/v4/research/session/{id}/history`, `GET /api/v1/workspace/sessions/{id}/notes`, `GET /api/v1/workspace/sessions/{id}/citations` |
| **Tested by** | E2E task011-navigation-consistency (A2, A3), E2E task010 DS (Page 3) |

#### P4. Research: ResearchWorkflowPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/research/:projectId/workflow` |
| **Route Name** | `research-project-workflow` |
| **File** | `pages/research/ResearchWorkflowPage.vue` |
| **Layout** | ResearchAppLayout (section: research, requiresAuth) |
| **Components** | ResearchPageHeader, LoadingState, EmptyState, ErrorState, WorkflowStepNavigation, ResearchQuestionStep, DocumentSelectionStep, AnalysisPendingState, EvidenceReviewStep, ResearchReportStep |
| **API** | `POST /api/v4/research/workflow`, `GET /api/v1/workspace/sessions/{id}`, `GET /api/v4/research/session/{id}/runs`, `POST /api/v1/workspace/sessions/{id}/citations`, `POST /api/v1/workspace/sessions/{id}/notes` |
| **Tested by** | E2E task011-navigation-consistency (A3), E2E task010 DS (Page 4) |

#### P5. Research: ResearchResultPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE (FROZEN — Task 010 baseline 1539935) |
| **Route** | `/research/:projectId/result/:runId` |
| **Route Name** | `research-project-result` |
| **File** | `pages/research/ResearchResultPage.vue` |
| **Layout** | ResearchAppLayout (section: research, requiresAuth) |
| **Components** | ResearchResultHeader, ResearchReportViewer, CitationPanel, ResearchResultErrorState |
| **API** | `GET /api/v1/workspace/sessions/{id}`, `GET /api/v4/research/session/{id}/runs`, export endpoint |
| **Tested by** | E2E task011-navigation-consistency (A4) |

#### P6. Library: LibrarySearchPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE (FROZEN — Task 008 baseline 06a6b74) |
| **Route** | `/library` |
| **Route Name** | `library-search` |
| **File** | `pages/library/LibrarySearchPage.vue` |
| **Layout** | ResearchAppLayout (section: library, requiresAuth) |
| **Components** | ResearchPageHeader, LoadingState, EmptyState, ErrorState, LibrarySearchBar, LibraryDocumentCard |
| **API** | `GET /api/v1/documents` |
| **Tested by** | E2E task011-navigation-consistency (B1) |

#### P7. Library: LibraryDetailPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE (FROZEN) |
| **Route** | `/library/:id` |
| **Route Name** | `library-detail` |
| **File** | `pages/library/LibraryDetailPage.vue` |
| **Layout** | ResearchAppLayout (section: library, requiresAuth) |
| **Components** | ResearchPageHeader, LoadingState, ErrorState, LibraryDocumentStatsPanel |
| **API** | `GET /api/v1/documents/{id}`, `GET /api/v1/documents/{id}/stats` |
| **Tested by** | E2E task011-navigation-consistency |

#### P8. Reader: ReaderPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE (FROZEN — Task 009 baseline b3fd9ac) |
| **Route** | `/reader/:id` |
| **Route Name** | `reader` |
| **File** | `pages/reader/ReaderPage.vue` |
| **Layout** | DefaultLayout |
| **Components** | ResearchPageHeader, LoadingState, ErrorState, EmptyState, PassageReader |
| **API** | Document content APIs |
| **Tested by** | E2E task009-reader-refactor (11/11) |

#### P9. Knowledge: KnowledgeExplorerPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE (PLACEHOLDER) |
| **Route** | `/knowledge` |
| **Route Name** | `knowledge-explorer` |
| **File** | `pages/knowledge/KnowledgeExplorerPage.vue` |
| **Layout** | ResearchAppLayout (section: knowledge, requiresAuth) |
| **Components** | ResearchPageHeader |
| **API** | None (placeholder) |

#### P10. Reports: ReportListPage
| Field | Value |
|-------|-------|
| **Status** | ACTIVE (FROZEN — Task 010 baseline 1539935) |
| **Route** | `/reports` |
| **Route Name** | `report-list` |
| **File** | `pages/reports/ReportListPage.vue` |
| **Layout** | ResearchAppLayout (section: reports, requiresAuth) |
| **Components** | ResearchPageHeader, LoadingState, EmptyState, ErrorState, ResearchReportsToolbar, ResearchReportList |
| **API** | Report list APIs |
| **Tested by** | E2E task011-navigation-consistency (A4) |

---

### 1.2 Legacy System: views/ — ACTIVE (no page/ overlap)

These views serve distinct capabilities with no canonical page/ equivalent. They remain ACTIVE and unchanged.

#### V1. HomeView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/` |
| **Route Name** | `home` |
| **File** | `views/HomeView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Public |
| **API** | `GET /api/v1/health` |
| **Why not delete** | Landing page. No canonical page/ equivalent. Nav links updated to `research-project-list`. |

#### V2. AboutView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/about` |
| **Route Name** | `about` |
| **File** | `views/AboutView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Public |
| **Why not delete** | Static info page. No equivalent. |

#### V3. LoginView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/login` |
| **Route Name** | `login` |
| **File** | `views/LoginView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Guest-only |
| **Why not delete** | Auth page. No equivalent. |

#### V4. RegisterView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/register` |
| **Route Name** | `register` |
| **File** | `views/RegisterView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Guest-only |
| **Why not delete** | Auth page. No equivalent. |

#### V5. SearchView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/search` |
| **Route Name** | `search` |
| **File** | `views/SearchView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Public |
| **API** | `GET /api/v1/search`, `GET /api/v1/search/suggest` |
| **Why not delete** | Cross-domain search. No canonical equivalent. Nav link updated to `research-project-list`. |

#### V6. BookListView + V7. BookDetailView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/books`, `/books/:id` |
| **Files** | `views/BookListView.vue`, `views/BookDetailView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Public |
| **API** | `GET /api/v1/books` |
| **Why not delete** | Classical bibliography — distinct from `/library` (research document library). Different domain, different URLs, different users. |

#### V8. VersionDetailView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/versions/:id` |
| **File** | `views/VersionDetailView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Public |
| **Why not delete** | Classical text version detail. No equivalent. |

#### V9. PersonListView + V10. PersonDetailView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/persons`, `/persons/:id` |
| **Files** | `views/PersonListView.vue`, `views/PersonDetailView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Public |
| **API** | `GET /api/v1/persons` |
| **Why not delete** | Person entity browsing. No equivalent. |

#### V11. GraphExplorerView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/graph` |
| **File** | `views/GraphExplorerView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | Public |
| **Components** | GraphCanvas |
| **Why not delete** | Graph visualization. `/knowledge` is a placeholder — GraphExplorerView is the real implementation. Different URLs, both needed. |

#### V12. LiteratureListView + V13. LiteratureDetailView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Routes** | `/literature`, `/literature/:id` |
| **Files** | `views/literature/LiteratureListView.vue`, `views/literature/LiteratureDetailView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | requiresAuth |
| **Why not delete** | Academic literature metadata management. Distinct domain from `/library` (research document library). LiteratureDetailView has nav to `research-workspace` (assistant tab) — preserved. |

#### V14. ClassicalVersionListView
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Route** | `/classical-versions` |
| **File** | `views/classical-versions/ClassicalVersionListView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | requiresAuth |
| **Why not delete** | Classical text version catalogue. No equivalent. |

#### V15–V17. Admin Views
| Field | Value |
|-------|-------|
| **Status** | ACTIVE |
| **Routes** | `/admin/literature-review`, `/admin/ingestion-tasks`, `/admin/source-policy` |
| **Files** | `views/admin/LiteratureReviewQueue.vue`, `views/admin/IngestionTasksView.vue`, `views/admin/SourcePolicyView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | requiresAuth + requiresAdmin / requiresSuperAdmin |
| **Why not delete** | Admin tools. No equivalent. |

---

### 1.3 COMPATIBILITY Views (Thin Adapters → Canonical pages/)

#### C1. ResearchNewView (ADAPTER)
| Field | Value |
|-------|-------|
| **Status** | **COMPATIBILITY** |
| **Route** | `/research/new` |
| **Route Name** | `research-new` |
| **File** | `views/ResearchNewView.vue` (now ~20 lines) |
| **Layout** | DefaultLayout |
| **Auth** | requiresAuth |
| **Implementation** | `onMounted → router.replace({ name: 'research-project-list' })` |
| **Why not delete** | Route name `research-new` must remain resolvable for external bookmarks. Nav links from HomeView, DashboardView all updated to canonical, but external references may exist. |
| **Compatibility term** | Indefinite — until zero external references confirmed. |
| **Deletion precondition** | Zero references to route name `research-new` in external systems + confirmed no bookmarks. |

#### C2. ResearchHomeView (ADAPTER)
| Field | Value |
|-------|-------|
| **Status** | **COMPATIBILITY** |
| **Route** | `/research/home` |
| **Route Name** | `research-home` |
| **File** | `views/ResearchHomeView.vue` (now ~20 lines) |
| **Layout** | DefaultLayout |
| **Auth** | requiresAuth |
| **Implementation** | `onMounted → router.replace({ name: 'research-project-list' })` |
| **Why not delete** | Highest-fan-in legacy route. All internal nav references now updated, but external bookmarks and test route stubs still use it. |
| **Compatibility term** | Indefinite — until zero external references confirmed. |
| **Deletion precondition** | Zero references to route name `research-home` externally + all unit test stubs cleaned. |

---

### 1.4 DEPRECATED Views (Distinct UX, Retained)

These views implement capabilities NOT replicated in canonical pages/. They remain as ACTIVE in the router but are labeled DEPRECATED because canonical pages/ provide overlapping (but differently-scoped) capabilities per project context.

#### D1. ResearchWorkspaceView
| Field | Value |
|-------|-------|
| **Status** | **DEPRECATED** (retained — global workspace panel ≠ canonical single-project workspace) |
| **Route** | `/research/workspace` (+ `/workspace` redirect) |
| **Route Name** | `research-workspace` |
| **File** | `views/ResearchWorkspaceView.vue` (2,227 lines) |
| **Layout** | DefaultLayout |
| **Auth** | requiresAuth |
| **Why cannot delete** | 1) Global multi-project aggregation panel (tabs: research, reports, assistant) — no canonical equivalent; 2) Imports ResearchWorkflowView internally; 3) 43 unit tests (evidence-to-graph-e2e.test.ts); 4) Nav bar has 4 links to it; 5) LiteratureDetailView navigates to it with assistant tab context. |
| **Dependency** | ResearchWorkflowView.vue (embedded) |
| **Deletion precondition** | Canonical page providing equivalent global aggregation, OR migration of all nav links + LiteratureDetailView to canonical routes. |

#### D2. ResearchWorkflowView (EMBEDDED)
| Field | Value |
|-------|-------|
| **Status** | **DEPRECATED** (retained — embedded in ResearchWorkspaceView) |
| **Route** | No direct route (embedded in ResearchWorkspaceView) |
| **File** | `views/ResearchWorkflowView.vue` (944 lines) |
| **Why cannot delete** | Embedded in ResearchWorkspaceView. 7 unit tests (research-workflow.test.ts). |
| **Deletion precondition** | ResearchWorkspaceView migration to canonical pages. |

#### D3. V4ResearchView
| Field | Value |
|-------|-------|
| **Status** | **DEPRECATED** (retained — V4 experimental features) |
| **Route** | `/v4/research-internal` |
| **Route Name** | `v4-research` |
| **File** | `views/V4ResearchView.vue` |
| **Layout** | DefaultLayout |
| **Auth** | requiresAuth |
| **Redirects** | `/v4/research` → `/research/workspace?tab=v4-research` |
| **Why cannot delete** | 29 unit tests (v4-research.test.ts). Backward compat for V4 feature users. |
| **Deletion precondition** | V4 features merged into canonical workflow OR fully deprecated. |

#### D4. DashboardView + D5. DocumentsView
| Field | Value |
|-------|-------|
| **Status** | **DEPRECATED** (retained — distinct UX) |
| **Routes** | `/dashboard`, `/documents` |
| **Files** | `views/DashboardView.vue`, `views/DocumentsView.vue` |
| **Why cannot delete** | Dashboard is an onboarding/dashboard page (distinct from ProjectListPage). DocumentsView is a placeholder. Nav links updated. |
| **Deletion precondition** | Dashboard onboarding flow merged into ProjectListPage or removed. |

---

### 1.5 REMOVED

#### U1. WorkspaceView.vue — DELETED (was in 23d1cef)

| Field | Value |
|-------|-------|
| **Status** | **REMOVED** (confirmed deleted in git status) |
| **Original File** | `views/WorkspaceView.vue` (758 lines) |
| **Verification** | Zero imports, zero route entries, zero test references (confirmed across entire codebase at time of deletion) |

---

## 2. Overlap Resolution — Decision A

### 2.1 Decision A Application

| # | Business Capability | Legacy (views/) | Canonical (pages/) | Resolution |
|---|---------------------|-----------------|---------------------|------------|
| 1 | Research Project List + Create | ResearchHomeView + ResearchNewView → ADAPTER (router.replace to ProjectListPage) | ProjectListPage (inline CreateProjectDialog) | CLOSED — no duplicate business logic |
| 2 | Research Workspace | ResearchWorkspaceView (global aggregation panel) | ResearchWorkspacePage (single-project workspace) | NOT DUPLICATE — different UX scope |
| 3 | Research Workflow | ResearchWorkflowView (embedded, global) | ResearchWorkflowPage (standalone, project-scoped) | NOT DUPLICATE — different scope |
| 4 | Research Report/Result | V4ResearchView (V4 experimental) | ResearchResultPage (canonical) | NOT DUPLICATE — V4 is experimental |
| 5 | Document Library | BookListView + BookDetailView + LiteratureListView + LiteratureDetailView | LibrarySearchPage + LibraryDetailPage | NOT DUPLICATE — different domains (classical books/literature vs research library) |

### 2.2 Rationale for Pairs 2-5 Non-Duplication

Pairs 2-5 appear overlapping in name only. The legacy implementations serve **global/unscoped** use cases (no projectId), while canonical pages are **project-scoped** (require :projectId route param). Forcing redirect would remove functionality users depend on. Specifically:
- `ResearchWorkspaceView` is a global dashboard aggregating ALL sessions; canonical `ResearchWorkspacePage` shows ONE session
- `V4ResearchView` contains experimental features (education mode, visualization) not in canonical workflow
- `BookListView` + `LiteratureListView` serve classical bibliography and academic literature respectively; `LibrarySearchPage` serves research document library — three distinct domains

---

## 3. Navigation Link Audit — Post-Fix

All internal navigation links updated:

| Source File | Old Target | New Target | Status |
|-------------|-----------|------------|--------|
| `HomeView.vue` L10, L15 | `research-new` / `research-home` | `research-project-list` | ✅ FIXED |
| `HomeView.vue` L37 | `research-home` / `research-new` | `research-project-list` | ✅ FIXED |
| `AppNavbar.vue` L108 | `research-home` / `research-new` | `/research` (path) | ✅ FIXED |
| `DashboardView.vue` L9 | `research-new` | `research-project-list` | ✅ FIXED |
| `DashboardView.vue` L39 | `research-home` | `research-project-list` | ✅ FIXED |
| `DashboardView.vue` L46, L69 | `research-new` | `research-project-list` | ✅ FIXED |
| `SearchView.vue` L379 | `research-home` | `research-project-list` | ✅ FIXED |
| `ResearchWorkspaceView.vue` L5 | `research-home` | `research-project-list` | ✅ FIXED |
| `ResearchWorkflowView.vue` L5 | `research-home` | `research-project-list` | ✅ FIXED |
| `V4ResearchView.vue` L5 | `research-home` | `research-project-list` | ✅ FIXED |

**Preserved (not overlapping)**:
| Source | Target | Reason |
|--------|--------|--------|
| `ResearchHomeView.vue` L27, L35, L59 | `research-workspace` | Legacy router name retained — global workspace panel |
| `LiteratureDetailView.vue` L358 | `research-workspace` | Assistant tab navigation to global workspace — correct target |
| `AppNavbar.vue` L112-L113 | `/research/workspace?tab=*` | Global workspace tabs — correct target |

---

## 4. Component Inventory

### 4.1 Cross-Import Verification (unchanged from baseline)
- **views/ → components/**: Legitimate — design system components
- **pages/ → components/**: Legitimate — domain + design system components
- **components/ → views/**: NONE
- **views/ → pages/**: NONE
- **pages/ → views/**: NONE

---

## 5. Test Impact Analysis

| Test Suite | Tests | Result |
|------------|-------|--------|
| Unit tests (vitest) | 574 | ALL PASS |
| E2E task011-navigation-consistency | 116 (29×4 viewports) | ALL PASS |
| E2E task010-design-system | 88 (22×4 viewports) | ALL PASS |
| Backend E2E critical journeys | [see R6 output below] | [pending] |

---

## 6. Frozen Baselines Verification

| Baseline | Commit | Surface | Status |
|----------|--------|---------|--------|
| Reader | b3fd9ac | ReaderPage.vue, PassageReader.vue | ✅ Unchanged |
| Library (Task 008) | 06a6b74 | LibrarySearchPage.vue, LibraryDetailPage.vue | ✅ Unchanged |
| Reports (Task 010) | 1539935 | ReportListPage.vue, reports/ components | ✅ Unchanged |
| Research Result (Task 010) | 1539935 | ResearchResultPage.vue, result/ components | ✅ Unchanged |
| DS (Phase 2) | 23d1cef | All R1-R7 surfaces | ✅ Unchanged |

---

## 7. Changed Files Summary

| File | Change |
|------|--------|
| `views/ResearchNewView.vue` | Rewritten: COMPATIBILITY adapter (~20 lines) |
| `views/ResearchHomeView.vue` | Rewritten: COMPATIBILITY adapter (~20 lines) |
| `views/HomeView.vue` | Nav links: research-new/home → research-project-list |
| `views/DashboardView.vue` | Nav links: research-new/home → research-project-list |
| `views/SearchView.vue` | Nav link: research-home → research-project-list |
| `views/ResearchWorkspaceView.vue` | Nav link: research-home → research-project-list |
| `views/ResearchWorkflowView.vue` | Nav link: research-home → research-project-list |
| `views/V4ResearchView.vue` | Nav link: research-home → research-project-list |
| `components/layout/AppNavbar.vue` | Nav link: /research/new or /research/home → /research |
| `docs/20-product/PAGE_ARCHITECTURE_CLEANUP_REPORT.md` | Updated for Decision A |

---

## Appendix A: Route Name Mapping (Current)

| Route Name | Route URL | Status | Delegates To |
|------------|-----------|--------|--------------|
| `research-project-list` | `/research` | ACTIVE | — |
| `research-project-detail` | `/research/:projectId` | ACTIVE | — |
| `research-project-workspace` | `/research/:projectId/workspace` | ACTIVE | — |
| `research-project-workflow` | `/research/:projectId/workflow` | ACTIVE | — |
| `research-project-result` | `/research/:projectId/result/:runId` | ACTIVE | — |
| `research-new` | `/research/new` | COMPATIBILITY | → `research-project-list` |
| `research-home` | `/research/home` | COMPATIBILITY | → `research-project-list` |
| `research-workspace` | `/research/workspace` | ACTIVE (legacy) | — (global panel) |
| `v4-research` | `/v4/research-internal` | ACTIVE (legacy) | — |

## Appendix B: Layout Usage

| Layout | Used By | Count |
|--------|---------|-------|
| `DefaultLayout.vue` | All legacy views + ReaderPage | 18 routes |
| `ResearchAppLayout.vue` | All canonical pages (research, library, knowledge, reports) | 8 routes |
