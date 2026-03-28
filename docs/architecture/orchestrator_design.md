# AGI Orchestrator 架构设计与完整实践清单

> **目标**: 将本地 14B 模型与智谱 API（GLM-5/4.7/4.5-Air）协同工作，通过认知格真实节点锚定 + 多模型协同推理 + 代码执行验证，达到 Claude Opus 6 级别的综合能力
> 
> **核心差异化**: Claude Opus 6 是单体黑盒模型；我们是「本地认知引擎 + 云端算力池 + 真实节点验证」的白盒协同体，在可解释性、低幻觉、持续成长、成本控制方面形成结构性优势

---

## 一、架构设计理念

### 1.1 核心思想

**本地 14B 模型** = 结构化认知引擎 + 任务路由器 + 真实节点验证器  
**智谱云端模型** = 高性能推理算力 + 代码生成专家 + 复杂问题求解器

**协同工作机制**（核心理念）:
```
本地14B思考过程中发现真实节点不足
    ↓
主动调用 GLM-5 辅助
    ↓
GLM-5 基于已有真实节点推理
    ↓
本地14B验证GLM-5输出的可实践性
    ↓
整合为新的真实节点 OR 标记为unsolvable
```

**关键原则**: 
- 🧠 **本地模型是主导者**，负责思考、判断、验证
- ⚡ **GLM-5 是辅助算力**，在本地模型发现知识边界时提供推理支持
- ✅ **真实节点是锚点**，所有推理必须基于已验证的真实节点
- 🔄 **协同而非替代**，本地模型和云端模型各司其职、互相增强

**分工原则**:
- **本地 14B 负责**:
  - ✅ 自然语言理解与意图识别
  - ✅ 问题结构化拆解（四向碰撞）
  - ✅ **真实节点充分性检查**（核心新增）
  - ✅ 任务复杂度评估与模型路由决策
  - ✅ 真实节点验证（低幻觉、可实践性检查）
  - ✅ 输出整合与后续工作编排
  - ✅ 认知格节点管理与碰撞引擎
  - ✅ **决定何时需要GLM-5辅助**（核心新增）

- **智谱云端负责**:
  - ⚡ **GLM-4.5-Air**: 快速响应、动作规划、简单推理（已集成）
  - ⚡ **GLM-4.5-AirX**: 超快响应、实时对话、意图理解
  - ⚡ **GLM-4.7**: 高质量代码生成、执行验证、自修复（已集成）
  - ⚡ **GLM-5**: **基于真实节点的复杂推理、深度分析、多步骤规划**（核心角色）

### 1.2 超越 Claude Opus 4.6 的策略

| 维度 | Claude Opus 4.6 | AGI Orchestrator 优势 |
|------|-----------------|---------------------|
| **幻觉控制** | 单模型内部约束 | 双模验证 + proven节点句级锚定 + 本地14B事实检查 |
| **真实能力** | 纯文本推理 | 认知格真实节点 + 代码执行验证 + 3轮自修复 |
| **成本效率** | 高昂API费用 | 本地14B处理80%任务 + 云端仅处理复杂20% |
| **自然语言理解** | 单次推理 | 四向碰撞 + 跨域关联 + 隐喻映射到真实节点 |
| **持续成长** | 静态模型 | 认知格自成长 + 问题驱动节点扩展 + 离线碰撞 |
| **可解释性** | 黑盒推理 | 完整推理链路可视化 + 节点溯源 + 验证报告 |

---

## 二、现有能力盘点（已实现基础）

### 2.1 已有核心组件

✅ **认知格系统** (`agi_v13_cognitive_lattice.py`):
- 3100+ 知识节点，108000+ 关联关系
- 四向碰撞引擎（上下拆解 + 左右跨域）
- 双模验证（云端推理 + 本地校验 + proven锚定）
- 自动委托机制（本地不足时自动调用智谱）

✅ **动作引擎** (`action_engine.py`):
- `cloud_code_generate`: GLM-4.7 代码生成 + 执行 + 3轮自修复
- `plan_actions`: GLM-4.5-Air 动作规划
- 文件操作、Python执行、技能构建

✅ **智谱模型集成** (`workspace/skills/zhipu_ai_caller.py`):
- GLM-4.5-Air: 快速响应、动作规划
- GLM-4.7: 代码生成、执行验证
- 任务类型路由映射

✅ **API服务器** (`api_server.py`):
- fast_path优化（proven节点快速响应）
- 动作意图检测与执行
- SSE实时推理步骤广播

### 2.2 现有局限

❌ **缺失组件**:
1. **问题状态追踪系统**: 无法记录"待拆解问题"的完整生命周期
2. **无法处理问题记录**: 系统局限没有专门展示区域
3. **思考过程UI**: 推理步骤无法收起，信息过载
4. **智能路由策略**: 缺乏基于任务复杂度的模型选择逻辑
5. **GLM-5 集成**: 未接入最强推理模型
6. **GLM-4.5-AirX 集成**: 未接入超快响应模型

