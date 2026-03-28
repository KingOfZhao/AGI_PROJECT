"""
模块: auto_神经符号知识图谱构建_融合数据建模的严格_65e323
描述: 神经符号知识图谱构建模块。融合数据建模的严格约束（外键）与认知图式的模糊联想。
      在构建知识图谱时，不仅建立逻辑上的强连接（外键），还基于共现和上下文建立弱连接（联想）。
      当逻辑路径断裂时，系统能像人类一样通过联想路径进行'模糊推理'，填补逻辑空白。
作者: AGI System
版本: 1.0.0
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class Node:
    """
    知识图谱节点基类。
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = "Entity"
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.node_id == other.node_id
        return False

@dataclass
class Edge:
    """
    知识图谱边。
    """
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0  # 1.0 代表强连接，<1.0 代表弱连接/联想
    edge_type: str = "LOGICAL"  # LOGICAL 或 ASSOCIATIVE

@dataclass
class DataRecord:
    """
    输入数据记录格式。
    """
    primary_key: str
    foreign_keys: Dict[str, str]  # 字段名 -> 指向的ID
    context_tokens: List[str]     # 用于构建联想的文本特征或标签

# --- 核心类 ---

class NeuralSymbolicGraph:
    """
    神经符号知识图谱类。
    管理节点、逻辑边和联想边的构建与检索。
    """

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.adjacency_index: Dict[str, List[Edge]] = defaultdict(list) # 邻接表索引
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)    # 联想倒排索引 (token -> node_ids)
        logger.info("NeuralSymbolicGraph 初始化完成.")

    def add_node(self, node: Node) -> bool:
        """
        添加节点到图谱。
        
        Args:
            node (Node): 待添加的节点对象。
            
        Returns:
            bool: 是否添加成功。
        """
        if not isinstance(node, Node):
            logger.error("无效的节点类型。")
            return False
        
        if node.node_id in self.nodes:
            logger.warning(f"节点 {node.node_id} 已存在，更新属性。")
            self.nodes[node.node_id].attributes.update(node.attributes)
        else:
            self.nodes[node.node_id] = node
            logger.debug(f"节点添加成功: {node.node_id}")
        return True

    def add_edge(self, source_id: str, target_id: str, relation: str, 
                 weight: float = 1.0, edge_type: str = "LOGICAL") -> Optional[Edge]:
        """
        添加边（关系）。
        
        Args:
            source_id (str): 源节点ID.
            target_id (str): 目标节点ID.
            relation (str): 关系名称.
            weight (float): 权重 (0.0-1.0).
            edge_type (str): 'LOGICAL' (逻辑/外键) 或 'ASSOCIATIVE' (联想/模糊).
            
        Returns:
            Optional[Edge]: 创建的边对象，失败返回None。
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            logger.error(f"无法创建边：节点缺失。Source: {source_id}, Target: {target_id}")
            return None
        
        if not (0.0 <= weight <= 1.0):
            logger.warning(f"权重 {weight} 超出范围，自动修正为 [0.0, 1.0]。")
            weight = max(0.0, min(1.0, weight))

        edge = Edge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
            edge_type=edge_type
        )
        self.edges.append(edge)
        self.adjacency_index[source_id].append(edge)
        logger.debug(f"边已添加: {source_id} -[{relation}]-> {target_id} ({edge_type})")
        return edge

    def build_index_for_association(self):
        """
        为所有节点建立基于属性的倒排索引，用于模糊联想检索。
        """
        logger.info("正在构建联想倒排索引...")
        count = 0
        for node_id, node in self.nodes.items():
            # 假设节点的 attributes 中包含 'tokens' 或使用 'label' 进行索引
            tokens = set()
            if "tags" in node.attributes and isinstance(node.attributes["tags"], list):
                tokens.update(node.attributes["tags"])
            tokens.add(node.label) # 标签也作为联想线索
            
            for token in tokens:
                self.inverted_index[token].add(node_id)
                count += 1
        logger.info(f"索引构建完成，共索引 {count} 个词条。")

# --- 核心功能函数 ---

def construct_graph_from_data(
    graph: NeuralSymbolicGraph, 
    records: List[DataRecord]
) -> None:
    """
    核心函数1：根据结构化数据记录构建图谱的'逻辑层'（强连接）。
    严格遵循外键约束建立实体间的关系。
    
    Args:
        graph (NeuralSymbolicGraph): 图谱实例。
        records (List[DataRecord]): 结构化数据记录列表。
    """
    logger.info(f"开始构建逻辑层，处理 {len(records)} 条记录...")
    
    # 第一步：创建所有节点
    for rec in records:
        node = Node(
            node_id=rec.primary_key,
            attributes={"context": rec.context_tokens}
        )
        graph.add_node(node)
    
    # 第二步：创建逻辑边（外键关系）
    for rec in records:
        source_node = graph.nodes.get(rec.primary_key)
        if not source_node: continue
        
        for rel_name, target_key in rec.foreign_keys.items():
            # 严格约束：如果目标ID不存在，逻辑上不应该连接，此处进行校验
            if target_key in graph.nodes:
                graph.add_edge(
                    source_id=rec.primary_key,
                    target_id=target_key,
                    relation=rel_name,
                    weight=1.0,  # 逻辑连接权重最高
                    edge_type="LOGICAL"
                )
            else:
                logger.warning(f"逻辑断裂: 节点 {rec.primary_key} 引用了不存在的目标 {target_key}")

def infer_associative_links(
    graph: NeuralSymbolicGraph, 
    similarity_threshold: float = 0.1
) -> None:
    """
    核心函数2：构建'联想层'（弱连接）。
    基于上下文共现性建立模糊边，填补逻辑空白。
    
    Args:
        graph (NeuralSymbolicGraph): 图谱实例。
        similarity_threshold (float): 建立连接的最小相似度阈值。
    """
    logger.info("开始构建联想层（模糊推理）...")
    
    # 确保索引已建立
    graph.build_index_for_association()
    
    processed_pairs = set()
    
    for node_id, node in graph.nodes.items():
        current_context = set(node.attributes.get("context", []))
        current_context.add(node.label)
        
        # 寻找具有相似上下文的其他节点
        candidate_matches: Dict[str, int] = defaultdict(int)
        
        for token in current_context:
            if token in graph.inverted_index:
                for match_id in graph.inverted_index[token]:
                    if match_id != node_id:
                        candidate_matches[match_id] += 1
        
        # 根据重叠度建立弱连接
        for match_id, overlap_count in candidate_matches.items():
            # 避免重复建立边
            pair = tuple(sorted((node_id, match_id)))
            if pair in processed_pairs:
                continue
            
            # 简单的Jaccard相似度模拟: 交集 / (集合A + 集合B - 交集)
            # 这里简化计算：权重基于重叠数量衰减
            strength = overlap_count / (len(current_context) + 5) # 模拟归一化
            
            if strength >= similarity_threshold:
                # 检查是否已存在逻辑边，如果存在则不覆盖，或增强
                existing_logical = any(
                    e.target_id == match_id and e.edge_type == "LOGICAL" 
                    for e in graph.adjacency_index[node_id]
                )
                
                if not existing_logical:
                    graph.add_edge(
                        source_id=node_id,
                        target_id=match_id,
                        relation="RELATED_TO", # 模糊关系
                        weight=strength,
                        edge_type="ASSOCIATIVE"
                    )
                    # 双向连接
                    graph.add_edge(
                        source_id=match_id,
                        target_id=node_id,
                        relation="RELATED_TO",
                        weight=strength,
                        edge_type="ASSOCIATIVE"
                    )
                    processed_pairs.add(pair)

    logger.info("联想层构建完成。")

def fuzzy_traverse(
    graph: NeuralSymbolicGraph, 
    start_id: str, 
    target_criteria: str, 
    max_depth: int = 3
) -> List[Dict[str, Any]]:
    """
    辅助函数：模糊遍历推理。
    当纯逻辑路径无法到达时，利用联想边进行跳步。
    
    Args:
        graph (NeuralSymbolicGraph): 图谱。
        start_id (str): 起始节点。
        target_criteria (str): 目标节点的特征（如Label）。
        max_depth (int): 最大搜索深度。
        
    Returns:
        List[Dict]: 推理路径列表，包含路径和置信度。
    """
    if start_id not in graph.nodes:
        return []

    results = []
    # 简化的BFS/DFS实现，优先走逻辑边，逻辑边走不通走联想边
    # 这里仅作演示：查找符合特征的邻居
    
    def _search(current_id: str, path: List[str], current_weight: float, depth: int):
        if depth > max_depth:
            return
        
        node = graph.nodes[current_id]
        
        # 检查当前节点是否符合目标特征
        if target_criteria in node.label or target_criteria in node.attributes.get("context", []):
            if current_id != start_id: # 排除起点
                results.append({
                    "path": path + [current_id],
                    "confidence": current_weight,
                    "type": "MIXED_PATH"
                })
                return # 找到即停止该分支

        # 遍历邻居
        for edge in graph.adjacency_index[current_id]:
            next_weight = current_weight * edge.weight
            if next_weight < 0.1: # 剪枝：置信度过低
                continue
            
            if edge.target_id not in path: # 防止环
                _search(edge.target_id, path + [current_id], next_weight, depth + 1)

    _search(start_id, [], 1.0, 0)
    return sorted(results, key=lambda x: x['confidence'], reverse=True)

# --- 使用示例 ---

if __name__ == "__main__":
    # 1. 初始化图谱
    kg = NeuralSymbolicGraph()

    # 2. 模拟输入数据 (领域：医疗/生物)
    # 假设我们有严格的数据表结构，同时包含文本描述
    data_samples = [
        DataRecord(
            primary_key="PATIENT_001",
            foreign_keys={"has_disease": "DIS_FLU"}, # 逻辑外键
            context_tokens=["fever", "cough", "winter", "influenza"] # 上下文特征
        ),
        DataRecord(
            primary_key="DIS_FLU",
            foreign_keys={"treated_by": "DRUG_TAMI"}, # 逻辑外键
            context_tokens=["influenza", "virus", "infection", "respiratory"]
        ),
        DataRecord(
            primary_key="DRUG_TAMI",
            foreign_keys={}, 
            context_tokens=["antiviral", "capsule", "influenza"]
        ),
        # 这个节点与 PATIENT_001 没有直接逻辑关系，但共享上下文 "fever"
        DataRecord(
            primary_key="SYM_FEVER",
            foreign_keys={}, 
            context_tokens=["symptom", "high_temp", "infection", "immune_response"]
        ),
        # 这个节点逻辑上断裂，但与 DRUG_TAMI 有联想
        DataRecord(
            primary_key="DIS_COVID",
            foreign_keys={}, # 假设这里没有直接外键连接到 DRUG_TAMI
            context_tokens=["virus", "respiratory", "pandemic", "corona"]
        )
    ]

    # 3. 构建逻辑层 (Step 1: Strict Data Modeling)
    print("\n[Phase 1] 构建严格逻辑连接...")
    construct_graph_from_data(kg, data_samples)

    # 4. 构建联想层 (Step 2: Fuzzy Cognitive Mapping)
    print("\n[Phase 2] 构建模糊联想连接...")
    infer_associative_links(kg, similarity_threshold=0.15)

    # 5. 检查图谱状态
    print(f"\n图谱统计: 节点数 {len(kg.nodes)}, 边数 {len(kg.edges)}")
    print("逻辑边示例:", [e for e in kg.edges if e.edge_type == "LOGICAL"][:2])
    print("联想边示例:", [e for e in kg.edges if e.edge_type == "ASSOCIATIVE"][:2])

    # 6. 模糊推理演示
    # 场景：从 DIS_COVID 出发，寻找治疗方法。
    # 逻辑上 DIS_COVID 没有外键指向药物。
    # 但 DIS_COVID 与 DIS_FLU 共享 "virus", "respiratory" 上下文。
    # DIS_FLU 连接着 DRUG_TAMI。
    print("\n[Phase 3] 模糊推理: 从 DIS_COVID 寻找潜在治疗相关实体...")
    paths = fuzzy_traverse(kg, "DIS_COVID", "antiviral", max_depth=3)
    
    if paths:
        print(f"发现潜在路径 (置信度: {paths[0]['confidence']:.2f}):")
        for node_id in paths[0]['path']:
            node = kg.nodes[node_id]
            print(f" -> {node.label} ({node_id})")
    else:
        print("未找到有效推理路径。")