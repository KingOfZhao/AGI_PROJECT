# 本地模型自成长框架 — AI 可读文档

> **生成时间**: 2026-03  
> **用途**: 供 AI 系统快速理解本项目的自成长引擎全貌（含 DiePre 框架增强）  
> **源文件索引**: 见文末「源文件清单」

---

## 1. 框架概述

**AGI 全速成长引擎 v7.0** 是一个自动化认知网络构建系统，通过多轮「四向碰撞」推演持续产生新的认知节点和可执行 SKILL，实现 AI 的自我进化。

- **核心循环**: 四向碰撞 → 证伪 → SKILL 生成 → 校验 → 可视化
- **模型协作**: 君臣佐使体系 (Ollama 14B / GLM-5 / GLM-4.7 / GLM-4.5)
- **DiePre 增强**: 从 DiePre AI 项目提炼 9 大核心模式，增强自成长能力
- **并行架构**: 8-16 并发 GLM-5 调用，每轮 ~75 次 API 调用，~600K tokens

---

## 2. 核心认知哲学

```
AGI = 结构化认知网络 + 人机共生 + 持续碰撞
```

### 四向碰撞模型

| 方向 | 说明 | 对应 Phase |
|------|------|-----------|
| 自上而下 | 从大问题拆解为可证伪子问题 | `_top_down()` |
| 自下而上 | 从已有节点归纳抽象新概念 | `_bottom_up()` |
| 左右重叠 | 跨域碰撞发现结构同构 | `_horizontal_overlap()` |
| 固化 | 通过证伪幸存的节点固化为真实能力 | `_falsify()` + `_convert()` |

### 节点真实性 5 级体系

| 级别 | 名称 | 定义 | 示例 |
|------|------|------|------|
| L1 | 本体真实 | 国际标准/物理定律/编程语言规范/广泛应用算法/开源组件API | ISO标准, PEP规范, RSA算法 |
| L2 | 关系真实 | 链式依赖验证/跨域碰撞/标准映射/设计模式实例化 | 所有前置节点均为L1+, ≥2领域验证 |
| L3 | 能力真实 | 代码可执行/链式调用/工程部署/性能达标/人类实践反馈 | 测试通过, 端到端验证, 竞赛评测通过 |
| L4 | 共识真实 | 开源广泛使用/行业最佳实践/学术引用/教育收录 | GitHub 10K+ stars, 多平台验证 |
| L5 | 进化真实 | 参数收敛σ<0.01/≥5轮证伪幸存/版本迭代核心保留 | 跨代验证有效 |

> 所有节点（含假设/已证伪）均存入数据库。真实性可升可降。

---

## 3. 成长引擎核心循环

### 3.1 串行模式 `run()`

每轮执行 9 个 Phase:

```
Phase 1: 自上而下 (_top_down)         → 8-15个可证伪子问题
Phase 2: 自下而上 (_bottom_up)         → 5-8个归纳模式
Phase 3: 左右重叠 (_horizontal_overlap) → 4-8个跨域重叠 (每轮2对域)
Phase 4: 深度关系推演 (_deep_reasoning) → 涌现能力+知识缺口+关系图谱
Phase 4.5: 代码维度推演 (_code_domain_growth) → 95维代码能力提升
Phase 5: 证伪 (_falsify)              → 过滤假节点, 保留proven
Phase 6: SKILL转换 (_convert)          → 代码生成 + PCM知识保存
Phase 7: 校验 (_validate)             → 元数据完整性检查
Phase 8: 可视化 (_visualize)           → 更新 web/data/
Phase 9: 依赖检查 (_dep_check)         → 每5个SKILL检查一次
```

### 3.2 并行模式 `run_parallel()` (v7.0)

使用 `ThreadPoolExecutor` + `ParallelGLM5Caller` 并行执行:

