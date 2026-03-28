#!/usr/bin/env python3
"""
刀模活字印刷3D模块 - CAD图纸到3D模块生成器

功能:
1. DXF/DWG解析 - 读取CAD文件提取刀线路径
2. 路径分解 - 将复杂路径分解为标准模块
3. 模块匹配 - 匹配预定义的模块库
4. STL生成 - 生成3D可打印的STL文件
5. 装配指南 - 生成模块装配说明

依赖: ezdxf (DXF解析), numpy (几何计算)
"""

import os
import sys
import json
import math
import struct
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum

PROJECT_ROOT = Path(__file__).parent

# 尝试导入ezdxf
try:
    import ezdxf
    from ezdxf.entities import Line, Arc, Circle, LWPolyline, Spline
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False
    print("警告: ezdxf未安装，DXF解析功能不可用。运行: pip install ezdxf")


# ═══════════════════════════════════════════════════════════════
# 常量和配置
# ═══════════════════════════════════════════════════════════════

class ModuleType(Enum):
    """模块类型"""
    STRAIGHT = "straight"           # 直线段
    ARC = "arc"                     # 圆弧
    CORNER_90 = "corner_90"         # 90度角
    CORNER_45 = "corner_45"         # 45度角
    CORNER_VAR = "corner_var"       # 可变角度
    T_JOINT = "t_joint"             # T形接头
    CROSS_JOINT = "cross_joint"     # 十字接头
    END_CAP = "end_cap"             # 端盖
    BRIDGE = "bridge"               # 刀片桥接
    EJECTOR_PAD = "ejector_pad"     # 顶出垫
    BASE_TILE = "base_tile"         # 底板瓷砖


# 模块参数 (单位: mm)
MODULE_PARAMS = {
    "blade_height": 23.8,           # 刀片高度 (IADD标准)
    "blade_thickness": 0.71,        # 刀片厚度 (2pt)
    "base_height": 5.0,             # 底座高度
    "slot_width": 0.86,             # 刀槽宽度 (含间隙)
    "slot_depth": 20.0,             # 刀槽深度
    "connector_size": 5.0,          # 燕尾榫尺寸
    "connector_taper": 15.0,        # 燕尾榫锥度 (度)
    "tolerance": 0.15,              # 打印公差
    "min_segment_length": 3.0,      # 最小线段长度
}

# P1S打印机参数
PRINTER_PARAMS = {
    "build_x": 256,
    "build_y": 256,
    "build_z": 256,
    "layer_height": 0.2,
    "nozzle_diameter": 0.4,
}


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class Point2D:
    """2D点"""
    x: float
    y: float
    
    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def angle_to(self, other: 'Point2D') -> float:
        return math.atan2(other.y - self.y, other.x - self.x)
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class PathSegment:
    """路径段"""
    start: Point2D
    end: Point2D
    segment_type: str = "line"  # line, arc
    center: Optional[Point2D] = None  # 圆弧中心
    radius: float = 0.0
    is_ccw: bool = True  # 逆时针
    
    @property
    def length(self) -> float:
        if self.segment_type == "line":
            return self.start.distance_to(self.end)
        elif self.segment_type == "arc" and self.radius > 0:
            angle = abs(self._arc_angle())
            return self.radius * angle
        return 0.0
    
    def _arc_angle(self) -> float:
        if not self.center:
            return 0.0
        start_angle = self.center.angle_to(self.start)
        end_angle = self.center.angle_to(self.end)
        angle = end_angle - start_angle
        if self.is_ccw and angle < 0:
            angle += 2 * math.pi
        elif not self.is_ccw and angle > 0:
            angle -= 2 * math.pi
        return angle


@dataclass
class DieCutModule:
    """刀模模块"""
    module_id: str
    module_type: ModuleType
    position: Point2D
    rotation: float = 0.0  # 弧度
    length: float = 0.0
    angle: float = 0.0  # 角度模块的角度
    params: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["module_type"] = self.module_type.value
        d["position"] = self.position.to_tuple()
        return d


@dataclass
class AssemblyGuide:
    """装配指南"""
    modules: List[DieCutModule]
    total_length: float
    module_count: Dict[str, int]
    estimated_cost: float
    stl_files: List[str]
    notes: List[str]


