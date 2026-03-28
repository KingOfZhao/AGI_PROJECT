# AGI 全速成长系统 — 实践清单

**文档版本**: v1.0  
**创建时间**: 2026-03-21  
**目标**: 实现本地模型在 GLM-5 驱动下的全速自成长，通过四向碰撞机制持续产出真实节点并转化为可执行 SKILL

---

## 一、系统架构概览

### 核心理念映射

| 用户理念 | 系统实现 | 技术组件 |
|---------|---------|---------|
| 四向碰撞（上下左右） | 自上而下拆解 + 自下而上构建 + 左右寻找重叠 | `FourWayCollisionEngine` |
| 真实节点 | 经过实践验证的知识点/能力单元 | `ProvenNode` (type=proven) |
| 能力转换 | 节点 → SKILL/PCM 的结构化转换 | `NodeToSkillConverter` |
| 人机共生 | AI 推演 + 人类实践验证 | `HumanVerificationQueue` |
| 认知自洽 | 领域内可实践能力的完整闭环 | `DomainCoherenceValidator` |

### 系统拓扑

```
┌─────────────────────────────────────────────────────────────┐
│                    AGI 全速成长系统                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  任务一       │───▶│  任务二       │───▶│  任务三       │ │
│  │  节点获取     │    │  验证优化     │    │  循环控制     │ │
│  │  (GLM-5)     │    │  (质量检查)   │    │  (10+轮)     │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                    │         │
│         ▼                    ▼                    ▼         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            认知网络数据库 (memory.db)                 │  │
│  │  - proven_nodes (真实节点)                           │  │
│  │  - skills (能力库)                                   │  │
│  │  - skill_dependencies (依赖关系)                     │  │
│  │  - growth_log (成长日志)                             │  │
│  │  - collision_history (碰撞历史)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、任务一：GLM-5 驱动的真实节点获取系统

### 目标指标

| 指标 | 目标值 | 监控方式 |
|------|--------|---------|
| Tokens 消耗速率 | ≥ 100万/小时 | `TokenUsageMonitor` |
| 真实节点产出速率 | ≥ 10个/小时 | `NodeProductionRate` |
| 节点→SKILL转换率 | ≥ 60% | `ConversionRate` |
| 数据库写入预留 | 10% tokens | `DatabaseWriteBuffer` |

### 四向碰撞引擎设计

#### 1. 自上而下拆解（Top-Down Decomposition）

**输入**: 不可证伪的大问题（如"如何实现 AGI"）  
**过程**: GLM-5 递归拆解为可证伪的子问题  
**输出**: 问题树（每个叶子节点都是可实践的小问题）

**Prompt 模板**:
```python
TOPDOWN_PROMPT = """
你是 AGI 架构师，擅长将宏大问题拆解为可实践的小问题。

大问题: {big_question}

要求:
1. 识别该问题的核心假设
2. 将问题拆解为 5-10 个子问题
3. 每个子问题必须满足:
   - 可证伪（能通过实践验证真伪）
   - 边界清晰（有明确的输入输出）
   - 独立性强（不强依赖其他子问题）
4. 标注每个子问题的:
   - 难度等级 (1-5)
   - 预估验证成本 (小时)
   - 前置依赖 (如有)

输出 JSON:
{{
  "parent_question": "...",
  "assumptions": ["假设1", "假设2"],
  "sub_questions": [
    {{
      "id": "Q1",
      "question": "...",
      "falsifiable": true,
      "difficulty": 3,
      "estimated_hours": 8,
      "dependencies": []
    }}
  ]
}}
"""
```

#### 2. 自下而上构建（Bottom-Up Construction）

**输入**: 已验证的真实节点集合  
**过程**: GLM-5 发现节点间的关联模式，构建更高层次的抽象  
**输出**: 新的复合能力/理论模型

**Prompt 模板**:
```python
BOTTOMUP_PROMPT = """
你是 AGI 模式识别专家，擅长从已知节点中发现新的结构。

已知真实节点:
{proven_nodes_json}

要求:
1. 分析这些节点的共性和差异
2. 识别可能的组合模式（至少 3 种）
3. 为每种模式构建一个新的抽象概念
4. 预测该抽象概念的应用场景
5. 提出验证该抽象概念的实践方案

输出 JSON:
{{
  "patterns": [
    {{
      "pattern_id": "P1",
      "pattern_name": "...",
      "involved_nodes": ["node_id1", "node_id2"],
      "abstraction": "新的抽象概念描述",
      "use_cases": ["场景1", "场景2"],
      "validation_plan": "如何验证这个抽象概念"
    }}
  ],
  "new_questions": ["从这些模式中产生的新问题"]
}}
"""
```

#### 3. 左右寻找重叠（Horizontal Overlap Detection）

**输入**: 两个不同领域的节点集合  
**过程**: GLM-5 识别跨领域的相似性和可迁移性  
**输出**: 跨域映射关系 + 迁移学习机会

**Prompt 模板**:
```python
HORIZONTAL_PROMPT = """
你是 AGI 跨域迁移专家，擅长发现不同领域的相似结构。

领域 A 节点: {domain_a_nodes}
领域 B 节点: {domain_b_nodes}

要求:
1. 识别两个领域的结构相似性
2. 找出可迁移的模式（至少 3 个）
3. 为每个迁移机会评估:
   - 相似度 (0-1)
   - 迁移难度 (1-5)
   - 预期收益
4. 提出跨域融合的新能力

输出 JSON:
{{
  "overlaps": [
    {{
      "overlap_id": "O1",
      "pattern_in_a": "...",
      "pattern_in_b": "...",
      "similarity": 0.85,
      "transfer_difficulty": 2,
      "expected_benefit": "...",
      "fusion_capability": "融合后的新能力描述"
    }}
  ]
}}
"""
```

#### 4. 重叠部分构建（Overlap-Based Construction）

**输入**: 四向碰撞产生的重叠区域  
**过程**: GLM-5 将重叠部分固化为真实节点  
**输出**: 新的 ProvenNode（标记来源：collision）

### 节点→SKILL 转换规则

```python
NODE_TO_SKILL_RULES = {
    "可执行性": {
        "condition": "节点包含明确的输入输出和执行步骤",
        "action": "直接转换为 SKILL",
        "template": "opus_flutter_engineer.meta.json"
    },
    "知识性": {
        "condition": "节点是纯知识/概念，无直接执行逻辑",
        "action": "转换为 PCM (Proven Concept Module)",
        "template": "pcm_template.json"
    },
    "组合性": {
        "condition": "节点是多个子节点的组合",
        "action": "转换为 Composite SKILL（含依赖关系）",
        "template": "composite_skill_template.json"
    },
    "待验证性": {
        "condition": "节点尚未通过人类实践验证",
        "action": "加入 HumanVerificationQueue",
        "template": "verification_task_template.json"
    }
}
```

### 实现代码框架

```python
# /Users/administruter/Desktop/AGI_PROJECT/growth_engine.py

