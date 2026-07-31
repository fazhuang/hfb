# Sprint 2 · Task 006 — Codex 验收文档

> **基线**: cea0802
> **验收日期**: 2026-07-19
> **范围**: ResearchResultPage Migration — 真实 workflow 驱动 E2E、Citation 真实性、浏览器导出、Session/Run 归属、SourceRef 精确 document_id+passage_id 路由、XSS 受控载荷、withdrawn/no-permission SourceRef、report-pending/report-failed 状态模型、jsdom navigation stderr 修复、文档收口

---

## 1. 改动文件清单

| 文件                                                                        | 改动类型 | 行数变化  | 所属批次             |
| --------------------------------------------------------------------------- | -------- | --------- | -------------------- |
| `apps/frontend/src/composables/useResearchResult.ts`                        | 修改     | ~+25/-10  | Batch 1              |
| `apps/frontend/src/components/research/result/ResearchResultErrorState.vue` | 修改     | ~+16/-0   | Batch 1              |
| `apps/frontend/src/__tests__/research-result-page.test.ts`                  | 修改     | ~+190/-5  | Batch 1-2            |
| `tests/e2e/test_critical_journeys.py`                                       | 修改     | ~+60/-100 | Batch 1-3 (E2E 修复) |
| `docs/20-product/2015-research-result-migration.md`                         | 修改     | ~+8/-6    | Batch 3              |
| `docs/20-product/2016-codex-acceptance-sprint2-task006.md`                  | 重写     | —         | Batch 4              |

**总计**: 6 文件已修改（工作树内）

---

## 2. 测试验收命令及结果

### 2.1 前端单元测试

```bash
cd apps/frontend
npm run test -- --run
```

**结果: 11 files / 303 tests / 303 passed / 0 failed / 0 skipped**

含 91 tests in `research-result-page.test.ts` (原 83 + 8 新增 report-pending/report-failed 状态测试), 51 in `research-workflow-page.test.ts`, 47 in `project-list.test.ts` 等。

### 2.2 前端类型检查 + 构建

```bash
cd apps/frontend
npm run type-check   # PASS — 0 errors
npm run build        # PASS
```

### 2.3 前端警告分类

- **Vue warnings**: 0
- **RouterLink warnings**: 0
- **jsdom "Not implemented: navigation"**: 0 (已通过 hash-URL stub 修复)
- **Node ExperimentalWarning (localStorage)**: 5 lines (预知，非 Vue/Router 问题)

### 2.4 后端 RBAC 隔离测试

```bash
uv run pytest tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation -v
```

**结果: 31 collected / 31 passed / 0 failed**

完整 pytest 汇总行:

```
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_can_read_own_session[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_can_read_own_session[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_cannot_read_b_session[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_cannot_read_a_session[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_can_read_own_notes[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_can_read_own_notes[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_cannot_read_b_notes[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_cannot_read_a_notes[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_can_read_own_citations[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_can_read_own_citations[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_cannot_read_b_citations[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_cannot_read_a_citations[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_can_read_own_history[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_can_read_own_history[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_cannot_read_b_history[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_cannot_read_a_history[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_can_read_own_runs[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_can_read_own_runs[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_cannot_read_b_runs[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_cannot_read_a_runs[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_a_cannot_get_b_notes_via_known_uuid[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_b_cannot_get_a_citations_via_known_uuid[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_404_does_not_leak_session_title[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_404_does_not_leak_other_user_id[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_export_own_session_own_run_succeeds[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_user_a_accesses_user_b_session_export_rejected[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_own_session_other_users_run_rejected[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_export_nonexistent_run_rejected[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_export_unsupported_format_rejected[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_export_empty_run_report_rejected[asyncio] PASSED
tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation::test_export_response_does_not_leak_other_user_data[asyncio] PASSED

============================= 31 passed in 36.67s ==============================
```

### 2.5 E2E CrossProjectIsolation

```bash
uv run pytest tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation -v --browser chromium
```

**结果: 6 collected / 6 passed / 0 failed** (真实 Chromium, 真实登录, 真实后端)

