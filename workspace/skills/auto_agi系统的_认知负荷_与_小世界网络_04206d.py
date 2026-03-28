"""
AGI系统的'认知负荷'与'小世界网络'优化模块

该模块实现了一个动态的小世界网络优化器，旨在解决AGI系统在处理海量节点时
面临的认知负荷问题。通过模仿人脑的小世界网络特性，在节点增长至数百万时
仍能保持'六度分隔'的高效检索能力。

核心功能：
1. 动态构建'高速路连接'（远距离强关联边）
2. 优化网络拓扑结构以降低平均路径长度
3. 防止认知搜索陷入局部最优解
4. 实时监控网络的小世界属性

输入输出格式：
- 输入：NetworkX图对象，需包含节点和边属性
- 输出：优化后的NetworkX图对象，包含新增的'highway'类型边

示例用法：
>>> G = nx.barabasi_albert_graph(1000, 3)
>>> optimizer = SmallWorldOptimizer()
>>> optimized_G = optimizer.optimize_network(G)
>>> optimizer.evaluate_network(optimized_G)
"""

import logging
import math
import random
from typing import Dict, List, Optional, Tuple, Set
import networkx as nx
from collections import deque

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SmallWorldOptimizer")

class SmallWorldOptimizer:
    """
    小世界网络优化器，实现动态高速路构建和网络拓扑优化
    
    该类通过添加少量长距离连接（高速路）来降低网络的平均路径长度，
    同时保持较高的聚类系数，从而实现小世界网络特性。
    
    Attributes:
        max_degree (int): 节点最大连接数限制，防止认知过载
        target_path_length (int): 目标平均路径长度（默认为6，符合六度分隔理论）
        highway_ratio (float): 高速路连接占总连接数的比例
        clustering_threshold (float): 聚类系数的最低阈值
    """
    
    def __init__(
        self,
        max_degree: int = 1000,
        target_path_length: int = 6,
        highway_ratio: float = 0.05,
        clustering_threshold: float = 0.3
    ) -> None:
        """
        初始化小世界网络优化器
        
        Args:
            max_degree: 节点最大连接数限制
            target_path_length: 目标平均路径长度
            highway_ratio: 高速路连接比例
            clustering_threshold: 聚类系数阈值
        """
        self._validate_init_params(max_degree, target_path_length, highway_ratio, clustering_threshold)
        self.max_degree = max_degree
        self.target_path_length = target_path_length
        self.highway_ratio = highway_ratio
        self.clustering_threshold = clustering_threshold
        logger.info("SmallWorldOptimizer initialized with max_degree=%d, target_path_length=%d", 
                    max_degree, target_path_length)
    
    def _validate_init_params(
        self,
        max_degree: int,
        target_path_length: int,
        highway_ratio: float,
        clustering_threshold: float
    ) -> None:
        """验证初始化参数的有效性"""
        if max_degree <= 0:
            raise ValueError("max_degree must be positive")
        if target_path_length <= 0:
            raise ValueError("target_path_length must be positive")
        if not 0 < highway_ratio < 1:
            raise ValueError("highway_ratio must be between 0 and 1")
        if not 0 < clustering_threshold <= 1:
            raise ValueError("clustering_threshold must be between 0 and 1")
    
    def optimize_network(self, G: nx.Graph, iterations: int = 5) -> nx.Graph:
        """
        优化网络拓扑结构以实现小世界特性
        
        通过动态添加高速路连接和优化现有连接，降低网络的平均路径长度，
        同时保持较高的聚类系数。
        
        Args:
            G: 输入的网络图
            iterations: 优化迭代次数
            
        Returns:
            nx.Graph: 优化后的网络图
            
        Raises:
            ValueError: 如果输入图无效或参数不合法
        """
        self._validate_network(G)
        
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        
        logger.info("Starting network optimization with %d iterations", iterations)
        
        try:
            # 创建图的副本以避免修改原图
            optimized_G = G.copy()
            
            # 记录初始网络指标
            initial_metrics = self._calculate_network_metrics(optimized_G)
            logger.info("Initial network metrics: %s", initial_metrics)
            
            for i in range(iterations):
                # 1. 识别需要优化的区域
                high_load_nodes = self._identify_high_load_nodes(optimized_G)
                
                # 2. 添加高速路连接
                self._add_highway_connections(optimized_G, high_load_nodes)
                
                # 3. 优化局部连接
                self._optimize_local_connections(optimized_G)
                
                # 计算当前指标
                current_metrics = self._calculate_network_metrics(optimized_G)
                logger.info("Iteration %d metrics: %s", i+1, current_metrics)
                
                # 检查是否达到目标
                if current_metrics['avg_path_length'] <= self.target_path_length:
                    logger.info("Target path length achieved at iteration %d", i+1)
                    break
            
            # 添加边类型属性
            for u, v in optimized_G.edges():
                if 'type' not in optimized_G[u][v]:
                    optimized_G[u][v]['type'] = 'regular'
            
            return optimized_G
            
        except Exception as e:
            logger.error("Error during network optimization: %s", str(e))
            raise RuntimeError(f"Network optimization failed: {str(e)}") from e
    
    def evaluate_network(self, G: nx.Graph) -> Dict[str, float]:
        """
        评估网络的小世界特性
        
        计算并返回网络的关键指标，包括：
        - 平均路径长度
        - 聚类系数
        - 网络密度
        - 高速路连接比例
        
        Args:
            G: 要评估的网络图
            
        Returns:
            Dict[str, float]: 包含网络指标的字典
        """
        self._validate_network(G)
        
        try:
            metrics = self._calculate_network_metrics(G)
            
            # 添加小世界特性评估
            metrics['small_world_coefficient'] = self._calculate_small_world_coefficient(
                metrics['clustering_coefficient'],
                metrics['avg_path_length']
            )
            
            # 评估是否达到六度分隔
            metrics['meets_six_degrees'] = metrics['avg_path_length'] <= self.target_path_length
            
            logger.info("Network evaluation results: %s", metrics)
            return metrics
            
        except Exception as e:
            logger.error("Error during network evaluation: %s", str(e))
            raise RuntimeError(f"Network evaluation failed: {str(e)}") from e
    
    def _validate_network(self, G: nx.Graph) -> None:
        """验证输入网络的有效性"""
        if not isinstance(G, nx.Graph):
            raise TypeError("Input must be a NetworkX Graph")
        if len(G.nodes()) == 0:
            raise ValueError("Network has no nodes")
    
    def _calculate_network_metrics(self, G: nx.Graph) -> Dict[str, float]:
        """计算网络的关键指标"""
        # 使用采样方法计算大网络的平均路径长度
        if len(G.nodes()) > 1000:
            sample_size = min(100, len(G.nodes()))
            sampled_nodes = random.sample(list(G.nodes()), sample_size)
            path_lengths = []
            for node in sampled_nodes:
                lengths = nx.single_source_shortest_path_length(G, node)
                path_lengths.extend([l for l in lengths.values() if l > 0])
            avg_path_length = sum(path_lengths) / len(path_lengths) if path_lengths else 0
        else:
            avg_path_length = nx.average_shortest_path_length(G)
        
        return {
            'node_count': len(G.nodes()),
            'edge_count': len(G.edges()),
            'avg_path_length': avg_path_length,
            'clustering_coefficient': nx.average_clustering(G),
            'network_density': nx.density(G),
            'highway_ratio': self._calculate_highway_ratio(G)
        }
    
    def _calculate_highway_ratio(self, G: nx.Graph) -> float:
        """计算网络中高速路连接的比例"""
        if len(G.edges()) == 0:
            return 0.0
        
        highway_edges = 0
        for u, v, data in G.edges(data=True):
            if data.get('type') == 'highway':
                highway_edges += 1
        
        return highway_edges / len(G.edges())
    
    def _calculate_small_world_coefficient(self, clustering: float, path_length: float) -> float:
        """
        计算小世界系数
        
        小世界系数是聚类系数与平均路径长度的比值，值越大表示小世界特性越明显
        """
        if path_length == 0:
            return 0.0
        return clustering / path_length
    
    def _identify_high_load_nodes(self, G: nx.Graph) -> List[int]:
        """
        识别高负载节点，这些节点需要优先优化连接
        
        高负载节点通常具有高介数中心性，是网络中的关键枢纽
        """
        if len(G.nodes()) == 0:
            return []
        
        # 使用采样方法计算大网络的介数中心性
        if len(G.nodes()) > 1000:
            k = min(100, len(G.nodes()))
            betweenness = nx.betweenness_centrality(G, k=k)
        else:
            betweenness = nx.betweenness_centrality(G)
        
        # 选择介数中心性最高的节点
        top_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
        top_count = max(1, int(len(top_nodes) * 0.1))  # 取前10%的节点
        return [node for node, _ in top_nodes[:top_count]]
    
    def _add_highway_connections(self, G: nx.Graph, high_load_nodes: List[int]) -> None:
        """
        添加高速路连接以减少平均路径长度
        
        高速路连接是连接网络中远距离节点的边，可以显著降低平均路径长度
        """
        if len(high_load_nodes) < 2:
            return
        
        # 计算需要添加的高速路连接数量
        current_edges = len(G.edges())
        target_highway_edges = int(current_edges * self.highway_ratio)
        current_highway_edges = sum(1 for _, _, data in G.edges(data=True) if data.get('type') == 'highway')
        edges_to_add = max(0, target_highway_edges - current_highway_edges)
        
        if edges_to_add == 0:
            return
        
        logger.info("Adding %d highway connections", edges_to_add)
        
        # 在高负载节点之间添加高速路连接
        added = 0
        attempts = 0
        max_attempts = edges_to_add * 3
        
        while added < edges_to_add and attempts < max_attempts:
            # 随机选择两个高负载节点
            u, v = random.sample(high_load_nodes, 2)
            
            # 确保节点不同且尚未连接
            if u != v and not G.has_edge(u, v):
                # 添加高速路连接
                G.add_edge(u, v, type='highway', weight=1.0)
                added += 1
            
            attempts += 1
    
    def _optimize_local_connections(self, G: nx.Graph) -> None:
        """
        优化局部连接以提高聚类系数
        
        在聚类系数低的区域添加连接，形成更多的三角形结构
        """
        if len(G.nodes()) < 3:
            return
        
        # 找出聚类系数低于阈值的节点
        low_clustering_nodes = [
            node for node in G.nodes()
            if nx.clustering(G, node) < self.clustering_threshold
        ]
        
        if not low_clustering_nodes:
            return
        
        logger.info("Optimizing local connections for %d low clustering nodes", 
                    len(low_clustering_nodes))
        
        # 对每个低聚类系数节点，尝试连接其邻居的邻居
        for node in low_clustering_nodes:
            neighbors = set(G.neighbors(node))
            second_neighbors = set()
            
            # 收集二跳邻居
            for neighbor in neighbors:
                second_neighbors.update(G.neighbors(neighbor))
            
            # 移除已连接的节点
            second_neighbors -= neighbors
            second_neighbors.discard(node)
            
            # 随机连接一些二跳邻居
            possible_edges = min(3, len(second_neighbors))
            if possible_edges > 0:
                for neighbor in random.sample(list(second_neighbors), possible_edges):
                    if not G.has_edge(node, neighbor):
                        G.add_edge(node, neighbor, type='local_optimization', weight=0.5)
    
    def get_cognitive_load(self, G: nx.Graph, node: int) -> float:
        """
        计算特定节点的认知负荷
        
        认知负荷由节点的连接数和连接的强度决定
        """
        if node not in G:
            raise ValueError(f"Node {node} not in graph")
        
        degree = G.degree(node)
        if degree == 0:
            return 0.0
        
        # 考虑边的权重和类型
        load = 0.0
        for _, neighbor, data in G.edges(node, data=True):
            weight = data.get('weight', 1.0)
            edge_type = data.get('type', 'regular')
            
            # 高速路连接产生更高的认知负荷
            if edge_type == 'highway':
                weight *= 1.5
            elif edge_type == 'local_optimization':
                weight *= 0.8
            
            load += weight
        
        # 归一化到0-1范围
        normalized_load = min(1.0, load / self.max_degree)
        return normalized_load

