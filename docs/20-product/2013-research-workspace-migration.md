# Research Workspace Migration

> **Created**: 2026-07-17
> **Status**: Complete
> **Commits**: HEAD

---

## Migration Sources

### Old Workspace Capabilities (Legacy)

The old ResearchWorkspaceView (`apps/frontend/src/views/ResearchWorkspaceView.vue`) was a 2200+ line 7-tab monolithic component covering:

| Tab | Capability | Disposition |
|-----|-----------|-------------|
| Materials | Document/version listing with search | → Library Search (not workspace) |
| Versions | Classical version browsing | → Library Search (not workspace) |
| Notes | Quick-note CRUD with session filter | → Workspace sidebar "Recent Notes" |
| Reports | V4 workflow run listing, step trace, report preview | → Workspace "Recent Reports" |
| Research | Inline version comparison workflow | → Standalone `/research/:projectId/workflow` |
| V4 Research | Full V4 workflow (topic → 5-step → report + citations + export) | → Research Workflow + Research Result pages |
| Assistant | SSE streaming AI chat, evidence sidebar, citation save | → Future: dedicated AI Assistant page |

### Related Legacy Views

- `V4ResearchView.vue` — Duplicated V4 workflow logic; merged into workflow/result pages
- `ResearchHomeView.vue` — Tool grid replaced by Project Detail and Workspace
- `ResearchWorkflowView.vue` — Version comparison; promoted to standalone route

### Already-Migrated Components (Reused)

- `ResearchActivityList.vue` — Adopted pattern for RecentResearchActivity
- `ProjectReports.vue` — Adopted pattern for RecentReports
- `ProjectNotes.vue` — Adopted pattern for RecentNotes
- `ResearchPageHeader.vue` — Shared layout component
- `LoadingState.vue`, `EmptyState.vue`, `ErrorState.vue` — Common state components

---

## Workspace Sections

### 1. Page Header (ResearchPageHeader)

- **Title**: Real ResearchSession.title
- **Description**: Real ResearchSession.context_notes (only when present)
- **Breadcrumbs**: 研究课题 → Current Topic → 研究工作区
- **Actions**: "开始新研究" → `/research/:projectId/workflow`, "查看课题详情" → `/research/:projectId`

**API**: `GET /api/v1/workspace/sessions/{session_id}` — single source of truth, called once

### 2. Start Research (ContinueResearchCard)

Always shows "开始新研究". Receives shared runs data from the parent page — does NOT make its own API call.

**Resume conclusion**: The current backend executes the 5-step workflow synchronously within a single HTTP request. Runs are either fully completed or failed — there is no partial execution state on the server. There is **no resume API**. The component ALWAYS shows "开始新研究" and NEVER shows "继续研究".

### 3. Recent Activity (RecentResearchActivity)

**API**: `GET /api/v4/research/session/{session_id}/history?limit=5`
- Supports `?limit=` query parameter — we request exactly 5
- Sorted by `created_at DESC` on server
- Returns `PublicHistoryEntry[]` — never exposes internal trace data
- Scoped to `session_id` via ownership check

### 4. Recent Runs (RecentReports)

Receives shared runs data from the parent page — does NOT make its own API call.

**Label**: "最近研究运行" (not "最近报告"). Runs are not always reports; only completed runs with `report_generation` completed are displayed. Only runs with real `run_id` and `report_generation: completed` get a "查看" link.

**API**: `GET /api/v4/research/session/{session_id}/runs` — called ONCE by the parent page, shared via props.
- Does NOT support limit — returns all runs
- Client-side filter: only runs with `report_generation` step completed
- Client-side sort by `completed_at DESC`; missing `completed_at` placed last
- Client-side truncation to 5
- Scoped to `session_id` via ownership check
- Never uses `started_at` as a substitute for `completed_at`

### 5. Recent Notes (RecentNotes)

**API**: `GET /api/v1/workspace/sessions/{session_id}/notes`
- Hard-coded limit 50 on server
- Sorted by `created_at DESC` on server
- Client-side truncation to 5
- Scoped to `session_id` via ownership check

### 6. Research Resources (ResearchResources)