import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class FourWayCollisionEngine:
    """四向碰撞引擎"""
    
    def __init__(self, lattice, glm5_caller):
        self.lattice = lattice
        self.glm5 = glm5_caller
        self.token_usage = {"total": 0, "hourly": 0, "last_reset": time.time()}
        
    def top_down_decompose(self, big_question: str) -> List[Dict]:
        """自上而下拆解"""
        prompt = TOPDOWN_PROMPT.format(big_question=big_question)
        result = self.glm5.call(prompt, task_type="complex_reasoning")
        self._track_tokens(result.get("tokens_used", 0))
        return result.get("sub_questions", [])
    
    def bottom_up_construct(self, proven_nodes: List[Dict]) -> List[Dict]:
        """自下而上构建"""
        nodes_json = json.dumps(proven_nodes, ensure_ascii=False, indent=2)
        prompt = BOTTOMUP_PROMPT.format(proven_nodes_json=nodes_json)
        result = self.glm5.call(prompt, task_type="pattern_recognition")
        self._track_tokens(result.get("tokens_used", 0))
        return result.get("patterns", [])
    
    def horizontal_overlap(self, domain_a: List[Dict], domain_b: List[Dict]) -> List[Dict]:
        """左右寻找重叠"""
        prompt = HORIZONTAL_PROMPT.format(
            domain_a_nodes=json.dumps(domain_a, ensure_ascii=False),
            domain_b_nodes=json.dumps(domain_b, ensure_ascii=False)
        )
        result = self.glm5.call(prompt, task_type="cross_domain_transfer")
        self._track_tokens(result.get("tokens_used", 0))
        return result.get("overlaps", [])
    
    def construct_from_overlap(self, overlaps: List[Dict]) -> List[Dict]:
        """从重叠部分构建新节点"""
        new_nodes = []
        for overlap in overlaps:
            if overlap.get("similarity", 0) > 0.7:
                node = {
                    "content": overlap.get("fusion_capability", ""),
                    "type": "proven",
                    "source": "collision",
                    "collision_type": "horizontal_overlap",
                    "confidence": overlap.get("similarity", 0),
                    "metadata": overlap
                }
                new_nodes.append(node)
        return new_nodes
    
    def _track_tokens(self, tokens: int):
        """追踪 tokens 使用量"""
        self.token_usage["total"] += tokens
        self.token_usage["hourly"] += tokens
        
        # 每小时重置
        if time.time() - self.token_usage["last_reset"] > 3600:
            print(f"[TokenUsage] 过去1小时消耗: {self.token_usage['hourly']:,} tokens")
            self.token_usage["hourly"] = 0
            self.token_usage["last_reset"] = time.time()


