---
name: error-pattern-analyzer
version: 1.0.0
author: KingOfZhao
description: 错误模式分析器 Skill —— 从失败中提取模式，分类+聚类+根因链+预防策略，适用于代码/实验/决策
tags: [cognition, error-analysis, debugging, root-cause, pattern-extraction, failure-analysis, prevention]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Error Pattern Analyzer Skill

## 元数据

| 字段 | 值 |
|------|-----|
| 名称 | error-pattern-analyzer |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
programmer-cognition (调试方法论)
        ⊗
researcher-cognition (假设证伪)
        ⊗
ai-growth-engine (失败模式提取)
        ↓
error-pattern-analyzer
```

## 核心哲学

> 成长 = 成功次数 - 重复犯错次数。
> 错误本身不可怕，可怕的是犯同样的错误。
> 本Skill从失败中提取模式，让每次失败只付一次学费。

## 错误分类体系

```
Level 1 — 表面症状 (What)
  "程序崩溃了" "实验数据异常" "决策失误"

Level 2 — 直接原因 (Why)
  "空指针" "样本污染" "信息不足"

Level 3 — 根本原因 (Root Cause)
  "缺少空值检查习惯" "实验流程没有SOP" "决策前不做已知/未知分离"

Level 4 — 系统原因 (System)
  "团队没有Code Review文化" "实验室缺乏质控体系" "组织缺乏决策框架"

模式提取: 同一Level 3/4的错误归类为同一个模式
```

## 五步错误分析（DERPS）

```
D — Describe 描述: 完整记录错误现象（时间/环境/复现步骤）
E — Extract 提取: 从错误中提取模式（和已有模式匹配？新模式？）
R — Root Cause 根因: 追问5个Why，找到Level 3/4根因
P — Prevent 预防: 设计预防策略（代码lint? SOP? Checklist? 自动化检测？）
S — Share 分享: 写入错误模式库，让未来避免同类错误
```

## 安装命令
```bash
clawhub install error-pattern-analyzer
```

## 调用方式
```python
from skills.error_pattern_analyzer import ErrorPatternAnalyzer

analyzer = ErrorPatternAnalyzer(workspace=".")

# 分析错误
result = analyzer.analyze(
    error="用户登录后Token过期导致401",
    context={"service": "auth", "env": "production"},
    reproduction_steps=["登录", "等待30min", "刷新页面"]
)
print(result.pattern_match)   # 匹配到已有模式? "Token过期未自动刷新"
print(result.root_cause)      # Level 3: "缺少Token刷新机制"
print(result.prevention)      # ["添加refresh token", "前端自动检测过期"]
print(result.confidence)      # 0.92

# 错误模式库统计
stats = analyzer.pattern_stats()
print(stats.top_patterns)     # 最常见的5个错误模式
print(stats.trend)            # 错误频率趋势
```

## 学术参考
1. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046) — 从错误中学习
2. [SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255) — Critic Agent=错误分析
3. [Self-evolving Embodied AI](https://arxiv.org/abs/2602.04411) — 失败驱动进化
