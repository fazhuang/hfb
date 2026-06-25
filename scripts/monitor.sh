#!/usr/bin/env bash
# ============================================================
# monitor.sh — HFB Platform health check & monitoring
# ============================================================
# Usage:
#   ./scripts/monitor.sh                  # One-shot health check
#   ./scripts/monitor.sh --watch [sec]    # Continuous watch (default: 30s)
#   ./scripts/monitor.sh --json           # JSON output (for automation)
#   ./scripts/monitor.sh --prometheus     # Prometheus metrics format
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# --- Config ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env
ENV_FILE="${PROJECT_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a; source "$ENV_FILE"; set +a
fi

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-hfb}"
POSTGRES_USER="${POSTGRES_USER:-hfb}"
ELASTICSEARCH_PORT="${ELASTICSEARCH_PORT:-9200}"
MINIO_PORT="${MINIO_PORT:-9000}"
REDIS_PORT="${REDIS_PORT:-6379}"
NEO4J_BOLT_PORT="${NEO4J_BOLT_PORT:-7687}"

MODE="${1:-}"

# --- Helpers ---
status_icon() {
    if [[ "$1" == "ok" ]]; then
        echo -e "${GREEN}●${NC}"
    elif [[ "$1" == "degraded" ]]; then
        echo -e "${YELLOW}◐${NC}"
    else
        echo -e "${RED}○${NC}"
    fi
}

# --- Check functions ---
check_http() {
    local url="$1"
    local timeout="${2:-5}"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$timeout" --max-time "$timeout" "$url" 2>/dev/null) || true
    if [[ "$status" =~ ^2[0-9][0-9]$ ]] || [[ "$status" == "200" ]]; then
        echo "ok"
    elif [[ -n "$status" ]]; then
        echo "degraded"
    else
        echo "down"
    fi
}

check_tcp() {
    local host="$1"
    local port="$2"
    local timeout="${3:-3}"
    if timeout "$timeout" bash -c "echo >/dev/tcp/${host}/${port}" 2>/dev/null; then
        echo "ok"
    else
        echo "down"
    fi
}

check_docker() {
    local container="$1"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
        echo "ok"
    else
        echo "down"
    fi
}

# --- Full health check ---
run_check() {
    local output_format="${1:-text}"

    local backend_status=$(check_http "http://localhost:${BACKEND_PORT}/health" 5)
    local backend_ready=$(check_http "http://localhost:${BACKEND_PORT}/ready" 5)
    local frontend_status=$(check_http "http://localhost:${FRONTEND_PORT}" 3)
    local postgres_status=$(check_tcp "localhost" "$POSTGRES_PORT" 3)
    local redis_status=$(check_tcp "localhost" "$REDIS_PORT" 3)
    local elasticsearch_status=$(check_http "http://localhost:${ELASTICSEARCH_PORT}/_cluster/health" 5)
    local minio_status=$(check_http "http://localhost:${MINIO_PORT}/minio/health/live" 3)

    # Overall status
    local overall="ok"
    for s in "$backend_status" "$postgres_status" "$redis_status"; do
        [[ "$s" == "down" ]] && overall="down"
    done
    for s in "$elasticsearch_status" "$minio_status"; do
        [[ "$s" == "down" ]] && [[ "$overall" != "down" ]] && overall="degraded"
    done

    case "$output_format" in
        json)
            cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "overall": "$overall",
  "services": {
    "backend":    {"status": "$backend_status",    "health": "$backend_ready"},
    "frontend":   {"status": "$frontend_status"},
    "postgres":   {"status": "$postgres_status"},
    "redis":      {"status": "$redis_status"},
    "elasticsearch": {"status": "$elasticsearch_status"},
    "minio":      {"status": "$minio_status"}
  }
}
EOF
            ;;
        prometheus)
            cat <<EOF
