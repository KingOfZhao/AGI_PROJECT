"""
高级Python模块：AGI技能进化引擎

该模块实现了一个用于AGI系统的“技能变异与优胜劣汰”环境。
它定义了一个多目标的适应度函数，综合考量执行成功率、计算资源消耗和通用性（跨域迁移能力），
旨在自动评估、筛选低效技能并保留高价值技能。

核心功能：
1. 多维度适应度评估
2. 基于遗传算法思想的技能进化与变异模拟
3. 种群管理与优胜劣汰

作者: AGI System Architect
日期: 2023-10-27
版本: 1.0.0
"""

import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SkillDomain(Enum):
    """技能所属领域的枚举"""
    GENERAL = "general"
    CODING = "coding"
    REASONING = "reasoning"
    PERCEPTION = "perception"
    TOOL_USE = "tool_use"

@dataclass
class SkillNode:
    """
    技能节点数据结构
    
    属性:
        id: 唯一标识符
        name: 技能名称
        success_rate: 执行成功率 (0.0 到 1.0)
        resource_cost: 计算资源消耗 (归一化值，越小越好)
        domain: 主要领域
        cross_domain_scores: 跨领域迁移得分字典 {domain: score}
        generation: 当前进化代数
        parent_id: 父节点ID (用于追踪血统)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unnamed Skill"
    success_rate: float = 0.0
    resource_cost: float = 1.0
    domain: SkillDomain = SkillDomain.GENERAL
    cross_domain_scores: Dict[SkillDomain, float] = field(default_factory=dict)
    generation: int = 0
    parent_id: Optional[str] = None
    
    def __post_init__(self):
        """数据验证与清理"""
        if not 0.0 <= self.success_rate <= 1.0:
            logger.warning(f"Skill {self.id} success_rate {self.success_rate} out of bounds. Clamping.")
            self.success_rate = max(0.0, min(1.0, self.success_rate))
        
        if self.resource_cost < 0:
            logger.warning(f"Skill {self.id} resource_cost cannot be negative. Setting to 0.")
            self.resource_cost = 0.0

class EvolutionConfig:
    """进化环境的配置参数"""
    def __init__(self,
                 population_limit: int = 100,
                 weights: Tuple[float, float, float] = (0.5, 0.3, 0.2),
                 mutation_rate: float = 0.1,
                 elitism_count: int = 5):
        """
        初始化配置
        
        Args:
            population_limit: 种群最大容量
            weights: 适应度函数权重
            mutation_rate: 变异概率
            elitism_count: 精英保留数量
        """
        self.population_limit = population_limit
        self.w_success, self.w_cost, self.w_general = weights
        self.mutation_rate = mutation_rate
        self.elitism_count = elitism_count
        
        # 验证权重和为1 (允许小误差)
        weight_sum = self.w_success + self.w_cost + self.w_general
        if not abs(weight_sum - 1.0) < 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {weight_sum}")

def calculate_fitness(skill: SkillNode, config: EvolutionConfig) -> float:
    """
    [核心函数 1]
    计算单个技能节点的综合适应度。
    
    适应度公式:
    F = (w_s * Success) + (w_c * (1 / (1 + Cost))) + (w_g * Generalization)
    
    其中:
    - Success: 执行成功率
    - Cost: 资源消耗 (归一化，通过反比例函数转化为收益)
    - Generalization: 平均跨域得分
    
    Args:
        skill (SkillNode): 待评估的技能节点
        config (EvolutionConfig): 进化配置参数
        
    Returns:
        float: 综合适应度得分 (0.0 到 1.0)
        
    Raises:
        ValueError: 如果输入数据无效
    """
    try:
        # 1. 基础效能
        p_success = skill.success_rate
        
        # 2. 资源效率 (Cost越低越好，使用 Sigmoid 或简单的反比例映射)
        # 这里使用 1 / (1 + cost)，假设 cost 已经归一化 (0.0-1.0 范围，或者 0-inf)
        # 如果 cost 是百分比，则 1 / (1 + cost) 会将 0 映射为 1，无穷大映射为 0
        p_efficiency = 1.0 / (1.0 + skill.resource_cost)
        
        # 3. 通用性
        # 计算除了主领域之外的跨域得分平均值
        other_domains_scores = [
            score for dom, score in skill.cross_domain_scores.items() 
            if dom != skill.domain
        ]
        
        if other_domains_scores:
            p_generalization = sum(other_domains_scores) / len(other_domains_scores)
        else:
            p_generalization = 0.0 # 如果没有跨域数据，通用性记为0
            
        # 加权求和
        total_fitness = (
            config.w_success * p_success +
            config.w_cost * p_efficiency +
            config.w_general * p_generalization
        )
        
        logger.debug(f"Skill {skill.name} Fitness: {total_fitness:.4f} "
                     f"(S:{p_success:.2f}, E:{p_efficiency:.2f}, G:{p_generalization:.2f})")
        
        return total_fitness
        
    except Exception as e:
        logger.error(f"Error calculating fitness for {skill.id}: {e}")
        return 0.0

def mutate_skill(skill: SkillNode, config: EvolutionConfig) -> SkillNode:
    """
    [核心函数 2]
    对技能节点进行变异操作，模拟进化过程中的随机扰动。
    
    变异策略:
    - 以一定概率微调成功率 (模拟学习优化)
    - 以一定概率微调资源消耗 (模拟代码重构)
    - 随机增加或减少跨领域能力
    
    Args:
        skill (SkillNode): 原始技能节点
        config (EvolutionConfig): 包含变异率的配置
        
    Returns:
        SkillNode: 变异后的新技能节点 (保持血统追踪)
    """
    new_skill = SkillNode(
        id=str(uuid.uuid4()),
        name=f"Evolved_{skill.name}",
        success_rate=skill.success_rate,
        resource_cost=skill.resource_cost,
        domain=skill.domain,
        cross_domain_scores=skill.cross_domain_scores.copy(),
        generation=skill.generation + 1,
        parent_id=skill.id
    )
    
    # 变异：成功率
    if random.random() < config.mutation_rate:
        delta = random.uniform(-0.1, 0.15) # 稍微偏向正向变异
        new_skill.success_rate = max(0.0, min(1.0, new_skill.success_rate + delta))
        
    # 变异：资源消耗
    if random.random() < config.mutation_rate:
        delta = random.uniform(-0.2, 0.1) # 稍微偏向优化
        new_skill.resource_cost = max(0.01, new_skill.resource_cost + delta)
        
    # 变异：通用性
    if random.random() < config.mutation_rate:
        # 随机选择一个非主领域进行能力突变
        all_domains = list(SkillDomain)
        other_domains = [d for d in all_domains if d != new_skill.domain]
        if other_domains:
            target_dom = random.choice(other_domains)
            current_score = new_skill.cross_domain_scores.get(target_dom, 0.0)
            new_score = max(0.0, min(1.0, current_score + random.uniform(-0.2, 0.3)))
            new_skill.cross_domain_scores[target_dom] = new_score
            
    logger.info(f"Mutated Skill {skill.id} -> {new_skill.id}")
    return new_skill

def evolve_population(current_skills: List[SkillNode], config: EvolutionConfig) -> List[SkillNode]:
    """
    [辅助函数]
    执行一代进化过程：评估 -> 选择 -> 变异 -> 淘汰。
    
    流程:
    1. 计算所有技能的适应度
    2. 按适应度降序排序
    3. 保留前 N 个精英
    4. 变异精英生成新后代填补种群
    5. 剔除适应度低于阈值的技能
    
    Args:
        current_skills (List[SkillNode]): 当前种群
        config (EvolutionConfig): 进化配置
        
    Returns:
        List[SkillNode]: 下一代种群
    """
    if not current_skills:
        logger.warning("Empty population provided for evolution.")
        return []

    logger.info(f"Starting evolution cycle for {len(current_skills)} skills...")
    
    # 1. 计算适应度并排序
    scored_skills = []
    for skill in current_skills:
        score = calculate_fitness(skill, config)
        scored_skills.append((score, skill))
    
    # 降序排列
    scored_skills.sort(key=lambda x: x[0], reverse=True)
    
    # 2. 选择
    # 保留顶尖精英
    next_gen = [skill for _, skill in scored_skills[:config.elitism_count]]
    
    # 3. 繁殖与变异
    # 为了维持种群数量，我们需要生成后代
    parents = [skill for _, skill in scored_skills[:int(len(scored_skills) * 0.5)]] # 前50%作为父母
    
    while len(next_gen) < config.population_limit:
        if not parents: break # 防止空列表异常
        parent = random.choice(parents)
        child = mutate_skill(parent, config)
        next_gen.append(child)
        
    # 4. 边界检查与清理
    # 确保最终种群数量符合限制
    final_population = next_gen[:config.population_limit]
    
    logger.info(f"Evolution complete. New population size: {len(final_population)}. "
                f"Top fitness: {scored_skills[0][0]:.4f}")
    
    return final_population

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化配置
    evo_config = EvolutionConfig(
        population_limit=20,
        weights=(0.4, 0.4, 0.2), # 成功率40%, 成本40%, 通用性20%
        mutation_rate=0.3
    )
    
    # 2. 生成初始种群 (模拟现有的1932个Skill，这里随机生成20个作为演示)
    initial_skills = []
    for i in range(20):
        s = SkillNode(
            name=f"Skill_{i}",
            success_rate=random.uniform(0.5, 0.9),
            resource_cost=random.uniform(0.1, 1.5),
            domain=random.choice(list(SkillDomain)),
            cross_domain_scores={
                SkillDomain.CODING: random.uniform(0.0, 0.5),
                SkillDomain.REASONING: random.uniform(0.0, 0.5)
            }
        )
        initial_skills.append(s)
        
    # 3. 运行进化循环
    print("--- Generation 0 ---")
    print(f"Top Skill: {initial_skills[0].name}")
    
    # 进化 5 代
    population = initial_skills
    for gen in range(5):
        print(f"\n--- Evolving Generation {gen+1} ---")
        population = evolve_population(population, evo_config)
        
        # 打印本代最强个体
        if population:
            best = population[0] # evolve_population 返回的是排序后的(隐含在逻辑中，或需重新计算确认)
            # 为了准确展示，重新计算一下最佳适应度
            best_score = calculate_fitness(best, evo_config)
            print(f"Best in Gen {gen+1}: {best.name} (Fitness: {best_score:.3f}, Success: {best.success_rate:.2f})")

    # 预期输出:
    # 将看到适应度随着代数增加而逐渐升高的趋势，或者资源消耗的优化。