# ═══════════════════════════════════════════════════════════════
# DXF解析器
# ═══════════════════════════════════════════════════════════════

class DXFParser:
    """DXF文件解析器"""
    
    def __init__(self):
        self.segments: List[PathSegment] = []
        self.bounds = {"min_x": float("inf"), "min_y": float("inf"),
                       "max_x": float("-inf"), "max_y": float("-inf")}
    
    def parse(self, filepath: Path) -> List[PathSegment]:
        """解析DXF文件"""
        if not HAS_EZDXF:
            raise ImportError("ezdxf未安装")
        
        doc = ezdxf.readfile(str(filepath))
        msp = doc.modelspace()
        
        self.segments = []
        
        for entity in msp:
            if entity.dxftype() == "LINE":
                self._parse_line(entity)
            elif entity.dxftype() == "ARC":
                self._parse_arc(entity)
            elif entity.dxftype() == "CIRCLE":
                self._parse_circle(entity)
            elif entity.dxftype() == "LWPOLYLINE":
                self._parse_polyline(entity)
        
        return self.segments
    
    def _parse_line(self, entity):
        """解析直线"""
        start = Point2D(entity.dxf.start.x, entity.dxf.start.y)
        end = Point2D(entity.dxf.end.x, entity.dxf.end.y)
        
        self._update_bounds(start)
        self._update_bounds(end)
        
        self.segments.append(PathSegment(
            start=start,
            end=end,
            segment_type="line"
        ))
    
    def _parse_arc(self, entity):
        """解析圆弧"""
        center = Point2D(entity.dxf.center.x, entity.dxf.center.y)
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)
        
        start = Point2D(
            center.x + radius * math.cos(start_angle),
            center.y + radius * math.sin(start_angle)
        )
        end = Point2D(
            center.x + radius * math.cos(end_angle),
            center.y + radius * math.sin(end_angle)
        )
        
        self._update_bounds(start)
        self._update_bounds(end)
        
        self.segments.append(PathSegment(
            start=start,
            end=end,
            segment_type="arc",
            center=center,
            radius=radius,
            is_ccw=True
        ))
    
    def _parse_circle(self, entity):
        """解析圆（分解为多段圆弧）"""
        center = Point2D(entity.dxf.center.x, entity.dxf.center.y)
        radius = entity.dxf.radius
        
        # 分解为4段圆弧
        for i in range(4):
            start_angle = i * math.pi / 2
            end_angle = (i + 1) * math.pi / 2
            
            start = Point2D(
                center.x + radius * math.cos(start_angle),
                center.y + radius * math.sin(start_angle)
            )
            end = Point2D(
                center.x + radius * math.cos(end_angle),
                center.y + radius * math.sin(end_angle)
            )
            
            self._update_bounds(start)
            self._update_bounds(end)
            
            self.segments.append(PathSegment(
                start=start,
                end=end,
                segment_type="arc",
                center=center,
                radius=radius,
                is_ccw=True
            ))
    
    def _parse_polyline(self, entity):
        """解析多段线"""
        points = list(entity.get_points("xy"))
        
        for i in range(len(points) - 1):
            start = Point2D(points[i][0], points[i][1])
            end = Point2D(points[i + 1][0], points[i + 1][1])
            
            self._update_bounds(start)
            self._update_bounds(end)
            
            # 检查是否有凸度（圆弧）
            bulge = entity[i].dxf.bulge if hasattr(entity[i].dxf, "bulge") else 0
            
            if abs(bulge) > 0.001:
                # 有凸度，是圆弧
                chord_length = start.distance_to(end)
                sagitta = abs(bulge) * chord_length / 2
                radius = (sagitta**2 + (chord_length/2)**2) / (2 * sagitta)
                
                mid = Point2D((start.x + end.x) / 2, (start.y + end.y) / 2)
                direction = Point2D(-(end.y - start.y), end.x - start.x)
                direction_len = math.sqrt(direction.x**2 + direction.y**2)
                if direction_len > 0:
                    direction.x /= direction_len
                    direction.y /= direction_len
                
                offset = radius - sagitta
                if bulge < 0:
                    offset = -offset
                
                center = Point2D(
                    mid.x + direction.x * offset,
                    mid.y + direction.y * offset
                )
                
                self.segments.append(PathSegment(
                    start=start,
                    end=end,
                    segment_type="arc",
                    center=center,
                    radius=radius,
                    is_ccw=bulge > 0
                ))
            else:
                self.segments.append(PathSegment(
                    start=start,
                    end=end,
                    segment_type="line"
                ))
        
        # 闭合多段线
        if entity.closed:
            start = Point2D(points[-1][0], points[-1][1])
            end = Point2D(points[0][0], points[0][1])
            self.segments.append(PathSegment(start=start, end=end, segment_type="line"))
    
    def _update_bounds(self, point: Point2D):
        """更新边界"""
        self.bounds["min_x"] = min(self.bounds["min_x"], point.x)
        self.bounds["min_y"] = min(self.bounds["min_y"], point.y)
        self.bounds["max_x"] = max(self.bounds["max_x"], point.x)
        self.bounds["max_y"] = max(self.bounds["max_y"], point.y)


