"""
Module: auto_一套用于维护agi认知网络健康度与时效性_b1db3e

Description:
    一套用于维护AGI认知网络健康度与时效性的动态机制。
    该模块模拟了AGI系统的认知维护过程，包含知识衰变监测、认知自洽性压力测试、
    反常检测以及基于意图-执行落差的空洞探测。旨在实现知识图谱的持续迭代与自我净化。

Core Concepts:
    1. Knowledge Decay (知识衰变): 监测知识的时效性，标记失效节点。
    2. Cognitive Consistency (认知自洽性): 主动发现逻辑冲突。
    3. Anomaly Detection (反常检测): 当常规模式失效时触发范式重构。
    4. Intent-Execution Gap (意图-执行落差): 探测系统认知边界。

Author: AGI System Core Team
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveMaintenance")


class NodeType(Enum):
    """定义认知网络中的节点类型"""
    CONCEPT = "concept"
    FACT = "fact"
    SKILL = "skill"
    PARADIGM = "paradigm"


class HealthStatus(Enum):
    """节点健康状态枚举"""
    HEALTHY = "healthy"
    DECAYING = "decaying"
    CONFLICT = "conflict"
    OBSOLETE = "obsolete"
    ANOMALOUS = "anomalous"


@dataclass
class CognitiveNode:
    """
    认知网络节点数据结构。
    
    Attributes:
        node_id: 节点唯一标识符
        content: 节点存储的知识内容
        type: 节点类型
        created_at: 创建时间
        last_accessed: 最后访问时间
        access_count: 访问次数
        residual_score: 残差分数，用于衡量当前知识与现实的偏差 (0.0-1.0)
        connections: 连接的其他节点ID列表
    """
    node_id: str
    content: str
    type: NodeType
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    residual_score: float = 0.0
    connections: List[str] = field(default_factory=list)

    def update_access(self):
        """更新访问时间和计数"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class CognitiveNetwork:
    """
    模拟AGI的认知网络存储。
    在实际AGI系统中，这可能对应一个图数据库。
    """
    def __init__(self):
        self.nodes: Dict[str, CognitiveNode] = {}

    def add_node(self, node: CognitiveNode):
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[CognitiveNode]:
        return self.nodes.get(node_id)


def calculate_time_decay(created_at: datetime, current_time: datetime) -> float:
    """
    [Helper] 计算基于时间的知识衰变因子。
    
    Args:
        created_at: 知识创建时间
        current_time: 当前时间
        
    Returns:
        float: 衰变因子 (0.0 - 1.0)，值越大表示衰变越严重。
        
    Raises:
        ValueError: 如果时间顺序无效。
    """
    if current_time < created_at:
        logger.error("Current time cannot be earlier than creation time.")
        raise ValueError("Invalid chronological order for decay calculation.")
    
    delta_seconds = (current_time - created_at).total_seconds()
    # 使用指数衰减模型，半衰期设为30天 (2592000秒)
    half_life_seconds = 2592000.0
    decay_factor = 1 - math.exp(-delta_seconds / half_life_seconds)
    
    # 边界检查
    return max(0.0, min(1.0, decay_factor))


def monitor_knowledge_decay(
    network: CognitiveNetwork, 
    residual_threshold: float = 0.75
) -> List[Tuple[str, float, str]]:
    """
    [Core 1] 知识衰变监测器。
    
    通过残差分析和时间衰减模型标记失效节点。
    残差分数越高，表示该知识与当前现实的偏差越大。
    
    Args:
        network: 认知网络实例
        residual_threshold: 触发警告的残差阈值
        
    Returns:
        List[Tuple[str, float, str]]: 失效节点报告列表 (节点ID, 综合衰变分, 诊断信息)
    """
    if not isinstance(network, CognitiveNetwork):
        raise TypeError("Input must be a CognitiveNetwork instance.")
    
    obsolete_reports = []
    current_time = datetime.now()
    
    logger.info(f"Starting decay monitoring for {len(network.nodes)} nodes...")
    
    for node_id, node in network.nodes.items():
        try:
            # 1. 计算时间衰减
            time_decay = calculate_time_decay(node.created_at, current_time)
            
            # 2. 计算基于访问频率的活跃度惩罚 (越不活跃，惩罚越高)
            # 假设如果超过10天未访问，活跃度开始显著下降
            days_inactive = (current_time - node.last_accessed).days
            inactivity_penalty = min(1.0, days_inactive / 30.0) 
            
            # 3. 综合衰变分数计算
            # 残差由外部反馈更新，这里结合内部状态
            total_decay = (node.residual_score * 0.5) + (time_decay * 0.3) + (inactivity_penalty * 0.2)
            
            if total_decay > residual_threshold:
                diagnosis = (
                    f"High decay detected. "
                    f"Residual: {node.residual_score:.2f}, "
                    f"TimeDecay: {time_decay:.2f}, "
                    f"Inactivity: {inactivity_penalty:.2f}"
                )
                obsolete_reports.append((node_id, total_decay, diagnosis))
                logger.warning(f"Node {node_id} marked as obsolete: {diagnosis}")
                
        except Exception as e:
            logger.error(f"Error processing node {node_id}: {e}")
            continue
            
    return obsolete_reports


