"""
模块: auto_人机共生_意图对齐_基于982个已有认_b9cbe5
描述: 实现基于动态权重图的语义鸿沟识别算法，用于AGI系统的意图对齐。

本模块通过构建一个连接用户意图（虚拟节点）与系统现有认知节点（真实节点）的动态
二部图，计算语义向量距离与上下文相关性的加权和。目标不是寻找最佳匹配，而是精
确量化'语义鸿沟'，即用户需求与现有能力之间的缺失部分（Gap）。

核心功能:
- 加载并验证现有认知节点数据。
- 计算用户输入与节点的语义相似度。
- 结合上下文动态调整权重。
- 识别并输出语义鸿沟最大的节点区域，辅助AGI进行自我补全。

依赖:
- numpy
- typing
- logging
- dataclasses
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CognitiveNode:
    """
    认知节点的数据结构。
    
    属性:
        node_id (str): 节点的唯一标识符。
        label (str): 节点的语义标签（如 '代码优化', '内存管理'）。
        embedding (np.ndarray): 节点的语义向量表示 (例如由BERT或Transformer生成)。
        connections (List[str]): 该节点在图中连接的其他节点ID列表。
    """
    node_id: str
    label: str
    embedding: np.ndarray
    connections: List[str]

class SemanticGapGraph:
    """
    动态权重图算法类，用于识别用户意图与现有认知节点之间的语义鸿沟。
    
    该类实现了一个基于向量相似度和图拓扑结构的混合算法。它不进行简单的
    关键词匹配，而是通过计算向量空间中的距离，结合节点的连接度（中心性），
    动态生成一个'认知缺失图谱'。
    """

    def __init__(self, existing_nodes: List[CognitiveNode], context_weight: float = 0.3):
        """
        初始化图算法实例。
        
        参数:
            existing_nodes (List[CognitiveNode]): 系统中已存在的982个认知节点。
            context_weight (float): 上下文（图拓扑结构）在权重计算中的比重 (0.0-1.0)。
        
        Raises:
            ValueError: 如果节点列表为空或参数范围无效。
        """
        if not existing_nodes:
            logger.error("初始化失败：认知节点列表不能为空。")
            raise ValueError("认知节点列表不能为空。")
        
        if not 0.0 <= context_weight <= 1.0:
            logger.error(f"无效的上下文权重: {context_weight}")
            raise ValueError("context_weight 必须在 0.0 和 1.0 之间。")

        self.nodes = {node.node_id: node for node in existing_nodes}
        self.context_weight = context_weight
        self.semantic_weight = 1.0 - context_weight
        logger.info(f"SemanticGapGraph 初始化完成，加载了 {len(self.nodes)} 个节点。")

    def _validate_vector(self, vector: np.ndarray, vector_name: str) -> None:
        """
        辅助函数：验证向量的维度和数据类型。
        
        参数:
            vector (np.ndarray): 待验证的向量。
            vector_name (str): 向量名称（用于日志）。
            
        Raises:
            TypeError: 如果类型不是np.ndarray。
            ValueError: 如果维度不一致。
        """
        if not isinstance(vector, np.ndarray):
            msg = f"{vector_name} 必须是 numpy.ndarray 类型，接收到: {type(vector)}"
            logger.error(msg)
            raise TypeError(msg)
        
        # 假设所有节点具有相同的向量维度，取第一个节点作为基准
        sample_node = next(iter(self.nodes.values()))
        if vector.shape != sample_node.embedding.shape:
            msg = (f"{vector_name} 维度不匹配。期望: {sample_node.embedding.shape}, "
                   f"实际: {vector.shape}")
            logger.error(msg)
            raise ValueError(msg)

    def calculate_semantic_gaps(
        self, 
        user_intent_vector: np.ndarray, 
        top_k: int = 5
    ) -> List[Tuple[str, str, float, float]]:
        """
        核心函数一：计算用户意图与现有节点之间的语义鸿沟。
        
        该函数执行以下步骤：
        1. 验证输入向量。
        2. 遍历所有现有节点，计算余弦相似度。
        3. 识别相似度低于阈值（即差距大）但在语义空间上具有邻近性的节点。
           这里我们通过反转相似度来寻找"最不匹配"但在图结构上重要的区域，
           以此定义"需要补全的鸿沟"。
        
        参数:
            user_intent_vector (np.ndarray): 用户输入的向量化表示。
            top_k (int): 返回的最显著的语义鸿沟数量。
            
        返回:
            List[Tuple[str, str, float, float]]: 
                包含 (节点ID, 节点标签, 鸿沟得分, 基础相似度) 的列表。
                鸿沟得分越高，表示该节点与用户意图的差异越大（即潜在的关键缺失点）。
        """
        try:
            self._validate_vector(user_intent_vector, "user_intent_vector")
            logger.info("开始计算语义鸿沟...")
            
            gap_scores = []
            
            # 归一化用户向量
            user_norm = np.linalg.norm(user_intent_vector)
            if user_norm == 0:
                return [] # 避免除以零
            norm_user_vec = user_intent_vector / user_norm

            for node_id, node in self.nodes.items():
                # 计算余弦相似度 (语义距离)
                node_norm = np.linalg.norm(node.embedding)
                if node_norm == 0:
                    continue
                
                similarity = np.dot(norm_user_vec, node.embedding / node_norm)
                
                # 计算动态权重：结合节点连接数（作为重要性的代理）
                # 连接越多，该节点越核心。如果核心节点与用户意图相似度低，则是巨大的鸿沟。
                degree_centrality = len(node.connections)
                # 简单的归一化/缩放，实际场景可能需要更复杂的PageRank
                importance_factor = np.log1p(degree_centrality) 
                
                # 鸿沟得分公式:
                # (1 - 相似度) 表示差异，importance_factor 表示重要性。
                # 我们寻找的是：差异大 且 重要的节点。
                gap_score = ((1.0 - similarity) * self.semantic_weight) + \
                            (importance_factor * self.context_weight)
                
                gap_scores.append((node_id, node.label, gap_score, similarity))

            # 按鸿沟得分降序排列，得分越高代表越是"缺失的关键点"
            gap_scores.sort(key=lambda x: x[2], reverse=True)
            
            result = gap_scores[:top_k]
            logger.info(f"识别到 {len(result)} 个主要语义鸿沟。")
            return result

        except Exception as e:
            logger.exception("计算语义鸿沟时发生未预期错误。")
            raise RuntimeError(f"Gap calculation failed: {e}") from e

    def map_intent_to_missing_nodes(
        self, 
        user_input: str, 
        gaps: List[Tuple[str, str, float, float]]
    ) -> Dict[str, List[str]]:
        """
        核心函数二：将识别出的鸿沟映射为具体的缺失认知节点建议。
        
        基于识别出的最大鸿沟节点，分析其邻居，构建一个"补全路径"。
        这模拟了AGI系统思考："虽然我有这些节点，但用户可能需要连接这些节点的新知识"。
        
        参数:
            user_input (str): 原始用户输入字符串 (仅用于日志和构造提示)。
            gaps (List[Tuple...]): calculate_semantic_gaps 的输出结果。
            
        返回:
            Dict[str, List[str]]: 一个字典，键是潜在的缺失能力领域，
                                  值是相关的现有节点ID列表（作为锚点）。
        """
        if not gaps:
            return {"general_unclear": ["无法确定具体缺失节点"]}

        logger.info(f"正在为用户意图 '{user_input}' 构建缺失节点映射...")
        missing_map = {}
        
        # 选取鸿沟最大的前几个节点作为锚点
        for node_id, label, score, _ in gaps:
            # 在实际AGI场景中，这里可能会调用LLM生成新的节点概念
            # 此处我们使用规则：将 "用户意图" + "现有核心节点" 组合为缺失领域
            suggested_capability = f"enhanced_{label}_for_specific_intent"
            
            # 获取该节点的邻居作为上下文支持
            neighbors = self.nodes[node_id].connections
            
            if suggested_capability not in missing_map:
                missing_map[suggested_capability] = []
            
            # 添加当前节点及其部分邻居作为参考上下文
            missing_map[suggested_capability].append(node_id)
            missing_map[suggested_capability].extend(neighbors[:2]) # 仅取少量邻居示例
            
        return missing_map

# ================= 使用示例 =================
if __name__ == "__main__":
    # 1. 模拟生成982个认知节点 (此处仅生成10个作为演示)
    MOCK_NODE_COUNT = 10
    VECTOR_DIM = 128
    
    mock_nodes = []
    for i in range(MOCK_NODE_COUNT):
        # 模拟向量：随机生成，为了演示，让某些节点特定相似
        vec = np.random.rand(VECTOR_DIM).astype(np.float32)
        # 模拟连接
        conns = [f"node_{np.random.randint(0, MOCK_NODE_COUNT)}" for _ in range(3)]
        
        node = CognitiveNode(
            node_id=f"node_{i}",
            label=f"cognitive_concept_{i}",
            embedding=vec,
            connections=conns
        )
        mock_nodes.append(node)

    # 2. 初始化图算法
    try:
        gap_analyzer = SemanticGapGraph(existing_nodes=mock_nodes, context_weight=0.4)
    except ValueError as e:
        print(f"初始化错误: {e}")

    # 3. 模拟用户输入 ("我想优化代码")
    # 在实际应用中，这里应该使用Encoder将文本转为向量
    # 我们创建一个随机向量模拟用户输入，并手动设置它与 node_0 相似
    user_vec = np.random.rand(VECTOR_DIM).astype(np.float32)
    # 强制让 user_vec 与 node_0 相似，与 node_1 不相似
    if MOCK_NODE_COUNT > 0:
        user_vec = mock_nodes[0].embedding + np.random.normal(0, 0.1, VECTOR_DIM)

    # 4. 计算语义鸿沟
    print("--- 正在分析意图对齐情况 ---")
    identified_gaps = gap_analyzer.calculate_semantic_gaps(user_vec, top_k=3)
    
    print(f"{'节点ID':<10} | {'标签':<20} | {'鸿沟得分':<10} | {'相似度':<10}")
    print("-" * 60)
    for nid, label, score, sim in identified_gaps:
        print(f"{nid:<10} | {label:<20} | {score:.4f}     | {sim:.4f}")

    # 5. 映射到缺失节点
    print("\n--- 缺失认知节点建议 ---")
    suggestions = gap_analyzer.map_intent_to_missing_nodes(
        "我想优化代码", 
        identified_gaps
    )
    for cap, refs in suggestions.items():
        print(f"建议补全能力: {cap}")
        print(f"  参考现有节点: {refs}")