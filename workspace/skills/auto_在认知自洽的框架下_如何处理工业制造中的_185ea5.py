"""
Module: cognitive_safety_resolver.py
Description: 在认知自洽的框架下，解决工业制造中效率与安全冲突的动态约束满足模型。
Author: Senior Python Engineer (AGI System Component)
Version: 1.0.0
"""

import logging
import typing
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveSafetyResolver")


class SafetyState(Enum):
    """定义系统的安全状态枚举"""
    SECURE = 0     # 安全区域，无人
    WARNING = 1    # 警戒区域，需降速
    CRITICAL = 2   # 危险区域，需急停


@dataclass
class EnvironmentalContext:
    """环境感知上下文数据结构"""
    human_distance: float  # 人员距离
    machine_wear_level: float  # 机器磨损度
    task_urgency: float  # 任务紧急度
    network_latency: float  # 网络延迟


@dataclass
class CognitiveState:
    """认知状态数据结构，存储各节点的动态权重"""
    efficiency_weight: float = 0.5
    safety_weight: float = 0.5
    current_speed_ratio: float = 0.0  # 0.0 到 1.0

    def __post_init__(self):
        self.validate()

    def validate(self):
        if not (0.0 <= self.efficiency_weight <= 1.0):
            raise ValueError("Efficiency weight must be between 0 and 1")
        if not (0.0 <= self.safety_weight <= 1.0):
            raise ValueError("Safety weight must be between 0 and 1")


