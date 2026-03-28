"""
Module: auto_动态计划修正机_在执行长期复杂任务时_5b4d2e
Description: 【动态计划修正机】在执行长期复杂任务时，系统能够实时监测‘现实数据’与‘顶层目标’的偏离度。
             一旦发现底层实践证伪了顶层假设，系统不是报错停止，而是自动生成‘修正方案’或‘降级目标’。
             它模拟了人类项目经理在突发状况下的应变能力，实现了计划与执行的动态平衡。
Author: AGI System
Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DynamicPlanCorrector")


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    DEVIATED = "deviated"      # 偏离
    COMPROMISED = "compromised" # 降级
    COMPLETED = "completed"
    FAILED = "failed"


class CorrectionType(Enum):
    """修正类型枚举"""
    RESOURCE_REALLOCATION = "resource_reallocation"  # 资源重新分配
    STRATEGY_PIVOT = "strategy_pivot"                # 策略转向
    GOAL_DEGRADATION = "goal_degradation"            # 目标降级
    EMERGENCY_STOP = "emergency_stop"                # 紧急停止


@dataclass
class Goal:
    """目标数据结构"""
    goal_id: str
    description: str
    target_value: float
    priority: int  # 1-10, 10为最高
    deadline: float  # Unix timestamp or relative time
    is_mandatory: bool = True  # 核心目标不可妥协


@dataclass
class RealityData:
    """现实状态数据结构"""
    current_progress: float  # 0.0 to 1.0
    resource_consumption: float
    error_count: int
    unexpected_events: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class CorrectionPlan:
    """修正方案数据结构"""
    correction_type: CorrectionType
    new_target: Optional[float]
    actions: List[str]
    reasoning: str
    confidence_score: float  # 0.0 to 1.0


class DynamicPlanCorrector:
    """
    动态计划修正机核心类。
    
    负责监测现实与计划的偏离，并生成动态修正方案。
    模拟人类项目经理在突发状况下的决策能力。
    """

    def __init__(self, deviation_threshold: float = 0.15, critical_threshold: float = 0.40):
        """
        初始化修正机。
        
        Args:
            deviation_threshold (float): 触发修正的偏离阈值，默认0.15 (15%)
            critical_threshold (float): 触发目标降级的临界阈值，默认0.40 (40%)
        """
        if not (0 < deviation_threshold < critical_threshold < 1):
            raise ValueError("阈值必须满足: 0 < deviation < critical < 1")
            
        self.deviation_threshold = deviation_threshold
        self.critical_threshold = critical_threshold
        self._correction_history: List[Dict] = []
        logger.info("DynamicPlanCorrector initialized with thresholds: dev=%.2f, crit=%.2f", 
                    deviation_threshold, critical_threshold)

    def _calculate_deviation(self, target: float, reality: RealityData) -> float:
        """
        辅助函数：计算当前现实与目标的偏离度。
        
        Args:
            target (float): 目标值
            reality (RealityData): 当前现实数据
            
        Returns:
            float: 偏离度 (0.0 to 1.0)
        """
        if target == 0:
            return 0.0 if reality.current_progress == 0 else 1.0
        
        # 简单的线性偏离计算，实际场景可能需要更复杂的归一化逻辑
        deviation = abs(target - reality.current_progress) / target
        
        # 考虑错误率和意外事件的惩罚因子
        penalty = 0.05 * reality.error_count + 0.10 * len(reality.unexpected_events)
        
        total_deviation = min(1.0, deviation + penalty)
        logger.debug(f"Calculated deviation: {total_deviation:.3f} (Base: {deviation}, Penalty: {penalty})")
        return total_deviation

    def monitor_and_correct(self, goal: Goal, reality: RealityData) -> Tuple[TaskStatus, Optional[CorrectionPlan]]:
        """
        核心函数1：监测现实与目标的偏离并生成修正方案。
        
        Args:
            goal (Goal): 顶层目标对象
            reality (RealityData): 当前现实状态数据
            
        Returns:
            Tuple[TaskStatus, Optional[CorrectionPlan]]: 返回当前任务状态和建议的修正方案。
                                                        如果状态正常，修正方案为None。
        
        Raises:
            ValueError: 如果输入数据无效
        """
        # 数据验证
        if not 0.0 <= reality.current_progress <= 1.0:
            raise ValueError("Progress must be between 0.0 and 1.0")
        if not isinstance(goal, Goal):
            raise TypeError("Invalid goal type")

        deviation = self._calculate_deviation(goal.target_value, reality)
        
        # 状态判断逻辑
        if deviation < self.deviation_threshold:
            logger.info(f"Goal {goal.goal_id} is on track. Deviation: {deviation:.2%}")
            return TaskStatus.RUNNING, None
        
        elif deviation >= self.critical_threshold:
            logger.warning(f"Goal {goal.goal_id} CRITICAL deviation: {deviation:.2%}. Initiating protocol.")
            status, plan = self._generate_contingency_plan(goal, reality, deviation)
            self._log_correction(goal, reality, plan)
            return status, plan
            
        else:
            logger.warning(f"Goal {goal.goal_id} minor deviation detected: {deviation:.2%}. Correcting.")
            plan = self._generate_adjustment_plan(goal, reality, deviation)
            self._log_correction(goal, reality, plan)
            return TaskStatus.DEVIATED, plan

    def _generate_adjustment_plan(self, goal: Goal, reality: RealityData, deviation: float) -> CorrectionPlan:
        """
        内部函数：生成微调方案（资源重分配或策略微调）。
        """
        actions = []
        reasoning = f"Deviation {deviation:.2f} exceeds threshold but is manageable. "
        
        # 简单的启发式规则
        if reality.resource_consumption < 0.5:
            actions.append("Inject additional resources to accelerate progress.")
            reasoning += "Resource injection selected."
        else:
            actions.append("Optimize current workflow to remove bottlenecks.")
            reasoning += "Process optimization selected."
            
        return CorrectionPlan(
            correction_type=CorrectionType.RESOURCE_REALLOCATION,
            new_target=goal.target_value, # 保持目标不变
            actions=actions,
            reasoning=reasoning,
            confidence_score=0.85
        )

    def _generate_contingency_plan(self, goal: Goal, reality: RealityData, deviation: float) -> Tuple[TaskStatus, CorrectionPlan]:
        """
        核心函数2：生成紧急应变方案（目标降级或战略转向）。
        """
        reasoning = f"Critical deviation {deviation:.2f}. "
        
        # 如果目标不是强制的，或者错误过多，尝试降级
        if not goal.is_mandatory or reality.error_count > 5:
            degraded_target = goal.target_value * (1 - deviation / 2) # 尝试保住部分成果
            reasoning += "Goal is not mandatory or errors are high. Degrading target to salvage results."
            
            return TaskStatus.COMPROMISED, CorrectionPlan(
                correction_type=CorrectionType.GOAL_DEGRADATION,
                new_target=degraded_target,
                actions=[
                    "Notify stakeholders of scope change.",
                    f"Reset target to {degraded_target:.2f}.",
                    "Lock current progress to prevent rollback."
                ],
                reasoning=reasoning,
                confidence_score=0.65
            )
        else:
            # 如果是强制目标，只能尝试激进转向
            reasoning += "Goal is mandatory. Attempting radical strategy pivot."
            return TaskStatus.DEVIATED, CorrectionPlan(
                correction_type=CorrectionType.STRATEGY_PIVOT,
                new_target=goal.target_value,
                actions=[
                    "Pause current execution path.",
                    "Switch to fallback algorithm/methodology.",
                    "Alert human supervisor for intervention."
                ],
                reasoning=reasoning,
                confidence_score=0.40 # 低信心，需要人工介入
            )

    def _log_correction(self, goal: Goal, reality: RealityData, plan: CorrectionPlan):
        """辅助函数：记录修正历史以便复盘"""
        entry = {
            "goal_id": goal.goal_id,
            "reality_progress": reality.current_progress,
            "correction_type": plan.correction_type.value,
            "actions_taken": plan.actions
        }
        self._correction_history.append(entry)
        logger.info(f"Correction logged: {entry}")

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化修正机
    corrector = DynamicPlanCorrector(deviation_threshold=0.15, critical_threshold=0.40)
    
    # 定义顶层目标
    project_goal = Goal(
        goal_id="G001",
        description="Deploy AGI Module Alpha",
        target_value=1.0, # 100% 完成
        priority=10,
        is_mandatory=False # 允许降级
    )

    # 模拟场景 1: 轻微偏离
    print("\n--- Scenario 1: Minor Deviation ---")
    current_status_minor = RealityData(
        current_progress=0.80, # 预期0.9，实际0.8
        resource_consumption=0.4,
        error_count=1,
        unexpected_events=[]
    )
    status, plan = corrector.monitor_and_correct(project_goal, current_status_minor)
    if plan:
        print(f"Status: {status.value}")
        print(f"Plan Actions: {plan.actions}")

    # 模拟场景 2: 严重偏离，触发降级
    print("\n--- Scenario 2: Critical Deviation ---")
    project_goal_mandatory = Goal(
        goal_id="G002",
        description="Maintain Life Support",
        target_value=1.0,
        priority=10,
        is_mandatory=True # 核心目标，不可降级
    )
    
    current_status_critical = RealityData(
        current_progress=0.20, # 严重滞后
        resource_consumption=0.9,
        error_count=10,
        unexpected_events=["System Overheat", "Network Partition"]
    )
    
    status_crit, plan_crit = corrector.monitor_and_correct(project_goal_mandatory, current_status_critical)
    if plan_crit:
        print(f"Status: {status_crit.value}")
        print(f"Plan Type: {plan_crit.correction_type.value}")
        print(f"Reasoning: {plan_crit.reasoning}")