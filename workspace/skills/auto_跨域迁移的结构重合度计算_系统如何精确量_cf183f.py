"""
模块: auto_跨域迁移的结构重合度计算_系统如何精确量_cf183f
描述: 实现基于认知几何的跨域结构重合度计算。
"""

import logging
import math
from typing import Dict, List, Tuple, Optional, Set

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Node:
    """
    表示认知结构中的节点。
    """
    def __init__(self, node_id: str, attributes: Dict[str, float]):
        """
        初始化节点。
        
        Args:
            node_id: 节点唯一标识符
            attributes: 节点属性字典，键为属性名，值为属性值
        """
        if not node_id:
            raise ValueError("Node ID cannot be empty")
        if not attributes:
            raise ValueError("Node must have at least one attribute")
            
        self.id = node_id
        self.attributes = attributes
        
    def get_attribute(self, name: str) -> Optional[float]:
        """获取节点属性值"""
        return self.attributes.get(name)
    
    def attribute_names(self) -> Set[str]:
        """获取所有属性名称"""
        return set(self.attributes.keys())

class Edge:
    """
    表示认知结构中的边（关系）。
    """
    def __init__(self, source: str, target: str, weight: float, relation_type: str):
        """
        初始化边。
        
        Args:
            source: 源节点ID
            target: 目标节点ID
            weight: 边权重
            relation_type: 关系类型
        """
        if not source or not target:
            raise ValueError("Source and target cannot be empty")
        if weight <= 0:
            raise ValueError("Weight must be positive")
            
        self.source = source
        self.target = target
        self.weight = weight
        self.relation_type = relation_type

class CognitiveStructure:
    """
    表示一个认知结构（如概念、理论等）。
    """
    def __init__(self, name: str):
        """
        初始化认知结构。
        
        Args:
            name: 结构名称
        """
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        
    def add_node(self, node: Node) -> None:
        """添加节点"""
        if node.id in self.nodes:
            logger.warning(f"Node {node.id} already exists, will be overwritten")
        self.nodes[node.id] = node
        
    def add_edge(self, edge: Edge) -> None:
        """添加边"""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError("Source or target node does not exist")
        self.edges.append(edge)
        
    def get_node(self, node_id: str) -> Optional[Node]:
        """获取节点"""
        return self.nodes.get(node_id)
    
    def get_edges_by_node(self, node_id: str) -> List[Edge]:
        """获取与指定节点相关的所有边"""
        return [e for e in self.edges if e.source == node_id or e.target == node_id]

def calculate_attribute_similarity(attr1: Dict[str, float], attr2: Dict[str, float]) -> float:
    """
    辅助函数：计算两个属性字典的相似度。
    
    使用余弦相似度计算。
    
    Args:
        attr1: 第一个属性字典
        attr2: 第二个属性字典
        
    Returns:
        相似度分数 [0, 1]
    """
    # 找出共同的属性
    common_attrs = set(attr1.keys()) & set(attr2.keys())
    if not common_attrs:
        return 0.0
    
    # 计算点积和模
    dot_product = 0.0
    norm1 = 0.0
    norm2 = 0.0
    
    for attr in common_attrs:
        val1 = attr1[attr]
        val2 = attr2[attr]
        dot_product += val1 * val2
        norm1 += val1 ** 2
        norm2 += val2 ** 2
        
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (math.sqrt(norm1) * math.sqrt(norm2))

