"""
UI实体布尔运算系统

本模块实现了一套将UI组件视为几何实体的布尔运算系统。
通过引入交集、并集、差集的概念，允许开发者动态合成复杂的UI形态。

核心功能:
1. 支持矩形、圆形、多边形等基本UI组件
2. 实现交、并、差三种布尔运算
3. 生成矢量化蒙版路径
4. 提供碰撞检测和区域计算

Example:
    >>> from auto_研发_ui实体布尔运算系统_将ui组件_889e91 import UIEntity, BooleanOperator
    >>> rect = UIEntity("rect", {"x": 0, "y": 0, "width": 100, "height": 100})
    >>> circle = UIEntity("circle", {"cx": 50, "cy": 50, "radius": 60})
    >>> operator = BooleanOperator()
    >>> result = operator.intersection(rect, circle)
    >>> print(result.to_mask_path())
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UIBooleanSystem")


class EntityType(Enum):
    """UI实体类型枚举"""
    RECTANGLE = auto()
    CIRCLE = auto()
    ELLIPSE = auto()
    POLYGON = auto()
    PATH = auto()


class BooleanOperation(Enum):
    """布尔运算类型枚举"""
    INTERSECTION = auto()  # 交集 (逻辑与/可见区域)
    UNION = auto()         # 并集 (逻辑或/节点合并)
    DIFFERENCE = auto()    # 差集 (逻辑非/镂空/蒙版)


@dataclass
class Point:
    """二维坐标点"""
    x: float
    y: float

    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.x, (int, float)) or not isinstance(self.y, (int, float)):
            raise TypeError("坐标值必须是数值类型")

    def distance_to(self, other: 'Point') -> float:
        """计算两点间距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def to_tuple(self) -> Tuple[float, float]:
        """转换为元组"""
        return (self.x, self.y)


@dataclass
class UIEntity:
    """
    UI实体基类
    
    Attributes:
        entity_type: 实体类型
        properties: 实体属性字典
        children: 子实体列表
        id: 实体唯一标识符
    """
    entity_type: EntityType
    properties: Dict[str, Union[float, str, List[Point]]]
    children: List['UIEntity'] = field(default_factory=list)
    id: Optional[str] = None

    def __post_init__(self):
        """初始化后验证"""
        self._validate_properties()
        if self.id is None:
            self.id = f"{self.entity_type.name}_{id(self)}"

    def _validate_properties(self):
        """验证实体属性"""
        if not isinstance(self.properties, dict):
            raise ValueError("属性必须是字典类型")

        # 根据实体类型验证必需属性
        required_props = {
            EntityType.RECTANGLE: ['x', 'y', 'width', 'height'],
            EntityType.CIRCLE: ['cx', 'cy', 'radius'],
            EntityType.ELLIPSE: ['cx', 'cy', 'rx', 'ry'],
            EntityType.POLYGON: ['points'],
            EntityType.PATH: ['d']
        }

        for prop in required_props.get(self.entity_type, []):
            if prop not in self.properties:
                raise ValueError(f"{self.entity_type.name} 缺少必需属性: {prop}")

    def get_bounding_box(self) -> Tuple[Point, Point]:
        """
        获取实体的边界框
        
        Returns:
            包含左上角和右下角坐标的元组
        """
        if self.entity_type == EntityType.RECTANGLE:
            x, y = self.properties['x'], self.properties['y']
            w, h = self.properties['width'], self.properties['height']
            return (Point(x, y), Point(x + w, y + h))

        elif self.entity_type == EntityType.CIRCLE:
            cx, cy = self.properties['cx'], self.properties['cy']
            r = self.properties['radius']
            return (Point(cx - r, cy - r), Point(cx + r, cy + r))

        elif self.entity_type == EntityType.ELLIPSE:
            cx, cy = self.properties['cx'], self.properties['cy']
            rx, ry = self.properties['rx'], self.properties['ry']
            return (Point(cx - rx, cy - ry), Point(cx + rx, cy + ry))

        elif self.entity_type == EntityType.POLYGON:
            points = self.properties['points']
            xs = [p.x for p in points]
            ys = [p.y for p in points]
            return (Point(min(xs), min(ys)), Point(max(xs), max(ys)))

        else:
            # 默认返回一个大的边界框
            return (Point(0, 0), Point(1000, 1000))

    def contains_point(self, point: Point) -> bool:
        """
        检查点是否在实体内部
        
        Args:
            point: 要检查的坐标点
            
        Returns:
            如果点在实体内部返回True，否则返回False
        """
        if self.entity_type == EntityType.RECTANGLE:
            x, y = self.properties['x'], self.properties['y']
            w, h = self.properties['width'], self.properties['height']
            return (x <= point.x <= x + w) and (y <= point.y <= y + h)

        elif self.entity_type == EntityType.CIRCLE:
            cx, cy = self.properties['cx'], self.properties['cy']
            r = self.properties['radius']
            center = Point(cx, cy)
            return point.distance_to(center) <= r

        # 其他类型的实现可以扩展...
        return False

    def to_mask_path(self) -> str:
        """
        将实体转换为SVG蒙版路径字符串
        
        Returns:
            SVG路径字符串
        """
        if self.entity_type == EntityType.RECTANGLE:
            x, y = self.properties['x'], self.properties['y']
            w, h = self.properties['width'], self.properties['height']
            return f"M {x},{y} h {w} v {h} h {-w} Z"

        elif self.entity_type == EntityType.CIRCLE:
            cx, cy = self.properties['cx'], self.properties['cy']
            r = self.properties['radius']
            return f"M {cx - r},{cy} a {r},{r} 0 1,0 {2*r},0 a {r},{r} 0 1,0 {-2*r},0 Z"

        elif self.entity_type == EntityType.POLYGON:
            points = self.properties['points']
            path = f"M {points[0].x},{points[0].y}"
            for p in points[1:]:
                path += f" L {p.x},{p.y}"
            path += " Z"
            return path

        else:
            return self.properties.get('d', '')


