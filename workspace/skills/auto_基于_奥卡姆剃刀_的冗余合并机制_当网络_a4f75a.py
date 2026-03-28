"""
Auto-Redundancy-Merger: 基于奥卡姆剃刀的冗余合并机制

该模块实现了AGI系统中的知识图谱/节点网络优化功能。
在'自下而上'的构建过程中，网络中常会出现语义高度重叠但结构不同的节点。
本模块通过计算语义编辑距离，识别冗余节点，并根据'奥卡姆剃刀'原则（如无必要，勿增实体）
制定合并策略，保留最简洁且覆盖广的节点，从而降低系统熵。

Core Features:
    - 语义编辑距离计算 (基于Levenshtein距离的改进)
    - 基于阈值的冗余检测
    - 综合复杂度与覆盖率的合并评分
    - 安全的节点合并与清理

Dependencies:
    - python-Levenshtein (用于快速编辑距离计算)
    - numpy (用于数值计算)
"""

import logging
import heapq
from typing import List, Dict, Tuple, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# 尝试导入Levenshtein库，如果不存在则使用内置的简单实现
try:
    import Levenshtein
    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False
    logging.warning("python-Levenshtein library not found. Falling back to pure Python implementation.")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OccamsRedundancyMerger")

class NodeType(Enum):
    """节点类型枚举"""
    CONCEPT = "concept"
    ACTION = "action"
    ENTITY = "entity"

@dataclass
class KnowledgeNode:
    """
    知识节点数据结构
    
    Attributes:
        id (str): 节点唯一标识符
        description (str): 节点的自然语言描述（用于语义计算）
        connections (Set[str]): 该节点连接的其他节点ID集合
        complexity (float): 节点的结构复杂度（默认为描述长度）
        node_type (NodeType): 节点类型
        metadata (Dict[str, Any]): 额外的元数据
    """
    id: str
    description: str
    connections: Set[str] = field(default_factory=set)
    complexity: float = 0.0
    node_type: NodeType = NodeType.CONCEPT
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # 如果未指定复杂度，默认使用描述长度作为基础复杂度指标
        if self.complexity == 0.0:
            self.complexity = len(self.description)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, KnowledgeNode):
            return self.id == other.id
        return False

def _calculate_levenshtein_distance(s1: str, s2: str) -> int:
    """
    辅助函数：计算两个字符串之间的Levenshtein编辑距离。
    如果是纯Python环境且无C加速，回退到此实现。
    """
    if len(s1) < len(s2):
        return _calculate_levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def calculate_semantic_distance(node_a: KnowledgeNode, node_b: KnowledgeNode) -> float:
    """
    核心函数1: 计算两个节点之间的语义编辑距离。
    
    将距离归一化为 [0, 1] 区间，0表示完全一致，1表示完全不同。
    同时考虑了节点类型的硬性约束。
    
    Args:
        node_a (KnowledgeNode): 节点A
        node_b (KnowledgeNode): 节点B
        
    Returns:
        float: 归一化的语义距离
        
    Raises:
        ValueError: 如果节点描述为空
    """
    if not node_a.description or not node_b.description:
        raise ValueError("Node description cannot be empty for distance calculation.")

    # 如果类型不同，视为语义距离无限大（不可合并）
    if node_a.node_type != node_b.node_type:
        return 1.0

    # 计算描述文本的编辑距离
    if LEVENSHTEIN_AVAILABLE:
        dist = Levenshtein.distance(node_a.description, node_b.description)
    else:
        dist = _calculate_levenshtein_distance(node_a.description, node_b.description)
    
    max_len = max(len(node_a.description), len(node_b.description))
    
    # 避免除以零
    if max_len == 0:
        return 0.0
    
    normalized_dist = dist / max_len
    logger.debug(f"Distance between '{node_a.id}' and '{node_b.id}': {normalized_dist:.4f}")
    return normalized_dist

