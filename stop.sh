#!/bin/bash
# AGI v13.3 — 停止服务脚本
PORT=5002

if lsof -ti :$PORT >/dev/null 2>&1; then
    echo "🛑 正在停止 AGI v13.3 服务 (端口 $PORT)..."
    lsof -ti :$PORT | xargs kill -9 2>/dev/null
    sleep 1
    echo "✅ 服务已停止"
else
    echo "ℹ️  端口 $PORT 上没有运行中的服务"
fi