```
Stage 1: 问题分解+知识加载 (并行)
  ├── 4个 top_down 问题 (parallel)
  └── 2个 bottom_up 归纳 (parallel)

Stage 2: 碰撞推演+代码维度 (并行)
  ├── 6个 horizontal_overlap 碰撞 (parallel)
  ├── 2个 deep_reasoning 推演 (parallel)
  └── 5组 code_domain 维度 (parallel)

Stage 3: 并行证伪 + 双轨分类 + 真实性分级
  ├── _falsify_parallel() → 所有候选节点同时证伪
  ├── DualTrackClassifier → 固定/可变/假设/废弃
  └── NodeTruthClassifier → L0-L5 五级分级

Stage 4: 并行SKILL转换 + 零回避扫描
  ├── _convert_parallel() → 并行代码生成
  ├── ComputeOptimizer.should_generate_skill() → 过滤低价值节点
  └── ZeroAvoidanceScanner.scan_skill() → 风险扫描

Stage 5: 验证 + 可视化

Stage 6: 成长记录 + 收敛报告
  ├── GrowthSessionRecorder.record_session()
  ├── RSS置信度合成
  └── 每5轮输出收敛报告
```

---

## 4. DiePre 框架 9 大增强模式

源文件: `core/diepre_growth_framework.py`

### 模式 1: 固定/可变双轨分类 (`DualTrackClassifier`)

- **原理**: 82项固定规则(物理定律/行业标准) + 46项可变参数(经验值)
- **分类逻辑**:
  - `confidence ≥ 0.90` 且 `verify_count ≥ 3` → `fixed_rule`
  - `confidence ≥ 0.60` → `variable_param`
  - `confidence ≥ 0.50` → `hypothesis`
  - 低于 0.50 → `deprecated`
- **升级路径**: `variable → fixed` (当 σ_sliding < 0.05)

### 模式 2: 参数收敛追踪器 (`ConvergenceTracker`)

- **原理**: 维护每个参数历史值列表，计算滑动标准差 σ
- **状态判定**:
  - σ < 0.05 → `converged` (已收敛)
  - σ > 0.30 → `high_volatility` (高波动，需更多数据)
  - 其他 → `converging` (收敛中)
- **窗口大小**: 10

### 模式 3: 零回避风险扫描 (`ZeroAvoidanceScanner`)

- **原理**: 不可说"一般不会出问题"，推演时不可隐藏风险
- **12类代码灾难模板**: CD01-CD12 (边界遗漏/并发竞态/内存泄漏/类型不匹配/依赖冲突/异常吞没/注入攻击/API超时/硬编码/复杂度爆炸/状态不一致/精度丢失)
- `scan_skill(code, meta)` → 规则扫描返回风险列表
- `generate_failure_modes(name, desc)` → 基于描述生成潜在失败模式

### 模式 4: 6阶段管线门控 (`PipelineStageGate`)

AGI 映射自 DiePre 的 6 阶段工艺管线:

| Stage | 名称 | 门控指标 | 最低阈值 |
|-------|------|---------|---------|
| 1 | 问题分解 | sub_questions_count | 1 |
| 2 | 知识加载 | context_nodes_count | 0 |
| 3 | 多Phase推演 | raw_nodes_count | 1 |
| 4 | SKILL生成 | skills_generated | 0 |
| 5 | 验证校验 | validation_rate | 0.3 |
| 6 | 成长记录 | recorded | 1 |

每个 Stage 有入口条件和出口质量门，不达标则阻断。

### 模式 5: RSS置信度合成 (`RSSConfidenceComposer`)

- **原理**: `e_total = √(Σeᵢ²)` — 多源误差的 RSS 堆叠
- **Phase 权重**:
  - `code_domain`: 0.95 (最高，可执行验证)
  - `falsify`: 1.0 (通过证伪最可靠)
  - `bottom_up`: 0.9
  - `deep_reasoning`: 0.85
  - `top_down`: 0.8
  - `horizontal`: 0.7 (创新性高但风险也高)
- `contribution_analysis()` 返回各 Phase 贡献度排序

### 模式 6: 成长会话记录器 (`GrowthSessionRecorder`)

- 每轮记录: 固定/可变节点数、SKILL数、风险数、tokens、耗时
- **灾难知识进化** (3阶段确认):
  - 1次发现 → `suspected` (疑似)
  - 2次复现 → `confirmed` (确认入库)
  - 5次数据 → `fully_quantified` (完全量化)
- 每10次验证自动生成成长报告
- 数据库表: `growth_sessions`, `disaster_knowledge`, `convergence_history`

### 模式 7: 节点真实性分级器 (`NodeTruthClassifier`)