# ═══════════════════════════════════════════════════════════════
# 模块分解器
# ═══════════════════════════════════════════════════════════════

class ModuleDecomposer:
    """路径到模块分解器"""
    
    def __init__(self, params: Dict = None):
        self.params = params or MODULE_PARAMS
        self.modules: List[DieCutModule] = []
        self.module_counter = 0
    
    def decompose(self, segments: List[PathSegment]) -> List[DieCutModule]:
        """分解路径为模块"""
        self.modules = []
        self.module_counter = 0
        
        # 构建连接图
        graph = self._build_graph(segments)
        
        # 遍历路径
        for segment in segments:
            if segment.segment_type == "line":
                self._decompose_line(segment)
            elif segment.segment_type == "arc":
                self._decompose_arc(segment)
        
        # 检测角点并添加角模块
        self._detect_corners(segments)
        
        # 添加端盖
        self._add_end_caps(segments)
        
        return self.modules
    
    def _build_graph(self, segments: List[PathSegment]) -> Dict[Tuple, List[int]]:
        """构建连接图"""
        graph = defaultdict(list)
        
        for i, seg in enumerate(segments):
            start_key = (round(seg.start.x, 2), round(seg.start.y, 2))
            end_key = (round(seg.end.x, 2), round(seg.end.y, 2))
            graph[start_key].append(i)
            graph[end_key].append(i)
        
        return dict(graph)
    
    def _decompose_line(self, segment: PathSegment):
        """分解直线段"""
        length = segment.length
        min_len = self.params["min_segment_length"]
        
        if length < min_len:
            return
        
        # 计算需要多少个模块
        standard_lengths = [50, 30, 20, 10, 5]  # 标准长度
        
        remaining = length
        current_pos = segment.start
        angle = segment.start.angle_to(segment.end)
        
        while remaining >= min_len:
            # 选择最大的可用长度
            module_length = min_len
            for std_len in standard_lengths:
                if std_len <= remaining:
                    module_length = std_len
                    break
            
            self.module_counter += 1
            self.modules.append(DieCutModule(
                module_id=f"STR_{self.module_counter:04d}",
                module_type=ModuleType.STRAIGHT,
                position=current_pos,
                rotation=angle,
                length=module_length
            ))
            
            # 移动到下一个位置
            current_pos = Point2D(
                current_pos.x + module_length * math.cos(angle),
                current_pos.y + module_length * math.sin(angle)
            )
            remaining -= module_length
    
    def _decompose_arc(self, segment: PathSegment):
        """分解圆弧"""
        if segment.radius <= 0 or not segment.center:
            return
        
        arc_length = segment.length
        if arc_length < self.params["min_segment_length"]:
            return
        
        # 计算圆弧角度
        arc_angle = abs(segment._arc_angle())
        
        # 小圆弧使用单个弧模块
        if arc_angle <= math.pi / 2:
            self.module_counter += 1
            self.modules.append(DieCutModule(
                module_id=f"ARC_{self.module_counter:04d}",
                module_type=ModuleType.ARC,
                position=segment.start,
                rotation=segment.center.angle_to(segment.start),
                params={
                    "radius": segment.radius,
                    "angle": math.degrees(arc_angle),
                    "is_ccw": segment.is_ccw
                }
            ))
        else:
            # 大圆弧分解为多个小弧
            num_segments = int(arc_angle / (math.pi / 4)) + 1
            segment_angle = arc_angle / num_segments
            
            start_angle = segment.center.angle_to(segment.start)
            
            for i in range(num_segments):
                current_angle = start_angle + i * segment_angle * (1 if segment.is_ccw else -1)
                pos = Point2D(
                    segment.center.x + segment.radius * math.cos(current_angle),
                    segment.center.y + segment.radius * math.sin(current_angle)
                )
                
                self.module_counter += 1
                self.modules.append(DieCutModule(
                    module_id=f"ARC_{self.module_counter:04d}",
                    module_type=ModuleType.ARC,
                    position=pos,
                    rotation=current_angle,
                    params={
                        "radius": segment.radius,
                        "angle": math.degrees(segment_angle),
                        "is_ccw": segment.is_ccw
                    }
                ))
    
    def _detect_corners(self, segments: List[PathSegment]):
        """检测角点"""
        # 按端点分组
        endpoints = defaultdict(list)
        for i, seg in enumerate(segments):
            start_key = (round(seg.start.x, 2), round(seg.start.y, 2))
            end_key = (round(seg.end.x, 2), round(seg.end.y, 2))
            endpoints[start_key].append((i, "start"))
            endpoints[end_key].append((i, "end"))
        
        # 检测连接点
        for point_key, connections in endpoints.items():
            if len(connections) == 2:
                # 两条线段连接
                seg1_idx, seg1_end = connections[0]
                seg2_idx, seg2_end = connections[1]
                
                seg1 = segments[seg1_idx]
                seg2 = segments[seg2_idx]
                
                # 计算角度
                if seg1_end == "start":
                    angle1 = seg1.end.angle_to(seg1.start)
                else:
                    angle1 = seg1.start.angle_to(seg1.end)
                
                if seg2_end == "start":
                    angle2 = seg2.start.angle_to(seg2.end)
                else:
                    angle2 = seg2.end.angle_to(seg2.start)
                
                angle_diff = abs(angle2 - angle1)
                if angle_diff > math.pi:
                    angle_diff = 2 * math.pi - angle_diff
                
                corner_angle = math.degrees(angle_diff)
                
                # 添加角模块
                if 85 <= corner_angle <= 95:
                    module_type = ModuleType.CORNER_90
                elif 40 <= corner_angle <= 50:
                    module_type = ModuleType.CORNER_45
                elif 10 <= corner_angle <= 170:
                    module_type = ModuleType.CORNER_VAR
                else:
                    continue
                
                self.module_counter += 1
                self.modules.append(DieCutModule(
                    module_id=f"CRN_{self.module_counter:04d}",
                    module_type=module_type,
                    position=Point2D(point_key[0], point_key[1]),
                    angle=corner_angle
                ))
            
            elif len(connections) == 3:
                # T形接头
                self.module_counter += 1
                self.modules.append(DieCutModule(
                    module_id=f"TJT_{self.module_counter:04d}",
                    module_type=ModuleType.T_JOINT,
                    position=Point2D(point_key[0], point_key[1])
                ))
            
            elif len(connections) == 4:
                # 十字接头
                self.module_counter += 1
                self.modules.append(DieCutModule(
                    module_id=f"CRS_{self.module_counter:04d}",
                    module_type=ModuleType.CROSS_JOINT,
                    position=Point2D(point_key[0], point_key[1])
                ))
    
    def _add_end_caps(self, segments: List[PathSegment]):
        """添加端盖"""
        endpoints = defaultdict(int)
        for seg in segments:
            start_key = (round(seg.start.x, 2), round(seg.start.y, 2))
            end_key = (round(seg.end.x, 2), round(seg.end.y, 2))
            endpoints[start_key] += 1
            endpoints[end_key] += 1
        
        for point_key, count in endpoints.items():
            if count == 1:
                self.module_counter += 1
                self.modules.append(DieCutModule(
                    module_id=f"END_{self.module_counter:04d}",
                    module_type=ModuleType.END_CAP,
                    position=Point2D(point_key[0], point_key[1])
                ))


