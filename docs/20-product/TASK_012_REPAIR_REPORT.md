# Task 012 Repair Report (Phase 1)

## Repair Date

2026-07-24

## Baseline

This repair is based on the **Phase 0 Supplemental Audit** (`docs/20-product/TASK_012_SUPPLEMENTAL_AUDIT.md`), which identified 6 issues (0 Critical / 0 High / 1 Medium / 3 Low / 1 Style / 1 None). Per Phase 1 scope, only issues within the allowed modification scope are addressed.

## Repaired Issues

### Summary

| Issue  | Impact | Status          | Fix                                                                                              |
| ------ | ------ | --------------- | ------------------------------------------------------------------------------------------------ |
| **P1** | Low    | ✅ Fixed        | Corrected misleading "Scroll behavior" comment in `router/index.ts`                              |
| **P2** | Low    | ✅ Fixed        | Removed empty `onMounted(() => {})` and `onBeforeUnmount(() => {})` from `ResearchAppLayout.vue` |
| **P3** | Style  | ✅ Fixed        | Merged two `router.afterEach` hooks into a single registration                                   |
| **P6** | Medium | ✅ Fixed        | Added design documentation for `ral-mobile-toggle` (z-index:300) + sidebar in-flow               |
| P4     | Flake  | ⬜ Not in scope | Intermittent B2 Tablet "Page crashed" — CI resource competition, not a code defect               |
| P5     | None   | ⬜ Not in scope | `sr-only` class pre-dates Task 012; no code change needed                                        |

### Not Modified

Per Phase 0 audit prohibitions, the following remain untouched:

- ❌ Route path / name / redirect / children definitions
- ❌ Sidebar in-flow strategy
- ❌ `[data-main-content]` attribute and `tabindex="-1"`
- ❌ ResearchAppLayout responsive breakpoints (`@media (max-width: 768px)`)
- ❌ `router.beforeEach` auth guard
- ❌ Task 011 / Task 012 E2E specs (no assertion changes)
- ❌ All component business logic, API calls, data model, permissions
- ❌ Global CSS rules (`prefers-reduced-motion`, `:focus-visible`, `.sr-only`)

---

## Fix Detail — P1: Misleading Comment in Router

### Audit Finding

`router/index.ts` L311–312: The comment on the first `afterEach` hook read "Scroll behavior — Reset scroll to top on forward navigation; restore saved position on back/forward." but the code only set `document.title` — no scroll logic existed.

### Fix

Rewrote the combined block comment to accurately describe the actual behavior:

```ts
// ---- Document title & focus management ----
// After each navigation: set document.title from route meta, then move
// focus to the main content area so screen-reader and keyboard users
// land on the page content.
```

### Files Changed

