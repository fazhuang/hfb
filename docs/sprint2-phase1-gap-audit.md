# Phase 1 Gap Audit — Design Tokens vs Common Components

**Date:** 2026-08-11
**Scope:** `apps/frontend/src/styles/tokens/*.css` × 5 components (HfbButton, HfbBadge, HfbDrawer, HfbSelect, HfbInput) + HfbTextarea shared contract
**Baseline:** HEAD `6bb825f0f1a13b62c3e2ae60b2ef26a75a3bc281` + uncommitted changes to `input.css`, `select.css` (state depends on both committed HEAD and pending working-tree modifications)


---

## Summary

| Component | Hardcoded Values | Missing Tokens | Token Naming Issues | Severity |
|-----------|-----------------|----------------|---------------------|----------|
| HfbButton | 5 | 3 | 0 | Medium |
| HfbBadge | 8 | 1 | 1 | High |
| HfbDrawer | 7 | 2 | 0 | Medium |
| HfbSelect | 3 | 1 | 0 | Low |
| HfbInput | 2 | 0 | 0 | Low |
| **Token System** | — | 6 | 0 | High |

**Critical path:** HfbBadge > Token System > HfbButton > HfbDrawer > HfbSelect > HfbInput

---

## 1. HfbButton (`button.css`)

**Token compliance: 85%** — Most properties tokenized. 5 hardcoded values, 3 missing tokens.

### G1.1 — Hardcoded spinner dimensions
```css
/* button.css:141-142 */
.hfb-button__spinner {
  width: 14px;   /* ← hardcoded, should be --space-3-5 */
  height: 14px;
  border: 2px solid currentColor;  /* ← 2px hardcoded */
}
```
**Fix:** Add `--component-spinner-size: 14px` and `--component-spinner-border: 2px` to `components.css`, or use `--space-3-5` for size. `border-width` has no token anywhere.

### G1.2 — Hardcoded disabled opacity
```css
/* button.css:123-133 */
.hfb-button--secondary:disabled { opacity: 0.5; }
.hfb-button--ghost:disabled     { opacity: 0.4; }
.hfb-button--danger:disabled    { opacity: 0.5; }
```
**Fix:** Add `--opacity-disabled: 0.5` and `--opacity-disabled-light: 0.4` to `components.css`. Inconsistency already present: secondary/danger 0.5, ghost 0.4 — needs design decision.

### G1.3 — Hardcoded active scale
```css
/* button.css:61,109 */
.hfb-button--primary:active:not(:disabled) { transform: scale(0.98); }
.hfb-button--danger:active:not(:disabled)  { transform: scale(0.98); }
```
**Fix:** Add `--btn-active-scale: 0.98` to `components.css`.

### G1.4 — Hardcoded focus-visible outline
```css
/* button.css:151-153 */
.hfb-button:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```
**Fix:** Add `--focus-outline-width: 2px` and `--focus-outline-offset: 2px` to `components.css`, or consolidate with existing `--focus-ring` pattern (currently uses `box-shadow` not `outline`).

### G1.5 — Focus ring pattern mismatch
Button uses `outline` for focus. Select and Input use `box-shadow` (via `--focus-ring` / `--color-input-focus-ring`). Inconsistent focus mechanism across components.

**Fix:** Standardize on single focus pattern. `box-shadow` preferred (does not affect layout, works on rounded corners).

---

## 2. HfbBadge (`badge.css`)

**Token compliance: 55%** — Worst offender. 8 hardcoded values, 1 missing token, 1 naming issue.

### G2.1 — Hardcoded font-size
```css
/* badge.css:11 */
.hfb-badge { font-size: 12px; }    /* ← should be var(--text-xs) */
/* badge.css:22 */
.hfb-badge--md { font-size: 13px; } /* ← should be var(--text-sm) */
```
`--text-xs: 12px` and `--text-sm: 13px` match exactly. Pure tokenization gap — no value change needed.

