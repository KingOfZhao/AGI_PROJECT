---
name: workflow-orchestrator
version: 1.0.0
author: KingOfZhao
description: 工作流编排器 Skill —— 将多个Skill组合为自动化工作流，支持串行/并行/条件分支/循环
tags: [cognition, workflow, orchestrator, automation, pipeline, skill-composition, dag]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Workflow Orchestrator Skill

## 元数据

| 字段 | 值 |
|------|-----|
| 名称 | workflow-orchestrator |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
skill-collision-engine (Skill组合)
        ⊗
skill-factory-optimizer (工厂自动化)
        ⊗
ai-growth-engine (工作流进化)
        ↓
workflow-orchestrator
```

## 核心哲学

> 单个Skill是节点，工作流是连接节点的图。
> 编排器让Skill之间自动协作，形成1+1>2的效果。

## 工作流定义

```python
# 示例：论文阅读→碰撞→生成洞见 的完整工作流

workflow = {
    "name": "paper-insight-pipeline",
    "nodes": [
        {"id": "fetch", "skill": "arxiv-collision-cognition", "action": "fetch_paper"},
        {"id": "collide", "skill": "arxiv-collision-cognition", "action": "collide"},
        {"id": "extract", "skill": "error-pattern-analyzer", "action": "extract_patterns"},
        {"id": "decide", "skill": "decision-framework", "action": "decide"},
        {"id": "record", "skill": "memory-hierarchy-system", "action": "remember"},
        {"id": "grow", "skill": "ai-growth-engine", "action": "record_action"},
    ],
    "edges": [
        {"from": "fetch", "to": "collide"},
        {"from": "collide", "to": "extract"},
        {"from": "extract", "to": "decide", "condition": "has_insights"},
        {"from": "extract", "to": "grow", "condition": "no_insights"},
        {"from": "decide", "to": "record"},
        {"from": "decide", "to": "grow"},
    ]
}
```

## 支持的执行模式

```
串行:   A → B → C → D
并行:   A ─┬→ B
            └→ C → D
条件:   A → [条件] → B (真) / C (假)
循环:   A → B → [检查] → B (不满足) / C (满足)
子流程: A → [子工作流X] → B
```

## 安装命令
```bash
clawhub install workflow-orchestrator
```

## 调用方式
```python
from skills.workflow_orchestrator import WorkflowOrchestrator

orchestrator = WorkflowOrchestrator(workspace=".")

# 注册已安装的Skill
orchestrator.register_skills(["arxiv-collision-cognition", 
                              "decision-framework", 
                              "memory-hierarchy-system"])

# 执行工作流
result = orchestrator.run(workflow="paper-insight-pipeline", 
                          input={"arxiv_id": "2603.15255"})
print(result.status)          # "completed"
print(result.node_results)     # 每个节点的输出
print(result.total_time_ms)    # 总执行时间

# 列出可用工作流
flows = orchestrator.list_workflows()
```

## 学术参考
1. [SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255) — 多Agent编排
2. [Group-Evolving Agents](https://arxiv.org/abs/2602.04837) — 群体协作
3. [Self-evolving Embodied AI](https://arxiv.org/abs/2602.04411) — 工作流自进化
