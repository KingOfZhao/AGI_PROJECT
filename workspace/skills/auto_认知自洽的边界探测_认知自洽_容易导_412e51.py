"""
Module: auto_认知自洽的边界探测_认知自洽_容易导_412e51
Description: 【认知自洽的边界探测】'认知自洽'容易导致'回音室效应'，使系统陷入局部最优。
             本模块设计了一个'红队测试'系统，主动寻找现有SKILL节点中的逻辑矛盾或覆盖盲区。
             它利用现有节点构建逻辑图，并自动生成'反事实'攻击向量，试图证伪现有知识体系的自洽性。
Author: Senior Python Engineer for AGI System
Version: 1.0.0
License: MIT
"""

import logging
import random
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveConsistencyProbe")


@dataclass
class SkillNode:
    """
    代表系统中的一个技能节点。
    
    Attributes:
        id (str): 节点的唯一标识符。
        description (str): 节点功能的描述。
        dependencies (List[str]): 该节点依赖的其他节点ID列表。
        truth_claims (List[str]): 该节点包含的逻辑断言或事实声明。
    """
    id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    truth_claims: List[str] = field(default_factory=list)


@dataclass
class LogicalGraph:
    """
    知识体系的逻辑图结构。
    """
    nodes: Dict[str, SkillNode] = field(default_factory=dict)
    adjacency_out: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    adjacency_in: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))


class ConsistencyProbingError(Exception):
    """自定义异常类，用于处理探测过程中的特定错误。"""
    pass


def _validate_skill_data(raw_data: List[Dict]) -> List[SkillNode]:
    """
    [辅助函数] 验证并转换原始数据为SkillNode对象列表。
    
    Args:
        raw_data (List[Dict]): 包含节点数据的字典列表。
        
    Returns:
        List[SkillNode]: 验证后的节点对象列表。
        
    Raises:
        ValueError: 如果数据格式不正确或缺少必要字段。
    """
    logger.info(f"Validating {len(raw_data)} raw skill nodes...")
    validated_nodes = []
    
    if not isinstance(raw_data, list):
        raise ValueError("Input data must be a list of dictionaries.")

    for item in raw_data:
        try:
            if not all(k in item for k in ['id', 'description']):
                logger.warning(f"Node missing required fields: {item}")
                continue
            
            # 简单的数据清洗
            node_id = str(item['id']).strip()
            desc = str(item['description']).strip()
            
            if len(node_id) < 1 or len(desc) < 10:
                logger.debug(f"Skipping node {node_id} due to insufficient content length.")
                continue

            node = SkillNode(
                id=node_id,
                description=desc,
                dependencies=item.get('dependencies', []),
                truth_claims=item.get('truth_claims', [])
            )
            validated_nodes.append(node)
        except Exception as e:
            logger.error(f"Error validating node {item.get('id', 'unknown')}: {e}")
            
    logger.info(f"Successfully validated {len(validated_nodes)} nodes.")
    return validated_nodes


def construct_logical_graph(nodes: List[SkillNode]) -> LogicalGraph:
    """
    [核心函数 1] 构建逻辑依赖图。
    
    分析节点间的依赖关系，构建有向图结构，用于后续的因果链分析。
    
    Args:
        nodes (List[SkillNode]): 技能节点列表。
        
    Returns:
        LogicalGraph: 构建完成的逻辑图对象。
    """
    logger.info("Constructing logical graph...")
    graph = LogicalGraph()
    node_map = {node.id: node for node in nodes}
    graph.nodes = node_map
    
    missing_deps_count = 0
    
    for node in nodes:
        for dep_id in node.dependencies:
            if dep_id in node_map:
                graph.adjacency_out[node.id].add(dep_id)
                graph.adjacency_in[dep_id].add(node.id)
            else:
                missing_deps_count += 1
                logger.warning(f"Node {node.id} depends on missing node {dep_id}. Blind spot detected.")
    
    logger.info(f"Graph construction complete. Missing dependencies (Blind Spots): {missing_deps_count}")
    return graph


