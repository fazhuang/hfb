# Research Result Page Migration

## Overview
Sprint 2 · Task 006 — migrated `ResearchResultPage` from hardcoded placeholder to real research result reading and evidence tracing page.

## Page Objective
- Display real research reports from runs
- Display real Citations, Evidence, and SourceRefs
- Show lineage completeness honestly
- Provide safe Markdown rendering (no v-html, no script execution)
- Reuse real backend export endpoint (GET /api/v4/research/session/{id}/runs/{run_id}/export) — no client-side Blob construction from output_artifacts.markdown
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
- `loading`, `ready`, `run-pending`, `run-failed`, `report-pending`, `report-failed`, `report-missing`, `forbidden`, `not-found`, `error`
- Each state has distinct UI with appropriate actions (retry, back to workspace/workflow)
- `report-pending`: report_generation step status is 'pending' or 'running' — distinct from run-pending (no steps yet)
- `report-failed`: report_generation step status is 'failed' — distinct from run-failed (non-report step failed)
- All states determined from real `step_execution_trace`, never from frontend timers or guessing

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
- **Frontend unit**: 91 tests in `research-result-page.test.ts` covering routes, reports, XSS, citations (including Batch 1 validation fixes), evidence, SourceRef (including internal route priority), export, isolation, error handling, cross-user security; includes 8 new report-pending/report-failed state tests (18a-18h)
- **Total frontend**: 303 tests, 11 files, all passing
- **Backend RBAC**: 31 tests passing (`TestWorkspaceApiIsolation`), complete pytest verbose output archived in Codex acceptance doc (2016).
- **Backend V4/Workflow**: 86 passing, 1 known failure (`test_query_unmapped_passage_fail_closed`)
- **E2E CrossProjectIsolation**: 6 passing
- **E2E ResearchResultPage**: 22 passing (real Chromium, real login, real backend, isolated in-memory SQLite) — `TestResearchResultPageE2E` in `test_critical_journeys.py`, **powered by real POST /api/v4/research/workflow executions** with **exact document_id + passage_id SourceRef routing** verified via authenticated runs API (Batch 1-3: 923cc04 → pending commit)
- **Type check**: PASS
- **Build**: PASS
- **Test seed endpoint**: `POST /api/v4/research/_test/seed-research-run` (gated by `SEED_TEST_DATA=1`) used ONLY for state-only fixtures (pending/failed/missing states); **no longer used** for report/Citation/Evidence/SourceRef authenticity E2E

## E2E Fixture Architecture (Batch 1)

### Real-workflow fixtures (authenticity E2E)

| Fixture | How run is generated | Used by |
|---|---|---|
| `result_workflow_rag_doc` | `POST /api/v1/search/ingest` → `PATCH /api/v1/documents/{id}/review` (rag_enabled=true) | (shared base) |
| `result_workflow_session` | Creates user + session → `POST /api/v4/research/workflow` (real 5-step execution, blocking, up to 180 s) | Real-report, citation, evidence, SourceRef, XSS, export, route-switch tests |
| `result_workflow_session_no_report` | `POST /api/v4/research/_test/seed-research-run` (state-only, same user as `result_workflow_session`) | Export-disabled, stale-export, route-switch tests |
| `result_workflow_cross_users` | Two users → two sessions → two `POST /api/v4/research/workflow` calls (both with real RAG doc) | Cross-user isolation, cross-session run rejection |

### State-only seed fixtures (documented boundary)

| Fixture | Purpose | NOT used for |
|---|---|---|
| `result_user` | Shared user for state fixtures | — |
| `result_session_no_report` | report-missing state | report/Citation/Evidence/SourceRef |
| `result_session_run_failed` | run-failed state | report/Citation/Evidence/SourceRef |
| `result_session_pending` | pending state | report/Citation/Evidence/SourceRef |
| `result_session_xss_payloads` | Controlled XSS payload verification | report/Citation/Evidence/SourceRef |
| `result_session_withdrawn_source` | Withdrawn / no-permission SourceRef | report/Citation/Evidence/SourceRef |

