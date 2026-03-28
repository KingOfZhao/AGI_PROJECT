"""
节点融合的'信息熵'增益评估模块

该模块实现了在AGI系统中，当发生'四向碰撞'产生重叠固化时，
评估新节点生成是否真正带来信息量提升的功能。
通过计算KL散度来量化信息增益，防止信息丢失或分辨率下降。

核心算法：
1. 计算原始节点集的概率分布
2. 计算融合后节点的概率分布
3. 使用KL散度评估信息增益
4. 根据阈值决定是否允许固化
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union
import logging
from dataclasses import dataclass
import math

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Node:
    """表示一个节点的数据结构"""
    id: str
    features: np.ndarray
    weight: float = 1.0
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.features, np.ndarray):
            raise TypeError("特征必须是numpy数组")
        if self.weight <= 0:
            raise ValueError("权重必须为正数")


@dataclass
class ValidationResult:
    """评估结果的数据结构"""
    allow_fusion: bool
    kl_divergence: float
    entropy_gain: float
    message: str
    original_entropy: float
    fused_entropy: float


def calculate_probability_distribution(
    nodes: List[Node],
    feature_bins: int = 10
) -> np.ndarray:
    """
    计算节点集的概率分布
    
    参数:
        nodes: 节点列表
        feature_bins: 特征离散化的bin数量
        
    返回:
        概率分布数组
        
    异常:
        ValueError: 如果节点列表为空或特征维度不一致
    """
    if not nodes:
        raise ValueError("节点列表不能为空")
    
    # 验证所有节点特征维度一致
    feature_dim = nodes[0].features.shape[0]
    for node in nodes:
        if node.features.shape[0] != feature_dim:
            raise ValueError("所有节点特征维度必须一致")
    
    # 合并所有特征并计算直方图
    all_features = np.array([node.features for node in nodes])
    hist, _ = np.histogramdd(all_features, bins=feature_bins)
    
    # 归一化为概率分布
    prob_dist = hist / np.sum(hist)
    
    # 添加极小值避免数值问题
    epsilon = 1e-10
    prob_dist = np.where(prob_dist == 0, epsilon, prob_dist)
    
    return prob_dist


def kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """
    计算两个概率分布之间的KL散度
    
    参数:
        p: 第一个概率分布
        q: 第二个概率分布
        
    返回:
        KL散度值
        
    异常:
        ValueError: 如果分布形状不匹配或包含非正值
    """
    if p.shape != q.shape:
        raise ValueError("概率分布形状必须匹配")
    
    if np.any(p <= 0) or np.any(q <= 0):
        raise ValueError("概率分布必须为正值")
    
    # 计算KL散度
    kl = np.sum(p * np.log(p / q))
    
    # 边界检查
    if math.isnan(kl) or math.isinf(kl):
        logger.warning("KL散度计算结果异常，返回最大值")
        return float('inf')
    
    return kl


def evaluate_fusion_gain(
    original_nodes: List[Node],
    fused_node: Node,
    kl_threshold: float = 0.1,
    entropy_threshold: float = 0.05
) -> ValidationResult:
    """
    评估节点融合的信息增益
    
    参数:
        original_nodes: 原始节点列表
        fused_node: 融合后的节点
        kl_threshold: KL散度阈值，超过此值认为信息丢失
        entropy_threshold: 熵变化阈值，小于此值认为信息增益不足
        
    返回:
        ValidationResult对象，包含评估结果和详细信息
        
    示例:
        >>> nodes = [Node("n1", np.array([1.0, 2.0])), 
        ...          Node("n2", np.array([1.5, 2.5]))]
        >>> fused = Node("fused", np.array([1.25, 2.25]))
        >>> result = evaluate_fusion_gain(nodes, fused)
        >>> print(result.allow_fusion)
        True
    """
    # 输入验证
    if not original_nodes:
        raise ValueError("原始节点列表不能为空")
    
    if not isinstance(fused_node, Node):
        raise TypeError("融合节点必须是Node类型")
    
    # 计算原始节点集的概率分布和熵
    try:
        original_dist = calculate_probability_distribution(original_nodes)
        original_entropy = -np.sum(original_dist * np.log(original_dist))
    except Exception as e:
        logger.error(f"计算原始节点熵失败: {str(e)}")
        raise
    
    # 计算融合节点的概率分布和熵
    try:
        fused_dist = calculate_probability_distribution([fused_node])
        fused_entropy = -np.sum(fused_dist * np.log(fused_dist))
    except Exception as e:
        logger.error(f"计算融合节点熵失败: {str(e)}")
        raise
    
    # 计算KL散度
    try:
        kl_div = kl_divergence(fused_dist, original_dist)
    except Exception as e:
        logger.error(f"计算KL散度失败: {str(e)}")
        kl_div = float('inf')
    
    # 计算熵增益
    entropy_gain = fused_entropy - original_entropy
    
    # 评估结果
    if kl_div > kl_threshold:
        msg = (f"KL散度过高({kl_div:.4f} > {kl_threshold})，"
               f"信息丢失严重，阻止融合")
        allow_fusion = False
    elif abs(entropy_gain) < entropy_threshold:
        msg = (f"熵增益不足({entropy_gain:.4f} < {entropy_threshold})，"
               f"信息分辨率下降，阻止融合")
        allow_fusion = False
    else:
        msg = (f"融合带来信息增益(KL={kl_div:.4f}, "
               f"熵增益={entropy_gain:.4f})，允许融合")
        allow_fusion = True
    
    logger.info(msg)
    
    return ValidationResult(
        allow_fusion=allow_fusion,
        kl_divergence=kl_div,
        entropy_gain=entropy_gain,
        message=msg,
        original_entropy=original_entropy,
        fused_entropy=fused_entropy
    )


def validate_node_features(nodes: List[Node]) -> bool:
    """
    验证节点特征的有效性
    
    参数:
        nodes: 节点列表
        
    返回:
        bool: 特征是否有效
        
    示例:
        >>> nodes = [Node("n1", np.array([1.0, 2.0]))]
        >>> validate_node_features(nodes)
        True
    """
    if not nodes:
        return False
    
    feature_dim = nodes[0].features.shape[0]
    
    for node in nodes:
        # 检查特征维度一致性
        if node.features.shape[0] != feature_dim:
            logger.warning(f"节点{node.id}特征维度不一致")
            return False
        
        # 检查特征值是否有限
        if not np.all(np.isfinite(node.features)):
            logger.warning(f"节点{node.id}包含无效特征值")
            return False
    
    return True


# 使用示例
if __name__ == "__main__":
    # 创建示例节点
    node1 = Node("node1", np.array([1.0, 2.0, 3.0]))
    node2 = Node("node2", np.array([1.1, 2.1, 3.1]))
    node3 = Node("node3", np.array([1.2, 2.2, 3.2]))
    node4 = Node("node4", np.array([1.3, 2.3, 3.3]))
    
    # 创建融合节点（良好融合）
    good_fused = Node("good_fused", np.array([1.15, 2.15, 3.15]))
    
    # 创建融合节点（信息丢失）
    bad_fused = Node("bad_fused", np.array([2.0, 3.0, 4.0]))
    
    # 评估良好融合
    print("评估良好融合:")
    result = evaluate_fusion_gain([node1, node2, node3, node4], good_fused)
    print(f"允许融合: {result.allow_fusion}")
    print(f"KL散度: {result.kl_divergence:.4f}")
    print(f"熵增益: {result.entropy_gain:.4f}")
    print(f"信息: {result.message}\n")
    
    # 评估不良融合
    print("评估不良融合:")
    result = evaluate_fusion_gain([node1, node2, node3, node4], bad_fused)
    print(f"允许融合: {result.allow_fusion}")
    print(f"KL散度: {result.kl_divergence:.4f}")
    print(f"熵增益: {result.entropy_gain:.4f}")
    print(f"信息: {result.message}")