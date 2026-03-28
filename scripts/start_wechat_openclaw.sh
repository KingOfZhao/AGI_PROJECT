#!/bin/bash
# 微信 OpenClaw 中转方案启动脚本
# OpenClaw 负责微信协议(iLink session管理), Bridge 负责AI处理(7步链)
#
# 架构: 微信 ←→ OpenClaw(18789) ←→ Bridge(9801) ←→ ChainProcessor(Ollama+GLM)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
NODE22="/opt/homebrew/opt/node@22/bin"

mkdir -p "$LOG_DIR"

echo "=== 微信 OpenClaw 中转启动 ==="

# 1. 启动 Bridge (OpenAI-compatible API → 本地7步链)
BRIDGE_PID=$(pgrep -f 'openclaw_bridge.py' 2>/dev/null || true)
if [ -n "$BRIDGE_PID" ]; then
    echo "[Bridge] 已在运行 (PID $BRIDGE_PID)"
else
    echo "[Bridge] 启动中..."
    nohup python3 "$SCRIPT_DIR/openclaw_bridge.py" > "$LOG_DIR/openclaw_bridge.log" 2>&1 &
    sleep 2
    if curl -s http://127.0.0.1:9801/health | grep -q 'ok'; then
        echo "[Bridge] ✅ 启动成功 (http://127.0.0.1:9801)"
    else
        echo "[Bridge] ❌ 启动失败，查看 $LOG_DIR/openclaw_bridge.log"
        exit 1
    fi
fi

# 2. 启动 OpenClaw Gateway (微信中转)
OC_PID=$(pgrep -f 'openclaw.*gateway' 2>/dev/null || true)
if [ -n "$OC_PID" ]; then
    echo "[OpenClaw] 已在运行 (PID $OC_PID)"
else
    echo "[OpenClaw] 启动中..."
    PATH="$NODE22:$PATH" nohup openclaw gateway --port 18789 --verbose > "$LOG_DIR/openclaw_gateway.log" 2>&1 &
    sleep 5
    echo "[OpenClaw] ✅ Gateway 已启动 (ws://127.0.0.1:18789)"
fi

echo ""
echo "=== 服务状态 ==="
echo "  Bridge:   http://127.0.0.1:9801  (本地7步链)"
echo "  OpenClaw: ws://127.0.0.1:18789   (微信中转)"
echo ""
echo "=== 日志 ==="
echo "  Bridge:   $LOG_DIR/openclaw_bridge.log"
echo "  OpenClaw: $LOG_DIR/openclaw_gateway.log"
echo ""
echo "如需重新扫码: PATH=$NODE22:\$PATH openclaw channels login --channel openclaw-weixin"
echo "停止服务: kill \$(pgrep -f 'openclaw_bridge.py') \$(pgrep -f 'openclaw.*gateway')"
