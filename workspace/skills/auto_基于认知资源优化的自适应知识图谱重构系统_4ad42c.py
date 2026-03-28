"""
名称: auto_基于认知资源优化的自适应知识图谱重构系统_4ad42c
描述: 基于认知资源优化的自适应知识图谱重构系统。该能力不仅仅是数据清洗，而是模拟人类'顿悟'或'熟练化'的过程。
"""

import logging
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """
    知识图谱的基础数据结构，用于存储节点和边。
    """
    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Tuple[str, str, str]] = []  # (source, relation, target)

    def add_node(self, node_id: str, data: Dict[str, Any]) -> None:
        """添加节点"""
        if not node_id:
            raise ValueError("Node ID cannot be empty")
        self.nodes[node_id] = data
        logger.debug(f"Node added: {node_id}")

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点数据"""
        return self.nodes.get(node_id)


class CognitiveResourceMonitor:
    """
    核心类：监测交互模式并计算认知负载。
    负责识别频繁共现的节点模式，并计算将其组块化后的收益。
    """

    def __init__(self, graph: KnowledgeGraph, threshold: float = 0.7) -> None:
        """
        初始化监测器。

        Args:
            graph (KnowledgeGraph): 当前的知识图谱实例。
            threshold (float): 触发重构的认知负载阈值 (0.0 to 1.0)。
        """
        if not isinstance(graph, KnowledgeGraph):
            raise TypeError("Invalid graph instance provided.")
        
        self.graph = graph
        self.threshold = self._validate_threshold(threshold)
        # 记录节点共现频率: {(node_a, node_b): count}
        self.co_occurrence_map: Dict[Tuple[str, str], int] = defaultdict(int)
        # 记录总的交互查询次数
        self.total_queries = 0
        # 缓存已生成的组块
        self.cognitive_chunks: Dict[str, Dict[str, Any]] = {}

    def _validate_threshold(self, value: float) -> float:
        """辅助函数：验证阈值参数"""
        if not 0.0 <= value <= 1.0:
            logger.warning(f"Threshold {value} out of range [0, 1]. Clamping.")
            return max(0.0, min(1.0, value))
        return value

    def monitor_query(self, queried_node_ids: List[str]) -> float:
        """
        核心函数 1: 监测查询并更新认知负载模型。
        模拟人类在一次查询中需要同时持有多个概念的工作记忆场景。

        Args:
            queried_node_ids (List[str]): 用户或AI在一次交互中查询的节点ID列表。

        Returns:
            float: 当前交互的认知负载得分 (0.0 to 1.0)。
        
        Raises:
            ValueError: 如果输入列表为空。
        """
        if not queried_node_ids:
            raise ValueError("Query list cannot be empty.")

        self.total_queries += 1
        unique_nodes = set(queried_node_ids)
        
        # 简单的认知负载计算：基于查询涉及的节点数量（假设工作记忆容量有限）
        # 使用对数函数模拟随着节点增加，认知压力指数级上升
        raw_load = math.log(len(unique_nodes) + 1) / 2.0 # 归一化系数
        
        # 更新共现统计
        sorted_nodes = sorted(list(unique_nodes))
        for i in range(len(sorted_nodes)):
            for j in range(i + 1, len(sorted_nodes)):
                pair = (sorted_nodes[i], sorted_nodes[j])
                self.co_occurrence_map[pair] += 1

        # 模拟负载归一化
        load_score = min(1.0, raw_load)
        
        logger.info(f"Query monitored. Nodes: {len(unique_nodes)}, Cognitive Load: {load_score:.4f}")
        return load_score

    def analyze_and_restructure(self) -> List[Dict[str, Any]]:
        """
        核心函数 2: 分析热点模式并执行重构。
        如果特定节点组合的查询频率超过阈值，则创建一个'认知组块'。

        Returns:
            List[Dict[str, Any]]: 本次重构生成的所有新组块列表。
        """
        if self.total_queries == 0:
            return []

        generated_chunks = []
        # 设定频率阈值：例如，总查询次数的10%
        freq_threshold = max(2, self.total_queries * 0.1)

        logger.info(f"Analyzing graph structure. Total queries: {self.total_queries}")

        for pair, count in self.co_occurrence_map.items():
            if count > freq_threshold:
                # 发现高频共现节点对，准备组块化
                node_a, node_b = pair
                
                # 检查是否已经合并
                chunk_id = f"chunk_{node_a}_{node_b}"
                if chunk_id in self.cognitive_chunks:
                    continue

                logger.info(f"High co-occurrence detected: {pair} ({count} times). Triggering Denormalization.")
                
                # 执行重构
                new_chunk = self._create_cognitive_chunk(node_a, node_b, chunk_id)
                if new_chunk:
                    generated_chunks.append(new_chunk)
                    # 重置该对的计数，模拟'熟练化'后不再需要监测
                    self.co_occurrence_map[pair] = 0 

        return generated_chunks

    def _create_cognitive_chunk(self, node_id_a: str, node_id_b: str, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        辅助函数：融合两个节点为一个组块（反范式化）。
        这模拟了大脑将复杂步骤打包为单一'例行程序'的过程。

        Args:
            node_id_a: 节点A ID
            node_id_b: 节点B ID
            chunk_id: 新组块ID

        Returns:
            生成的组块数据字典，如果失败则返回None。
        """
        data_a = self.graph.get_node(node_id_a)
        data_b = self.graph.get_node(node_id_b)

        if not data_a or not data_b:
            logger.error(f"Missing nodes for chunking: {node_id_a} or {node_id_b}")
            return None

        try:
            # 融合逻辑：简单合并属性，并添加元数据标记
            merged_data = {
                "type": "CognitiveChunk",
                "source_nodes": [node_id_a, node_id_b],
                "content": {**data_a, **data_b}, # 浅合并
                "optimization_level": "high",
                "description": f"Automated fusion of {node_id_a} and {node_id_b} to reduce cognitive load."
            }
            
            # 将组块写回图谱（作为新节点）和本地缓存
            self.graph.add_node(chunk_id, merged_data)
            self.cognitive_chunks[chunk_id] = merged_data
            
            logger.debug(f"Cognitive Chunk created: {chunk_id}")
            return merged_data
            
        except Exception as e:
            logger.error(f"Error during chunk creation: {e}")
            return None

