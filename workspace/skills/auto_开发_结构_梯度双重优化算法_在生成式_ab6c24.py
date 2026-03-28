"""
高级Python模块：结构-梯度双重优化算法 (SGDOA) 用于生成式建筑设计

该模块实现了一种结合图神经网络逻辑与建筑空间句法理论的优化算法。
核心思想是将建筑构件视为网络节点，模拟'人流'或'视觉流'的反向传播，
并通过'结构残差连接'（如通高庭院、自动扶梯）来解决空间布局中的'梯度消失'（死胡同）问题。

Author: AGI System Core
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SGDO_Architecture")


@dataclass
class SpaceNode:
    """
    建筑空间节点数据结构。
    
    Attributes:
        id (str): 空间唯一标识符。
        area (float): 空间面积 (平方米)。
        floor (int): 所在楼层。
        attr_power (float): 空间的吸引力（如商业价值、景观视野），范围0.0-1.0。
        neighbors (List[str]): 相邻空间节点ID列表。
        residual_type (Optional[str]): 残差连接类型（如 'escalator', 'atrium'）。
    """
    id: str
    area: float
    floor: int
    attr_power: float = 0.5
    neighbors: List[str] = field(default_factory=list)
    residual_type: Optional[str] = None

    def __post_init__(self):
        if not 0.0 <= self.attr_power <= 1.0:
            raise ValueError(f"Node {self.id}: attr_power must be between 0.0 and 1.0")


class GradientFlowOptimizer:
    """
    核心：结构-梯度双重优化器。
    
    实现基于图的反向传播模拟，计算人流梯度的分布，
    并识别需要结构干预的'死胡同'区域。
    """

    def __init__(self, nodes: List[SpaceNode], learning_rate: float = 0.01):
        """
        初始化优化器。
        
        Args:
            nodes (List[SpaceNode]): 建筑空间节点列表。
            learning_rate (float): 梯度下降的学习率，用于调整连接权重。
        """
        self.nodes = {node.id: node for node in nodes}
        self.node_ids = list(self.nodes.keys())
        self.n_nodes = len(nodes)
        self.learning_rate = learning_rate
        
        # 初始化邻接权重矩阵 (连接强度)
        self.adj_matrix = np.zeros((self.n_nodes, self.n_nodes))
        self._initialize_graph()

        logger.info(f"Optimizer initialized with {self.n_nodes} nodes.")

    def _initialize_graph(self):
        """构建图的邻接矩阵，基于节点邻居关系。"""
        id_to_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        
        for node in self.nodes.values():
            i = id_to_idx[node.id]
            for neighbor_id in neighbor_ids:
                if neighbor_id in id_to_idx:
                    j = id_to_idx[neighbor_id]
                    # 初始权重基于空间吸引力
                    self.adj_matrix[i, j] = 0.5 
                    self.adj_matrix[j, i] = 0.5

    def _simulate_flow_propagation(self, steps: int = 10) -> np.ndarray:
        """
        辅助函数：模拟前向人流传播。
        
        模拟从入口（通常是底层或特定节点）向整个建筑传播的'活跃度'。
        
        Args:
            steps (int): 传播迭代次数。
            
        Returns:
            np.ndarray: 每个节点的活跃度分数。
        """
        # 假设入口节点是第一个节点或标记为'entrance'的节点
        # 这里简化：随机选取底层节点作为源
        source_indices = [i for i, nid in enumerate(self.node_ids) if self.nodes[nid].floor == 0]
        
        if not source_indices:
            logger.warning("No ground floor nodes found for flow source.")
            source_indices = [0]

        activity = np.zeros(self.n_nodes)
        activity[source_indices] = 1.0  # 初始人流

        # 简单的扩散过程
        for _ in range(steps):
            new_activity = np.zeros(self.n_nodes)
            for i in range(self.n_nodes):
                # 活跃度由邻居流入
                incoming = np.sum(self.adj_matrix[:, i] * activity)
                # 衰减因子
                new_activity[i] = (activity[i] * 0.8 + incoming * 0.2) * self.nodes[self.node_ids[i]].attr_power
            activity = new_activity
            
        return activity

    def analyze_gradient_vanishing(self, threshold: float = 0.05) -> Dict[str, float]:
        """
        核心函数：分析人流梯度消失点。
        
        通过比较理论上的最大人流与实际模拟人流，识别'冷区'。
        
        Args:
            threshold (float): 判定为'死胡同'的活跃度阈值。
            
        Returns:
            Dict[str, float]: 返回节点ID与其活跃度分数的字典。
        """
        logger.info("Starting gradient analysis...")
        
        activity_scores = self._simulate_flow_propagation(steps=20)
        
        cold_spots = {}
        for idx, score in enumerate(activity_scores):
            node_id = self.node_ids[idx]
            if score < threshold:
                logger.warning(f"Gradient vanishing detected at Node {node_id} (Score: {score:.4f})")
                cold_spots[node_id] = score
                
        return cold_spots

    def apply_structural_residual(self, target_node_id: str, source_node_id: str, connection_type: str = "escalator"):
        """
        核心函数：应用结构残差连接。
        
        在物理空间中增加垂直或水平连接，在图结构中增加强权重边。
        
        Args:
            target_node_id (str): 目标节点（冷区）。
            source_node_id (str): 源节点（热区/高活跃区）。
            connection_type (str): 连接类型。
        """
        if target_node_id not in self.nodes or source_node_id not in self.nodes:
            raise ValueError("Invalid node IDs for residual connection.")

        logger.info(f"Applying structural residual: {connection_type} between {source_node_id} -> {target_node_id}")

        # 更新物理属性
        self.nodes[target_node_id].residual_type = connection_type
        
        # 更新图逻辑：增加强连接
        id_to_idx = {nid: i for i, nid in enumerate(self.node_ids)}
        i, j = id_to_idx[source_node_id], id_to_idx[target_node_id]
        
        # 残差连接通常具有比普通走廊更高的通过能力
        boost_factor = 1.5 if connection_type == "escalator" else 1.2
        self.adj_matrix[i, j] = min(1.0, self.adj_matrix[i, j] + boost_factor)
        self.adj_matrix[j, i] = min(1.0, self.adj_matrix[j, i] + boost_factor)

        # 更新邻居列表
        if source_node_id not in self.nodes[target_node_id].neighbors:
            self.nodes[target_node_id].neighbors.append(source_node_id)
            self.nodes[source_node_id].neighbors.append(target_node_id)

    def optimize_layout(self, max_iterations: int = 5):
        """
        执行完整的优化循环。
        """
        for i in range(max_iterations):
            logger.info(f"Optimization Iteration {i+1}/{max_iterations}")
            cold_spots = self.analyze_gradient_vanishing()
            
            if not cold_spots:
                logger.info("Layout optimized. No critical cold spots remaining.")
                break
            
            # 简单策略：将冷区连接到最近的同列高层活跃区
            # (此处简化逻辑，实际应包含空间距离计算)
            for cold_id in cold_spots:
                # 随机选择一个高活跃区进行连接演示
                # 在实际算法中，这里应基于空间邻近性选择
                hot_nodes = [n for n in self.nodes.values() if n.attr_power > 0.8]
                if hot_nodes:
                    source = np.random.choice(hot_nodes)
                    self.apply_structural_residual(cold_id, source.id, "atrium_link")

# 输入输出格式说明
"""
Input Format:
    List[SpaceNode]: 包含建筑构件信息的列表。
    
