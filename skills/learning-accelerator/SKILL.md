---
name: learning-accelerator
version: 1.0.0
author: KingOfZhao
description: 学习加速器 Skill —— SOUL五律适配学习场景，费曼技巧×间隔重复×主动召回+学习记忆系统
tags: [cognition, learning, education, feynman-technique, spaced-repetition, knowledge-retention]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Learning Accelerator Skill

## 元数据

| 字段 | 值 |
|------|-----|
| 名称 | learning-accelerator |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
self-evolution-cognition (自进化=自学习)
        ⊗
human-ai-closed-loop (学习需要实践反馈)
        ⊗
ai-growth-engine (Growth Score=学习进度度量)
        ↓
learning-accelerator
```

## 核心方法

### 1. 费曼技巧 × 已知/未知

```
学习任何新知识时:
1. 学完后用"小学生能听懂的话"复述 → 暴露真正的[UNKNOWN]
2. 找到卡壳的地方 → 那就是知识缺口
3. 回去补缺口 → 重新费曼
4. 循环直到能流畅复述

SOUL映射: 费曼技巧 = 已知/未知分离的实践版
```

### 2. 间隔重复（Spaced Repetition）

```
记忆曲线: 1天 → 3天 → 7天 → 14天 → 30天 → 90天
每个知识点按曲线自动安排复习

Agent实现:
  learning_cards/
    {topic}/
      card_{id}.json
        {
          "question": "...",
          "answer": "...",
          "interval_days": 3,
          "next_review": "2026-04-03",
          "ease_factor": 2.5,
          "repetitions": 4,
          "confidence": 0.85
        }
```

### 3. 主动召回（Active Recall）

```
禁止: 反复阅读笔记（被动学习，效率低）
强制: 闭上笔记，尝试回忆（主动学习，效率高5x）

Agent实现:
  每次心跳触发"随机抽卡"：
  从 learning_cards/ 中随机抽取到期复习的卡片
  要求Agent先尝试回答（不看答案）
  对比答案 → 更新置信度 → 调整间隔
```

### 4. 学习 Growth Score

```
Learning Growth Score = 
  (本轮主动召回正确率 - 上轮) × 知识点重要性权重

停滞 → 触发"学习方法反思"（是不是方法不对？）
退步 → 触发"间隔调整"（是不是间隔太短/太长？）
```

## 安装命令
```bash
clawhub install learning-accelerator
```

## 调用方式
```python
from skills.learning_accelerator import LearningAccelerator

learner = LearningAccelerator(workspace=".")

# 学习新知识
learner.learn(topic="Transformer架构", content="...")

# 费曼复述检查
result = learner.feynman_check(topic="Transformer架构")
print(result.explanation)       # Agent的复述
print(result.gaps)              # 暴露的知识缺口
print(result.confidence)        # 理解置信度

# 间隔重复复习
review = learner.daily_review()
print(review.cards_due)         # 今日到期卡片数
print(review.accuracy)          # 正确率

# 学习状态
stats = learner.stats()
print(stats.total_cards)        # 总知识点数
print(stats.mastery_distribution) # 掌握度分布
print(stats.growth_score)       # 学习成长度
```

## 学术参考
1. [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) — 记忆理论
2. [Beyond RAG for Agent Memory](https://arxiv.org/abs/2602.02007) — 知识检索优化
3. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046) — 自学习Agent
