"""
模块: intent_driven_nullspace_motion
描述: 实现意图驱动的零空间运动生成。
      机器人在执行确定性任务（如焊接）时，利用其冗余自由度（身体姿态、朝向）进行'解释性表达'。
      AI分析任务上下文（全局意图），动态调整非关键运动轨迹，使其动作展现出类似人类工匠的'韵律感'或'审慎感'。
      例如，在易碎品旁自动放慢速度（不仅是物理需要，更是传递'小心'的信号），实现机器人的非语言沟通能力。

作者: AGI System
版本: 1.0.0
日期: 2023-10-27
"""

import logging
import numpy as np
from enum import Enum
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

class IntentType(Enum):
    """任务意图类型枚举"""
    PRECISION = "precision"      # 精密操作，如芯片焊接
    DELICATE = "delicate"        # 小心操作，如处理易碎品
    AGGRESSIVE = "aggressive"    # 快速操作，如粗加工
    RHYTHMIC = "rhythmic"        # 韵律操作，如喷涂或艺术性动作
    NEUTRAL = "neutral"          # 普通移动

@dataclass
class ContextData:
    """环境上下文数据"""
    fragile_nearby: bool = False
    human_proximity: float = 0.0  # 0.0 to 1.0
    task_complexity: float = 0.5  # 0.0 to 1.0
    current_force_feedback: float = 0.0

@dataclass
class RobotState:
    """机器人状态快照"""
    joint_positions: np.ndarray
    joint_velocities: np.ndarray
    end_effector_pose: np.ndarray  # [x, y, z, rx, ry, rw]

@dataclass
class MotionProfile:
    """生成的运动配置文件"""
    primary_task_trajectory: np.ndarray
    null_space_modifiers: Dict[str, float]
    expressive_velocity_scale: float
    suggested_body_orientation: np.ndarray
    intent_hash: str

# --- 核心类 ---

class IntentAnalyzer:
    """
    分析全局任务上下文，确定当前的机器人运动意图。
    这部分属于'大脑'，决定如何通过动作表达情感或状态。
    """
    
    def analyze_context(self, context: ContextData) -> IntentType:
        """
        根据环境数据判断意图类型
        
        Args:
            context (ContextData): 当前环境上下文
            
        Returns:
            IntentType: 识别出的意图类型
        """
        if context.fragile_nearby:
            logger.info("Intent detected: DELICATE (Fragile object detected)")
            return IntentType.DELICATE
        
        if context.human_proximity > 0.8:
            logger.info("Intent detected: PRECISION (Human collaboration)")
            return IntentType.PRECISION
        
        if context.task_complexity > 0.8:
            logger.info("Intent detected: RHYTHMIC (Complex artistic task)")
            return IntentType.RHYTHMIC
            
        return IntentType.NEUTRAL

class NullSpaceMotionGenerator:
    """
    基于意图生成零空间运动指令。
    零空间允许机器人在保持末端执行器（手）任务不变的情况下，
    移动其身体（肘部、躯干）以表达意图。
    """
    
    def __init__(self, dof: int = 7):
        """
        初始化生成器
        
        Args:
            dof (int): 机器人自由度数量
        """
        self.dof = dof
        self._validate_dof(dof)

    def _validate_dof(self, dof: int):
        if not isinstance(dof, int) or dof < 3:
            raise ValueError("DOF must be an integer greater than 2 for redundancy.")

    def _calculate_jacobian_pseudo_inverse(self, state: RobotState) -> np.ndarray:
        """
        计算雅可比矩阵的伪逆（辅助函数）。
        在实际工程中，这需要正运动学模型。此处使用随机矩阵模拟结构。
        """
        # 模拟雅可比矩阵 (6 x DOF)
        J = np.random.rand(6, self.dof)
        # 计算阻尼最小二乘伪逆
        lambda_damping = 0.01
        JJT = np.dot(J, J.T) + lambda_damping * np.eye(6)
        J_pinv = np.dot(J.T, np.linalg.inv(JJT))
        return J_pinv

    def _calculate_null_space_projection(self, J_pinv: np.ndarray) -> np.ndarray:
        """
        计算零空间投影矩阵: I - J# * J
        """
        I = np.eye(self.dof)
        J = np.dot(J_pinv, np.random.rand(self.dof, 6)) # 模拟恢复J用于计算
        # 修正：伪逆计算通常涉及原矩阵，此处简化逻辑为投影算子标准公式
        # 实际应使用: Null = I - pinv(J) @ J
        # 这里为了代码可运行且不依赖复杂的物理引擎，使用简化逻辑
        projection = I - np.dot(J_pinv, np.random.rand(6, self.dof)) 
        return projection

    def generate_expressive_motion(
        self, 
        intent: IntentType, 
        current_state: RobotState,
        primary_task_target: np.ndarray
    ) -> MotionProfile:
        """
        核心函数：生成包含表达力的运动规划。
        
        Args:
            intent (IntentType): 当前意图
            current_state (RobotState): 当前机器人状态
            primary_task_target (np.ndarray): 主要任务目标位置
            
        Returns:
            MotionProfile: 包含修正后的运动参数
            
        Raises:
            ValueError: 如果输入数据维度不匹配
        """
        if primary_task_target.shape[0] != 6:
             raise ValueError("Primary task target must be a 6D vector (pose).")

        logger.info(f"Generating motion for intent: {intent.value}")
        
        # 1. 基础运动 (主任务)
        # 假设主任务是简单的直线插值
        primary_trajectory = np.linspace(
            current_state.end_effector_pose, 
            primary_task_target, 
            num=10
        )
        
        # 2. 零空间参数 (副任务/表达力)
        null_space_modifiers = {}
        velocity_scale = 1.0
        body_orientation_bias = np.zeros(3) # roll, pitch, yaw bias
        
        if intent == IntentType.DELICATE:
            # 意图：小心
            # 动作：减速，身体姿态后倾（增加物理距离感）
            velocity_scale = 0.3
            body_orientation_bias = np.array([0, -0.1, 0]) # Pitch back slightly
            null_space_modifiers["elbow_stiffness"] = 0.9 # 变得僵硬/谨慎
            
        elif intent == IntentType.PRECISION:
            # 意图：专注
            # 动作：稳定躯干，略微前倾
            velocity_scale = 0.7
            body_orientation_bias = np.array([0, 0.05, 0]) 
            null_space_modifiers["damping"] = 1.2
            
        elif intent == IntentType.AGGRESSIVE:
            # 意图：高效/强力
            # 动作：大幅度摆动，全速
            velocity_scale = 1.2
            body_orientation_bias = np.array([0.1, 0, 0])
            null_space_modifiers["elbow_stiffness"] = 0.4

        elif intent == IntentType.RHYTHMIC:
            # 意图：艺术感
            # 动作：加入正弦波调制
            # 此处简化为参数传递，实际会在轨迹生成中加入 sin(t)
            null_space_modifiers["oscillation_amplitude"] = 0.05
            velocity_scale = 1.0

        # 3. 计算零空间投影矩阵 (模拟)
        J_pinv = self._calculate_jacobian_pseudo_inverse(current_state)
        null_projection = self._calculate_null_space_projection(J_pinv)
        
        # 模拟将意图向量映射到关节速度的零空间分量
        # q_dot_null = Null * (q_dot_posture - q_dot_current)
        # 这里我们只返回参数，由底层控制器执行
        intent_hash = f"{intent.value}_{hash(tuple(body_orientation_bias))}"

        return MotionProfile(
            primary_task_trajectory=primary_trajectory,
            null_space_modifiers=null_space_modifiers,
            expressive_velocity_scale=velocity_scale,
            suggested_body_orientation=body_orientation_bias,
            intent_hash=intent_hash
        )

