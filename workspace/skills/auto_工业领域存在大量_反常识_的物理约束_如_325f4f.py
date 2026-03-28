"""
工业物理约束层模块

本模块实现了一个物理约束验证系统，用于在工业自动化规划过程中自动检测和过滤违反基本物理定律的方案。
主要解决LLM在工业规划中常见的物理幻觉问题（如忽略重力、材料强度等约束）。

核心功能：
1. 物理约束规则定义
2. 规划方案验证
3. 物理可行性分析
"""

import math
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PhysicsConstraintLayer")

# 物理常量定义
GRAVITY = 9.81  # m/s²
STANDARD_MATERIALS = {
    'steel': {'density': 7850, 'yield_strength': 250e6},  # kg/m³, Pa
    'aluminum': {'density': 2700, 'yield_strength': 275e6},
    'concrete': {'density': 2400, 'yield_strength': 30e6}
}

class ConstraintType(Enum):
    """物理约束类型枚举"""
    GRAVITY = "gravity"
    MATERIAL_STRENGTH = "material_strength"
    THERMAL = "thermal"
    FLUID_DYNAMICS = "fluid_dynamics"

@dataclass
class PhysicsConstraint:
    """物理约束数据结构"""
    name: str
    constraint_type: ConstraintType
    description: str
    validation_func: callable
    priority: int = 1  # 1-5, 5为最高优先级

@dataclass
class ValidationResult:
    """验证结果数据结构"""
    is_valid: bool
    violated_constraints: List[str]
    confidence_score: float  # 0-1
    message: str
    suggestions: List[str]

