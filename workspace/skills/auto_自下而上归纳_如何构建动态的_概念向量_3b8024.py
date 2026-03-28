"""
模块名称: auto_自下而上归纳_如何构建动态的_概念向量_3b8024
描述: 本模块实现了一个自下而上的归纳系统，用于构建动态的概念向量空间。
      它利用HDBSCAN算法对非结构化节点进行无监督聚类，从而自动识别
      '重叠固化'节点，并检测语义漂移。该系统不依赖静态的预训练嵌入作为
      最终分类依据，而是通过密度聚类动态生成概念簇。
"""

import logging
import numpy as np
import hdbscan
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Node:
    """
    表示知识图谱中的一个节点。
    
    属性:
        id: 节点的唯一标识符
        raw_text: 节点的原始非结构化文本
        vector: 节点的语义向量 (通过某种编码器生成，此处假设已生成)
        meta: 元数据信息
    """
    id: str
    raw_text: str
    vector: Optional[np.ndarray] = None
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConceptCluster:
    """
    表示归纳出的概念簇（固化节点）。
    
    属性:
        cluster_id: 簇的ID
        centroid: 簇的中心向量
        member_ids: 属于该簇的节点ID列表
        keywords: 描述该簇的关键词列表
        stability_score: 稳定性得分 (0.0-1.0)，用于评估语义漂移
    """
    cluster_id: int
    centroid: np.ndarray
    member_ids: List[str]
    keywords: List[str]
    stability_score: float = 0.0

class DynamicConceptSpace:
    """
    动态概念向量空间构建器。
    
    该类负责将非结构化的节点数据通过无监督聚类转换为结构化的概念空间。
    它支持增量更新，并能识别新出现的模式。
    """
    
    def __init__(self, min_cluster_size: int = 5, min_samples: int = 3, 
                 drift_threshold: float = 0.15):
        """
        初始化动态概念空间。
        
        参数:
            min_cluster_size: HDBSCAN最小簇大小
            min_samples: HDBSCAN采样参数
            drift_threshold: 语义漂移阈值，超过此值认为簇发生了概念漂移
        """
        if min_cluster_size < 2:
            raise ValueError("min_cluster_size must be at least 2")
        if not 0.0 <= drift_threshold <= 1.0:
            raise ValueError("drift_threshold must be between 0.0 and 1.0")
            
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.drift_threshold = drift_threshold
        self.clusters: Dict[int, ConceptCluster] = {}
        self.unclustered_nodes: List[str] = []
        
        logger.info(f"Initialized DynamicConceptSpace with min_cluster_size={min_cluster_size}")

    def _validate_vectors(self, nodes: List[Node]) -> np.ndarray:
        """
        辅助函数：验证节点并提取向量矩阵。
        
        参数:
            nodes: 节点列表
            
        返回:
            归一化后的向量矩阵 (n_samples, n_features)
            
        异常:
            ValueError: 如果节点没有向量或向量维度不一致
        """
        if not nodes:
            raise ValueError("Node list cannot be empty")
            
        vectors = []
        for i, node in enumerate(nodes):
            if node.vector is None:
                raise ValueError(f"Node {node.id} has no vector data")
            if not isinstance(node.vector, np.ndarray):
                raise TypeError(f"Vector for node {node.id} must be a numpy array")
            vectors.append(node.vector)
            
        try:
            matrix = np.vstack(vectors)
            # 归一化处理，以便使用欧氏距离近似余弦相似度
            return normalize(matrix)
        except Exception as e:
            logger.error(f"Error stacking vectors: {str(e)}")
            raise ValueError("Inconsistent vector dimensions across nodes")

    def _extract_cluster_keywords(self, cluster_nodes: List[Node]) -> List[str]:
        """
        辅助函数：从簇中提取关键词。
        
        这里使用简单的词频统计作为示例。
        在生产环境中，应使用TF-IDF或TextRank等算法。
        
        参数:
            cluster_nodes: 簇内的节点列表
            
        返回:
            前5个高频词列表
        """
        all_words = []
        for node in cluster_nodes:
            # 简单分词（按空格分割，实际需要更复杂的NLP处理）
            words = node.raw_text.lower().split()
            all_words.extend(words)
            
        # 过滤停用词 (此处省略具体实现)
        word_counts = Counter(all_words)
        return [word for word, count in word_counts.most_common(5)]

    def induce_concepts(self, nodes: List[Node]) -> Dict[int, ConceptCluster]:
        """
        核心函数：执行自下而上的概念归纳。
        
        使用HDBSCAN对输入节点进行聚类，生成新的概念簇。
        
        参数:
            nodes: 待处理的节点列表，包含向量表示
            
        返回:
            新生成的概念簇字典 {cluster_id: ConceptCluster}
            
        示例:
            >>> space = DynamicConceptSpace()
            >>> nodes = [Node(id="1", raw_text="cat", vector=np.random.rand(128)),
            ...          Node(id="2", raw_text="dog", vector=np.random.rand(128))]
            >>> clusters = space.induce_concepts(nodes)
        """
        logger.info(f"Starting concept induction for {len(nodes)} nodes...")
        
        # 1. 数据验证与准备
        try:
            X = self._validate_vectors(nodes)
        except ValueError as e:
            logger.error(f"Data validation failed: {e}")
            return {}

        # 2. 执行HDBSCAN聚类
        # 使用euclidean距离，因为向量已归一化，等同于cosine距离
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric='euclidean',
            cluster_selection_method='eom' # Excess of Mass
        )
        
        try:
            labels = clusterer.fit_predict(X)
            probabilities = clusterer.probabilities_
        except Exception as e:
            logger.exception("Clustering failed")
            return {}

        # 3. 处理聚类结果
        new_clusters: Dict[int, ConceptCluster] = {}
        node_map = {n.id: n for n in nodes}
        
        # 按标签分组节点
        clustered_indices = {}
        for idx, label in enumerate(labels):
            if label == -1:
                self.unclustered_nodes.append(nodes[idx].id)
            else:
                if label not in clustered_indices:
                    clustered_indices[label] = []
                clustered_indices[label].append(idx)
        
        # 构建概念簇对象
        for label, indices in clustered_indices.items():
            cluster_nodes = [nodes[i] for i in indices]
            cluster_vectors = X[indices]
            
            # 计算中心点
            centroid = np.mean(cluster_vectors, axis=0)
            
            # 提取关键词
            keywords = self._extract_cluster_keywords(cluster_nodes)
            
            # 计算初始稳定性（基于成员到中心的平均距离）
            dists = np.linalg.norm(cluster_vectors - centroid, axis=1)
            stability = 1.0 - np.mean(dists) # 距离越小稳定性越高
            
            cluster = ConceptCluster(
                cluster_id=int(label),
                centroid=centroid,
                member_ids=[n.id for n in cluster_nodes],
                keywords=keywords,
                stability_score=float(stability)
            )
            new_clusters[label] = cluster
            
        self.clusters.update(new_clusters)
        logger.info(f"Induction complete. Found {len(new_clusters)} clusters, "
                    f"{len(self.unclustered_nodes)} noise points.")
        
        return new_clusters

    def detect_semantic_drift(self, new_nodes: List[Node]) -> List[Tuple[int, float]]:
        """
        核心函数：检测现有概念簇的语义漂移。
        
        比较新节点与现有簇中心的相似度，判断簇是否发生了概念漂移。
        
        参数:
            new_nodes: 新进入的节点列表
            
        返回:
            发生漂移的簇列表，包含 (cluster_id, drift_score)
            
        示例:
            >>> drifts = space.detect_semantic_drift(new_batch_nodes)
            >>> if drifts: print("Warning: Semantic drift detected!")
        """
        if not self.clusters:
            logger.warning("No existing clusters to detect drift against.")
            return []

        drift_report = []
        X_new = self._validate_vectors(new_nodes)
        
        # 获取现有簇的中心矩阵
        cluster_ids = list(self.clusters.keys())
        centroids = np.array([self.clusters[cid].centroid for cid in cluster_ids])
        
        # 计算相似度矩阵
        # (n_new_nodes, n_clusters)
        sim_matrix = cosine_similarity(X_new, centroids)
        
        # 分析每个簇的漂移情况
        for i, cid in enumerate(cluster_ids):
            # 获取分配给该簇的新节点（基于最高相似度）
            member_mask = np.argmax(sim_matrix, axis=1) == i
            if not np.any(member_mask):
                continue
                
            assigned_sims = sim_matrix[member_mask, i]
            avg_sim = np.mean(assigned_sims)
            
            # 漂移分数 = 1 - 平均相似度
            drift_score = 1.0 - avg_sim
            
            # 更新簇的稳定性（滑动平均模拟）
            current_stability = self.clusters[cid].stability_score
            new_stability = (current_stability + avg_sim) / 2
            self.clusters[cid].stability_score = new_stability
            
            if drift_score > self.drift_threshold:
                logger.warning(f"Semantic drift detected in Cluster {cid}. "
                               f"Drift score: {drift_score:.4f}")
                drift_report.append((cid, drift_score))
                
        return drift_report

