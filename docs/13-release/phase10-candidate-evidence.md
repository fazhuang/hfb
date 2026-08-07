# Phase 10 Candidate Evidence — D2-COV-003

## Commit SHA

`57a946eb8de19b649439901fd0524c7e9186cd8c`

## Test Execution — Full Coverage Suite (Re-run)

**Date:** 2026-08-07
**Harness:** `/private/tmp/hfb-d2-harness/bin/python` (Python 3.13.13)
**Command:** `pytest tests/unit/ tests/integration/ apps/backend/tests/ --cov=apps/backend --cov-report=json --cov-report=term-missing`
**Exit Code:** 0
**Result:** 3244 passed, 0 failed, 0 error, 1 deselected
**Duration:** 413.99s (0:06:53)

### Coverage Summary

```
Name     Stmts   Miss Branch BrPart  Cover
TOTAL   11207    964   3128    284    90%
```

- `percent_covered_display`: **90%**
- `percent_covered` (raw): 89.58%
- Statements: **91%**
- Branches: 83%

### Snippet from Full Log

```
apps/backend/scripts/backfill_passage.py        78      6     28      3    92%
-------------------------------------------------------------------------------
TOTAL                                        11207    964   3128    284    90%
Coverage JSON written to file coverage.json
Required test coverage of 70.0% reached. Total coverage: 89.58%
================ 3244 passed, 1 deselected in 413.99s (0:06:53) ================
FINAL_EXIT=0
```

## Workspace Status

```
 M tests/conftest.py
 M tests/unit/test_ai.py
 M tests/unit/test_chunking.py
 M tests/unit/test_generation_proof.py
 M tests/unit/test_source_whitelist.py
 M tests/unit/test_sprint2_academic.py
 M tests/unit/test_v1_entities_api.py
?? apps/backend/tests/test_research_workflow_service.py
?? apps/backend/tests/unit/
?? coverage.json
?? docs/13-release/phase10-candidate-evidence.md
?? tests/unit/test_p10_cov_005.py
```

## No Business Code Changes

```
git diff HEAD~1 -- apps/backend/  → (empty, 0 lines changed)
```

## Verdict

**PASS** — Backend TOTAL 90% (display), Exit Code 0, 3244 tests green. D2-COV-003 threshold met.