完整 pytest 汇总行:

```
tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation::test_a_workspace_loads[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation::test_a_project_detail_loads[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation::test_switch_own_projects_no_residue[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation::test_cross_user_workspace_blocked[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation::test_cross_user_project_blocked[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation::test_cross_user_workflow_blocked[chromium] PASSED
```

- 登录方式: `_login_via_ui()` — 通过 `/login` 页面填写用户名密码，点击「登录」按钮，等待重定向。非 localStorage 注入。
- 无 `page.route` / `route.fulfill`。唯一的 `page.route` 命中在注释行 (line 345: `#   - No page.route / route.fulfill`)。

### 2.6 E2E ResearchResultPage

```bash
uv run pytest tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E -v --browser chromium
```

**结果: 22 collected / 22 passed / 0 failed** (真实 Chromium, 真实登录, 真实后端)

完整 pytest 汇总行:

```
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_real_workflow_report_loads[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_real_workflow_citation_shows_evidence[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_real_workflow_citation_marker_clickable[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_real_workflow_lineage_displayed[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_real_workflow_sourceref_link_routes[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_real_workflow_lineage_complete_or_partial[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_export_markdown_real_browser_download[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_export_disabled_when_no_report[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_export_no_double_click[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_export_stale_after_route_switch[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_cross_user_result_blocked[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_run_not_belonging_to_session_rejected[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_xss_script_no_executable_node[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_xss_no_dangerous_href[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_xss_no_navigation_or_script_execution[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_withdrawn_source_no_internal_link[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_withdrawn_source_no_malicious_sourceref_url[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_markdown_xss_script_not_executed[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_markdown_xss_javascript_url_not_active[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_markdown_xss_no_iframe_svg[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_route_switch_clears_stale_data[chromium] PASSED
tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E::test_switch_from_error_to_ready_clears_error[chromium] PASSED
```

- 登录方式: 同上 `_login_via_ui()` — 真实 `/login` 页面交互。
- 无 `page.route` / `route.fulfill` (grep 确认: 0 命中在 `test_critical_journeys.py`)。

### 2.7 综合运行

```bash
uv run pytest \
  tests/unit/test_api_rbac.py::TestWorkspaceApiIsolation \
  tests/e2e/test_critical_journeys.py::TestCrossProjectIsolation \
  tests/e2e/test_critical_journeys.py::TestResearchResultPageE2E \
  -v --browser chromium
```

**结果: 59 collected / 59 passed / 0 failed**

完整 pytest 汇总:

```
============================== 59 passed in 127.49s (0:02:07) ==============================
```

### 2.8 前端 warnings 过滤

```bash
rg -n "Vue warn|No match found|Failed to resolve|RouterLink|Unhandled|Not implemented: navigation|Error:" /tmp/hfb-result-final-frontend.log
```

**结果: 无匹配 (NO_MATCHES_FOUND)**。仅 Node ExperimentalWarning (localStorage)，不混同为 Vue/Router warning。

### 2.9 E2E 测试清单及真实数据边界

