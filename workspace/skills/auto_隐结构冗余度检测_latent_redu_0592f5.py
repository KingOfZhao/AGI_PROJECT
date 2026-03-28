"""
模块: auto_隐结构冗余度检测_latent_redu_0592f5
描述: 隐结构冗余度检测。
       利用高维向量空间计算节点间的‘功能距离’，
       自动聚类并合并那些在解决问题时表现出完全替代关系的冗余节点。
作者: AGI System Core Engineer
版本: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeNode:
    """
    知识节点数据结构。
    
    Attributes:
        node_id (str): 节点的唯一标识符。
        content (str): 节点的文本内容或描述。
        embedding (Optional[np.ndarray]): 节点的向量表示。
        merged_ids (Set[str]): 被合并进该节点的ID集合。
    """
    node_id: str
    content: str
    embedding: Optional[np.ndarray] = None
    merged_ids: Set[str] = None

    def __post_init__(self):
        if self.merged_ids is None:
            self.merged_ids = set()

def validate_embeddings(nodes: List[KnowledgeNode]) -> bool:
    """
    辅助函数：验证节点列表中的向量数据是否有效。
    
    Args:
        nodes (List[KnowledgeNode]): 待验证的节点列表。
        
    Returns:
        bool: 如果所有节点都有有效向量则返回True，否则抛出ValueError。
        
    Raises:
        ValueError: 如果节点列表为空或向量维度不一致/缺失。
    """
    if not nodes:
        logger.error("节点列表为空，无法进行检测。")
        raise ValueError("节点列表不能为空。")
    
    first_embedding = nodes[0].embedding
    if first_embedding is None:
        raise ValueError("节点的embedding不能为None。")
        
    reference_dim = first_embedding.shape
    
    for i, node in enumerate(nodes):
        if node.embedding is None:
            logger.error(f"节点 {node.node_id} 缺少向量数据。")
            raise ValueError(f"节点 {node.node_id} 向量缺失。")
        if node.embedding.shape != reference_dim:
            logger.error(f"节点 {node.node_id} 维度不匹配。")
            raise ValueError("所有节点的向量维度必须一致。")
            
    logger.info(f"数据验证通过: {len(nodes)} 个节点, 维度 {reference_dim}。")
    return True

def compute_functional_distance_matrix(nodes: List[KnowledgeNode]) -> np.ndarray:
    """
    核心函数：计算节点间的高维功能距离矩阵。
    
    功能距离定义：基于余弦相似度的反向指标（1 - cosine_similarity）。
    数值越小代表语义越接近，冗余度越高。
    
    Args:
        nodes (List[KnowledgeNode]): 包含向量数据的节点列表。
        
    Returns:
        np.ndarray: 对称的距离矩阵，shape为 (n_nodes, n_nodes)。
    """
    logger.info("正在构建向量矩阵并计算功能距离...")
    
    # 提取向量矩阵
    embeddings = np.array([node.embedding for node in nodes])
    
    # 计算余弦相似度矩阵
    # 使用sklearn进行优化计算，避免双重循环
    similarity_matrix = cosine_similarity(embeddings)
    
    # 转换为距离: Distance = 1 - Similarity
    # 添加微小epsilon防止数值误差导致的负数
    distance_matrix = 1.0 - similarity_matrix + 1e-9
    
    # 确保对角线为0 (自身距离为0)
    np.fill_diagonal(distance_matrix, 0.0)
    
    logger.info("功能距离矩阵计算完成。")
    return distance_matrix

def cluster_and_merge_nodes(
    nodes: List[KnowledgeNode], 
    distance_threshold: float = 0.15, 
    min_cluster_size: int = 1
) -> Tuple[List[KnowledgeNode], Dict[str, Any]]:
    """
    核心函数：执行聚类并合并冗余节点。
    
    使用层次聚类算法基于预计算的距离矩阵进行聚类。
    对于包含多个节点的簇，保留其中一个作为主节点，其余节点合并入主节点。
    
    Args:
        nodes (List[KnowledgeNode]): 原始节点列表。
        distance_threshold (float): 聚类阈值。距离小于此值的节点将被视为冗余。
                                    值越小，合并条件越严格。默认0.15。
        min_cluster_size (int): 最小簇大小，通常为1。
        
    Returns:
        Tuple[List[KnowledgeNode], Dict[str, Any]]: 
            - merged_nodes: 去重后的节点列表。
            - report: 包含合并统计信息的字典。
    """
    # 1. 数据验证
    validate_embeddings(nodes)
    
    # 2. 计算距离矩阵
    dist_matrix = compute_functional_distance_matrix(nodes)
    
    # 3. 层次聚类
    # linkage='average' 适合处理语义簇，避免极端值影响
    logger.info(f"开始聚类，距离阈值: {distance_threshold}")
    
    clustering_model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="precomputed",  # 使用预计算的距离矩阵
        linkage="average"
    )
    
    labels = clustering_model.fit_predict(dist_matrix)
    
    # 4. 节点合并逻辑
    clusters: Dict[int, List[KnowledgeNode]] = {}
    for idx, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(nodes[idx])
        
    final_nodes: List[KnowledgeNode] = []
    merged_count = 0
    
    # 按照簇ID排序处理，确保确定性
    for cluster_id in sorted(clusters.keys()):
        cluster_nodes = clusters[cluster_id]
        
        if len(cluster_nodes) == 1:
            # 无冗余，直接保留
            final_nodes.append(cluster_nodes[0])
        else:
            # 发现冗余簇
            # 策略：保留第一个节点（或可按内容长度、权重排序），合并其余节点
            primary_node = cluster_nodes[0]
            redundant_nodes = cluster_nodes[1:]
            
            # 记录被合并的节点信息
            for red_node in redundant_nodes:
                primary_node.merged_ids.add(red_node.node_id)
                # 如果被合并节点本身已经合并了其他节点，传递ID
                if red_node.merged_ids:
                    primary_node.merged_ids.update(red_node.merged_ids)
            
            final_nodes.append(primary_node)
            merged_count += len(redundant_nodes)
            logger.debug(f"簇 {cluster_id}: 保留 {primary_node.node_id}, 合并 {[n.node_id for n in redundant_nodes]}")

    report = {
        "original_count": len(nodes),
        "final_count": len(final_nodes),
        "nodes_merged": merged_count,
        "compression_ratio": (merged_count / len(nodes)) * 100 if nodes else 0,
        "threshold_used": distance_threshold
    }
    
    logger.info(f"合并完成。原始: {report['original_count']}, 新: {report['final_count']}, 冗余消除: {report['nodes_merged']}")
    
    return final_nodes, report

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 模拟生成测试数据
    def generate_mock_nodes(n=100, dim=128):
        nodes = []
        base_vectors = np.random.rand(5, dim) # 5个基础概念
        
        for i in range(n):
            # 随机选择一个基础概念并添加噪声，模拟语义重复
            base_idx = i % 5
            noise = np.random.normal(0, 0.05, dim)
            vec = base_vectors[base_idx] + noise
            # 归一化
            vec = vec / np.linalg.norm(vec)
            
            node = KnowledgeNode(
                node_id=f"node_{i:04d}",
                content=f"这是关于概念 {base_idx} 的变体描述 {i}",
                embedding=vec
            )
            nodes.append(node)
        return nodes

    print("--- 开始运行隐结构冗余度检测示例 ---")
    
    # 1. 准备数据
    mock_nodes = generate_mock_nodes(n=50, dim=64)
    print(f"生成了 {len(mock_nodes)} 个模拟节点。")
    
    # 2. 执行检测与合并
    # 阈值设为0.2，允许一定的语义漂移
    try:
        optimized_nodes, stats = cluster_and_merge_nodes(
            mock_nodes, 
            distance_threshold=0.2
        )
        
        print("\n--- 结果报告 ---")
        print(f"原始节点数: {stats['original_count']}")
        print(f"优化后节点数: {stats['final_count']}")
        print(f"压缩率: {stats['compression_ratio']:.2f}%")
        
        # 验证一个合并示例
        for node in optimized_nodes:
            if node.merged_ids:
                print(f"\n示例合并节点 ID: {node.node_id}")
                print(f"  合并了以下ID: {node.merged_ids}")
                break

    except ValueError as e:
        print(f"错误: {e}")