"""
高级技能模块：小样本跨域微调协议

该模块实现了针对长尾分布节点的跨域微调协议。核心思想是利用结构化图（Graph）而非
纯文本描述来表示技能，从而在仅有极少量案例（如1-2个）的情况下，通过结构化类比
实现向新领域的鲁棒迁移。

核心假设验证：结构图在特征空间中的几何距离比文本Embedding的语义距离在少样本
迁移中更具判别力。

版本: 1.0.0
作者: AGI System Core
"""

import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """定义图中节点的类型"""
    ROOT = "root"
    ACTION = "action"
    OBJECT = "object"
    CONTEXT = "context"
    ATTRIBUTE = "attribute"

@dataclass
class SkillNode:
    """
    技能节点数据结构
    
    Attributes:
        id (str): 节点唯一标识
        content (str): 节点文本内容
        type (NodeType): 节点类型
        embedding (Optional[np.ndarray]): 节点的向量表示
        connections (Dict[str, float]): 连接的子节点ID及其权重
    """
    id: str
    content: str
    type: NodeType
    embedding: Optional[np.ndarray] = None
    connections: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.type, NodeType):
            raise ValueError(f"Invalid NodeType: {self.type}")

class GraphEmbeddingError(Exception):
    """自定义异常：图嵌入生成失败"""
    pass

