"""
高级技能模块: 将物理世界结构视为可微分神经网络进行优化
"""

import logging
import numpy as np
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PhysicsWorldConfig:
    """物理世界配置参数"""
    structure_dims: Tuple[int, int]  # 结构尺寸 (行, 列)
    material_density: float = 1.0    # 材料密度
    gravity: float = 9.81           # 重力加速度
    max_iterations: int = 1000       # 最大迭代次数
    learning_rate: float = 0.01     # 学习率
    stability_threshold: float = 0.01  # 稳定性阈值
    random_seed: Optional[int] = None  # 随机种子


@dataclass
class OptimizationResult:
    """优化结果数据结构"""
    optimized_structure: np.ndarray
    fitness_history: List[float]
    final_fitness: float
    iterations: int
    converged: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


def validate_structure(structure: np.ndarray) -> bool:
    """
    验证物理结构数组的有效性
    
    Args:
        structure: 待验证的物理结构数组
        
    Returns:
        bool: 如果结构有效返回True，否则返回False
        
    Raises:
        ValueError: 如果结构包含无效值
    """
    if not isinstance(structure, np.ndarray):
        raise ValueError("结构必须是numpy数组")
        
    if structure.size == 0:
        raise ValueError("结构数组不能为空")
        
    if np.any(structure < 0):
        raise ValueError("结构值不能为负")
        
    if np.any(structure > 1e6):
        raise ValueError("结构值超出合理范围(1e6)")
        
    return True


