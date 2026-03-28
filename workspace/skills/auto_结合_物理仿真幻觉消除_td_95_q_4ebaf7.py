"""
模块名称: auto_结合_物理仿真幻觉消除_td_95_q_4ebaf7
描述: 结合物理仿真、力觉信号映射与混合验证体系，实现意图可行性验证的思维-行动闭环系统。
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Optional
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型枚举"""
    GRASP = "grasp"
    PUSH = "push"
    ROTATE = "rotate"
    MOVE = "move"


@dataclass
class Intent:
    """意图数据结构"""
    type: IntentType
    target_position: np.ndarray
    force_vector: np.ndarray
    friction_coefficient: float = 0.5
    mass: float = 1.0

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.target_position, np.ndarray) or self.target_position.shape != (3,):
            raise ValueError("目标位置必须是形状为(3,)的numpy数组")
        if not isinstance(self.force_vector, np.ndarray) or self.force_vector.shape != (3,):
            raise ValueError("力向量必须是形状为(3,)的numpy数组")
        if self.friction_coefficient < 0 or self.friction_coefficient > 1:
            raise ValueError("摩擦系数必须在0到1之间")
        if self.mass <= 0:
            raise ValueError("质量必须大于0")


@dataclass
class PhysicsState:
    """物理状态数据结构"""
    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray
    force_feedback: np.ndarray

    def __post_init__(self):
        """数据验证"""
        for field in [self.position, self.velocity, self.acceleration, self.force_feedback]:
            if not isinstance(field, np.ndarray) or field.shape != (3,):
                raise ValueError("所有向量必须是形状为(3,)的numpy数组")


class PhysicsSimulator:
    """物理仿真沙箱"""

    def __init__(self, gravity: float = 9.81, time_step: float = 0.01):
        """
        初始化物理仿真器
        
        参数:
            gravity: 重力加速度(m/s²)
            time_step: 仿真时间步长(s)
        """
        self.gravity = gravity
        self.time_step = time_step
        self._validate_parameters()

    def _validate_parameters(self):
        """验证仿真参数"""
        if self.gravity < 0:
            raise ValueError("重力加速度不能为负")
        if self.time_step <= 0 or self.time_step > 0.1:
            raise ValueError("时间步长必须在0到0.1秒之间")

    def simulate_interaction(
        self,
        intent: Intent,
        initial_state: PhysicsState,
        steps: int = 100
    ) -> Tuple[PhysicsState, Dict[str, float]]:
        """
        模拟意图执行过程
        
        参数:
            intent: 意图对象
            initial_state: 初始物理状态
            steps: 仿真步数
            
        返回:
            Tuple[最终状态, 仿真统计]
        """
        if steps <= 0 or steps > 1000:
            raise ValueError("仿真步数必须在1到1000之间")

        current_state = initial_state
        stats = {
            "collision_count": 0,
            "max_force": 0.0,
            "total_work": 0.0
        }

        for _ in range(steps):
            # 计算作用力
            net_force = self._calculate_net_force(intent, current_state)
            
            # 更新物理状态
            new_state = self._update_physics(current_state, net_force)
            
            # 检测碰撞
            if self._check_collision(new_state.position):
                stats["collision_count"] += 1
                new_state = self._handle_collision(new_state)
            
            # 更新统计
            force_magnitude = np.linalg.norm(new_state.force_feedback)
            if force_magnitude > stats["max_force"]:
                stats["max_force"] = force_magnitude
            
            stats["total_work"] += np.dot(new_state.force_feedback, new_state.velocity) * self.time_step
            current_state = new_state

        logger.info(f"仿真完成: 碰撞次数={stats['collision_count']}, 最大力={stats['max_force']:.2f}N")
        return current_state, stats

    def _calculate_net_force(self, intent: Intent, state: PhysicsState) -> np.ndarray:
        """计算净作用力"""
        # 重力
        gravity_force = np.array([0, 0, -self.gravity * intent.mass])
        
        # 摩擦力
        if np.linalg.norm(state.velocity) > 0.01:
            friction = -intent.friction_coefficient * intent.mass * self.gravity * \
                      (state.velocity / np.linalg.norm(state.velocity))
        else:
            friction = np.zeros(3)
        
        # 意图施加的力
        applied_force = intent.force_vector
        
        return gravity_force + friction + applied_force

    def _update_physics(self, state: PhysicsState, net_force: np.ndarray) -> PhysicsState:
        """更新物理状态"""
        acceleration = net_force / state.mass
        new_velocity = state.velocity + acceleration * self.time_step
        new_position = state.position + new_velocity * self.time_step
        
        # 计算力反馈
        force_feedback = -net_force  # 根据牛顿第三定律
        
        return PhysicsState(
            position=new_position,
            velocity=new_velocity,
            acceleration=acceleration,
            force_feedback=force_feedback
        )

    def _check_collision(self, position: np.ndarray) -> bool:
        """简单的碰撞检测"""
        # 假设地面在z=0平面
        return position[2] < 0

    def _handle_collision(self, state: PhysicsState) -> PhysicsState:
        """处理碰撞"""
        new_position = state.position.copy()
        new_position[2] = 0  # 修正位置
        
        # 反弹效应
        new_velocity = state.velocity.copy()
        if new_velocity[2] < 0:
            new_velocity[2] *= -0.5  # 能量损失
        
        return PhysicsState(
            position=new_position,
            velocity=new_velocity,
            acceleration=state.acceleration,
            force_feedback=state.force_feedback * 0.8  # 碰撞力衰减
        )


