"""
Module: industrial_energy_transfer_optimizer.py
Description: 构建产业能量传递效率优化器，利用生态系统能量流动分析优化供应链。
             模拟自然生态中的能量金字塔和食物网机制，评估价值链的鲁棒性与损耗。
Author: Senior Python Engineer (AGI System)
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import heapq
import networkx as nx
from typing import Dict, List, Tuple, Set, Optional, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class SupplyNode:
    """
    供应链节点定义。
    
    Attributes:
        node_id (str): 节点唯一标识
        node_type (str): 节点类型 (Producer, Consumer, Apex)
        base_value (float): 节点包含的基础价值/能量
        efficiency (float): 节点的转化效率 (0.0 到 1.0)
    """
    node_id: str
    node_type: str  # 'producer', 'intermediate', 'apex'
    base_value: float = 0.0
    efficiency: float = 1.0  # 默认无损耗

    def __post_init__(self):
        if not 0.0 <= self.efficiency <= 1.0:
            logger.warning(f"Node {self.node_id} efficiency {self.efficiency} out of bounds. Clamping to [0, 1].")
            self.efficiency = max(0.0, min(1.0, self.efficiency))
        if self.base_value < 0:
            logger.warning(f"Node {self.node_id} base_value cannot be negative. Setting to 0.")
            self.base_value = 0.0

@dataclass
class SupplyChainEdge:
    """
    供应链边定义（能量流动路径）。
    
    Attributes:
        source (str): 源节点ID
        target (str): 目标节点ID
        transaction_cost (float): 交易过程中的价值损耗（类比热量散失）
        dependency_weight (float): 目标节点对源节点的依赖程度
    """
    source: str
    target: str
    transaction_cost: float = 0.0
    dependency_weight: float = 1.0

# --- 核心类 ---

class EcoEnergyOptimizer:
    """
    产业能量传递效率优化器。
    
    利用生态学原理分析供应链。将企业视为物种，资金/物料流视为能量流。
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, SupplyNode] = {}
        logger.info("EcoEnergyOptimizer initialized.")

    def add_node(self, node: SupplyNode) -> None:
        """添加节点到供应链网络"""
        if node.node_id in self.nodes:
            logger.warning(f"Node {node.node_id} already exists. Overwriting.")
        self.nodes[node.node_id] = node
        self.graph.add_node(node.node_id, data=node)
        logger.debug(f"Node added: {node.node_id}")

    def add_edge(self, edge: SupplyChainEdge) -> None:
        """添加连接（能量流动通道）"""
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Edge creation failed: Source {edge.source} or Target {edge.target} not found.")
        
        self.graph.add_edge(
            edge.source, 
            edge.target, 
            weight=edge.dependency_weight,
            cost=edge.transaction_cost
        )
        logger.debug(f"Edge added: {edge.source} -> {edge.target}")

    def calculate_theoretical_efficiency(self) -> float:
        """
        计算整个系统的理论传递效率。
        
        类比生态效率（Lindeman效率），计算从生产者到顶级消费者的平均能量留存率。
        
        Returns:
            float: 系统整体效率 (0.0 - 1.0)
        """
        if not self.graph.nodes:
            return 0.0

        apex_nodes = [n_id for n_id, n_data in self.nodes.items() if n_data.node_type == 'apex']
        if not apex_nodes:
            logger.warning("No Apex nodes found in the system.")
            return 0.0

        total_efficiency_score = 0.0
        
        for apex in apex_nodes:
            # 反向遍历寻找所有生产者路径
            for source in self.nodes:
                if self.nodes[source].node_type == 'producer':
                    try:
                        # 使用Dijkstra寻找最小损耗路径（即最高效率路径）
                        # 这里我们将 'cost' 和 efficiency 结合作为路径权重
                        # 权重 = -log(efficiency) + transaction_cost，求最小和
                        # 简化版：这里我们计算所有路径的平均损耗
                        if nx.has_path(self.graph, source, apex):
                            paths = nx.all_simple_paths(self.graph, source, apex)
                            for path in paths:
                                path_efficiency = 1.0
                                for i in range(len(path) - 1):
                                    u, v = path[i], path[i+1]
                                    node_v = self.nodes[v]
                                    edge_data = self.graph.get_edge_data(u, v)
                                    
                                    # 损耗 = 节点转化损耗 + 边交易损耗
                                    step_loss = (1 - node_v.efficiency) + edge_data.get('cost', 0)
                                    path_efficiency *= (1 - step_loss)
                                
                                total_efficiency_score += path_efficiency
                    except Exception as e:
                        logger.error(f"Error calculating path {source}->{apex}: {e}")
                        continue
        
        # 简单归一化处理，实际场景需要更复杂的加权逻辑
        return total_efficiency_score / len(self.nodes) if self.nodes else 0.0

    def simulate_cascade_failure(self, failed_node_id: str) -> Dict[str, float]:
        """
        模拟级联失效效应。
        
        当一个“生产者”失效时，计算对“顶级捕食者”（终端产品）的具体影响。
        这是一个类似食物网崩溃的模拟。
        
        Args:
            failed_node_id (str): 失效的节点ID
            
        Returns:
            Dict[str, float]: 受影响的顶级节点ID及其价值损失比例。
        """
        if failed_node_id not in self.nodes:
            raise ValueError(f"Node {failed_node_id} does not exist.")

        logger.info(f"Simulating cascade failure initiated by: {failed_node_id}")
        
        impact_report: Dict[str, float] = {}
        
        # 找到所有顶级节点
        apex_nodes = [n for n, data in self.nodes.items() if data.node_type == 'apex']
        
        # 受影响的下游节点集合
        # 注意：在供应链中，上游失效影响下游，所以在图中是沿出边方向传播
        descendants = nx.descendants(self.graph, failed_node_id)
        descendants.add(failed_node_id) # 包含自身
        
        for apex in apex_nodes:
            if apex in descendants:
                # 计算该Apex节点对失效节点的依赖度
                # 这里简化为：计算失效节点到Apex的最大流（作为依赖权重）
                # 或者简单地计算路径上的权重乘积
                loss_ratio = self._calculate_dependency_impact(failed_node_id, apex)
                impact_report[apex] = loss_ratio
                logger.warning(f"Apex node '{apex}' impacted. Estimated loss: {loss_ratio:.2%}")
            else:
                impact_report[apex] = 0.0
                
        return impact_report

    def _calculate_dependency_impact(self, source: str, target: str) -> float:
        """
        辅助函数：计算特定源节点对目标节点的贡献度/影响因子。
        
        使用最大流算法模拟能量/物资供应的依赖程度。
        """
        try:
            # NetworkX的maximum_value_flow
            # 这里的容量(capacity)我们使用边的dependency_weight
            flow_value, _ = nx.maximum_flow(self.graph, source, target, capacity='weight')
            
            # 归一化：我们需要知道target总共需要多少输入
            # 简单处理：获取target所有入边的权重和
            total_in_weight = sum(data['weight'] for _, _, data in self.graph.in_edges(target, data=True))
            
            if total_in_weight == 0:
                return 0.0
            
            # 影响比例 = 单源贡献 / 总需求
            return min(1.0, flow_value / total_in_weight)
            
        except nx.NetworkXError:
            return 0.0

    def optimize_redundancy_strategy(self, critical_node_id: str) -> List[str]:
        """
        构建多源能量（供应）备份策略。
        
        分析当前的“食物网”冗余度。如果关键节点单点故障风险高，
        建议引入新的“物种”（供应商）或建立新的连接。
        
        Args:
            critical_node_id (str): 需要进行鲁棒性增强的关键节点
            
        Returns:
            List[str]: 建议增加的备份源节点类型或ID列表
        """
        if critical_node_id not in self.nodes:
            raise ValueError("Target node not found.")

        # 检查当前节点的供应源
        predecessors = list(self.graph.predecessors(critical_node_id))
        redundancy_score = len(predecessors)
        
        suggestions = []
        
        if redundancy_score == 0:
            msg = f"Node {critical_node_id} has no suppliers. Critical vulnerability."
            logger.critical(msg)
            suggestions.append("URGENT: Establish primary supply source.")
        elif redundancy_score == 1:
            # 单一来源风险
            logger.warning(f"Node {critical_node_id} has single source dependency.")
            suggestions.append(f"Add secondary supplier to diversity input for {critical_node_id}.")
            
            # 尝试在图中寻找潜在的其他同类供应商
            # 逻辑：寻找与现有supplier具有相同base_value的producer节点
            current_supplier = predecessors[0]
            potential_backups = [
                n for n, data in self.nodes.items() 
                if data.node_type == 'producer' and n != current_supplier
            ]
            
            if potential_backups:
                suggestions.append(f"Potential backups identified: {potential_backups}")
            else:
                suggestions.append("No existing producers available. Onboard new vendors.")
                
        else:
            # 检查依赖权重是否平衡
            weights = [self.graph[u][critical_node_id]['weight'] for u in predecessors]
            if max(weights) > sum(weights) * 0.8:
                logger.warning(f"Node {critical_node_id} relies heavily on a single source despite multiple links.")
                suggestions.append("Balance the dependency weights among existing suppliers.")
            else:
                logger.info(f"Node {critical_node_id} has a healthy redundant supply web.")
                suggestions.append("Supply chain structure is robust.")

        return suggestions

