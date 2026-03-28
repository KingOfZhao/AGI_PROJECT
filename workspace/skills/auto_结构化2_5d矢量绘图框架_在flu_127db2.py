"""
结构化2.5D矢量绘图框架 (Structured 2.5D Vector Drawing Framework)

该模块实现了一个基于构造实体几何 (CSG) 的参数化矢量绘图核心逻辑。
它允许用户定义具有高度信息的2D图元，并通过非破坏性布尔运算（并集、交集、差集）
组合成复杂的2.5D零件。

主要特点：
- 参数化设计：所有图元和操作均保留参数，支持实时修改。
- 非破坏性编辑：CSG树结构允许回溯和修改历史操作。
- 2.5D支持：图元包含Z轴高度和拉伸信息，可用于模拟简单的3D效果或CAM路径。

Author: AGI System
Version: 1.0.0
Date: 2023-10-27
"""

import logging
import json
from typing import List, Dict, Optional, Union, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import math

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BooleanOperation(Enum):
    """定义CSG支持的布尔运算类型"""
    UNION = "union"           # 并集 (A + B)
    DIFFERENCE = "difference" # 差集 (A - B)
    INTERSECTION = "intersection" # 交集 (A ∩ B)

class PrimitiveType(Enum):
    """定义基础几何图元类型"""
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ROUNDED_RECT = "rounded_rect"

@dataclass
class Point2D:
    """二维坐标点"""
    x: float
    y: float

    def __post_init__(self):
        if not isinstance(self.x, (int, float)) or not isinstance(self.y, (int, float)):
            raise TypeError("坐标必须是数字类型")

@dataclass
class GeometryPrimitive:
    """
    几何图元基类/数据结构
    代表CSG树中的叶子节点，包含具体的几何参数。
    """
    id: str
    type: PrimitiveType
    position: Point2D
    height: float = 10.0  # 2.5D的高度属性（拉伸厚度）
    params: Dict[str, Any] = field(default_factory=dict) # 额外参数，如半径、宽高等

    def __post_init__(self):
        self._validate_params()

    def _validate_params(self):
        """验证图元参数的有效性"""
        if self.height <= 0:
            logger.warning(f"图元 {self.id} 的高度 {self.height} 无效，已重置为 0.1")
            self.height = 0.1

        if self.type == PrimitiveType.CIRCLE:
            if 'radius' not in self.params or self.params['radius'] <= 0:
                raise ValueError(f"圆形图元 {self.id} 缺少有效的 'radius' 参数")
        
        elif self.type == PrimitiveType.RECTANGLE:
            if 'width' not in self.params or 'height_2d' not in self.params:
                raise ValueError(f"矩形图元 {self.id} 缺少 'width' 或 'height_2d' 参数")

    def to_dict(self) -> Dict:
        """序列化图元"""
        return {
            "id": self.id,
            "type": self.type.value,
            "position": asdict(self.position),
            "height": self.height,
            "params": self.params
        }

class CSGNode:
    """
    CSG树节点
    可以是一个具体的图元（叶子），也可以是一个操作（分支）。
    """
    def __init__(self, 
                 node_type: str = "primitive", 
                 primitive: Optional[GeometryPrimitive] = None,
                 operation: Optional[BooleanOperation] = None,
                 left_child: Optional['CSGNode'] = None,
                 right_child: Optional['CSGNode'] = None):
        
        self.node_type = node_type # 'primitive' or 'operation'
        self.primitive = primitive
        self.operation = operation
        self.left_child = left_child
        self.right_child = right_child
        self._cache = None # 缓存计算结果，用于性能优化
        
        logger.debug(f"创建CSG节点: 类型={node_type}")

    def is_leaf(self) -> bool:
        return self.node_type == "primitive"

    def to_json(self) -> str:
        """将CSG树序列化为JSON字符串，用于存储或网络传输"""
        return json.dumps(self._to_dict_recursive(), indent=2)

    def _to_dict_recursive(self) -> Dict:
        """递归辅助函数，构建字典结构"""
        if self.is_leaf():
            return {
                "type": "primitive",
                "data": self.primitive.to_dict() if self.primitive else None
            }
        else:
            return {
                "type": "operation",
                "op": self.operation.value if self.operation else None,
                "left": self.left_child._to_dict_recursive() if self.left_child else None,
                "right": self.right_child._to_dict_recursive() if self.right_child else None
            }

