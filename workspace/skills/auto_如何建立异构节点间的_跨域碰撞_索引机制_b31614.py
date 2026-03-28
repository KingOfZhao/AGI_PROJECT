"""
模块: cross_domain_collision_index
描述: 建立异构节点间的'跨域碰撞'索引机制，基于结构同构性和功能相似性实现深层联系发现。

本模块实现了一个多维索引系统，用于发现看似无关节点间的潜在联系（如'生物学'与'建筑设计'）。
核心机制包括:
1. 结构同构性分析（基于图/树结构的相似度）
2. 功能相似性计算（基于向量嵌入和语义空间）
3. 跨域碰撞索引（快速检索潜在碰撞对象）

依赖:
    - numpy
    - scipy
    - networkx
    - scikit-learn

输入格式:
    - 节点数据: Dict[str, Any]，必须包含'attributes'和'structure'字段
    - 查询参数: Dict[str, Any]，包含'target_node'和'collision_threshold'

输出格式:
    - 碰撞结果: List[Dict[str, Any]]，包含'node_id', 'collision_score'和'match_details'
"""

import logging
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from scipy.spatial.distance import cosine
from sklearn.preprocessing import normalize
import networkx as nx
from networkx.algorithms.isomorphism import is_isomorphic

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NodeData:
    """节点数据结构封装"""
    node_id: str
    attributes: Dict[str, Any]
    structure: Dict[str, Any]  # 包含图结构或树结构数据
    embedding: Optional[np.ndarray] = None