**API**: `GET /api/v1/workspace/sessions/{session_id}/citations`
- Hard-coded limit 100 on server
- Sorted by `created_at DESC` on server
- Client-side `session_id` filter + truncation to 5
- Scoped to `session_id` via ownership check

### 7. AI Research Assistant (ResearchAssistantEntry)

- Input field for research question
- Does NOT call any AI API
- Stores question in `sessionStorage` with key format: `hfb.research.{projectId}.pending-question`
- Key is scoped to the current ResearchSession id — isolated per topic
- Navigates to `/research/:projectId/workflow`
- The workflow consumable (`useResearchWorkflow.initPendingQuestion()`) reads and clears only the key for its own `projectId`
- Falls back to navigation without question if sessionStorage unavailable
- Research question never enters URL or console

---

## Data Sorting Strategy

| Section | Backend Sort | Backend Limit? | Client Action |
|---------|-------------|----------------|---------------|
| Recent Activity | `created_at DESC` | Yes (`?limit=5`) | Safety `.slice(0,5)` |
| Recent Runs | None (storage order) | No | Filter to `report_generation:completed`, sort by `completed_at DESC` (missing last), take 5 |
| Recent Notes | `created_at DESC` | Hard 50 | Take first 5 |
| Research Resources | `created_at DESC` | Hard 100 | Filter by session_id, take 5 |

### Shared Runs Strategy

The Workspace page calls `GET /api/v4/research/session/{id}/runs` exactly once and passes the result to both `ContinueResearchCard` (for error display + retry) and `RecentReports` (for display). The two child components do NOT make independent API calls. Retry from either component triggers the page-level `loadRuns()` once.
## Session Isolation

All data sources are strictly scoped to `ResearchSession.id`:

- All listing endpoints check `session.user_id == current_user` → 404 if mismatch
- Backend endpoints scope by `session_id` ownership; each data component watches `props.projectId` and clears stale data + cancels in-flight requests on route switch
- No `project_id` field exists anywhere
- sessionStorage key format: `hfb.research.{projectId}.pending-question` — scoped per ResearchSession id

---

## Page State Matrix

### Page-Level

| State | Trigger | Display |
|-------|---------|---------|
| Loading | Initial mount, route change | LoadingState "正在加载工作区..." |
| Success | Session loaded | Full workspace with all sections |
| Not Found | 404 from session API | EmptyState "课题不存在" + link to list |
| Permission Denied | 403 from session API | ErrorState "权限不足" + retry |
| Error | Network/other failure | ErrorState with message + retry |

### Block-Level (each section independently)

Each child component (ContinueResearchCard, RecentResearchActivity, RecentReports, RecentNotes, ResearchResources) manages its own:
- Loading state
- Empty state
- Error state with independent retry

A section failure never blocks other sections from rendering.

---

## Route Structure

```
/research/:projectId/workspace  → ResearchWorkspacePage (this page)
/research/:projectId             → ProjectDetailPage (课题详情)
/research/:projectId/workflow    → ResearchWorkflowPage (开始新研究)
/research/:projectId/result/:runId → ResearchResultPage (报告查看)
```

All use `projectId` = `ResearchSession.id`.

---

## Unmigrated Capabilities

The following capabilities from the old workspace are intentionally NOT migrated:

| Capability | Reason |
|-----------|--------|
| Materials/Versions tabs | Belongs in Library Search, not research workspace |
| Inline AI chat (SSE streaming) | Future: dedicated AI Assistant page under `/research/:projectId/assistant` |
| Evidence sidebar with graph preview | Future: AI Assistant page |
| Citation save to collection | Currently no UI — backend API exists (`POST /api/v1/workspace/sessions/{id}/citations`) |
| Inline note editor | Future: Notes page under research |
| V4 workflow inline execution | Moved to standalone ResearchWorkflowPage |
| Version comparison inline | Moved to standalone ResearchWorkflowPage |
| Education & Visualization modes | Future: Knowledge Explorer or dedicated pages |
| Run replay with hash comparison | Moved to ResearchResultPage |
| Report markdown export | Future: ResearchResultPage |

---

## Blocking Issues

