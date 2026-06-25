#!/usr/bin/env bash
# ============================================================
# test.sh — 运行所有测试
# ============================================================
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

HAS_ERROR=0

run_step() {
    local name="$1"
    shift
    echo -e "${BLUE}[TEST]${NC} $name..."
    if "$@"; then
        echo -e "  ${GREEN}✅ Passed${NC}"
    else
        echo -e "  ${RED}❌ Failed${NC}"
        HAS_ERROR=1
    fi
}

# Unit tests
run_step "Python unit tests" pytest tests/unit -v --tb=short
run_step "Node unit tests" pnpm run test 2>/dev/null || true

# Coverage
run_step "Coverage report" pytest tests/unit --cov --cov-report=term-missing

echo ""
if [ "$HAS_ERROR" -eq 0 ]; then
    echo -e "${GREEN}All tests passed! 🎉${NC}"
else
    echo -e "${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi
