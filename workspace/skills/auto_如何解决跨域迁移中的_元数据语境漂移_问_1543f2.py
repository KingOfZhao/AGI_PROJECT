"""
模块: auto_如何解决跨域迁移中的_元数据语境漂移_问_1543f2
描述: 解决跨域迁移中的“元数据语境漂移”问题。

本模块实现了一个基于上下文感知的动态权重调整机制。在AGI或大规模知识检索系统中，
同一词汇在不同领域（如计算机网络 vs. 认知心理学）可能具有截然不同的含义。
本系统通过计算输入语境与领域原型的语义距离，动态调整检索节点的权重，
防止因词汇重叠而导致的错误关联。

典型应用场景:
    - 跨学科知识图谱检索
    - AGI系统的多语境理解
    - 专业领域搜索引擎的消歧

Author: AGI System Core Engineer
Date: 2023-10-27
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型别名，提高代码可读性
EmbeddingVector = np.ndarray  # 语义向量
DomainLabel = str             # 领域标签


@dataclass
class NodeMetadata:
    """
    知识节点的元数据结构。
    
    Attributes:
        node_id (str): 节点的唯一标识符。
        term (str): 节点包含的关键词（如 "延迟"）。
        domain (DomainLabel): 节点所属领域（如 "networking", "psychology"）。
        context_vector (EmbeddingVector): 节点语义的向量表示，由嵌入模型生成。
        static_weight (float): 节点的初始静态权重/相关性得分 (0.0 到 1.0)。
    """
    node_id: str
    term: str
    domain: DomainLabel
    context_vector: EmbeddingVector
    static_weight: float


def _cosine_similarity(vec_a: EmbeddingVector, vec_b: EmbeddingVector) -> float:
    """
    辅助函数：计算两个向量之间的余弦相似度。
    
    Args:
        vec_a (EmbeddingVector): 向量A。
        vec_b (EmbeddingVector): 向量B。

    Returns:
        float: 相似度得分，范围 [-1, 1]。
    
    Raises:
        ValueError: 如果向量维度不匹配或 norm 为 0。
    """
    if vec_a.shape != vec_b.shape:
        logger.error(f"向量维度不匹配: A{vec_a.shape} vs B{vec_b.shape}")
        raise ValueError("Vector dimensions must match.")
    
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def calculate_contextual_relevance(
    query_context: EmbeddingVector,
    domain_prototypes: Dict[DomainLabel, EmbeddingVector],
    node: NodeMetadata,
    alpha: float = 0.7
) -> Tuple[str, float]:
    """
    核心函数 1: 计算特定节点在给定查询语境下的动态相关性得分。
    
    通过比较查询语境与领域原型（该领域的典型语义中心），计算一个惩罚因子。
    如果节点所属领域与查询语境高度不符，即使关键词匹配，其最终权重也会被降低。
    
    公式:
        Final_Score = static_weight * (alpha + (1 - alpha) * Domain_Similarity)
        其中 Domain_Similarity 是查询向量与该节点所属领域原型向量的相似度。
    
    Args:
        query_context (EmbeddingVector): 用户当前查询的语义向量。
        domain_prototypes (Dict[DomainLabel, EmbeddingVector]): 各领域的原型向量字典。
        node (NodeMetadata): 待评估的知识节点。
        alpha (float): 基础权重因子 (0.0-1.0)，用于保留多少原始静态权重。
                       默认 0.7 表示哪怕语境不完全匹配，仍保留 70% 的原始相关性。

    Returns:
        Tuple[str, float]: (节点ID, 调整后的动态权重)。
    
    Example:
        >>> query_vec = np.array([0.9, 0.1, 0.0]) # 指向网络/技术方向
        >>> prototypes = {"network": np.array([1.0, 0.0, 0.0]), "psych": np.array([0.0, 1.0, 0.0])}
        >>> node_net = NodeMetadata("n1", "latency", "network", ..., 1.0)
        >>> calculate_contextual_relevance(query_vec, prototypes, node_net)
        ('n1', 0.97)  # 高分
    """
    if not 0.0 <= alpha <= 1.0:
        logger.warning(f"Alpha值 {alpha} 超出推荐范围 [0, 1]，已自动截断。")
        alpha = max(0.0, min(1.0, alpha))

    node_domain = node.domain
    if node_domain not in domain_prototypes:
        logger.warning(f"节点 {node.node_id} 的领域 '{node_domain}' 缺少原型定义，使用中性权重。")
        domain_sim = 0.5 # 未知领域给予中等偏低的语境相关性
    else:
        prototype_vec = domain_prototypes[node_domain]
        try:
            domain_sim = _cosine_similarity(query_context, prototype_vec)
        except ValueError as e:
            logger.error(f"计算相似度失败: {e}")
            domain_sim = 0.0

    # 归一化相似度到 [0, 1] 范围 (假设 cosine 可能是 -1 到 1)
    normalized_sim = (domain_sim + 1) / 2
    
    # 动态权重调整机制
    # 如果 domain_sim 高，权重接近 node.static_weight
    # 如果 domain_sim 低，权重被显著抑制
    dynamic_weight = node.static_weight * (alpha + (1 - alpha) * normalized_sim)
    
    logger.debug(f"Node {node.node_id} | Domain: {node_domain} | Sim: {domain_sim:.4f} | Final W: {dynamic_weight:.4f}")
    
    return node.node_id, float(dynamic_weight)


def filter_and_rank_nodes(
    query: str,
    query_vector: EmbeddingVector,
    domain_prototypes: Dict[DomainLabel, EmbeddingVector],
    candidate_nodes: List[NodeMetadata],
    threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    核心函数 2: 批量处理候选节点，过滤语境漂移节点并排序。
    
    该函数是模块的主入口，用于处理一组初始检索到的候选节点，
    剔除那些虽然词汇匹配但语境严重冲突的节点。
    
    Args:
        query (str): 原始查询文本（仅用于日志）。
        query_vector (EmbeddingVector): 查询的嵌入向量。
        domain_prototypes (Dict[DomainLabel, EmbeddingVector]): 领域原型映射。
        candidate_nodes (List[NodeMetadata]): 候选节点列表。
        threshold (float): 保留节点的最低动态权重阈值。

    Returns:
        List[Dict[str, Any]]: 排序后的结果列表，包含节点ID、权重和原始元数据。
        
    Input Format:
        candidate_nodes: 包含 NodeMetadata 对象的列表。
        domain_prototypes: Key为领域名，Value为该领域平均语义向量的字典。
        
    Output Format:
        [{'id': str, 'score': float, 'domain': str, 'term': str}, ...]
    """
    if not candidate_nodes:
        logger.info("无候选节点输入。")
        return []

    logger.info(f"开始处理查询: '{query}'，候选节点数: {len(candidate_nodes)}")
    
    weighted_results = []
    
    for node in candidate_nodes:
        # 数据验证
        if not isinstance(node.context_vector, np.ndarray) or node.context_vector.size == 0:
            logger.warning(f"节点 {node.node_id} 向量无效，跳过。")
            continue
            
        try:
            node_id, score = calculate_contextual_relevance(
                query_vector, domain_prototypes, node
            )
            
            if score >= threshold:
                weighted_results.append({
                    "id": node_id,
                    "score": score,
                    "domain": node.domain,
                    "term": node.term
                })
        except Exception as e:
            logger.error(f"处理节点 {node.node_id} 时发生异常: {e}")
            continue

    # 根据动态权重降序排列
    weighted_results.sort(key=lambda x: x["score"], reverse=True)
    
    logger.info(f"处理完成。保留节点数: {len(weighted_results)}/{len(candidate_nodes)}")
    return weighted_results

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 模拟数据准备
    
    # 假设我们的嵌入维度是 3 维 (为了演示方便，实际可能是 768 或 1536)
    # 领域原型: 计算机网络偏向 x 轴, 认知心理学偏向 y 轴
    mock_prototypes = {
        "computer_network": np.array([0.9, 0.1, 0.0]), # 技术语境
        "cognitive_psychology": np.array([0.1, 0.9, 0.0]) # 心理语境
    }

    # 候选节点：包含关键词 "Delay/Latency" 但属于不同领域
    nodes_db = [
        NodeMetadata(
            node_id="net_001", 
            term="latency", 
            domain="computer_network", 
            context_vector=np.array([0.85, 0.15, 0.0]), 
            static_weight=0.95 # 初始相关性很高
        ),
        NodeMetadata(
            node_id="psy_001", 
            term="delay", # 注意：词义漂移点
            domain="cognitive_psychology", 
            context_vector=np.array([0.1, 0.85, 0.0]), 
            static_weight=0.90 # 初始相关性也很高
        ),
        NodeMetadata(
            node_id="net_002", 
            term="packet_loss", 
            domain="computer_network", 
            context_vector=np.array([0.8, 0.2, 0.0]), 
            static_weight=0.80
        )
    ]

    # 2. 场景：用户查询 "网络延迟优化" (语境偏向计算机)
    # 模拟用户查询向量 (偏向 x 轴)
    user_query_vec = np.array([0.95, 0.05, 0.0]) 
    
    print("--- 场景 1: 查询 '网络延迟优化' (技术语境) ---")
    results = filter_and_rank_nodes(
        query="网络延迟优化",
        query_vector=user_query_vec,
        domain_prototypes=mock_prototypes,
        candidate_nodes=nodes_db,
        threshold=0.2
    )
    
    for res in results:
        print(f"ID: {res['id']} | Domain: {res['domain']:20} | Score: {res['score']:.4f} | Term: {res['term']}")
    
    # 预期结果：net_001 (Latency) 得分最高，psy_001 (Delay) 权重应被大幅降低甚至过滤
    
    print("\n--- 场景 2: 查询 '延迟满足感实验' (心理语境) ---")
    # 模拟用户查询向量 (偏向 y 轴)
    user_query_vec_psych = np.array([0.05, 0.95, 0.0])
    
    results_psych = filter_and_rank_nodes(
        query="延迟满足感实验",
        query_vector=user_query_vec_psych,
        domain_prototypes=mock_prototypes,
        candidate_nodes=nodes_db,
        threshold=0.2
    )
    
    for res in results_psych:
        print(f"ID: {res['id']} | Domain: {res['domain']:20} | Score: {res['score']:.4f} | Term: {res['term']}")
        
    # 预期结果：psy_001 得分最高，net_001 权重被降低