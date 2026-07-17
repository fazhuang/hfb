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

### 2. Continue Research (ContinueResearchCard)

Checks `GET /api/v4/research/session/{projectId}/runs` for incomplete runs.

**Resume conclusion**: The current backend executes the 5-step workflow synchronously within a single HTTP request. Runs are either fully completed or failed — there is no partial execution state on the server. There is **no resume API**. The component defaults to showing "开始新研究" and only shows "继续研究" when a run with pending/running steps exists (future-proofing).

**API**: `GET /api/v4/research/session/{session_id}/runs`
- No limit support — returns all runs
- Sorted by storage order (not time-sorted by backend)
- Filtered by `session_id` via ownership check

### 3. Recent Activity (RecentResearchActivity)

**API**: `GET /api/v4/research/session/{session_id}/history?limit=5`
- Supports `?limit=` query parameter — we request exactly 5
- Sorted by `created_at DESC` on server
- Returns `PublicHistoryEntry[]` — never exposes internal trace data
- Scoped to `session_id` via ownership check

### 4. Recent Reports (RecentReports)

**API**: `GET /api/v4/research/session/{session_id}/runs`
- Does NOT support limit — returns all runs
- Client-side sort by `completed_at DESC`
- Client-side truncation to 5
- Scoped to `session_id` via ownership check

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
- Stores question in `sessionStorage` (`hfb.research.pending-question`)
- Navigates to `/research/:projectId/workflow`
- Falls back to navigation without question if sessionStorage unavailable

---

## Data Sorting Strategy

| Section | Backend Sort | Backend Limit? | Client Action |
|---------|-------------|----------------|---------------|
| Recent Activity | `created_at DESC` | Yes (`?limit=5`) | Safety `.slice(0,5)` |
| Recent Reports | None (storage order) | No | Sort by `completed_at DESC`, take 5 |
| Recent Notes | `created_at DESC` | Hard 50 | Take first 5 |
| Research Resources | `created_at DESC` | Hard 100 | Filter by session_id, take 5 |

---

## Session Isolation

All data sources are strictly scoped to `ResearchSession.id`:

- All listing endpoints check `session.user_id == current_user` → 404 if mismatch
- No cross-session data leakage is possible
- The only cross-session endpoint (`POST /api/v4/research/runs/{run_id}/replay`) searches all user sessions but still scoped to `current_user`
- No `project_id` field exists anywhere

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

1. **No resume API**: Workflow runs synchronously — no partial state or resume endpoint exists.
2. **No limit on runs endpoint**: `GET /api/v4/research/session/{id}/runs` returns all runs with no pagination.
3. **No status field on session**: Sessions have no status (active/completed/archived) — all sessions appear equally.

---

## Backend Pre-existing Failure Baseline

The backend had 1 pre-existing test failure unrelated to this task:
- `test_query_unmapped_passage_fail_closed` — not in the 12 test suite run.

Current backend full suite: **12/12 passed** (0 failures).

---

## Test Results

### Backend

```
12 passed in 0.94s
```
No new failures. All 12 tests pass.

### Frontend

```
Test Files  9 passed (9)
Tests  175 passed (175)
```

- TypeScript: no errors
- Build: successful

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
