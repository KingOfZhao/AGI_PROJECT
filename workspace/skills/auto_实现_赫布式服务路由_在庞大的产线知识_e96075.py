"""
模块名称: hebbian_service_router
描述: 实现基于赫布学习理论的产线知识图谱动态路由系统。
      系统通过观察服务调用模式，自动优化高频路径的访问性能。

数据输入格式:
    - 调用记录: {"source": "问题节点ID", "target": "解决方案节点ID", "timestamp": int}
    - 知识图谱: 网络X图对象，节点包含"latency"属性，边包含"weight"属性

数据输出格式:
    - 路由决策: {"path": ["node1", "node2"], "total_latency": float, "confidence": float}
"""

import time
import logging
import heapq
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field

import networkx as nx

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RouterConfig:
    """路由器配置参数"""
    learning_rate: float = 0.1  # 赫布学习率
    decay_rate: float = 0.01   # 权重衰减率
    min_weight: float = 0.1    # 最小连接权重
    max_weight: float = 10.0   # 最大连接权重
    cache_threshold: int = 5   # 触发缓存的调用次数阈值
    max_path_length: int = 10  # 最大路径搜索深度


class HebbianKnowledgeGraph:
    """基于赫布理论的产线知识图谱路由系统
    
    属性:
        graph (nx.DiGraph): 有向知识图谱
        config (RouterConfig): 配置参数
        call_history (List[Tuple[str, str]]): 调用历史记录
        node_cache (Dict[str, Any]): 热点节点缓存
    """
    
    def __init__(self, config: Optional[RouterConfig] = None):
        """初始化赫布知识图谱
        
        参数:
            config: 路由器配置，如果为None则使用默认配置
        """
        self.graph = nx.DiGraph()
        self.config = config if config else RouterConfig()
        self.call_history = []
        self.node_cache = {}
        self._initialize_graph()
        
    def _initialize_graph(self) -> None:
        """初始化示例知识图谱结构"""
        # 添加问题节点
        problems = [
            ("p1", {"type": "problem", "desc": "电机过热", "latency": 0.8}),
            ("p2", {"type": "problem", "desc": "传送带卡顿", "latency": 0.5}),
            ("p3", {"type": "problem", "desc": "传感器故障", "latency": 0.6})
        ]
        
        # 添加解决方案节点
        solutions = [
            ("s1", {"type": "solution", "desc": "检查冷却系统", "latency": 1.2}),
            ("s2", {"type": "solution", "desc": "调整皮带张力", "latency": 0.9}),
            ("s3", {"type": "solution", "desc": "更换传感器", "latency": 1.0})
        ]
        
        # 添加中间节点
        intermediates = [
            ("i1", {"type": "intermediate", "desc": "电机诊断", "latency": 0.3}),
            ("i2", {"type": "intermediate", "desc": "传送带诊断", "latency": 0.4})
        ]
        
        self.graph.add_nodes_from(problems)
        self.graph.add_nodes_from(solutions)
        self.graph.add_nodes_from(intermediates)
        
        # 添加初始边
        edges = [
            ("p1", "i1", {"weight": 1.0}),
            ("p1", "s1", {"weight": 0.5}),
            ("p2", "i2", {"weight": 1.0}),
            ("i1", "s1", {"weight": 1.0}),
            ("i2", "s2", {"weight": 1.0}),
            ("p3", "s3", {"weight": 1.0}),
            ("p2", "s3", {"weight": 0.3})
        ]
        self.graph.add_edges_from(edges)
        
        logger.info("Initialized knowledge graph with %d nodes and %d edges", 
                   len(self.graph.nodes), len(self.graph.edges))
    
    def record_call(self, source: str, target: str) -> None:
        """记录服务调用并更新连接权重
        
        参数:
            source: 源节点ID
            target: 目标节点ID
            
        异常:
            ValueError: 如果节点不存在
        """
        if source not in self.graph or target not in self.graph:
            logger.error("Attempt to record call with non-existent nodes: %s -> %s", source, target)
            raise ValueError("Source or target node does not exist")
            
        self.call_history.append((source, target))
        self._update_hebbian_weights(source, target)
        
        # 检查是否达到缓存阈值
        call_count = self._count_calls(source, target)
        if call_count >= self.config.cache_threshold:
            self._add_to_cache(source, target)
            
        logger.debug("Recorded call from %s to %s (count: %d)", source, target, call_count)
    
    def _update_hebbian_weights(self, source: str, target: str) -> None:
        """基于赫布理论更新连接权重
        
        参数:
            source: 源节点ID
            target: 目标节点ID
        """
        if not self.graph.has_edge(source, target):
            self.graph.add_edge(source, target, weight=self.config.min_weight)
            logger.info("Created new edge from %s to %s", source, target)
        
        # 赫布学习规则: weight += learning_rate * (1 - weight)
        current_weight = self.graph.edges[source, target]["weight"]
        new_weight = current_weight + self.config.learning_rate * (1 - current_weight)
        
        # 应用权重衰减到其他边
        self._apply_weight_decay(source, target)
        
        # 更新权重并确保在范围内
        new_weight = max(self.config.min_weight, min(self.config.max_weight, new_weight))
        self.graph.edges[source, target]["weight"] = new_weight
        
        logger.debug("Updated edge %s->%s weight: %.2f -> %.2f", 
                    source, target, current_weight, new_weight)
    
    def _apply_weight_decay(self, exclude_source: str, exclude_target: str) -> None:
        """对所有边应用权重衰减，除了指定的边
        
        参数:
            exclude_source: 排除的源节点ID
            exclude_target: 排除的目标节点ID
        """
        for u, v, data in self.graph.edges(data=True):
            if u == exclude_source and v == exclude_target:
                continue
                
            data["weight"] = max(
                self.config.min_weight,
                data["weight"] - self.config.decay_rate
            )
    
    def _count_calls(self, source: str, target: str) -> int:
        """计算特定路径的调用次数
        
        参数:
            source: 源节点ID
            target: 目标节点ID
            
        返回:
            调用次数
        """
        return sum(1 for s, t in self.call_history if s == source and t == target)
    
    def _add_to_cache(self, source: str, target: str) -> None:
        """将路径添加到缓存
        
        参数:
            source: 源节点ID
            target: 目标节点ID
        """
        cache_key = f"{source}->{target}"
        if cache_key not in self.node_cache:
            path = self.find_optimal_path(source, target)
            if path:
                self.node_cache[cache_key] = {
                    "path": path,
                    "timestamp": time.time(),
                    "call_count": self._count_calls(source, target)
                }
                logger.info("Added path %s to cache", cache_key)
    
    def find_optimal_path(self, source: str, target: str) -> Optional[List[str]]:
        """使用改进的Dijkstra算法寻找最优路径
        
        参数:
            source: 源节点ID
            target: 目标节点ID
            
        返回:
            最优路径节点列表，如果找不到则返回None
            
        异常:
            ValueError: 如果节点不存在
        """
        if source not in self.graph or target not in self.graph:
            logger.error("Path search with non-existent nodes: %s -> %s", source, target)
            raise ValueError("Source or target node does not exist")
            
        # 检查缓存
        cache_key = f"{source}->{target}"
        if cache_key in self.node_cache:
            logger.debug("Using cached path for %s", cache_key)
            return self.node_cache[cache_key]["path"]
        
        # 使用优先队列实现Dijkstra算法
        heap = []
        heapq.heappush(heap, (0, source, []))
        visited = set()
        
        while heap:
            current_cost, current_node, path = heapq.heappop(heap)
            
            if current_node in visited:
                continue
                
            visited.add(current_node)
            new_path = path + [current_node]
            
            if current_node == target:
                logger.info("Found optimal path %s with cost %.2f", new_path, current_cost)
                return new_path
                
            if len(new_path) >= self.config.max_path_length:
                continue
                
            for neighbor in self.graph.neighbors(current_node):
                if neighbor not in visited:
                    edge_data = self.graph.edges[current_node, neighbor]
                    node_data = self.graph.nodes[neighbor]
                    
                    # 计算综合成本: 延迟/权重
                    cost = current_cost + (node_data["latency"] / edge_data["weight"])
                    heapq.heappush(heap, (cost, neighbor, new_path))
        
        logger.warning("No path found from %s to %s", source, target)
        return None
    
    def get_path_latency(self, path: List[str]) -> float:
        """计算路径总延迟
        
        参数:
            path: 节点ID列表
            
        返回:
            总延迟时间
            
        异常:
            ValueError: 如果路径无效
        """
        if not path or len(path) < 2:
            raise ValueError("Invalid path")
            
        total_latency = 0.0
        for i in range(len(path) - 1):
            source, target = path[i], path[i+1]
            if not self.graph.has_edge(source, target):
                raise ValueError(f"No edge between {source} and {target}")
                
            node_latency = self.graph.nodes[target]["latency"]
            edge_weight = self.graph.edges[source, target]["weight"]
            total_latency += node_latency / edge_weight
            
        return total_latency
    
    def get_path_confidence(self, path: List[str]) -> float:
        """计算路径的置信度(基于权重)
        
        参数:
            path: 节点ID列表
            
        返回:
            路径置信度(0-1)
        """
        if not path or len(path) < 2:
            return 0.0
            
        weights = []
        for i in range(len(path) - 1):
            source, target = path[i], path[i+1]
            if self.graph.has_edge(source, target):
                weights.append(self.graph.edges[source, target]["weight"])
        
        if not weights:
            return 0.0
            
        # 置信度计算为平均权重归一化
        avg_weight = sum(weights) / len(weights)
        return min(1.0, avg_weight / self.config.max_weight)


# 使用示例
if __name__ == "__main__":
    # 初始化路由器
    config = RouterConfig(learning_rate=0.2, cache_threshold=3)
    router = HebbianKnowledgeGraph(config)
    
    # 模拟服务调用
    print("模拟服务调用...")
    for _ in range(5):
        router.record_call("p1", "i1")
        router.record_call("i1", "s1")
    
    # 查找最优路径
    print("\n查找最优路径:")
    path = router.find_optimal_path("p1", "s1")
    if path:
        print(f"最优路径: {path}")
        print(f"总延迟: {router.get_path_latency(path):.2f}")
        print(f"置信度: {router.get_path_confidence(path):.2f}")
    
    # 测试新路径学习
    print("\n测试新路径学习:")
    router.record_call("p2", "s3")
    path = router.find_optimal_path("p2", "s3")
    print(f"新路径: {path}")
    
    # 检查缓存
    print("\n缓存内容:")
    for key, value in router.node_cache.items():
        print(f"{key}: {value}")