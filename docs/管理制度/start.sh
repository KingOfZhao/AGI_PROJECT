#!/bin/bash
# ============================================================
# 治理层级推演引擎 v2.0 — 王朝循环制 启动脚本
# ============================================================
# 五阶段循环: 【推演】→【构建】→【反贼】→【分裂】→【一统】
#
# 用法:
#   ./start.sh                # 默认1循环×10轮 (有断点自动续推)
#   ./start.sh 3              # 3个王朝循环×10轮
#   ./start.sh 2 5            # 2个王朝循环×5轮
#   ./start.sh --fresh        # 清除一切, 全新推演
#   ./start.sh --fresh 2 10   # 清除一切, 2循环×10轮
#   ./start.sh --no-resume    # 忽略断点, 全新推演 (保留缓存)
# ============================================================

cd "$(dirname "$0")"

CYCLES=1
ROUNDS=10
EXTRA_ARGS=""

# 解析参数
if [ "$1" = "--fresh" ]; then
    echo "🗑️  清除搜索缓存、断点、旧体系..."
    rm -f .gov_search_cache.json
    rm -f .gov_checkpoint.json
    rm -f .gov_state_*.json
    rm -f "上一次层级体系.json"
    EXTRA_ARGS="--no-resume"
    CYCLES=${2:-1}
    ROUNDS=${3:-10}
elif [ "$1" = "--no-resume" ]; then
    EXTRA_ARGS="--no-resume"
    CYCLES=${2:-1}
    ROUNDS=${3:-10}
else
    CYCLES=${1:-1}
    ROUNDS=${2:-10}
fi

# 显示断点状态
if [ -f .gov_checkpoint.json ] && [ -z "$EXTRA_ARGS" ]; then
    echo "🔄 发现未完成的推演断点:"
    cat .gov_checkpoint.json | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"   Session: {d.get('session_id','?')}\")
print(f\"   王朝循环: {d.get('completed_cycle',0)+1}\")
print(f\"   轮次进度: {d.get('completed_round',0)}/{d.get('rounds_per_cycle','?')}\")
print(f\"   阶段进度: Phase {d.get('completed_phase',0)}/5\")
print(f\"   断点时间: {d.get('saved_at','?')[:19]}\")
" 2>/dev/null
    echo "   将自动从断点继续..."
    echo ""
fi

# 检测 Ollama 本地模型
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:14b}"
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Ollama 已连接, 使用本地模型: $OLLAMA_MODEL"
else
    echo "❌ Ollama 未运行! 请先启动: ollama serve"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  治理层级推演引擎 v2.1 — 本地模型 + 王朝循环制               ║"
echo "║  五阶段: 推演→构建→反贼→分裂→一统                            ║"
echo "║  模型: $OLLAMA_MODEL                                         ║"
echo "║  王朝循环: $CYCLES | 每循环: ${ROUNDS}轮 | 分裂阈值: 5反贼      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  皇帝陛下, 本地推演开始..."
echo ""

OLLAMA_MODEL="$OLLAMA_MODEL" python3 governance_reasoning_engine.py \
    --cycles "$CYCLES" \
    --rounds "$ROUNDS" \
    $EXTRA_ARGS
