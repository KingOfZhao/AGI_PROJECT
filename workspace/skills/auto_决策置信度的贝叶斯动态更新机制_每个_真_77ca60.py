"""
决策置信度的贝叶斯动态更新机制

该模块实现了一个基于树状结构的贝叶斯置信度更新系统。它允许在节点状态（验证/证伪）
发生变化时，通过贝叶斯推理将置信度变化向上传播至父节点，并向下修正子节点的权重，
从而实现系统决策置信度的动态校准。

核心功能：
1. 支持带权重的树形节点结构。
2. 基于贝叶斯后验概率的置信度向上传播。
3. 基于父节点置信度变化的子节点权重修正。
4. 完整的数据验证和日志记录。

Author: Senior Python Engineer (AGI System)
Date: 2023-10-27
"""

import logging
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
MIN_CONFIDENCE = 0.001  # 避免除零和log(0)的最小置信度
MAX_CONFIDENCE = 0.999  # 最大置信度
DEFAULT_PRIOR = 0.5     # 默认先验概率


@dataclass
class ReasoningNode:
    """
    推理节点类。
    
    代表AGI推理过程中的一个真实节点，包含其当前状态、置信度及父子关系。
    
    Attributes:
        node_id (str): 节点的唯一标识符。
        name (str): 节点名称。
        prior (float): 初始先验概率 (0.0 to 1.0)。
        confidence (float): 当前后验置信度 (0.0 to 1.0)。
        is_verified (Optional[bool]): 验证状态。True为验证，False为证伪，None为未定。
        children (List['ReasoningNode']): 子节点列表。
        parent (Optional['ReasoningNode']): 父节点引用。
        weight (float): 该节点在父节点计算中的权重 (0.0 to 1.0)。
    """
    node_id: str
    name: str
    prior: float = DEFAULT_PRIOR
    confidence: float = DEFAULT_PRIOR
    is_verified: Optional[bool] = None
    children: List['ReasoningNode'] = field(default_factory=list)
    parent: Optional['ReasoningNode'] = None
    weight: float = 1.0

    def __post_init__(self):
        """初始化后进行数据校验。"""
        self.prior = _validate_probability(self.prior, f"Node {self.node_id} prior")
        self.confidence = _validate_probability(self.confidence, f"Node {self.node_id} confidence")
        self.weight = _validate_probability(self.weight, f"Node {self.node_id} weight")

    def add_child(self, child_node: 'ReasoningNode'):
        """添加子节点并建立双向引用。"""
        if not isinstance(child_node, ReasoningNode):
            raise TypeError("Child must be an instance of ReasoningNode")
        child_node.parent = self
        self.children.append(child_node)
        logger.debug(f"Added child {child_node.node_id} to parent {self.node_id}")


def _validate_probability(value: float, context: str = "Value") -> float:
    """
    辅助函数：验证概率值是否在合法范围内，并强制裁剪。
    
    Args:
        value (float): 待验证的数值。
        context (str): 上下文描述，用于日志。
        
    Returns:
        float: 校正后的数值 (MIN_CONFIDENCE to MAX_CONFIDENCE)。
        
    Raises:
        TypeError: 如果输入不是浮点数或整数。
    """
    if not isinstance(value, (float, int)):
        raise TypeError(f"{context} must be a float, got {type(value)}")
    
    if not (0.0 <= value <= 1.0):
        logger.warning(f"{context} value {value} out of bounds [0, 1]. Clamping.")
    
    # 裁剪到安全范围，防止数学计算错误
    return max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, float(value)))


def _calculate_weighted_evidence(nodes: List[ReasoningNode]) -> Tuple[float, float]:
    """
    辅助函数：计算子节点列表提供的加权证据。
    
    在贝叶斯更新中，我们将子节点的置信度视为证据强度。
    
    Args:
        nodes (List[ReasoningNode]): 子节点列表。
        
    Returns:
        Tuple[float, float]: (正向证据累积, 负向证据累积)
    """
    pos_evidence = 0.0
    neg_evidence = 0.0
    
    if not nodes:
        return 1.0, 1.0 # 无证据则似然比为1（中性）

    for node in nodes:
        # 权重归一化预处理（这里简化处理，假设调用者管理权重总和）
        # 证据强度 = 节点置信度 * 权重
        # 如果节点被验证，它提供正向证据；如果被证伪，提供负向证据；未定则按置信度比例提供
        if node.is_verified is True:
            pos_evidence += node.confidence * node.weight
        elif node.is_verified is False:
            neg_evidence += (1.0 - node.confidence) * node.weight
        else:
            # 状态未定时，根据当前置信度模糊贡献
            pos_evidence += node.confidence * node.weight * 0.5 # 降低未定节点的影响力
            neg_evidence += (1.0 - node.confidence) * node.weight * 0.5
            
    return pos_evidence, neg_evidence


