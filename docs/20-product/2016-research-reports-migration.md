# Research Reports Page Migration

> **Task**: Sprint 2 · Task 007
> **Date**: 2026-07-20
> **Status**: Complete

## Summary

Migrated `ReportListPage` from placeholder to a real research report history list page. Research users can now view their own reports across all research sessions, identify report statuses, navigate to frozen ResearchResultPage with real IDs, and export reports.

## Routes

| Route | Page | Component |
|-------|------|-----------|
| `/reports` | Report List | `pages/reports/ReportListPage.vue` |
| `/research/:projectId/result/:runId` | Research Result | `pages/research/ResearchResultPage.vue` (frozen) |

## Domain Mapping

```
projectId = ResearchSession.id
runId = ResearchRun.id
```

## Files Changed

### Backend (1 file)
- `apps/backend/app/api/v4/research.py`
  - Added `GET /api/v4/research/reports` — aggregates runs across all user sessions
  - Helper `_derive_run_status()` — derives run_status from step_execution_trace
  - Helper `_derive_report_status()` — derives report_status from trace + output_artifacts

### Frontend (7 files)
- `apps/frontend/src/composables/useResearchReports.ts` — NEW: data orchestration, fetch, pagination, status filter, export, race protection
- `apps/frontend/src/pages/reports/ReportListPage.vue` — Replaced placeholder with full implementation
- `apps/frontend/src/components/reports/ResearchReportsToolbar.vue` — NEW: status filter dropdown
- `apps/frontend/src/components/reports/ResearchReportList.vue` — NEW: report list container
- `apps/frontend/src/components/reports/ResearchReportListItem.vue` — NEW: single report row
- `apps/frontend/src/components/reports/ResearchReportStatusBadge.vue` — NEW: dual-mode status badge

### Tests (2 files)
- `apps/frontend/src/__tests__/research-reports-page.test.ts` — NEW: 20 unit tests
- `tests/e2e/test_critical_journeys.py` — Added `TestResearchReportsPageE2E` class: 7 E2E tests + 2 fixtures

## Reports API

### GET /api/v4/research/reports

Aggregates research runs across all of the current user's sessions.

**Parameters:**
- `page` (int, default 1)
- `limit` (int, default 20)
- `status` (str, optional): filter by report_status

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [{
      "session_id": "uuid",
      "session_title": "Research Session Title",
      "run_id": "uuid",
      "topic": "Research Question",
      "run_status": "completed|failed|running|pending",
      "report_status": "ready|missing|failed|pending",
      "created_at": "ISO8601",
      "completed_at": "ISO8601|null",
      "workflow_type": "full_research_flow"
    }],
    "total": 5,
    "page": 1,
    "limit": 20
  }
}
```

## Status Derivation

### run_status
- Any step `failed` → `failed`
- Any step `running` or `pending` → `running`
- All steps `completed` → `completed`
- No steps → `pending`

### report_status
- `report_generation` step `failed` → `failed`
- `report_generation` step missing or `pending`/`running` → `pending`
- `report_generation` completed but `output_artifacts.markdown` empty → `missing`
- `output_artifacts.markdown` non-empty → `ready`

## Authorization

- **List**: Only sessions belonging to `current_user` are collected (via `WorkspaceService.list_sessions` user_id filter)
- **Export**: Validates session ownership + run belongs to session + markdown non-empty, fail-closed
- **Result page navigation**: Backend validates session ownership + run-in-session membership per run

## States

### Page States
- `loading` — during API fetch
- `empty` — no reports at all
- `empty-filtered` — no results for current status filter (with clear-filter action)
- `ready` — reports displayed
- `error` — API failure (with retry)

### Report States
- `run pending` — workflow not started
- `run running` — workflow in progress
- `run failed` — workflow step failed
- `run completed` — all steps completed
- `report pending` — report_generation step not yet reached
- `report failed` — report_generation step failed
- `report missing` — report_generation completed but markdown empty
- `report ready` — markdown present (view + export enabled)

## Race Protection

- Request sequence counter (`reqSeq`) blocks stale responses from overwriting current data
- `AbortController` pattern via `reqSeq` failsafe on unmount
- Export double-click guard blocks concurrent downloads

## Security

- Backend `list_sessions()` filters by `user_id` — cross-user data never collected
- `_derive_report_status` checks `step_name` AND `name` field (seed runs use `name`, real runs use `step_name`)
- Export validates: format support, session ownership, run-in-session membership, session_id match on run record, non-empty markdown
- Frontend error messages are security-safe (no raw server error exposure for 401/403/404/409/500+)

## Test Coverage

### Frontend Unit (20 tests)
- B1: Page states (loading, empty, error, ready) — 4 tests
- B2: Status display (run/report badges, view link visibility, export button visibility) — 4 tests
- B3: Navigation (real session_id/run_id in links, multi-session links) — 2 tests
- B4: Status filter (API calls with status param, empty filter state) — 2 tests
- B5: Export (real export endpoint, double-click prevention, error handling) — 3 tests
- B6: Race protection (stale response blocked) — 1 test
- B7: Pagination (page navigation) — 1 test
- B8: Contract (correct API endpoint, no project_id, real IDs) — 3 tests

### E2E Browser (7 tests)
- Real login + report list loads with own reports
- View report link uses real session_id/run_id
- Click view → navigate to frozen ResearchResultPage
- Real Markdown export download
- User A cannot see B's reports (list + direct URL)
- User B cannot see A's reports
- New user sees empty state

### Frozen Tests (all passing)
- Frontend: 303→323 tests (12 files, all passing)
- RBAC: 31/31 PASS (TestWorkspaceApiIsolation)
- CrossProjectIsolation: 6/6 PASS
- Type check: PASS
- Build: PASS
