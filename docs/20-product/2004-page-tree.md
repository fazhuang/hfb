# 2004 — Page Tree

## Purpose

Define the official page tree (information architecture) for the HFB platform post-UI-redesign. This reflects the target state from the page disposition arbitration, not the current codebase.

## Scope

All user-facing pages across all modules: Research, Library, Knowledge, Reports, Administration, Authentication, System.

## Content

```
HFB Platform
│
├── System (Public)
│   ├── /                         Home
│   │   ├── Welcome hero (auth-aware)
│   │   └── Research entry CTA
│   ├── /about                    About
│   │   └── Vision statement
│   ├── /not-found                Not Found (404)
│   └── /error                    Error State (5xx)
│
├── Authentication (Public)
│   ├── /login                    Login
│   ├── /register                 Register
│   └── /access-denied            Access Denied (403)
│
├── Library (Public)
│   ├── /library/search           Library Search
│   │   ├── Full-text search with autocomplete
│   │   ├── Entity type filters (book, person, version, passage, document)
│   │   ├── Dynasty/category facets
│   │   ├── Result cards (polymorphic by entity type)
│   │   └── Pagination
│   ├── /library/:docId           Document Detail
│   │   ├── Document metadata (title, dynasty, category, year, language)
│   │   ├── Compliance panel (copyright, license, review status — auth-only)
│   │   ├── Abstract
│   │   ├── Chapters list → Document Reader
│   │   ├── Versions list → Document Reader
│   │   └── "Ask AI" → Research Workspace
│   ├── /library/:docId/read      Document Reader
│   │   ├── Fulltext reading with expand/collapse
│   │   ├── Chapter navigation (parsed from content)
│   │   ├── Scroll-to-passage anchoring
│   │   └── Passage translation display
│   └── /library/:docId/citation/:citId   Citation Detail
│       ├── Citation metadata (claim, quote, source)
│       ├── Source document link → Document Detail
│       └── Evidence trace → Knowledge Explorer
│
├── Knowledge (Public)
│   ├── /knowledge                            Knowledge Explorer
│   │   ├── Entity search with type filters
│   │   ├── Entity browsing (person, book, version, passage)
│   │   ├── Graph canvas (neighborhood, subgraph, path finding)
│   │   ├── Dynasty/category distribution charts
│   │   └── Deep-link support (?type=&id=, ?trace=)
│   └── /knowledge/:entityType/:entityId      Entity Detail
│       ├── Entity metadata (dynamic by type)
│       ├── Biography/abstract section
│       ├── Related entities
│       ├── Notable works / versions
│       └── External references
│
├── Research (Authenticated)
│   ├── /research                               Project List
│   │   ├── Project cards grid
│   │   ├── Inline project creation
│   │   └── Project actions (open, archive, delete)
│   ├── /research/:projectId                    Project Detail
│   │   ├── Project header (name, description)
│   │   ├── Tools grid:
│   │   │   ├── Research Workspace
│   │   │   ├── Research Workflow
│   │   │   ├── Report List
│   │   │   ├── Notes and Evidence
│   │   │   └── Library Search
│   │   └── Project actions (rename, archive)
│   ├── /research/:projectId/workspace          Research Workspace
│   │   ├── AI Assistant (SSE streaming chat)
│   │   ├── Evidence sidebar (RAG citations + graph preview)
│   │   ├── Citation saving
│   │   ├── Session management
│   │   └── V4 workflow inline execution
│   ├── /research/:projectId/workflow           Research Workflow
│   │   ├── Step 1: Search passages
│   │   ├── Step 2: Select source/target
│   │   ├── Step 3: Diff comparison + operation table
│   │   ├── Step 4: Evidence verification + notes
│   │   └── Export Markdown
│   └── /research/:projectId/result/:runId      Research Result
│       ├── Report content (full text)
│       ├── Citations list (expandable)
│       ├── Citation → Note creation
│       ├── Citation → Citation Collection saving
│       ├── Export Markdown (with notes)
│       ├── Save note
│       ├── Re-search from report
│       └── Replay verification
│
├── Reports (Authenticated)
│   ├── /reports                         Report List
│   │   ├── Report cards (topic, date, steps)
│   │   ├── Step execution trace badges
│   │   └── Report preview snippets
│   ├── /reports/:runId                  Report Detail
│   │   ├── Full report content
│   │   ├── Citations (with deep-link to Knowledge Explorer)
│   │   ├── Citation → Note creation
│   │   ├── Citation saving
│   │   ├── Export Markdown
│   │   ├── Note editor
│   │   └── Evidence trace links
│   └── /notes                           Notes and Evidence
│       ├── Notes grid (by session filter)
│       ├── Quick-note input
│       ├── Session picker
│       ├── Note CRUD
│       └── Evidence browser
│
├── Administration (Authenticated + Admin)
│   ├── /admin/documents                 Document Management
│   │   ├── Review queue (filtered table)
│   │   ├── Copyright status filter
│   │   ├── Review actions (approve/reject)
│   │   ├── RAG enable/disable
│   │   ├── Withdraw document
│   │   └── Click-through to Document Detail
│   ├── /admin/data-quality              Data Quality
│   │   ├── Ingestion task log (filtered table)
│   │   ├── Success/failure metrics
│   │   ├── Source coverage dashboard
│   │   └── Recent errors summary
│   ├── /admin/users                     User and Permission Management
│   │   ├── User list
│   │   ├── Role assignment
│   │   └── Permission management
│   └── /admin/system                    System Operations
│       ├── Source policy management
│       ├── System health status
│       ├── Version and environment info
│       └── Entity counts overview
```

## Page Count Summary

| Module | Pages | Auth Required |
|--------|-------|--------------|
| System | 4 | None |
| Authentication | 3 | Guest-only (login/register), None (access-denied) |
| Library | 4 | None |
| Knowledge | 2 | None |
| Research | 5 | Authenticated |
| Reports | 3 | Authenticated |
| Administration | 4 | Admin/SuperAdmin |
| **Total** | **25** | — |

## References

- `docs/20-product/2006-page-inventory.md` — Current page inventory
- `docs/20-product/2007-page-disposition.md` — Page disposition arbitration
- `apps/frontend/src/router/index.ts` — Current router definition
- `apps/frontend/src/components/layout/AppNavbar.vue` — Current navbar links
