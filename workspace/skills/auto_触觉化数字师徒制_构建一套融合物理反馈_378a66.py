"""
高阶模块：触觉化数字师徒制系统

该模块实现了一套融合物理反馈的强化学习人类反馈（RLHF）系统。它不仅基于代码运行逻辑的成功或失败，
更引入了“操作阻力”、“材料形变”等物理传感器数据作为核心Reward信号。系统旨在通过模拟工匠的“手感”
（力反馈数据），训练AI智能体在虚拟环境中重现对材料的微观调整能力，实现从“逻辑正确”到“物理完美”的跨越。

核心组件：
- PhysicalSensorEmulator: 模拟生成物理环境数据（用于演示，实际部署替换为真实驱动）。
- HapticRewardModel: 融合物理参数的奖励模型。
- MasteryApprenticeLearner: 核心学习引擎，整合RLHF逻辑。

Created by: AGI System
Version: 1.0.0
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MaterialState(Enum):
    """材料状态枚举，用于定义不同的物理特性基准"""
    ELASTIC = "elastic"
    PLASTIC = "plastic"
    FRACTURED = "fractured"
    IDEAL = "ideal"


@dataclass
class PhysicalFeedback:
    """
    物理反馈数据结构。
    
    Attributes:
        timestamp (float): 时间戳。
        force_vector (np.ndarray): 三维力向量。
        torque_vector (np.ndarray): 三维扭矩向量。
        material_deformation (float): 材料形变系数 (0.0-1.0)。
        vibration_frequency (float): 振动频率，用于模拟表面粗糙度反馈。
    """
    timestamp: float
    force_vector: np.ndarray
    torque_vector: np.ndarray
    material_deformation: float
    vibration_frequency: float = 0.0

    def __post_init__(self):
        """数据验证"""
        if not (0.0 <= self.material_deformation <= 1.0):
            raise ValueError("材料形变系数必须在0.0到1.0之间")


@dataclass
class ActionTrajectory:
    """
    智能体的动作轨迹数据。
    
    Attributes:
        target_position (List[float]): 目标位置坐标。
        velocity (float): 执行速度。
        code_logic_score (float): 代码逻辑评分 (0.0-1.0)。
    """
    target_position: List[float]
    velocity: float
    code_logic_score: float = 1.0


class HapticRewardModel:
    """
    触觉奖励模型。
    
    根据物理反馈与理想工匠模型的偏差计算Reward。不仅仅看任务是否完成，
    更看重完成过程中的'力道'、'顺滑度'和'材料保护程度'。
    """
    
    def __init__(self, ideal_force_profile: Dict[str, float]):
        """
        初始化奖励模型。
        
        Args:
            ideal_force_profile: 包含理想物理参数的字典，如 'max_force', 'ideal_deformation'.
        """
        self.ideal_max_force = ideal_force_profile.get('max_force', 10.0)
        self.ideal_deformation = ideal_force_profile.get('ideal_deformation', 0.05)
        logger.info("HapticRewardModel 初始化完成，理想力阈值: %.2f", self.ideal_max_force)

    def compute_haptic_score(self, feedback: PhysicalFeedback) -> float:
        """
        辅助函数：计算单一的触觉评分。
        
        基于高斯分布计算当前力反馈与理想值的接近程度。
        
        Args:
            feedback (PhysicalFeedback): 传感器反馈数据。
            
        Returns:
            float: 触觉评分 (0.0 - 1.0)。
        """
        current_force_magnitude = np.linalg.norm(feedback.force_vector)
        
        # 阻力评分：越接近理想力道得分越高，过大或过小都会扣分
        force_diff = abs(current_force_magnitude - self.ideal_max_force)
        force_score = np.exp(- (force_diff ** 2) / (2 * (self.ideal_max_force * 0.1) ** 2))
        
        # 形变评分：形变越小越好（假设是非破坏性操作），或者越接近理想形变
        deform_diff = abs(feedback.material_deformation - self.ideal_deformation)
        deform_score = 1.0 - min(deform_diff / 0.5, 1.0) # 简单线性惩罚
        
        # 综合权重
        haptic_score = 0.7 * force_score + 0.3 * deform_score
        
        logger.debug(f"计算触觉评分: 力={current_force_magnitude:.2f}, 力分={force_score:.2f}, 形变分={deform_score:.2f}")
        return np.clip(haptic_score, 0.0, 1.0)


class MasteryApprenticeLearner:
    """
    核心类：数字师徒制学习系统。
    
    整合代码逻辑评分与物理反馈评分，生成最终的强化学习Reward。
    """
    
    def __init__(self, reward_model: HapticRewardModel, physics_weight: float = 0.6):
        """
        初始化学习器。
        
        Args:
            reward_model (HapticRewardModel): 触觉奖励模型实例。
            physics_weight (float): 物理反馈在总奖励中的权重 (0.0-1.0)。
                                    默认0.6表示"手感"比"代码逻辑"更重要。
        """
        if not 0.0 <= physics_weight <= 1.0:
            raise ValueError("physics_weight 必须在 0 和 1 之间")
            
        self.reward_model = reward_model
        self.physics_weight = physics_weight
        self.logic_weight = 1.0 - physics_weight
        self.episode_memory: List[Dict[str, Any]] = []
        
    def process_step(
        self, 
        action: ActionTrajectory, 
        sensor_data: PhysicalFeedback
    ) -> Tuple[float, Dict[str, float]]:
        """
        核心函数：处理单步交互并生成综合奖励。
        
        Args:
            action (ActionTrajectory): 智能体执行的动作。
            sensor_data (PhysicalFeedback): 环境返回的物理传感器数据。
            
        Returns:
            Tuple[float, Dict[str, float]]: 
                - final_reward: 综合奖励值。
                - details: 奖励分解详情。
        
        Raises:
            ValueError: 如果输入数据包含NaN或无效值。
        """
        # 1. 数据验证
        if np.isnan(sensor_data.force_vector).any():
            logger.error("检测到无效的力传感器数据 (NaN)")
            raise ValueError("Invalid sensor data: force vector contains NaN")
            
        # 2. 计算逻辑奖励（传统RL）
        logic_reward = action.code_logic_score
        if logic_reward < 0.5:
            logger.warning("代码逻辑评分不及格，物理反馈权重降低")
            # 如果逻辑错误（如撞墙），物理反馈毫无意义，直接给予重罚
            return -10.0, {"logic_penalty": -10.0}

        # 3. 计算物理/触觉奖励
        haptic_score = self.reward_model.compute_haptic_score(sensor_data)
        
        # 4. 融合奖励
        # 只有当逻辑基本正确时，才考虑物理层面的优化
        final_reward = (self.logic_weight * logic_reward * 10) + \
                       (self.physics_weight * haptic_score * 10 * logic_reward)
        
        # 记录日志
        details = {
            "logic_component": logic_reward,
            "haptic_component": haptic_score,
            "final_reward": final_reward
        }
        self.episode_memory.append(details)
        
        logger.info(f"Step处理完成 - Logic: {logic_reward:.2f}, Haptic: {haptic_score:.2f}, Total: {final_reward:.2f}")
        
        return final_reward, details

    def simulate_craftsman_micro_adjustment(self, current_error: float) -> np.ndarray:
        """
        核心函数：模拟工匠的微观调整能力。
        
        基于当前的误差，生成一个模拟工匠手部微调的力向量。
        这是一个PD控制器的变体，但引入了非线性阻尼来模拟生物肌肉特性。
        
        Args:
            current_error (float): 当前位置与目标位置的误差幅度。
            
        Returns:
            np.ndarray: 建议的微调力向量 (3D)。
        """
        # 模拟生物肌肉的非线性响应
        # 小误差时高灵敏度，大误差时平滑阻尼
        if abs(current_error) < 0.01:
            # 微观领域：引入高频微调（模仿工匠的震颤调整）
            adjustment = np.random.normal(0, 0.001, 3)
            logger.debug("进入微观调整模式：模仿工匠手感震颤")
        else:
            # 宏观领域：线性比例控制
            gain = 0.5
            damping = 0.1 * np.sign(current_error) * (current_error ** 0.5)
            adjustment = np.array([gain * current_error - damping, 0, 0]) # 假设X轴为主轴
            
        return adjustment


# ================= 使用示例 =================
if __name__ == "__main__":
    # 1. 初始化配置
    IDEAL_PARAMS = {'max_force': 15.0, 'ideal_deformation': 0.02}
    reward_model = HapticRewardModel(ideal_force_profile=IDEAL_PARAMS)
    learner = MasteryApprenticeLearner(reward_model, physics_weight=0.7)
    
    print("\n--- 开始模拟数字师徒制训练循环 ---")
    
    # 2. 模拟一个交互步骤
    # 假设智能体尝试移动到某处，代码逻辑是通的
    action = ActionTrajectory(target_position=[1.0, 0.0, 0.0], velocity=0.5, code_logic_score=1.0)
    
    # 模拟传感器传回数据：力稍微大了一点，形变正常
    sensor_feedback = PhysicalFeedback(
        timestamp=0.01,
        force_vector=np.array([16.5, 0.2, 0.1]), # 励磁略大
        torque_vector=np.array([0.0, 0.0, 0.0]),
        material_deformation=0.025
    )
    
    # 3. 计算奖励
    reward, breakdown = learner.process_step(action, sensor_feedback)
    print(f"Final Reward: {reward}")
    
    # 4. 模拟工匠微观调整
    error = 0.005 # 假设只有极小的误差
    micro_adjust = learner.simulate_craftsman_micro_adjustment(error)
    print(f"Recommended Micro-adjustment Force: {micro_adjust}")