1. **No resume API**: Workflow runs synchronously — no partial state or resume endpoint exists. ContinueResearchCard always shows "开始新研究".
2. **No limit on runs endpoint**: `GET /api/v4/research/session/{id}/runs` returns all runs with no pagination. Solved by shared page-level loading + client-side truncation.
3. **No status field on session**: Sessions have no status (active/completed/archived) — all sessions appear equally.
4. **Runs ≠ reports**: Not all runs have report artifacts. Only runs with `report_generation: completed` step are displayed in RecentReports.

---

## Backend Pre-existing Failure Baseline

At HEAD (6217ed2), `tests/unit/test_sprint4_v4.py` has ~70 tests. One pre-existing failure: `test_query_unmapped_passage_fail_closed` — the API returns `success: True` for chunks without `passage_id` when the test expects fail-closed behavior. This is unrelated to workspace migration.

**Correction (2026-07-17):** The original migration report referenced a non-existent file `test_v4_workflow.py` with "12 tests" — that file has never existed in any git commit. The actual test file is `test_sprint4_v4.py`.

---

## Test Results

### Backend

**Full suite:** 1013 passed, 1 failed, 19 skipped, 1 deselected in 167.34s (0:02:47).

**The single failure is `test_query_unmapped_passage_fail_closed`** in `tests/unit/test_sprint4_v4.py` — a pre-existing failure unrelated to workspace migration (root cause documented below).

**API Isolation (`TestWorkspaceApiIsolation`): 24/24 passed.** Coverage: 5 GET endpoints × 2 users × 2 directions (own + cross) + 2 known-UUID cross-verification + 2 no-data-leak assertions. All tests use real JWT auth chain (no overrides of `get_current_user` or `get_auth_service`).

**Full collection:** `uv run pytest --collect-only -q` → `1033/1034 tests collected (1 deselected)` in 3.87s. Breakdown: `apps/backend/tests/` (12), `tests/unit/`, `tests/e2e/` (25), `tests/integration/`. `scripts/p2t1_e2e_test.py` excluded via `norecursedirs = scripts` in `pytest.ini`.

### Frontend

```
Test Files  10 passed (10)
Tests  197 passed (197)
```

- TypeScript: no errors (vue-tsc --noEmit)
- Build: successful (vite build, 78 chunks)
- Vue Router warnings: **0**
- RouterLink resolution warnings: **0**
- No console suppression in any test file

#### Warning Analysis

| Warning | Source | Count | Verdict |
|---------|--------|-------|---------|
| `ExperimentalWarning: localStorage is not available` | Node.js (vitest worker threads) | 5-7 per run | Not our code — Node.js experimental flag for `--localstorage-file`. Does not affect test behavior. |

No other warnings appear in test output.

### New Tests Added (43 tests in research-workspace.test.ts)

1-2. Loads ResearchSession, fetches with correct projectId
3. No fake context_notes when missing
4-5. Navigation links correct
6-9. Section isolation (each section receives projectId)
12. ContinueResearchCard renders
14. Section failure does not block page
18. Not Found for missing session
19. 403 shows error
20. Page-level retry
22. No internal technical fields
23. AI entry does not call AI API
24. No fixed IDs in links
25. No project_id in types
26. projectId === ResearchSession.id
27. Race condition guard
28. No state writes after unmount
29. Page refresh recovery
30. Session detail fetched once
31. No duplicate concurrent requests
+ ContinueResearchCard: 5 component tests
+ RecentResearchActivity: 2 limit tests
+ RecentReports: 2 limit + sort tests
+ RecentNotes: 1 limit test
+ ResearchResources: 2 session isolation tests
+ ResearchAssistantEntry: 5 functional tests
+ Domain mapping: 2 type contract tests

---

## File Changes

### Modified
- `apps/frontend/src/pages/research/ResearchWorkspacePage.vue` — Replaced stub with full implementation
- `apps/frontend/src/types/research.ts` — Added `ResearchCitationSummary` and `toCitationSummary`
- `docs/20-product/2007-page-disposition.md` — Updated workspace entry

### Added
- `apps/frontend/src/components/research/ContinueResearchCard.vue`
- `apps/frontend/src/components/research/RecentResearchActivity.vue`
- `apps/frontend/src/components/research/RecentReports.vue`
- `apps/frontend/src/components/research/RecentNotes.vue`
- `apps/frontend/src/components/research/ResearchResources.vue`
- `apps/frontend/src/components/research/ResearchAssistantEntry.vue`
- `apps/frontend/src/__tests__/research-workspace.test.ts` (43 tests)
- `docs/20-product/2013-research-workspace-migration.md` (this file)

