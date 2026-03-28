"""
名称: auto_智能手势驱动的参数化草图生成器_将flu_9948f8
描述: 智能手势驱动的参数化草图生成器。将Flutter的手势识别（Velocity, Scale, Drag）直接转化为CAD的几何约束意图。
     利用算法预测用户意图，将随机的'像素涂抹'实时转化为精确的'工程特征'。
作者: AGI System
版本: 1.0.0
"""

import logging
import math
from typing import List, Tuple, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GeometryType(Enum):
    """定义支持的几何约束类型"""
    LINE_HORIZONTAL = "LINE_HORIZONTAL"
    LINE_VERTICAL = "LINE_VERTICAL"
    LINE_ALIGNED = "LINE_ALIGNED"  # 任意角度直线
    CIRCLE = "CIRCLE"
    ARC = "ARC"
    UNKNOWN = "UNKNOWN"

@dataclass
class FlutterGestureData:
    """
    模拟从Flutter端接收的手势数据结构。
    
    Attributes:
        points (List[Tuple[float, float]]): 触摸点的屏幕坐标列表 [(x1, y1), (x2, y2), ...]
        velocity (Tuple[float, float]): 手势结束时的速度向量
        scale (float): 缩放手势比例 (用于判断圆的大小变化)
        duration_ms (int): 手势持续的时间 (毫秒)
    """
    points: List[Tuple[float, float]]
    velocity: Tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0
    duration_ms: int = 0

    def __post_init__(self):
        """数据验证"""
        if not self.points:
            raise ValueError("Points list cannot be empty")
        if len(self.points) < 2:
            raise ValueError("At least two points are required to form a geometry")

@dataclass
class CADConstraintEntity:
    """
    生成的CAD实体结构，包含几何参数和约束信息。
    """
    geometry_type: GeometryType
    start_point: Tuple[float, float]
    end_point: Optional[Tuple[float, float]] = None  # 对于点或圆可能为空或相同
    center: Optional[Tuple[float, float]] = None     # 对于圆/弧
    radius: Optional[float] = None                   # 对于圆/弧
    constraints: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # AI预测的置信度