def check_cognitive_consistency(
    network: CognitiveNetwork, 
    node_id_a: str, 
    node_id_b: str
) -> Tuple[bool, float]:
    """
    [Core 2] 认知自洽性压力测试。
    
    比较两个相关联的节点，检测逻辑冲突。
    这是一个模拟函数，实际系统中会使用逻辑推理引擎或嵌入向量比对。
    
    Args:
        network: 认知网络实例
        node_id_a: 节点A ID
        node_id_b: 节点B ID
        
    Returns:
        Tuple[bool, float]: (是否存在冲突, 冲突强度 0.0-1.0)
        
    Raises:
        ValueError: 如果节点不存在。
    """
    node_a = network.get_node(node_id_a)
    node_b = network.get_node(node_id_b)
    
    if not node_a or not node_b:
        logger.error(f"Missing nodes for consistency check: {node_id_a}, {node_id_b}")
        raise ValueError("One or both nodes do not exist in the network.")
    
    # 模拟：检查类型互斥或简单的语义冲突
    # 例如：如果一个节点是 'Sky' (Blue) 另一个是 'Sky' (Green) 
    # 这里用残差之和模拟冲突概率
    conflict_potential = (node_a.residual_score + node_b.residual_score) / 2.0
    
    # 如果两者连接紧密但残差都很高，说明认知存在撕裂
    has_conflict = False
    conflict_intensity = 0.0
    
    if node_id_b in node_a.connections:
        # 如果节点A连接到B，但两者的残差差异巨大，可能意味着范式转移未完成
        delta = abs(node_a.residual_score - node_b.residual_score)
        if delta > 0.5:
            has_conflict = True
            conflict_intensity = delta
            logger.info(f"Consistency Conflict detected between {node_id_a} and {node_id_b}")
    
    return has_conflict, conflict_intensity


def detect_intent_execution_gap(
    network: CognitiveNetwork,
    intent_vector: List[float],
    execution_loss: float
) -> Optional[str]:
    """
    [Core 3] 意图-执行落差探测 (空洞雷达)。
    
    当系统试图执行某个任务但失败（高Loss）时，此函数被调用。
    它在认知网络中寻找应该负责该任务但目前能力不足的区域（空洞）。
    
    Args:
        network: 认知网络实例
        intent_vector: 意图的向量表示 (简化为List[float])
        execution_loss: 执行失败的损失值 (0.0-1.0)
        
    Returns:
        Optional[str]: 返回需要重构的范式节点ID，如果系统健康则返回None。
    """
    if execution_loss < 0.1:
        return None
        
    logger.warning(f"High execution loss detected: {execution_loss}. Scanning for cognitive voids...")
    
    # 寻找最相关的范式节点
    # 模拟：寻找与intent_vector维度最匹配的PARADIGM类型节点
    # 这里简化逻辑：寻找残差最高的范式节点，认为它是导致失败的短板
    candidate_node = None
    max_residual = -1.0
    
    for node_id, node in network.nodes.items():
        if node.type == NodeType.PARADIGM:
            # 简单模拟：假设我们通过某种匹配逻辑找到了相关范式
            # 这里选取残差最高的作为替罪羊进行重构
            if node.residual_score > max_residual:
                max_residual = node.residual_score
                candidate_node = node_id
                
    if candidate_node and max_residual > 0.6:
        logger.info(f"Paradigm shift triggered for node: {candidate_node}")
        return candidate_node
        
    return None

# --- Usage Example ---
if __name__ == "__main__":
    # 1. 初始化认知网络
    cn = CognitiveNetwork()
    
    # 添加一些测试节点
    # 健康节点
    node1 = CognitiveNode("p_001", "Gravity pulls objects down", NodeType.FACT)
    
    # 失效节点 (创建于很久以前，且残差高)
    old_time = datetime.now() - timedelta(days=100)
    node2 = CognitiveNode(
        "p_002", "Newtonian mechanics explains all physics", 
        NodeType.PARADIGM, 
        created_at=old_time,
        residual_score=0.9 # 高残差，无法解释量子现象
    )
    
    # 冲突节点
    node3 = CognitiveNode(
        "p_003", "Light is purely a wave", 
        NodeType.CONCEPT, 
        residual_score=0.2,
        connections=["p_002"]
    )
    
    cn.add_node(node1)
    cn.add_node(node2)
    cn.add_node(node3)
    
    print("--- 1. Monitoring Knowledge Decay ---")
    decay_report = monitor_knowledge_decay(cn, residual_threshold=0.7)
    for report in decay_report:
        print(f"Report: {report}")

    print("\n--- 2. Checking Cognitive Consistency ---")
    try:
        is_conflict, intensity = check_cognitive_consistency(cn, "p_002", "p_003")
        print(f"Conflict Status: {is_conflict}, Intensity: {intensity:.2f}")
    except ValueError as e:
        print(e)

    print("\n--- 3. Detecting Intent-Execution Gap ---")
    # 模拟一次高Loss的任务执行
    intent = [0.1, 0.5, 0.9] # 模拟意图向量
    target_paradigm = detect_intent_execution_gap(cn, intent, execution_loss=0.85)
    if target_paradigm:
        print(f"Action Required: Trigger restructuring for paradigm {target_paradigm}")