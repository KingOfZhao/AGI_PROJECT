"""
Module: auto_左右跨域_重叠层_实现跨域概念映射的自_1f970d
Domain: transfer_learning
Description: 
    该模块实现了跨域概念映射的自动化验证与元认知节点的生成。
    它通过计算两个领域（如'编程调试'与'烹饪调味'）之间的结构同构性，
    识别深层的通用模式（如'微量修改-反馈-迭代'循环），并将这种重叠
    固化为一个新的元认知节点，以支持AGI系统的迁移学习能力。

Input Format:
    Domain objects containing lists of ConceptNodes and Relations.
    
Output Format:
    A MetaCognitiveNode object representing the abstracted common pattern,
    along with a similarity score.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RelationType(Enum):
    """定义关系类型的枚举，用于标准化边类型。"""
    CAUSES = "causes"
    REQUIRES = "requires"
    MODIFIES = "modifies"
    EVALUATES = "evaluates"
    FEEDBACK = "feedback"


@dataclass
class ConceptNode:
    """表示领域内的一个概念节点。"""
    id: str
    label: str
    attributes: Dict[str, str] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, ConceptNode):
            return False
        return self.id == other.id


@dataclass
class Relation:
    """表示节点之间的关系。"""
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0


@dataclass
class Domain:
    """表示一个知识领域。"""
    name: str
    nodes: List[ConceptNode]
    relations: List[Relation]


@dataclass
class MetaCognitiveNode:
    """表示从跨域映射中提取的元认知节点。"""
    id: str
    name: str
    abstraction_pattern: str
    source_domains: List[str]
    similarity_score: float
    description: str


def validate_domain(domain: Domain) -> None:
    """
    辅助函数：验证领域数据的完整性和一致性。
    
    Args:
        domain: 待验证的领域对象。
        
    Raises:
        ValueError: 如果节点ID重复或关系引用了不存在的节点。
    """
    if not domain.nodes:
        logger.warning(f"Domain '{domain.name}' has no nodes.")
        return

    node_ids = {node.id for node in domain.nodes}
    if len(node_ids) != len(domain.nodes):
        raise ValueError(f"Domain '{domain.name}' contains duplicate node IDs.")

    for rel in domain.relations:
        if rel.source_id not in node_ids:
            raise ValueError(f"Relation source '{rel.source_id}' not found in domain '{domain.name}'.")
        if rel.target_id not in node_ids:
            raise ValueError(f"Relation target '{rel.target_id}' not found in domain '{domain.name}'.")
    
    logger.info(f"Domain '{domain.name}' validated successfully.")


def _calculate_structural_signature(domain: Domain) -> Dict[str, Set[Tuple[str, str, str]]]:
    """
    内部辅助函数：计算领域的结构签名。
    将图结构转换为三元组集合 (source_type, edge_type, target_type) 的抽象表示。
    
    Args:
        domain: 输入领域。
        
    Returns:
        包含结构三元组的字典。
    """
    node_map = {node.id: node.label for node in domain.nodes}
    signatures = set()
    
    for rel in domain.relations:
        source_label = node_map.get(rel.source_id, "Unknown")
        target_label = node_map.get(rel.target_id, "Unknown")
        # 使用标签和关系类型作为签名特征
        sig = (source_label, rel.relation_type.value, target_label)
        signatures.add(sig)
        
    return {"triples": signatures}


def calculate_isomorphism(domain_a: Domain, domain_b: Domain) -> float:
    """
    核心函数 1：计算两个领域之间的同构性分数。
    使用Jaccard相似度比较两个领域的结构签名。
    
    Args:
        domain_a: 第一个领域（例如：编程调试）。
        domain_b: 第二个领域（例如：烹饪调味）。
        
    Returns:
        0.0 到 1.0 之间的相似度分数。
        
    Raises:
        ValueError: 如果输入数据无效。
    """
    try:
        validate_domain(domain_a)
        validate_domain(domain_b)
        
        sig_a = _calculate_structural_signature(domain_a)["triples"]
        sig_b = _calculate_structural_signature(domain_b)["triples"]
        
        if not sig_a and not sig_b:
            return 1.0  # 两个空域视为相同
        if not sig_a or not sig_b:
            return 0.0
            
        intersection = sig_a.intersection(sig_b)
        union = sig_a.union(sig_b)
        
        similarity = len(intersection) / len(union)
        
        logger.info(f"Calculated isomorphism between '{domain_a.name}' and '{domain_b.name}': {similarity:.4f}")
        return similarity
        
    except Exception as e:
        logger.error(f"Error calculating isomorphism: {e}")
        raise


def solidify_meta_cognitive_node(domain_a: Domain, domain_b: Domain, threshold: float = 0.3) -> Optional[MetaCognitiveNode]:
    """
    核心函数 2：利用跨域重叠固化为一个新的元认知节点。
    如果相似度超过阈值，则提取共同模式并生成元节点。
    
    Args:
        domain_a: 源领域 A。
        domain_b: 源领域 B。
        threshold: 生成元节点的最小相似度阈值。
        
    Returns:
        MetaCognitiveNode 对象，如果相似度不足则返回 None。
    """
    try:
        score = calculate_isomorphism(domain_a, domain_b)
        
        if score < threshold:
            logger.info(f"Similarity {score:.2f} below threshold {threshold}. No meta-node generated.")
            return None
            
        # 提取共同模式
        sig_a = _calculate_structural_signature(domain_a)["triples"]
        sig_b = _calculate_structural_signature(domain_b)["triples"]
        common_patterns = sig_a.intersection(sig_b)
        
        # 生成抽象描述
        pattern_desc = " & ".join([f"{p[0]}-{p[1]}-{p[2]}" for p in common_patterns])
        
        # 生成唯一ID
        hash_input = f"{domain_a.name}_{domain_b.name}_{pattern_desc}".encode('utf-8')
        node_id = hashlib.md5(hash_input).hexdigest()[:8]
        
        meta_node = MetaCognitiveNode(
            id=f"meta_{node_id}",
            name=f"Abstracted_{domain_a.name}_To_{domain_b.name}",
            abstraction_pattern=pattern_desc,
            source_domains=[domain_a.name, domain_b.name],
            similarity_score=score,
            description=f"Derived from the structural overlap between {domain_a.name} and {domain_b.name}. "
                        f"Core logic: {pattern_desc}"
        )
        
        logger.info(f"Successfully generated MetaCognitiveNode: {meta_node.name}")
        return meta_node
        
    except Exception as e:
        logger.error(f"Failed to solidify meta-cognitive node: {e}")
        return None


# Example Usage
if __name__ == "__main__":
    # 定义领域 1: 编程调试
    # 结构: 代码 -> (导致) -> Bug -> (需要) -> 修复 -> (修改) -> 代码
    coding_nodes = [
        ConceptNode("c1", "SourceCode"),
        ConceptNode("c2", "Bug"),
        ConceptNode("c3", "Fix")
    ]
    coding_relations = [
        Relation("c1", "c2", RelationType.CAUSES),
        Relation("c2", "c3", RelationType.REQUIRES),
        Relation("c3", "c1", RelationType.MODIFIES)
    ]
    domain_coding = Domain("ProgrammingDebugging", coding_nodes, coding_relations)

    # 定义领域 2: 烹饪调味
    # 结构: 汤底 -> (导致) -> 咸味 -> (需要) -> 加水/调料 -> (修改) -> 汤底
    # 为了演示同构性，我们映射标签到类似的抽象概念，或者让算法发现结构相似性
    # 这里我们构建一个结构同构的图
    cooking_nodes = [
        ConceptNode("k1", "SoupBase"),
        ConceptNode("k2", "SaltyTaste"),
        ConceptNode("k3", "Seasoning")
    ]
    cooking_relations = [
        Relation("k1", "k2", RelationType.CAUSES),
        Relation("k2", "k3", RelationType.REQUIRES),
        Relation("k3", "k1", RelationType.MODIFIES)
    ]
    domain_cooking = Domain("CookingSeasoning", cooking_nodes, cooking_relations)

    # 执行跨域映射
    try:
        # 1. 计算同构性
        similarity = calculate_isomorphism(domain_coding, domain_cooking)
        print(f"Isomorphism Score: {similarity:.2f}")

        # 2. 固化元认知节点
        meta_node = solidify_meta_cognitive_node(domain_coding, domain_cooking)
        
        if meta_node:
            print("\n--- Meta Cognitive Node Generated ---")
            print(f"ID: {meta_node.id}")
            print(f"Name: {meta_node.name}")
            print(f"Description: {meta_node.description}")
            print(f"Pattern: {meta_node.abstraction_pattern}")
            print(f"Score: {meta_node.similarity_score}")
        else:
            print("No significant pattern found to abstract.")
            
    except Exception as e:
        print(f"Error in execution: {e}")