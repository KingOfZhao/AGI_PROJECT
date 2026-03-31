---
name: skill-factory-optimizer
version: 1.0.0
author: KingOfZhao
description: Skill工厂优化器 —— 推广引擎+质量监控+工厂自进化，让Skill工厂从"生成-发布"升级为全闭环
tags: [cognition, meta-skill, factory, promotion, monitoring, quality, self-evolution, marketing]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Skill Factory Optimizer

## 元数据

| 字段       | 值                              |
|------------|-------------------------------|
| 名称       | skill-factory-optimizer        |
| 版本       | 1.0.0                          |
| 作者       | KingOfZhao                     |
| 发布日期   | 2026-03-31                     |
| 置信度     | 96%                            |

## 来源碰撞

```
ai-growth-engine (成长引擎)
        ⊗
skill-collision-engine (碰撞引擎)
        ⊗
推广需求 (用户指令)
        ↓
skill-factory-optimizer (工厂全闭环)
```

## 核心哲学

> 工厂之前只做3步：生成→验证→发布。
> 真正的工厂需要6步全闭环：**生成→验证→发布→推广→监控→优化**。
> 本Skill补齐缺失的后3步。

## 工厂全闭环六阶段

```
1. GENERATE 生成    ← skill-collision-engine (已有)
2. VERIFY 验证      ← VERIFICATION_PROTOCOL.md (已有)
3. PUBLISH 发布     ← clawhub publish + git push (已有)
4. PROMOTE 推广     ← skill-promotion-engine (本Skill新增) 🆕
5. MONITOR 监控     ← factory-quality-dashboard (本Skill新增) 🆕
6. OPTIMIZE 优化    ← ai-growth-engine RAPVL (本Skill新增) 🆕
```

## 🆕 能力一：自动推广引擎

每个新Skill发布后，自动生成多平台推广内容：

### 四向推广碰撞（用SOUL方法论写推广文）

```
正面碰撞（价值主张）: 这个Skill解决什么问题？用户痛点是什么？
反面对撞（对比优势）: 不用这个Skill会怎样？现有方案有什么缺陷？
侧面碰撞（差异化）: 这个Skill和其他同类Skill的区别是什么？独特卖点？
整体碰撞（趋势定位）: 这个方向的趋势如何？用户为什么要现在关注？
```

### 推广内容模板

```python
# 知乎专栏模板
zhihu_template = """
# {skill_name}: {one_line_description}

## 为什么需要这个Skill？
{正面碰撞: 痛点描述}

## 我之前试过的方案（都不够好）
{反面对撞: 现有方案缺陷}

## 这个Skill有什么不同？
{侧面碰撞: 差异化卖点}

## 未来趋势
{整体碰撞: 方向趋势}

## 快速开始
\`\`\`bash
clawhub install {skill_slug}
\`\`\`

## 安装后能做什么？
{3个具体使用场景}

---

*开源认知 Skill by KingOfZhao*
*GitHub: {github_url}*
"""

# CSDN模板（技术侧重，含代码示例）
# X/Twitter模板（140字精华版）
# Discord模板（社区互动版）
```

### 推广渠道配置

```python
channels = {
    "知乎": {
        "format": "long_form",
        "tone": "专业+故事性",
        "title_pattern": "我开源了{skill_name}，让Agent拥有{核心能力}",
        "tags": ["OpenClaw", "AI Agent", "开源", skill_category]
    },
    "CSDN": {
        "format": "tech_tutorial",
        "tone": "技术+实操",
        "title_pattern": "【开源】{skill_name}: {技术亮点}（附安装命令）",
        "code_examples": True
    },
    "X/Twitter": {
        "format": "thread",
        "tone": "精炼+话题性",
        "max_chars": 280,
        "hashtags": ["#OpenClaw", "#AI", "#AIAgent", "#开源"]
    },
    "Discord": {
        "format": "community",
        "tone": "友好+互动",
        "channel": "#chinese-contributors",
        "call_to_action": "试用后反馈！"
    }
}
```

## 🆕 能力二：工厂质量监控

### 监控指标

