"""
模块名称: auto_记忆压缩与检索效率_随着719个节点增长_581e11
描述: 实现分层记忆索引机制，支持高频节点优先检索和低频节点归档。
      针对大规模节点（从719个扩展到百万级）的检索性能优化。
作者: 高级Python工程师
日期: 2023-10-27
版本: 1.0.0
"""

import logging
import math
import time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from heapq import heappush, heappop

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass(order=True)
class MemoryNode:
    """
    记忆节点数据结构。
    
    属性:
        id (str): 节点唯一标识符
        content (str): 记忆内容
        embedding (List[float]): 向量嵌入表示
        access_count (int): 访问次数，用于计算热度
        last_access (float): 最后访问时间戳
        priority (float): 排序优先级，由access_count和last_access计算得出
    """
    id: str
    content: str
    embedding: List[float] = field(compare=False)
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    priority: float = field(init=False)

    def __post_init__(self):
        """初始化后计算优先级"""
        self.update_priority()

    def update_priority(self) -> None:
        """更新节点优先级，结合访问频次和时间衰减"""
        # 简单的优先级算法: 访问次数 * 时间衰减因子
        # 这里使用对数函数平滑访问次数的影响，防止差距过大
        time_decay = 1.0 / (1.0 + (time.time() - self.last_access) / 3600.0)  # 每小时衰减
        self.priority = math.log1p(self.access_count) * time_decay

    def touch(self) -> None:
        """更新访问时间和计数"""
        self.access_count += 1
        self.last_access = time.time()
        self.update_priority()

