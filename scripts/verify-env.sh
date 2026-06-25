#!/usr/bin/env bash
# ============================================================
# verify-env.sh — Validate .env against .env.example
# ============================================================
# Usage: ./scripts/verify-env.sh [--strict]
#   --strict  Also require non-empty values for all vars
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

STRICT_MODE=false
[[ "${1:-}" == "--strict" ]] && STRICT_MODE=true

HAS_ERROR=0
HAS_WARN=0

# --- Helpers ---
pass() { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; HAS_WARN=1; }
fail() { echo -e "  ${RED}✗${NC} $1"; HAS_ERROR=1; }

# --- Find files ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
ENV_FILE="$PROJECT_DIR/.env"

echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  .env Validation${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""

# --- Check files exist ---
if [[ ! -f "$ENV_EXAMPLE" ]]; then
    fail ".env.example not found at $ENV_EXAMPLE"
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    fail ".env not found at $ENV_FILE"
    echo ""
    echo -e "${YELLOW}Run: cp .env.example .env${NC}"
    exit 1
fi

echo -e "${BLUE}Config files:${NC}"
echo "  .env.example : $ENV_EXAMPLE"
echo "  .env         : $ENV_FILE"
echo ""

# --- Extract variable names from .env.example ---
echo -e "${BOLD}Checking required variables...${NC}"

# Parse .env.example for variable names (handle VAR=value and VAR=)
declare -a VARS=()
while IFS='=' read -r key _; do
    # Skip comments and blank lines
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# || "$key" =~ ^[[:space:]]*$ ]] && continue
    # Trim whitespace
    key=$(echo "$key" | xargs)
    VARS+=("$key")
done < "$ENV_EXAMPLE"

TOTAL=0
MISSING=0
EMPTY=0
OK=0

for var in "${VARS[@]}"; do
    TOTAL=$((TOTAL + 1))

    # Check if variable exists in .env
    if ! grep -qE "^[[:space:]]*${var}=" "$ENV_FILE"; then
        fail "Missing: $var"
        MISSING=$((MISSING + 1))
        continue
    fi

    # Get the value
    value=$(grep -E "^[[:space:]]*${var}=" "$ENV_FILE" | head -1 | sed 's/^[^=]*=//' | xargs)

    if [[ -z "$value" ]]; then
        if $STRICT_MODE; then
            warn "Empty:   $var (required in strict mode)"
            EMPTY=$((EMPTY + 1))
        else
            pass "Present: $var (empty)"
            OK=$((OK + 1))
        fi
    else
        # Check for default/placeholder values
        if [[ "$value" =~ ^change-me ]] || [[ "$value" == "changeme" ]]; then
            warn "Default: $var = (still has placeholder value)"
            OK=$((OK + 1))
        else
            pass "Present: $var = ${value:0:30}$([[ ${#value} -gt 30 ]] && echo '...')"
            OK=$((OK + 1))
        fi
    fi
done

# --- Summary ---
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  Validation Summary${NC}"
echo -e "${BOLD}============================================${NC}"
echo -e "  Total variables:   ${TOTAL}"
echo -e "  ${GREEN}OK:                 ${OK}${NC}"
echo -e "  ${YELLOW}Warnings:           ${HAS_WARN}${NC}"
echo -e "  ${RED}Missing:            ${MISSING}${NC}"
echo -e "  ${RED}Empty (strict):     ${EMPTY}${NC}"
echo ""

if [[ $MISSING -gt 0 ]]; then
    echo -e "${RED}✗ Some variables are missing from .env — add them before proceeding.${NC}"
    echo -e "  Compare: diff <(grep -o '^[A-Z_]*' .env.example | sort) <(grep -o '^[A-Z_]*' .env | sort)"
    exit 1
fi

if [[ $HAS_ERROR -gt 0 ]]; then
    echo -e "${RED}✗ Validation failed with errors.${NC}"
    exit 1
fi

if [[ $HAS_WARN -gt 0 ]]; then
    echo -e "${YELLOW}⚠ Validation passed with warnings. Review before deploying to production.${NC}"
    exit 0
fi

echo -e "${GREEN}✓ All variables present and configured.${NC}"
