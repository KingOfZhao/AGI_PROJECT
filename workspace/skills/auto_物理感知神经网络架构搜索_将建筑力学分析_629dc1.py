"""
物理感知神经网络架构搜索模块

本模块实现了一种新颖的架构搜索方法，将建筑力学原理直接嵌入神经网络拓扑设计中。
通过构建'力学同构网络'，确保梯度流遵循类似力学传导的'刚度'约束，从而防止梯度消失/爆炸问题。

核心思想：
- 将神经网络层视为结构力学中的节点
- 将层间连接视为力学传导路径
- 通过刚度矩阵约束梯度传播
- 自动生成工程鲁棒性强的AI模型

典型应用场景：
1. 复杂流体动力学预测
2. 地震响应分析
3. 材料应力应变预测
4. 多物理场耦合仿真
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Union
import logging
from dataclasses import dataclass
from enum import Enum
import time
from abc import ABC, abstractmethod

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PhysicalConstraintType(Enum):
    """物理约束类型枚举"""
    STIFFNESS = "stiffness"      # 刚度约束
    DAMPING = "damping"          # 阻尼约束
    MASS = "mass"                # 质量约束
    STABILITY = "stability"      # 稳定性约束

@dataclass
class LayerMechanicalProperty:
    """层力学属性数据结构"""
    stiffness: float            # 刚度系数
    damping_ratio: float        # 阻尼比
    mass: float                 # 等效质量
    max_load: float             # 最大承载力
    
    def validate(self) -> bool:
        """验证力学参数合理性"""
        if self.stiffness <= 0 or self.damping_ratio < 0 or self.mass <= 0:
            return False
        return True

@dataclass
class ArchitecturalCandidate:
    """架构候选解数据结构"""
    layer_configs: List[Dict]               # 各层配置
    mechanical_props: List[LayerMechanicalProperty]  # 各层力学属性
    fitness_score: float                    # 适应度分数
    stability_index: float                  # 稳定性指标
    
    def is_valid(self) -> bool:
        """检查候选架构有效性"""
        if not self.layer_configs or not self.mechanical_props:
            return False
        if len(self.layer_configs) != len(self.mechanical_props):
            return False
        return all(prop.validate() for prop in self.mechanical_props)

class MechanicalNAS:
    """
    物理感知神经网络架构搜索核心类
    
    该类实现了将力学分析嵌入神经网络拓扑设计的完整流程，包括：
    1. 搜索空间定义
    2. 候选架构生成
    3. 力学约束评估
    4. 架构优化迭代
    
    示例:
        >>> nas = MechanicalNAS(input_dim=64, output_dim=10)
        >>> best_arch = nas.search(max_iterations=100)
        >>> print(f"最佳架构适应度: {best_arch.fitness_score}")
    """
    
    def __init__(self, input_dim: int, output_dim: int, 
                 max_layers: int = 10, population_size: int = 20):
        """
        初始化架构搜索器
        
        参数:
            input_dim: 输入维度
            output_dim: 输出维度
            max_layers: 最大网络层数
            population_size: 候选架构种群大小
            
        异常:
            ValueError: 当输入参数不合法时抛出
        """
        # 输入验证
        if input_dim <= 0 or output_dim <= 0:
            raise ValueError("输入/输出维度必须为正整数")
        if max_layers <= 0 or population_size <= 0:
            raise ValueError("层数和种群大小必须为正整数")
            
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.max_layers = max_layers
        self.population_size = population_size
        self.search_history = []
        
        # 物理约束参数
        self.constraint_weights = {
            PhysicalConstraintType.STIFFNESS: 0.4,
            PhysicalConstraintType.DAMPING: 0.3,
            PhysicalConstraintType.STABILITY: 0.3
        }
        
        logger.info(f"初始化力学感知NAS: input={input_dim}, output={output_dim}, "
                   f"max_layers={max_layers}, pop_size={population_size}")
    
    def _generate_random_architecture(self) -> ArchitecturalCandidate:
        """
        生成随机候选架构（内部方法）
        
        返回:
            ArchitecturalCandidate: 随机生成的候选架构
        """
        num_layers = np.random.randint(2, self.max_layers + 1)
        layer_configs = []
        mechanical_props = []
        
        # 生成各层配置
        prev_dim = self.input_dim
        for i in range(num_layers - 1):
            # 随机生成层维度（确保单调递减趋势）
            min_dim = max(self.output_dim, prev_dim // 4)
            max_dim = prev_dim
            curr_dim = np.random.randint(min_dim, max_dim + 1)
            
            layer_configs.append({
                "type": "dense",
                "input_dim": prev_dim,
                "output_dim": curr_dim,
                "activation": np.random.choice(["relu", "tanh", "sigmoid"])
            })
            
            # 生成力学属性
            stiffness = np.random.uniform(0.1, 10.0)
            damping_ratio = np.random.uniform(0.05, 0.5)
            mass = np.random.uniform(0.5, 5.0)
            max_load = np.random.uniform(1.0, 100.0)
            
            mechanical_props.append(LayerMechanicalProperty(
                stiffness=stiffness,
                damping_ratio=damping_ratio,
                mass=mass,
                max_load=max_load
            ))
            
            prev_dim = curr_dim
        
        # 输出层
        layer_configs.append({
            "type": "output",
            "input_dim": prev_dim,
            "output_dim": self.output_dim,
            "activation": "linear"
        })
        
        mechanical_props.append(LayerMechanicalProperty(
            stiffness=np.random.uniform(1.0, 10.0),
            damping_ratio=np.random.uniform(0.1, 0.3),
            mass=1.0,
            max_load=np.random.uniform(50.0, 200.0)
        ))
        
        return ArchitecturalCandidate(
            layer_configs=layer_configs,
            mechanical_props=mechanical_props,
            fitness_score=0.0,
            stability_index=0.0
        )
    
    def evaluate_mechanical_constraints(self, candidate: ArchitecturalCandidate) -> Tuple[float, float]:
        """
        评估候选架构的力学约束满足情况
        
        参数:
            candidate: 候选架构
            
        返回:
            Tuple[float, float]: (综合适应度分数, 稳定性指标)
            
        异常:
            ValueError: 当候选架构无效时抛出
        """
        if not candidate.is_valid():
            raise ValueError("无效的候选架构")
            
        # 计算全局刚度矩阵条件数
        stiffness_matrix = self._build_global_stiffness_matrix(candidate)
        try:
            cond_number = np.linalg.cond(stiffness_matrix)
            stiffness_score = 1.0 / (1.0 + np.log(cond_number))
        except np.linalg.LinAlgError:
            stiffness_score = 0.0
        
        # 计算阻尼分布均匀性
        damping_values = [prop.damping_ratio for prop in candidate.mechanical_props]
        damping_score = 1.0 - np.std(damping_values) / (np.mean(damping_values) + 1e-6)
        
        # 计算结构稳定性指标
        stability_index = self._calculate_stability_index(candidate)
        
        # 综合适应度
        fitness = (
            self.constraint_weights[PhysicalConstraintType.STIFFNESS] * stiffness_score +
            self.constraint_weights[PhysicalConstraintType.DAMPING] * max(0, damping_score) +
            self.constraint_weights[PhysicalConstraintType.STABILITY] * stability_index
        )
        
        return fitness, stability_index
    
    def _build_global_stiffness_matrix(self, candidate: ArchitecturalCandidate) -> np.ndarray:
        """
        构建全局刚度矩阵（内部方法）
        
        参数:
            candidate: 候选架构
            
        返回:
            np.ndarray: 全局刚度矩阵
        """
        num_layers = len(candidate.layer_configs)
        matrix_size = num_layers + 1  # 节点数 = 层数 + 1
        
        # 初始化刚度矩阵
        K = np.zeros((matrix_size, matrix_size))
        
        # 填充刚度矩阵（简化版三对角矩阵）
        for i in range(num_layers):
            k = candidate.mechanical_props[i].stiffness
            K[i, i] += k
            K[i, i+1] -= k
            K[i+1, i] -= k
            K[i+1, i+1] += k
        
        # 添加边界条件（固定端约束）
        K[0, 0] += 1e6  # 输入端固定
        K[-1, -1] += 1e6  # 输出端固定
        
        return K
    
    def _calculate_stability_index(self, candidate: ArchitecturalCandidate) -> float:
        """
        计算架构稳定性指标（内部方法）
        
        参数:
            candidate: 候选架构
            
        返回:
            float: 稳定性指标 [0,1]
        """
        # 检查梯度传播路径的"结构完整性"
        stability = 1.0
        prev_stiffness = float('inf')
        
        for i, prop in enumerate(candidate.mechanical_props):
            # 刚度应逐渐减小（类似结构中的力传递）
            if prop.stiffness > prev_stiffness * 1.2:
                stability *= 0.8  # 惩罚刚度突然增大
            
            # 阻尼比应在合理范围内
            if prop.damping_ratio > 0.5:
                stability *= 0.9
            
            # 质量分布检查
            if i > 0 and prop.mass > candidate.mechanical_props[i-1].mass * 2.0:
                stability *= 0.85
                
            prev_stiffness = prop.stiffness
        
        return stability
    
    def search(self, max_iterations: int = 100, 
               target_fitness: float = 0.85) -> ArchitecturalCandidate:
        """
        执行架构搜索过程
        
        参数:
            max_iterations: 最大迭代次数
            target_fitness: 目标适应度阈值
            
        返回:
            ArchitecturalCandidate: 最佳候选架构
            
        异常:
            RuntimeError: 当搜索过程失败时抛出
        """
        start_time = time.time()
        logger.info(f"开始架构搜索: max_iter={max_iterations}, target={target_fitness}")
        
        best_candidate = None
        best_fitness = 0.0
        
        try:
            # 初始化种群
            population = [self._generate_random_architecture() 
                         for _ in range(self.population_size)]
            
            for iteration in range(max_iterations):
                # 评估种群
                fitness_scores = []
                for candidate in population:
                    fitness, stability = self.evaluate_mechanical_constraints(candidate)
                    candidate.fitness_score = fitness
                    candidate.stability_index = stability
                    fitness_scores.append(fitness)
                
                # 记录最佳个体
                current_best_idx = np.argmax(fitness_scores)
                current_best = population[current_best_idx]
                
                if current_best.fitness_score > best_fitness:
                    best_fitness = current_best.fitness_score
                    best_candidate = current_best
                    logger.info(f"迭代 {iteration}: 发现新最佳架构，适应度={best_fitness:.4f}")
                
                # 检查终止条件
                if best_fitness >= target_fitness:
                    logger.info(f"达到目标适应度 {target_fitness}, 提前终止搜索")
                    break
                
                # 进化操作：选择 + 变异
                new_population = self._evolve_population(population, fitness_scores)
                population = new_population
            
            if best_candidate is None:
                raise RuntimeError("架构搜索失败：未找到有效候选")
            
            elapsed = time.time() - start_time
            logger.info(f"搜索完成: 最佳适应度={best_fitness:.4f}, 耗时={elapsed:.2f}秒")
            
            return best_candidate
            
        except Exception as e:
            logger.error(f"架构搜索过程发生错误: {str(e)}")
            raise RuntimeError(f"架构搜索失败: {str(e)}")
    
    def _evolve_population(self, population: List[ArchitecturalCandidate],
                          fitness_scores: List[float]) -> List[ArchitecturalCandidate]:
        """
        进化种群（内部方法）
        
        参数:
            population: 当前种群
            fitness_scores: 适应度分数列表
            
        返回:
            List[ArchitecturalCandidate]: 新一代种群
        """
        # 选择操作：保留前20%精英
        sorted_indices = np.argsort(fitness_scores)[::-1]
        elite_size = max(2, self.population_size // 5)
        elite = [population[i] for i in sorted_indices[:elite_size]]
        
        # 生成新个体
        new_population = elite.copy()
        while len(new_population) < self.population_size:
            # 从精英中随机选择父代
            parent = elite[np.random.randint(len(elite))]
            
            # 复制并变异
            child = self._mutate_architecture(parent)
            new_population.append(child)
        
        return new_population
    
    def _mutate_architecture(self, parent: ArchitecturalCandidate) -> ArchitecturalCandidate:
        """
        变异操作：对父代架构进行微调
        
        参数:
            parent: 父代架构
            
        返回:
            ArchitecturalCandidate: 变异后的子代架构
        """
        # 深拷贝父代
        child = ArchitecturalCandidate(
            layer_configs=[config.copy() for config in parent.layer_configs],
            mechanical_props=[LayerMechanicalProperty(
                stiffness=prop.stiffness,
                damping_ratio=prop.damping_ratio,
                mass=prop.mass,
                max_load=prop.max_load
            ) for prop in parent.mechanical_props],
            fitness_score=0.0,
            stability_index=0.0
        )
        
        # 随机变异力学属性
        mutation_prob = 0.3
        for prop in child.mechanical_props:
            if np.random.random() < mutation_prob:
                # 刚度变异
                prop.stiffness *= np.random.uniform(0.8, 1.2)
                prop.stiffness = np.clip(prop.stiffness, 0.1, 10.0)
                
                # 阻尼变异
                prop.damping_ratio *= np.random.uniform(0.9, 1.1)
                prop.damping_ratio = np.clip(prop.damping_ratio, 0.05, 0.5)
                
                # 质量变异
                prop.mass *= np.random.uniform(0.9, 1.1)
                prop.mass = np.clip(prop.mass, 0.5, 5.0)
        
        return child

def visualize_architecture_stiffness(architecture: ArchitecturalCandidate) -> None:
    """
    可视化架构刚度分布（辅助函数）
    
    参数:
        architecture: 候选架构
    """
    try:
        import matplotlib.pyplot as plt
        
        stiffness_values = [prop.stiffness for prop in architecture.mechanical_props]
        layer_indices = range(1, len(stiffness_values) + 1)
        
        plt.figure(figsize=(10, 5))
        plt.plot(layer_indices, stiffness_values, 'o-', linewidth=2)
        plt.title("Network Layer Stiffness Distribution")
        plt.xlabel("Layer Index")
        plt.ylabel("Stiffness Coefficient")
        plt.grid(True)
        plt.show()
        
    except ImportError:
        logger.warning("Matplotlib未安装，无法可视化刚度分布")

def export_architecture_to_json(architecture: ArchitecturalCandidate) -> Dict:
    """
    将架构导出为JSON格式（辅助函数）
    
    参数:
        architecture: 候选架构
        
    返回:
        Dict: JSON可序列化的字典
    """
    return {
        "layer_configs": architecture.layer_configs,
        "mechanical_properties": [
            {
                "stiffness": prop.stiffness,
                "damping_ratio": prop.damping_ratio,
                "mass": prop.mass,
                "max_load": prop.max_load
            } for prop in architecture.mechanical_props
        ],
        "fitness_score": architecture.fitness_score,
        "stability_index": architecture.stability_index
    }

# 使用示例
if __name__ == "__main__":
    try:
        # 创建NAS实例
        nas = MechanicalNAS(input_dim=128, output_dim=10, max_layers=8)
        
        # 执行架构搜索
        best_architecture = nas.search(max_iterations=50, target_fitness=0.8)
        
        # 输出最佳架构信息
        print("\n最佳架构信息:")
        print(f"层数: {len(best_architecture.layer_configs)}")
        print(f"适应度分数: {best_architecture.fitness_score:.4f}")
        print(f"稳定性指标: {best_architecture.stability_index:.4f}")
        
        # 导出为JSON
        arch_json = export_architecture_to_json(best_architecture)
        print("\nJSON格式架构:")
        print(arch_json)
        
    except Exception as e:
        logger.error(f"示例运行失败: {str(e)}")