# 使用示例
if __name__ == "__main__":
    import networkx as nx
    
    # 创建一个随机网络
    print("Creating initial network...")
    G = nx.barabasi_albert_graph(1000, 3)
    
    # 初始化优化器
    optimizer = SmallWorldOptimizer(
        max_degree=500,
        target_path_length=6,
        highway_ratio=0.05
    )
    
    # 评估初始网络
    print("\nInitial network metrics:")
    initial_metrics = optimizer.evaluate_network(G)
    for metric, value in initial_metrics.items():
        print(f"{metric}: {value:.4f}")
    
    # 优化网络
    print("\nOptimizing network...")
    optimized_G = optimizer.optimize_network(G, iterations=3)
    
    # 评估优化后的网络
    print("\nOptimized network metrics:")
    final_metrics = optimizer.evaluate_network(optimized_G)
    for metric, value in final_metrics.items():
        print(f"{metric}: {value:.4f}")
    
    # 计算特定节点的认知负荷
    high_degree_nodes = sorted(optimized_G.degree(), key=lambda x: x[1], reverse=True)[:3]
    print("\nCognitive load for top 3 high-degree nodes:")
    for node, degree in high_degree_nodes:
        load = optimizer.get_cognitive_load(optimized_G, node)
        print(f"Node {node} (degree {degree}): cognitive load = {load:.4f}")