Output Format:
    Dict: 优化后的图结构数据，包含节点状态和邻接矩阵。
"""

# 使用示例
if __name__ == "__main__":
    try:
        # 1. 定义建筑节点数据
        floor_0_lobby = SpaceNode(id="L01", area=200, floor=0, attr_power=0.9)
        floor_0_shop = SpaceNode(id="S01", area=50, floor=0, attr_power=0.7, neighbors=["L01"])
        floor_1_gallery = SpaceNode(id="G01", area=100, floor=1, attr_power=0.4) # 孤立节点，可能导致梯度消失
        floor_2_office = SpaceNode(id="O01", area=150, floor=2, attr_power=0.2) # 极其孤立
        
        building_layout = [floor_0_lobby, floor_0_shop, floor_1_gallery, floor_2_office]

        # 2. 初始化优化器
        optimizer = GradientFlowOptimizer(nodes=building_layout)

        # 3. 执行分析与优化
        # 首次检测
        initial_cold_spots = optimizer.analyze_gradient_vanishing()
        print(f"Initial Cold Spots: {initial_cold_spots}")

        # 4. 自动优化
        optimizer.optimize_layout(max_iterations=3)

        # 5. 验证结果
        final_cold_spots = optimizer.analyze_gradient_vanishing()
        print(f"Final Cold Spots: {final_cold_spots}")

    except ValueError as ve:
        logger.error(f"Data Validation Error: {ve}")
    except Exception as e:
        logger.critical(f"System Crash: {e}", exc_info=True)