---
name: prompt-engineering-cognition
version: 1.0.0
author: KingOfZhao
description: Prompt工程认知 Skill —— SOUL五律适配Prompt设计，四向碰撞+已知未知+迭代优化+Prompt记忆库
tags: [cognition, prompt-engineering, llm, optimization, iteration, prompt-patterns]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Prompt Engineering Cognition Skill

## 元数据

| 字段 | 值 |
|------|-----|
| 名称 | prompt-engineering-cognition |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
self-evolution-cognition (已知/未知+自进化)
        ⊗
programmer-cognition (代码=Prompt的类比)
        ⊗
ai-growth-engine (迭代优化)
        ↓
prompt-engineering-cognition
```

## SOUL五律 × Prompt工程

### 1. 已知 vs 未知 → Prompt清晰度分离
```
已知(写Prompt前明确): 任务目标、输出格式、约束条件、示例
未知(需要迭代发现): 最佳System Prompt措辞、few-shot最优数量、温度参数
规则: 每个Prompt必须标注 [期望输出] 和 [已知限制]
```

### 2. 四向碰撞 → Prompt优化四向碰撞
```
正面: 这个Prompt能准确传达任务吗？有歧义吗？
反面: 这个Prompt在什么输入下会产生错误输出？边缘case？
侧面: 这个Prompt的模式能复用到其他任务吗？
整体: 这个Prompt是否符合项目整体Prompt架构？和系统Prompt冲突吗？
```

### 3. 人机闭环 → Prompt迭代优化
```
V0: 初始Prompt → 测试5个输入 → 记录失败case
V1: 修正失败case → 测试10个输入 → 记录失败case
V2: 加入few-shot → 测试20个输入 → 记录失败case
...
收敛: 连续10个输入全部正确 → 标记为STABLE
```

### 4. 文件即记忆 → Prompt版本库
```
prompts/
  {task_name}/
    v0_prompt.md
    v1_prompt.md
    test_cases.jsonl
    iteration_log.md
    final_stable.md
```

### 5. 红线
```
🔴 不在Prompt中硬编码敏感信息
🔴 不假设模型能"理解"模糊指令（必须明确）
🔴 不跳过边缘case测试
🔴 不在生产环境使用未经验证的Prompt
🔴 不忽视Prompt长度对输出的影响
```

## 安装命令
```bash
clawhub install prompt-engineering-cognition
```

## 调用方式
```python
from skills.prompt_engineering_cognition import PromptEngineeringCognition

pe = PromptEngineeringCognition(workspace=".")

# 优化Prompt
result = pe.optimize(
    prompt="分析这段代码的问题",
    test_cases=[
        {"input": "good code", "expected": "no issues"},
        {"input": "buggy code", "expected": "specific bugs found"},
    ]
)
print(result.optimized_prompt)  # 优化后的Prompt
print(result.version)           # "v3"
print(result.test_pass_rate)    # 0.95

# Prompt评审
review = pe.review(prompt=system_prompt, context="DiePre视觉检测")
print(review.ambiguities)       # 歧义点
print(recommendations)          # 改进建议
```

## 学术参考
1. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046) — Prompt自进化
2. [SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255) — 多Prompt协作
3. [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) — Prompt记忆库
