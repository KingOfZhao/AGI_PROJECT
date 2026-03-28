# OpenClaw 自我强化训练指南

## 概述

利用智谱 GLM API 持续强化 OpenClaw 代码能力，目标超越 Claude Opus 4.6。

## 训练策略

| 阶段 | 任务类型 | 难度 | 模型 |
|------|---------|------|------|
| warmup (前10轮) | HumanEval / LeetCode Hard | easy~hard | GLM-5-Turbo |
| intermediate | GitHub Issue / SWE-bench | expert | GLM-5-Turbo |
| advanced | 系统级挑战 | master | GLM-5-Turbo + GLM-5验证 |
| synthetic | 自生成合成难题 | 动态 | 混合 |

## 快速开始

```bash
# 1. 确保配置了 API Key
export ZHIPU_API_KEY="your_key"
# 或在 .env 中配置

# 2. 热身训练 (推荐首次使用)
./scripts/start_self_reinforce.sh warmup 5 3

# 3. 中级训练
./scripts/start_self_reinforce.sh intermediate 10 5

# 4. 高级训练
./scripts/start_self_reinforce.sh advanced 10 3

# 5. 交互模式 (自定义任务)
python3 scripts/openclaw_self_reinforce.py --interactive

# 6. 合成难题 (AI自生成)
python3 scripts/openclaw_self_reinforce.py --synthetic --epochs 10
```

## 核心功能

### 1. 额度守护
- 自动查询智谱额度 (5小时/周/月)
- 低于 5% 自动降级到 GLM-4.7
- 峰谷调度: 14:00-18:00 = 3x, 其他 = 2x

### 2. 代码评估
- 语法检查 (compile)
- 测试运行 (subprocess)
- 复杂度分析 (LOC/函数/类)

### 3. Skill 存储
- 自动保存最佳版本到 `workspace/skills/`
- 元数据记录 (任务ID/难度/轮数/测试结果)
- 支持增量进化 (基于历史最佳版本)

## 输出位置

| 类型 | 路径 |
|------|------|
| 训练日志 | `data/training_logs/session_*.json` |
| 生成Skill | `workspace/skills/reinforce_*.py` |
| 元数据 | `workspace/skills/reinforce_*.meta.json` |

## 推荐训练计划

**每日 (50-100轮)**
```bash
# 早间热身 (谷时 2x)
./scripts/start_self_reinforce.sh warmup 5 5

# 下午深度 (避开 14:00-18:00 峰时)
./scripts/start_self_reinforce.sh intermediate 10 3
```

**每周复盘**
1. 查看 `data/training_logs/` 中的成功率趋势
2. 将最优 Skill 打包成 OpenClaw Agent
3. 与 Claude Opus 4.6 A/B 测试

## API 端点说明

⚠️ **重要**: 使用 Coding Plan Pro 必须用 Coding 端点:
- ✅ `https://open.bigmodel.cn/api/coding/paas/v4`
- ❌ `https://open.bigmodel.cn/api/paas/v4` (仅免费模型)

## 相关文件

- `scripts/openclaw_self_reinforce.py` — 主训练器
- `scripts/start_self_reinforce.sh` — 启动脚本
- `scripts/wechat_chain_processor.py` — 7步链处理器
- `api/env_config.py` — 环境配置
