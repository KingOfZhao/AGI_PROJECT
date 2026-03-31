# arxiv-collision-cognition

> ArXiv 论文碰撞认知 Skill —— 用四向碰撞从学术论文中炼出可操作的项目洞见

**作者**: KingOfZhao  
**版本**: 1.0.0  
**发布日期**: 2026-03-31  
**许可证**: MIT

---

## 这个 Skill 解决什么问题？

读论文时，大多数人只能总结"作者提出了方法X达到了精度Y"。  
`arxiv-collision-cognition` 强制你的 Agent 用四个视角与论文碰撞，
挖出论文和你项目之间真正有价值的交叉点：

```
正面碰撞  → 论文核心方法能直接迁移到你的项目吗？
反面碰撞  → 论文的失败场景正是你的优势场景吗？
侧面碰撞  → Ablation/附录中有什么被作者低估的方法？
整体碰撞  → 这篇论文预示着什么行业趋势？你该怎么布局？
```

每次碰撞都写入日志，产生带置信度的可操作洞见清单，支持人类标记「已验证/已证伪」。

## 快速安装

```bash
clawhub install arxiv-collision-cognition
```

## 完整使用示例

```python
from skills.arxiv_collision_cognition import ArxivCollisionCognition

acc = ArxivCollisionCognition(workspace=".")

# 与 ArXiv 论文碰撞
result = acc.collide(
    arxiv_id="2401.00123",   # 替换为你感兴趣的论文ID
    project_context={
        "domain": "corrugated packaging quality control",
        "known": [
            "当前视觉检测准确率87%",
            "主要缺陷：压痕过深、刀模偏移"
        ],
        "unknown": [
            "如何检测微小(<0.5mm)的纸板分层",
            "声波检测是否适用于高速生产线"
        ]
    }
)

# 输出碰撞结果
for insight in result.actionable_insights:
    print(f"[{insight.confidence:.0%}] {insight.description}")
    print(f"  → 行动项: {insight.action}")
    print(f"  → 来自: {insight.collision_direction} 碰撞")

# 人类标记已验证
acc.mark_tried("insight_001", result="validated", notes="在测试线上准确率提升到91%")
```

## 四向碰撞输出示例

```
[92%] 论文的多尺度特征融合可用于检测不同尺寸的压痕缺陷
  → 行动项: 修改 DiePre 视觉模块，添加 FPN 多尺度分支
  → 来自: 正面碰撞

[78%] 论文在低对比度场景下失效 → 正是我们夜班低光照工况的机会
  → 行动项: 在低光照下收集更多训练数据，建立差异化优势
  → 来自: 反面碰撞

[85%] 论文 Appendix B 的轻量化版本推理速度快 3x，主文未重点介绍
  → 行动项: 评估轻量版是否满足生产线实时要求
  → 来自: 侧面碰撞

[88%] 该方向论文数量 2024 年增长 340%，预示工业视觉将成标配
  → 行动项: 提前布局专利申请，6个月内完成核心模块
  → 来自: 整体碰撞
```

## 与其他 Skill 配合使用

```bash
# 发现洞见后，用人机闭环验证
clawhub install human-ai-closed-loop

# 将洞见注入自进化框架
clawhub install self-evolution-cognition

# 在 DiePre 场景落地
clawhub install diepre-vision-cognition
```

## 变更日志

### v1.0.0 (2026-03-31)
- 初始发布
- 四向碰撞推理框架实现
- ArXiv API 集成
- 通过自验证置信度: 95%

---

*开源认知 Skill by KingOfZhao*
