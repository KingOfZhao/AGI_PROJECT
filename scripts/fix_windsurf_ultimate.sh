#!/bin/bash
# Windsurf 内容审核拦截终极修复脚本
# 适用于: Permission denied: Your request was blocked by our content policy
# 根因: Windsurf Memories 中缓存了触发内容策略的文本 (身份覆盖指令/自主Agent语言)
# 修复: 清除所有持久化的对话上下文和 Memories 存储

set -e

echo "🔧 开始彻底清理 Windsurf 内容审核问题..."
echo ""

# 1. 删除历史记录（包含 API key）
echo "1️⃣ 清理对话历史..."
rm -rf ~/Library/Application\ Support/Windsurf/User/History
rm -rf ~/Library/Application\ Support/Windsurf.backup.*/User/History
echo "   ✅ 历史记录已清理"

# 2. 清理状态数据库和 Memories（核心修复点）
echo "2️⃣ 清理状态数据库和 Windsurf Memories..."
rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb*
rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json
# Windsurf/Codeium 的 Memories 持久化存储
rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/codeium.codeium*
rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/windsurf*
# 清理所有 globalStorage（保险起见全清）
find ~/Library/Application\ Support/Windsurf/User/globalStorage \
     -name "*.db" -o -name "*.db-shm" -o -name "*.db-wal" \
     -o -name "*.json" 2>/dev/null | xargs rm -f 2>/dev/null || true
echo "   ✅ 状态数据库和 Memories 已清理"

# 3. 清理所有缓存
echo "3️⃣ 清理缓存..."
rm -rf ~/Library/Application\ Support/Windsurf/Cached*
rm -rf ~/Library/Application\ Support/Windsurf/Code\ Cache
rm -rf ~/Library/Application\ Support/Windsurf/GPUCache
rm -rf ~/Library/Application\ Support/Windsurf/DawnGraphiteCache
rm -rf ~/Library/Application\ Support/Windsurf/DawnWebGPUCache
echo "   ✅ 缓存已清理"

# 4. 清理工作区存储
echo "4️⃣ 清理工作区存储..."
find ~/Library/Application\ Support/Windsurf/User/workspaceStorage \
     -name "*.db" -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf/User/workspaceStorage \
     -name "*.db-shm" -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf/User/workspaceStorage \
     -name "*.db-wal" -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf/User/workspaceStorage \
     -name "*.json" -delete 2>/dev/null || true
echo "   ✅ 工作区存储已清理"

# 4.5. 清理对话历史
echo "4️⃣.5 清理对话历史..."
rm -rf ~/Library/Application\ Support/Windsurf/User/History
find ~/Library/Application\ Support/Windsurf \
     -name "*conversation*" -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf \
     -name "*history*" -type f -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf \
     -name "*memory*" -type f -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf \
     -name "*cascade*" -type f -delete 2>/dev/null || true
echo "   ✅ 对话历史已清理"

# 5. 检查项目代码中的硬编码 API key
echo "5️⃣ 检查项目代码..."
KEY_PREFIX=$(echo "$ZHIPU_API_KEY" | cut -c1-16 2>/dev/null)
if [ -n "$KEY_PREFIX" ]; then
    HARDCODED=$(grep -r "$KEY_PREFIX" ~/Desktop/AGI_PROJECT/ --include="*.py" --include="*.json" 2>/dev/null | grep -v ".git" | wc -l)
    if [ "$HARDCODED" -gt 0 ]; then
        echo "   ⚠️  发现 $HARDCODED 处硬编码 API key"
        echo "   运行以下命令查看详情："
        echo "   grep -r \"$KEY_PREFIX\" ~/Desktop/AGI_PROJECT/ --include=\"*.py\" --include=\"*.json\""
    else
        echo "   ✅ 项目代码干净"
    fi
else
    echo "   ⚠️  ZHIPU_API_KEY 未设置，跳过检查"
fi

# 6. 确保环境变量已设置
echo "6️⃣ 检查环境变量..."
if [ -z "$ZHIPU_API_KEY" ]; then
    echo "   ⚠️  ZHIPU_API_KEY 未设置"
    echo "   请手动将以下行添加到 ~/.zshrc："
    echo '   export ZHIPU_API_KEY="your_zhipu_api_key_here"'
    echo "   然后运行: source ~/.zshrc"
else
    echo "   ✅ 环境变量已存在"
fi

echo ""
echo "✅ 清理完成！"
echo ""
echo "=== 必须执行的步骤 ==="
echo "1. 完全退出 Windsurf:  killall Windsurf  或  Cmd+Q"
echo "2. 等待 3 秒后重新打开 Windsurf"
echo "3. 开启新对话（不要恢复旧对话）"
echo ""
echo "=== 已修复的根因 ==="
echo "  ✅ SOUL.md   - 移除身份覆盖语言"
echo "  ✅ AGENTS.md - 移除绕过安全确认的指令"
echo "  ✅ .windsurf/rules/project-context.md - 建立正确项目上下文"
echo "  ✅ Windsurf Memories / globalStorage 完整清除"
echo ""
echo "=== 如果仍然报错 ==="
echo "核选项 - 重置整个 Windsurf 存储（会丢失所有扩展设置）:"
echo "  mv ~/Library/Application\ Support/Windsurf \\"
echo "     ~/Library/Application\ Support/Windsurf.old.\$(date +%s)"
echo ""
echo "=== 预防措施 ==="
echo "  • 避免在 Prompt 中使用 '不是chatbot/越狱/绕过限制' 等语言"
echo "  • 避免让 AI 读取 SOUL.md/AGENTS.md 全文内容"
echo "  • .windsurf/rules/ 文件夹中的内容会自动注入每次对话，保持内容安全"
