"""
模块: semantic_linking_engine
描述: 实现基于语义相似度的自动链接机制，用于动态构建认知网络。
作者: Senior Python Engineer
版本: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型别名
NodeID = str
EmbeddingVector = np.ndarray
ContextState = Dict[str, float]

@dataclass
class CognitiveNode:
    """
    认知网络中的节点数据结构。
    
    属性:
        id: 节点的唯一标识符
        content: 节点的文本或数据内容
        embedding: 节点的语义向量表示 (维度通常为128, 256, 768等)
        context_weight: 当前上下文状态下的动态权重
        created_at: 创建时间戳
    """
    id: NodeID
    content: str
    embedding: Optional[EmbeddingVector] = None
    context_weight: float = 1.0
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        """数据验证"""
        if not self.id:
            raise ValueError("Node ID cannot be empty")
        if self.embedding is not None and not isinstance(self.embedding, np.ndarray):
            raise TypeError("Embedding must be a numpy array")

@dataclass
class NetworkEdge:
    """
    网络边的数据结构。
    
    属性:
        source: 源节点ID
        target: 目标节点ID
        weight: 边的权重，范围[0, 1]
        decay_factor: 时间衰减因子
    """
    source: NodeID
    target: NodeID
    weight: float = 0.0
    decay_factor: float = 0.99

class SemanticLinkingEngine:
    """
    核心引擎：基于语义相似度和上下文关联强度自动建立链接。
    
    该类负责维护认知图谱，计算节点间的语义相似度，
    并根据当前的上下文状态动态调整边的权重。
    """
    
    def __init__(self, similarity_threshold: float = 0.75, max_edges_per_node: int = 10):
        """
        初始化链接引擎。
        
        参数:
            similarity_threshold: 建立链接的最低相似度阈值
            max_edges_per_node: 单个节点允许的最大边数（防止爆炸）
        """
        self.nodes: Dict[NodeID, CognitiveNode] = {}
        self.edges: Dict[Tuple[NodeID, NodeID], NetworkEdge] = {}
        self.global_context: ContextState = {}  # 存储全局上下文关键词及强度
        
        # 参数校验
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0 and 1")
        if max_edges_per_node < 1:
            raise ValueError("Max edges per node must be at least 1")
            
        self.similarity_threshold = similarity_threshold
        self.max_edges_per_node = max_edges_per_node
        logger.info(f"SemanticLinkingEngine initialized with threshold {similarity_threshold}")

    def _cosine_similarity(self, vec_a: EmbeddingVector, vec_b: EmbeddingVector) -> float:
        """
        [辅助函数] 计算两个向量之间的余弦相似度。
        
        参数:
            vec_a: 向量A
            vec_b: 向量B
            
        返回:
            相似度得分，范围[-1, 1]，通常在语义空间中为[0, 1]
        """
        if vec_a is None or vec_b is None:
            return 0.0
        
        # 边界检查：维度必须一致
        if vec_a.shape != vec_b.shape:
            logger.warning(f"Dimension mismatch: {vec_a.shape} vs {vec_b.shape}")
            return 0.0

        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def _calculate_dynamic_weight(self, base_similarity: float, context_boost: float) -> float:
        """
        [辅助函数] 计算综合动态权重。
        
        公式: Weight = Base_Similarity * (1 + Context_Boost_Factor)
        
        参数:
            base_similarity: 基础语义相似度
            context_boost: 基于当前上下文的加成系数
            
        返回:
            最终的边权重
        """
        raw_weight = base_similarity * (1 + context_boost)
        return min(max(raw_weight, 0.0), 1.0)  # Clamp to [0, 1]

    def update_global_context(self, keywords: Dict[str, float]):
        """
        更新全局上下文状态。这会影响后续链接的权重计算。
        
        参数:
            keywords: 包含关键词及其当前相关性的字典
        """
        self.global_context = keywords
        logger.debug(f"Context updated with {len(keywords)} keywords")

    def add_node(self, node: CognitiveNode) -> bool:
        """
        添加新节点到认知网络。
        
        参数:
            node: 要添加的节点对象
            
        返回:
            是否添加成功
        """
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists. Update skipped.")
            return False
            
        self.nodes[node.id] = node
        logger.info(f"Node added: {node.id}")
        return True

    def auto_link_node(self, candidate_node: CognitiveNode) -> List[NetworkEdge]:
        """
        [核心函数 1] 自动链接机制。
        
        将新节点与现有网络中的节点进行比对，基于语义相似度建立边。
        同时会考虑当前的全局上下文。
        
        参数:
            candidate_node: 待链接的候选节点
            
        返回:
            新建立的边的列表
        """
        if candidate_node.embedding is None:
            logger.error(f"Node {candidate_node.id} has no embedding, cannot link.")
            return []

        # 确保节点已在网络中（或临时加入计算）
        if candidate_node.id not in self.nodes:
            self.add_node(candidate_node)

        new_edges: List[NetworkEdge] = []
        candidate_edges_count = 0

        # 遍历现有节点计算相似度
        for existing_id, existing_node in self.nodes.items():
            if existing_id == candidate_node.id:
                continue

            # 1. 计算基础语义相似度
            similarity = self._cosine_similarity(candidate_node.embedding, existing_node.embedding)
            
            if similarity < self.similarity_threshold:
                continue

            # 2. 计算上下文加成 (简单模拟：如果节点内容包含上下文关键词)
            context_boost = 0.0
            for keyword, strength in self.global_context.items():
                if keyword in existing_node.content:
                    context_boost += strength * 0.1  # 简单线性叠加

            # 3. 计算最终权重
            final_weight = self._calculate_dynamic_weight(similarity, context_boost)

            # 4. 创建边
            edge = NetworkEdge(
                source=candidate_node.id,
                target=existing_id,
                weight=final_weight
            )
            
            # 双向存储（无向图假设）
            self.edges[(candidate_node.id, existing_id)] = edge
            new_edges.append(edge)
            candidate_edges_count += 1

            if candidate_edges_count >= self.max_edges_per_node:
                logger.info(f"Reached max edges limit for node {candidate_node.id}")
                break
        
        logger.info(f"Auto-linking complete for {candidate_node.id}. Created {len(new_edges)} edges.")
        return new_edges

    def reinforce_edges(self, active_node_ids: List[NodeID], reinforcement_rate: float = 0.05):
        """
        [核心函数 2] 动态权重更新机制。
        
        根据节点在当前上下文中的活跃度，动态调整相关边的权重。
        这模拟了Hebbian学习规则：同时激活的节点连接更强。
        如果边长时间未被激活，其权重会衰减。
        
        参数:
            active_node_ids: 当前处于活跃状态的节点ID列表
            reinforcement_rate: 权重增加的速率
        """
        active_set = set(active_node_ids)
        
        for key, edge in list(self.edges.items()):
            source, target = key
            
            # 检查边是否连接了活跃节点
            is_source_active = source in active_set
            is_target_active = target in active_set
            
            current_weight = edge.weight
            
            if is_source_active and is_target_active:
                # 双向激活：显著增强
                edge.weight = min(1.0, current_weight + reinforcement_rate * 1.5)
                # 重置衰减（可选）
                edge.decay_factor = 0.995 
            elif is_source_active or is_target_active:
                # 单向激活：轻微增强
                edge.weight = min(1.0, current_weight + reinforcement_rate * 0.5)
            else:
                # 未激活：权重衰减
                edge.weight = current_weight * edge.decay_factor
                
            # 边界检查：权重过低则移除边
            if edge.weight < 0.1:
                del self.edges[key]
                logger.debug(f"Edge removed due to low weight: {source}-{target}")

        logger.info(f"Edge dynamics updated. Total edges: {len(self.edges)}")

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化引擎
    try:
        engine = SemanticLinkingEngine(similarity_threshold=0.5, max_edges_per_node=5)
    except ValueError as e:
        print(f"Initialization Error: {e}")
        exit(1)

    # 2. 模拟数据 (通常这些向量来自于BERT/OpenAI等Embedding模型)
    # 这里我们使用随机向量模拟 256 维语义向量
    def get_random_embedding():
        return np.random.rand(256)

    # 3. 创建现有节点
    node_1 = CognitiveNode(id="cat", content="feline animal", embedding=get_random_embedding())
    node_2 = CognitiveNode(id="dog", content="canine animal", embedding=get_random_embedding())
    
    # 为了演示相似度，我们让node_3的向量接近node_1
    vec_base = get_random_embedding()
    node_3 = CognitiveNode(id="tiger", content="big cat", embedding=vec_base)
    
    # 将现有节点加入引擎
    engine.add_node(node_1)
    engine.add_node(node_2)
    
    # 4. 设置上下文：我们在讨论"animal"
    engine.update_global_context({"animal": 1.0, "zoo": 0.5})

    # 5. 自动链接新节点 (Tiger)
    # 稍微修改向量以模拟相似但不完全相同
    node_3.embedding = vec_base + np.random.normal(0, 0.1, 256) 
    new_edges = engine.auto_link_node(node_3)
    
    print(f"\nCreated Edges for {node_3.id}:")
    for edge in new_edges:
        print(f" - Connects to {edge.target} with weight {edge.weight:.4f}")

    # 6. 动态强化
    # 假设 "cat" 和 "tiger" 在当前交互中被激活
    engine.reinforce_edges(active_node_ids=["cat", "tiger"])
    
    # 7. 验证最终权重
    print("\nFinal Edge Status:")
    for key, edge in engine.edges.items():
        print(f"Edge {key}: Weight {edge.weight:.4f}")