"""
模块: zombie_node_detector
描述: 用于检测AGI系统或知识图谱中的“空转节点”（Zombie Nodes）。
      这些节点在逻辑上自洽，但在物理现实中不可行（违背物理定律）。
作者: AGI System Core Engineer
版本: 1.0.0
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PhysicsViolationType(Enum):
    """物理违规类型枚举"""
    ENERGY_CONSERVATION = "能量守恒违背"
    THERMODYNAMICS_SECOND_LAW = "热力学第二定律违背 (熵减)"
    SPEED_LIMIT = "超越光速限制"
    CAUSALITY = "因果律违背"
    UNDEFINED_ENTITY = "未定义的物理实体"

@dataclass
class PhysicsVector:
    """通用物理向量类，用于表示能量、质量、动量等"""
    value: float
    unit: str
    uncertainty: float = 0.0

    def __add__(self, other: 'PhysicsVector') -> 'PhysicsVector':
        if self.unit != other.unit:
            raise ValueError(f"单位不匹配: {self.unit} vs {other.unit}")
        return PhysicsVector(
            value=self.value + other.value,
            unit=self.unit,
            uncertainty=math.sqrt(self.uncertainty**2 + other.uncertainty**2)
        )

    def is_positive(self) -> bool:
        return self.value > 0

@dataclass
class ConceptNode:
    """概念节点定义"""
    id: str
    name: str
    description: str
    inputs: Dict[str, PhysicsVector] = field(default_factory=dict)
    outputs: Dict[str, PhysicsVector] = field(default_factory=dict)
    required_conditions: List[str] = field(default_factory=list)

class PhysicsValidator:
    """
    物理边界验证器。
    基于基础物理定律检查节点的输入输出是否自洽。
    """
    
    # 物理常数
    C = 299792458  # 光速 m/s
    MIN_ENTROPY_INCREASE = 0  # 孤立系统熵增下限

    def __init__(self, strict_mode: bool = True):
        """
        初始化验证器。
        
        Args:
            strict_mode (bool): 如果为True，未知物理量默认视为不可行；
                                如果为False，允许未定义的物理量通过。
        """
        self.strict_mode = strict_mode
        logger.info(f"PhysicsValidator initialized with strict_mode={strict_mode}")

    def validate_energy_conservation(self, inputs: Dict[str, PhysicsVector], 
                                     outputs: Dict[str, PhysicsVector]) -> Tuple[bool, Optional[str]]:
        """
        核心函数1: 验证能量守恒定律。
        检查输入的总能量是否大于或等于输出的总能量（考虑损耗）。
        
        Args:
            inputs: 输入的物理量字典
            outputs: 输出的物理量字典
            
        Returns:
            (bool, Optional[str]): (是否合法, 错误信息)
        """
        energy_in = inputs.get('energy', PhysicsVector(0, 'J'))
        energy_out = outputs.get('energy', PhysicsVector(0, 'J'))
        
        # 边界检查：确保数值有效
        if not all(math.isfinite(v.value) for v in [energy_in, energy_out]):
            return False, "包含无效数值"
            
        if energy_out.value > energy_in.value:
            msg = f"能量不守恒: 输入 {energy_in.value}J < 输出 {energy_out.value}J"
            logger.warning(msg)
            return False, msg
            
        return True, None

    def validate_thermodynamics(self, inputs: Dict[str, PhysicsVector], 
                                outputs: Dict[str, PhysicsVector]) -> Tuple[bool, Optional[str]]:
        """
        核心函数2: 验证热力学第二定律。
        检查是否在没有外部做功的情况下产生了有序结构（熵减）。
        """
        # 简化模型：检查是否从热能完全转化为功而没有热量损失
        # 或者检查 'order' 指标是否在没有能量输入的情况下增加
        
        has_heat_in = inputs.get('heat', PhysicsVector(0, 'J')).value > 0
        has_work_out = outputs.get('work', PhysicsVector(0, 'J')).value > 0
        has_waste_heat = outputs.get('waste_heat', PhysicsVector(0, 'J')).value > 0
        
        if has_heat_in and has_work_out and not has_waste_heat:
            # 这是一个简化的检查：热量完全转化为功（第二类永动机）
            return False, "违背热力学第二定律：热能完全转化为功而不产生其他影响"
            
        return True, None

    def check_physical_existence(self, node: ConceptNode) -> Tuple[bool, Optional[str]]:
        """
        辅助函数: 检查概念所依赖的物理实体是否存在。
        例如检查"真空中的呼吸"——真空不支持呼吸介质。
        """
        # 定义不存在的或互斥的物理条件
        impossible_conditions = {
            "vacuum_breathing": ["vacuum", "oxygen_exchange"],
            "perpetual_motion": ["infinite_energy_source", "closed_system"]
        }
        
        # 检查节点描述中的关键词
        desc_lower = node.description.lower()
        
        # 规则1：真空中的生物过程
        if "vacuum" in desc_lower and ("breathe" in desc_lower or "combustion" in desc_lower):
             return False, f"物理不可行: 在真空中无法进行需要介质的交互 (如呼吸/燃烧)"
             
        # 规则2：逻辑上的绝对否定
        if "square_circle" in node.name.lower():
            return False, "逻辑矛盾: 方形圆不存在"
            
        return True, None

class ZombieNodeDetector:
    """
    主检测器类，整合所有验证逻辑。
    """
    
    def __init__(self):
        self.validator = PhysicsValidator(strict_mode=True)
        logger.info("ZombieNodeDetector instance created.")

    def analyze_node(self, node: ConceptNode) -> Dict[str, Union[bool, List[str]]]:
        """
        对给定的节点进行全面分析，判断是否为空转节点。
        
        Args:
            node (ConceptNode): 待分析的概念节点。
            
        Returns:
            dict: 包含分析结果。
                {
                    "is_zombie": bool,
                    "violations": List[str],
                    "confidence": float
                }
        """
        if not node.id or not node.name:
            raise ValueError("节点必须包含ID和名称")

        violations = []
        
        # 1. 检查物理存在性
        is_valid_existence, msg_exist = self.validator.check_physical_existence(node)
        if not is_valid_existence:
            violations.append(f"[Entity Error]: {msg_exist}")

        # 2. 检查能量守恒
        is_valid_energy, msg_energy = self.validator.validate_energy_conservation(node.inputs, node.outputs)
        if not is_valid_energy:
            violations.append(f"[Energy Error]: {msg_energy}")

        # 3. 检查热力学定律
        is_valid_thermo, msg_thermo = self.validator.validate_thermodynamics(node.inputs, node.outputs)
        if not is_valid_thermo:
            violations.append(f"[Thermodynamics Error]: {msg_thermo}")

        is_zombie = len(violations) > 0
        
        if is_zombie:
            logger.warning(f"检测到空转节点: {node.name} - Reasons: {violations}")
        else:
            logger.info(f"节点验证通过: {node.name}")

        return {
            "is_zombie": is_zombie,
            "violations": violations,
            "confidence": 1.0 if is_zombie else 0.0 # 简化的置信度
        }

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 示例 1: 一个正常的节点
    normal_node = ConceptNode(
        id="node_001",
        name="Internal Combustion Engine",
        description="Converts chemical energy to mechanical work.",
        inputs={
            "fuel_energy": PhysicsVector(value=1000, unit="J"),
            "oxygen": PhysicsVector(value=10, unit="mol")
        },
        outputs={
            "work": PhysicsVector(value=300, unit="J"),
            "waste_heat": PhysicsVector(value=700, unit="J")
        }
    )

    # 示例 2: 一个空转节点 - 违背能量守恒
    zombie_node_energy = ConceptNode(
        id="node_002",
        name="Infinite Battery",
        description="Outputs more energy than input without loss.",
        inputs={"energy": PhysicsVector(value=10, unit="J")},
        outputs={"energy": PhysicsVector(value=1000, unit="J")}
    )

    # 示例 3: 一个空转节点 - 物理环境矛盾
    zombie_node_env = ConceptNode(
        id="node_003",
        name="Vacuum Respiration",
        description="A biological process to breathe in a perfect vacuum for eternal life.",
        inputs={"vacuum": PhysicsVector(value=1, unit="atm_neg")},
        outputs={"life_force": PhysicsVector(value=999, unit="years")}
    )

    detector = ZombieNodeDetector()

    print("-" * 30)
    print(f"Analyzing: {normal_node.name}")
    result1 = detector.analyze_node(normal_node)
    print(f"Result: Zombie={result1['is_zombie']}")

    print("-" * 30)
    print(f"Analyzing: {zombie_node_energy.name}")
    result2 = detector.analyze_node(zombie_node_energy)
    print(f"Result: Zombie={result2['is_zombie']}, Violations: {result2['violations']}")

    print("-" * 30)
    print(f"Analyzing: {zombie_node_env.name}")
    result3 = detector.analyze_node(zombie_node_env)
    print(f"Result: Zombie={result3['is_zombie']}, Violations: {result3['violations']}")