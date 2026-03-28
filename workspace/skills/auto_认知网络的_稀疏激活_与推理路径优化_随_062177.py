"""
高级Python模块：认知网络的稀疏激活与推理路径优化
Name: auto_认知网络的_稀疏激活_与推理路径优化_随_062177
Description: 实现基于稀疏激活机制的认知子网络动态构建与推理路径优化。
             针对大规模节点网络（191+），通过模拟人脑的稀疏激活机制，
             仅激活与当前上下文（'四向碰撞'场景）最相关的子图进行推理。
Author: Senior Python Engineer (AGI System)
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import heapq
from typing import Dict, List, Set, Tuple, Optional, Any
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CognitiveGraph:
    """
    认知图谱类，用于管理节点、边及其激活状态。
    """
    def __init__(self, node_count: int, edge_probability: float = 0.05):
        """
        初始化认知图谱。
        
        Args:
            node_count (int): 节点总数。
            edge_probability (float): 随机生成图的边连接概率（稀疏矩阵）。
        """
        if node_count < 1:
            raise ValueError("节点数量必须大于0")
        
        self.node_count = node_count
        # 使用邻接表存储稀疏图结构: {node_id: [neighbor_ids]}
        self.adjacency: Dict[int, List[int]] = {i: [] for i in range(node_count)}
        # 模拟节点特征向量的维度
        self.embedding_dim = 128
        # 随机初始化节点特征 (float32以节省内存)
        self.embeddings: np.ndarray = np.random.randn(node_count, self.embedding_dim).astype(np.float32)
        
        # 随机生成稀疏连接
        self._generate_sparse_edges(edge_probability)
        logger.info(f"初始化认知图谱: {node_count}个节点, 平均度数约为 {int(node_count * edge_probability)}")

    def _generate_sparse_edges(self, prob: float):
        """辅助函数：随机生成稀疏边"""
        for i in range(self.node_count):
            for j in range(i + 1, self.node_count):
                if np.random.rand() < prob:
                    self.adjacency[i].append(j)
                    self.adjacency[j].append(i)

def validate_context_input(context_nodes: List[int], graph_size: int) -> None:
    """
    辅助函数：验证输入的上下文节点是否有效。
    
    Args:
        context_nodes (List[int]): 当前激活的上下文节点列表（如'四向碰撞'涉及的节点）。
        graph_size (int): 图的总节点数。
        
    Raises:
        ValueError: 如果输入为空或节点ID越界。
    """
    if not context_nodes:
        logger.error("上下文节点列表不能为空")
        raise ValueError("上下文节点列表不能为空")
    
    if not all(0 <= node < graph_size for node in context_nodes):
        logger.error(f"节点ID越界，有效范围是 0 到 {graph_size - 1}")
        raise ValueError("检测到无效的节点ID")

def sparse_activate_subgraph(
    graph: CognitiveGraph, 
    context_nodes: List[int], 
    activation_threshold: float = 0.3, 
    max_hops: int = 3
) -> Tuple[Set[int], Dict[int, float]]:
    """
    核心函数1：稀疏激活子图。
    
    根据输入的初始上下文节点（模拟外界刺激），基于特征相似度和拓扑距离
    动态传播激活信号，构建局部认知子网络。
    
    Args:
        graph (CognitiveGraph): 认知图谱实例。
        context_nodes (List[int]): 初始的高亮节点（例如感知输入）。
        activation_threshold (float): 激活阈值，低于此值的节点不被激活。
        max_hops (int): 信号传播的最大跳数。
        
    Returns:
        Tuple[Set[int], Dict[int, float]]: 
            - 激活的节点ID集合。
            - 节点ID到其最终激活能量的映射。
            
    Example:
        >>> g = CognitiveGraph(200)
        >>> active_nodes, energies = sparse_activate_subgraph(g, [0, 5, 10])
    """
    validate_context_input(context_nodes, graph.node_count)
    
    logger.info(f"开始稀疏激活，种子节点: {context_nodes}")
    
    # 初始化激活能量
    current_activations: Dict[int, float] = {n: 1.0 for n in context_nodes}
    visited: Set[int] = set(context_nodes)
    
    # 使用BFS策略传播激活（模拟信号扩散）
    queue = [(n, 0) for n in context_nodes] # (node_id, current_hop)
    
    while queue:
        curr_node, curr_hop = queue.pop(0)
        
        if curr_hop >= max_hops:
            continue
            
        # 计算当前节点的特征向量，用于相似度计算
        curr_vec = graph.embeddings[curr_node]
        
        for neighbor in graph.adjacency[curr_node]:
            if neighbor not in visited:
                # 模拟衰减：随着距离增加，能量衰减
                distance_decay = 1.0 / (curr_hop + 1)
                
                # 模拟关联强度：基于余弦相似度
                neighbor_vec = graph.embeddings[neighbor]
                similarity = np.dot(curr_vec, neighbor_vec) / (np.linalg.norm(curr_vec) * np.linalg.norm(neighbor_vec) + 1e-8)
                
                # 计算传入能量
                incoming_energy = current_activations[curr_node] * distance_decay * max(0, similarity)
                
                if incoming_energy > activation_threshold:
                    visited.add(neighbor)
                    current_activations[neighbor] = current_activations.get(neighbor, 0) + incoming_energy
                    queue.append((neighbor, curr_hop + 1))
    
    logger.info(f"激活完成，共激活 {len(visited)} 个节点（总节点数 {graph.node_count}）")
    return visited, current_activations

def optimize_reasoning_path(
    graph: CognitiveGraph, 
    active_nodes: Set[int], 
    activations: Dict[int, float], 
    start_node: int, 
    end_node: int
) -> List[int]:
    """
    核心函数2：优化推理路径。
    
    在激活的稀疏子图中，寻找一条从start_node到end_node的路径，
    该路径旨在最大化路径上的激活能量（语义相关性）并最小化路径长度。
    这模拟了AGI在处理'四向碰撞'时如何在不同概念间建立高权重的逻辑链路。
    
    Args:
        graph (CognitiveGraph): 认知图谱实例。
        active_nodes (Set[int]): 稀疏激活函数返回的活跃节点集合。
        activations (Dict[int, float]): 节点的激活能量。
        start_node (int): 推理起点。
        end_node (int): 推理终点。
        
    Returns:
        List[int]: 优化后的节点路径列表。如果无法到达，返回空列表。
        
    Raises:
        ValueError: 如果起点或终点不在激活子网中。
        
    Example:
        >>> path = optimize_reasoning_path(g, active_nodes, energies, 0, 15)
    """
    if start_node not in active_nodes or end_node not in active_nodes:
        logger.warning("起点或终点未在稀疏激活范围内，无法进行局部推理。")
        # 在实际AGI中，这可能触发重新激活或全图检索，这里简单处理
        raise ValueError("推理端点必须位于激活的子网络中")

    logger.info(f"开始路径优化: {start_node} -> {end_node}")
    
    # 使用优先队列的Dijkstra变种
    # 优先级指标 = 路径累积成本。我们希望成本最小。
    # 成本定义：1 / (activation + epsilon) - 激活度越高，成本越低
    # 同时考虑拓扑距离权重
    
    priority_queue = [(0.0, start_node, [])] # (cost, current_node, path)
    visited_costs: Dict[int, float] = {start_node: 0.0}
    
    while priority_queue:
        cost, current, path = heapq.heappop(priority_queue)
        
        if current == end_node:
            logger.info(f"找到优化路径，长度: {len(path)}, 总成本: {cost:.4f}")
            return path + [current]
        
        if cost > visited_costs.get(current, float('inf')):
            continue
            
        temp_path = path + [current]
        
        for neighbor in graph.adjacency[current]:
            if neighbor in active_nodes:
                # 只有在稀疏激活集合中的节点才被视为可行路径
                # 边的成本：基于目标节点的激活能量，能量越高成本越低
                node_energy = activations.get(neighbor, 0.01)
                edge_cost = 1.0 / (node_energy + 0.1) # 加0.1防止除零和平滑
                
                new_cost = cost + edge_cost
                
                if new_cost < visited_costs.get(neighbor, float('inf')):
                    visited_costs[neighbor] = new_cost
                    heapq.heappush(priority_queue, (new_cost, neighbor, temp_path))
    
    logger.warning("未找到连接路径")
    return []

# ==========================================
# 使用示例 / Usage Example
# ==========================================
if __name__ == "__main__":
    try:
        # 1. 构建大规模认知网络 (模拟 200 个节点)
        print("--- 步骤 1: 初始化认知网络 ---")
        cognitive_net = CognitiveGraph(node_count=200, edge_probability=0.1)
        
        # 2. 定义上下文输入 (模拟 '四向碰撞' 产生的初始刺激)
        # 假设节点 0, 3, 50, 180 是当前感知到的核心冲突点
        collision_context = [0, 3, 50, 180]
        
        # 3. 执行稀疏激活
        print("\n--- 步骤 2: 执行稀疏激活 ---")
        active_subset, energy_map = sparse_activate_subgraph(
            graph=cognitive_net,
            context_nodes=collision_context,
            activation_threshold=0.2,
            max_hops=4
        )
        print(f"激活节点数量: {len(active_subset)} / {cognitive_net.node_count}")
        
        # 4. 在激活的子网络中进行路径优化推理
        # 假设我们需要从节点 0 推理到节点 50
        print("\n--- 步骤 3: 优化推理路径 ---")
        if 0 in active_subset and 50 in active_subset:
            best_path = optimize_reasoning_path(
                graph=cognitive_net,
                active_nodes=active_subset,
                activations=energy_map,
                start_node=0,
                end_node=50
            )
            print(f"最优路径: {best_path}")
        else:
            print("指定节点未被激活。")

    except ValueError as ve:
        logger.error(f"参数验证错误: {ve}")
    except Exception as e:
        logger.error(f"系统运行时发生意外错误: {e}", exc_info=True)