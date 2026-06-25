#!/usr/bin/env bash
# ============================================================
# setup.sh — 一键初始化开发环境
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

log()  { echo -e "${BLUE}[SETUP]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  皇甫谧数字人文平台 — 环境初始化${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""

# --- Check prerequisites ---
log "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || err "Python 3.12+ required. Install from https://python.org"
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
py_ver=$(echo "$PYTHON_VERSION" | awk -F. '{print $1*100 + $2}')
[ "$py_ver" -ge 312 ] || err "Python >= 3.12 required. Current: $PYTHON_VERSION"
ok "Python $PYTHON_VERSION"

command -v node >/dev/null 2>&1 || err "Node.js 22+ required. Install from https://nodejs.org"
NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
[ "$NODE_VERSION" -ge 22 ] || warn "Node >= 22 recommended. Current: $(node -v)"
ok "Node $(node -v)"

command -v pnpm >/dev/null 2>&1 || {
    warn "pnpm not found. Installing via corepack..."
    corepack enable && corepack prepare pnpm@10 --activate
}
PNPM_VERSION=$(pnpm -v)
pnpm_ver=$(echo "$PNPM_VERSION" | awk -F. '{print $1}')
[ "$pnpm_ver" -ge 10 ] || warn "pnpm >= 10 recommended. Current: $PNPM_VERSION"
ok "pnpm $PNPM_VERSION"

command -v docker >/dev/null 2>&1 || warn "Docker not found. Some features require Docker."
command -v git >/dev/null 2>&1 || err "Git is required."

# --- Setup Python environment ---
log "Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "Created .venv"
else
    ok ".venv already exists"
fi

source .venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1
pip install -e ".[dev]" >/dev/null 2>&1
ok "Python dependencies installed"

# --- Setup Node environment ---
log "Setting up Node environment..."
pnpm install --frozen-lockfile 2>/dev/null || pnpm install
ok "Node dependencies installed"

# --- Setup pre-commit hooks ---
log "Setting up pre-commit hooks..."
pre-commit install --install-hooks >/dev/null 2>&1 || warn "pre-commit setup skipped (run 'pre-commit install' manually)"
ok "Pre-commit hooks installed"

# --- Setup .env ---
if [ ! -f ".env" ]; then
    cp .env.example .env
    ok "Created .env from .env.example (please edit with your values)"
else
    ok ".env already exists"
fi

# --- Verify .env ---
log "Verifying .env configuration..."
bash scripts/verify-env.sh || warn "Some .env variables need attention (see above)"

# --- Create git branch ---
log "Checking git setup..."
if [ "$(git branch --show-current)" = "main" ]; then
    warn "You are on main branch. Consider creating a feature branch."
fi

# --- Done ---
echo ""
echo -e "${GREEN}${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}  ✅ Setup complete!${NC}"
echo -e "${GREEN}${BOLD}============================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your local settings"
echo "  2. Run: make dev"
echo "  3. Visit: http://localhost:8000/docs"
echo ""
echo "Happy coding! 🚀"