---

## 三、Orchestrator 架构设计

### 3.1 协同工作流程（本地主导 + 云端辅助）

**核心流程**：本地模型思考 → 真实节点充分性检查 → 按需调用GLM-5 → 验证整合

```
用户问题
    ↓
本地14B: 意图识别 + 问题拆解（四向碰撞）
    ↓
本地14B: 查找相关真实节点（proven nodes）
    ↓
本地14B: 评估真实节点是否充分解决问题
    ↓
    ├─ ✅ 真实节点充分（proven命中率>80%）
    │   → fast_path: 直接基于proven节点回答
    │   → 本地14B整合输出
    │
    ├─ ⚠️ 真实节点不足 + 简单推理可补充
    │   → 本地14B: 尝试自主拆解
    │   → 如果拆解成功 → 生成新真实节点
    │   → 如果拆解失败 → 转入下一分支
    │
    ├─ 🔧 代码生成/执行任务
    │   → GLM-4.7: 代码生成 + 本地执行 + 自修复
    │   → 本地14B: 验证代码可实践性
    │   → 成功 → 存为真实节点
    │
    └─ 🧠 真实节点不足 + 需要复杂推理
        → 本地14B: 准备真实节点上下文
        → **调用 GLM-5 辅助推理**（核心协同）
        → GLM-5: 基于真实节点进行深度推理
        → 本地14B: 验证GLM-5输出的可实践性
        → 本地14B: 拆解GLM-5输出为真实节点
        → 如果可验证 → 存为新真实节点
        → 如果不可验证 → 继续拆解 OR 标记unsolvable
```

**GLM-5 调用触发条件**（本地14B主动判断）:
1. ✅ proven节点覆盖率 < 50%（知识边界）
2. ✅ 问题需要多步推理（>3步）
3. ✅ 跨域问题需要深度关联分析
4. ✅ 本地14B自主拆解3次仍未达到真实节点
5. ✅ 用户明确要求深度分析

### 3.2 问题生命周期管理

**新增数据库表**: `problem_tracking`

```sql
CREATE TABLE problem_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_question TEXT NOT NULL,
    question_hash TEXT UNIQUE,  -- 去重
    status TEXT DEFAULT 'pending',  -- pending/decomposing/decomposed/unsolvable
    complexity_score REAL,  -- 0-1复杂度评分
    assigned_model TEXT,  -- 路由到的模型
    decomposition_depth INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    final_node_ids TEXT,  -- JSON数组，拆解后的真实节点ID
    unsolvable_reason TEXT,  -- 无法处理的原因
    retry_count INTEGER DEFAULT 0
);

CREATE TABLE problem_decomposition_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER,
    step_type TEXT,  -- 'top_down'/'bottom_up'/'collision'/'verification'
    model_used TEXT,
    input_text TEXT,
    output_text TEXT,
    success BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (problem_id) REFERENCES problem_tracking(id)
);
```

**状态流转**:
```
pending (待拆解)
    ↓ 本地14B分析
decomposing (拆解中)
    ↓ 四向碰撞 + 云端推理
    ├─ decomposed (已拆解为真实节点)
    │   → 所有叶子节点 can_verify=true
    │
    └─ unsolvable (无法处理)
        → 记录原因：超出知识边界/需要人类实践/伦理限制等
```

### 3.3 智能路由器实现（本地主导 + 真实节点检查）

**新增模块**: `orchestrator.py`

