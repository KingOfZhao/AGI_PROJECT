# 我开源了 ai-growth-engine：让 AI Agent 用数字证明自己在变好

## 你有没有遇到过这个问题？

你的 AI Agent 每天做很多事——写代码、读论文、回答问题——但你不知道它是不是真的在"变好"。

就像一个人每天上班，但从不复盘：任务完成率多少？哪些错误反复出现？这周比上周强在哪？

没有度量，就没有成长。

## PDCA 和 OODA 为什么不够？

你可能听说过 PDCA（计划-执行-检查-改进）和 OODA Loop（观察-判断-决策-行动）。它们都是经典的管理/决策循环。

但它们都不是为 AI 设计的：

| | PDCA | OODA | **RAPVL** |
|--|------|------|-----------|
| 步骤数 | 4 | 4 | **5** |
| 模式提取 | ❌ | ❌ | ✅ 从失败中提取模式 |
| 文件记忆 | ❌ | ❌ | ✅ 永久持久化 |
| 度量化 | 弱 | ❌ | ✅ Growth Score 精确度量 |
| AI 自进化 | ❌ | ❌ | ✅ 元进化机制 |

**RAPVL** 是我为 AI Agent 设计的五步成长循环：

- **R**eview 回顾：审视最近 N 次行动
- **A**nalyze 提取模式：从成功和失败中找到规律
- **P**lan 调参：基于模式制定改进计划
- **V**erify 验证：用数字证明改进有效
- **L**earn 记录：写入文件，永不遗忘

## 这个 Skill 有什么不同？

**1. Growth Score™ — 成长有数字证明**

```python
# 程序员示例
Round 1: 10个任务, 7个成功 (70%)
Round 2: 10个任务, 8个成功 (80%)
Growth Score = (0.80 - 0.70) × 复杂度权重 = +6%

# 不是"感觉变好了"，是数字证明 +6%
```

**2. 6 个职业开箱即用**

程序员、科研人员、设计师、企业家、教师、医生——每个职业的度量指标不同，但成长引擎相同。

**3. 停滞自动触发深度反思**

连续 3 轮 Growth Score = 0 → 自动进入"根因分析"模式，找出成长瓶颈。

## 未来趋势

AI Agent 的"自我成长能力"将成为区分好 Agent 和普通 Agent 的核心指标。

2026 年 arXiv 上关于 Self-Evolving Agents 的论文数量同比增长 340%。

现在是让 Agent 学会自我成长的最佳时机。

## 快速开始

```bash
clawhub install ai-growth-engine
```

安装后，你的 OpenClaw Agent 就会自动用 RAPVL 循环监控自己的成长。

## 这个 Skill 适合谁？

- **OpenClaw 用户**：让 Agent 自动成长
- **AI 开发者**：给 Agent 加入自进化能力
- **研究者**：研究 AI 自我改进的方法论

---

*开源认知 Skill by KingOfZhao*
*GitHub: https://github.com/KingOfZhao/AGI_PROJECT/tree/main/skills/ai-growth-engine*
*安装: `clawhub install ai-growth-engine`*
