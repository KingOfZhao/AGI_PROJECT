"""
模块: auto_四向碰撞中的_固化_路径优化问题_左右_04f948
描述: 四向碰撞中的‘固化’路径优化问题。
‘左右跨域重叠’最终需要‘固化为真实节点’。如何量化评估一次跨域重叠的质量？
需要建立指标来衡量重叠区域的信息熵减情况。即：验证通过跨域桥接，是否让原本
模糊（高熵）的目标域问题变得清晰（低熵），并据此调整迁移桥梁的权重。

领域: 信息论/系统动力学
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DomainState:
    """
    领域状态的数据结构。
    
    Attributes:
        node_id (str): 节点的唯一标识符。
        probability_vector (List[float]): 描述该领域状态的离散概率分布。
                                          必须满足归一化条件 (和为1)。
    """
    node_id: str
    probability_vector: List[float]

    def __post_init__(self):
        """数据验证：确保概率向量有效。"""
        if not self.probability_vector:
            raise ValueError("概率向量不能为空")
        if not math.isclose(sum(self.probability_vector), 1.0, rel_tol=1e-5):
            raise ValueError(f"概率向量之和必须为1.0，当前为: {sum(self.probability_vector)}")
        if any(p < 0 for p in self.probability_vector):
            raise ValueError("概率值不能为负")

def calculate_shannon_entropy(prob_dist: List[float]) -> float:
    """
    辅助函数：计算给定概率分布的香农熵。
    
    Args:
        prob_dist (List[float]): 归一化的概率分布列表。
        
    Returns:
        float: 信息熵值 (bits)。
    """
    entropy = 0.0
    for p in prob_dist:
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def evaluate_cross_domain_overlap_quality(
    source_domain: DomainState,
    target_domain: DomainState,
    bridge_weight: float = 1.0
) -> Tuple[float, Dict[str, float]]:
    """
    核心函数1：量化评估一次跨域重叠的质量。
    
    通过计算桥接前后的信息熵变化，判断跨域重叠是否带来了信息的清晰化（熵减）。
    这里假设跨域重叠会对目标域的概率分布产生加权影响，使其分布趋于集中。
    
    Args:
        source_domain (DomainState): 源领域状态（提供上下文）。
        target_domain (DomainState): 目标领域状态（待优化的对象）。
        bridge_weight (float): 迁移桥梁的基础权重 (0.0 到 1.0)。
        
    Returns:
        Tuple[float, Dict[str, float]]: 
            - float: 熵减量 (负值表示熵增，即模糊化)。
            - Dict: 包含详细指标的字典。
            
    Raises:
        ValueError: 如果维度不匹配或权重越界。
    """
    # 输入验证
    if not (0.0 <= bridge_weight <= 1.0):
        raise ValueError("桥梁权重必须在 0.0 和 1.0 之间")
        
    if len(source_domain.probability_vector) != len(target_domain.probability_vector):
        logger.warning(f"维度不匹配: 源 {len(source_domain.probability_vector)} vs 目标 {len(target_domain.probability_vector)}")
        raise ValueError("源域和目标域的概率向量维度必须一致以计算重叠")

    logger.info(f"开始评估跨域重叠: {source_domain.node_id} -> {target_domain.node_id}")

    # 1. 计算原始熵 (目标域的模糊程度)
    original_entropy = calculate_shannon_entropy(target_domain.probability_vector)
    
    # 2. 模拟“固化”/重叠效应
    # 假设重叠效应是源域分布对目标域分布的加权融合
    # 这里的融合系数 alpha 取决于 bridge_weight
    # 新分布 P_new = (1-alpha)*P_target + alpha * P_source
    alpha = bridge_weight * 0.5  # 简化的融合系数模型
    
    new_vector = []
    for p_t, p_s in zip(target_domain.probability_vector, source_domain.probability_vector):
        val = (1 - alpha) * p_t + alpha * p_s
        new_vector.append(val)
        
    # 归一化处理 (防止浮点误差)
    total = sum(new_vector)
    new_vector = [v / total for v in new_vector]
    
    # 3. 计算新熵
    new_entropy = calculate_shannon_entropy(new_vector)
    
    # 4. 计算熵减 (Entropy Reduction)
    entropy_reduction = original_entropy - new_entropy
    
    metrics = {
        "original_entropy": original_entropy,
        "new_entropy": new_entropy,
        "entropy_reduction": entropy_reduction,
        "bridge_weight_used": bridge_weight
    }
    
    logger.info(f"评估结果: 原始熵 {original_entropy:.4f}, 新熵 {new_entropy:.4f}, 熵减 {entropy_reduction:.4f}")
    
    return entropy_reduction, metrics

def adjust_bridge_weight_dynamically(
    current_weight: float,
    entropy_reduction_history: List[float],
    learning_rate: float = 0.1
) -> float:
    """
    核心函数2：根据历史熵减记录动态调整迁移桥梁的权重。
    
    如果跨域重叠持续带来熵减（信息变得清晰），则增加权重（固化路径）。
    如果导致熵增（信息变得混乱），则降低权重（削弱连接）。
    
    Args:
        current_weight (float): 当前的桥梁权重。
        entropy_reduction_history (List[float]): 历史熵减值列表 (最近的记录)。
        learning_rate (float): 调整的步长。
        
    Returns:
        float: 调整后的新权重。
    """
    if not entropy_reduction_history:
        return current_weight
        
    # 边界检查
    if learning_rate <= 0:
        raise ValueError("学习率必须为正数")

    # 计算平均趋势
    avg_reduction = sum(entropy_reduction_history) / len(entropy_reduction_history)
    
    adjustment = 0.0
    # 如果平均熵减为正（有效），增加权重
    if avg_reduction > 0.01:
        adjustment = learning_rate
        logger.debug(f"检测到有效熵减 ({avg_reduction:.4f})，增强桥梁。")
    # 如果平均熵减为负（有害），减少权重
    elif avg_reduction < -0.01:
        adjustment = -learning_rate
        logger.debug(f"检测到熵增 ({avg_reduction:.4f})，削弱桥梁。")
    else:
        logger.debug("熵变化不明显，保持权重。")
        
    new_weight = current_weight + adjustment
    
    # 权重截断 (保持在 0.0 到 1.0 之间)
    new_weight = max(0.0, min(1.0, new_weight))
    
    logger.info(f"权重调整: {current_weight:.4f} -> {new_weight:.4f}")
    
    return new_weight

if __name__ == "__main__":
    # 使用示例
    
    try:
        # 1. 定义领域状态
        # 目标域：比较模糊的状态 (分布相对均匀，高熵)
        target = DomainState(
            node_id="Target_Node_A", 
            probability_vector=[0.2, 0.2, 0.3, 0.3]
        )
        
        # 源域：相对确定的状态 (分布集中，低熵)
        source = DomainState(
            node_id="Source_Node_B", 
            probability_vector=[0.8, 0.1, 0.05, 0.05]
        )
        
        # 2. 评估重叠质量
        reduction, details = evaluate_cross_domain_overlap_quality(
            source, target, bridge_weight=0.8
        )
        
        print(f"--- 单次评估结果 ---
        熵减量: {reduction:.4f} bits
        详情: {details}
        ")
        
        # 3. 模拟动态调整过程
        history = [0.15, 0.12, 0.18, -0.05] # 模拟最近几次的熵减记录
        current_w = 0.5
        new_w = adjust_bridge_weight_dynamically(current_w, history, learning_rate=0.05)
        
        print(f"--- 动态调整结果 ---
        旧权重: {current_w}
        新权重: {new_w}
        ")

    except ValueError as e:
        logger.error(f"运行示例时发生错误: {e}")