def generate_counter_factual_attacks(graph: LogicalGraph, attack_intensity: float = 0.5) -> List[Dict]:
    """
    [核心函数 2] 生成反事实攻击向量。
    
    遍历逻辑图，寻找潜在的矛盾点或覆盖盲区，并生成旨在破坏系统自洽性的测试用例。
    策略包括：
    1. 孤立点检测（盲区）。
    2. 依赖链断裂模拟（逻辑证伪）。
    3. 描述语义冲突检测（简化版，基于关键词）。
    
    Args:
        graph (LogicalGraph): 知识图谱。
        attack_intensity (float): 攻击强度 (0.0 to 1.0)，决定生成的攻击向量的激进程度。
        
    Returns:
        List[Dict]: 生成的攻击向量列表，每个向量包含目标节点ID和攻击逻辑描述。
    """
    if not (0.0 <= attack_intensity <= 1.0):
        raise ConsistencyProbingError("attack_intensity must be between 0.0 and 1.0")

    logger.info("Initiating Red Team: Generating counter-factual attacks...")
    attack_vectors = []
    
    # 1. 探测孤立节点（认知盲区）
    all_node_ids = set(graph.nodes.keys())
    connected_node_ids = set(graph.adjacency_out.keys()).union(set(graph.adjacency_in.keys()))
    isolated_nodes = all_node_ids - connected_node_ids
    
    for node_id in isolated_nodes:
        attack_vectors.append({
            "target_node": node_id,
            "attack_type": "ISOLATION_ANOMALY",
            "vector": f"Node {node_id} has no logical connections. Is it dead code or an ungrounded belief?",
            "severity": "LOW"
        })

    # 2. 探测逻辑自洽性（回音室检测）
    # 随机选择连接紧密的节点进行“否定”测试
    target_nodes = random.sample(
        list(graph.nodes.keys()), 
        min(int(len(graph.nodes) * attack_intensity), 50)
    )

    for node_id in target_nodes:
        node = graph.nodes[node_id]
        
        # 生成反事实前提
        if "always" in node.description.lower() or "never" in node.description.lower():
            attack_vectors.append({
                "target_node": node_id,
                "attack_type": "ABSOLUTE_CLAIM_FALSIFICATION",
                "vector": f"Challenge absolute claim in '{node.description[:30]}...'. Construct scenario where this condition is false.",
                "severity": "HIGH"
            })
        
        # 依赖循环检测 (简易版)
        if node_id in graph.adjacency_out.get(node_id, set()):
             attack_vectors.append({
                "target_node": node_id,
                "attack_type": "CIRCULAR_LOGIC",
                "vector": f"Node {node_id} depends on itself. Immediate logical invalidity.",
                "severity": "CRITICAL"
            })

        # 生成反事实攻击
        if node.dependencies:
            random_dep = random.choice(node.dependencies)
            attack_vectors.append({
                "target_node": node_id,
                "attack_type": "DEPENDENCY_DENIAL",
                "vector": f"Assume dependency '{random_dep}' is FALSE/UNAVAILABLE. Does node {node_id} collapse?",
                "severity": "MEDIUM"
            })

    logger.info(f"Generated {len(attack_vectors)} attack vectors.")
    return attack_vectors


def run_consistency_probe(raw_skill_data: List[Dict]) -> Dict:
    """
    执行完整的认知自洽性边界探测流程。
    
    Args:
        raw_skill_data (List[Dict]): 原始技能数据列表。
        
    Returns:
        Dict: 包含逻辑图统计信息和攻击向量的报告。
    """
    try:
        # 1. 数据验证
        validated_nodes = _validate_skill_data(raw_skill_data)
        if len(validated_nodes) < 5:
            logger.warning("Data set too small for meaningful consistency probing.")

        # 2. 构建图谱
        graph = construct_logical_graph(validated_nodes)

        # 3. 红队攻击
        vectors = generate_counter_factual_attacks(graph, attack_intensity=0.8)

        # 4. 生成报告
        report = {
            "total_nodes_analyzed": len(graph.nodes),
            "total_blind_spots": len([v for v in vectors if v["attack_type"] == "ISOLATION_ANOMALY"]),
            "critical_issues": len([v for v in vectors if v["severity"] == "CRITICAL"]),
            "attack_vectors": vectors,
            "status": "PROBE_COMPLETE"
        }
        return report

    except Exception as e:
        logger.error(f"Critical failure in consistency probe: {e}")
        return {"status": "FAILED", "error": str(e)}


# ==========================================
# Usage Example
# ==========================================
if __name__ == "__main__":
    # 模拟 AGI 系统中的 1622 个 SKILL 节点数据 (这里仅演示少量数据)
    mock_data = [
        {
            "id": "skill_001", 
            "description": "This skill always handles user authentication securely.", 
            "dependencies": ["skill_002"],
            "truth_claims": ["Authentication is always secure"]
        },
        {
            "id": "skill_002", 
            "description": "Database connection manager.", 
            "dependencies": [], # No dependencies
        },
        {
            "id": "skill_003", 
            "description": "Legacy module for plain text storage.", 
            "dependencies": ["skill_999"] # 999 does not exist -> Blind spot
        },
        {
            "id": "skill_004",
            "description": "Circular dependency test.",
            "dependencies": ["skill_004"] # Self dependency
        },
        {
            "id": "skill_005",
            "description": "An isolated node with no connections."
        }
    ]

    print("--- Starting Cognitive Consistency Probe ---")
    result_report = run_consistency_probe(mock_data)
    
    print(f"\nProbe Status: {result_report['status']}")
    print(f"Nodes Analyzed: {result_report['total_nodes_analyzed']}")
    print(f"Detected Blind Spots: {result_report['total_blind_spots']}")
    print(f"Critical Issues Found: {result_report['critical_issues']}")
    
    print("\n--- Sample Attack Vectors (Top 3) ---")
    for vector in result_report['attack_vectors'][:3]:
        print(f"[{vector['severity']}] {vector['attack_type']}: {vector['vector']}")