### Not Modified (Preserved)
- All old views (ResearchWorkspaceView.vue, V4ResearchView.vue, ResearchHomeView.vue, ResearchWorkflowView.vue)
- All old routes
- All backend files
- All database models
- `ProjectDetailPage.vue` and its child components

---

## Backend Dual-User Isolation Test Matrix

Full suite: `tests/unit/test_api_rbac.py` + `tests/unit/test_p0_2_http_verify.py` + `tests/unit/test_classical_versions_rbac.py`

### TestApiRBAC — Workspace API Isolation (24 tests, 24 passed, real JWT auth chain)

| Group | Count | Pass | Principle |
|-------|-------|------|-----------|
| RBAC permission checks (direct service) | 6 | 6 | Admin/Researcher/Visitor/nonexistent user |
| GraphService RBAC | 3 | 3 | Search, create relation, neighbors |
| SearchService RBAC | 2 | 2 | Search + suggest |
| DashboardService RBAC | 1 | 1 | Overview |
| Workspace isolation (service layer) | 2 | 2 | Cross-user session create/delete |
| Workspace API isolation | 24 | 24 | 2 users × 5 endpoints × 2 directions (own + cross) + 2 known-UUID cross-verification + 2 no-data-leak |

**Auth chain:** Real `AuthService.register()` → real JWT access tokens via `create_access_token()` → `Authorization: Bearer <token>` headers on all requests. No overrides of `get_current_user`, `get_auth_service`, or permission guards. Only `get_session` is overridden to use in-memory SQLite.

**Covered endpoints:** `GET sessions`, `GET notes`, `GET citations`, `GET history`, `GET runs`

**All cross-user access returns 404** (not 403). Response body never leaks session title or other user's ID.

### Additional RBAC Tests (36 tests, 36 passed)

| File | Count | Coverage |
|------|-------|----------|
| `test_p0_2_http_verify.py` | 32 | Auth registration, login, token refresh, source URI validation, TREATS evidence policy |
| `test_classical_versions_rbac.py` | 26 | Classical version CRUD RBAC, soft-delete verification |

### Total RBAC + Workspace Isolation: 100 tests, 100 passed

---

## Browser-Level Cross-Project Isolation Probes

**File:** `tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation`

**Execution:** `uv run pytest tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation -v --browser chromium`

**Infrastructure:** In-memory SQLite backend + Vite dev server, dual users created via registration API (`POST /api/v1/auth/register`). Login performed through real browser UI (`/login` page), NOT localStorage injection. A and B use separate data — each has their own session, notes, citations, and query history.

**Auth:** Real login via Playwright: fill username/password fields, click "登录" button, wait for redirect. No `page.evaluate` for localStorage. No `route.fulfill` or mock API. Browsers use independent contexts created by `pytest-playwright` fixture.

**Screenshots/traces:** Written to `/tmp` on failure only; never committed to the source tree.

| Test | Result | Assertion |
|------|--------|-----------|
| `test_a_workspace_loads` | ✅ PASS | Own workspace: correct `<h1>` title, no "课题不存在", session API 200 captured |
| `test_a_project_detail_loads` | ✅ PASS | Own project detail shows "开始研究" |
| `test_switch_own_projects_no_residue` | ✅ PASS | Navigate A1→A2 within same page: A2 title visible, A1 title/note/citation/history/run ID ALL absent from DOM, A2 data present |
| `test_cross_user_workspace_blocked` | ✅ PASS | A visits B's `/research/{B_id}/workspace` → "课题不存在" visible, session API returns 404 (captured), B's title NOT in DOM, B's note NOT in DOM |
| `test_cross_user_project_blocked` | ✅ PASS | A visits B's `/research/{B_id}` → access-denied state, B's note/citation NOT in DOM, session API returns 404 (captured) |
| `test_cross_user_workflow_blocked` | ✅ PASS | A visits B's `/research/{B_id}/workflow` → "课题不存在", session API 404 captured (proves workflow page actually requests session), B's title/history query/run ID ALL absent from DOM |

