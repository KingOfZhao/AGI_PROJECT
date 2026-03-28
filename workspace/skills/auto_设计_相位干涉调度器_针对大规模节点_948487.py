"""
模块: auto_设计_相位干涉调度器_针对大规模节点_948487
描述:
    设计并实现一个基于音乐复节奏理论的'相位干涉调度器'。
    针对大规模节点（如2467+）的维护，摒弃传统单调的心跳机制，
    转而采用具有微周期差异的'节奏'（Rhythms）。通过监测不同
    频率节点的激活相位，利用干涉原理预测系统峰值和潜在死锁。
    
    核心功能:
    1. 将系统负载转化为“复节奏”模式，避免惊群效应。
    2. 监测多频率节点的“重拍”（相位对齐）时刻。
    3. 动态微调节点的执行相位，平滑系统负载曲线。

Author: AGI System
Date: 2023-10-27
"""

import logging
import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class NodeCategory(Enum):
    """定义节点的类别，不同类别对应不同的基础频率（心跳周期）。"""
    DATABASE = "DATABASE"     # 慢节奏，长周期
    COMPUTE = "COMPUTE"       # 中等节奏
    NETWORK_IO = "NETWORK_IO" # 快节奏，短周期
    UI_RENDER = "UI_RENDER"   # 极快节奏


@dataclass
class NodeRhythm:
    """
    节点节奏配置对象。
    
    Attributes:
        node_id (str): 唯一节点标识符。
        category (NodeCategory): 节点类别。
        base_frequency (float): 基础频率（Hz），即每秒心跳次数。
        phase_shift (float): 初始相位偏移 (0.0 到 1.0)。
        current_phase (float): 当前相位 (0.0 到 2*PI)。
    """
    node_id: str
    category: NodeCategory
    base_frequency: float
    phase_shift: float = 0.0
    current_phase: float = 0.0

    def __post_init__(self):
        """初始化后处理，设置默认相位。"""
        if not 0.0 <= self.phase_shift < 1.0:
            raise ValueError(f"Phase shift must be in [0, 1), got {self.phase_shift}")
        
        # 将相位偏移转换为弧度
        self.current_phase = self.phase_shift * 2 * math.pi
        logger.debug(f"Node {self.node_id} initialized with phase {self.current_phase:.2f} rad.")


