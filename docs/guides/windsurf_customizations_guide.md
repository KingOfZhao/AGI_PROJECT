# Windsurf 永久指令位置和清理指南

## 问题根源
Windsurf 的对话历史里累积了大量 API key，触发内容审核拦截。

## 永久指令存储位置

### 1. 项目级别（最高优先级）
```
~/Desktop/AGI_PROJECT/.windsurf/
├── rules/           # ← 这里放规则文件（目前为空）
├── skills/          # ← 自定义技能
│   ├── local-chain/SKILL.md
│   └── skill-search/SKILL.md
├── workflows/       # ← 工作流
└── hooks.json       # ← 钩子配置
```

### 2. 用户级别
```
~/Library/Application Support/Windsurf/User/
├── settings.json              # 基础设置
├── globalStorage/
│   ├── state.vscdb           # SQLite 数据库（含对话历史）
│   └── storage.json          # 全局状态
└── workspaceStorage/
    └── {hash}/workspace.json  # 每个工作区的配置
```

### 3. Cascade Customizations（在 UI 中）
打开 Windsurf → Settings → Customizations:
- **Memories**: 记忆系统
- **Rules**: 永久规则
- **System Prompt**: 自定义系统提示
- **Project Instructions**: 项目指令

## 清理步骤

### 快速修复（推荐）
```bash
# 运行终极修复脚本
~/Desktop/AGI_PROJECT/scripts/fix_windsurf_ultimate.sh

# 重启 Windsurf
killall Windsurf && sleep 2 && open -a Windsurf
```

### 手动清理
1. **删除历史记录**
   ```bash
   rm -rf ~/Library/Application\ Support/Windsurf/User/History
   ```

2. **删除状态数据库**
   ```bash
   rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/state.vscdb*
   rm -rf ~/Library/Application\ Support/Windsurf/User/globalStorage/storage.json
   ```

3. **清理缓存**
   ```bash
   rm -rf ~/Library/Application\ Support/Windsurf/Cached*
   rm -rf ~/Library/Application\ Support/Windsurf/Code\ Cache
   rm -rf ~/Library/Application\ Support/Windsurf/GPUCache
   ```

4. **检查项目代码**
   ```bash
   grep -r "8b9c47697cba446baeae08f712faddc7" ~/Desktop/AGI_PROJECT/ --include="*.py"
   ```

5. **完全重置（最后手段）**
   ```bash
   # 备份并删除整个配置目录
   mv ~/Library/Application\ Support/Windsurf ~/Library/Application\ Support/Windsurf.old.$(date +%s)

   # 重新打开 Windsurf（会自动创建新配置）
   open -a Windsurf
   ```

## 永久指令最佳实践

### ✅ 推荐做法
- 使用环境变量：`os.environ.get("ZHIPU_API_KEY")`
- 把敏感信息放在 `~/.zshrc` 或 `.env` 文件
- `.env` 添加到 `.gitignore`
- 保持 customizations 简洁（只写编码相关）

### ❌ 避免
- 在代码里硬编码 API key
- 在 system prompt 里写敏感信息
- 在 Memories 里存储凭证
- 在对话中打印完整 API key

## 当前已修复的文件

1. ✅ `core/agi_v13_cognitive_lattice.py` - 5 处硬编码 → 环境变量
2. ✅ `api/tool_controller.py` - 1 处硬编码 → 环境变量
3. ✅ `~/.zshrc` - 已添加 `ZHIPU_API_KEY`
4. ✅ 历史记录已清理（169 处 API key）

## Windsurf Cascade 模式清理

在 Cascade 对话中：
1. 点击右上角 **Customizations** 图标
2. 找到以下部分并清理：
   - **Memories**: 删除所有包含 API key 的记忆
   - **Rules**: 删除敏感规则
   - **System Prompt**: 简化为纯编码相关
   - **Project Instructions**: 检查是否有敏感内容

## 验证清理成功

```bash
# 检查是否还有硬编码
grep -r "8b9c47697cba446baeae08f712faddc7" ~/Desktop/AGI_PROJECT/ --include="*.py" --include="*.json"

# 如果没有输出，说明已清理干净
```