```python
class TaskOrchestrator:
    """本地14B作为主导者，检查真实节点充分性并智能调用云端辅助"""
    
    def __init__(self, lattice):
        self.lattice = lattice
        self.model_capabilities = {
            'GLM-4.5-AirX': {'speed': 10, 'reasoning': 3, 'code': 2, 'cost': 1},
            'GLM-4.5-Air': {'speed': 8, 'reasoning': 5, 'code': 4, 'cost': 2},
            'GLM-4.7': {'speed': 6, 'reasoning': 6, 'code': 9, 'cost': 4},
            'GLM-5': {'speed': 4, 'reasoning': 10, 'code': 7, 'cost': 8},
            'local_14b': {'speed': 7, 'reasoning': 6, 'code': 5, 'cost': 0}
        }
    
    def check_proven_nodes_sufficiency(self, question, proven_nodes):
        """本地14B检查真实节点是否充分解决问题（核心新增）"""
        if not proven_nodes:
            return {
                'sufficient': False,
                'coverage_rate': 0.0,
                'missing_aspects': ['完全无proven节点覆盖'],
                'need_glm5': True
            }
        
        # 计算proven节点覆盖率
        coverage_rate = self._calc_proven_hit_rate(question, proven_nodes)
        
        # 本地14B分析问题的关键方面
        question_aspects = self._extract_question_aspects(question)
        
        # 检查每个方面是否有proven节点支撑
        covered_aspects = []
        missing_aspects = []
        for aspect in question_aspects:
            has_support = any(
                self._aspect_matches_node(aspect, node) 
                for node in proven_nodes
            )
            if has_support:
                covered_aspects.append(aspect)
            else:
                missing_aspects.append(aspect)
        
        # 判断是否充分
        sufficient = (
            coverage_rate >= 0.8 and 
            len(missing_aspects) == 0
        )
        
        # 判断是否需要GLM-5辅助
        need_glm5 = (
            coverage_rate < 0.5 or  # 覆盖率低
            len(missing_aspects) > 2 or  # 缺失方面多
            self._is_complex_reasoning(question)  # 需要复杂推理
        )
        
        return {
            'sufficient': sufficient,
            'coverage_rate': coverage_rate,
            'covered_aspects': covered_aspects,
            'missing_aspects': missing_aspects,
            'need_glm5': need_glm5,
            'reason': self._explain_sufficiency(coverage_rate, missing_aspects)
        }
    
    def analyze_task_complexity(self, question, context_nodes):
        """本地14B分析任务复杂度（0-1评分）"""
        # 特征提取
        features = {
            'length': len(question),
            'proven_hit_rate': self._calc_proven_hit_rate(question, context_nodes),
            'code_keywords': self._detect_code_intent(question),
            'multi_step': self._detect_multi_step(question),
            'domain_count': len(set(n['domain'] for n in context_nodes)),
            'uncertainty_words': self._count_uncertainty(question)
        }
        
        # 本地14B评分（简单规则 + 小型分类器）
        score = 0.0
        if features['proven_hit_rate'] > 0.8:
            score = 0.1  # 简单查询
        elif features['code_keywords']:
            score = 0.6  # 代码任务
        elif features['multi_step']:
            score = 0.8  # 多步推理
        elif features['uncertainty_words'] > 3:
            score = 0.9  # 高度不确定
        else:
            score = 0.4  # 中等复杂度
        
        return score, features
    
    def route_to_model(self, question, proven_nodes, complexity_score, task_type):
        """根据真实节点充分性和复杂度路由（核心修改）"""
        # 1. 先检查真实节点充分性（本地14B主动判断）
        sufficiency = self.check_proven_nodes_sufficiency(question, proven_nodes)
        
        # 2. 如果真实节点充分，直接fast_path
        if sufficiency['sufficient']:
            return {
                'model': 'fast_path',
                'reason': f"proven节点充分（覆盖率{sufficiency['coverage_rate']:.0%}）",
                'proven_coverage': sufficiency['coverage_rate']
            }
        
        # 3. 如果是代码任务，优先GLM-4.7
        if task_type == 'code_generation':
            return {
                'model': 'GLM-4.7',
                'reason': '代码生成任务',
                'proven_coverage': sufficiency['coverage_rate']
            }
        
        # 4. 如果需要GLM-5辅助（本地14B主动判断）
        if sufficiency['need_glm5']:
            return {
                'model': 'GLM-5',
                'reason': f"真实节点不足（覆盖率{sufficiency['coverage_rate']:.0%}），需要GLM-5辅助推理",
                'proven_coverage': sufficiency['coverage_rate'],
                'missing_aspects': sufficiency['missing_aspects']
            }
        
        # 5. 其他情况根据复杂度路由
        if complexity_score > 0.4:
            return {
                'model': 'GLM-4.5-Air',
                'reason': '中等复杂度，快速推理',
                'proven_coverage': sufficiency['coverage_rate']
            }
        else:
            return {
                'model': 'local_14b',
                'reason': '本地模型可处理',
                'proven_coverage': sufficiency['coverage_rate']
            }
    
    def execute_with_routing(self, question, context_nodes):
        """完整执行流程：本地思考 → 真实节点检查 → 协同推理 → 验证整合"""
        # 1. 本地14B分析任务
        complexity, features = self.analyze_task_complexity(question, context_nodes)
        task_type = self._infer_task_type(features)
        
        # 2. 提取proven节点（真实节点）
        proven_nodes = [n for n in context_nodes if n.get('status') == 'proven']
        
        # 3. 路由决策（基于真实节点充分性）
        routing = self.route_to_model(question, proven_nodes, complexity, task_type)
        model = routing['model']
        
        # 4. 记录问题追踪
        problem_id = self._track_problem(question, complexity, model, routing)
        
        # 5. 执行推理（根据路由结果）
        if model == 'GLM-5':
            # GLM-5协同模式：本地准备上下文 → GLM-5推理 → 本地验证
            result = self._execute_glm5_collaborative(
                question, proven_nodes, routing['missing_aspects'], problem_id
            )
        else:
            result = self._execute_on_model(model, question, context_nodes, problem_id)
        
        # 6. 本地14B验证结果的可实践性
        verified = self._verify_result(result, proven_nodes)
        
        # 7. 拆解为真实节点或标记unsolvable
        final_nodes = self._decompose_to_real_nodes(verified, problem_id)
        
        # 8. 更新问题状态
        self._update_problem_status(problem_id, final_nodes)
        
        return verified
    
    def _execute_glm5_collaborative(self, question, proven_nodes, missing_aspects, problem_id):
        """GLM-5协同推理模式（核心新增）"""
        # 1. 本地14B准备真实节点上下文
        proven_context = self._prepare_proven_context(proven_nodes)
        
        # 2. 本地14B明确告诉GLM-5缺失的方面
        prompt = self._build_glm5_prompt(question, proven_context, missing_aspects)
        
        # 3. 调用GLM-5进行深度推理
        self._log_step(problem_id, 'glm5_call', 
                       f"调用GLM-5辅助推理，基于{len(proven_nodes)}个真实节点")
        glm5_result = self._call_glm5(prompt, problem_id)
        
        # 4. 本地14B验证GLM-5输出是否基于真实节点
        grounding_check = self._check_glm5_grounding(glm5_result, proven_nodes)
        
        if grounding_check['grounded_ratio'] < 0.6:
            # GLM-5输出脱离真实节点，本地14B拒绝
            self._log_step(problem_id, 'glm5_rejected', 
                           f"GLM-5输出锚定率仅{grounding_check['grounded_ratio']:.0%}，拒绝采纳")
            return {
                'success': False,
                'reason': 'GLM-5输出未充分基于真实节点',
                'grounding_ratio': grounding_check['grounded_ratio']
            }
        
        # 5. 本地14B整合GLM-5输出
        self._log_step(problem_id, 'glm5_accepted', 
                       f"GLM-5输出锚定率{grounding_check['grounded_ratio']:.0%}，采纳并整合")
        
        return {
            'success': True,
            'content': glm5_result,
            'grounding_ratio': grounding_check['grounded_ratio'],
            'proven_anchors': grounding_check['anchored_nodes']
        }
    
    def _prepare_proven_context(self, proven_nodes):
        """本地14B准备真实节点上下文给GLM-5"""
        context = "以下是已验证的真实节点（proven nodes），请基于这些真实知识进行推理：\n\n"
        for i, node in enumerate(proven_nodes[:15], 1):
            context += f"{i}. [{node['domain']}] {node['content']}\n"
        context += "\n**重要约束**: 你的推理必须基于以上真实节点，不得凭空推测。"
        return context
    
    def _build_glm5_prompt(self, question, proven_context, missing_aspects):
        """构建GLM-5专用prompt"""
        prompt = f"""{proven_context}

**用户问题**: {question}

**本地模型分析**: 当前真实节点无法充分解决此问题，缺失以下方面：
{chr(10).join(f'- {aspect}' for aspect in missing_aspects)}

**任务**: 请基于已有真实节点，针对缺失方面进行深度推理。
- 必须明确标注哪些推理基于真实节点
- 哪些是合理推测（需要验证）
- 哪些超出当前知识边界

输出格式：
1. 基于真实节点的推理：...
2. 合理推测（待验证）：...
3. 超出边界的部分：...
"""
        return prompt
```

