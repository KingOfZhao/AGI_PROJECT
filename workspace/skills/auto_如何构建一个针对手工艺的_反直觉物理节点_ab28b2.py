"""
高级Python模块：构建针对手工艺的“反直觉物理节点”强化学习环境

该模块实现了一个定制的强化学习（RL）框架，旨在发现手工艺操作中
反直觉的高效物理策略（例如：抡大锤时的末端放松效应）。

核心逻辑：
通过引入稀疏奖励、能量效率惩罚以及针对极值行为的特殊奖励塑形，
引导智能体在数亿次试错中跳出常规力学的局部最优解。

Author: AGI System Core Engineer
Version: 1.0.0
"""

import logging
import numpy as np
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('counter_intuitive_physics.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class PhysicsState:
    """
    物理状态数据类，用于验证输入数据格式。
    
    Attributes:
        position (np.ndarray): 末端执行器的位置
        velocity (np.ndarray): 末端执行器的速度
        force_applied (np.ndarray): 当前施加的力
        time_step (int): 当前时间步
    """
    position: np.ndarray
    velocity: np.ndarray
    force_applied: np.ndarray
    time_step: int

    def __post_init__(self):
        """数据验证和边界检查"""
        if not isinstance(self.position, np.ndarray) or self.position.shape != (3,):
            raise ValueError("Position must be a numpy array of shape (3,)")
        if not isinstance(self.velocity, np.ndarray) or self.velocity.shape != (3,):
            raise ValueError("Velocity must be a numpy array of shape (3,)")
        if not isinstance(self.force_applied, np.ndarray) or self.force_applied.shape != (3,):
            raise ValueError("Force must be a numpy array of shape (3,)")
        if self.time_step < 0:
            raise ValueError("Time step cannot be negative")


class CounterIntuitiveCraftEnv:
    """
    一个模拟手工艺操作的强化学习环境。
    
    目标是最大化冲击力（如砸钉子），同时最小化能量消耗。
    智能体必须学会在特定时刻（如撞击前瞬间）改变施力策略（如放松）。
    
    Attributes:
        max_steps (int): 每个episode的最大步数
        target_impact_velocity (float): 目标冲击速度
        state (Optional[PhysicsState]): 当前物理状态
    """

    def __init__(self, max_steps: int = 200, target_impact_velocity: float = 10.0):
        """
        初始化环境。
        
        Args:
            max_steps (int): Episode最大长度。
            target_impact_velocity (float): 产生高额奖励所需的最小速度。
        """
        self.max_steps = max_steps
        self.target_impact_velocity = target_impact_velocity
        self.state: Optional[PhysicsState] = None
        self._step_count = 0
        logger.info("CounterIntuitiveCraftEnv initialized with target velocity: %.2f", target_impact_velocity)

    def _calculate_base_physics(self, force: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        [辅助函数] 模拟基础物理引擎。
        
        简化的运动学模型：F = ma，更新速度和位置。
        包含阻尼和重力影响。
        
        Args:
            force (np.ndarray): 智能体施加的力
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: 更新后的位置和速度
        """
        if self.state is None:
            raise RuntimeError("Environment state is not initialized. Call reset() first.")

        mass = 1.0  # 假设单位质量
        gravity = np.array([0, 0, -9.8])
        damping = 0.1
        
        # 计算加速度 (F + m*g - damping*v) / m
        acceleration = force + gravity - damping * self.state.velocity
        new_velocity = self.state.velocity + acceleration * 0.01  # dt = 0.01
        new_position = self.state.position + new_velocity * 0.01
        
        # 边界检查：防止穿透地面
        if new_position[2] < 0:
            new_position[2] = 0
            # 模拟撞击：如果速度向下且很大，触发撞击事件
            if new_velocity[2] < -self.target_impact_velocity:
                logger.debug("Impact detected with velocity: %.2f", abs(new_velocity[2]))
        
        return new_position, new_velocity

    def reset(self) -> np.ndarray:
        """
        重置环境状态到初始条件。
        
        Returns:
            np.ndarray: 初始观察向量
        """
        initial_pos = np.array([0.0, 0.0, 1.0])
        initial_vel = np.array([0.0, 0.0, 0.0])
        initial_force = np.array([0.0, 0.0, 0.0])
        
        self.state = PhysicsState(
            position=initial_pos,
            velocity=initial_vel,
            force_applied=initial_force,
            time_step=0
        )
        self._step_count = 0
        logger.info("Environment reset.")
        return self._get_observation()

    def _get_observation(self) -> np.ndarray:
        """将内部状态展平为观察向量"""
        if self.state is None:
            return np.zeros(9)
        return np.concatenate([
            self.state.position, 
            self.state.velocity, 
            self.state.force_applied
        ])

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        核心函数：执行一步动作，更新物理状态并计算奖励。
        
        Args:
            action (np.ndarray): 智能体输出的力向量，范围通常在 [-1, 1] 或具体物理单位。
            
        Returns:
            Tuple[np.ndarray, float, bool, Dict]:
            - observation (np.ndarray): 新的观察
            - reward (float): 奖励值
            - done (bool): 是否结束
            - info (Dict): 调试信息
            
        Raises:
            ValueError: 如果动作维度不正确
        """
        if self.state is None:
            raise RuntimeError("Call reset() before step()")
        
        if not isinstance(action, np.ndarray) or action.shape != (3,):
            logger.error("Invalid action shape: %s", action.shape)
            raise ValueError("Action must be a numpy array of shape (3,)")
            
        # 1. 动作缩放与噪声（增加探索难度）
        scaled_action = action * 10.0  # 力的缩放因子
        
        # 2. 更新物理状态
        next_pos, next_vel = self._calculate_base_physics(scaled_action)
        
        self.state.position = next_pos
        self.state.velocity = next_vel
        self.state.force_applied = scaled_action
        self.state.time_step += 1
        self._step_count += 1
        
        # 3. 计算奖励 (核心逻辑)
        reward = self._compute_counter_intuitive_reward(scaled_action)
        
        # 4. 终止条件
        done = self._step_count >= self.max_steps or self.state.position[2] <= 0
        
        info = {
            "impact_velocity": abs(next_vel[2]) if self.state.position[2] <= 0 else 0,
            "energy_used": np.linalg.norm(scaled_action)
        }
        
        return self._get_observation(), reward, done, info

    def _compute_counter_intuitive_reward(self, current_force: np.ndarray) -> float:
        """
        核心函数：设计用于发现反直觉策略的奖励函数。
        
        传统的直觉是：持续用力会导致最大速度。
        反直觉策略是：在撞击前瞬间减少力（放松）以利用惯性或结构共振。
        
        奖励结构:
        1. Impact Reward: 只有当物体撞击地面（z<=0）时且速度极高时给予巨额奖励。
        2. Energy Penalty: 持续惩罚力的使用（力 x 步数），迫使AI寻找省力方式。
        3. Relaxation Bonus: 如果在高速状态下力的模量突然减小，给予额外奖励。
        
        Args:
            current_force (np.ndarray): 当前施加的力
            
        Returns:
            float: 计算出的奖励值
        """
        reward = 0.0
        
        # 基础生存惩罚
        reward -= 0.01  # 时间惩罚
        
        # 能量效率惩罚 (鼓励不要一直盲目用力)
        force_magnitude = np.linalg.norm(current_force)
        energy_penalty = -0.001 * force_magnitude
        reward += energy_penalty
        
        # 检测撞击事件
        if self.state.position[2] <= 0:
            impact_speed = abs(self.state.velocity[2])
            
            # 只有超过阈值速度才有奖励，否则惩罚（撞得太轻）
            if impact_speed > self.target_impact_velocity:
                # 针对极值点的非线性奖励
                # 速度越快，奖励呈指数级增长
                speed_bonus = (impact_speed - self.target_impact_velocity) ** 2
                
                # 反直觉奖励检测：
                # 如果在撞击瞬间，施加的力很小（即"放松"），给予额外加成
                # 这模拟了"鞭打效应"或"共振"的收益
                relaxation_factor = 1.0
                if force_magnitude < 1.0:  # 阈值设得很低
                    relaxation_factor = 2.5
                    logger.debug("Counter-intuitive relaxation detected! Force: %.2f", force_magnitude)
                
                reward += speed_bonus * relaxation_factor
            else:
                reward -= 10.0  # 撞击力度不足的惩罚
                
        return reward


# 使用示例
if __name__ == "__main__":
    # 1. 实例化环境
    env = CounterIntuitiveCraftEnv(max_steps=50, target_impact_velocity=8.0)
    obs = env.reset()
    
    print(f"Initial Observation: {obs}")
    
    # 2. 模拟一个简单的随机策略 (在实际RL中会被PPO/SAC替代)
    total_reward = 0
    done = False
    
    # 模拟一个"直觉"策略：一直向下按
    intuitive_action = np.array([0, 0, -1.0]) # 持续向下施力
    
    # 模拟一个"反直觉"策略：先加速后放松 (此处仅作演示，实际需配合时间步)
    # 注意：这里只是随机演示step函数的调用，不代表训练过程
    
    try:
        while not done:
            # 随机动作模拟探索
            action = np.random.uniform(-1, 1, 3)
            
            # 调用核心步进函数
            obs, reward, done, info = env.step(action)
            total_reward += reward
            
            # 简单的日志输出
            if done:
                logger.info(f"Episode finished. Impact Velocity: {info['impact_velocity']:.2f}")
                logger.info(f"Total Reward: {total_reward:.2f}")
                
    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
    except Exception as e:
        logger.error(f"Unexpected error during simulation: {e}")