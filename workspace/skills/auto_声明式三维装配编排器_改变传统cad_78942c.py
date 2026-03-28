"""
 declarative_3d_assembler.py
 高级Python模块：声明式三维装配编排器

 该模块实现了一种声明式的三维装配策略，改变了传统CAD软件中
 逐一添加配合关系的繁琐模式。借鉴Flutter/React的布局思维，
 允许工程师以数据结构的形式声明部件之间的拓扑关系（如圆周均布、
 线性堆叠、轴对齐），由编排器自动推导具体的几何变换矩阵。

 Author: AGI System
 Version: 1.0.0
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Declarative3DAssembler")

# --- 数据结构定义 ---

class LayoutType(Enum):
    """定义装配布局的类型"""
    STACK_X = auto()      # 沿X轴线性堆叠
    STACK_Y = auto()      # 沿Y轴线性堆叠
    CIRCULAR = auto()     # 圆周均布
    PAIR_ALIGN = auto()   # 双部件对齐

@dataclass
class Vector3:
    """简单的三维向量类"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __repr__(self) -> str:
        return f"Vector3(x={self.x:.2f}, y={self.y:.2f}, z={self.z:.2f})"

@dataclass
class Transform:
    """
    描述一个部件在三维空间中的位置和旋转。
    此处简化为位移，实际AGI场景可扩展为4x4矩阵。
    """
    position: Vector3 = field(default_factory=Vector3)
    rotation: Vector3 = field(default_factory=Vector3) # Euler angles for simplicity

    def __repr__(self) -> str:
        return f"Pos: {self.position}, Rot: {self.rotation}"

@dataclass
class Part:
    """
    表示一个三维部件。
    """
    id: str
    name: str
    width: float = 10.0  # 包围盒尺寸，用于间距计算
    height: float = 10.0
    depth: float = 10.0
    # 计算后的最终位姿
    transform: Transform = field(default_factory=Transform)

@dataclass
class LayoutConstraint:
    """
    声明式约束容器。
    类似于Flutter的Flex或Row/Column配置。
    """
    layout_type: LayoutType
    parts: List[str]      # 引用的部件ID列表
    params: Dict = field(default_factory=dict) # 额外参数，如半径、间距、对齐轴

# --- 核心类 ---

