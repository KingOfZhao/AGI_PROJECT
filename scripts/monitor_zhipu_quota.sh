#!/bin/bash
# OpenClaw 智谱 API 配额监控脚本

set -e

echo "=================================================="
echo "📊 OpenClaw 智谱 API 配额监控"
echo "=================================================="
echo ""

# 1. 检查本地 Token 配额
echo "1️⃣ 本地 Token 配额"
echo "--------------------------------------------------"
if [ -f ~/Desktop/AGI_PROJECT/data/zhipu_quota.json ]; then
    cat ~/Desktop/AGI_PROJECT/data/zhipu_quota.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
daily_used = data.get('daily_used_tokens', 0)
daily_limit = data.get('daily_limit_tokens', 0)
total_used = data.get('total_used_tokens', 0)
total_limit = data.get('total_limit_tokens', 0)
daily_pct = (daily_used / daily_limit * 100) if daily_limit > 0 else 0
total_pct = (total_used / total_limit * 100) if total_limit > 0 else 0

print(f'今日已用: {daily_used:,} / {daily_limit:,} tokens ({daily_pct:.2f}%)')
print(f'总已用:   {total_used:,} / {total_limit:,} tokens ({total_pct:.2f}%)')
print(f'剩余可用: {total_limit - total_used:,} tokens')
print(f'配额健康: {\"✅\" if total_pct < 70 else \"⚠️\" if total_pct < 90 else \"🔴\"}')
"
else
    echo "❌ 未找到 zhipu_quota.json"
fi
echo ""

# 2. 检查智谱账户余额
echo "2️⃣ 智谱账户余额"
echo "--------------------------------------------------"
if [ -n "$ZHIPU_API_KEY" ]; then
    BALANCE=$(curl -s "https://www.bigmodel.cn/api/biz/account/query-customer-account-report" \
        -H "Authorization: Bearer $ZHIPU_API_KEY" \
        -H "User-Agent: OpenClaw-Monitor/1.0" 2>/dev/null)

    echo "$BALANCE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        balance = data['data']['availableBalance']
        total_spent = data['data']['totalSpendAmount']
        print(f'可用余额: ¥{balance:.2f}')
        print(f'已消费:   ¥{total_spent:.2f}')
        print(f'账户状态: {\"✅ 正常\" if balance > 0 else \"🔴 余额不足\"}')
    else:
        print('❌ API 请求失败:', data.get('msg', 'Unknown error'))
except Exception as e:
    print('❌ 解析失败:', str(e))
" 2>/dev/null || echo "❌ 无法获取账户信息"
else
    echo "⚠️  ZHIPU_API_KEY 未设置"
fi
echo ""

# 3. 检查 Idle Growth Engine 状态
echo "3️⃣ 闲置推演引擎"
echo "--------------------------------------------------"
if [ -f ~/Desktop/AGI_PROJECT/scripts/idle_growth_engine.py ]; then
    python3 ~/Desktop/AGI_PROJECT/scripts/idle_growth_engine.py --status 2>&1 | grep -A 5 "闲置推演引擎状态"
else
    echo "❌ 未找到 idle_growth_engine.py"
fi
echo ""

# 4. 检查最近的 429 错误
echo "4️⃣ 最近速率限制错误"
echo "--------------------------------------------------"
if [ -d ~/Desktop/AGI_PROJECT/logs ]; then
    ERRORS=$(grep -r "429\|rate.*limit" ~/Desktop/AGI_PROJECT/logs/ 2>/dev/null | tail -5)
    if [ -n "$ERRORS" ]; then
        echo "$ERRORS" | head -5
        echo ""
        echo "⚠️  检测到速率限制错误，建议："
        echo "   1. 检查账户余额是否充足"
        echo "   2. 降低 Idle Growth Engine 频率"
        echo "   3. 等待 1 小时后重试"
    else
        echo "✅ 无近期速率限制错误"
    fi
else
    echo "❌ logs 目录不存在"
fi
echo ""

# 5. 建议
echo "=================================================="
echo "💡 建议"
echo "=================================================="
BALANCE=$(curl -s "https://www.bigmodel.cn/api/biz/account/query-customer-account-report" \
    -H "Authorization: Bearer $ZHIPU_API_KEY" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['availableBalance'])" 2>/dev/null || echo "0")

if [ "$(echo "$BALANCE <= 0" | bc)" -eq 1 ]; then
    echo "🔴 账户余额不足，请立即充值:"
    echo "   https://open.bigmodel.cn/"
else
    echo "✅ 账户余额充足 (¥$BALANCE)"
fi
echo ""
echo "查看完整诊断报告:"
echo "  cat ~/Desktop/AGI_PROJECT/data/rate_limit_diagnosis.md"
