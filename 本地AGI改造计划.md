# 本地AGI改造计划

## 已知
- M1 Max 32GB 可跑 14B 模型（已验证 qwen2.5-coder 正常）
- Ollama 提供 OpenAI 兼容 API（localhost:11434）
- OpenClaw 可通过 Anthropic 兼容接口接入 Ollama（需确认）
- 当前模型能力：代码生成、文本推理（通用LLM）

## 未知（核心问题）
1. "AGI模型"的具体定义是什么？需要哪些能力增量？
2. Ollama + OpenClaw 的本地接入是否可行？
3. 能否通过 prompt engineering + RAG + tool-use 在现有模型上实现"类AGI"行为？
4. 是否需要微调（fine-tune）？还是通过系统架构（agent框架）实现？

## 可执行路径（从易到难）

### 路径A：Ollama + OpenClaw 接入（最快，今天可完成）
- 配置 OpenClaw 使用本地 Ollama 模型
- 测试本地模型是否能跑通心跳/技能/Cron
- 优势：零依赖外部API，完全离线

### 路径B：本地RAG + 认知记忆系统（1-2天）
- 用 nomic-embed-text 建立本地知识库向量索引
- 将 MEMORY.md / DiePre知识库 / 推演成果注入
- 让模型能"回忆"和"推理"历史知识

### 路径C：自我改进循环（1周）
- 模型输出 → 自我验证 → 修正认知 → 更新知识库
- 用 SOUL.md 的自验证协议驱动

### 路径D：LoRA微调（需要更多资源）
- 基于qwen2.5-coder做领域微调（DiePre/刀模/视觉识别）
- 需要 A100 或多GPU，当前 M1 Max 32GB 可做小规模QLoRA

## 决策点
用户需要确认：
1. 目标是什么？完全离线？还是本地优先+云端兜底？
2. 重点领域？DiePre刀模？通用AGI？具身智能？
3. 先跑哪条路径？
