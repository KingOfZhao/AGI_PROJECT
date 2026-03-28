"""
Module: computational_economics_manager.py
Description: 计算经济学管理模块，用于为AGI系统的Skill打上计算成本标签，
             并在推理阶段基于资源约束进行决策。
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from functools import wraps

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据模型 ---

@dataclass
class ResourceConstraints:
    """
    资源约束条件的数据结构。
    
    Attributes:
        max_flops (float): 允许的最大浮点运算次数。
        max_memory_mb (float): 允许的最大内存占用（MB）。
        max_latency_ms (float): 允许的最大延迟（毫秒）。
        max_cost_usd (Optional[float]): 允许的最大金钱成本（美元），可选。
    """
    max_flops: float
    max_memory_mb: float
    max_latency_ms: float
    max_cost_usd: Optional[float] = None

    def __post_init__(self):
        """数据验证：确保约束值为非负数。"""
        if self.max_flops < 0 or self.max_memory_mb < 0 or self.max_latency_ms < 0:
            raise ValueError("Resource constraints must be non-negative values.")
        if self.max_cost_usd is not None and self.max_cost_usd < 0:
            raise ValueError("Cost constraint must be non-negative.")

@dataclass
class EconomicSkill:
    """
    封装Skill的元数据，包含计算经济学标签。
    
    Attributes:
        skill_id (str): Skill的唯一标识符。
        description (str): 功能描述。
        avg_flops (float): 平均浮点运算需求。
        avg_memory_mb (float): 平均内存占用。
        avg_latency_ms (float): 平均执行延迟。
        cost_weight (float): 成本权重因子，用于复杂计算。
    """
    skill_id: str
    description: str
    avg_flops: float
    avg_memory_mb: float
    avg_latency_ms: float
    cost_weight: float = 1.0
    # 内部标签，运行时计算
    estimated_cost: float = field(init=False, default=0.0)

    def __post_init__(self):
        if self.avg_flops < 0 or self.avg_memory_mb < 0 or self.avg_latency_ms < 0:
            raise ValueError(f"Skill {self.skill_id} resource metrics cannot be negative.")

# --- 辅助函数 ---

def calculate_weighted_cost(skill: EconomicSkill, price_per_flop: float = 1e-9) -> float:
    """
    辅助函数：根据资源消耗和权重计算综合经济成本。
    
    这是一个简化的成本模型，假设成本与计算量、内存和时间成正比。
    
    Args:
        skill (EconomicSkill): 包含资源估算的Skill对象。
        price_per_flop (float): 每单位FLOP的假设价格。
        
    Returns:
        float: 计算出的综合成本指数。
    """
    try:
        compute_cost = skill.avg_flops * price_per_flop
        # 假设内存和延迟也有对应的换算系数
        memory_cost = skill.avg_memory_mb * 0.001  # 假设的内存单位成本
        latency_cost = skill.avg_latency_ms * 0.0001  # 假设的时间单位成本
        
        total_cost = (compute_cost + memory_cost + latency_cost) * skill.cost_weight
        return round(total_cost, 6)
    except TypeError as e:
        logger.error(f"Type error in cost calculation for {skill.skill_id}: {e}")
        return float('inf')

# --- 核心功能类 ---

class EconomicDecisionEngine:
    """
    核心类：管理Skill注册、打标和基于约束的推理决策。
    """
    
    def __init__(self):
        self.skill_registry: Dict[str, EconomicSkill] = {}
        logger.info("EconomicDecisionEngine initialized.")

    def register_skill(self, skill: EconomicSkill) -> None:
        """
        核心函数1：注册Skill并自动打上计算成本标签。
        
        Args:
            skill (EconomicSkill): 待注册的Skill对象。
        """
        if not isinstance(skill, EconomicSkill):
            logger.error("Invalid object type provided for registration.")
            raise TypeError("Item must be an instance of EconomicSkill")
            
        # 计算并打上成本标签
        skill.estimated_cost = calculate_weighted_cost(skill)
        self.skill_registry[skill.skill_id] = skill
        logger.info(f"Skill registered: {skill.skill_id} | Est. Cost: {skill.estimated_cost}")

    def select_optimal_skill(
        self, 
        candidate_ids: List[str], 
        constraints: ResourceConstraints
    ) -> Optional[EconomicSkill]:
        """
        核心函数2：在推理时根据资源约束选择最优Skill。
        
        逻辑：
        1. 过滤掉不符合硬性资源约束的Skill。
        2. 在剩余Skill中选择成本最低的。
        
        Args:
            candidate_ids (List[str]): 候选Skill ID列表。
            constraints (ResourceConstraints): 资源约束对象。
            
        Returns:
            Optional[EconomicSkill]: 最优的Skill对象，若无满足条件则返回None。
        """
        logger.info(f"Selecting skill from candidates: {candidate_ids} with constraints.")
        
        feasible_skills = []
        
        for sid in candidate_ids:
            if sid not in self.skill_registry:
                logger.warning(f"Skill ID {sid} not found in registry. Skipping.")
                continue
            
            skill = self.skill_registry[sid]
            
            # 边界检查与约束验证
            if (skill.avg_flops <= constraints.max_flops and 
                skill.avg_memory_mb <= constraints.max_memory_mb and 
                skill.avg_latency_ms <= constraints.max_latency_ms):
                
                # 如果设置了金钱约束，检查成本
                if constraints.max_cost_usd is not None:
                    if skill.estimated_cost > constraints.max_cost_usd:
                        logger.debug(f"Skill {sid} exceeded cost budget.")
                        continue
                
                feasible_skills.append(skill)
            else:
                logger.debug(f"Skill {sid} exceeded hardware resource limits.")
        
        if not feasible_skills:
            logger.warning("No feasible skills found under current constraints.")
            return None
            
        # 按预估成本排序，选择成本最低的 (经济最优)
        optimal_skill = min(feasible_skills, key=lambda s: s.estimated_cost)
        logger.info(f"Selected optimal skill: {optimal_skill.skill_id}")
        return optimal_skill

# --- 装饰器/工具 (额外功能) ---

def measure_real_cost(func: Callable) -> Callable:
    """
    一个装饰器，用于在实际运行函数时测量并记录时间和内存（近似值）。
    用于后续更新Skill的经济标签。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            logger.info(f"Execution Metric: {func.__name__} took {duration_ms:.2f} ms")
            # 在真实场景中，这里会将数据回传给系统以更新avg_latency_ms
    return wrapper