```
factory_metrics = {
    # 产出指标
    "total_skills": 11,                    # 已发布Skill总数
    "skills_this_week": 11,               # 本周产出
    "average_confidence": 0.96,           # 平均自验证置信度
    "first_publish_success_rate": 0.90,   # 首次发布成功率

    # 质量指标
    "low_confidence_skills": [],          # 置信度<95%的Skill（应触发优化）
    "stale_skills": [],                   # >30天未更新的Skill
    "orphan_skills": [],                  # 无引用关系的孤立Skill

    # 碰撞指标（来自skill-collision-engine）
    "collision_matrix_coverage": "3/55",  # 已碰撞/总碰撞方向
    "collision_success_rate": 0.85,       # 碰撞产生新Skill的比例
    "best_collision_direction": "...",    # 最高产出碰撞方向

    # 推广指标
    "promotion_coverage": "7/11",         # 已推广/总Skill数
    "pending_promotions": [],             # 待推广Skill列表
}
```

### 质量告警规则

```
告警规则:
  - 置信度 < 95% → 🟡 需要补充验证
  - 孤立Skill（无父子关系）→ 🟡 需要建立碰撞关系
  - >7天未推广 → 🟡 推广积压
  - 碰撞矩阵覆盖率 < 20% → 🟠 碰撞方向不足
  - 连续2个Skill置信度下降 → 🔴 碰撞质量下降，需人工介入
```

## 🆕 能力三：工厂自进化（RAPVL应用于工厂自身）

```
把 ai-growth-engine 的 RAPVL 循环应用于工厂:

R — Review:     回顾最近发布的N个Skill的验证报告
A — Analyze:    提取低置信度的共同模式（哪个Step最容易FAIL？）
P — Plan:       制定优化计划（补充外部知识？调整碰撞权重？）
V — Verify:     下次碰撞时检查置信度是否提升
L — Learn:      更新 skill-collision-engine 的碰撞参数

Growth Score (工厂版):
  = (本轮平均置信度 - 上轮平均置信度) × 新Skill复杂度权重
```

## 安装命令

```bash
clawhub install skill-factory-optimizer
# 或手动安装
cp -r skills/skill-factory-optimizer ~/.openclaw/skills/
```

## 调用方式

```python
from skills.skill_factory_optimizer import SkillFactoryOptimizer

optimizer = SkillFactoryOptimizer(workspace=".", skills_dir="./skills")

# 1. 自动推广
promo = optimizer.generate_promotion(
    skill_name="ai-growth-engine",
    channels=["知乎", "CSDN", "X", "Discord"],
    collision_insights={  # 四向碰撞产生的推广素材
        "正面": "Agent不知道自己是否在变好",
        "反面": "PDCA和OODA都不适合AI",
        "侧面": "RAPVL比PDCA多模式提取+文件记忆",
        "整体": "AI成长是所有Agent的核心需求"
    }
)
print(promo.zhihu)    # 知乎专栏文章
print(promo.csdn)     # CSDN技术文章
print(promo.x_thread) # X推文串

# 2. 工厂质量报告
report = optimizer.factory_report()
print(report.total_skills)          # 11
print(report.average_confidence)    # 0.96
print(report.alerts)                # ["🟡 researcher-cognition待推广"]
print(report.collision_coverage)    # "3/55 (5%)"
print(report.recommendations)       # ["建议碰撞方向: human-ai × arxiv-collision"]

# 3. 工厂自进化
evolution = optimizer.run_factory_rapvl()
print(evolution.growth_score)       # +0.03
print(evolution.param_updates)      # {"direction_weights": {"反面": 0.30}}
print(evolution.next_actions)       # ["补充Wikipedia知识注入", "碰撞human-ai×arxiv"]
```

## 与其他 Skill 的关系

```
SOUL (根)
  └── self-evolution-cognition
        ├── skill-collision-engine (碰撞引擎)
        ├── ai-growth-engine (成长引擎)
        │       └── skill-factory-optimizer (本Skill: 工厂全闭环) 🆕
        │               ├── 推广引擎 (四向推广碰撞)
        │               ├── 质量监控 (指标+告警)
        │               └── 工厂自进化 (RAPVL)
        └── [所有其他Skill] (被优化对象)
```

## 学术参考文献

1. **[A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046)** — 工厂自进化的理论基础
2. **[SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255)** — 多Agent进化（←工厂多Skill进化）
3. **[Group-Evolving Agents](https://arxiv.org/abs/2602.04837)** — 经验共享（←碰撞矩阵优化）
4. **[Self-evolving Embodied AI](https://arxiv.org/abs/2602.04411)** — 元进化循环
5. **[Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564)** — 推广素材记忆
6. **[Beyond RAG for Agent Memory](https://arxiv.org/abs/2602.02007)** — 跨Skill经验聚合
