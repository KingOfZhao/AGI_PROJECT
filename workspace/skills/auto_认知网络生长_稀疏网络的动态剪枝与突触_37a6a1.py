"""
模块: auto_认知网络生长_稀疏网络的动态剪枝与突触_37a6a1
描述: 实现基于神经可塑性原理的动态图网络，支持自动剪枝与突触生长。
"""

import logging
import numpy as np
import networkx as nx
from typing import List, Tuple, Dict, Optional, Set

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NeuroPlasticityNetwork:
    """
    一个模拟生物神经可塑性的动态稀疏图网络。
    
    该网络能够根据节点的激活历史和连接的使用频率，自动执行：
    1. 突触生长: 在高频激活区域生成新的连接。
    2. 突触修剪: 移除长期不活跃的连接和节点（模拟遗忘）。
    
    Attributes:
        graph (nx.DiGraph): 有向图结构，包含节点和边。
        decay_rate (float): 激活值的衰减率。
        prune_threshold (float): 活力值低于此阈值的边将被移除。
        growth_threshold (float): 激活值高于此阈值的节点将尝试生成新连接。
        max_nodes (int): 网络允许的最大节点数量。
    """
    
    def __init__(
        self, 
        initial_nodes: int = 64, 
        decay_rate: float = 0.95, 
        prune_threshold: float = 0.1, 
        growth_threshold: float = 0.8,
        max_nodes: int = 100
    ) -> None:
        """
        初始化认知网络。
        
        Args:
            initial_nodes: 初始节点数量，默认为64。
            decay_rate: 活力值的衰减系数 (0, 1)。
            prune_threshold: 边的修剪阈值。
            growth_threshold: 节点的生长触发阈值。
            max_nodes: 网络生长的上限。
        """
        if not (0 < decay_rate < 1):
            raise ValueError("decay_rate must be between 0 and 1")
        if initial_nodes < 1:
            raise ValueError("initial_nodes must be at least 1")
            
        self.graph = nx.DiGraph()
        self.decay_rate = decay_rate
        self.prune_threshold = prune_threshold
        self.growth_threshold = growth_threshold
        self.max_nodes = max_nodes
        
        # 初始化节点和边
        self._initialize_network(initial_nodes)
        logger.info(f"Network initialized with {initial_nodes} nodes.")

    def _initialize_network(self, n: int) -> None:
        """初始化稀疏连接的网络结构。"""
        nodes = [(i, {"activation": 0.0, "firing_count": 0}) for i in range(n)]
        self.graph.add_nodes_from(nodes)
        
        # 创建初始稀疏连接 (约5%的密度)
        for i in range(n):
            for j in range(n):
                if i != j and np.random.rand() < 0.05:
                    # 边属性: weight(权重), vitality(活力/使用频率)
                    self.graph.add_edge(i, j, weight=np.random.rand(), vitality=0.5)

    def update_state(self, input_signals: Dict[int, float]) -> None:
        """
        根据输入信号更新网络状态，并触发衰减。
        
        Args:
            input_signals: 字典，键为节点ID，值为外部输入的激活强度。
        """
        # 1. 更新节点激活度
        for node_id, signal in input_signals.items():
            if self.graph.has_node(node_id):
                current_act = self.graph.nodes[node_id].get('activation', 0.0)
                new_act = current_act + signal
                self.graph.nodes[node_id]['activation'] = min(new_act, 1.0) # 归一化上限
                self.graph.nodes[node_id]['firing_count'] = self.graph.nodes[node_id].get('firing_count', 0) + 1
            else:
                logger.warning(f"Node {node_id} not found in network.")

        # 2. 全局衰减
        self._apply_global_decay()

    def _apply_global_decay(self) -> None:
        """对所有节点和边的活力值应用指数衰减。"""
        for u, v, data in self.graph.edges(data=True):
            data['vitality'] *= self.decay_rate
            
        for node, data in self.graph.nodes(data=True):
            data['activation'] *= self.decay_rate

    def dynamic_pruning(self) -> int:
        """
        移除长期不活跃的连接和孤立节点。
        
        Returns:
            removed_count: 被移除的边和节点的总数量。
        """
        edges_to_remove = []
        
        # 1. 剪枝边
        for u, v, data in self.graph.edges(data=True):
            if data.get('vitality', 0) < self.prune_threshold:
                edges_to_remove.append((u, v))
        
        self.graph.remove_edges_from(edges_to_remove)
        
        # 2. 移除孤立节点 (可选，视具体AGI逻辑而定，这里假设保留核心结构)
        # 此处仅移除完全没有连接且激活度极低的节点
        nodes_to_remove = [
            n for n in self.graph.nodes() 
            if self.graph.degree(n) == 0 and self.graph.nodes[n]['activation'] < 0.01
        ]
        self.graph.remove_nodes_from(nodes_to_remove)
        
        removed_total = len(edges_to_remove) + len(nodes_to_remove)
        if removed_total > 0:
            logger.info(f"Pruned {len(edges_to_remove)} edges and {len(nodes_to_remove)} nodes.")
        
        return removed_total

    def dynamic_growth(self) -> int:
        """
        在高频激活区域生成新连接（突触生长）。
        
        逻辑：寻找激活度超过阈值的节点，向其邻域或随机未连接节点建立新连接。
        
        Returns:
            new_edges_count: 新生成的边数量。
        """
        new_edges_count = 0
        current_nodes = list(self.graph.nodes())
        
        if len(current_nodes) == 0:
            return 0

        for node in current_nodes:
            node_data = self.graph.nodes[node]
            if node_data.get('activation', 0) > self.growth_threshold:
                # 尝试生长
                # 策略：如果节点数量未达上限，有概率连接到其他活跃节点或新节点
                if np.random.rand() < 0.3: # 生长概率
                    # 选择目标：优先连接到也存在一定激活度的节点
                    potential_targets = [
                        n for n in current_nodes 
                        if n != node and not self.graph.has_edge(node, n)
                    ]
                    
                    if potential_targets:
                        target = np.random.choice(potential_targets)
                        # 建立新突触
                        self.graph.add_edge(node, target, weight=np.random.rand(), vitality=1.0)
                        new_edges_count += 1
                        logger.debug(f"New synapse grown: {node} -> {target}")
                    else:
                        # 如果没有合适的目标且未达上限，则分裂/生成新节点 (概念性实现)
                        if self.graph.number_of_nodes() < self.max_nodes:
                            new_id = max(current_nodes) + 1
                            self.graph.add_node(new_id, activation=0.1, firing_count=0)
                            self.graph.add_edge(node, new_id, weight=0.5, vitality=1.0)
                            new_edges_count += 1
                            logger.info(f"New node generated: {new_id} connected from {node}")

        return new_edges_count

    def get_network_stats(self) -> Dict[str, float]:
        """获取网络统计信息。"""
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "avg_vitality": np.mean([d['vitality'] for u, v, d in self.graph.edges(data=True)]) if self.graph.number_of_edges() > 0 else 0
        }

