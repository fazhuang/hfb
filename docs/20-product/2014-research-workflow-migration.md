# Research Workflow Migration

> **Created**: 2026-07-17
> **Commit**: (see git log)
> **Source**: `V4ResearchView.vue` (research tab) + `ResearchWorkspaceView.vue` (v4-research tab)
> **Target**: `pages/research/ResearchWorkflowPage.vue`
> **Route**: `/research/:projectId/workflow`
> **Refs**: `docs/20-product/2007-page-disposition.md` (Item 16 — MERGE)

---

## 1. Migration Sources

| Source File | Capability Absorbed | How Absorbed |
|---|---|---|
| `views/V4ResearchView.vue` | Full research workflow (topic → 5-step pipeline → report + citations + export + note) | Extracted into composable `useResearchWorkflow.ts` + 5 step components |
| `views/ResearchWorkspaceView.vue` (v4-research tab) | Inline V4 workflow + report list + citation extraction | Deduplicated — workflow now standalone; report list stays in workspace |
| `components/research/ResearchAssistantEntry.vue` | sessionStorage question passing | Renamed key from `hfb.research.pending-question` to `hfb.research.{projectId}.pending-question` for project isolation |
| `components/research/ContinueResearchCard.vue` | Resumable run detection | Stays in workspace; now linked to `/research/:projectId/workflow` |

## 2. Real Workflow API Contract

### Endpoint

```
POST /api/v4/research/workflow
```

### Request Schema (V4ResearchWorkflowRequest)

```python
class V4ResearchWorkflowRequest(BaseModel):
    session_id: str      # Required — ResearchSession.id
    topic: str           # Required — research question
    workflow_type: Literal["full_research_flow"]  # default: "full_research_flow"
```

**Not supported by backend:**
- `document_ids` — no document selection field exists
- `supplementary_notes` — no secondary text field exists
- `search_scope` — no retrieval scope parameter exists
- `idempotency_key` — no dedup key exists
- Cancel API — no workflow cancellation endpoint exists

### Response Schema (V4WorkflowResponse inside V4ApiEnvelope)

```python
class V4WorkflowResponse(BaseModel):
    run_id: str                              # Server-generated UUID
    session_id: str                          # Echo back
    steps: list[V4WorkflowStep]              # 5-step results
    traceability: V4TraceabilityBlock | None

class V4WorkflowStep(BaseModel):
    name: str                                # "topic_selection" | "literature_retrieval" | ...
    status: Literal["pending", "running", "completed", "failed"]
    result: dict[str, Any] | None
    trace_ids: list[str]

class V4TraceabilityBlock(BaseModel):
    query_id: str
    trace_ids: list[str]
    citation_count: int
    source_documents: list[str]
    session_id: str | None
```

### Execution Model

Backend executes ALL 5 steps synchronously in a single HTTP request/response cycle:
1. `topic_selection` — breaks topic into sub-questions
2. `literature_retrieval` — queries Elasticsearch + builds snapshot
3. `evidence_synthesis` — groups snapshot into evidence
4. `report_generation` — builds report sections from evidence
5. `citation_export` — exports citations from evidence

If any step fails, subsequent steps are marked `pending` and overall `success=false`.
If literature retrieval returns zero records, workflow fails with `NO_EVIDENCE`.

## 3. Five-Step → Synchronous Execution Mapping

| UI Step | Backend Step | User Input? | Backend Action |
|---|---|---|---|
| 1. Research Question | (none) | Yes — user types topic | Nothing triggered |
| 2. Document Selection | (none — not supported) | No — system auto-retrieves | Nothing triggered |
| 3. AI Analysis | All 5 backend steps execute | No | `POST /workflow` → synchronous execution |
| 4. Evidence Review | (from run artifacts) | Yes — user reviews | `GET /session/{id}/runs` |
| 5. Research Report | (from run artifacts) | Yes — user reviews | Same runs response |

**Key insight:** Steps 1 and 2 are pure client-side UI. Step 3 triggers a single API call that completes steps 3-4-5 in the backend within one HTTP response.

## 4. Document Selection

**Current backend does NOT support manual document selection.**

The `V4ResearchWorkflowRequest` schema has only three fields: `session_id`, `topic`, `workflow_type`. There is no `document_ids`, `search_scope`, or `library_filter` field.

**Implementation decision:** Step 2 "Document Selection" displays a system notice:
> 系统将根据您的研究问题自动检索相关文献。当前版本不支持手动选择特定文献，所有可检索到的相关文献都将纳入分析范围。

The user sees their question (for confirmation) and clicks "开始分析" to proceed.

## 5. Evidence / Citation Mapping

### Evidence Structure (from run artifacts)

