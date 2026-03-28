"""
r-策略型敏捷实践引擎

该模块实现了一个针对高度不确定环境的AGI决策引擎。它放弃了构建单一庞大预测模型的
传统方法，转而采用生物学的r-选择策略（R-selection strategy）。通过在模拟环境中
并行生成大量低成本、结构简单但多样的"微型闭环"（Micro-Loops）或"小摊贩"策略，
利用环境反馈进行快速筛选和迭代。这种方法适用于火星探索、极端金融交易或网络安全
防御等缺乏历史数据且环境动态变化的领域。

Dependencies:
    - numpy
    - pandas (optional, for advanced logging/analysis)
"""

import logging
import random
import time
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional, Tuple
from enum import Enum
import json

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("R_Strategy_Engine")

class StrategyStatus(Enum):
    """策略状态枚举"""
    ACTIVE = 1
    DORMANT = 2
    TERMINATED = 3

@dataclass
class ActionPayload:
    """策略执行动作的载荷"""
    action_type: str
    parameters: Dict[str, float]
    timestamp: float = field(default_factory=time.time)

@dataclass
class MicroStrategy:
    """
    微型闭环策略实体。
    
    Attributes:
        id (str): 唯一标识符
        genes (Dict): 策略参数，模拟生物基因
        fitness (float): 适应度得分
        status (StrategyStatus): 当前状态
        history (List): 历史表现记录
    """
    id: str
    genes: Dict[str, float]
    fitness: float = 0.0
    status: StrategyStatus = StrategyStatus.ACTIVE
    history: List[float] = field(default_factory=list)

    def mutate(self, mutation_rate: float = 0.1) -> None:
        """对策略基因进行随机变异"""
        for key in self.genes:
            if random.random() < mutation_rate:
                # 添加高斯噪声
                change = random.gauss(0, 0.1) * self.genes[key]
                self.genes[key] += change
                # 边界检查
                self.genes[key] = max(0.0, min(1.0, self.genes[key]))
                
        # 变更ID以反映变异
        self.id = hashlib.md5((self.id + str(time.time())).encode()).hexdigest()[:8]
        logger.debug(f"Strategy {self.id} mutated.")

class EnvironmentSimulation:
    """
    模拟环境类。
    
    用于测试策略的适应性。在真实场景中，这里会连接到真实世界的API或传感器。
    """
    def __init__(self, volatility: float = 0.5):
        self.volatility = volatility
        self.step_count = 0

    def execute_and_get_feedback(self, action: ActionPayload) -> float:
        """
        执行动作并返回即时奖励。
        
        Args:
            action (ActionPayload): 动作载荷
            
        Returns:
            float: 归一化的奖励分数 [-1.0, 1.0]
        """
        # 模拟复杂环境的随机反馈
        # 这里的逻辑仅作演示：假设动作参数与环境隐藏状态的匹配度决定奖励
        base_reward = random.uniform(-self.volatility, self.volatility)
        
        # 模拟某些参数组合可能带来爆发性收益或亏损
        if action.parameters.get('risk_level', 0) > 0.8:
            base_reward *= random.choice([-2.0, 2.0])
            
        self.step_count += 1
        return base_reward