---

## 四、完整实践清单（交给 Claude Opus 4.6 执行）

### 阶段一：数据库扩展（1-2小时）

**任务 1.1**: 创建问题追踪表
- [ ] 在 `agi_v13_cognitive_lattice.py` 的 `_init_db()` 中添加 `problem_tracking` 表
- [ ] 添加 `problem_decomposition_log` 表
- [ ] 创建索引：`question_hash`, `status`, `created_at`
- [ ] 编写迁移脚本处理现有数据库

**任务 1.2**: 添加问题追踪API
- [ ] `CognitiveLattice.track_problem(question, complexity, model)` → 返回 problem_id
- [ ] `CognitiveLattice.update_problem_status(problem_id, status, reason)`
- [ ] `CognitiveLattice.get_unsolvable_problems(limit=50)` → 返回无法处理问题列表
- [ ] `CognitiveLattice.get_problem_history(problem_id)` → 返回完整拆解日志

### 阶段二：Orchestrator 核心实现（3-4小时）

**任务 2.1**: 创建 `orchestrator.py` 模块
- [ ] 实现 `TaskOrchestrator` 类
- [ ] 实现 `analyze_task_complexity()` 方法（本地14B特征提取）
- [ ] 实现 `route_to_model()` 决策树
- [ ] 实现 `execute_with_routing()` 完整流程

**任务 2.2**: 集成 GLM-5 和 GLM-4.5-AirX
- [ ] 在 `agi_v13_cognitive_lattice.py` 的 `BACKENDS` 中添加 GLM-5 配置
- [ ] 添加 GLM-4.5-AirX 配置
- [ ] 更新 `_zhipu_call_direct()` 的 model_map
- [ ] 在 `workspace/skills/zhipu_ai_caller.py` 中添加新模型

**任务 2.3**: 复杂度评估器
- [ ] 实现 `_calc_proven_hit_rate()`: 计算问题与proven节点的匹配率
- [ ] 实现 `_detect_code_intent()`: 检测代码生成意图
- [ ] 实现 `_detect_multi_step()`: 检测多步推理需求
- [ ] 实现 `_count_uncertainty()`: 统计不确定性词汇