| #   | 测试                                               | 覆盖项                                                                                                                                                                                                                                                                                                  | 真实/状态 |
| --- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| 1   | `test_real_workflow_report_loads`                  | 真实 workflow → 报告、面包屑、标题、Citation marker、证据面板                                                                                                                                                                                                                                           | 真实      |
| 2   | `test_real_workflow_citation_shows_evidence`       | 真实 Citation 点击 → 真实 claim + quote                                                                                                                                                                                                                                                                 | 真实      |
| 3   | `test_real_workflow_citation_marker_clickable`     | 真实 [N] marker 可点击 → 匹配 Citation 选中                                                                                                                                                                                                                                                             | 真实      |
| 4   | `test_real_workflow_lineage_displayed`             | 真实 lineage badge + SourceRef card                                                                                                                                                                                                                                                                     | 真实      |
| 5   | `test_real_workflow_sourceref_link_routes`         | **fail-closed 同一 trace 绑定**: manifest target trace → 精确 Citation 匹配(无 fallback) → Evidence detail trace_id 验证 → scoped SourceRef link(.eed-card .esrc-link--internal) → href path==/versions/{document_id} + query passage=={passage_id} → click 后 URL 精确匹配 → 无 javascript:/data: 链接 | 真实      |
| 6   | `test_real_workflow_lineage_complete_or_partial`   | 每个真实 Citation 均有 lineage badge                                                                                                                                                                                                                                                                    | 真实      |
| 7   | `test_export_markdown_real_browser_download`       | Playwright `expect_download()` → filename (.md) + content + Content-Type + Content-Disposition                                                                                                                                                                                                          | 真实      |
| 8   | `test_export_disabled_when_no_report`              | report-missing 状态 → 导出按钮 disabled                                                                                                                                                                                                                                                                 | 状态      |
| 9   | `test_export_no_double_click`                      | `el.click(); el.click()` 同步双击 → download_count==1                                                                                                                                                                                                                                                   | 真实      |
| 10  | `test_export_stale_after_route_switch`             | 切换到 report-missing → 导出 disabled                                                                                                                                                                                                                                                                   | 真实+状态 |
| 11  | `test_cross_user_result_blocked`                   | User A 访问 B 的真实结果 → not-found, 无泄露                                                                                                                                                                                                                                                            | 真实      |
| 12  | `test_run_not_belonging_to_session_rejected`       | 跨 Session run ID → rejected                                                                                                                                                                                                                                                                            | 真实      |
| 13  | `test_markdown_xss_script_not_executed`            | 真实报告中无 `<script>`, onerror=, onclick=                                                                                                                                                                                                                                                             | 真实      |
| 14  | `test_markdown_xss_javascript_url_not_active`      | 真实报告中无 javascript: 链接                                                                                                                                                                                                                                                                           | 真实      |
| 15  | `test_markdown_xss_no_iframe_svg`                  | 真实报告中无 iframe                                                                                                                                                                                                                                                                                     | 真实      |
| 16  | `test_xss_script_no_executable_node`               | 受控载荷: DOM 查询证实无真实 [onerror]/[onclick]/[onload] 元素, 无 <iframe>/<svg>, 正常文字渲染                                                                                                                                                                                                         | 状态      |
| 17  | `test_xss_no_dangerous_href`                       | 受控载荷: javascript: source_ref_url → 非活动链接, Evidence card 无真实 <script> 元素, onerror= 属性检查                                                                                                                                                                                                | 状态      |
| 18  | `test_xss_no_navigation_or_script_execution`       | 受控载荷: 遍历 XSS 报告 → 无导航、无 dialog                                                                                                                                                                                                                                                             | 状态      |
| 19  | `test_withdrawn_source_no_internal_link`           | no document_id → 无内部 /versions/ 链接, 无 javascript: 链接                                                                                                                                                                                                                                            | 状态      |
| 20  | `test_withdrawn_source_no_malicious_sourceref_url` | javascript: source_ref_url → 非活动链接                                                                                                                                                                                                                                                                 | 状态      |
| 21  | `test_route_switch_clears_stale_data`              | 真实→report-missing 切换清除旧报告                                                                                                                                                                                                                                                                      | 真实+状态 |
| 22  | `test_switch_from_error_to_ready_clears_error`     | report-missing→真实 切换清除错误、显示报告                                                                                                                                                                                                                                                              | 真实+状态 |

**Fixture 分层**:

- **真实 workflow fixtures**: 通过 `POST /api/v4/research/workflow` 生成 — 报告/Citation/Evidence/SourceRef 的真实性由此证明
- **状态 seed fixtures**: 仅用于 pending/failed/missing/XSS-payload/withdrawn-source 状态 — 不得用于真实性断言

---

## 3. SourceRef 同一 trace 绑定 (B1 Fail-Closed Fix — a1796e6)

### 旧逻辑缺陷

```
manifest target trace A
≠
页面第一条 Citation 的 trace B (fallback)
≠
实际 SourceRef link 的 Evidence B
```

