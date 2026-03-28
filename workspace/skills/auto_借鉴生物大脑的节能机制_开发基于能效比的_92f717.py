"""
Module: bio_inspired_energy_efficient_scheduler
Description: 借鉴生物大脑的节能机制（如突触修剪和稀疏激活），开发基于能效比的节点优先级队列和剪枝策略。
"""

import logging
import heapq
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass(order=True)
class ComputeNode:
    """
    表示计算节点的类，包含能效比和激活状态。
    
    属性:
        node_id (str): 节点唯一标识符
        energy_cost (float): 激活该节点所需的能量（模拟生物代谢成本）
        utility_score (float): 节点对当前任务的效用/贡献度
        efficiency_ratio (float): utility_score / energy_cost (自动计算)
        is_active (bool): 节点是否处于激活状态
    """
    node_id: str = field(compare=False)
    energy_cost: float = field(compare=False)
    utility_score: float = field(compare=False)
    efficiency_ratio: float = field(init=False, compare=True)
    is_active: bool = field(default=True, compare=False)

    def __post_init__(self):
        """数据验证和能效比计算"""
        if self.energy_cost <= 0:
            logger.error(f"Node {self.node_id} has invalid energy cost: {self.energy_cost}")
            raise ValueError("Energy cost must be positive.")
        
        # 计算能效比
        self.efficiency_ratio = self.utility_score / self.energy_cost
        logger.debug(f"Node {self.node_id} initialized with efficiency: {self.efficiency_ratio:.4f}")

