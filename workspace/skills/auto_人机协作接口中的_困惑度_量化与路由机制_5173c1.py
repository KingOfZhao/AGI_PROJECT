"""
人机协作接口中的困惑度量化与路由机制

该模块实现了一个基于系统状态感知的决策引擎，用于在AGI系统中实现动态的人机协作。
核心逻辑是计算当前任务节点的“全局困惑度”，该指标综合了节点的连接强度（拓扑稳定性）
和边缘概率（语义/逻辑不确定性）。基于此指标，系统决定是自主处理任务，还是将任务
路由给人类专家进行物理证伪或干预。

Input Format:
    - nodes: List[Dict], 节点对象列表，包含 'id', 'type', 'connections' 等字段
    - edges: List[Dict], 边对象列表，包含 'source', 'target', 'weight', 'probability' 等字段
    - threshold: float, 路由阈值

Output Format:
    - Dict: 包含 'global_perplexity' (float), 'decision' (str), 'confidence' (float)
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

# 定义常量
DEFAULT_PERPLEXITY_THRESHOLD = 0.75
MIN_PROBABILITY = 1e-9  # 防止log(0)计算错误

@dataclass
class Node:
    """图节点数据结构"""
    id: str
    type: str  # e.g., 'concept', 'action', 'state'
    stability: float = 1.0  # 节点自身的稳定性因子

@dataclass
class Edge:
    """图边数据结构"""
    source: str
    target: str
    weight: float  # 连接强度 (0.0 to 1.0)
    probability: float  # 边缘逻辑概率 (0.0 to 1.0)

class PerplexityRouter:
    """
    计算全局困惑度并决定任务路由的类。
    
    核心算法思想：
    1. 连接强度反映了系统对当前拓扑结构的信心。
    2. 边缘概率反映了系统对下一步推理或行动的确信度。
    3. 困惑度 = 信息熵的指数形式，这里简化为不确定性的加权和。
    """
    
    def __init__(self, threshold: float = DEFAULT_PERPLEXITY_THRESHOLD):
        """
        初始化路由器。
        
        Args:
            threshold (float): 决定路由给人类的困惑度阈值。
        """
        if not 0.0 <= threshold <= 1.0:
            logger.error(f"Invalid threshold value: {threshold}. Must be between 0 and 1.")
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        self.threshold = threshold
        self._graph_cache: Dict[str, List[Edge]] = {}
        logger.info(f"PerplexityRouter initialized with threshold: {threshold}")

    def _validate_inputs(self, nodes: List[Node], edges: List[Edge]) -> bool:
        """验证输入数据的完整性"""
        if not nodes:
            logger.warning("Validation failed: Nodes list is empty.")
            return False
        
        node_ids = {n.id for n in nodes}
        
        for edge in edges:
            if edge.source not in node_ids or edge.target not in node_ids:
                logger.error(f"Validation failed: Edge refers to non-existent node ({edge.source} -> {edge.target})")
                return False
            if not (0.0 <= edge.weight <= 1.0 and 0.0 <= edge.probability <= 1.0):
                logger.error(f"Validation failed: Edge values out of bounds for {edge.source}->{edge.target}")
                return False
                
        return True

    def _build_adjacency(self, edges: List[Edge]) -> Dict[str, List[Edge]]:
        """构建邻接表缓存以加速查找"""
        adj: Dict[str, List[Edge]] = {}
        for edge in edges:
            if edge.source not in adj:
                adj[edge.source] = []
            adj[edge.source].append(edge)
        return adj

    def calculate_local_uncertainty(self, edge: Edge) -> float:
        """
        辅助函数：计算单条边的局部不确定性（熵）。
        
        Args:
            edge (Edge): 连接两个节点的边对象。
            
        Returns:
            float: 局部不确定性分数 (0.0 to 1.0)。
        """
        # 使用二元熵的概念简化：H(p) = -p*log(p) - (1-p)*log(1-p)
        # 这里我们结合连接权重，不确定性 = 权重 * (1 - 确信度)
        # 如果 probability 是 0.5（最不确定），不确定性最高
        
        p = max(edge.probability, MIN_PROBABILITY)
        entropy = -p * math.log(p) - (1 - p) * math.log(1 - p)
        
        # 归一化熵值 (ln(2) = 0.693...)
        normalized_entropy = entropy / math.log(2)
        
        # 结合权重：权重越低，该路径的参考价值越低，不确定性占比调整
        # 这里简化模型：不确定性 = 归一化熵 * (1 - weight_factor)
        # 或者更直观：不确定性由概率分布的不确定性和连接的强弱共同决定
        
        return normalized_entropy * (1.0 - edge.weight * 0.5) # 简化的加权公式

    def compute_global_perplexity(self, nodes: List[Node], edges: List[Edge]) -> float:
        """
        核心函数1：计算系统的全局困惑度。
        
        方法：
        遍历所有连接，计算加权平均不确定性。
        
        Args:
            nodes (List[Node]): 当前上下文的节点列表。
            edges (List[Edge]): 连接节点的边列表。
            
        Returns:
            float: 全局困惑度评分 (0.0 到 1.0)。
        """
        if not self._validate_inputs(nodes, edges):
            raise ValueError("Invalid input data for perplexity calculation.")
            
        if not edges:
            return 0.0 # 无连接意味着无推理路径，通常视为无困惑或需特殊处理
            
        total_weighted_uncertainty = 0.0
        total_weights = 0.0
        
        # 构建邻接关系
        adj = self._build_adjacency(edges)
        
        for node in nodes:
            # 获取该节点的出边
            outgoing_edges = adj.get(node.id, [])
            if not outgoing_edges:
                continue
                
            for edge in outgoing_edges:
                local_u = self.calculate_local_uncertainty(edge)
                # 使用节点的稳定性修正权重
                effective_weight = edge.weight * node.stability
                total_weighted_uncertainty += local_u * effective_weight
                total_weights += effective_weight
        
        if total_weights == 0:
            return 1.0 # 如果没有有效连接，视为最高困惑度
            
        avg_uncertainty = total_weighted_uncertainty / total_weights
        
        # 将不确定性映射回困惑度 (这里简化处理，直接使用平均不确定性作为困惑度指数)
        # 实际 AGI 场景可能使用 Softmax 温度系数调整
        perplexity = min(1.0, max(0.0, avg_uncertainty))
        
        logger.debug(f"Computed Perplexity: {perplexity}")
        return perplexity

    def route_decision(self, perplexity: float, context_metadata: Optional[Dict] = None) -> Dict:
        """
        核心函数2：基于困惑度决定路由方向。
        
        Args:
            perplexity (float): 计算出的全局困惑度。
            context_metadata (Optional[Dict]): 额外的上下文信息，如紧急程度、风险等级。
            
        Returns:
            Dict: 包含决策信息的字典。
                - action: 'AI_PROCESS' 或 'HUMAN_INTERVENTION'
                - reason: 决策原因
                - confidence: 决策信心度
        """
        if perplexity < 0 or perplexity > 1:
            logger.error(f"Perplexity value out of bounds: {perplexity}")
            raise ValueError("Perplexity must be between 0 and 1.")

        # 动态调整阈值（基于元数据，示例）
        dynamic_threshold = self.threshold
        if context_metadata:
            risk_level = context_metadata.get('risk_level', 0)
            # 风险越高，越倾向于让人类介入，降低阈值
            dynamic_threshold = max(0.1, self.threshold - (risk_level * 0.1))
        
        logger.info(f"Evaluating: Perplexity {perplexity:.4f} vs Threshold {dynamic_threshold:.4f}")
        
        if perplexity > dynamic_threshold:
            return {
                "action": "HUMAN_INTERVENTION",
                "reason": "Global perplexity exceeds safety threshold. Physical falsification required.",
                "confidence": (perplexity - dynamic_threshold) / (1.0 - dynamic_threshold),
                "target": "human_operator_queue"
            }
        else:
            return {
                "action": "AI_PROCESS",
                "reason": "Confidence sufficient for autonomous top-down processing.",
                "confidence": (dynamic_threshold - perplexity) / dynamic_threshold,
                "target": "ai_inference_engine"
            }

# 使用示例
if __name__ == "__main__":
    # 模拟数据
    node_1 = Node(id="concept_1", type="abstract", stability=0.9)
    node_2 = Node(id="action_1", type="physical", stability=0.6)
    node_3 = Node(id="state_1", type="temporal", stability=0.8)
    
    # 边缘：source -> target，weight (连接强度)，probability (逻辑发生概率)
    # 假设这是一个关于机器人抓取物体的场景
    edge_1 = Edge(source="concept_1", target="action_1", weight=0.9, probability=0.95) # 非常确信
    edge_2 = Edge(source="action_1", target="state_1", weight=0.4, probability=0.55)   # 非常不确定，且连接弱
    
    nodes_list = [node_1, node_2, node_3]
    edges_list = [edge_1, edge_2]
    
    # 初始化路由器
    router = PerplexityRouter(threshold=0.6)
    
    try:
        # 1. 计算困惑度
        global_p = router.compute_global_perplexity(nodes_list, edges_list)
        print(f"System Global Perplexity: {global_p:.4f}")
        
        # 2. 做出决策
        # 假设这是一个高风险任务
        metadata = {"risk_level": 2} 
        result = router.route_decision(global_p, context_metadata=metadata)
        
        print("-" * 30)
        print("Decision Result:")
        for key, value in result.items():
            print(f"{key}: {value}")
            
    except ValueError as e:
        logger.error(f"Execution failed: {e}")