"""
伟人竞技场引擎 — 多视角推演增强
==================================
数据源: data/sage_arena.json (100人 × 419维能力)

核心机制:
  1. 根据推演主题选择领域相关伟人(3-5人)
  2. 每位伟人的哲学作为推理约束/透镜
  3. 多视角交叉碰撞, 产出增强结论

不是模拟人格对话, 而是用伟人思维框架约束推演方向。
避免幻觉: 伟人只提供"思考方向", 不编造未验证的结论。
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path


@dataclass
class Sage:
    """伟人"""
    name: str
    domain: str
    era: str
    philosophy: str
    abilities: Dict[str, int]  # 419维 or 7维
    # 运行时计算
    relevance_score: float = 0.0
    perspective: str = ""  # 针对特定主题的视角提示


@dataclass
class ArenaResult:
    """竞技场推演结果"""
    topic: str
    sages_selected: List[str]
    perspectives: Dict[str, str]  # sage_name → perspective
    consensus: str  # 多视角共识
    conflicts: List[str]  # 视角冲突
    blind_spots: List[str]  # 共同盲区
    enhanced_facts: List[str]  # 新涌现的已知
    open_questions: List[str]  # 新涌现的未知


# === DiePre领域核心能力维度 ===
DIEPRE_CORE_DIMENSIONS = [
    "第一性原理",   # 从物理基本定律推导
    "数学建模",     # 公式化
    "实验验证",     # 实测数据支撑
    "工程实践",     # 可制造性
    "形式化推理",   # 逻辑严谨
    "跨学科迁移",   # 材料/力学/统计交叉
    "系统工程",     # 整体误差控制
    "直觉推理",     # 经验判断
    "风险控制",     # 安全裕度
    "细节执行",     # 参数精度
]

# === 通用推演能力维度 ===
GENERAL_DIMENSIONS = [
    "辩证思维", "抽象思维", "归纳推理", "因果推理",
    "矛盾分析", "持久专注", "独立思考", "知识传承",
]


class SageArena:
    """
    伟人竞技场引擎
    
    使用流程:
    1. load_sages() — 加载伟人数据
    2. select_for_topic(topic, dimensions) — 选出相关伟人
    3. generate_perspectives(topic) — 生成各视角
    4. synthesize() — 交叉碰撞, 产出增强结论
    """
    
    def __init__(self, data_path: str = None):
        if data_path is None:
            data_path = str(Path(__file__).parent.parent / "data" / "sage_arena.json")
        self.sages: Dict[str, Sage] = {}
        self._load(data_path)
    
    def _load(self, path: str):
        with open(path) as f:
            data = json.load(f)
        for name, info in data["sages"].items():
            self.sages[name] = Sage(
                name=name,
                domain=info.get("domain", ""),
                era=info.get("era", ""),
                philosophy=info.get("philosophy", ""),
                abilities=info.get("abilities", {}),
            )
    
    def select_for_topic(
        self,
        topic: str,
        dimensions: List[str] = None,
        top_n: int = 5,
        diversity: bool = True,
    ) -> List[Sage]:
        """
        根据主题选择最相关的伟人
        
        Args:
            topic: 推演主题描述
            dimensions: 评估维度 (默认DIEPRE核心)
            top_n: 返回数量
            diversity: 是否强制领域多样性
        """
        if dimensions is None:
            dimensions = DIEPRE_CORE_DIMENSIONS
        
        # 主题关键词匹配 → 额外加权
        topic_keywords = {
            "误差": ["实验验证", "数学建模", "形式化推理"],
            "公式": ["数学建模", "第一性原理", "形式化推理"],
            "材料": ["跨学科迁移", "实验验证", "工程实践"],
            "标准": ["制度设计", "形式化推理", "系统工程"],
            "裱合": ["跨学科迁移", "工程实践", "实验验证"],
            "压痕": ["工程实践", "实验验证", "数学建模"],
            "公差": ["数学建模", "风险控制", "系统工程"],
            "微瓦楞": ["第一性原理", "跨学科迁移", "细节执行"],
            "K因子": ["数学建模", "第一性原理", "实验验证"],
            "RSS": ["数学建模", "形式化推理", "风险控制"],
            "分布": ["数学建模", "形式化推理", "抽象思维"],
            "相变": ["第一性原理", "抽象思维", "范式革命"],
            "膨胀": ["实验验证", "数学建模", "跨学科迁移"],
            "收缩": ["实验验证", "数学建模", "因果推理"],
            "折叠": ["工程实践", "实验验证", "数学建模"],
            "爆线": ["风险控制", "实验验证", "工程实践"],
        }
        
        extra_dims = set()
        for kw, dims in topic_keywords.items():
            if kw in topic:
                extra_dims.update(dims)
        eval_dims = list(set(dimensions + list(extra_dims)))
        
        # 评分: 加权平均 + 领域匹配加分 + 最高分惩罚(避免全能型垄断)
        scored = []
        for name, sage in self.sages.items():
            scores = [sage.abilities.get(d, 0) for d in eval_dims]
            total = sum(scores)
            avg = total / len(eval_dims) if eval_dims else 0
            
            # 领域匹配加分: domain名称与topic关键词匹配
            domain_bonus = 0
            topic_lower = topic.lower()
            for kw in sage.domain.split("/"):
                if kw in topic_lower or any(c in topic for c in kw):
                    domain_bonus = 3.0
            
            # 区分度: 用方差而非均值 — 全能型(全99)方差=0, 专家型有高分峰
            if scores:
                mean_s = sum(scores) / len(scores)
                variance = sum((s - mean_s) ** 2 for s in scores) / len(scores)
                # 方差越大说明越有专长, 给加分
                specialty_bonus = (variance ** 0.5) * 0.1
            else:
                specialty_bonus = 0
            
            # 最高分截断: 如果太多维=99, 降低区分度(全99说明数据没有区分力)
            max_count = sum(1 for s in scores if s >= 99)
            saturation_penalty = max_count * 0.05  # 每99分一个扣0.05
            
            final_score = avg + domain_bonus + specialty_bonus - saturation_penalty
            sage.relevance_score = final_score
            scored.append(sage)
        
        # 排序
        scored.sort(key=lambda s: s.relevance_score, reverse=True)
        
        # 多样性选择: 确保不同领域
        if diversity:
            selected = []
            domains_seen = set()
            for s in scored:
                if len(selected) >= top_n:
                    break
                if s.domain not in domains_seen or len(selected) >= top_n - 1:
                    selected.append(s)
                    domains_seen.add(s.domain)
            return selected
        else:
            return scored[:top_n]
    
    def generate_perspectives(self, topic: str, sages: List[Sage]) -> Dict[str, str]:
        """
        为每位伟人生成针对该主题的推理视角
        
        不是模拟对话, 而是提取哲学中与主题相关的思考方向
        """
        perspectives = {}
        
        for sage in sages:
            # 从哲学和领域中提取推理方向
            perspective = self._build_perspective(sage, topic)
            perspectives[sage.name] = perspective
            sage.perspective = perspective
        
        return perspectives
    
    def _build_perspective(self, sage: Sage, topic: str) -> str:
        """构建单视角推理提示"""
        # 核心思维框架
        frameworks = {
            "第一性原理": "从物理基本定律出发推导，不依赖经验公式",
            "数学建模": "将问题形式化为数学表达式，追求精确解",
            "实验验证": "任何结论必须有实测数据支撑，拒绝纯理论推导",
            "工程实践": "必须考虑可制造性和工艺约束，理想解不等于工程解",
            "形式化推理": "每一步推理必须逻辑严谨，不允许跳跃",
            "跨学科迁移": "从其他领域借鉴已验证的模型和方法",
            "系统工程": "关注整体误差链，局部最优不等于全局最优",
            "矛盾分析": "识别主要矛盾和次要矛盾，优先解决主要矛盾",
            "辩证思维": "考虑问题的正反两面，避免极端化",
            "风险控制": "在最坏情况下仍能保证安全裕度",
            "细节执行": "小数点后第三位的差异决定了产品成败",
            "范式革命": "当现有框架无法解释现象时，勇于更换框架",
        }
        
        # 选出该伟人最强的3个相关框架
        top_abilities = sorted(
            sage.abilities.items(), key=lambda x: x[1], reverse=True
        )[:10]
        
        relevant_frameworks = []
        for dim, score in top_abilities:
            if dim in frameworks and score >= 90:
                relevant_frameworks.append(frameworks[dim])
        
        if not relevant_frameworks:
            relevant_frameworks = ["从该领域的核心方法论出发分析"]
        
        # 构建视角
        parts = [
            f"【{sage.name}·{sage.domain}】",
            f"哲学: {sage.philosophy}",
            f"推理框架: {'; '.join(relevant_frameworks[:3])}",
        ]
        
        return "\n".join(parts)
    
    def synthesize(
        self,
        topic: str,
        known_facts: List[str],
        sages: List[Sage],
        perspectives: Dict[str, str],
    ) -> ArenaResult:
        """
        多视角交叉碰撞, 产出增强结论
        
        这是核心方法: 将已知事实通过多个视角透镜分析
        """
        conflicts = []
        blind_spots = []
        enhanced = []
        questions = []
        
        # 收集各视角的关键词/方向
        all_directions = []
        for name, persp in perspectives.items():
            sage = self.sages[name]
            # 从能力维度提取推理方向
            top_dims = sorted(
                sage.abilities.items(), key=lambda x: x[1], reverse=True
            )[:5]
            directions = [d for d, s in top_dims if s >= 95]
            all_directions.append((name, directions, persp))
        
        # === 交叉碰撞 ===
        
        # 1. 检测视角冲突
        if len(all_directions) >= 2:
            # 找出不同伟人强调但方向相反的能力
            positive_dims = set()
            caution_dims = set()
            for name, dims, _ in all_directions:
                for d in dims:
                    if d in ["风险控制", "矛盾分析", "辩证思维", "细节执行"]:
                        caution_dims.add(d)
                    else:
                        positive_dims.add(d)
            
            if positive_dims and caution_dims:
                conflicts.append(
                    f"激进派(追求{', '.join(list(positive_dims)[:2])}) "
                    f"vs 保守派(强调{', '.join(list(caution_dims)[:2])})"
                )
        
        # 2. 识别共同盲区
        all_top_dims = set()
        for _, dims, _ in all_directions:
            all_top_dims.update(dims)
        
        potentially_missing = [
            "实验验证", "工程实践", "风险控制", "细节执行",
            "跨学科迁移", "形式化推理",
        ]
        for dim in potentially_missing:
            if dim not in all_top_dims:
                blind_spots.append(f"所有选中伟人均未强调「{dim}」— 该维度可能被低估")
        
        # 3. 增强已知事实
        for fact in known_facts:
            # 检查是否有伟人的视角可以深化该事实
            for name, dims, persp in all_directions:
                for dim in dims:
                    if any(kw in fact for kw in self._dim_to_keywords(dim)):
                        enhanced.append(
                            f"[{name}·{dim}] {fact} → 需从{dim}角度进一步验证"
                        )
                        break
        
        # 4. 生成共识和问题
        consensus_parts = []
        for name, dims, _ in all_directions:
            if "第一性原理" in dims:
                consensus_parts.append("从基本物理定律推导")
            if "实验验证" in dims:
                consensus_parts.append("实测数据优先")
            if "数学建模" in dims:
                consensus_parts.append("公式化精确表达")
            if "系统工程" in dims:
                consensus_parts.append("全局误差链控制")
        
        consensus = "; ".join(set(consensus_parts)) if consensus_parts else "多视角分析完成"
        
        # 从盲区和冲突中生成问题
        for bs in blind_spots:
            questions.append(f"需要补充「{bs.split('—')[0].strip().replace('「','').replace('」','')}」维度的分析")
        for c in conflicts:
            questions.append(f"如何平衡{c}的张力?")
        
        return ArenaResult(
            topic=topic,
            sages_selected=[s.name for s in sages],
            perspectives=perspectives,
            consensus=consensus,
            conflicts=conflicts,
            blind_spots=blind_spots,
            enhanced_facts=enhanced,
            open_questions=questions,
        )
    
    def _dim_to_keywords(self, dim: str) -> List[str]:
        """能力维度 → 事实关键词映射"""
        mapping = {
            "第一性原理": ["公式", "定律", "基本", "推导", "物理"],
            "数学建模": ["公式", "系数", "参数", "模型", "计算"],
            "实验验证": ["实测", "实验", "数据", "验证", "测量"],
            "工程实践": ["工艺", "制造", "生产", "设备", "可加工"],
            "形式化推理": ["逻辑", "推导", "证明", "严格", "定义"],
            "跨学科迁移": ["借鉴", "交叉", "多学科", "类比", "迁移"],
            "系统工程": ["整体", "全局", "链", "集成", "综合"],
            "风险控制": ["安全", "裕度", "极限", "失效", "临界"],
            "细节执行": ["精度", "公差", "偏差", "小数", "修正"],
        }
        return mapping.get(dim, [dim])
    
    def run_arena(
        self,
        topic: str,
        known_facts: List[str],
        dimensions: List[str] = None,
        top_n: int = 5,
    ) -> ArenaResult:
        """一键运行竞技场"""
        sages = self.select_for_topic(topic, dimensions, top_n)
        perspectives = self.generate_perspectives(topic, sages)
        result = self.synthesize(topic, known_facts, sages, perspectives)
        return result
    
    def print_result(self, result: ArenaResult):
        """打印竞技场结果"""
        print(f"\n{'='*70}")
        print(f"  伟人竞技场 — {result.topic}")
        print(f"{'='*70}")
        
        print(f"\n🎯 参与伟人: {', '.join(result.sages_selected)}")
        
        print(f"\n--- 各视角 ---")
        for name, persp in result.perspectives.items():
            print(f"\n{persp}")
        
        print(f"\n--- 共识 ---")
        print(f"  {result.consensus}")
        
        if result.conflicts:
            print(f"\n⚡ 视角冲突:")
            for c in result.conflicts:
                print(f"  • {c}")
        
        if result.blind_spots:
            print(f"\n🔍 共同盲区:")
            for bs in result.blind_spots:
                print(f"  • {bs}")
        
        if result.enhanced_facts:
            print(f"\n💡 增强分析:")
            for ef in result.enhanced_facts[:5]:
                print(f"  • {ef}")
        
        if result.open_questions:
            print(f"\n❓ 涌现问题:")
            for q in result.open_questions:
                print(f"  • {q}")


if __name__ == "__main__":
    arena = SageArena()
    
    print(f"已加载 {len(arena.sages)} 位伟人")
    
    # === 场景1: K因子相变模型 ===
    print("\n" + "=" * 70)
    print("  场景1: K因子相变模型推演增强")
    print("=" * 70)
    
    r1 = arena.run_arena(
        topic="K因子相变模型 — 压痕深度与材料刚度的非线性关系",
        known_facts=[
            "K=0.35(单瓦楞正常), K=0.25(爆线临界)",
            "d/T≥0.65触发相变, K骤降",
            "MC≥16%触发湿态相变",
            "K因子不是连续函数, 存在相变边界",
        ],
        top_n=5,
    )
    arena.print_result(r1)
    
    # === 场景2: ±0.5mm精度不可达 ===
    print("\n" + "=" * 70)
    print("  场景2: ±0.5mm精密级数学不可达的工程解法")
    print("=" * 70)
    
    r2 = arena.run_arena(
        topic="RSS修正后±0.5mm不可达(Bobst=0.687mm)的工程解决方案",
        known_facts=[
            "Bobst修正RSS总误差0.687mm, 国产1.155mm",
            "6种非正态分布修正系数已建立",
            "确定性误差0.18mm不可压缩",
            "随机误差0.363mm主导",
        ],
        top_n=5,
    )
    arena.print_result(r2)
    
    # === 场景3: 微瓦楞标准盲区 ===
    print("\n" + "=" * 70)
    print("  场景3: 微瓦楞E/F槽宽修正 — GB标准缺失的填补策略")
    print("=" * 70)
    
    r3 = arena.run_arena(
        topic="微瓦楞E/F槽宽修正公式 — GB标准完全缺失的填补策略",
        known_facts=[
            "FEFCO vs JIS槽宽差异≥0.5mm",
            "DiePre修正公式: W=(t+C_res)×K_stru",
            "GB在微瓦楞领域4个参数完全缺失",
            "JIS Z 1506原文未获取",
        ],
        top_n=5,
    )
    arena.print_result(r3)
    
    # === 验证: 伟人选择是否合理 ===
    print("\n" + "=" * 70)
    print("  验证: 伟人选择相关性")
    print("=" * 70)
    
    test_topics = [
        "误差预算RSS计算",
        "裱合胶水收缩耦合",
        "扇形误差公式",
        "清废临界角",
        "出口标准切换",
    ]
    
    for topic in test_topics:
        sages = arena.select_for_topic(topic, top_n=3)
        names = [(s.name, s.domain, f"{s.relevance_score:.1f}") for s in sages]
        print(f"  {topic}: {', '.join(f'{n}({d},{s})' for n,d,s in names)}")
