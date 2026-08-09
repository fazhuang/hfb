# Phase 10 Candidate Evidence — D2-FINAL 终期归档

## Git 基线

- **Candidate Baseline SHA:** `b8ebd0c620714c283d009006639f3efc4297743d`
- **发布门禁基准 SHA:** `b8ebd0c620714c283d009006639f3efc4297743d`（CI 5/5 全绿门禁）
- **`git status --short`:** Clean worktree — `coverage.json` 已由 `.gitignore` 忽略。
- **CI 全绿批次:** 5/5 workflows all passing on `master` (HEAD `b8ebd0c`)

## D2-COV — Backend Coverage

- **Command:** `pytest tests/unit/ tests/integration/ --cov=apps/backend --cov-report=json:coverage.json --cov-report=term-missing`
- **Result:** 2481 passed, 1 deselected, 0 failed, 0 error
- **Coverage:** `percent_covered` = 90.0174%（≥ 90.0100%）
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

## CI 5/5 Green Gate (master, HEAD `b8ebd0c620714c283d009006639f3efc4297743d`)

| Workflow      | Status     | URL                                                      |
| ------------- | ---------- | -------------------------------------------------------- |
| Build         | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31278196268 |
| Test          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31278196273 |
| Documentation | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31272102204 |
| Lint          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31278196276 |
| Security      | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31278196267 |
