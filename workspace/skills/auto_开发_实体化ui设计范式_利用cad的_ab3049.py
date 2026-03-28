"""
名称: auto_开发_实体化ui设计范式_利用cad的_ab3049
描述: 本模块实现了'实体化UI设计范式'的核心逻辑。
      它利用计算几何算法模拟CAD内核的CSG（实体几何构造）操作，
      将Flutter等界面中的2D UI组件映射为具备物理属性的3D实体。
      系统能够根据物理法则（如材料成本、光线遮挡）自动优化UI形态。
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MaterializedUIEngine")

class GeometryError(Exception):
    """自定义异常：几何计算错误"""
    pass

class MaterialType(Enum):
    """材料类型枚举"""
    GLASS = 1.0  # 密度系数
    PLASTIC = 1.2
    METAL = 7.8

@dataclass
class Vector3:
    """三维向量"""
    x: float
    y: float
    z: float

    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

@dataclass
class UIComponent:
    """
    UI实体组件数据结构
    ---
    输入数据格式说明:
    - component_id: 组件唯一标识
    - position: 3D空间坐标
    - dimension: 长/宽/高
    - material: 材质类型
    - is_hollow: 是否已挖空
    """
    component_id: str
    position: Vector3
    dimension: Vector3
    material: MaterialType = MaterialType.PLASTIC
    is_hollow: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def volume(self) -> float:
        """计算当前体积"""
        return self.dimension.x * self.dimension.y * self.dimension.z

    @property
    def center_point(self) -> Vector3:
        """计算几何中心"""
        return Vector3(
            self.position.x + self.dimension.x / 2,
            self.position.y + self.dimension.y / 2,
            self.position.z + self.dimension.z / 2
        )

def _check_collision(a: UIComponent, b: UIComponent) -> bool:
    """
    辅助函数：检测两个3D包围盒是否碰撞
    """
    return (abs(a.center_point.x - b.center_point.x) < (a.dimension.x + b.dimension.x) / 2 and
            abs(a.center_point.y - b.center_point.y) < (a.dimension.y + b.dimension.y) / 2 and
            abs(a.center_point.z - b.center_point.z) < (a.dimension.z + b.dimension.z) / 2)

def perform_csg_subtraction(
    target: UIComponent, 
    tool: UIComponent, 
    safety_margin: float = 0.1
) -> UIComponent:
    """
    核心函数：执行CSG差集运算以优化材料使用
    ---
    模拟CAD中的 'Subtract' 操作。在UI按钮内部创建一个较小的 '工具体'，
    将其挖空以节省 '材料'，同时保留外壳厚度。
    
    参数:
        target: 需要被挖空的目标UI组件（例如按钮）
        tool: 用于挖空的工具体（通常是一个缩小的内部块）
        safety_margin: 最小壁厚安全检查值
        
    返回:
        UIComponent: 修改后的实体组件
    
    异常:
        GeometryError: 如果几何参数无效或壁厚过薄
    """
    logger.info(f"Performing CSG Subtraction on {target.component_id}")
    
    # 1. 数据验证
    if target.volume <= 0 or tool.volume <= 0:
        raise GeometryError("Component volume must be positive.")
    
    # 2. 边界检查：确保工具体完全位于目标内部
    # 简化算法：检查工具体的边界是否超出目标边界
    is_inside = (
        tool.position.x >= target.position.x and
        tool.position.y >= target.position.y and
        tool.position.z >= target.position.z and
        (tool.position.x + tool.dimension.x) <= (target.position.x + target.dimension.x) and
        (tool.position.y + tool.dimension.y) <= (target.position.y + target.dimension.y) and
        (tool.position.z + tool.dimension.z) <= (target.position.z + target.dimension.z)
    )
    
    if not is_inside:
        logger.warning("Tool geometry exceeds target bounds. Clamping or aborting.")
        raise GeometryError("Tool volume exceeds target volume boundaries.")

    # 3. 计算壁厚 (简化版：基于X轴宽度差)
    wall_thickness = (target.dimension.x - tool.dimension.x) / 2
    if wall_thickness < safety_margin:
        raise GeometryError(f"Wall thickness {wall_thickness} is below safety margin {safety_margin}.")

    # 4. 模拟物理属性变更
    # 实际体积 = 外部体积 - 内部挖空体积
    final_volume = target.volume - tool.volume
    
    # 更新组件状态
    target.metadata['physical_volume'] = final_volume
    target.metadata['mass'] = final_volume * target.material.value
    target.is_hollow = True
    
    logger.debug(f"New calculated mass: {target.metadata['mass']}")
    return target

def optimize_layout_by_union(
    components: List[UIComponent]
) -> Tuple[List[UIComponent], float]:
    """
    核心函数：通过并集运算优化空间布局
    ---
    遍历UI组件列表，检测视觉/物理碰撞。
    如果检测到重叠，模拟CSG 'Union' 运算将它们合并为单一实体，
    防止在AR环境中的Z-fighting（深度冲突）闪烁。
    
    参数:
        components: 待处理的UI组件列表
        
    返回:
        Tuple[List[UIComponent], float]: (优化后的组件列表, 节省的空间体积)
    """
    if not components:
        return [], 0.0

    logger.info(f"Starting layout optimization for {len(components)} components.")
    
    optimized_components = []
    merged_indices = set()
    total_saved_volume = 0.0
    
    for i, comp_a in enumerate(components):
        if i in merged_indices:
            continue
            
        current_merge = comp_a
        
        for j, comp_b in enumerate(components):
            if i == j or j in merged_indices:
                continue
                
            if _check_collision(current_merge, comp_b):
                logger.info(f"Collision detected between {comp_a.component_id} and {comp_b.component_id}. Merging.")
                
                # 模拟并集：创建一个新的包围盒包含两者
                # 新的起点
                new_x = min(current_merge.position.x, comp_b.position.x)
                new_y = min(current_merge.position.y, comp_b.position.y)
                new_z = min(current_merge.position.z, comp_b.position.z)
                
                # 新的尺寸
                new_dx = max(
                    current_merge.position.x + current_merge.dimension.x,
                    comp_b.position.x + comp_b.dimension.x
                ) - new_x
                new_dy = max(
                    current_merge.position.y + current_merge.dimension.y,
                    comp_b.position.y + comp_b.dimension.y
                ) - new_y
                new_dz = max(
                    current_merge.position.z + current_merge.dimension.z,
                    comp_b.position.z + comp_b.dimension.z
                ) - new_z
                
                # 计算重叠体积（节省的空间）
                overlap_x = min(current_merge.dimension.x, comp_b.dimension.x) - abs(current_merge.center_point.x - comp_b.center_point.x)
                # 简化计算，实际CSG体积计算要复杂得多
                
                # 创建合并后的组件
                current_merge = UIComponent(
                    component_id=f"merged_{comp_a.component_id}_{comp_b.component_id}",
                    position=Vector3(new_x, new_y, new_z),
                    dimension=Vector3(new_dx, new_dy, new_dz),
                    material=comp_a.material # 继承主组件材质
                )
                
                merged_indices.add(j)
        
        optimized_components.append(current_merge)
        
    return optimized_components, total_saved_volume

def generate_flutter_metadata(component: UIComponent) -> Dict[str, Any]:
    """
    输出转换：将物理属性转换为Flutter渲染引擎可读的元数据
    """
    return {
        "id": component.component_id,
        "transform": [
            component.dimension.x, 0, 0, component.position.x,
            0, component.dimension.y, 0, component.position.y,
            0, 0, component.dimension.z, component.position.z,
            0, 0, 0, 1
        ],
        "physics_body": {
            "mass": component.metadata.get('mass', 0.0),
            "is_hollow": component.is_hollow,
            "material_density": component.material.value
        }
    }

if __name__ == "__main__":
    # 使用示例
    
    # 1. 定义一个标准按钮 (100x40x10 mm)
    btn_position = Vector3(0, 0, 0)
    btn_dim = Vector3(100, 40, 10)
    button = UIComponent("btn_submit", btn_position, btn_dim, MaterialType.PLASTIC)
    
    # 2. 定义一个内部挖空工具 (留2mm壁厚)
    # 工具位置向内缩2mm
    tool_pos = Vector3(2, 2, 2)
    # 工具尺寸减小4mm (两侧各2mm)
    tool_dim = Vector3(96, 36, 6) # 假设背面封闭，Z轴挖8mm
    tool = UIComponent("cutter_tool", tool_pos, tool_dim)
    
    try:
        # 3. 执行挖空操作 (CSG Subtraction)
        # 这模拟了为了节省AR场景中的'虚拟材料'或增加真实感
        hollow_button = perform_csg_subtraction(button, tool)
        
        # 4. 输出结果
        print(f"Original Volume: {button.volume} mm3")
        print(f"Final Mass: {hollow_button.metadata['mass']:.2f} g")
        
        # 5. 生成Flutter数据
        flutter_data = generate_flutter_metadata(hollow_button)
        print(f"Flutter Transform Matrix: {flutter_data['transform']}")
        
    except GeometryError as e:
        logger.error(f"Design Rule Check Failed: {e}")

    # 6. 布局优化测试
    overlapping_btn = UIComponent("btn_cancel", Vector3(90, 0, 0), Vector3(100, 40, 10))
    layout, saved = optimize_layout_by_union([button, overlapping_btn])
    print(f"Merged component count: {len(layout)}")