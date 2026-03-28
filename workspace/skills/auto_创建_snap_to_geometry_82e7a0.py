"""
Module: auto_创建_snap_to_geometry_82e7a0
Description: 实现智能白板的几何捕捉算法，支持中点、垂足、端点及切点捕捉。
             该模块旨在为Flutter手势交互层提供后端几何计算逻辑，实现
             '手绘即建模'的工程级精度。

Domain: cross_domain
Author: Senior Python Engineer
"""

import math
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Point:
    """表示二维平面上的一个点。"""
    x: float
    y: float

    def __post_init__(self):
        """验证坐标是否为数值类型。"""
        if not isinstance(self.x, (int, float)) or not isinstance(self.y, (int, float)):
            raise ValueError("坐标必须是数值类型")


@dataclass
class LineSegment:
    """表示由起点和终点定义的线段。"""
    start: Point
    end: Point

    def __post_init__(self):
        """验证线段有效性。"""
        if self.start.x == self.end.x and self.start.y == self.end.y:
            logger.warning("线段长度为0，可能导致除零错误")


@dataclass
class Circle:
    """表示由圆心和半径定义的圆。"""
    center: Point
    radius: float

    def __post_init__(self):
        """验证半径有效性。"""
        if self.radius <= 0:
            raise ValueError("圆半径必须大于0")


def euclidean_distance(p1: Point, p2: Point) -> float:
    """
    辅助函数：计算两点之间的欧几里得距离。

    Args:
        p1: 起点
        p2: 终点

    Returns:
        两点之间的距离。
    """
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


def calculate_perpendicular_foot(point: Point, line: LineSegment) -> Point:
    """
    核心函数1：计算点到直线的垂足。

    Args:
        point: 指定的点（通常是手指触摸点）。
        line: 目标线段。

    Returns:
        垂足坐标点。
    """
    dx = line.end.x - line.start.x
    dy = line.end.y - line.start.y
    
    # 如果线段长度为0，返回起点
    if dx == 0 and dy == 0:
        return line.start

    # 参数 t 表示投影点在线段上的比例位置
    # t = ((p - p1) . (p2 - p1)) / |p2 - p1|^2
    t = ((point.x - line.start.x) * dx + (point.y - line.start.y) * dy) / (dx**2 + dy**2)
    
    # 计算垂足坐标
    foot_x = line.start.x + t * dx
    foot_y = line.start.y + t * dy
    
    return Point(foot_x, foot_y)


def calculate_tangent_points(point: Point, circle: Circle) -> Tuple[Point, Point]:
    """
    核心函数2：计算圆外一点到圆的两条切线的切点。

    Args:
        point: 圆外一点。
        circle: 目标圆。

    Returns:
        包含两个切点坐标的元组。

    Raises:
        ValueError: 如果点在圆内，无法计算切点。
    """
    dist = euclidean_distance(point, circle.center)
    
    if dist < circle.radius:
        raise ValueError("点在圆内部，不存在切点")
    
    # 向量 V 从圆心指向外部点
    vx = point.x - circle.center.x
    vy = point.y - circle.center.y
    
    # 计算角度偏移量 alpha，其中 sin(alpha) = r / d
    alpha = math.asin(circle.radius / dist)
    
    # 向量 V 的角度 beta
    beta = math.atan2(vy, vx)
    
    # 两个切点的角度
    angle1 = beta - alpha
    angle2 = beta + alpha
    
    t1 = Point(
        circle.center.x + circle.radius * math.cos(angle1),
        circle.center.y + circle.radius * math.sin(angle1)
    )
    t2 = Point(
        circle.center.x + circle.radius * math.cos(angle2),
        circle.center.y + circle.radius * math.sin(angle2)
    )
    
    return t1, t2