### G2.2 — Hardcoded padding values
```css
/* badge.css:11 */
.hfb-badge { padding: var(--space-0-5) 8px; }       /* 8px → --space-2 */
/* badge.css:21 */
.hfb-badge--md { padding: var(--space-0-75) 10px; }  /* 10px → --space-2-5 */
/* badge.css:28 */
.hfb-badge--pill { padding: var(--space-0-75) 12px; } /* 12px → --space-3 */
/* badge.css:35 */
.hfb-badge--dot { padding: var(--space-0-5) 10px; }   /* 10px → --space-2-5 */
```
4 instances of hardcoded horizontal padding.

### G2.3 — Hardcoded pill border-radius
```css
/* badge.css:27 */
.hfb-badge--pill { border-radius: 9999px; }  /* ← should be var(--radius-full) */
```
`--radius-full: 9999px` exists in `radius.css`. Pure tokenization gap.

### G2.4 — Hardcoded dot dimensions
```css
/* badge.css:37-39 */
.hfb-badge__dot {
  width: 8px;   /* ← should be var(--space-2) */
  height: 8px;
}
```

### G2.5 — Neutral variant naming
Badge uses `--color-tag-bg` for neutral variant background. No `--color-neutral-*` token family exists. `--color-tag-bg` is a layout/surface token (`colors.css:21`), not a semantic color. If badge is the canonical neutral badge, token should be named `--color-neutral-bg` or badge should reference a dedicated badge token.

**Fix:** Either add `--badge-neutral-bg`, `--badge-neutral-text`, `--badge-neutral-border` to `components.css`, or add `--color-neutral-*` family to `semantic.css`.

---

## 3. HfbDrawer (`drawer.css`)

**Token compliance: 78%** — 7 hardcoded values, 2 missing token categories.

### G3.1 — Hardcoded widths
```css
/* drawer.css:53-68 */
.hfb-drawer--sm { width: 320px; }
.hfb-drawer--md { width: 480px; }
.hfb-drawer--lg { width: 640px; }
.hfb-drawer--xl { width: 800px; }
```
**Fix:** Add `--drawer-width-sm: 320px`, `--drawer-width-md: 480px`, `--drawer-width-lg: 640px`, `--drawer-width-xl: 800px` to `components.css`.

### G3.2 — Hardcoded heights
```css
/* drawer.css:70-81 */
.hfb-drawer--sm { height: 200px; }
.hfb-drawer--md { height: 360px; }
.hfb-drawer--lg { height: 480px; }
```
**Fix:** Add `--drawer-height-sm: 200px`, `--drawer-height-md: 360px`, `--drawer-height-lg: 480px` to `components.css`.

### G3.3 — Hardcoded close button dimensions
```css
/* drawer.css:100-105 */
.hfb-drawer__close {
  width: 28px;    /* ← should be --space-7 */
  height: 28px;
  font-size: 18px; /* ← no matching text token (--text-lg=16px, --text-xl=20px) */
}
```
Width/height map to `--space-7: 28px`. Font-size 18px has no typography token — `--text-lg` is 16px, `--text-xl` is 20px. Gap in typography scale.

### G3.4 — Missing 18px typography token
Typography scale: `12, 13, 14, 16, 20, 22, 24`. 18px is missing. Drawer close button needs it.

**Fix:** Add `--text-lg-plus: 18px` or restructure scale to include 18px.

---

## 4. HfbSelect (`select.css`)

**Token compliance: 90%** — 3 hardcoded values, 1 missing token.

### G4.1 — Hardcoded menu max-height
```css
/* select.css:94 */
.hfb-select__menu { max-height: 240px; }
```
**Fix:** Add `--select-menu-max-height: 240px` to `components.css`.

### G4.2 — Hardcoded error ring
```css
/* select.css:66 */
.hfb-select__trigger--error { box-shadow: 0 0 0 1px var(--color-error); }
```
`1px` hardcoded. Compare input.css which uses `--focus-ring-error: 0 0 0 3px rgba(252, 129, 129, 0.3)` for focus-error — different approach (1px solid vs 3px rgba).