class HierarchicalMemoryIndex:
    """
    分层记忆索引系统。
    
    实现高频节点（热数据）和低频节点（冷数据）的分层管理。
    热数据保持在快速检索层（内存优先队列），冷数据归档但仍可检索。
    
    属性:
        hot_capacity (int): 热数据层容量
        hot_nodes (List[Tuple[float, str]]): 热数据堆结构 (priority, node_id)
        node_map (Dict[str, MemoryNode]): 节点ID到节点的映射
        archive_map (Dict[str, MemoryNode]): 归档节点映射 (模拟冷存储)
    """

    def __init__(self, hot_capacity: int = 1000):
        """
        初始化分层索引。
        
        参数:
            hot_capacity (int): 热数据层最大容量，默认1000
        """
        if hot_capacity <= 0:
            logger.error("热数据层容量必须大于0")
            raise ValueError("热数据层容量必须大于0")
            
        self.hot_capacity = hot_capacity
        self.hot_nodes: List[Tuple[float, str]] = []  # 最小堆，存储(优先级, ID)
        self.node_map: Dict[str, MemoryNode] = {}     # 所有节点的快速查找表
        self.archive_map: Dict[str, MemoryNode] = {}  # 归档节点存储
        logger.info(f"分层记忆索引初始化完成，热数据容量: {hot_capacity}")

    def add_node(self, node: MemoryNode) -> None:
        """
        添加节点到索引系统。
        
        参数:
            node (MemoryNode): 待添加的记忆节点
            
        异常:
            ValueError: 如果节点ID已存在或数据无效
        """
        if not node.id or not node.embedding:
            logger.error("节点ID或嵌入向量不能为空")
            raise ValueError("无效的节点数据")
            
        if node.id in self.node_map:
            logger.warning(f"节点ID {node.id} 已存在，更新节点")
            self._update_existing_node(node)
            return

        # 添加到主映射
        self.node_map[node.id] = node
        
        # 尝试添加到热数据层
        if len(self.hot_nodes) < self.hot_capacity:
            heappush(self.hot_nodes, (node.priority, node.id))
            logger.debug(f"节点 {node.id} 添加到热数据层")
        else:
            # 如果热数据层已满，与最小元素比较
            if node.priority > self.hot_nodes[0][0]:
                # 移除最小元素到归档
                removed_priority, removed_id = heappop(self.hot_nodes)
                self._archive_node(removed_id)
                # 添加新节点到热数据层
                heappush(self.hot_nodes, (node.priority, node.id))
                logger.debug(f"节点 {node.id} 替换进入热数据层，节点 {removed_id} 被归档")
            else:
                # 直接归档
                self._archive_node(node.id)
                logger.debug(f"节点 {node.id} 直接归档")

    def retrieve(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        检索与查询向量最匹配的节点。
        
        优先检索热数据层，必要时检索归档数据。
        使用简化的余弦相似度计算。
        
        参数:
            query_embedding (List[float]): 查询向量
            top_k (int): 返回的最大结果数
            
        返回:
            List[Dict[str, Any]]: 匹配结果列表，包含节点ID、内容和相似度
            
        异常:
            ValueError: 如果查询向量无效
        """
        if not query_embedding:
            logger.error("查询向量不能为空")
            raise ValueError("无效的查询向量")
            
        if top_k <= 0:
            logger.warning("top_k必须大于0，已自动设置为1")
            top_k = 1

        start_time = time.time()
        results: List[Dict[str, Any]] = []
        
        # 1. 检索热数据层
        hot_candidates = self._search_heap(query_embedding)
        
        # 2. 如果热数据不足，检索归档数据 (模拟部分检索，实际生产中可能使用向量数据库)
        if len(hot_candidates) < top_k and self.archive_map:
            archive_candidates = self._search_archive(query_embedding)
            hot_candidates.extend(archive_candidates)
        
        # 3. 合并并排序结果
        hot_candidates.sort(key=lambda x: x['similarity'], reverse=True)
        results = hot_candidates[:top_k]
        
        # 4. 更新命中节点的访问状态
        for res in results:
            node = self.node_map.get(res['id'])
            if node:
                node.touch()
                # 如果节点在归档中但变得热门，重新提升 (简化逻辑)
                if node.id in self.archive_map and len(self.hot_nodes) < self.hot_capacity:
                    self._promote_from_archive(node.id)

        query_time = (time.time() - start_time) * 1000
        logger.info(f"检索完成，返回 {len(results)} 个结果，耗时 {query_time:.2f}ms")
        return results

    def _archive_node(self, node_id: str) -> None:
        """将节点移动到归档区"""
        if node_id in self.node_map:
            node = self.node_map[node_id]
            self.archive_map[node_id] = node
            # 注意：这里不将其从 node_map 移除，因为需要保持全局可访问性
            # 在真实场景中，归档可能意味着移动到磁盘或分布式存储

    def _promote_from_archive(self, node_id: str) -> None:
        """从归档区提升节点回热数据层"""
        if node_id in self.archive_map:
            node = self.archive_map.pop(node_id)
            if len(self.hot_nodes) < self.hot_capacity:
                heappush(self.hot_nodes, (node.priority, node.id))
                logger.debug(f"节点 {node_id} 从归档提升回热数据层")

    def _update_existing_node(self, node: MemoryNode) -> None:
        """更新已存在的节点"""
        existing_node = self.node_map[node.id]
        existing_node.content = node.content
        existing_node.embedding = node.embedding
        existing_node.touch()
        # 注意：更新优先级后，堆结构可能需要重建，这里简化处理
        # 实际生产中可能需要更复杂的堆更新逻辑或延迟更新

    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _search_heap(self, query_embedding: List[float]) -> List[Dict[str, Any]]:
        """在热数据堆中检索"""
        candidates = []
        # 堆不直接支持随机访问，这里为了演示遍历堆
        # 在实际大数据量场景中，热数据层通常会维护一个并行的向量索引（如HNSW）
        for _, node_id in self.hot_nodes:
            node = self.node_map.get(node_id)
            if node:
                similarity = self._calculate_similarity(query_embedding, node.embedding)
                candidates.append({
                    'id': node.id,
                    'content': node.content,
                    'similarity': similarity
                })
        return candidates

    def _search_archive(self, query_embedding: List[float]) -> List[Dict[str, Any]]:
        """在归档数据中检索 (模拟)"""
        candidates = []
        # 这里仅模拟检索部分归档数据以节省资源
        # 实际中会使用 ANN (Approximate Nearest Neighbor) 算法
        limit = min(len(self.archive_map), 100)  # 限制扫描数量
        for i, (node_id, node) in enumerate(self.archive_map.items()):
            if i >= limit:
                break
            similarity = self._calculate_similarity(query_embedding, node.embedding)
            candidates.append({
                'id': node.id,
                'content': node.content,
                'similarity': similarity
            })
        return candidates

# 辅助函数
def generate_mock_embedding(dim: int = 128) -> List[float]:
    """
    生成模拟的向量嵌入。
    
    参数:
        dim (int): 向量维度
        
    返回:
        List[float]: 随机生成的向量
    """
    import random
    return [random.gauss(0, 1) for _ in range(dim)]

def benchmark_index_performance(node_counts: List[int]) -> None:
    """
    基准测试索引性能。
    
    参数:
        node_counts (List[int]): 要测试的节点数量列表
    """
    logger.info("开始性能基准测试...")
    for count in node_counts:
        index = HierarchicalMemoryIndex(hot_capacity=max(100, count // 10))
        
        # 插入数据
        start_time = time.time()
        for i in range(count):
            node = MemoryNode(
                id=f"node_{i}",
                content=f"测试内容 {i}",
                embedding=generate_mock_embedding()
            )
            index.add_node(node)
        insert_time = (time.time() - start_time) * 1000
        
        # 检索数据
        query = generate_mock_embedding()
        start_time = time.time()
        results = index.retrieve(query, top_k=5)
        query_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"节点数: {count:>} | "
            f"插入耗时: {insert_time:.2f}ms | "
            f"检索耗时: {query_time:.2f}ms | "
            f"热数据层大小: {len(index.hot_nodes)}"
        )

if __name__ == "__main__":
    # 使用示例
    try:
        # 1. 初始化索引
        memory_index = HierarchicalMemoryIndex(hot_capacity=50)
        
        # 2. 添加节点
        nodes_to_add = [
            MemoryNode("skill_001", "Python编程", generate_mock_embedding()),
            MemoryNode("skill_002", "数据分析", generate_mock_embedding()),
            MemoryNode("skill_003", "机器学习", generate_mock_embedding()),
        ]
        
        for node in nodes_to_add:
            memory_index.add_node(node)
        
        # 3. 模拟访问以提升优先级
        target_node = memory_index.node_map["skill_001"]
        for _ in range(10):
            target_node.touch()  # 增加热度
        
        # 4. 检索
        query_vec = generate_mock_embedding()
        retrieved = memory_index.retrieve(query_vec, top_k=2)
        
        print("\n检索结果示例:")
        for res in retrieved:
            print(f"ID: {res['id']}, 内容: {res['content']}, 相似度: {res['similarity']:.4f}")
            
        # 5. 性能测试 (模拟从719节点增长)
        print("\n性能基准测试 (模拟规模增长):")
        benchmark_index_performance([100, 719, 2000, 5000])
        
    except Exception as e:
        logger.error(f"运行示例时发生错误: {e}", exc_info=True)