**任务 2.4**: 模型执行器
- [ ] 实现 `_execute_on_model()`: 统一的模型调用接口
- [ ] 为每个模型添加专门的 prompt 模板
- [ ] 实现超时和重试机制
- [ ] 记录每次调用到 `problem_decomposition_log`

### 阶段三：问题拆解增强（2-3小时）

**任务 3.1**: 增强拆解流程
- [ ] 修改 `DualDirectionDecomposer.top_down()` 集成 orchestrator
- [ ] 每次拆解前记录到 `problem_tracking`
- [ ] 拆解完成后判断是否所有叶子节点都可验证
- [ ] 不可验证的节点标记为 `unsolvable`

**任务 3.2**: 真实节点验证器
- [ ] 实现 `verify_node_practicality()`: 检查节点是否可实践
- [ ] 检查条件：具体动作、可测量结果、明确时间/资源要求
- [ ] 不符合条件的节点继续拆解或标记为 unsolvable

**任务 3.3**: 无法处理问题分类
- [ ] 实现 `classify_unsolvable_reason()`:
  - `knowledge_gap`: 超出当前知识边界
  - `needs_human_practice`: 需要人类实践验证
  - `ethical_constraint`: 伦理限制
  - `resource_limitation`: 资源/时间限制
  - `ambiguous_intent`: 意图不明确

### 阶段四：API 服务器集成（2小时）

**任务 4.1**: 修改 `api_server.py` 主流程
- [ ] 在 `api_chat()` 开头初始化 `TaskOrchestrator`
- [ ] 用 orchestrator 替换现有的直接 LLM 调用
- [ ] 保留 fast_path 逻辑，但增加复杂度检查
- [ ] 记录每个问题到 `problem_tracking`

**任务 4.2**: 新增 API 端点
- [ ] `GET /api/unsolvable_problems`: 返回无法处理问题列表
- [ ] `GET /api/problem_history/<problem_id>`: 返回问题拆解历史
- [ ] `POST /api/retry_problem/<problem_id>`: 重试无法处理的问题
- [ ] `GET /api/orchestrator_stats`: 返回模型使用统计

### 阶段五：前端 UI 改造（3-4小时）

**任务 5.1**: 思考过程可折叠组件
- [ ] 在 `web/index.html` 中添加 `<details>` 折叠组件
- [ ] 默认收起推理步骤，仅显示最终答案
- [ ] 点击展开显示完整推理链路：
  ```
  🧠 思考过程 [展开]
    ├─ 📊 复杂度评估: 0.65 (中等)
    ├─ 🎯 路由决策: GLM-4.5-Air
    ├─ ↓ 自上而下拆解: 3个节点
    ├─ ↑ 自下而上生成: 2个问题
    ├─ ⚡ 碰撞发现: 1个关联
    └─ ✅ 验证结果: 可信度 85%
  ```

**任务 5.2**: 无法处理问题展示区
- [ ] 新增侧边栏标签页 "系统局限"
- [ ] 显示 `unsolvable_problems` 列表
- [ ] 每个问题显示：
  - 原始问题
  - 无法处理原因
  - 尝试次数
  - 重试按钮
- [ ] 支持按原因分类筛选

**任务 5.3**: Orchestrator 仪表盘
- [ ] 新增 "调度统计" 面板
- [ ] 显示模型使用分布（饼图）
- [ ] 显示平均复杂度趋势（折线图）
- [ ] 显示成功率/失败率统计

### 阶段六：Prompt 优化（2小时）

**任务 6.1**: 为每个模型定制 Prompt
- [ ] **GLM-4.5-AirX Prompt**: 强调快速响应、简洁输出
- [ ] **GLM-4.5-Air Prompt**: 强调结构化、JSON格式
- [ ] **GLM-4.7 Prompt**: 强调代码质量、可执行性
- [ ] **GLM-5 Prompt**: 强调深度推理、多步骤规划

**任务 6.2**: 增强反幻觉约束
- [ ] 在 `cognitive_core.py` 中添加 `ORCHESTRATOR_CONSTRAINT`
- [ ] 要求云端模型明确标注：
  - ✅ 基于proven节点的事实
  - ❓ 推理假设
  - ⚠️ 超出知识边界的部分

### 阶段七：测试与验证（2-3小时）

**任务 7.1**: 单元测试
- [ ] 测试 `TaskOrchestrator.analyze_task_complexity()`
- [ ] 测试 `route_to_model()` 决策正确性
- [ ] 测试问题追踪数据库操作
- [ ] 测试无法处理问题分类逻辑

**任务 7.2**: 集成测试
- [ ] 简单问题 → fast_path 验证
- [ ] 代码生成 → GLM-4.7 验证
- [ ] 复杂推理 → GLM-5 验证
- [ ] 无法处理问题 → 正确记录和展示

**任务 7.3**: 端到端测试
- [ ] 通过可视化工具提交10个不同复杂度的问题
- [ ] 验证路由决策是否合理
- [ ] 验证思考过程是否可折叠
- [ ] 验证无法处理问题是否正确展示