### G4.3 — Error ring inconsistency with HfbInput
| Component | Error State | Focus+Error State |
|-----------|-------------|-------------------|
| HfbSelect | `box-shadow: 0 0 0 1px var(--color-error)` | No separate focus+error |
| HfbInput | `box-shadow: 0 0 0 1px var(--color-error)` | `box-shadow: var(--focus-ring-error)` (3px rgba) |

HfbInput has a distinct focus-error ring (3px), HfbSelect does not. Input error ring is 1px solid; input error+focus ring is 3px rgba. Select has no error+focus differentiation.

**Fix:** Standardize error and error+focus ring across all form components. Add `--form-error-ring: 0 0 0 1px var(--color-error)` token.

### G4.4 — Hardcoded zero padding
```css
/* select.css:99 */
.hfb-select__menu { padding: var(--space-1) 0; }
```
`0` should be `var(--space-0)`. Minor.

---

## 5. HfbInput (`input.css`)

**Token compliance: 92%** — Best compliance. 2 hardcoded values, 0 missing tokens.

### G5.1 — Same error ring issue as Select
```css
/* input.css:71 */
.hfb-input__field--error { box-shadow: 0 0 0 1px var(--color-error); }
```
Same `1px` hardcoding. Falls under G4.3 umbrella fix.

### G5.2 — Prefix/suffix padding override
```css
/* input.css:132-137 */
.hfb-input__container--with-prefix .hfb-input__field { padding-left: var(--space-1); }
.hfb-input__container--with-suffix .hfb-input__field { padding-right: var(--space-1); }
```
Uses token correctly. No issue — noting for completeness.

### G5.3 — HfbTextarea Shared Class & CSS Import Contract
`HfbTextarea.vue` (`apps/frontend/src/components/common/HfbTextarea.vue`) imports `input.css` and reuses `hfb-input-*` class namespace.
- **Import audit:** `<style scoped>@import '../../styles/base/input.css';</style>` — CSS `@import`, not JS `import`.
- **Class audit:** Reuses `.hfb-input-wrapper`, `.hfb-input__label`, `.hfb-input__required`, `.hfb-input__field`, `.hfb-input__field--error`, `.hfb-input__error`, `.hfb-input__hint`, `.hfb-input__footer`. Does NOT reuse `.hfb-input__container`.
- **Conflict check:** No class collisions detected. However, any Tokenization changes to `HfbInput` or `input.css` **must be validated concurrently against `HfbTextarea`** to prevent styling regressions.

---

## 6. Token System Gaps

These are missing from the token layer itself — shared across components.

### G6.1 — No opacity tokens
`components.css` has no opacity scale. Used by button disabled states (0.4, 0.5).

**Fix:** Add to `components.css`:
```css
--opacity-disabled: 0.5;
--opacity-disabled-light: 0.4;
```

### G6.2 — No active/press scale token
Button active state uses `scale(0.98)`. No token for interaction scales.

**Fix:** Add `--btn-active-scale: 0.98` to `components.css`.

### G6.3 — No focus outline tokens
Focus pattern split across components: button uses `outline`, form controls use `box-shadow`. No shared focus-width or focus-offset tokens.

**Fix:** Standardize on `box-shadow` pattern. Token set already has `--focus-ring`, `--focus-ring-sm`, `--focus-ring-error`, `--focus-ring-accent`, `--shadow-focus-*`. Consider consolidating duplicates (`--focus-ring` = `--shadow-focus-ring`, `--focus-ring-accent` = `--shadow-accent-focus`).

### G6.4 — Duplicate focus ring tokens
| Token | Value | Defined In |
|-------|-------|-----------|
| `--focus-ring-accent` | `0 0 0 2px rgba(43, 108, 176, 0.2)` | `components.css` |
| `--shadow-accent-focus` | `0 0 0 2px rgba(43, 108, 176, 0.2)` | `shadow.css` |
| `--focus-ring` | `0 0 0 3px rgba(66, 153, 225, 0.15)` | `components.css` |
| `--shadow-focus-ring` | `0 0 0 3px rgba(66, 153, 225, 0.15)` | `shadow.css` |
| `--shadow-accent-sm` | `0 2px 8px rgba(43, 108, 176, 0.1)` | `shadow.css:15,22` — **duplicate definition** |

