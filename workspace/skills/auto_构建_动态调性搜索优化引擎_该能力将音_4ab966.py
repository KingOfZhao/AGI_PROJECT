"""
模块名称: dynamic_tonality_search_engine
功能描述: 构建动态调性搜索优化引擎，将音乐中和声解决张力的逻辑转化为算法中的搜索权重调节机制。
           用于解决复杂迷宫或资源调度问题，提升AI在局部最优陷阱中的鲁棒性。
"""

import logging
import math
import random
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TonalityOptimizer")

class HarmonicState(Enum):
    """定义算法当前的调性状态"""
    TONIC = "tonic"           # 主和弦状态（全局最优附近）
    DOMINANT = "dominant"     # 属和弦状态（接近目标）
    SUBDOMINANT = "subdominant" # 下属和弦状态（搜索中）
    DISSONANCE = "dissonance" # 离调/不协和状态（局部最优/停滞）

class Node:
    """
    搜索空间中的节点基类。
    假设用于迷宫或图搜索场景。
    """
    def __init__(self, node_id: int, coordinates: Tuple[int, int], is_target: bool = False):
        self.id = node_id
        self.coords = coordinates
        self.is_target = is_target
        self.neighbors: List['Node'] = []

    def add_neighbor(self, neighbor_node: 'Node'):
        """添加邻接节点"""
        if neighbor_node not in self.neighbors:
            self.neighbors.append(neighbor_node)

    def __repr__(self):
        return f"Node(id={self.id}, coords={self.coords}, target={self.is_target})"

class DynamicTonalityEngine:
    """
    动态调性搜索优化引擎。
    
    核心思想是将音乐中的和声逻辑映射到启发式搜索权重中：
    1. 当陷入局部最优（离调）时，使用'重属和弦'策略（临时目标偏移）强制跳出。
    2. 当接近全局最优（主和弦）时，指数级增加权重以加速收敛。
    
    Attributes:
        initial_weight (float): 初始启发式权重。
        dissonance_threshold (float): 判定陷入停滞的阈值。
        modulation_intensity (float): 离调策略的跳转强度。
    """

    def __init__(self, 
                 initial_weight: float = 1.0, 
                 dissonance_threshold: int = 5,
                 modulation_intensity: float = 0.8):
        """
        初始化引擎。

        Args:
            initial_weight (float): 基础权重因子。
            dissonance_threshold (int): 连续多少次没有改进则判定为'离调/停滞'。
            modulation_intensity (float): 强制跳脱时的随机扰动系数 (0.0-1.0)。
        """
        if not 0.0 <= modulation_intensity <= 1.0:
            raise ValueError("modulation_intensity 必须在 0.0 和 1.0 之间")
        
        self.current_weight = initial_weight
        self.dissonance_threshold = dissonance_threshold
        self.modulation_intensity = modulation_intensity
        self._stagnation_counter = 0
        self._current_state = HarmonicState.SUBDOMINANT
        
        logger.info("动态调性引擎初始化完成。")

    def _calculate_distance(self, coord_a: Tuple[int, int], coord_b: Tuple[int, int]) -> float:
        """辅助函数：计算欧几里得距离"""
        return math.sqrt((coord_a[0] - coord_b[0])**2 + (coord_a[1] - coord_b[1])**2)

    def _resolve_harmonic_tension(self, 
                                  current_score: float, 
                                  best_score: float, 
                                  distance_to_goal: float) -> None:
        """
        核心辅助函数：解析当前状态并调整内部权重（和声张力）。
        
        逻辑：
        1. 接近目标（主和弦）：指数增加权重。
        2. 停滞不前（离调）：标记为不协和状态，准备触发跳转。
        """
        if current_score > best_score:
            # 有改进，重置停滞计数
            self._stagnation_counter = 0
            self._current_state = HarmonicState.DOMINANT
        else:
            self._stagnation_counter += 1

        # 调性（权重）调节逻辑
        if distance_to_goal < 5.0:
            # 接近主和弦：张力解决
            self._current_state = HarmonicState.TONIC
            # 指数级增加收敛权重，模拟向主和弦解决的倾向
            self.current_weight = math.exp(5.0 - distance_to_goal)
            logger.debug(f"进入主和弦区域，距离: {distance_to_goal:.2f}, 权重激增: {self.current_weight:.2f}")
        
        elif self._stagnation_counter >= self.dissonance_threshold:
            # 陷入停滞（离调/不协和）
            self._current_state = HarmonicState.DISSONANCE
            logger.warning(f"检测到搜索停滞 (离调)，计数: {self._stagnation_counter}")

    def select_next_step(self, 
                         current_node: Node, 
                         goal_node: Node, 
                         evaluation_func: Callable[[Node, Node], float]) -> Tuple[Node, float]:
        """
        核心函数：选择下一个搜索步骤。
        
        结合当前调性状态（权重）和启发式评估函数选择最佳节点。
        如果处于'离调'状态，引入'重属和弦'策略（随机扰动）。

        Args:
            current_node (Node): 当前所在节点。
            goal_node (Node): 目标节点。
            evaluation_func (Callable): 评估函数，例如距离估算。

        Returns:
            Tuple[Node, float]: 选择的下一个节点及其得分。
        """
        if not current_node.neighbors:
            raise ValueError("当前节点没有邻居，无法移动。")

        # 模拟得分计算（这里简化为距离的倒数 * 权重）
        # 实际应用中 evaluation_func 可能返回 cost
        raw_score = evaluation_func(current_node, goal_node)
        
        dist_to_goal = self._calculate_distance(current_node.coords, goal_node.coords)
        self._resolve_harmonic_tension(raw_score, raw_score, dist_to_goal) # 简化示例，实际需传入历史best_score

        candidate_scores: Dict[int, float] = {}
        
        for neighbor in current_node.neighbors:
            # 基础启发式得分 (距离越近得分越高)
            h_cost = self._calculate_distance(neighbor.coords, goal_node.coords)
            # 应用调性权重
            weighted_score = (1.0 / (h_cost + 1e-6)) * self.current_weight
            
            # 重属和弦策略：如果处于离调状态，引入随机性强制跳脱
            if self._current_state == HarmonicState.DISSONANCE:
                random_factor = random.uniform(-self.modulation_intensity, self.modulation_intensity)
                weighted_score *= (1 + random_factor)
                logger.info(f"应用重属和弦策略(随机偏移): 邻居 {neighbor.id} 得分扰动")

            candidate_scores[neighbor.id] = weighted_score

        # 选择得分最高的节点
        best_neighbor_id = max(candidate_scores, key=candidate_scores.get)
        selected_node = next(n for n in current_node.neighbors if n.id == best_neighbor_id)
        
        logger.info(f"状态: {self._current_state.value} | 选择节点: {selected_node.id} | 权重: {self.current_weight:.2f}")
        
        # 如果刚刚进行了离调处理，重置状态
        if self._current_state == HarmonicState.DISSONANCE:
             self._stagnation_counter = 0 # 强制跳转后重置计数
             self._current_state = HarmonicState.SUBDOMINANT
             
        return selected_node, candidate_scores[best_neighbor_id]

