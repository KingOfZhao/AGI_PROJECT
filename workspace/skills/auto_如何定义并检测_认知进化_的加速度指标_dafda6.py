"""
模块名称: auto_如何定义并检测_认知进化_的加速度指标_dafda6
描述: 该模块构建了一个复合指标系统，用于量化AGI系统的“认知进化”速度。
      它不仅仅关注知识库的规模（节点数量），而是深入评估连接密度、
      证伪周转效率以及跨域概念的复用能力。
      
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CognitiveState:
    """
    表示系统在某一时间点的认知状态快照。
    
    Attributes:
        timestamp (float): 时间戳（Unix时间或模拟时间）。
        total_nodes (int): 知识节点总数。
        total_edges (int): 知识图谱中的连接总数。
        falsifications (int): 该时间段内被证伪或重构的概念数量。
        domain_crossings (int): 概念在不同领域间被调用的次数。
    """
    timestamp: float
    total_nodes: int
    total_edges: int
    falsifications: int = 0
    domain_crossings: int = 0

@dataclass
class CognitiveMetrics:
    """
    计算后的标准化认知指标向量。
    
    范围通常在 [0, 1] 之间，用于消除量纲影响。
    """
    node_growth_rate: float = 0.0
    connectivity_index: float = 0.0  # 替代简单的连接数，考虑网络密度
    falsification_velocity: float = 0.0
    cross_domain_reuse: float = 0.0
    
    def to_vector(self) -> Tuple[float, float, float, float]:
        """返回指标向量，用于后续的加速度计算。"""
        return (
            self.node_growth_rate,
            self.connectivity_index,
            self.falsification_velocity,
            self.cross_domain_reuse
        )

@dataclass
class AccelerationResult:
    """加速度检测结果。"""
    is_accelerating: bool
    acceleration_vector: Tuple[float, float, float, float]
    composite_score: float  # 加权和
    details: str

class CognitiveEvolutionMonitor:
    """
    AGI认知进化监测仪。
    
    用于计算单一时间片的指标以及连续时间片之间的加速度。
    """
    
    def __init__(self, window_size: int = 3, acceleration_threshold: float = 0.05):
        """
        初始化监测仪。
        
        Args:
            window_size (int): 用于计算趋势的历史窗口大小。
            acceleration_threshold (float): 判定为'加速'的复合增长率阈值。
        """
        self.history: List[CognitiveState] = []
        self.metrics_history: List[CognitiveMetrics] = []
        self.window_size = window_size
        self.acceleration_threshold = acceleration_threshold
        logger.info("CognitiveEvolutionMonitor initialized with window size %d", window_size)

    def _validate_state(self, state: CognitiveState) -> bool:
        """验证输入状态的合法性。"""
        if state.total_nodes < 0 or state.total_edges < 0:
            logger.error("Invalid state: Negative nodes or edges detected.")
            raise ValueError("Nodes and edges must be non-negative.")
        if self.history and state.timestamp <= self.history[-1].timestamp:
            logger.warning("Non-sequential timestamp detected. Calculation may be inaccurate.")
        return True

    @staticmethod
    def _safe_divide(numerator: float, denominator: float) -> float:
        """辅助函数：安全除法，防止除以零。"""
        if denominator == 0:
            return 0.0
        return numerator / denominator

    def calculate_metrics(self, current: CognitiveState, previous: Optional[CognitiveState] = None) -> CognitiveMetrics:
        """
        [核心函数 1] 计算当前状态的认知指标向量。
        
        如果没有提供前一状态，则部分速率指标为0。
        
        Args:
            current (CognitiveState): 当前快照。
            previous (Optional[CognitiveState]): 上一时间步快照。
            
        Returns:
            CognitiveMetrics: 标准化后的指标对象。
        """
        self._validate_state(current)
        
        node_growth = 0.0
        falsification_vel = 0.0
        time_delta = 1.0 # 默认时间单位

        if previous:
            time_delta = max(0.001, current.timestamp - previous.timestamp)
            node_diff = current.total_nodes - previous.total_nodes
            # 归一化节点增长率 (使用Log防止数值爆炸，这里简单处理)
            node_growth = self._safe_divide(node_diff, previous.total_nodes) / time_delta
            
            # 证伪周转率 (代表自我修正的速度)
            falsification_vel = self._safe_divide(current.falsifications, current.total_nodes) / time_delta

        # 连接率 (网络密度): 2*E / (V*(V-1))
        # 近似为平均度数
        density = self._safe_divide(current.total_edges, current.total_nodes * (current.total_nodes - 1) / 2) \
                  if current.total_nodes > 1 else 0
                  
        # 跨域复用指数
        reuse_index = self._safe_divide(current.domain_crossings, current.total_nodes)

        metrics = CognitiveMetrics(
            node_growth_rate=min(node_growth, 1.0), # Cap at 1.0 for stability in demo
            connectivity_index=density,
            falsification_velocity=min(falsification_vel, 1.0),
            cross_domain_reuse=min(reuse_index, 1.0)
        )
        
        logger.debug(f"Calculated metrics: {metrics}")
        return metrics

    def detect_acceleration(self, new_state: CognitiveState) -> AccelerationResult:
        """
        [核心函数 2] 检测认知进化的加速度。
        
        通过比较当前指标向量与历史平均向量的变化率来判断。
        
        Args:
            new_state (CognitiveState): 最新的系统状态。
            
        Returns:
            AccelerationResult: 包含是否加速、加速度向量和综合得分。
        """
        if not self._validate_state(new_state):
            raise ValueError("Invalid input state")

        # 1. 计算当前指标
        prev_state = self.history[-1] if self.history else None
        current_metrics = self.calculate_metrics(new_state, prev_state)
        
        # 2. 更新历史
        self.history.append(new_state)
        self.metrics_history.append(current_metrics)
        
        # 保持窗口大小
        if len(self.history) > self.window_size:
            self.history.pop(0)
            self.metrics_history.pop(0)

        if len(self.metrics_history) < 2:
            return AccelerationResult(False, (0,0,0,0), 0.0, "Insufficient data for acceleration calculation.")

        # 3. 计算加速度 (当前指标 - 历史平均) / 历史平均
        # 这里的加速度定义为相对于近期平均水平的“提升速度”
        historical_avg = self._calculate_historical_average()
        curr_vec = current_metrics.to_vector()
        avg_vec = historical_avg.to_vector()
        
        acceleration_components = []
        for i in range(4):
            # (Current - Avg) / Avg
            comp_accel = self._safe_divide(curr_vec[i] - avg_vec[i], avg_vec[i] if avg_vec[i] != 0 else 1.0)
            acceleration_components.append(comp_accel)

        # 4. 计算复合得分 (加权平均)
        # 权重: 连接性(0.4), 跨域(0.3), 证伪(0.2), 节点增长(0.1) - 强调质量优于数量
        weights = [0.1, 0.4, 0.2, 0.3] 
        composite_score = sum(a * w for a, w in zip(acceleration_components, weights))
        
        is_accelerating = composite_score > self.acceleration_threshold
        
        result = AccelerationResult(
            is_accelerating=is_accelerating,
            acceleration_vector=tuple(acceleration_components),
            composite_score=composite_score,
            details=f"Composite score {composite_score:.4f} vs threshold {self.acceleration_threshold}"
        )
        
        logger.info(f"Acceleration Check: {'PASS' if is_accelerating else 'FAIL'}. Score: {composite_score:.4f}")
        return result

    def _calculate_historical_average(self) -> CognitiveMetrics:
        """[辅助函数] 计算历史窗口内的平均指标。"""
        if not self.metrics_history:
            return CognitiveMetrics()
            
        sums = [0.0, 0.0, 0.0, 0.0]
        count = len(self.metrics_history)
        
        for m in self.metrics_history:
            vec = m.to_vector()
            for i in range(4):
                sums[i] += vec[i]
                
        return CognitiveMetrics(
            node_growth_rate=sums[0]/count,
            connectivity_index=sums[1]/count,
            falsification_velocity=sums[2]/count,
            cross_domain_reuse=sums[3]/count
        )

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 创建监测仪实例
    monitor = CognitiveEvolutionMonitor(window_size=3, acceleration_threshold=0.05)
    
    # 模拟数据输入
    # 阶段 1: 初始状态
    state_1 = CognitiveState(timestamp=1.0, total_nodes=100, total_edges=150, falsifications=5, domain_crossings=10)
    
    # 阶段 2: 线性增长 (无加速)
    state_2 = CognitiveState(timestamp=2.0, total_nodes=110, total_edges=165, falsifications=5, domain_crossings=11)
    
    # 阶段 3: 指数/结构性增长 (连接率和复用率大幅提升 - 真正的认知进化)
    state_3 = CognitiveState(timestamp=3.0, total_nodes=140, total_edges=350, falsifications=20, domain_crossings=80)

    print("--- Processing State 1 ---")
    res1 = monitor.detect_acceleration(state_1)
    print(f"Result: {res1.details}")

    print("\n--- Processing State 2 (Linear Growth) ---")
    res2 = monitor.detect_acceleration(state_2)
    print(f"Is Accelerating: {res2.is_accelerating}")
    print(f"Score: {res2.composite_score:.4f}")

    print("\n--- Processing State 3 (Structural Phase Transition) ---")
    res3 = monitor.detect_acceleration(state_3)
    print(f"Is Accelerating: {res3.is_accelerating}")
    print(f"Acceleration Vector (Growth, Conn, Falsify, Reuse): {res3.acceleration_vector}")
    print(f"Composite Score: {res3.composite_score:.4f}")
    print(f"Details: {res3.details}")