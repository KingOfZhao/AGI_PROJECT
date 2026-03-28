"""
模块: auto_基于_人机反馈熵_的信噪比动态阈值_在人_ade159
描述: 实现基于人机交互反馈熵的信噪比动态阈值系统，用于评估AI节点质量并动态调整权重。
"""

import math
import logging
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """人类反馈类型枚举"""
    CORRECTION = "correction"  # 修正
    ADOPTION = "adoption"      # 采纳
    IGNORE = "ignore"          # 忽略
    RANDOM = "random"          # 随机反馈


@dataclass
class NodeFeedback:
    """节点反馈数据结构"""
    node_id: str
    feedback_type: FeedbackType
    timestamp: float
    confidence: float = 1.0  # 反馈置信度[0.0-1.0]
    context: Optional[Dict] = None  # 上下文信息


@dataclass
class NodeMetrics:
    """节点评估指标"""
    entropy: float
    snr: float
    quality_score: float
    feedback_count: int
    last_updated: float


def calculate_feedback_entropy(
    feedback_history: List[NodeFeedback],
    window_size: int = 100,
    decay_factor: float = 0.95
) -> float:
    """
    计算节点的反馈熵值
    
    参数:
        feedback_history: 节点的反馈历史记录
        window_size: 滑动窗口大小(默认100)
        decay_factor: 时间衰减因子(默认0.95)
    
    返回:
        float: 计算得到的熵值(0.0-1.0)
    
    异常:
        ValueError: 当输入数据无效时抛出
    
    示例:
        >>> feedbacks = [NodeFeedback(...), ...]
        >>> entropy = calculate_feedback_entropy(feedbacks)
    """
    if not feedback_history:
        logger.warning("Empty feedback history provided")
        return 0.0
    
    if window_size <= 0:
        raise ValueError("Window size must be positive")
    
    if not (0 < decay_factor <= 1):
        raise ValueError("Decay factor must be in (0, 1]")
    
    # 获取最近的反馈记录
    recent_feedbacks = feedback_history[-window_size:]
    
    # 初始化计数器
    feedback_counts = {ft: 0.0 for ft in FeedbackType}
    total_weight = 0.0
    
    # 计算加权计数
    for i, feedback in enumerate(recent_feedbacks):
        weight = decay_factor ** (len(recent_feedbacks) - i - 1)
        feedback_counts[feedback.feedback_type] += weight
        total_weight += weight
    
    # 计算概率分布
    probabilities = []
    for count in feedback_counts.values():
        if total_weight > 0:
            prob = count / total_weight
            if prob > 0:
                probabilities.append(prob)
    
    # 计算熵值
    entropy = 0.0
    for prob in probabilities:
        entropy -= prob * math.log2(prob)
    
    # 归一化到[0,1]
    max_entropy = math.log2(len(FeedbackType))
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    
    logger.debug(f"Calculated entropy: {normalized_entropy:.3f}")
    return min(max(normalized_entropy, 0.0), 1.0)


def calculate_dynamic_snr(
    entropy: float,
    base_threshold: float = 0.5,
    adaptation_rate: float = 0.2
) -> Tuple[float, float]:
    """
    基于熵值计算动态信噪比阈值
    
    参数:
        entropy: 输入的熵值(0.0-1.0)
        base_threshold: 基础阈值(默认0.5)
        adaptation_rate: 自适应率(默认0.2)
    
    返回:
        Tuple[float, float]: (动态阈值, 信噪比)
    
    示例:
        >>> threshold, snr = calculate_dynamic_snr(0.7)
    """
    # 输入验证
    if not (0 <= entropy <= 1):
        logger.error(f"Invalid entropy value: {entropy}")
        raise ValueError("Entropy must be in [0, 1]")
    
    if not (0 <= base_threshold <= 1):
        raise ValueError("Base threshold must be in [0, 1]")
    
    # 计算动态调整因子
    entropy_deviation = abs(entropy - base_threshold)
    adjustment = adaptation_rate * entropy_deviation
    
    # 计算动态阈值
    if entropy > base_threshold:
        dynamic_threshold = base_threshold + adjustment
    else:
        dynamic_threshold = base_threshold - adjustment
    
    # 确保阈值在有效范围内
    dynamic_threshold = min(max(dynamic_threshold, 0.1), 0.9)
    
    # 计算信噪比(1-熵值)
    snr = 1 - entropy
    
    logger.info(f"Dynamic threshold: {dynamic_threshold:.3f}, SNR: {snr:.3f}")
    return dynamic_threshold, snr


