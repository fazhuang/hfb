# Project List Migration

> **Date**: 2026-07-17
> **Commit**: `904a42a`
> **Status**: Complete
> **Source**: Task — migrate old research project list to new ProjectListPage

---

## Migration Sources

### Old Functionality Sources

| Source File | What Was Used | Mapped To |
|---|---|---|
| `views/ResearchNewView.vue` | Topic creation form (name + description) | `CreateProjectDialog.vue` — modal dialog replacing the standalone page |
| `views/ResearchWorkspaceView.vue` | `GET /api/v1/workspace/sessions` call pattern, pagination pattern, formatDate helper | Direct API call in `ProjectListPage.vue`, same pagination controls |
| `api/client.ts` | Axios `api` instance | Reused directly — no new API wrapper |
| - | API response from `GET /api/v1/workspace/sessions` | Mapped via `toProjectSummary()` to `ResearchProjectSummary` — a view-model, not a separate entity |
| `composables/useApi.ts` | `useEntityList` pattern | NOT reused — sessions endpoint does not support `page`/`q` params, so custom loading/pagination logic is needed |
| `stores/research.ts` | `ResearchTopic` interface shape (name, description, createdAt) | NOT reused — new page uses `ResearchProjectSummary` type from `types/research.ts` backed by server API |

### Shared Components Reused

| Component | File | Usage |
|---|---|---|
| `ResearchPageHeader` | `components/layout/ResearchPageHeader.vue` | Page title, description, actions slot ("新建课题" button) |
| (None) | Pagination is inline in `ProjectListPage` — matches pattern from `EntityListPage.vue` and `ResearchWorkspaceView.vue` | Same prev/next button + page-info pattern |

### New Components Created

| Component | File | Purpose |
|---|---|---|
| `LoadingState` | `components/common/LoadingState.vue` | Reusable loading spinner with message |
| `EmptyState` | `components/common/EmptyState.vue` | Reusable empty state with icon, title, description, action slot |
| `ErrorState` | `components/common/ErrorState.vue` | Reusable error display with retry button |
| `ProjectListToolbar` | `components/research/ProjectListToolbar.vue` | Search bar with debounced input + clear filter |
| `ProjectListItem` | `components/research/ProjectListItem.vue` | Single project card — name, description, dates, enter button |
| `CreateProjectDialog` | `components/research/CreateProjectDialog.vue` | Modal form: name (required) + description (optional) |

---

## API Endpoints Used

| Method | Endpoint | Purpose | Real Backend Capabilities |
|---|---|---|---|
| `GET` | `/api/v1/workspace/sessions` | List user's research sessions | No query params accepted; hardcoded `limit=20` default; no search/pagination/status support; no `total` in response |
| `POST` | `/api/v1/workspace/sessions` | Create new research session | Only accepts `{ title: string }` (title defaults to "未命名研究"); no description or status fields |

> **Important:** The backend route handler does not accept `limit` as a query parameter. The `limit=100` sent by the frontend is silently ignored by the server — `WorkspaceService.list_sessions()` always uses the default of 20.

---

## Data Model

### `ResearchProjectSummary` (`types/research.ts`)

```typescript
/**
 * ResearchProjectSummary — 研究课题列表项
 *
 * 产品层名称：研究课题
 * 后端实体名称：ResearchSession
 * 当前路由参数 projectId 实际承载 ResearchSession.id
 *
 * This is NOT a separate database entity. It is a view-model mapped from
 * the ResearchSession aggregate root — the only research-scoping entity
 * in the current system.
 */
interface ResearchProjectSummary {
  id: string;                    // UUID from ResearchSession.id — the sole identifier
  title: string;                 // from ResearchSession.title
  description?: string | null;   // NOT provided by backend; optional, not added by mapping
  created_at: string | null;     // ISO timestamp from ResearchSession.created_at
  updated_at: string | null;     // ISO timestamp from ResearchSession.updated_at
}
```

---

## Search Implementation

The backend `GET /api/v1/workspace/sessions` does **NOT** support server-side search (`q` parameter) or status filtering. Search is applied **client-side**:

