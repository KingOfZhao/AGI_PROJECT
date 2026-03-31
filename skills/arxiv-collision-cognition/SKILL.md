---
name: arxiv-collision-cognition
version: 1.0.0
author: KingOfZhao
description: ArXiv 论文碰撞认知 Skill —— 用四向碰撞推理从学术论文中提取可操作洞见
tags: [cognition, arxiv, research, collision-reasoning, knowledge-extraction, literature]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# ArXiv Collision Cognition Skill

## 元数据

| 字段       | 值                              |
|------------|-------------------------------|
| 名称       | arxiv-collision-cognition      |
| 版本       | 1.0.0                          |
| 作者       | KingOfZhao                     |
| 发布日期   | 2026-03-31                     |
| 置信度     | 95%                            |

## 核心能力

将 ArXiv 论文与你当前项目的已知知识进行四向碰撞，提取跨域洞见：

1. **正面碰撞**：论文核心方法与你的现有方案直接对比，找出可迁移技术
2. **反面碰撞**：论文的局限性/失败案例是否正是你的场景优势？
3. **侧面碰撞**：论文的非主要贡献（ablation / appendix）中是否有隐藏宝藏？
4. **整体碰撞**：论文的研究方向趋势是否预示你项目的未来路径？

已知/未知分离 + 文件记忆 + 人机闭环全部在此场景中应用。

## 安装命令

```bash
clawhub install arxiv-collision-cognition
# 或手动安装
cp -r skills/arxiv-collision-cognition ~/.openclaw/skills/
```

## 调用方式

```python
from skills.arxiv_collision_cognition import ArxivCollisionCognition

acc = ArxivCollisionCognition(workspace=".")

# 用 ArXiv ID 触发碰撞
result = acc.collide(
    arxiv_id="2403.12345",
    project_context={
        "domain": "packaging quality control",
        "known": ["corrugated board defect types", "current detection accuracy 87%"],
        "unknown": ["thermal deformation modeling", "acoustic inspection feasibility"]
    }
)

print(result.confidence)         # 置信度
print(result.actionable_insights) # 可操作洞见列表
print(result.collision_log)      # 四向碰撞详情
```
