# Project Detail Migration

> **Date**: 2026-07-17
> **Commit**: —
> **Source Page**: `ProjectDetailPage.vue` (was placeholder; now fully migrated)
> **Target Route**: `/research/:projectId`

---

## Migration Sources

Old project detail capabilities were scattered across several un-scoped views:

| Old Source | Capability | Migration Approach |
|-----------|-----------|-------------------|
| `ProjectListPage.vue` | `GET /api/v1/workspace/sessions?limit=100` | Already implemented inline. Detail page now uses the single-session endpoint. |
| `ResearchWorkspaceView.vue` | 7-tab workspace (materials, versions, notes, reports, research, V4, assistant) | Split across dedicated pages. Detail page pulls notes, reports (runs), and query history into separate API-backed panels. |
| `ResearchWorkflowView.vue` | Version comparison workflow (search → select → diff → verify) | Promoted to own route `/research/:projectId/workflow` — linked from detail page via header actions. |
| `V4ResearchView.vue` | V4 workflow inline (topic → 5-steps → report) | Runs surfaced in Reports panel via `/api/v4/research/session/{id}/runs`. |
| `ResearchHomeView.vue` | Project hub with tools grid | Superseded by this detail page. |

---

## Single-Detail API Conclusion

**Resolved: `GET /api/v1/workspace/sessions/{session_id}` exists and is used.**

| Aspect | Finding |
|--------|---------|
| **Endpoint** | `GET /api/v1/workspace/sessions/{session_id}` |
| **Auth** | `workspace.read` permission |
| **Response schema** | `_session_dict()`: `{id, title, active_entities, context_notes, created_at, updated_at}` |
| **404** | Returns HTTP 404 when session not found or belongs to another user |
| **403** | Returned when user lacks `workspace.read` permission |
| **title** | ✅ Present |
| **description** | ❌ Not a separate field. `context_notes` (Markdown) is used as project description when non-null |
| **status** | ❌ No status field on ResearchSession model |
| **created_at** | ✅ ISO timestamp |
| **updated_at** | ✅ ISO timestamp |
| **Notes** | `GET /api/v1/workspace/sessions/{session_id}/notes` — paginated list |
| **Reports (runs)** | `GET /api/v4/research/session/{session_id}/runs` — workflow runs from `workflow_state` JSON |
| **Activity (history)** | `GET /api/v4/research/session/{session_id}/history` — QueryHistory rows |
| **Update** | `PATCH /api/v1/workspace/sessions/{session_id}` — body: `{title?, active_entities?, context_notes?}` |
| **Delete** | `DELETE /api/v1/workspace/sessions/{session_id}` — soft delete |

---

## ResearchSession Field Mapping

```
ResearchSession.id          → ResearchProjectDetail.id         ← routed as :projectId
ResearchSession.title       → ResearchProjectDetail.title      ← page header
ResearchSession.context_notes → ResearchProjectDetail.context_notes ← "project description"
ResearchSession.created_at  → ResearchProjectDetail.created_at ← displayed
ResearchSession.updated_at  → ResearchProjectDetail.updated_at ← displayed
ResearchSession.active_entities → NOT displayed (internal)
ResearchSession.chat_history    → NOT displayed (internal)
ResearchSession.workflow_state  → NOT displayed (internal; consumed by runs)
ResearchSession.user_id     → NOT displayed (internal)
```

**Mapping function** (`toProjectDetail`): defined once in `types/research.ts`; all components import from that single source.

---

## projectId Semantics

- `route.params.projectId` is `ResearchSession.id` (UUID string)
- No independent `Project` table, model, or `project_id` column exists
- The product-layer term "研究课题" maps 1:1 to the `ResearchSession` aggregate root
- No double parameter (`projectId` + `sessionId`) — only one parameter

---

## Page Section Data Sources

| Section | API Endpoint | Empty State | Error Handling |
|---------|-------------|------------|----------------|
| **Page Header** | `GET /api/v1/workspace/sessions/{id}` | N/A (page-level) | Page-level ErrorState |
| **Project Overview** | Same as above | N/A | Same |
| **Research Activity** | `GET /api/v4/research/session/{id}/history` | "暂无研究活动" | Section-level ErrorState |
| **Reports** | `GET /api/v4/research/session/{id}/runs` | "暂无报告" | Section-level ErrorState |
| **Notes** | `GET /api/v1/workspace/sessions/{id}/notes` | "暂无笔记" | Section-level ErrorState |