class NodeToSkillConverter:
    """节点→SKILL 转换器"""
    
    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.skill_dir.mkdir(parents=True, exist_ok=True)
    
    def convert(self, node: Dict) -> Optional[Dict]:
        """转换节点为 SKILL"""
        # 判断节点类型
        if self._is_executable(node):
            return self._to_skill(node)
        elif self._is_knowledge(node):
            return self._to_pcm(node)
        elif self._is_composite(node):
            return self._to_composite_skill(node)
        else:
            return None
    
    def _is_executable(self, node: Dict) -> bool:
        """判断是否可执行"""
        content = node.get("content", "").lower()
        return any(kw in content for kw in ["实现", "生成", "执行", "调用", "处理"])
    
    def _is_knowledge(self, node: Dict) -> bool:
        """判断是否为知识"""
        content = node.get("content", "").lower()
        return any(kw in content for kw in ["概念", "定义", "原理", "理论", "知识"])
    
    def _is_composite(self, node: Dict) -> bool:
        """判断是否为组合"""
        return "sub_nodes" in node or "dependencies" in node
    
    def _to_skill(self, node: Dict) -> Dict:
        """转换为 SKILL"""
        skill_name = self._generate_skill_name(node)
        skill_meta = {
            "name": skill_name,
            "file": f"skills/{skill_name}.py",
            "description": node.get("content", ""),
            "tags": node.get("tags", []) + ["glm5_generated", "auto_growth"],
            "created_at": datetime.now().isoformat(),
            "forged_by": "growth_engine",
            "source_node_id": node.get("id", ""),
            "design_spec": {
                "name": skill_name,
                "display_name": node.get("content", "")[:50],
                "functions": [],  # 需要进一步解析
                "dependencies": node.get("dependencies", []),
                "estimated_lines": self._estimate_lines(node)
            }
        }
        return skill_meta
    
    def _to_pcm(self, node: Dict) -> Dict:
        """转换为 PCM (Proven Concept Module)"""
        return {
            "type": "pcm",
            "name": self._generate_skill_name(node),
            "concept": node.get("content", ""),
            "domain": node.get("domain", "general"),
            "confidence": node.get("confidence", 0.8),
            "references": node.get("references", [])
        }
    
    def _to_composite_skill(self, node: Dict) -> Dict:
        """转换为组合 SKILL"""
        skill = self._to_skill(node)
        skill["composite"] = True
        skill["sub_skills"] = node.get("sub_nodes", [])
        return skill
    
    def _generate_skill_name(self, node: Dict) -> str:
        """生成 SKILL 名称"""
        content = node.get("content", "")[:30]
        # 简单转换为 snake_case
        name = content.lower().replace(" ", "_").replace("，", "_")
        name = "".join(c if c.isalnum() or c == "_" else "" for c in name)
        return f"auto_{name}_{node.get('id', 'unknown')[:8]}"
    
    def _estimate_lines(self, node: Dict) -> int:
        """估算代码行数"""
        complexity = node.get("complexity", "medium")
        base_lines = {"low": 100, "medium": 300, "high": 800}
        return base_lines.get(complexity, 300)
```

---

## 三、任务二：成长验证与优化系统

### 验证流程

```
生成 SKILL → 模板校验 → 依赖检查 → 可视化接入 → 调用关系分析 → 人类验证队列
     ↓            ↓           ↓            ↓              ↓                ↓
  格式正确?    依赖完整?   UI可用?      关系清晰?      实践可行?        反馈优化
```

### SKILL 模板校验器

```python
class SkillTemplateValidator:
    """SKILL 模板校验器（基于 Claude Opus 4.6 标准）"""
    
    REQUIRED_FIELDS = [
        "name", "file", "description", "tags", "created_at", 
        "forged_by", "design_spec"
    ]
    
    DESIGN_SPEC_REQUIRED = [
        "name", "display_name", "functions", "dependencies"
    ]
    
    def validate(self, skill_meta: Dict) -> Dict:
        """校验 SKILL 元数据"""
        issues = []
        
        # 1. 必需字段检查
        for field in self.REQUIRED_FIELDS:
            if field not in skill_meta:
                issues.append(f"缺少必需字段: {field}")
        
        # 2. design_spec 检查
        if "design_spec" in skill_meta:
            spec = skill_meta["design_spec"]
            for field in self.DESIGN_SPEC_REQUIRED:
                if field not in spec:
                    issues.append(f"design_spec 缺少字段: {field}")
        
        # 3. functions 结构检查
        if "design_spec" in skill_meta and "functions" in skill_meta["design_spec"]:
            for func in skill_meta["design_spec"]["functions"]:
                if not all(k in func for k in ["name", "purpose", "params", "returns"]):
                    issues.append(f"函数 {func.get('name', '?')} 缺少必需字段")
        
        # 4. 文件路径检查
        if "file" in skill_meta:
            if not skill_meta["file"].startswith("skills/"):
                issues.append("file 路径应以 skills/ 开头")
            if not skill_meta["file"].endswith(".py"):
                issues.append("file 路径应以 .py 结尾")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "score": max(0, 100 - len(issues) * 10)
        }


