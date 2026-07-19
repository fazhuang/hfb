# Sprint 2 · Task 006 — Codex 验收文档

> **基线**: cea0802
> **提交**: (pending)
> **验收日期**: 2026-07-19
> **范围**: ResearchResultPage Migration — 真实 workflow 驱动 E2E、Citation 真实性、浏览器导出、Session/Run 归属、SourceRef 路由、XSS 受控载荷、withdrawn/no-permission SourceRef、文档收口

---

## 1. 改动文件清单

| 文件 | 改动类型 | 行数变化 | 所属批次 |
|------|---------|---------|---------|
| `tests/e2e/test_critical_journeys.py` | 重写 | ~+800/-500 | Batch 1-3 |
| `docs/20-product/2015-research-result-migration.md` | 修改 | ~+30/-15 | Batch 3 |
| `docs/20-product/2016-codex-acceptance-sprint2-task006.md` | 重写 | ~+80/-80 | Batch 4 |

**总计**: 3 文件，~+910/-595 行

---

## 2. 测试验收命令及结果

### 2.1 前端单元测试

```bash
cd apps/frontend
npm run test -- --run
```

**结果: 295 collected, 295 passed, 0 failed, 0 skipped**

含 83 tests in `research-result-page.test.ts`，51 in `research-workflow-page.test.ts`，47 in `project-list.test.ts`，etc.

### 2.2 前端类型检查 + 构建

```bash
cd apps/frontend
npm run typecheck   # PASS — 0 errors
npm run build       # PASS
```

### 2.3 后端 RBAC 隔离测试

```bash
cd /Users/likeming/Sites/hfb
uv run pytest tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation -q -rA
```

**结果: 31 collected, 31 passed, 0 failed**

含 7 个导出端点测试（own-run, cross-user, cross-session mismatch, unsupported format, empty report, data leak checks）。

### 2.4 E2E 测试收集清单

```bash
cd /Users/likeming/Sites/hfb
uv run pytest \
  tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation \
  tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E \
  --collect-only -q
```

**结果: 28 collected** (= 6 CrossProjectIsolation + 22 ResearchResultPageE2E)

### 2.5 E2E 测试实际运行

```bash
cd /Users/likeming/Sites/hfb
uv run pytest \
  tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation \
  tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E \
  -q --browser chromium
```

**结果: (pending run — 需要真实 LLM 后端)**

