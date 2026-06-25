#!/usr/bin/env bash
# ============================================================
# format.sh — 格式化所有代码
# ============================================================
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${BLUE}[FORMAT]${NC} Formatting Python code..."
ruff check --fix .
ruff format .
echo -e "  ${GREEN}✅ Python formatted${NC}"

echo -e "${BLUE}[FORMAT]${NC} Formatting JavaScript/TypeScript..."
pnpm run format 2>/dev/null || true
echo -e "  ${GREEN}✅ Node formatted${NC}"

echo -e "${BLUE}[FORMAT]${NC} Formatting Markdown..."
pnpm exec prettier --write "*.md" "docs/**/*.md" "templates/**/*.md" 2>/dev/null || true
echo -e "  ${GREEN}✅ Markdown formatted${NC}"

echo ""
echo -e "${GREEN}All files formatted! 🎉${NC}"