class DependencyAnalyzer:
    """依赖关系分析器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.graph = {}  # skill_name -> [dependencies]
    
    def analyze_all_skills(self, skills: List[Dict]):
        """分析所有 SKILL 的依赖关系"""
        # 构建依赖图
        for skill in skills:
            name = skill.get("name", "")
            deps = skill.get("design_spec", {}).get("dependencies", [])
            self.graph[name] = deps
        
        # 检测循环依赖
        cycles = self._detect_cycles()
        
        # 计算依赖深度
        depths = self._calculate_depths()
        
        # 识别核心 SKILL（被依赖最多）
        core_skills = self._identify_core_skills()
        
        return {
            "total_skills": len(skills),
            "total_dependencies": sum(len(deps) for deps in self.graph.values()),
            "cycles": cycles,
            "max_depth": max(depths.values()) if depths else 0,
            "core_skills": core_skills,
            "isolated_skills": [s for s, deps in self.graph.items() if not deps]
        }
    
    def _detect_cycles(self) -> List[List[str]]:
        """检测循环依赖"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            if node in rec_stack:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:])
                return
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for dep in self.graph.get(node, []):
                dfs(dep, path[:])
            
            rec_stack.remove(node)
        
        for skill in self.graph:
            dfs(skill, [])
        
        return cycles
    
    def _calculate_depths(self) -> Dict[str, int]:
        """计算每个 SKILL 的依赖深度"""
        depths = {}
        
        def get_depth(skill):
            if skill in depths:
                return depths[skill]
            deps = self.graph.get(skill, [])
            if not deps:
                depths[skill] = 0
                return 0
            depths[skill] = 1 + max(get_depth(d) for d in deps)
            return depths[skill]
        
        for skill in self.graph:
            get_depth(skill)
        
        return depths
    
    def _identify_core_skills(self, top_n: int = 5) -> List[Dict]:
        """识别核心 SKILL（被依赖最多的）"""
        dependency_count = {}
        for skill, deps in self.graph.items():
            for dep in deps:
                dependency_count[dep] = dependency_count.get(dep, 0) + 1
        
        sorted_skills = sorted(dependency_count.items(), key=lambda x: x[1], reverse=True)
        return [{"skill": s, "depended_by": c} for s, c in sorted_skills[:top_n]]


class VisualizationIntegrator:
    """可视化集成器"""
    
    def __init__(self, web_dir: Path):
        self.web_dir = web_dir
        self.skills_json_path = web_dir / "data" / "skills.json"
    
    def integrate_skill(self, skill_meta: Dict):
        """将 SKILL 集成到可视化页面"""
        # 读取现有 skills.json
        if self.skills_json_path.exists():
            with open(self.skills_json_path, 'r', encoding='utf-8') as f:
                skills_data = json.load(f)
        else:
            skills_data = {"skills": [], "last_updated": ""}
        
        # 添加新 SKILL
        skills_data["skills"].append({
            "id": skill_meta.get("name", ""),
            "name": skill_meta.get("name", ""),
            "display_name": skill_meta.get("design_spec", {}).get("display_name", ""),
            "description": skill_meta.get("description", ""),
            "tags": skill_meta.get("tags", []),
            "functions": skill_meta.get("design_spec", {}).get("functions", []),
            "dependencies": skill_meta.get("design_spec", {}).get("dependencies", []),
            "created_at": skill_meta.get("created_at", ""),
            "source": skill_meta.get("forged_by", "unknown")
        })
        
        skills_data["last_updated"] = datetime.now().isoformat()
        
        # 写回文件
        self.skills_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.skills_json_path, 'w', encoding='utf-8') as f:
            json.dump(skills_data, f, ensure_ascii=False, indent=2)
