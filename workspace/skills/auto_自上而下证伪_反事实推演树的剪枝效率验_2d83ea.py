"""
自上而下证伪：反事实推演树的剪枝效率验证模块

该模块实现了一个针对复杂决策节点的反事实推演树验证系统。
通过构建'反事实模拟器'，自动生成负面场景攻击假设，
并验证剪枝策略在缩减搜索空间方面的有效性。

核心功能:
- 反事实场景生成
- 推演树剪枝策略验证
- 搜索空间缩减效率计算
- 递归深度监控与防护

数据格式:
输入:
- 假设节点 (dict): 包含决策参数和约束条件
- 验证配置 (dict): 包含最大递归深度、分支因子等参数

输出:
- 验证结果 (dict): 包含剪枝效率指标和验证状态
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import math
import random
from time import perf_counter

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TreeNode:
    """推演树节点数据结构"""
    hypothesis_id: str
    parameters: Dict[str, float]
    depth: int
    is_falsified: bool = False
    children: List['TreeNode'] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class CounterfactualSimulator:
    """反事实模拟器，生成负面场景攻击假设"""

    def __init__(self, max_depth: int = 5):
        """
        初始化反事实模拟器
        
        Args:
            max_depth: 最大递归深度限制，防止无限递归
        """
        self.max_depth = max_depth
        self.scenario_counter = 0
        logger.info("CounterfactualSimulator initialized with max_depth=%d", max_depth)

    def generate_counterfactuals(
        self,
        hypothesis: Dict[str, float],
        num_scenarios: int = 3
    ) -> List[Dict[str, float]]:
        """
        生成反事实场景攻击给定假设
        
        Args:
            hypothesis: 原始假设参数
            num_scenarios: 要生成的反事实场景数量
            
        Returns:
            反事实场景列表，每个场景都是对原始假设的修改
            
        Raises:
            ValueError: 如果输入假设为空或num_scenarios为负数
        """
        if not hypothesis:
            logger.error("Empty hypothesis provided")
            raise ValueError("Hypothesis cannot be empty")
            
        if num_scenarios <= 0:
            logger.warning("num_scenarios must be positive, using default value 3")
            num_scenarios = 3
            
        counterfactuals = []
        logger.debug("Generating %d counterfactuals for hypothesis %s", num_scenarios, hypothesis)
        
        for _ in range(num_scenarios):
            self.scenario_counter += 1
            # 生成参数扰动
            perturbed = {}
            for key, value in hypothesis.items():
                # 随机选择增加或减少参数值
                change = random.uniform(-0.2, 0.2) * value
                perturbed[key] = value + change
                
            counterfactuals.append(perturbed)
            logger.debug("Generated counterfactual #%d: %s", self.scenario_counter, perturbed)
            
        logger.info("Generated %d counterfactual scenarios", len(counterfactuals))
        return counterfactuals


def validate_search_space_reduction(
    original_size: int,
    pruned_size: int,
    iterations: int
) -> float:
    """
    验证搜索空间缩减效率
    
    Args:
        original_size: 原始搜索空间大小
        pruned_size: 剪枝后的搜索空间大小
        iterations: 执行的迭代次数
        
    Returns:
        效率比率 (0.0到1.0，1.0表示完全剪枝)
        
    Raises:
        ValueError: 如果输入参数无效
    """
    if original_size <= 0 or pruned_size < 0:
        logger.error("Invalid search space sizes: original=%d, pruned=%d", original_size, pruned_size)
        raise ValueError("Search space sizes must be positive")
        
    if iterations <= 0:
        logger.error("Invalid iterations count: %d", iterations)
        raise ValueError("Iterations must be positive")
        
    if pruned_size > original_size:
        logger.warning("Pruned size (%d) larger than original (%d), clamping to original", 
                      pruned_size, original_size)
        pruned_size = original_size
        
    reduction_ratio = 1.0 - (pruned_size / original_size)
    efficiency = reduction_ratio / math.log10(iterations + 1)  # 对数缩放效率
    
    logger.info("Search space reduction: original=%d, pruned=%d, efficiency=%.3f", 
                original_size, pruned_size, efficiency)
    return min(max(efficiency, 0.0), 1.0)  # 确保在0-1范围内


def verify_pruning_efficiency(
    root_hypothesis: Dict[str, float],
    simulator: CounterfactualSimulator,
    max_depth: int = 3,
    branch_factor: int = 2
) -> Tuple[TreeNode, Dict[str, float]]:
    """
    验证剪枝策略效率的主函数
    
    构建推演树，应用反事实攻击，计算剪枝效率
    
    Args:
        root_hypothesis: 根节点假设参数
        simulator: 反事实模拟器实例
        max_depth: 树的最大深度
        branch_factor: 每个节点的分支因子
        
    Returns:
        元组 (根节点, 效率指标字典)
        
    Raises:
        ValueError: 如果输入参数无效
        RuntimeError: 如果递归深度超过限制
    """
    # 输入验证
    if not root_hypothesis:
        logger.error("Empty root hypothesis provided")
        raise ValueError("Root hypothesis cannot be empty")
        
    if max_depth <= 0:
        logger.error("Invalid max_depth: %d", max_depth)
        raise ValueError("Max depth must be positive")
        
    if branch_factor <= 0:
        logger.error("Invalid branch_factor: %d", branch_factor)
        raise ValueError("Branch factor must be positive")
        
    logger.info("Starting pruning efficiency verification with max_depth=%d, branch_factor=%d", 
                max_depth, branch_factor)
    
    # 初始化根节点
    root = TreeNode(
        hypothesis_id="root",
        parameters=root_hypothesis,
        depth=0
    )
    
    # 统计指标
    stats = {
        'total_nodes': 1,
        'falsified_nodes': 0,
        'max_depth_reached': 0,
        'original_space_size': 0,
        'pruned_space_size': 0,
        'efficiency': 0.0,
        'time_elapsed': 0.0
    }
    
    start_time = perf_counter()
    
    try:
        # 构建推演树
        _build_counterfactual_tree(
            node=root,
            simulator=simulator,
            current_depth=1,
            max_depth=max_depth,
            branch_factor=branch_factor,
            stats=stats
        )
        
        # 计算剪枝效率
        stats['original_space_size'] = (branch_factor ** (max_depth + 1) - 1) // (branch_factor - 1)
        stats['pruned_space_size'] = stats['total_nodes']
        stats['efficiency'] = validate_search_space_reduction(
            stats['original_space_size'],
            stats['pruned_space_size'],
            stats['total_nodes']
        )
        
    except RecursionError as e:
        logger.error("Recursion depth exceeded: %s", str(e))
        raise RuntimeError("Maximum recursion depth exceeded") from e
    except Exception as e:
        logger.error("Unexpected error during verification: %s", str(e))
        raise RuntimeError(f"Verification failed: {str(e)}") from e
    finally:
        stats['time_elapsed'] = perf_counter() - start_time
        
    logger.info("Verification completed. Efficiency: %.3f", stats['efficiency'])
    return root, stats


def _build_counterfactual_tree(
    node: TreeNode,
    simulator: CounterfactualSimulator,
    current_depth: int,
    max_depth: int,
    branch_factor: int,
    stats: Dict[str, int]
) -> None:
    """
    递归构建反事实推演树的辅助函数
    
    Args:
        node: 当前节点
        simulator: 反事实模拟器
        current_depth: 当前递归深度
        max_depth: 最大允许深度
        branch_factor: 分支因子
        stats: 统计信息字典
    """
    # 边界检查
    if current_depth > max_depth:
        logger.debug("Max depth reached at node %s", node.hypothesis_id)
        stats['max_depth_reached'] = max(stats['max_depth_reached'], current_depth - 1)
        return
        
    # 生成反事实场景
    try:
        counterfactuals = simulator.generate_counterfactuals(
            hypothesis=node.parameters,
            num_scenarios=branch_factor
        )
    except ValueError as e:
        logger.warning("Failed to generate counterfactuals for node %s: %s", 
                      node.hypothesis_id, str(e))
        return
        
    # 处理每个反事实场景
    for i, cf in enumerate(counterfactuals):
        stats['total_nodes'] += 1
        child_id = f"{node.hypothesis_id}_{current_depth}_{i}"
        
        # 随机决定是否证伪 (模拟实际验证过程)
        is_falsified = random.random() < 0.3  # 30%概率被证伪
        
        child = TreeNode(
            hypothesis_id=child_id,
            parameters=cf,
            depth=current_depth,
            is_falsified=is_falsified
        )
        node.children.append(child)
        
        if is_falsified:
            stats['falsified_nodes'] += 1
            logger.debug("Node %s falsified, pruning branch", child_id)
            continue  # 剪枝，不继续构建子树
            
        # 递归构建子树
        _build_counterfactual_tree(
            node=child,
            simulator=simulator,
            current_depth=current_depth + 1,
            max_depth=max_depth,
            branch_factor=branch_factor,
            stats=stats
        )


# 使用示例
if __name__ == "__main__":
    # 示例假设
    example_hypothesis = {
        'param1': 1.0,
        'param2': 0.5,
        'param3': 2.0
    }
    
    # 创建模拟器
    simulator = CounterfactualSimulator(max_depth=5)
    
    try:
        # 验证剪枝效率
        root, results = verify_pruning_efficiency(
            root_hypothesis=example_hypothesis,
            simulator=simulator,
            max_depth=3,
            branch_factor=2
        )
        
        # 打印结果
        print("\n验证结果:")
        print(f"原始搜索空间大小: {results['original_space_size']}")
        print(f"剪枝后空间大小: {results['pruned_space_size']}")
        print(f"剪枝效率: {results['efficiency']:.3f}")
        print(f"证伪节点数: {results['falsified_nodes']}")
        print(f"最大深度达到: {results['max_depth_reached']}")
        print(f"耗时: {results['time_elapsed']:.4f}秒")
        
    except Exception as e:
        print(f"验证失败: {str(e)}")