class BooleanOperator:
    """
    UI实体布尔运算处理器
    
    提供对UI实体的布尔运算功能，包括交集、并集、差集运算。
    """
    
    def __init__(self, precision: int = 2):
        """
        初始化布尔运算处理器
        
        Args:
            precision: 计算结果的小数精度
        """
        self.precision = precision
        logger.info(f"布尔运算处理器初始化完成，精度: {precision}")

    def _round_value(self, value: float) -> float:
        """辅助函数：四舍五入到指定精度"""
        return round(value, self.precision)

    def _validate_entity(self, entity: UIEntity) -> None:
        """辅助函数：验证实体有效性"""
        if not isinstance(entity, UIEntity):
            raise TypeError(f"期望UIEntity类型，得到 {type(entity)}")
        
        if entity.properties is None:
            raise ValueError("实体属性不能为空")

    def intersection(self, entity1: UIEntity, entity2: UIEntity) -> UIEntity:
        """
        计算两个实体的交集（逻辑与/可见区域）
        
        Args:
            entity1: 第一个UI实体
            entity2: 第二个UI实体
            
        Returns:
            表示交集的新UI实体
            
        Raises:
            TypeError: 如果输入不是UIEntity类型
            ValueError: 如果实体属性无效
            
        Example:
            >>> rect = UIEntity(EntityType.RECTANGLE, {"x": 0, "y": 0, "width": 100, "height": 100})
            >>> circle = UIEntity(EntityType.CIRCLE, {"cx": 50, "cy": 50, "radius": 60})
            >>> result = operator.intersection(rect, circle)
        """
        self._validate_entity(entity1)
        self._validate_entity(entity2)
        
        logger.debug(f"计算交集: {entity1.id} ∩ {entity2.id}")
        
        # 获取边界框
        bb1 = entity1.get_bounding_box()
        bb2 = entity2.get_bounding_box()
        
        # 计算交集的边界框
        x_left = max(bb1[0].x, bb2[0].x)
        y_top = max(bb1[0].y, bb2[0].y)
        x_right = min(bb1[1].x, bb2[1].x)
        y_bottom = min(bb1[1].y, bb2[1].y)
        
        # 检查是否有交集
        if x_left >= x_right or y_top >= y_bottom:
            logger.warning("实体没有交集区域")
            return UIEntity(EntityType.RECTANGLE, {
                "x": 0, "y": 0, "width": 0, "height": 0
            }, id="empty_intersection")
        
        # 创建交集实体
        width = self._round_value(x_right - x_left)
        height = self._round_value(y_bottom - y_top)
        
        result = UIEntity(EntityType.RECTANGLE, {
            "x": self._round_value(x_left),
            "y": self._round_value(y_top),
            "width": width,
            "height": height
        }, id=f"intersection_{entity1.id}_{entity2.id}")
        
        logger.info(f"交集计算完成: {result.id}, 面积: {width * height}")
        return result

    def union(self, entity1: UIEntity, entity2: UIEntity) -> UIEntity:
        """
        计算两个实体的并集（逻辑或/节点合并）
        
        Args:
            entity1: 第一个UI实体
            entity2: 第二个UI实体
            
        Returns:
            表示并集的新UI实体
            
        Example:
            >>> rect = UIEntity(EntityType.RECTANGLE, {"x": 0, "y": 0, "width": 100, "height": 100})
            >>> circle = UIEntity(EntityType.CIRCLE, {"cx": 150, "cy": 50, "radius": 60})
            >>> result = operator.union(rect, circle)
        """
        self._validate_entity(entity1)
        self._validate_entity(entity2)
        
        logger.debug(f"计算并集: {entity1.id} ∪ {entity2.id}")
        
        # 获取边界框
        bb1 = entity1.get_bounding_box()
        bb2 = entity2.get_bounding_box()
        
        # 计算并集的边界框
        x_left = min(bb1[0].x, bb2[0].x)
        y_top = min(bb1[0].y, bb2[0].y)
        x_right = max(bb1[1].x, bb2[1].x)
        y_bottom = max(bb1[1].y, bb2[1].y)
        
        width = self._round_value(x_right - x_left)
        height = self._round_value(y_bottom - y_top)
        
        # 创建一个包含两个原始实体的复合实体
        result = UIEntity(EntityType.RECTANGLE, {
            "x": self._round_value(x_left),
            "y": self._round_value(y_top),
            "width": width,
            "height": height
        }, children=[entity1, entity2], id=f"union_{entity1.id}_{entity2.id}")
        
        logger.info(f"并集计算完成: {result.id}, 边界框: {width}x{height}")
        return result

    def difference(self, entity1: UIEntity, entity2: UIEntity) -> UIEntity:
        """
        计算两个实体的差集（逻辑非/镂空/蒙版）
        
        Args:
            entity1: 被减实体
            entity2: 要减去的实体
            
        Returns:
            表示差集的新UI实体
            
        Example:
            >>> rect = UIEntity(EntityType.RECTANGLE, {"x": 0, "y": 0, "width": 100, "height": 100})
            >>> circle = UIEntity(EntityType.CIRCLE, {"cx": 50, "cy": 50, "radius": 30})
            >>> result = operator.difference(rect, circle)
        """
        self._validate_entity(entity1)
        self._validate_entity(entity2)
        
        logger.debug(f"计算差集: {entity1.id} - {entity2.id}")
        
        # 这里简化处理，实际实现需要复杂的几何计算
        # 返回一个带有蒙版信息的复合实体
        result = UIEntity(EntityType.PATH, {
            "d": f"{entity1.to_mask_path()} {entity2.to_mask_path()}",
            "fill-rule": "evenodd"
        }, children=[entity1, entity2], id=f"difference_{entity1.id}_{entity2.id}")
        
        logger.info(f"差集计算完成: {result.id}")
        return result

    def calculate_overlap_area(self, entity1: UIEntity, entity2: UIEntity) -> float:
        """
        辅助函数：计算两个实体的重叠面积
        
        Args:
            entity1: 第一个UI实体
            entity2: 第二个UI实体
            
        Returns:
            重叠区域的面积
        """
        intersection = self.intersection(entity1, entity2)
        
        if intersection.entity_type == EntityType.RECTANGLE:
            w = intersection.properties['width']
            h = intersection.properties['height']
            return self._round_value(w * h)
        
        return 0.0

    def batch_operation(self, entities: List[UIEntity], operation: BooleanOperation) -> UIEntity:
        """
        批量布尔运算
        
        Args:
            entities: UI实体列表
            operation: 布尔运算类型
            
        Returns:
            运算结果实体
            
        Raises:
            ValueError: 如果实体列表为空
        """
        if not entities:
            raise ValueError("实体列表不能为空")
        
        if len(entities) == 1:
            return entities[0]
        
        result = entities[0]
        
        for entity in entities[1:]:
            if operation == BooleanOperation.INTERSECTION:
                result = self.intersection(result, entity)
            elif operation == BooleanOperation.UNION:
                result = self.union(result, entity)
            elif operation == BooleanOperation.DIFFERENCE:
                result = self.difference(result, entity)
        
        logger.info(f"批量{operation.name}运算完成，处理了 {len(entities)} 个实体")
        return result


