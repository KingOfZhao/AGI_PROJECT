"""
Module: cognitive_consistency_verifier
Description: Implements a formal validator for cognitive consistency in closed-loop domains.
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import itertools
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RelationType(Enum):
    """定义节点间的关系类型"""
    SUPPORTS = "supports"        # 正向支持 (A -> B)
    CONTRADICTS = "contradicts"  # 冲突/矛盾 (A <-> -B)
    INDEPENDENT = "independent"  # 独立无关

class ConflictLevel(Enum):
    """认知冲突的严重等级"""
    CRITICAL = "critical"  # 逻辑互斥，系统崩溃风险
    WARNING = "warning"    # 资源竞争，需要权衡
    RESOLVED = "resolved"  # 已解决

@dataclass
class KnowledgeNode:
    """知识图谱中的节点实体"""
    node_id: str
    content: str
    node_type: str  # e.g., 'goal', 'constraint', 'fact'
    weight: float = 1.0  # 节点重要性权重

@dataclass
class LogicalRelation:
    """节点间的逻辑关系"""
    source_id: str
    target_id: str
    relation_type: RelationType
    condition: Optional[str] = None  # 触发条件描述

@dataclass
class CognitiveConflict:
    """检测到的认知冲突点"""
    conflict_id: str
    involved_nodes: List[str]
    description: str
    level: ConflictLevel
    resolution_hints: List[str] = field(default_factory=list)

class CognitiveConsistencyVerifier:
    """
    认知自洽性形式化验证器。
    
    针对特定领域（如'小摊贩知识'），通过遍历逻辑图谱检测
    目标冲突、资源约束违背及逻辑循环。
    
    Attributes:
        nodes (Dict[str, KnowledgeNode]): 知识节点库。
        relations (List[LogicalRelation]): 节点间的关系集合。
        verified (bool): 是否已执行验证。
    """

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.relations: List[LogicalRelation] = []
        self.verified: bool = False
        logger.info("Cognitive Consistency Verifier initialized.")

    def add_knowledge_node(self, node: KnowledgeNode) -> None:
        """添加知识节点到验证器"""
        if not node.node_id:
            raise ValueError("Node ID cannot be empty")
        self.nodes[node.node_id] = node
        logger.debug(f"Node added: {node.node_id}")

    def define_relation(self, relation: LogicalRelation) -> None:
        """定义节点间的关系"""
        if relation.source_id not in self.nodes or relation.target_id not in self.nodes:
            raise KeyError("Source or Target node ID not found in knowledge base")
        self.relations.append(relation)
        logger.debug(f"Relation defined: {relation.source_id} -> {relation.target_id}")

    def _build_adjacency_matrix(self) -> Dict[Tuple[str, str], RelationType]:
        """辅助函数：构建邻接关系矩阵以便快速查询"""
        matrix = {}
        for rel in self.relations:
            matrix[(rel.source_id, rel.target_id)] = rel.relation_type
        return matrix

    def check_internal_consistency(self, context: Optional[Dict] = None) -> List[CognitiveConflict]:
        """
        核心函数：执行认知自洽性验证。
        
        逻辑：
        1. 检查显式定义的 CONTRADICTS 关系。
        2. 检查隐式冲突（例如：两个互斥的目标被同一父节点支持）。
        3. 基于边界条件检测资源冲突。
        
        Args:
            context (Optional[Dict]): 运行时上下文，例如资源预算。
            
        Returns:
            List[CognitiveConflict]: 检测到的冲突列表。
        """
        if not self.nodes:
            logger.warning("No nodes to verify.")
            return []

        conflicts: List[CognitiveConflict] = []
        adj_matrix = self._build_adjacency_matrix()
        
        # 策略 1: 显式矛盾检测
        # 遍历所有关系，寻找类型为 CONTRADICTS 的连接
        for rel in self.relations:
            if rel.relation_type == RelationType.CONTRADICTS:
                conflict = CognitiveConflict(
                    conflict_id=f"conflict_{len(conflicts)}",
                    involved_nodes=[rel.source_id, rel.target_id],
                    description=f"Explicit contradiction between {rel.source_id} and {rel.target_id}",
                    level=ConflictLevel.CRITICAL,
                    resolution_hints=["Prioritize one node over the other", "Introduce conditional logic"]
                )
                conflicts.append(conflict)
                logger.warning(f"Conflict detected: {conflict.description}")

        # 策略 2: 目标-约束传播分析
        # 检查是否存在路径：Goal A -> Supports -> Action B -> Contradicts -> Constraint C
        # 这里简化为检查：如果两个节点同时被一个核心节点支持，但它们彼此矛盾
        all_node_ids = list(self.nodes.keys())
        for i in range(len(all_node_ids)):
            for j in range(i + 1, len(all_node_ids)):
                node_a = all_node_ids[i]
                node_b = all_node_ids[j]
                
                # 检查 A 和 B 是否具有互斥属性 (此处简化逻辑，实际需更复杂的推理)
                # 假设如果 A 是 'increase_quality' 且 B 是 'cut_cost_max'，且没有特定协调机制
                # 这里通过 _analyze_semantic_compatibility 进行检测
                is_compatible, reason = self._analyze_semantic_compatibility(node_a, node_b, context)
                if not is_compatible:
                    conflict = CognitiveConflict(
                        conflict_id=f"conflict_{len(conflicts)}",
                        involved_nodes=[node_a, node_b],
                        description=f"Implicit cognitive dissonance: {reason}",
                        level=ConflictLevel.WARNING,
                        resolution_hints=["Rebalance resource allocation", "Modify target thresholds"]
                    )
                    conflicts.append(conflict)
                    logger.info(f"Potential dissonance found between {node_a} and {node_b}")

        self.verified = True
        return conflicts

    def _analyze_semantic_compatibility(self, node_id_a: str, node_id_b: str, context: Optional[Dict]) -> Tuple[bool, str]:
        """
        辅助函数：语义兼容性分析。
        
        模拟针对'小摊贩领域'的特定逻辑规则。
        在真实AGI场景中，这里会调用向量数据库或LLM进行推理。
        """
        node_a = self.nodes[node_id_a]
        node_b = self.nodes[node_id_b]

        # 规则示例：如果节点是Goal类型，且内容包含特定关键词
        # 这是一个简化的形式化验证逻辑示例
        if node_a.node_type == 'goal' and node_b.node_type == 'goal':
            # 假设我们有关于资源限制的上下文
            if context and 'budget' in context:
                # 模拟：提高质量通常需要预算，降低成本限制预算
                # 这里仅作演示，实际需依赖知识图谱的属性推理
                if ("quality" in node_a.content.lower() and "cost" in node_b.content.lower() and "reduce" in node_b.content.lower()):
                    if context['budget'] < 1000: # 假设的低预算阈值
                        return (False, "Resource scarcity makes high quality and cost cutting mutually exclusive")
        
        return (True, "Compatible")

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 初始化验证器
    verifier = CognitiveConsistencyVerifier()

    # 2. 构建小摊贩知识节点
    n1 = KnowledgeNode("g1", "Maximize Food Quality", "goal", 0.9)
    n2 = KnowledgeNode("g2", "Minimize Operational Cost", "goal", 0.8)
    n3 = KnowledgeNode("c1", "Use Premium Ingredients", "action", 0.5)
    n4 = KnowledgeNode("c2", "Reduce Waste", "action", 0.5)
    
    # 3. 添加节点
    for n in [n1, n2, n3, n4]:
        verifier.add_knowledge_node(n)

    # 4. 定义逻辑关系
    # 提高质量 -> 需要 -> 高级食材
    verifier.define_relation(LogicalRelation("g1", "c1", RelationType.SUPPORTS))
    # 降低成本 -> 矛盾于 -> 高级食材 (隐含：高级食材太贵)
    verifier.define_relation(LogicalRelation("g2", "c1", RelationType.CONTRADICTS, condition="budget < threshold"))
    
    # 5. 执行验证 (模拟低预算环境)
    runtime_context = {"budget": 500, "season": "winter"}
    
    print("--- Starting Verification ---")
    detected_conflicts = verifier.check_internal_consistency(context=runtime_context)
    
    print(f"\n--- Verification Report: Found {len(detected_conflicts)} conflicts ---")
    for conflict in detected_conflicts:
        print(f"ID: {conflict.conflict_id}")
        print(f"Level: {conflict.level}")
        print(f"Nodes: {conflict.involved_nodes}")
        print(f"Desc: {conflict.description}")
        print("-" * 30)