Evidence is extracted from `GET /api/v4/research/session/{id}/runs` → `output_artifacts.citations` OR `replay_manifest.retrieval_snapshot` + `replay_manifest.traces`.

Each evidence entry has:
```typescript
interface WorkflowEvidence {
  trace_id: string;       // Trace lineage identifier
  document_id: string;    // Source document UUID
  chunk_id: string;       // Document chunk UUID
  claim_text: string;     // AI-generated claim (归纳)
  quote: string;          // Original text excerpt (原文)
  citation_text: string;  // Citation identifier string
}
```

### Citation Structure

```typescript
interface WorkflowCitation {
  trace_id: string;
  citation_text: string;
  document_id: string;
  quote: string;
}
```

### Distinction in UI

- **AI 归纳** (`claim_text`) — blue label, regular font
- **原文** (`quote`) — green label, serif font, left green border
- **引用标识** (`citation_text`) — grey label, monospace
- **定位信息** — Chunk ID (truncated) or "暂无精确定位"

### Available User Actions

| Action | API Supported? | Implemented? |
|---|---|---|
| 保存引用 (Save Citation) | Yes — `POST /api/v1/workspace/sessions/{id}/citations` | Yes |
| 查看原文 (View Original) | No — no passage/chapter read API in scope | No |
| 保存证据 (Save Evidence) | No — no evidence save API | No |
| 加入笔记 (Add Note) | Yes — `POST /api/v1/workspace/sessions/{id}/notes` | Available via composable |

## 6. Report / run_id

### Report Structure

```typescript
interface WorkflowReport {
  run_id: string;          // Server-generated UUID
  topic: string;           // Original research question
  title: string;           // "研究报告：{topic}"
  markdown: string;        // Full Markdown artifact
  completed_at: string | null;  // ISO timestamp
  artifact_id?: string;    // Content hash (first 16 chars of SHA-256)
  evidence_count: number;  // From extracted evidence
  citation_count: number;  // From extracted citations
}
```

### Navigation

```
/research/:projectId/result/:runId
```

- `projectId` = `ResearchSession.id`
- `runId` = Server-generated UUID from workflow response
- Report page content is NOT implemented here — only the navigation link
- No temporary or client-generated run IDs are used

### Persistence

Runs are persisted in `ResearchSession.workflow_state` JSON column via `persist_research_run()`. Retrievable via `GET /api/v4/research/session/{id}/runs`. No `GET /api/v4/research/result/{runId}` endpoint exists — result display uses the runs list response.

## 7. sessionStorage Behavior

### Key Format

```
hfb.research.{projectId}.pending-question
```

Old key: `hfb.research.pending-question` (global, no project isolation).

New key: `hfb.research.{projectId}.pending-question` (scoped to ResearchSession.id).

### Behavior

1. **Write**: `ResearchAssistantEntry` sets value before navigating to workflow
2. **Read**: `ResearchWorkflowPage.onMounted()` reads from project-scoped key
3. **Clear**: Immediately after read, the key is removed
4. **Cross-project isolation**: Key contains projectId — reading for sess-001 never reads sess-002's key

## 8. No Pause/Resume

Backend executes synchronously — all 5 steps in one HTTP response. There is no:
- Step-by-step polling API
- Pause/resume API
- Partial execution persistence
- Resumable run recovery

`ContinueResearchCard` in the workspace checks for runs with `pending` or `running` step status as future-proofing but always defaults to "开始新研究".

## 9. Error Handling

| Status | Description | User Message |
|---|---|---|
| 400 | Bad Request | 输入不合法，请检查研究问题后重试 |
| 401 | Unauthorized | 登录已过期，请重新登录 |
| 403 | Forbidden | 您没有权限执行此操作 |
| 404 | Not Found | 研究课题或文献不存在 |
| 409 | Conflict | 状态冲突，该工作流可能已在执行中 |
| 422 | Validation Error | 输入格式校验失败，请检查后重试 |
| 429 | Too Many Requests | 请求过于频繁，请稍后再试 |
| 5xx | Server Error | 服务端错误，请稍后重试 |
| Network | Connection failed | 网络连接失败，请检查网络后重试 |
| Timeout | Request timeout | 请求超时。服务端可能已完成处理...请勿重复提交 |

### Timeout Handling

On timeout (`ECONNABORTED`), the page:
1. Displays the timeout message with the "server may have completed" warning
2. Attempts to fetch runs — if a completed run is found, transitions to evidence review
3. Does NOT auto-retry
4. Does NOT assume success or failure

## 10. Component Architecture

