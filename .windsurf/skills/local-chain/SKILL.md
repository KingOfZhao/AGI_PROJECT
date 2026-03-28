---
name: local-chain
description: Delegate tasks to the local 7-step AI chain processor (Ollama+GLM models) instead of using Claude directly. Use this for code generation, analysis, reasoning, and any task that local models can handle.
---

# Local 7-Step AI Chain Processor

Use this skill to delegate work to the local AI chain, reducing Claude Opus consumption.

## When to Use
- Code generation or refactoring tasks
- Analysis and reasoning questions
- Documentation generation
- Any task where local models (Ollama/GLM) can produce acceptable results

## How to Invoke

```bash
python3 /Users/administruter/Desktop/AGI_PROJECT/scripts/wechat_chain_processor.py "你的问题"
```

## Python API

```python
import sys
sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT/scripts')
sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT/core')

from wechat_chain_processor import ChainProcessor, ChainResult

chain = ChainProcessor()
result = chain.process("问题内容", context="可选上下文")

# result.final_answer   — 最终答案
# result.steps          — 每步详情 [{step, model, content, duration, success}]
# result.route_decision — 路由类型: simple/analysis/deep/code/full
# result.risks          — 零回避扫描发现的风险
# result.total_duration — 总耗时(秒)
# result.summary()      — 可读摘要
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