| File                                | Change                                                                                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/frontend/src/router/index.ts` | L311–330: Replaced misleading "Scroll behavior" + separate "Focus management" sections with a single accurate block comment and merged hook |

---

## Fix Detail — P2: Empty Lifecycle Hooks in ResearchAppLayout

### Audit Finding

`ResearchAppLayout.vue` L65–66: Empty `onMounted(() => {})` and `onBeforeUnmount(() => {})` calls — historical iteration residue with no effect.

### Fix

Removed the two empty lifecycle calls and their imports. Replaced with expanded inline documentation explaining the sidebar in-flow design and mobile toggle positioning contract.

### Files Changed

| File                                              | Change                                                                                                              |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `apps/frontend/src/layouts/ResearchAppLayout.vue` | L54: `import { ref } from 'vue'` (removed `onMounted, onBeforeUnmount`)                                             |
| `apps/frontend/src/layouts/ResearchAppLayout.vue` | L61–69: Removed `onMounted(() => {}); onBeforeUnmount(() => {});`, replaced with design documentation comment block |

---

## Fix Detail — P3: Merge Two afterEach Hooks

### Audit Finding

`router/index.ts`: Two separate `router.afterEach` registrations existed (L313–317 for title, L322–330 for focus). They shared the same trigger (every navigation) and had no ordering dependency, so they should be a single hook.

### Fix

Merged into one `router.afterEach` that handles both `document.title` and `focus` management in sequence.

### Files Changed

| File                                | Change                                                                          |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| `apps/frontend/src/router/index.ts` | L311–330: Single `afterEach` registration (was two) with combined comment block |

---

## Fix Detail — P6: Mobile Toggle Design Documentation

### Audit Finding

`ResearchAppLayout.vue`: `.ral-mobile-toggle` uses `position:fixed; z-index:300` while the sidebar remains in-flow (`position:sticky`). This spatial independence is intentional (avoids layout thrash, preserves nav-link reachability) but was undocumented.

### Fix

Added an explicit design comment in the `<script>` block explaining the spatial contract between `.ral-mobile-toggle` and the in-flow sidebar.

```ts
// The .ral-mobile-toggle button (position:fixed, z-index:300) only
// appears at ≤768px via @media query. At that width the sidebar remains
// in-flow (position:sticky), so the toggle is spatially independent of
// the sidebar — it does not push or reposition the sidebar, which stays
// in the document flow for nav-link reachability.
```

### Files Changed

| File                                              | Change                                                       |
| ------------------------------------------------- | ------------------------------------------------------------ |
| `apps/frontend/src/layouts/ResearchAppLayout.vue` | L61–69: Documentation comment replaces empty lifecycle hooks |

---

## Test Evidence

### New Tests (13 added)

| Test File                                          | Tests | Covers                                                                                                               |
| -------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------- |
| `src/__tests__/router-aftereach-repair.test.ts`    | 6     | P1 (accurate title behavior + comment semantics), P3 (single merged hook)                                            |
| `src/__tests__/research-app-layout-repair.test.ts` | 7     | P2 (layout renders without empty hooks), P6 (mobile toggle design contract + sidebar invariants + data-main-content) |

All 13 new tests verify specific repair assertions:

- **router-aftereach-repair.test.ts**: title from meta with fallback brand, "· HFB" suffix, focus management with `preventScroll: true`, no-throw on absent element, both title+focus in one hook
- **research-app-layout-repair.test.ts**: layout renders, sidebar expand/collapse toggle, mobile toggle ARIA label correctness (expand/collapse states), [data-main-content] + tabindex="-1" present, sidebar display≠none (in-flow invariant), mobile toggle CSS class existence

### Pre-existing Test Preservation

No existing test assertions were modified, relaxed, skipped, or deleted. All 371 original tests pass with zero changes.

---

## Verification Results

| Check                     | Command                                                          | Result                                                  |
| ------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------- |
| Type Check                | `npx vue-tsc --noEmit`                                           | ✅ Zero errors                                          |
| Unit Tests                | `npx vitest run`                                                 | ✅ **384/384** (371 original + 13 new, 16 files, 8.95s) |
| Build                     | `npx vite build`                                                 | ✅ 4.12s (363 modules, zero warnings)                   |
| Task 012 E2E              | `npx playwright test ... task012-interaction-responsive.spec.ts` | ✅ **184/184** (4.2m, 0 fail/skip/fixme)                |
| Task 011 E2E (regression) | `npx playwright test ... task011-navigation-consistency.spec.ts` | ✅ **116/116** (3.7m, 0 fail)                           |

All E2E tests executed against real backend (`127.0.0.1:8000`, health=200) + real seed data + `researcher` account across 4 viewports (Mobile 375×812 / Tablet 768×1024 / Desktop 1280×800 / Wide 1440×900).

---

## Changed Files Summary

| File                                                             | Lines Changed | Purpose                                 |
| ---------------------------------------------------------------- | ------------- | --------------------------------------- |
| `apps/frontend/src/router/index.ts`                              | ~10           | P1: comment correction + P3: hook merge |
| `apps/frontend/src/layouts/ResearchAppLayout.vue`                | ~4            | P2: remove empty hooks + P6: design doc |
| `apps/frontend/src/__tests__/router-aftereach-repair.test.ts`    | +161 new      | P1 + P3 test coverage                   |
| `apps/frontend/src/__tests__/research-app-layout-repair.test.ts` | +160 new      | P2 + P6 test coverage                   |

**Total: 4 files modified/created, ~24 lines changed in source, ~321 lines of new test code.**

---

## Conclusion

Phase 1 Task 012 repair: **ALL 4 issues in scope (P1, P2, P3, P6) fixed.** All gates green — Type Check, 384/384 Unit Tests, Build, 184/184 Task 012 E2E, 116/116 Task 011 regression. No test assertions relaxed or skipped. No re-design of Router. No API/permission/data-model changes. Research link frozen baselines preserved.
