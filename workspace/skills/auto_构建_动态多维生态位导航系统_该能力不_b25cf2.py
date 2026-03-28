"""
Module: dynamic_niche_navigation_system
Description: 构建动态多维生态位导航系统，模拟企业或个人的核心竞争力演化，
             实时计算边际适应度，并在竞争强度过高时触发生态位偏移机制。
Author: Advanced Python Engineer for AGI System
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import math
import numpy as np
from typing import List, Dict, Tuple, Optional, Union

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
Vector = List[float]
Matrix = List[List[float]]

class DynamicNicheNavigationSystem:
    """
    动态多维生态位导航系统。
    
    该系统通过模拟生物演化机制，分析当前竞争环境（拥挤效应），
    计算边际适应度，并自动寻找低竞争、高收益的蓝海区域。
    
    Attributes:
        current_position (np.ndarray): 当前在多维资源空间中的坐标。
        energy_capital (float): 当前持有的能量/资本。
        mutation_rate (float): 探索新领域时的变异/创新程度。
        crowding_threshold (float): 触发生态位偏移的拥挤度阈值。
    """

    def __init__(self, 
                 initial_position: Vector, 
                 initial_capital: float, 
                 mutation_rate: float = 0.1, 
                 crowding_threshold: float = 0.75) -> None:
        """
        初始化导航系统。

        Args:
            initial_position (Vector): 初始核心竞争力坐标（例如：技术含量, 市场规模, 创新指数）。
            initial_capital (float): 初始资本。
            mutation_rate (float): 变异率，决定探索的激进程度。
            crowding_threshold (float): 拥挤阈值 (0.0 到 1.0)。

        Raises:
            ValueError: 如果输入参数不符合逻辑约束。
        """
        self.current_position = np.array(initial_position, dtype=float)
        self.energy_capital = initial_capital
        self.mutation_rate = mutation_rate
        self.crowding_threshold = crowding_threshold
        
        # 内部状态
        self._history: List[Dict] = []
        self._validate_inputs()
        
        logger.info(f"System initialized at position {self.current_position} with capital {self.energy_capital}")

    def _validate_inputs(self) -> None:
        """验证输入数据的合法性。"""
        if len(self.current_position) == 0:
            raise ValueError("Initial position vector cannot be empty.")
        if self.energy_capital <= 0:
            raise ValueError("Initial capital must be positive.")
        if not 0 <= self.crowding_threshold <= 1:
            raise ValueError("Crowding threshold must be between 0 and 1.")

    def calculate_crowding_intensity(self, competitor_positions: Matrix) -> float:
        """
        计算当前坐标的拥挤强度（竞争强度）。
        
        使用高斯核密度估计的简化版本来模拟拥挤效应。
        距离越近的竞争对手贡献越大的拥挤度。

        Args:
            competitor_positions (Matrix): 竞争对手在多维空间中的坐标列表。

        Returns:
            float: 标准化后的拥挤强度 (0.0 到 1.0)。
        """
        if not competitor_positions:
            return 0.0
        
        try:
            current = self.current_position
            distances = []
            for comp_pos in competitor_positions:
                comp_arr = np.array(comp_pos)
                if comp_arr.shape != current.shape:
                    logger.warning(f"Competitor dimension mismatch: {comp_arr.shape} vs {current.shape}")
                    continue
                
                # 计算欧几里得距离
                dist = np.linalg.norm(current - comp_arr)
                distances.append(dist)
            
            if not distances:
                return 0.0

            # 模拟拥挤度：距离越近，拥挤度越高。使用指数衰减
            # 1 / (1 + dist) 模型
            raw_crowding = sum([1 / (1 + d) for d in distances])
            
            # 归一化处理 (简单的sigmoid归一化或最大值限制)
            # 这里假设 crowded 度随着数量增加无界，但我们限制在 0-1 之间用于决策
            normalized = 1 - math.exp(-raw_crowding * 0.1) 
            
            logger.debug(f"Calculated crowding intensity: {normalized:.4f}")
            return normalized

        except Exception as e:
            logger.error(f"Error calculating crowding intensity: {e}")
            return 0.0

    def calculate_marginal_fitness(self, resource_richness: float, crowding_intensity: float) -> float:
        """
        计算边际适应度。
        
        基于热力学熵增原理和资源收益递减规律。
        Fitness = (Resource * Efficiency) - (Entropy Cost * Crowding)

        Args:
            resource_richness (float): 当前领域的潜在资源量 (0.0-1.0)。
            crowding_intensity (float): 当前领域的拥挤度。

        Returns:
            float: 净适应度/收益。
        """
        # 基础收益
        potential_gain = resource_richness * self.energy_capital
        
        # 拥挤导致的内耗成本 (熵增)
        friction_cost = crowding_intensity * math.log(1 + self.energy_capital) * 0.5
        
        fitness = potential_gain - friction_cost
        logger.info(f"Fitness calculated: {fitness:.2f} (Gain: {potential_gain:.2f}, Cost: {friction_cost:.2f})")
        return fitness

    def trigger_niche_shift(self, knowledge_base: Dict[str, Vector]) -> np.ndarray:
        """
        触发生态位偏移（蓝海战略）。
        
        利用交叉学科知识（knowledge_base）寻找与当前位置距离较远，
        但能量环境较好的新坐标。

        Args:
            knowledge_base (Dict[str, Vector]): 包含其他领域/行业坐标的字典。

        Returns:
            np.ndarray: 推荐的新坐标向量。
        """
        logger.warning("Crowding threshold exceeded. Triggering Niche Shift (Mutation).")
        
        best_target = None
        max_score = -float('inf')
        
        current_dim = len(self.current_position)
        
        for domain, coords in knowledge_base.items():
            target_vector = np.array(coords)
            if target_vector.shape != (current_dim,):
                continue
                
            # 简单启发式：寻找距离足够远（蓝海特征）的候选
            # 实际AGI场景会调用向量数据库进行语义/逻辑搜索
            distance = np.linalg.norm(self.current_position - target_vector)
            
            # 评分函数：鼓励适度的创新距离（不要跳到完全无法生存的维度）
            # 这里的评分是模拟，假设距离越远分越高（差异化竞争）
            score = distance 
            
            if score > max_score:
                max_score = score
                best_target = target_vector

        if best_target is None:
            logger.error("No suitable niche found in knowledge base. Staying put.")
            return self.current_position

        # 添加随机扰动以模拟创新的不可预测性
        mutation_noise = np.random.normal(0, self.mutation_rate, current_dim)
        new_position = best_target + mutation_noise
        
        # 确保非负（如果坐标代表非负资源）
        new_position = np.maximum(new_position, 0)
        
        logger.info(f"Niche shift target acquired: {new_position}")
        return new_position

    def run_navigation_cycle(self, 
                             environment_data: Dict, 
                             cross_domain_knowledge: Dict[str, Vector]) -> Dict:
        """
        执行一次完整的导航循环。

        Args:
            environment_data (Dict): 包含 'competitors' 和 'local_resources' 的字典。
            cross_domain_knowledge (Dict): 跨领域知识库。

        Returns:
            Dict: 包含决策结果的字典。
        """
        try:
            # 1. 感知环境
            competitors = environment_data.get('competitors', [])
            resources = environment_data.get('resources', 0.5)
            
            # 2. 计算拥挤度
            crowding = self.calculate_crowding_intensity(competitors)
            
            # 3. 决策：保持或迁移
            if crowding > self.crowding_threshold:
                # 迁移成本消耗能量
                migration_cost = 10.0 
                if self.energy_capital > migration_cost:
                    self.current_position = self.trigger_niche_shift(cross_domain_knowledge)
                    self.energy_capital -= migration_cost
                    action = "NICHE_SHIFT"
                else:
                    logger.warning("Insufficient capital for migration. Adapting in place.")
                    action = "HOLD_LOW_CAPITAL"
                    crowding = self.crowding_threshold # 强制忍受
            else:
                action = "HOLD_EXPLOIT"

            # 4. 计算适应度并更新能量
            fitness = self.calculate_marginal_fitness(resources, crowding)
            self.energy_capital += fitness * 0.1 # 假设一部分转化为资本积累

            result = {
                "action_taken": action,
                "current_position": self.current_position.tolist(),
                "crowding_level": crowding,
                "fitness_score": fitness,
                "updated_capital": self.energy_capital
            }
            
            self._history.append(result)
            return result

        except KeyError as ke:
            logger.error(f"Missing key in environment data: {ke}")
            raise
        except Exception as e:
            logger.critical(f"System crash during navigation cycle: {e}")
            raise

# 辅助函数：生成模拟环境数据
def generate_mock_environment(num_competitors: int, dimensions: int) -> Dict:
    """
    生成模拟的竞争对手和市场环境数据。
    
    Args:
        num_competitors (int): 竞争对手数量。
        dimensions (int): 市场维度。
        
    Returns:
        Dict: 环境数据字典。
    """
    competitors = [np.random.uniform(0, 10, dimensions).tolist() for _ in range(num_competitors)]
    return {
        "competitors": competitors,
        "resources": np.random.uniform(0.3, 0.9)
    }

# 使用示例
if __name__ == "__main__":
    # 初始化系统：定义在 3D 空间（如技术、资本、流量）中的位置
    initial_coords = [5.0, 5.0, 5.0]
    system = DynamicNicheNavigationSystem(initial_coords, initial_capital=100.0, crowding_threshold=0.6)
    
    # 定义跨领域知识库（蓝海区域候选）
    knowledge_base = {
        "bio_biomimicry": [8.0, 1.0, 9.0],   # 生物仿生领域
        "quantum_finance": [2.0, 9.0, 3.0],  # 量子金融
        "rural_tech": [1.0, 3.0, 8.0]        # 下沉市场科技
    }
    
    # 模拟运行周期
    print("--- Cycle 1: Low Competition ---")
    env_low_comp = generate_mock_environment(2, 3) # 只有2个竞争对手
    result_1 = system.run_navigation_cycle(env_low_comp, knowledge_base)
    print(f"Result 1: {result_1['action_taken']}, Capital: {result_1['updated_capital']:.2f}")
    
    print("\n--- Cycle 2: High Competition (Triggering Shift) ---")
    # 构造高拥挤环境：把很多竞争对手放在当前位置附近
    crowded_competitors = [[5.1, 5.0, 4.9], [5.2, 5.3, 5.0], [4.9, 4.8, 5.2]]
    env_high_comp = {"competitors": crowded_competitors, "resources": 0.8}
    result_2 = system.run_navigation_cycle(env_high_comp, knowledge_base)
    print(f"Result 2: {result_2['action_taken']}, New Pos: {result_2['current_position']}")