# HELP hfb_service_status Service health status (1=healthy 0=unhealthy)
# TYPE hfb_service_status gauge
hfb_service_status{service="backend"} $([[ "$backend_status" == "ok" ]] && echo 1 || echo 0)
hfb_service_status{service="frontend"} $([[ "$frontend_status" == "ok" ]] && echo 1 || echo 0)
hfb_service_status{service="postgres"} $([[ "$postgres_status" == "ok" ]] && echo 1 || echo 0)
hfb_service_status{service="redis"} $([[ "$redis_status" == "ok" ]] && echo 1 || echo 0)
hfb_service_status{service="elasticsearch"} $([[ "$elasticsearch_status" == "ok" ]] && echo 1 || echo 0)
hfb_service_status{service="minio"} $([[ "$minio_status" == "ok" ]] && echo 1 || echo 0)
# HELP hfb_overall_status Overall platform health
# TYPE hfb_overall_status gauge
hfb_overall_status $([[ "$overall" == "ok" ]] && echo 1 || echo 0)
EOF
            ;;
        *)
            echo ""
            echo -e "${BOLD}  $(status_icon "$overall")  HFB Platform Status${NC}"
            echo "  ─────────────────────────────────"
            printf "  %-20s %s\n" "Backend"        "$(status_icon "$backend_status") $backend_status"
            printf "  %-20s %s\n" "  └─ Health"     "$(status_icon "$backend_ready") $backend_ready"
            printf "  %-20s %s\n" "Frontend"       "$(status_icon "$frontend_status") $frontend_status"
            printf "  %-20s %s\n" "PostgreSQL"     "$(status_icon "$postgres_status") $postgres_status"
            printf "  %-20s %s\n" "Redis"          "$(status_icon "$redis_status") $redis_status"
            printf "  %-20s %s\n" "Elasticsearch"  "$(status_icon "$elasticsearch_status") $elasticsearch_status"
            printf "  %-20s %s\n" "MinIO"          "$(status_icon "$minio_status") $minio_status"
            echo ""

            # Docker containers
            echo -e "  ${BOLD}Docker Containers:${NC}"
            for c in hfb-backend hfb-backend-dev hfb-frontend hfb-frontend-dev hfb-postgres hfb-postgres-dev hfb-redis-dev hfb-elasticsearch hfb-elasticsearch-dev hfb-minio hfb-minio-dev hfb-neo4j; do
                local d_status=$(check_docker "$c")
                if [[ "$d_status" == "ok" ]]; then
                    printf "  %-30s %s running\n" "$c" "$(status_icon ok)"
                fi
            done
            echo ""

            # Disk usage of volumes
            echo -e "  ${BOLD}Docker Volumes:${NC}"
            docker system df -v 2>/dev/null | grep -E 'hfb|postgres|redis|minio|es|neo4j' | while read -r line; do
                echo "  $line"
            done || echo "  (Docker not available)"

            echo ""
            echo -e "  ${BOLD}Endpoints:${NC}"
            echo "  Backend API:     http://localhost:${BACKEND_PORT}"
            echo "  API Docs:        http://localhost:${BACKEND_PORT}/docs"
            echo "  Frontend:        http://localhost:${FRONTEND_PORT}"
            echo "  MinIO Console:   http://localhost:${MINIO_CONSOLE_PORT:-9001}"
            echo ""
            ;;
    esac
}

# --- Main ---
case "$MODE" in
    --json|-j)
        run_check json
        ;;
    --prometheus|-p)
        run_check prometheus
        ;;
    --watch|-w)
        INTERVAL="${2:-30}"
        echo -e "${CYAN}Watching HFB platform health (every ${INTERVAL}s, Ctrl+C to stop)...${NC}"
        while true; do
            clear 2>/dev/null || true
            run_check text
            echo -e "${CYAN}Next check in ${INTERVAL}s...  [$(date '+%H:%M:%S')]${NC}"
            sleep "$INTERVAL"
        done
        ;;
    *)
        run_check text
        ;;
esac
