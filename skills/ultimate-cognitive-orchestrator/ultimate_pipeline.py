#!/usr/bin/env python3
"""
Ultimate Cognitive Orchestrator — 完整6阶段Pipeline实现
34个Skill的统一调度内核，think()一个接口调度一切
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum
from collections import defaultdict
import json
import time
import hashlib


# ═══════════════════════════════════════════════════════
# 常量与配置
# ═══════════════════════════════════════════════════════

EXISTING_12_DOMAINS = [
    "商业", "科研", "工业", "医疗", "法律", "教育",
    "艺术", "农业", "环境", "政策", "金融", "军事"
]

DIMENSION_NAMES = {
    "D1": "核心知识", "D2": "前沿未知", "D3": "验证方法", "D4": "记忆体系",
    "D5": "红线清单", "D6": "工具生态", "D7": "决策框架", "D8": "失败模式",
    "D9": "人机闭环", "D10": "跨领域融合", "D11": "趋势预测", "D12": "成长指标",
}

DOMAIN_KEYWORDS = {
    "代码": ["代码", "编程", "bug", "部署", "API", "数据库", "CI", "CD", "Docker",
              "Git", "架构", "debug", "refactor", "test", "code", "programming",
              "deploy", "infrastructure", "server", "frontend", "backend"],
    "商业": ["商业", "市场", "用户", "增长", "收入", "利润", "ROI", "融资", "估值",
              "产品", "PMF", "竞争", "品牌", "定价", "market", "revenue", "profit",
              "startup", "business", "customer", "growth"],
    "工业": ["精度", "产线", "制造", "质量", "CPK", "FMEA", "SPC", "设备", "工艺",
              "刀模", "模具", "精益", "六西格玛", "不良率", "manufacturing", "quality",
              "precision", "production", "lean", "factory"],
    "科研": ["研究", "实验", "假设", "论文", "统计", "p值", "可复现", "arXiv",
              "文献", "元分析", "research", "hypothesis", "experiment", "paper"],
    "金融": ["投资", "估值", "风险", "回报", "对冲", "衍生品", "夏普", "回撤",
              "量化", "交易", "investment", "valuation", "risk", "hedge", "trading"],
    "医疗": ["诊断", "临床", "患者", "治疗", "药物", "医学", "基因", "影像",
              "RCT", "NNT", "diagnosis", "clinical", "patient", "treatment"],
    "环境": ["碳", "排放", "气候", "可持续", "LCA", "ESG", "碳中和", "生态",
              "carbon", "emission", "climate", "sustainable"],
    "教育": ["教学", "课程", "学习", "评估", "Bloom", "学生", "培训",
              "teaching", "learning", "assessment", "education"],
    "法律": ["合同", "合规", "知识产权", "版权", "专利", "法规", "GDPR",
              "contract", "compliance", "IP", "patent", "legal"],
    "政策": ["政策", "监管", "政府", "法规", "公共", "治理",
              "policy", "regulation", "government", "governance"],
    "农业": ["农业", "作物", "土壤", "灌溉", "粮食", "农药",
              "agriculture", "crop", "soil", "farming"],
    "军事": ["军事", "国防", "情报", "战略", "威慑",
              "military", "defense", "intelligence", "strategy"],
    "艺术": ["设计", "UI", "UX", "品牌", "视觉", "创意", "审美",
              "design", "brand", "visual", "creative", "art"],
}

DOMAIN_DEFAULT_DIMS = {
    "代码": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"],
    "商业": ["D1", "D2", "D3", "D4", "D5", "D7", "D8", "D9", "D10", "D11", "D12"],
    "工业": ["D1", "D2", "D3", "D4", "D5", "D7", "D8", "D9", "D10", "D11", "D12"],
    "科研": ["D1", "D2", "D3", "D4", "D5", "D7", "D8", "D9", "D10", "D11", "D12"],
    "金融": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"],
    "医疗": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11"],
    "教育": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"],
    "法律": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"],
    "农业": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12"],
    "环境": ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11"],
    "政策": ["D3", "D7", "D8", "D10"],
    "军事": ["D3", "D7", "D8", "D10"],
    "艺术": ["D1", "D3", "D6", "D7", "D10"],
}

SKILL_DAG = {
    "self-evolution-cognition": [],
    "diepre-vision-cognition": [],
    "human-ai-closed-loop": [],
    "arxiv-collision-cognition": [],
    "skill-collision-engine": ["self-evolution-cognition", "human-ai-closed-loop"],
    "ai-growth-engine": ["self-evolution-cognition"],
    "skill-factory-optimizer": ["skill-collision-engine", "ai-growth-engine"],
    "universal-occupation-adapter": ["skill-collision-engine", "self-evolution-cognition"],
    "multi-domain-fusion-engine": ["skill-collision-engine"],
    "expert-identity-adapter": ["universal-occupation-adapter"],
    "global-domain-fusion-orchestrator": ["multi-domain-fusion-engine"],
    "expert-identity-self-evolution-engine": ["expert-identity-adapter", "self-evolution-cognition"],
    "self-evolving-domain-engine": ["domain-orchestrator-runtime", "expert-identity-self-evolution-engine"],
    "business-industry-fusion": ["universal-occupation-adapter", "skill-collision-engine"],
    "ai4science-bridge": ["arxiv-collision-cognition", "skill-collision-engine"],
    "fincode-quant-engine": ["universal-occupation-adapter", "skill-collision-engine"],
    "programmer-cognition": ["universal-occupation-adapter"],
    "researcher-cognition": ["universal-occupation-adapter"],
    "designer-cognition": ["universal-occupation-adapter"],
    "entrepreneur-cognition": ["universal-occupation-adapter"],
    "creative-lateral-thinking": ["self-evolution-cognition"],
    "kingofzhao-decision-framework": ["self-evolution-cognition"],
    "learning-accelerator": ["human-ai-closed-loop"],
    "memory-hierarchy-system": ["self-evolution-cognition"],
    "error-pattern-analyzer": ["self-evolution-cognition", "ai-growth-engine"],
    "knowledge-graph-builder": ["self-evolution-cognition"],
    "vision-action-evolution-loop": ["diepre-vision-cognition"],
    "diepre-embodied-bridge": ["diepre-vision-cognition"],
    "prompt-engineering-cognition": ["self-evolution-cognition"],
    "workflow-orchestrator": ["self-evolution-cognition"],
    "ultimate-domain-orchestrator": ["global-domain-fusion-orchestrator"],
    "cognitive-fusion-universe": ["ultimate-domain-orchestrator", "knowledge-graph-builder"],
    "domain-orchestrator-runtime": ["ultimate-domain-orchestrator", "cognitive-fusion-universe"],
}

DOMAIN_OCCUPATION_SKILL = {
    "代码": "programmer-cognition",
    "科研": "researcher-cognition",
    "商业": "entrepreneur-cognition",
    "艺术": "designer-cognition",
}

DOMAIN_PAIR_FUSION = {
    frozenset(["商业", "工业"]): "business-industry-fusion",
    frozenset(["科研", "代码"]): "ai4science-bridge",
    frozenset(["金融", "代码"]): "fincode-quant-engine",
}

TASK_TYPE_DIMS = {
    "decision":    ["D1", "D2", "D3", "D5", "D7", "D10"],
    "verification":["D3", "D5", "D8"],
    "learning":    ["D1", "D4", "D9", "D12"],
    "creation":    ["D1", "D2", "D6", "D10", "D11"],
    "execution":   ["D5", "D6", "D8", "D9"],
}


# ═══════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════

class ScheduleMode(Enum):
    SINGLE   = "single"
    CHAIN    = "chain"
    PARALLEL = "parallel"
    DAG      = "dag"
    EMERGENT = "emergent"


@dataclass
class DomainScore:
    domain: str
    score: float
    match_type: str  # keyword / affinity / context


@dataclass
class Dimension:
    domain: str
    code: str
    name: str
    content: str
    confidence: float


@dataclass
class CognitivePoint:
    insight: str
    confidence: float
    source_domains: list[str] = field(default_factory=list)
    source_dimensions: list[str] = field(default_factory=list)
    source_skills: list[str] = field(default_factory=list)
    collision_type: str = "holistic"
    status: str = "verified"  # verified/high_confidence/speculative


@dataclass
class TaskProfile:
    domains: list[DomainScore] = field(default_factory=list)
    primary: list[DomainScore] = field(default_factory=list)
    complexity: str = "low"   # low/mid/high/max
    task_type: str = "decision"
    urgency: str = "normal"


@dataclass
class SchedulePlan:
    mode: ScheduleMode
    skills_ordered: list[str] = field(default_factory=list)
    domains_active: list[str] = field(default_factory=list)
    dims_loaded: list[str] = field(default_factory=list)
    est_confidence: float = 0.9


@dataclass
class SkillResult:
    skill_name: str
    output: str
    points: list[CognitivePoint] = field(default_factory=list)
    confidence: float = 0.9
    duration_ms: float = 0.0


@dataclass
class OrchestratedOutput:
    answer: str
    confidence: float
    domains_used: list[str]
    skills_used: list[str]
    dims_used: list[str]
    points: list[CognitivePoint]
    warnings: list[str]
    mode: ScheduleMode
    profile: TaskProfile
    duration_ms: float = 0.0


# ═══════════════════════════════════════════════════════
# DAG 依赖管理
# ═══════════════════════════════════════════════════════

class SkillDependencyDAG:
    """Skill依赖有向无环图"""

    def __init__(self, adj: dict[str, list[str]]):
        self.adj = {k: list(v) for k, v in adj.items()}

    def topological_sort(self, skills: list[str]) -> list[str]:
        """拓扑排序: 返回按依赖顺序排列的Skill列表"""
        skill_set = set(skills)
        in_degree: dict[str, int] = {s: 0 for s in skill_set}
        for s in skill_set:
            for dep in self.adj.get(s, []):
                if dep in skill_set:
                    in_degree[s] += 1

        queue = [s for s, d in in_degree.items() if d == 0]
        result = []
        while queue:
            queue.sort(key=lambda s: len(self.adj.get(s, [])))  # 优先处理叶子节点
            node = queue.pop(0)
            result.append(node)
            for s in skill_set:
                if node in self.adj.get(s, []):
                    in_degree[s] -= 1
                    if in_degree[s] == 0:
                        queue.append(s)
        return result

    def get_dependencies(self, skill: str) -> list[str]:
        return list(self.adj.get(skill, []))

    def get_execution_layers(self, skills: list[str]) -> list[list[str]]:
        """分层: 同层Skill可并行执行"""
        remaining = set(skills)
        layers = []
        resolved = set()
        while remaining:
            layer = []
            for s in remaining:
                deps = set(self.get_dependencies(s))
                if deps.issubset(resolved):
                    layer.append(s)
            if not layer:
                break  # 循环依赖保护
            layers.append(sorted(layer))
            resolved.update(layer)
            remaining -= set(layer)
        return layers

    def get_transitive_deps(self, skill: str) -> set[str]:
        """获取所有传递依赖"""
        visited = set()
        stack = list(self.get_dependencies(skill))
        while stack:
            s = stack.pop()
            if s not in visited:
                visited.add(s)
                stack.extend(self.get_dependencies(s))
        return visited


# ═══════════════════════════════════════════════════════
# Phase 1: 任务理解
# ═══════════════════════════════════════════════════════

def detect_domains(task: str, context: list[str] = None, max_domains: int = 8) -> list[DomainScore]:
    """领域识别: 三层信号(关键词+上下文+关联)"""
    scores: dict[str, float] = {}
    task_lower = task.lower()

    # Layer 1: 关键词匹配
    for domain, keywords in DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in task_lower)
        if hits > 0:
            scores[domain] = min(hits * 0.25, 1.0)

    # Layer 2: 上下文推断
    if context:
        for ctx in context[-5:]:
            ctx_lower = ctx.lower()
            for domain, keywords in DOMAIN_KEYWORDS.items():
                hits = sum(1 for kw in keywords if kw.lower() in ctx_lower)
                if hits > 0:
                    scores[domain] = max(scores.get(domain, 0), min(hits * 0.20, 0.8))

    # Layer 3: 关联领域加分
    AFFINITY = {
        "商业": ["工业", "金融", "代码", "政策"], "工业": ["商业", "代码", "环境", "金融"],
        "科研": ["代码", "医疗", "金融", "工业"], "金融": ["商业", "科研", "代码", "政策"],
        "代码": ["商业", "科研", "工业", "医疗", "金融", "艺术"], "医疗": ["科研", "代码", "金融"],
        "环境": ["工业", "金融", "政策", "农业"], "教育": ["科研", "代码", "商业"],
        "法律": ["商业", "金融", "代码", "政策"], "政策": ["法律", "金融", "商业", "环境"],
        "农业": ["环境", "工业", "金融", "政策"], "军事": ["代码", "科研", "工业"],
        "艺术": ["商业", "代码", "教育"],
    }
    for d, s in list(scores.items()):
        if s >= 0.5:
            for rel in AFFINITY.get(d, []):
                scores[rel] = max(scores.get(rel, 0), s * 0.3)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:max_domains]
    return [DomainScore(d, s, "keyword" if s >= 0.5 else "affinity") for d, s in ranked if s >= 0.2]


def classify_task_type(task: str) -> str:
    """任务类型分类"""
    t = task.lower()
    decision_kw = ["决策", "选择", "判断", "要不要", "should", "decide", "which"]
    verification_kw = ["验证", "检查", "正确", "verify", "check", "validate"]
    learning_kw = ["学习", "理解", "解释", "learn", "explain", "understand"]
    creation_kw = ["创建", "设计", "生成", "create", "design", "generate"]
    execution_kw = ["执行", "实现", "部署", "implement", "deploy", "build"]
    for kws, typ in [(decision_kw, "decision"), (verification_kw, "verification"),
                     (learning_kw, "learning"), (creation_kw, "creation"),
                     (execution_kw, "execution")]:
        if any(kw in t for kw in kws):
            return typ
    return "decision"


def profile_task(task: str, context: list[str] = None) -> TaskProfile:
    """完整任务画像"""
    ds = detect_domains(task, context)
    primary = [d for d in ds if d.score >= 0.5]
    n = len(primary)
    complexity = "low" if n <= 1 else "mid" if n <= 3 else "high" if n <= 6 else "max"
    return TaskProfile(
        domains=ds, primary=primary, complexity=complexity,
        task_type=classify_task_type(task), urgency="normal",
    )


# ═══════════════════════════════════════════════════════
# Phase 2: 调度规划
# ═══════════════════════════════════════════════════════

class SchedulePlanner:
    """调度规划器"""

    def __init__(self, dag: SkillDependencyDAG):
        self.dag = dag

    def plan(self, profile: TaskProfile) -> SchedulePlan:
        complexity_mode = {
            "low": ScheduleMode.SINGLE, "mid": ScheduleMode.CHAIN,
            "high": ScheduleMode.DAG, "max": ScheduleMode.EMERGENT,
        }
        mode = complexity_mode[profile.complexity]

        # 选择Skill
        skills = self._select_skills(profile, mode)

        # 拓扑排序
        ordered = self.dag.topological_sort(skills)

        # 计算维度
        dims = self._compute_dims(profile, ordered)

        # 预估置信度
        conf = self._estimate_confidence(profile, mode)

        return SchedulePlan(
            mode=mode, skills_ordered=ordered,
            domains_active=[d.domain for d in profile.primary],
            dims_loaded=dims, est_confidence=conf,
        )

    def _select_skills(self, profile: TaskProfile, mode: ScheduleMode) -> list[str]:
        skills = set()
        for ds in profile.primary:
            # 职业 Skill
            occ = DOMAIN_OCCUPATION_SKILL.get(ds.domain)
            if occ:
                skills.add(occ)
                skills.update(self.dag.get_transitive_deps(occ))
        # 融合 Skill
        domains = [d.domain for d in profile.primary]
        for i, a in enumerate(domains):
            for b in domains[i+1:]:
                fusion = DOMAIN_PAIR_FUSION.get(frozenset([a, b]))
                if fusion:
                    skills.add(fusion)
                    skills.update(self.dag.get_transitive_deps(fusion))
        # 基础 Skill
        skills.add("self-evolution-cognition")
        # 元引擎 (根据复杂度)
        if mode in (ScheduleMode.DAG, ScheduleMode.EMERGENT):
            skills.add("domain-orchestrator-runtime")
            skills.update(self.dag.get_transitive_deps("domain-orchestrator-runtime"))
        if mode == ScheduleMode.EMERGENT:
            skills.add("self-evolving-domain-engine")
            skills.update(self.dag.get_transitive_deps("self-evolving-domain-engine"))
        return list(skills)

    def _compute_dims(self, profile: TaskProfile, skills: list[str]) -> list[str]:
        seen = set()
        dims = []
        type_dims = TASK_TYPE_DIMS.get(profile.task_type, [])
        for ds in profile.primary:
            domain_dims = DOMAIN_DEFAULT_DIMS.get(ds.domain, ["D1", "D3", "D5"])
            for d in list(dict.fromkeys(domain_dims + type_dims)):
                key = f"{ds.domain}:{d}"
                if key not in seen:
                    seen.add(key)
                    dims.append(d)
        return list(dict.fromkeys(dims))

    def _estimate_confidence(self, profile: TaskProfile, mode: ScheduleMode) -> float:
        base = 0.90
        if profile.complexity == "low":
            base = 0.96
        elif profile.complexity == "mid":
            base = 0.93
        elif profile.complexity == "high":
            base = 0.88
        else:
            base = 0.82
        # 主领域评分加权
        if profile.primary:
            avg_score = sum(d.score for d in profile.primary) / len(profile.primary)
            base *= (0.5 + 0.5 * avg_score)
        return min(base, 0.99)


# ═══════════════════════════════════════════════════════
# Phase 3: 依赖加载
# ═══════════════════════════════════════════════════════

class SkillLoader:
    """Skill实例加载器"""

    def __init__(self, dag: SkillDependencyDAG):
        self.dag = dag
        self._cache: dict[str, Any] = {}

    def load_with_deps(self, skills: list[str]) -> list[tuple[str, Any]]:
        """按DAG拓扑排序加载Skill及所有依赖"""
        ordered = self.dag.topological_sort(skills)
        loaded = []
        for name in ordered:
            if name not in self._cache:
                self._cache[name] = self._instantiate(name)
            loaded.append((name, self._cache[name]))
        return loaded

    def _instantiate(self, name: str) -> Any:
        """实例化Skill(实际实现读取SKILL.md)"""
        return {"name": name, "type": "skill_instance"}  # placeholder


# ═══════════════════════════════════════════════════════
# Phase 4: 执行调度
# ═══════════════════════════════════════════════════════

class ExecutionEngine:
    """执行引擎"""

    def __init__(self, dag: SkillDependencyDAG):
        self.dag = dag

    def execute(self, plan: SchedulePlan, loaded_skills: list[tuple[str, Any]],
                task: str, profile: TaskProfile) -> list[SkillResult]:
        """根据调度模式执行"""
        if plan.mode == ScheduleMode.SINGLE:
            return self._exec_single(loaded_skills, task, profile)
        elif plan.mode == ScheduleMode.CHAIN:
            return self._exec_chain(loaded_skills, task, profile)
        elif plan.mode == ScheduleMode.DAG:
            return self._exec_dag(loaded_skills, task, profile)
        else:  # EMERGENT
            return self._exec_emergent(loaded_skills, task, profile)

    def _exec_single(self, skills, task, profile) -> list[SkillResult]:
        """单Skill执行"""
        if not skills:
            return [SkillResult("none", "无匹配Skill", [], 0.5)]
        name, instance = skills[-1]  # 最后一个=最具体的
        return [SkillResult(name, f"[{name}] 执行结果", self._gen_points(name, profile), 0.95)]

    def _exec_chain(self, skills, task, profile) -> list[SkillResult]:
        """链式执行: A输出→B输入→C输入"""
        results = []
        context = task
        for name, instance in skills:
            pts = self._gen_points(name, profile)
            result = SkillResult(name, f"[{name}] 基于{context[:50]}...的结果", pts, 0.93)
            results.append(result)
            context = f"{task}\n{result.output}"
        return results

    def _exec_dag(self, skills, task, profile) -> list[SkillResult]:
        """DAG分层并行执行"""
        skill_names = [s[0] for s in skills]
        layers = self.dag.get_execution_layers(skill_names)
        skill_map = {s[0]: s[1] for s in skills}
        all_results = {}
        results = []
        for layer in layers:
            for name in layer:
                deps = {d: all_results[d] for d in self.dag.get_dependencies(name) if d in all_results}
                r = SkillResult(name, f"[{name}] DAG执行(依赖: {list(deps.keys())})",
                                self._gen_points(name, profile), 0.91)
                all_results[name] = r
                results.append(r)
        return results

    def _exec_emergent(self, skills, task, profile) -> list[SkillResult]:
        """认知涌现: 全Skill参与"""
        results = []
        for name, instance in skills:
            pts = self._gen_points(name, profile)
            results.append(SkillResult(name, f"[{name}] 涌现模式参与", pts, 0.88))
        # 检测涌现点
        if len(results) >= 5:
            results.append(SkillResult(
                "_emergent", "[涌现] 多Skill碰撞产生的新认知点",
                [CognitivePoint(
                    insight=f"[认知涌现] {len(results)}个Skill协作发现跨领域综合认知",
                    confidence=0.85, source_skills=[r.skill_name for r in results],
                    collision_type="emergent", status="high_confidence",
                )], 0.85,
            ))
        return results

    def _gen_points(self, skill_name: str, profile: TaskProfile) -> list[CognitivePoint]:
        """生成模拟认知点(实际实现调用Skill)"""
        domains = [d.domain for d in profile.primary]
        return [
            CognitivePoint(
                insight=f"[{skill_name}] 正面分析: {domains[0] if domains else '通用'}领域认知",
                confidence=0.95, source_skills=[skill_name], collision_type="positive",
            ),
            CognitivePoint(
                insight=f"[{skill_name}] 反面验证: 潜在风险和限制",
                confidence=0.88, source_skills=[skill_name], collision_type="negative",
            ),
            CognitivePoint(
                insight=f"[{skill_name}] 侧面视角: 跨领域桥接认知",
                confidence=0.82, source_skills=[skill_name], collision_type="lateral",
            ),
        ]


# ═══════════════════════════════════════════════════════
# Phase 5: 综合输出
# ═══════════════════════════════════════════════════════

class OutputSynthesizer:
    """综合输出器"""

    def synthesize(self, results: list[SkillResult], plan: SchedulePlan,
                   profile: TaskProfile) -> OrchestratedOutput:
        # 收集所有认知点
        all_points = []
        for r in results:
            all_points.extend(r.points)
        all_points.sort(key=lambda p: p.confidence, reverse=True)

        # 分离验证层级
        verified = [p for p in all_points if p.confidence >= 0.90]
        speculative = [p for p in all_points if p.confidence < 0.90]

        # 按碰撞类型分组
        by_type: dict[str, list[CognitivePoint]] = {}
        for p in verified:
            by_type.setdefault(p.collision_type, []).append(p)

        # 构建答案
        sections = [f"## 调度模式: {plan.mode.value}"]
        sections.append(f"## 活跃领域: {', '.join(plan.domains_active)}")

        type_labels = {"positive": "正面分析", "negative": "反面验证",
                       "lateral": "侧面视角", "holistic": "综合评估", "emergent": "认知涌现"}
        for ctype, label in type_labels.items():
            if ctype in by_type:
                sections.append(f"\n### {label}")
                for p in by_type[ctype][:5]:
                    tag = "✓" if p.confidence >= 0.95 else "○"
                    sections.append(f"- {tag} [{p.confidence:.0%}] {p.insight}")

        if speculative:
            sections.append("\n### ⚠️ 待验证 [推测]")
            for p in speculative[:3]:
                sections.append(f"- [{p.confidence:.0%}] {p.insight}")

        # 来源
        sections.append(f"\n### 认知来源")
        used_skills = list(dict.fromkeys(r.skill_name for r in results if not r.skill_name.startswith("_")))
        for s in used_skills:
            sections.append(f"- Skill: {s}")
        for d in profile.domains:
            if d.score >= 0.5:
                dims = DOMAIN_DEFAULT_DIMS.get(d.domain, [])[:6]
                sections.append(f"- 领域: {d.domain} 维度{dims}")

        # 综合置信度
        if verified:
            overall = sum(p.confidence for p in verified) / len(verified)
        else:
            overall = 0.5

        # 警告
        warnings = []
        if overall < 0.95:
            warnings.append(f"综合置信度{overall:.0%}<95%，建议人类补充")
        if profile.complexity in ("high", "max"):
            warnings.append(f"涉及{len(profile.primary)}个领域，可能存在维度冲突")
        if speculative:
            warnings.append(f"{len(speculative)}个认知点<90%置信度")

        return OrchestratedOutput(
            answer="\n".join(sections), confidence=overall,
            domains_used=plan.domains_active, skills_used=used_skills,
            dims_used=plan.dims_loaded, points=verified + speculative,
            warnings=warnings, mode=plan.mode, profile=profile,
        )


# ═══════════════════════════════════════════════════════
# Phase 6: 自进化
# ═══════════════════════════════════════════════════════

class EvolutionTracker:
    """自进化追踪器"""

    def __init__(self, log_path: str = "data/orchestrator_evolution.jsonl"):
        self.log_path = log_path

    def record(self, entry: dict):
        entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def check_evolution_trigger(self, output: OrchestratedOutput, recent_count: int) -> bool:
        """检查是否触发框架进化"""
        if output.confidence < 0.85:
            return True
        if recent_count > 20:
            return True
        return False


# ═══════════════════════════════════════════════════════
# 主入口: UltimateCognitiveOrchestrator
# ═══════════════════════════════════════════════════════

class UltimateCognitiveOrchestrator:
    """终极认知编排器 — 34个Skill的统一调度内核"""

    def __init__(self):
        self.dag = SkillDependencyDAG(SKILL_DAG)
        self.planner = SchedulePlanner(self.dag)
        self.loader = SkillLoader(self.dag)
        self.engine = ExecutionEngine(self.dag)
        self.synthesizer = OutputSynthesizer()
        self.evolution = EvolutionTracker()

    def think(self, task: str, context: list[str] = None) -> OrchestratedOutput:
        """
        主入口: 任何问题 → 统一调度 → 综合输出

        Args:
            task: 任意自然语言任务
            context: 历史对话上下文(可选)

        Returns:
            OrchestratedOutput: 结构化输出
        """
        t0 = time.time()

        # Phase 1: 任务理解
        profile = profile_task(task, context)

        # Phase 2: 调度规划
        plan = self.planner.plan(profile)

        # Phase 3: 依赖加载
        loaded = self.loader.load_with_deps(plan.skills_ordered)

        # Phase 4: 执行调度
        results = self.engine.execute(plan, loaded, task, profile)

        # Phase 5: 综合输出
        output = self.synthesizer.synthesize(results, plan, profile)

        # Phase 6: 自进化
        output.duration_ms = (time.time() - t0) * 1000
        self.evolution.record({
            "task": task[:200], "mode": plan.mode.value,
            "skills": plan.skills_ordered, "confidence": output.confidence,
            "domains": plan.domains_active, "duration_ms": output.duration_ms,
        })

        return output


# ═══════════════════════════════════════════════════════
# 使用示例
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    uco = UltimateCognitiveOrchestrator()

    # 简单任务(单领域)
    r1 = uco.think("帮我检查这段代码有没有安全漏洞")
    print(f"[单领域] 模式={r1.mode.value} 置信度={r1.confidence:.0%}")
    print(r1.answer[:200])

    # 中等复杂度(跨领域)
    r2 = uco.think("刀模工厂客户要求±0.15mm精度，国产设备±0.30mm，要不要买Bobst?")
    print(f"\n[跨领域] 模式={r2.mode.value} 置信度={r2.confidence:.0%} 领域={r2.domains_used}")
    print(r2.answer[:300])

    # 高复杂度(多领域涌现)
    r3 = uco.think("评估碳交易框架对制造业+金融+农业+政策的影响，给出投资建议")
    print(f"\n[多领域] 模式={r3.mode.value} 置信度={r3.confidence:.0%} Skills={r3.skills_used}")
    if r3.warnings:
        print(f"警告: {r3.warnings}")