class DeclarativeAssembler:
    """
    声明式三维装配编排器核心类。
    
    负责解析声明式的布局约束，并计算每个部件的最终空间变换。
    
    输入格式说明:
        - add_part: 接收Part对象，包含ID和几何元数据。
        - add_constraint: 接收LayoutConstraint，描述布局逻辑。
    
    输出格式说明:
        - assemble: 返回 Dict[str, Transform]，Key为部件ID，Value为计算后的变换矩阵/对象。
    """

    def __init__(self):
        self._parts_registry: Dict[str, Part] = {}
        self._constraints: List[LayoutConstraint] = []
        logger.info("Declarative Assembler initialized.")

    def add_part(self, part: Part) -> None:
        """注册一个部件到编排器中"""
        if not part.id:
            raise ValueError("Part ID cannot be empty.")
        if part.id in self._parts_registry:
            logger.warning(f"Overwriting existing part with ID: {part.id}")
        
        self._parts_registry[part.id] = part
        logger.debug(f"Part registered: {part.id}")

    def add_constraint(self, constraint: LayoutConstraint) -> None:
        """添加一个声明式布局约束"""
        if not constraint.parts:
            raise ValueError("Constraint must apply to at least one part.")
        
        # 验证引用的部件是否存在
        for pid in constraint.parts:
            if pid not in self._parts_registry:
                raise ValueError(f"Unknown Part ID in constraint: {pid}")
        
        self._constraints.append(constraint)
        logger.info(f"Constraint added: {constraint.layout_type.name} for {len(constraint.parts)} parts.")

    def _calculate_circular_layout(self, parts: List[Part], center: Vector3, radius: float, axis: str = 'Z') -> None:
        """
        辅助函数：计算圆周均布逻辑。
        
        Args:
            parts: 需要布局的部件列表
            center: 圆心坐标
            radius: 分布半径
            axis: 旋转平面法线轴 ('X', 'Y', 'Z')
        """
        count = len(parts)
        if count == 0:
            return
        
        angle_step = (2 * math.pi) / count
        logger.debug(f"Calculating circular layout for {count} parts, radius {radius}")
        
        for i, part in enumerate(parts):
            angle = i * angle_step
            # 简化处理：默认绕Z轴分布
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle)
            z = center.z
            
            part.transform.position = Vector3(x, y, z)
            # 自动旋转部件使其朝向圆心（简易逻辑：设置Z轴旋转）
            part.transform.rotation = Vector3(0, 0, math.degrees(angle))

    def _calculate_stack_layout(self, parts: List[Part], axis: str, spacing: float, alignment: str = 'center') -> None:
        """
        辅助函数：计算线性堆叠逻辑（类似Row/Column）。
        
        Args:
            parts: 部件列表
            axis: 堆叠轴 ('X', 'Y', 'Z')
            spacing: 部件间距
            alignment: 对齐方式 (暂未完全实现对齐逻辑，默认起始对齐)
        """
        current_offset = 0.0
        logger.debug(f"Calculating stack layout on axis {axis} with spacing {spacing}")
        
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        idx = axis_map.get(axis.upper(), 0)
        dimensions = ['width', 'height', 'depth']
        
        for part in parts:
            # 获取当前部件在该轴上的尺寸
            part_dim = getattr(part, dimensions[idx])
            
            # 创建位置向量
            pos = [0.0, 0.0, 0.0]
            pos[idx] = current_offset + part_dim / 2
            
            part.transform.position = Vector3(*pos)
            
            # 更新偏移量：当前部件尺寸 + 间距
            current_offset += part_dim + spacing

    def assemble(self) -> Dict[str, Transform]:
        """
        执行装配计算。
        遍历所有约束，推导几何位置。
        
        Returns:
            包含每个部件最终变换的字典。
        """
        logger.info("Starting assembly resolution...")
        
        for constraint in self._constraints:
            # 获取约束涉及的实体对象
            resolved_parts = [self._parts_registry[pid] for pid in constraint.parts]
            
            if constraint.layout_type == LayoutType.CIRCULAR:
                radius = constraint.params.get('radius', 50.0)
                center = constraint.params.get('center', Vector3(0,0,0))
                self._calculate_circular_layout(resolved_parts, center, radius)
                
            elif constraint.layout_type in [LayoutType.STACK_X, LayoutType.STACK_Y]:
                spacing = constraint.params.get('spacing', 5.0)
                axis_char = 'X' if constraint.layout_type == LayoutType.STACK_X else 'Y'
                self._calculate_stack_layout(resolved_parts, axis_char, spacing)
                
            elif constraint.layout_type == LayoutType.PAIR_ALIGN:
                # 简单的对齐逻辑：将第二个部件移动到第一个部件的位置（或保持相对偏移）
                if len(resolved_parts) >= 2:
                    target_pos = resolved_parts[0].transform.position
                    # 这里演示轴对齐：Y轴对齐
                    resolved_parts[1].transform.position.y = target_pos.y
                    logger.info(f"Aligned {resolved_parts[1].id} Y-axis to {resolved_parts[0].id}")

        # 汇总结果
        results = {pid: p.transform for pid, p in self._parts_registry.items()}
        logger.info(f"Assembly complete. Resolved {len(results)} transforms.")
        return results

# --- 使用示例与测试 ---

if __name__ == "__main__":
    # 1. 初始化编排器
    assembler = DeclarativeAssembler()

    # 2. 定义部件 (模拟CAD零件库)
    # 6个螺栓
    bolts = [Part(id=f"bolt_{i}", name="M6 Bolt", width=5, height=10, depth=5) for i in range(6)]
    # 2个长梁
    beams = [Part(id=f"beam_{i}", name="Structural Beam", width=100, height=10, depth=10) for i in range(2)]
    
    # 3. 注册部件
    for b in bolts + beams:
        assembler.add_part(b)

    # 4. 声明约束 (核心逻辑)
    
    # 场景A: 6个螺栓在圆周上均布
    assembler.add_constraint(
        LayoutConstraint(
            layout_type=LayoutType.CIRCULAR,
            parts=[b.id for b in bolts],
            params={'radius': 50.0, 'center': Vector3(0, 0, 0)}
        )
    )

    # 场景B: 2个梁沿X轴排列，间距20mm
    assembler.add_constraint(
        LayoutConstraint(
            layout_type=LayoutType.STACK_X,
            parts=[b.id for b in beams],
            params={'spacing': 20.0}
        )
    )

    # 5. 执行自动推导
    final_transforms = assembler.assemble()

    # 6. 打印结果 (在实际应用中，这里会驱动CAD内核或Three.js渲染)
    print("\n--- Assembly Results ---")
    for pid, transform in final_transforms.items():
        print(f"Part: {pid:<10} | {transform}")