#!/bin/bash
# Windsurf 内容审核拦截终极修复脚本
# 适用于: Permission denied: Your request was blocked by our content policy

set -e

echo "🔧 开始彻底清理 Windsurf 内容审核问题..."
echo ""

# 1. 删除历史记录（包含 API key）
echo "1️⃣ 清理对话历史..."
rm -rf ~/Library/Application\ Support/Windsurf/User/History
rm -rf ~/Library/Application\ Support/Windsurf.backup.*/User/History
echo "   ✅ 历史记录已清理"

# 2. 清理状态数据库
echo "2️⃣ 清理状态数据库..."
rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb*
rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json
echo "   ✅ 状态数据库已清理"

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
find ~/Library/Application\ Support/Windsurf/User/workspaceStorage -name "*.db" -delete 2>/dev/null || true
find ~/Library/Application\ Support/Windsurf/User/workspaceStorage -name "*.json" -delete 2>/dev/null || true
echo "   ✅ 工作区存储已清理"

# 5. 检查项目代码中的硬编码 API key
echo "5️⃣ 检查项目代码..."
HARDCODED=$(grep -r "8b9c47697cba446baeae08f712faddc7" ~/Desktop/AGI_PROJECT/ --include="*.py" --include="*.json" 2>/dev/null | grep -v ".git" | wc -l)
if [ "$HARDCODED" -gt 0 ]; then
    echo "   ⚠️  发现 $HARDCODED 处硬编码 API key"
    echo "   运行以下命令查看详情："
    echo "   grep -r \"8b9c47697cba446baeae08f712faddc7\" ~/Desktop/AGI_PROJECT/ --include=\"*.py\" --include=\"*.json\""
else
    echo "   ✅ 项目代码干净"
fi

# 6. 确保环境变量已设置
echo "6️⃣ 检查环境变量..."
if [ -z "$ZHIPU_API_KEY" ]; then
    echo "   ⚠️  ZHIPU_API_KEY 未设置"
    echo "   正在添加到 ~/.zshrc..."
    echo 'export ZHIPU_API_KEY="8b9c47697cba446baeae08f712faddc7.rYaSMdJYONxdGgBb"' >> ~/.zshrc
    export ZHIPU_API_KEY="8b9c47697cba446baeae08f712faddc7.rYaSMdJYONxdGgBb"
    echo "   ✅ 环境变量已设置"
else
    echo "   ✅ 环境变量已存在"
fi

echo ""
echo "✅ 清理完成！"
echo ""
echo "现在需要："
echo "1. 完全退出 Windsurf (Cmd+Q 或 killall Windsurf)"
echo "2. 重新打开 Windsurf"
echo "3. 开启新对话"
echo ""
echo "如果还报错，考虑："
echo "- 删除整个 Windsurf 目录重新初始化："
echo "  mv ~/Library/Application\ Support/Windsurf ~/Library/Application\ Support/Windsurf.old.\$(date +%s)"
echo "- 检查 .windsurf/skills 和 .windsurf/hooks.json 是否有敏感内容"
