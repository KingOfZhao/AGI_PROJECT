"""
人机共生循环中的'贝叶斯置信度'动态校准模块

该模块实现了一个反馈接口，用于将人类的模糊反馈（如'这个方法不太好'）转化为精确的数学信号，
并实时更新相关节点的贝叶斯后验概率。支持多种反馈类型和自定义映射规则。

核心功能：
1. 反馈信号映射：将模糊人类反馈转化为数值信号
2. 贝叶斯后验概率更新：基于实践结果动态校准置信度
3. 多节点管理：支持同时跟踪多个知识节点的置信度

典型用例：
>>> calibrator = BayesianConfidenceCalibrator()
>>> calibrator.update_posterior("node_1", "positive", strength=0.8)
>>> calibrator.update_posterior("node_2", "negative", strength=0.3)
>>> print(calibrator.get_confidence("node_1"))
"""

import logging
import math
from typing import Dict, Literal, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型枚举"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    STRONG_POSITIVE = "strong_positive"
    STRONG_NEGATIVE = "strong_negative"


@dataclass
class ConfidenceNode:
    """置信度节点数据结构"""
    alpha: float = 1.0  # 成功计数 + 先验
    beta: float = 1.0   # 失败计数 + 先验
    history: list = field(default_factory=list)  # 历史记录
    
    @property
    def confidence(self) -> float:
        """计算当前置信度（后验均值）"""
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def variance(self) -> float:
        """计算当前置信度方差"""
        a = self.alpha
        b = self.beta
        return (a * b) / ((a + b)**2 * (a + b + 1))


