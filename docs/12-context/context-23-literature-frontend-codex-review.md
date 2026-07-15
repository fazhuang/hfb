# Context 23: Literature Frontend Codex Re-Review

审计时间：2026-07-10
审计范围：`apps/frontend` 文献管理、全文审核、采集任务、来源白名单前端入口与门禁。

## 结论

**PASS**

上一轮唯一阻塞项 `FE-PERM-001：前端没有三层权限模型` 已关闭。当前前端已经区分普通用户、管理员、超级管理员，并且文献入口、版权状态、来源链接、全文展示、全文审核、全文撤回、构建和测试均通过验收。

## 本轮复验摘要

| 验收项 | 结果 | 证据 |
| --- | --- | --- |
| 是否有清晰入口 | PASS | `AppNavbar.vue:81-106` 保留 `/literature`，并按能力显示 `/admin/literature-review`、`/admin/ingestion-tasks`、`/admin/source-policy`；`router/index.ts:97-135` 声明对应路由。 |
| 是否区分普通用户、管理员、超级管理员 | PASS | `auth.ts:67-87` 明确拆分 `isSuperAdmin`、`isAdminRole`、`canReviewDocuments`、`canManageSourcePolicies`；`router/index.ts:158-172` 分别检查 `requiresAdmin` 与 `requiresSuperAdmin`；`AppNavbar.vue:95-105` 按审核权限和来源策略权限分别显示菜单。 |
| 是否显示版权状态 | PASS | `LiteratureListView.vue:93-101` 列表展示版权列；`LiteratureDetailView.vue:17-40` 合规面板展示版权状态、许可类型、授权依据、审核状态、RAG 状态。 |
| 是否显示来源链接 | PASS | `LiteratureDetailView.vue:70-74` 渲染 `source_url` 为“查看来源”外链，并已加 `rel="noopener noreferrer"`。 |
| 是否能审核全文 | PASS | `LiteratureReviewQueue.vue:1-26` 提供全文审核队列并跳转详情；`LiteratureDetailView.vue:86-99` 仅在 `auth.canReviewDocuments` 时显示审核操作；`LiteratureDetailView.vue:208-223` 调用 `PATCH /api/v1/documents/{id}/review`。 |
| 是否能撤回全文 | PASS | `LiteratureDetailView.vue:111-119` 仅在审核权限下显示撤回原因和确认撤回；`LiteratureDetailView.vue:242-258` 调用 `POST /api/v1/documents/{id}/withdraw` 并更新撤回状态。 |
| 是否构建通过 | PASS | `pnpm --filter @hfb/frontend run build` 成功，Vite 输出 `✓ built in 6.04s`。 |
| 是否测试通过 | PASS | `pnpm --filter @hfb/frontend run test` 成功，`4 passed (4)` test files，`26 passed (26)` tests。 |

## 阻塞项复验

### FE-PERM-001：前端没有三层权限模型

**状态：CLOSED**

复验依据：

- `auth.ts:44-50` 定义可授予管理员能力的角色名，且 `auth.ts:71-81` 不再把 `is_superuser` 等同于唯一管理员判断。
- `auth.ts:228-239` 将 `isSuperAdmin`、`isAdminRole`、`canReviewDocuments`、`canManageSourcePolicies` 对外返回，组件和路由可以直接使用能力判断。
- `router/index.ts:117-135` 中全文审核、采集任务仍是 `requiresAdmin`，来源白名单改为 `requiresSuperAdmin`。
- `router/index.ts:158-172` 中 `requiresAdmin` 使用 `auth.canReviewDocuments`，`requiresSuperAdmin` 使用 `auth.canManageSourcePolicies`。
- `AppNavbar.vue:95-105` 将全文审核/采集任务和来源白名单拆成两个显示条件。
- `LiteratureDetailView.vue:86-120` 将审核、RAG、撤回操作挂在 `auth.canReviewDocuments` 下，普通用户不再看到管理操作。

## 测试覆盖

`admin-views.test.ts` 已覆盖三种身份：

- 普通用户：可见文献入口，不可见全文审核、采集任务、来源白名单菜单，详情页不显示管理操作。
- 管理员 / Reviewer：可见全文审核、采集任务，不可见来源白名单，详情页可见管理操作。
- 超级管理员：可见全文审核、采集任务、来源白名单，并可渲染来源白名单页面。

## 非阻塞观察

- `pnpm --filter @hfb/frontend run test` 通过，但测试输出仍有 Vue Router warn：`admin-views.test.ts` 中挂载 `AppNavbar` 的轻量测试路由没有声明所有导航目标，如 `/books`、`/research`、`/graph`。这不影响本轮权限结论，但后续可以补齐测试路由以减少噪音。
- 本轮没有启动浏览器截图；验收基于源码路径、前端单元测试和生产构建。当前验收问题是权限门禁与菜单可见性，已有源码和测试证据足够支持 PASS。

## 运行命令

```bash
pnpm --filter @hfb/frontend run build
pnpm --filter @hfb/frontend run test
```

## Gate

**PASS**

前端文献模块通过本轮验收。已接受当前三层权限闭环、文献可见性、审核/撤回入口、构建与测试结果。后续请冻结 `apps/frontend/src/stores/auth.ts`、`apps/frontend/src/router/index.ts`、`apps/frontend/src/components/layout/AppNavbar.vue`、`apps/frontend/src/views/literature/LiteratureDetailView.vue`、`apps/frontend/src/__tests__/admin-views.test.ts` 中与三层权限相关的已验收行为，除非有新的权限需求或复验任务。
