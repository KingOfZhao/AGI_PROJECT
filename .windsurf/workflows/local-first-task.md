---
description: Execute a task using GLM-First strategy - implement directly with GLM-5.1, no local model invocation
---

# GLM-First Task Execution

> 本地模型已停用。所有任务直接由 GLM-5.1 完成。

## Step 1: 参考 Skill 概念文档
查看 `skills/` 目录下相关 SKILL.md ，了解概念和设计模式。
Skill 文件为纯文档参考，不调用任何本地进程。

## Step 2: GLM-5.1 直接实现
通过 OpenClaw (primary: glm51/glm-5.1) 完成编码和推理任务。

## Step 3: 验证结果
- 代码是否语法正确可运行？
- 是否准确完整地回答了原始问题？

## Step 4: 后处理
- 提取知识节点写入 SKILL.md 概念文档
- 记录到 CRM 系统
