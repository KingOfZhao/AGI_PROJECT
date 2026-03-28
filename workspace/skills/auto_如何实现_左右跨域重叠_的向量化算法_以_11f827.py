"""
高级模块：左右跨域重叠向量化算法

该模块实现了一个基于高维语义映射和拓扑结构相似性的算法，旨在发现跨学科领域间的非显而易见关联（弱连接）。
核心思想：不仅仅比较节点的语义相似度，而是构建节点的“拓扑指纹”，比较其在各自网络中的结构角色。

作者: AGI System
版本: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Node:
    """
    节点数据结构。
    
    Attributes:
        id (str): 节点的唯一标识符。
        domain (str): 节点所属领域（如 'Biology', 'CS'）。
        embedding (np.ndarray): 节点的语义向量。
        neighbors (List[str]): 邻接节点ID列表，用于构建拓扑结构。
    """
    id: str
    domain: str
    embedding: np.ndarray
    neighbors: List[str]

class CrossDomainVectorization:
    """
    实现“左右跨域重叠”的向量化算法。
    
    该类负责构建高维映射空间，计算拓扑结构相似性，并识别跨域弱连接。
    """

    def __init__(self, nodes: List[Node], embedding_dim: int = 128):
        """
        初始化算法实例。
        
        Args:
            nodes (List[Node]): 节点对象列表。
            embedding_dim (int): 语义向量的维度。
        
        Raises:
            ValueError: 如果节点列表为空或维度设置无效。
        """
        if not nodes:
            raise ValueError("节点列表不能为空")
        if embedding_dim <= 0:
            raise ValueError("嵌入维度必须为正整数")
            
        self.nodes = nodes
        self.embedding_dim = embedding_dim
        self.node_map: Dict[str, Node] = {n.id: n for n in nodes}
        self.id_to_idx: Dict[str, int] = {n.id: i for i, n in enumerate(nodes)}
        
        logger.info(f"初始化完成: 加载 {len(nodes)} 个节点, 向量维度 {embedding_dim}")

    def _calculate_topological_fingerprint(self, node_id: str) -> np.ndarray:
        """
        [辅助函数] 计算单个节点的拓扑结构指纹。
        
        该算法通过聚合邻居的语义向量来表征节点的局部结构角色。
        这是一种简化的“上下文嵌入”，强调节点在网络中的位置而非内容。
        
        Args:
            node_id (str): 目标节点ID。
            
        Returns:
            np.ndarray: 归一化的拓扑指纹向量。
        """
        if node_id not in self.node_map:
            logger.warning(f"节点 {node_id} 未找到，返回零向量")
            return np.zeros(self.embedding_dim)

        node = self.node_map[node_id]
        neighbor_embeddings = []
        
        for neighbor_id in node.neighbors:
            if neighbor_id in self.node_map:
                neighbor_embeddings.append(self.node_map[neighbor_id].embedding)
        
        if not neighbor_embeddings:
            # 孤立节点使用自身向量的微小扰动或零向量
            return np.zeros(self.embedding_dim)

        # 计算邻居向量的中心点（Centroid）作为结构特征
        # 这里代表了一个节点的“左/右”上下文环境
        avg_embedding = np.mean(neighbor_embeddings, axis=0)
        
        # 数据验证：检查NaN
        if np.isnan(avg_embedding).any():
            logger.error(f"节点 {node_id} 计算出 NaN 指纹")
            return np.zeros(self.embedding_dim)
            
        return self._safe_normalize(avg_embedding)

    def _safe_normalize(self, vector: np.ndarray) -> np.ndarray:
        """
        [辅助函数] 安全的向量归一化。
        
        Args:
            vector (np.ndarray): 输入向量。
            
        Returns:
            np.ndarray: 单位向量。如果模长为0，返回原向量。
        """
        norm = np.linalg.norm(vector)
        if norm < 1e-10:
            return vector
        return vector / norm

    def build_cross_domain_map(self) -> np.ndarray:
        """
        [核心函数 1] 构建跨域高维特征矩阵。
        
        结合原始语义向量和拓扑指纹，生成混合特征向量。
        混合向量 = Weight * Semantic + (1-Weight) * Topology
        
        Returns:
            np.ndarray: 形状为 (N, D) 的混合特征矩阵。
        """
        logger.info("开始构建跨域高维映射空间...")
        features = []
        topo_weight = 0.4  # 赋予拓扑结构40%的权重
        
        for node in self.nodes:
            semantic_vec = self._safe_normalize(node.embedding)
            topo_vec = self._calculate_topological_fingerprint(node.id)
            
            # 融合语义与结构
            # 这种融合允许即使语义不同但结构角色相似的节点产生关联
            hybrid_vec = (topo_weight * topo_vec) + ((1 - topo_weight) * semantic_vec)
            hybrid_vec = self._safe_normalize(hybrid_vec)
            features.append(hybrid_vec)
            
        feature_matrix = np.array(features)
        logger.info(f"特征矩阵构建完成，形状: {feature_matrix.shape}")
        return feature_matrix

    def discover_weak_ties(
        self, 
        top_k: int = 5, 
        exclude_same_domain: bool = True
    ) -> List[Tuple[str, str, float]]:
        """
        [核心函数 2] 发现并排序跨域弱连接。
        
        基于混合特征矩阵计算余弦相似度，寻找不同领域间结构/语义最相似的节点对。
        
        Args:
            top_k (int): 每个节点保留的最相似跨域节点数量。
            exclude_same_domain (bool): 是否排除同领域的连接。
            
        Returns:
            List[Tuple[str, str, float]]: 排序后的连接列表 (Node_A, Node_B, Similarity)。
        """
        if top_k <= 0:
            raise ValueError("top_k 必须大于 0")

        logger.info("开始计算跨域关联...")
        feature_matrix = self.build_cross_domain_map()
        
        # 计算余弦相似度矩阵 (N, N)
        # 注意：在大规模数据下应使用近似最近邻算法(ANN)，此处演示使用矩阵乘法
        similarity_matrix = np.dot(feature_matrix, feature_matrix.T)
        
        results: List[Tuple[str, str, float]] = []
        
        for i, node_a in enumerate(self.nodes):
            # 获取相似度排序（降序）
            # argsort是升序，所以取负或反转
            sorted_indices = np.argsort(-similarity_matrix[i])
            
            count = 0
            for j in sorted_indices:
                # 跳过自身
                if i == j:
                    continue
                    
                node_b = self.nodes[j]
                
                # 边界检查与领域过滤
                if exclude_same_domain and node_a.domain == node_b.domain:
                    continue
                
                score = float(similarity_matrix[i, j])
                
                # 只保留显著的非显而易见连接 (示例阈值：0.7)
                # 实际上，对于“弱连接”，我们寻找的是中等程度的相似性，而非极高
                if score > 0.6: 
                    results.append((node_a.id, node_b.id, score))
                    count += 1
                
                if count >= top_k:
                    break
        
        # 按相似度得分全局排序
        results.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"发现 {len(results)} 条潜在跨域连接。")
        return results

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 模拟数据生成
    # 假设向量维度为 64
    DIM = 64
    mock_nodes = []
    
    # 领域 A: 生物学
    # 节点 'Apoptosis': 语义向量随机，但有特定的邻居结构
    bio_emb = np.random.rand(DIM)
    # 模拟 'Apoptosis' 的邻居 (例如信号传导路径)
    mock_nodes.append(Node(id="Bio_Apoptosis", domain="Biology", embedding=bio_emb, neighbors=["Bio_Signal", "Bio_Cell_Death"]))
    mock_nodes.append(Node(id="Bio_Signal", domain="Biology", embedding=np.random.rand(DIM), neighbors=["Bio_Apoptosis"]))
    mock_nodes.append(Node(id="Bio_Cell_Death", domain="Biology", embedding=np.random.rand(DIM), neighbors=["Bio_Apoptosis"]))

    # 领域 B: 软件工程
    # 节点 'SelfDestruct': 语义向量可能不同，但我们人为构造相似的邻居结构
    # 或者是语义相似，或者是结构相似
    cs_emb = np.random.rand(DIM)
    # 让 'SelfDestruct' 的向量在语义空间稍微接近 'Apoptosis'，但不完全相同
    cs_emb = cs_emb * 0.6 + bio_emb * 0.4 
    
    # 构造相似的结构：'SelfDestruct' 也连接到 'Signal' 和 'Handler'
    mock_nodes.append(Node(id="CS_SelfDestruct", domain="Software", embedding=cs_emb, neighbors=["CS_Signal", "CS_Handler"]))
    mock_nodes.append(Node(id="CS_Signal", domain="Software", embedding=np.random.rand(DIM), neighbors=["CS_SelfDestruct"]))
    mock_nodes.append(Node(id="CS_Handler", domain="Software", embedding=np.random.rand(DIM), neighbors=["CS_SelfDestruct"]))

    # 添加一些噪音节点
    for i in range(10):
        dom = "Noise"
        mock_nodes.append(Node(id=f"Noise_{i}", domain=dom, embedding=np.random.rand(DIM), neighbors=[]))

    try:
        # 2. 初始化算法
        algo = CrossDomainVectorization(nodes=mock_nodes, embedding_dim=DIM)
        
        # 3. 执行发现
        # 寻找生物学和软件工程之间的联系
        weak_ties = algo.discover_weak_ties(top_k=3, exclude_same_domain=True)
        
        print("\n=== 发现的跨域弱连接 ===")
        for node_a, node_b, score in weak_ties:
            print(f"连接: [{node_a}] <---> [{node_b}] | 强度: {score:.4f}")
            
    except ValueError as ve:
        logger.error(f"输入验证错误: {ve}")
    except Exception as e:
        logger.error(f"运行时发生意外错误: {e}", exc_info=True)