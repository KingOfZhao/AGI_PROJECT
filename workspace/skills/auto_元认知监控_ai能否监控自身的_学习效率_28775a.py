"""
模块: auto_元认知监控_ai能否监控自身的_学习效率_28775a
描述: 实现基于成本效益分析的元认知监控系统。该系统评估构建新节点（如神经网络神经元、
      决策树分支或MCTS节点）的边际效益与边际成本。当成本超过收益时，自动停止探索，
      从而优化计算资源分配，避免在低潜力路径上浪费资源。
"""

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from uuid import uuid4, UUID

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NodeProfile:
    """
    被监控节点的配置文件。
    
    Attributes:
        node_id (UUID): 节点唯一标识符。
        depth (int): 当前节点在搜索树或网络中的深度。
        predicted_gain (float): 预测开启该节点带来的误差减少量（0.0到1.0）。
        estimated_cost (float): 预计消耗的计算资源（归一化后的FLOPs或时间）。
        status (str): 节点当前状态.
    """
    node_id: UUID = field(default_factory=uuid4)
    depth: int = 0
    predicted_gain: float = 0.0
    estimated_cost: float = 0.0
    status: str = "pending"

@dataclass
class MetaCognitiveConfig:
    """
    元认知控制参数。
    
    Attributes:
        cost_threshold (float): 绝对成本阈值，超过此值直接拒绝。
        roi_threshold (float): 投资回报率阈值。
        history_size (int): 用于计算平均效率的历史窗口大小。
        decay_factor (float): 深度衰减因子，越深的节点需要越高的收益。
    """
    cost_threshold: float = 1000.0
    roi_threshold: float = 0.05
    history_size: int = 10
    decay_factor: float = 0.9

