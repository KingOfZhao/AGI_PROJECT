#!/bin/bash
# OpenClaw 自主成长引擎启动脚本
# 用法:
#   ./start_autonomous_growth.sh daemon    # 守护进程模式
#   ./start_autonomous_growth.sh once      # 运行一次
#   ./start_autonomous_growth.sh batch 10  # 批量运行10个任务
#   ./start_autonomous_growth.sh status    # 查看状态
#   ./start_autonomous_growth.sh stop      # 停止守护进程

cd "$(dirname "$0")/.."

MODE=${1:-status}
PARAM=${2:-5}

# 检查 API Key
if [ -z "$ZHIPU_API_KEY" ] && [ -f .env ]; then
    export $(grep -E '^ZHIPU_API_KEY=' .env | xargs 2>/dev/null)
fi

case "$MODE" in
    daemon)
        echo "🚀 启动自主成长守护进程..."
        nohup python3 scripts/autonomous_growth.py --daemon > logs/autonomous_growth.log 2>&1 &
        echo "PID: $!"
        echo "日志: logs/autonomous_growth.log"
        ;;
    once)
        echo "🔄 运行一次成长循环..."
        python3 scripts/autonomous_growth.py --once
        ;;
    batch)
        echo "📦 批量运行 $PARAM 个任务..."
        python3 scripts/autonomous_growth.py --batch "$PARAM"
        ;;
    status)
        echo "📊 成长引擎状态:"
        python3 scripts/autonomous_growth.py --status
        ;;
    stop)
        if [ -f .autonomous_growth.pid ]; then
            PID=$(cat .autonomous_growth.pid)
            echo "🛑 停止守护进程 (PID: $PID)..."
            kill "$PID" 2>/dev/null
            rm -f .autonomous_growth.pid
            echo "✅ 已停止"
        else
            echo "⚠️ 未找到运行中的守护进程"
        fi
        ;;
    add)
        # 添加任务: ./start_autonomous_growth.sh add code_reinforce:实现分布式锁
        echo "📥 添加任务: $PARAM"
        python3 scripts/autonomous_growth.py --add "$PARAM"
        ;;
    *)
        echo "用法: $0 {daemon|once|batch N|status|stop|add type:title}"
        ;;
esac
