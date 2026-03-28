"""
Module: fuzzy_intent_resolver
Author: Senior Python Engineer (AGI System Core)
Description: 实现基于上下文感知的模糊意图到结构化参数的动态对齐算法。
             该模块通过结合领域约束与历史交互反馈（实践证伪），
             将“稍微大一点”等自然语言转化为精确的数值参数。
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型别名
Numeric = Union[int, float]
ParameterDict = Dict[str, Numeric]
HistoryLog = List[Dict[str, Union[str, Numeric]]]

@dataclass
class ContextConstraints:
    """
    定义特定上下文中参数的物理或逻辑约束。
    
    Attributes:
        min_val (Numeric): 参数最小值
        max_val (Numeric): 参数最大值
        default_val (Numeric): 默认值
        unit (str): 单位，如 'em', 'px', '%'
        step (Optional[Numeric]): 推荐的离散步长，如果为None则视为连续
    """
    min_val: Numeric
    max_val: Numeric
    default_val: Numeric
    unit: str = "unitless"
    step: Optional[Numeric] = None

    def __post_init__(self):
        if self.min_val >= self.max_val:
            raise ValueError("min_val must be less than max_val")
        if not (self.min_val <= self.default_val <= self.max_val):
            raise ValueError("default_val must be between min and max")


class FuzzyIntentEngine:
    """
    模糊意图解析引擎。
    
    负责管理不同技能上下文的约束，维护历史交互数据，
    并根据模糊副词生成精确的结构化参数。
    """

    def __init__(self):
        # 存储不同上下文的约束 { "context_name": ContextConstraints }
        self._constraints_db: Dict[str, ContextConstraints] = {}
        # 存储历史交互数据，用于动态校准
        self._interaction_history: Dict[str, HistoryLog] = {}
        
        # 预定义的模糊副词基准映射 (范围 0.0 - 1.0)
        # 0.0 代表无变化/最小，1.0 代表最大变化/最大
        self._linguistic_quantifiers = {
            "tiny": 0.1,
            "稍微": 0.2,
            "一点": 0.2,
            "一些": 0.3,
            "适中": 0.5,
            "moderate": 0.5,
            "large": 0.7,
            "强力": 0.85,
            "max": 1.0,
            "maximum": 1.0
        }
        logger.info("FuzzyIntentEngine initialized.")

    def register_context(self, context_name: str, constraints: ContextConstraints) -> None:
        """
        注册一个技能上下文及其参数约束。
        
        Args:
            context_name (str): 上下文唯一标识符 (e.g., 'font_sizer')
            constraints (ContextConstraints): 参数约束对象
        """
        if not isinstance(constraints, ContextConstraints):
            raise TypeError("Constraints must be an instance of ContextConstraints")
        
        self._constraints_db[context_name] = constraints
        self._interaction_history[context_name] = []
        logger.info(f"Context '{context_name}' registered with range [{constraints.min_val}, {constraints.max_val}]")

    def _calculate_base_delta(self, constraints: ContextConstraints, intensity: float) -> Numeric:
        """
        辅助函数：根据强度计算基础变化量。
        
        使用非线性映射使微小调整更细腻，大调整更显著。
        映射公式: delta = (max - min) * (intensity ^ 1.5) * direction_factor
        这里仅计算正向变化幅度。
        """
        range_span = constraints.max_val - constraints.min_val
        # 使用幂函数调整敏感度，使低强度输入变化更平滑
        adjusted_intensity = math.pow(intensity, 1.5)
        delta = range_span * adjusted_intensity * 0.5 # 0.5作为基础系数，防止单次调整过大
        return delta

    def resolve_intent(
        self, 
        context_name: str, 
        current_value: Numeric, 
        fuzzy_operator: str
    ) -> Dict[str, Union[Numeric, str]]:
        """
        核心函数：解析模糊意图并返回结构化参数。
        
        Args:
            context_name (str): 目标上下文
            current_value (Numeric): 当前参数值
            fuzzy_operator (str): 模糊副词 (e.g., "稍微", "强力")
            
        Returns:
            Dict: 包含 'new_value', 'delta', 'unit', 'status' 的字典
            
        Raises:
            ValueError: 如果上下文未注册
        """
        # 1. 验证与准备
        if context_name not in self._constraints_db:
            logger.error(f"Context '{context_name}' not found.")
            raise ValueError(f"Context '{context_name}' not registered.")
        
        constraints = self._constraints_db[context_name]
        operator_key = fuzzy_operator.lower()
        
        # 2. 获取语义强度
        intensity = self._linguistic_quantifiers.get(operator_key)
        if intensity is None:
            logger.warning(f"Unknown fuzzy operator '{fuzzy_operator}', defaulting to moderate (0.5).")
            intensity = 0.5
            
        # 3. 动态校准
        # 检查历史数据，根据用户习惯微调intensity (模拟"实践证伪"逻辑)
        # 这里简化为：如果历史操作频繁导致边界碰撞，则衰减强度
        history = self._interaction_history.get(context_name, [])
        collision_count = sum(1 for record in history if record.get("hit_boundary"))
        calibration_factor = max(0.5, 1.0 - (collision_count * 0.1)) # 碰撞越多，调整越保守
        
        calibrated_intensity = intensity * calibration_factor
        logger.debug(f"Calibrating intensity: {intensity} -> {calibrated_intensity} (Factor: {calibration_factor})")

        # 4. 计算数值
        # 假设意图总是正向增加 (Decrease needs separate handling or sign detection in NLP pre-step)
        # 为演示 '稍微大一点' -> 正向 Delta
        delta = self._calculate_base_delta(constraints, calibrated_intensity)
        new_value = current_value + delta
        
        # 5. 边界检查与修正
        hit_boundary = False
        if new_value > constraints.max_val:
            new_value = constraints.max_val
            hit_boundary = True
            logger.info(f"Value clamped to MAX {constraints.max_val} for context '{context_name}'")
        elif new_value < constraints.min_val:
            new_value = constraints.min_val
            hit_boundary = True
            logger.info(f"Value clamped to MIN {constraints.min_val} for context '{context_name}'")

        # 6. 记录交互历史
        record = {
            "operator": fuzzy_operator,
            "input_val": current_value,
            "output_val": new_value,
            "hit_boundary": hit_boundary
        }
        self._interaction_history[context_name].append(record)
        # 保持历史记录在合理大小
        if len(self._interaction_history[context_name]) > 100:
            self._interaction_history[context_name].pop(0)

        # 7. 构造返回结构
        result = {
            "new_value": round(new_value, 4),
            "delta": round(new_value - current_value, 4),
            "unit": constraints.unit,
            "status": "clamped" if hit_boundary else "success"
        }
        
        logger.info(f"Resolved '{fuzzy_operator}' in '{context_name}': {current_value} -> {new_value}")
        return result

# 模块级使用示例
if __name__ == "__main__":
    # 初始化引擎
    engine = FuzzyIntentEngine()
    
    # 定义场景：字体大小调节
    # 假设字体大小范围 12px - 72px
    font_constraints = ContextConstraints(
        min_val=12, 
        max_val=72, 
        default_val=16, 
        unit="px"
    )
    engine.register_context("font_resizer", font_constraints)
    
    # 模拟交互 1: "稍微大一点"
    print("--- Interaction 1: '稍微' ---")
    current_font = 16.0
    result_1 = engine.resolve_intent("font_resizer", current_font, "稍微")
    print(f"Input: {current_font}{font_constraints.unit}, Intent: '稍微'")
    print(f"Output: {result_1['new_value']}{result_1['unit']} (Delta: {result_1['delta']})")
    
    # 模拟交互 2: "强力大一点" (使用更大的强度)
    print("\n--- Interaction 2: '强力' ---")
    current_font = result_1['new_value']
    result_2 = engine.resolve_intent("font_resizer", current_font, "强力")
    print(f"Input: {current_font:.2f}, Intent: '强力'")
    print(f"Output: {result_2['new_value']}{result_2['unit']} (Delta: {result_2['delta']})")

    # 模拟交互 3: 边界测试
    print("\n--- Interaction 3: Boundary Test (Max) ---")
    current_font = 70.0
    result_3 = engine.resolve_intent("font_resizer", current_font, "强力")
    print(f"Input: {current_font:.2f}, Intent: '强力'")
    print(f"Output: {result_3['new_value']}{result_3['unit']} (Status: {result_3['status']})")