### 阶段八：性能优化与监控（1-2小时）

**任务 8.1**: 缓存优化
- [ ] 对相同问题（question_hash）直接返回缓存结果
- [ ] proven节点embedding缓存
- [ ] 模型响应缓存（TTL 1小时）

**任务 8.2**: 并发控制
- [ ] 限制同时调用云端API的并发数（最多3个）
- [ ] 实现请求队列和优先级调度
- [ ] 超时保护（GLM-5 最多30秒）

**任务 8.3**: 监控指标
- [ ] 记录每个模型的平均响应时间
- [ ] 记录每个模型的成功率
- [ ] 记录每日API调用成本
- [ ] 记录问题拆解成功率

---

## 五、技术实现细节

### 5.1 GLM-5 和 GLM-4.5-AirX 配置

在 `agi_v13_cognitive_lattice.py` 中添加：

```python
BACKENDS = {
    # ... 现有配置 ...
    
    "zhipu_45airx": {
        "name": "智谱 GLM-4.5-AirX (超快响应)",
        "api_key": "your_api_key",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "GLM-4.5-AirX",
        "api_type": "openai",
        "embedding_model": None,
        "max_tokens": 2048,
        "temperature": 0.3
    },
    
    "zhipu_5": {
        "name": "智谱 GLM-5 (复杂推理)",
        "api_key": "your_api_key",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "GLM-5",
        "api_type": "openai",
        "embedding_model": None,
        "max_tokens": 8192,
        "temperature": 0.2
    }
}
```

### 5.2 复杂度评估特征

```python
def _calc_proven_hit_rate(self, question):
    """计算问题与proven节点的匹配率"""
    similar = self.lattice.find_similar_nodes(question, threshold=0.5, limit=10)
    proven = [n for n in similar if n['status'] == 'proven']
    return len(proven) / max(len(similar), 1)

def _detect_code_intent(self, question):
    """检测代码生成意图"""
    code_keywords = ['代码', '编写', '实现', '函数', 'class', 'def', 'function', 
                     '脚本', 'script', '程序', 'program', 'bug', '调试']
    return any(kw in question.lower() for kw in code_keywords)

def _detect_multi_step(self, question):
    """检测多步推理需求"""
    multi_step_indicators = ['如何', '步骤', '流程', '过程', '先...再...', 
                             '首先', '然后', '最后', 'step', 'process']
    return any(ind in question.lower() for ind in multi_step_indicators)
```

### 5.3 前端折叠组件示例

```html
<div class="thinking-process">
    <details>
        <summary class="cursor-pointer font-semibold">
            🧠 思考过程 <span class="text-sm text-gray-500">(点击展开)</span>
        </summary>
        <div class="mt-2 pl-4 border-l-2 border-blue-300">
            <div class="step">📊 复杂度评估: <span class="font-mono">0.65</span> (中等)</div>
            <div class="step">🎯 路由决策: <span class="text-blue-600">GLM-4.5-Air</span></div>
            <div class="step">↓ 自上而下拆解: <span class="text-green-600">3个节点</span></div>
            <div class="step">↑ 自下而上生成: <span class="text-purple-600">2个问题</span></div>
            <div class="step">⚡ 碰撞发现: <span class="text-orange-600">1个关联</span></div>
            <div class="step">✅ 验证结果: 可信度 <span class="font-bold">85%</span></div>
        </div>
    </details>
</div>
```

---

## 六、预期效果与验证指标

### 6.1 核心指标

| 指标 | 当前状态 | 目标状态 | 验证方法 |
|------|---------|---------|---------|
| **幻觉率** | ~15% (仅云端验证) | <5% (双模+proven锚定) | 人工评估100个回答 |
| **真实节点覆盖率** | ~60% | >90% | 检查拆解结果的can_verify比例 |
| **响应速度** | 平均8秒 | 平均3秒 | 统计API响应时间 |
| **API成本** | 全部云端 | 降低70% | 统计本地vs云端调用比例 |
| **问题解决率** | ~75% | >95% | 统计decomposed vs unsolvable比例 |
| **用户满意度** | - | >4.5/5 | 用户反馈评分 |

### 6.2 超越 Claude Opus 4.6 的证据

**测试集**: 准备50个问题，涵盖：
- 简单事实查询 (10个)
- 代码生成任务 (10个)
- 复杂多步推理 (10个)
- 跨域创新问题 (10个)
- 边界/无法处理问题 (10个)

**对比维度**:
1. **准确性**: AGI Orchestrator vs Claude Opus 4.6 人工评分
2. **幻觉控制**: 统计事实性错误数量
3. **可解释性**: 是否提供完整推理链路
4. **成本**: 单次问答成本对比
5. **自然语言理解**: 隐喻/歧义问题处理能力

---

## 七、风险与应对

