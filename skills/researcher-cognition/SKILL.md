---
name: researcher-cognition
version: 1.0.0
author: KingOfZhao
description: 科研人员认知 Skill —— SOUL五律适配学术研究，文献碰撞四向推理+假设验证+可复现性红线
tags: [cognition, researcher, academic, literature-review, hypothesis-testing, reproducibility, scientific-method]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Researcher Cognition Skill

## 元数据

| 字段       | 值                              |
|------------|-------------------------------|
| 名称       | researcher-cognition           |
| 版本       | 1.0.0                          |
| 作者       | KingOfZhao                     |
| 发布日期   | 2026-03-31                     |
| 置信度     | 96%                            |

## 来源碰撞

```
arxiv-collision-cognition (论文碰撞)
        ⊗
self-evolution-cognition (自进化)
        ⊗
human-ai-closed-loop (人机闭环)
        ↓
researcher-cognition (科研人员专用认知)
```

## SOUL 五律 × 科研适配

### 1. 已知 vs 未知 → 假设驱动的已知/未知

```
科研的已知 vs 未知:
  已知 (F): 已有实验数据、已发表论文、已验证理论、已复现结果
  未知 (V): 未验证的假设、矛盾的数据、理论空白、方法局限

强制规则:
  每个研究问题必须先列已知集合和未知集合
  结论只能从已知集合自然涌现，禁止从框架推导
  未知中的每个条目标注: [重要/次要] + [预计验证方式] + [所需资源]
```

### 2. 四向碰撞 → 文献碰撞四向推理

```
对每篇论文执行四向碰撞:

正面碰撞: 论文核心方法能否直接复现/迁移？
  - 实验设置是否完整？
  - 代码是否开源？
  - 数据集是否可获取？

反面碰撞: 论文的局限性是否是你的机会？
  - 论文声称的"state-of-art"在什么条件下不成立？
  - 消融实验中哪些组件贡献最小（可替换）？
  - 论文未讨论的边缘case有哪些？

侧面碰撞: 论文的非主要贡献是否有隐藏价值？
  - Appendix中是否有被低估的方法？
  - 错误分析中是否暴露了新的研究方向？
  - 作者的失败尝试（如果披露）暗示了什么？

整体碰撞: 论文预示什么趋势？你该怎么布局？
  - 该方向论文增长率如何？
  - 跟进工作的竞争格局？
  - 是否存在跨领域迁移的机会？
```

### 3. 人机闭环 → 实验验证循环

```
科研实践验证方式:
  1. AI整理文献 → 已知/未知分离 → 生成假设清单
  2. 人类设计实验 → 控制变量 → 收集数据
  3. AI分析数据 → 统计检验 → 提取洞见
  4. 人类评估洞见 → 判断是否有意义 → 注入想象力
  5. AI结构化输出 → 论文初稿 → 迭代

关键: AI不能做实验（当前），人类不能高效读所有文献
→ 闭环互补: AI做文献碰撞+数据分析，人类做实验设计+意义判断
```

### 4. 文件即记忆 → 研究记忆系统

```
强制文件记忆:
  literature_review/{topic}/
    known.md          — 该领域已确认的事实（附引用）
    unknown.md        — 该领域未解决的问题
    hypotheses.md     — 假设清单（每个标注验证状态）
    collision_log/    — 每篇论文的四向碰撞记录

  experiments/{exp_id}/
    hypothesis.md     — 被验证的假设
    setup.md          — 实验设置（可复现性核心）
    data/             — 原始数据
    analysis.md       — 数据分析+统计检验
    conclusion.md     — 结论 + 置信度标注

  insights/
    daily/{date}.md   — 每日研究洞见
    verified.md       — 已验证洞见（人类确认）
    rejected.md       — 已证伪假设（同样有价值）
```

### 5. 置信度 + 红线 → 科研红线清单

```
科研红线（永不触碰）:
  🔴 不伪造/篡改数据（最基本）
  🔴 不选择性报告结果（cherry-picking）
  🔴 不声称"已验证"实际未验证的结论
  🔴 不忽略矛盾数据（矛盾数据=最有价值的信息）
  🔴 不复制原文不标注引用（学术诚信）
  🔴 不在置信度<80%时发布结论

置信度标注（科研版）:
  - [已复现] 自己独立复现了结果
  - [已验证] 多源交叉验证一致
  - [高确信] 理论推导严密 + 部分实验支持
  - [推测] 理论预测但未实验验证 → 必须标注为推测
  - [不确定] 数据不足或矛盾 → 必须设计新实验
```

## 与 arxiv-collision-cognition 的区别

```
arxiv-collision-cognition:
  → 通用论文碰撞工具（与任何项目碰撞）
  → 输入: arXiv ID + 项目上下文
  → 输出: 可操作洞见列表

researcher-cognition:
  → 科研人员的完整认知框架
  → 输入: 整个研究过程（文献→假设→实验→结论）
  → 输出: 结构化研究记忆 + 可复现实验记录
  → 内含 arxiv-collision-cognition 作为子能力
```

## 安装命令

```bash
clawhub install researcher-cognition
# 或手动安装
cp -r skills/researcher-cognition ~/.openclaw/skills/
```

## 调用方式

```python
from skills.researcher_cognition import ResearcherCognition

researcher = ResearcherCognition(workspace="./research")

# 文献碰撞
collision = researcher.collide_paper(
    arxiv_id="2603.15255",
    domain="self-evolving agents",
    known=["SAGE uses 4 agents", "tested on 3 benchmarks"],
    unknown=["scalability", "generalization to other domains"]
)

# 假设管理
researcher.add_hypothesis(
    "四向碰撞推理的涌现认知产出率随碰撞深度非线性增长",
    priority="high",
    verification_method="controlled experiment with 50+ collision pairs"
)

# 实验记录
researcher.log_experiment(
    exp_id="exp_001",
    hypothesis="四向碰撞产出率非线性增长",
    setup={"variable": "collision_depth", "range": [1,2,3,4,5]},
    data={"results": [...]},
    conclusion="假设成立，深度≥3时产出率饱和",
    confidence=0.88
)

# 研究状态总览
status = researcher.status()
print(status.total_papers_collided)  # 47
print(status.active_hypotheses)      # 12
print(status.verified_insights)      # 23
print(status.rejected_hypotheses)    # 8
```

## 学术参考文献

1. **[A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046)** — 自进化综述（研究方法论的参考）
2. **[SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255)** — 四Agent闭环（四向碰撞的学术对应）
3. **[Group-Evolving Agents](https://arxiv.org/abs/2602.04837)** — 经验共享（科研协作的理论基础）
4. **[Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564)** — 研究记忆系统
5. **[Beyond RAG for Agent Memory](https://arxiv.org/abs/2602.02007)** — 文献检索超越RAG
6. **[Self-evolving Embodied AI](https://arxiv.org/abs/2602.04411)** — 自迭代实验设计
