"""
Module: semantic_gravity_engine
Description: 基于现有拓扑结构的动态'语义引力'算法实现。
             实现认知自洽性驱动的节点重组，而非单纯的向量相似度匹配。

Author: Senior Python Engineer (AGI System)
Version: 1.0.0
"""

import logging
import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SemanticGravityEngine:
    """
    实现'语义引力'算法，通过认知自洽性（图论属性）与语义特征结合，
    动态重组知识图谱节点。
    """

    def __init__(self, graph: nx.Graph, node_embeddings: Dict[str, np.ndarray], gravity_constant: float = 1.0):
        """
        初始化引力引擎。

        Args:
            graph (nx.Graph): 现有的网络拓扑结构（1168个节点）。
            node_embeddings (Dict[str, np.ndarray]): 节点的向量表示，用于计算语义距离。
            gravity_constant (float): 引力常数，调节吸引力强度。
        """
        self.graph = graph
        self.embeddings = node_embeddings
        self.G = gravity_constant
        self._validate_inputs()

    def _validate_inputs(self):
        """验证输入数据的完整性和一致性。"""
        if not isinstance(self.graph, nx.Graph):
            raise TypeError("Input graph must be a networkx.Graph instance.")
        
        if len(self.graph) == 0:
            raise ValueError("Graph cannot be empty.")
            
        missing_embeddings = set(self.graph.nodes) - set(self.embeddings.keys())
        if missing_embeddings:
            raise ValueError(f"Missing embeddings for nodes: {list(missing_embeddings)[:5]}...")
        
        logger.info(f"Initialized engine with {len(self.graph)} nodes.")

    def _calculate_cognitive_self_consistency(self, node_u: str, node_v: str) -> float:
        """
        辅助函数：计算两个节点交互后的'认知自洽性'增益。
        
        定义：自洽性 = (局部聚类系数变化) / (平均路径长度变化 + epsilon)
        这模拟了物理系统中熵减的过程。
        
        Args:
            node_u (str): 源节点ID。
            node_v (str): 目标节点ID。
            
        Returns:
            float: 自洽性得分 (0.0 to 1.0)。
        """
        try:
            # 1. 计算聚类系数差异（假设连接后的潜在聚类系数）
            # 这里简化为：如果连接它们，共同邻居的比例
            neighbors_u = set(self.graph.neighbors(node_u))
            neighbors_v = set(self.graph.neighbors(node_v))
            intersection = neighbors_u.intersection(neighbors_v)
            union = neighbors_u.union(neighbors_v)
            
            # 如果没有并集（两个孤立节点），则无法计算聚类，返回默认低值
            if not union:
                return 0.1
            
            # Jaccard系数作为局部聚类增益的代理
            clustering_score = len(intersection) / len(union)
            
            # 2. 计算路径长度差异
            # 原始距离（如果不可达则设为极大值）
            try:
                dist = nx.shortest_path_length(self.graph, source=node_u, target=node_v)
            except nx.NetworkXNoPath:
                dist = 10.0 # 惩罚不连通
            
            # 距离越远，连接带来的"结构坍缩"（即建立捷径）带来的自洽性收益越高
            # 但需要结合聚类系数，避免连接两个完全不相关的孤立群落
            path_score = 1.0 / (1.0 + dist)
            
            # 综合自洽性
            consistency = (clustering_score * 0.6) + (path_score * 0.4)
            return consistency
            
        except Exception as e:
            logger.error(f"Error calculating consistency for {node_u}-{node_v}: {e}")
            return 0.0

    def calculate_semantic_gravity(self, new_node_id: str, new_node_emb: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        核心函数：计算新节点对现有拓扑的动态引力。
        
        公式: F = G * (Consistency(u, v) * Similarity(u, v)) / (Distance_Embedding(u, v)^2)
        注意：这里的 Distance_Embedding 使用向量距离的平滑版本。
        
        Args:
            new_node_id (str): 新增节点的ID。
            new_node_emb (np.ndarray): 新增节点的向量。
            top_k (int): 返回吸引力最强的前K个节点。
            
        Returns:
            List[Tuple[str, float]]: 排序后的(节点ID, 引力得分)列表。
        """
        if new_node_id in self.graph:
            logger.warning(f"Node {new_node_id} already exists. Calculating attractive forces anyway.")
        
        # 预计算新节点的向量范数
        norm_new = new_node_emb.reshape(1, -1)
        
        scores = {}
        
        # 为了性能，在大图中可能需要采样或使用近似最近邻
        # 这里演示全量计算逻辑
        logger.info(f"Calculating semantic gravity for new node: {new_node_id}")
        
        # 批量计算向量相似度以提高性能
        existing_nodes = list(self.embeddings.keys())
        existing_embs = np.array([self.embeddings[n] for n in existing_nodes])
        
        # 计算余弦相似度 (0到1)
        sims = cosine_similarity(norm_new, existing_embs).flatten()
        
        for idx, node_v in enumerate(existing_nodes):
            sim = sims[idx]
            
            # 如果语义相似度太低，直接跳过以节省计算资源
            if sim < 0.2:
                continue
                
            # 计算认知自洽性 (图结构属性)
            # 创建临时视图或使用启发式方法计算，此处调用完整计算
            consistency = self._calculate_cognitive_self_consistency(new_node_id, node_v)
            
            # 引力计算
            # 使用 1 - sim 作为距离代理，加上 epsilon 防止除零
            vector_distance = 1.0 - sim + 1e-5
            
            # 核心算法：引力 = 常数 * (自洽性 * 语义质量) / 距离平方
            # 这里将相似度视为"质量"
            force = self.G * (consistency * sim) / (vector_distance ** 2)
            
            scores[node_v] = force
            
        # 排序并返回Top K
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        logger.info(f"Top attractive node for {new_node_id}: {sorted_scores[0][0]} with force {sorted_scores[0][1]:.4f}")
        
        return sorted_scores

    def restructure_topology(self, new_node_id: str, attractors: List[Tuple[str, float]], threshold: float = 0.5) -> bool:
        """
        核心函数：基于引力计算结果重组拓扑结构。
        
        如果引力超过阈值，建立新边，并可能触发局部拓扑的"坍缩"（合并或聚类）。
        
        Args:
            new_node_id (str): 新节点ID。
            attractors (List[Tuple[str, float]]): 吸引节点列表。
            threshold (float): 建立连接的引力阈值。
            
        Returns:
            bool: 是否发生了结构重组。
        """
        restructured = False
        
        # 将新节点加入图中（如果尚未加入）
        if new_node_id not in self.graph:
            self.graph.add_node(new_node_id)
            logger.info(f"Added new node {new_node_id} to topology.")

        for target_node, force in attractors:
            if force > threshold:
                # 建立物理连接
                self.graph.add_edge(new_node_id, target_node, weight=force)
                logger.info(f"Created edge: {new_node_id} -> {target_node} (Force: {force:.4f})")
                
                # 检查是否需要进行更激进的重组（例如：三角闭合）
                # 如果A吸引B，且B强连接C，检查A是否应该连接C
                neighbors = list(self.graph.neighbors(target_node))
                for neighbor in neighbors:
                    if neighbor != new_node_id:
                        # 简单的三角闭合增强逻辑
                        if not self.graph.has_edge(new_node_id, neighbor):
                             # 如果自洽性极高，自动闭合三角
                             # 这里简化处理，实际应递归调用 consistency check
                             pass 
                restructured = True
                
        return restructured

# Usage Example
if __name__ == "__main__":
    # 1. 构造模拟数据 (1168 nodes)
    NUM_NODES = 1168
    DIM = 128
    
    # 生成随机图
    G = nx.barabasi_albert_graph(NUM_NODES, 3, seed=42)
    
    # 生成随机Embeddings
    embs = {str(i): np.random.rand(DIM) for i in range(NUM_NODES)}
    
    # 初始化引擎
    try:
        engine = SemanticGravityEngine(graph=G, node_embeddings=embs, gravity_constant=0.8)
        
        # 模拟新节点: "street_vendor" (小摊贩)
        # 假设这个向量在某些维度上与 "supply_chain" (供应链) 有潜在的隐式关联
        new_node_emb = np.random.rand(DIM) 
        # 手动调整使其与节点 '10' (假设为代表生存策略的节点) 相似
        target_influence = embs['10']
        new_node_emb = new_node_emb * 0.5 + target_influence * 0.5
        
        # 计算引力
        top_attractors = engine.calculate_semantic_gravity("new_vendor_node", new_node_emb, top_k=3)
        
        # 重组拓扑
        if top_attractors:
            engine.restructure_topology("new_vendor_node", top_attractors, threshold=0.1)
            
    except Exception as e:
        logger.error(f"Simulation failed: {e}")