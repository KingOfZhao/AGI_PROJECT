---
name: memory-hierarchy-system
version: 1.0.0
author: KingOfZhao
description: 记忆层级系统 Skill —— token/文件/参数三级记忆架构，热/温/冷分层+自动压缩+遗忘曲线
tags: [cognition, memory, hierarchy, retention, compression, forgetting-curve, agent-memory]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Memory Hierarchy System Skill

## 元数据

| 字段 | 值 |
|------|-----|
| 名称 | memory-hierarchy-system |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
self-evolution-cognition (文件即记忆)
        ⊗
arxiv: Memory in the Age of AI Agents (2512.13564)
        ⊗
arxiv: Beyond RAG (2602.02007)
        ⊗
learning-accelerator (间隔重复)
        ↓
memory-hierarchy-system
```

## 三级记忆架构

```
L1 — Token Memory (热记忆)
  位置: 当前对话上下文
  容量: ~200K tokens
  生命周期: 单次对话
  用途: 实时推理、工作记忆
  策略: 对话结束前必须提取关键信息到L2

L2 — File Memory (温记忆)
  位置: workspace文件 (MEMORY.md, memory/*.md, VERIFICATION_LOG.md)
  容量: 无限
  生命周期: 永久
  用途: 跨session记忆、知识积累
  策略: 每日心跳整理，定期压缩归档

L3 — Compressed Memory (冷记忆)
  位置: data/memory_index.json + data/knowledge_store.jsonl
  容量: 无限（压缩后）
  生命周期: 永久（只读归档）
  用途: 长期知识库、历史查询
  策略: L2中>30天未访问的内容自动压缩到L3
```

## 热/温/冷分层策略

```
写入路径: L1 → (对话结束) → L2 → (30天未访问) → L3
读取路径: 先查L1 → 未命中查L2 → 未命中查L3

自动压缩规则:
  - L2文件>100行 → 提取摘要存L3，原文标记[ARCHIVED]
  - L2文件>90天未访问 → 压缩到L3
  - L3内容按相关性索引，支持语义检索

遗忘曲线（选择性遗忘）:
  - 置信度100%的内容: 永不遗忘
  - 置信度<50%且>60天未验证: 压缩到L3
  - 标记[推测]且>30天未验证: 删除或降级
```

## 安装命令
```bash
clawhub install memory-hierarchy-system
```

## 调用方式
```python
from skills.memory_hierarchy_system import MemoryHierarchy

memory = MemoryHierarchy(workspace=".")

# 写入记忆
memory.remember(key="DiePre K因子", value="灰板0.35-0.40", level=2, confidence=0.95)

# 读取记忆（自动L1→L2→L3查找）
result = memory.recall(query="K因子")
print(result.value)        # "灰板0.35-0.40"
print(result.source_level) # L2
print(result.confidence)   # 0.95

# 记忆维护（心跳触发）
maintenance = memory.maintain()
print(maintenance.l1_to_l2)      # 本次L1→L2迁移数
print(maintenance.l2_to_l3)      # 本次压缩数
print(maintenance.forgotten)      # 本次遗忘数
print(maintenance.stats)          # 各层级容量统计
```

## 学术参考
1. [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) — 核心理论基础
2. [Beyond RAG for Agent Memory](https://arxiv.org/abs/2602.02007) — Decoupling+Aggregation
3. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046) — 记忆驱动自进化
