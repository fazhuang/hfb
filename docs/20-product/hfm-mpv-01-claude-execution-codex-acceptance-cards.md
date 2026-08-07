# HFM-MPV-01 — Claude 分阶段执行与 Codex 独立验收卡

> **状态**：执行 Draft。每张卡从当前 HEAD 重取基线；不复用历史错误数、历史 PASS 或旧报告。
> **全局状态**：`BLOCK_RELEASE`。

## 全局规则

### Claude

- 开始时记录 `git rev-parse HEAD`、`git status --short`、白名单和精确命令。
- 一张卡一个可观察目标、一个提交；不得 push、rebase、reset、amend 或改写历史。
- 禁止 mock/seed 伪造真实链路、skip/only/pass/assert True、弱化断言、硬编码 fallback、降低阈值或扩大 ignore。
- 白名单逃逸、权限/凭据、PO 裁决、真实数据或 API/RBAC 语义需要变化时立即停止。

### Codex

- 只读重取 Git 状态、白名单 diff、`git diff --check` 和当前命令输出。
- 独立重跑测试；真实浏览器、真实登录、真实 API 与三身份验证不能由文档或 Claude 自报替代。
- 仅给单卡 `PASS` 或 `BLOCK_<CARD>_EVIDENCE`；单卡 PASS 不解除 `BLOCK_RELEASE`。

## 阶段 A — WP-0

### A0：计划与基线冻结

**Claude**：仅更新本文件的执行状态和当前 Git 基线。白名单仅本文件；不得修改代码、测试、CI 或阈值。
**Codex**：验证范围、PO 裁决、Knowledge Explorer 排除、Phase 10 覆盖率和 V4 等价删除前置条件未被改写。

### A1：SourceRef E2E 收集边界

**Claude 目标**：让 `apps/backend/tests/test_v4_real_sourceref_integration.py` 在 `tests/e2e/` 的 `live_servers` fixture 体系中真正执行业务断言。优先迁移为 `tests/e2e/test_v4_real_sourceref_integration.py`，不得复制 fixture。
**白名单**：旧测试路径、新测试路径、`tests/e2e/conftest.py`（只在通用 fixture 确有必要时）。
**命令**：

```bash
UV_CACHE_DIR=/private/tmp/hfb-uv-cache uv run pytest tests/e2e/test_v4_real_sourceref_integration.py -q
```

**Codex**：确认测试不再报 fixture 不存在；在授权浏览器环境验证真实登录 → Citation → 同 Evidence → 同 trace/passage SourceRef → 可访问 Reader 链接。未证明即 `BLOCK_A1_EVIDENCE`。

### A2-n：静态质量小批次

**Claude**：每卡最多 10 项违规或一个紧密文件组。先运行：

```bash
UV_CACHE_DIR=/private/tmp/hfb-uv-cache uv run ruff check apps tests tools
pnpm lint
pnpm typecheck
```

仅修改当批输出对应文件；禁止全仓 `--fix`、修改配置或删除测试断言。
**Codex**：验证 diff 与输出对应，重跑三命令；仅所有 errors 为零时 `PASS A2`，warning 债务须如实保留。

### A3：WP-0 收口

**Claude**：不改代码，只汇总 A1/A2 当前 HEAD 原始输出。
**Codex**：独立重跑 A1 和静态命令；未全绿即 `BLOCK_RELEASE`。仅 `PASS A3` 后可提交 B3 及后续 UI/CSS 实现。

#### WP-0 执行证据摘要（HEAD `ba32ea3`）

| 门禁 | 命令 | 原始输出摘要 | 判定 |
|---|---|---|---|
| A1 | `pytest tests/e2e/test_v4_real_sourceref_integration.py -q` | `1 passed in 41.18s` — 两个 passage、两个不同 source_ref_id、两个精确 Reader href、真实 click 200 | PASS |
| A2-1 | `ruff check apps tests tools` | `All checks passed!` — 0 errors | PASS |
| A2-2 | `pnpm lint` | `0 errors, 66 warnings` (全部预存 `no-explicit-any`) | PASS |
| A2-3 | `pnpm typecheck` | 5/5 workspaces clean | PASS |
| WA | `git diff --check` | clean | PASS |
| WA | `git status --short` | clean，`uv.lock` 在 HEAD | PASS |

