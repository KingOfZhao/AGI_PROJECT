"""
模块: auto_针对_真实节点_的固化和存储_如何为30_9aa3f4
描述: 针对'真实节点'的固化和存储：如何为3052个节点设计'动态置信度权重'系统？
     实现了模拟人类遗忘曲线的衰减机制和基于'人机共生'实践验证的'TruthRank'算法。

设计理念:
    1. 动态权重: 节点权重不是静态的，而是随时间按Ebbinghaus遗忘曲线衰减。
    2. 实践固化: 只有通过人机交互验证的节点才能获得权重加成，抵抗衰减。
    3. TruthRank: 类似PageRank的算法，但根据验证状态调整链接权重。

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """定义知识图谱中节点的类型。"""
    CONCEPT = "concept"      # 概念节点
    ENTITY = "entity"        # 实体节点
    PRACTICE = "practice"    # 实践验证节点
    INFERENCE = "inference"  # 理论推导节点


@dataclass
class KnowledgeNode:
    """
    知识节点数据结构。
    
    Attributes:
        id: 节点唯一标识符
        content: 节点内容/描述
        node_type: 节点类型
        base_confidence: 基础置信度 (0.0 - 1.0)
        last_verified: 上次验证的时间戳
        verification_count: 累计被验证的次数
        decay_rate: 衰减系数 (越大衰减越快)
    """
    id: str
    content: str
    node_type: NodeType
    base_confidence: float = 0.5
    last_verified: datetime = field(default_factory=datetime.now)
    verification_count: int = 0
    decay_rate: float = 0.1  # 默认衰减率

    def __post_init__(self):
        """数据验证和初始化后处理。"""
        if not 0.0 <= self.base_confidence <= 1.0:
            raise ValueError(f"base_confidence must be between 0 and 1, got {self.base_confidence}")
        if not self.id:
            raise ValueError("Node ID cannot be empty")


class TruthRankSystem:
    """
    核心类：实现动态置信度权重系统和TruthRank算法。
    
    Methods:
        calculate_dynamic_confidence: 计算节点的当前动态权重
        execute_truth_rank: 执行TruthRank算法计算全局权重
        verify_node: 模拟人机共生实践，验证并更新节点状态
    """

    def __init__(self, damping_factor: float = 0.85, max_iterations: int = 100, tolerance: float = 1e-6):
        """
        初始化TruthRank系统。
        
        Args:
            damping_factor: 阻尼系数，类似于PageRank中的d
            max_iterations: 最大迭代次数
            tolerance: 收敛容差
        """
        self.damping_factor = damping_factor
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.graph: Dict[str, KnowledgeNode] = {}
        self.edges: Dict[str, Set[str]] = {}  # 邻接表: source_id -> {target_ids}
        
        logger.info("TruthRankSystem initialized with damping=%.2f", damping_factor)

    def add_node(self, node: KnowledgeNode) -> None:
        """添加节点到图中。"""
        if node.id in self.graph:
            logger.warning("Node %s already exists, updating content.", node.id)
        self.graph[node.id] = node
        if node.id not in self.edges:
            self.edges[node.id] = set()

    def add_edge(self, source_id: str, target_id: str) -> None:
        """添加边（链接）。"""
        if source_id not in self.graph or target_id not in self.graph:
            raise ValueError("Both source and target nodes must exist in the graph")
        self.edges[source_id].add(target_id)

    def calculate_dynamic_confidence(self, node_id: str, current_time: datetime) -> float:
        """
        [核心函数 1] 计算节点的动态置信度权重。
        
        实现基于Ebbinghaus遗忘曲线的衰减模型：
        R = e^(-t/S)，其中t为时间间隔，S为记忆稳定性（此处由验证次数决定）。
        同时结合验证次数提供'固化'效果，防止完全遗忘。
        
        Args:
            node_id: 节点ID
            current_time: 当前时间
            
        Returns:
            float: 0.0 到 1.0 之间的动态置信度分数
        """
        if node_id not in self.graph:
            logger.error("Node %s not found", node_id)
            return 0.0

        node = self.graph[node_id]
        
        # 计算时间差（秒）
        delta_time = (current_time - node.last_verified).total_seconds()
        
        # 避免除零，如果刚刚验证过，delta_time视为极小值
        if delta_time < 0:
            delta_time = 0

        # 记忆稳定性：验证次数越多，稳定性越高，衰减越慢
        # 这是一个简化的心理物理学模型
        stability = 1.0 + math.log1p(node.verification_count)
        
        # 衰减因子：基于时间差和稳定性
        # 衰减公式: exp(-decay_rate * time / stability)
        forgetting_factor = math.exp(-node.decay_rate * delta_time / (stability * 3600)) # 假设输入时间单位需调整，此处按小时级衰减模拟
        
        # 计算最终权重：基础置信度 * 遗忘因子
        # 长期记忆底限：确保被多次验证的节点不会衰减至0
        long_term_floor = min(0.9, 0.1 * node.verification_count)
        
        dynamic_weight = (node.base_confidence * forgetting_factor)
        
        # 应用底限
        final_weight = max(long_term_floor, dynamic_weight)
        
        return min(1.0, final_weight)

    def execute_truth_rank(self) -> Dict[str, float]:
        """
        [核心函数 2] 执行TruthRank算法。
        
        算法逻辑：
        1. 初始化：每个节点权重均等
        2. 迭代：
           TR(V) = (1-d)/N + d * (Sum(TR(I) * W(I->V) / OutDegree(I)))
           其中 W(I->V) 是链接权重：
             - 如果链接源于'实践验证'(PRACTICE类型节点)，W = 1.0
             - 如果链接源于'理论推导'(INFERENCE类型节点)，W = 0.6 (降权)
        3. 收敛检查。
        
        Returns:
            Dict[str, float]: 节点ID到最终TruthRank分数的映射
        """
        if not self.graph:
            return {}

        node_count = len(self.graph)
        ranks: Dict[str, float] = {nid: 1.0 / node_count for nid in self.graph}
        
        logger.info("Starting TruthRank calculation for %d nodes...", node_count)

        for i in range(self.max_iterations):
            new_ranks: Dict[str, float] = {}
            diff = 0.0
            
            for node_id in self.graph:
                rank_sum = 0.0
                
                # 查找所有指向当前节点的源节点
                # 注意：为了性能，实际生产环境应维护逆邻接表
                incoming_nodes = [
                    src_id for src_id, targets in self.edges.items() 
                    if node_id in targets
                ]

                for src_id in incoming_nodes:
                    src_node = self.graph[src_id]
                    out_degree = len(self.edges[src_id])
                    
                    if out_degree == 0:
                        continue
                        
                    # 关键创新点：基于节点类型的链接权重调整
                    if src_node.node_type == NodeType.PRACTICE:
                        link_weight = 1.0  # 实践验证链接，最高权重
                    elif src_node.node_type == NodeType.INFERENCE:
                        link_weight = 0.6  # 理论推导链接，降权
                    else:
                        link_weight = 0.8  # 默认权重
                        
                    # 源节点的动态权重也会影响传递的Rank值
                    src_dynamic_weight = self.calculate_dynamic_confidence(src_id, datetime.now())
                    
                    rank_sum += (ranks[src_id] * link_weight * src_dynamic_weight) / out_degree

                new_rank = ((1 - self.damping_factor) / node_count) + (self.damping_factor * rank_sum)
                new_ranks[node_id] = new_rank
                diff += abs(new_rank - ranks[node_id])

            ranks = new_ranks
            
            # 收敛检查
            if diff < self.tolerance:
                logger.info("TruthRank converged after %d iterations.", i + 1)
                break
        else:
            logger.warning("TruthRank did not converge within max iterations.")

        return ranks

    def verify_node(self, node_id: str, current_time: datetime, boost_score: float = 0.1) -> bool:
        """
        [辅助函数] 模拟'人机共生'验证过程。
        
        当人类用户或系统交互确认某节点有效时调用。
        更新验证时间，重置衰减曲线，增加验证计数。
        
        Args:
            node_id: 待验证的节点ID
            current_time: 验证时间
            boost_score: 基础置信度的增加量
            
        Returns:
            bool: 验证是否成功
        """
        if node_id not in self.graph:
            logger.error("Verification failed: Node %s does not exist.", node_id)
            return False

        node = self.graph[node_id]
        
        # 更新验证状态
        node.last_verified = current_time
        node.verification_count += 1
        
        # 提升基础置信度，上限为1.0
        node.base_confidence = min(1.0, node.base_confidence + boost_score)
        
        logger.info("Node '%s' verified. Count: %d, New Base Confidence: %.4f",
                    node_id, node.verification_count, node.base_confidence)
        return True

# Data format definitions for integration
INPUT_NODE_FORMAT = """
{
    "id": "unique_string",
    "content": "string",
    "type": "concept|entity|practice|inference",
    "base_confidence": 0.0-1.0
}
"""

OUTPUT_RANK_FORMAT = """
{
    "node_id": "unique_string",
    "rank_score": 0.0-1.0,
    "dynamic_confidence": 0.0-1.0,
    "verification_status": "verified|unverified"
}
"""

def main():
    """使用示例：模拟一个拥有3052个节点（此处简化为5个）的知识图谱运行。"""
    
    # 1. 初始化系统
    tr_system = TruthRankSystem(damping_factor=0.85)
    
    # 2. 创建节点 (模拟数据)
    nodes = [
        KnowledgeNode("n1", "Gravity", NodeType.CONCEPT, 0.8),
        KnowledgeNode("n2", "Apple falls", NodeType.PRACTICE, 0.9),  # 实践节点
        KnowledgeNode("n3", "General Relativity", NodeType.INFERENCE, 0.6), # 理论推导
        KnowledgeNode("n4", "Quantum Mechanics", NodeType.INFERENCE, 0.5),
        KnowledgeNode("n5", "Observation X", NodeType.PRACTICE, 0.7)
    ]
    
    for node in nodes:
        tr_system.add_node(node)
        
    # 3. 创建链接 (边)
    # 实践验证指向概念 (权重高)
    tr_system.add_edge("n2", "n1") 
    tr_system.add_edge("n5", "n4")
    # 理论推导指向概念 (权重低)
    tr_system.add_edge("n3", "n1")
    tr_system.add_edge("n4", "n3")

    # 4. 模拟时间流逝和验证
    now = datetime.now()
    
    # 模拟 n2 (Apple falls) 刚刚被验证
    tr_system.verify_node("n2", now)
    
    # 模拟 n3 (Relativity) 很久以前被验证，且未再验证 (模拟遗忘)
    past_time = now - timedelta(days=365)
    tr_system.graph["n3"].last_verified = past_time
    
    # 5. 计算动态置信度
    print(f"Node n1 Dynamic Confidence: {tr_system.calculate_dynamic_confidence('n1', now):.4f}")
    print(f"Node n3 Dynamic Confidence: {tr_system.calculate_dynamic_confidence('n3', now):.4f}")
    
    # 6. 执行 TruthRank
    final_ranks = tr_system.execute_truth_rank()
    
    print("\n--- TruthRank Results ---")
    for nid, score in sorted(final_ranks.items(), key=lambda item: item[1], reverse=True):
        print(f"Node {nid}: Rank Score = {score:.6f}")

if __name__ == "__main__":
    main()