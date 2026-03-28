"""
高级Python模块：基于认知亲密度的动态向量化投影算法

该模块实现了一种融合语义特征与结构拓扑特征的混合投影算法，
旨在发现跨域节点间非显性的迁移通道。

作者: AGI System Architect
版本: 1.0.0
领域: cognitive_science / network_theory
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveIntimacyProjector")


@dataclass
class Node:
    """
    节点数据结构定义。
    
    属性:
        id (str): 节点的唯一标识符
        domain (str): 节点所属的领域（如 'biology', 'computer_science'）
        embedding (np.ndarray): 节点的语义向量（如BERT嵌入）
        neighbors (List[str]): 相邻节点的ID列表
    """
    id: str
    domain: str
    embedding: np.ndarray
    neighbors: List[str]


class TopologyEmbeddingEngine:
    """
    拓扑嵌入引擎：负责将节点的局部连接模式转换为拓扑特征向量。
    这里实现了基于结构角色的特征提取（Structural Role Embedding）。
    """
    
    def __init__(self, max_walk_length: int = 4, vector_dim: int = 128):
        """
        初始化拓扑引擎。
        
        参数:
            max_walk_length: 随机游走或结构统计的最大深度
            vector_dim: 生成的拓扑向量维度
        """
        self.max_walk_length = max_walk_length
        self.vector_dim = vector_dim
        logger.info("TopologyEmbeddingEngine initialized with dim=%d", vector_dim)

    def _calculate_local_structural_metrics(self, node: Node, graph_map: Dict[str, Node]) -> np.ndarray:
        """
        辅助函数：计算节点的局部结构指标。
        
        参数:
            node: 目标节点
            graph_map: 全局节点ID到节点对象的映射
            
        返回:
            包含局部度数、聚类系数近似值、平均邻居度数等特征的向量
        """
        degree = len(node.neighbors)
        if degree == 0:
            return np.zeros(4)  # 孤立节点特征为0

        # 计算邻居的度数统计
        neighbor_degrees = []
        triangles = 0
        
        for neighbor_id in node.neighbors:
            if neighbor_id in graph_map:
                neighbor_node = graph_map[neighbor_id]
                neighbor_degrees.append(len(neighbor_node.neighbors))
                # 简单的三角形计数（局部聚类）
                triangles += len(set(node.neighbors) & set(neighbor_node.neighbors))
        
        avg_neighbor_degree = np.mean(neighbor_degrees) if neighbor_degrees else 0
        max_neighbor_degree = np.max(neighbor_degrees) if neighbor_degrees else 0
        
        # 局部聚类系数近似 (归一化)
        clustering_proxy = (triangles / (degree * (degree - 1))) if degree > 1 else 0
        
        # 归一化特征向量 (简单的统计特征)
        # 实际生产中可替换为 GraphWave 或 Role2Vec
        features = np.array([
            np.log1p(degree), 
            avg_neighbor_degree / 10.0,  # 假设度数不会过大，简单缩放
            max_neighbor_degree / 20.0,
            np.clip(clustering_proxy, 0, 1)
        ])
        
        return features

    def generate_topology_vector(self, node: Node, graph_map: Dict[str, Node]) -> np.ndarray:
        """
        核心函数1：生成节点的拓扑指纹向量。
        
        参数:
            node: 目标节点
            graph_map: 图数据映射
            
        返回:
            归一化的拓扑特征向量 (维度: self.vector_dim)
        """
        base_metrics = self._calculate_local_structural_metrics(node, graph_map)
        
        # 为了匹配 vector_dim，我们使用简单的线性投影模拟高维嵌入
        # 在真实场景中，这里应使用预训练的GNN或DeepWalk模型
        # 此处使用随机投影模拟固定的哈希映射，确保维度一致性
        np.random.seed(hash(node.id) % (2**32))
        projection_matrix = np.random.randn(len(base_metrics), self.vector_dim)
        
        # 模拟非线性变换
        topo_vector = np.tanh(np.dot(base_metrics, projection_matrix))
        
        # L2归一化
        norm = np.linalg.norm(topo_vector)
        if norm > 1e-6:
            topo_vector = topo_vector / norm
            
        return topo_vector


class CognitiveIntimacyProjector:
    """
    认知亲密度投影器：整合语义向量和拓扑向量，寻找跨域迁移通道。
    """
    
    def __init__(self, topology_weight: float = 0.4, semantic_weight: float = 0.6):
        """
        初始化投影器。
        
        参数:
            topology_weight: 拓扑相似度在最终评分中的权重
            semantic_weight: 语义相似度在最终评分中的权重
        """
        if not np.isclose(topology_weight + semantic_weight, 1.0, atol=1e-3):
            logger.warning("Weights do not sum to 1.0, normalizing...")
            total = topology_weight + semantic_weight
            self.topo_w = topology_weight / total
            self.sema_w = semantic_weight / total
        else:
            self.topo_w = topology_weight
            self.sema_w = semantic_weight
            
        self.topo_engine = TopologyEmbeddingEngine()
        self.node_embeddings: Dict[str, np.ndarray] = {}
        logger.info("CognitiveIntimacyProjector ready. Topo Weight: %.2f", self.topo_w)

    def build_projections(self, nodes: List[Node]) -> Dict[str, np.ndarray]:
        """
        核心函数2：为所有节点构建混合投影向量。
        
        参数:
            nodes: 包含413个节点的列表
            
        返回:
            字典，Key为Node ID，Value为融合后的投影向量
            
        异常:
            ValueError: 如果输入节点列表为空
        """
        if not nodes:
            raise ValueError("Input node list cannot be empty.")
        
        logger.info(f"Starting projection for {len(nodes)} nodes...")
        
        # 构建全局图索引以供拓扑查找
        graph_map = {n.id: n for n in nodes}
        projections = {}
        
        for node in nodes:
            # 1. 获取语义向量 (假设已归一化)
            sem_vec = node.embedding
            if np.linalg.norm(sem_vec) == 0:
                logger.warning(f"Node {node.id} has zero semantic vector.")
                continue
                
            # 2. 获取拓扑向量
            topo_vec = self.topo_engine.generate_topology_vector(node, graph_map)
            
            # 3. 向量融合
            # 方法：加权求和 + 简单的拼接策略 (这里演示加权融合，需保证维度一致或投影后一致)
            # 为了简化，假设语义向量和拓扑向量维度相同，或者我们需要将它们映射到同一空间
            # 此处策略：生成一个融合得分向量，或者直接拼接。
            # 本算法采用：空间对齐后的加权叠加
            
            # 维度对齐 (如果语义是768维，拓扑是128维，通常需要MLP映射)
            # 这里假设 topo_engine 输出的维度与语义维度一致，或者我们将它们处理为同维度
            # 为演示通用性，我们将 topo 扩展或截断以匹配 sem (Simulated alignment)
            
            target_dim = len(sem_vec)
            aligned_topo = np.resize(topo_vec, target_dim) # 简单的维度调整模拟
            
            hybrid_vec = (self.sema_w * sem_vec) + (self.topo_w * aligned_topo)
            
            # 归一化最终向量
            norm = np.linalg.norm(hybrid_vec)
            if norm > 1e-6:
                hybrid_vec = hybrid_vec / norm
                
            projections[node.id] = hybrid_vec
            
        self.node_embeddings = projections
        logger.info("Projection completed.")
        return projections

    def find_transfer_bridges(self, source_id: str, top_k: int = 5) -> List[Tuple[str, float, str]]:
        """
        核心函数3：基于构建的投影，寻找潜在的迁移桥梁。
        验证假设：高拓扑相似性的跨域节点。
        
        参数:
            source_id: 源节点ID
            top_k: 返回最相似的K个节点
            
        返回:
            列表，包含 (目标节点ID, 相似度得分, 原因说明)
        """
        if source_id not in self.node_embeddings:
            raise ValueError(f"Source node {source_id} not found in projections.")
            
        source_vec = self.node_embeddings[source_id]
        source_domain = None
        # 假设我们需要知道源领域，实际应从外部传入或存储
        # 此处简化逻辑，直接计算全局相似度然后过滤
        
        results = []
        
        for target_id, target_vec in self.node_embeddings.items():
            if target_id == source_id:
                continue
                
            # 计算余弦相似度
            similarity = np.dot(source_vec, target_vec)
            
            # 只有当相似度超过阈值时才记录 (例如 > 0.7)
            if similarity > 0.6: # 阈值可调
                # 在实际应用中，这里需要检查 target_domain != source_domain
                # 现在仅模拟排序
                reason = "High cognitive intimacy (Semantic + Structural match)"
                results.append((target_id, similarity, reason))
                
        # 按相似度降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]

# --- 使用示例与数据验证 ---

def _generate_mock_data(num_nodes: int = 413, dim: int = 64) -> List[Node]:
    """辅助函数：生成模拟测试数据"""
    nodes = []
    for i in range(num_nodes):
        # 模拟语义向量
        vec = np.random.randn(dim)
        vec = vec / np.linalg.norm(vec)
        
        # 模拟连接 (随机连接)
        neighbors = [f"node_{np.random.randint(0, num_nodes)}" for _ in range(np.random.randint(1, 10))]
        
        node = Node(
            id=f"node_{i}",
            domain="mock_domain" if i % 2 == 0 else "target_domain",
            embedding=vec,
            neighbors=neighbors
        )
        nodes.append(node)
    return nodes

if __name__ == "__main__":
    # 1. 准备数据
    logger.info("Generating mock data for 413 nodes...")
    all_nodes = _generate_mock_data()
    
    # 2. 初始化算法
    projector = CognitiveIntimacyProjector(topology_weight=0.5, semantic_weight=0.5)
    
    try:
        # 3. 构建投影
        # 这一步会计算每个节点的拓扑向量并与语义向量融合
        projections = projector.build_projections(all_nodes)
        
        # 4. 寻找迁移通道
        # 选取第一个节点作为源
        source_node_id = all_nodes[0].id
        bridges = projector.find_transfer_bridges(source_node_id, top_k=3)
        
        print(f"\n--- Transfer Bridge Analysis for {source_node_id} ---")
        for target_id, score, reason in bridges:
            print(f"Target: {target_id} | Score: {score:.4f} | Reason: {reason}")
            
    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)