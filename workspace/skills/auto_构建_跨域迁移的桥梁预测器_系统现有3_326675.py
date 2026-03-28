"""
模块名称: bridge_predictor.py
描述: 构建'跨域迁移的桥梁预测器'。
      本模块实现了基于图论与向量空间模型的跨域迁移距离计算。
      通过计算两个领域（如'烹饪'与'软件架构'）在抽象图结构中的
      拓扑距离与语义向量夹角，预测潜在的技能节点迁移可能性。
      系统现有节点数: 3559 (模拟基准)。
"""

import logging
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    Attributes:
        id (int): 节点唯一标识符。
        name (str): 节点名称。
        domain (str): 所属领域。
        connections (List[int]): 连接的其他节点ID列表。
        vector (Optional[List[float]]): 节点的语义向量表示 (模拟嵌入)。
    """
    id: int
    name: str
    domain: str
    connections: List[int]
    vector: Optional[List[float]] = None

class BridgePredictor:
    """
    跨域迁移桥梁预测器。
    
    使用图拓扑结构和语义相似度来预测两个领域之间可能产生
    新节点'碰撞'的桥梁路径。
    """

    def __init__(self, nodes: Dict[int, SkillNode], vector_dim: int = 128):
        """
        初始化预测器。
        
        Args:
            nodes (Dict[int, SkillNode]): 系统现有的节点字典。
            vector_dim (int): 语义向量的维度。
        """
        if not nodes:
            raise ValueError("节点字典不能为空")
        
        self.nodes = nodes
        self.vector_dim = vector_dim
        self._graph_cache = {}
        logger.info(f"BridgePredictor 初始化完成，载入 {len(nodes)} 个节点。")

    def _validate_node_existence(self, node_id: int) -> None:
        """
        辅助函数：验证节点是否存在。
        
        Args:
            node_id (int): 节点ID。
            
        Raises:
            ValueError: 如果节点ID不存在。
        """
        if node_id not in self.nodes:
            error_msg = f"节点 ID {node_id} 不在系统中。"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def calculate_transfer_distance(self, source_id: int, target_id: int) -> float:
        """
        核心函数 1: 计算两个节点之间的'可迁移距离' (Transfer Distance)。
        
        算法逻辑:
        1. 计算拓扑距离: 基于图上的最短路径长度 (这里简化为随机游走模拟或直接连接检查)。
        2. 计算语义距离: 两个节点向量的余弦相似度。
        3. 综合距离 = (1 / (1 + 语义相似度)) * 拓扑距离因子。
        
        Args:
            source_id (int): 源节点ID (例如 '烹饪' 领域节点)。
            target_id (int): 目标节点ID (例如 '软件架构' 领域节点)。
            
        Returns:
            float: 可迁移距离 (0.0 - 1.0)，值越大表示迁移潜力越高。
        """
        self._validate_node_existence(source_id)
        self._validate_node_existence(target_id)
        
        source_node = self.nodes[source_id]
        target_node = self.nodes[target_id]

        # 1. 计算语义相似度
        if source_node.vector is None or target_node.vector is None:
            # 模拟向量生成 (实际应用中应加载预训练向量)
            source_node.vector = [random.gauss(0, 1) for _ in range(self.vector_dim)]
            target_node.vector = [random.gauss(0, 1) for _ in range(self.vector_dim)]
            
        cosine_sim = self._calculate_cosine_similarity(source_node.vector, target_node.vector)
        
        # 2. 计算拓扑距离 (简化版：基于是否直接连接或共享邻居)
        # 如果在真实的3559节点图中，这里应使用 BFS/Dijkstra
        shared_connections = set(source_node.connections) & set(target_node.connections)
        topo_factor = 1.0 / (1.0 + len(shared_connections)) # 共享邻居越少，拓扑距离感越强，但在跨域中这是常态
        
        # 3. 跨域惩罚/奖励因子
        domain_penalty = 0.0
        if source_node.domain != target_node.domain:
            domain_penalty = 0.5 # 鼓励跨域

        # 最终距离公式 (示例公式)
        # 如果语义相似度低且属于不同领域，通过特定公式计算意外性
        distance = (1.0 - cosine_sim) * (topo_factor + domain_penalty)
        
        # 边界检查
        final_score = max(0.0, min(1.0, distance))
        
        logger.debug(f"计算距离: {source_node.name} -> {target_node.name}, 得分: {final_score:.4f}")
        return final_score

    def predict_collision_nodes(self, domain_a: str, domain_b: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """
        核心函数 2: 预测两个领域之间最可能发生'碰撞'产生新真实节点的连接。
        
        它寻找在 Domain A 和 Domain B 之间具有最高'可迁移距离'的节点对。
        
        Args:
            domain_a (str): 第一个领域名称。
            domain_b (str): 第二个领域名称。
            top_k (int): 返回的最优预测数量。
            
        Returns:
            List[Tuple[int, float]]: 预测的桥梁节点ID列表及其得分，按得分降序排列。
        """
        logger.info(f"开始预测领域碰撞: '{domain_a}' <-> '{domain_b}'")
        
        nodes_a = [n for n in self.nodes.values() if n.domain == domain_a]
        nodes_b = [n for n in self.nodes.values() if n.domain == domain_b]

        if not nodes_a or not nodes_b:
            logger.warning("一个或两个领域在当前数据集中不存在。")
            return []

        candidates = []
        
        # 为了性能，通常不全量计算，这里演示采样或全量计算（取决于节点规模）
        # 3559个节点规模较小，可以接受 O(N*M) 的部分计算
        sample_b = nodes_b[:min(len(nodes_b), 100)] # 限制计算量防止超时
        
        for node_a in nodes_a:
            for node_b in sample_b:
                # 跳过同名节点或已连接节点（可选逻辑）
                if node_a.id == node_b.id:
                    continue
                
                dist = self.calculate_transfer_distance(node_a.id, node_b.id)
                
                # 只有当距离超过随机阈值时才视为潜在桥梁
                if dist > 0.5: 
                    candidates.append((node_a.id, node_b.id, dist))
        
        # 排序并取 Top K
        candidates.sort(key=lambda x: x[2], reverse=True)
        results = [(item[0], item[2]) for item in candidates[:top_k]]
        
        logger.info(f"发现 {len(results)} 个潜在跨域桥梁。")
        return results

    def _calculate_cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        辅助函数: 计算两个向量的余弦相似度。
        
        Args:
            vec_a (List[float]): 向量 A。
            vec_b (List[float]): 向量 B。
            
        Returns:
            float: 余弦相似度 (-1.0 到 1.0)。
        """
        if len(vec_a) != len(vec_b):
            logger.error("向量维度不匹配")
            raise ValueError("向量维度不匹配")

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * b for a, b in zip(vec_a, vec_a)))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return dot_product / (norm_a * norm_b)