# 使用示例
if __name__ == "__main__":
    # 模拟数据：3176个节点可能太大，此处演示逻辑
    # 假设向量维度为128
    DIM = 128
    
    # 生成模拟节点数据
    def generate_mock_nodes(n: int, center: np.ndarray, spread: float, label: str) -> List[Node]:
        nodes = []
        for i in range(n):
            vec = center + np.random.randn(DIM) * spread
            node = Node(
                id=f"{label}_{i}",
                raw_text=f"This is text about {label} number {i}",
                vector=vec
            )
            nodes.append(node)
        return nodes

    # 创建两个不同的概念中心
    center_cats = np.random.rand(DIM)
    center_dogs = np.random.rand(DIM) + 2.0  # 使其远离cats
    
    nodes_cats = generate_mock_nodes(50, center_cats, 0.2, "cat")
    nodes_dogs = generate_mock_nodes(50, center_dogs, 0.2, "dog")
    nodes_noise = [Node(id=f"noise_{i}", raw_text="random text", vector=np.random.rand(DIM)) for i in range(10)]
    
    all_nodes = nodes_cats + nodes_dogs + nodes_noise
    
    # 初始化空间
    concept_space = DynamicConceptSpace(min_cluster_size=5, drift_threshold=0.3)
    
    print("--- Phase 1: Initial Induction ---")
    # 执行归纳
    clusters = concept_space.induce_concepts(all_nodes)
    
    for cid, cluster in clusters.items():
        print(f"Cluster {cid}: Members={len(cluster.member_ids)}, Keywords={cluster.keywords}")
        
    print("\n--- Phase 2: Drift Detection ---")
    # 模拟语义漂移：引入稍微偏离中心的"猫"数据
    drifted_cats = generate_mock_nodes(10, center_cats + 0.5, 0.1, "drifted_cat")
    drifts = concept_space.detect_semantic_drift(drifted_cats)
    
    if drifts:
        print(f"Detected drifts: {drifts}")
    else:
        print("No significant drift detected.")