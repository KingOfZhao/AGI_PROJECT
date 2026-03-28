"""
高级技能模块：生成式感知-行动契约

该模块实现了AGI系统中的“流动性智能”核心组件。它摒弃了传统的静态指令模式，
转而采用基于实时反馈的动态控制循环。技能不再是一系列固定的坐标点，
而是一个持续运行的“感知-行动”契约，确保系统在面对动态环境时能够自适应调整。

版权所有 (C) 2023 AGI Systems Inc.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Tuple, Optional, Dict, Any
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GenerativeSkill")

class SkillState(Enum):
    """技能状态的枚举类"""
    IDLE = auto()
    RUNNING = auto()
    CONVERGED = auto()
    FAILED = auto()
    ADAPTIVE_EVOLUTION = auto()

@dataclass
class PerceptionData:
    """
    感知数据结构
    包含了从传感器获取的原始数据及其预处理后的状态。
    """
    timestamp: float
    force_feedback: Tuple[float, float, float]  # (x, y, z) 力反馈
    object_position: Tuple[float, float, float] # (x, y, z) 物体位置
    object_velocity: Tuple[float, float, float] # (x, y, z) 物体速度
    
    def is_valid(self) -> bool:
        """验证数据有效性"""
        return all(isinstance(v, (int, float)) for v in self.object_position)

@dataclass
class ActionCommand:
    """
    行动指令结构
    生成的行动指令，包含末端执行器的目标状态。
    """
    target_position: Tuple[float, float, float]
    target_force: Optional[Tuple[float, float, float]] = None
    gripper_state: float = 1.0  # 0.0 (闭合) 到 1.0 (打开)
    metadata: Dict[str, Any] = field(default_factory=dict)

class GenerativeSkill:
    """
    生成式感知-行动技能基类。
    
    该类定义了一个持续运行的循环，通过感知数据实时生成动作。
    如果环境发生变化（如物体移动），内部状态机会自动演化行为策略。
    
    Attributes:
        skill_name (str): 技能名称。
        target_force_range (Tuple[float, float]): 期望维持的力范围。
        tolerance (float): 允许的误差阈值。
        max_iterations (int): 最大迭代次数，防止死循环。
    """
    
    def __init__(
        self, 
        skill_name: str, 
        target_force_range: Tuple[float, float],
        tolerance: float = 0.5,
        max_iterations: int = 1000
    ):
        self.skill_name = skill_name
        self.target_force_range = target_force_range
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self._state = SkillState.IDLE
        self._current_iteration = 0
        
        logger.info(f"Initializing skill: {self.skill_name} with target force {target_force_range}")

    def _validate_perception(self, perception: PerceptionData) -> bool:
        """
        辅助函数：验证感知数据的完整性和边界。
        
        Args:
            perception (PerceptionData): 输入的感知数据。
            
        Returns:
            bool: 数据是否通过验证。
        """
        if not perception.is_valid():
            logger.error("Invalid perception data detected: NaN or wrong type.")
            return False
        
        # 边界检查：假设工作空间限制在 +/- 1000mm
        if any(abs(v) > 1000.0 for v in perception.object_position):
            logger.warning("Perception data out of workspace bounds.")
            return False
            
        return True

    def _calculate_adaptive_action(
        self, 
        perception: PerceptionData
    ) -> ActionCommand:
        """
        核心函数：基于当前感知计算下一步行动。
        
        这是一个简单的阻抗控制示例逻辑：
        1. 检查当前接触力。
        2. 如果力小于目标下限，向物体移动（追踪/抓取）。
        3. 如果力大于目标上限，稍微后退（释放压力）。
        4. 如果在范围内，保持位置（维持）。
        
        Args:
            perception (PerceptionData): 当前时刻的感知数据。
            
        Returns:
            ActionCommand: 生成的指令。
        """
        current_pos = perception.object_position
        current_vel = perception.object_velocity
        current_force = perception.force_feedback
        
        # 计算合力的大小（简化处理，只考虑Z轴或模长）
        force_magnitude = sum(f**2 for f in current_force)**0.5
        min_force, max_force = self.target_force_range
        
        target_pos = current_pos # 默认跟踪物体位置
        
        # 流动性智能：根据力反馈动态调整位置偏移
        if force_magnitude < min_force:
            # 接触不足，继续前进（追踪/压紧）
            adjustment = 0.01  # 向前推进 10mm
            self._state = SkillState.ADAPTIVE_EVOLUTION
            logger.debug(f"Force {force_magnitude:.2f} < {min_force}, moving closer.")
        elif force_magnitude > max_force:
            # 接触过紧，后退（释放）
            adjustment = -0.01 # 后退 10mm
            self._state = SkillState.ADAPTIVE_EVOLUTION
            logger.debug(f"Force {force_magnitude:.2f} > {max_force}, pulling back.")
        else:
            # 维持接触
            adjustment = 0.0
            if self._state == SkillState.ADAPTIVE_EVOLUTION:
                 self._state = SkillState.CONVERGED
                 logger.info("Skill converged to target force range.")
        
        # 简单的预测：如果物体在移动，预测下一时刻位置
        predicted_pos = (
            current_pos[0] + current_vel[0] * 0.1,
            current_pos[1] + current_vel[1] * 0.1,
            current_pos[2] + current_vel[2] * 0.1 + adjustment
        )
        
        return ActionCommand(
            target_position=predicted_pos,
            gripper_state=0.5, # 0.5 代表柔性抓取模式
            metadata={"logic": "impedance_control"}
        )

    def execute_cycle(
        self, 
        get_perception: Callable[[], PerceptionData],
        execute_action: Callable[[ActionCommand], None]
    ) -> SkillState:
        """
        核心函数：执行一次完整的感知-行动循环。
        
        这个函数通常由更高层的调度器在循环中调用，或者由本类的 run() 方法阻塞调用。
        它实现了契约的核心逻辑：感知 -> 验证 -> 规划 -> 执行 -> 状态更新。
        
        Args:
            get_perception (Callable): 获取感知数据的回调函数。
            execute_action (Callable): 执行动作的回调函数。
            
        Returns:
            SkillState: 当前技能的运行状态。
        """
        if self._state == SkillState.IDLE:
            self._state = SkillState.RUNNING
            
        try:
            # 1. 感知
            perception = get_perception()
            
            # 2. 数据验证
            if not self._validate_perception(perception):
                raise ValueError("Perception validation failed.")
                
            # 3. 生成行动 (Generative Core)
            action = self._calculate_adaptive_action(perception)
            
            # 4. 执行行动
            execute_action(action)
            
            self._current_iteration += 1
            
            if self._current_iteration > self.max_iterations:
                logger.warning("Max iterations reached.")
                self._state = SkillState.FAILED
                
        except Exception as e:
            logger.error(f"Error in execution cycle: {str(e)}", exc_info=True)
            self._state = SkillState.FAILED
            
        return self._state

    def run(
        self, 
        get_perception: Callable[[], PerceptionData],
        execute_action: Callable[[ActionCommand], None],
        interval: float = 0.01
    ) -> bool:
        """
        阻塞式运行技能，直到收敛或失败。
        
        Args:
            get_perception (Callable): 感知回调。
            execute_action (Callable): 行动回调。
            interval (float): 循环频率（秒）。
            
        Returns:
            bool: 技能是否成功收敛。
        """
        logger.info(f"Starting skill loop for: {self.skill_name}")
        while self._state not in [SkillState.CONVERGED, SkillState.FAILED]:
            self.execute_cycle(get_perception, execute_action)
            time.sleep(interval)
            
        return self._state == SkillState.CONVERGED

# --- 模拟环境与使用示例 ---

class MockRobotEnv:
    """
    模拟的机器人环境，用于演示技能的运行。
    """
    def __init__(self):
        self.obj_pos = [0.5, 0.0, 0.2]
        self.obj_vel = [0.0, 0.0, 0.0] # 物体突然开始移动
        self.contact_force = 0.0
        self.step_count = 0

    def get_sensor_data(self) -> PerceptionData:
        """模拟传感器读取"""
        # 模拟物体在第50步突然开始向上移动
        if self.step_count > 50:
            self.obj_vel = [0.0, 0.0, 0.05] 
            self.obj_pos[2] += self.obj_vel[2]
            
        # 模拟力反馈：如果机器人位置接近物体位置
        # 这里简化逻辑：假设机器人总是能追上Z轴
        # 如果物体移动快，力变小；如果追上了，力变大
        
        return PerceptionData(
            timestamp=time.time(),
            force_feedback=(0, 0, self.contact_force),
            object_position=tuple(self.obj_pos),
            object_velocity=tuple(self.obj_vel)
        )

    def apply_action(self, action: ActionCommand):
        """模拟执行动作"""
        # 模拟物理引擎的一步
        # 机器人试图移动到 action.target_position
        # 简单的力计算逻辑
        dist_z = action.target_position[2] - self.obj_pos[2]
        
        # 简化的接触力模型
        if dist_z > 0: # 机器人超过物体表面
            self.contact_force = dist_z * 100.0 # 弹性系数
        else:
            self.contact_force = 0.0
            
        logger.info(
            f"Step {self.step_count}: Obj Z={self.obj_pos[2]:.3f}, "
            f"Force={self.contact_force:.1f}, Status={skill._state.name}"
        )
        self.step_count += 1

if __name__ == "__main__":
    # 实例化模拟环境
    env = MockRobotEnv()
    
    # 定义技能：维持接触力在 10N 到 20N 之间
    # 这是一个“触摸/跟随”契约，而不是单纯的“到达坐标”
    skill = GenerativeSkill(
        skill_name="Dynamic_Contact_Tracing",
        target_force_range=(10.0, 20.0),
        max_iterations=200
    )
    
    # 运行技能
    success = skill.run(
        get_perception=env.get_sensor_data,
        execute_action=env.apply_action,
        interval=0.05
    )
    
    if success:
        print("\nSkill execution completed successfully (Converged).")
    else:
        print("\nSkill execution failed.")