def merge_redundant_nodes(
    nodes: List[KnowledgeNode], 
    distance_threshold: float = 0.2, 
    complexity_weight: float = 0.7
) -> List[KnowledgeNode]:
    """
    核心函数2: 基于奥卡姆剃刀原则的冗余合并主逻辑。
    
    算法流程：
    1. 遍历所有节点对，计算语义距离。
    2. 筛选出距离小于阈值的节点对。
    3. 对候选合并对进行评分，保留 '描述最简洁(权重w) 且 覆盖最广(权重1-w)' 的节点。
    4. 执行合并操作，将冗余节点的连接迁移到保留节点。
    5. 移除冗余节点。
    
    Args:
        nodes (List[KnowledgeNode]): 当前网络中的所有节点列表
        distance_threshold (float): 判定为冗余的距离阈值 (0.0 - 1.0)
        complexity_weight (float): 复杂度在评分中的权重 (0.0 - 1.0)，越高越偏向简单节点
        
    Returns:
        List[KnowledgeNode]: 经过合并优化后的节点列表
        
    Example:
        >>> nodes = [
        ...     KnowledgeNode(id="1", description="acquire data", connections={"2"}	node_type=NodeType.ACTION),
        ...     KnowledgeNode(id="2", description="get data", connections={"3"}	node_type=NodeType.ACTION)
        ... ]
        >>> optimized = merge_redundant_nodes(nodes, distance_threshold=0.3)
    """
    # 数据验证
    if not 0.0 <= distance_threshold <= 1.0:
        raise ValueError("Distance threshold must be between 0 and 1.")
    if not nodes:
        return []

    logger.info(f"Starting redundancy merge on {len(nodes)} nodes. Threshold: {distance_threshold}")
    
    # 使用并查集结构来管理合并组
    # parent: Dict[str, str] key是子节点ID，value是保留的父节点ID
    parent_map: Dict[str, str] = {n.id: n.id for n in nodes}
    node_dict: Dict[str, KnowledgeNode] = {n.id: n for n in nodes}
    
    # 按ID排序以保证确定性
    sorted_ids = sorted(node_dict.keys())
    
    # 1. 寻找冗余对
    # 存储格式: (distance, id_a, id_b)
    merge_candidates: List[Tuple[float, str, str]] = []
    
    for i in range(len(sorted_ids)):
        for j in range(i + 1, len(sorted_ids)):
            id_a = sorted_ids[i]
            id_b = sorted_ids[j]
            node_a = node_dict[id_a]
            node_b = node_dict[id_b]
            
            try:
                dist = calculate_semantic_distance(node_a, node_b)
                if dist < distance_threshold:
                    heapq.heappush(merge_candidates, (dist, id_a, id_b))
                    logger.info(f"Candidate found: '{node_a.description}' <-> '{node_b.description}' (Dist: {dist:.3f})")
            except ValueError as e:
                logger.error(f"Error calculating distance for {id_a}, {id_b}: {e}")

    # 2. 处理合并
    # 记录已被删除的节点ID
    removed_ids: Set[str] = set()
    
    while merge_candidates:
        dist, id_a, id_b = heapq.heappop(merge_candidates)
        
        # 如果其中任何一个已经被合并/删除，跳过
        if id_a in removed_ids or id_b in removed_ids:
            continue
            
        node_a = node_dict[id_a]
        node_b = node_dict[id_b]
        
        # 决策：保留哪一个？ (奥卡姆剃刀 + 覆盖率)
        # Score = w * (1/complexity_norm) + (1-w) * (coverage_norm)
        # 这里简化：complexity越低越好，connections越多越好
        
        # 归一化覆盖率 (简单用连接数)
        conn_a = len(node_a.connections)
        conn_b = len(node_b.connections)
        max_conn = max(conn_a, conn_b, 1)
        
        # 评分：分越高越好。
        # 复杂度：越小越好，所以用倒数或负相关。这里复杂度用 1/complexity
        score_a = complexity_weight * (1.0 / (node_a.complexity + 1e-5)) + (1 - complexity_weight) * (conn_a / max_conn)
        score_b = complexity_weight * (1.0 / (node_b.complexity + 1e-5)) + (1 - complexity_weight) * (conn_b / max_conn)
        
        survivor: KnowledgeNode
        redundant: KnowledgeNode
        
        if score_a >= score_b:
            survivor = node_a
            redundant = node_b
        else:
            survivor = node_b
            redundant = node_a
            
        logger.info(f"Merging '{redundant.id}' into '{survivor.id}'. "
                    f"Reason: Survivor Score {max(score_a, score_b):.2f} > {min(score_a, score_b):.2f}")

        # 执行合并逻辑
        # 1. 转移连接
        # 注意：不能将自己连接到自己，需过滤
        new_connections = redundant.connections - {survivor.id}
        survivor.connections.update(new_connections)
        
        # 2. 更新元数据 (可选：记录合并历史)
        if "merged_ids" not in survivor.metadata:
            survivor.metadata["merged_ids"] = []
        survivor.metadata["merged_ids"].append(redundant.id)
        
        # 3. 标记冗余节点已移除
        removed_ids.add(redundant.id)
        
        # 4. 更新全局节点字典中其他节点对redundant的引用
        # 将所有指向 redundant.id 的连接改为 survivor.id
        for nid, n in node_dict.items():
            if nid in removed_ids:
                continue
            if redundant.id in n.connections:
                n.connections.remove(redundant.id)
                n.connections.add(survivor.id)

    # 3. 构建最终结果
    final_nodes = [n for n in node_dict.values() if n.id not in removed_ids]
    
    logger.info(f"Merge complete. Reduced {len(nodes)} -> {len(final_nodes)} nodes.")
    return final_nodes

# --- Usage Example ---
if __name__ == "__main__":
    # 创建测试节点：模拟语义重复但结构略有不同的场景
    n1 = KnowledgeNode(
        id="skill_001", 
        description="Open the file and read data", 
        connections={"db_01"}, 
        complexity=10.0
    )
    n2 = KnowledgeNode(
        id="skill_002", 
        description="Open file and read",  # 高度相似，且更简洁
        connections={"db_01", "api_01"},   # 覆盖更广
        complexity=5.0
    )
    n3 = KnowledgeNode(
        id="skill_003", 
        description="Close the application", # 完全不同的功能
        connections={"sys_01"},
        node_type=NodeType.ACTION
    )
    n4 = KnowledgeNode(
        id="skill_004",
        description="Open the file and read data", # 与n1完全一样
        connections={},
        complexity=12.0
    )

    all_nodes = [n1, n2, n3, n4]
    
    print("--- Before Merge ---")
    for n in all_nodes:
        print(f"ID: {n.id}, Desc: '{n.description}', Conns: {n.connections}")

    # 执行合并
    # 阈值设为0.2，因为n1, n2, n4 之间的距离很小
    try:
        merged_nodes = merge_redundant_nodes(all_nodes, distance_threshold=0.25)
        
        print("\n--- After Merge ---")
        for n in merged_nodes:
            print(f"ID: {n.id}, Desc: '{n.description}', Conns: {n.connections}, Meta: {n.metadata}")
            
    except ValueError as ve:
        logger.error(f"Validation Error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")