# --- 辅助函数 ---

def validate_graph_integrity(optimizer: EcoEnergyOptimizer) -> bool:
    """
    辅助函数：验证供应链图的完整性。
    
    检查是否存在孤立节点或断开的子图。
    """
    if not optimizer.graph:
        logger.error("Graph is empty.")
        return False
        
    # 检查是否弱连通（允许上下游未完全连接的情况，视业务逻辑而定）
    # 这里我们假设至少应该有一个连接的骨干
    if nx.number_weakly_connected_components(optimizer.graph) > 1:
        logger.warning("Graph contains disconnected components. Supply chain is fragmented.")
        # 这不一定是错误，可能是有独立的生产线，但在生态系统中通常意味着孤岛
    
    return True

# --- 使用示例 ---

if __name__ == "__main__":
    # 初始化优化器
    optimizer = EcoEnergyOptimizer()

    # 1. 构建供应链网络（生态模型）
    # 生产者（原材料）
    optimizer.add_node(SupplyNode("Mine_A", "producer", base_value=100, efficiency=0.9))
    optimizer.add_node(SupplyNode("Mine_B", "producer", base_value=100, efficiency=0.85)) # 备份源

    # 中间消费者（加工厂）
    optimizer.add_node(SupplyNode("Refinery_1", "intermediate", efficiency=0.8))
    
    # 顶级消费者（终端产品）
    optimizer.add_node(SupplyNode("Factory_Final", "apex", efficiency=0.95))

    # 添加能量流动关系（边）
    # Mine_A -> Refinery_1 (高依赖)
    optimizer.add_edge(SupplyChainEdge("Mine_A", "Refinery_1", transaction_cost=0.05, dependency_weight=10.0))
    # Mine_B -> Refinery_1 (低依赖，作为备份)
    optimizer.add_edge(SupplyChainEdge("Mine_B", "Refinery_1", transaction_cost=0.05, dependency_weight=2.0))
    
    # Refinery_1 -> Factory_Final
    optimizer.add_edge(SupplyChainEdge("Refinery_1", "Factory_Final", transaction_cost=0.02, dependency_weight=5.0))

    # 验证图
    validate_graph_integrity(optimizer)

    # 2. 计算系统效率
    sys_eff = optimizer.calculate_theoretical_efficiency()
    print(f"\nSystem Theoretical Efficiency: {sys_eff:.4f}")

    # 3. 模拟级联失效
    # 假设 Mine_A 倒闭
    print("\n--- Simulating Failure of Mine_A ---")
    impact = optimizer.simulate_cascade_failure("Mine_A")
    for node, loss in impact.items():
        print(f"Impact on {node}: {loss:.2%} supply disruption")

    # 4. 优化冗余策略
    print("\n--- Optimization Strategy for Refinery_1 ---")
    strategies = optimizer.optimize_redundancy_strategy("Refinery_1")
    for s in strategies:
        print(f"Strategy: {s}")
