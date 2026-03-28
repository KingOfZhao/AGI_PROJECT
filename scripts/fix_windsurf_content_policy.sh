#!/bin/bash
# Windsurf 内容审核拦截修复脚本
# 用途：清理 Windsurf 缓存、状态、对话历史

set -e

echo "🧹 清理 Windsurf 内容审核缓存..."

# 1. 清理缓存
echo "1️⃣ 清理缓存..."
rm -rf ~/Library/Application\ Support/Windsurf/Cached*
rm -rf ~/Library/Application\ Support/Windsurf/Code\ Cache
rm -rf ~/Library/Application\ Support/Windsurf/GPUCache
rm -rf ~/Library/Application\ Support/Windsurf/DawnGraphiteCache
rm -rf ~/Library/Application\ Support/Windsurf/DawnWebGPUCache

# 2. 清理状态数据库
echo "2️⃣ 清理状态数据库..."
rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb*
rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json

# 3. 清理工作区存储
echo "3️⃣ 清理工作区存储..."
find ~/Library/Application\ Support/Windsurf/User/workspaceStorage -name "*.db" -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf/User/workspaceStorage -name "*.json" -delete 2>/dev/null || true

# 4. 清理对话历史
echo "4️⃣ 清理对话历史..."
find ~/Library/Application\ Support/Windsurf -name "*conversation*" -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf -name "*history*" -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf -name "*memory*" -delete 2>/dev/null || true

echo "✅ 清理完成！"
echo ""
echo "现在需要："
echo "1. 完全退出 Windsurf (Cmd+Q)"
echo "2. 重新打开 Windsurf"
echo "3. 开启新对话"
echo ""
echo "如果还报错，检查项目代码里是否还有硬编码的 API key："
echo "  grep -r \"\$ZHIPU_API_KEY\" ~/Desktop/AGI_PROJECT/ --include='*.py' --include='*.json'"
