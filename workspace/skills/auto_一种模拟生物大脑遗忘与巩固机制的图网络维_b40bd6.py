"""
高级AGI技能模块：生物启发式图网络维护算法

该模块实现了一种模拟生物大脑遗忘与巩固机制的图网络维护算法。
通过引入'热力学隐喻'，计算知识节点的'生命周期成本'，结合时序衰减与实践反馈，
利用图拓扑结构分析系统脆弱性，实现认知网络的自我修复与演进。

Author: AGI System Architect
Version: 1.0.0
Domain: Cross Domain / Cognitive Architecture
"""

import logging
import math
import networkx as nx
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeNode:
    """
    知识节点数据结构，包含状态与元数据。
    
    Attributes:
        id (str): 节点唯一标识符
        content (str): 知识内容描述
        creation_time (datetime): 创建时间
        last_accessed (datetime): 最后访问时间
        feedback_score (float): 实践反馈分数 (0.0 到 1.0)
        access_count (int): 累计访问次数
    """
    id: str
    content: str
    creation_time: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    feedback_score: float = 0.5
    access_count: int = 0

    def update_access(self, delta_feedback: float = 0.0):
        """更新访问时间和反馈分数"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        # 确保分数在合法范围内
        self.feedback_score = max(0.0, min(1.0, self.feedback_score + delta_feedback))


class BioInspiredGraphMaintainer:
    """
    核心类：基于热力学隐喻与生物遗忘机制的图网络维护器。
    
    负责计算节点活力、系统脆弱性，并执行修剪与加固操作，防止认知熵增。
    """

    def __init__(self, decay_rate: float = 0.05, critical_threshold: float = 0.2):
        """
        初始化维护器。
        
        Args:
            decay_rate (float): 时序衰减率，控制遗忘速度。
            critical_threshold (float): 活力阈值，低于此值的节点将被标记为修剪候选。
        """
        self.graph = nx.DiGraph()
        self.decay_rate = decay_rate
        self.critical_threshold = critical_threshold
        self._node_store: Dict[str, KnowledgeNode] = {}
        
        logger.info("BioInspiredGraphMaintainer initialized with decay_rate=%.3f", decay_rate)

    def add_node(self, node: KnowledgeNode, neighbors: Optional[Set[str]] = None):
        """
        添加知识节点到网络中。
        
        Args:
            node (KnowledgeNode): 待添加的节点对象。
            neighbors (Optional[Set[str]]): 建立连接的邻居节点ID集合。
        """
        if not node or not node.id:
            raise ValueError("Invalid node or node ID provided.")
            
        self.graph.add_node(node.id)
        self._node_store[node.id] = node
        
        if neighbors:
            for neighbor_id in neighbors:
                if neighbor_id in self._node_store:
                    self.graph.add_edge(node.id, neighbor_id)
        
        logger.debug("Node %s added to graph.", node.id)

    def _calculate_temporal_vitality(self, node_id: str) -> float:
        """
        [辅助函数] 计算节点的时序活力。
        
        结合时间衰减和访问频率，模拟短期记忆向长期记忆转化的稳定性。
        Vitality = (Feedback * Decay_Factor) + (Access_Freq_Normalized)
        
        Args:
            node_id (str): 节点ID
            
        Returns:
            float: 活力值 (0.0 到 1.0+)
        """
        if node_id not in self._node_store:
            return 0.0
            
        node = self._node_store[node_id]
        now = datetime.now()
        
        # 计算时间差（小时）
        time_delta = (now - node.last_accessed).total_seconds() / 3600.0
        
        # 热力学衰减：模拟熵增，随时间推移无序度增加（活力降低）
        # 使用指数衰减模型
        decay_factor = math.exp(-self.decay_rate * time_delta)
        
        # 基础活力 = 反馈分数 * 衰减因子
        base_vitality = node.feedback_score * decay_factor
        
        # 访问频率加成：防止高价值但近期未访问的节点被误删
        frequency_bonus = math.log1p(node.access_count) * 0.05
        
        return base_vitality + frequency_bonus

    def analyze_structural_vulnerability(self) -> Dict[str, float]:
        """
        [核心函数 1] 分析网络拓扑结构，计算系统脆弱性。
        
        利用介数中心性和PageRank识别关键节点。
        如果一个节点PageRank高但连接脆弱，它需要被'加固'。
        
        Returns:
            Dict[str, float]: 节点ID到重要性权重的映射。
        """
        logger.info("Starting structural vulnerability analysis...")
        
        if self.graph.number_of_nodes() == 0:
            return {}
            
        try:
            # 计算PageRank (衡量节点的影响力)
            pagerank_scores = nx.pagerank(self.graph, alpha=0.85)
            
            # 计算介数中心性 (衡量节点作为'桥梁'的重要性)
            # 如果节点介数高，删除它会破坏网络的连通性
            betweenness_scores = nx.betweenness_centrality(self.graph, normalized=True)
            
            structural_weights = {}
            for node_id in self.graph.nodes():
                pr = pagerank_scores.get(node_id, 0)
                bc = betweenness_scores.get(node_id, 0)
                # 综合权重：高PR和高BC的节点具有极高的系统价值
                structural_weights[node_id] = (pr * 0.6) + (bc * 0.4)
                
            logger.info("Analysis complete for %d nodes.", len(structural_weights))
            return structural_weights
            
        except Exception as e:
            logger.error("Error during graph analysis: %s", e, exc_info=True)
            return {n: 0.5 for n in self.graph.nodes()}

    def execute_maintenance_cycle(self) -> Tuple[List[str], List[str]]:
        """
        [核心函数 2] 执行完整的维护周期：修剪与加固。
        
        流程:
        1. 计算每个节点的'生命周期成本' (LCM)。
           LCM = (时序活力 * 0.4) + (结构重要性 * 0.6)
        2. 修剪低LCM节点 (模拟遗忘/凋亡)。
        3. 加固高LCM节点 (模拟突触增强/巩固)。
        
        Returns:
            Tuple[List[str], List[str]]: (被修剪的节点ID列表, 被加固的节点ID列表)
        """
        logger.info("Starting maintenance cycle...")
        structural_weights = self.analyze_structural_vulnerability()
        
        pruned_nodes = []
        consolidated_nodes = []
        
        nodes_to_evaluate = list(self.graph.nodes())
        
        for node_id in nodes_to_evaluate:
            if node_id not in self._node_store:
                continue
                
            # 1. 计算活力
            vitality = self._calculate_temporal_vitality(node_id)
            
            # 2. 获取结构权重
            struct_importance = structural_weights.get(node_id, 0)
            
            # 3. 综合评分 (生命周期成本)
            # 如果结构重要性高，即使活力低（近期未用），也可能被保留
            lifecycle_score = (vitality * 0.4) + (struct_importance * 0.6)
            
            # 决策逻辑
            if lifecycle_score < self.critical_threshold:
                # 执行修剪 (Forgetting)
                self._prune_node(node_id)
                pruned_nodes.append(node_id)
            elif lifecycle_score > (self.critical_threshold + 0.5):
                # 执行加固
                self._consolidate_node(node_id)
                consolidated_nodes.append(node_id)
                
        logger.info("Cycle complete. Pruned: %d, Consolidated: %d", 
                    len(pruned_nodes), len(consolidated_nodes))
        return pruned_nodes, consolidated_nodes

    def _prune_node(self, node_id: str):
        """物理移除节点"""
        self.graph.remove_node(node_id)
        if node_id in self._node_store:
            del self._node_store[node_id]
        logger.debug("Node %s has been pruned (Forgotten).", node_id)

    def _consolidate_node(self, node_id: str):
        """逻辑加固节点：增加反馈分数，防止未来衰减"""
        if node_id in self._node_store:
            node = self._node_store[node_id]
            # 强化连接，提升抗衰减能力
            node.feedback_score = min(1.0, node.feedback_score + 0.1)
            node.update_access(delta_feedback=0.05)
            logger.debug("Node %s has been consolidated (Memory Reinforced).", node_id)

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化系统
    maintainer = BioInspiredGraphMaintainer(decay_rate=0.1, critical_threshold=0.3)
    
    # 模拟知识输入
    # 节点A: 核心概念，高连接度
    node_a = KnowledgeNode(id="concept_core", content="Foundation of Logic", feedback_score=0.9)
    
    # 节点B: 过时信息，孤立
    node_b = KnowledgeNode(id="old_fact", content="Obsolete Data", feedback_score=0.1)
    
    # 节点C: 中等价值，作为桥梁
    node_c = KnowledgeNode(id="bridge_concept", content="Connector Logic", feedback_score=0.7)
    
    # 添加到网络
    maintainer.add_node(node_a)
    maintainer.add_node(node_b, neighbors={"concept_core"}) # B -> A
    maintainer.add_node(node_c, neighbors={"concept_core"}) # C -> A
    
    # 模拟时间流逝：让节点B变得非常"旧"
    fake_past = datetime.now() - timedelta(days=30)
    maintainer._node_store["old_fact"].last_accessed = fake_past
    
    # 模拟节点C的高频访问
    for _ in range(10):
        maintainer._node_store["bridge_concept"].update_access(0.02)

    print("\n--- Starting Maintenance Cycle ---")
    pruned, consolidated = maintainer.execute_maintenance_cycle()
    
    print(f"\nResult Report:")
    print(f"Nodes Pruned (Forgotten): {pruned}")
    print(f"Nodes Consolidated (Strengthened): {consolidated}")
    print(f"Remaining Nodes in Graph: {list(maintainer.graph.nodes)}")