# 辅助函数：模拟单次训练周期
def run_plasticity_cycle(network: NeuroPlasticityNetwork, signals: Dict[int, float], steps: int = 1) -> None:
    """
    辅助函数：执行多次网络的更新、剪枝和生长周期。
    
    Args:
        network: NeuroPlasticityNetwork 实例。
        signals: 外部输入信号。
        steps: 迭代次数。
    """
    if not isinstance(network, NeuroPlasticityNetwork):
        raise TypeError("Invalid network object provided.")
        
    for step in range(steps):
        # 1. 输入信号刺激
        network.update_state(signals)
        
        # 2. 动态剪枝 (遗忘)
        network.dynamic_pruning()
        
        # 3. 动态生长 (学习)
        network.dynamic_growth()
        
        stats = network.get_network_stats()
        logger.info(f"Step {step+1}: Nodes={stats['node_count']}, Edges={stats['edge_count']}")

if __name__ == "__main__":
    # 使用示例
    # 1. 创建网络
    net = NeuroPlasticityNetwork(initial_nodes=64, max_nodes=80)
    
    # 2. 定义输入信号 (模拟对节点0和1的高频刺激)
    # 假设输入信号总是集中在前几个节点
    high_freq_signals = {0: 0.9, 1: 0.85, 2: 0.8}
    
    # 3. 运行模拟周期
    print("Starting simulation...")
    try:
        # 模拟10个时间步长
        run_plasticity_cycle(net, high_freq_signals, steps=10)
        
        # 4. 检查最终状态
        final_stats = net.get_network_stats()
        print(f"Final Network Stats: {final_stats}")
        
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)