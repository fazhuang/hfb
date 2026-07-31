# 2009 — Research App Shell

> **Generated**: 2026-07-17
> **Sprint**: UI Sprint 2
> **Scope**: Research application skeleton with unified layout, primary navigation, and page header system

---

## Purpose

Document the new unified researcher application shell — `ResearchAppLayout` with vertical sidebar navigation and `ResearchPageHeader` — established for all four researcher modules (Research, Library, Knowledge, Reports).

---

## New Components

### `layouts/ResearchAppLayout.vue`

Vertical sidebar layout replacing the old top-navbar `DefaultLayout` for researcher pages.

| Feature           | Detail                                                        |
| ----------------- | ------------------------------------------------------------- |
| **Brand**         | "皇甫谧数字人文平台" with 📜 icon, links to `/`               |
| **Sidebar**       | Fixed left rail, 240px default, collapsible to 64px           |
| **Navigation**    | Contains `<ResearchPrimaryNav />`                             |
| **Project badge** | Placeholder "当前项目" indicator in sidebar footer            |
| **User area**     | Avatar initial + display name from auth store                 |
| **Content**       | `<router-view />` for child page rendering                    |
| **Collapse**      | Toggle button in sidebar footer                               |
| **Responsive**    | At ≤768px, sidebar overlays; collapsed state hides off-canvas |

### `components/layout/ResearchPrimaryNav.vue`

Vertical primary navigation with four research modules + separated Administration.

| Nav Item       | Target Route               | Icon |
| -------------- | -------------------------- | ---- |
| Research       | `/research`                | 🔬   |
| Library        | `/library`                 | 📚   |
| Knowledge      | `/knowledge`               | 🔗   |
| Reports        | `/reports`                 | 📊   |
| Administration | `/admin/literature-review` | ⚙️   |

**Active state**: Walks `route.matched` for `meta.section` — supports deep sub-routes. `/research/123/workflow` correctly activates "Research".

**Separation**: Administration rendered below a horizontal separator (`rpn-separator`), visually distinct from the four research modules.

### `components/layout/ResearchPageHeader.vue`

Unified page header for all researcher pages.

| Prop             | Type           | Required | Description                                               |
| ---------------- | -------------- | -------- | --------------------------------------------------------- |
| `title`          | `string`       | Yes      | Page title (rendered as `<h1>`)                           |
| `description`    | `string`       | No       | Subtitle text below title                                 |
| `breadcrumbs`    | `Breadcrumb[]` | No       | Array of `{ label, to? }` — last item rendered as current |
| `actions` (slot) | —              | No       | Right-aligned action buttons                              |

No store bindings, no API calls — pure presentational component.

---

## New Target Routes (under ResearchAppLayout)

| Route                                | Component                             | Section   |
| ------------------------------------ | ------------------------------------- | --------- |
| `/research`                          | `ProjectListPage`                     | research  |
| `/research/:projectId`               | `ProjectDetailPage`                   | research  |
| `/research/:projectId/workspace`     | `ResearchWorkspacePage`               | research  |
| `/research/:projectId/workflow`      | `ResearchWorkflowPage`                | research  |
| `/research/:projectId/result/:runId` | `ResearchResultPage`                  | research  |
| `/library`                           | `LibrarySearchPage` (placeholder)     | library   |
| `/knowledge`                         | `KnowledgeExplorerPage` (placeholder) | knowledge |
| `/reports`                           | `ReportListPage` (placeholder)        | reports   |

All new routes set `meta: { section: '<module>', requiresAuth: true }`.

---

## New Placeholder Pages

Three minimal placeholder pages created for modules not yet rebuilt:

| File                                        | Route        | Content              |
| ------------------------------------------- | ------------ | -------------------- |
| `pages/library/LibrarySearchPage.vue`       | `/library`   | "功能迁移中" message |
| `pages/knowledge/KnowledgeExplorerPage.vue` | `/knowledge` | "功能迁移中" message |
| `pages/reports/ReportListPage.vue`          | `/reports`   | "功能迁移中" message |

All three use `ResearchAppLayout` + `ResearchPageHeader`. Zero business logic, zero API calls.

---

## Legacy Items Hidden from New Nav

The new `ResearchPrimaryNav` does NOT display these legacy items:

- Dashboard (`/dashboard`) — RETIRED per disposition
- Workspace (`/research/workspace`) — REBUILD as Research Workspace
- Graph (`/graph`) — REBUILD as Knowledge Explorer
- Books, Persons, Literature, Classical Versions, Search — MERGE into Library/Knowledge
- V4 Research — MERGE into Research Workspace
- Old admin links beyond `/admin/literature-review`

**All old routes still exist and work.** The navbar `AppNavbar.vue` is untouched.

---

## Administration Current Target

The Administration nav item points to `/admin/literature-review` — the most stable existing admin entry point. When `/admin/documents` (Document Management) is built per the page disposition, the nav target will be updated.

---

## Old Pages Relocated to ResearchPageHeader

The 5 research pages previously had inline title structures. They now use `ResearchPageHeader`:

