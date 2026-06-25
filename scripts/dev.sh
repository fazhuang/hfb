#!/usr/bin/env bash
# ============================================================
# dev.sh — 启动开发环境
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting development environment...${NC}"

# Start infrastructure services
echo -e "${BLUE}[1/3] Starting Docker services...${NC}"
docker compose -f docker-compose.dev.yml up -d postgres neo4j --wait 2>/dev/null || true

# Start backend
echo -e "${BLUE}[2/3] Starting backend...${NC}"
source .venv/bin/activate 2>/dev/null || true
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --app-dir apps/backend &
BACKEND_PID=$!

# Start frontend
echo -e "${BLUE}[3/3] Starting frontend...${NC}"
pnpm --filter @hfb/frontend dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Development Environment Ready${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap SIGINT to cleanup
trap 'echo "Shutting down..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; wait; exit 0' INT TERM

# Wait for both
wait