def initialize_physics_world(
    config: PhysicsWorldConfig
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    初始化物理世界结构
    
    Args:
        config: 物理世界配置对象
        
    Returns:
        Tuple[np.ndarray, Dict]: 初始化的结构数组和元数据字典
        
    Example:
        >>> config = PhysicsWorldConfig(structure_dims=(10, 10))
        >>> structure, meta = initialize_physics_world(config)
        >>> print(structure.shape)
        (10, 10)
    """
    if config.random_seed is not None:
        np.random.seed(config.random_seed)
        
    # 初始化结构数组 (这里简化处理，实际应用中可能需要更复杂的初始化)
    structure = np.random.rand(*config.structure_dims) * config.material_density
    
    # 计算初始元数据
    metadata = {
        'initial_mass': np.sum(structure),
        'gravity_load': config.gravity * np.sum(structure),
        'density_variance': np.var(structure),
        'creation_time': logging.Formatter.default_time_format
    }
    
    logger.info(f"初始化物理世界: 尺寸={config.structure_dims}, 初始质量={metadata['initial_mass']:.2f}")
    
    return structure, metadata


def compute_physics_gradients(
    structure: np.ndarray,
    config: PhysicsWorldConfig
) -> np.ndarray:
    """
    计算物理结构的梯度 (模拟反向传播)
    
    Args:
        structure: 当前物理结构数组
        config: 物理世界配置
        
    Returns:
        np.ndarray: 结构梯度数组
        
    Note:
        这是一个简化版的梯度计算，实际应用中需要根据具体物理定律实现
    """
    try:
        validate_structure(structure)
        
        # 计算重力影响梯度
        gravity_grad = structure * config.gravity
        
        # 计算结构稳定性梯度 (简化模型)
        stability_grad = np.gradient(structure)
        stability_grad = np.sqrt(stability_grad[0]**2 + stability_grad[1]**2)
        
        # 计算材料分布梯度
        distribution_grad = np.abs(structure - np.mean(structure))
        
        # 组合梯度 (加权平均)
        combined_grad = (
            0.4 * gravity_grad + 
            0.4 * stability_grad + 
            0.2 * distribution_grad
        )
        
        # 归一化梯度
        grad_norm = np.linalg.norm(combined_grad)
        if grad_norm > 1e-6:
            combined_grad = combined_grad / grad_norm
            
        return combined_grad
        
    except Exception as e:
        logger.error(f"梯度计算失败: {str(e)}")
        raise RuntimeError(f"梯度计算失败: {str(e)}") from e


def optimize_physical_structure(
    initial_structure: np.ndarray,
    config: PhysicsWorldConfig
) -> OptimizationResult:
    """
    优化物理结构 (主优化循环)
    
    Args:
        initial_structure: 初始物理结构
        config: 优化配置参数
        
    Returns:
        OptimizationResult: 包含优化结果的数据对象
        
    Example:
        >>> config = PhysicsWorldConfig(structure_dims=(5, 5), max_iterations=100)
        >>> initial = np.random.rand(5, 5)
        >>> result = optimize_physical_structure(initial, config)
        >>> print(f"最终适应度: {result.final_fitness:.4f}")
    """
    # 输入验证
    try:
        validate_structure(initial_structure)
    except ValueError as e:
        logger.error(f"无效的初始结构: {str(e)}")
        return OptimizationResult(
            optimized_structure=initial_structure,
            fitness_history=[],
            final_fitness=0.0,
            iterations=0,
            converged=False,
            metadata={'error': str(e)}
        )
    
    # 初始化变量
    current_structure = initial_structure.copy()
    fitness_history = []
    best_fitness = -np.inf
    no_improvement_count = 0
    converged = False
    
    logger.info(f"开始优化过程, 最大迭代次数: {config.max_iterations}")
    
    for iteration in range(config.max_iterations):
        try:
            # 计算当前结构的适应度 (简化模型)
            # 这里使用结构稳定性和材料分布的综合评分
            stability_score = 1.0 / (1.0 + np.std(current_structure))
            distribution_score = 1.0 - np.mean(np.abs(
                current_structure - np.mean(current_structure)
            ))
            fitness = 0.7 * stability_score + 0.3 * distribution_score
            
            fitness_history.append(fitness)
            
            # 检查是否收敛
            if fitness > best_fitness + config.stability_threshold:
                best_fitness = fitness
                no_improvement_count = 0
            else:
                no_improvement_count += 1
                
            if no_improvement_count > 10 or iteration == config.max_iterations - 1:
                converged = True
                logger.info(f"在迭代 {iteration} 达到收敛")
                break
                
            # 计算梯度并更新结构
            gradients = compute_physics_gradients(current_structure, config)
            current_structure += config.learning_rate * gradients
            
            # 确保结构值在合理范围内
            current_structure = np.clip(
                current_structure, 
                0.0, 
                config.material_density * 2
            )
            
            # 每100次迭代记录一次进度
            if iteration % 100 == 0:
                logger.debug(
                    f"迭代 {iteration}: 适应度={fitness:.4f}, "
                    f"质量={np.sum(current_structure):.2f}"
                )
                
        except Exception as e:
            logger.error(f"优化过程中断于迭代 {iteration}: {str(e)}")
            break
    
    # 准备最终结果
    result = OptimizationResult(
        optimized_structure=current_structure,
        fitness_history=fitness_history,
        final_fitness=fitness_history[-1] if fitness_history else 0.0,
        iterations=len(fitness_history),
        converged=converged,
        metadata={
            'initial_mass': np.sum(initial_structure),
            'final_mass': np.sum(current_structure),
            'mass_change': np.sum(current_structure) - np.sum(initial_structure),
            'best_fitness': best_fitness,
            'config': config.__dict__
        }
    )
    
    logger.info(
        f"优化完成: 最终适应度={result.final_fitness:.4f}, "
        f"迭代次数={result.iterations}, 收敛={result.converged}"
    )
    
    return result


def visualize_optimization_result(result: OptimizationResult) -> None:
    """
    可视化优化结果 (简化版)
    
    Args:
        result: 优化结果对象
    """
    try:
        print("\n=== 优化结果摘要 ===")
        print(f"最终适应度: {result.final_fitness:.4f}")
        print(f"迭代次数: {result.iterations}")
        print(f"收敛状态: {'成功' if result.converged else '未收敛'}")
        print(f"质量变化: {result.metadata['mass_change']:.2f}")
        print("\n优化后的结构示例 (前5x5部分):")
        
        if result.optimized_structure.ndim == 2:
            print(result.optimized_structure[:5, :5])
        else:
            print(result.optimized_structure[:5])
            
    except Exception as e:
        logger.warning(f"结果可视化失败: {str(e)}")


def run_physics_optimization_demo() -> None:
    """
    运行物理世界优化演示
    
    这个函数演示了如何使用上述功能来优化一个物理结构。
    """
    print("=== 物理世界优化演示 ===")
    
    # 1. 创建配置
    config = PhysicsWorldConfig(
        structure_dims=(20, 20),
        material_density=1.0,
        gravity=9.81,
        max_iterations=500,
        learning_rate=0.05,
        stability_threshold=0.001,
        random_seed=42
    )
    
    # 2. 初始化物理世界
    initial_structure, meta = initialize_physics_world(config)
    print(f"\n初始结构质量: {meta['initial_mass']:.2f}")
    print(f"重力负载: {meta['gravity_load']:.2f}")
    
    # 3. 运行优化
    result = optimize_physical_structure(initial_structure, config)
    
    # 4. 显示结果
    visualize_optimization_result(result)
    
    # 5. 分析优化历史
    if result.fitness_history:
        improvement = (result.fitness_history[-1] - result.fitness_history[0]) / result.fitness_history[0]
        print(f"\n适应度提升: {improvement*100:.2f}%")


if __name__ == "__main__":
    run_physics_optimization_demo()