5 duplicated token pairs. `shadow.css` line 15 and 22 both define `--shadow-accent-sm` identically.

### G6.5 — No form-specific error ring token
HfbSelect and HfbInput both use `0 0 0 1px var(--color-error)` inline. No `--form-error-ring` token.

**Fix:** Add `--form-error-ring: 0 0 0 1px var(--color-error)` to `components.css`.

### G6.6 — Missing 18px typography step
Typography scale: 12, 13, 14, 16, 20, 22, 24. Gap at 18px. Drawer close button needs it.

**Fix:** Add `--text-lg-plus: 18px` or rework scale.

---

## 7. Consolidation Opportunities

### C1 — Focus mechanism unification
| Current State | Proposed |
|---------------|----------|
| Button: `outline: 2px solid` | All: `box-shadow: var(--focus-ring)` |
| Select/Input: `box-shadow: var(--focus-ring)` | Same |

### C2 — Duplicate token cleanup
Remove from `shadow.css` (keep in `components.css` as canonical):
- `--shadow-accent-focus` (dup of `--focus-ring-accent`)
- `--shadow-focus-ring` (dup of `--focus-ring`)
- `--shadow-accent-sm` duplicate definition on lines 15 and 22

Or merge component tokens into `shadow.css` and delete `components.css` focus tokens. Either direction — pick one canonical home.

### C3 — Error ring standardization
| State | Pattern |
|-------|---------|
| HfbInput error | `box-shadow: 0 0 0 1px var(--color-error)` |
| HfbInput error+focus | `box-shadow: var(--focus-ring-error)` (3px) |
| HfbSelect error | `box-shadow: 0 0 0 1px var(--color-error)` |
| HfbSelect error+focus | Missing |

Standardize to: error state = `var(--form-error-ring)`, error+focus = `var(--focus-ring-error)`.

---

## 8. Prioritized Action Items

### P0 — Do immediately (high impact, low risk)
1. **Badge tokenization** (G2.1–G2.4): Replace all hardcoded `font-size`, `padding`, `border-radius`, `width`/`height` with tokens. 8 line changes, zero visual diff.
2. **Remove duplicate `--shadow-accent-sm`** in `shadow.css` line 22.

### P1 — This sprint (medium impact)
3. **Opacity tokens** (G6.1): Add `--opacity-disabled`, `--opacity-disabled-light`.
4. **Active scale token** (G1.3/G6.2): Add `--btn-active-scale`.
5. **Menu max-height token** (G4.1): Add `--select-menu-max-height`.
6. **Form error ring token** (G6.5): Add `--form-error-ring`.

### P2 — Next sprint (lower impact, needs design alignment)
7. **Drawer dimension tokens** (G3.1–G3.2): Add `--drawer-width-*` and `--drawer-height-*` tokens.
8. **Focus mechanism unification** (C1): Migrate button from `outline` to `box-shadow`.
9. **Duplicate focus token cleanup** (C2): Single canonical home.
10. **18px typography token** (G6.4): Add to scale.

### P3 — Defer (nice to have)
11. **Spinner tokenization** (G1.1): Low visual impact.
12. **Badge neutral naming** (G2.5): Semantic naming decision needed first.

---

## 9. Verification Checklist

After fixes applied to any component, verify:
- [ ] `grep -nE '[0-9]+px' apps/frontend/src/styles/base/<component>.css` returns zero non-token, non-zero px values
- [ ] `grep -nE '9999px' apps/frontend/src/styles/base/badge.css` returns zero
- [ ] `npx eslint apps/frontend/src/components/common/<Component>.vue` passes
- [ ] `npx vue-tsc --noEmit` passes
- [ ] `pnpm --filter @hfb/frontend test` passes
- [ ] Visual regression: component screenshots match baseline (run Playwright visual tests if available)

---

*Generated by Phase 1 Gap Audit. No components modified. Report only.*
