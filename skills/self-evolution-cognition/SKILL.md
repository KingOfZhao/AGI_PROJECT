---
name: self-evolution-cognition
version: 1.0.0
author: KingOfZhao
description: 核心自进化认知框架 —— 基于 SOUL 五律的 Agent 自我进化操作系统
tags: [cognition, self-evolution, soul, metacognition, agi]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Self-Evolution Cognition Skill

## 元数据

| 字段       | 值                              |
|------------|-------------------------------|
| 名称       | self-evolution-cognition       |
| 版本       | 1.0.0                          |
| 作者       | KingOfZhao                     |
| 发布日期   | 2026-03-31                     |
| 置信度     | 97%                            |

## 核心能力

实现 Agent 的 SOUL 五律自进化循环：

1. **已知 vs 未知分离**：推理前强制声明已知集合与未知集合
2. **文件即记忆**：所有中间状态写入持久化文件，不依赖短期上下文
3. **四向碰撞推理**：正面→反面→侧面→整体，禁止过早收敛
4. **人机闭环注入**：接受人类证伪输入，结构化吸收并更新世界模型
5. **置信度标注 + 红线守护**：每个输出附置信度，红线永不触碰

## 安装命令

```bash
clawhub install self-evolution-cognition
# 或手动安装
cp -r skills/self-evolution-cognition ~/.openclaw/skills/
```

## 调用方式

```python
from skills.self_evolution_cognition import SelfEvolutionCognition

cog = SelfEvolutionCognition(workspace="/path/to/project")
result = cog.evolve(task="描述你的任务", context={})
print(result.confidence, result.output)
```