# --- 使用示例与数据生成 ---

def _mock_system_initialization(num_nodes: int = 3559) -> Dict[int, SkillNode]:
    """
    辅助函数：生成模拟的AGI系统节点数据。
    """
    domains = ["Cooking", "Software_Architecture", "Music", "Biology", "Finance"]
    nodes = {}
    
    for i in range(num_nodes):
        domain = random.choice(domains)
        # 随机生成连接 (模拟图结构)
        conns = [random.randint(0, num_nodes-1) for _ in range(random.randint(1, 10))]
        nodes[i] = SkillNode(
            id=i,
            name=f"Skill_{domain[:3]}_{i}",
            domain=domain,
            connections=conns
        )
    return nodes

if __name__ == "__main__":
    # 1. 生成模拟数据
    logger.info("生成模拟节点数据...")
    system_nodes = _mock_system_initialization(3559)
    
    # 2. 初始化预测器
    predictor = BridgePredictor(system_nodes)
    
    # 3. 计算特定两个节点的距离
    # 假设我们想看 'Cooking' 领域的第 5 个节点 和 'Software_Architecture' 的第 100 个节点
    try:
        node_1 = 5
        node_2 = 100
        # 强制设置领域以便演示
        system_nodes[node_1].domain = "Cooking"
        system_nodes[node_2].domain = "Software_Architecture"
        
        distance = predictor.calculate_transfer_distance(node_1, node_2)
        print(f"\n节点 {node_1} ({system_nodes[node_1].domain}) 与 节点 {node_2} ({system_nodes[node_2].domain}) 的迁移距离: {distance:.4f}")
        
        # 4. 预测跨域碰撞
        print("\n正在预测 'Cooking' 与 'Software_Architecture' 之间的潜在桥梁...")
        predictions = predictor.predict_collision_nodes("Cooking", "Software_Architecture", top_k=3)
        
        print("Top 3 潜在桥梁节点 (Node ID, Score):")
        for node_id, score in predictions:
            print(f"Node ID: {node_id} (Domain: {system_nodes[node_id].domain}), Score: {score:.4f}")
            
    except ValueError as e:
        logger.error(f"运行时错误: {e}")