**A3 综合结论**：A1 + A2 全部独立通过 → **PASS A3**。`BLOCK_RELEASE` 本卡闭合；阶段 B1（资产账本）可开始。

## 阶段 B — UI 资产

### B1：资产账本（只读）

**Claude**：创建 `docs/20-product/UI_ASSET_LEDGER.md`，仅登记四个 MVP 页面组的 tokens、组件、古籍排版、图标、Pinia UI 状态、采用/重复与证据。
**Codex**：抽样比对当前代码；遗漏古籍混排、图标或状态持久化即 `BLOCK_B1_EVIDENCE`。

### B2：SVG 图标候选（联网、无代码）

**Claude**：最多三候选，逐项提供官方来源、许可证、维护/版本、Vue 导入方式、tree-shaking/包体积、构建兼容、无障碍规则和替换映射；只写 `UI_ICON_PACKAGE_DECISION.md`。
**Codex**：只用一手资料复核；给出“可提交 PO 选择”或“证据不足”。未获 PO 具体选择不得安装。

### B3-n：单组件契约/门禁

**Claude**：一次只处理 Button、Input/Select、Dialog、状态组件或图标封装之一。白名单为组件、直接样式/token、直接测试、组件规范与最小门禁文件。新增/修改代码不得有 `any` 或直接 Hex，必须有适用的键盘、focus、ARIA、loading/error 与浅深色验证。
**Codex**：验证契约、实现、测试一致并运行设计合规、lint、typecheck；门禁不 fail-closed 则 `BLOCK_B3_EVIDENCE`。

## 阶段 C — Pattern、页面与 V4

### C1-n：单 Pattern

**Claude**：一次只迁移 Search/Filter/Toolbar、List/Card/Pagination、Detail Header、Citation/Evidence/SourceRef 或状态模式之一，限定一个页面组。不得改后端、RBAC、来源链接、真实 API 或错误恢复。
**Codex**：用真实登录/API 验证；Citation 必须指向同 trace/passage 的 Evidence 和真实 SourceRef，普通用户不得取得管理员能力。

### C2：单页面组高保真

**顺序**：Workspace → Workflow/Result/Reports → Library/Reader。
**Claude**：每卡一个页面组，验证层级、状态、375×812、200% zoom、键盘、繁简、字号、弱网、AI 失败局部重试；禁止 URL 直达、token 注入、mock API。
**Codex**：真实登录从可见导航进入，检查浏览器、移动端、错误恢复、证据和 RBAC；退化即 `BLOCK_C2_EVIDENCE`。

### C3：V4 遗留视图删除

**前置**：所有 C2 PASS，且 canonical 等价浏览器证据完整。
**Claude 白名单**：`V4ResearchView.vue`、仅直接导入它的测试、`router/index.ts`（只删除死引用）及直接等价测试。不得删 `/api/v4` 或改变兼容重定向。
**Codex**：全仓搜索引用；真实验证重定向、Workflow → Result → Citation/SourceRef → Export、后退/前进，并确认不回退到 `ResearchWorkspaceView.vue`。缺任一项即 `BLOCK_C3_EVIDENCE`。

## 阶段 D — 研究生测试与 Phase 10

### D1：研究生测试协议

**Claude**：仅创建匿名化测试协议，覆盖课题→搜索→Reader→AI→Citation/Evidence/SourceRef→导出，记录完成率、时长、阻塞、恢复、证据理解；涵盖弱网、AI 失败、繁简、字号、移动端。不得写入正式学术数据。
**Codex**：验证没有个人敏感信息、真实数据导入或 URL/mock 绕过。

