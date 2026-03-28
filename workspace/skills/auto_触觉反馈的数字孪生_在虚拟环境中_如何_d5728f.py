"""
名称: auto_触觉反馈的数字孪生_在虚拟环境中_如何_d5728f
描述: 实现基于物理的触觉渲染模型，用于AGI在虚拟环境中的手眼协调与策略调整。
作者: Senior Python Engineer
日期: 2023-10-27
版本: 1.0.0
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Tuple, Dict, Optional, List
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MaterialType(Enum):
    """材料类型枚举"""
    ELASTIC = "elastic"          # 弹性材料
    VISCOELASTIC = "viscoelastic" # 粘弹性材料
    RIGID = "rigid"              # 刚性材料

@dataclass
class MaterialProperties:
    """
    材料物理属性数据结构
    
    属性:
        stiffness (float): 刚度系数
        damping (float): 阻尼系数
        density (float): 密度 (kg/m^3)
        material_type (MaterialType): 材料类型枚举
        yield_point (Optional[float]): 屈服点，超过此值将发生塑性形变
    """
    stiffness: float
    damping: float
    density: float
    material_type: MaterialType = MaterialType.ELASTIC
    yield_point: Optional[float] = None

    def __post_init__(self):
        """数据验证"""
        if self.stiffness < 0:
            raise ValueError("Stiffness must be non-negative")
        if self.damping < 0:
            raise ValueError("Damping must be non-negative")
        if self.density <= 0:
            raise ValueError("Density must be positive")

@dataclass
class ContactState:
    """
    接触状态数据结构
    
    属性:
        position (np.ndarray): 接触点位置 [x, y, z]
        normal_force (np.ndarray): 法向力向量
        penetration_depth (float): 穿透深度
        contact_velocity (np.ndarray): 接触点相对速度
    """
    position: np.ndarray
    normal_force: np.ndarray = field(default_factory=lambda: np.zeros(3))
    penetration_depth: float = 0.0
    contact_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))

class HapticFeedbackSystem:
    """
    触觉反馈数字孪生系统
    
    该系统建立基于物理的触觉渲染模型，使AI能够"感觉"虚拟环境中的材料属性。
    通过将真实节点映射到虚拟维度，实现基于反馈的策略调整。
    
    示例:
        >>> system = HapticFeedbackSystem()
        >>> material = MaterialProperties(1e5, 0.5, 1000)
        >>> contact = ContactState(position=np.array([0.1, 0.2, 0.3]), 
        ...                         penetration_depth=0.001)
        >>> feedback = system.compute_haptic_feedback(material, contact)
    """
    
    def __init__(self, time_step: float = 0.001):
        """
        初始化触觉反馈系统
        
        参数:
            time_step (float): 仿真时间步长 (秒)
        """
        self.time_step = time_step
        self._previous_forces = {}  # 存储历史力数据用于粘弹性计算
        self._history_length = 10   # 历史数据保留长度
        logger.info("HapticFeedbackSystem initialized with time_step=%.4f", time_step)
    
    def _validate_input(self, material: MaterialProperties, contact: ContactState) -> None:
        """
        验证输入数据的有效性
        
        参数:
            material: 材料属性对象
            contact: 接触状态对象
            
        抛出:
            ValueError: 如果输入数据无效
        """
        if not isinstance(material, MaterialProperties):
            raise TypeError("material must be MaterialProperties instance")
        
        if not isinstance(contact, ContactState):
            raise TypeError("contact must be ContactState instance")
            
        if contact.penetration_depth < 0:
            raise ValueError("Penetration depth cannot be negative")
            
        if np.any(np.isnan(contact.position)) or np.any(np.isinf(contact.position)):
            raise ValueError("Contact position contains invalid values")
    
    def compute_haptic_feedback(
        self, 
        material: MaterialProperties, 
        contact: ContactState
    ) -> Dict[str, np.ndarray]:
        """
        计算触觉反馈力
        
        基于材料属性和接触状态，计算虚拟环境中的触觉反馈力。
        支持弹性、粘弹性和刚性材料的模拟。
        
        参数:
            material: 材料属性对象
            contact: 接触状态对象
            
        返回:
            Dict[str, np.ndarray]: 包含以下键的字典:
                - 'force': 总反馈力向量 [Fx, Fy, Fz]
                - 'torque': 反馈力矩向量 [Tx, Ty, Tz]
                - 'stiffness_component': 刚度分量力
                - 'damping_component': 阻尼分量力
                
        抛出:
            ValueError: 如果输入数据无效
        """
        try:
            self._validate_input(material, contact)
            
            # 计算刚度力分量 (胡克定律)
            stiffness_force = self._compute_stiffness_force(material, contact)
            
            # 计算阻尼力分量
            damping_force = self._compute_damping_force(material, contact)
            
            # 计算总力
            total_force = stiffness_force + damping_force
            
            # 计算力矩 (假设接触点相对于原点)
            torque = np.cross(contact.position, total_force)
            
            # 存储历史数据用于粘弹性材料
            contact_id = id(contact)
            if contact_id not in self._previous_forces:
                self._previous_forces[contact_id] = []
            
            self._previous_forces[contact_id].append(total_force.copy())
            if len(self._previous_forces[contact_id]) > self._history_length:
                self._previous_forces[contact_id].pop(0)
            
            result = {
                'force': total_force,
                'torque': torque,
                'stiffness_component': stiffness_force,
                'damping_component': damping_force
            }
            
            logger.debug("Computed haptic feedback: F=%.2f N", np.linalg.norm(total_force))
            return result
            
        except Exception as e:
            logger.error("Error computing haptic feedback: %s", str(e))
            raise
    
    def _compute_stiffness_force(
        self, 
        material: MaterialProperties, 
        contact: ContactState
    ) -> np.ndarray:
        """
        计算刚度力分量
        
        参数:
            material: 材料属性
            contact: 接触状态
            
        返回:
            np.ndarray: 刚度力向量
        """
        # 假设法向量为z方向 (实际应用中应从几何体获取)
        normal = np.array([0, 0, 1])
        
        # 弹性力 = 刚度 * 穿透深度 * 法向量
        elastic_force = material.stiffness * contact.penetration_depth * normal
        
        # 考虑塑性变形
        if (material.yield_point is not None and 
            contact.penetration_depth > material.yield_point):
            plastic_reduction = (contact.penetration_depth - material.yield_point) * 0.8
            elastic_force *= (1 - plastic_reduction)
            
        return elastic_force
    
    def _compute_damping_force(
        self, 
        material: MaterialProperties, 
        contact: ContactState
    ) -> np.ndarray:
        """
        计算阻尼力分量
        
        参数:
            material: 材料属性
            contact: 接触状态
            
        返回:
            np.ndarray: 阻尼力向量
        """
        # 阻尼力 = 阻尼系数 * 速度
        damping_force = material.damping * contact.contact_velocity
        
        # 对于粘弹性材料，添加历史依赖性
        if material.material_type == MaterialType.VISCOELASTIC:
            contact_id = id(contact)
            if contact_id in self._previous_forces and self._previous_forces[contact_id]:
                history_avg = np.mean(self._previous_forces[contact_id], axis=0)
                damping_force += 0.1 * history_avg  # 添加历史依赖分量
                
        return damping_force
    
    def adapt_material_properties(
        self, 
        base_material: MaterialProperties,
        contact_history: List[ContactState]
    ) -> MaterialProperties:
        """
        根据接触历史自适应调整材料属性
        
        参数:
            base_material: 基础材料属性
            contact_history: 接触状态历史列表
            
        返回:
            MaterialProperties: 调整后的材料属性
        """
        if not contact_history:
            return base_material
            
        # 计算平均穿透深度
        avg_depth = np.mean([c.penetration_depth for c in contact_history])
        
        # 根据穿透深度调整刚度
        adjusted_stiffness = base_material.stiffness
        if avg_depth > 0.001:  # 如果平均穿透超过1mm
            adjusted_stiffness *= 1.2  # 增加刚度
            
        # 根据速度调整阻尼
        velocities = [np.linalg.norm(c.contact_velocity) for c in contact_history]
        avg_velocity = np.mean(velocities)
        adjusted_damping = base_material.damping * (1 + 0.1 * avg_velocity)
        
        logger.info("Adapted material properties: stiffness=%.1f, damping=%.3f", 
                   adjusted_stiffness, adjusted_damping)
        
        return MaterialProperties(
            stiffness=adjusted_stiffness,
            damping=adjusted_damping,
            density=base_material.density,
            material_type=base_material.material_type,
            yield_point=base_material.yield_point
        )

# 使用示例
if __name__ == "__main__":
    # 初始化触觉系统
    haptic_system = HapticFeedbackSystem(time_step=0.002)
    
    # 创建材料属性 (硅胶材料)
    silicone = MaterialProperties(
        stiffness=5e4,    # 50 kN/m
        damping=0.3,      # 阻尼系数
        density=1100,     # kg/m^3
        material_type=MaterialType.VISCOELASTIC
    )
    
    # 模拟接触状态
    contact_state = ContactState(
        position=np.array([0.05, 0.02, 0.1]),
        penetration_depth=0.002,  # 2mm穿透
        contact_velocity=np.array([0, 0, -0.1])  # 10cm/s向下速度
    )
    
    # 计算触觉反馈
    feedback = haptic_system.compute_haptic_feedback(silicone, contact_state)
    
    print("触觉反馈结果:")
    print(f"总力: {feedback['force']} N")
    print(f"力矩: {feedback['torque']} Nm")
    print(f"刚度分量: {feedback['stiffness_component']} N")
    print(f"阻尼分量: {feedback['damping_component']} N")
    
    # 自适应材料属性
    contact_history = [contact_state] * 5  # 模拟历史接触
    adjusted_material = haptic_system.adapt_material_properties(silicone, contact_history)
    print(f"\n调整后的刚度: {adjusted_material.stiffness} N/m")