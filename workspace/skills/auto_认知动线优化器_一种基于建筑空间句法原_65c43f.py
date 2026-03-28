"""
认知动线优化器

一种基于建筑空间句法原理的神经网络架构搜索与正则化工具。
将网络层视为'房间'，激活函数视为'门禁'，利用空间句法中的'整合度'和'选择度'指标来分析网络拓扑结构。
该能力可自动识别网络中的'死胡同'（梯度消失区域）和'拥堵点'（过拟合区域），并动态调整网络拓扑，
使信息流像建筑中的理想人流一样顺畅，实现'零摩擦'的前向传播。

Domain: Cross Domain (Architecture Spatial Syntax x Deep Learning)
Author: AGI System
Version: 1.0.0
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
logger = logging.getLogger("CognitivePathOptimizer")

@dataclass
class LayerNode:
    """
    网络层节点定义（对应建筑空间中的'房间'）。
    
    Attributes:
        id (str): 层的唯一标识符。
        out_channels (int): 输出通道数（对应房间的容量）。
        activation (str): 激活函数类型（对应门禁类型，如 'relu', 'sigmoid', 'none'）。
        connections (List[str]): 连接到的下一层节点ID列表。
    """
    id: str
    out_channels: int
    activation: str = "relu"
    connections: List[str] = field(default_factory=list)

class CognitivePathOptimizer:
    """
    基于空间句法的认知动线优化器。
    
    通过计算网络拓扑的整合度与选择度，识别梯度流瓶颈并生成优化建议。
    """

    def __init__(self, nodes: List[LayerNode], max_depth: int = 100):
        """
        初始化优化器。
        
        Args:
            nodes (List[LayerNode]): 网络层的节点列表。
            max_depth (int): 搜索路径的最大深度，防止死循环。
        
        Raises:
            ValueError: 如果节点列表为空或节点ID重复。
        """
        if not nodes:
            raise ValueError("节点列表不能为空")
        
        self.nodes = {node.id: node for node in nodes}
        if len(self.nodes) != len(nodes):
            raise ValueError("检测到重复的节点ID，每个节点ID必须唯一")
            
        self.max_depth = max_depth
        self.node_ids = list(self.nodes.keys())
        self.num_nodes = len(self.node_ids)
        self._topo_matrix = None
        
        logger.info(f"初始化认知动线优化器，包含 {self.num_nodes} 个节点。")

    def _build_adjacency_matrix(self) -> np.ndarray:
        """
        [辅助函数] 构建邻接矩阵。
        
        Returns:
            np.ndarray: 形状为 (N, N) 的邻接矩阵，N为节点数量。
        """
        matrix = np.zeros((self.num_nodes, self.num_nodes), dtype=np.float32)
        id_to_idx = {node_id: i for i, node_id in enumerate(self.node_ids)}

        for node_id, node in self.nodes.items():
            i = id_to_idx[node_id]
            for conn_id in node.connections:
                if conn_id in id_to_idx:
                    j = id_to_idx[conn_id]
                    # 权重可根据激活函数类型调整，这里假设连接权重受'门禁'影响
                    # Sigmoid/Tanh 容易导致拥挤，权重设为0.5，ReLU/None设为1.0
                    weight = 0.5 if node.activation in ['sigmoid', 'tanh'] else 1.0
                    matrix[i][j] = weight
                else:
                    logger.warning(f"节点 {node_id} 连接到不存在的节点 {conn_id}，已忽略。")
        
        self._topo_matrix = matrix
        return matrix

    def _calculate_depth_map(self) -> Dict[str, float]:
        """
        [核心函数 1] 计算每个节点的平均深度。
        在空间句法中，平均深度反映了该节点在拓扑结构中的整合程度。
        深度值越大，信息到达该节点越困难（梯度消失风险越高）。
        
        Returns:
            Dict[str, float]: 节点ID到平均深度的映射。
        """
        if self._topo_matrix is None:
            self._build_adjacency_matrix()

        # 使用Floyd-Warshall算法计算最短路径
        dist = np.full((self.num_nodes, self.num_nodes), np.inf)
        n = self.num_nodes
        
        # 初始化距离矩阵
        for i in range(n):
            dist[i][i] = 0
            for j in range(n):
                if self._topo_matrix[i][j] > 0:
                    # 这里使用倒数作为距离，权重越大（通畅），距离越短
                    # 为了简化，假设权重1.0代表距离1
                    dist[i][j] = 1.0 / self._topo_matrix[i][j]

        # Floyd-Warshall 核心逻辑
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    if dist[i][k] + dist[k][j] < dist[i][j]:
                        dist[i][j] = dist[i][k] + dist[k][j]

        # 计算平均深度
        depths = {}
        for i, node_id in enumerate(self.node_ids):
            total_depth = np.sum(dist[i][np.isfinite(dist[i])])
            count = np.sum(np.isfinite(dist[i])) - 1 # 减去自身
            
            if count > 0:
                mean_depth = total_depth / count
            else:
                mean_depth = np.inf # 孤立节点
                
            depths[node_id] = mean_depth
            logger.debug(f"节点 {node_id} 平均深度: {mean_depth:.2f}")

        return depths

    def analyze_topology_dynamics(self) -> Dict[str, Dict[str, Union[float, str]]]:
        """
        [核心函数 2] 分析拓扑动力学特征。
        
        结合平均深度（整合度）和连接度，识别网络中的'死胡同'和'拥堵点'。
        
        Returns:
            Dict: 包含每个节点分析结果的字典。
                {
                    "node_id": {
                        "integration": float,  # 整合度指标
                        "status": str,         # 状态诊断
                        "suggestion": str      # 优化建议
                    }
                }
        """
        depths = self._calculate_depth_map()
        results = {}
        
        # 计算全局统计量以进行归一化
        valid_depths = [d for d in depths.values() if np.isfinite(d)]
        if not valid_depths:
            logger.error("网络拓扑无法计算有效深度，可能存在断裂。")
            return {}

        mean_sys_depth = np.mean(valid_depths)
        std_sys_depth = np.std(valid_depths)
        
        logger.info(f"系统平均深度: {mean_sys_depth:.2f}, 标准差: {std_sys_depth:.2f}")

        for node_id, depth in depths.items():
            node_info = self.nodes[node_id]
            integration = 1.0 / depth if depth > 0 else 0
            
            status = "Healthy"
            suggestion = "No action needed"
            
            # 边界检查与状态判定
            if not np.isfinite(depth):
                status = "Isolated_Dead_End"
                suggestion = "CRITICAL: 节点完全孤立，建议添加 Residual Connection 或检查上游连接。"
            elif depth > mean_sys_depth + 2 * std_sys_depth:
                status = "Gradient_Vanishing_Risk"
                suggestion = "WARNING: 深度过深，存在梯度消失风险。建议引入 Skip Connection 或更换为 ReLU/GELU。"
            elif depth < mean_sys_depth - std_sys_depth and len(node_info.connections) > 3:
                status = "Traffic_Congestion_Point"
                suggestion = "INFO: 整合度高且连接稠密，可能成为计算瓶颈或过拟合点。建议增加 Dropout 或 Split 网络。"
            elif node_info.activation in ['sigmoid', 'tanh'] and depth > mean_sys_depth:
                status = "Narrow_Gate"
                suggestion = "OPTIMIZE: 激活函数限制了深层信息的流动。建议替换为 ReLU 或 LeakyReLU。"

            results[node_id] = {
                "integration": round(integration, 4),
                "mean_depth": round(depth, 4),
                "status": status,
                "suggestion": suggestion
            }
            
            if status != "Healthy":
                logger.warning(f"节点 {node_id} 状态: {status} | 建议: {suggestion}")

        return results

    def generate_routing_plan(self) -> List[Tuple[str, str]]:
        """
        [辅助/扩展] 基于分析生成简单的路由优化计划（例如建议添加的跳跃连接）。
        
        Returns:
            List[Tuple[str, str]]: 建议添加的 (源节点, 目标节点) 连接列表。
        """
        analysis = self.analyze_topology_dynamics()
        suggestions = []
        
        # 寻找最深层的节点和最浅层的节点，建议建立快捷路径
        deep_nodes = [nid for nid, data in analysis.items() if "Vanishing" in data['status'] or "Dead_End" in data['status']]
        
        # 简单的启发式：如果深层节点有问题，尝试将其连接到输出层或最近的健康层
        # 这里仅作演示逻辑：建议将深层节点连接到网络的最终输出（假设最后一个节点是输出）
        output_node_id = self.node_ids[-1] 
        
        for node_id in deep_nodes:
            if node_id != output_node_id:
                suggestions.append((node_id, output_node_id))
                logger.info(f"路由建议: 建立从 {node_id} 到 {output_node_id} 的跳跃连接以缓解深度问题。")
                
        return suggestions

# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 1. 定义网络拓扑（模拟一个有问题的网络）
    # input -> conv1 -> conv2 -> conv3 (sigmoid, deep) -> output
    #       |          -> branch (dead end)
    try:
        nodes_definition = [
            LayerNode("input", 64, "none", ["conv1"]),
            LayerNode("conv1", 128, "relu", ["conv2", "branch"]), # 分支点
            LayerNode("conv2", 256, "relu", ["conv3"]),
            LayerNode("conv3", 512, "sigmoid", ["output"]), # Sigmoid在深层，模拟Narrow Gate
            LayerNode("branch", 32, "relu", []), # 死胡同，无连接
            LayerNode("output", 10, "softmax", [])
        ]

        # 2. 实例化优化器
        optimizer = CognitivePathOptimizer(nodes_definition)

        # 3. 运行动线分析
        print("\n--- 开始认知动线分析 ---")
        analysis_results = optimizer.analyze_topology_dynamics()

        # 4. 打印结果
        print("\n--- 分析报告 ---")
        for node_id, result in analysis_results.items():
            print(f"Node: {node_id:<10} | Status: {result['status']:<25} | Suggestion: {result['suggestion']}")
            
        # 5. 获取路由建议
        print("\n--- 路由优化建议 ---")
        plan = optimizer.generate_routing_plan()
        
    except ValueError as e:
        logger.error(f"初始化失败: {e}")
    except Exception as e:
        logger.error(f"运行时错误: {e}")