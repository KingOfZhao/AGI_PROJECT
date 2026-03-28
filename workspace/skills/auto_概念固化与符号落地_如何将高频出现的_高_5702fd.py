"""
Module: auto_concept_solidification.py
Description: 概念固化与符号落地：将高频出现的、高协方差的一组‘重叠节点’动态聚合，
             自动生成一个新的‘原子化’概念节点，并赋予其唯一的符号标识。
Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import uuid
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Any
from itertools import combinations
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class CognitiveNode:
    """
    认知节点基类，表示系统中的一个信息单元。
    """
    node_id: str
    label: str
    vector: np.ndarray
    attributes: Dict[str, Any] = field(default_factory=dict)
    connections: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if not isinstance(self.vector, np.ndarray):
            raise TypeError("Vector must be a numpy array.")
        if not isinstance(self.connections, set):
            raise TypeError("Connections must be a set of node IDs.")

@dataclass
class ConceptNode(CognitiveNode):
    """
    概念节点：由基础节点聚合而成的更高阶抽象。
    """
    source_ids: Set[str] = field(default_factory=set)  # 组成该概念的原始节点ID
    cohesion_score: float = 0.0  # 内部聚合度
    abstraction_level: int = 1   # 抽象层级

# --- 辅助函数 ---

def calculate_semantic_covariance(node_group: List[CognitiveNode], global_center: np.ndarray) -> float:
    """
    辅助函数：计算一组节点之间的语义协方差强度。
    这里使用简化的统计模型：计算组内向量与全局中心的协方差矩阵的平均迹，
    并结合组内平均余弦相似度来模拟‘重叠度’。

    Args:
        node_group (List[CognitiveNode]): 待计算的节点列表。
        global_center (np.ndarray): 全局语义空间的中心点向量。

    Returns:
        float: 协方差强度得分 (0.0 到 1.0)。

    Raises:
        ValueError: 如果节点列表为空或向量维度不一致。
    """
    if not node_group:
        raise ValueError("Node group cannot be empty.")
    
    vectors = np.array([node.vector for node in node_group])
    
    # 检查维度一致性
    if vectors.shape[1] != global_center.shape[0]:
        raise ValueError("Vector dimensions mismatch with global center.")

    # 1. 计算相对于全局中心的协方差（表示该组节点共同偏离中心的程度）
    # 这里简化为计算组内向量的方差均值，方差越小且方向越一致，协方差得分越高
    centered_vectors = vectors - global_center
    cov_matrix = np.cov(centered_vectors, rowvar=False)
    # 取协方差矩阵的Frobenius范数作为总体的协方差强度指标
    cov_strength = np.linalg.norm(cov_matrix, 'fro')
    
    # 2. 计算组内余弦相似度（模拟语义重叠）
    # 如果节点完全重叠，相似度接近1
    similarity_sum = 0
    count = 0
    for v1, v2 in combinations(vectors, 2):
        norm_prod = np.linalg.norm(v1) * np.linalg.norm(v2)
        if norm_prod == 0:
            continue
        cos_sim = np.dot(v1, v2) / norm_prod
        similarity_sum += cos_sim
        count += 1
    
    avg_similarity = similarity_sum / count if count > 0 else 1.0
    
    # 归一化处理 (简单的Sigmoid映射模拟非线性激活)
    # 实际AGI中可能使用更复杂的能量函数
    final_score = 1 / (1 + np.exp(- (avg_similarity * 10 - 5))) 
    
    logger.debug(f"Calculated covariance score: {final_score:.4f}")
    return final_score

# --- 核心逻辑类 ---

class ConceptSolidificationEngine:
    """
    概念固化引擎。
    负责监控高频共现节点，计算协方差，并在满足条件时生成新的原子化概念符号。
    """

    def __init__(self, vector_dim: int = 128, merge_threshold: float = 0.85):
        """
        初始化引擎。

        Args:
            vector_dim (int): 语义向量的维度。
            merge_threshold (float): 聚合固化的阈值（0-1）。
        """
        self.vector_dim = vector_dim
        self.merge_threshold = merge_threshold
        self.node_registry: Dict[str, CognitiveNode] = {}
        self.global_center = np.zeros(vector_dim) # 简化：假设原点为中心，实际应动态维护
        logger.info(f"ConceptSolidificationEngine initialized with dim={vector_dim}, threshold={merge_threshold}")

    def register_node(self, node: CognitiveNode) -> None:
        """注册节点到引擎中。"""
        if node.vector.shape[0] != self.vector_dim:
            raise ValueError(f"Invalid vector dimension. Expected {self.vector_dim}, got {node.vector.shape[0]}")
        self.node_registry[node.node_id] = node
        logger.debug(f"Node {node.node_id} registered.")

    def _generate_symbol_id(self, source_ids: Set[str]) -> str:
        """
        内部方法：根据源节点ID生成唯一的符号标识。
        使用哈希确保相同组合生成相同ID，模拟概念的稳定性。
        """
        sorted_ids = "".join(sorted(list(source_ids)))
        hash_digest = hashlib.md5(sorted_ids.encode()).hexdigest()[:8]
        return f"CONCEPT_{hash_digest}"

    def aggregate_overlapping_nodes(self, candidate_ids: List[str]) -> Optional[ConceptNode]:
        """
        核心函数 1: 尝试将一组候选节点聚合为一个概念。
        
        流程：
        1. 验证节点存在性。
        2. 计算语义协方差。
        3. 如果协方差 > 阈值，生成新概念节点。
        4. 计算新概念的向量（加权平均或AutoEncoder，此处用平均）。
        5. 赋予符号。

        Args:
            candidate_ids (List[str]): 候选节点ID列表。

        Returns:
            Optional[ConceptNode]: 如果固化成功返回新节点，否则返回None。
        """
        if len(candidate_ids) < 2:
            logger.warning("Aggregation requires at least 2 nodes.")
            return None

        nodes = []
        for nid in candidate_ids:
            if nid not in self.node_registry:
                logger.error(f"Node ID {nid} not found in registry.")
                return None
            nodes.append(self.node_registry[nid])

        try:
            covariance_score = calculate_semantic_covariance(nodes, self.global_center)
        except Exception as e:
            logger.error(f"Error calculating covariance: {e}")
            return None

        if covariance_score >= self.merge_threshold:
            logger.info(f"High covariance detected ({covariance_score:.4f}). Solidifying concept...")
            
            # 生成新向量（质心）
            new_vector = np.mean([n.vector for n in nodes], axis=0)
            
            # 生成符号
            new_id = self._generate_symbol_id(set(candidate_ids))
            
            # 检查是否已存在
            if new_id in self.node_registry:
                logger.info(f"Concept {new_id} already exists. Reinforcing connections.")
                return self.node_registry[new_id]

            # 创建新概念节点
            new_concept = ConceptNode(
                node_id=new_id,
                label=f"AutoConcept_{new_id[:8]}",
                vector=new_vector,
                source_ids=set(candidate_ids),
                cohesion_score=covariance_score,
                abstraction_level=2 # 假设基础节点是Level 1
            )
            
            # 更新连接关系
            for node in nodes:
                node.connections.add(new_id)
                new_concept.connections.add(node.node_id)

            self.node_registry[new_id] = new_concept
            logger.info(f"NEW CONCEPT CREATED: {new_id} from sources: {candidate_ids}")
            return new_concept
        
        else:
            logger.debug(f"Covariance {covariance_score:.4f} below threshold. No solidification.")
            return None

    def ground_concept_to_symbol(self, concept_node: ConceptNode, symbolic_label: str = None) -> Dict[str, Any]:
        """
        核心函数 2: 符号落地。
        将抽象的概念节点映射到具体的符号标识，使其可被系统其他部分引用。
        
        Args:
            concept_node (ConceptNode): 需要落地的概念节点。
            symbolic_label (str, optional): 自定义符号名。如果为空则自动生成。

        Returns:
            Dict[str, Any]: 包含落地信息的元数据字典。
        """
        if concept_node.node_id not in self.node_registry:
            raise ValueError("Concept node is not registered in the engine.")

        label = symbolic_label if symbolic_label else concept_node.label
        
        # 模拟落地过程：生成JSON-LD风格的表达
        grounding_metadata = {
            "@context": "http://agi-system/core/v1",
            "@id": concept_node.node_id,
            "@type": "AtomicConcept",
            "label": label,
            "vector_signature": hashlib.sha256(concept_node.vector.tobytes()).hexdigest(),
            "grounded_timestamp": str(uuid.uuid1()), # 模拟时间戳
            "source_complexity": len(concept_node.source_ids),
            "is_solidified": True
        }

        # 更新节点属性
        concept_node.attributes['grounding'] = grounding_metadata
        concept_node.label = label
        
        logger.info(f"Concept grounded: {concept_node.node_id} -> '{label}'")
        return grounding_metadata

# --- 使用示例与测试 ---

def run_demo():
    """
    演示如何使用ConceptSolidificationEngine进行概念固化。
    """
    print("\n=== AGI Concept Solidification Demo ===\n")
    
    # 1. 初始化引擎
    engine = ConceptSolidificationEngine(vector_dim=64, merge_threshold=0.75)
    
    # 2. 模拟一组高频共现、语义重叠的节点（例如：'苹果', '红色', '水果', '甜味'）
    # 在向量空间中，它们应该比较接近
    base_vector = np.random.rand(64)
    
    node_apple = CognitiveNode(
        node_id="node_1", 
        label="apple_instance", 
        vector=base_vector + np.random.normal(0, 0.01, 64)
    )
    node_red = CognitiveNode(
        node_id="node_2", 
        label="red_color", 
        vector=base_vector + np.random.normal(0, 0.01, 64)
    )
    node_fruit = CognitiveNode(
        node_id="node_3", 
        label="fruit_category", 
        vector=base_vector + np.random.normal(0, 0.02, 64)
    )
    
    # 3. 注册节点
    engine.register_node(node_apple)
    engine.register_node(node_red)
    engine.register_node(node_fruit)
    
    # 4. 尝试聚合 (高协方差组)
    print("Attempting to aggregate high-covariance nodes...")
    high_cov_group = ["node_1", "node_2", "node_3"]
    new_concept = engine.aggregate_overlapping_nodes(high_cov_group)
    
    if new_concept:
        print(f"Success! Concept formed: {new_concept.node_id}")
        
        # 5. 符号落地
        print("Grounding concept to symbol 'RED_FRUIT_OBJECT'...")
        metadata = engine.ground_concept_to_symbol(new_concept, "RED_FRUIT_OBJECT")
        print(f"Grounding Metadata: {json.dumps(metadata, indent=2)}")
    
    # 6. 尝试聚合不相关的节点
    print("\nAttempting to aggregate unrelated nodes...")
    unrelated_node = CognitiveNode(
        node_id="node_4", 
        label="car_engine", 
        vector=np.random.rand(64) * 10 # 完全不同的向量
    )
    engine.register_node(unrelated_node)
    
    fail_concept = engine.aggregate_overlapping_nodes(["node_1", "node_4"])
    if not fail_concept:
        print("Correctly rejected low-covariance aggregation.")

if __name__ == "__main__":
    run_demo()