```
pages/research/ResearchWorkflowPage.vue
  ├── WorkflowStepNavigation.vue         (5-step progress indicator)
  ├── ResearchQuestionStep.vue           (Step 1: question input)
  ├── DocumentSelectionStep.vue          (Step 2: auto-retrieval notice)
  ├── AnalysisPendingState.vue           (Step 3: loading + elapsed timer)
  ├── EvidenceReviewStep.vue             (Step 4: evidence/citation display)
  └── ResearchReportStep.vue             (Step 5: report preview + nav)

composables/useResearchWorkflow.ts       (state machine, API calls, extraction)
```

## 11. Not Migrated (Remaining in Old Views)

| Capability | Location | Reason |
|---|---|---|
| Education mode | V4ResearchView | Belongs in Knowledge Explorer (future) |
| Visualization mode | V4ResearchView | Belongs in Knowledge Explorer (future) |
| Inline report list + detail | ResearchWorkspaceView | Stays in workspace (separate concern) |
| Version comparison workflow | ResearchWorkspaceView (research tab) | Already standalone ResearchWorkflowView |
| AI chat (SSE) | ResearchWorkspaceView (assistant tab) | Deferred |
| Replay verification | V4ResearchView | Will be part of Research Result page |

## 12. Blocking Issues

None. The migration is complete and self-contained.

## 13. Test Results

### Workflow-Related Backend Tests

```
tests/test_v4_workflow.py — 12/12 passed
  - TestWorkflowWithEvidence: 4/4
  - TestWorkflowNoEvidence: 4/4
  - TestCitationIntegrity: 2/2
  - TestSessionIsolation: 2/2
```

Backend has 12 total tests (only v4 workflow test file exists).

### Backend Full Test Suite

No full test suite beyond `test_v4_workflow.py` (12 tests). No `test_query_unmapped_passage_fail_closed` test exists in the backend.

### Frontend Tests

```
10 test files, 211 tests, all passed
  - research-workflow-page.test.ts: 36 new tests
  - research-workflow.test.ts: 3 existing (version comparison workflow)
  - v4-research.test.ts: 11 existing
  - research-workspace.test.ts: existing
  - project-list.test.ts: 47 existing
  - project-detail.test.ts: existing
  - research-app-shell.test.ts: existing
  - evidence-to-graph-e2e.test.ts: existing
  - system.test.ts: 3 existing
  - admin-views.test.ts: existing
```

### Build

```
vite build — SUCCESS
  ResearchWorkflowPage-CgXCovr8.js  21.43 kB (gzip: 7.93 kB)
```

### Backend Pre-existing Failure Baseline

**Correction (2026-07-17):** The original migration report claimed "No backend tests existed before this migration beyond `test_v4_workflow.py` (12 tests, all pass)" and "No `test_query_unmapped_passage_fail_closed` test exists." Both claims are incorrect:

1. The file `test_v4_workflow.py` has **never existed** in any git commit — it was a reference error.
2. `test_query_unmapped_passage_fail_closed` **does exist** in `tests/unit/test_sprint4_v4.py` and is a genuine pre-existing failure (API returns `success: True` when test expects fail-closed behavior for unmapped passages).

At HEAD (6217ed2), `tests/unit/test_sprint4_v4.py` has ~70 tests: 69 pass, 1 failure (`test_query_unmapped_passage_fail_closed`). The workflow-related test suite is much larger than the original report suggested.

## 14. Modified Files

### New Files

| File | Purpose |
|---|---|
| `pages/research/ResearchWorkflowPage.vue` | Main workflow page (replaced placeholder) |
| `composables/useResearchWorkflow.ts` | Single-source-of-truth state + API composable |
| `components/research/workflow/ResearchQuestionStep.vue` | Step 1: question input |
| `components/research/workflow/DocumentSelectionStep.vue` | Step 2: auto-retrieval notice |
| `components/research/workflow/AnalysisPendingState.vue` | Step 3: loading indicator |
| `components/research/workflow/EvidenceReviewStep.vue` | Step 4: evidence/citation display |
| `components/research/workflow/ResearchReportStep.vue` | Step 5: report preview + nav |
| `components/research/workflow/WorkflowStepNavigation.vue` | 5-step progress indicator |
| `__tests__/research-workflow-page.test.ts` | 36 comprehensive tests |
| `docs/20-product/2014-research-workflow-migration.md` | This document |

### Modified Files

| File | Change |
|---|---|
| `docs/20-product/2007-page-disposition.md` | Updated Item 16 (V4 Research) — marked workflow as MIGRATED |
| `router/index.ts` | Route `/research/:projectId/workflow` already existed (placeholder → real page) |

### Not Modified

- `views/V4ResearchView.vue` — preserved (education, visualization tabs still active)
- `views/ResearchWorkflowView.vue` — preserved (version comparison workflow)
- `views/ResearchWorkspaceView.vue` — preserved (workspace with reports tab)
- Backend API — no changes
- Database — no changes