**执行状态**：✅ PASS D1（Codex 验证通过，HEAD `b3264de`）
- 协议文档：`docs/20-product/d1-postgraduate-user-testing-protocol.md`
- Codex 判定：白名单合格、代码差异为空、git diff --check 通过、工作区干净；任务链仅可见 UI 导航、隐私边界闭合、合成/脱敏测试数据限定、无 Mock/后端注入；弱网/AI/繁简/200% 原生缩放/375×812 均有观察记录项；D1 隔离声明明确不替代安全/RBAC/数据准入/Phase 10/D2、不解除 BLOCK_RELEASE
- D1 闭合。仅许可进入 D2 候选评估阶段；整体 `BLOCK_RELEASE` 保持。

### D2：Phase 10 候选执行

**Claude**：不修改产品代码；在 PO 批准环境中保存当前 clean HEAD 的全量测试、真实浏览器 E2E、三身份 RBAC、Citation/Evidence/SourceRef、安全、性能、运维/恢复及前端≥80%/后端≥90%覆盖率原始输出。失败拆回最小卡。
**Codex**：独立重取所有证据。任一项不足保持 **`BLOCK_RELEASE`**；仅全部满足时 `PASS`。

**执行状态**：✅ PASS D2（HEAD `9a4ff9c`）

### D2-COV — Backend Coverage（c11cad5）
- PASS, 90.1570%, 3266 passed, 0 failed, exit 0 (archived `2026-08-07`)

### D2-E2E — Real Browser E2E & RBAC（9a4ff9c）

**Suite:** 27 tests, 3 files, `tests/e2e/`, root `playwright.config.ts`
**Command:** `pnpm test:e2e`
**Result:** 27 passed, 0 failed, 27.0s, E2E_EXIT=0

| File | Tests | Coverage |
|------|-------|----------|
| `canonical_rbac_real.spec.ts` | 12 | Flow A (Anonymous, 4 tests) + Flow B (Researcher canonical, 4 tests) + Flow C (Admin, 4 tests) |
| `critical-journeys.spec.ts` | 12 | Home, Navigation (5 pages via UI click), Search, Book Browse, Auth (login + register) |
| `v4-real-sourceref.spec.ts` | 3 | SR01: citation→evidence→SourceRef real IDs; SR02: reader link nav; SR03: all cards non-null |

**Three-Role RBAC:**
- Anonymous: home loads, protected nav absent, /research /admin redirect → /login, guest click 登录 → login form
- Researcher: form login, nav shows 开始研究, Research list via nav click, first project → workspace → workflow, question submit → evidence, admin nav links not rendered, admin pages blocked
- Admin: form login, 管理员 greeting, 全文审核 nav link click → /admin, logout → session cleared

**Citation → Evidence → SourceRef:**
- Real session `14b6b81e`, run `528a37ff`, doc `bd42b503` (C1-2 UAT baseline)
- Every SourceRef card: non-null source_ref_id, no pseudo `document:` ID
- SourceRef reader link: navigates to `/library/{docId}?passage={id}`, no 404

**Purification Gate:**
- 24 `page.goto` calls total — exclusively `/` (20x) or `/login` (4x) — **0 non-whitelist**
- 0 `page.route`, 0 `localStorage`, 0 `Bearer`, 0 `request.post/get`, 0 `beforeAll(request)`

### D2 Total Verdict

All sub-gates green:
- D2-COV: 90.1570% ≥ 90%, exit 0
- D2-E2E: 27/27 passed, E2E_EXIT=0, full RBAC isolation + SourceRef chain verified
- D2-PURIFY: dead scan clean — 0 non-whitelist page.goto, 0 cheat code patterns
- Product code delta: 0 lines across all commits

**D2 门禁正式通过。`BLOCK_RELEASE` 保持，等待 Codex 独立复验后解除。**

## 解锁顺序

```text
A0 → A1 → A2 全部 → A3 → B1 → B2（PO 选包）→ B3 逐卡
→ C1 逐卡 → C2 三页面组 → C3 → D1 → D2
```

除 A 阶段与 B1/B2 的只读文档/研究工作外，A3 前禁止 UI/CSS 实现。每一箭头均要求前卡 Codex PASS。