| Page                    | Old                                     | New                                                              |
| ----------------------- | --------------------------------------- | ---------------------------------------------------------------- |
| `ProjectListPage`       | `<h1>Project List</h1>` + inline styles | `<ResearchPageHeader title="Research" />`                        |
| `ProjectDetailPage`     | `<h1>Project Header</h1>`               | `<ResearchPageHeader title="项目详情" :breadcrumbs="[...]" />`   |
| `ResearchWorkspacePage` | `<h1>Research Header</h1>`              | `<ResearchPageHeader title="研究工作台" :breadcrumbs="[...]" />` |
| `ResearchWorkflowPage`  | `<h1>Research Workflow</h1>`            | `<ResearchPageHeader title="研究流程" :breadcrumbs="[...]" />`   |
| `ResearchResultPage`    | `<h1>Report Header</h1>`                | `<ResearchPageHeader title="研究结果" :breadcrumbs="[...]" />`   |

---

## Route Ordering Note

The new `ResearchAppLayout` routes for `/research` are defined **before** the legacy `path: 'research', redirect: ...` in the router configuration. This ensures the new layout captures `/research` and its children, while the legacy redirect only catches paths that don't match the new structure (backward compatibility).

---

## Responsive Handling

| Breakpoint | Behavior                                                                            |
| ---------- | ----------------------------------------------------------------------------------- |
| >768px     | Fixed 240px sidebar, scrollable content area                                        |
| ≤768px     | Sidebar overlays content, collapsible (default collapsed on mobile via user toggle) |
| All        | Page content switches from `padding: 24px 32px` to `padding: 16px 20px`             |

No animation/transition beyond sidebar width change.

---

## CSS Constraints Followed

- All styles use existing CSS custom properties (`--color-border`, `--color-text-primary`, `--color-accent`, `--color-hover`, `--color-active`, `--color-navbar-bg`, `--color-text-muted`, `--color-text-secondary`)
- No new color system, gradients, shadows, or decorative elements
- No global CSS changes
- No theme or font system modifications
- Layout CSS lives in the layout/component files, not duplicated across pages

---

## Test Results

**Test file**: `src/__tests__/research-app-shell.test.ts` (21 new tests)

All 21 tests pass + all 39 existing tests pass = **60/60 total tests passing**.

Test coverage:

1. ✅ Four research modules displayed in nav
2. ✅ Dashboard/Workspace/Graph NOT in nav
3. ✅ `/research` activates Research nav
4. ✅ `/research/123/workflow` activates Research nav (sub-route)
5. ✅ `/library` activates Library nav
6. ✅ `/knowledge` activates Knowledge nav
7. ✅ `/reports` activates Reports nav
8. ✅ `ResearchPageHeader` renders title correctly
9. ✅ `ResearchPageHeader` actions slot available
10. ✅ All 5 research pages loadable via routes

Additional:

- Administration separator exists
- Collapsed state hides labels but preserves icons
- `meta.section` propagates correctly through matched routes

**Type check**: Clean — `vue-tsc --noEmit` passes with zero errors.
**Build**: Clean — `vite build` succeeds (3.87s).

---

## Files Modified / Created

### New files (11)

```
apps/frontend/src/layouts/ResearchAppLayout.vue
apps/frontend/src/components/layout/ResearchPrimaryNav.vue
apps/frontend/src/components/layout/ResearchPageHeader.vue
apps/frontend/src/pages/library/LibrarySearchPage.vue
apps/frontend/src/pages/knowledge/KnowledgeExplorerPage.vue
apps/frontend/src/pages/reports/ReportListPage.vue
apps/frontend/src/__tests__/research-app-shell.test.ts
docs/20-product/2009-research-app-shell.md
```

### Modified files (6)

```
apps/frontend/src/router/index.ts                       — add ResearchAppLayout routes
apps/frontend/src/pages/research/ProjectListPage.vue     — adopt ResearchPageHeader
apps/frontend/src/pages/research/ProjectDetailPage.vue   — adopt ResearchPageHeader
apps/frontend/src/pages/research/ResearchWorkspacePage.vue — adopt ResearchPageHeader
apps/frontend/src/pages/research/ResearchWorkflowPage.vue — adopt ResearchPageHeader
apps/frontend/src/pages/research/ResearchResultPage.vue  — adopt ResearchPageHeader
```

### NOT modified

- `views/` — all 22 old view files untouched
- `AppNavbar.vue` — untouched
- `DefaultLayout.vue` — untouched
- `AppMain.vue`, `AppFooter.vue` — untouched
- All stores, composables, API modules — untouched

---

## Known Limitations

1. **Route collision**: Legacy `path: 'research', redirect: ...` still exists. The new route group is placed before it to take precedence, but both remain. Final cleanup happens in a later sprint per the page disposition migration plan.

2. **Administration nav target**: Points to `/admin/literature-review` (old review queue). Will update to `/admin/documents` when Document Management is built.

3. **Project placeholder**: "当前项目" badge in sidebar is static text. Not connected to project state (no multi-project store exists yet).

4. **Mobile collapse**: Sidebar collapse is manual (button-triggered), not automatic on mobile breakpoint. Fine for scaffold.

5. **No route transition**: Router-view content switches without animation. Not needed for scaffold.

6. **Library/Knowledge/Reports placeholder pages**: All three show "功能迁移中" — content will arrive in subsequent sprints per the page disposition.

---

## References

- `docs/20-product/2004-page-tree.md` — Target page tree
- `docs/20-product/2007-page-disposition.md` — Page disposition arbitration
- `docs/20-product/2008-research-workflow-pages.md` — Previous scaffold (5 research pages)