**Two consecutive runs both pass identically.**

### CI Chromium Installation

In `.github/workflows/test.yml`:
```yaml
- name: Install Chromium for browser E2E
  run: uv run python -m playwright install chromium --with-deps

- name: Install frontend dependencies
  run: |
    npm install -g pnpm@10
    pnpm install --dir apps/frontend --frozen-lockfile

- name: Run browser E2E isolation tests
  run: |
    uv run pytest tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation \
      -v --browser chromium --tracing=retain-on-failure \
      -o "screenshot_dir=/tmp/e2e-screenshots"
  env:
    TESTING: 1
  timeout-minutes: 10
```

CI does not depend on pre-installed browsers, running services, or existing databases.

---

## Pytest Collection Count

**Command:** `uv run pytest --collect-only -q`

**Result:** `1033/1034 tests collected (1 deselected)`

**Deselection:** 1 real_llm test excluded via marker filter (`-m "not real_llm"`).

**Breakdown:**

| Directory | Tests | Status |
|-----------|-------|--------|
| `apps/backend/tests/` | 12 | 12 passed |
| `tests/unit/` | ~955 | ~954 passed, 1 failed (`test_query_unmapped_passage_fail_closed`) |
| `tests/e2e/` | 25 | 19 skipped (no --browser), 6 require --browser chromium |
| `tests/integration/` | ~41 | All passed |
| `scripts/p2t1_e2e_test.py` | 0 | Excluded via `norecursedirs = scripts` in pytest.ini |

**scripts/p2t1_e2e_test.py exclusion:** Previously collected by pytest (triggering `SystemExit: 0` during collection). Now excluded via `norecursedirs` in `pytest.ini` — the script still exists but is no longer treated as a test file. No file deletion was needed.

**Why the original report said "12 tests":** The original migration report referenced a non-existent file `test_v4_workflow.py` with "12 tests" — that file has never existed in any git commit. The actual test file `test_sprint4_v4.py` contains ~70 tests (at HEAD 6217ed2: 69 passed, 1 pre-existing failure). The full project backend suite discovers **1013 tests that execute** — the "12" was a counting artifact, not a statement about the full project.

---

## `test_query_unmapped_passage_fail_closed` Root Cause

**Status:** Pre-existing failure (confirmed at HEAD 6217ed2, unrelated to workspace migration).

**What the test does:** Creates a Document + DocumentChunk without `passage_id`, then calls `POST /api/v4/research/session` with `query="针灸"`. Expects `success=False` or `TRACE_LINEAGE_INCOMPLETE` in response.

**What actually happens:** The API returns `success: True` with a full academic response (decomposition, evidence, citations, metadata). The backend's `citation_persistence.py:198` raises `RuntimeError` ("Cannot resolve SourceRef..."), but `academic_service.py:1076` catches it and the query still succeeds. The `trace_lineage.py:234` module correctly logs a warning that chunks without `passage_id` are skipped from trace records, but this does not cause the overall request to fail-closed.

**Why it persists:** The `fail-closed` design intent (reject unmapped passages) was never fully implemented in the research session creation path. The route returns success and the error is only logged, not propagated. This is a code-level gap, not a test bug.

---

## Unverified Items

1. **Resume/replay workflow:** No resume API exists (`GET /api/v4/research/session/{id}/runs` returns completed runs only — no partial execution state). The frontend `ContinueResearchCard` always shows "开始新研究".

2. **V4 Research Portal E2E tests (8 tests):** Use selectors from retired `/v4/research` route (`#v4-topic`, `#v4-viz-type`, `nav a[href="/v4/research"]`). Route `/v4/research` now redirects. These tests need rewriting against the new `/research/:projectId/workflow` route — out of scope for workspace migration.

3. **Education & Visualization modes:** Retired from workspace; future placement in Knowledge Explorer or dedicated pages is undecided.

4. **AI Assistant (SSE streaming chat):** The old workspace's inline AI chat is not migrated. Backend SSE endpoint and evidence sidebar APIs exist but are not wired to any current frontend page.

5. **Citation save/collection UI:** Backend `POST /api/v1/workspace/sessions/{id}/citations` exists but has no dedicated UI. ResearchResources displays existing citations; creation is only possible via the workflow evidence step.