class PhaseInterferenceScheduler:
    """
    相位干涉调度器。
    
    利用复节奏（Polyrhythm）原理，管理大规模节点的并发控制。
    当多个不同频率的节点在某一时刻相位对齐（发生干涉/重拍），
    调度器判定为高风险时刻，并建议推迟非关键任务以避免系统过载。
    """

    def __init__(self, coherence_threshold: float = 0.9):
        """
        初始化调度器。
        
        Args:
            coherence_threshold (float): 
                相位相干性阈值 (0.0-1.0)。
                当节点群的平均相位向量模长超过此值时，视为“重拍”。
        """
        self.nodes: Dict[str, NodeRhythm] = {}
        self.coherence_threshold = coherence_threshold
        self.tick_count = 0
        logger.info("PhaseInterferenceScheduler initialized.")

    def register_node(self, node: NodeRhythm) -> bool:
        """
        核心函数 1: 注册节点到调度器。
        
        Args:
            node (NodeRhythm): 待注册的节点对象。
            
        Returns:
            bool: 注册是否成功。
        """
        if not isinstance(node, NodeRhythm):
            logger.error("Invalid node type provided.")
            return False
        
        if node.node_id in self.nodes:
            logger.warning(f"Node {node.node_id} already exists. Updating.")
        
        self.nodes[node.node_id] = node
        logger.info(f"Registered Node: {node.node_id} (Freq: {node.base_frequency} Hz)")
        return True

    def calculate_interference_intensity(self) -> Tuple[float, float]:
        """
        核心函数 2: 计算当前时刻的系统干涉强度。
        
        通过计算所有节点的相位向量之和（类似波的叠加），
        得到系统的“合力”大小。
        
        Returns:
            Tuple[float, float]: 
                (干涉强度, 平均相位角)
                干涉强度范围 [0, 1]，1表示完全同相（危险），0表示均匀分布（平稳）。
        """
        if not self.nodes:
            return 0.0, 0.0

        sum_cos = 0.0
        sum_sin = 0.0
        
        active_nodes = list(self.nodes.values())
        
        for node in active_nodes:
            # 累加单位向量
            sum_cos += math.cos(node.current_phase)
            sum_sin += math.sin(node.current_phase)
            
        # 计算平均向量
        n = len(active_nodes)
        avg_x = sum_cos / n
        avg_y = sum_sin / n
        
        # 模长代表相干性
        coherence = math.sqrt(avg_x**2 + avg_y**2)
        
        # 计算平均相位角
        avg_phase = math.atan2(avg_y, avg_x)
        
        return coherence, avg_phase

    def _advance_time(self, delta_time: float):
        """
        辅助函数: 推进模拟时间，更新所有节点的相位。
        
        Args:
            delta_time (float): 推进的时间（秒）。
        """
        for node in self.nodes.values():
            # 角速度 = 2 * PI * 频率
            angular_velocity = 2 * math.pi * node.base_frequency
            node.current_phase += angular_velocity * delta_time
            
            # 保持相位在 [0, 2*PI] 范围内
            node.current_phase %= (2 * math.pi)

    def simulate_tick(self, delta_time: float = 0.1) -> Dict[str, float]:
        """
        执行一次调度周期的模拟。
        
        Args:
            delta_time (float): 时间步长。
            
        Returns:
            Dict[str, float]: 包含当前状态信息的字典。
        """
        self._advance_time(delta_time)
        self.tick_count += 1
        
        coherence, phase = self.calculate_interference_intensity()
        
        # 如果发生“重拍”（高相干性），触发预警
        status = "NORMAL"
        if coherence > self.coherence_threshold:
            status = "CRITICAL_PEAK"
            logger.warning(
                f"⚡ INTERFERENCE DETECTED! Coherence: {coherence:.2f}. "
                f"Multiple rhythms aligning. Risk of system lockup."
            )
        elif coherence > self.coherence_threshold * 0.7:
            status = "WARNING"
            logger.info(f"Rising intensity detected: {coherence:.2f}")

        return {
            "tick": self.tick_count,
            "coherence": coherence,
            "mean_phase": phase,
            "status": status
        }

    def optimize_phase_distribution(self):
        """
        高级功能: 优化当前节点的相位以减少未来的干涉。
        简单策略：如果某类节点过于集中，随机微调其相位。
        """
        logger.info("Running phase optimization (Anti-herd effect)...")
        for node in self.nodes.values():
            # 如果随机数小于0.1，给予一个小的相位微调
            if random.random() < 0.1:
                adjustment = random.uniform(-0.1, 0.1)
                node.current_phase = (node.current_phase + adjustment) % (2 * math.pi)


def simulate_large_scale_cluster():
    """
    使用示例：模拟一个包含大量节点（2500+）的集群运行。
    """
    scheduler = PhaseInterferenceScheduler(coherence_threshold=0.85)
    
    # 模拟生成 2467 个节点
    # 数据库节点 (慢速，少部分) - 10s 周期 -> 0.1 Hz
    # 计算节点 (中速) - 5s 周期 -> 0.2 Hz
    # IO节点 (快速) - 2s 周期 -> 0.5 Hz
    
    node_configs = [
        (NodeCategory.DATABASE, 0.1, 100),
        (NodeCategory.COMPUTE, 0.2, 800),
        (NodeCategory.NETWORK_IO, 0.5, 1000),
        (NodeCategory.UI_RENDER, 1.0, 567)
    ]
    
    total_nodes = 0
    for category, freq, count in node_configs:
        for i in range(count):
            # 随机分配初始相位，模拟真实世界的不同步
            phase = random.random()
            node = NodeRhythm(
                node_id=f"{category.value}_{i}",
                category=category,
                base_frequency=freq,
                phase_shift=phase
            )
            scheduler.register_node(node)
            total_nodes += 1
            
    print(f"\n=== Starting Simulation with {total_nodes} nodes ===")
    
    # 运行 100 个 tick
    try:
        for _ in range(100):
            # 每次步进 0.2 秒
            stats = scheduler.simulate_tick(delta_time=0.2)
            
            # 模拟：如果在峰值，尝试优化
            if stats['status'] == "CRITICAL_PEAK":
                scheduler.optimize_phase_distribution()
                
    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)

    print("\n=== Simulation Complete ===")

if __name__ == "__main__":
    simulate_large_scale_cluster()