#!/usr/bin/env python3
"""
Domain Orchestrator Runtime — 5步Pipeline完整实现
任务→领域识别→维度加载→Skill路由→碰撞→综合输出
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class CollisionMode(Enum):
    SINGLE = "single"        # 单领域四向碰撞
    PAIR = "pair"            # 两领域跨域碰撞
    MULTI = "multi"          # 3+领域递归碰撞


@dataclass
class Dimension:
    """单个认知维度"""
    domain: str
    code: str        # D1-D12
    name: str        # 维度名称
    content: str     # 具体内容
    confidence: float


@dataclass
class CognitivePoint:
    """碰撞产出的认知点"""
    insight: str
    confidence: float
    source_domains: list[str]
    source_dimensions: list[str]
    collision_type: str    # positive/negative/lateral/holistic
    verification_status: str  # verified/high_confidence/speculative/uncertain


@dataclass
class DomainScore:
    """领域相关性评分"""
    domain: str
    score: float          # 0-1
    match_type: str       # keyword/context/profile


@dataclass
class SkillRoute:
    """Skill路由结果"""
    skill_name: str
    reason: str
    relevance: float


@dataclass
class OrchestratorOutput:
    """编排器最终输出"""
    answer: str
    confidence: float
    active_domains: list[str]
    loaded_dimensions: list[str]
    routed_skills: list[str]
    cognitive_points: list[CognitivePoint]
    warnings: list[str]
    used_collision_mode: CollisionMode


# ============================================================
# Step 1: DOMAIN_DETECT — 领域识别
# ============================================================

DOMAIN_KEYWORDS = {
    "代码": ["代码", "编程", "bug", "部署", "API", "数据库", "CI", "CD", "Docker",
              "Git", "架构", "debug", "refactor", "test", "infrastructure",
              "code", "programming", "deploy", "architecture", "system design"],
    "商业": ["商业", "市场", "用户", "增长", "收入", "利润", "ROI", "融资", "估值",
              "产品", "PMF", "竞争", "品牌", "定价",
              "market", "revenue", "profit", "startup", "business model", "growth"],
    "工业": ["精度", "产线", "制造", "质量", "CPK", "FMEA", "SPC", "设备", "工艺",
              "刀模", "模具", "精益", "六西格玛", "不良率",
              "manufacturing", "quality", "precision", "production", "lean"],
    "科研": ["研究", "实验", "假设", "论文", "统计", "p值", "随机对照", "可复现",
              "arXiv", "文献", "元分析", "系统综述",
              "research", "hypothesis", "experiment", "paper", "reproducibility"],
    "金融": ["投资", "估值", "风险", "回报", "对冲", "衍生品", "夏普", "回撤",
              "量化", "交易", "组合", "资产",
              "investment", "valuation", "risk", "return", "hedge", "trading"],
    "医疗": ["诊断", "临床", "患者", "治疗", "药物", "医学", "基因", "影像",
              "RCT", "NNT", "病理", "循证",
              "diagnosis", "clinical", "patient", "treatment", "drug"],
    "环境": ["碳", "排放", "气候", "可持续", "LCA", "ESG", "碳中和", "生态",
              "能源", "污染", "废水",
              "carbon", "emission", "climate", "sustainable", "ESG"],
    "教育": ["教学", "课程", "学习", "评估", "Bloom", "学生", "培训", "教育",
              "teaching", "learning", "assessment", "curriculum"],
    "法律": ["合同", "合规", "知识产权", "版权", "专利", "法规", "GDPR", "诉讼",
              "contract", "compliance", "IP", "patent", "legal"],
    "政策": ["政策", "监管", "政府", "法规", "公共", "行政", "治理",
              "policy", "regulation", "government", "governance"],
    "农业": ["农业", "作物", "土壤", "灌溉", "粮食", "农药", "种植",
              "agriculture", "crop", "soil", "farming"],
    "军事": ["军事", "国防", "情报", "战略", "威慑", "安全",
              "military", "defense", "intelligence", "strategy"],
}

# 每个领域在运行时默认加载的维度
DOMAIN_DEFAULT_DIMS = {
    "代码": ["D1", "D3", "D5", "D6", "D7", "D8"],
    "商业": ["D1", "D3", "D5", "D7", "D8", "D10"],
    "工业": ["D1", "D3", "D5", "D7", "D8", "D10"],
    "科研": ["D1", "D3", "D5", "D7", "D8", "D10"],
    "金融": ["D1", "D3", "D5", "D7", "D8", "D10"],
    "医疗": ["D1", "D3", "D5", "D7", "D10"],
    "环境": ["D1", "D3", "D5", "D10"],
    "教育": ["D1", "D3", "D7", "D9"],
    "法律": ["D1", "D3", "D5", "D7"],
    "政策": ["D3", "D7", "D10"],
    "农业": ["D1", "D3", "D5", "D10"],
    "军事": ["D3", "D7", "D8"],
}

def detect_domains(task: str, context: list[str] = None, max_domains: int = 5) -> list[DomainScore]:
    """
    Step 1: 领域识别
    三层信号: 任务关键词 + 历史上下文 + 权重衰减
    """
    scores: dict[str, float] = {}

    # Layer 1: 任务描述关键词匹配
    task_lower = task.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw.lower() in task_lower)
        if match_count > 0:
            scores[domain] = min(match_count * 0.25, 1.0)  # 4个关键词=满分

    # Layer 2: 历史上下文推断（前N轮对话）
    if context:
        for ctx in context[-5:]:  # 最近5轮
            ctx_lower = ctx.lower()
            for domain, keywords in DOMAIN_KEYWORDS.items():
                match_count = sum(1 for kw in keywords if kw.lower() in ctx_lower)
                if match_count > 0:
                    scores[domain] = max(
                        scores.get(domain, 0),
                        min(match_count * 0.20, 0.8)  # 上下文权重略低
                    )

    # Layer 3: 关联领域加分（expert-identity D10跨域映射）
    DOMAIN_AFFINITY = {
        "商业": ["工业", "金融", "代码", "政策"],
        "工业": ["商业", "代码", "环境", "金融"],
        "科研": ["代码", "医疗", "金融", "工业"],
        "金融": ["商业", "科研", "代码", "政策", "环境"],
        "代码": ["商业", "科研", "工业", "医疗", "金融"],
        "医疗": ["科研", "代码", "金融", "政策"],
        "环境": ["工业", "金融", "政策", "农业"],
        "教育": ["科研", "代码", "商业"],
        "法律": ["商业", "金融", "代码", "政策"],
        "政策": ["法律", "金融", "商业", "环境"],
        "农业": ["环境", "工业", "金融", "政策"],
        "军事": ["代码", "科研", "工业", "政策"],
    }
    for domain, score in list(scores.items()):
        if score >= 0.5:  # 只对高置信度主领域触发关联
            for related in DOMAIN_AFFINITY.get(domain, []):
                if related not in scores:
                    scores[related] = score * 0.3  # 关联领域30%折扣

    # 排序 + 剪枝
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:max_domains]

    return [
        DomainScore(domain=d, score=s, match_type="keyword" if s >= 0.5 else "affinity")
        for d, s in ranked if s >= 0.2  # 最低阈值
    ]


# ============================================================
# Step 2: DIMENSION_LOAD — 维度加载
# ============================================================

def load_dimensions(
    active_domains: list[DomainScore],
    task_type: str = "decision"  # decision/verification/learning/creation/execution
) -> list[Dimension]:
    """
    Step 2: 维度加载
    根据领域和任务类型动态选择加载哪些维度
    """
    TASK_TYPE_DIMS = {
        "decision":  ["D1", "D2", "D3", "D5", "D7", "D10"],
        "verification": ["D3", "D5", "D8"],
        "learning":  ["D1", "D4", "D9", "D12"],
        "creation":  ["D1", "D2", "D6", "D10", "D11"],
        "execution": ["D5", "D6", "D8", "D9"],
    }

    dims: list[Dimension] = []
    seen: set[str] = set()

    # 每个主领域加载默认维度
    for ds in active_domains:
        default_codes = DOMAIN_DEFAULT_DIMS.get(ds.domain, ["D1", "D3", "D5"])
        task_codes = TASK_TYPE_DIMS.get(task_type, [])
        all_codes = list(dict.fromkeys(default_codes + task_codes))  # 去重保序

        for code in all_codes:
            key = f"{ds.domain}:{code}"
            if key not in seen:
                seen.add(key)
                dims.append(Dimension(
                    domain=ds.domain,
                    code=code,
                    name=DIMENSION_NAMES[code],
                    content=get_dimension_content(ds.domain, code),
                    confidence=ds.score,
                ))

    return dims


# ============================================================
# Step 3: SKILL_ROUTE — Skill路由
# ============================================================

# 领域→职业Skill映射
DOMAIN_OCCUPATION_SKILL = {
    "代码": "programmer-cognition",
    "科研": "researcher-cognition",
    "商业": "entrepreneur-cognition",
    "艺术设计": "designer-cognition",
}

# 领域对→融合Skill映射
DOMAIN_PAIR_FUSION_SKILL = {
    frozenset(["商业", "工业"]): "business-industry-fusion",
    frozenset(["科研", "代码"]): "ai4science-bridge",
    frozenset(["金融", "代码"]): "fincode-quant-engine",
}

def route_skills(active_domains: list[DomainScore]) -> list[SkillRoute]:
    """
    Step 3: Skill路由
    检查职业Skill + 融合Skill
    """
    routes: list[SkillRoute] = []

    # 职业Skill路由
    for ds in active_domains:
        if ds.score >= 0.5:
            skill = DOMAIN_OCCUPATION_SKILL.get(ds.domain)
            if skill:
                routes.append(SkillRoute(
                    skill_name=skill,
                    reason=f"主领域[{ds.domain}]评分{ds.score:.1f}≥0.5",
                    relevance=ds.score,
                ))

    # 融合Skill路由（两两组合）
    primary = [ds for ds in active_domains if ds.score >= 0.5]
    for i, a in enumerate(primary):
        for b in primary[i+1:]:
            fusion = DOMAIN_PAIR_FUSION_SKILL.get(frozenset([a.domain, b.domain]))
            if fusion:
                routes.append(SkillRoute(
                    skill_name=fusion,
                    reason=f"融合方向[{a.domain}×{b.domain}]",
                    relevance=min(a.score, b.score),
                ))

    # 去重 + 排序
    seen: set[str] = set()
    unique = []
    for r in routes:
        if r.skill_name not in seen:
            seen.add(r.skill_name)
            unique.append(r)
    unique.sort(key=lambda x: x.relevance, reverse=True)

    return unique


# ============================================================
# Step 4: COLLIDE — 碰撞执行
# ============================================================

def execute_collision(
    task: str,
    dimensions: list[Dimension],
    collision_mode: CollisionMode,
) -> list[CognitivePoint]:
    """
    Step 4: 碰撞执行
    单领域: 四向碰撞
    跨领域: 交叉碰撞
    """
    points: list[CognitivePoint] = []

    if collision_mode == CollisionMode.SINGLE:
        # 单领域四向碰撞
        primary = [d for d in dimensions if d.confidence >= 0.5]
        for dim in primary[:6]:  # 最多6个维度参与碰撞
            base_insights = generate_four_way(dim, task)
            points.extend(base_insights)

    elif collision_mode == CollisionMode.PAIR:
        # 两领域交叉碰撞
        domains = set(d.domain for d in dimensions)
        domain_dims = {d: [dim for dim in dimensions if dim.domain == d] for d in domains}

        domain_list = list(domains)
        for i in range(len(domain_list)):
            for j in range(i+1, len(domain_list)):
                da, db = domain_list[i], domain_list[j]
                cross = cross_domain_collide(
                    domain_dims[da], domain_dims[db], task
                )
                points.extend(cross)

    elif collision_mode == CollisionMode.MULTI:
        # 多领域递归碰撞（分组→碰撞→合并）
        domains = sorted(set(d.domain for d in dimensions))
        if len(domains) <= 4:
            # 4个以下: 全排列两两碰撞
            domain_dims = {d: [dim for dim in dimensions if dim.domain == d] for d in domains}
            all_pairs = []
            for i in range(len(domains)):
                for j in range(i+1, len(domains)):
                    all_pairs.append(cross_domain_collide(
                        domain_dims[domains[i]], domain_dims[domains[j]], task
                    ))
            # 合并认知点（去重+置信度取max）
            points = merge_cognitive_points([p for pair in all_pairs for p in pair])
        else:
            # 5+个领域: 分两组→分别碰撞→结果再碰撞
            mid = len(domains) // 2
            group_a = domains[:mid]
            group_b = domains[mid:]
            # (递归调用简化为两两碰撞)
            points = pairwise_merge_collision(dimensions, group_a, group_b, task)

    # 过滤: 置信度 < 80% 的标记为[推测]
    for p in points:
        if p.confidence < 0.80:
            p.verification_status = "speculative"
        elif p.confidence < 0.95:
            p.verification_status = "high_confidence"
        else:
            p.verification_status = "verified"

    return sorted(points, key=lambda p: p.confidence, reverse=True)


def generate_four_way(dim: Dimension, task: str) -> list[CognitivePoint]:
    """单维度四向碰撞"""
    return [
        CognitivePoint(
            insight=f"[正面] {dim.domain}{dim.code}: 基于'{dim.content[:50]}...'分析任务",
            confidence=dim.confidence * 0.95,
            source_domains=[dim.domain], source_dimensions=[dim.code],
            collision_type="positive", verification_status="verified",
        ),
        CognitivePoint(
            insight=f"[反面] {dim.domain}{dim.code}: 反面验证——如果忽略此维度会出现什么问题？",
            confidence=dim.confidence * 0.85,
            source_domains=[dim.domain], source_dimensions=[dim.code],
            collision_type="negative", verification_status="high_confidence",
        ),
        CognitivePoint(
            insight=f"[侧面] {dim.domain}{dim.code}: 从相邻领域视角重新审视",
            confidence=dim.confidence * 0.80,
            source_domains=[dim.domain], source_dimensions=[dim.code],
            collision_type="lateral", verification_status="high_confidence",
        ),
        CognitivePoint(
            insight=f"[整体] {dim.domain}{dim.code}: 综合评估——此维度对任务的全局影响",
            confidence=dim.confidence * 0.90,
            source_domains=[dim.domain], source_dimensions=[dim.code],
            collision_type="holistic", verification_status="verified",
        ),
    ]


def cross_domain_collide(
    dims_a: list[Dimension],
    dims_b: list[Dimension],
    task: str,
) -> list[CognitivePoint]:
    """跨领域碰撞"""
    points = []
    for da in dims_a[:3]:  # 每个领域最多3个维度参与
        for db in dims_b[:3]:
            # 正面: 两个维度的交集
            overlap = find_overlap(da.content, db.content)
            if overlap:
                points.append(CognitivePoint(
                    insight=f"[跨域正面] {da.domain}{da.code}×{db.domain}{db.code}: {overlap}",
                    confidence=min(da.confidence, db.confidence) * 0.93,
                    source_domains=[da.domain, db.domain],
                    source_dimensions=[da.code, db.code],
                    collision_type="positive", verification_status="verified",
                ))

            # 反面: 两个维度的矛盾
            conflict = find_conflict(da.content, db.content)
            if conflict:
                points.append(CognitivePoint(
                    insight=f"[跨域反面] {da.domain}{da.code} vs {db.domain}{db.code}: {conflict}",
                    confidence=min(da.confidence, db.confidence) * 0.88,
                    source_domains=[da.domain, db.domain],
                    source_dimensions=[da.code, db.code],
                    collision_type="negative", verification_status="high_confidence",
                ))

            # 侧面: A的已知+B的未知 → 桥接
            bridge = find_bridge(da.content, db.content)
            if bridge:
                points.append(CognitivePoint(
                    insight=f"[跨域侧面] {da.domain}→{db.domain}: {bridge}",
                    confidence=min(da.confidence, db.confidence) * 0.82,
                    source_domains=[da.domain, db.domain],
                    source_dimensions=[da.code, db.code],
                    collision_type="lateral", verification_status="high_confidence",
                ))

    return points


# ============================================================
# Step 5: SYNTHESIZE — 综合输出
# ============================================================

def synthesize(
    task: str,
    cognitive_points: list[CognitivePoint],
    active_domains: list[DomainScore],
    loaded_dims: list[Dimension],
    routed_skills: list[SkillRoute],
    collision_mode: CollisionMode,
    confidence_threshold: float = 0.90,
) -> OrchestratorOutput:
    """
    Step 5: 综合输出
    结构化答案 + 置信度 + 来源标注
    """
    # 分离高置信度 vs 低置信度
    verified = [p for p in cognitive_points if p.confidence >= confidence_threshold]
    speculative = [p for p in cognitive_points if p.confidence < confidence_threshold]

    # 按碰撞类型分组
    by_type: dict[str, list[CognitivePoint]] = {}
    for p in verified:
        by_type.setdefault(p.collision_type, []).append(p)

    # 构建答案结构
    sections = []

    # 涉及的领域
    domain_names = [ds.domain for ds in active_domains if ds.score >= 0.5]
    sections.append(f"## 涉及领域: {', '.join(domain_names)}")

    # 正面认知
    if "positive" in by_type:
        sections.append("\n### 正面分析")
        for p in by_type["positive"][:5]:
            sections.append(f"- [{p.confidence:.0%}] {p.insight}")

    # 反面认知
    if "negative" in by_type:
        sections.append("\n### 反面验证")
        for p in by_type["negative"][:3]:
            sections.append(f"- [{p.confidence:.0%}] {p.insight}")

    # 侧面认知
    if "lateral" in by_type:
        sections.append("\n### 侧面视角")
        for p in by_type["lateral"][:3]:
            sections.append(f"- [{p.confidence:.0%}] {p.insight}")

    # 综合认知
    if "holistic" in by_type:
        sections.append("\n### 综合评估")
        for p in by_type["holistic"][:3]:
            sections.append(f"- [{p.confidence:.0%}] {p.insight}")

    # 推测性认知（带警告）
    if speculative:
        sections.append("\n### ⚠️ 待验证 [推测]")
        for p in speculative[:3]:
            sections.append(f"- [{p.confidence:.0%}] {p.insight}")

    # 使用到的认知源
    source_section = "\n### 认知来源"
    for ds in active_domains:
        dims_used = [d.code for d in loaded_dims if d.domain == ds.domain]
        if dims_used:
            source_section += f"\n- {ds.domain}: 维度{dims_used} (相关性{ds.score:.0%})"
    for rs in routed_skills:
        source_section += f"\n- Skill: {rs.skill_name} ({rs.reason})"
    sections.append(source_section)

    answer = "\n".join(sections)

    # 计算综合置信度
    if verified:
        overall_confidence = sum(p.confidence for p in verified) / len(verified)
    else:
        overall_confidence = 0.5

    # 生成警告
    warnings = []
    if overall_confidence < 0.95:
        warnings.append(f"综合置信度{overall_confidence:.0%}<95%，建议人类补充信息")
    if len(domain_names) >= 3:
        warnings.append(f"涉及{len(domain_names)}个领域，可能存在维度冲突")
    if speculative:
        warnings.append(f"{len(speculative)}个认知点置信度<90%，标记为[推测]")

    return OrchestratorOutput(
        answer=answer,
        confidence=overall_confidence,
        active_domains=domain_names,
        loaded_dimensions=list(set(d.code for d in loaded_dims)),
        routed_skills=[rs.skill_name for rs in routed_skills],
        cognitive_points=verified + speculative,
        warnings=warnings,
        used_collision_mode=collision_mode,
    )


# ============================================================
# 辅助函数（简化实现）
# ============================================================

DIMENSION_NAMES = {
    "D1": "核心知识", "D2": "前沿未知", "D3": "验证方法", "D4": "记忆体系",
    "D5": "红线清单", "D6": "工具生态", "D7": "决策框架", "D8": "失败模式",
    "D9": "人机闭环", "D10": "跨领域融合", "D11": "趋势预测", "D12": "成长指标",
}

def get_dimension_content(domain: str, code: str) -> str:
    """从expert-identity.md获取具体内容（实际实现读取文件）"""
    return f"[{domain}]{DIMENSION_NAMES[code]}的内容..."

def find_overlap(a: str, b: str) -> Optional[str]:
    """找两个维度内容的交集（简化版）"""
    return None  # 实际实现用语义相似度

def find_conflict(a: str, b: str) -> Optional[str]:
    """找矛盾（简化版）"""
    return None

def find_bridge(a: str, b: str) -> Optional[str]:
    """找桥接（简化版）"""
    return None

def merge_cognitive_points(points_list: list[list[CognitivePoint]]) -> list[CognitivePoint]:
    """合并去重"""
    seen = set()
    result = []
    for pts in points_list:
        for p in pts:
            key = p.insight[:50]
            if key not in seen:
                seen.add(key)
                result.append(p)
    return result

def pairwise_merge_collision(
    dimensions: list[Dimension],
    group_a: list[str], group_b: list[str],
    task: str,
) -> list[CognitivePoint]:
    """分组碰撞（递归简化版）"""
    all_points = []
    dims_a = [d for d in dimensions if d.domain in group_a]
    dims_b = [d for d in dimensions if d.domain in group_b]
    # 组内碰撞
    for i, da in enumerate(dims_a[:2]):
        for db in dims_a[i+1:3]:
            all_points.extend(cross_domain_collide([da], [db], task))
    for i, da in enumerate(dims_b[:2]):
        for db in dims_b[i+1:3]:
            all_points.extend(cross_domain_collide([da], [db], task))
    # 组间碰撞
    if dims_a and dims_b:
        all_points.extend(cross_domain_collide(dims_a[:2], dims_b[:2], task))
    return all_points


# ============================================================
# 主入口
# ============================================================

def orchestrate(
    task: str,
    context: list[str] = None,
    task_type: str = "decision",
    max_domains: int = 5,
) -> OrchestratorOutput:
    """
    Domain Orchestrator Runtime 主入口
    
    Args:
        task: 任意自然语言任务描述
        context: 历史对话上下文（可选）
        task_type: 任务类型 decision/verification/learning/creation/execution
        max_domains: 最大活跃领域数
    
    Returns:
        OrchestratorOutput: 结构化输出
    """
    # Step 1: 领域识别
    domain_scores = detect_domains(task, context, max_domains)
    if not domain_scores:
        return OrchestratorOutput(
            answer="无法识别任务涉及的领域。请提供更多上下文。",
            confidence=0.3, active_domains=[], loaded_dimensions=[],
            routed_skills=[], cognitive_points=[],
            warnings=["领域识别失败"], used_collision_mode=CollisionMode.SINGLE,
        )

    active = [ds for ds in domain_scores if ds.score >= 0.5]
    background = [ds for ds in domain_scores if ds.score < 0.5]

    # Step 2: 维度加载
    dimensions = load_dimensions(active, task_type)

    # Step 3: Skill路由
    skills = route_skills(domain_scores)

    # Step 4: 碰撞执行（选择模式）
    primary_count = len(active)
    if primary_count <= 1:
        mode = CollisionMode.SINGLE
    elif primary_count == 2:
        mode = CollisionMode.PAIR
    else:
        mode = CollisionMode.MULTI

    points = execute_collision(task, dimensions, mode)

    # Step 5: 综合输出
    return synthesize(
        task, points, domain_scores, dimensions, skills, mode
    )


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    result = orchestrate(
        task="一家做刀模的工厂，客户要求±0.15mm精度但只有国产设备±0.30mm，要不要投200万买Bobst？",
        task_type="decision",
    )
    print(result.answer)
    print(f"\n置信度: {result.confidence:.0%}")
    print(f"活跃领域: {result.active_domains}")
    print(f"加载维度: {result.loaded_dimensions}")
    print(f"路由Skill: {result.routed_skills}")
    if result.warnings:
        print(f"⚠️ 警告: {result.warnings}")
