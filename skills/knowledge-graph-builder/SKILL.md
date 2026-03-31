---
name: knowledge-graph-builder
version: 1.0.0
author: KingOfZhao
description: 知识图谱构建器 Skill —— 将碎片化认知结构化为节点+关系图谱，支持Skill碰撞矩阵可视化
tags: [cognition, knowledge-graph, visualization, structured-knowledge, graph, ontology, nodes]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Knowledge Graph Builder Skill

## 元数据

| 字段 | 值 |
|------|-----|
| 名称 | knowledge-graph-builder |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
skill-collision-engine (碰撞矩阵)
        ⊗
memory-hierarchy-system (知识存储)
        ⊗
arxiv-collision-cognition (论文知识提取)
        ↓
knowledge-graph-builder
```

## 核心哲学

> 认知世界的本质是无穷层级的框架节点。
> 知识图谱就是把这些节点和关系可视化。
> 没有图谱的认知是碎片，有图谱的认知是结构。

## 图谱模型

```
节点(Node):
  - id: 唯一标识
  - type: skill | concept | paper | tool | person | project
  - name: 显示名称
  - confidence: 置信度
  - level: 层级（根/核心/叶子）
  - metadata: 领域特有数据

关系(Edge):
  - parent_of: 父子关系（skill-collision → programmer-cognition）
  - collision_of: 碰撞关系（self-evo × diepre → vision-action）
  - references: 引用关系（paper → concept）
  - extends: 扩展关系（skill_v2 extends skill_v1）
  - conflicts_with: 冲突关系（两个认知点矛盾）
```

## Skill进化树可视化

```
自动生成当前Skill工厂的进化树:
  深度 = Skill的层级
  宽度 = 每层的Skill数量
  颜色 = Skill类型（核心/元引擎/领域/职业）
  连线 = 碰撞关系

输出格式: Mermaid图表（可直接嵌入Markdown/README）
```

## 安装命令
```bash
clawhub install knowledge-graph-builder
```

## 调用方式
```python
from skills.knowledge_graph_builder import KnowledgeGraphBuilder

kg = KnowledgeGraphBuilder(workspace=".")

# 添加节点
kg.add_node("DiePre K因子", type="concept", confidence=0.95)
kg.add_node("灰板K=0.35-0.40", type="concept", confidence=0.90)

# 添加关系
kg.add_edge("DiePre K因子", "灰板K=0.35-0.40", relation="has_value")

# 生成进化树
tree = kg.generate_evolution_tree()
print(tree.mermaid)    # Mermaid格式图表
print(tree.stats)      # 节点数、关系数、深度、宽度

# 查询
results = kg.query("K因子相关的所有认知")
print(results.nodes)   # 相关节点列表
print(results.paths)   # 节点间路径
```

## 学术参考
1. [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) — 知识结构化
2. [Beyond RAG for Agent Memory](https://arxiv.org/abs/2602.02007) — 图谱检索
3. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046) — 知识驱动进化
