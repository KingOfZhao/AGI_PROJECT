"""
高级因果链路检索模块

该模块实现了超越传统向量相似度搜索的因果检索算法。
通过构建知识图谱并应用因果推理，返回连接用户现状与目标状态的
'最小作用力路径'，解决传统RAG碎片化问题。

Author: AGI System Core Engineer
Version: 2.0.0
"""

import logging
import heapq
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
import numpy as np
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CausalChainRetriever")


@dataclass
class KnowledgeNode:
    """
    知识节点数据结构
    
    Attributes:
        id (str): 节点唯一标识符
        content (str): 节点文本内容
        embedding (np.ndarray): 节点的向量嵌入表示
        metadata (Dict[str, Any]): 附加元数据
    """
    id: str
    content: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证"""
        if not self.id or not isinstance(self.id, str):
            raise ValueError("节点ID必须是非空字符串")
        if not self.content or not isinstance(self.content, str):
            raise ValueError("节点内容必须是非空字符串")
        if self.embedding is None or not isinstance(self.embedding, np.ndarray):
            raise ValueError("嵌入向量必须是numpy数组")
        if len(self.embedding.shape) != 1:
            raise ValueError("嵌入向量必须是一维数组")


@dataclass
class CausalEdge:
    """
    因果边数据结构
    
    Attributes:
        source_id (str): 源节点ID
        target_id (str): 目标节点ID
        weight (float): 边的权重（因果强度）
        relation_type (str): 关系类型（如'causes', 'enables', 'prevents'）
    """
    source_id: str
    target_id: str
    weight: float
    relation_type: str = "causes"
    
    def __post_init__(self):
        """数据验证"""
        if self.weight < 0 or self.weight > 1:
            raise ValueError("权重必须在0到1之间")
        valid_relations = {"causes", "enables", "prevents", "correlates"}
        if self.relation_type not in valid_relations:
            raise ValueError(f"关系类型必须是: {valid_relations}")


class CausalChainRetriever:
    """
    因果链路检索器
    
    实现基于解释力的检索算法，返回连接现状与目标的最小作用力路径。
    该算法不依赖于简单的向量相似度，而是通过因果图寻找逻辑关联路径。
    
    Attributes:
        nodes (Dict[str, KnowledgeNode]): 节点存储字典
        edges (List[CausalEdge]): 边列表
        adjacency (Dict[str, List[Tuple[str, float]]]): 邻接表表示
        embed_dim (int): 嵌入向量维度
        
    Example:
        >>> retriever = CausalChainRetriever(embed_dim=128)
        >>> retriever.add_node(node1)
        >>> retriever.add_edge(edge1)
        >>> path, score = retriever.retrieve_causal_chain(
        ...     current_state_emb, target_state_emb, top_k=3
        ... )
    """
    
    def __init__(self, embed_dim: int = 768):
        """
        初始化检索器
        
        Args:
            embed_dim: 嵌入向量维度
        """
        if embed_dim <= 0:
            raise ValueError("嵌入维度必须是正整数")
            
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[CausalEdge] = []
        self.adjacency: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        self.embed_dim = embed_dim
        self._is_built = False
        
        logger.info(f"初始化因果链路检索器，嵌入维度: {embed_dim}")
    
    def add_node(self, node: KnowledgeNode) -> None:
        """
        添加知识节点到检索器
        
        Args:
            node: 知识节点对象
            
        Raises:
            ValueError: 节点验证失败
        """
        if node.embedding.shape[0] != self.embed_dim:
            raise ValueError(
                f"节点嵌入维度{node.embedding.shape[0]}与检索器维度{self.embed_dim}不匹配"
            )
        
        self.nodes[node.id] = node
        self._is_built = False
        logger.debug(f"添加节点: {node.id}")
    
    def add_edge(self, edge: CausalEdge) -> None:
        """
        添加因果边到检索器
        
        Args:
            edge: 因果边对象
            
        Raises:
            ValueError: 边引用的节点不存在
        """
        if edge.source_id not in self.nodes:
            raise ValueError(f"源节点{edge.source_id}不存在")
        if edge.target_id not in self.nodes:
            raise ValueError(f"目标节点{edge.target_id}不存在")
        
        self.edges.append(edge)
        # 反向权重用于反向搜索
        self.adjacency[edge.target_id].append((edge.source_id, edge.weight))
        self._is_built = False
        logger.debug(f"添加边: {edge.source_id} -> {edge.target_id}")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 第一个向量
            vec2: 第二个向量
            
        Returns:
            余弦相似度值 [-1, 1]
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def _find_similar_nodes(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 5,
        exclude_ids: Optional[Set[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        查找与查询向量最相似的节点
        
        Args:
            query_embedding: 查询向量
            top_k: 返回的最大节点数
            exclude_ids: 需要排除的节点ID集合
            
        Returns:
            包含(节点ID, 相似度)元组的列表，按相似度降序排列
        """
        if exclude_ids is None:
            exclude_ids = set()
        
        similarities = []
        for node_id, node in self.nodes.items():
            if node_id in exclude_ids:
                continue
            sim = self._cosine_similarity(query_embedding, node.embedding)
            similarities.append((node_id, sim))
        
        # 按相似度降序排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _dijkstra_path(
        self, 
        start_ids: Set[str], 
        end_ids: Set[str],
        max_depth: int = 5
    ) -> Tuple[Optional[List[str]], float]:
        """
        使用改进的Dijkstra算法寻找最小作用力路径
        
        Args:
            start_ids: 起始节点ID集合
            end_ids: 目标节点ID集合
            max_depth: 最大搜索深度
            
        Returns:
            (路径节点列表, 路径得分)，如果没有路径则返回
        """
        # 初始化距离和前驱
        distances: Dict[str, float] = {nid: float('inf') for nid in self.nodes}
        predecessors: Dict[str, Optional[str]] = {nid: None for nid in self.nodes}
        distances.update({sid: 0.0 for sid in start_ids})
        
        # 优先队列: (累计距离, 节点ID, 深度)
        heap = [(0.0, sid, 0) for sid in start_ids]
        heapq.heapify(heap)
        
        visited: Set[str] = set()
        
        while heap:
            current_dist, current_id, depth = heapq.heappop(heap)
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            # 到达目标节点
            if current_id in end_ids:
                # 回溯路径
                path = []
                node = current_id
                while node is not None:
                    path.append(node)
                    node = predecessors[node]
                path.reverse()
                return path, current_dist
            
            # 超过最大深度
            if depth >= max_depth:
                continue
            
            # 遍历邻居（反向边，从target到source）
            for neighbor_id, weight in self.adjacency.get(current_id, []):
                if neighbor_id in visited:
                    continue
                
                # 作用力 = 1 - 因果强度（强度越高，作用力越小）
                effort = 1.0 - weight
                new_dist = current_dist + effort
                
                if new_dist < distances[neighbor_id]:
                    distances[neighbor_id] = new_dist
                    predecessors[neighbor_id] = current_id
                    heapq.heappush(heap, (new_dist, neighbor_id, depth + 1))
        
        return None, float('inf')
    
    def retrieve_causal_chain(
        self,
        current_state_embedding: np.ndarray,
        target_state_embedding: np.ndarray,
        top_k: int = 3,
        max_depth: int = 5,
        explanation_threshold: float = 0.3
    ) -> Tuple[List[List[KnowledgeNode]], List[float]]:
        """
        核心检索函数：检索连接现状与目标的因果链路
        
        该算法不返回简单的相似Q&A，而是返回一条能够解释
        如何从现状到达目标的'最小作用力路径'。
        
        Args:
            current_state_embedding: 现状状态的向量嵌入
            target_state_embedding: 目标状态的向量嵌入
            top_k: 返回的最多路径数量
            max_depth: 路径的最大深度（节点数）
            explanation_threshold: 解释力阈值，低于此值的路径将被过滤
            
        Returns:
            (路径列表, 得分列表): 
            - 路径列表：每个元素是KnowledgeNode链表
            - 得分列表：每个路径的解释力得分（越高越好）
            
        Raises:
            ValueError: 输入验证失败
            RuntimeError: 检索器状态异常
            
        Example:
            >>> current_emb = np.random.randn(768)
            >>> target_emb = np.random.randn(768)
            >>> paths, scores = retriever.retrieve_causal_chain(
            ...     current_emb, target_emb, top_k=2
            ... )
            >>> for path, score in zip(paths, scores):
            ...     print(f"得分: {score:.3f}")
            ...     for node in path:
            ...         print(f"  -> {node.content}")
        """
        # 输入验证
        if current_state_embedding is None or target_state_embedding is None:
            raise ValueError("现状和目标嵌入向量不能为空")
        
        if current_state_embedding.shape[0] != self.embed_dim:
            raise ValueError(
                f"现状嵌入维度{current_state_embedding.shape[0]}与检索器维度{self.embed_dim}不匹配"
            )
        
        if target_state_embedding.shape[0] != self.embed_dim:
            raise ValueError(
                f"目标嵌入维度{target_state_embedding.shape[0]}与检索器维度{self.embed_dim}不匹配"
            )
        
        if not self.nodes:
            logger.warning("检索器中没有节点")
            return [], []
        
        logger.info("开始因果链路检索...")
        
        # 1. 找到与现状最相似的节点（作为路径起点）
        start_candidates = self._find_similar_nodes(
            current_state_embedding, 
            top_k=top_k
        )
        start_ids = {nid for nid, _ in start_candidates if _ > explanation_threshold}
        
        # 2. 找到与目标最相似的节点（作为路径终点）
        end_candidates = self._find_similar_nodes(
            target_state_embedding, 
            top_k=top_k
        )
        end_ids = {nid for nid, _ in end_candidates if _ > explanation_threshold}
        
        if not start_ids or not end_ids:
            logger.warning("未找到足够相似的起点或终点节点")
            return [], []
        
        logger.info(
            f"找到{len(start_ids)}个起点候选, {len(end_ids)}个终点候选"
        )
        
        # 3. 使用改进的Dijkstra寻找最小作用力路径
        path_ids, effort = self._dijkstra_path(start_ids, end_ids, max_depth)
        
        if path_ids is None:
            logger.info("未找到连接路径")
            return [], []
        
        # 4. 计算解释力得分
        # 解释力 = (起点相似度 + 终点相似度) / 2 - 路径作用力
        start_sim = next(sim for nid, sim in start_candidates if nid == path_ids[0])
        end_sim = next(sim for nid, sim in end_candidates if nid == path_ids[-1])
        explanation_power = (start_sim + end_sim) / 2 - effort
        
        # 5. 构建返回结果
        result_path = [self.nodes[nid] for nid in path_ids]
        
        logger.info(
            f"找到因果链路，长度: {len(path_ids)}, 解释力: {explanation_power:.3f}"
        )
        
        return [result_path], [explanation_power]
    
    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """
        根据ID获取节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            节点对象，如果不存在则返回None
        """
        return self.nodes.get(node_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取检索器统计信息
        
        Returns:
            包含节点数、边数等统计信息的字典
        """
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "embed_dim": self.embed_dim,
            "is_built": self._is_built,
            "avg_connections": (
                sum(len(conns) for conns in self.adjacency.values()) / len(self.adjacency)
                if self.adjacency else 0
            )
        }


# 使用示例
if __name__ == "__main__":
    # 创建检索器实例
    retriever = CausalChainRetriever(embed_dim=128)
    
    # 创建示例知识节点
    np.random.seed(42)
    
    node1 = KnowledgeNode(
        id="problem_analysis",
        content="系统性能下降，需要分析根本原因",
        embedding=np.random.randn(128),
        metadata={"category": "diagnosis"}
    )
    
    node2 = KnowledgeNode(
        id="identify_bottleneck",
        content="识别数据库查询为性能瓶颈",
        embedding=np.random.randn(128),
        metadata={"category": "analysis"}
    )
    
    node3 = KnowledgeNode(
        id="optimize_query",
        content="优化数据库索引和查询语句",
        embedding=np.random.randn(128),
        metadata={"category": "solution"}
    )
    
    node4 = KnowledgeNode(
        id="performance_restored",
        content="系统性能恢复正常水平",
        embedding=np.random.randn(128),
        metadata={"category": "outcome"}
    )
    
    # 添加节点到检索器
    for node in [node1, node2, node3, node4]:
        retriever.add_node(node)
    
    # 创建因果边
    edge1 = CausalEdge("problem_analysis", "identify_bottleneck", 0.85, "causes")
    edge2 = CausalEdge("identify_bottleneck", "optimize_query", 0.9, "enables")
    edge3 = CausalEdge("optimize_query", "performance_restored", 0.95, "causes")
    
    # 添加边到检索器
    for edge in [edge1, edge2, edge3]:
        retriever.add_edge(edge)
    
    # 执行因果链路检索
    current_state = np.random.randn(128)  # 模拟现状向量
    target_state = np.random.randn(128)   # 模拟目标向量
    
    paths, scores = retriever.retrieve_causal_chain(
        current_state, target_state, top_k=3, max_depth=5
    )
    
    # 打印结果
    print("\n=== 因果链路检索结果 ===")
    for i, (path, score) in enumerate(zip(paths, scores)):
        print(f"\n路径 {i+1} (解释力: {score:.3f}):")
        for j, node in enumerate(path):
            prefix = "└─>" if j == len(path)-1 else "├─>"
            print(f"  {prefix} {node.content}")
    
    # 打印统计信息
    print("\n=== 检索器统计 ===")
    stats = retriever.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")