class MetacognitiveMonitor:
    """
    元认知监控器核心类。
    
    负责追踪系统的学习效率，并在探索新节点前进行成本效益分析。
    """
    
    def __init__(self, config: Optional[MetaCognitiveConfig] = None):
        """
        初始化监控器。
        
        Args:
            config (Optional[MetaCognitiveConfig]): 配置对象，如果为None则使用默认配置。
        """
        self.config = config if config else MetaCognitiveConfig()
        self._efficiency_history: List[float] = []
        self._total_resources_consumed: float = 0.0
        self._total_gain_realized: float = 0.0
        logger.info("Metacognitive Monitor initialized with config: %s", self.config)

    def _calculate_marginal_efficiency(self, current_cost: float, current_gain: float) -> float:
        """
        [辅助函数] 计算当前的边际效率。
        
        基于历史滑动窗口计算加权效率，近期的效率权重更高。
        
        Args:
            current_cost (float): 当前操作的成本。
            current_gain (float): 当前操作的收益。
            
        Returns:
            float: 计算出的效率指数。
        """
        if current_cost <= 0:
            return float('inf')
        
        instant_efficiency = current_gain / current_cost
        
        # 维护滑动窗口
        self._efficiency_history.append(instant_efficiency)
        if len(self._efficiency_history) > self.config.history_size:
            self._efficiency_history.pop(0)
            
        # 计算加权平均（简单的移动平均）
        avg_efficiency = sum(self._efficiency_history) / len(self._efficiency_history)
        
        logger.debug(f"Current instant efficiency: {instant_efficiency:.4f}, Avg: {avg_efficiency:.4f}")
        return avg_efficiency

    def evaluate_exploration_potential(self, node: NodeProfile) -> Tuple[bool, str]:
        """
        [核心函数 1] 评估是否应该探索特定节点。
        
        综合考虑绝对成本、预测ROI以及深度衰减。
        
        Args:
            node (NodeProfile): 待评估的节点对象。
            
        Returns:
            Tuple[bool, str]: (是否允许探索, 决策理由)
        
        Raises:
            ValueError: 如果输入数据无效。
        """
        # 数据验证
        if node.predicted_gain < 0 or node.estimated_cost < 0:
            logger.error("Invalid input: Negative cost or gain detected.")
            raise ValueError("Cost and gain must be non-negative.")
            
        logger.info(f"Evaluating Node {node.node_id} at Depth {node.depth}...")

        # 1. 绝对成本检查
        if node.estimated_cost > self.config.cost_threshold:
            reason = "Rejected: Exceeded absolute cost threshold."
            logger.warning(reason)
            return False, reason

        # 2. 深度惩罚
        # 越深的节点，不确定性越大，要求更高的预测收益
        depth_penalty = self.config.decay_factor ** node.depth
        adjusted_gain = node.predicted_gain * depth_penalty
        
        # 3. 边际效益检查
        if node.estimated_cost == 0:
            roi = float('inf')
        else:
            roi = adjusted_gain / node.estimated_cost

        if roi < self.config.roi_threshold:
            reason = f"Rejected: ROI ({roi:.4f}) below threshold ({self.config.roi_threshold})."
            logger.warning(reason)
            return False, reason

        # 4. 全局效率趋势检查
        # 如果系统整体学习效率正在下降，则变得更保守
        avg_eff = self._calculate_marginal_efficiency(node.estimated_cost, adjusted_gain)
        
        # 动态调整阈值（示例：如果平均效率极低，即使ROI达标也可能拒绝）
        # 这里简化处理，仅记录日志用于监控
        if avg_eff < (self.config.roi_threshold / 2):
            logger.warning("System learning efficiency is dropping significantly. Consider halting global search.")

        reason = f"Approved: ROI {roi:.4f} meets requirements."
        logger.info(reason)
        return True, reason

    def update_global_stats(self, actual_cost: float, actual_gain: float) -> None:
        """
        [核心函数 2] 更新系统全局学习统计信息。
        
        在节点处理完成后调用，用于修正未来的预测模型。
        
        Args:
            actual_cost (float): 实际消耗的资源。
            actual_gain (float): 实际获得的误差减少/性能提升。
        """
        if actual_cost < 0 or actual_gain < 0:
            logger.error("Attempted to update stats with negative values.")
            return

        self._total_resources_consumed += actual_cost
        self._total_gain_realized += actual_gain
        
        # 触发效率计算以更新历史窗口
        self._calculate_marginal_efficiency(actual_cost, actual_gain)
        
        overall_eff = 0.0
        if self._total_resources_consumed > 0:
            overall_eff = self._total_gain_realized / self._total_resources_consumed
            
        logger.info(f"Global stats updated. Total Cost: {self._total_resources_consumed:.2f}, "
                    f"Total Gain: {self._total_gain_realized:.4f}, "
                    f"Overall Efficiency: {overall_eff:.4f}")

# 使用示例
if __name__ == "__main__":
    # 初始化监控系统
    monitor_config = MetaCognitiveConfig(
        cost_threshold=500.0,
        roi_threshold=0.01,
        decay_factor=0.95
    )
    monitor = MetacognitiveMonitor(config=monitor_config)

    print("--- 场景 1: 高收益，低成本 (应该通过) ---")
    node1 = NodeProfile(
        depth=2,
        predicted_gain=0.8,  # 预测误差减少0.8
        estimated_cost=10.0   # 成本很低
    )
    decision, msg = monitor.evaluate_exploration_potential(node1)
    print(f"Decision: {decision}, Message: {msg}")
    if decision:
        # 模拟处理...
        monitor.update_global_stats(10.0, 0.8)

    print("\n--- 场景 2: 低收益，高成本 (应该拒绝) ---")
    node2 = NodeProfile(
        depth=5,
        predicted_gain=0.05, # 预测收益很低
        estimated_cost=200.0  # 成本较高
    )
    # 深度为5，惩罚严重，实际adjusted_gain会非常低
    decision, msg = monitor.evaluate_exploration_potential(node2)
    print(f"Decision: {decision}, Message: {msg}")

    print("\n--- 场景 3: 临界情况 (动态检查) ---")
    node3 = NodeProfile(
        depth=1,
        predicted_gain=0.5,
        estimated_cost=40.0 # ROI = 0.0125 > 0.01，应该通过
    )
    decision, msg = monitor.evaluate_exploration_potential(node3)
    print(f"Decision: {decision}, Message: {msg}")