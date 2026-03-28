#!/bin/bash
# DiePre AI 优化推演启动脚本
# 用法: ./start.sh [cycles] [rounds]
#   默认: 2循环 × 5轮

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CYCLES=${1:-2}
ROUNDS=${2:-5}

echo "=========================================="
echo "  DiePre AI 优化推演引擎"
echo "  循环: $CYCLES | 每循环: $ROUNDS 轮"
echo "=========================================="

cd "$SCRIPT_DIR"
python3 diepre_optimization_engine.py --cycles "$CYCLES" --rounds "$ROUNDS"