class CrossDomainCollisionIndex:
    """
    跨域碰撞索引系统
    
    功能:
    - 构建多维索引结构
    - 基于结构同构性和功能相似性计算碰撞分数
    - 提供快速检索接口
    
    使用示例:
    >>> index = CrossDomainCollisionIndex()
    >>> node1 = NodeData(
    ...     node_id="bio_cell",
    ...     attributes={"domain": "biology", "function": "energy_production"},
    ...     structure={"graph": nx.DiGraph()},
    ...     embedding=np.random.rand(128)
    ... )
    >>> index.add_node(node1)
    >>> results = index.find_collisions("bio_cell", collision_threshold=0.7)
    """
    
    def __init__(self, embedding_dim: int = 128):
        """
        初始化索引系统
        
        Args:
            embedding_dim: 嵌入向量维度
        """
        self.embedding_dim = embedding_dim
        self.nodes: Dict[str, NodeData] = {}
        self.structure_index: Dict[str, nx.DiGraph] = {}
        self.embedding_index: Dict[str, np.ndarray] = {}
        self.domain_index: Dict[str, List[str]] = {}
        
        logger.info("Initialized CrossDomainCollisionIndex with embedding_dim=%d", embedding_dim)
    
    def _validate_node_data(self, node_data: NodeData) -> bool:
        """
        验证节点数据格式
        
        Args:
            node_data: 待验证的节点数据
            
        Returns:
            bool: 数据是否有效
            
        Raises:
            ValueError: 当数据无效时
        """
        if not isinstance(node_data.node_id, str) or not node_data.node_id.strip():
            raise ValueError("node_id must be a non-empty string")
            
        if not isinstance(node_data.attributes, dict):
            raise ValueError("attributes must be a dictionary")
            
        if "domain" not in node_data.attributes:
            raise ValueError("attributes must contain 'domain' field")
            
        if not isinstance(node_data.structure, dict):
            raise ValueError("structure must be a dictionary")
            
        if "graph" not in node_data.structure:
            raise ValueError("structure must contain 'graph' field")
            
        if node_data.embedding is not None and node_data.embedding.shape != (self.embedding_dim,):
            raise ValueError(f"embedding must have shape ({self.embedding_dim},)")
            
        return True
    
    def _extract_structure_features(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """
        从图结构中提取特征（辅助函数）
        
        Args:
            graph: 网络图结构
            
        Returns:
            Dict[str, Any]: 结构特征字典
        """
        features = {
            "node_count": graph.number_of_nodes(),
            "edge_count": graph.number_of_edges(),
            "density": nx.density(graph),
            "avg_degree": sum(dict(graph.degree()).values()) / graph.number_of_nodes() if graph.number_of_nodes() > 0 else 0,
            "is_directed": nx.is_directed(graph),
            "is_weakly_connected": nx.is_weakly_connected(graph) if nx.is_directed(graph) else nx.is_connected(graph)
        }
        
        logger.debug("Extracted structure features: %s", features)
        return features
    
    def _calculate_structural_similarity(self, graph1: nx.DiGraph, graph2: nx.DiGraph) -> float:
        """
        计算两个图结构之间的相似度
        
        Args:
            graph1: 第一个图结构
            graph2: 第二个图结构
            
        Returns:
            float: 结构相似度分数 [0, 1]
        """
        # 快速检查基本属性相似度
        if abs(graph1.number_of_nodes() - graph2.number_of_nodes()) > 5:
            return 0.0
            
        if abs(graph1.number_of_edges() - graph2.number_of_edges()) > 10:
            return 0.0
            
        # 使用图同构算法计算精确相似度
        if is_isomorphic(graph1, graph2):
            return 1.0
            
        # 计算近似相似度
        features1 = self._extract_structure_features(graph1)
        features2 = self._extract_structure_features(graph2)
        
        # 计算特征差异
        diff = 0.0
        for key in ["node_count", "edge_count", "density", "avg_degree"]:
            max_val = max(features1[key], features2[key])
            if max_val > 0:
                diff += abs(features1[key] - features2[key]) / max_val
                
        similarity = max(0, 1 - diff / 4)  # 归一化到[0,1]
        logger.debug("Calculated structural similarity: %.3f", similarity)
        return similarity
    
    def _calculate_functional_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        计算两个功能嵌入之间的相似度
        
        Args:
            embedding1: 第一个嵌入向量
            embedding2: 第二个嵌入向量
            
        Returns:
            float: 功能相似度分数 [0, 1]
        """
        if embedding1 is None or embedding2 is None:
            return 0.0
            
        # 计算余弦相似度
        similarity = 1 - cosine(embedding1, embedding2)
        logger.debug("Calculated functional similarity: %.3f", similarity)
        return similarity
    
    def add_node(self, node_data: NodeData) -> None:
        """
        添加节点到索引系统
        
        Args:
            node_data: 节点数据
            
        Raises:
            ValueError: 当节点数据无效时
        """
        try:
            self._validate_node_data(node_data)
            
            # 存储节点
            self.nodes[node_data.node_id] = node_data
            
            # 构建结构索引
            if isinstance(node_data.structure["graph"], nx.DiGraph):
                self.structure_index[node_data.node_id] = node_data.structure["graph"]
            else:
                raise ValueError("structure['graph'] must be a networkx.DiGraph instance")
                
            # 构建嵌入索引
            if node_data.embedding is not None:
                self.embedding_index[node_data.node_id] = node_data.embedding
                
            # 构建域索引
            domain = node_data.attributes["domain"]
            if domain not in self.domain_index:
                self.domain_index[domain] = []
            self.domain_index[domain].append(node_data.node_id)
            
            logger.info("Added node %s to index", node_data.node_id)
            
        except Exception as e:
            logger.error("Failed to add node %s: %s", node_data.node_id, str(e))
            raise
    
    def find_collisions(
        self,
        target_node_id: str,
        collision_threshold: float = 0.7,
        structural_weight: float = 0.5,
        functional_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        查找与目标节点发生跨域碰撞的节点
        
        Args:
            target_node_id: 目标节点ID
            collision_threshold: 碰撞阈值 [0, 1]
            structural_weight: 结构相似度权重 [0, 1]
            functional_weight: 功能相似度权重 [0, 1]
            
        Returns:
            List[Dict[str, Any]]: 碰撞结果列表，每个结果包含:
                - node_id: 碰撞节点ID
                - collision_score: 综合碰撞分数
                - structural_similarity: 结构相似度分数
                - functional_similarity: 功能相似度分数
                - match_details: 匹配细节描述
                
        Raises:
            ValueError: 当目标节点不存在或参数无效时
        """
        # 参数验证
        if target_node_id not in self.nodes:
            raise ValueError(f"Target node {target_node_id} not found in index")
            
        if not 0 <= collision_threshold <= 1:
            raise ValueError("collision_threshold must be between 0 and 1")
            
        if not 0 <= structural_weight <= 1 or not 0 <= functional_weight <= 1:
            raise ValueError("weights must be between 0 and 1")
            
        if abs(structural_weight + functional_weight - 1) > 0.01:
            raise ValueError("structural_weight + functional_weight must equal 1")
            
        target_node = self.nodes[target_node_id]
        results = []
        
        logger.info("Searching collisions for node %s with threshold %.2f", target_node_id, collision_threshold)
        
        for node_id, node in self.nodes.items():
            # 跳过自身和同域节点
            if node_id == target_node_id:
                continue
                
            if node.attributes["domain"] == target_node.attributes["domain"]:
                continue
                
            try:
                # 计算结构相似度
                structural_sim = self._calculate_structural_similarity(
                    target_node.structure["graph"],
                    node.structure["graph"]
                )
                
                # 计算功能相似度
                functional_sim = self._calculate_functional_similarity(
                    target_node.embedding,
                    node.embedding
                )
                
                # 计算综合碰撞分数
                collision_score = (
                    structural_weight * structural_sim +
                    functional_weight * functional_sim
                )
                
                # 检查是否超过阈值
                if collision_score >= collision_threshold:
                    match_details = {
                        "structural_match": structural_sim > 0.6,
                        "functional_match": functional_sim > 0.6,
                        "cross_domain": True
                    }
                    
                    result = {
                        "node_id": node_id,
                        "collision_score": collision_score,
                        "structural_similarity": structural_sim,
                        "functional_similarity": functional_sim,
                        "match_details": match_details
                    }
                    
                    results.append(result)
                    logger.debug(
                        "Found collision candidate: %s (score: %.3f)",
                        node_id, collision_score
                    )
                    
            except Exception as e:
                logger.warning(
                    "Failed to calculate collision score for node %s: %s",
                    node_id, str(e)
                )
                continue
                
        # 按碰撞分数排序
        results.sort(key=lambda x: x["collision_score"], reverse=True)
        
        logger.info(
            "Found %d collision candidates for node %s",
            len(results), target_node_id
        )
        
        return results


def generate_sample_graph(node_count: int, edge_probability: float = 0.3) -> nx.DiGraph:
    """
    生成示例图结构（辅助函数）
    
    Args:
        node_count: 节点数量
        edge_probability: 边生成概率
        
    Returns:
        nx.DiGraph: 生成的有向图
    """
    graph = nx.DiGraph()
    graph.add_nodes_from(range(node_count))
    
    for i in range(node_count):
        for j in range(node_count):
            if i != j and np.random.random() < edge_probability:
                graph.add_edge(i, j)
                
    return graph


def demo_usage():
    """演示跨域碰撞索引系统的使用"""
    # 创建索引系统
    index = CrossDomainCollisionIndex(embedding_dim=128)
    
    # 添加生物学节点
    bio_node = NodeData(
        node_id="bio_cell",
        attributes={"domain": "biology", "function": "energy_production"},
        structure={"graph": generate_sample_graph(10, 0.3)},
        embedding=np.random.rand(128)
    )
    index.add_node(bio_node)
    
    # 添加建筑节点（结构相似但不同域）
    arch_node = NodeData(
        node_id="arch_building",
        attributes={"domain": "architecture", "function": "structural_support"},
        structure={"graph": generate_sample_graph(10, 0.3)},
        embedding=np.random.rand(128)
    )
    index.add_node(arch_node)
    
    # 添加计算机科学节点（功能相似但不同域）
    cs_node = NodeData(
        node_id="cs_network",
        attributes={"domain": "computer_science", "function": "data_distribution"},
        structure={"graph": generate_sample_graph(8, 0.2)},
        embedding=np.random.rand(128)
    )
    index.add_node(cs_node)
    
    # 查找碰撞
    collisions = index.find_collisions("bio_cell", collision_threshold=0.5)
    
    print("\nCollision results:")
    for result in collisions:
        print(f"Node: {result['node_id']}, Score: {result['collision_score']:.3f}")
        print(f"  Structural: {result['structural_similarity']:.3f}")
        print(f"  Functional: {result['functional_similarity']:.3f}")
        print(f"  Details: {result['match_details']}\n")


if __name__ == "__main__":
    demo_usage()