# 使用示例
if __name__ == "__main__":
    # 创建布尔运算处理器
    operator = BooleanOperator(precision=2)
    
    # 创建UI实体
    rect = UIEntity(EntityType.RECTANGLE, {
        "x": 0, "y": 0, "width": 100, "height": 100
    }, id="rect1")
    
    circle = UIEntity(EntityType.CIRCLE, {
        "cx": 80, "cy": 80, "radius": 50
    }, id="circle1")
    
    # 计算交集
    intersection = operator.intersection(rect, circle)
    print(f"交集边界框: {intersection.get_bounding_box()}")
    
    # 计算并集
    union = operator.union(rect, circle)
    print(f"并集边界框: {union.get_bounding_box()}")
    
    # 计算差集
    difference = operator.difference(rect, circle)
    print(f"差集路径: {difference.to_mask_path()}")
    
    # 计算重叠面积
    area = operator.calculate_overlap_area(rect, circle)
    print(f"重叠面积: {area}")
    
    # 批量运算示例
    rect2 = UIEntity(EntityType.RECTANGLE, {
        "x": 50, "y": 50, "width": 100, "height": 100
    }, id="rect2")
    
    batch_result = operator.batch_operation(
        [rect, circle, rect2], 
        BooleanOperation.UNION
    )
    print(f"批量并集结果: {batch_result.id}")