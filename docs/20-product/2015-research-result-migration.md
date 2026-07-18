# Research Result Page Migration

## Overview
Sprint 2 · Task 006 — migrated `ResearchResultPage` from hardcoded placeholder to real research result reading and evidence tracing page.

## Page Objective
- Display real research reports from runs
- Display real Citations, Evidence, and SourceRefs
- Show lineage completeness honestly
- Provide safe Markdown rendering (no v-html, no script execution)
- Reuse real export capability (Blob from output_artifacts.markdown)
- Cross-session, cross-user, cross-run isolation

## Route
`/research/:projectId/result/:runId` — `research-project-result`

## Domain Mapping
- `projectId` = `ResearchSession.id`
- `runId` = `ResearchRun.run_id`
- No `project_id` or second entity model introduced
- No frontend-generated runId

## Data Sources
- **Session**: `GET /api/v1/workspace/sessions/{session_id}` — title, ownership
- **Runs**: `GET /api/v4/research/session/{session_id}/runs` — target run filtered by runId
- **Report**: `output_artifacts.markdown` from target run (real field)
- **Evidence**: `replay_manifest.retrieval_snapshot` + `replay_manifest.traces` cross-reference
- **Citations**: `output_artifacts.citations` from target run
- **SourceRef**: `retrieval_snapshot.source_ref_title`, `source_ref_url`, `source_ref_id`

## No Faked Data
- No fake report, no fake citation, no fake evidence
- No frontend confidence scoring from string length or keyword count
- No synthetic SourceRef from document_id
- No fabricated lineage claims
- Missing fields shown honestly ("缺少文献来源信息", "证据链不完整")

## Markdown Safety
- Custom text-based parser — no v-html, no innerHTML
- Citation markers `[trace_id]` are parsed by regex; ONLY markers matching a real trace_id from the current run's `output_artifacts.citations` become clickable buttons
- Unknown, cross-run, or missing trace_id markers render as plain text (not clickable)
- Display numbers are view-local sequential indices; the stable identity is always `trace_id`
- Click events emit the real `trace_id` — no array-index or regex-guessed identifiers
- External links (`source_ref_url`) open via `<a target="_blank" rel="noopener noreferrer">`
- No script execution, no event attributes, no iframe, no javascript: URLs
- Tests cover XSS scenarios (script, onerror, javascript: URL)

## Export
- Backend endpoint: `GET /api/v4/research/session/{session_id}/runs/{run_id}/export?format=markdown`
- Authorization: `research.export` permission + session ownership + run-in-session validation
- Fail-closed: 404 for cross-user/session, 409 for empty report, 400 for unsupported format
- Returns `text/markdown; charset=utf-8` with `Content-Disposition: attachment`
- Frontend downloads the real backend Blob response — no local Blob construction from `report.markdown`
- Filename: `hfb-research-report-{runId[:8]}.md`
- Blob URL released after download; double-click blocked; stale export cleared on route change
- No PDF/DOCX buttons (not supported)

## Error States
- `loading`, `ready`, `run-pending`, `run-failed`, `report-missing`, `forbidden`, `not-found`, `error`
- Each state has distinct UI with appropriate actions (retry, back to workspace/workflow)

## Lineage Rules
- **Full**: `trace_id` + `document_id` + content + `source_ref_title` + `passage_id`
- **Partial**: missing `source_ref_title` or `passage_id`
- **Minimal**: missing identifiers or content
- Rule derivation is documented, no opaque scoring

## Components
| Component | Responsibility | Lines |
|---|---|---|
| `ResearchResultPage.vue` | Route params, orchestration, status routing | ~175 |
| `ResearchResultHeader.vue` | Breadcrumbs, export button, session/run info | ~115 |
| `ResearchRunSummary.vue` | Run ID, status, steps, stats | ~140 |
| `ResearchReportViewer.vue` | Safe Markdown parsing, section/paragraph rendering, citation markers | ~280 |
| `CitationPanel.vue` | Citation list, selection, evidence detail routing | ~190 |
| `EvidenceDetail.vue` | Claim, quote, citation text, metadata | ~140 |
| `LineageStatusBadge.vue` | Full/partial/minimal lineage display | ~100 |
| `SourceReferenceCard.vue` | SourceRef title, URL, passage locator | ~115 |
| `ResearchResultErrorState.vue` | All non-ready states with actions | ~175 |
| `useResearchResult.ts` | Composable: session/run loading, evidence extraction, export, stale-call protection | ~440 |

## Tests
- **Frontend unit**: 81 tests in `research-result-page.test.ts` covering routes, reports, XSS, citations (including Batch 1 validation fixes), evidence, SourceRef (including internal route priority), export, isolation, error handling, cross-user security
- **Total frontend**: 282+ tests, 11 files, all passing
- **Backend RBAC**: 31 tests passing (`TestWorkspaceApiIsolation`), including 7 export-specific tests covering own-run, cross-user, cross-session mismatch, unsupported format, empty report, and data-leak checks
- **Backend V4/Workflow**: 86 passing, 1 known failure (`test_query_unmapped_passage_fail_closed`)
- **E2E CrossProjectIsolation**: 6 passing
- **E2E ResearchResultPage**: 12 passing (real Chromium, real login, real backend, isolated in-memory SQLite) — `TestResearchResultPageE2E` in `test_critical_journeys.py`
- **Type check**: PASS
- **Build**: PASS
- **Test seed endpoint**: `POST /api/v4/research/_test/seed-research-run` (gated by `SEED_TEST_DATA=1`) used by E2E fixtures to create complete runs without LLM dependency

## Known Limitations
1. No single-run detail API — filtering runs list by run_id (backend validates session ownership)
2. No PDF/DOCX export — only Markdown via dedicated export endpoint with session/run authorization
3. Internal document/passage routing: SourceReferenceCard now constructs internal `router-link` to `/versions/:docId?passage=:passageId` when `document_id` is available, with document-level fallback (`/versions/:docId`) when only `document_id` exists. External `source_ref_url` is secondary fallback only. No document_id → no internal link displayed
4. No Markdown rendering library — custom text parser (safe by construction, no HTML interpretation)
5. `test_query_unmapped_passage_fail_closed` is a known independent defect — not skipped, not xfailed, assertions not weakened; ResultPage displays incomplete lineage honestly for such cases
6. ~~`export_markdown` backend endpoint only supports `version_comparison` workflow — ResultPage uses Blob export instead~~ Resolved: dedicated V4 export endpoint `GET /api/v4/research/session/{id}/runs/{run_id}/export` with full session/run authorization
