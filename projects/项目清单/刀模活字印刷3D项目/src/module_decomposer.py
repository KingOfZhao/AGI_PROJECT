#!/usr/bin/env python3
"""
刀模活字模块拆解器 — CAD二维图纸 → 活字模块序列
将DXF/DWG中的切割路径拆解为标准化模块,如同活字印刷拆字排版
"""
import math
import json
import os
from typing import List, Dict, Tuple, Optional
from knowledge_base import IADD_STEEL_RULE_SPECS, CONNECTOR_SPECS, BAMBU_P1S_P2S

# ─── 几何基元 ────────────────────────────────────────────────────

class Point:
    __slots__ = ("x", "y")
    def __init__(self, x: float, y: float):
        self.x, self.y = x, y
    def dist(self, other: "Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)
    def angle_to(self, other: "Point") -> float:
        return math.atan2(other.y - self.y, other.x - self.x)
    def __repr__(self):
        return f"({self.x:.2f},{self.y:.2f})"
    def to_dict(self):
        return {"x": round(self.x, 3), "y": round(self.y, 3)}

class Segment:
    """直线段或圆弧段"""
    def __init__(self, start: Point, end: Point, seg_type: str = "LINE",
                 layer: str = "CUT", radius: float = 0, center: Point = None,
                 bulge: float = 0):
        self.start = start
        self.end = end
        self.seg_type = seg_type  # LINE / ARC
        self.layer = layer        # CUT / CREASE / PERF
        self.radius = radius
        self.center = center
        self.bulge = bulge

    @property
    def length(self) -> float:
        if self.seg_type == "ARC" and self.radius > 0:
            angle = self._arc_angle()
            return abs(self.radius * angle)
        return self.start.dist(self.end)

    @property
    def angle(self) -> float:
        """段的方向角 (rad)"""
        return self.start.angle_to(self.end)

    def _arc_angle(self) -> float:
        if not self.center:
            return 0
        a1 = math.atan2(self.start.y - self.center.y, self.start.x - self.center.x)
        a2 = math.atan2(self.end.y - self.center.y, self.end.x - self.center.x)
        da = a2 - a1
        if da > math.pi: da -= 2 * math.pi
        if da < -math.pi: da += 2 * math.pi
        return abs(da)

    def to_dict(self):
        d = {"type": self.seg_type, "layer": self.layer,
             "start": self.start.to_dict(), "end": self.end.to_dict(),
             "length_mm": round(self.length, 2)}
        if self.seg_type == "ARC":
            d["radius"] = round(self.radius, 2)
            if self.center:
                d["center"] = self.center.to_dict()
        return d


# ─── 模块定义 ────────────────────────────────────────────────────

class Module:
    """一个可3D打印的刀模模块"""
    def __init__(self, mod_type: str, params: dict):
        self.mod_type = mod_type  # STRAIGHT/ARC/CORNER_90/CORNER_VAR/T_JOINT/CROSS_JOINT/END_CAP/BRIDGE
        self.params = params
        self.segments: List[Segment] = []  # 对应的原始CAD段
        self.position: Optional[Point] = None  # 在底板上的位置
        self.rotation_deg: float = 0  # 旋转角度

    @property
    def print_volume_mm3(self) -> float:
        """估算3D打印体积"""
        bp = self.params.get("blade_point", "2pt")
        bp_mm = IADD_STEEL_RULE_SPECS["blade_thickness"].get(bp, {}).get("mm", 0.71)
        body_w = max(8.0, bp_mm + 4.03)
        body_d = 12.0
        h = 28.8

        if self.mod_type == "STRAIGHT":
            return body_w * body_d * self.params.get("length_mm", 50)
        elif self.mod_type in ("CORNER_90", "CORNER_45", "CORNER_VAR"):
            blk = self.params.get("block_mm", 20)
            return blk * blk * h
        elif self.mod_type in ("T_JOINT", "CROSS_JOINT"):
            return 20 * 20 * h
        elif self.mod_type == "END_CAP":
            return 10 * body_w * h
        elif self.mod_type == "BRIDGE":
            return self.params.get("bridge_len", 5) * body_w * h
        return 1000  # default

    @property
    def print_time_min(self) -> float:
        """估算打印时间(分钟)"""
        vol = self.print_volume_mm3
        # PETG-CF ~10mm³/s at 0.15mm layer height
        return vol / (10 * 60) + 2  # +2min setup

    @property
    def weight_g(self) -> float:
        """估算重量(g)"""
        # PETG-CF density ~1.3g/cm³, infill ~80%
        return self.print_volume_mm3 * 1.3 * 0.8 / 1000

    def to_dict(self):
        return {
            "type": self.mod_type,
            "params": self.params,
            "segments": [s.to_dict() for s in self.segments],
            "position": self.position.to_dict() if self.position else None,
            "rotation_deg": self.rotation_deg,
            "print_volume_mm3": round(self.print_volume_mm3, 1),
            "print_time_min": round(self.print_time_min, 1),
            "weight_g": round(self.weight_g, 1),
        }


# ─── 连接图 ──────────────────────────────────────────────────────

class ConnectionGraph:
    """几何连接图: 节点=端点交点, 边=线段"""
    MERGE_TOL = 0.5  # mm

    def __init__(self):
        self.nodes: List[Point] = []
        self.edges: List[Tuple[int, int, Segment]] = []  # (node_i, node_j, segment)

    def add_segment(self, seg: Segment):
        ni = self._get_or_add_node(seg.start)
        nj = self._get_or_add_node(seg.end)
        self.edges.append((ni, nj, seg))

    def _get_or_add_node(self, pt: Point) -> int:
        for i, n in enumerate(self.nodes):
            if n.dist(pt) < self.MERGE_TOL:
                return i
        self.nodes.append(pt)
        return len(self.nodes) - 1

    def degree(self, node_idx: int) -> int:
        return sum(1 for a, b, _ in self.edges if a == node_idx or b == node_idx)

    def neighbors(self, node_idx: int) -> List[Tuple[int, Segment]]:
        result = []
        for a, b, seg in self.edges:
            if a == node_idx:
                result.append((b, seg))
            elif b == node_idx:
                result.append((a, seg))
        return result

    def find_paths(self) -> List[List[Tuple[int, Segment]]]:
        """找出所有连续路径"""
        visited_edges = set()
        paths = []

        # 从度数=1的端点开始(开放路径), 或任意节点(闭合路径)
        start_nodes = [i for i in range(len(self.nodes)) if self.degree(i) == 1]
        if not start_nodes:
            start_nodes = [0] if self.nodes else []

        for start in start_nodes:
            path = []
            current = start
            while True:
                found = False
                for idx, (a, b, seg) in enumerate(self.edges):
                    if idx in visited_edges:
                        continue
                    if a == current:
                        visited_edges.add(idx)
                        path.append((b, seg))
                        current = b
                        found = True
                        break
                    elif b == current:
                        visited_edges.add(idx)
                        path.append((a, seg))
                        current = a
                        found = True
                        break
                if not found:
                    break
            if path:
                paths.append(path)

        # 处理未访问的边(闭合路径)
        for idx, (a, b, seg) in enumerate(self.edges):
            if idx not in visited_edges:
                visited_edges.add(idx)
                paths.append([(b, seg)])

        return paths


# ─── 模块拆解器 ──────────────────────────────────────────────────

class ModuleDecomposer:
    """将CAD几何实体拆解为标准化模块序列"""

    MAX_MODULE_LENGTH = 250  # mm (P1S/P2S限制)
    LENGTH_STEP = 5          # mm (标准化步进)
    MIN_MODULE_LENGTH = 10   # mm (最小模块长度)

    def __init__(self, blade_point: str = "2pt"):
        self.blade_point = blade_point
        self.bp_mm = IADD_STEEL_RULE_SPECS["blade_thickness"][blade_point]["mm"]
        self.modules: List[Module] = []
        self.graph = ConnectionGraph()

    def add_segments(self, segments: List[Segment]):
        """添加CAD解析出的线段"""
        for seg in segments:
            if seg.layer in ("CUT", "CREASE", "PERF"):
                self.graph.add_segment(seg)

    def decompose(self) -> List[Module]:
        """执行拆解: 线段→连接图→路径→模块序列"""
        self.modules = []

        # Step 1: 找出所有路径
        paths = self.graph.find_paths()

        for path in paths:
            # Step 2: 对每条路径生成模块序列
            path_modules = self._path_to_modules(path)
            self.modules.extend(path_modules)

        # Step 3: 添加节点处的特殊模块
        self._add_junction_modules()

        return self.modules

    def _path_to_modules(self, path: List[Tuple[int, Segment]]) -> List[Module]:
        """将连续路径转换为模块序列"""
        modules = []

        # 合并共线段
        merged = self._merge_collinear(path)

        for node_idx, seg in merged:
            if seg.seg_type == "LINE":
                line_modules = self._line_to_modules(seg)
                modules.extend(line_modules)
            elif seg.seg_type == "ARC":
                arc_module = self._arc_to_module(seg)
                modules.append(arc_module)

        # 在相邻模块间检测角度变化,插入转角模块
        modules_with_corners = self._insert_corners(modules)

        # 添加端头
        if modules_with_corners:
            # 检查路径是否开放(非闭合)
            first_seg = path[0][1] if path else None
            last_seg = path[-1][1] if path else None
            if first_seg and last_seg:
                start_deg = self.graph.degree(self._find_start_node(path))
                end_deg = self.graph.degree(path[-1][0])
                if start_deg == 1:
                    modules_with_corners.insert(0, Module("END_CAP", {
                        "blade_point": self.blade_point, "style": "平头"}))
                if end_deg == 1:
                    modules_with_corners.append(Module("END_CAP", {
                        "blade_point": self.blade_point, "style": "平头"}))

        return modules_with_corners

    def _find_start_node(self, path):
        if not path: return 0
        first_node_idx, first_seg = path[0]
        for a, b, seg in self.graph.edges:
            if seg is first_seg:
                return a if b == first_node_idx else b
        return 0

    def _merge_collinear(self, path: List[Tuple[int, Segment]]) -> List[Tuple[int, Segment]]:
        """合并共线连续LINE段"""
        if not path:
            return []

        merged = [path[0]]
        for i in range(1, len(path)):
            prev_node, prev_seg = merged[-1]
            curr_node, curr_seg = path[i]

            if (prev_seg.seg_type == "LINE" and curr_seg.seg_type == "LINE"):
                # 检查角度差
                angle_diff = abs(prev_seg.angle - curr_seg.angle)
                if angle_diff < 0.02 or abs(angle_diff - math.pi) < 0.02:  # ~1° 容差
                    # 合并: 延伸前一段
                    new_seg = Segment(prev_seg.start, curr_seg.end,
                                     "LINE", prev_seg.layer)
                    merged[-1] = (curr_node, new_seg)
                    continue

            merged.append(path[i])

        return merged

    def _line_to_modules(self, seg: Segment) -> List[Module]:
        """将直线段拆解为STRAIGHT模块"""
        length = seg.length
        modules = []

        while length > 0:
            # 确定模块长度
            if length <= self.MAX_MODULE_LENGTH:
                mod_len = self._standardize_length(length)
            else:
                mod_len = self.MAX_MODULE_LENGTH

            if mod_len < self.MIN_MODULE_LENGTH and modules:
                # 太短,合并到前一个模块(如果可能)
                prev = modules[-1]
                prev_len = prev.params["length_mm"]
                new_len = prev_len + mod_len
                if new_len <= self.MAX_MODULE_LENGTH:
                    prev.params["length_mm"] = self._standardize_length(new_len)
                    break

            mod = Module("STRAIGHT", {
                "blade_point": self.blade_point,
                "length_mm": mod_len,
                "role": seg.layer,
            })
            mod.segments.append(seg)
            modules.append(mod)
            length -= mod_len

        return modules

    def _arc_to_module(self, seg: Segment) -> Module:
        """将圆弧段转换为ARC模块"""
        angle_deg = math.degrees(seg._arc_angle()) if seg.center else 90
        return Module("ARC", {
            "blade_point": self.blade_point,
            "radius_mm": round(seg.radius, 1),
            "angle_deg": round(angle_deg, 1),
            "role": seg.layer,
        })

    def _insert_corners(self, modules: List[Module]) -> List[Module]:
        """在方向变化处插入转角模块"""
        if len(modules) < 2:
            return modules

        result = [modules[0]]
        for i in range(1, len(modules)):
            prev = modules[i - 1]
            curr = modules[i]

            # 计算方向变化
            if prev.segments and curr.segments:
                prev_angle = prev.segments[-1].angle
                curr_angle = curr.segments[0].angle
                diff = math.degrees(curr_angle - prev_angle)
                diff = ((diff + 180) % 360) - 180  # 归一化到 [-180, 180]

                if abs(diff) > 5:  # >5° 需要转角模块
                    corner_angle = abs(diff)
                    radius = max(self.bp_mm, 1.42)  # 最小弯曲半径

                    corner = Module("CORNER_VAR", {
                        "blade_point": self.blade_point,
                        "angle_deg": round(corner_angle, 1),
                        "inner_radius_mm": radius,
                        "block_mm": max(15, radius * 2 + 8),
                    })
                    result.append(corner)

            result.append(curr)

        return result

    def _add_junction_modules(self):
        """在T形/十字交汇处添加接头模块"""
        for i, node in enumerate(self.graph.nodes):
            deg = self.graph.degree(i)
            if deg == 3:
                self.modules.append(Module("T_JOINT", {
                    "blade_point": self.blade_point,
                    "junction_angle_deg": 90,
                    "position": node.to_dict(),
                }))
            elif deg >= 4:
                self.modules.append(Module("CROSS_JOINT", {
                    "blade_point": self.blade_point,
                    "position": node.to_dict(),
                }))

    def _standardize_length(self, length: float) -> float:
        """将长度对齐到5mm步进"""
        std = round(length / self.LENGTH_STEP) * self.LENGTH_STEP
        return max(self.MIN_MODULE_LENGTH, min(std, self.MAX_MODULE_LENGTH))

    # ─── 统计与输出 ──────────────────────────────────────────────

    def summary(self) -> dict:
        """生成拆解摘要"""
        type_counts = {}
        total_weight = 0
        total_time = 0

        for m in self.modules:
            type_counts[m.mod_type] = type_counts.get(m.mod_type, 0) + 1
            total_weight += m.weight_g
            total_time += m.print_time_min

        unique_params = set()
        for m in self.modules:
            key = f"{m.mod_type}_{json.dumps(m.params, sort_keys=True)}"
            unique_params.add(key)

        reuse_rate = 1 - len(unique_params) / len(self.modules) if self.modules else 0

        return {
            "total_modules": len(self.modules),
            "unique_types": len(unique_params),
            "type_breakdown": type_counts,
            "reuse_rate": round(reuse_rate, 3),
            "total_weight_g": round(total_weight, 1),
            "total_print_time_min": round(total_time, 1),
            "total_print_time_hours": round(total_time / 60, 1),
            "est_material_cost_yuan": round(total_weight * 0.05, 2),
        }

    def to_json(self) -> str:
        return json.dumps({
            "blade_point": self.blade_point,
            "modules": [m.to_dict() for m in self.modules],
            "summary": self.summary(),
        }, ensure_ascii=False, indent=2)

    def to_bom(self) -> str:
        """生成BOM(物料清单)"""
        summary = self.summary()
        lines = ["# 模块物料清单 (BOM)", ""]
        lines.append(f"| 类型 | 数量 | 说明 |")
        lines.append(f"|------|------|------|")
        for t, c in sorted(summary["type_breakdown"].items(), key=lambda x: -x[1]):
            lines.append(f"| {t} | {c} | |")
        lines.append(f"| **总计** | **{summary['total_modules']}** | |")
        lines.append("")
        lines.append(f"- 不同模块种类: {summary['unique_types']}")
        lines.append(f"- 复用率: {summary['reuse_rate']*100:.1f}%")
        lines.append(f"- 总重量: {summary['total_weight_g']:.0f}g")
        lines.append(f"- 总打印时间: {summary['total_print_time_hours']:.1f}小时")
        lines.append(f"- 预估材料成本: ¥{summary['est_material_cost_yuan']:.1f}")
        return "\n".join(lines)


# ─── DXF 解析适配器 ──────────────────────────────────────────────

def parse_dxf_entities(dxf_path: str) -> List[Segment]:
    """解析DXF文件为Segment列表 (需要 ezdxf 库)"""
    segments = []
    try:
        import ezdxf
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        for entity in msp:
            layer = entity.dxf.layer.upper() if hasattr(entity.dxf, "layer") else "CUT"
            # 标准化图层名
            role = "CUT"
            if "CREASE" in layer or "压痕" in layer or "SCORE" in layer:
                role = "CREASE"
            elif "PERF" in layer or "穿孔" in layer:
                role = "PERF"
            elif "GUIDE" in layer or "DIM" in layer or "TEXT" in layer or "辅助" in layer:
                continue  # 跳过辅助图层

            if entity.dxftype() == "LINE":
                s = entity.dxf.start
                e = entity.dxf.end
                segments.append(Segment(
                    Point(s.x, s.y), Point(e.x, e.y), "LINE", role))

            elif entity.dxftype() == "ARC":
                cx, cy = entity.dxf.center.x, entity.dxf.center.y
                r = entity.dxf.radius
                sa = math.radians(entity.dxf.start_angle)
                ea = math.radians(entity.dxf.end_angle)
                sp = Point(cx + r * math.cos(sa), cy + r * math.sin(sa))
                ep = Point(cx + r * math.cos(ea), cy + r * math.sin(ea))
                segments.append(Segment(
                    sp, ep, "ARC", role, radius=r, center=Point(cx, cy)))

            elif entity.dxftype() == "LWPOLYLINE":
                points = list(entity.get_points(format="xyseb"))
                for i in range(len(points) - 1):
                    x1, y1, _, _, b1 = points[i]
                    x2, y2, _, _, _ = points[i + 1]
                    if abs(b1) < 0.001:
                        segments.append(Segment(
                            Point(x1, y1), Point(x2, y2), "LINE", role))
                    else:
                        # bulge → arc
                        dx, dy = x2 - x1, y2 - y1
                        chord = math.hypot(dx, dy)
                        sagitta = abs(b1) * chord / 2
                        r = (chord**2 / 4 + sagitta**2) / (2 * sagitta) if sagitta > 0 else chord
                        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                        # center offset perpendicular to chord
                        d = r - sagitta
                        nx, ny = -dy / chord, dx / chord
                        sign = 1 if b1 > 0 else -1
                        cx, cy = mx + sign * d * nx, my + sign * d * ny
                        segments.append(Segment(
                            Point(x1, y1), Point(x2, y2), "ARC", role,
                            radius=r, center=Point(cx, cy), bulge=b1))

                if entity.closed and len(points) >= 2:
                    x1, y1, _, _, b1 = points[-1]
                    x2, y2, _, _, _ = points[0]
                    segments.append(Segment(
                        Point(x1, y1), Point(x2, y2), "LINE", role))

            elif entity.dxftype() == "CIRCLE":
                cx, cy = entity.dxf.center.x, entity.dxf.center.y
                r = entity.dxf.radius
                # 圆 → 4段弧
                for i in range(4):
                    sa = i * math.pi / 2
                    ea = (i + 1) * math.pi / 2
                    sp = Point(cx + r * math.cos(sa), cy + r * math.sin(sa))
                    ep = Point(cx + r * math.cos(ea), cy + r * math.sin(ea))
                    segments.append(Segment(
                        sp, ep, "ARC", role, radius=r, center=Point(cx, cy)))

    except ImportError:
        print("⚠ ezdxf未安装, 请: pip install ezdxf")
    except Exception as e:
        print(f"⚠ DXF解析错误: {e}")

    return segments


def decompose_dxf(dxf_path: str, blade_point: str = "2pt") -> ModuleDecomposer:
    """便捷函数: DXF → 模块拆解"""
    segments = parse_dxf_entities(dxf_path)
    decomposer = ModuleDecomposer(blade_point)
    decomposer.add_segments(segments)
    decomposer.decompose()
    return decomposer


# ─── 测试用: 生成模拟矩形盒刀模 ──────────────────────────────────

def generate_test_box(L=300, W=200, H=150) -> List[Segment]:
    """生成测试用矩形盒展开图线段"""
    segments = []
    # 简化的 FEFCO 0201 展开图
    # 底板: L×W → 四个侧面: L×H, W×H → 顶盖翻盖
    x0, y0 = 0, 0

    # 底板矩形
    pts = [
        (x0, y0), (x0 + L, y0), (x0 + L, y0 + W), (x0, y0 + W), (x0, y0)
    ]
    for i in range(len(pts) - 1):
        segments.append(Segment(
            Point(pts[i][0], pts[i][1]),
            Point(pts[i+1][0], pts[i+1][1]),
            "LINE", "CUT"))

    # 左侧面
    pts_l = [
        (x0 - H, y0), (x0, y0), (x0, y0 + W), (x0 - H, y0 + W), (x0 - H, y0)
    ]
    for i in range(len(pts_l) - 1):
        segments.append(Segment(
            Point(pts_l[i][0], pts_l[i][1]),
            Point(pts_l[i+1][0], pts_l[i+1][1]),
            "LINE", "CUT"))

    # 右侧面
    pts_r = [
        (x0 + L, y0), (x0 + L + H, y0),
        (x0 + L + H, y0 + W), (x0 + L, y0 + W)
    ]
    for i in range(len(pts_r) - 1):
        segments.append(Segment(
            Point(pts_r[i][0], pts_r[i][1]),
            Point(pts_r[i+1][0], pts_r[i+1][1]),
            "LINE", "CUT"))

    # 折痕线 (压痕)
    for x in [x0, x0 + L]:
        segments.append(Segment(
            Point(x, y0), Point(x, y0 + W), "LINE", "CREASE"))

    return segments


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1].endswith((".dxf", ".DXF")):
        # 解析DXF文件
        dxf_path = sys.argv[1]
        bp = sys.argv[2] if len(sys.argv) > 2 else "2pt"
        print(f"解析: {dxf_path} (刀片: {bp})")
        decomposer = decompose_dxf(dxf_path, bp)
    else:
        # 使用测试盒
        L = int(sys.argv[1]) if len(sys.argv) > 1 else 300
        W = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        H = int(sys.argv[3]) if len(sys.argv) > 3 else 150
        print(f"测试盒: {L}×{W}×{H}mm")

        segs = generate_test_box(L, W, H)
        decomposer = ModuleDecomposer("2pt")
        decomposer.add_segments(segs)
        decomposer.decompose()

    print(f"\n{decomposer.to_bom()}")

    # 保存JSON
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "module_list.json")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(decomposer.to_json())
    print(f"\n输出: {out_path}")