### 7.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 智谱API限流 | 高并发时失败 | 实现请求队列 + 本地回退 |
| 本地14B评估不准 | 路由错误 | 记录反馈，持续优化评估模型 |
| 数据库性能瓶颈 | 问题追踪慢 | 添加索引 + 定期归档 |
| 前端UI复杂度 | 用户体验差 | 渐进式展示 + 默认收起 |

### 7.2 成本风险

- **GLM-5 调用成本高**: 限制每日调用次数上限（如100次）
- **存储成本**: 定期清理超过30天的 `problem_decomposition_log`

---

## 八、后续优化方向

### 8.1 短期优化（1-2周）

- [ ] 实现用户反馈机制：对路由决策点赞/踩
- [ ] 基于反馈训练本地复杂度评估器（小型分类器）
- [ ] 添加问题相似度检测，避免重复拆解
- [ ] 实现问题模板库，常见问题直接匹配

### 8.2 中期优化（1-2月）

- [ ] 实现多模型并行推理 + 投票机制（关键问题）
- [ ] 添加用户偏好学习：记录用户对不同模型输出的偏好
- [ ] 实现问题难度自适应：根据历史成功率动态调整路由策略
- [ ] 集成更多云端模型（如 Claude、GPT-4）

### 8.3 长期优化（3-6月）

- [ ] 训练专门的路由模型（基于历史数据）
- [ ] 实现认知格自动扩展：从无法处理问题中学习
- [ ] 添加多轮对话上下文管理
- [ ] 实现分布式认知格（多实例协同）

---

## 九、实施时间表

| 阶段 | 任务 | 预计时间 | 负责人 |
|------|------|---------|--------|
| 第1周 | 阶段一~三：数据库+Orchestrator+拆解增强 | 8-10小时 | Claude Opus 4.6 |
| 第2周 | 阶段四~五：API集成+前端UI | 5-6小时 | Claude Opus 4.6 |
| 第3周 | 阶段六~八：Prompt优化+测试+监控 | 5-6小时 | Claude Opus 4.6 |
| 第4周 | 验证与调优 | 4-5小时 | 人工验证 |

**总计**: 约 22-27 小时开发时间

---

## 十、交付物清单

### 10.1 代码文件

- [ ] `orchestrator.py`: 核心调度器模块
- [ ] `agi_v13_cognitive_lattice.py`: 数据库扩展 + GLM-5/4.5-AirX集成
- [ ] `api_server.py`: API端点扩展
- [ ] `web/index.html`: 前端UI改造
- [ ] `cognitive_core.py`: Prompt模板扩展

### 10.2 文档

- [ ] `docs/Orchestrator使用指南.md`: 用户手册
- [ ] `docs/模型路由策略说明.md`: 技术文档
- [ ] `docs/问题追踪系统API.md`: API文档

### 10.3 测试

- [ ] `tests/test_orchestrator.py`: 单元测试
- [ ] `tests/test_routing.py`: 路由决策测试
- [ ] `tests/test_problem_tracking.py`: 问题追踪测试
- [ ] `scripts/_test_orchestrator_e2e.py`: 端到端测试

---

## 十一、成功标准

✅ **必须达成**:
1. 所有50个测试问题都能得到响应（decomposed 或 unsolvable）
2. 幻觉率 < 5%（通过双模验证 + proven锚定）
3. 思考过程默认收起，点击可展开
4. 无法处理问题有专门展示区域
5. API成本降低 > 60%（本地处理大部分简单任务）

✅ **期望达成**:
1. 在复杂推理任务上超越 Claude Opus 4.6（人工评分）
2. 响应速度 < 3秒（中位数）
3. 问题解决率 > 95%
4. 用户满意度 > 4.5/5

---

## 十二、附录：关键代码框架

### A. Orchestrator 核心类