def calculate_structural_overlap(
    structure1: CognitiveStructure, 
    structure2: CognitiveStructure,
    node_mapping: Dict[str, str],
    alpha: float = 0.5,
    beta: float = 0.5
) -> Tuple[float, Dict[str, float]]:
    """
    核心函数：计算两个认知结构之间的结构重合度。
    
    使用加权组合计算节点相似度和边结构相似度。
    
    Args:
        structure1: 第一个认知结构
        structure2: 第二个认知结构
        node_mapping: 节点映射字典 {structure1_node_id: structure2_node_id}
        alpha: 节点相似度权重
        beta: 边结构相似度权重
        
    Returns:
        tuple: (总相似度分数, 详细指标字典)
    """
    if not node_mapping:
        raise ValueError("Node mapping cannot be empty")
    
    if alpha + beta != 1.0:
        logger.warning("Alpha and beta should sum to 1.0 for proper weighting")
    
    # 1. 计算节点相似度
    node_similarity_scores = []
    for node1_id, node2_id in node_mapping.items():
        node1 = structure1.get_node(node1_id)
        node2 = structure2.get_node(node2_id)
        
        if not node1 or not node2:
            logger.warning(f"Node mapping contains invalid IDs: {node1_id} -> {node2_id}")
            continue
            
        sim = calculate_attribute_similarity(node1.attributes, node2.attributes)
        node_similarity_scores.append(sim)
    
    if not node_similarity_scores:
        node_similarity = 0.0
    else:
        node_similarity = sum(node_similarity_scores) / len(node_similarity_scores)
    
    # 2. 计算边结构相似度
    edge_similarity_scores = []
    for node1_id, node2_id in node_mapping.items():
        edges1 = structure1.get_edges_by_node(node1_id)
        edges2 = structure2.get_edges_by_node(node2_id)
        
        if not edges1 and not edges2:
            continue
            
        # 计算边权重分布相似度
        weights1 = [e.weight for e in edges1]
        weights2 = [e.weight for e in edges2]
        
        # 简单相似度计算：比较平均权重
        avg1 = sum(weights1) / len(weights1) if weights1 else 0
        avg2 = sum(weights2) / len(weights2) if weights2 else 0
        
        if avg1 == 0 and avg2 == 0:
            edge_sim = 1.0
        elif avg1 == 0 or avg2 == 0:
            edge_sim = 0.0
        else:
            edge_sim = 1.0 - abs(avg1 - avg2) / max(avg1, avg2)
            
        edge_similarity_scores.append(edge_sim)
    
    if not edge_similarity_scores:
        edge_similarity = 0.0
    else:
        edge_similarity = sum(edge_similarity_scores) / len(edge_similarity_scores)
    
    # 3. 计算总相似度
    total_similarity = alpha * node_similarity + beta * edge_similarity
    
    # 准备详细指标
    details = {
        "node_similarity": node_similarity,
        "edge_similarity": edge_similarity,
        "total_similarity": total_similarity,
        "mapped_nodes": len(node_mapping),
        "total_nodes_structure1": len(structure1.nodes),
        "total_nodes_structure2": len(structure2.nodes)
    }
    
    return total_similarity, details

def recommend_migration(
    similarity_score: float,
    threshold: float = 0.7,
    details: Optional[Dict[str, float]] = None
) -> Tuple[bool, str]:
    """
    核心函数：基于相似度分数推荐是否进行逻辑迁移。
    
    Args:
        similarity_score: 结构重合度分数
        threshold: 迁移阈值
        details: 详细指标字典
        
    Returns:
        tuple: (是否推荐迁移, 推荐理由)
    """
    if details is None:
        details = {}
        
    if similarity_score >= threshold:
        reason = (f"High structural overlap ({similarity_score:.2f}) indicates "
                "strong potential for logical migration.")
        if details.get("node_similarity", 0) > 0.8:
            reason += " Exceptionally strong node attribute match."
        if details.get("edge_similarity", 0) > 0.8:
            reason += " Excellent causal structure alignment."
        return True, reason
    else:
        reason = (f"Structural overlap ({similarity_score:.2f}) below threshold "
                f"({threshold}). Migration not recommended.")
        if similarity_score > threshold - 0.1:
            reason += " Consider reviewing specific mappings for potential improvements."
        return False, reason

