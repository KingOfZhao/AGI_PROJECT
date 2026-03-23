#!/bin/bash
# ============================================================
# AGI v13.3 Cognitive Lattice — 一键启动脚本
# 启动本地模型可视化前端 + 后端服务
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=5002
VENV_DIR="$PROJECT_DIR/venv"
PYTHON="$VENV_DIR/bin/python3"
SERVER="$PROJECT_DIR/api_server.py"

echo "============================================================"
echo "  AGI v13.3 Cognitive Lattice — 启动中..."
echo "  项目目录: $PROJECT_DIR"
echo "============================================================"

# 1. 检查虚拟环境
if [ ! -f "$PYTHON" ]; then
    echo "❌ 虚拟环境不存在: $VENV_DIR"
    echo "   请先运行: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
echo "✅ 虚拟环境: $VENV_DIR"

# 2. 检查 Ollama 是否运行
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Ollama 服务: 运行中"
else
    echo "⚠️  Ollama 服务未运行，尝试启动..."
    if command -v ollama &>/dev/null; then
        ollama serve &>/dev/null &
        sleep 3
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "✅ Ollama 服务: 已启动"
        else
            echo "⚠️  Ollama 启动失败，部分功能可能不可用（可视化界面仍可使用）"
        fi
    else
        echo "⚠️  未安装 Ollama，本地模型推理不可用（可切换为云端后端）"
    fi
fi

# 3. 检查端口占用
if lsof -ti :$PORT >/dev/null 2>&1; then
    echo "⚠️  端口 $PORT 被占用，正在释放..."
    lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
    sleep 1
    echo "✅ 端口 $PORT 已释放"
fi

# 4. 确保 data 目录存在
mkdir -p "$PROJECT_DIR/data"

# 5. 启动后端服务
echo ""
echo "🚀 启动 API Server..."
cd "$PROJECT_DIR"
"$PYTHON" "$SERVER" &
SERVER_PID=$!

# 6. 等待服务就绪
echo -n "   等待服务启动"
for i in $(seq 1 30); do
    if curl -s http://localhost:$PORT/api/stats >/dev/null 2>&1; then
        echo ""
        echo ""
        echo "============================================================"
        echo "  ✅ AGI v13.3 服务已启动！"
        echo ""
        echo "  🌐 可视化前端: http://localhost:$PORT"
        echo "  📡 API 端点:   http://localhost:$PORT/api/"
        echo "  🛑 停止服务:   ./stop.sh 或 kill $SERVER_PID"
        echo "============================================================"
        echo ""

        # 自动打开浏览器
        if command -v open &>/dev/null; then
            open "http://localhost:$PORT"
        elif command -v xdg-open &>/dev/null; then
            xdg-open "http://localhost:$PORT"
        fi
        
        # 前台等待，Ctrl+C 退出
        wait $SERVER_PID
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "❌ 服务启动超时，请检查日志"
kill $SERVER_PID 2>/dev/null
exit 1
