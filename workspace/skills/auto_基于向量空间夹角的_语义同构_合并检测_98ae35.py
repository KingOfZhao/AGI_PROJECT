"""
Module: auto_semantic_isomorphism_merge_98ae35
Description: 基于向量空间夹角的'语义同构'合并检测。

本模块实现了在高维向量空间中检测语义冗余节点的算法。主要用于处理大规模认知网络
（如AGI系统的记忆单元），通过计算节点Embedding的余弦相似度，识别描述同一微观
事实的不同节点。当夹角过小且上下文不可区分时，判定为语义同构，触发合并建议。

Author: Senior Python Engineer
Version: 1.0.0
Date: 2023-10-27
License: MIT
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass
from pydantic import BaseModel, Field, validator

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据模型定义 ---

class NodeEmbedding(BaseModel):
    """
    节点Embedding数据模型。
    
    Attributes:
        id (str): 节点的唯一标识符。
        content (str): 节点的文本内容描述。
        vector (List[float]): 节点的向量表示。
        context_tags (Set[str]): 上下文标签，用于辅助区分语义。
    """
    id: str
    content: str
    vector: List[float]
    context_tags: Set[str] = Field(default_factory=set)

    @validator('vector')
    def check_vector_not_empty(cls, v):
        if not v:
            raise ValueError("Vector cannot be empty")
        return v

@dataclass
class MergeRecommendation:
    """
    合并建议结果数据结构。
    """
    target_node_id: str
    source_node_ids: List[str]
    similarity_score: float
    reason: str

# --- 核心功能类 ---

class SemanticIsomorphismDetector:
    """
    语义同构检测器。
    
    该类负责加载节点数据，构建向量索引，并基于余弦相似度检测冗余节点。
    它还考虑了上下文标签来防止误报（例如，"苹果"在"水果"上下文和"手机"上下文中
    应该被区分，即使字面向量可能相似）。
    """

    def __init__(self, similarity_threshold: float = 0.95, min_cluster_size: int = 2):
        """
        初始化检测器。

        Args:
            similarity_threshold (float): 判定为同构的余弦相似度阈值 (0.0 to 1.0)。
            min_cluster_size (int): 形成簇的最小节点数。
        """
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.node_matrix: Optional[np.ndarray] = None
        self.node_map: Dict[int, NodeEmbedding] = {}
        logger.info(f"Initialized detector with threshold: {similarity_threshold}")

    def _normalize_vectors(self, vectors: List[List[float]]) -> np.ndarray:
        """
        辅助函数：对向量进行L2归一化。
        
        Args:
            vectors (List[List[float]]): 原始向量列表。
            
        Returns:
            np.ndarray: 归一化后的numpy矩阵。
        """
        arr = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        # 防止除以零
        norms[norms == 0] = 1e-10
        normalized_arr = arr / norms
        return normalized_arr

    def load_nodes(self, nodes: List[NodeEmbedding]) -> None:
        """
        加载节点并构建向量矩阵。
        
        Args:
            nodes (List[NodeEmbedding]): 节点对象列表。
        
        Raises:
            ValueError: 如果节点列表为空。
        """
        if not nodes:
            raise ValueError("Node list cannot be empty.")
        
        vectors = []
        self.node_map.clear()
        
        for idx, node in enumerate(nodes):
            self.node_map[idx] = node
            vectors.append(node.vector)
            
        self.node_matrix = self._normalize_vectors(vectors)
        logger.info(f"Loaded {len(nodes)} nodes into the detector.")

    def _calculate_cosine_similarity_matrix(self) -> np.ndarray:
        """
        核心函数：计算全量节点的余弦相似度矩阵。
        
        由于向量已在_load阶段归一化，点积即为余弦相似度。
        
        Returns:
            np.ndarray: N x N 的相似度矩阵。
        """
        if self.node_matrix is None:
            raise RuntimeError("Nodes not loaded. Call load_nodes() first.")
            
        logger.debug("Calculating cosine similarity matrix...")
        # 矩阵乘法计算相似度
        sim_matrix = np.dot(self.node_matrix, self.node_matrix.T)
        return sim_matrix

    def _check_context_compatibility(self, node_a: NodeEmbedding, node_b: NodeEmbedding) -> bool:
        """
        辅助函数：检查上下文兼容性。
        
        如果两个节点有交集的上下文标签，或者其中一个没有标签（通用节点），
        则认为在上下文中不可区分（或不需要区分），允许合并。
        这是一个简化的逻辑，实际AGI场景可能更复杂。
        
        Args:
            node_a: 节点A
            node_b: 节点B
            
        Returns:
            bool: True表示在上下文中足够相似/兼容，False表示应区分。
        """
        # 如果都没有标签，纯粹依赖向量
        if not node_a.context_tags and not node_b.context_tags:
            return True
            
        # 检查交集
        intersection = node_a.context_tags & node_b.context_tags
        return bool(intersection)

    def detect_redundancies(self) -> List[MergeRecommendation]:
        """
        核心函数：执行同构检测并生成合并建议。
        
        Algorithm:
        1. 计算相似度矩阵。
        2. 过滤掉低于阈值的连接。
        3. 使用并查集或类似的聚类逻辑将相似节点分组。
        4. 验证上下文。
        5. 生成MergeRecommendation。
        
        Returns:
            List[MergeRecommendation]: 建议合并的节点组列表。
        """
        if self.node_matrix is None:
            raise RuntimeError("Nodes not loaded.")

        sim_matrix = self._calculate_cosine_similarity_matrix()
        n_nodes = len(self.node_map)
        visited = set()
        recommendations = []
        
        logger.info("Scanning for semantic isomorphisms...")

        for i in range(n_nodes):
            if i in visited:
                continue

            current_cluster_indices = [i]
            # 寻找与i相似且未被访问的节点
            for j in range(i + 1, n_nodes):
                if j in visited:
                    continue
                
                # 边界检查：忽略自相似度（对角线）和负值
                if sim_matrix[i, j] >= self.similarity_threshold:
                    node_i = self.node_map[i]
                    node_j = self.node_map[j]
                    
                    # 上下文二次校验
                    if self._check_context_compatibility(node_i, node_j):
                        current_cluster_indices.append(j)
            
            # 如果找到了冗余簇
            if len(current_cluster_indices) >= self.min_cluster_size:
                # 标记为已访问
                for idx in current_cluster_indices:
                    visited.add(idx)
                
                # 生成建议：选择第一个节点作为Target，其余作为Source
                target_idx = current_cluster_indices[0]
                source_indices = current_cluster_indices[1:]
                
                target_node = self.node_map[target_idx]
                source_nodes = [self.node_map[idx] for idx in source_indices]
                
                # 计算簇内平均相似度作为分数
                # 这里简化处理，取 i 与其他的平均相似度
                scores = [sim_matrix[target_idx, s] for s in source_indices]
                avg_score = np.mean(scores)
                
                rec = MergeRecommendation(
                    target_node_id=target_node.id,
                    source_node_ids=[n.id for n in source_nodes],
                    similarity_score=float(avg_score),
                    reason=f"High semantic similarity (>{self.similarity_threshold}) and context overlap detected."
                )
                recommendations.append(rec)
                logger.info(f"Found redundancy cluster: Target {target_node.id} merges {len(source_nodes)} nodes.")

        return recommendations

# --- 使用示例 ---

def generate_mock_data(count: int = 100, vector_dim: int = 128) -> List[NodeEmbedding]:
    """生成模拟数据用于测试"""
    import random
    data = []
    for i in range(count):
        # 随机生成向量
        vec = np.random.randn(vector_dim).tolist()
        # 偶尔生成一些非常相似的向量（模拟同构）
        if i > 0 and i % 10 == 0:
            # 复制前一个向量并添加微小噪声
            base_vec = data[-1].vector
            noise = np.random.normal(0, 0.01, vector_dim)
            vec = (np.array(base_vec) + noise).tolist()
            tag = data[-1].context_tags
        else:
            tag = {f"domain_{random.randint(1,5)}"}
            
        data.append(NodeEmbedding(
            id=f"node_{i:04d}",
            content=f"Content description for node {i}",
            vector=vec,
            context_tags=tag
        ))
    return data

if __name__ == "__main__":
    # 示例用法
    print("Running Semantic Isomorphism Detection Demo...")
    
    # 1. 准备数据
    # 生成50个节点，其中包含一些人为制造的相似节点
    mock_nodes = generate_mock_data(count=50, vector_dim=64)
    print(f"Generated {len(mock_nodes)} mock nodes.")

    # 2. 初始化检测器
    # 阈值设为0.90，稍微宽松一点以便捕捉到模拟的相似数据
    detector = SemanticIsomorphismDetector(similarity_threshold=0.90)

    try:
        # 3. 加载数据
        detector.load_nodes(mock_nodes)

        # 4. 执行检测
        results = detector.detect_redundancies()

        # 5. 输出结果
        print(f"\nDetected {len(results)} merge recommendations.")
        for rec in results:
            print(f"- Merge {rec.source_node_ids} into {rec.target_node_id}")
            print(f"  Score: {rec.similarity_score:.4f}")
            print(f"  Reason: {rec.reason}")
            
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)