class BayesianConfidenceCalibrator:
    """
    人机共生循环中的贝叶斯置信度动态校准器
    
    该类实现了基于贝叶斯推断的置信度校准系统，能够将人类的模糊反馈转化为精确的数学调整，
    并实时更新相关节点的后验概率。
    
    特性：
    - 支持多种反馈类型和自定义映射
    - 自动边界检查和数据验证
    - 详细的错误处理和日志记录
    - 支持多节点管理
    
    使用示例：
    >>> calibrator = BayesianConfidenceCalibrator()
    >>> # 添加新节点
    >>> calibrator.add_node("method_1")
    >>> # 更新置信度
    >>> calibrator.update_posterior("method_1", "positive", strength=0.7)
    >>> calibrator.update_posterior("method_1", "negative", strength=0.3)
    >>> # 获取置信度
    >>> confidence = calibrator.get_confidence("method_1")
    """
    
    def __init__(self, 
                 feedback_mapping: Optional[Dict[FeedbackType, Tuple[float, float]]] = None,
                 default_strength: float = 0.5,
                 min_samples: int = 5):
        """
        初始化贝叶斯置信度校准器
        
        参数:
            feedback_mapping: 自定义反馈类型到(成功调整, 失败调整)的映射
            default_strength: 默认反馈强度
            min_samples: 最小样本数，用于计算可靠置信度
        """
        self.nodes: Dict[str, ConfidenceNode] = {}
        self.min_samples = min_samples
        self.default_strength = default_strength
        
        # 默认反馈映射：反馈类型 -> (成功调整, 失败调整)
        self.feedback_mapping = feedback_mapping or {
            FeedbackType.POSITIVE: (0.7, 0.3),
            FeedbackType.NEGATIVE: (0.3, 0.7),
            FeedbackType.NEUTRAL: (0.5, 0.5),
            FeedbackType.STRONG_POSITIVE: (0.9, 0.1),
            FeedbackType.STRONG_NEGATIVE: (0.1, 0.9)
        }
        
        logger.info("Initialized BayesianConfidenceCalibrator with min_samples=%d", min_samples)
    
    def add_node(self, node_id: str, initial_alpha: float = 1.0, initial_beta: float = 1.0) -> None:
        """
        添加一个新的置信度节点
        
        参数:
            node_id: 节点唯一标识符
            initial_alpha: 初始成功计数（先验）
            initial_beta: 初始失败计数（先验）
            
        异常:
            ValueError: 如果节点已存在或参数无效
        """
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
            
        if node_id in self.nodes:
            raise ValueError(f"Node {node_id} already exists")
            
        if initial_alpha <= 0 or initial_beta <= 0:
            raise ValueError("Initial alpha and beta must be positive")
            
        self.nodes[node_id] = ConfidenceNode(alpha=initial_alpha, beta=initial_beta)
        logger.info("Added new node: %s with initial alpha=%.2f, beta=%.2f", 
                   node_id, initial_alpha, initial_beta)
    
    def _validate_feedback_strength(self, strength: float) -> float:
        """验证反馈强度在[0,1]范围内"""
        if not 0 <= strength <= 1:
            logger.warning("Strength %.2f out of bounds, clamping to [0,1]", strength)
            strength = max(0.0, min(1.0, strength))
        return strength
    
    def _map_feedback_to_signal(self, 
                               feedback_type: Union[FeedbackType, str],
                               strength: float) -> Tuple[float, float]:
        """
        将模糊反馈映射为数值信号
        
        参数:
            feedback_type: 反馈类型（枚举或字符串）
            strength: 反馈强度[0,1]
            
        返回:
            Tuple[float, float]: (成功调整, 失败调整)
        """
        if isinstance(feedback_type, str):
            try:
                feedback_type = FeedbackType(feedback_type.lower())
            except ValueError:
                logger.warning("Unknown feedback type: %s, using NEUTRAL", feedback_type)
                feedback_type = FeedbackType.NEUTRAL
                
        if feedback_type not in self.feedback_mapping:
            logger.warning("Feedback type %s not in mapping, using NEUTRAL", feedback_type)
            feedback_type = FeedbackType.NEUTRAL
            
        base_success, base_failure = self.feedback_mapping[feedback_type]
        adjusted_success = base_success * strength
        adjusted_failure = base_failure * strength
        
        logger.debug("Mapped feedback %s (strength=%.2f) to success=%.2f, failure=%.2f",
                    feedback_type.value, strength, adjusted_success, adjusted_failure)
        return adjusted_success, adjusted_failure
    
    def update_posterior(self, 
                        node_id: str,
                        feedback_type: Union[FeedbackType, str],
                        strength: Optional[float] = None) -> float:
        """
        基于人类反馈更新节点的后验概率
        
        参数:
            node_id: 要更新的节点ID
            feedback_type: 反馈类型
            strength: 反馈强度[0,1]，None则使用默认值
            
        返回:
            float: 更新后的置信度
            
        异常:
            ValueError: 如果节点不存在或参数无效
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist. Add it first with add_node()")
            
        strength = self._validate_feedback_strength(strength if strength is not None else self.default_strength)
        success_adj, failure_adj = self._map_feedback_to_signal(feedback_type, strength)
        
        # 更新节点参数
        node = self.nodes[node_id]
        node.alpha += success_adj
        node.beta += failure_adj
        
        # 记录历史
        node.history.append({
            'feedback_type': feedback_type.value if isinstance(feedback_type, FeedbackType) else feedback_type,
            'strength': strength,
            'success_adj': success_adj,
            'failure_adj': failure_adj,
            'new_confidence': node.confidence
        })
        
        logger.info("Updated node %s: alpha=%.2f, beta=%.2f, confidence=%.4f",
                   node_id, node.alpha, node.beta, node.confidence)
        return node.confidence
    
    def get_confidence(self, node_id: str) -> float:
        """
        获取节点的当前置信度
        
        参数:
            node_id: 节点ID
            
        返回:
            float: 当前置信度[0,1]
            
        异常:
            ValueError: 如果节点不存在
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist")
            
        node = self.nodes[node_id]
        total_samples = node.alpha + node.beta - 2  # 减去初始先验
        
        if total_samples < self.min_samples:
            logger.warning("Node %s has insufficient samples (%d < %d), confidence may not be reliable",
                          node_id, total_samples, self.min_samples)
            
        return node.confidence
    
    def get_reliable_confidence(self, node_id: str) -> Tuple[float, bool]:
        """
        获取可靠置信度，并指示是否达到最小样本数
        
        参数:
            node_id: 节点ID
            
        返回:
            Tuple[float, bool]: (置信度, 是否可靠)
        """
        confidence = self.get_confidence(node_id)
        total_samples = self.nodes[node_id].alpha + self.nodes[node_id].beta - 2
        is_reliable = total_samples >= self.min_samples
        return confidence, is_reliable
    
    def get_all_confidences(self) -> Dict[str, Tuple[float, bool]]:
        """
        获取所有节点的可靠置信度
        
        返回:
            Dict[str, Tuple[float, bool]]: {节点ID: (置信度, 是否可靠)}
        """
        return {
            node_id: self.get_reliable_confidence(node_id)
            for node_id in self.nodes
        }
    
    def reset_node(self, node_id: str, initial_alpha: float = 1.0, initial_beta: float = 1.0) -> None:
        """
        重置节点的置信度
        
        参数:
            node_id: 节点ID
            initial_alpha: 新的初始成功计数
            initial_beta: 新的初始失败计数
        """
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist")
            
        if initial_alpha <= 0 or initial_beta <= 0:
            raise ValueError("Initial alpha and beta must be positive")
            
        self.nodes[node_id] = ConfidenceNode(alpha=initial_alpha, beta=initial_beta)
        logger.info("Reset node %s to alpha=%.2f, beta=%.2f", node_id, initial_alpha, initial_beta)


# 示例用法
if __name__ == "__main__":
    # 创建校准器实例
    calibrator = BayesianConfidenceCalibrator(min_samples=3)
    
    # 添加几个知识节点
    calibrator.add_node("method_A")
    calibrator.add_node("method_B", initial_alpha=2.0, initial_beta=1.0)
    
    # 模拟人类反馈
    print("\n=== 模拟人类反馈 ===")
    calibrator.update_posterior("method_A", "positive", 0.8)
    calibrator.update_posterior("method_A", "positive", 0.9)
    calibrator.update_posterior("method_A", "negative", 0.6)
    
    calibrator.update_posterior("method_B", FeedbackType.STRONG_POSITIVE, 0.7)
    calibrator.update_posterior("method_B", "neutral", 0.5)
    
    # 获取所有置信度
    print("\n=== 当前置信度 ===")
    for node_id, (confidence, is_reliable) in calibrator.get_all_confidences().items():
        print(f"{node_id}: {confidence:.4f} (reliable: {is_reliable})")
    
    # 测试边界情况
    print("\n=== 测试边界情况 ===")
    try:
        calibrator.update_posterior("nonexistent_node", "positive")
    except ValueError as e:
        print(f"Expected error: {e}")
    
    # 测试自动边界检查
    calibrator.update_posterior("method_A", "positive", 1.5)  # 会自动调整到[0,1]范围