def simple_heuristic(node_a: Node, node_b: Node) -> float:
    """示例评估函数：简单的距离倒数"""
    dist = math.sqrt((node_a.coords[0] - node_b.coords[0])**2 + (node_a.coords[1] - node_b.coords[1])**2)
    return -dist # 返回负距离表示越近越好（或者用倒数）

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 构建简单的测试图 (迷宫模拟)
    # 5个节点的线性图：0 -> 1 -> 2 -> 3 -> 4 (Target)
    nodes = [Node(i, (i*10, 0), is_target=(i==4)) for i in range(5)]
    for i in range(len(nodes) - 1):
        nodes[i].add_neighbor(nodes[i+1])
        nodes[i+1].add_neighbor(nodes[i]) # 双向

    # 添加一个死胡同分支，模拟局部最优陷阱
    trap_node = Node(99, (10, 10)) 
    nodes[1].add_neighbor(trap_node) # 节点1连接到陷阱
    trap_node.add_neighbor(nodes[1])

    # 2. 初始化引擎
    engine = DynamicTonalityEngine(dissonance_threshold=2, modulation_intensity=0.5)
    
    # 3. 运行搜索模拟
    current = nodes[0]
    goal = nodes[4]
    steps = 0
    path = [current.id]
    
    print(f"开始搜索: 从 {current.id} 到 {goal.id}")
    
    while current.id != goal.id and steps < 20:
        try:
            # 模拟评分函数传入
            next_node, score = engine.select_next_step(current, goal, simple_heuristic)
            current = next_node
            path.append(current.id)
            steps += 1
        except ValueError as e:
            print(f"搜索终止: {e}")
            break
            
    print(f"搜索结束。路径: {path}")