class DrawingEngine:
    """
    绘图引擎核心类
    负责管理CSG树，处理参数修改，并生成最终的绘图指令数据。
    虽然Flutter负责渲染，但此处的Python后端负责逻辑验证和树管理。
    """
    def __init__(self):
        self.root: Optional[CSGNode] = None
        self.primitives_registry: Dict[str, GeometryPrimitive] = {}
        logger.info("DrawingEngine 初始化完成")

    def create_primitive(self, 
                         p_type: PrimitiveType, 
                         id: str, 
                         x: float, y: float, 
                         height: float, 
                         **kwargs) -> GeometryPrimitive:
        """
        创建一个新的几何图元并注册。
        
        Args:
            p_type: 图元类型
            id: 唯一标识符
            x, y: 位置坐标
            height: 拉伸高度
            **kwargs: 特定图元参数 (radius, width, etc.)
            
        Returns:
            GeometryPrimitive: 创建好的图元对象
            
        Raises:
            ValueError: 参数校验失败
        """
        if id in self.primitives_registry:
            logger.error(f"ID冲突: {id} 已存在")
            raise ValueError(f"图元 ID {id} 已存在")

        pos = Point2D(x, y)
        prim = GeometryPrimitive(
            id=id, 
            type=p_type, 
            position=pos, 
            height=height, 
            params=kwargs
        )
        
        self.primitives_registry[id] = prim
        logger.info(f"创建图元: {id} ({p_type.value})")
        return prim

    def build_csg_tree(self, 
                       operation: BooleanOperation, 
                       left: Union[CSGNode, GeometryPrimitive], 
                       right: Union[CSGNode, GeometryPrimitive]) -> CSGNode:
        """
        构建或合并CSG树节点。
        
        Args:
            operation: 布尔运算类型
            left: 左操作数 (可以是图元或另一个CSG节点)
            right: 右操作数
            
        Returns:
            CSGNode: 新构建的复合节点
        """
        logger.info(f"构建CSG节点: {operation.value}")
        
        # 将原始图元包装为CSGNode
        left_node = left if isinstance(left, CSGNode) else CSGNode(node_type="primitive", primitive=left)
        right_node = right if isinstance(right, CSGNode) else CSGNode(node_type="primitive", primitive=right)

        new_node = CSGNode(
            node_type="operation",
            operation=operation,
            left_child=left_node,
            right_child=right_node
        )
        return new_node

    def update_primitive_param(self, prim_id: str, param_name: str, new_value: float) -> bool:
        """
        【核心功能】实时更新图元参数。
        这是参数化设计的核心，允许非破坏性修改。
        
        Args:
            prim_id: 要修改的图元ID
            param_name: 参数名 (如 'radius', 'position_x')
            new_value: 新值
            
        Returns:
            bool: 是否修改成功
        """
        if prim_id not in self.primitives_registry:
            logger.error(f"修改失败: 找不到ID {prim_id}")
            return False

        prim = self.primitives_registry[prim_id]
        
        try:
            if param_name == "position_x":
                prim.position.x = new_value
            elif param_name == "position_y":
                prim.position.y = new_value
            elif param_name == "height":
                prim.height = new_value
            else:
                if param_name not in prim.params:
                    logger.warning(f"参数 {param_name} 在图元 {prim_id} 中不存在，将创建新字段")
                prim.params[param_name] = new_value
            
            # 触发重新验证
            prim._validate_params()
            logger.info(f"参数更新成功: {prim_id}.{param_name} = {new_value}")
            return True
            
        except Exception as e:
            logger.exception(f"更新参数时发生错误: {e}")
            return False

    def export_to_render_data(self) -> Dict:
        """
        导出为渲染引擎（如Flutter）可识别的JSON格式。
        实际生产中，这里会执行多边形裁剪算法（如Weiler-Atherton），
        此处仅导出结构化数据供前端解析。
        """
        if not self.root:
            return {"status": "empty"}
        
        return {
            "status": "ok",
            "csg_tree": self.root.to_dict_recursive(),
            "primitives_list": [p.to_dict() for p in self.primitives_registry.values()]
        }

# ==========================================
# 辅助函数
# ==========================================

def calculate_bounding_box(prim: GeometryPrimitive) -> Tuple[Point2D, Point2D]:
    """
    计算几何图元的轴对齐包围盒 (AABB)。
    用于辅助视图缩放或碰撞检测。
    
    Args:
        prim: 几何图元对象
        
    Returns:
        (min_point, max_point): 左上角和右下角坐标
    """
    cx, cy = prim.position.x, prim.position.y
    
    if prim.type == PrimitiveType.CIRCLE:
        r = prim.params.get('radius', 0)
        return (Point2D(cx - r, cy - r), Point2D(cx + r, cy + r))
        
    elif prim.type == PrimitiveType.RECTANGLE:
        w = prim.params.get('width', 0) / 2
        h = prim.params.get('height_2d', 0) / 2
        return (Point2D(cx - w, cy - h), Point2D(cx + w, cy + h))
        
    else:
        # 默认返回中心点
        return (Point2D(cx, cy), Point2D(cx, cy))

# ==========================================
# 使用示例
# ==========================================

if __name__ == "__main__":
    # 初始化引擎
    engine = DrawingEngine()
    
    try:
        # 1. 创建基础图元：一个圆角矩形板
        plate = engine.create_primitive(
            p_type=PrimitiveType.ROUNDED_RECT,
            id="plate_01",
            x=0, y=0,
            height=5.0,
            width=100, height_2d=50, corner_radius=5
        )
        
        # 2. 创建减去部分：一个圆柱孔
        hole = engine.create_primitive(
            p_type=PrimitiveType.CIRCLE,
            id="hole_01",
            x=0, y=0,
            height=10.0, # 孔的高度大于板，确保穿透
            radius=10
        )
        
        # 3. 构建CSG树：板 - 孔
        # 场景：带孔的板
        csg_tree = engine.build_csg_tree(
            operation=BooleanOperation.DIFFERENCE,
            left=plate,
            right=hole
        )
        
        engine.root = csg_tree
        
        # 4. 实时参数修改演示
        print("\n--- 修改前 ---")
        print(f"孔半径: {hole.params['radius']}")
        
        # 将孔的半径从10修改为15（非破坏性修改）
        engine.update_primitive_param("hole_01", "radius", 15)
        
        print("\n--- 修改后 ---")
        print(f"孔半径: {hole.params['radius']}")
        
        # 5. 导出数据供前端渲染
        render_data = engine.export_to_render_data()
        print("\n--- 导出渲染数据 (JSON片段) ---")
        print(json.dumps(render_data, indent=2)[:500] + "...")
        
        # 6. 辅助函数测试
        bbox_min, bbox_max = calculate_bounding_box(plate)
        print(f"\n板的包围盒: ({bbox_min.x}, {bbox_min.y}) 到 ({bbox_max.x}, {bbox_max.y})")
        
    except ValueError as e:
        logger.error(f"运行时错误: {e}")
    except Exception as e:
        logger.critical(f"系统崩溃: {e}")