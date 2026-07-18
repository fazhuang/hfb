# Sprint 2 · Task 006 — Codex 验收文档

> **基线**: cea0802
> **提交**: a05c183
> **验收日期**: 2026-07-19
> **范围**: ResearchResultPage Migration — Citation 真实性、后端导出、Session/Run 归属、SourceRef 路由、E2E 测试、文档收口

---

## 1. 改动文件清单

| 文件 | 改动类型 | 行数变化 | 所属批次 |
|------|---------|---------|---------|
| `apps/frontend/src/components/research/result/ResearchReportViewer.vue` | 修改 | +40/-15 | Batch 1 |
| `apps/frontend/src/composables/useResearchResult.ts` | 修改 | +110/-25 | Batch 1+2 |
| `apps/frontend/src/pages/research/ResearchResultPage.vue` | 修改 | +15/-5 | Batch 1+2 |
| `apps/frontend/src/components/research/result/SourceReferenceCard.vue` | 重写 | +120/-20 | Batch 3 |
| `apps/frontend/src/__tests__/research-result-page.test.ts` | 修改 | +300/-80 | Batch 1+2+3 |
| `apps/backend/app/api/v4/research.py` | 修改 | +230/-12 | Batch 2+3+4 |
| `tests/unit/test_api_rbac.py` | 修改 | +165/-0 | Batch 2 |
| `tests/e2e/test_critical_journeys.py` | 修改 | +380/-0 | Batch 4 |
| `docs/20-product/2015-research-result-migration.md` | 修改 | +18/-10 | Batch 1+2+4 |
| `docs/20-product/2007-page-disposition.md` | 修改 | +5/-5 | Batch 3+4 |

**总计**: 10 文件，+1629/-85 行

---

## 2. 测试验收命令及结果

### 2.1 前端单元测试

```bash
cd apps/frontend
npm run test -- --run src/__tests__/research-result-page.test.ts
```

**结果: 81 collected, 81 passed, 0 failed, 0 skipped**

| 测试批 | 范围 | 数量 |
|--------|------|------|
| BATCH 1 | Route & Session | 11 |
| BATCH 2 | Report states | 7 |
| BATCH 3 | XSS / Markdown safety | 5 |
| BATCH 4 | Citations | 6 |
| BATCH 4b | Citation validation (新增) | 6 |
| BATCH 5 | Evidence | 10 |
| BATCH 6 | SourceRef (重写) | 7 |
| BATCH 7 | Export (重写) | 10 |
| BATCH 8 | Isolation | 5 |
| BATCH 9 | Error handling | 8 |
| BATCH 10 | Cross-user security | 5 |

### 2.2 后端 RBAC 隔离测试

```bash
cd /Users/likeming/Sites/hfb
uv run pytest tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation -q
```

**结果: 31 collected, 31 passed, 0 failed**

含 7 个新增导出端点测试:
- `test_export_own_session_own_run_succeeds` — 自己的 Session + Run 导出成功，MIME/Content-Disposition 正确
- `test_user_a_accesses_user_b_session_export_rejected` — 跨用户 Session 导出拒绝 (404)
- `test_own_session_other_users_run_rejected` — 自己的 Session + 他人的 Run 拒绝 (404)
- `test_export_nonexistent_run_rejected` — 不存在的 Run 拒绝 (404)
- `test_export_unsupported_format_rejected` — 不支持格式拒绝 (400)
- `test_export_empty_run_report_rejected` — 空报告拒绝 (409)
- `test_export_response_does_not_leak_other_user_data` — 响应不含其他用户数据

### 2.3 E2E ResearchResultPage 测试

```bash
cd /Users/likeming/Sites/hfb
uv run pytest tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E -v --browser chromium
```

**结果: 12 collected, 12 passed, 0 failed (30.89s)**