def evaluate_node_quality(
    node_id: str,
    feedback_history: List[NodeFeedback],
    current_metrics: Optional[NodeMetrics] = None
) -> NodeMetrics:
    """
    评估节点质量并生成评估指标
    
    参数:
        node_id: 节点ID
        feedback_history: 节点的反馈历史
        current_metrics: 当前节点指标(可选)
    
    返回:
        NodeMetrics: 包含所有评估指标的数据对象
    
    示例:
        >>> metrics = evaluate_node_quality("node_123", feedbacks)
    """
    if not node_id:
        raise ValueError("Node ID cannot be empty")
    
    try:
        # 计算反馈熵
        entropy = calculate_feedback_entropy(feedback_history)
        
        # 计算动态信噪比
        threshold, snr = calculate_dynamic_snr(entropy)
        
        # 计算质量分数
        quality_score = snr * (1 - entropy)
        
        # 创建或更新指标
        metrics = NodeMetrics(
            entropy=entropy,
            snr=snr,
            quality_score=quality_score,
            feedback_count=len(feedback_history),
            last_updated=feedback_history[-1].timestamp if feedback_history else 0
        )
        
        logger.info(f"Node {node_id} quality evaluation: {metrics}")
        return metrics
    
    except Exception as e:
        logger.error(f"Error evaluating node quality: {str(e)}")
        raise


def should_downgrade_node(metrics: NodeMetrics, threshold: float = 0.3) -> bool:
    """
    判断节点是否应该被降权
    
    参数:
        metrics: 节点评估指标
        threshold: 降权阈值(默认0.3)
    
    返回:
        bool: True表示应该降权
    
    示例:
        >>> if should_downgrade_node(metrics):
        ...     print("Node should be downgraded")
    """
    if not (0 <= threshold <= 1):
        raise ValueError("Threshold must be in [0, 1]")
    
    # 高熵值且低信噪比表示节点质量差
    is_high_entropy = metrics.entropy > 0.7
    is_low_snr = metrics.snr < threshold
    
    # 需要有足够的反馈样本
    has_sufficient_data = metrics.feedback_count >= 10
    
    decision = is_high_entropy and is_low_snr and has_sufficient_data
    
    if decision:
        logger.warning(
            f"Node downgrade recommended: entropy={metrics.entropy:.2f}, "
            f"snr={metrics.snr:.2f}, feedbacks={metrics.feedback_count}"
        )
    
    return decision


# 示例使用
if __name__ == "__main__":
    # 模拟一些反馈数据
    from time import time
    
    def create_sample_feedbacks() -> List[NodeFeedback]:
        """创建示例反馈数据"""
        feedbacks = []
        now = time()
        
        # 创建多样化的反馈
        for i in range(50):
            # 模拟70%的随机反馈(高熵)
            if i % 10 in (1, 3, 5, 7, 9):
                fb_type = FeedbackType.RANDOM
            else:
                fb_type = FeedbackType.ADOPTION
            
            feedbacks.append(NodeFeedback(
                node_id="sample_node",
                feedback_type=fb_type,
                timestamp=now - (50 - i) * 3600,  # 每小时一个反馈
                confidence=0.9 if fb_type != FeedbackType.RANDOM else 0.5
            ))
        
        return feedbacks
    
    # 运行示例
    try:
        feedbacks = create_sample_feedbacks()
        metrics = evaluate_node_quality("sample_node", feedbacks)
        
        print("\nNode Quality Metrics:")
        print(f"Entropy: {metrics.entropy:.3f}")
        print(f"SNR: {metrics.snr:.3f}")
        print(f"Quality Score: {metrics.quality_score:.3f}")
        print(f"Feedback Count: {metrics.feedback_count}")
        
        if should_downgrade_node(metrics):
            print("\nRecommendation: This node should be downgraded due to poor performance")
        else:
            print("\nRecommendation: Node performance is acceptable")
    
    except Exception as e:
        logger.error(f"Example failed: {str(e)}")