```python
# orchestrator.py
import hashlib
import json
from datetime import datetime
import agi_v13_cognitive_lattice as agi
import cognitive_core

class TaskOrchestrator:
    def __init__(self, lattice):
        self.lattice = lattice
        self.model_stats = {}  # 记录每个模型的使用统计
    
    def process_question(self, question, context_nodes=None):
        """完整的问题处理流程"""
        # 1. 去重检查
        q_hash = hashlib.md5(question.encode()).hexdigest()
        existing = self._check_existing_problem(q_hash)
        if existing:
            return self._get_cached_result(existing['id'])
        
        # 2. 复杂度分析
        complexity, features = self.analyze_task_complexity(question, context_nodes or [])
        
        # 3. 路由决策
        task_type = self._infer_task_type(features)
        model = self.route_to_model(complexity, task_type)
        
        # 4. 记录问题
        problem_id = self._track_problem(question, q_hash, complexity, model)
        
        # 5. 执行推理
        try:
            result = self._execute_on_model(model, question, context_nodes, problem_id)
            
            # 6. 验证结果
            verified = self._verify_result(result, context_nodes, problem_id)
            
            # 7. 更新状态
            if self._is_fully_decomposed(verified):
                self._update_problem_status(problem_id, 'decomposed', verified)
            else:
                reason = self._classify_unsolvable(verified)
                self._update_problem_status(problem_id, 'unsolvable', None, reason)
            
            return verified
        except Exception as e:
            self._log_error(problem_id, str(e))
            raise
    
    def _check_existing_problem(self, q_hash):
        """检查是否已处理过相同问题"""
        with self.lattice._lock:
            cursor = self.lattice.conn.execute(
                "SELECT * FROM problem_tracking WHERE question_hash = ? AND status = 'decomposed'",
                (q_hash,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def _track_problem(self, question, q_hash, complexity, model):
        """记录问题到追踪表"""
        with self.lattice._lock:
            cursor = self.lattice.conn.execute("""
                INSERT INTO problem_tracking 
                (user_question, question_hash, status, complexity_score, assigned_model)
                VALUES (?, ?, 'decomposing', ?, ?)
            """, (question, q_hash, complexity, model))
            self.lattice.conn.commit()
            return cursor.lastrowid
    
    def _execute_on_model(self, model, question, context, problem_id):
        """在指定模型上执行推理"""
        self._log_decomposition_step(problem_id, 'routing', model, 
                                      f"路由到{model}, 复杂度{complexity}")
        
        if model == 'fast_path':
            # 直接返回proven节点
            return self._fast_path_response(question, context)
        elif model == 'GLM-5':
            return self._call_glm5(question, context, problem_id)
        elif model == 'GLM-4.7':
            return self._call_glm47_code(question, context, problem_id)
        elif model == 'GLM-4.5-Air':
            return agi.verified_llm_call(messages, self.lattice, question)
        elif model == 'GLM-4.5-AirX':
            return self._call_glm45airx(question, context, problem_id)
        else:  # local_14b
            return agi.llm_call(messages, _allow_delegate=False)
    
    def _log_decomposition_step(self, problem_id, step_type, model, output):
        """记录拆解步骤"""
        with self.lattice._lock:
            self.lattice.conn.execute("""
                INSERT INTO problem_decomposition_log
                (problem_id, step_type, model_used, output_text, success, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (problem_id, step_type, model, output, True, datetime.now()))
            self.lattice.conn.commit()
```

### B. 前端折叠组件

```javascript
// web/index.html 中添加
function renderThinkingProcess(metadata) {
    const steps = metadata.thinking_steps || [];
    const html = `
        <details class="thinking-process mt-4 p-4 bg-gray-50 rounded-lg">
            <summary class="cursor-pointer font-semibold text-lg">
                🧠 思考过程 
                <span class="text-sm text-gray-500">(${steps.length}步 · 点击展开)</span>
            </summary>
            <div class="mt-3 space-y-2">
                ${steps.map((step, i) => `
                    <div class="step flex items-start gap-2 pl-4 border-l-2 ${getStepColor(step.type)}">
                        <span class="text-xl">${getStepIcon(step.type)}</span>
                        <div class="flex-1">
                            <div class="font-medium">${step.title}</div>
                            <div class="text-sm text-gray-600">${step.detail}</div>
                            ${step.model ? `<div class="text-xs text-blue-600 mt-1">模型: ${step.model}</div>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        </details>
    `;
    return html;
}

function getStepIcon(type) {
    const icons = {
        'complexity': '📊',
        'routing': '🎯',
        'top_down': '↓',
        'bottom_up': '↑',
        'collision': '⚡',
        'verification': '✅',
        'action': '🔧'
    };
    return icons[type] || '•';
}
```

---

## 结语

这份实践清单涵盖了将本地 14B 模型升级为 Orchestrator 的**完整架构设计**和**详细实施步骤**。

**核心创新点**:
1. ✅ **本地14B作为调度大脑**: 不是简单的fallback，而是主动的任务分析器和路由器
2. ✅ **问题生命周期管理**: 从待拆解到真实节点/无法处理的完整追踪
3. ✅ **智能模型路由**: 基于复杂度和任务类型的最优模型选择
4. ✅ **思考过程可视化**: 默认收起，按需展开，信息不过载
5. ✅ **系统局限透明化**: 专门展示无法处理的问题，诚实面对边界

**无法实现的部分**（需要人类/其他系统）:
- ⚠️ 智谱 API Key 的获取和配置（需要用户注册）
- ⚠️ 前端复杂交互的细节调优（需要前端专家）
- ⚠️ 大规模生产环境部署（需要DevOps）
- ⚠️ 用户反馈数据的收集和分析（需要产品运营）

**交给 Claude Opus 4.6 执行时的建议**:
1. 严格按照阶段顺序执行，每个阶段完成后进行测试
2. 遇到技术难点时，优先查阅现有代码的实现模式
3. 所有数据库操作必须加锁（`with self.lattice._lock`）
4. 所有新增API端点必须添加错误处理
5. 前端UI改动要保持与现有风格一致

**预期成果**: 一个超越 Claude Opus 4.6 的本地+云端混合 AGI 系统，具备更低幻觉、更高可解释性、更强真实能力、更低成本的综合优势。