# --- 使用示例 ---

if __name__ == "__main__":
    try:
        # 1. 初始化决策引擎
        engine = EconomicDecisionEngine()

        # 2. 定义几个不同的Skill（模拟不同复杂度的模型）
        # Skill A: 轻量级，快速，低精度
        skill_light = EconomicSkill(
            skill_id="lightweight_classifier",
            description="Fast text classification",
            avg_flops=1e6,      # 1 MFLOPS
            avg_memory_mb=50,
            avg_latency_ms=10,
            cost_weight=0.5     # 运行便宜
        )

        # Skill B: 重量级，慢，高精度
        skill_heavy = EconomicSkill(
            skill_id="heavy_llm_reasoning",
            description="Complex reasoning with LLM",
            avg_flops=1e12,     # 1 TFLOPS
            avg_memory_mb=16000,
            avg_latency_ms=5000,
            cost_weight=5.0     # 运行昂贵
        )

        # 3. 注册Skill（自动打标签）
        engine.register_skill(skill_light)
        engine.register_skill(skill_heavy)

        # 4. 定义资源约束场景
        # 场景 A: 移动设备/边缘计算，资源受限
        edge_constraints = ResourceConstraints(
            max_flops=1e9,
            max_memory_mb=500,
            max_latency_ms=200
        )

        # 场景 B: 服务器集群，资源充足
        server_constraints = ResourceConstraints(
            max_flops=1e14,
            max_memory_mb=32000,
            max_latency_ms=10000,
            max_cost_usd=0.05  # 设定预算上限
        )

        # 5. 推理决策
        candidates = ["lightweight_classifier", "heavy_llm_reasoning"]

        print("\n--- Decision for Edge Device ---")
        best_for_edge = engine.select_optimal_skill(candidates, edge_constraints)
        if best_for_edge:
            print(f"Chosen: {best_for_edge.skill_id}")
            print(f"Cost: {best_for_edge.estimated_cost}")

        print("\n--- Decision for Server ---")
        best_for_server = engine.select_optimal_skill(candidates, server_constraints)
        if best_for_server:
            print(f"Chosen: {best_for_server.skill_id}")
            print(f"Cost: {best_for_server.estimated_cost}")
            
        # 6. 边界测试：极度严格的约束
        impossible_constraints = ResourceConstraints(
            max_flops=10,
            max_memory_mb=1,
            max_latency_ms=1
        )
        print("\n--- Decision for Impossible Constraints ---")
        best_impossible = engine.select_optimal_skill(candidates, impossible_constraints)
        print(f"Result: {best_impossible}")

    except Exception as e:
        logger.error(f"System crashed: {e}", exc_info=True)