```

### 每 5 个 SKILL 的增量检查

```python
class IncrementalChecker:
    """增量检查器（每 5 个 SKILL）"""
    
    def __init__(self):
        self.skill_count = 0
        self.last_check_count = 0
    
    def should_check(self) -> bool:
        """是否应该执行检查"""
        return self.skill_count - self.last_check_count >= 5
    
    def check(self, all_skills: List[Dict]):
        """执行增量检查"""
        print(f"\n{'='*60}")
        print(f"增量检查 (当前 SKILL 数: {len(all_skills)})")
        print(f"{'='*60}")
        
        # 1. 依赖关系分析
        analyzer = DependencyAnalyzer("memory.db")
        dep_report = analyzer.analyze_all_skills(all_skills)
        
        print(f"\n依赖关系报告:")
        print(f"  总 SKILL 数: {dep_report['total_skills']}")
        print(f"  总依赖数: {dep_report['total_dependencies']}")
        print(f"  最大依赖深度: {dep_report['max_depth']}")
        print(f"  循环依赖数: {len(dep_report['cycles'])}")
        print(f"  孤立 SKILL 数: {len(dep_report['isolated_skills'])}")
        
        if dep_report['core_skills']:
            print(f"\n核心 SKILL (被依赖最多):")
            for core in dep_report['core_skills']:
                print(f"    - {core['skill']}: 被 {core['depended_by']} 个 SKILL 依赖")
        
        if dep_report['cycles']:
            print(f"\n⚠️ 发现循环依赖:")
            for cycle in dep_report['cycles']:
                print(f"    - {' → '.join(cycle)}")
        
        # 2. 调用关系可视化（生成 Mermaid 图）
        self._generate_dependency_graph(all_skills)
        
        self.last_check_count = self.skill_count
    
    def _generate_dependency_graph(self, skills: List[Dict]):
        """生成依赖关系图（Mermaid 格式）"""
        mermaid = ["graph TD"]
        
        for skill in skills:
            name = skill.get("name", "")
            deps = skill.get("design_spec", {}).get("dependencies", [])
            
            for dep in deps:
                mermaid.append(f"    {name} --> {dep}")
        
        graph_path = Path("/Users/administruter/Desktop/AGI_PROJECT/docs/321自成长待处理/skill_dependency_graph.md")
        graph_path.write_text("\n".join(mermaid), encoding='utf-8')
        print(f"\n依赖关系图已生成: {graph_path}")
```

---

## 四、任务三：循环控制系统

### 循环终止条件推演

**阈值 X 的计算公式**:

```python
def calculate_threshold_X(current_round: int, history: List[Dict]) -> int:
    """
    动态计算有效产出阈值 X
    
    参数:
        current_round: 当前轮次
        history: 历史轮次数据
    
    返回:
        阈值 X（有效节点+SKILL 总数）
    """
    # 基础阈值：第 1 轮期望产出 20 个有效节点/SKILL
    base_threshold = 20
    
    # 增长因子：每轮期望增长 1.5 倍
    growth_factor = 1.5
    
    # 当前轮期望阈值
    expected = base_threshold * (growth_factor ** (current_round - 1))
    
    # 历史平均产出
    if history:
        avg_output = sum(h.get("effective_output", 0) for h in history) / len(history)
        # 如果历史平均低于期望，降低阈值（容错）
        if avg_output < expected * 0.7:
            expected = avg_output * 1.2
    
    return int(expected)
