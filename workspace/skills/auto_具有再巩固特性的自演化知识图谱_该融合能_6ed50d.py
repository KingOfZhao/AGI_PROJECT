"""
高级技能模块：具有再巩固特性的自演化知识图谱 (Self-Evolving Knowledge Graph with Reconsolidation)

该模块实现了一个模拟人类记忆机制的动态知识图谱。核心特性在于“记忆再巩固”：
当记忆（节点或关系）被提取（查询）时，系统不仅返回数据，还会根据当前的
查询上下文和时间衰减因子，更新记忆的权重和连接强度。这使得知识图谱能够
随使用场景自然演化，强化常用路径，弱化过时信息。

版本: 1.0.0
作者: AGI System Core Engineer
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from uuid import uuid4, UUID

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class MemoryNode:
    """
    知识图谱中的节点，代表一个概念或实体。
    
    Attributes:
        id (UUID): 节点的唯一标识符。
        content (str): 节点存储的实际内容/知识。
        weight (float): 节点的权重，代表记忆的清晰度或重要性 (0.0 to 1.0)。
        last_accessed (float): 上次被访问的时间戳 (Unix timestamp)。
        created_at (float): 节点创建时间。
        neighbors (Dict[UUID, float]): 邻接表，存储连接的节点ID及边的权重。
    """
    id: UUID = field(default_factory=uuid4)
    content: str = ""
    weight: float = 0.5  # 初始权重
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    neighbors: Dict[UUID, float] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.content, str):
            raise ValueError("Content must be a string.")
        if not (0.0 <= self.weight <= 1.0):
            raise ValueError("Weight must be between 0.0 and 1.0.")


class ReconsolidatingKnowledgeGraph:
    """
    自演化知识图谱类。
    
    实现了基于查询的记忆重构机制。读取操作被视为一种'再巩固'过程，
    会触发节点权重的动态调整。
    """

    def __init__(self, decay_rate: float = 0.05, consolidation_factor: float = 0.1):
        """
        初始化图谱。
        
        Args:
            decay_rate (float): 记忆随时间自然衰减的速率。
            consolidation_factor (float): 每次访问时权重增加的因子。
        """
        self._nodes: Dict[UUID, MemoryNode] = {}
        self.decay_rate = decay_rate
        self.consolidation_factor = consolidation_factor
        logger.info("Initialized ReconsolidatingKnowledgeGraph with decay=%s, consolidation=%s",
                    decay_rate, consolidation_factor)

    def add_node(self, content: str, initial_weight: float = 0.5) -> UUID:
        """
        向图谱中添加新的知识节点。
        
        Args:
            content (str): 知识内容。
            initial_weight (float): 初始权重。
            
        Returns:
            UUID: 新创建节点的ID。
            
        Raises:
            ValueError: 如果参数无效。
        """
        if not content.strip():
            raise ValueError("Node content cannot be empty.")
        
        node = MemoryNode(content=content, weight=initial_weight)
        self._nodes[node.id] = node
        logger.debug("Added node %s with content: '%s'", node.id, content)
        return node.id

    def link_nodes(self, source_id: UUID, target_id: UUID, strength: float = 0.5) -> bool:
        """
        在两个节点之间创建或更新连接。
        
        Args:
            source_id (UUID): 源节点ID。
            target_id (UUID): 目标节点ID。
            strength (float): 连接强度 (0.0 to 1.0)。
            
        Returns:
            bool: 是否成功连接。
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            logger.error("Link failed: Node ID not found.")
            return False
        
        if not (0.0 <= strength <= 1.0):
            raise ValueError("Connection strength must be between 0.0 and 1.0.")

        # 双向连接，模拟联想记忆
        self._nodes[source_id].neighbors[target_id] = strength
        self._nodes[target_id].neighbors[source_id] = strength
        logger.info("Linked %s <-> %s with strength %s", source_id, target_id, strength)
        return True

    def _calculate_dynamic_weight(self, node: MemoryNode) -> float:
        """
        [辅助函数] 计算节点的当前动态权重。
        
        结合基础权重和基于时间的衰减。这是实现'模糊性'的核心。
        Memory intensity = BaseWeight * e^(-lambda * dt)
        
        Args:
            node (MemoryNode): 记忆节点对象。
            
        Returns:
            float: 计算后的当前权重。
        """
        current_time = time.time()
        time_delta = current_time - node.last_accessed
        # 时间差越大，衰减越多
        decayed_weight = node.weight * math.exp(-self.decay_rate * time_delta / 3600) # 按小时衰减
        return max(0.01, min(1.0, decayed_weight))

    def query(self, keyword: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        核心功能：查询图谱并触发再巩固。
        
        搜索包含关键词的节点。找到后，会更新该节点的权重（再巩固），
        并微调与其相连的边。
        
        Args:
            keyword (str): 搜索关键词。
            top_k (int): 返回的最相关结果数量。
            
        Returns:
            List[Tuple[str, float]]: 返回内容和当前动态权重的列表。
        """
        if not keyword or not isinstance(keyword, str):
            raise ValueError("Keyword must be a non-empty string.")
            
        results: List[Tuple[MemoryNode, float]] = []
        
        for node in self._nodes.values():
            if keyword.lower() in node.content.lower():
                # 1. 计算当前时刻的动态强度
                current_intensity = self._calculate_dynamic_weight(node)
                results.append((node, current_intensity))

        if not results:
            logger.info("Query for '%s' found no results.", keyword)
            return []

        # 按强度排序
        results.sort(key=lambda x: x[1], reverse=True)
        top_results = results[:top_k]
        
        output_data = []
        current_time = time.time()

        # 2. 记忆再巩固 过程
        for node, intensity in top_results:
            logger.debug("Reconsolidating memory: %s", node.id)
            
            # 更新节点：刷新访问时间，提升基础权重
            node.last_accessed = current_time
            node.weight = min(1.0, node.weight + self.consolidation_factor)
            
            # 更新连接边：强化相关的连接（LTP - 长时程增强模拟）
            for neighbor_id in node.neighbors:
                if neighbor_id in self._nodes:
                    # 每次激活，连接强度微增
                    current_edge_strength = node.neighbors[neighbor_id]
                    new_strength = min(1.0, current_edge_strength + 0.05)
                    node.neighbors[neighbor_id] = new_strength
                    self._nodes[neighbor_id].neighbors[node.id] = new_strength
            
            output_data.append((node.content, intensity))

        logger.info("Query '%s' triggered reconsolidation on %d nodes.", keyword, len(top_results))
        return output_data

    def prune_network(self, threshold: float = 0.1):
        """
        清理僵化的知识。
        
        移除权重过低或连接强度过弱的边，模拟遗忘。
        """
        to_remove_edges = []
        count = 0
        
        for node in self._nodes.values():
            # 计算当前实际强度
            current_weight = self._calculate_dynamic_weight(node)
            if current_weight < threshold:
                # 标记节点为待遗忘（实际应用中可能只是归档，这里简单处理为重置权重）
                node.weight = 0.01
                logger.debug("Node %s weight dropped to minimal due to pruning.", node.id)

            # 检查边的强度
            neighbors_to_keep = {}
            for neighbor_id, strength in node.neighbors.items():
                if strength >= threshold:
                    neighbors_to_keep[neighbor_id] = strength
                else:
                    count += 1
            node.neighbors = neighbors_to_keep
            
        logger.info("Pruning complete. Weakened %d connections.", count)


# --- 使用示例 ---
if __name__ == "__main__":
    # 1. 初始化
    kg = ReconsolidatingKnowledgeGraph(decay_rate=0.1, consolidation_factor=0.2)
    
    # 2. 添加知识
    python_id = kg.add_node("Python is a high-level programming language.")
    java_id = kg.add_node("Java is a statically typed language.")
    ai_id = kg.add_node("Artificial Intelligence requires Python skills.")
    
    # 3. 建立关联
    kg.link_nodes(python_id, ai_id, strength=0.8)
    kg.link_nodes(java_id, ai_id, strength=0.3)
    
    print("\n--- Initial Query ---")
    # 第一次查询，触发再巩固
    results = kg.query("Python")
    for content, weight in results:
        print(f"Result: {content} (Retrieval Strength: {weight:.4f})")
        
    # 模拟时间流逝（实际应用中这里会是真实的等待）
    # 在实际代码中，time.time()会自动增加，这里为了演示逻辑，不需要sleep
    
    print("\n--- Second Query (Reinforcing) ---")
    # 再次查询，权重应该比上一次更高（因为被巩固了）
    results = kg.query("Python")
    for content, weight in results:
        print(f"Result: {content} (Retrieval Strength: {weight:.4f})")
        
    # 检查内部状态
    print(f"\nInternal weight of Python node: {kg._nodes[python_id].weight:.4f}")
    print(f"Edge strength Python<->AI: {kg._nodes[python_id].neighbors[ai_id]:.4f}")