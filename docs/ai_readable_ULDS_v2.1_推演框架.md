# ULDS v2.1 九大规律推演框架 — AI 可读文档

> **生成时间**: 2026-03  
> **用途**: 供 AI 系统快速理解本项目的 ULDS 推演框架全貌  
> **源文件索引**: 见文末「源文件清单」

---

## 1. 框架概述

**ULDS** = Universal Laws Deduction Skill v2.1  
核心理念: **人类认知的一切科学技能和能力都从十一大必然规律出发，从规律到答案之间的路径就是推演——逐级细化直到路径清晰可见、可执行。**

- 优先级: **P0**（系统最高优先级 meta-skill）
- 自动化程度: ~90%，全程标注 `[CODE]` / `[HUMAN]`
- 零回避: 不回避任何问题，包括框架自身局限

---

## 2. 十一大规律 (Eleven Laws)

| 编号 | 名称 | 说明 |
|------|------|------|
| L1 | 数学公理与定理 | 数学结构、证明、公式 |
| L2 | 物理定律 | 力学、热力学、电磁学等 |
| L3 | 化学定律 | 化学反应、材料科学 |
| L4 | 逻辑规律 | 形式逻辑、推理规则 |
| L5 | 信息论规律 | 熵、编码、信道容量 |
| L6 | 系统理论与控制论 | 反馈、稳定性、涌现 |
| L7 | 概率与统计规律 | 随机过程、统计推断 |
| L8 | 对称性与守恒原理 | 不变量、对称变换 |
| L9 | 可计算性与算法极限 | 停机问题、复杂度、Gödel |
| L10 | 演化动力学 | 变异+选择+保留→适应 |
| L11 | 认识论极限 | Gödel不完备+观测者效应+有限理性 |

> 十一大规律是 **硬编码底层**，不可突破，只可在其约束内推演。

---

## 3. 推演管线 (Pipeline)

```
Step0 输入初始化
  → Step1 规律→约束映射 (将问题映射到 L1-L11 中的相关规律)
    → Step2 变量引入 (F→V→F 链式收敛: 固定→可变→固定)
      → Step3 迭代提炼 (PHRP 五级渐进细化)
        → Step4 全链路验证 (测试+证伪+边界检查)
          → Step5 输出交付 (可执行结果)
            → Step6 反馈闭环 (人类验证→参数修正→规律回溯)
```

### 关键机制

- **F→V→F 链式收敛**: Fixed(固定规则) → Variable(可变参数) → Fixed(收敛后升级为固定)
- **PHRP 五级渐进细化**: 逐层细化直到可执行
- **六步闭环**: 每轮推演形成完整闭环，反馈驱动下一轮

---

## 4. 推演引擎实现 (deduction_runner.py)

### 4.1 核心执行流程

推演引擎将每个计划分为 **5个阶段** 顺序执行:

| 阶段 | Phase | 使用模型 | 说明 |
|------|-------|---------|------|
| 1 | decompose | GLM-5 | 问题分解为子问题 |
| 2 | analyze | GLM-5 | 深度分析+规律映射 |
| 3 | implement | GLM-5 | 实现方案+代码生成 |
| 4 | validate | Ollama本地 | 幻觉校验+结果验证 |
| 5 | report | GLM-5 Turbo | 报告生成+拓展方向 |

### 4.2 模型调用架构 (君臣佐使)

```
call_model(prompt, model_preference)
  ├── "ollama_local" → call_ollama() → Ollama 14B (君 Emperor: 幻觉校验)
  ├── "glm5"         → call_zhipu()  → GLM-5 (臣 Minister: 深度推理)
  ├── "glm5_turbo"   → call_zhipu()  → GLM-5 Turbo (快臣: 快速推演)
  └── "glm47"        → call_zhipu()  → GLM-4.7 (佐 Assistant: 快速编码)
```

- **API**: 智谱 AI (zhipuai SDK)
- **Ollama 本地模型**: 通过 HTTP 调用 `http://localhost:11434/api/generate`
- **超时**: GLM-5 300s, Ollama 60s
- **Fallback**: GLM-5 失败 → 降级 GLM-5 Turbo → 降级 GLM-4.7

### 4.3 结构化输出标记

推演过程中使用以下标记提取结构化信息:

| 标记 | 含义 | 正则提取 |
|------|------|---------|
| `[NODE]` | 新发现的认知节点 | `\[NODE\]\s*(.+?)(?:\n\|$)` |
| `[RELATION]` | 节点间关系 | `\[RELATION\]\s*(.+?)(?:\n\|$)` |
| `[EXPAND]` | 拓展推演方向 | `\[EXPAND\]\s*(.+?)(?:\n\|$)` |
| `[BLOCKED]` | 阻塞问题 | `\[BLOCKED\]\s*(.+?)(?:\n\|$)` |

### 4.4 问题质量过滤

`is_valid_problem(text)` 函数过滤以下无效问题:
- Shell 提示符垃圾 (匹配 `SHELL_PROMPT_GARBAGE` 正则)
- 过短文本 (< 6字符)
- 代码片段 (`{self.`, 模板字面量, 不匹配括号)
- `classify_problem()` 对有效问题进行智能分类

### 4.5 自动拓展

report 阶段自动提取 `[EXPAND]` 标记，生成新推演计划插入队列:
- 队列设置支持: 优先项目、问题优先、最大拓展数
- 新计划继承父计划的 ULDS 规律和超越策略

---

## 5. 推演数据库 (deduction_db.py)