class DynamicConstraintSatisfactionModel:
    """
    核心类：动态约束满足模型 (DCSP)
    
    实现基于认知博弈的权重调整。在边缘计算端实时平衡效率与安全。
    不使用简单的 if-else，而是通过多目标优化函数计算最优解。
    
    Use Case:
        >>> model = DynamicConstraintSatisfactionModel()
        >>> context = EnvironmentalContext(5.0, 0.2, 0.8, 0.01)
        >>> state = model.resolve_conflict(context)
        >>> print(f"Recommended Speed: {state.current_speed_ratio}")
    """

    def __init__(self, safety_threshold: float = 2.0, warning_threshold: float = 10.0):
        """
        初始化模型
        
        Args:
            safety_threshold (float): 安全距离阈值，低于此值触发CRITICAL
            warning_threshold (float): 警告距离阈值，低于此值触发WARNING
        """
        self.safety_threshold = safety_threshold
        self.warning_threshold = warning_threshold
        logger.info("DCSP Model initialized with thresholds: Safe<%s, Warn<%s", 
                    safety_threshold, warning_threshold)

    def _assess_risk_level(self, distance: float) -> SafetyState:
        """
        辅助函数：评估风险等级
        
        Args:
            distance (float): 探测到的人员距离
            
        Returns:
            SafetyState: 当前安全状态枚举值
        """
        try:
            if distance < 0:
                raise ValueError("Distance cannot be negative")
            
            if distance < self.safety_threshold:
                return SafetyState.CRITICAL
            elif distance < self.warning_threshold:
                return SafetyState.WARNING
            else:
                return SafetyState.SECURE
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            # Fail-safe: 默认返回最危险状态
            return SafetyState.CRITICAL

    def _calculate_dynamic_weights(self, context: EnvironmentalContext) -> typing.Tuple[float, float]:
        """
        核心函数 1: 计算动态权重
        
        基于环境上下文调整认知网络中“效率”与“安全”节点的权重。
        权重的总和归一化，但具体的博弈取决于上下文（如任务紧急度可能轻微抑制安全权重）。
        
        Args:
            context (EnvironmentalContext): 环境数据
            
        Returns:
            Tuple[float, float]: (efficiency_weight, safety_weight)
        """
        # 基础安全权重基于距离
        risk_state = self._assess_risk_level(context.human_distance)
        
        base_safety = 0.0
        if risk_state == SafetyState.CRITICAL:
            base_safety = 0.95
        elif risk_state == SafetyState.WARNING:
            # 距离越近，权重越高，使用反比函数
            ratio = (self.warning_threshold - context.human_distance) / (self.warning_threshold - self.safety_threshold)
            base_safety = 0.5 + (ratio * 0.4) # Range 0.5 - 0.9
        else:
            base_safety = 0.3 # 默认情况，安全仍需占一定比重

        # 任务紧急度对安全权重的侵蚀
        # 紧急度极高时，系统可能会承担微高风险（但在CRITICAL状态下不可覆盖）
        urgency_modifier = context.task_urgency * 0.1
        
        final_safety_weight = min(1.0, base_safety + (0.05 if context.machine_wear_level > 0.8 else 0.0))
        
        # 在非CRITICAL状态下，允许紧急度轻微调整权重
        if risk_state != SafetyState.CRITICAL:
            final_safety_weight = max(0.2, final_safety_weight - urgency_modifier)

        final_efficiency_weight = 1.0 - final_safety_weight
        
        logger.debug(f"Weights calculated: Safety={final_safety_weight:.2f}, Eff={final_efficiency_weight:.2f}")
        return final_efficiency_weight, final_safety_weight

    def resolve_conflict(self, context: EnvironmentalContext) -> CognitiveState:
        """
        核心函数 2: 解决冲突并输出认知状态
        
        综合计算结果，生成最终的控制指令（速度比率）。
        这是一个软约束过程：即使在安全权重很高时，速度也不一定是0，
        而是根据距离进行非线性衰减，除非达到硬约束边界。
        
        Args:
            context (EnvironmentalContext): 输入环境数据
            
        Returns:
            CognitiveState: 包含权重和最终行动建议的状态对象
        """
        if not isinstance(context, EnvironmentalContext):
            raise TypeError("Invalid context type provided.")

        try:
            # 1. 获取动态权重
            eff_w, safe_w = self._calculate_dynamic_weights(context)
            
            # 2. 计算最终行动
            # 这里的逻辑模拟神经网络的激活值计算
            # Speed = (Efficiency_Desire * eff_w) * (Safety_Allowance * safe_w)
            # 简化为：基础期望速度 * 安全衰减系数
            
            base_speed = 1.0 # 默认全速
            
            # 硬约束检查
            risk_state = self._assess_risk_level(context.human_distance)
            
            final_speed = 0.0
            
            if risk_state == SafetyState.CRITICAL:
                final_speed = 0.0 # 硬性停止
                logger.warning("CRITICAL Safety State engaged. Forcing STOP.")
            elif risk_state == SafetyState.WARNING:
                # 在Warning区域，速度与距离成正比，与安全权重成反比（安全权重高 -> 速度低）
                # 这是一个平滑的过渡，而不是突变
                distance_factor = context.human_distance / self.warning_threshold
                final_speed = base_speed * distance_factor * (eff_w / (eff_w + safe_w + 1e-6)) # Softmax-like
            else:
                # Secure区域，主要受限于机器磨损
                final_speed = base_speed * (1.0 - context.machine_wear_level * 0.5)
                
            # 边界检查
            final_speed = max(0.0, min(1.0, final_speed))
            
            state = CognitiveState(
                efficiency_weight=eff_w,
                safety_weight=safe_w,
                current_speed_ratio=final_speed
            )
            
            logger.info(f"Resolved Conflict: Speed={final_speed:.2f} (Eff: {eff_w:.2f}, Safe: {safe_w:.2f})")
            return state

        except ZeroDivisionError:
            logger.critical("Mathematical error in conflict resolution.")
            return CognitiveState(0.0, 1.0, 0.0) # Fail-safe
        except Exception as e:
            logger.critical(f"Unexpected error in resolution: {e}")
            return CognitiveState(0.0, 1.0, 0.0) # Fail-safe


# Main execution example for demonstration
if __name__ == "__main__":
    # 模拟场景：一辆工厂AGV小车
    model = DynamicConstraintSatisfactionModel(safety_threshold=1.0, warning_threshold=5.0)
    
    # 场景 1: 远距离，高紧急度
    ctx1 = EnvironmentalContext(human_distance=20.0, machine_wear_level=0.1, task_urgency=0.9, network_latency=0.01)
    result1 = model.resolve_conflict(ctx1)
    print(f"Scenario 1 Speed: {result1.current_speed_ratio}") # Expected: High speed
    
    # 场景 2: 中距离，进入警告区
    ctx2 = EnvironmentalContext(human_distance=3.0, machine_wear_level=0.1, task_urgency=0.9, network_latency=0.01)
    result2 = model.resolve_conflict(ctx2)
    print(f"Scenario 2 Speed: {result2.current_speed_ratio}") # Expected: Reduced speed
    
    # 场景 3: 极近距离，触发硬约束
    ctx3 = EnvironmentalContext(human_distance=0.5, machine_wear_level=0.1, task_urgency=1.0, network_latency=0.01)
    result3 = model.resolve_conflict(ctx3)
    print(f"Scenario 3 Speed: {result3.current_speed_ratio}") # Expected: 0.0