```

**有效产出定义**:
- 真实节点：通过四向碰撞产生，confidence > 0.7
- SKILL：通过模板校验，score > 80
- PCM：概念清晰，有明确应用场景

### 循环主控制器

```python
class GrowthLoopController:
    """全速成长循环控制器"""
    
    def __init__(self, collision_engine, converter, validator, checker):
        self.collision_engine = collision_engine
        self.converter = converter
        self.validator = validator
        self.checker = checker
        self.history = []
        self.all_skills = []
    
    def run(self, min_rounds: int = 10, max_rounds: int = 100):
        """运行成长循环"""
        print(f"\n{'='*60}")
        print(f"AGI 全速成长系统启动")
        print(f"最少轮次: {min_rounds}, 最多轮次: {max_rounds}")
        print(f"{'='*60}\n")
        
        for round_num in range(1, max_rounds + 1):
            print(f"\n{'#'*60}")
            print(f"# 第 {round_num} 轮成长")
            print(f"{'#'*60}\n")
            
            # 任务一：节点获取
            round_result = self._task_one(round_num)
            
            # 任务二：验证优化
            round_result = self._task_two(round_result)
            
            # 记录历史
            self.history.append(round_result)
            
            # 判断是否达到阈值
            threshold_X = calculate_threshold_X(round_num, self.history)
            effective_output = round_result.get("effective_output", 0)
            
            print(f"\n本轮有效产出: {effective_output}")
            print(f"阈值 X: {threshold_X}")
            
            if round_num >= min_rounds and effective_output >= threshold_X:
                print(f"\n✅ 达到阈值，成长循环结束（第 {round_num} 轮）")
                break
            
            if round_num >= min_rounds and effective_output < threshold_X * 0.3:
                print(f"\n⚠️ 产出过低，建议人工介入检查")
        
        # 生成最终报告
        self._generate_final_report()
    
    def _task_one(self, round_num: int) -> Dict:
        """任务一：节点获取"""
        print(f"[任务一] 节点获取中...")
        
        start_time = time.time()
        start_tokens = self.collision_engine.token_usage["total"]
        
        # 1. 自上而下拆解
        big_questions = [
            "如何实现 AGI",
            "如何让 AI 具备自我成长能力",
            "如何构建真实认知网络"
        ]
        all_sub_questions = []
        for q in big_questions:
            sub_qs = self.collision_engine.top_down_decompose(q)
            all_sub_questions.extend(sub_qs)
        
        # 2. 自下而上构建
        proven_nodes = self._get_proven_nodes()
        patterns = self.collision_engine.bottom_up_construct(proven_nodes)
        
        # 3. 左右寻找重叠
        domain_a = [n for n in proven_nodes if "flutter" in n.get("tags", [])]
        domain_b = [n for n in proven_nodes if "cad" in n.get("tags", [])]
        overlaps = []
        if domain_a and domain_b:
            overlaps = self.collision_engine.horizontal_overlap(domain_a, domain_b)
        
        # 4. 从重叠构建新节点
        new_nodes = self.collision_engine.construct_from_overlap(overlaps)
        
        # 5. 节点→SKILL 转换
        new_skills = []
        for node in new_nodes:
            skill = self.converter.convert(node)
            if skill:
                new_skills.append(skill)
        
        end_tokens = self.collision_engine.token_usage["total"]
        elapsed = time.time() - start_time
        
        return {
            "round": round_num,
            "sub_questions": len(all_sub_questions),
            "patterns": len(patterns),
            "overlaps": len(overlaps),
            "new_nodes": len(new_nodes),
            "new_skills": len(new_skills),
            "tokens_used": end_tokens - start_tokens,
            "elapsed_seconds": elapsed
        }
    
    def _task_two(self, round_result: Dict) -> Dict:
        """任务二：验证优化"""
        print(f"[任务二] 验证优化中...")
        
        new_skills = round_result.get("new_skills", 0)
        valid_skills = 0
        
        # 模拟验证（实际应从数据库读取）
        for i in range(new_skills):
            skill_meta = {"name": f"skill_{i}", "design_spec": {}}
            validation = self.validator.validate(skill_meta)
            if validation["valid"]:
                valid_skills += 1
                self.all_skills.append(skill_meta)
        
        # 每 5 个 SKILL 检查一次
        self.checker.skill_count = len(self.all_skills)
        if self.checker.should_check():
            self.checker.check(self.all_skills)
        
        # 计算有效产出
        effective_output = round_result.get("new_nodes", 0) + valid_skills
        round_result["effective_output"] = effective_output
        round_result["valid_skills"] = valid_skills
        
        return round_result
    
    def _get_proven_nodes(self) -> List[Dict]:
        """获取已有的真实节点（从数据库）"""
        # 实际应从 memory.db 读取
        return []
    
    def _generate_final_report(self):
        """生成最终报告"""
        report_path = Path("/Users/administruter/Desktop/AGI_PROJECT/docs/321自成长待处理/growth_final_report.md")
        
        total_rounds = len(self.history)
        total_nodes = sum(h.get("new_nodes", 0) for h in self.history)
        total_skills = sum(h.get("valid_skills", 0) for h in self.history)
        total_tokens = sum(h.get("tokens_used", 0) for h in self.history)
        
        report = f"""# AGI 全速成长系统 — 最终报告

## 总体统计

- 总轮次: {total_rounds}
- 总节点产出: {total_nodes}
- 总 SKILL 产出: {total_skills}
- 总 Tokens 消耗: {total_tokens:,}
- 平均每轮 Tokens: {total_tokens // total_rounds if total_rounds else 0:,}

## 逐轮详情

| 轮次 | 新节点 | 新SKILL | Tokens | 有效产出 | 耗时(s) |
|------|--------|---------|--------|---------|---------|
"""
        
        for h in self.history:
            report += f"| {h['round']} | {h.get('new_nodes', 0)} | {h.get('valid_skills', 0)} | {h.get('tokens_used', 0):,} | {h.get('effective_output', 0)} | {h.get('elapsed_seconds', 0):.1f} |\n"
        
        report_path.write_text(report, encoding='utf-8')
        print(f"\n最终报告已生成: {report_path}")
```

---

## 五、数据库扩展

### 新增表结构

```sql
-- 真实节点表
CREATE TABLE IF NOT EXISTS proven_nodes (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'proven', 'hypothesis', 'pattern'
    source TEXT,  -- 'collision', 'human_practice', 'ai_reasoning'
    collision_type TEXT,  -- 'top_down', 'bottom_up', 'horizontal', 'overlap'
    confidence REAL DEFAULT 0.8,
    domain TEXT,
    tags TEXT,  -- JSON array
    metadata TEXT,  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_by TEXT,  -- 'human', 'ai', 'both'
    verification_date TIMESTAMP
);

