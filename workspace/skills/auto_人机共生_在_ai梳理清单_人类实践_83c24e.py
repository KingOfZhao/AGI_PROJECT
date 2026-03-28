"""
模块名称: skill_recommendation_engine
描述: 实现基于"实践成本"的人机共生任务推荐系统。该模块构建技能依赖与成本图，
      并验证"最近邻推荐算法"是否优于"随机推荐"。

核心功能:
1. 构建技能图谱（Skill Graph），包含依赖关系与实践成本。
2. 基于用户当前状态（已掌握技能与剩余精力）推荐最优技能。
3. 蒙特卡洛模拟验证推荐算法的有效性。

Author: Senior Python Engineer
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import random
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
from collections import deque

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 定义类型别名
SkillId = str
CostValue = float
AdjacencyList = Dict[SkillId, List[SkillId]]

@dataclass
class Skill:
    """技能数据类，包含元信息和实践成本"""
    id: SkillId
    name: str
    base_cost: CostValue  # 基础实践成本 (0.0 到 10.0)
    dependencies: Set[SkillId] = field(default_factory=set)
    utility: float = 1.0  # 技能对AGI系统的效用值

    def __post_init__(self):
        if not (0.0 <= self.base_cost <= 10.0):
            raise ValueError(f"Skill {self.id} cost must be between 0 and 10.")

@dataclass
class UserState:
    """用户状态数据类"""
    acquired_skills: Set[SkillId] = field(default_factory=set)
    current_energy: float = 100.0  # 用户当天的剩余精力值
    
    def can_afford(self, cost: float) -> bool:
        return self.current_energy >= cost

class SkillGraph:
    """
    技能依赖与成本图。
    
    管理技能节点、依赖关系，并计算基于用户状态的动态成本。
    """
    
    def __init__(self, skills: List[Skill]):
        self.skills: Dict[SkillId, Skill] = {s.id: s for s in skills}
        self.graph: AdjacencyList = {s.id: list(s.dependencies) for s in skills}
        logger.info(f"Initialized SkillGraph with {len(self.skills)} skills.")
        
    def _validate_skill_exists(self, skill_id: SkillId):
        if skill_id not in self.skills:
            logger.error(f"Skill ID {skill_id} not found in graph.")
            raise ValueError(f"Skill ID {skill_id} not found.")

    def get_dynamic_cost(self, skill_id: SkillId, user_state: UserState) -> float:
        """
        计算动态实践成本。
        
        基础成本 * (1 + 依赖缺失系数)。
        如果前置技能未掌握，成本显著增加。
        """
        self._validate_skill_exists(skill_id)
        skill = self.skills[skill_id]
        
        missing_deps = skill.dependencies - user_state.acquired_skills
        if not missing_deps:
            return skill.base_cost
        
        # 惩罚系数：每缺失一个依赖，成本增加20%
        penalty = 1.0 + (0.2 * len(missing_deps))
        dynamic_cost = skill.base_cost * penalty
        
        logger.debug(f"Calculated dynamic cost for {skill_id}: {dynamic_cost} (Missing deps: {len(missing_deps)})")
        return dynamic_cost

    def get_unlockable_skills(self, user_state: UserState) -> List[SkillId]:
        """获取所有依赖已满足，但尚未掌握的技能"""
        unlockable = []
        for skill_id, skill in self.skills.items():
            if skill_id in user_state.acquired_skills:
                continue
            
            if skill.dependencies.issubset(user_state.acquired_skills):
                unlockable.append(skill_id)
        return unlockable

class RecommendationEngine:
    """
    推荐引擎核心类。
    实现最近邻推荐与随机推荐策略，并进行效果对比。
    """
    
    def __init__(self, graph: SkillGraph):
        self.graph = graph
        
    def recommend_nearest_neighbor(self, user_state: UserState, top_k: int = 3) -> List[Tuple[SkillId, CostValue]]:
        """
        核心算法：基于最小实践成本（最近邻）的推荐。
        
        策略：在所有可解锁的技能中，优先推荐实践成本（动态）最低的技能。
        这符合"最小阻力路径"原则，旨在维持用户的持续心流体验。
        
        Args:
            user_state: 当前用户状态
            top_k: 返回的推荐数量
            
        Returns:
            推荐列表 [(SkillID, Cost)]
        """
        candidates = self.graph.get_unlockable_skills(user_state)
        if not candidates:
            logger.info("No unlockable skills available.")
            return []

        # 计算所有候选技能的动态成本
        cost_map = {}
        for skill_id in candidates:
            cost = self.graph.get_dynamic_cost(skill_id, user_state)
            cost_map[skill_id] = cost
            
        # 按成本排序
        sorted_skills = sorted(cost_map.items(), key=lambda item: item[1])
        
        # 过滤掉用户精力无法负担的技能
        affordable_recommendations = [
            (sid, cost) for sid, cost in sorted_skills 
            if user_state.can_afford(cost)
        ]
        
        return affordable_recommendations[:top_k]

    def recommend_random(self, user_state: UserState, top_k: int = 3) -> List[Tuple[SkillId, CostValue]]:
        """
        对照算法：随机推荐。
        
        从可解锁技能中随机抽取，不考虑成本优化。
        """
        candidates = self.graph.get_unlockable_skills(user_state)
        if not candidates:
            return []
            
        random.shuffle(candidates)
        recommendations = []
        
        for skill_id in candidates:
            cost = self.graph.get_dynamic_cost(skill_id, user_state)
            if user_state.can_afford(cost):
                recommendations.append((skill_id, cost))
                if len(recommendations) >= top_k:
                    break
                
        return recommendations

def simulate_user_progression(
    engine: RecommendationEngine, 
    initial_state: UserState, 
    strategy: str = "nn",
    max_steps: int = 100
) -> Tuple[int, float]:
    """
    辅助函数：模拟用户的技能习得过程。
    
    Args:
        engine: 推荐引擎实例
        initial_state: 用户初始状态
        strategy: 'nn' (Nearest Neighbor) 或 'random'
        max_steps: 最大模拟步数（防止死循环）
        
    Returns:
        (习得的技能总数, 消耗的总精力)
    """
    current_state = UserState(
        acquired_skills=initial_state.acquired_skills.copy(),
        current_energy=initial_state.current_energy
    )
    
    total_energy_consumed = 0.0
    steps = 0
    
    while steps < max_steps:
        if strategy == "nn":
            recs = engine.recommend_nearest_neighbor(current_state, top_k=1)
        else:
            recs = engine.recommend_random(current_state, top_k=1)
            
        if not recs:
            # 无更多可推荐或精力不足
            break
            
        # 用户接受推荐，更新状态
        skill_id, cost = recs[0]
        current_state.acquired_skills.add(skill_id)
        current_state.current_energy -= cost
        total_energy_consumed += cost
        steps += 1
        
    return len(current_state.acquired_skills), total_energy_consumed

# ============================================================
# 数据生成与主程序逻辑
# ============================================================

def generate_mock_skills(num_skills: int = 50) -> List[Skill]:
    """
    生成模拟技能数据，构建随机依赖图。
    """
    skills = []
    for i in range(num_skills):
        deps = set()
        # 确保依赖关系指向已存在的技能 (DAG性质)
        if i > 0:
            num_deps = random.randint(0, min(3, i))
            possible_deps = [f"skill_{j}" for j in range(i)]
            if possible_deps:
                deps = set(random.sample(possible_deps, num_deps))
                
        skill = Skill(
            id=f"skill_{i}",
            name=f"Capability Module {i}",
            base_cost=random.uniform(1.0, 5.0),
            dependencies=deps
        )
        skills.append(skill)
    return skills

def main():
    """
    主执行函数：验证推荐策略。
    
    场景：
    系统拥有N个技能，用户初始精力有限。
    对比 Nearest Neighbor 策略与 Random 策略在消耗相同精力下能掌握的技能数量。
    """
    logger.info("Starting Recommendation Strategy Validation...")
    
    # 1. 初始化环境
    NUM_SKILLS = 2067  # 模拟大规模技能库 (这里简化为200个用于演示，实际逻辑支持2067)
    NUM_SKILLS_SIM = 200 
    mock_skills = generate_mock_skills(NUM_SKILLS_SIM)
    graph = SkillGraph(mock_skills)
    engine = RecommendationEngine(graph)
    
    # 2. 定义初始状态
    # 假设用户已掌握前5个基础技能，拥有100点精力
    initial_user = UserState(
        acquired_skills={f"skill_{i}" for i in range(5)},
        current_energy=100.0
    )
    
    # 3. 运行模拟对比
    nn_count, nn_cost = simulate_user_progression(engine, initial_user, strategy="nn")
    rand_count, rand_cost = simulate_user_progression(engine, initial_user, strategy="random")
    
    # 4. 输出结果
    print("\n" + "="*40)
    print(f" SIMULATION RESULTS (Total Skills: {NUM_SKILLS_SIM})")
    print("="*40)
    print(f"Strategy: Nearest Neighbor (Cost-Optimized)")
    print(f" - Skills Acquired: {nn_count}")
    print(f" - Total Energy Used: {nn_cost:.2f}")
    print("-" * 40)
    print(f"Strategy: Random Selection")
    print(f" - Skills Acquired: {rand_count}")
    print(f" - Total Energy Used: {rand_cost:.2f}")
    print("="*40)
    
    if nn_count > rand_count:
        print("✅ Conclusion: Nearest Neighbor strategy is superior in skill acquisition density.")
    else:
        print("⚠️ Conclusion: Nearest Neighbor did not outperform Random in this specific run.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"System crashed: {e}", exc_info=True)