| # | 测试 | 覆盖项 | 真实/状态 |
|---|------|--------|----------|
| 1 | `test_real_workflow_report_loads` | 真实 workflow → 报告、面包屑、标题、Citation marker、证据面板 | 真实 |
| 2 | `test_real_workflow_citation_shows_evidence` | 真实 Citation 点击 → 真实 claim + quote | 真实 |
| 3 | `test_real_workflow_citation_marker_clickable` | 真实 [N] marker 可点击 → 匹配 Citation 选中 | 真实 |
| 4 | `test_real_workflow_lineage_displayed` | 真实 lineage badge + SourceRef card | 真实 |
| 5 | `test_real_workflow_sourceref_link_routes` | 真实 document_id→/versions/:id precise href + passage= param, click 导航至精确 URL, 无 javascript:/data: | 真实 |
| 6 | `test_real_workflow_lineage_complete_or_partial` | 每个真实 Citation 均有 lineage badge | 真实 |
| 7 | `test_export_markdown_real_browser_download` | Playwright `expect_download()` → filename (.md) + content (# heading) + Content-Type (text/markdown) + Content-Disposition (attachment) | 真实 |
| 8 | `test_export_disabled_when_no_report` | report-missing 状态 → 导出按钮 disabled | 状态 |
| 9 | `test_export_no_double_click` | 快速双击 → download_count==1 | 真实 |
| 10 | `test_export_stale_after_route_switch` | 切换到 report-missing → 导出 disabled | 真实+状态 |
| 11 | `test_cross_user_result_blocked` | User A 访问 B 的真实结果 → not-found, 无泄露 | 真实 |
| 12 | `test_run_not_belonging_to_session_rejected` | 跨 Session run ID → rejected | 真实 |
| 13 | `test_markdown_xss_script_not_executed` | 真实报告中无 `<script>`, onerror=, onclick= | 真实 |
| 14 | `test_markdown_xss_javascript_url_not_active` | 真实报告中无 javascript: 链接 | 真实 |
| 15 | `test_markdown_xss_no_iframe_svg` | 真实报告中无 iframe | 真实 |
| 16 | `test_xss_script_no_executable_node` | 受控载荷: <script>, onerror=, onclick=, <iframe>, <svg> → 全部中和，正常文字渲染 | 状态 |
| 17 | `test_xss_no_dangerous_href` | 受控载荷: javascript: source_ref_url → 非活动链接, claim/quote 安全 | 状态 |
| 18 | `test_xss_no_navigation_or_script_execution` | 受控载荷: 遍历 XSS 报告 → 无导航、无 dialog | 状态 |
| 19 | `test_withdrawn_source_no_internal_link` | no document_id → 无内部 /versions/ 链接, 无 javascript: 链接 | 状态 |
| 20 | `test_withdrawn_source_no_malicious_sourceref_url` | javascript: source_ref_url → 非活动链接 | 状态 |
| 21 | `test_route_switch_clears_stale_data` | 真实→report-missing 切换清除旧报告 | 真实+状态 |
| 22 | `test_switch_from_error_to_ready_clears_error` | report-missing→真实 切换清除错误、显示报告 | 真实+状态 |

**Fixture 分层**:
- **真实 workflow fixtures** (`result_workflow_session`, `result_workflow_cross_users`): 通过 `POST /api/v4/research/workflow` 生成 — 报告/Citation/Evidence/SourceRef 的真实性由此证明
- **状态 seed fixtures** (`result_session_no_report`, `result_session_run_failed`, `result_session_pending`, `result_session_xss_payloads`, `result_session_withdrawn_source`): 仅用于 pending/failed/missing/XSS-payload/withdrawn-source 状态 — 不得用于真实性断言

### 2.6 代码格式

```bash
git diff --check    # clean — 无空白问题
```

---

## 3. `test_query_unmapped_passage_fail_closed` 状态

**仍为独立已知失败**。未跳过（not skipped）、未 xfailed、未弱化断言。其生产逻辑、断言、skip/xfail 状态均未被本 Task 修改。ResearchResultPage 对此类情况诚实显示不完整 lineage。

---

## 4. 真实 workflow fixture 生成路径

| Fixture | 生成路径 |
|---|---|
| `result_workflow_rag_doc` | `POST /api/v1/search/ingest` → `PATCH /api/v1/documents/{id}/review` (rag_enabled=true) |
| `result_workflow_session` | Create user + session → `POST /api/v4/research/workflow` (真实 5-step 执行, blocking, up to 180s) |
| `result_workflow_cross_users` | 2 users → 2 sessions → 2 `POST /api/v4/research/workflow` (均含真实 RAG doc) |

## 5. seed fixture 严格边界

| Fixture | 允许用途 | 禁止用途 |
|---|---|---|
| `result_user` | 共享用户 for state fixtures | — |
| `result_session_no_report` | report-missing 状态 | report/Citation/Evidence/SourceRef 真实性 |
| `result_session_run_failed` | run-failed 状态 | report/Citation/Evidence/SourceRef 真实性 |
| `result_session_pending` | pending 状态 | report/Citation/Evidence/SourceRef 真实性 |
| `result_session_xss_payloads` | Controlled XSS 载荷验证 | report/Citation/Evidence/SourceRef 真实性 |
| `result_session_withdrawn_source` | Withdrawn/no-permission SourceRef | report/Citation/Evidence/SourceRef 真实性 |
| `result_workflow_session_no_report` | report-missing 状态（同用户） | report/Citation/Evidence/SourceRef 真实性 |

每个 seed fixture docstring 明确标注: *"Do NOT use this fixture to assert report/Citation/Evidence/SourceRef authenticity."*

---

## 6. 关键设计决策

### Batch 1 — 真实 workflow E2E fixture 替换 seed

- **旧方案**: `POST /api/v4/research/_test/seed-research-run` 直接写入固定 Markdown、Citation、Evidence、SourceRef — 不是真实 workflow 产物
- **新方案**: `result_workflow_session` 创建真实用户、Session、RAG 文献，通过 `POST /api/v4/research/workflow` 执行真实 5-step workflow，从真实响应获取 run_id
- **RAG 文献**: 通过标准 `POST /api/v1/search/ingest` + `PATCH /api/v1/documents/{id}/review` 创建，含唯一 watermark (`ResultE2E验证`) 保证检索命中
- **禁用 seed API 边界**: 仅状态 fixtures 保留 seed 机制 — 文档明确标注"不得用于真实性断言"

### Batch 2 — 真实浏览器导出 + SourceRef E2E

- **导出**: Playwright `page.expect_download()` — 点击真实导出按钮，验证 filename, content, Content-Type (text/markdown), Content-Disposition (attachment)
- **SourceRef**: 验证 `router-link.esrc-link--internal` 的 `:to` 指向 `/versions/{document_id}?passage={passage_id}`，click 在应用内导航至精确 URL；验证无 `javascript:`/`data:` 载荷
- **Double-click guard**: 断言 download_count == 1

### Batch 3 — XSS 受控载荷 + withdrawn SourceRef

- **XSS 受控载荷**: seed fixture 注入 `<script>`, `<img onerror>`, `onclick`, `javascript:`, `<iframe>`, `<svg>` — 所有向量在 Vue 模板绑定文字解析器中被中和
- **正常功能保留**: 正常中文文字、安全外链（https://）仍可渲染
- **Withdrawn/no-permission**: seed fixture 模拟无 `document_id` 的 retrieval_snapshot — 无内部链接、无 javascript: 链接、不泄露文献正文

### Batch 4 — 文档收口

- 删除"Blob from output_artifacts.markdown"旧表述
- 明确区分真实 workflow E2E 与状态测试数据
- 测试清单与 pytest collected 数一致（28 collected, 22+6 文档数字一致）
- 标明 `test_query_unmapped_passage_fail_closed` 仍失败且未被本任务修改
- 未实际运行的 E2E 命令标为 `pending`

---

## 7. 已知限制

1. 无单 Run 详情 API — 前端通过 runs 列表过滤
2. 无 PDF/DOCX 导出 — 仅 Markdown，通过专用导出端点
3. E2E 需要真实 LLM 后端（未 mock）— `result_workflow_session` 执行真实 `POST /api/v4/research/workflow`
4. `test_query_unmapped_passage_fail_closed` — 已知独立缺陷，未被本 Task 修改

---

## 8. 未修改的冻结页面

以下页面在本 Task 中均未修改：

- `ProjectListPage`
- `ProjectDetailPage`
- `ResearchWorkspacePage`
- `ResearchWorkflowPage`
