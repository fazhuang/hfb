# Phase 10 Candidate Evidence — D2-FINAL 终期归档

## Git 基线

- **Candidate Baseline SHA:** `2c9470ffd70b202e6ca84a38feba2fffbb6472bb`
- **发布门禁基准 SHA:** `2c9470ffd70b202e6ca84a38feba2fffbb6472bb`（CI 5/5 全绿门禁）
- **`git status --short`:** Clean worktree — zero uncommitted changes. `apps/` 业务代码零变动 (CI fix only).
- **CI 全绿批次:** 5/5 workflows all passing on branch `fix/d2-ci-fix-001` (SHA `2c9470f`)

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

## CI 5/5 Green Gate (SHA `2c9470ffd70b202e6ca84a38feba2fffbb6472bb`)

| Workflow      | Status     | URL                                                      |
| ------------- | ---------- | -------------------------------------------------------- |
| Build         | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31212889386 |
| Test          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31212889485 |
| Lint          | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31212890849 |
| Security      | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31212889907 |
| Documentation | ✅ success | https://github.com/fazhuang/hfb/actions/runs/31212892401 |
