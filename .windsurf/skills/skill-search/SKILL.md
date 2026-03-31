---
name: skill-search
description: "[概念存档 · 已停用] 本地 Skill 库检索概念文档。本地模型已停用，不再通过本地模型搜索或调用 SKILL 库。"
status: disabled
---

# Local Skill Library Search（概念存档）

> ⚠️ **已停用**：本地模型已关闭，不再通过 `pcm_skill_router` 搜索和调用本地 SKILL 库。
> Skill 文件保留为概念文档参考。

以下内容保留为架构概念参考，不再实际执行。

(概念) Search 6000+ skills in `/Users/administruter/Desktop/AGI_PROJECT/skills/` using the PCM skill router.

## When to Use
- Before implementing any new functionality
- When looking for reusable code patterns
- When the user asks about capabilities

## 当前替代方案

Skill 文件作为概念文档手动参考。所有实际编码和实现直接由 **GLM-5.1** 处理。

## Skill Categories
- **openclaw**: 5982 community skills (code/deploy/search/security/data)
- **gstack**: 29 engineering workflow skills (review/qa/deploy/security)
- **custom**: User-generated skills from growth engine

## After Finding Skills
1. Read the skill's full content if score > 5.0
2. Adapt or compose multiple skills for complex tasks
3. If no good match, proceed with new implementation