- 实现5级真实性分类（见第2节表格）
- L1检查: 关键词匹配 (ISO/ECMA/PEP/RFC/定律/定理/算法名等)
- L2检查: 链式依赖全真实 + 跨域验证 ≥ 2 + 层级继承
- L3检查: test_passed / chain_call_verified / deploy_verified / benchmark / human_verified
- L4检查: usage_count ≥ 10000 / in_textbook / multi_platform ≥ 3
- L5检查: σ < 0.01 + verify ≥ 10 / falsify_survived ≥ 5 / version ≥ 3

### 模式 8: 链式调用追踪器 (`ChainLinkTracker`)

- 记录节点间有向链式调用关系
- 表: `node_chains` (chain_id, from_node_id, to_node_id, call_type, verified)
- `get_chain_context(node_id)` → 返回链式依赖列表 (用于真实性L2/L3判定)
- `discover_components(min_chain_length)` → 从调用链自动发现可复用组件

### 模式 9: 算力智能调优器 (`ComputeOptimizer`)

- 按真实性级别分配 token 预算:
  - L0 hypothesis: 0.5x (4096)
  - L3 capability: 1.2x (9830) — 代码生成需要更多
  - L5 evolutionary: 0.3x (2457) — 极少维护验证
  - deprecated: 0x
- `should_generate_skill(node)` → 低真实性+低置信度跳过SKILL生成
- `update_phase_weights()` → 根据 RSS 贡献度动态调整 Phase 权重
- `adjust_concurrency()` → 根据延迟和错误率调整并发度 (2-16)

---

## 5. API 调用与限速

### 自适应限速器 (`AdaptiveRateLimiter`)

- 初始 QPS: 1.0, 最大: 5.0, 最小: 0.2
- 成功连续15次 → QPS × 1.15
- 每次 429 → QPS × 0.5^(连续429次数)
- 线程安全 (threading.Lock)

### GLM-5 调用函数

| 函数 | 用途 | 特点 |
|------|------|------|
| `call_glm5()` | 串行模式单次调用 | 150s超时, 3次429退避重试 |
| `call_glm5_throttled()` | 带自适应限速的调用 | 线程安全, 5次重试, 指数退避 |
| `ParallelGLM5Caller.submit_batch()` | 批量并行调用 | ThreadPoolExecutor, 8-16并发 |

---

## 6. 数据持久化

### SQLite 表

| 表 | 用途 |
|----|------|
| `proven_nodes` | 认知节点 (含 truth_level, verify_count, falsify_survived, chain_count) |
| `skills` | SKILL 技能 (名称, 文件路径, 元数据JSON, 验证分数) |
| `skill_dependencies` | SKILL 依赖关系 |
| `growth_log` | 成长日志 (轮次, 阶段, tokens, 耗时) |
| `collision_history` | 碰撞历史 (类型, 输入/输出节点, prompt/response) |
| `pcm` | 概念模型 (知识型节点, 非可执行) |
| `node_chains` | 链式调用关系 |
| `growth_sessions` | DiePre成长会话 |
| `disaster_knowledge` | 灾难知识库 |
| `convergence_history` | 收敛追踪历史 |

### 文件系统

- SKILL 代码: `workspace/skills/{name}.py`
- SKILL 元数据: `workspace/skills/{name}.meta.json`
- 推演日志: `data/growth_reasoning_log.jsonl`
- 可视化数据: `web/data/growth_report.json`

---

## 7. Prompt 模板一览

| Prompt | 输入 | 输出格式 |
|--------|------|---------|
| `TOPDOWN_PROMPT` | 大问题 + 系统状态 | `{"sub_questions": [...]}` |
| `BOTTOMUP_PROMPT` | 已有节点列表 | `{"patterns": [...]}` |
| `HORIZONTAL_PROMPT` | 两个领域的节点 | `{"overlaps": [...]}` |
| `FALSIFY_PROMPT` | 节点内容 + 置信度 | `{"can_be_falsified": bool, "adjusted_confidence": float}` |
| `SKILL_GEN_PROMPT` | 名称 + 描述 + 领域 | Python代码 (```python...```) |
| `CODE_DOMAIN_PROMPT` | 维度详情 + 系统状态 | `{"improvements": [...]}` |
| `DEEP_REASONING_PROMPT` | 节点列表 | `{"relationships": [...], "knowledge_gaps": [...], "emergent_capabilities": [...]}` |

