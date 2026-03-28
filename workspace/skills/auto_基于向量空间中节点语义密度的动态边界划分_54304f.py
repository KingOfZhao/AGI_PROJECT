"""
模块: auto_基于向量空间中节点语义密度的动态边界划分_54304f
描述: 基于向量空间中节点语义密度的动态边界划分，识别认知孤岛与高密度簇。
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Any
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ClusterResult:
    """
    聚类结果数据结构。
    
    Attributes:
        cluster_labels (np.ndarray): 每个节点的簇标签，-1表示噪声点。
        densities (np.ndarray): 每个节点的局部密度值。
        core_indices (List[int]): 核心节点（高密度区）的索引列表。
        sparse_indices (List[int]): 稀疏节点（认知孤岛）的索引列表。
    """
    cluster_labels: np.ndarray
    densities: np.ndarray
    core_indices: List[int]
    sparse_indices: List[int]

def validate_input_data(node_vectors: np.ndarray) -> None:
    """
    辅助函数：验证输入节点向量矩阵的有效性。
    
    Args:
        node_vectors (np.ndarray): 节点向量矩阵，形状为 (n_samples, n_features)。
    
    Raises:
        ValueError: 如果输入数据不是二维数组或为空。
        TypeError: 如果输入不是numpy数组。
    """
    if not isinstance(node_vectors, np.ndarray):
        logger.error("输入类型错误：期望 numpy.ndarray")
        raise TypeError("node_vectors 必须是 numpy.ndarray 类型")
    
    if node_vectors.ndim != 2:
        logger.error(f"输入维度错误：期望 2 维，得到 {node_vectors.ndim} 维")
        raise ValueError("node_vectors 必须是二维数组
    if node_vectors.shape[0] == 0:
        logger.error("输入数据为空")
        raise ValueError("节点向量矩阵不能为空")
    logger.info("输入数据验证通过。")

def calculate_semantic_density(node_vectors: np.ndarray, k_neighbors: int = 15) -> np.ndarray:
    """
    核心函数 1: 计算向量空间中每个节点的语义密度。
    
    通过计算节点与其K近邻的平均余弦相似度来定义局部密度。
    密度越高，表示该节点周围语义越集中（高密度簇）；
    密度越低，表示该节点处于语义稀疏区（认知孤岛）。
    
    Args:
        node_vectors (np.ndarray): 归一化后的节点向量矩阵
        k_neighbors (int): 计算局部密度时考虑的最近邻数量。
    
    Returns:
        np.ndarray: 每个节点的密度评分数组。
    """
    try:
        n_samples = node_vectors.shape[0]
        # 边界检查：确保K值有效
        effective_k = min(k_neighbors, n_samples - 1)
        if effective_k < 1:
            logger.warning("样本数量过少，无法计算密度。")
            return np.ones(n_samples)

        logger.info(f"开始计算语义密度，样本数: {n_samples}, K: {effective_k}")
        
        # 计算余弦相似度矩阵
        # 注意：对于大规模数据，建议使用近似最近邻算法(如Annoy, FAISS)优化此处
        sim_matrix = cosine_similarity(node_vectors)
        
        # 排除自身相似度 (设为-1，排序后会在最后)
        np.fill_diagonal(sim_matrix, -1)
        
        # 找到每行前K个最相似节点的索引
        # argpartition 比 argsort 更快，当我们只需要前k个时
        top_k_indices = np.argpartition(sim_matrix, -effective_k, axis=1)[:, -effective_k:]
        
        # 计算平均相似度作为密度
        densities = np.zeros(n_samples)
        for i in range(n_samples):
            # 获取具体相似度值
            neighbor_sims = sim_matrix[i, top_k_indices[i]]
            densities[i] = np.mean(neighbor_sims)
            
        logger.info("语义密度计算完成。")
        return densities
        
    except Exception as e:
        logger.exception("计算语义密度时发生错误")
        raise

def dynamic_boundary_partition(node_vectors: np.ndarray, 
                               density_threshold: float = 0.5, 
                               dbscan_eps: float = 0.2, 
                               min_samples: int = 5) -> ClusterResult:
    """
    核心函数 2: 执行动态边界划分，识别认知孤岛与高密度簇。
    
    算法流程：
    1. 数据归一化。
    2. 计算节点密度。
    3. 基于密度进行分层：高密度区（核心）、低密度区（稀疏）。
    4. 使用 DBSCAN 对高密度区域进行聚类，识别具体的“认知内卷”区域。
    
    Args:
        node_vectors (np.ndarray): 原始节点向量矩阵。
        density_threshold (float): 判定稀疏/稠密的密度分位数阈值 (0.0-1.0)。
        dbscan_eps (float): DBSCAN算法的邻域半径。
        min_samples (int): DBSCAN算法的核心点最小样本数。
    
    Returns:
        ClusterResult: 包含标签、密度、核心索引和稀疏索引的结果对象。
    """
    validate_input_data(node_vectors)
    
    try:
        logger.info("开始执行动态边界划分算法...")
        
        # 1. 数据归一化 (对于余弦相似度至关重要)
        normalized_vectors = normalize(node_vectors)
        
        # 2. 计算密度
        densities = calculate_semantic_density(normalized_vectors)
        
        # 3. 动态阈值划分
        # 计算密度的统计分位数，自适应地划分边界
        cutoff_value = np.quantile(densities, density_threshold)
        
        # 稀疏区索引 (认知盲区/孤岛) -> 密度低于阈值
        sparse_indices = np.where(densities < cutoff_value)[0].tolist()
        
        # 稠密区索引 (潜在的内卷区) -> 密度高于阈值
        dense_mask = densities >= cutoff_value
        dense_indices = np.where(dense_mask)[0]
        
        # 4. 对稠密区进行聚类分析 (识别不同的认知簇)
        # 初始化标签为 -1 (噪声/未分类)
        labels = np.full(len(node_vectors), -1, dtype=int)
        
        if len(dense_indices) > 0:
            dense_vectors = normalized_vectors[dense_indices]
            
            # 使用 DBSCAN 识别连通的稠密簇
            # metric='cosine' 对于语义空间非常重要
            clusterer = DBSCAN(eps=dbscan_eps, min_samples=min_samples, metric='cosine')
            dense_labels = clusterer.fit_predict(dense_vectors)
            
            # 将稠密区的聚类结果映射回原索引
            labels[dense_indices] = dense_labels
            
            # 提取核心区域的索引 (即属于某个有效簇的节点)
            # 标签 >= 0 表示属于某个簇
            core_indices = dense_indices[dense_labels >= 0].tolist()
        else:
            core_indices = []

        logger.info(f"划分完成。总节点: {len(node_vectors)}, "
                    f"高密度簇节点: {len(core_indices)}, "
                    f"认知孤岛节点: {len(sparse_indices)}")
        
        return ClusterResult(
            cluster_labels=labels,
            densities=densities,
            core_indices=core_indices,
            sparse_indices=sparse_indices
        )
        
    except Exception as e:
        logger.exception("动态边界划分过程中发生异常")
        raise

# 使用示例
if __name__ == "__main__":
    # 模拟生成 1085 个节点的向量数据 (模拟 Embeddings)
    # 假设特征维度为 128
    num_nodes = 1085
    embed_dim = 128
    
    # 生成数据：包含一个明显的簇和一些分散的点
    np.random.seed(42)
    # 1. 生成一个稠密簇 (围绕中心点)
    cluster_center = np.random.rand(embed_dim)
    dense_points = cluster_center + np.random.normal(0, 0.05, (800, embed_dim))
    
    # 2. 生成稀疏点 (模拟认知孤岛)
    sparse_points = np.random.rand(285, embed_dim)
    
    # 合并并打乱
    mock_data = np.vstack([dense_points, sparse_points])
    np.random.shuffle(mock_data)
    
    print(f"输入数据形状: {mock_data.shape}")
    
    # 执行算法
    # density_threshold=0.3 意味着密度最低的30%区域被视为稀疏区
    try:
        result = dynamic_boundary_partition(
            node_vectors=mock_data,
            density_threshold=0.3,
            dbscan_eps=0.15,
            min_samples=5
        )
        
        print(f"\n=== 算法结果 ===")
        print(f"发现簇数量 (不含噪声): {len(set(result.cluster_labels)) - (1 if -1 in result.cluster_labels else 0)}")
        print(f"高密度核心节点数: {len(result.core_indices)}")
        print(f"认知孤岛/稀疏区节点数: {len(result.sparse_indices)}")
        
        # 展示部分稀疏区索引 (用于引导AI生成跨域清单)
        print(f"\n建议探索的稀疏区节点索引 (前10个): {result.sparse_indices[:10]}")
        
    except Exception as e:
        print(f"运行示例失败: {e}")