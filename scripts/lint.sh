#!/usr/bin/env bash
# ============================================================
# lint.sh — 运行所有代码检查
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
    echo -e "${BLUE}[LINT]${NC} $name..."
    if "$@"; then
        echo -e "  ${GREEN}✅ Passed${NC}"
    else
        echo -e "  ${RED}❌ Failed${NC}"
        HAS_ERROR=1
    fi
}

# Python
run_step "Ruff check" ruff check .
run_step "Ruff format check" ruff format --check .
run_step "Mypy" mypy . --config-file=pyproject.toml || true

# Node
run_step "ESLint" pnpm run lint 2>/dev/null || true
run_step "Prettier check" pnpm run format:check 2>/dev/null || true

# Docker
if command -v hadolint >/dev/null 2>&1; then
    run_step "Hadolint (backend)" hadolint docker/dev/Dockerfile.backend
    run_step "Hadolint (frontend)" hadolint docker/dev/Dockerfile.frontend
fi

echo ""
if [ "$HAS_ERROR" -eq 0 ]; then
    echo -e "${GREEN}All lint checks passed! 🎉${NC}"
else
    echo -e "${RED}Some lint checks failed. Please fix the issues above.${NC}"
    exit 1
fi
