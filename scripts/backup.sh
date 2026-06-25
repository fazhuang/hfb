#!/usr/bin/env bash
# ============================================================
# backup.sh — Backup PostgreSQL + Neo4j + config
# ============================================================
# Usage:
#   ./scripts/backup.sh                    # Full backup
#   ./scripts/backup.sh postgres           # PostgreSQL only
#   ./scripts/backup.sh neo4j              # Neo4j only
#   ./scripts/backup.sh config             # Config files only
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

log()  { echo -e "${BLUE}[BACKUP]${NC} $1"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Config ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_BASE="${PROJECT_DIR}/backups/${TIMESTAMP}"

# --- Load .env if available ---
ENV_FILE="${PROJECT_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_BASE="${BACKUP_DIR}/${TIMESTAMP}"

mkdir -p "$BACKUP_BASE"

SCOPE="${1:-all}"

echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  HFB Platform — Backup${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""
log "Timestamp: $TIMESTAMP"
log "Backup dir: $BACKUP_BASE"
echo ""

# --- PostgreSQL backup ---
backup_postgres() {
    log "Backing up PostgreSQL (${POSTGRES_DB:-hfb})..."

    local pg_host="${POSTGRES_HOST:-localhost}"
    local pg_port="${POSTGRES_PORT:-5432}"
    local pg_user="${POSTGRES_USER:-hfb}"
    local pg_db="${POSTGRES_DB:-hfb}"

    # Check if running in Docker
    local container="hfb-postgres"
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        docker exec "$container" pg_dump -U "$pg_user" -d "$pg_db" \
            --clean --if-exists --no-owner --no-privileges \
            > "$BACKUP_BASE/postgres_${pg_db}_${TIMESTAMP}.sql"
        ok "PostgreSQL dump via Docker ($container)"
    elif command -v pg_dump &>/dev/null; then
        PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
            -h "$pg_host" -p "$pg_port" -U "$pg_user" -d "$pg_db" \
            --clean --if-exists --no-owner --no-privileges \
            > "$BACKUP_BASE/postgres_${pg_db}_${TIMESTAMP}.sql"
        ok "PostgreSQL dump via local pg_dump"
    else
        warn "pg_dump not found and Docker container not running — skipping PostgreSQL"
        return 1
    fi

    # Compress
    gzip -f "$BACKUP_BASE/postgres_${pg_db}_${TIMESTAMP}.sql"
    ok "Compressed: postgres_${pg_db}_${TIMESTAMP}.sql.gz"
}

# --- Neo4j backup ---
backup_neo4j() {
    log "Backing up Neo4j..."

    local container="hfb-neo4j"
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        docker exec "$container" neo4j-admin database dump neo4j \
            --to-path=/var/lib/neo4j/data/dumps/ 2>/dev/null || {
            warn "neo4j-admin dump not supported in this Neo4j version — skipping"
            return 1
        }
        docker cp "${container}:/var/lib/neo4j/data/dumps/." "$BACKUP_BASE/neo4j/" 2>/dev/null
        ok "Neo4j dump via Docker ($container)"
    else
        warn "Neo4j container not running — skipping"
        return 1
    fi
}

# --- Config backup ---
backup_config() {
    log "Backing up configuration files..."

    local config_files=(
        ".env"
        ".env.example"
        "docker-compose.dev.yml"
        "docker-compose.prod.yml"
        "pyproject.toml"
        "package.json"
        "pnpm-workspace.yaml"
    )

    for f in "${config_files[@]}"; do
        if [[ -f "${PROJECT_DIR}/${f}" ]]; then
            mkdir -p "$BACKUP_BASE/config"
            cp "${PROJECT_DIR}/${f}" "$BACKUP_BASE/config/"
            ok "Copied: $f"
        fi
    done
}

# --- Manifest ---
write_manifest() {
    cat > "$BACKUP_BASE/manifest.json" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "scope": "$SCOPE",
  "backup_dir": "$BACKUP_BASE",
  "files": $(find "$BACKUP_BASE" -type f -not -name manifest.json -exec basename {} \; | jq -R -s -c 'split("\n")[:-1]')
}
EOF
    ok "Manifest written: manifest.json"
}

# --- Execute ---
case "$SCOPE" in
    all)
        backup_postgres || true
        backup_neo4j || true
        backup_config || true
        ;;
    postgres)
        backup_postgres
        ;;
    neo4j)
        backup_neo4j
        ;;
    config)
        backup_config
        ;;
    *)
        err "Unknown scope: $SCOPE (valid: all, postgres, neo4j, config)"
        ;;
esac

write_manifest

# --- Cleanup old backups ---
log "Cleaning up backups older than ${BACKUP_RETENTION_DAYS} days..."
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime "+${BACKUP_RETENTION_DAYS}" \
    -not -path "$BACKUP_DIR" -exec rm -rf {} \; 2>/dev/null || true
ok "Old backup cleanup complete"

# --- Summary ---
echo ""
echo -e "${GREEN}${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}  Backup Complete${NC}"
echo -e "${GREEN}${BOLD}============================================${NC}"
echo ""
echo "  Location: $BACKUP_BASE"
echo "  Size:     $(du -sh "$BACKUP_BASE" | cut -f1)"
echo "  Files:"
find "$BACKUP_BASE" -type f -not -name manifest.json | while read -r f; do
    echo "    - $(basename "$f") ($(du -h "$f" | cut -f1))"
done
echo ""
