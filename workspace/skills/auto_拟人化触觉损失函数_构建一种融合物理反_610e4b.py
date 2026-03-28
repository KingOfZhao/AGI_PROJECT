"""
名称: auto_拟人化触觉损失函数_构建一种融合物理反_610e4b
描述: 【拟人化触觉损失函数】构建一种融合物理反馈的调试机制。不仅依赖代码的逻辑报错，
      还引入'数字触觉'（如模拟物理摩擦力、材质阻尼的参数）。当AI生成的控制代码在物理
      引擎中运行时，若产生非自然的抖动（类比工匠手抖），系统自动判定为高损失值。
      这让AI在生成制造指令时，能像老工匠一样'感觉'材料的极限，避免过度切削或结构断裂，
      实现从'逻辑正确'到'工艺稳健'的跨越。
领域: cross_domain
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PhysicalState:
    """
    表示物理引擎在特定时间步长的状态数据。
    
    Attributes:
        timestamp (float): 时间戳 (s)。
        position (np.ndarray): 执行器的3D位置向量 [x, y, z]。
        velocity (np.ndarray): 执行器的3D速度向量 [vx, vy, vz]。
        force_feedback (np.ndarray): 末端执行器的受力/力矩反馈。
        material_resistance (float): 当前模拟的材料阻力系数 (0.0-1.0)。
    """
    timestamp: float
    position: np.ndarray
    velocity: np.ndarray
    force_feedback: np.ndarray
    material_resistance: float


class TactileLossFunction:
    """
    拟人化触觉损失函数类。
    
    该类用于评估AI生成的控制轨迹在物理仿真中的表现。
    它不仅仅检查是否到达目标点（逻辑正确），还通过计算“数字触觉”指标
    （如抖动、力反馈平滑度）来评估工艺的稳健性。
    
    Example:
        >>> # 模拟一段简单的物理状态数据
        >>> states = [
        ...     PhysicalState(0.0, np.array([0,0,0]), np.array([1,0,0]), np.array([0,0,0]), 0.5),
        ...     PhysicalState(0.1, np.array([0.1,0,0]), np.array([1,0,0]), np.array([5,0,0]), 0.5),
        ...     PhysicalState(0.2, np.array([0.2,0.01,0]), np.array([0.9,0.1,0]), np.array([5.5,0,0]), 0.5)
        ... ]
        >>> loss_fn = TactileLossFunction(damping_coeff=0.8)
        >>> loss, metrics = loss_fn.calculate_tactile_loss(states)
        >>> print(f"Total Loss: {loss:.4f}")
    """

    def __init__(self, damping_coeff: float = 0.9, friction_limit: float = 10.0):
        """
        初始化触觉损失函数参数。
        
        Args:
            damping_coeff (float): 理想的环境阻尼系数，用于评估运动是否平滑。
            friction_limit (float): 允许的最大静摩擦力/阻力阈值，超过此值视为操作过猛。
        """
        self.damping_coeff = damping_coeff
        self.friction_limit = friction_limit
        logger.info("TactileLossFunction initialized with damping={}, friction_limit={}".format(
            damping_coeff, friction_limit
        ))

    def _validate_inputs(self, trajectory: List[PhysicalState]) -> bool:
        """
        辅助函数：验证输入的物理轨迹数据。
        
        Args:
            trajectory (List[PhysicalState]): 物理状态列表。
            
        Returns:
            bool: 数据是否有效。
            
        Raises:
            ValueError: 如果数据为空或格式不正确。
        """
        if not trajectory:
            logger.error("Input trajectory is empty.")
            raise ValueError("Trajectory cannot be empty.")
        
        if not isinstance(trajectory[0], PhysicalState):
            logger.error("Invalid data type in trajectory.")
            raise TypeError("Trajectory must contain PhysicalState objects.")
            
        return True

    def _calculate_jitter_index(self, velocities: np.ndarray) -> float:
        """
        辅助函数：计算抖动指数。
        
        通过计算速度向量的二阶导数（加速度的突变，即Jerk）来量化“手抖”程度。
        
        Args:
            velocities (np.ndarray): 速度序列 (N, 3)。
            
        Returns:
            float: 归一化的抖动指数。
        """
        if len(velocities) < 3:
            return 0.0
        
        # 计算加速度 (速度的一阶差分)
        accel = np.diff(velocities, axis=0)
        # 计算 Jerk (加速度的一阶差分，即速度的二阶差分)
        jerk = np.diff(accel, axis=0)
        
        # 取范数并求平均
        jerk_magnitudes = np.linalg.norm(jerk, axis=1)
        jitter_score = np.mean(jerk_magnitudes)
        
        return float(jitter_score)

    def calculate_material_resistance_loss(self, trajectory: List[PhysicalState]) -> Tuple[float, dict]:
        """
        核心函数 1: 计算基于材料阻力反馈的损失。
        
        模拟“工匠手感”：如果AI施加的力超过了材料的物理极限（由material_resistance
        和force_feedback模拟），则产生高损失，意味着可能导致材料断裂或工具磨损。
        
        Args:
            trajectory (List[PhysicalState]): 物理状态时间序列。
            
        Returns:
            Tuple[float, dict]: (损失值, 详细指标字典)
        """
        self._validate_inputs(trajectory)
        
        excess_force_penalties = []
        resistance_violations = 0
        
        for state in trajectory:
            # 模拟物理极限：力反馈不应超过 (1.0 / material_resistance) * friction_limit
            # 这里简化模型：假设材料越硬(resistance越高)，允许的力越大，但也越脆
            max_safe_force = self.friction_limit * (1.0 + state.material_resistance)
            current_force_mag = np.linalg.norm(state.force_feedback)
            
            if current_force_mag > max_safe_force:
                # 超出安全力，指数级惩罚
                excess = (current_force_mag - max_safe_force) ** 2
                excess_force_penalties.append(excess)
                resistance_violations += 1
            else:
                excess_force_penalties.append(0.0)

        # 归一化损失
        raw_loss = np.sum(excess_force_penalties)
        # 使用 Sigmoid-like 函数平滑损失，防止梯度爆炸，同时保持区分度
        normalized_loss = 1 - np.exp(-raw_loss / 1000) 
        
        metrics = {
            "resistance_violations_count": resistance_violations,
            "avg_excess_force": np.mean(excess_force_penalties),
            "material_loss_raw": raw_loss
        }
        
        logger.debug(f"Calculated material resistance loss: {normalized_loss:.4f}")
        return normalized_loss, metrics

    def calculate_kinesthetic_loss(self, trajectory: List[PhysicalState]) -> Tuple[float, dict]:
        """
        核心函数 2: 计算动觉/运动学损失（抖动与阻尼）。
        
        模拟“动作平滑度”：评估动作是否像老工匠一样流畅，还是像新手一样抖动。
        包含物理阻尼的评估。
        
        Args:
            trajectory (List[PhysicalState]): 物理状态时间序列。
            
        Returns:
            Tuple[float, dict]: (损失值, 详细指标字典)
        """
        self._validate_inputs(trajectory)
        
        velocities = np.array([s.velocity for s in trajectory])
        
        # 1. 计算抖动 (Jerk)
        jitter_index = self._calculate_jitter_index(velocities)
        
        # 2. 检查速度是否过高（模拟物理摩擦/阻尼限制）
        # 理论上，高阻尼环境下高速运动需要极大能量，可能是不稳定的标志
        speed_magnitudes = np.linalg.norm(velocities, axis=1)
        avg_speed = np.mean(speed_magnitudes)
        max_speed = np.max(speed_magnitudes)
        
        # 假设有一个基于阻尼的安全速度阈值
        safe_speed_threshold = 10.0 / self.damping_coeff
        speed_violation_penalty = max(0, max_speed - safe_speed_threshold)
        
        # 综合损失
        # 抖动权重更高，因为它是工艺不精的主要表现
        total_loss = (jitter_index * 0.7) + (speed_violation_penalty * 0.3)
        
        metrics = {
            "jitter_index": jitter_index,
            "average_speed": avg_speed,
            "max_speed": max_speed,
            "speed_violation": speed_violation_penalty
        }
        
        logger.debug(f"Calculated kinesthetic loss: {total_loss:.4f}")
        return total_loss, metrics

    def compute_total_tactile_loss(self, trajectory: List[PhysicalState]) -> Tuple[float, dict]:
        """
        汇总函数：计算总的拟人化触觉损失。
        
        Args:
            trajectory (List[PhysicalState]): 物理状态时间序列。
            
        Returns:
            Tuple[float, dict]: 总损失值和合并的详细指标。
        """
        try:
            loss_material, metrics_m = self.calculate_material_resistance_loss(trajectory)
            loss_motion, metrics_k = self.calculate_kinesthetic_loss(trajectory)
            
            # 权重融合
            total_loss = 0.5 * loss_material + 0.5 * loss_motion
            
            combined_metrics = {**metrics_m, **metrics_k}
            combined_metrics['total_tactile_loss'] = total_loss
            
            logger.info(f"Total Tactile Loss computed: {total_loss:.4f}")
            return total_loss, combined_metrics
            
        except Exception as e:
            logger.error(f"Error computing tactile loss: {e}")
            # 返回一个极大的损失值以示惩罚
            return float('inf'), {"error": str(e)}

# ==========================================
# 使用示例与模拟测试
# ==========================================

def run_simulation_example():
    """
    演示如何使用 TactileLossFunction 来评估一段模拟的控制轨迹。
    """
    print("--- Running Tactile Loss Function Simulation ---")
    
    # 1. 生成模拟数据
    # 场景 A: 平滑的运动 (老工匠)
    smooth_trajectory = []
    for t in np.linspace(0, 1, 10):
        state = PhysicalState(
            timestamp=t,
            position=np.array([t, 0, 0]),
            velocity=np.array([1.0, 0, 0]), # 匀速
            force_feedback=np.array([2.0, 0, 0]), # 恒定小的力
            material_resistance=0.5
        )
        smooth_trajectory.append(state)
    
    # 场景 B: 抖动的运动 (新手/不稳定的AI)
    jittery_trajectory = []
    for t in np.linspace(0, 1, 10):
        # 添加随机抖动
        noise_vel = np.random.normal(0, 0.5, 3)
        noise_force = np.random.normal(0, 10, 3) # 力反馈剧烈波动
        
        state = PhysicalState(
            timestamp=t,
            position=np.array([t, 0, 0]),
            velocity=np.array([1.0, 0, 0]) + noise_vel, 
            force_feedback=np.array([2.0, 0, 0]) + noise_force, 
            material_resistance=0.5
        )
        jittery_trajectory.append(state)

    # 2. 初始化损失函数
    loss_fn = TactileLossFunction(damping_coeff=0.8, friction_limit=15.0)
    
    # 3. 评估场景 A
    print("\n[Evaluating Smooth Trajectory]")
    loss_a, metrics_a = loss_fn.compute_total_tactile_loss(smooth_trajectory)
    print(f"Total Loss: {loss_a:.4f} (Lower is better)")
    print(f"Metrics: Jitter={metrics_a['jitter_index']:.4f}, Resistance Violations={metrics_a['resistance_violations_count']}")

    # 4. 评估场景 B
    print("\n[Evaluating Jittery Trajectory]")
    loss_b, metrics_b = loss_fn.compute_total_tactile_loss(jittery_trajectory)
    print(f"Total Loss: {loss_b:.4f} (Lower is better)")
    print(f"Metrics: Jitter={metrics_b['jitter_index']:.4f}, Resistance Violations={metrics_b['resistance_violations_count']}")

if __name__ == "__main__":
    run_simulation_example()