"""
Module: cognitive_energy_budget_system
Description: 基于生态代谢率的认知能量预算系统。
"""

import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveEnergySystem")


class MetabolicState(Enum):
    """认知代谢状态枚举"""
    ACTIVE = "Active (Homeostasis)"
    STRESSED = "Resource Stressed"
    HIBERNATION = "Hibernation (Low Metabolism)"
    CRITICAL = "Critical Survival Mode"


@dataclass
class ResourceEnvironment:
    """外部资源环境定义"""
    total_compute_units: float  # 总可用算力 (FLOPS等)
    total_data_flux: float      # 数据流速率
    energy_budget: float        # 能量预算（电力/资金）

    @property
    def resource_abundance(self) -> float:
        """计算资源丰度指数 (0.0 - 1.0)"""
        # 这里使用简化的归一化逻辑，实际应用需要更复杂的基准测试
        base_requirement = 1000.0  # 基础生存阈值
        if base_requirement == 0:
            return 0.0
        abundance = (self.total_compute_units + self.total_data_flux) / (2 * base_requirement)
        return min(max(abundance, 0.0), 1.0)


@dataclass
class CognitiveNode:
    """认知系统中的节点（如神经网络层、记忆单元或Agent）"""
    node_id: str
    value_roi: float  # 价值/投资回报率 (0.0 - 1.0)
    maintenance_cost: float  # 维护成本
    entropy_level: float = 0.0  # 熵值（无用信息的积累）
    active: bool = True


class CognitiveMetabolicSystem:
    """
    基于生态代谢率的认知能量预算系统。
    
    实现了认知代谢标度律，根据环境资源动态调整系统活跃度（认知体温）。
    """

    def __init__(self, initial_nodes: List[CognitiveNode], environment: ResourceEnvironment):
        """
        初始化系统。
        
        Args:
            initial_nodes: 初始认知节点列表
            environment: 资源环境配置
        """
        self.nodes: Dict[str, CognitiveNode] = {n.node_id: n for n in initial_nodes}
        self.environment = environment
        self.state = MetabolicState.ACTIVE
        self.cognitive_temperature = 1.0  # 1.0 为标准活跃温度
        self._metabolic_scaling_factor = 0.75  # 模拟克莱伯定律的标度指数

        logger.info("System initialized with %d nodes.", len(self.nodes))

    def _calculate_metabolic_rate(self, mass: float) -> float:
        """
        辅助函数：根据生态代谢标度律计算基础代谢率。
        
        模拟生物学中的 Kleiber's Law (BMR ∝ M^0.75)。
        在此上下文中，mass 代表系统的 '活跃连接质量'。
        
        Args:
            mass: 系统的活跃质量（节点数量和复杂度的函数）
            
        Returns:
            float: 基础代谢率
        """
        if mass <= 0:
            return 0.0
        # 添加简单的边界检查
        mass = max(mass, 1e-9)
        bmr = math.pow(mass, self._metabolic_scaling_factor)
        return bmr

    def regulate_internal_state(self):
        """
        核心函数1：调节内部代谢状态和认知体温。
        
        根据外部资源丰度，调整系统状态（活跃/冬眠/临界），
        并设定认知体温，影响节点的活跃度阈值。
        """
        abundance = self.environment.resource_abundance
        current_load = sum(n.maintenance_cost for n in self.nodes.values() if n.active)
        metabolic_demand = self._calculate_metabolic_rate(len(self.nodes))

        logger.info(f"Regulating state. Abundance: {abundance:.2f}, Demand: {metabolic_demand:.2f}")

        # 状态机逻辑
        if abundance > 0.8:
            self.state = MetabolicState.ACTIVE
            self.cognitive_temperature = 1.0 + (abundance - 0.8) * 0.5  # 高资源时略微发热（探索模式）
        elif 0.3 <= abundance <= 0.8:
            self.state = MetabolicState.STRESSED
            self.cognitive_temperature = 0.8
        elif 0.1 <= abundance < 0.3:
            self.state = MetabolicState.HIBERNATION
            self.cognitive_temperature = 0.3  # 降低体温，抑制非必要活动
            logger.warning("Entering Hibernation Mode due to low resources.")
        else:
            self.state = MetabolicState.CRITICAL
            self.cognitive_temperature = 0.1  # 仅维持核心心跳
            logger.critical("CRITICAL: System entering survival mode.")

        # 检查负载是否超过预算，如果是，强制降低体温
        if current_load > self.environment.energy_budget:
            self.cognitive_temperature *= 0.5
            logger.warning("Budget exceeded. Forced cooling applied.")

    def execute_metabolic_optimization(self):
        """
        核心函数2：执行代谢优化策略（遗忘/修剪）。
        
        在低代谢模式下，主动增加节点熵增，并'遗忘'（关闭）
        低ROI的节点以保存能量。
        """
        if self.state == MetabolicState.ACTIVE:
            # 活跃模式下，甚至可能恢复部分节点（未实现）
            return

        logger.info(f"Executing optimization for state: {self.state.name}")

        # 决定遗忘的阈值取决于当前的认知体温
        # 温度越低，对ROI的要求越高（只有极高价值的节点才能在冬眠中存活）
        survival_threshold = self.cognitive_temperature * 0.8 

        nodes_to_deactivate = []

        for node in self.nodes.values():
            if not node.active:
                continue

            # 环境压力导致熵增（随机噪声/数据退化）
            entropy_increase = random.uniform(0, 0.1) * (1.0 - self.cognitive_temperature)
            node.entropy_level += entropy_increase

            # 检查节点是否应该被"代谢"（遗忘）
            # 判断标准：ROI低于阈值 且 (熵过高 或 系统处于危急状态)
            is_low_value = node.value_roi < survival_threshold
            is_high_entropy = node.entropy_level > 0.7
            is_critical_mode = self.state == MetabolicState.CRITICAL

            if is_critical_mode and node.value_roi < 0.9:
                # 危急模式：只保留绝对核心
                nodes_to_deactivate.append(node.node_id)
            elif is_low_value and is_high_entropy:
                nodes_to_deactivate.append(node.node_id)

        # 执行遗忘
        for nid in nodes_to_deactivate:
            if nid in self.nodes:
                self.nodes[nid].active = False
                logger.debug(f"Node {nid} deactivated (Forgotten) due to metabolic optimization.")

        logger.info(f"Optimization complete. Active nodes: {sum(1 for n in self.nodes.values() if n.active)}")

    def get_system_status(self) -> Dict:
        """辅助函数：获取当前系统状态的摘要"""
        active_nodes = [n for n in self.nodes.values() if n.active]
        return {
            "state": self.state.value,
            "cognitive_temperature": self.cognitive_temperature,
            "active_node_count": len(active_nodes),
            "total_node_count": len(self.nodes),
            "resource_abundance": self.environment.resource_abundance
        }


