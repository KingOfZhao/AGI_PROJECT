"""
模块名称: dynamic_skill_topology.py
描述: 针对当前280个可执行技能节点(SKILL)，基于'最小能量原理'构建动态技能拓扑索引。
      该索引不依赖静态标签，而是根据近期人机交互频率动态调整连接权重，
      形成热通路，模拟人类认知中的'近期效应'，优化AGI知识调用效率。

Author: Senior Python Engineer
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import heapq
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 常量定义
TOTAL_SKILLS = 280
DECAY_LAMBDA = 0.95  # 时间衰减系数
ENERGY_ALPHA = 0.1   # 能量平滑系数
INTERACTION_THRESHOLD = 1e-3  # 交互权重阈值

@dataclass
class SkillNode:
    """
    技能节点数据结构。
    
    Attributes:
        id (str): 技能节点的唯一标识符。
        description (str): 技能的简短描述。
        base_energy (float): 节点的基础能量值，代表静态重要性。
        connections (Dict[str, float]): 指向其他节点的连接及其动态权重。
        last_updated (int): 上次更新的时间戳（模拟）。
    """
    id: str
    description: str
    base_energy: float = 1.0
    connections: Dict[str, float] = field(default_factory=dict)
    last_updated: int = 0

def validate_skill_graph(graph: Dict[str, SkillNode]) -> bool:
    """
    辅助函数：验证技能图谱数据的完整性。
    
    Args:
        graph (Dict[str, SkillNode]): 技能图谱字典。
        
    Returns:
        bool: 如果数据有效返回True，否则抛出ValueError。
        
    Raises:
        ValueError: 如果节点数量不符或连接指向不存在的节点。
    """
    logger.info("开始验证技能图谱数据...")
    if len(graph) != TOTAL_SKILLS:
        raise ValueError(f"节点数量错误: 期望 {TOTAL_SKILLS}, 实际 {len(graph)}")
    
    for node_id, node in graph.items():
        if node.id != node_id:
            raise ValueError(f"节点ID不匹配: 字典Key {node_id} != 节点ID {node.id}")
        
        for conn_id in node.connections.keys():
            if conn_id not in graph:
                raise ValueError(f"节点 {node_id} 包含无效连接指向不存在的节点 {conn_id}")
                
    logger.info("图谱验证通过。")
    return True

def calculate_dynamic_weights(
    graph: Dict[str, SkillNode], 
    interaction_history: Dict[Tuple[str, str], float],
    current_time: int
) -> None:
    """
    核心函数1：基于近期交互历史计算动态权重。
    
    根据 '最小能量原理'，交互频率越高（电流越大），路径上的'电阻'（阻抗）应该越小，
    即连接权重越大。同时引入时间衰减机制模拟'近期效应'。
    
    公式: W_dynamic = W_base + Sum(Interaction * e^(-lambda * dt))
    
    Args:
        graph (Dict[str, SkillNode]): 技能图谱。
        interaction_history (Dict[Tuple[str, str], float]): 
            键为(源节点, 目标节点)，值为交互强度。
            此处假设输入已经是预处理过的近期（如7天）数据。
        current_time (int): 当前时间戳。
        
    Returns:
        None: 直接修改图中的连接权重。
    """
    logger.info("正在计算动态权重...")
    
    for (src_id, dest_id), strength in interaction_history.items():
        if src_id in graph and dest_id in graph[src_id].connections:
            # 获取该连接的基础权重（静态）
            base_weight = graph[src_id].connections[dest_id].get('base', 0.5)
            
            # 计算时间衰减因子
            # 注意：这里简化处理，假设 interaction_history 包含时间戳信息，
            # 或者输入数据已经是加权后的近期频率。
            # 为演示原理，我们直接增加权重，模拟热通路形成。
            
            # 应用能量函数：增加活跃连接的权重
            new_weight = base_weight + strength * DECAY_LAMBDA
            
            # 权重截断，防止无限增长
            graph[src_id].connections[dest_id]['dynamic'] = min(new_weight, 10.0)
        else:
            logger.warning(f"忽略无效交互记录: {src_id} -> {dest_id}")

def find_optimal_skill_path(
    graph: Dict[str, SkillNode], 
    start_id: str, 
    end_id: str
) -> Tuple[Optional[List[str]], float]:
    """
    核心函数2：寻找能量最低的路径（A*算法变体）。
    
    在动态拓扑中，寻找从起点到终点的路径。
    代价函数定义为: Cost = 1 / Weight。
    权重越高（热通路），代价越低，越容易被选中。
    
    Args:
        graph (Dict[str, SkillNode]): 更新后的技能图谱。
        start_id (str): 起始技能ID。
        end_id (str): 目标技能ID。
        
    Returns:
        Tuple[Optional[List[str]], float]: 
            - 路径列表 (如果没有找到则返回None)
            - 总能量消耗 (总代价)
    """
    if start_id not in graph or end_id not in graph:
        logger.error("起点或终点不在图谱中。")
        return None, float('inf')
        
    logger.info(f"开始寻路: {start_id} -> {end_id}")
    
    # 优先队列: (累计代价, 当前节点ID, 路径列表)
    pq = [(0.0, start_id, [start_id])]
    visited = set()
    
    while pq:
        current_cost, u, path = heapq.heappop(pq)
        
        if u == end_id:
            logger.info(f"找到最优路径，总代价: {current_cost:.4f}")
            return path, current_cost
            
        if u in visited:
            continue
        visited.add(u)
        
        for v, conn_data in graph[u].connections.items():
            if v in visited:
                continue
                
            # 获取动态权重，如果没有则回退到基础权重
            weight = conn_data.get('dynamic', conn_data.get('base', 0.1))
            
            # 边界检查：防止除以零
            if weight <= 0:
                weight = 0.01
                
            # 计算代价：权重越高，代价越低
            edge_cost = 1.0 / weight
            
            new_cost = current_cost + edge_cost
            
            heapq.heappush(pq, (new_cost, v, path + [v]))
            
    logger.warning("未找到连接路径。")
    return None, float('inf')

# --- 使用示例与模拟 ---
if __name__ == "__main__":
    # 1. 初始化模拟数据 (280个节点)
    skill_graph = {}
    for i in range(TOTAL_SKILLS):
        node_id = f"skill_{i:03d}"
        # 随机初始化一些连接
        connections = {}
        # 确保图是连通的，简单的环状 + 随机跳跃
        next_node = f"skill_{(i+1)%TOTAL_SKILLS:03d}"
        connections[next_node] = {'base': 0.5}
        
        if i % 10 == 0 and i + 5 < TOTAL_SKILLS:
            jump_node = f"skill_{i+5:03d}"
            connections[jump_node] = {'base': 0.2}
            
        skill_graph[node_id] = SkillNode(
            id=node_id,
            description=f"自动化技能节点 #{i}",
            connections=connections
        )

    try:
        # 数据验证
        validate_skill_graph(skill_graph)
        
        # 2. 模拟近期交互历史 (模拟高频使用某些路径)
        # 假设最近用户频繁使用 skill_000 -> skill_001 的路径
        mock_interactions = {
            ("skill_000", "skill_001"): 5.0,  # 高频
            ("skill_001", "skill_002"): 4.5,
            ("skill_050", "skill_051"): 2.0
        }
        
        # 3. 更新动态权重
        calculate_dynamic_weights(skill_graph, mock_interactions, current_time=1000)
        
        # 检查权重是否更新
        logger.info(f"更新后权重 skill_000->skill_001: {skill_graph['skill_000'].connections['skill_001']}")
        
        # 4. 寻路测试
        # 从 skill_000 到 skill_002
        # 正常路径是 000->001->002
        # 由于我们增强了这段路径的权重，算法应该优选这条路（虽然它可能本来也是唯一的路，但代价会显著降低）
        
        path, cost = find_optimal_skill_path(skill_graph, "skill_000", "skill_002")
        
        if path:
            print(f"\n=== 寻路结果 ===")
            print(f"路径: {' -> '.join(path)}")
            print(f"总能量代价: {cost:.4f} (越低越好)")
            
    except ValueError as ve:
        logger.error(f"数据验证失败: {ve}")
    except Exception as e:
        logger.error(f"系统运行时错误: {e}", exc_info=True)