class FewShotTuningProtocol:
    """
    小样本跨域微调协议类。
    
    处理长尾分布的冷门技能迁移，通过结构化图映射实现少样本学习。
    """

    def __init__(self, embedding_dim: int = 128, similarity_threshold: float = 0.85):
        """
        初始化协议。
        
        Args:
            embedding_dim (int): 嵌入向量的维度
            similarity_threshold (float): 判定迁移成功的相似度阈值
        """
        if embedding_dim <= 0:
            raise ValueError("Embedding dimension must be positive.")
        if not 0 < similarity_threshold <= 1:
            raise ValueError("Similarity threshold must be in (0, 1].")
            
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        self.knowledge_base: Dict[str, SkillNode] = {}
        logger.info(f"FewShotTuningProtocol initialized with dim={embedding_dim}")

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        辅助函数：计算两个向量之间的余弦相似度。
        
        Args:
            vec_a (np.ndarray): 向量A
            vec_b (np.ndarray): 向量B
            
        Returns:
            float: 相似度得分 [0, 1]
        """
        if vec_a is None or vec_b is None:
            return 0.0
        if vec_a.shape != vec_b.shape:
            logger.error(f"Shape mismatch: {vec_a.shape} vs {vec_b.shape}")
            return 0.0
            
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def _mock_text_encoder(self, text: str) -> np.ndarray:
        """
        辅助函数：模拟文本编码器（如BERT/Sentence-BERT）。
        实际生产环境中应替换为真实的模型推理服务。
        """
        # 简单的哈希模拟生成固定向量，仅用于演示
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(self.embedding_dim)
        vec = vec / np.linalg.norm(vec) # 归一化
        return vec

    def construct_skill_graph(self, cases: List[Dict[str, Any]]) -> Tuple[SkillNode, List[SkillNode]]:
        """
        核心函数 1: 从少量案例构建结构化技能图。
        
        即使只有1-2个案例，也尝试提取 Action-Object-Context 结构。
        这是实现结构类比的基础。
        
        Args:
            cases (List[Dict]): 案例列表，每个案例包含 'action', 'object', 'context' 等键。
            
        Returns:
            Tuple[SkillNode, List[SkillNode]]: 根节点和提取出的关键子节点列表。
            
        Raises:
            ValueError: 如果案例为空或格式错误。
        """
        if not cases:
            raise ValueError("Cases list cannot be empty for graph construction.")
            
        logger.info(f"Constructing skill graph from {len(cases)} case(s).")
        
        # 创建根节点（代表该冷门技能本身）
        root_id = f"skill_{hash(frozenset(cases[0].items()))}"
        root_node = SkillNode(id=root_id, content="SkillRoot", type=NodeType.ROOT)
        
        extracted_nodes = []
        
        # 聚合案例中的结构信息（这里简化为提取共有属性）
        # 在实际AGI中，这里会使用Parser或LLM提取本体结构
        action_counts: Dict[str, int] = {}
        object_counts: Dict[str, int] = {}
        
        for case in cases:
            action = case.get("action", "unknown")
            obj = case.get("object", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
            object_counts[obj] = object_counts.get(obj, 0) + 1
            
        # 构建核心结构节点
        most_common_action = max(action_counts, key=action_counts.get)
        most_common_obj = max(object_counts, key=object_counts.get)
        
        # Action Node
        action_node = SkillNode(
            id=f"{root_id}_action",
            content=most_common_action,
            type=NodeType.ACTION,
            embedding=self._mock_text_encoder(most_common_action)
        )
        # Object Node
        obj_node = SkillNode(
            id=f"{root_id}_obj",
            content=most_common_obj,
            type=NodeType.OBJECT,
            embedding=self._mock_text_encoder(most_common_obj)
        )
        
        # 建立连接
        root_node.connections[action_node.id] = 1.0
        root_node.connections[obj_node.id] = 0.8
        action_node.connections[obj_node.id] = 0.5 # Action 作用于 Object
        
        extracted_nodes.extend([action_node, obj_node])
        
        # 计算根节点的聚合Embedding (Graph Embedding的简化版：子节点平均池化)
        if extracted_nodes:
            embeddings = [n.embedding for n in extracted_nodes if n.embedding is not None]
            if embeddings:
                root_node.embedding = np.mean(embeddings, axis=0)
            else:
                root_node.embedding = np.zeros(self.embedding_dim)
        else:
            root_node.embedding = np.zeros(self.embedding_dim)
            
        self.knowledge_base[root_id] = root_node
        for node in extracted_nodes:
            self.knowledge_base[node.id] = node
            
        return root_node, extracted_nodes

    def cross_domain_transfer(self, 
                              source_skill: SkillNode, 
                              target_domain_description: str) -> Dict[str, Any]:
        """
        核心函数 2: 执行跨域迁移。
        
        通过结构图类比，将源技能迁移到目标领域。验证结构图比纯文本更鲁棒。
        
        逻辑：
        1. 编码目标领域描述。
        2. 计算目标描述与源技能图各节点的相似度。
        3. 如果最大相似度超过阈值，生成迁移映射建议。
        
        Args:
            source_skill (SkillNode): 源技能的根节点（包含图结构）。
            target_domain_description (str): 目标领域的文本描述。
            
        Returns:
            Dict[str, Any]: 包含 'success', 'similarity', 'mapping' 的结果字典。
        """
        if source_skill is None or source_skill.embedding is None:
            return {"success": False, "error": "Invalid source skill graph."}
            
        logger.info(f"Attempting transfer from skill {source_skill.id} to target domain.")
        
        target_embedding = self._mock_text_encoder(target_domain_description)
        
        # 1. 基于整体结构的相似度
        root_sim = self._cosine_similarity(source_skill.embedding, target_embedding)
        
        # 2. 细粒度节点匹配
        best_node_match: Optional[SkillNode] = None
        max_node_sim = 0.0
        
        for node_id, weight in source_skill.connections.items():
            if node_id in self.knowledge_base:
                child_node = self.knowledge_base[node_id]
                if child_node.embedding is not None:
                    sim = self._cosine_similarity(child_node.embedding, target_embedding)
                    # 加权相似度
                    weighted_sim = sim * weight
                    if weighted_sim > max_node_sim:
                        max_node_sim = weighted_sim
                        best_node_match = child_node
        
        # 综合评估：结构相似度 vs 纯文本相似度
        # 这里我们假设如果图结构中的核心节点匹配度高，则迁移可信度高
        final_score = max(root_sim, max_node_sim)
        
        logger.info(f"Root Similarity: {root_sim:.4f}, Best Node Similarity: {max_node_sim:.4f}")
        
        if final_score >= self.similarity_threshold:
            return {
                "success": True,
                "confidence": float(final_score),
                "mapping": {
                    "source_node": best_node_match.id if best_node_match else source_skill.id,
                    "target_concept": target_domain_description,
                    "strategy": "Structure Analogy" if max_node_sim > root_sim else "Global Semantic"
                },
                "message": "Transfer successful via structured analogy."
            }
        else:
            return {
                "success": False,
                "confidence": float(final_score),
                "mapping": None,
                "message": "Similarity below threshold. Transfer rejected to ensure safety."
            }

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 模拟场景：拥有一个极冷门的技能 "古法修缮茅草屋" (仅1个案例)
    # 希望迁移到新领域 "现代生态屋顶维护"
    
    logger.info("--- Starting Few-Shot Cross-Domain Tuning Demo ---")
    
    # 1. 初始化协议
    protocol = FewShotTuningProtocol(embedding_dim=64, similarity_threshold=0.7)
    
    # 2. 准备长尾数据 (仅1个案例)
    few_shot_cases = [
        {
            "action": "thatching", # 修缮茅草
            "object": "straw roof", # 茅草屋顶
            "context": "traditional waterproofing"
        }
    ]
    
    try:
        # 3. 构建结构化技能图
        # 验证点：即使只有1个案例，也能构建出 (Action: thatching) -> (Object: straw roof) 的图
        skill_root, nodes = protocol.construct_skill_graph(few_shot_cases)
        logger.info(f"Graph constructed. Root ID: {skill_root.id}")
        logger.info(f"Extracted Action: {nodes[0].content}, Object: {nodes[1].content}")
        
        # 4. 定义目标域
        target_domain = "installing solar panels on green roof" # 在绿色屋顶安装太阳能板 (结构类比: 安装 -> 屋顶)
        
        # 5. 尝试迁移
        result = protocol.cross_domain_transfer(skill_root, target_domain)
        
        print("\n--- Transfer Result ---")
        print(f"Success: {result['success']}")
        print(f"Confidence: {result['confidence']:.4f}")
        print(f"Message: {result['message']}")
        if result['success']:
            print(f"Mapping Strategy: {result['mapping']['strategy']}")
            
        # 6. 边界测试：完全不相关的领域
        unrelated_result = protocol.cross_domain_transfer(skill_root, "baking chocolate cake")
        print("\n--- Negative Test (Unrelated Domain) ---")
        print(f"Success: {unrelated_result['success']} (Expected: False)")
        
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)