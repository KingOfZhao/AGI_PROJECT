---
name: expert-identity-adapter
version: 1.0.0
author: KingOfZhao
description: 专家身份适配器 —— 将expert-identity框架动态加载到任何Agent，自动识别领域+加载维度+配置人机闭环
tags: [cognition, meta-skill, expert, identity, adapter, dynamic, configuration, 12-domains]
license: MIT
homepage: https://github.com/KingOfZhao/AGI_PROJECT
---

# Expert Identity Adapter

## 元数据
| 字段 | 值 |
|------|-----|
| 名称 | expert-identity-adapter |
| 版本 | 1.0.0 |
| 作者 | KingOfZhao |
| 发布日期 | 2026-03-31 |
| 置信度 | 96% |

## 来源碰撞
```
universal-occupation-adapter (职业适配)
        ⊗
expert-identity (12领域×12维度)
        ⊗
memory-hierarchy-system (记忆加载)
        ⊗
workflow-orchestrator (流程编排)
        ↓
expert-identity-adapter
```

## 四向碰撞

**正面**: universal-occupation-adapter解决"适配一个职业"，expert-identity-adapter解决"适配任意领域组合"。一个任务可能同时涉及商业+工业+金融(如DiePre投资决策)，需要同时加载3个领域的维度。

**反面**: 不能一次性加载全部12个领域(太多context、太多噪音)。需要智能识别当前任务涉及哪些领域，只加载相关维度。

**侧面**: 领域识别可以基于任务描述的关键词匹配+历史上下文。例如提到"估值"→加载金融D1，提到"±0.15mm"→加载工业D1。

**整体**: 这是Skill工厂的**最终元层**——它让任何Agent在任何时刻都能自动识别自己需要什么领域知识、加载什么维度、遵守什么红线。

## 核心能力

### 1. 领域自动识别

```python
def identify_domains(task_description: str, context: list) -> list[str]:
    """
    基于任务描述和上下文自动识别涉及的领域
    
    关键词→领域映射:
    "估值/ROI/投资" → 金融
    "±0.xmm/精度/产线" → 工业
    "假设/实验/p值" → 科研
    "合同/合规/GDPR" → 法律
    "诊断/临床/患者" → 医疗
    "UI/UX/设计系统" → 艺术
    "部署/CI/CD/测试" → 代码
    ...
    
    返回: 按相关性排序的领域列表(最多3个主领域)
    """
```

### 2. 维度动态加载

```python
def load_dimensions(domains: list[str], task_type: str) -> dict:
    """
    根据领域和任务类型加载需要的维度
    
    任务类型 → 需要的维度:
    "决策"  → D1(已知) + D2(未知) + D3(验证) + D5(红线) + D7(决策) + D10(跨域)
    "验证"  → D3(验证) + D5(红线) + D8(失败模式)
    "学习"  → D1(已知) + D4(记忆) + D9(人机闭环) + D12(成长)
    "创造"  → D1(已知) + D2(未知) + D6(工具) + D10(跨域) + D11(趋势)
    "执行"  → D5(红线) + D6(工具) + D8(失败模式) + D9(人机闭环)
    """
```

### 3. 跨领域融合触发

```python
def check_fusion_trigger(domains: list[str]) -> FusionRecommendation | None:
    """
    如果当前任务涉及≥2个领域，检查是否有对应的融合Skill
    
    例如:
    domains = ["商业", "工业"] → 推荐加载 business-industry-fusion
    domains = ["科研", "代码"] → 推荐加载 ai4science-bridge
    domains = ["金融", "代码"] → 推荐加载 fincode-quant-engine
    domains = ["商业", "金融"] → 推荐生成新Skill(待完成)
    """
```

## 覆盖的顶级领域和子维度

```
直接覆盖: 全部12个领域
直接覆盖: 全部12个子维度
间接覆盖: 全部74对跨领域融合方向

这是当前覆盖范围最广的Skill。
```

## 工作流集成

```
任务开始
  ↓
expert-identity-adapter.identify_domains(task)
  ↓
加载领域维度 (D1/D2/D3/D5/D7/D10等)
  ↓
check_fusion_trigger() → 如有融合Skill则加载
  ↓
执行任务 (SOUL四向碰撞 + 领域知识)
  ↓
输出结果 + 标注使用到的领域和维度
  ↓
memory_hierarchy_system.remember(本次经验)
```

## 安装
```bash
clawhub install expert-identity-adapter
```

## 与其他Skill的关系

```
expert-identity-adapter (本Skill: 最终元层)
  ├── 读取 expert-identity.md (144节点定义)
  ├── 触发 multi-domain-fusion-engine (融合Skill生成)
  ├── 调用 universal-occupation-adapter (职业适配)
  ├── 使用 memory-hierarchy-system (维度缓存)
  └── 集成 workflow-orchestrator (流程编排)
```

## 学术参考
1. [A Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046) — Agent自适应
2. [SAGE: Multi-Agent Self-Evolution](https://arxiv.org/abs/2603.15255) — 多角色切换
3. [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) — 动态记忆加载
4. [Beyond RAG for Agent Memory](https://arxiv.org/abs/2602.02007) — 上下文感知检索