# --- 辅助功能 ---

def validate_robot_state(state: RobotState) -> bool:
    """
    辅助函数：验证机器人状态数据的完整性和合理性。
    
    Args:
        state (RobotState): 待验证的状态对象
        
    Returns:
        bool: 数据是否有效
        
    Raises:
        TypeError: 如果类型不匹配
    """
    if not isinstance(state, RobotState):
        logger.error("Invalid state type provided.")
        raise TypeError("Input must be a RobotState instance")
        
    if np.any(np.isnan(state.joint_positions)):
        logger.warning("Joint positions contain NaN values.")
        return False
        
    if np.any(np.abs(state.joint_velocities) > 10.0): # 假设速度限制
        logger.warning("Joint velocities exceed safety limits.")
        return False
        
    return True

# --- 主逻辑与演示 ---

def run_demo():
    """
    使用示例：展示如何结合上下文生成意图驱动的运动。
    """
    print("--- 启动意图驱动零空间运动生成演示 ---")
    
    # 1. 初始化系统
    analyzer = IntentAnalyzer()
    generator = NullSpaceMotionGenerator(dof=7) # 假设7轴机械臂
    
    # 2. 模拟输入数据
    # 场景：机械臂正在工作，传感器检测到附近有易碎品
    current_context = ContextData(
        fragile_nearby=True,
        human_proximity=0.2,
        task_complexity=0.4
    )
    
    # 模拟当前机器人状态
    current_state = RobotState(
        joint_positions=np.array([0, 0.5, 0, 1.2, 0, 0.8, 0]),
        joint_velocities=np.zeros(7),
        end_effector_pose=np.array([0.5, 0.1, 0.4, 0, 0, 1.0]) # x,y,z, rx,ry,rz
    )
    
    # 目标位置 (主任务)
    target_pose = np.array([0.6, 0.1, 0.3, 0, 0, 1.0])
    
    # 3. 验证数据
    if not validate_robot_state(current_state):
        print("Robot state invalid, aborting.")
        return

    # 4. 分析意图
    detected_intent = analyzer.analyze_context(current_context)
    
    # 5. 生成运动
    try:
        motion_profile = generator.generate_expressive_motion(
            intent=detected_intent,
            current_state=current_state,
            primary_task_target=target_pose
        )
        
        # 6. 输出结果
        print(f"\n生成的运动配置 ID: {motion_profile.intent_hash}")
        print(f"意图类型: {detected_intent.value}")
        print(f"表达性速度缩放: {motion_profile.expressive_velocity_scale}")
        print(f"建议身体姿态偏移: {motion_profile.suggested_body_orientation}")
        print(f"零空间参数: {motion_profile.null_space_modifiers}")
        print("轨迹点预览 (前3个):")
        print(motion_profile.primary_task_trajectory[:3])
        
        print("\n解释: 机器人将在执行主任务的同时，降低速度并调整姿态，以传达'小心'的意图。")
        
    except ValueError as e:
        logger.error(f"Motion generation failed: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    run_demo()