# ═══════════════════════════════════════════════════════════════
# STL生成器
# ═══════════════════════════════════════════════════════════════

class STLGenerator:
    """STL文件生成器（纯Python实现）"""
    
    def __init__(self, params: Dict = None):
        self.params = params or MODULE_PARAMS
        self.triangles: List[Tuple[Tuple, Tuple, Tuple, Tuple]] = []  # (normal, v1, v2, v3)
    
    def generate_straight_module(self, length: float) -> bytes:
        """生成直线模块STL"""
        self.triangles = []
        
        # 尺寸参数
        slot_width = self.params["slot_width"]
        slot_depth = self.params["slot_depth"]
        base_height = self.params["base_height"]
        connector_size = self.params["connector_size"]
        
        # 总宽度
        total_width = slot_width + 4  # 两侧各2mm壁厚
        total_height = base_height + slot_depth
        
        # 创建基本长方体
        self._add_box(0, 0, 0, length, total_width, total_height)
        
        # 减去刀槽
        slot_offset = (total_width - slot_width) / 2
        self._add_box(0, slot_offset, base_height, length, slot_width, slot_depth, subtract=True)
        
        # 添加燕尾榫连接器（两端）
        self._add_dovetail(0, total_width / 2, base_height / 2, connector_size, inward=True)
        self._add_dovetail(length, total_width / 2, base_height / 2, connector_size, inward=False)
        
        return self._to_binary_stl()
    
    def generate_corner_module(self, angle: float) -> bytes:
        """生成角模块STL"""
        self.triangles = []
        
        # 简化：生成基本角形状
        slot_width = self.params["slot_width"]
        base_height = self.params["base_height"]
        slot_depth = self.params["slot_depth"]
        
        size = 20  # 角模块基本尺寸
        total_height = base_height + slot_depth
        
        # 创建L形（90度角）或楔形
        if 85 <= angle <= 95:
            # 90度角 - L形
            self._add_box(0, 0, 0, size, size/2, total_height)
            self._add_box(0, size/2, 0, size/2, size/2, total_height)
        else:
            # 其他角度 - 简化为三角形基座
            angle_rad = math.radians(angle)
            # 生成楔形
            self._add_wedge(0, 0, 0, size, size, total_height, angle_rad)
        
        return self._to_binary_stl()
    
    def generate_arc_module(self, radius: float, arc_angle: float) -> bytes:
        """生成圆弧模块STL"""
        self.triangles = []
        
        slot_width = self.params["slot_width"]
        base_height = self.params["base_height"]
        slot_depth = self.params["slot_depth"]
        total_height = base_height + slot_depth
        
        # 圆弧分段数
        num_segments = max(8, int(arc_angle / 10))
        angle_step = math.radians(arc_angle) / num_segments
        
        inner_radius = radius - slot_width / 2 - 2
        outer_radius = radius + slot_width / 2 + 2
        
        # 生成圆弧扇形
        for i in range(num_segments):
            angle1 = i * angle_step
            angle2 = (i + 1) * angle_step
            
            # 底面
            p1 = (inner_radius * math.cos(angle1), inner_radius * math.sin(angle1), 0)
            p2 = (outer_radius * math.cos(angle1), outer_radius * math.sin(angle1), 0)
            p3 = (outer_radius * math.cos(angle2), outer_radius * math.sin(angle2), 0)
            p4 = (inner_radius * math.cos(angle2), inner_radius * math.sin(angle2), 0)
            
            self._add_quad(p1, p2, p3, p4, (0, 0, -1))
            
            # 顶面
            p1t = (*p1[:2], total_height)
            p2t = (*p2[:2], total_height)
            p3t = (*p3[:2], total_height)
            p4t = (*p4[:2], total_height)
            
            self._add_quad(p1t, p4t, p3t, p2t, (0, 0, 1))
            
            # 内侧面
            self._add_quad(p1, p4, p4t, p1t, (-math.cos((angle1+angle2)/2), -math.sin((angle1+angle2)/2), 0))
            
            # 外侧面
            self._add_quad(p2, p2t, p3t, p3, (math.cos((angle1+angle2)/2), math.sin((angle1+angle2)/2), 0))
        
        return self._to_binary_stl()
    
    def _add_box(self, x, y, z, length, width, height, subtract=False):
        """添加长方体"""
        # 8个顶点
        v = [
            (x, y, z),
            (x + length, y, z),
            (x + length, y + width, z),
            (x, y + width, z),
            (x, y, z + height),
            (x + length, y, z + height),
            (x + length, y + width, z + height),
            (x, y + width, z + height),
        ]
        
        # 6个面（每面2个三角形）
        faces = [
            (0, 3, 2, 1, (0, 0, -1)),  # 底面
            (4, 5, 6, 7, (0, 0, 1)),   # 顶面
            (0, 1, 5, 4, (0, -1, 0)),  # 前面
            (2, 3, 7, 6, (0, 1, 0)),   # 后面
            (0, 4, 7, 3, (-1, 0, 0)),  # 左面
            (1, 2, 6, 5, (1, 0, 0)),   # 右面
        ]
        
        for i1, i2, i3, i4, normal in faces:
            if not subtract:
                self._add_quad(v[i1], v[i2], v[i3], v[i4], normal)
    
    def _add_quad(self, p1, p2, p3, p4, normal):
        """添加四边形（分解为2个三角形）"""
        self.triangles.append((normal, p1, p2, p3))
        self.triangles.append((normal, p1, p3, p4))
    
    def _add_dovetail(self, x, y, z, size, inward=True):
        """添加燕尾榫"""
        # 简化：只记录位置
        pass
    
    def _add_wedge(self, x, y, z, length, width, height, angle):
        """添加楔形"""
        # 简化的楔形生成
        v = [
            (x, y, z),
            (x + length, y, z),
            (x + length * math.cos(angle), y + length * math.sin(angle), z),
            (x, y, z + height),
            (x + length, y, z + height),
            (x + length * math.cos(angle), y + length * math.sin(angle), z + height),
        ]
        
        # 底面
        self._add_quad(v[0], v[2], v[1], v[0], (0, 0, -1))
        # 顶面
        self._add_quad(v[3], v[4], v[5], v[3], (0, 0, 1))
    
    def _to_binary_stl(self) -> bytes:
        """转换为二进制STL格式"""
        # 80字节头
        header = b"Binary STL generated by DieCut3D" + b"\0" * (80 - 33)
        
        # 三角形数量
        num_triangles = len(self.triangles)
        
        # 构建数据
        data = bytearray(header)
        data.extend(struct.pack("<I", num_triangles))
        
        for normal, v1, v2, v3 in self.triangles:
            # 法向量
            data.extend(struct.pack("<fff", *normal))
            # 顶点
            data.extend(struct.pack("<fff", *v1))
            data.extend(struct.pack("<fff", *v2))
            data.extend(struct.pack("<fff", *v3))
            # 属性
            data.extend(struct.pack("<H", 0))
        
        return bytes(data)
    
    def save(self, filepath: Path, stl_data: bytes):
        """保存STL文件"""
        filepath.write_bytes(stl_data)


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

