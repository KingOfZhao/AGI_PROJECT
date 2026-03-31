---
name: local-chain
description: "[概念存档 · 已停用] 本地7步AI调用链概念文档。本地模型已停用，所有任务直接由 GLM-5.1 处理。"
status: disabled
---

# Local 7-Step AI Chain Processor（概念存档）

> ⚠️ **已停用**：本地模型（Ollama/qwen2.5-coder:14b）已关闭。
> 所有编码和推理任务直接由 **GLM-5.1**（glm51）处理，无需本地链。

以下内容保留为架构概念参考，不再实际执行。

## When to Use
- Code generation or refactoring tasks
- Analysis and reasoning questions
- Documentation generation
- Any task where local models (Ollama/GLM) can produce acceptable results

## 当前替代方案

直接使用 GLM-5.1 处理所有任务，无需调用本地链：

```python
# 通过 OpenClaw 使用 GLM-5.1
# primary model: glm51/glm-5.1 (已在 openclaw.json 配置)
```

## Route Types
| Route | Steps | Use Case |
|-------|-------|----------|
| simple | Ollama直答 | 闲聊/问候 |
| analysis | Ollama路由 → GLM-5T | 一般分析 |
| deep | Ollama → GLM-5T → GLM-5 | 深度推理 |
| code | Ollama → GLM-5T → GLM-4.7 | 代码生成 |
| full | 全部7步 | 复杂问题 |

## Verification
After receiving local chain results, verify:
1. Answer addresses the original question
2. Code (if any) is syntactically correct
3. No hallucination warnings flagged
4. Risk scan results are acceptable

If results are unsatisfactory, retry with more context or escalate to Claude with explanation.