# 使用示例
if __name__ == "__main__":
    # 1. 初始化知识图谱
    kg = KnowledgeGraph()
    kg.add_node("apple", {"color": "red", "taste": "sweet"})
    kg.add_node("pie", {"type": "dessert", "temp": "hot"})
    kg.add_node("cinnamon", {"spice": True, "smell": "strong"})

    # 2. 初始化认知监测系统
    monitor = CognitiveResourceMonitor(kg, threshold=0.8)

    # 3. 模拟交互：人类频繁查询 apple 和 pie 的组合
    # 假设这是一个做苹果派的场景，用户不断查看这两个信息
    queries = [
        ["apple", "pie"],
        ["apple", "pie"],
        ["apple", "pie", "cinnamon"],
        ["apple", "pie"],
        ["apple", "pie"],
        ["apple", "pie", "sugar"], # sugar node doesn't exist, should handle gracefully in a real system
        ["apple", "pie"],
        ["apple", "pie"],
    ]

    print("--- Starting Simulation ---")
    for q in queries:
        try:
            load = monitor.monitor_query(q)
            # 只有当负载较高时才尝试分析（为了性能，虽然本例是演示）
            if load > 0.5:
                chunks = monitor.analyze_and_restructure()
                if chunks:
                    print(f">>> System Insight: Detected cognitive bottleneck. Auto-generated Chunk:")
                    for chunk in chunks:
                        print(f"    - {chunk['description']}")
        except ValueError as ve:
            logger.warning(f"Simulation skip: {ve}")

    print("--- Final Graph Nodes ---")
    for nid, data in kg.nodes.items():
        print(f"ID: {nid}, Data: {data}")