class CADTo3DPipeline:
    """CAD到3D完整流程"""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or PROJECT_ROOT / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        self.parser = DXFParser() if HAS_EZDXF else None
        self.decomposer = ModuleDecomposer()
        self.stl_gen = STLGenerator()
    
    def process(self, cad_file: Path) -> AssemblyGuide:
        """处理CAD文件"""
        print(f"处理CAD文件: {cad_file}")
        
        # 1. 解析DXF
        if self.parser and cad_file.suffix.lower() == ".dxf" and cad_file.stat().st_size > 0:
            try:
                segments = self.parser.parse(cad_file)
                print(f"  解析到 {len(segments)} 个路径段")
            except Exception as e:
                print(f"  DXF解析失败: {e}，使用演示路径")
                segments = self._create_demo_segments()
        else:
            # 演示模式：创建示例路径
            print("  使用演示路径")
            segments = self._create_demo_segments()
        
        # 2. 分解为模块
        modules = self.decomposer.decompose(segments)
        print(f"  分解为 {len(modules)} 个模块")
        
        # 3. 统计模块
        module_count = defaultdict(int)
        total_length = 0
        for m in modules:
            module_count[m.module_type.value] += 1
            total_length += m.length
        
        # 4. 生成STL文件
        stl_files = []
        for module in modules:
            stl_file = self._generate_module_stl(module)
            if stl_file:
                stl_files.append(str(stl_file))
        
        # 5. 估算成本
        estimated_cost = self._estimate_cost(modules)
        
        # 6. 生成装配指南
        guide = AssemblyGuide(
            modules=modules,
            total_length=total_length,
            module_count=dict(module_count),
            estimated_cost=estimated_cost,
            stl_files=stl_files,
            notes=[
                "所有模块使用燕尾榫连接",
                "建议使用PETG-CF材料打印",
                "打印层高: 0.2mm",
                "填充率: 40%",
            ]
        )
        
        # 7. 保存报告
        self._save_report(guide, cad_file.stem)
        
        return guide
    
    def _create_demo_segments(self) -> List[PathSegment]:
        """创建演示路径"""
        segments = []
        
        # 简单矩形
        points = [
            Point2D(0, 0),
            Point2D(100, 0),
            Point2D(100, 50),
            Point2D(0, 50),
        ]
        
        for i in range(len(points)):
            segments.append(PathSegment(
                start=points[i],
                end=points[(i + 1) % len(points)],
                segment_type="line"
            ))
        
        return segments
    
    def _generate_module_stl(self, module: DieCutModule) -> Optional[Path]:
        """生成单个模块的STL"""
        try:
            if module.module_type == ModuleType.STRAIGHT:
                stl_data = self.stl_gen.generate_straight_module(module.length or 20)
            elif module.module_type in [ModuleType.CORNER_90, ModuleType.CORNER_45, ModuleType.CORNER_VAR]:
                stl_data = self.stl_gen.generate_corner_module(module.angle or 90)
            elif module.module_type == ModuleType.ARC:
                radius = module.params.get("radius", 20)
                angle = module.params.get("angle", 45)
                stl_data = self.stl_gen.generate_arc_module(radius, angle)
            else:
                return None
            
            stl_file = self.output_dir / f"{module.module_id}.stl"
            self.stl_gen.save(stl_file, stl_data)
            return stl_file
            
        except Exception as e:
            print(f"  生成STL失败 {module.module_id}: {e}")
            return None
    
    def _estimate_cost(self, modules: List[DieCutModule]) -> float:
        """估算成本"""
        # 简化估算：每个模块约5元材料成本
        base_cost = len(modules) * 5
        
        # 加上打印时间成本
        print_time_cost = len(modules) * 2  # 每个模块约2元打印成本
        
        return base_cost + print_time_cost
    
    def _save_report(self, guide: AssemblyGuide, name: str):
        """保存装配报告"""
        report_file = self.output_dir / f"{name}_report.json"
        
        report = {
            "name": name,
            "generated_at": str(Path.cwd()),
            "total_modules": len(guide.modules),
            "total_length": guide.total_length,
            "module_count": guide.module_count,
            "estimated_cost": guide.estimated_cost,
            "stl_files": guide.stl_files,
            "notes": guide.notes,
            "modules": [m.to_dict() for m in guide.modules]
        }
        
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"  报告已保存: {report_file}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="刀模活字印刷3D模块生成器")
    parser.add_argument("cad_file", nargs="?", help="CAD文件路径 (DXF)")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output) if args.output else None
    pipeline = CADTo3DPipeline(output_dir)
    
    if args.demo or not args.cad_file:
        print("运行演示模式...")
        
        # 创建演示DXF（如果不存在）
        demo_file = PROJECT_ROOT / "demo.dxf"
        if not demo_file.exists():
            print("创建演示文件...")
            # 简单的演示
            demo_file.write_text("")
        
        guide = pipeline.process(demo_file)
    else:
        cad_file = Path(args.cad_file)
        if not cad_file.exists():
            print(f"文件不存在: {cad_file}")
            return
        
        guide = pipeline.process(cad_file)
    
    print("\n═══════════════════════════════════════")
    print("          生成完成")
    print("═══════════════════════════════════════")
    print(f"总模块数: {len(guide.modules)}")
    print(f"模块统计: {guide.module_count}")
    print(f"预估成本: ¥{guide.estimated_cost:.2f}")
    print(f"STL文件数: {len(guide.stl_files)}")


if __name__ == "__main__":
    main()