---

## 8. 终止条件与检查点

- **终止**: `rnd >= min_rounds` 且 `有效节点数 >= 10 + rnd * 4`
- **检查点**: `save_checkpoint()` 每轮末尾保存
- **收敛报告**: 每5轮自动输出
- **最终报告**: `_final_report()` 汇总所有轮次

---

## 9. 关联性标签

```yaml
system_id: growth_engine_v7
category: self-growth
priority: P0
relates_to:
  - system: ULDS v2.1 推演框架
    relation: 自成长引擎的四向碰撞是ULDS六步闭环的实例化; TOPDOWN/BOTTOMUP/HORIZONTAL/FALSIFY四个Prompt体现ULDS的规律→推演→验证管线
    shared_concepts: [F→V→F链式收敛, 证伪机制, 规律约束(USER_AGI_PHILOSOPHY), 六步闭环]
  - system: 可视化CRM系统
    relation: CRM的model页面展示growth_engine的95维能力矩阵; CRM的skills页面展示growth_engine生成的SKILL库; web/data/growth_report.json由growth_engine写入
    shared_concepts: [SKILL技能库, 95维能力矩阵, 模型配置(君臣佐使), 进度追踪]
  - system: DiePre推演引擎
    relation: diepre_growth_framework.py的9大模式直接提炼自DiePre项目; DualTrackClassifier映射DiePre的82固定+46可变规则
    shared_concepts: [双轨分类, 收敛追踪, 零回避扫描, 管线门控, RSS合成, 灾难知识进化]
  - system: 推演引擎(deduction_runner)
    relation: 两者共享proven_nodes表和skills表; deduction_runner产生的节点可被growth_engine的证伪Phase复用
    shared_concepts: [proven_nodes数据库, SKILL元数据格式, 模型调用(call_zhipu/call_ollama)]
tags:
  - self-growth
  - four-direction-collision
  - parallel-inference
  - diepre-enhanced
  - node-truthfulness
  - chain-link-tracking
  - compute-optimization
  - dual-track-classification
  - convergence-tracking
  - zero-avoidance
  - skill-generation
  - adaptive-rate-limiting
```

---

## 10. 成长方向

| 方向 | 当前状态 | 目标 | 优先级 |
|------|---------|------|--------|
| **SWE-Bench 突破** | 35分 | 55分 (与GPT-5持平) | 高 |
| **95维均分提升** | 84.2 | 87+ (超越Opus 4) | 高 |
| **Agent自治能力** | 40分 | 70分 (自主工具使用+任务规划) | 高 |
| **多语言代码生成** | 60分 | 75分 (Rust/Go/Java全覆盖) | 中 |
| **L3能力真实节点占比** | 低 (多数L0/L1) | 30%+ 节点达到L3 (代码可执行验证) | 高 |
| **收敛率提升** | 收敛率未知 (初期) | 60%+ 参数域达到converged状态 | 中 |
| **SKILL有效率** | 64.5% | 80%+ (减少stub代码) | 高 |
| **灾难知识完全量化** | suspected为主 | 50%+ 灾难达到fully_quantified | 中 |
| **跨域迁移深度** | 表面相似匹配 | 深层结构同构发现 + 可执行融合SKILL | 中 |
| **算力优化** | 固定8并发 | 自适应2-16并发, API成本降30% | 低 |

---

## 源文件清单

| 文件 | 说明 |
|------|------|
| `core/growth_engine.py` (1440行) | 成长引擎主程序: GrowthEngine类, 串行/并行循环, 9个Phase, SKILL生成 |
| `core/diepre_growth_framework.py` (1149行) | DiePre 9大增强模式: 双轨分类/收敛追踪/零回避/管线门控/RSS合成/会话记录/真实性分级/链式追踪/算力调优 |
| `data/growth_reasoning_log.jsonl` | GLM-5 调用日志 (JSONL格式) |
| `web/data/growth_report.json` | 可视化报告数据 |
| `workspace/skills/*.py` + `*.meta.json` | 生成的SKILL代码和元数据 |
