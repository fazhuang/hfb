#!/bin/bash
# HFB 本地启动脚本
# 用法: chmod +x start.sh && ./start.sh

set -e

cd /Users/likeming/Sites/hfb

# 停止旧进程
pkill -f 'uvicorn main:app' 2>/dev/null || true
pkill -f 'vite' 2>/dev/null || true
sleep 1

# 清理旧的 SQLite 数据库，确保干净启动
rm -f apps/backend/hfb-dev.db

# 启动后端 (SQLite)
echo "=== 启动后端 :8000 ==="
cd apps/backend
DATABASE_URL=sqlite+aiosqlite:///./hfb-dev.db uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../..

# 等待后端就绪
echo "等待后端..."
for i in $(seq 1 20); do
  if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "后端就绪"
    break
  fi
  sleep 1
done

# 启动前端
echo "=== 启动前端 :5173 ==="
cd apps/frontend
npx vite --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
cd ../..

sleep 2

echo ""
echo "=========================================="
echo "  前端: http://127.0.0.1:5173/v4/research"
echo "  API:  http://127.0.0.1:8000"
echo "  文档: http://127.0.0.1:8000/docs"
echo ""
echo "  注册账号后即可登录使用"
echo "  停止: kill $BACKEND_PID $FRONTEND_PID"
echo "=========================================="
