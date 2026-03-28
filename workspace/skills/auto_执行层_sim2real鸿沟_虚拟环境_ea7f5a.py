"""
Module: auto_执行层_sim2real鸿沟_虚拟环境_ea7f5a
Description: 【执行层：Sim2Real鸿沟】
             实现针对精密装配任务的域随机化策略，解决从虚拟仿真到实体机械臂迁移过程中的
             摩擦力不确定性与位置误差问题。目标是将位置误差控制在0.1mm以内。
Author: Senior Python Engineer (AGI System)
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RandomizationLevel(Enum):
    """域随机化强度的枚举类"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

@dataclass
class PhysicsProperties:
    """用于存储物理属性的配置数据类"""
    static_friction: float = 0.5
    dynamic_friction: float = 0.4
    restitution: float = 0.1
    mass: float = 1.0  # kg
    
    def __post_init__(self):
        """数据验证：确保物理属性在合理范围内"""
        if not (0.0 <= self.static_friction <= 2.0):
            raise ValueError(f"Invalid static friction: {self.static_friction}")
        if not (0.0 <= self.dynamic_friction <= 2.0):
            raise ValueError(f"Invalid dynamic friction: {self.dynamic_friction}")
        if not (0.0 <= self.restitution <= 1.0):
            raise ValueError(f"Invalid restitution: {self.restitution}")
        if self.mass <= 0:
            raise ValueError(f"Mass must be positive: {self.mass}")

@dataclass
class SimulationConfig:
    """仿真环境配置"""
    target_accuracy_mm: float = 0.1
    time_step: float = 0.001  # 仿真步长
    gravity: Tuple[float, float, float] = (0, 0, -9.81)
    
    def __post_init__(self):
        if self.target_accuracy_mm <= 0:
            raise ValueError("Target accuracy must be positive.")