当 manifest 中的 target trace 无法在页面上匹配到 Citation 时，旧代码退回到 `citation_items.first.click()`，导致验证的是任意一条 Citation 的 Evidence，而非 manifest 指定的那条。测试误报"通过"实则绑定链断裂。

### 修复内容

**1. 删除 fallback** — 不再有 `citation_items.first.click()` 退路

**2. fail-closed 失败** — 找不到匹配 Citation 时 assert 失败，携带 target_trace_id 和所有 rendered_citation_ids

**3. Evidence detail 同 trace 验证** — 点击 Citation 后，读取 `.eed-meta-row:has-text("证据 ID") .eed-meta-value`，验证其 16 位前缀与 target_trace_id 精确匹配

**4. scoped SourceRef 定位** — 使用 `.eed-card .esrc-link--internal` 而非页面级 `.esrc-link--internal`，确保 SourceRef card 属于当前 selected Evidence detail

**5. 保留所有精确断言**:

- `href path == /versions/{document_id}`（非 startsWith）
- `href query passage == {passage_id}`（精确匹配）
- click 后 `pathname == /versions/{document_id}`
- click 后 `query passage == {passage_id}`
- 无 `javascript:` / `data:` href

### 审计 trace

```
target_trace_id:  be6bca03-e706-5034-af40-7dff9c3b3293
document_id:      a5a97b67-cec2-4d6a-b123-6498fcfc69e8
passage_id:       1486e64c-27dd-4202-829e-f812eced1604
rendered citation IDs: [be6bca03-e706...]  ← 精确匹配, 无 fallback
displayed evidence ID: be6bca03-e706...     ← 同一 trace 确认
href:             /versions/a5a97b67-...?passage=1486e64c-...
click URL path:   /versions/a5a97b67-...    ← 精确匹配
click URL passage: 1486e64c-...             ← 精确匹配
```

---

## 4. report-pending / report-failed 判定规则

基于真实 `step_execution_trace` 中的 `report_generation` 步骤状态:

```
1. 无 steps / steps 为空              → run-pending
2. report_generation.status = failed   → report-failed (不是 run-failed)
3. 非 report_generation step 明确 failed → run-failed
4. report_generation.status = pending/running → report-pending
5. 无 report_generation step + 其他步骤未完成 → report-pending
6. report_generation.status = completed + markdown 为空 → report-missing
7. report_generation.status = completed + markdown 非空 → ready
```

不得由前端时间、计时器或 markdown 内容伪造。

---

## 5. `test_query_unmapped_passage_fail_closed` 状态

**仍为独立已知失败**。未跳过（not skipped）、未 xfailed、未弱化断言。其生产逻辑、断言、skip/xfail 状态均未被本 Task 修改。文件位置: `tests/unit/test_sprint4_v4.py:290`。

---

## 6. 冻结页面命中结果

`git diff cea0802..HEAD --name-only` 未命中以下任何文件:

- `ProjectListPage`
- `ProjectDetailPage`
- `ResearchWorkspacePage`
- `ResearchWorkflowPage`

冻结页面未被修改。

---

## 7. 已知限制

1. 无单 Run 详情 API — 前端通过 runs 列表过滤
2. 无 PDF/DOCX 导出 — 仅 Markdown
3. E2E 需要真实 LLM 后端（未 mock）
4. `test_query_unmapped_passage_fail_closed` — 已知独立缺陷

---

## 8. Git 发布基线

Git 发布基线不由文档内固定 SHA 定义。最终验收时必须实时执行：

```bash
git fetch origin
git rev-parse HEAD
git rev-parse origin/master
git status --short
git status -sb
```

只有当 `HEAD == origin/master` 且工作树干净（`git status --short` 空输出）时，才构成已推送发布基线。

### 历史实现/修复提交（迁移链）

以下为历史实现/修复提交，不是"当前 HEAD"：

```
940d830 → 9847aa9 → fd81294 → 67131d2 → a1796e6
```

实际 Git 状态以验收命令实时输出为准。

---

## 9. 未修改的冻结页面

- `ProjectListPage`
- `ProjectDetailPage`
- `ResearchWorkspacePage`
- `ResearchWorkflowPage`
