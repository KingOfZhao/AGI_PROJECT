"""
名称: auto_构建_参数化ui装配系统_将ui组件视_6e384d
描述: 构建“参数化UI装配系统”。将UI组件视为CAD零件，支持相对坐标系的自动推导。
      当父级组件（如容器）发生几何变换（旋转、缩放）时，子级组件像CAD装配体中的
      零件一样自动跟随变换，且保持相对约束关系。
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ParametricUIAssembler")

@dataclass
class Transform:
    """
    表示二维空间中的几何变换。
    
    Attributes:
        x (float): X轴坐标。
        y (float): Y轴坐标。
        rotation (float): 旋转角度（度数）。
        scale_x (float): X轴缩放比例。
        scale_y (float): Y轴缩放比例。
    """
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0

    def to_matrix(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """
        将变换转换为3x3仿射变换矩阵（行优先）。
        用于高效的矩阵乘法推导。
        """
        rad = math.radians(self.rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        
        # 缩放 -> 旋转 -> 平移
        # Matrix: [cos*sx, -sin*sy, tx]
        #         [sin*sx,  cos*sy, ty]
        #         [0,       0,      1 ]
        
        a = cos_r * self.scale_x
        b = -sin_r * self.scale_y
        c = self.x
        d = sin_r * self.scale_x
        e = cos_r * self.scale_y
        f = self.y
        
        return ((a, b, c), (d, e, f))

@dataclass
class UIComponent:
    """
    UI组件基类，模拟CAD零件。
    
    Attributes:
        component_id (str): 组件唯一标识符。
        local_transform (Transform): 相对于父级的局部变换。
        children (List['UIComponent']): 子组件列表。
        _cached_world_transform (Optional[Transform]): 缓存的世界坐标变换，避免重复计算。
    """
    component_id: str
    local_transform: Transform = field(default_factory=Transform)
    children: List['UIComponent'] = field(default_factory=list)
    _cached_world_transform: Optional[Transform] = field(default=None, init=False, repr=False)

    def add_child(self, child: 'UIComponent') -> None:
        """添加子组件。"""
        if not isinstance(child, UIComponent):
            raise TypeError("Child must be an instance of UIComponent")
        self.children.append(child)
        logger.info(f"Added child {child.component_id} to {self.component_id}")

    def update_local_transform(self, **kwargs: float) -> None:
        """
        更新局部变换参数。
        
        Args:
            **kwargs: Transform属性
        """
        valid_keys = {'x', 'y', 'rotation', 'scale_x', 'scale_y'}
        for key, value in kwargs.items():
            if key in valid_keys:
                if not isinstance(value, (int, float)):
                    raise ValueError(f"Value for {key} must be numeric")
                setattr(self.local_transform, key, value)
            else:
                logger.warning(f"Invalid transform key ignored: {key}")
        
        # 标记需要重新计算世界坐标
        self._cached_world_transform = None
        # 递归标记所有子节点需要更新
        self._invalidate_children_cache()

    def _invalidate_children_cache(self) -> None:
        """递归清除子节点的缓存。"""
        for child in self.children:
            child._cached_world_transform = None
            child._invalidate_children_cache()

    def get_world_transform(self, parent_world: Optional[Transform] = None) -> Transform:
        """
        核心算法：递归推导世界坐标变换。
        模拟CAD装配体的层级关系。
        
        Args:
            parent_world (Optional[Transform]): 父级的世界变换。如果是None，则视为根节点。
        
        Returns:
            Transform: 当前组件在世界坐标系中的变换。
        """
        if self._cached_world_transform is not None:
            return self._cached_world_transform

        if parent_world is None:
            # 如果是根节点且没有显式传入父级变换，默认为单位矩阵
            # 但通常根节点会有自己的位置，这里简化处理：
            # 如果parent_world是None，我们假设父级是(0,0,0)
            parent_matrix = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        else:
            parent_matrix = parent_world.to_matrix()

        local_matrix = self.local_transform.to_matrix()
        
        # 矩阵乘法: Parent * Local = World
        # P = ((p00, p01, p02), (p10, p11, p12))
        # L = ((l00, l01, l02), (l10, l11, l12))
        
        p00, p01, p02 = parent_matrix[0]
        p10, p11, p12 = parent_matrix[1]
        l00, l01, l02 = local_matrix[0]
        l10, l11, l12 = local_matrix[1]

        # 结果矩阵计算
        r00 = p00 * l00 + p01 * l10
        r01 = p00 * l01 + p01 * l11
        r02 = p00 * l02 + p01 * l12 + p02 # 平移X
        
        r10 = p10 * l00 + p11 * l10
        r11 = p10 * l01 + p11 * l11
        r12 = p10 * l02 + p11 * l12 + p12 # 平移Y
        
        # 将矩阵反向解析回Transform参数（简化解码，仅提取主要信息）
        # 提取缩放
        sx = math.sqrt(r00**2 + r10**2)
        sy = math.sqrt(r01**2 + r11**2)
        
        # 提取旋转 (atan2)
        rotation = math.degrees(math.atan2(r10, r00))
        
        world_transform = Transform(
            x=r02, 
            y=r12, 
            rotation=rotation, 
            scale_x=sx, 
            scale_y=sy
        )
        
        self._cached_world_transform = world_transform
        return world_transform

def traverse_and_render(component: UIComponent, parent_world: Optional[Transform] = None, level: int = 0) -> Dict[str, Any]:
    """
    辅助函数：遍历组件树并生成渲染数据。
    
    Args:
        component (UIComponent): 当前组件。
        parent_world (Optional[Transform]): 父级的世界变换。
        level (int): 当前层级深度。
        
    Returns:
        Dict[str, Any]: 包含层级结构的渲染信息字典。
    """
    current_world = component.get_world_transform(parent_world)
    
    indent = "  " * level
    logger.debug(f"{indent}Processing {component.component_id}: World Pos({current_world.x:.1f}, {current_world.y:.1f})")
    
    node_data = {
        "id": component.component_id,
        "world_transform": {
            "x": round(current_world.x, 2),
            "y": round(current_world.y, 2),
            "rotation": round(current_world.rotation, 2),
            "scale_x": round(current_world.scale_x, 2),
            "scale_y": round(current_world.scale_y, 2)
        },
        "children": []
    }
    
    for child in component.children:
        child_data = traverse_and_render(child, current_world, level + 1)
        node_data["children"].append(child_data)
        
    return node_data

def build_dashboard_layout() -> Dict[str, Any]:
    """
    核心函数：构建一个仪表盘布局示例。
    
    场景：一个旋转的主面板，上面有一个固定的按钮和一个嵌套的图标。
    演示当父级旋转时，子级如何保持相对位置并跟随旋转。
    
    Returns:
        Dict[str, Any]: 完整的渲染树数据。
    """
    logger.info("Building parametric UI layout...")
    
    # 1. 根容器：位于 (100, 100)，旋转 45 度
    root_panel = UIComponent(
        component_id="root_panel",
        local_transform=Transform(x=100, y=100, rotation=45)
    )
    
    # 2. 子组件A：按钮，相对于父级位于 (50, 0)
    # 期望效果：由于父级旋转45度，该按钮在屏幕空间应位于对角线上
    # 且按钮自身也应该继承45度旋转
    button = UIComponent(
        component_id="submit_btn",
        local_transform=Transform(x=50, y=0)
    )
    
    # 3. 子组件B：嵌套图标，位于按钮内部 (10, 10)，且自身旋转 90 度
    # 期望效果：世界旋转 = 45 (父) + 90 (自身) = 135 度
    icon = UIComponent(
        component_id="btn_icon",
        local_transform=Transform(x=10, y=10, rotation=90)
    )
    
    # 装配
    button.add_child(icon)
    root_panel.add_child(button)
    
    # 模拟动态更新：父级突然缩放
    logger.info("Simulating parent scaling transformation...")
    root_panel.update_local_transform(scale_x=2.0) # X轴放大2倍
    
    # 生成最终渲染数据
    render_tree = traverse_and_render(root_panel)
    
    return render_tree

if __name__ == "__main__":
    # 使用示例
    try:
        result_tree = build_dashboard_layout()
        print("\n--- Final Render Tree (JSON View) ---")
        import json
        print(json.dumps(result_tree, indent=2))
        
        # 验证数据
        btn_world = result_tree['children'][0]['world_transform']
        icon_world = result_tree['children'][0]['children'][0]['world_transform']
        
        print(f"\nValidation:")
        print(f"Root Panel Scale X: {result_tree['world_transform']['scale_x']}") # Should be 2.0
        print(f"Button World Rotation: {btn_world['rotation']}") # Should be 45
        print(f"Icon World Rotation: {icon_world['rotation']}") # Should be 135
        
    except Exception as e:
        logger.error(f"System failed: {e}")
        raise