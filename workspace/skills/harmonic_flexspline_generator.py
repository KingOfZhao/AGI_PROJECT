#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
谐波减速器柔性环(Flexspline)参数化CAD生成器
=============================================
用CadQuery生成3D STEP + 用ezdxf生成2D工程图

柔性环结构:
  - 薄壁杯形体(开口端带外齿)
  - 杯底法兰(连接输出轴)
  - 外齿轮齿形(渐开线齿形简化为梯形近似)

典型参数(SHF-25型):
  齿数z=100, 模数m=0.5, 外径≈50mm, 壁厚0.3mm, 杯深30mm
"""

import math
import sys
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "workspace" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 参数定义 ====================

class FlexsplineParams:
    """柔性环参数集"""
    def __init__(
        self,
        module: float = 0.5,         # 模数(mm)
        teeth: int = 100,            # 齿数
        wall_thickness: float = 0.3, # 壁厚(mm)
        cup_depth: float = 30.0,     # 杯深(mm)
        flange_thickness: float = 3.0,  # 法兰厚度(mm)
        flange_od: float = 20.0,     # 法兰外径(mm) — 输出轴连接
        shaft_bore: float = 10.0,    # 轴孔直径(mm)
        bolt_count: int = 4,         # 法兰螺栓孔数
        bolt_hole_d: float = 3.2,    # 螺栓孔直径(mm)
        bolt_circle_d: float = 16.0, # 螺栓分布圆直径(mm)
        tooth_height_factor: float = 2.25,  # 齿高系数(ha*+c*)
        addendum_factor: float = 1.0,       # 齿顶高系数
        pressure_angle: float = 20.0,       # 压力角(度)
        name: str = "SHF-25",
    ):
        self.module = module
        self.teeth = teeth
        self.wall_thickness = wall_thickness
        self.cup_depth = cup_depth
        self.flange_thickness = flange_thickness
        self.flange_od = flange_od
        self.shaft_bore = shaft_bore
        self.bolt_count = bolt_count
        self.bolt_hole_d = bolt_hole_d
        self.bolt_circle_d = bolt_circle_d
        self.tooth_height_factor = tooth_height_factor
        self.addendum_factor = addendum_factor
        self.pressure_angle = pressure_angle
        self.name = name

        # 派生参数
        self.pitch_diameter = module * teeth          # 分度圆直径
        self.addendum = module * addendum_factor      # 齿顶高
        self.dedendum = module * (tooth_height_factor - addendum_factor)  # 齿根高
        self.tip_diameter = self.pitch_diameter + 2 * self.addendum       # 齿顶圆直径
        self.root_diameter = self.pitch_diameter - 2 * self.dedendum      # 齿根圆直径
        self.outer_diameter = self.tip_diameter       # 外径(含齿)
        self.inner_diameter = self.root_diameter - 2 * wall_thickness     # 内径
        self.tooth_height = self.addendum + self.dedendum                 # 全齿高

    def summary(self) -> str:
        return (
            f"谐波减速器柔性环 [{self.name}]\n"
            f"  齿数={self.teeth}, 模数={self.module}mm, 压力角={self.pressure_angle}°\n"
            f"  分度圆∅{self.pitch_diameter:.1f}, 齿顶圆∅{self.tip_diameter:.1f}, 齿根圆∅{self.root_diameter:.1f}\n"
            f"  壁厚={self.wall_thickness}mm, 杯深={self.cup_depth}mm\n"
            f"  法兰∅{self.flange_od}×{self.flange_thickness}mm, 轴孔∅{self.shaft_bore}mm\n"
            f"  {self.bolt_count}-∅{self.bolt_hole_d}螺栓孔 PCD∅{self.bolt_circle_d}"
        )


# ==================== CadQuery 3D模型 ====================

def generate_3d_step(params: FlexsplineParams = None, output_path: str = None) -> dict:
    """
    用CadQuery生成柔性环3D STEP文件

    简化策略: 齿形用梯形近似(真实渐开线需要FreeCAD Gear workbench)
    杯体用回转体(revolve) + 齿用阵列(polarArray)
    """
    if params is None:
        params = FlexsplineParams()

    try:
        import cadquery as cq
    except ImportError:
        return {"success": False, "error": "cadquery未安装: pip install cadquery"}

    p = params
    r_root = p.root_diameter / 2
    r_tip = p.tip_diameter / 2
    r_inner = r_root - p.wall_thickness
    tooth_zone_height = min(10.0, p.cup_depth * 0.4)

    # --- 1. 齿形轮廓多边形(单次构建所有齿, 避免N次布尔union) ---
    tooth_angle = 2 * math.pi / p.teeth
    tip_half_angle = tooth_angle * 0.17   # 齿顶半角
    root_half_angle = tooth_angle * 0.27  # 齿根半角

    gear_points = []
    for i in range(p.teeth):
        ca = tooth_angle * i
        a1 = ca - tooth_angle / 2 + (tooth_angle / 2 - root_half_angle)
        gear_points.append((r_root * math.cos(a1), r_root * math.sin(a1)))
        a2 = ca - tip_half_angle
        gear_points.append((r_tip * math.cos(a2), r_tip * math.sin(a2)))
        a3 = ca + tip_half_angle
        gear_points.append((r_tip * math.cos(a3), r_tip * math.sin(a3)))
        a4 = ca + root_half_angle
        gear_points.append((r_root * math.cos(a4), r_root * math.sin(a4)))
    gear_points.append(gear_points[0])

    # 齿环: 多边形外轮廓一次性挤出, 再减内孔
    wp = cq.Workplane("XY").transformed(offset=(0, 0, p.cup_depth - tooth_zone_height))
    wp = wp.moveTo(gear_points[0][0], gear_points[0][1])
    for pt in gear_points[1:]:
        wp = wp.lineTo(pt[0], pt[1])
    wp = wp.close()
    gear_outer = wp.extrude(tooth_zone_height)

    gear_hole = (
        cq.Workplane("XY")
        .transformed(offset=(0, 0, p.cup_depth - tooth_zone_height))
        .circle(r_inner)
        .extrude(tooth_zone_height)
    )
    gear_ring = gear_outer.cut(gear_hole)

    # --- 2. 杯体(无齿段薄壁) ---
    cup_plain_h = p.cup_depth - tooth_zone_height - p.flange_thickness
    cup_plain = (
        cq.Workplane("XY")
        .transformed(offset=(0, 0, p.flange_thickness))
        .circle(r_root).circle(r_inner)
        .extrude(cup_plain_h)
    )

    # --- 3. 杯底法兰 + 轴孔 + 螺栓孔 ---
    flange = (
        cq.Workplane("XY")
        .circle(max(r_inner, p.flange_od / 2))
        .circle(p.shaft_bore / 2)
        .extrude(p.flange_thickness)
    )
    bolt_r = p.bolt_circle_d / 2
    bolt_holes = (
        cq.Workplane("XY")
        .polarArray(bolt_r, 0, 360, p.bolt_count)
        .circle(p.bolt_hole_d / 2)
        .extrude(p.flange_thickness)
    )
    flange = flange.cut(bolt_holes)

    # --- 4. 组合(仅3次union, 而非N次) ---
    result = flange.union(cup_plain).union(gear_ring)

    # --- 5. 导出STEP ---
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(OUTPUT_DIR / f"flexspline_{p.name}_{ts}.step")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cq.exporters.export(result, str(out))

    return {
        "success": True,
        "path": str(out),
        "format": "STEP",
        "params": params.summary(),
        "size_bytes": out.stat().st_size,
    }


# ==================== ezdxf 2D工程图 ====================

def generate_2d_drawing(params: FlexsplineParams = None, output_path: str = None) -> dict:
    """
    用ezdxf生成柔性环2D工程图:
      - 主视图: 纵剖面(半剖)
      - 俯视图: 齿形端面(含齿)
      - 标注: 关键尺寸
      - 标题栏
    """
    if params is None:
        params = FlexsplineParams()

    import ezdxf

    p = params
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    r_root = p.root_diameter / 2
    r_tip = p.tip_diameter / 2
    r_inner = r_root - p.wall_thickness
    r_pitch = p.pitch_diameter / 2

    # ========= 俯视图(端面) — 放在上方 =========
    cx, cy = 0, p.cup_depth + 40 + r_tip  # 中心位置

    # 齿顶圆
    msp.add_circle((cx, cy), radius=r_tip)
    # 齿根圆(虚线用细线表示)
    msp.add_circle((cx, cy), radius=r_root)
    # 分度圆(点划线)
    msp.add_circle((cx, cy), radius=r_pitch)
    # 内壁圆
    msp.add_circle((cx, cy), radius=r_inner)
    # 轴孔
    msp.add_circle((cx, cy), radius=p.shaft_bore / 2)
    # 法兰外圆
    msp.add_circle((cx, cy), radius=p.flange_od / 2)

    # 螺栓孔
    bolt_r = p.bolt_circle_d / 2
    for i in range(p.bolt_count):
        angle = math.radians(360 / p.bolt_count * i + 90)
        hx = cx + bolt_r * math.cos(angle)
        hy = cy + bolt_r * math.sin(angle)
        msp.add_circle((hx, hy), radius=p.bolt_hole_d / 2)

    # 中心线
    cl = r_tip + 8
    msp.add_line((cx - cl, cy), (cx + cl, cy))
    msp.add_line((cx, cy - cl), (cx, cy + cl))

    # 简化齿形示意(画几个齿)
    for i in range(0, p.teeth, max(1, p.teeth // 20)):
        angle = 2 * math.pi * i / p.teeth
        # 齿根到齿顶的径向线
        x1 = cx + r_root * math.cos(angle)
        y1 = cy + r_root * math.sin(angle)
        x2 = cx + r_tip * math.cos(angle)
        y2 = cy + r_tip * math.sin(angle)
        msp.add_line((x1, y1), (x2, y2))

    # 俯视图标注
    msp.add_text(f"∅{p.tip_diameter:.1f} 齿顶圆", dxfattribs={"height": 2, "insert": (cx + r_tip + 3, cy + 5)})
    msp.add_text(f"∅{p.pitch_diameter:.1f} 分度圆", dxfattribs={"height": 2, "insert": (cx + r_pitch + 3, cy - 5)})
    msp.add_text(f"∅{p.root_diameter:.1f} 齿根圆", dxfattribs={"height": 2, "insert": (cx + r_root + 3, cy - 10)})
    msp.add_text(f"∅{p.shaft_bore} 轴孔", dxfattribs={"height": 1.8, "insert": (cx + p.shaft_bore / 2 + 2, cy + 2)})
    msp.add_text(f"z={p.teeth}, m={p.module}", dxfattribs={"height": 2.5, "insert": (cx - r_tip, cy + r_tip + 5)})

    # ========= 主视图(纵剖面 半剖) — 放在下方 =========
    sx = -r_tip - 5   # 主视图左边起点
    sy = 0            # 基线Y
    cup_h = p.cup_depth
    ft = p.flange_thickness
    wt = p.wall_thickness
    th = p.tooth_height

    # 外轮廓(右半 — 剖面)
    # 杯底法兰(右侧)
    pts_outer_right = [
        (0, sy),                                   # 中心线底部
        (p.flange_od / 2, sy),                     # 法兰外径底部
        (p.flange_od / 2, sy + ft),                # 法兰外径顶部
        (r_root, sy + ft),                         # 过渡到薄壁
        (r_root, sy + cup_h - 0),                  # 薄壁外壁顶部(齿根)
        (r_tip, sy + cup_h),                       # 齿顶(开口端)
    ]
    for i in range(len(pts_outer_right) - 1):
        msp.add_line(pts_outer_right[i], pts_outer_right[i + 1])

    # 内轮廓(右侧)
    pts_inner_right = [
        (p.shaft_bore / 2, sy),                    # 轴孔底部
        (p.shaft_bore / 2, sy + ft),               # 轴孔顶部(法兰内)
        (r_inner, sy + ft),                        # 过渡到内壁
        (r_inner, sy + cup_h),                     # 内壁顶部(开口端)
    ]
    for i in range(len(pts_inner_right) - 1):
        msp.add_line(pts_inner_right[i], pts_inner_right[i + 1])

    # 顶边(开口端)
    msp.add_line((r_inner, sy + cup_h), (r_tip, sy + cup_h))

    # 底边
    msp.add_line((p.shaft_bore / 2, sy), (p.flange_od / 2, sy))

    # 左半(镜像 — 外视图)
    pts_outer_left = [(-x, y) for x, y in pts_outer_right]
    for i in range(len(pts_outer_left) - 1):
        msp.add_line(pts_outer_left[i], pts_outer_left[i + 1])

    pts_inner_left = [(-x, y) for x, y in pts_inner_right]
    for i in range(len(pts_inner_left) - 1):
        msp.add_line(pts_inner_left[i], pts_inner_left[i + 1])

    msp.add_line((-r_inner, sy + cup_h), (-r_tip, sy + cup_h))
    msp.add_line((-p.shaft_bore / 2, sy), (-p.flange_od / 2, sy))

    # 中心线(纵)
    msp.add_line((0, sy - 5), (0, sy + cup_h + 5))

    # 剖面线(右半填充区域 — 简化用对角线表示)
    hatch_spacing = 2.0
    for y_offset in range(int(ft / hatch_spacing) + 1):
        yy = sy + y_offset * hatch_spacing
        if yy <= sy + ft:
            msp.add_line((p.shaft_bore / 2 + 0.5, yy), (p.flange_od / 2 - 0.5, yy))

    # ========= 尺寸标注 =========
    dim_x = r_tip + 15

    # 杯深
    msp.add_line((dim_x, sy), (dim_x + 5, sy))
    msp.add_line((dim_x, sy + cup_h), (dim_x + 5, sy + cup_h))
    msp.add_line((dim_x + 2, sy), (dim_x + 2, sy + cup_h))
    msp.add_text(f"{cup_h}", dxfattribs={"height": 2.5, "insert": (dim_x + 4, sy + cup_h / 2)})

    # 法兰厚度
    dim_x2 = r_tip + 25
    msp.add_line((dim_x2, sy), (dim_x2 + 5, sy))
    msp.add_line((dim_x2, sy + ft), (dim_x2 + 5, sy + ft))
    msp.add_line((dim_x2 + 2, sy), (dim_x2 + 2, sy + ft))
    msp.add_text(f"{ft}", dxfattribs={"height": 2, "insert": (dim_x2 + 4, sy + ft / 2)})

    # 壁厚标注
    msp.add_text(f"壁厚={wt}", dxfattribs={"height": 2, "insert": (r_root + 3, sy + cup_h / 2)})

    # 外径标注
    msp.add_text(f"∅{p.tip_diameter:.1f}", dxfattribs={"height": 2.5, "insert": (-r_tip - 15, sy + cup_h + 3)})

    # ========= 标题栏 =========
    title_y = sy - 15
    title_w = 2 * (r_tip + 30)
    title_x = -(r_tip + 15)
    msp.add_lwpolyline([
        (title_x, title_y), (title_x + title_w, title_y),
        (title_x + title_w, title_y - 25), (title_x, title_y - 25),
        (title_x, title_y),
    ], close=True)

    msp.add_text(f"谐波减速器柔性环 [{p.name}]", dxfattribs={"height": 4, "insert": (title_x + 3, title_y - 8)})
    msp.add_text(f"z={p.teeth} m={p.module} α={p.pressure_angle}°", dxfattribs={"height": 2.5, "insert": (title_x + 3, title_y - 15)})
    msp.add_text(f"材料: 40CrNiMoA (弹性合金钢)", dxfattribs={"height": 2.5, "insert": (title_x + 3, title_y - 21)})
    msp.add_text(f"日期: {datetime.now().strftime('%Y-%m-%d')}", dxfattribs={"height": 2, "insert": (title_x + title_w - 40, title_y - 21)})

    # ========= 参数表 =========
    table_x = -(r_tip + 15)
    table_y = title_y - 30
    params_text = [
        f"分度圆直径: ∅{p.pitch_diameter:.1f}mm",
        f"齿顶圆直径: ∅{p.tip_diameter:.1f}mm",
        f"齿根圆直径: ∅{p.root_diameter:.1f}mm",
        f"杯深: {p.cup_depth}mm  壁厚: {p.wall_thickness}mm",
        f"法兰: ∅{p.flange_od}×{p.flange_thickness}mm  轴孔∅{p.shaft_bore}mm",
        f"{p.bolt_count}-∅{p.bolt_hole_d}螺栓孔 PCD∅{p.bolt_circle_d}mm",
    ]
    for i, txt in enumerate(params_text):
        msp.add_text(txt, dxfattribs={"height": 2, "insert": (table_x, table_y - i * 4)})

    # 导出
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(OUTPUT_DIR / f"flexspline_2d_{p.name}_{ts}.dxf")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out))

    return {
        "success": True,
        "path": str(out),
        "format": "DXF",
        "params": params.summary(),
    }


# ==================== 主入口 ====================

def generate_flexspline(
    module: float = 0.5,
    teeth: int = 100,
    wall_thickness: float = 0.3,
    cup_depth: float = 30.0,
    name: str = "SHF-25",
    generate_step: bool = True,
    generate_dxf: bool = True,
) -> dict:
    """
    一键生成谐波减速器柔性环CAD文件

    Returns:
        {"success": bool, "step_path": str, "dxf_path": str, "params": str}
    """
    params = FlexsplineParams(
        module=module, teeth=teeth,
        wall_thickness=wall_thickness, cup_depth=cup_depth,
        name=name,
    )

    results = {"success": True, "params": params.summary()}

    if generate_dxf:
        dxf_result = generate_2d_drawing(params)
        results["dxf_path"] = dxf_result.get("path", "")
        results["dxf_success"] = dxf_result["success"]

    if generate_step:
        step_result = generate_3d_step(params)
        results["step_path"] = step_result.get("path", "")
        results["step_success"] = step_result["success"]
        if not step_result["success"]:
            results["step_error"] = step_result.get("error", "")

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("谐波减速器柔性环(Flexspline) CAD生成器")
    print("=" * 60)

    p = FlexsplineParams()
    print(f"\n{p.summary()}\n")

    # 先生成2D(必定成功)
    print("--- 生成2D工程图(ezdxf) ---")
    r2d = generate_2d_drawing(p)
    print(f"  {'✅' if r2d['success'] else '❌'} {r2d.get('path', r2d.get('error', ''))}")

    # 再尝试3D
    print("\n--- 生成3D STEP(CadQuery) ---")
    try:
        r3d = generate_3d_step(p)
        print(f"  {'✅' if r3d['success'] else '❌'} {r3d.get('path', r3d.get('error', ''))}")
        if r3d.get("size_bytes"):
            print(f"  文件大小: {r3d['size_bytes'] / 1024:.1f} KB")
    except Exception as e:
        print(f"  ❌ 3D生成异常: {e}")
        print("  提示: 100齿union操作较慢, 可减少齿数测试")

    print("\n完成!")