Each state-only fixture docstring explicitly states: *"Do NOT use this fixture to assert report/Citation/Evidence/SourceRef authenticity."*

## E2E Test Inventory (TestResearchResultPageE2E, 22 tests)

### Real-workflow authenticity (Batch 1)
1. `test_real_workflow_report_loads` — real workflow → ResultPage with real report
2. `test_real_workflow_citation_shows_evidence` — real citation click → real evidence detail
3. `test_real_workflow_citation_marker_clickable` — real [N] marker click → matching citation selected
4. `test_real_workflow_lineage_displayed` — real evidence has lineage badge + SourceRef card
5. `test_real_workflow_sourceref_link_routes` — real document_id → /versions/:id link, click navigates, no javascript:/data:
6. `test_real_workflow_lineage_complete_or_partial` — every real citation has a lineage badge (full/partial/minimal)

### Real browser export (Batch 2)
7. `test_export_markdown_real_browser_download` — Playwright `expect_download()` → validates filename (.md), content (# markdown), Content-Type (text/markdown), Content-Disposition (attachment)
8. `test_export_disabled_when_no_report` — export button disabled for report-missing state
9. `test_export_no_double_click` — rapid double-click → download_count==1, no duplicate
10. `test_export_stale_after_route_switch` — switch to report-missing → export disabled

### Real-workflow isolation (Batch 1)
11. `test_cross_user_result_blocked` — User A accessing B's real-workflow result → not-found, no data leak
12. `test_run_not_belonging_to_session_rejected` — cross-session run ID mismatch → rejected

### XSS on real-workflow report (sanity check)
13. `test_markdown_xss_script_not_executed` — no <script>, onerror=, onclick= in DOM
14. `test_markdown_xss_javascript_url_not_active` — no javascript: links
15. `test_markdown_xss_no_iframe_svg` — no iframes in report

### XSS controlled-input (seed payloads in real browser, Batch 3)
16. `test_xss_script_no_executable_node` — controlled <script>, onerror=, onclick=, <iframe>, <svg> payloads → all neutralised, normal text renders
17. `test_xss_no_dangerous_href` — controlled javascript: source_ref_url → not active link, claim/quote text safe
18. `test_xss_no_navigation_or_script_execution` — click through XSS report → no navigation, no dialog

### SourceRef withdrawn / no-permission (seed payloads, Batch 3)
19. `test_withdrawn_source_no_internal_link` — no document_id → no internal /versions/ link, no javascript: link
20. `test_withdrawn_source_no_malicious_sourceref_url` — javascript: source_ref_url → not rendered as active link

### Route-switch isolation (state-only secondary fixture)
21. `test_route_switch_clears_stale_data` — real→report-missing switch clears old report
22. `test_switch_from_error_to_ready_clears_error` — report-missing→real switch clears error, shows report

## Known Limitations
1. No single-run detail API — filtering runs list by run_id (backend validates session ownership)
2. No PDF/DOCX export — only Markdown via dedicated backend export endpoint with session/run authorization
3. Internal document/passage routing: SourceReferenceCard constructs internal `router-link` to `/versions/:docId?passage=:passageId` when `document_id` is available, with document-level fallback (`/versions/:docId`) when only `document_id` exists. External `source_ref_url` is secondary fallback only. No document_id → no internal link displayed. Router-link click navigates within app (verified in E2E).
4. No Markdown rendering library — custom text parser (safe by construction, no HTML interpretation)
5. `test_query_unmapped_passage_fail_closed` is a known independent defect — not skipped, not xfailed, assertions not weakened; ResultPage displays incomplete lineage honestly for such cases. Unmodified by Sprint 2 Task 006.
6. E2E tests require a real LLM backend (not mocked) for the workflow step — the `result_workflow_session` and `result_workflow_cross_users` fixtures execute real POST /api/v4/research/workflow calls. State-only fixtures (pending/failed/missing) use `POST /api/v4/research/_test/seed-research-run` gated by `SEED_TEST_DATA=1` and must not be counted as authenticity evidence.