| # | 测试 | 覆盖项 |
|---|------|--------|
| 1 | `test_result_page_loads_with_valid_run` | 完整报告显示、面包屑、标题、导出按钮、Citation marker、证据面板 |
| 2 | `test_citation_click_shows_evidence` | Citation 点击 → 证据详情（claim + quote） |
| 3 | `test_citation_marker_in_report_clickable` | 报告内 `[N]` marker 可点击选择 Citation |
| 4 | `test_lineage_completeness_displayed` | 完整 lineage badge + SourceRef 标题 |
| 5 | `test_source_ref_external_link_present` | SourceRef 链接可见、"打开原文" 文本 |
| 6 | `test_markdown_xss_script_not_executed` | `<script>` 不渲染、事件属性不在 DOM |
| 7 | `test_markdown_xss_javascript_url_not_active` | `javascript:` URL 非活跃链接 |
| 8 | `test_markdown_xss_no_iframe_svg` | 报告内无 iframe 元素 |
| 9 | `test_export_markdown_download` | 后端导出端点 200 + MIME + Content-Disposition |
| 10 | `test_route_switch_clears_stale_data` | ready→report-missing 切换后旧报告不可见 |
| 11 | `test_cross_user_result_blocked` | 跨用户访问 404、无数据泄露 |
| 12 | `test_switch_from_error_to_ready_clears_error` | 错误状态→ready 切换后错误清除、报告显示 |

### 2.4 编译验收

```bash
npm run typecheck   # PASS — 0 errors
npm run build       # PASS — 5.63s
```

### 2.5 代码格式

```bash
git diff --check    # clean — 无空白问题
```

---

## 3. `test_query_unmapped_passage_fail_closed` 状态

**仍为独立已知失败**。未跳过（not skipped）、未 xfailed、未弱化断言。ResearchResultPage 对此类情况诚实显示不完整 lineage（"证据链不完整"、"缺少文献来源信息"）。本 Task 未掩盖或变通此缺陷。

---

## 4. git log

```
a05c183 feat(ui): Sprint 2 Task 006 — ResearchResultPage migration batches 1-4
7474ac6 fix(security): add URL scheme validation to SourceReferenceCard external links
d00876b docs: Context 29 — research result migration verification
8228130 feat(ui): migrate research result page
```

cea0802..HEAD 共 4 个提交，均属于本 Task 或前置巡检。

---

## 5. 关键设计决策

### Batch 1 — Citation 校验
- `ResearchReportViewer` 接受 `validCitationTraceIds: Set<string>` prop
- `displayNumbers` 为 computed，由 report markdown 中出现的合法 trace_id 顺序生成
- 未知 marker 以 `[trace_id]` 文本回退，不渲染按钮
- click 事件始终发出真实 `trace_id`

### Batch 2 — 后端导出端点
- `GET /api/v4/research/session/{session_id}/runs/{run_id}/export?format=markdown`
- 三层校验：Session 所有权 → Run 在 Session 内 → Run 的 `session_id` 字段与 URL 匹配
- 错误分层：400（格式）/ 404（授权）/ 409（空报告）/ 500（安全回退消息）
- 前端下载真实后端 Blob 响应，不本地构造

### Batch 3 — Run/Session 归属 + SourceRef
- `get_session_runs` 显式跳过 `run.session_id != url.session_id` 的 run（防御性加固）
- SourceRef 路由优先级：`document_id + passage_id` 内部 `router-link` → 仅 `document_id` 文档级链接 → 无 `document_id` 外部 `<a>` 链接回退

### Batch 4 — E2E 基础架构
- `POST /api/v4/research/_test/seed-research-run`，由 `SEED_TEST_DATA=1` 环境变量控制
- 每次 E2E 模块独立启动 uvicorn + Vite + in-memory SQLite
- 所有 E2E 测试使用真实登录 UI 流程（非 localStorage 注入）

---

## 6. 已知限制

1. 无单 Run 详情 API — 前端通过 runs 列表过滤；后端验证 Session 所有权
2. 无 PDF/DOCX 导出 — 仅 Markdown，通过专用导出端点
3. 无独立 Document/Passage Reader 页面 — SourceRef 内部 `router-link` 指向现有 `/versions/:id?passage=:pid`，在 Document Reader 重建前作为过渡方案
4. 无 Markdown 渲染库 — 自定义文本解析器（安全构造，无 HTML 解释）
5. `test_query_unmapped_passage_fail_closed` — 已知独立缺陷

---

## 7. 未修改的冻结页面

以下页面在本 Task 中均未修改：

- `ProjectListPage`
- `ProjectDetailPage`
- `ResearchWorkspacePage`
- `ResearchWorkflowPage`
