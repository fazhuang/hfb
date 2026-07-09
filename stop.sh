#!/bin/bash
# 停止所有 HFB 进程
pkill -f 'uvicorn main:app' 2>/dev/null && echo "后端已停止" || echo "后端未运行"
pkill -f 'vite' 2>/dev/null && echo "前端已停止" || echo "前端未运行"