def create_sample_structure() -> Tuple[CognitiveStructure, CognitiveStructure, Dict[str, str]]:
    """
    辅助函数：创建示例认知结构用于演示。
    
    Returns:
        tuple: (结构1, 结构2, 节点映射)
    """
    # 创建第一个结构：生物进化论
    evolution = CognitiveStructure("Biological Evolution")
    
    # 添加节点
    variation = Node("variation", {"rate": 0.8, "impact": 0.9})
    selection = Node("selection", {"strength": 0.9, "pressure": 0.85})
    inheritance = Node("inheritance", {"fidelity": 0.95, "mechanism": 0.9})
    adaptation = Node("adaptation", {"fitness": 0.9, "scope": 0.7})
    
    evolution.add_node(variation)
    evolution.add_node(selection)
    evolution.add_node(inheritance)
    evolution.add_node(adaptation)
    
    # 添加边
    evolution.add_edge(Edge("variation", "selection", 0.85, "influences"))
    evolution.add_edge(Edge("selection", "adaptation", 0.9, "leads_to"))
    evolution.add_edge(Edge("inheritance", "adaptation", 0.88, "enables"))
    
    # 创建第二个结构：产品迭代
    product_iteration = CognitiveStructure("Product Iteration")
    
    # 添加节点
    innovation = Node("innovation", {"rate": 0.75, "impact": 0.85})
    market_feedback = Node("market_feedback", {"strength": 0.85, "pressure": 0.8})
    knowledge_transfer = Node("knowledge_transfer", {"fidelity": 0.9, "mechanism": 0.85})
    product_fit = Node("product_fit", {"fitness": 0.85, "scope": 0.75})
    
    product_iteration.add_node(innovation)
    product_iteration.add_node(market_feedback)
    product_iteration.add_node(knowledge_transfer)
    product_iteration.add_node(product_fit)
    
    # 添加边
    product_iteration.add_edge(Edge("innovation", "market_feedback", 0.8, "influences"))
    product_iteration.add_edge(Edge("market_feedback", "product_fit", 0.85, "leads_to"))
    product_iteration.add_edge(Edge("knowledge_transfer", "product_fit", 0.82, "enables"))
    
    # 创建节点映射
    mapping = {
        "variation": "innovation",
        "selection": "market_feedback",
        "inheritance": "knowledge_transfer",
        "adaptation": "product_fit"
    }
    
    return evolution, product_iteration, mapping

if __name__ == "__main__":
    # 示例用法
    print("=== 认知几何结构重合度计算示例 ===")
    
    # 创建示例结构
    structure1, structure2, mapping = create_sample_structure()
    
    print(f"\n比较结构: {structure1.name} vs {structure2.name}")
    print(f"节点映射: {mapping}")
    
    # 计算结构重合度
    similarity, details = calculate_structural_overlap(
        structure1, structure2, mapping, alpha=0.6, beta=0.4
    )
    
    print("\n计算结果:")
    print(f"节点相似度: {details['node_similarity']:.4f}")
    print(f"边结构相似度: {details['edge_similarity']:.4f}")
    print(f"总结构重合度: {similarity:.4f}")
    
    # 推荐迁移
    recommend, reason = recommend_migration(similarity, threshold=0.75, details=details)
    
    print("\n迁移建议:")
    print(f"推荐迁移: {'是' if recommend else '否'}")
    print(f"理由: {reason}")
    
    # 测试低相似度情况
    print("\n=== 测试低相似度情况 ===")
    bad_mapping = {
        "variation": "product_fit",
        "selection": "knowledge_transfer",
        "inheritance": "innovation",
        "adaptation": "market_feedback"
    }
    print(f"节点映射: {bad_mapping}")
    
    similarity, details = calculate_structural_overlap(
        structure1, structure2, bad_mapping
    )
    
    print("\n计算结果:")
    print(f"节点相似度: {details['node_similarity']:.4f}")
    print(f"边结构相似度: {details['edge_similarity']:.4f}")
    print(f"总结构重合度: {similarity:.4f}")
    
    recommend, reason = recommend_migration(similarity, threshold=0.75, details=details)
    print("\n迁移建议:")
    print(f"推荐迁移: {'是' if recommend else '否'}")
    print(f"理由: {reason}")