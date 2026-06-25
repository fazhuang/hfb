#!/usr/bin/env bash
# ============================================================
# release.sh — Release workflow
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh 0.3.0
# ============================================================
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
    echo -e "${RED}Usage: $0 <version>${NC}"
    echo -e "Example: $0 0.3.0"
    exit 1
fi

# Validate version format
echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || {
    echo -e "${RED}Error: Version must be in format X.Y.Z (e.g. 0.3.0)${NC}"
    exit 1
}

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  Release v${VERSION}${NC}"
echo -e "${BLUE}============================================${NC}"

# Ensure working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: Working directory is not clean. Please commit or stash changes.${NC}"
    exit 1
fi

# Ensure on main
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo -e "${YELLOW}Warning: You are not on 'main' branch. Current: ${BRANCH}${NC}"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

# Run checks
echo -e "${BLUE}[1/5] Running lint checks...${NC}"
make lint || { echo -e "${RED}Lint failed. Aborting.${NC}"; exit 1; }

echo -e "${BLUE}[2/5] Running tests...${NC}"
make test || { echo -e "${RED}Tests failed. Aborting.${NC}"; exit 1; }

# Update version
echo -e "${BLUE}[3/5] Updating version to ${VERSION}...${NC}"
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import re
for f in ['pyproject.toml', 'package.json']:
    if __import__('os').path.exists(f):
        with open(f) as fh:
            content = fh.read()
        content = re.sub(r'version\s*=\s*\"[^\"]+\"', f'version = \"{VERSION}\"', content)
        with open(f, 'w') as fh:
            fh.write(content)
"
fi

# Update CHANGELOG
echo -e "${BLUE}[4/5] Updating CHANGELOG.md...${NC}"
DATE=$(date +%Y-%m-%d)
sed -i '' "1s/.*/# Changelog\n\n## [${VERSION}] - ${DATE}/" CHANGELOG.md 2>/dev/null || true

# Create tag
echo -e "${BLUE}[5/5] Creating git tag v${VERSION}...${NC}"
git add pyproject.toml package.json CHANGELOG.md
git commit -m "chore: release v${VERSION}" || true
git tag -a "v${VERSION}" -m "Release v${VERSION}"

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Release v${VERSION} prepared!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Next steps:"
echo "  git push origin main --follow-tags"
echo "  Create release on GitHub: https://github.com/huangfumi/hfb/releases/new?tag=v${VERSION}"