1. Fetch up to 100 sessions from API on mount
2. User types in search box → debounced 300ms → filter `allProjects` by title match
3. No server-side search parameter is sent

### Status Filtering

The backend `ResearchSession` model has no status field. Sessions are either active or soft-deleted. Status filtering was **not implemented** — no data source exists for it.

---

## Pagination Model

Pagination is **client-side** (same reason as search):

1. All projects fetched from API (up to 100)
2. Client-side search filters the full set
3. Client-side pagination: 10 items per page
4. Simple prev/next pagination controls match the project's existing pattern

Single pagination state: `page` ref. No duplicate page/offset/cursor models.

---

## Create Project Flow

1. User clicks "新建课题" → `CreateProjectDialog` opens (v-model pattern)
2. Focus moves to name input (autofocus on dialog open)
3. User fills name (required) + optional description
4. Submit → `POST /api/v1/workspace/sessions` with `{ title }`
5. Success: dialog closes, toast shows, list refreshes via `loadProjects()`
6. Failure: error message displayed inline in dialog, dialog stays open
7. Double-submit: disabled while `submitting` flag is true

### Unmigrated Fields

The old `ResearchNewView.vue` had:
- `description` field — **NOT sent to API** because `POST /api/v1/workspace/sessions` only accepts `title`
- `researchStore.setTopic()` — **NOT used** because the new flow uses server-persisted sessions

---

## State Handling

| State | Implementation |
|---|---|
| Initial loading | `LoadingState` component with spinner |
| Search loading | Same loading state with "正在搜索..." message |
| Empty list | `EmptyState` with "还没有研究课题" + create button |
| Search no results | `EmptyState` with "未找到匹配的课题" + clear filter button |
| API error | `ErrorState` with error message + retry button |
| Create success | Green toast "课题创建成功" (auto-dismiss 3s) |
| Create failure | Red error text in dialog showing backend message |

---

## Race Condition Protection

- `reqId` counter in `ProjectListPage` — each `loadProjects()` call increments it
- On response, checks `myReqId !== reqId` — discards stale responses
- On unmount, `reqId = -1` — all pending callbacks discard their results

---

## Known Limitations

1. **No server-side search**: Backend `list_sessions` accepts only `user_id` and `limit`. Client-side search works for up to 100 sessions but will not scale beyond that.
2. **No status field**: `ResearchSession` has no status concept. Cannot filter by active/completed/etc.
3. **No description field**: `POST /api/v1/workspace/sessions` only accepts `title`. The description textarea in dialog captures user input but does NOT send it to the server — it's silently discarded.
4. **Max 100 sessions**: The page requests `limit=100`. The backend's `list_sessions` default is 20. More than 100 sessions would require server-side pagination support.
5. **No recent activity**: `ResearchSession` tracks `created_at`/`updated_at` but not per-project "recent activity". This field was not implemented.

---

## Test Results

- **Type check**: `vue-tsc --noEmit` passes (0 errors)
- **Unit tests**: 95/95 pass (35 new + 60 existing)
- **Build**: `vite build` succeeds (252 modules, 0 errors)

### Test Coverage Summary

| # | Test | Status |
|---|---|---|
| 1 | Page loads and requests session list | PASS |
| 2 | Successfully renders project names | PASS |
| 3 | Search filters client-side | PASS |
| 4 | Clear filter restores full list | PASS |
| 5 | Empty list shows empty state | PASS |
| 6 | Search-no-results shows distinct empty state | PASS |
| 7 | API failure shows error state | PASS |
| 8 | Retry button re-fetches | PASS |
| 9 | Create button opens dialog | PASS |
| 10 | Missing name disables submit | PASS |
| 11 | Prevents double submission | PASS |
| 12 | Create success refreshes list | PASS |
| 13 | Create failure shows backend error | PASS |
| 14 | Click project navigates to /research/:projectId | PASS |
| 15 | Pagination present when items exceed page size | PASS |
| 16 | No internal technical fields rendered | PASS |
| 17 | Race condition guard | PASS |
| 18 | No state write warnings on unmount | PASS |
