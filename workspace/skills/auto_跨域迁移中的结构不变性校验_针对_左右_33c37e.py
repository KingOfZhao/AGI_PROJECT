"""
Module: auto_跨域迁移中的结构不变性校验_针对_左右_33c37e
Description: 跨域迁移中的结构不变性校验: 针对“左右跨域重叠”，当AI将一个领域的SKILL
             （如编程中的递归逻辑）迁移到另一个领域（如管理学中的层级拆解）时，
             如何验证其结构有效性而非仅仅是表面类比？
             本模块构建一个“结构映射一致性检查器”，确保源领域和目标领域的核心关系
             （因果、时序、包含）保持同构。
Author: Senior Python Engineer
Version: 1.0.0
Date: 2023-10-27
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RelationType(Enum):
    """定义结构映射支持的关系类型枚举"""
    CAUSALITY = "causality"      # 因果关系
    TEMPORAL = "temporal"        # 时序关系
    INCLUSION = "inclusion"      # 包含关系
    DEPENDENCY = "dependency"    # 依赖关系
    ISOMORPHIC = "isomorphic"    # 同构关系

class GraphNode:
    """图节点类，代表领域中的实体"""
    def __init__(self, node_id: str, attributes: Optional[Dict[str, Any]] = None):
        self.node_id = node_id
        self.attributes = attributes or {}

    def __repr__(self) -> str:
        return f"Node({self.node_id})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GraphNode):
            return False
        return self.node_id == other.node_id

    def __hash__(self) -> int:
        return hash(self.node_id)

class GraphEdge:
    """图边类，代表实体间的关系"""
    def __init__(self, source: GraphNode, target: GraphNode, relation: RelationType, weight: float = 1.0):
        self.source = source
        self.target = target
        self.relation = relation
        self.weight = weight

    def __repr__(self) -> str:
        return f"Edge({self.source}->{self.target}, {self.relation.value})"

class DomainGraph:
    """领域图结构，包含节点和边"""
    def __init__(self, name: str):
        self.name = name
        self.nodes: Set[GraphNode] = set()
        self.edges: List[GraphEdge] = []

    def add_node(self, node: GraphNode) -> None:
        """添加节点"""
        if node in self.nodes:
            logger.warning(f"Node {node.node_id} already exists in graph {self.name}")
            return
        self.nodes.add(node)
        logger.debug(f"Added node {node.node_id} to graph {self.name}")

    def add_edge(self, source_id: str, target_id: str, relation: RelationType, weight: float = 1.0) -> None:
        """添加边"""
        source_node = next((n for n in self.nodes if n.node_id == source_id), None)
        target_node = next((n for n in self.nodes if n.node_id == target_id), None)

        if not source_node or not target_node:
            error_msg = f"Source node {source_id} or target node {target_id} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)

        edge = GraphEdge(source_node, target_node, relation, weight)
        self.edges.append(edge)
        logger.debug(f"Added edge from {source_id} to {target_id} with relation {relation.value}")

    def get_adjacency_list(self) -> Dict[str, List[Tuple[str, RelationType, float]]]:
        """获取邻接表表示的图结构"""
        adj_list: Dict[str, List[Tuple[str, RelationType, float]]] = {}
        for node in self.nodes:
            adj_list[node.node_id] = []

        for edge in self.edges:
            adj_list[edge.source.node_id].append(
                (edge.target.node_id, edge.relation, edge.weight)
            )

        return adj_list

def validate_graph_integrity(graph: DomainGraph) -> bool:
    """
    辅助函数：验证图结构的完整性
    检查图中是否存在孤立节点或无效的边引用
    
    Args:
        graph: 待验证的领域图
        
    Returns:
        bool: 图结构是否有效
        
    Raises:
        ValueError: 如果图结构存在严重问题
    """
    if not graph.nodes:
        logger.warning(f"Graph {graph.name} has no nodes")
        return False

    node_ids = {node.node_id for node in graph.nodes}
    
    # 检查边是否引用了存在的节点
    for edge in graph.edges:
        if edge.source.node_id not in node_ids or edge.target.node_id not in node_ids:
            error_msg = f"Edge references non-existent node in graph {graph.name}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    logger.info(f"Graph {graph.name} integrity validation passed")
    return True

def check_relation_isomorphism(
    source_graph: DomainGraph, 
    target_graph: DomainGraph, 
    node_mapping: Dict[str, str]
) -> Tuple[bool, Dict[str, Any]]:
    """
    核心函数：检查两个图之间的结构映射一致性
    
    Args:
        source_graph: 源领域图
        target_graph: 目标领域图
        node_mapping: 节点映射字典，key为源节点ID，value为目标节点ID
        
    Returns:
        Tuple[bool, Dict[str, Any]]: 
            - 第一个元素表示是否通过结构一致性检查
            - 第二个元素包含详细的检查结果报告
            
    Raises:
        ValueError: 如果输入图结构无效或映射不完整
    """
    # 验证输入图结构
    if not validate_graph_integrity(source_graph) or not validate_graph_integrity(target_graph):
        error_msg = "Invalid graph structure detected"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # 验证节点映射完整性
    source_node_ids = {node.node_id for node in source_graph.nodes}
    if set(node_mapping.keys()) != source_node_ids:
        error_msg = "Node mapping does not cover all source nodes"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # 准备结果报告
    report = {
        "is_consistent": True,
        "mismatched_edges": [],
        "missing_edges": [],
        "extra_edges": [],
        "coverage_percentage": 0.0
    }
    
    # 获取邻接表表示
    source_adj = source_graph.get_adjacency_list()
    target_adj = target_graph.get_adjacency_list()
    
    # 检查每条源边是否在目标图中有对应边
    matched_edges = 0
    total_source_edges = len(source_graph.edges)
    
    for source_edge in source_graph.edges:
        source_id = source_edge.source.node_id
        target_id = node_mapping[source_id]
        
        # 获取目标节点ID
        target_source_id = node_mapping[source_edge.source.node_id]
        target_target_id = node_mapping[source_edge.target.node_id]
        
        # 检查目标图中是否存在对应的边
        found = False
        if target_source_id in target_adj:
            for neighbor, relation, weight in target_adj[target_source_id]:
                if neighbor == target_target_id and relation == source_edge.relation:
                    found = True
                    matched_edges += 1
                    break
        
        if not found:
            report["is_consistent"] = False
            report["mismatched_edges"].append({
                "source_edge": str(source_edge),
                "expected_target": f"{target_source_id}->{target_target_id}",
                "expected_relation": source_edge.relation.value
            })
    
    # 计算覆盖率
    if total_source_edges > 0:
        report["coverage_percentage"] = (matched_edges / total_source_edges) * 100
    
    logger.info(f"Relation isomorphism check completed. Coverage: {report['coverage_percentage']:.2f}%")
    return report["is_consistent"], report

def analyze_structural_invariance(
    source_graph: DomainGraph, 
    target_graph: DomainGraph, 
    node_mapping: Dict[str, str],
    relation_types: Optional[List[RelationType]] = None
) -> Dict[str, Any]:
    """
    核心函数：分析跨域迁移的结构不变性
    
    Args:
        source_graph: 源领域图
        target_graph: 目标领域图
        node_mapping: 节点映射字典
        relation_types: 需要检查的关系类型列表，默认为None表示检查所有类型
        
    Returns:
        Dict[str, Any]: 包含结构不变性分析结果的字典
        
    Raises:
        ValueError: 如果输入参数无效
    """
    # 参数验证
    if not node_mapping:
        error_msg = "Node mapping cannot be empty"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # 如果没有指定关系类型，则检查所有类型
    if relation_types is None:
        relation_types = list(RelationType)
    
    # 执行结构一致性检查
    is_consistent, consistency_report = check_relation_isomorphism(
        source_graph, target_graph, node_mapping
    )
    
    # 计算结构相似度得分
    similarity_score = consistency_report["coverage_percentage"] / 100.0
    
    # 准备分析结果
    analysis_result = {
        "is_consistent": is_consistent,
        "similarity_score": similarity_score,
        "consistency_report": consistency_report,
        "relation_analysis": {},
        "recommendation": ""
    }
    
    # 按关系类型分析
    for rel_type in relation_types:
        source_edges = [e for e in source_graph.edges if e.relation == rel_type]
        target_edges = [e for e in target_graph.edges if e.relation == rel_type]
        
        analysis_result["relation_analysis"][rel_type.value] = {
            "source_count": len(source_edges),
            "target_count": len(target_edges),
            "preservation_rate": 0.0
        }
        
        if source_edges:
            # 计算该关系类型的保留率
            preserved = 0
            for edge in source_edges:
                source_id = edge.source.node_id
                target_id = edge.target.node_id
                
                mapped_source = node_mapping.get(source_id)
                mapped_target = node_mapping.get(target_id)
                
                if mapped_source and mapped_target:
                    # 检查目标图中是否存在对应的边
                    found = any(
                        e.source.node_id == mapped_source and 
                        e.target.node_id == mapped_target and 
                        e.relation == rel_type
                        for e in target_edges
                    )
                    if found:
                        preserved += 1
            
            preservation_rate = preserved / len(source_edges)
            analysis_result["relation_analysis"][rel_type.value]["preservation_rate"] = preservation_rate
    
    # 生成建议
    if is_consistent:
        analysis_result["recommendation"] = "结构映射完全一致，迁移方案可行。"
    else:
        weak_relations = [
            rel for rel, data in analysis_result["relation_analysis"].items()
            if data["preservation_rate"] < 0.7
        ]
        
        if weak_relations:
            analysis_result["recommendation"] = (
                f"警告：以下关系类型的结构保留率较低: {', '.join(weak_relations)}。"
                "建议重新检查这些关系类型的映射策略。"
            )
        else:
            analysis_result["recommendation"] = (
                "结构映射存在不一致，但核心关系保留率尚可。"
                "建议检查具体的边映射差异并调整迁移策略。"
            )
    
    logger.info(f"Structural invariance analysis completed. Similarity score: {similarity_score:.2f}")
    return analysis_result

def create_sample_graphs() -> Tuple[DomainGraph, DomainGraph, Dict[str, str]]:
    """
    辅助函数：创建示例图结构用于演示
    
    Returns:
        Tuple[DomainGraph, DomainGraph, Dict[str, str]]: 
            - 源领域图（递归逻辑）
            - 目标领域图（组织层级）
            - 节点映射字典
    """
    # 创建源领域图（递归逻辑）
    recursion_graph = DomainGraph("Recursion_Logic")
    
    # 添加节点
    base_case = GraphNode("base_case", {"description": "递归基本情况"})
    recursive_step = GraphNode("recursive_step", {"description": "递归步骤"})
    problem = GraphNode("problem", {"description": "原始问题"})
    subproblem = GraphNode("subproblem", {"description": "子问题"})
    result = GraphNode("result", {"description": "最终结果"})
    
    recursion_graph.add_node(base_case)
    recursion_graph.add_node(recursive_step)
    recursion_graph.add_node(problem)
    recursion_graph.add_node(subproblem)
    recursion_graph.add_node(result)
    
    # 添加边
    recursion_graph.add_edge("problem", "subproblem", RelationType.INCLUSION)
    recursion_graph.add_edge("subproblem", "base_case", RelationType.DEPENDENCY)
    recursion_graph.add_edge("subproblem", "recursive_step", RelationType.CAUSALITY)
    recursion_graph.add_edge("recursive_step", "result", RelationType.CAUSALITY)
    recursion_graph.add_edge("base_case", "result", RelationType.CAUSALITY)
    
    # 创建目标领域图（组织层级）
    org_graph = DomainGraph("Organization_Hierarchy")
    
    # 添加节点
    root_task = GraphNode("root_task", {"description": "根任务"})
    subtask = GraphNode("subtask", {"description": "子任务"})
    leaf_task = GraphNode("leaf_task", {"description": "叶子任务"})
    manager = GraphNode("manager", {"description": "管理者"})
    worker = GraphNode("worker", {"description": "执行者"})
    outcome = GraphNode("outcome", {"description": "最终产出"})
    
    org_graph.add_node(root_task)
    org_graph.add_node(subtask)
    org_graph.add_node(leaf_task)
    org_graph.add_node(manager)
    org_graph.add_node(worker)
    org_graph.add_node(outcome)
    
    # 添加边
    org_graph.add_edge("root_task", "subtask", RelationType.INCLUSION)
    org_graph.add_edge("subtask", "leaf_task", RelationType.INCLUSION)
    org_graph.add_edge("subtask", "manager", RelationType.DEPENDENCY)
    org_graph.add_edge("manager", "worker", RelationType.CAUSALITY)
    org_graph.add_edge("worker", "outcome", RelationType.CAUSALITY)
    
    # 创建节点映射
    node_mapping = {
        "problem": "root_task",
        "subproblem": "subtask",
        "base_case": "leaf_task",
        "recursive_step": "manager",
        "result": "outcome"
    }
    
    return recursion_graph, org_graph, node_mapping

if __name__ == "__main__":
    # 示例用法
    print("=== 结构不变性校验示例 ===")
    
    # 创建示例图
    source_graph, target_graph, mapping = create_sample_graphs()
    
    try:
        # 执行结构不变性分析
        analysis = analyze_structural_invariance(
            source_graph, 
            target_graph, 
            mapping,
            [RelationType.CAUSALITY, RelationType.INCLUSION, RelationType.DEPENDENCY]
        )
        
        # 输出结果
        print(f"\n结构一致性: {'通过' if analysis['is_consistent'] else '未通过'}")
        print(f"结构相似度得分: {analysis['similarity_score']:.2f}")
        print("\n关系类型分析:")
        for rel, data in analysis["relation_analysis"].items():
            print(f"  {rel}: 源领域 {data['source_count']} 条, 目标领域 {data['target_count']} 条, 保留率 {data['preservation_rate']:.2f}")
        
        print("\n建议:", analysis["recommendation"])
        
        # 检查具体不一致的边
        if not analysis["is_consistent"]:
            print("\n不一致的边:")
            for mismatch in analysis["consistency_report"]["mismatched_edges"]:
                print(f"  源边: {mismatch['source_edge']}")
                print(f"  期望目标边: {mismatch['expected_target']}, 关系类型: {mismatch['expected_relation']}")
                print("  ---")
                
    except ValueError as e:
        print(f"错误: {str(e)}")