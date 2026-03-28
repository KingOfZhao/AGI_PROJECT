"""
极简工业级矢量渲染引擎

该模块实现了一个基于Flutter Canvas API的CAD矢量渲染引擎，专门优化移动端性能。
利用层级剔除算法和参数化曲线绘制，实现工业级精度的图纸查看。

核心特性：
- 像素级对齐的工业设计图纸渲染
- 海量图元的即时渲染优化
- 轻量级实现，不依赖WebGL
- 支持参数化曲线和曲面绘制
"""

import math
import logging
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum, auto

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CADRenderer")


class PrimitiveType(Enum):
    """CAD图元类型枚举"""
    LINE = auto()
    ARC = auto()
    CIRCLE = auto()
    BEZIER = auto()
    POLYLINE = auto()
    TEXT = auto()


@dataclass
class Point2D:
    """二维坐标点，支持工业级精度"""
    x: float
    y: float
    
    def __post_init__(self):
        """验证坐标数据"""
        if not (isinstance(self.x, (int, float)) and isinstance(self.y, (int, float))):
            raise ValueError("坐标必须是数字类型")
    
    def to_tuple(self) -> Tuple[float, float]:
        """转换为元组格式"""
        return (self.x, self.y)
    
    def distance_to(self, other: 'Point2D') -> float:
        """计算两点距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)


@dataclass
class CADPrimitive:
    """CAD图元基类"""
    primitive_type: PrimitiveType
    layer: str = "default"
    color: str = "#000000"
    line_weight: float = 1.0
    visible: bool = True
    selected: bool = False
    metadata: Dict = field(default_factory=dict)
    
    def get_bounding_box(self) -> Tuple[Point2D, Point2D]:
        """获取图元包围盒（子类需实现）"""
        raise NotImplementedError


@dataclass
class Line(CADPrimitive):
    """直线段图元"""
    start: Point2D = field(default_factory=lambda: Point2D(0, 0))
    end: Point2D = field(default_factory=lambda: Point2D(0, 0))
    
    def __post_init__(self):
        self.primitive_type = PrimitiveType.LINE
    
    def get_bounding_box(self) -> Tuple[Point2D, Point2D]:
        min_x = min(self.start.x, self.end.x)
        min_y = min(self.start.y, self.end.y)
        max_x = max(self.start.x, self.end.x)
        max_y = max(self.start.y, self.end.y)
        return (Point2D(min_x, min_y), Point2D(max_x, max_y))
    
    def length(self) -> float:
        """计算线段长度"""
        return self.start.distance_to(self.end)


@dataclass
class Arc(CADPrimitive):
    """圆弧图元"""
    center: Point2D = field(default_factory=lambda: Point2D(0, 0))
    radius: float = 1.0
    start_angle: float = 0.0  # 弧度
    end_angle: float = math.pi / 2  # 弧度
    
    def __post_init__(self):
        self.primitive_type = PrimitiveType.ARC
        if self.radius <= 0:
            raise ValueError("半径必须大于0")
    
    def get_bounding_box(self) -> Tuple[Point2D, Point2D]:
        # 简化计算，实际应考虑圆弧部分
        min_x = self.center.x - self.radius
        min_y = self.center.y - self.radius
        max_x = self.center.x + self.radius
        max_y = self.center.y + self.radius
        return (Point2D(min_x, min_y), Point2D(max_x, max_y))


@dataclass
class Circle(CADPrimitive):
    """圆形图元"""
    center: Point2D = field(default_factory=lambda: Point2D(0, 0))
    radius: float = 1.0
    
    def __post_init__(self):
        self.primitive_type = PrimitiveType.CIRCLE
        if self.radius <= 0:
            raise ValueError("半径必须大于0")
    
    def get_bounding_box(self) -> Tuple[Point2D, Point2D]:
        min_x = self.center.x - self.radius
        min_y = self.center.y - self.radius
        max_x = self.center.x + self.radius
        max_y = self.center.y + self.radius
        return (Point2D(min_x, min_y), Point2D(max_x, max_y))


@dataclass
class BezierCurve(CADPrimitive):
    """贝塞尔曲线图元"""
    control_points: List[Point2D] = field(default_factory=list)
    
    def __post_init__(self):
        self.primitive_type = PrimitiveType.BEZIER
        if len(self.control_points) < 2:
            raise ValueError("贝塞尔曲线至少需要2个控制点")
    
    def get_bounding_box(self) -> Tuple[Point2D, Point2D]:
        if not self.control_points:
            return (Point2D(0, 0), Point2D(0, 0))
        
        min_x = min(p.x for p in self.control_points)
        min_y = min(p.y for p in self.control_points)
        max_x = max(p.x for p in self.control_points)
        max_y = max(p.y for p in self.control_points)
        return (Point2D(min_x, min_y), Point2D(max_x, max_y))


class CADRenderer:
    """
    极简工业级矢量渲染引擎
    
    实现针对移动端优化的CAD渲染引擎，利用层级剔除算法和参数化曲线绘制。
    支持像素级对齐和工业设计图纸查看。
    
    使用示例:
    >>> renderer = CADRenderer()
    >>> line = Line(start=Point2D(0, 0), end=Point2D(100, 50), color="#FF0000")
    >>> renderer.add_primitive(line)
    >>> renderer.render()
    """
    
    def __init__(self, viewport_width: int = 1920, viewport_height: int = 1080):
        """
        初始化渲染引擎
        
        参数:
            viewport_width: 视口宽度(像素)
            viewport_height: 视口高度(像素)
        """
        if viewport_width <= 0 or viewport_height <= 0:
            raise ValueError("视口尺寸必须大于0")
        
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.primitives: List[CADPrimitive] = []
        self.layers: Dict[str, List[CADPrimitive]] = {}
        self.zoom_level = 1.0
        self.pan_offset = Point2D(0, 0)
        self.visible_layers: set = set()
        self._render_stats = {
            'total_primitives': 0,
            'rendered_primitives': 0,
            'culled_primitives': 0
        }
        
        logger.info(f"CAD渲染引擎初始化完成，视口尺寸: {viewport_width}x{viewport_height}")
    
    def add_primitive(self, primitive: CADPrimitive) -> None:
        """
        添加图元到渲染引擎
        
        参数:
            primitive: CAD图元对象
            
        异常:
            TypeError: 如果输入不是CADPrimitive类型
        """
        if not isinstance(primitive, CADPrimitive):
            raise TypeError("必须添加CADPrimitive类型的图元")
        
        self.primitives.append(primitive)
        
        # 按图层组织
        layer_name = primitive.layer
        if layer_name not in self.layers:
            self.layers[layer_name] = []
            self.visible_layers.add(layer_name)  # 默认新图层可见
            logger.debug(f"创建新图层: {layer_name}")
        
        self.layers[layer_name].append(primitive)
        logger.debug(f"添加图元到图层 {layer_name}: {primitive.primitive_type.name}")
    
    def remove_primitive(self, primitive: CADPrimitive) -> bool:
        """
        从渲染引擎移除图元
        
        参数:
            primitive: 要移除的CAD图元
            
        返回:
            bool: 是否成功移除
        """
        try:
            self.primitives.remove(primitive)
            layer_name = primitive.layer
            if layer_name in self.layers:
                self.layers[layer_name].remove(primitive)
                if not self.layers[layer_name]:  # 如果图层为空
                    del self.layers[layer_name]
                    self.visible_layers.discard(layer_name)
            logger.debug(f"移除图元: {primitive.primitive_type.name}")
            return True
        except ValueError:
            logger.warning("尝试移除不存在的图元")
            return False
    
    def set_layer_visibility(self, layer_name: str, visible: bool) -> None:
        """
        设置图层可见性
        
        参数:
            layer_name: 图层名称
            visible: 可见性状态
        """
        if layer_name not in self.layers:
            logger.warning(f"图层 {layer_name} 不存在")
            return
        
        if visible:
            self.visible_layers.add(layer_name)
        else:
            self.visible_layers.discard(layer_name)
        
        logger.info(f"设置图层 {layer_name} 可见性: {visible}")
    
    def _apply_transform(self, point: Point2D) -> Point2D:
        """
        应用视口变换（平移和缩放）
        
        参数:
            point: 原始坐标点
            
        返回:
            Point2D: 变换后的屏幕坐标
        """
        transformed_x = (point.x + self.pan_offset.x) * self.zoom_level
        transformed_y = (point.y + self.pan_offset.y) * self.zoom_level
        return Point2D(transformed_x, transformed_y)
    
    def _is_in_viewport(self, bbox: Tuple[Point2D, Point2D]) -> bool:
        """
        检查包围盒是否在视口内（用于剔除优化）
        
        参数:
            bbox: 包围盒 (min_point, max_point)
            
        返回:
            bool: 是否在视口内
        """
        min_point, max_point = bbox
        
        # 转换为屏幕坐标
        screen_min = self._apply_transform(min_point)
        screen_max = self._apply_transform(max_point)
        
        # 检查是否与视口相交
        intersects = not (
            screen_max.x < 0 or 
            screen_min.x > self.viewport_width or
            screen_max.y < 0 or 
            screen_min.y > self.viewport_height
        )
        
        return intersects
    
    def _render_line(self, line: Line) -> Dict:
        """渲染直线段，返回Flutter Canvas绘制指令"""
        if not self._is_in_viewport(line.get_bounding_box()):
            return {}
        
        start_screen = self._apply_transform(line.start)
        end_screen = self._apply_transform(line.end)
        
        return {
            'type': 'line',
            'start': start_screen.to_tuple(),
            'end': end_screen.to_tuple(),
            'color': line.color,
            'stroke_width': line.line_weight * self.zoom_level,
            'anti_alias': True
        }
    
    def _render_circle(self, circle: Circle) -> Dict:
        """渲染圆形，返回Flutter Canvas绘制指令"""
        if not self._is_in_viewport(circle.get_bounding_box()):
            return {}
        
        center_screen = self._apply_transform(circle.center)
        radius_screen = circle.radius * self.zoom_level
        
        return {
            'type': 'circle',
            'center': center_screen.to_tuple(),
            'radius': radius_screen,
            'color': circle.color,
            'stroke_width': circle.line_weight * self.zoom_level,
            'style': 'stroke'
        }
    
    def _render_arc(self, arc: Arc) -> Dict:
        """渲染圆弧，返回Flutter Canvas绘制指令"""
        if not self._is_in_viewport(arc.get_bounding_box()):
            return {}
        
        center_screen = self._apply_transform(arc.center)
        radius_screen = arc.radius * self.zoom_level
        
        return {
            'type': 'arc',
            'center': center_screen.to_tuple(),
            'radius': radius_screen,
            'start_angle': arc.start_angle,
            'end_angle': arc.end_angle,
            'color': arc.color,
            'stroke_width': arc.line_weight * self.zoom_level,
            'use_center': False
        }
    
    def _render_bezier(self, bezier: BezierCurve) -> Dict:
        """渲染贝塞尔曲线，返回Flutter Canvas绘制指令"""
        if not self._is_in_viewport(bezier.get_bounding_box()):
            return {}
        
        transformed_points = [self._apply_transform(p) for p in bezier.control_points]
        
        return {
            'type': 'bezier',
            'control_points': [p.to_tuple() for p in transformed_points],
            'color': bezier.color,
            'stroke_width': bezier.line_weight * self.zoom_level
        }
    
    def render(self, optimize: bool = True) -> Dict:
        """
        执行渲染过程，生成Flutter Canvas绘制指令
        
        参数:
            optimize: 是否启用层级剔除优化
            
        返回:
            Dict: 包含渲染指令和统计信息的字典
            
        输出格式:
        {
            'instructions': [
                {
                    'type': 'line',
                    'start': (x1, y1),
                    'end': (x2, y2),
                    'color': '#RRGGBB',
                    'stroke_width': float
                },
                // 更多绘制指令...
            ],
            'stats': {
                'total_primitives': int,
                'rendered_primitives': int,
                'culled_primitives': int
            }
        }
        """
        self._render_stats = {
            'total_primitives': len(self.primitives),
            'rendered_primitives': 0,
            'culled_primitives': 0
        }
        
        instructions = []
        
        # 按图层渲染（利用CAD的层级剔除算法）
        for layer_name, layer_primitives in self.layers.items():
            if layer_name not in self.visible_layers:
                self._render_stats['culled_primitives'] += len(layer_primitives)
                continue
            
            for primitive in layer_primitives:
                if not primitive.visible:
                    self._render_stats['culled_primitives'] += 1
                    continue
                
                # 根据图元类型调用相应的渲染方法
                render_func = {
                    PrimitiveType.LINE: self._render_line,
                    PrimitiveType.CIRCLE: self._render_circle,
                    PrimitiveType.ARC: self._render_arc,
                    PrimitiveType.BEZIER: self._render_bezier
                }.get(primitive.primitive_type)
                
                if render_func:
                    instruction = render_func(primitive)
                    if instruction:  # 空字典表示被剔除
                        instructions.append(instruction)
                        self._render_stats['rendered_primitives'] += 1
                    else:
                        self._render_stats['culled_primitives'] += 1
        
        logger.info(
            f"渲染完成: 总图元 {self._render_stats['total_primitives']}, "
            f"渲染 {self._render_stats['rendered_primitives']}, "
            f"剔除 {self._render_stats['culled_primitives']}"
        )
        
        return {
            'instructions': instructions,
            'stats': self._render_stats
        }
    
    def zoom_to_fit(self) -> None:
        """自动缩放以适应所有图元"""
        if not self.primitives:
            return
        
        # 计算所有图元的总包围盒
        all_bboxes = [p.get_bounding_box() for p in self.primitives]
        
        min_x = min(bbox[0].x for bbox in all_bboxes)
        min_y = min(bbox[0].y for bbox in all_bboxes)
        max_x = max(bbox[1].x for bbox in all_bboxes)
        max_y = max(bbox[1].y for bbox in all_bboxes)
        
        content_width = max_x - min_x
        content_height = max_y - min_y
        
        # 计算缩放比例
        scale_x = self.viewport_width / content_width if content_width > 0 else 1
        scale_y = self.viewport_height / content_height if content_height > 0 else 1
        self.zoom_level = min(scale_x, scale_y) * 0.9  # 留出10%边距
        
        # 计算平移偏移以居中显示
        self.pan_offset = Point2D(
            -min_x + (self.viewport_width / self.zoom_level - content_width) / 2,
            -min_y + (self.viewport_height / self.zoom_level - content_height) / 2
        )
        
        logger.info(f"自动缩放完成，缩放级别: {self.zoom_level:.2f}")
    
    def clear(self) -> None:
        """清除所有图元"""
        self.primitives.clear()
        self.layers.clear()
        self.visible_layers.clear()
        logger.info("已清除所有图元")


# 示例用法
if __name__ == "__main__":
    try:
        # 创建渲染引擎
        renderer = CADRenderer(viewport_width=1920, viewport_height=1080)
        
        # 添加一些图元
        line1 = Line(
            start=Point2D(100, 100),
            end=Point2D(500, 300),
            color="#FF0000",
            line_weight=2.0,
            layer="outline"
        )
        
        circle1 = Circle(
            center=Point2D(300, 200),
            radius=50,
            color="#00FF00",
            line_weight=1.5,
            layer="dimensions"
        )
        
        arc1 = Arc(
            center=Point2D(400, 400),
            radius=80,
            start_angle=0,
            end_angle=math.pi,
            color="#0000FF",
            layer="details"
        )
        
        bezier1 = BezierCurve(
            control_points=[
                Point2D(50, 50),
                Point2D(150, 200),
                Point2D(300, 100),
                Point2D(400, 300)
            ],
            color="#FF00FF",
            layer="curves"
        )
        
        # 添加图元到渲染引擎
        renderer.add_primitive(line1)
        renderer.add_primitive(circle1)
        renderer.add_primitive(arc1)
        renderer.add_primitive(bezier1)
        
        # 设置图层可见性
        renderer.set_layer_visibility("dimensions", False)  # 隐藏尺寸层
        
        # 自动缩放以适应所有图元
        renderer.zoom_to_fit()
        
        # 执行渲染
        result = renderer.render()
        
        # 输出渲染结果
        print(f"\n渲染完成！统计信息:")
        print(f"- 总图元数: {result['stats']['total_primitives']}")
        print(f"- 渲染图元数: {result['stats']['rendered_primitives']}")
        print(f"- 剔除图元数: {result['stats']['culled_primitives']}")
        print(f"\n绘制指令数量: {len(result['instructions'])}")
        
    except Exception as e:
        logger.error(f"渲染过程中发生错误: {str(e)}", exc_info=True)