class PhysicsConstraintLayer:
    """
    工业物理约束层实现类
    
    属性:
        constraints (List[PhysicsConstraint]): 已注册的物理约束列表
        materials_db (Dict): 材料属性数据库
        tolerance (float): 计算容差阈值
    
    示例:
        >>> pcl = PhysicsConstraintLayer()
        >>> pcl.register_standard_constraints()
        >>> plan = {"structure": "floating_platform", "material": "aluminum", "load": 1000}
        >>> result = pcl.validate_plan(plan)
    """
    
    def __init__(self, tolerance: float = 1e-6):
        """
        初始化物理约束层
        
        参数:
            tolerance: 物理计算容差阈值
        """
        self.constraints: List[PhysicsConstraint] = []
        self.materials_db: Dict = STANDARD_MATERIALS.copy()
        self.tolerance = tolerance
        logger.info("PhysicsConstraintLayer initialized with tolerance %s", tolerance)
    
    def register_constraint(self, constraint: PhysicsConstraint) -> None:
        """
        注册新的物理约束
        
        参数:
            constraint: 要添加的物理约束对象
            
        异常:
            ValueError: 如果约束无效或已存在
        """
        if not isinstance(constraint, PhysicsConstraint):
            raise ValueError("Invalid constraint type")
            
        if any(c.name == constraint.name for c in self.constraints):
            raise ValueError(f"Constraint '{constraint.name}' already exists")
            
        self.constraints.append(constraint)
        self.constraints.sort(key=lambda x: x.priority, reverse=True)
        logger.debug("Registered constraint: %s (priority %d)", constraint.name, constraint.priority)
    
    def register_standard_constraints(self) -> None:
        """注册标准工业物理约束集"""
        # 重力约束
        self.register_constraint(
            PhysicsConstraint(
                name="gravity_support",
                constraint_type=ConstraintType.GRAVITY,
                description="所有结构必须有足够的支撑对抗重力",
                validation_func=self._validate_gravity_support,
                priority=5
            )
        )
        
        # 材料强度约束
        self.register_constraint(
            PhysicsConstraint(
                name="material_strength",
                constraint_type=ConstraintType.MATERIAL_STRENGTH,
                description="结构应力不得超过材料屈服强度",
                validation_func=self._validate_material_strength,
                priority=5
            )
        )
        
        logger.info("Standard constraints registered")
    
    def validate_plan(self, plan: Dict) -> ValidationResult:
        """
        验证工业规划方案是否符合物理约束
        
        参数:
            plan: 包含规划参数的字典，必须包含以下字段:
                - structure: 结构类型
                - material: 使用的材料
                - load: 预期负载(N)
                - dimensions: 尺寸(m)
                
        返回:
            ValidationResult: 包含验证结果和建议
            
        异常:
            ValueError: 如果输入数据无效或缺失
        """
        try:
            # 输入验证
            self._validate_input_plan(plan)
            
            violated = []
            messages = []
            suggestions = []
            total_score = 1.0
            
            for constraint in self.constraints:
                is_valid, msg, suggestion = constraint.validation_func(plan)
                if not is_valid:
                    violated.append(constraint.name)
                    messages.append(f"{constraint.description}: {msg}")
                    if suggestion:
                        suggestions.append(suggestion)
                    # 根据约束优先级调整置信度
                    total_score -= 0.2 * constraint.priority / 5
            
            confidence = max(0.0, min(1.0, total_score))
            is_valid = len(violated) == 0
            
            result = ValidationResult(
                is_valid=is_valid,
                violated_constraints=violated,
                confidence_score=confidence,
                message="; ".join(messages) if messages else "All constraints satisfied",
                suggestions=suggestions
            )
            
            logger.info("Plan validation completed. Valid: %s, Confidence: %.2f", is_valid, confidence)
            return result
            
        except Exception as e:
            logger.error("Validation failed: %s", str(e))
            raise
    
    def _validate_input_plan(self, plan: Dict) -> None:
        """验证输入规划数据的有效性"""
        required_fields = ['structure', 'material', 'load', 'dimensions']
        for field in required_fields:
            if field not in plan:
                raise ValueError(f"Missing required field: {field}")
                
        if plan['material'] not in self.materials_db:
            raise ValueError(f"Unknown material: {plan['material']}")
            
        if plan['load'] <= 0:
            raise ValueError("Load must be positive")
            
        if not isinstance(plan['dimensions'], (tuple, list)) or len(plan['dimensions']) != 3:
            raise ValueError("Dimensions must be a 3-element sequence (x,y,z)")
    
    def _validate_gravity_support(self, plan: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        验证重力支撑约束
        
        参数:
            plan: 规划方案字典
            
        返回:
            Tuple[验证结果, 消息, 建议]
        """
        # 检查是否有悬浮结构
        if "floating" in plan['structure'].lower() and "support" not in plan:
            msg = "Floating structure without support mechanism"
            suggestion = "Add support structure or use magnetic levitation with power backup"
            return False, msg, suggestion
        
        # 计算重量和支撑力
        material = self.materials_db[plan['material']]
        volume = math.prod(plan['dimensions'])
        weight = volume * material['density'] * GRAVITY
        
        # 检查支撑力是否足够
        support_force = plan.get('support_force', 0)
        if support_force < weight * 1.5:  # 1.5倍安全系数
            msg = f"Insufficient support force ({support_force}N) for weight ({weight:.2f}N)"
            suggestion = f"Increase support force to at least {weight * 1.5:.2f}N"
            return False, msg, suggestion
        
        return True, "Gravity support adequate", None
    
    def _validate_material_strength(self, plan: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        验证材料强度约束
        
        参数:
            plan: 规划方案字典
            
        返回:
            Tuple[验证结果, 消息, 建议]
        """
        material = self.materials_db[plan['material']]
        cross_section = plan['dimensions'][0] * plan['dimensions'][1]
        
        # 计算应力
        stress = plan['load'] / cross_section
        
        # 考虑安全系数
        safety_factor = 1.5
        allowable_stress = material['yield_strength'] / safety_factor
        
        if stress > allowable_stress:
            msg = (f"Stress ({stress/1e6:.2f} MPa) exceeds allowable "
                   f"({allowable_stress/1e6:.2f} MPa) for {plan['material']}")
            suggestion = (
                f"Increase cross-section area or use stronger material "
                f"(current yield strength: {material['yield_strength']/1e6:.2f} MPa)"
            )
            return False, msg, suggestion
        
        return True, "Material strength adequate", None
    
    def add_custom_material(self, name: str, properties: Dict) -> None:
        """
        添加自定义材料到数据库
        
        参数:
            name: 材料名称
            properties: 材料属性字典，必须包含'density'和'yield_strength'
            
        异常:
            ValueError: 如果属性无效
        """
        if 'density' not in properties or 'yield_strength' not in properties:
            raise ValueError("Material properties must include 'density' and 'yield_strength'")
            
        if properties['density'] <= 0 or properties['yield_strength'] <= 0:
            raise ValueError("Material properties must be positive values")
            
        self.materials_db[name] = properties
        logger.info("Added custom material: %s", name)

# 使用示例
if __name__ == "__main__":
    # 初始化物理约束层
    pcl = PhysicsConstraintLayer()
    pcl.register_standard_constraints()
    
    # 添加自定义材料
    pcl.add_custom_material(
        "carbon_fiber",
        {"density": 1600, "yield_strength": 600e6}
    )
    
    # 测试用例1: 有效方案
    valid_plan = {
        "structure": "supported_platform",
        "material": "steel",
        "load": 5000,  # N
        "dimensions": (1.0, 1.0, 0.1),  # m
        "support_force": 12000  # N
    }
    
    # 测试用例2: 无效方案(违反重力约束)
    invalid_plan1 = {
        "structure": "floating_platform",
        "material": "aluminum",
        "load": 2000,
        "dimensions": (2.0, 2.0, 0.05)
    }
    
    # 测试用例3: 无效方案(违反材料强度)
    invalid_plan2 = {
        "structure": "bridge",
        "material": "concrete",
        "load": 1e6,  # 非常大的负载
        "dimensions": (0.1, 0.1, 5.0),  # 小截面
        "support_force": 2e6
    }
    
    # 验证并打印结果
    for i, plan in enumerate([valid_plan, invalid_plan1, invalid_plan2], 1):
        print(f"\nTest Case {i}: {plan['structure']}")
        try:
            result = pcl.validate_plan(plan)
            print(f"Valid: {result.is_valid}")
            print(f"Confidence: {result.confidence_score:.2f}")
            print(f"Message: {result.message}")
            if result.suggestions:
                print("Suggestions:")
                for sug in result.suggestions:
                    print(f"- {sug}")
        except ValueError as e:
            print(f"Validation Error: {str(e)}")