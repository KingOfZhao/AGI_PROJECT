"""
模块名称: cognitive_orphanage_manager
描述: 实现针对AGI知识库中'认知孤儿'节点的识别、聚类与归档功能。
      该模块通过语义相似度计算，将未被引用的孤立节点归类到现有的活跃类目中，
      以实现知识库的去重与结构优化。

Author: Senior Python Engineer
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class Node:
    """
    知识图谱中的节点数据结构。
    
    属性:
        id (str): 节点的唯一标识符。
        text (str): 节点的文本内容。
        type (str): 节点类型 (e.g., 'orphan', 'core')。
        embedding (Optional[np.ndarray]): 文本的向量表示。
        ref_count (int): 被其他节点或SKILL引用的次数。
    """
    id: str
    text: str
    type: str = 'unknown'
    embedding: Optional[np.ndarray] = None
    ref_count: int = 0

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("节点ID必须是非空字符串")
        if self.embedding is not None and not isinstance(self.embedding, np.ndarray):
            try:
                self.embedding = np.array(self.embedding)
            except Exception as e:
                raise TypeError(f"Embedding转换失败: {e}")


@dataclass
class ClusterResult:
    """
    聚类结果的数据结构。
    
    属性:
        target_core_node_id (str): 目标核心节点的ID（归档目标）。
        orphan_ids (List[str]): 被归类到该目标下的孤儿节点ID列表。
        confidence (float): 聚类的平均置信度（平均相似度）。
    """
    target_core_node_id: str
    orphan_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0


# --- 辅助函数 ---

def validate_embeddings(nodes: List[Node]) -> bool:
    """
    验证节点列表中的嵌入向量是否有效。
    
    参数:
        nodes (List[Node]): 待验证的节点列表。
        
    返回:
        bool: 如果所有节点都有非空且维度一致的embedding，返回True，否则False。
        
    异常:
        ValueError: 如果embedding维度不一致。
    """
    if not nodes:
        logger.warning("节点列表为空，验证跳过。")
        return True

    dim = None
    for node in nodes:
        if node.embedding is None:
            logger.error(f"节点 {node.id} 缺少嵌入向量。")
            return False
        
        if dim is None:
            dim = node.embedding.shape
        elif node.embedding.shape != dim:
            logger.error(f"节点 {node.id} 的嵌入维度 {node.embedding.shape} 与期望维度 {dim} 不一致。")
            raise ValueError("嵌入向量维度不一致")
            
    return True


# --- 核心逻辑函数 ---

def identify_orphans(all_nodes: List[Node]) -> Tuple[List[Node], List[Node]]:
    """
    识别并分离'认知孤儿'节点和'核心'节点。
    
    逻辑:
        1. 孤儿节点: ref_count == 0 且 未被标记为系统保留。
        2. 核心节点: ref_count > 0，作为潜在的归档目标。
    
    参数:
        all_nodes (List[Node]): 知识库中所有节点的列表。
        
    返回:
        Tuple[List[Node], List[Node]]: (孤儿节点列表, 核心节点列表)
    """
    logger.info(f"开始扫描 {len(all_nodes)} 个节点以识别孤儿...")
    
    orphans: List[Node] = []
    cores: List[Node] = []
    
    if not all_nodes:
        return orphans, cores

    for node in all_nodes:
        # 简单的边界检查
        if not isinstance(node, Node):
            logger.warning(f"跳过无效数据类型: {type(node)}")
            continue
            
        if node.ref_count == 0:
            orphans.append(node)
        else:
            cores.append(node)
            
    logger.info(f"识别完成: 发现 {len(orphans)} 个孤儿节点, {len(cores)} 个核心节点。")
    return orphans, cores


def semantic_deduplication_clustering(
    core_nodes: List[Node], 
    orphan_nodes: List[Node], 
    similarity_threshold: float = 0.85
) -> List[ClusterResult]:
    """
    基于语义相似度将孤儿节点聚类到核心节点。
    
    算法流程:
        1. 验证向量数据。
        2. 构建核心节点的向量索引矩阵。
        3. 遍历孤儿节点，计算其与所有核心节点的余弦相似度。
        4. 找到相似度最高的核心节点。
        5. 如果最高相似度超过阈值，则将孤儿节点分配给该核心节点。
        6. 生成归档建议（ClusterResult）。
    
    参数:
        core_nodes (List[Node]): 核心节点列表（归档目标）。
        orphan_nodes (List[Node]): 待归档的孤儿节点列表。
        similarity_threshold (float): 判定为语义重复的阈值 (0.0 to 1.0)。
        
    返回:
        List[ClusterResult]: 聚类结果列表，包含每个核心节点接纳的孤儿信息。
    """
    logger.info("开始语义去重聚类过程...")
    
    # 1. 数据验证
    if not validate_embeddings(core_nodes) or not validate_embeddings(orphan_nodes):
        raise ValueError("输入节点包含无效或缺失的嵌入向量，无法进行聚类。")

    if not core_nodes or not orphan_nodes:
        logger.info("核心节点或孤儿节点为空，无需聚类。")
        return []

    # 2. 准备向量矩阵
    try:
        core_matrix = np.array([n.embedding for n in core_nodes])
        orphan_matrix = np.array([n.embedding for n in orphan_nodes])
    except Exception as e:
        logger.error(f"向量矩阵构建失败: {e}")
        raise

    # 3. 计算相似度矩阵 (Orphans x Cores)
    # sim_matrix[i][j] 表示 orphan_i 与 core_j 的相似度
    sim_matrix = cosine_similarity(orphan_matrix, core_matrix)
    
    # 4. 分配逻辑
    # 初始化结果容器 {core_id: ClusterResult}
    results_map: Dict[str, ClusterResult] = {
        node.id: ClusterResult(target_core_node_id=node.id) 
        for node in core_nodes
    }
    
    matched_count = 0
    
    for i, orphan in enumerate(orphan_nodes):
        # 获取当前孤儿与所有核心节点的相似度
        similarities = sim_matrix[i]
        
        # 找到最高相似度的索引
        max_sim_idx = np.argmax(similarities)
        max_sim_score = similarities[max_sim_idx]
        
        if max_sim_score >= similarity_threshold:
            target_core = core_nodes[max_sim_idx]
            
            # 将孤儿添加到对应核心节点的结果中
            results_map[target_core.id].orphan_ids.append(orphan.id)
            results_map[target_core.id].confidence = (
                (results_map[target_core.id].confidence * (len(results_map[target_core.id].orphan_ids) - 1) + max_sim_score) 
                / len(results_map[target_core.id].orphan_ids)
            )
            matched_count += 1
            logger.debug(f"匹配成功: 孤儿 '{orphan.id}' -> 核心 '{target_core.id}' (Sim: {max_sim_score:.4f})")
        else:
            logger.debug(f"孤儿 '{orphan.id}' 未找到足够相似的核心节点 (Max Sim: {max_sim_score:.4f})")

    # 5. 过滤掉没有接纳任何孤儿的结果
    final_results = [res for res in results_map.values() if res.orphan_ids]
    
    logger.info(f"聚类完成。共处理 {len(orphan_nodes)} 个孤儿，成功匹配归档 {matched_count} 个。")
    return final_results


# --- 使用示例 ---

if __name__ == "__main__":
    # 模拟生成测试数据
    def generate_mock_embedding(dim=128):
        return np.random.rand(dim)

    # 核心节点 (被引用)
    nodes_data = [
        Node(id="core_1", text="Python编程基础", ref_count=10, embedding=generate_mock_embedding()),
        Node(id="core_2", text="机器学习算法原理", ref_count=5, embedding=generate_mock_embedding()),
        Node(id="core_3", text="数据清洗技巧", ref_count=8, embedding=generate_mock_embedding()),
    ]
    
    # 让 core_1 和 orphan_1 的向量非常相似 (模拟重复)
    base_vec = generate_mock_embedding()
    nodes_data[0].embedding = base_vec
    
    # 孤儿节点 (未被引用)
    # orphan_1 是 core_1 的重复项
    # orphan_2 是无关噪声
    # orphan_3 是 core_2 的重复项
    orphan_data = [
        Node(id="orph_1", text="Python基础编程入门", ref_count=0, embedding=base_vec + (np.random.rand(128) * 0.01)), # 高相似度
        Node(id="orph_2", text="天气预报", ref_count=0, embedding=generate_mock_embedding()), # 低相似度
        Node(id="orph_3", text="ML算法综述", ref_count=0, embedding=nodes_data[1].embedding + (np.random.rand(128) * 0.05)), # 中高相似度
    ]

    all_nodes = nodes_data + orphan_data

    try:
        # 1. 识别孤儿
        orphans, cores = identify_orphans(all_nodes)
        
        # 2. 执行语义去重聚类
        # 阈值设为 0.9，确保只聚合非常相似的内容
        clustering_results = semantic_deduplication_clustering(
            core_nodes=cores, 
            orphan_nodes=orphans, 
            similarity_threshold=0.90
        )
        
        # 3. 打印结果
        print("\n=== 归档建议报告 ===")
        for res in clustering_results:
            print(f"目标类目: {res.target_core_node_id}")
            print(f"  - 接纳的孤儿节点: {res.orphan_ids}")
            print(f"  - 平均相似度: {res.confidence:.4f}")
            print("-" * 30)
            
    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}", exc_info=True)