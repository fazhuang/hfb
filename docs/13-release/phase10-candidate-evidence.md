# Phase 10 Candidate Evidence — D2-FINAL 终期归档

## Git 基线

- **Candidate Baseline SHA:** `2667905150ca0da16bd7149774493ad49055ef5d`
- **发布门禁基准 SHA:** `2667905150ca0da16bd7149774493ad49055ef5d`（CI 5/5 全绿门禁）
- **`git status --short`:** Clean worktree — zero uncommitted changes.
- **CI 全绿批次:** 5/5 workflows all passing on `master` (HEAD `2667905`)

## D2-COV — Backend Coverage

- **Command:** `pytest tests/unit/ tests/integration/ --cov=apps/backend --cov-report=json`
- **Result:** 2477 passed, 0 failed, 0 error, 1 deselected
- **Coverage:** `percent_covered` = 90.0244%（≥ 90.0100%）
- **Exit Code:** 0
- **Verdict:** PASS

## D2-E2E — Browser E2E

- **Command:** `pnpm test:e2e`
- **Result:** 27 passed, 0 failed
- **Exit Code:** 0
- **Verdict:** PASS
- **Fix:** `workers=1` in `playwright.config.ts` — eliminates auth-session collisions when running parallel E2E against a single shared backend

## D2-SEC — Security Audit

- **Command:** `pnpm audit --registry https://registry.npmjs.org`
- **Result:** 0 known vulnerabilities
- **Exit Code:** 0
- **Verdict:** PASS

## CI 5/5 Green Gate (master, HEAD `2667905150ca0da16bd7149774493ad49055ef5d`)

| Workflow      | Status     | URL                                                      |
| ------------- | ---------- | -------------------------------------------------------- |
| Build         | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31265795027 |
| Test          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31265795052 |
| Documentation | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31265795033 |
| Lint          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31265795034 |
| Security      | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31265795056 |
