# 2008 — Research Workflow Pages

> **Generated**: 2026-07-17
> **Sprint**: UI Sprint 1
> **Scope**: Research module scaffold — 5 new pages, 5 new routes

---

## Purpose

Document the newly scaffolded Research Workflow pages, their routes, directory structure, and relationships. These pages form the skeleton of the redesigned research module per the page tree (`2004-page-tree.md`) and page disposition (`2007-page-disposition.md`).

---

## New Pages

| # | File | Page Name | Route | Auth |
|---|------|-----------|-------|------|
| 1 | `pages/research/ProjectListPage.vue` | Project List | `/research` | Authenticated |
| 2 | `pages/research/ProjectDetailPage.vue` | Project Detail | `/research/:projectId` | Authenticated |
| 3 | `pages/research/ResearchWorkspacePage.vue` | Research Workspace | `/research/:projectId/workspace` | Authenticated |
| 4 | `pages/research/ResearchWorkflowPage.vue` | Research Workflow | `/research/:projectId/workflow` | Authenticated |
| 5 | `pages/research/ResearchResultPage.vue` | Research Result | `/research/:projectId/result/:runId` | Authenticated |

---

## New Routes

All routes are added at the end of `router/index.ts` under the existing `DefaultLayout` children. No existing routes were modified or removed.

```typescript
// Project List
{ path: 'research', name: 'research-project-list', component: ProjectListPage, meta: { requiresAuth: true } }

// Project Detail
{ path: 'research/:projectId', name: 'research-project-detail', component: ProjectDetailPage, meta: { requiresAuth: true } }

// Research Workspace
{ path: 'research/:projectId/workspace', name: 'research-project-workspace', component: ResearchWorkspacePage, meta: { requiresAuth: true } }

// Research Workflow
{ path: 'research/:projectId/workflow', name: 'research-project-workflow', component: ResearchWorkflowPage, meta: { requiresAuth: true } }

// Research Result
{ path: 'research/:projectId/result/:runId', name: 'research-project-result', component: ResearchResultPage, meta: { requiresAuth: true } }
```

**Route collision note**: The existing `/research` redirect (`path: 'research'` → `/research/workspace?tab=research`) takes precedence over the new `research-project-list` route due to definition order. The new route becomes active once the legacy redirect is retired per the page disposition migration plan.

---

## Directory Structure

```
apps/frontend/src/pages/research/
├── ProjectListPage.vue          # /research
├── ProjectDetailPage.vue        # /research/:projectId
├── ResearchWorkspacePage.vue    # /research/:projectId/workspace
├── ResearchWorkflowPage.vue     # /research/:projectId/workflow
└── ResearchResultPage.vue       # /research/:projectId/result/:runId
```

---

## Page Relationships

```
/research                              ProjectListPage
  │                                      ├── Search box
  │                                      ├── Project list
  │                                      └── Pagination
  │
  └── /research/:projectId              ProjectDetailPage
        │                                  ├── Project Header
        │                                  ├── Project Metadata
        │                                  ├── Research Sessions
        │                                  ├── Reports
        │                                  └── Notes
        │
        ├── /research/:projectId/workspace   ResearchWorkspacePage
        │                                      ├── Research Header
        │                                      ├── Continue Research
        │                                      ├── Recent Projects
        │                                      ├── Recent Reports
        │                                      ├── Recent Notes
        │                                      └── AI Research Assistant (sidebar)
        │
        ├── /research/:projectId/workflow    ResearchWorkflowPage
        │                                      ├── Step 1: Research Question
        │                                      ├── Step 2: Document Selection
        │                                      ├── Step 3: AI Analysis
        │                                      ├── Step 4: Evidence Review
        │                                      └── Step 5: Research Report
        │
        └── /research/:projectId/result/:runId  ResearchResultPage
                                                 ├── Report Header
                                                 ├── Summary
                                                 ├── Evidence
                                                 ├── Citation
                                                 └── Export
```

---

## Page Structure Conventions

All pages follow the same structural conventions:

- **Layout**: All pages render within `DefaultLayout` (navbar + content + footer), no custom layout
- **Max width**: Consistent max-width per page type (1200px workspace, 900px list/detail, 720px workflow)
- **Naming**: `XxxPage.vue` suffix, PascalCase
- **Props**: None — pages receive params via `useRoute()`
- **State**: No store, no API, no composable dependencies in scaffold state
- **Styles**: Scoped `<style scoped>`, CSS custom properties via `var(--color-*, fallback)`
- **Sections**: Placeholder sections wrapped in dashed-border containers for visual identification

---

## What Was NOT Done

- No visual design applied (pure scaffold)
- No business logic implemented
- No API calls or store integrations
- No form inputs or interactive elements beyond structural placeholders
- No old pages modified or deleted
- No old routes removed or changed
- No V4 migration or merging implemented
- No permission changes

---

## References

- `docs/20-product/2004-page-tree.md` — Target page tree
- `docs/20-product/2007-page-disposition.md` — Page disposition arbitration
- `apps/frontend/src/pages/research/` — New page directory
- `apps/frontend/src/router/index.ts` — Router with new routes appended