Each sub-section (activity, reports, notes) loads independently. Failure in one sub-section does not affect project detail display or other sub-sections.

---

## Activity Association

Research activity is sourced from `GET /api/v4/research/session/{session_id}/history`. Each `QueryHistory` record represents a research query step. Activity records are filtered by `session_id` and displayed in reverse chronological order with:
- Query type badge (研究/报告/综合/教育/图谱/搜索/工作流)
- Query text (may include workflow step prefix)
- Citation count
- Timestamp

No synthetic activity is generated. If `QueryHistory` is empty for the session, the "暂无研究活动" empty state is shown.

---

## Report Association

Reports are sourced from `GET /api/v4/research/session/{session_id}/runs`. Each run represents a persisted workflow execution (5-step pipeline). Each report shows:
- Topic (or "未命名报告" if missing)
- Step execution status badges (completed/pending/failed)
- Completion timestamp
- "查看" link to `/research/:projectId/result/:runId`

If no runs exist for the session, the "暂无报告" empty state is shown.

---

## Note Association

Notes are sourced from `GET /api/v1/workspace/sessions/{session_id}/notes`. Each note shows:
- Content (Markdown text)
- Tags (if present)
- Creation timestamp

If no notes exist for the session, the "暂无笔记" empty state is shown.

---

## Edit and Delete Capability Conclusion

| Operation | API Exists | Implemented |
|-----------|-----------|-------------|
| **Edit title** | ✅ `PATCH .../sessions/{id}` with `title` | ✅ EditProjectDialog |
| **Edit description (context_notes)** | ✅ `PATCH .../sessions/{id}` with `context_notes` | ✅ EditProjectDialog |
| **Delete** | ✅ `DELETE .../sessions/{id}` | ✅ DeleteProjectDialog with confirmation |
| **Archive** | ❌ No archive field/endpoint | Not shown |

Delete requires explicit confirmation dialog ("确定要删除课题「X」吗？此操作不可撤销。"). On success, navigates to `/research`. On error, displays the real server error message.

Edit and Delete are behind a "更多操作" (···) dropdown menu in the page header actions area.

---

## Page-Level vs Section-Level States

| State | Level | Component |
|-------|-------|-----------|
| Initial loading | Page | `LoadingState` ("正在加载课题信息...") |
| Not Found (404) | Page | `EmptyState` ("课题不存在") |
| Permission Denied (403) | Page | `ErrorState` ("权限不足") |
| Network/server error | Page | `ErrorState` with retry button |
| Report load failure | Section | `ErrorState` inside ProjectReports ("报告加载失败") |
| Notes load failure | Section | `ErrorState` inside ProjectNotes ("笔记加载失败") |
| Activity load failure | Section | `ErrorState` inside ResearchActivityList ("活动加载失败") |
| No reports | Section | `EmptyState` ("暂无报告") |
| No notes | Section | `EmptyState` ("暂无笔记") |
| No activity | Section | `EmptyState` ("暂无研究活动") |

---

## Not Migrated

- Research Workspace (`/research/:projectId/workspace`) — separate migration task
- Research Workflow (`/research/:projectId/workflow`) — separate migration task
- Research Result (`/research/:projectId/result/:runId`) — separate migration task
- Old views (`ResearchWorkspaceView`, `ResearchHomeView`, `V4ResearchView`, `ResearchWorkflowView`) — preserved
- Old routes — preserved

---

## Blocking Issues

None. All required APIs exist (`GET`, `PATCH`, `DELETE` sessions; notes; runs; history).

Note: The `ResearchSession` model has no `description` or `status` field. The `context_notes` field (Markdown) serves as the description in the UI when present. No status badge is rendered.

---

## Test Results

- **Backend**: From `tests/unit/test_sprint4_v4.py` (~70 tests): 69 passed, 1 pre-existing failure (`test_query_unmapped_passage_fail_closed` — API returns `success: True` for chunks without `passage_id` when test expects fail-closed; citation persistence requires a pre-existing SourceRef).
  - **Correction (2026-07-17):** The original report's "776 passed" figure was the full backend suite count. The test file is `test_sprint4_v4.py`, not any `test_v4_workflow.py` (which doesn't exist).
- **Frontend**: 132/132 tests passing (8 test files), 25 new project-detail tests
- **Type check**: Clean (vue-tsc --noEmit)
- **Build**: Succeeds (vite build)