def update_confidence_upward(node: ReasoningNode, likelihood_ratio: float = 1.5) -> None:
    """
    核心函数：向上传播置信度更新。
    
    当一个节点被验证或证伪时，调用此函数更新其父节点的置信度。
    使用简化的贝叶斯公式：
    Posterior Odds = Prior Odds * Likelihood Ratio
    
    这里我们基于子节点的整体状态动态计算似然比。
    
    Args:
        node (ReasoningNode): 状态发生变化的源节点（子节点）。
        likelihood_ratio (float): 事件发生时的基础置信度倍率。
        
    Raises:
        ValueError: 如果节点孤立无父节点。
    """
    if node.parent is None:
        logger.info(f"Node {node.node_id} is root. No upward propagation.")
        return

    parent = node.parent
    
    # 1. 收集所有子节点的证据
    pos_ev, neg_ev = _calculate_weighted_evidence(parent.children)
    
    # 2. 计算新的后验概率
    # O(H) = P(H) / (1 - P(H))
    prior_odds = parent.prior / (1.0 - parent.prior)
    
    # 根据证据调整似然比 (简单模拟：证据差决定LR大小)
    dynamic_lr = 1.0
    if node.is_verified:
        dynamic_lr = likelihood_ratio * (1 + pos_ev)
    elif node.is_verified is False:
        dynamic_lr = 1.0 / (likelihood_ratio * (1 + neg_ev))
    
    # 更新 Odds
    post_odds = prior_odds * dynamic_lr
    
    # 转回概率 P(H) = O(H) / (1 + O(H))
    new_confidence = post_odds / (1.0 + post_odds)
    
    # 边界检查
    new_confidence = _validate_probability(new_confidence, f"Parent {parent.node_id} updated confidence")
    
    logger.info(f"Upward Update: Parent {parent.node_id} confidence {parent.confidence:.4f} -> {new_confidence:.4f} due to child {node.node_id}")
    
    parent.confidence = new_confidence
    
    # 递归向上传播
    update_confidence_upward(parent, likelihood_ratio)


def propagate_weights_downward(node: ReasoningNode, decay_factor: float = 0.9) -> None:
    """
    核心函数：向下修正子节点权重。
    
    当父节点的置信度发生显著变化时，子节点的权重应被重新评估。
    如果父节点置信度低，子节点的权重可能被稀释；如果父节点置信度高，子节点权重维持。
    
    Args:
        node (ReasoningNode): 父节点（置信度已更新）。
        decay_factor (float): 置信度转化为权重时的衰减系数。
    """
    if not node.children:
        return

    # 计算权重修正因子
    # 如果父节点置信度 > 0.5，因子接近1；如果 < 0.5，因子降低
    # 使用 Sigmoid 或线性映射，这里使用简单的线性映射
    # weight_modifier = 2 * confidence - 1 (range -1 to 1)
    # 更安全的计算方式：
    base_modifier = node.confidence * 2.0 # Range [0, 2]
    
    logger.info(f"Downward Propagation: Adjusting weights for children of {node.node_id} (Conf: {node.confidence:.4f})")

    for child in node.children:
        # 保留原始权重的一部分，加上基于父节点的新权重
        # NewWeight = OldWeight * (1-df) + (OldWeight * Modifier) * df
        # 简化模型：直接根据父节点置信度缩放子节点权重
        
        old_weight = child.weight
        adjustment = (base_modifier - 1.0) * decay_factor # 计算偏移量
        
        # 更新权重：原始权重 + 偏移
        new_weight = old_weight + adjustment
        
        # 防止负权重，并限制范围
        new_weight = _validate_probability(max(0.1, new_weight), f"Child {child.node_id} weight")
        
        child.weight = new_weight
        logger.debug(f"Child {child.node_id} weight updated: {old_weight:.4f} -> {new_weight:.4f}")
        
        # 递归向下传播
        propagate_weights_downward(child, decay_factor)


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 1. 构建推理树
    # 根节点：解决复杂AGI任务
    root = ReasoningNode(node_id="ROOT", name="AGI_Task_Solution", prior=0.5)
    
    # 子问题1：代码生成 (初始置信度 0.6)
    sub1 = ReasoningNode(node_id="S1", name="Code_Gen", prior=0.6)
    
    # 子问题2：逻辑推理 (初始置信度 0.4)
    sub2 = ReasoningNode(node_id="S2", name="Logic_Reasoning", prior=0.4)
    
    root.add_child(sub1)
    root.add_child(sub2)
    
    # 子子节点：代码生成下的具体模块
    sub1_1 = ReasoningNode(node_id="S1_1", name="Syntax_Check", prior=0.9)
    sub1.add_child(sub1_1)

    print(f"初始状态 - Root Confidence: {root.confidence:.4f}")
    print(f"初始状态 - S1 Confidence: {sub1.confidence:.4f}, Weight: {sub1.weight:.4f}")

    # 2. 模拟事件：子节点 S1_1 (语法检查) 被验证通过
    print("\n>>> Event: Syntax Check (S1_1) Verified as True")
    sub1_1.is_verified = True
    
    # 2.1 向上传播：从 S1_1 -> S1 -> ROOT
    # 先手动触发 S1_1 到 S1 的更新（模拟递归的第一步或叶子节点触发）
    # 在实际复杂系统中，这可能由事件监听器自动触发
    # 这里我们演示从叶子开始向上：
    update_confidence_upward(sub1_1, likelihood_ratio=2.0)
    
    # 注意：update_confidence_upward 是递归的，所以 S1 和 ROOT 的置信度应该都已经更新
    # 但为了演示向下传播，我们需要显式调用向下修正
    
    print(f"更新后 - S1 Confidence: {sub1.confidence:.4f}") 
    # S1 的置信度应该因为 S1_1 的成功而增加
    
    # 3. 向下修正权重
    # 由于 ROOT 的置信度可能变了，或者 S1 变了，我们重新校准整棵树
    propagate_weights_downward(root)
    
    print("\n>>> Final State:")
    print(f"Root Confidence: {root.confidence:.4f}")
    print(f"Child S1 (Code Gen): Confidence={sub1.confidence:.4f}, Weight={sub1.weight:.4f}")
    print(f"Child S2 (Logic):    Confidence={sub2.confidence:.4f}, Weight={sub2.weight:.4f}")
    # 如果 ROOT 置信度变高，S1 和 S2 的权重分布可能会发生变化