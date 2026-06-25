#!/usr/bin/env bash
# ============================================================
# restore.sh — Restore PostgreSQL + Neo4j from backups
# ============================================================
# Usage:
#   ./scripts/restore.sh <backup-dir>              # Restore all
#   ./scripts/restore.sh <backup-dir> postgres      # PostgreSQL only
#   ./scripts/restore.sh <backup-dir> neo4j         # Neo4j only
#   ./scripts/restore.sh --list                     # List available backups
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
BOLD='\033[1m'

log()  { echo -e "${BLUE}[RESTORE]${NC} $1"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Config ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if available
ENV_FILE="${PROJECT_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_DIR}/backups}"

# --- List backups ---
list_backups() {
    echo -e "${BOLD}Available backups:${NC}"
    echo ""
    if [[ ! -d "$BACKUP_DIR" ]] || [[ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]]; then
        echo "  No backups found in $BACKUP_DIR"
        exit 0
    fi
    for d in $(ls -1dt "$BACKUP_DIR"/*/ 2>/dev/null); do
        local ts=$(basename "$d")
        local size=$(du -sh "$d" 2>/dev/null | cut -f1)
        local files=$(find "$d" -type f -not -name manifest.json | wc -l | xargs)
        echo -e "  ${GREEN}${ts}${NC}  (${size}, ${files} files)"
        find "$d" -type f -not -name manifest.json | while read -r f; do
            echo "    - $(basename "$f")"
        done
    done
}

# --- Confirm ---
confirm() {
    local msg="${1:-Continue?}"
    echo ""
    echo -e "${YELLOW}${BOLD}⚠  WARNING: This will overwrite existing data!${NC}"
    echo ""
    read -r -p "$msg (type 'yes' to confirm): " reply
    if [[ "$reply" != "yes" ]]; then
        echo "Aborted."
        exit 0
    fi
}

# --- Handle --list ---
if [[ "${1:-}" == "--list" ]] || [[ "${1:-}" == "-l" ]]; then
    list_backups
    exit 0
fi

# --- Validate args ---
BACKUP_SRC="${1:-}"
SCOPE="${2:-all}"

if [[ -z "$BACKUP_SRC" ]]; then
    echo -e "${RED}Usage: $0 <backup-dir> [postgres|neo4j|all]${NC}"
    echo -e "${RED}       $0 --list${NC}"
    echo ""
    list_backups
    exit 1
fi

if [[ ! -d "$BACKUP_SRC" ]]; then
    err "Backup directory not found: $BACKUP_SRC"
fi

echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  HFB Platform — Restore${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""
log "Source: $BACKUP_SRC"
log "Scope:  $SCOPE"
echo ""

# --- PostgreSQL restore ---
restore_postgres() {
    local pg_host="${POSTGRES_HOST:-localhost}"
    local pg_port="${POSTGRES_PORT:-5432}"
    local pg_user="${POSTGRES_USER:-hfb}"
    local pg_db="${POSTGRES_DB:-hfb}"

    # Find the SQL dump (possibly gzipped)
    local sql_file
    sql_file=$(find "$BACKUP_SRC" -maxdepth 1 \( -name "postgres_*.sql" -o -name "postgres_*.sql.gz" \) 2>/dev/null | head -1)

    if [[ -z "$sql_file" ]]; then
        warn "No PostgreSQL dump found in $BACKUP_SRC — skipping"
        return 1
    fi

    confirm "Restore PostgreSQL from $(basename "$sql_file")?"

    log "Restoring PostgreSQL..."

    local container="hfb-postgres"
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        if [[ "$sql_file" == *.gz ]]; then
            gunzip -c "$sql_file" | docker exec -i "$container" psql -U "$pg_user" -d "$pg_db"
        else
            docker exec -i "$container" psql -U "$pg_user" -d "$pg_db" < "$sql_file"
        fi
        ok "PostgreSQL restored via Docker ($container)"
    elif command -v psql &>/dev/null; then
        if [[ "$sql_file" == *.gz ]]; then
            gunzip -c "$sql_file" | PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
                -h "$pg_host" -p "$pg_port" -U "$pg_user" -d "$pg_db"
        else
            PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
                -h "$pg_host" -p "$pg_port" -U "$pg_user" -d "$pg_db" < "$sql_file"
        fi
        ok "PostgreSQL restored via local psql"
    else
        err "psql not found and Docker container not running — cannot restore"
    fi
}

# --- Neo4j restore ---
restore_neo4j() {
    local container="hfb-neo4j"
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        warn "Neo4j container not running — skipping"
        return 1
    fi

    local dump_dir="$BACKUP_SRC/neo4j"
    if [[ ! -d "$dump_dir" ]]; then
        warn "No Neo4j dump found in $BACKUP_SRC — skipping"
        return 1
    fi

    confirm "Restore Neo4j from $dump_dir?"

    log "Restoring Neo4j..."

    # Stop Neo4j, copy dump, restore, restart
    docker stop "$container"
    docker cp "$dump_dir/." "${container}:/var/lib/neo4j/data/dumps/"
    docker start "$container"
    sleep 5
    docker exec "$container" neo4j-admin database restore neo4j \
        --from-path=/var/lib/neo4j/data/dumps/ --overwrite-destination 2>/dev/null || {
        warn "neo4j-admin restore failed — may need manual intervention"
        return 1
    }
    ok "Neo4j restored via Docker"
}

# --- Execute ---
case "$SCOPE" in
    all)
        restore_postgres || true
        restore_neo4j || true
        ;;
    postgres)
        restore_postgres
        ;;
    neo4j)
        restore_neo4j
        ;;
    *)
        err "Unknown scope: $SCOPE (valid: all, postgres, neo4j)"
        ;;
esac

echo ""
echo -e "${GREEN}${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}  Restore Complete${NC}"
echo -e "${GREEN}${BOLD}============================================${NC}"
echo ""
echo "  Verify:"
echo "    docker compose -f docker-compose.dev.yml restart backend"
echo "    curl http://localhost:8000/health"
echo ""
