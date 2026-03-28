#!/bin/bash
# OpenClaw 自我强化训练启动脚本
# 用法: ./start_self_reinforce.sh [phase] [epochs] [tasks]
#   phase: warmup | intermediate | advanced | mixed (默认 warmup)
#   epochs: 每任务轮数 (默认 5)
#   tasks: 最大任务数 (默认 3)

cd "$(dirname "$0")/.."

PHASE=${1:-warmup}
EPOCHS=${2:-5}
TASKS=${3:-3}

echo "🦞 OpenClaw 自我强化训练"
echo "========================"
echo "阶段: $PHASE"
echo "轮数: $EPOCHS"
echo "任务: $TASKS"
echo ""

# 检查 API Key
if [ -z "$ZHIPU_API_KEY" ] && [ -f .env ]; then
    export $(grep -E '^ZHIPU_API_KEY=' .env | xargs)
fi

if [ -z "$ZHIPU_API_KEY" ]; then
    echo "⚠️  请设置 ZHIPU_API_KEY 环境变量或在 .env 中配置"
    exit 1
fi

# 运行训练
python3 scripts/openclaw_self_reinforce.py \
    --phase "$PHASE" \
    --epochs "$EPOCHS" \
    --tasks "$TASKS"
