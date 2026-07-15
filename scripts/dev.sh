#!/usr/bin/env bash
# ============================================================
# dev.sh — 启动开发环境 (PostgreSQL 模式)
#
# 前置条件:
#   Docker 已运行
#   .env 已配置（从 .env.example 复制并填写）
#
# 启动命令:
#   bash scripts/dev.sh
#
# 服务端口:
#   Backend:    http://127.0.0.1:8000
#   API Docs:   http://127.0.0.1:8000/docs
#   Frontend:   http://127.0.0.1:5173
#   PostgreSQL: localhost:5432
#   Redis:      localhost:6379
#   Elasticsearch: localhost:9200
#   MinIO:      localhost:9000 (console: 9001)
#
# 健康检查:
#   curl -i http://127.0.0.1:8000/health
#   curl -i http://127.0.0.1:8000/ready
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting development environment...${NC}"

# Start all infrastructure services
echo -e "${BLUE}[1/3] Starting Docker services (PostgreSQL, Redis, Elasticsearch, MinIO)...${NC}"
docker compose -f docker-compose.dev.yml up -d postgres redis elasticsearch minio --wait 2>/dev/null

# Verify Docker services are healthy
echo -e "${YELLOW}Verifying Docker services...${NC}"
for svc in hfb-postgres-dev hfb-redis-dev hfb-elasticsearch-dev hfb-minio-dev; do
  status=$(docker inspect -f '{{.State.Health.Status}}' "$svc" 2>/dev/null || echo "missing")
  echo "  $svc: $status"
  if [ "$status" != "healthy" ]; then
    echo -e "${YELLOW}  ⚠  $svc is not healthy yet, waiting...${NC}"
    sleep 2
  fi
done

# Start backend
echo -e "${BLUE}[2/3] Starting backend (PostgreSQL mode)...${NC}"
source .venv/bin/activate 2>/dev/null || true
uvicorn main:app --host 127.0.0.1 --port 8000 --reload --app-dir apps/backend &
BACKEND_PID=$!

# Wait for backend readiness
echo -e "${YELLOW}Waiting for backend...${NC}"
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:8000/ready > /dev/null 2>&1; then
    echo -e "${GREEN}  Backend ready (all services healthy)${NC}"
    break
  fi
  if [ $i -eq 30 ]; then
    echo -e "${YELLOW}  ⚠  Backend not ready after 30s, continuing anyway${NC}"
  fi
  sleep 1
done

# Start frontend
echo -e "${BLUE}[3/3] Starting frontend...${NC}"
pnpm --filter @hfb/frontend dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Development Environment Ready${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  Backend:  http://127.0.0.1:8000"
echo "  API Docs: http://127.0.0.1:8000/docs"
echo "  Frontend: http://127.0.0.1:5173"
echo ""
echo "  Health check:  curl -i http://127.0.0.1:8000/health"
echo "  Readiness:     curl -i http://127.0.0.1:8000/ready"
echo ""

# Trap SIGINT to cleanup
trap 'echo "Shutting down..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; wait; exit 0' INT TERM

# Wait for both
wait