-- SKILL 表（扩展）
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    file_path TEXT,
    description TEXT,
    tags TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    forged_by TEXT,  -- 'human', 'growth_engine', 'glm5'
    source_node_id TEXT,  -- 关联 proven_nodes.id
    meta_json TEXT,  -- 完整的 .meta.json 内容
    validation_score INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (source_node_id) REFERENCES proven_nodes(id)
);

-- SKILL 依赖关系表
CREATE TABLE IF NOT EXISTS skill_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT NOT NULL,
    depends_on TEXT NOT NULL,  -- 被依赖的 skill_id
    dependency_type TEXT,  -- 'required', 'optional', 'suggested'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    FOREIGN KEY (depends_on) REFERENCES skills(id)
);

-- 成长日志表
CREATE TABLE IF NOT EXISTS growth_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_number INTEGER NOT NULL,
    phase TEXT NOT NULL,  -- 'task_one', 'task_two', 'task_three'
    event_type TEXT,  -- 'node_created', 'skill_generated', 'validation_passed'
    entity_id TEXT,  -- node_id or skill_id
    tokens_used INTEGER DEFAULT 0,
    elapsed_seconds REAL,
    metadata TEXT,  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 碰撞历史表
CREATE TABLE IF NOT EXISTS collision_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collision_type TEXT NOT NULL,  -- 'top_down', 'bottom_up', 'horizontal', 'overlap'
    input_nodes TEXT,  -- JSON array of node IDs
    output_nodes TEXT,  -- JSON array of new node IDs
    glm5_prompt TEXT,
    glm5_response TEXT,
    tokens_used INTEGER,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PCM 表（Proven Concept Module）
CREATE TABLE IF NOT EXISTS pcm (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    concept TEXT NOT NULL,
    domain TEXT,
    confidence REAL DEFAULT 0.8,
    references TEXT,  -- JSON array
    source_node_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_node_id) REFERENCES proven_nodes(id)
);
```

---

## 六、实践步骤清单

### 阶段 1: 环境准备（2小时）

- [ ] 1.1 确认智谱 API Key 余额充足（建议 ¥500+）
- [ ] 1.2 配置 GLM-5 API 调用（更新 `agi_v13_cognitive_lattice.py`）
- [ ] 1.3 创建数据库表（执行上述 SQL）
- [ ] 1.4 安装依赖：`pip install requests sqlite3 pathlib`

### 阶段 2: 核心引擎实现（8小时）

- [ ] 2.1 实现 `FourWayCollisionEngine` 类
- [ ] 2.2 实现 `NodeToSkillConverter` 类
- [ ] 2.3 实现 `SkillTemplateValidator` 类
- [ ] 2.4 实现 `DependencyAnalyzer` 类
- [ ] 2.5 实现 `VisualizationIntegrator` 类
- [ ] 2.6 实现 `IncrementalChecker` 类
- [ ] 2.7 实现 `GrowthLoopController` 类

### 阶段 3: Prompt 工程优化（4小时）

- [ ] 3.1 优化 `TOPDOWN_PROMPT`（加入 few-shot 示例）
- [ ] 3.2 优化 `BOTTOMUP_PROMPT`（加入模式识别示例）
- [ ] 3.3 优化 `HORIZONTAL_PROMPT`（加入跨域迁移示例）
- [ ] 3.4 设计节点质量评估 Prompt

### 阶段 4: 可视化集成（4小时）

- [ ] 4.1 创建 `web/data/skills.json` 数据文件
- [ ] 4.2 更新前端页面读取 skills.json
- [ ] 4.3 实现 SKILL 详情展示（依赖关系/前置条件/产出）
- [ ] 4.4 实现依赖关系图可视化（使用 Mermaid 或 D3.js）

### 阶段 5: 首轮测试（2小时）

- [ ] 5.1 手动运行第 1 轮成长循环
- [ ] 5.2 检查 tokens 消耗是否 > 10万/轮
- [ ] 5.3 检查生成的节点质量
- [ ] 5.4 检查生成的 SKILL 是否符合模板
- [ ] 5.5 检查数据库写入是否正常

### 阶段 6: 参数调优（4小时）

- [ ] 6.1 调整 GLM-5 temperature（建议 0.7-0.9）
- [ ] 6.2 调整节点 confidence 阈值（建议 0.7）
- [ ] 6.3 调整 SKILL 转换规则
- [ ] 6.4 调整阈值 X 计算公式
- [ ] 6.5 调整每轮大问题数量（建议 3-5 个）

### 阶段 7: 全速运行（24小时+）

- [ ] 7.1 启动 10 轮成长循环
- [ ] 7.2 实时监控 tokens 消耗速率
- [ ] 7.3 每 5 个 SKILL 检查依赖关系
- [ ] 7.4 记录每轮产出到 growth_log
- [ ] 7.5 生成最终报告

### 阶段 8: 人类验证（持续）

- [ ] 8.1 审查生成的 SKILL 代码质量
- [ ] 8.2 实践验证 SKILL 的可执行性
- [ ] 8.3 反馈优化建议到系统
- [ ] 8.4 标记高质量节点为 verified_by='human'
- [ ] 8.5 将人类实践结果注入认知网络

---

## 七、关键指标监控

### Tokens 消耗监控

```python
# 目标: ≥ 100万 tokens/小时
# 实时监控命令
SELECT 
    strftime('%Y-%m-%d %H:00', created_at) as hour,
    SUM(tokens_used) as total_tokens
