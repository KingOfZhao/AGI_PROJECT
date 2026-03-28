"""
auto_基于时序衰减与结果反馈的节点活跃度动态评_374d3c

该模块实现了一个基于时序衰减与结果反馈的节点活跃度动态评分系统。
主要功能包括：
1. 动态计算节点活跃度分数，结合时间衰减和调用结果反馈。
2. 支持新节点的冷启动处理。
3. 提供完整的日志记录和错误处理机制。
"""

import logging
import math
import time
from typing import Dict, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('node_activity.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NodeActivityScorer:
    """
    基于时序衰减与结果反馈的节点活跃度动态评分系统。
    
    数学模型：
    活跃度分数 = base_score * (1 + decay_rate)^(-time_delta) * (1 + feedback_factor * success_rate)
    
    其中：
    - base_score: 节点的基础分数（冷启动初始值）
    - decay_rate: 时间衰减率（0 < decay_rate <= 1）
    - time_delta: 距离上次成功调用的时间间隔（秒）
    - feedback_factor: 反馈影响因子（0 < feedback_factor <= 1）
    - success_rate: 成功调用比例（0 <= success_rate <= 1）
    """

    def __init__(
        self,
        base_score: float = 50.0,
        decay_rate: float = 0.1,
        feedback_factor: float = 0.5,
        cold_start_period: int = 3600
    ):
        """
        初始化节点活跃度评分系统。
        
        :param base_score: 新节点的基础分数，默认50.0
        :param decay_rate: 时间衰减率，默认0.1
        :param feedback_factor: 反馈影响因子，默认0.5
        :param cold_start_period: 冷启动周期（秒），默认3600秒（1小时）
        """
        if not 0 < decay_rate <= 1:
            raise ValueError("decay_rate must be between 0 and 1")
        if not 0 < feedback_factor <= 1:
            raise ValueError("feedback_factor must be between 0 and 1")
        if base_score <= 0:
            raise ValueError("base_score must be positive")
        if cold_start_period <= 0:
            raise ValueError("cold_start_period must be positive")

        self.base_score = base_score
        self.decay_rate = decay_rate
        self.feedback_factor = feedback_factor
        self.cold_start_period = cold_start_period
        
        # 存储节点信息：{node_id: (last_success_time, success_count, total_count)}
        self.nodes: Dict[str, Tuple[float, int, int]] = {}
        
        logger.info(
            "NodeActivityScorer initialized with base_score=%.2f, decay_rate=%.2f, "
            "feedback_factor=%.2f, cold_start_period=%d",
            base_score, decay_rate, feedback_factor, cold_start_period
        )

    def update_node(
        self,
        node_id: str,
        is_success: bool,
        timestamp: Optional[float] = None
    ) -> None:
        """
        更新节点的调用记录。
        
        :param node_id: 节点唯一标识符
        :param is_success: 调用是否成功
        :param timestamp: 调用时间戳（默认为当前时间）
        :raises ValueError: 如果node_id为空或timestamp为负数
        """
        if not node_id:
            raise ValueError("node_id cannot be empty")
        
        if timestamp is None:
            timestamp = time.time()
        elif timestamp < 0:
            raise ValueError("timestamp cannot be negative")
        
        if node_id not in self.nodes:
            # 冷启动处理：新节点初始记录
            self.nodes[node_id] = (timestamp, 1 if is_success else 0, 1)
            logger.info("New node registered: %s", node_id)
        else:
            last_time, success_count, total_count = self.nodes[node_id]
            
            # 更新成功计数和时间
            if is_success:
                success_count += 1
                last_time = timestamp
            
            total_count += 1
            self.nodes[node_id] = (last_time, success_count, total_count)
            
            logger.debug(
                "Updated node %s: success=%s, new_success_count=%d, total_count=%d",
                node_id, is_success, success_count, total_count
            )

    def calculate_score(self, node_id: str) -> float:
        """
        计算指定节点的当前活跃度分数。
        
        :param node_id: 节点唯一标识符
        :return: 活跃度分数（0到100）
        :raises KeyError: 如果节点不存在
        :raises ValueError: 如果计算过程中出现无效值
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id} not found")
        
        last_time, success_count, total_count = self.nodes[node_id]
        current_time = time.time()
        
        # 时间衰减计算
        time_delta = current_time - last_time
        if time_delta < 0:
            raise ValueError("Time delta cannot be negative")
        
        decay_factor = math.exp(-self.decay_rate * time_delta / self.cold_start_period)
        
        # 反馈因子计算
        success_rate = success_count / total_count if total_count > 0 else 0
        feedback_component = 1 + self.feedback_factor * (2 * success_rate - 1)
        
        # 最终分数计算
        raw_score = self.base_score * decay_factor * feedback_component
        
        # 分数归一化到0-100范围
        normalized_score = max(0.0, min(100.0, raw_score))
        
        logger.debug(
            "Calculated score for node %s: time_delta=%.2fs, decay_factor=%.4f, "
            "success_rate=%.2f, feedback_component=%.4f, raw_score=%.2f, normalized_score=%.2f",
            node_id, time_delta, decay_factor, success_rate, 
            feedback_component, raw_score, normalized_score
        )
        
        return normalized_score

    def get_all_scores(self) -> Dict[str, float]:
        """
        获取所有节点的当前活跃度分数。
        
        :return: 字典 {node_id: score}
        """
        return {node_id: self.calculate_score(node_id) for node_id in self.nodes}

    def remove_node(self, node_id: str) -> None:
        """
        从系统中移除节点。
        
        :param node_id: 要移除的节点ID
        :raises KeyError: 如果节点不存在
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id} not found")
        
        del self.nodes[node_id]
        logger.info("Node removed: %s", node_id)

    def _is_in_cold_start(self, node_id: str) -> bool:
        """
        检查节点是否仍在冷启动期。
        
        :param node_id: 节点ID
        :return: 如果在冷启动期返回True，否则False
        """
        if node_id not in self.nodes:
            return False
            
        last_time, _, _ = self.nodes[node_id]
        return (time.time() - last_time) < self.cold_start_period


# 使用示例
if __name__ == "__main__":
    # 创建评分器实例
    scorer = NodeActivityScorer(
        base_score=50.0,
        decay_rate=0.05,
        feedback_factor=0.7,
        cold_start_period=7200  # 2小时冷启动期
    )
    
    # 模拟节点调用
    nodes = ["node1", "node2", "node3"]
    
    # 初始调用（冷启动）
    for node in nodes:
        scorer.update_node(node, True)
        print(f"{node} initial score: {scorer.calculate_score(node):.2f}")
    
    # 模拟一段时间后的调用
    time.sleep(2)  # 模拟时间流逝
    
    # node1 成功调用
    scorer.update_node("node1", True)
    # node2 失败调用
    scorer.update_node("node2", False)
    # node3 不调用
    
    # 打印当前分数
    print("\nAfter 2 seconds:")
    for node in nodes:
        print(f"{node} score: {scorer.calculate_score(node):.2f}")
    
    # 获取所有分数
    print("\nAll scores:", scorer.get_all_scores())
    
    # 尝试移除节点
    scorer.remove_node("node3")
    print("\nAfter removing node3:", scorer.get_all_scores())