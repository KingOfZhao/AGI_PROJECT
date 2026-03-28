"""
模块名称: affective_robot_control.py
描述: 实现基于情感计算的物理机器人控制回路，建立情绪-精度动态补偿模型。
      该模块通过模拟机器人的情绪状态（如焦虑、自信）来动态调整运动控制的精度参数，
      实现类似于人类的"紧张导致僵硬"或"放松导致平滑"的运动特性。

Author: AGI System
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RobotState(Enum):
    """机器人内部情绪/生理状态枚举"""
    IDLE = 0
    CALM = 1
    ALERT = 2
    ANXIOUS = 3
    PANIC = 4

@dataclass
class EmotionalState:
    """
    情感状态数据模型。
    
    属性:
        arousal (float): 唤醒度 (0.0 到 1.0)，表示活跃/兴奋程度。
        valence (float): 效价 (0.0 到 1.0)，表示愉快程度。
        confidence (float): 自信度 (0.0 到 1.0)，影响决策的果断性。
        timestamp (float): 状态生成的时间戳。
    """
    arousal: float
    valence: float
    confidence: float
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """数据验证"""
        if not (0.0 <= self.arousal <= 1.0):
            raise ValueError(f"Arousal must be between 0 and 1, got {self.arousal}")
        if not (0.0 <= self.valence <= 1.0):
            raise ValueError(f"Valence must be between 0 and 1, got {self.valence}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")

@dataclass
class ControlParameters:
    """
    机器人控制参数模型。
    
    属性:
        kp (float): 比例增益。
        ki (float): 积分增益。
        kd (float): 微分增益。
        max_speed (float): 最大运动速度限制。
        smoothing_factor (float): 运动平滑因子 (0.0-1.0)。
    """
    kp: float
    ki: float
    kd: float
    max_speed: float
    smoothing_factor: float

def _calculate_emotional_damping(state: EmotionalState) -> float:
    """
    [辅助函数] 根据情感状态计算系统的阻尼系数。
    
    该函数模拟了情绪对物理控制的影响。高唤醒度/低自信通常会导致系统"僵硬"，
    即增加阻尼或减少平滑度，以防止错误，但牺牲了灵活性。
    
    参数:
        state (EmotionalState): 当前的情感状态。
        
    返回:
        float: 计算出的平滑因子 (0.0 到 1.0)。
               1.0 表示最平滑，0.0 表示完全僵硬。
    """
    try:
        # 焦虑因子：唤醒度高且自信低时，焦虑增加
        anxiety_metric = state.arousal * (1.0 - state.confidence)
        
        # 计算平滑因子：焦虑越高，平滑度越低（动作越僵硬/精细）
        # 使用指数衰减模型
        smoothing = math.exp(-3.0 * anxiety_metric)
        
        # 边界裁剪
        return max(0.05, min(1.0, smoothing))
    except Exception as e:
        logger.error(f"Error calculating emotional damping: {e}")
        return 0.5  # 返回安全默认值

def map_emotion_to_control_params(state: EmotionalState) -> ControlParameters:
    """
    [核心函数 1] 将情感状态映射为具体的机器人控制参数。
    
    实现了"情绪-精度"动态补偿模型的核心逻辑。
    当机器人处于"焦虑"或"高唤醒"状态时，降低PID的P项以减少过冲风险，
    同时降低速度限制，增加平滑因子（或通过平滑函数处理）。
    
    参数:
        state (EmotionalState): 输入的情感状态对象。
        
    返回:
        ControlParameters: 计算后的控制参数。
        
    异常:
        TypeError: 如果输入类型不正确。
    """
    if not isinstance(state, EmotionalState):
        logger.error("Invalid input type for map_emotion_to_control_params")
        raise TypeError("Input must be an EmotionalState instance")

    logger.info(f"Mapping emotional state: Arousal={state.arousal:.2f}, Conf={state.confidence:.2f}")

    try:
        # 基础PID参数 (模拟标准工业设置)
        base_kp = 1.8
        base_ki = 0.1
        base_kd = 0.5
        base_max_speed = 1.5 # m/s

        # 情感调制因子
        # 自信度低时，降低Kp以减少震荡风险，变得更保守
        kp_mod = 0.5 + (0.5 * state.confidence)
        
        # 唤醒度高时（紧张），降低最大速度以保安全
        speed_mod = 1.0 - (state.arousal * 0.7)
        
        # 计算动态平滑因子
        smoothing = _calculate_emotional_damping(state)

        # 构建参数
        params = ControlParameters(
            kp=base_kp * kp_mod,
            ki=base_ki,
            kd=base_kd * (1 + (1 - state.confidence)), # 不自信时增加阻尼D
            max_speed=base_max_speed * max(0.1, speed_mod),
            smoothing_factor=smoothing
        )

        logger.debug(f"Generated Control Params: Kp={params.kp:.3f}, Speed={params.max_speed:.2f}")
        return params

    except Exception as e:
        logger.critical(f"Critical error in parameter mapping: {e}")
        # 故障安全：返回最保守的参数
        return ControlParameters(kp=0.5, ki=0.0, kd=1.0, max_speed=0.1, smoothing_factor=0.1)

def execute_emotional_actuation(
    target_position: Tuple[float, float, float],
    current_position: Tuple[float, float, float],
    params: ControlParameters
) -> Tuple[float, float, float]:
    """
    [核心函数 2] 基于给定的控制参数执行动作计算。
    
    模拟机器人的底层运动控制回路。这里简化了PID计算，重点展示
    如何应用平滑因子（Smoothing Factor）来模拟情感对运动轨迹的影响。
    
    输入格式:
        target_position: (x, y, z) 目标坐标
        current_position: (x, y, z) 当前坐标
        
    输出格式:
        Tuple[float, float, float]: 计算出的速度向量
    """
    if len(target_position) != 3 or len(current_position) != 3:
        raise ValueError("Positions must be 3-dimensional tuples (x, y, z)")

    velocity_vector = [0.0, 0.0, 0.0]
    
    try:
        for i in range(3):
            # 计算原始误差
            error = target_position[i] - current_position[i]
            
            # 简化的P控制器计算原始速度
            raw_velocity = error * params.kp
            
            # 应用情感平滑/阻尼模型
            # 这里的平滑因子混合了当前速度和目标速度
            # smoothing_factor 越低，动作越"生硬"或"谨慎"
            smoothed_velocity = raw_velocity * params.smoothing_factor
            
            # 应用速度限制
            if abs(smoothed_velocity) > params.max_speed:
                smoothed_velocity = math.copysign(params.max_speed, smoothed_velocity)
            
            velocity_vector[i] = smoothed_velocity

        logger.info(f"Actuation Cmd: Vx={velocity_vector[0]:.2f}, Vy={velocity_vector[1]:.2f}, Vz={velocity_vector[2]:.2f}")
        return tuple(velocity_vector)

    except Exception as e:
        logger.error(f"Actuation calculation failed: {e}")
        return (0.0, 0.0, 0.0)

# === 使用示例 ===
if __name__ == "__main__":
    # 场景 1: 机器人处于平静、自信的状态
    calm_state = EmotionalState(arousal=0.2, valence=0.8, confidence=0.9)
    
    # 场景 2: 机器人检测到潜在威胁，处于焦虑状态
    anxious_state = EmotionalState(arousal=0.9, valence=0.2, confidence=0.3)

    target_pos = (10.0, 5.0, 0.0)
    current_pos = (0.0, 0.0, 0.0)

    print("--- Test Case: Calm State ---")
    calm_params = map_emotion_to_control_params(calm_state)
    print(f"Params: {calm_params}")
    velocity = execute_emotional_actuation(target_pos, current_pos, calm_params)
    print(f"Resulting Velocity: {velocity}\n")

    print("--- Test Case: Anxious State ---")
    anxious_params = map_emotion_to_control_params(anxious_state)
    print(f"Params: {anxious_params}")
    velocity = execute_emotional_actuation(target_pos, current_pos, anxious_params)
    print(f"Resulting Velocity: {velocity}")