class EnergyAwareBrainScheduler:
    """
    借鉴生物大脑节能机制（如只激活相关神经元，抑制低效连接）的调度器。
    实现基于能效比的优先级队列和动态剪枝。
    """

    def __init__(self, global_energy_budget: float = 1000.0):
        """
        初始化调度器。
        
        Args:
            global_energy_budget (float): 系统总能量预算
        """
        self.global_energy_budget = global_energy_budget
        self.current_energy_consumption = 0.0
        # 使用堆结构维护优先级（注意：Python的heap是最小堆，我们需要最大堆，所以取负）
        self.priority_queue: List[ComputeNode] = []
        self.node_registry: Dict[str, ComputeNode] = {}
        logger.info(f"Scheduler initialized with budget: {global_energy_budget}")

    def _validate_node_inputs(self, energy: float, utility: float) -> None:
        """辅助函数：验证输入数据的合法性"""
        if not isinstance(energy, (int, float)) or not isinstance(utility, (int, float)):
            raise TypeError("Energy and utility must be numeric.")
        if energy <= 0:
            raise ValueError("Energy cost must be strictly positive.")

    def register_node(self, node_id: str, energy_cost: float, utility_score: float) -> None:
        """
        核心函数1: 注册节点并加入优先级队列。
        
        Args:
            node_id (str): 节点ID
            energy_cost (float): 能量消耗
            utility_score (float): 效用分数
        """
        try:
            self._validate_node_inputs(energy_cost, utility_score)
            
            if node_id in self.node_registry:
                logger.warning(f"Node {node_id} already exists. Updating.")
                # 实际场景中可能需要复杂的更新逻辑，这里简化为移除旧的
                # 注意：移除堆中元素比较复杂，这里仅做演示，实际生产建议使用更高效的索引结构
            
            node = ComputeNode(
                node_id=node_id,
                energy_cost=energy_cost,
                utility_score=utility_score
            )
            
            self.node_registry[node_id] = node
            # 存入堆时，取efficiency_ratio的负数以实现最大堆效果
            heapq.heappush(self.priority_queue, (-node.efficiency_ratio, node))
            logger.info(f"Registered node: {node_id} (Ratio: {node.efficiency_ratio:.2f})")
            
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to register node {node_id}: {e}")

    def run_pruning_and_scheduling(self) -> Tuple[List[str], float]:
        """
        核心函数2: 运行剪枝策略并调度节点。
        
        模拟生物大脑在能量受限时抑制低效神经元的机制。
        从优先级队列中依次取出能效比最高的节点，直到能量预算耗尽。
        低效节点将被'修剪'（标记为非活跃）。
        
        Returns:
            Tuple[List[str], float]: (激活的节点ID列表, 剩余能量)
        """
        logger.info("Starting pruning and scheduling cycle...")
        activated_nodes = []
        temp_heap = [] # 用于存储未处理的节点，保持堆结构
        
        # 重置当前消耗
        self.current_energy_consumption = 0.0
        
        while self.priority_queue:
            neg_ratio, node = heapq.heappop(self.priority_queue)
            
            # 边界检查：能量是否足够激活该节点
            if (self.current_energy_consumption + node.energy_cost) <= self.global_energy_budget:
                # 激活节点
                node.is_active = True
                self.current_energy_consumption += node.energy_cost
                activated_nodes.append(node.node_id)
                logger.debug(f"Activated node: {node.node_id}")
                
                # 如果需要保留节点在堆中用于下一轮，可以在这里重新push，或者根据业务逻辑重置
                # 这里假设这是一次性调度，所以不重新push回self.priority_queue
                # 但为了演示保留未使用的节点，我们使用temp_heap
            else:
                # 能量不足，执行"突触修剪" Synaptic Pruning
                node.is_active = False
                logger.warning(f"PRUNING node {node.node_id} due to energy constraints. (Cost: {node.energy_cost})")
                # 如果未激活的节点需要保留在系统中等待下次预算增加，可以放入temp_heap
                # heapq.heappush(temp_heap, (neg_ratio, node))

        # 恢复未处理的节点（如果有的话，本例中temp_heap保留未激活节点）
        self.priority_queue = temp_heap
        
        remaining_energy = self.global_energy_budget - self.current_energy_consumption
        logger.info(f"Scheduling complete. Activated {len(activated_nodes)} nodes. Remaining Energy: {remaining_energy:.2f}")
        
        return activated_nodes, remaining_energy

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统当前状态摘要"""
        active_count = sum(1 for n in self.node_registry.values() if n.is_active)
        return {
            "total_budget": self.global_energy_budget,
            "consumed": self.current_energy_consumption,
            "active_nodes": active_count,
            "pruned_nodes": len(self.node_registry) - active_count
        }

# 使用示例
if __name__ == "__main__":
    # 1. 初始化模拟大脑调度器，设定总能量预算
    scheduler = EnergyAwareBrainScheduler(global_energy_budget=100.0)
    
    # 2. 注册神经元节点（模拟不同的计算任务）
    # 节点A: 高能耗，极高贡献 (高能效)
    scheduler.register_node("Neuron_A", energy_cost=30.0, utility_score=90.0) 
    
    # 节点B: 低能耗，中等贡献 (极高能效)
    scheduler.register_node("Neuron_B", energy_cost=10.0, utility_score=50.0)
    
    # 节点C: 中等能耗，低贡献 (低能效)
    scheduler.register_node("Neuron_C", energy_cost=50.0, utility_score=20.0)
    
    # 节点D: 中等能耗，中等贡献 (中等能效)
    scheduler.register_node("Neuron_D", energy_cost=20.0, utility_score=40.0)
    
    # 3. 运行基于能效的调度和剪枝
    # 预期行为：
    # Budget = 100
    # 1. Neuron B (Ratio 5.0) -> Cost 10. Total 10. Rem 90.
    # 2. Neuron A (Ratio 3.0) -> Cost 30. Total 40. Rem 60.
    # 3. Neuron D (Ratio 2.0) -> Cost 20. Total 60. Rem 40.
    # 4. Neuron C (Ratio 0.4) -> Cost 50. Total would be 110 > 100. PRUNED.
    active_ids, remaining = scheduler.run_pruning_and_scheduling()
    
    print("\n--- Simulation Results ---")
    print(f"Active Nodes: {active_ids}")
    print(f"Remaining Energy: {remaining}")
    print(f"System Status: {scheduler.get_system_status()}")