---
name: fincode-quant-engine
version: 1.0.0
author: KingOfZhao
description: 金融×代码融合量化引擎 Skill —— 投资理论×算法交易×风险管理三领域融合，凯利公式+VaR+回测框架
tags: [cognition, finance, quant, trading, risk, algorithmic, investment]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# FinCode Quant Engine Skill

## 元数据
| 字段 | 值 |
|------|-----|
| 名称 | fincode-quant-engine |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
entrepreneur-cognition (决策框架)
        ⊗
programmer-cognition (代码工程)
        ⊗
expert-identity: 金融维度10(跨领域代码) × 代码维度10(跨领域金融)
        ⊗
researcher-cognition (统计验证)
        ↓
fincode-quant-engine
```

## 四向碰撞

**正面**: 量化金融的核心=金融理论(为什么)×代码实现(怎么做)×统计验证(对不对)三领域缺一不可
**反面**: 99%的回测过拟合——样本外验证是最低标准，walk-forward验证才是及格线
**侧面**: 行为金融学(科研心理学×金融决策偏差)可以解释为什么理性模型在真实市场失效
**整体**: AI量化交易的终局=金融信号×代码执行×AI风控×人类监督的四层架构

## 三层架构

```
L1 — 策略层(金融理论)
  因子模型 → 信号生成 → 组合优化 → 凯利仓位
  
L2 — 执行层(代码工程)
  数据管道 → 回测引擎 → 模拟交易 → 实盘接口
  
L3 — 风控层(风险管理)
  VaR/CVaR → 最大回撤控制 → 尾部风险 → 压力测试
```

## 核心公式

```python
# 凯利公式(仓位大小)
kelly_fraction = (win_prob * avg_win - loss_prob * avg_loss) / avg_win

# 风险调整收益
sharpe = (returns.mean() - risk_free) / returns.std()
sortino = (returns.mean() - risk_free) / downside_std()

# VaR(99%置信度)
var_99 = returns.quantile(0.01)

# 信息比率(vs基准)
ir = (portfolio_return - benchmark_return) / tracking_error
```

## 验证框架（SOUL适配）

```
金融验证 vs 科研验证:
  金融: 回测(含滑点/手续费) → 样本外验证 → Walk-Forward → 纸盘 → 小资金 → 全仓
  科研: 假设 → 实验 → 统计检验 → 可复现 → 同行评审
  
共同红线:
  🔴 不在样本内调参然后在样本外报告（过拟合）
  🔴 不忽略交易成本（滑点+手续费+冲击成本）
  🔴 不承诺收益（金融市场本质上是不确定系统）
  🔴 不使用未验证模型做实盘
  🔴 不隐瞒最大回撤
```

## 安装
```bash
clawhub install fincode-quant-engine
```

## 学术参考
1. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046)
2. [SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255) — 多Agent市场模拟
3. [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) — 市场记忆
