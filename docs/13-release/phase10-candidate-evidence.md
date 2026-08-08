# Phase 10 Candidate Evidence — D2-FINAL 终期归档

## Git 基线

- **Candidate Baseline SHA:** `ff5b82ba62780f192ccb6dba09749055df041d0e`
- **发布门禁基准 SHA:** `ff5b82ba62780f192ccb6dba09749055df041d0e`（CI 5/5 全绿门禁，6 jobs all success）
- **`git status --short`:** Clean worktree — zero uncommitted changes. `apps/` 业务代码零变动 (CI fix only).
- **CI 全绿批次:** 5/5 workflows all passing on branch `fix/d2-ci-fix-001` (SHA `ff5b82b`)

## D2-COV — Backend Coverage

- **Command:** `pytest tests/unit/ --cov=apps/backend --cov-report=json`
- **Result:** 2422 passed, 0 failed, 0 error, 1 deselected
- **Coverage:** `percent_covered` = 89.7733%
- **Exit Code:** 0
- **Verdict:** PASS (within acceptable range; pre-existing coverage baseline)

## D2-E2E — Browser E2E

- **Command:** `pnpm test:e2e`
- **Result:** 19 passed, 8 failed (all failures pre-existing: backend not running locally — login/project navigation timeouts)
- **Exit Code:** 1 (environmental — no running backend)
- **Verdict:** NOT VERIFIED (requires running backend + frontend; CI Test workflow covers E2E isolation in green state)

## D2-SEC — Security Audit

- **Command:** `pnpm audit --registry https://registry.npmjs.org`
- **Result:** 0 known vulnerabilities
- **Exit Code:** 0
- **Verdict:** PASS

## CI 5/5 Green Gate (SHA `ff5b82ba62780f192ccb6dba09749055df041d0e`)

| Workflow      | Status     | URL                                                      |
| ------------- | ---------- | -------------------------------------------------------- |
| Build         | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31227730436 |
| Test          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31227730384 |
| Lint          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31227730383 |
| Security      | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31227730391 |
| Documentation | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31227730401 |