class IntentValidator:
    """意图验证系统"""

    def __init__(self, physics_sim: PhysicsSimulator):
        """
        初始化验证器
        
        参数:
            physics_sim: 物理仿真器实例
        """
        self.physics_sim = physics_sim

    def validate_intent(
        self,
        intent: Intent,
        initial_state: PhysicsState,
        force_threshold: float = 100.0,
        position_tolerance: float = 0.1
    ) -> Tuple[bool, Dict[str, float]]:
        """
        验证意图的可行性
        
        参数:
            intent: 意图对象
            initial_state: 初始物理状态
            force_threshold: 最大允许力(N)
            position_tolerance: 位置容差(m)
            
        返回:
            Tuple[是否可行, 验证结果]
        """
        if force_threshold <= 0:
            raise ValueError("力阈值必须大于0")
        if position_tolerance <= 0:
            raise ValueError("位置容差必须大于0")

        # 运行物理仿真
        final_state, stats = self.physics_sim.simulate_interaction(intent, initial_state)
        
        # 混合验证
        position_error = np.linalg.norm(final_state.position - intent.target_position)
        force_valid = stats["max_force"] <= force_threshold
        position_valid = position_error <= position_tolerance
        collision_valid = stats["collision_count"] < 10  # 允许少量碰撞
        
        is_feasible = force_valid and position_valid and collision_valid
        
        result = {
            "position_error": position_error,
            "max_force": stats["max_force"],
            "collision_count": stats["collision_count"],
            "force_valid": force_valid,
            "position_valid": position_valid,
            "collision_valid": collision_valid,
            "total_work": stats["total_work"]
        }
        
        logger.info(f"意图验证完成: 可行={is_feasible}, 位置误差={position_error:.3f}m")
        return is_feasible, result


def create_sample_intent() -> Intent:
    """创建示例意图"""
    return Intent(
        type=IntentType.MOVE,
        target_position=np.array([1.0, 2.0, 0.5]),
        force_vector=np.array([5.0, 10.0, 20.0]),
        friction_coefficient=0.3,
        mass=2.0
    )


def create_initial_state() -> PhysicsState:
    """创建初始物理状态"""
    return PhysicsState(
        position=np.array([0.0, 0.0, 1.0]),
        velocity=np.array([0.1, 0.1, 0.0]),
        acceleration=np.zeros(3),
        force_feedback=np.zeros(3)
    )


if __name__ == "__main__":
    # 使用示例
    try:
        # 初始化系统
        simulator = PhysicsSimulator(gravity=9.81, time_step=0.01)
        validator = IntentValidator(simulator)
        
        # 创建测试意图和初始状态
        test_intent = create_sample_intent()
        initial_state = create_initial_state()
        
        # 验证意图
        is_feasible, result = validator.validate_intent(
            test_intent,
            initial_state,
            force_threshold=50.0,
            position_tolerance=0.2
        )
        
        print(f"\n意图验证结果: {'可行' if is_feasible else '不可行'}")
        print(f"详细信息: {result}")
        
    except Exception as e:
        logger.error(f"系统运行错误: {str(e)}", exc_info=True)