### 5.1 核心表结构

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `projects` | 项目管理 | id, name, description, status, progress |
| `deduction_plans` | 推演计划 | id, project_id, title, priority, status, ulds_laws, model_preference |
| `deduction_steps` | 推演步骤 | plan_id, step_number, phase, prompt, response, model_used, tokens_used |
| `deduction_results` | 推演结果 | plan_id, result_type, content, truth_level, tests_passed |
| `deduction_reports` | 推演报告 | plan_id, project_id, report_type, title, metrics |
| `blocked_problems` | 阻塞问题 | id, plan_id, title, severity, status, suggested_solution |
| `deduction_nodes` | 认知节点 | plan_id, step_number, node_type, content, confidence |
| `queue_settings` | 队列配置 | priority_project, auto_expand, deduction_order |
| `model_configs` | 模型配置 | model_id, display_name, enabled, rate_limit |
| `workflows` | 工作流 | id, name, project_id, steps_json, status |
| `crm_users` | CRM用户 | id, name, role |
| `task_feedback` | 任务反馈 | task_id, user_id, feedback_type |

### 5.2 Shell 安全检查

`check_shell_safety(cmd)` 函数阻止危险命令:
- 黑名单: `rm -rf`, `mkfs`, `dd if=`, `chmod 777`, `curl | sh` 等
- 返回 `(safe: bool, reason: str)`

---

## 6. 8大超越策略

| 编号 | 策略 | 说明 |
|------|------|------|
| S1 | 规律约束注入 | 将 L1-L11 硬编码注入 System Prompt |
| S2 | 技能库锚定 | 6000+ SKILL 库提供具体能力 |
| S3 | 王朝治理 | 借鉴历史人物高光的圆桌决策 |
| S4 | 四向碰撞 | 自上而下+自下而上+左右重叠+固化 |
| S5 | 5级真实性 | L1-L5 节点真实性分级体系 |
| S6 | 并行推理 | 多线程并行 GLM-5 调用 |
| S7 | 零回避扫描 | 不隐藏任何风险 |
| S8 | 链式收敛 | F→V→F 参数收敛机制 |

---

## 7. 自身局限声明

1. **ULDS不是万能的** — 没有领域 Skill 只给出空框架
2. **十一大规律可能不完备** — 保留 L12+ 拓展性
3. **清晰度95%≠正确** — 清晰地走向错误方向最危险
4. **ULDS本身受 L9(递归风险) 和 L11(模型≠现实) 约束**

---

## 8. 集成方式

| 组件 | 集成方式 |
|------|---------|
| `diepre_reasoning_engine` | SYSTEM_PROMPT + `call_glm5_claude_mode` 已注入十一大规律摘要 |
| `ooda_controller` | P0 最高优先级加载 + `SkillLoader.call()` 自动注入 |
| `pcm_router` | `core-framework` 类别 + 全意图关键词匹配 |

---

## 9. 关联性标签

```yaml
system_id: ulds_v2.1
category: core-framework
priority: P0
relates_to:
  - system: 本地模型自成长框架
    relation: ULDS为自成长引擎提供推演方法论; growth_engine的四向碰撞(top_down/bottom_up/horizontal/falsify)是ULDS六步闭环的实例化
    shared_concepts: [F→V→F链式收敛, 证伪机制, 节点真实性, 规律约束注入]
  - system: 可视化CRM系统
    relation: CRM的推演列表(deduction页面)直接管理ULDS推演计划; deduction_runner.py执行推演后通过--export导出到CRM
    shared_concepts: [推演计划, ULDS规律标注(L1-L11), 超越策略(S1-S8), 阻塞问题]
  - system: DiePre推演引擎
    relation: ULDS v2.1从DiePre项目抽象而来; diepre_reasoning_engine.py的SYSTEM_PROMPT注入十一大规律
    shared_concepts: [F→V→F约束传播, 工艺管线, 零回避]
tags:
  - universal-laws
  - deduction-framework
  - constraint-propagation
  - fixed-variable-chain
  - eleven-laws
  - P0-meta-skill
  - reasoning-pipeline
  - shell-safety
  - node-extraction
  - auto-expand
```

---

## 10. 成长方向

| 方向 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| **L12+ 规律拓展** | 11大规律, 保留拓展口 | 识别并纳入新规律 (如博弈论/网络效应) | 中 |
| **推演自动化率提升** | ~90% [CODE] | 95%+ 全自动推演, 减少 [HUMAN] 标注 | 高 |
| **多模型推演协同** | 5阶段固定分配模型 | 按问题复杂度动态路由模型 | 高 |
| **推演质量评估** | truth_level 二值 (L0/L1) | 接入5级真实性分级 (与自成长框架对齐) | 高 |
| **跨项目推演复用** | 每计划独立推演 | 推演结果跨项目复用, 共享节点池 | 中 |
| **ULDS自我证伪** | 自身局限声明 (静态) | 每N轮自动对ULDS框架本身进行L11证伪检查 | 低 |
| **领域Skill自动加载** | 手动关联 | 根据推演主题自动匹配并加载领域SKILL | 高 |

---

## 源文件清单

| 文件 | 说明 |
|------|------|
| `workspace/skills/ulds_v2_九大规律推演框架.meta.json` | 框架元数据 (版本、规律列表、管线、集成) |
| `deduction_runner.py` | 推演引擎主程序 (模型调用、阶段执行、问题提取、节点提取) |
| `deduction_db.py` | 推演数据库 (表结构、CRUD、Shell安全、初始化) |