class RStrategyEngine:
    """
    r-策略型敏捷实践引擎核心类。
    
    负责种群的初始化、并发模拟、适应度评估、选择与繁殖。
    
    Input Format:
        - config: Dict, 包含种群大小、变异率等配置
        - environment: EnvironmentSimulation实例
        
    Output Format:
        - best_strategy: MicroStrategy, 当前最优策略实体
    """
    
    def __init__(self, config: Dict[str, Any], environment: EnvironmentSimulation):
        self.population_size = config.get('population_size', 100)
        self.mutation_rate = config.get('mutation_rate', 0.05)
        self.survival_rate = config.get('survival_rate', 0.2)
        self.env = environment
        self.population: List[MicroStrategy] = []
        self.generation = 0
        
        self._initialize_population()
        logger.info(f"Engine initialized with population size: {self.population_size}")

    def _initialize_population(self) -> None:
        """初始化随机种群（爆发式生成）"""
        for _ in range(self.population_size):
            genes = {
                'risk_level': random.random(),
                'exploration_factor': random.random(),
                'conservation_bias': random.random(),
                'reaction_speed': random.random()
            }
            s_id = hashlib.md5(str(time.time() + random.randint(0, 10000)).encode()).hexdigest()[:8]
            self.population.append(MicroStrategy(id=s_id, genes=genes))
            
    def _evaluate_single_strategy(self, strategy: MicroStrategy) -> float:
        """
        辅助函数：评估单个策略的适应度。
        
        创建一个微型闭环，运行模拟并计算得分。
        """
        try:
            # 根据基因构建动作
            params = strategy.genes
            action = ActionPayload(action_type="simulate_move", parameters=params)
            
            # 运行多次取平均值以减少噪声影响
            rewards = []
            for _ in range(3): # 简单的微型闭环
                reward = self.env.execute_and_get_feedback(action)
                rewards.append(reward)
            
            avg_fitness = sum(rewards) / len(rewards)
            
            # 数据验证
            if not isinstance(avg_fitness, (int, float)):
                raise ValueError("Fitness must be numeric")
                
            strategy.fitness = avg_fitness
            strategy.history.append(avg_fitness)
            return avg_fitness
            
        except Exception as e:
            logger.error(f"Error evaluating strategy {strategy.id}: {e}")
            strategy.fitness = -1.0 # 惩罚错误
            return -1.0

    def evolve_generation(self) -> None:
        """
        核心函数：执行一代进化过程。
        
        包含评估、筛选、繁殖三个步骤。
        """
        logger.info(f"Starting Generation {self.generation} evolution...")
        
        # 1. 并行评估（在真实AGI中这里使用异步并发）
        # 这里为了代码演示清晰，使用串行模拟并行
        for strategy in self.population:
            if strategy.status == StrategyStatus.ACTIVE:
                self._evaluate_single_strategy(strategy)
        
        # 2. 环境选择（筛选存活者）
        # 过滤掉无效策略并排序
        active_strategies = [s for s in self.population if s.status == StrategyStatus.ACTIVE]
        active_strategies.sort(key=lambda x: x.fitness, reverse=True)
        
        survivors_count = int(self.population_size * self.survival_rate)
        survivors = active_strategies[:survivors_count]
        
        logger.info(f"Selection complete. Top fitness: {survivors[0].fitness:.4f} (ID: {survivors[0].id})")
        
        # 3. 繁殖与种群恢复（生成下一代）
        new_population = list(survivors) # 保留精英
        
        # 填充剩余种群空间
        while len(new_population) < self.population_size:
            # 随机选择父代（存活者）
            parent = random.choice(survivors)
            
            # 克隆并变异
            child_genes = parent.genes.copy()
            child = MicroStrategy(
                id=parent.id + "_c", 
                genes=child_genes
            )
            child.mutate(self.mutation_rate)
            new_population.append(child)
            
        self.population = new_population
        self.generation += 1

    def get_best_strategy(self) -> Optional[MicroStrategy]:
        """获取当前种群中的最优策略"""
        if not self.population:
            return None
        return max(self.population, key=lambda x: x.fitness)

    def run_auto_pilot(self, max_generations: int = 10) -> Dict[str, Any]:
        """
        核心函数：自动运行进化循环直到满足条件。
        
        模拟在不确定环境中的快速迭代过程。
        """
        report = {
            "start_time": time.time(),
            "generations_run": 0,
            "final_best_fitness": -float('inf'),
            "history_best_fitness": []
        }
        
        try:
            for gen in range(max_generations):
                self.evolve_generation()
                best = self.get_best_strategy()
                if best:
                    report["history_best_fitness"].append(best.fitness)
                    report["final_best_fitness"] = best.fitness
                    
                # 动态调整环境波动率，模拟环境变化
                self.env.volatility = max(0.1, self.env.volatility * 0.99)
                
            report["generations_run"] = max_generations
            status = "SUCCESS"
            
        except Exception as e:
            logger.critical(f"Auto-pilot crashed: {e}")
            status = "FAILED"
            report["error"] = str(e)
            
        report["end_time"] = time.time()
        report["duration"] = report["end_time"] - report["start_time"]
        logger.info(f"Auto-pilot finished. Status: {status}, Best Fitness: {report['final_best_fitness']:.4f}")
        return report

# Usage Example
if __name__ == "__main__":
    # 配置引擎：种群小，变异率高，适应不确定环境
    engine_config = {
        'population_size': 50,
        'mutation_rate': 0.15,
        'survival_rate': 0.3
    }
    
    # 初始化高波动环境模拟
    sim_env = EnvironmentSimulation(volatility=0.8)
    
    # 实例化引擎
    engine = RStrategyEngine(config=engine_config, environment=sim_env)
    
    # 运行自动进化
    final_report = engine.run_auto_pilot(max_generations=5)
    
    # 打印报告
    print("\n=== Evolution Report ===")
    print(json.dumps(final_report, indent=2))
    
    best_strat = engine.get_best_strategy()
    print(f"\nBest Strategy Genes: {best_strat.genes}")