class DomainRandomizer:
    """
    核心类：负责生成域随机化策略，弥合Sim2Real鸿沟。
    
    主要关注点：
    1. 摩擦力随机化：模拟现实世界中接触表面的不确定性。
    2. 动力学噪声注入：模拟机械臂关节控制的不稳定性。
    3. 视觉/传感器噪声（本模块侧重动力学）。
    """
    
    def __init__(self, config: SimulationConfig):
        self.config = config
        self._rng = np.random.default_rng()
        logger.info("DomainRandomizer initialized with target accuracy: {}mm".format(config.target_accuracy_mm))

    def _generate_noise_value(self, base: float, range_val: float, distribution: str = 'uniform') -> float:
        """
        辅助函数：生成基于基础值的随机噪声。
        
        Args:
            base (float): 基础物理值。
            range_val (float): 随机化范围 (+/-)。
            distribution (str): 分布类型 ('uniform' 或 'gaussian')。
            
        Returns:
            float: 添加噪声后的值。
        """
        if distribution == 'uniform':
            noise = self._rng.uniform(low=-range_val, high=range_val)
        elif distribution == 'gaussian':
            noise = self._rng.normal(loc=0.0, scale=range_val / 3.0) # 3-sigma covers the range
        else:
            raise ValueError(f"Unsupported distribution: {distribution}")
            
        return base + noise

    def randomize_physics_environment(
        self, 
        base_props: PhysicsProperties, 
        level: RandomizationLevel = RandomizationLevel.MEDIUM
    ) -> Dict[str, Any]:
        """
        核心函数 1: 针对精密装配环境的物理属性随机化。
        
        特别针对摩擦力不确定性进行建模，防止策略过拟合于特定的摩擦系数。
        
        Args:
            base_props (PhysicsProperties): 标准物理参数。
            level (RandomizationLevel): 随机化强度等级。
            
        Returns:
            Dict[str, Any]: 包含随机化后物理参数的字典，可直接传入仿真引擎。
        """
        logger.debug(f"Randomizing physics with level: {level.name}")
        
        # 根据等级定义随机化范围系数
        ranges = {
            RandomizationLevel.LOW: 0.05,
            RandomizationLevel.MEDIUM: 0.15,
            RandomizationLevel.HIGH: 0.30
        }
        factor = ranges.get(level, 0.15)
        
        try:
            # 重点：摩擦力随机化，模拟表面粗糙度、灰尘、油污等影响
            # 现实中摩擦力很难精确测量，且随时间变化
            rand_static_fric = self._generate_noise_value(
                base_props.static_friction, 
                base_props.static_friction * factor
            )
            rand_dynamic_fric = self._generate_noise_value(
                base_props.dynamic_friction, 
                base_props.dynamic_friction * factor
            )
            
            # 确保摩擦力非负
            rand_static_fric = max(0.01, rand_static_fric)
            rand_dynamic_fric = max(0.01, rand_dynamic_fric)
            
            randomized_props = {
                "static_friction": rand_static_fric,
                "dynamic_friction": rand_dynamic_fric,
                "restitution": self._generate_noise_value(base_props.restitution, 0.05),
                "mass": self._generate_noise_value(base_props.mass, base_props.mass * factor * 0.5)
            }
            
            logger.info(f"Applied Physics Randomization: Friction={rand_dynamic_fric:.4f}")
            return randomized_props
            
        except Exception as e:
            logger.error(f"Error during physics randomization: {e}")
            raise RuntimeError("Physics randomization failed.") from e

    def calculate_action_perturbation(
        self, 
        target_position: np.ndarray, 
        current_step: int, 
        max_steps: int
    ) -> Tuple[np.ndarray, float]:
        """
        核心函数 2: 计算动作空间的扰动（模拟控制误差）。
        
        在精密装配中，单纯的物理参数随机化不够，必须在动作层面引入扰动，
        模拟真实机械臂在接近目标（0.1mm精度）时的微小震动和控制偏差。
        
        Args:
            target_position (np.ndarray): 目标位置。
            current_step (int): 当前训练步数。
            max_steps (int): 总训练步数。
            
        Returns:
            Tuple[np.ndarray, float]: (扰动后的位置增量, 置信度)
        """
        if not isinstance(target_position, np.ndarray) or target_position.shape != (3,):
            raise ValueError("Target position must be a numpy array of shape (3,)")
            
        # 课程学习：随着训练进行，减少动作扰动幅度，让策略先学粗略再学精细
        progress = min(1.0, current_step / max_steps)
        noise_amplitude = 0.005 * (1.0 - progress)  # 最大5mm的初始扰动，逐渐衰减
        
        # 生成微小的高斯噪声
        noise = self._rng.normal(loc=0.0, scale=noise_amplitude, size=3)
        
        # 模拟机械臂在特定轴向上的刚度不同（例如Z轴重力方向通常刚度较高）
        stiffness_factor = np.array([1.0, 1.0, 0.8]) 
        perturbed_action = target_position + (noise * stiffness_factor)
        
        confidence = 1.0 - np.linalg.norm(noise) / 0.01 # 简单的置信度计算
        
        logger.debug(f"Action perturbation applied. Noise magnitude: {np.linalg.norm(noise):.6f}m")
        return perturbed_action, confidence

# Usage Example & Data Flow Demonstration
if __name__ == "__main__":
    # 1. 初始化配置
    sim_config = SimulationConfig(target_accuracy_mm=0.1)
    base_physics = PhysicsProperties(static_friction=0.6, dynamic_friction=0.5)
    
    # 2. 初始化域随机化器
    randomizer = DomainRandomizer(config=sim_config)
    
    print("-" * 30)
    print("Starting Sim2Real Domain Randomization Cycle...")
    
    # 3. 模拟训练循环中的随机化过程
    for step in range(3):
        print(f"\n--- Simulation Step {step+1} ---")
        
        # A. 随机化环境物理属性（特别是摩擦力）
        # 这会改变每一步仿真环境的底层物理引擎参数
        try:
            env_params = randomizer.randomize_physics_environment(
                base_physics, 
                level=RandomizationLevel.HIGH
            )
            print(f"Env Params: Static Friction={env_params['static_friction']:.3f}")
            
            # B. 计算带有扰动的动作（模拟控制噪声）
            target_pos = np.array([0.5, 0.1, 0.2])
            action, conf = randomizer.calculate_action_perturbation(target_pos, step, 3)
            error_magnitude = np.linalg.norm(action - target_pos)
            
            print(f"Action Perturbation: {action}")
            print(f"Position Error (m): {error_magnitude:.6f}")
            
            # 验证是否满足误差要求（在最终执行层会通过视觉伺服进一步修正）
            # 这里主要验证随机化是否在合理范围内产生扰动
            
        except Exception as e:
            logger.error(f"Simulation step failed: {e}")
            
    print("-" * 30)
    print("Domain Randomization Check Complete.")