# Phase 10 Candidate Evidence — D2-FINAL 终期归档

## Git 基线

- **Candidate Baseline SHA:** `5f1ea42249c87f5030ec3f0aea4284ae7b8b0aa9`
- **发布门禁基准 SHA:** `5f1ea42249c87f5030ec3f0aea4284ae7b8b0aa9`（CI 5/5 全绿门禁）
- **`git status --short`:** Clean worktree — `coverage.json` 已由 `.gitignore` 忽略。
- **CI 全绿批次:** 5/5 workflows all passing on `master` (HEAD `5f1ea42`)

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

## CI 5/5 Green Gate (master, HEAD `5f1ea42249c87f5030ec3f0aea4284ae7b8b0aa9`)

| Workflow      | Status     | URL                                                      |
| ------------- | ---------- | -------------------------------------------------------- |
| Build         | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31295398193 |
| Test          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31295398226 |
| Documentation | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31295398194 |
| Lint          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31295398187 |
| Security      | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31295398192 |