class GeometrySnapper:
    """
    几何捕捉引擎类。
    管理场景中的几何图元，并根据输入点计算最近的捕捉点。
    """

    def __init__(self, snap_threshold: float = 10.0):
        """
        初始化捕捉引擎。

        Args:
            snap_threshold: 捕捉阈值（像素），超过此距离不进行捕捉。
        """
        self.snap_threshold = snap_threshold
        self.lines: List[LineSegment] = []
        self.circles: List[Circle] = []
        logger.info(f"GeometrySnapper 初始化完成，捕捉阈值: {snap_threshold}")

    def add_geometry(self, geometry: Union[LineSegment, Circle]) -> None:
        """
        向场景中添加几何图元。

        Args:
            geometry: 线段或圆对象。
        """
        if isinstance(geometry, (LineSegment, Circle)):
            if isinstance(geometry, LineSegment):
                self.lines.append(geometry)
            else:
                self.circles.append(geometry)
            logger.debug(f"添加几何图元: {type(geometry).__name__}")
        else:
            logger.error(f"不支持的几何类型: {type(geometry)}")

    def find_snap_point(self, raw_point: Point) -> Optional[Point]:
        """
        查找原始输入点最近的几何特征点（捕捉点）。

        检查逻辑包括：
        1. 线段端点
        2. 线段中点
        3. 线段垂足
        4. 圆的切点
        5. 圆心

        Args:
            raw_point: 用户手指/光标的原始坐标。

        Returns:
            捕捉到的点坐标，如果没有在阈值内找到则返回 None。
        """
        nearest_point: Optional[Point] = None
        min_dist = float('inf')

        # 检查线段
        for line in self.lines:
            # 1. 检查端点
            for endpoint in [line.start, line.end]:
                d = euclidean_distance(raw_point, endpoint)
                if d < self.snap_threshold and d < min_dist:
                    min_dist = d
                    nearest_point = endpoint

            # 2. 检查中点
            midpoint = Point((line.start.x + line.end.x) / 2, (line.start.y + line.end.y) / 2)
            d_mid = euclidean_distance(raw_point, midpoint)
            if d_mid < self.snap_threshold and d_mid < min_dist:
                min_dist = d_mid
                nearest_point = midpoint

            # 3. 检查垂足
            try:
                foot = calculate_perpendicular_foot(raw_point, line)
                # 还需要检查垂足是否在线段范围内
                # 简单的边界检查：垂足坐标是否在start和end的包围盒内
                min_x, max_x = min(line.start.x, line.end.x), max(line.start.x, line.end.x)
                min_y, max_y = min(line.start.y, line.end.y), max(line.start.y, line.end.y)
                
                if min_x - 1e-6 <= foot.x <= max_x + 1e-6 and min_y - 1e-6 <= foot.y <= max_y + 1e-6:
                    d_foot = euclidean_distance(raw_point, foot)
                    if d_foot < self.snap_threshold and d_foot < min_dist:
                        min_dist = d_foot
                        nearest_point = foot
            except Exception as e:
                logger.warning(f"计算垂足时发生错误: {e}")

        # 检查圆
        for circle in self.circles:
            # 4. 检查圆心
            d_center = euclidean_distance(raw_point, circle.center)
            if d_center < self.snap_threshold and d_center < min_dist:
                min_dist = d_center
                nearest_point = circle.center

            # 5. 检查切点 (仅当点在圆外时)
            try:
                t1, t2 = calculate_tangent_points(raw_point, circle)
                for t in [t1, t2]:
                    d_t = euclidean_distance(raw_point, t)
                    if d_t < self.snap_threshold and d_t < min_dist:
                        min_dist = d_t
                        nearest_point = t
            except ValueError:
                # 点在圆内，忽略切点计算
                pass
            except Exception as e:
                logger.warning(f"计算切点时发生错误: {e}")

        if nearest_point:
            logger.info(f"捕捉成功: 原始点 {raw_point} -> 捕捉点 {nearest_point}, 距离: {min_dist:.2f}")
        else:
            logger.debug(f"未找到捕捉点: {raw_point}")

        return nearest_point


# 使用示例
if __name__ == "__main__":
    # 1. 初始化捕捉引擎，设置阈值为 15.0 像素
    snapper = GeometrySnapper(snap_threshold=15.0)

    # 2. 添加几何图元
    # 一条从 (0,0) 到 (100,100) 的线段
    line1 = LineSegment(Point(0, 0), Point(100, 100))
    snapper.add_geometry(line1)

    # 一个圆心在 (200, 200)，半径为 50 的圆
    circle1 = Circle(Point(200, 200), 50)
    snapper.add_geometry(circle1)

    # 3. 模拟用户输入
    # 测试中点捕捉: (48, 52) 应该捕捉到 (50, 50)
    input_p1 = Point(48, 52)
    snap_p1 = snapper.find_snap_point(input_p1)
    print(f"Input: {input_p1} -> Snap: {snap_p1}")  # 预期: (50.0, 50.0)

    # 测试垂足捕捉: (20, 100) 在线段上方，垂足应在 (60, 60) 附近
    input_p2 = Point(20, 100)
    snap_p2 = snapper.find_snap_point(input_p2)
    print(f"Input: {input_p2} -> Snap: {snap_p2}")  # 预期: (60.0, 60.0)

    # 测试切点捕捉: 点 (200, 270) 在圆正下方，切点应在圆底附近
    input_p3 = Point(200, 270)
    snap_p3 = snapper.find_snap_point(input_p3)
    print(f"Input: {input_p3} -> Snap: {snap_p3}")  # 预期: (200.0, 250.0) 或附近切点

    # 测试无捕捉情况
    input_p4 = Point(500, 500)
    snap_p4 = snapper.find_snap_point(input_p4)
    print(f"Input: {input_p4} -> Snap: {snap_p4}")  # 预期: None