# ==========================================
# Usage Example / Test Simulation
# ==========================================
if __name__ == "__main__":
    # 1. 构建模拟环境
    # 初始资源丰富
    env = ResourceEnvironment(
        total_compute_units=2000.0,
        total_data_flux=1500.0,
        energy_budget=500.0
    )

    # 2. 构建初始认知节点
    nodes = [
        CognitiveNode("core_logic", value_roi=0.99, maintenance_cost=10.0),
        CognitiveNode("visual_encoder", value_roi=0.85, maintenance_cost=20.0),
        CognitiveNode("old_memory_1", value_roi=0.2, maintenance_cost=5.0),
        CognitiveNode("old_memory_2", value_roi=0.15, maintenance_cost=5.0),
        CognitiveNode("exploration_agent", value_roi=0.4, maintenance_cost=15.0),
    ]

    # 3. 初始化系统
    agi_system = CognitiveMetabolicSystem(nodes, env)
    
    print("--- Cycle 1: Abundant Resources ---")
    agi_system.regulate_internal_state()
    agi_system.execute_metabolic_optimization()
    print(agi_system.get_system_status())

    print("\n--- Cycle 2: Resource Drought (Simulating Winter) ---")
    # 模拟资源骤降
    env.total_compute_units = 200.0
    env.total_data_flux = 100.0
    agi_system.regulate_internal_state()
    agi_system.execute_metabolic_optimization()
    print(agi_system.get_system_status())

    print("\n--- Cycle 3: Critical Resources ---")
    # 模拟资源枯竭
    env.total_compute_units = 50.0
    env.total_data_flux = 10.0
    agi_system.regulate_internal_state()
    agi_system.execute_metabolic_optimization()
    print(agi_system.get_system_status())