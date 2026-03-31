# researcher-cognition: 让 AI 用科学家的方式读论文、做研究

## 痛点

AI 读论文时，大多数人只能得到：
> "这篇论文提出了方法 X，在基准 Y 上达到了精度 Z"

这不是研究，这是搬运。

真正的科研需要：
- 这篇论文能复现吗？实验设置完整吗？
- 局限性在哪里？有没有更好的方向？
- Appendix 里有没有被低估的方法？
- 这个方向的趋势如何？我该跟进吗？

## 核心能力

### 文献碰撞四向推理

对每篇论文从 4 个方向碰撞：

```
正面碰撞 → 核心方法能否直接复现/迁移？
反面对撞 → 局限性是否正是你的机会？
侧面碰撞 → Appendix/消融实验中有没有隐藏宝藏？
整体碰撞 → 预示什么趋势？你该怎么布局？
```

### 假设全生命周期管理

```
提出假设 → 设计实验 → 收集数据 → 分析验证 → 结论 → 记录
    ↑                                              |
    └──────────── 已证伪假设同样有价值 ←───────────────┘
```

### 结构化研究记忆

```
literature_review/{topic}/
  known.md          — 已确认的事实（附引用）
  unknown.md        — 未解决的问题
  hypotheses.md     — 假设清单（每个标注验证状态）

experiments/{exp_id}/
  hypothesis.md     — 被验证的假设
  setup.md          — 实验设置（可复现性核心）
  data/             — 原始数据
  analysis.md       — 统计检验
  conclusion.md     — 结论 + 置信度
```

### 6 条科研红线

```
🔴 不伪造/篡改数据
🔴 不选择性报告结果（cherry-picking）
🔴 不忽略矛盾数据（矛盾 = 最有价值的信息）
🔴 不复制原文不标注引用
🔴 不在置信度 < 80% 时发布结论
🔴 不声称"已验证"实际未验证的结论
```

## 与 arxiv-collision-cognition 的区别

| | arxiv-collision-cognition | researcher-cognition |
|--|--------------------------|---------------------|
| 定位 | 通用论文碰撞工具 | 科研人员完整认知框架 |
| 输入 | 单篇论文 + 项目上下文 | 整个研究过程 |
| 输出 | 可操作洞见列表 | 结构化研究记忆 |
| 假设管理 | ❌ | ✅ 全生命周期 |
| 实验记录 | ❌ | ✅ 可复现记录 |

## 快速安装

```bash
clawhub install researcher-cognition
```

---

*开源认知 Skill by KingOfZhao*
*GitHub: https://github.com/KingOfZhao/AGI_PROJECT/tree/main/skills/researcher-cognition*
*安装: `clawhub install researcher-cognition`*