FROM growth_log
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;
```

### 节点产出监控

```python
# 目标: ≥ 10 个真实节点/小时
SELECT 
    strftime('%Y-%m-%d %H:00', created_at) as hour,
    COUNT(*) as node_count,
    AVG(confidence) as avg_confidence
FROM proven_nodes
WHERE source = 'collision'
GROUP BY hour
ORDER BY hour DESC
LIMIT 24;
```

### SKILL 质量监控

```python
# 目标: ≥ 60% 转换率，≥ 80 分验证分数
SELECT 
    COUNT(*) as total_skills,
    AVG(validation_score) as avg_score,
    SUM(CASE WHEN validation_score >= 80 THEN 1 ELSE 0 END) as high_quality_count
FROM skills
WHERE forged_by = 'growth_engine';
```

---

## 八、风险与应对

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|---------|
| GLM-5 API 限流 | 无法达到 100万 tokens/小时 | 中 | 1) 申请提额 2) 多账号轮询 3) 降低并发 |
| 生成节点质量低 | 转换率 < 60% | 中 | 1) 优化 Prompt 2) 提高 confidence 阈值 3) 增加人类验证 |
| 循环依赖过多 | SKILL 无法正常调用 | 低 | 1) 检测后自动打破 2) 重新设计依赖 |
| 数据库性能瓶颈 | 写入延迟高 | 低 | 1) 批量写入 2) 索引优化 3) 迁移到 PostgreSQL |
| Tokens 预算耗尽 | 成长中断 | 高 | 1) 实时监控余额 2) 设置告警 3) 预留备用账号 |

---

## 九、成功标准

### 最低标准（10 轮后）

- ✅ Tokens 总消耗 ≥ 1000万
- ✅ 真实节点产出 ≥ 100 个
- ✅ SKILL 产出 ≥ 60 个
- ✅ SKILL 验证通过率 ≥ 60%
- ✅ 依赖关系图清晰无循环

### 优秀标准（10 轮后）

- 🌟 Tokens 总消耗 ≥ 2000万
- 🌟 真实节点产出 ≥ 200 个
- 🌟 SKILL 产出 ≥ 120 个
- 🌟 SKILL 验证通过率 ≥ 80%
- 🌟 至少 5 个 SKILL 被人类实践验证为真

### 卓越标准（10 轮后）

- 💎 Tokens 总消耗 ≥ 5000万
- 💎 真实节点产出 ≥ 500 个
- 💎 SKILL 产出 ≥ 300 个
- 💎 SKILL 验证通过率 ≥ 90%
- 💎 至少 20 个 SKILL 被人类实践验证为真
- 💎 形成至少 3 个跨域知识迁移案例
- 💎 产生至少 1 个突破性的新认知概念

---

## 十、下一步行动

1. **立即执行**:
   - [ ] 阅读并理解本实践清单
   - [ ] 确认智谱 API Key 余额
   - [ ] 执行阶段 1（环境准备）

2. **本周完成**:
   - [ ] 执行阶段 2-4（核心引擎实现 + Prompt 优化 + 可视化）
   - [ ] 执行阶段 5（首轮测试）

3. **下周完成**:
   - [ ] 执行阶段 6（参数调优）
   - [ ] 启动阶段 7（全速运行 10 轮）

4. **持续进行**:
   - [ ] 执行阶段 8（人类验证）
   - [ ] 根据实际情况调整参数和策略

---

## 附录：核心代码文件清单

| 文件路径 | 说明 | 预估行数 |
|---------|------|---------|
| `growth_engine.py` | 全速成长核心引擎 | 800 |
| `four_way_collision.py` | 四向碰撞引擎 | 400 |
| `node_to_skill.py` | 节点→SKILL 转换器 | 300 |
| `skill_validator.py` | SKILL 模板校验器 | 200 |
| `dependency_analyzer.py` | 依赖关系分析器 | 300 |
| `visualization_integrator.py` | 可视化集成器 | 200 |
| `growth_loop_controller.py` | 循环控制器 | 400 |
| `database_schema.sql` | 数据库表结构 | 150 |
| `run_growth.py` | 启动脚本 | 100 |
| **总计** | | **~2850 行** |

---

**文档结束**