def _calculate_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    辅助函数：计算两点之间的欧几里得距离。
    
    Args:
        p1: 第一个点的坐标
        p2: 第二个点的坐标
        
    Returns:
        float: 两点间的距离
    """
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def analyze_line_intent(points: List[Tuple[float, float]], velocity: Tuple[float, float]) -> CADConstraintEntity:
    """
    核心函数 1: 分析线条绘制意图。
    根据起点、终点以及手势速度方向，判断应生成水平线、垂直线还是斜线。
    包含“自动吸附”逻辑。
    
    Args:
        points: 坐标点列表
        velocity: 手势速度向量
        
    Returns:
        CADConstraintEntity: 生成的约束实体
        
    Raises:
        ValueError: 如果数据点不足
    """
    if len(points) < 2:
        raise ValueError("Insufficient points for line analysis")

    start_p = points[0]
    end_p = points[-1]
    
    dx = end_p[0] - start_p[0]
    dy = end_p[1] - start_p[1]
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    
    # 定义吸附阈值 (Snap Threshold)
    # 如果角度在 -10 到 10 度之间，认为是水平线
    # 如果角度在 80 到 100 或 -80 到 -100 度之间，认为是垂直线
    snap_threshold = 10.0 
    
    geometry_type = GeometryType.LINE_ALIGNED
    constraints = {}
    confidence = 0.8
    
    # 水平吸附检测
    if abs(angle_deg) < snap_threshold or abs(angle_deg - 180) < snap_threshold or abs(angle_deg + 180) < snap_threshold:
        geometry_type = GeometryType.LINE_HORIZONTAL
        # 吸附操作：保持起点X，强制终点Y等于起点Y
        end_p = (end_p[0], start_p[1])
        constraints["horizontal"] = True
        confidence = 0.95 + (0.05 * (1 - abs(angle_deg)/snap_threshold)) # 角度越直，置信度越高
        logger.info(f"Snapped to Horizontal. Original angle: {angle_deg:.2f}")
        
    # 垂直吸附检测
    elif abs(abs(angle_deg) - 90) < snap_threshold:
        geometry_type = GeometryType.LINE_VERTICAL
        # 吸附操作：保持起点Y，强制终点X等于起点X
        end_p = (start_p[0], end_p[1])
        constraints["vertical"] = True
        confidence = 0.95 + (0.05 * (1 - (abs(abs(angle_deg) - 90)/snap_threshold)))
        logger.info(f"Snapped to Vertical. Original angle: {angle_deg:.2f}")
        
    else:
        logger.info(f"Line remains Aligned. Angle: {angle_deg:.2f}")
        constraints["angle"] = angle_deg

    # 利用速度向量进行辅助预测（如果速度很快且方向一致，增加置信度）
    speed = math.sqrt(velocity[0]**2 + velocity[1]**2)
    if speed > 1000: # 假设阈值
        confidence = min(1.0, confidence * 1.05)

    return CADConstraintEntity(
        geometry_type=geometry_type,
        start_point=start_p,
        end_point=end_p,
        constraints=constraints,
        confidence=confidence
    )

def analyze_closed_shape_intent(points: List[Tuple[float, float]]) -> CADConstraintEntity:
    """
    核心函数 2: 分析封闭形状（圆/多边形）意图。
    通过计算手势路径的闭合率和到中心点的距离方差来判断是否为圆。
    
    Args:
        points: 坐标点列表
        
    Returns:
        CADConstraintEntity: 生成的约束实体
    """
    if len(points) < 3:
        # 降级为线段处理或抛出错误，这里简单处理为返回未知
        return CADConstraintEntity(GeometryType.UNKNOWN, points[0])

    start_p = points[0]
    end_p = points[-1]
    
    # 1. 闭合性检测
    closing_distance = _calculate_distance(start_p, end_p)
    path_length = sum(_calculate_distance(points[i], points[i+1]) for i in range(len(points)-1))
    
    # 如果首尾距离小于总路径长度的10%，认为是尝试画封闭图形
    is_closed_attempt = (path_length > 0) and (closing_distance < (path_length * 0.1))
    
    if not is_closed_attempt:
        # 如果不是封闭图形，可能是一条曲线或者是未完成的圆弧
        # 这里简化逻辑，如果不闭合则暂时不认为是圆
        logger.info("Gesture not closed enough for circle detection.")
        return CADConstraintEntity(GeometryType.ARC, points[0], end_p=end_p)

    # 2. 圆形度检测
    # 计算所有点的几何中心
    avg_x = sum(p[0] for p in points) / len(points)
    avg_y = sum(p[1] for p in points) / len(points)
    center = (avg_x, avg_y)
    
    # 计算每个点到中心的距离
    distances = [_calculate_distance(p, center) for p in points]
    avg_radius = sum(distances) / len(distances)
    
    # 计算半径的方差（标准差/平均值），越小越像圆
    if avg_radius == 0: return CADConstraintEntity(GeometryType.UNKNOWN, points[0])
    
    variance = sum((d - avg_radius)**2 for d in distances) / len(distances)
    std_dev_ratio = math.sqrt(variance) / avg_radius
    
    # 阈值：标准差比率小于0.15 (即波动小于15%) 认为是圆
    if std_dev_ratio < 0.15:
        logger.info(f"Circle detected. Radius: {avg_radius:.2f}, Deviation: {std_dev_ratio:.2f}")
        return CADConstraintEntity(
            geometry_type=GeometryType.CIRCLE,
            start_point=start_p, # 对于圆，start_point不太重要，主要是center
            center=center,
            radius=avg_radius,
            constraints={"concentric": False, "radius_lock": False},
            confidence=1.0 - std_dev_ratio
        )
    
    # 如果闭合但不像圆，可能是矩形或多边形 (此处暂不实现矩形拟合)
    logger.info("Closed shape detected, but not a circle.")
    return CADConstraintEntity(GeometryType.UNKNOWN, points[0])

def process_gesture_to_cad(gesture_data: FlutterGestureData) -> List[CADConstraintEntity]:
    """
    主处理函数：将原始手势数据转化为CAD实体列表。
    包含预处理、意图分发和结果聚合。
    
    Args:
        gesture_data: 输入的手势数据对象
        
    Returns:
        List[CADConstraintEntity]: 解析出的CAD实体列表
        
    Example:
        >>> data = FlutterGestureData(points=[(0,0), (100, 5), (200, 2)])
        >>> entities = process_gesture_to_cad(data)
        >>> print(entities[0].geometry_type)
        GeometryType.LINE_HORIZONTAL
    """
    results = []
    try:
        points = gesture_data.points
        
        # 预处理：简单的噪点过滤（如果两点距离极近则移除后一个点，简化逻辑）
        # 这里省略复杂的道格拉斯-普克算法，直接使用原始点
        
        # 特征判断：如果是简单的两点连线或开放路径
        # 这里我们做一个简单的启发式判断：
        # 如果首尾距离相对于总路径长度很大，通常是线条
        # 如果首尾很近，通常是形状
        
        if len(points) < 2:
            return []

        start_end_dist = _calculate_distance(points[0], points[-1])
        total_dist = sum(_calculate_distance(points[i], points[i+1]) for i in range(len(points)-1))
        
        # 启发式规则：如果是简单的快速滑动（点数少，距离长），判定为线
        # 如果是点数多且闭合，判定为形状
        is_likely_line = (len(points) < 10) or (total_dist == 0) or (start_endDist / total_dist > 0.8)
        
        # 简单的分发逻辑：实际中会使用更复杂的分类器
        # 我们假设画线和画圆是两种不同的工具模式，或者通过闭合性区分
        # 这里尝试通过闭合性自动区分
        
        entity = None
        if start_end_dist < (total_dist * 0.15) and len(points) > 5:
            entity = analyze_closed_shape_intent(points)
        else:
            entity = analyze_line_intent(points, gesture_data.velocity)
            
        if entity:
            results.append(entity)
            
    except Exception as e:
        logger.error(f"Error processing gesture: {e}", exc_info=True)
        # 返回一个空的或错误的实体，或者根据需求重试
        
    return results

# ================= 使用示例 =================
if __name__ == "__main__":
    # 示例 1: 绘制一条稍微歪斜的水平线 (意图: 应被矫正为水平)
    # 点集: (0,0) -> (50, 2) -> (100, -1) -> (150, 1)
    line_data = FlutterGestureData(
        points=[(0, 0), (50, 2), (100, -1), (150, 1)],
        velocity=(500, 0),
        duration_ms=200
    )
    
    print("--- Processing Line Gesture ---")
    cad_entities = process_gesture_to_cad(line_data)
    for ent in cad_entities:
        print(f"Type: {ent.geometry_type.value}")
        print(f"Start: {ent.start_point}, End: {ent.end_point}")
        print(f"Confidence: {ent.confidence:.2f}")
        print(f"Constraints: {ent.constraints}")

    print("\n" + "="*30 + "\n")

    # 示例 2: 绘制一个近似的圆
    # 生成一个稍微带点噪点的圆
    import random
    circle_points = []
    cx, cy, r = 500, 500, 100
    for i in range(50):
        angle = 2 * math.pi * i / 50
        # 添加随机噪点
        noise = random.uniform(-5, 5) 
        x = cx + (r + noise) * math.cos(angle)
        y = cy + (r + noise) * math.sin(angle)
        circle_points.append((x, y))
    # 闭合回起点附近
    circle_points.append((circle_points[0][0]+1, circle_points[0][1]+1))

    circle_data = FlutterGestureData(
        points=circle_points,
        velocity=(0,0),
        duration_ms=600
    )

    print("--- Processing Circle Gesture ---")
    cad_entities_circle = process_gesture_to_cad(circle_data)
    for ent in cad_entities_circle:
        print(f"Type: {ent.geometry_type.value}")
        print(f"Center: {ent.center}, Radius: {ent.radius:.2f}")
        print(f"Confidence: {ent.confidence:.2f}")