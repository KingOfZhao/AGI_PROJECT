#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DXF工艺图纸生成技能 — 用ezdxf生成工艺步骤图纸
===============================================
核心能力:
  1. 从工艺规划JSON生成工序流程图DXF
  2. 绘制零件轮廓+加工标注DXF
  3. 生成热处理温度曲线DXF
  4. 创建Mastercam可导入的DXF模板

参考: ezdxf (https://github.com/mozman/ezdxf)
"""

import sys
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SKILL_META = {
    "name": "cad_drawing_generator",
    "display_name": "DXF工艺图纸生成器",
    "description": "用ezdxf生成工艺步骤DXF图纸: 工序流程图/零件标注图/热处理曲线/Mastercam可导入模板",
    "tags": ["CAD", "DXF", "ezdxf", "图纸生成", "工艺图", "工业制造"],
    "capabilities": [
        "generate_process_flow_dxf: 工艺步骤流程图",
        "generate_part_outline_dxf: 零件轮廓+标注",
        "generate_heat_treatment_curve: 热处理温度曲线",
        "generate_flange_dxf: 参数化法兰盘图纸",
    ],
}


def _ensure_ezdxf():
    try:
        import ezdxf
        return ezdxf
    except ImportError:
        raise ImportError("ezdxf未安装, 请运行: pip install ezdxf")


def _default_output(name: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = PROJECT_ROOT / "workspace" / "outputs" / f"{name}_{ts}.dxf"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


# ==================== 工序流程图 ====================

def generate_process_flow_dxf(
    steps: List[Dict],
    title: str = "工艺流程图",
    output_path: str = None,
) -> Dict[str, Any]:
    """
    从工艺步骤列表生成DXF工序流程图

    Args:
        steps: [{"step": 1, "operation": "车削", "description": "...", ...}, ...]
        title: 图纸标题
        output_path: 输出DXF路径

    Returns:
        {"success": bool, "path": str, "steps_count": int}
    """
    ezdxf = _ensure_ezdxf()
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # 标题
    msp.add_text(title, dxfattribs={
        "height": 8, "insert": (10, 20 + len(steps) * 40 + 20),
        "style": "Standard",
    })

    box_w, box_h = 120, 25
    start_x, start_y = 30, 20 + (len(steps) - 1) * 40
    arrow_len = 15

    for i, step in enumerate(steps):
        x = start_x
        y = start_y - i * 40

        # 画框
        msp.add_lwpolyline(
            [(x, y), (x + box_w, y), (x + box_w, y + box_h), (x, y + box_h), (x, y)],
            close=True,
        )

        # 步骤编号+工序名
        step_num = step.get("step", i + 1)
        op_name = step.get("operation", step.get("category", f"步骤{step_num}"))
        msp.add_text(f"[{step_num}] {op_name}", dxfattribs={
            "height": 4, "insert": (x + 3, y + box_h - 8),
        })

        # 描述
        desc = step.get("description", step.get("action", ""))[:50]
        if desc:
            msp.add_text(desc, dxfattribs={
                "height": 2.5, "insert": (x + 3, y + 4),
            })

        # 右侧参数标注
        tool = step.get("tool", step.get("tools_required", ""))
        if isinstance(tool, list):
            tool = ", ".join(tool[:2])
        if tool:
            msp.add_text(f"工具: {str(tool)[:30]}", dxfattribs={
                "height": 2, "insert": (x + box_w + 5, y + box_h - 6),
            })

        params = step.get("parameters", {})
        if isinstance(params, dict):
            param_text = ", ".join(f"{k}={v}" for k, v in list(params.items())[:3])
            if param_text:
                msp.add_text(param_text[:40], dxfattribs={
                    "height": 2, "insert": (x + box_w + 5, y + 4),
                })

        # 箭头连接下一步
        if i < len(steps) - 1:
            cx = x + box_w / 2
            msp.add_line((cx, y), (cx, y - arrow_len))
            # 箭头头部
            msp.add_line((cx, y - arrow_len), (cx - 2, y - arrow_len + 4))
            msp.add_line((cx, y - arrow_len), (cx + 2, y - arrow_len + 4))

    # 保存
    out = Path(output_path) if output_path else _default_output("process_flow")
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out))

    return {"success": True, "path": str(out), "steps_count": len(steps)}


# ==================== 零件轮廓+标注 ====================

def generate_part_outline_dxf(
    width: float, height: float,
    holes: List[Dict] = None,
    chamfers: List[Dict] = None,
    title: str = "零件图",
    material: str = "",
    output_path: str = None,
) -> Dict[str, Any]:
    """
    生成零件轮廓 + 尺寸标注 DXF

    Args:
        width: 零件宽度(mm)
        height: 零件高度(mm)
        holes: [{"x": cx, "y": cy, "d": diameter}, ...]
        chamfers: [{"x": x, "y": y, "size": c}, ...] 倒角
        title: 标题
        material: 材料
        output_path: 输出路径
    """
    ezdxf = _ensure_ezdxf()
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # 外轮廓
    msp.add_lwpolyline(
        [(0, 0), (width, 0), (width, height), (0, height), (0, 0)],
        close=True,
    )

    # 尺寸标注 (简化版 — 用文字+线段模拟)
    # 底边尺寸
    dim_offset = -8
    msp.add_line((0, dim_offset), (width, dim_offset))
    msp.add_line((0, 0), (0, dim_offset - 2))
    msp.add_line((width, 0), (width, dim_offset - 2))
    msp.add_text(f"{width}", dxfattribs={
        "height": 3, "insert": (width / 2 - 5, dim_offset - 4),
    })

    # 左边尺寸
    dim_offset_x = -8
    msp.add_line((dim_offset_x, 0), (dim_offset_x, height))
    msp.add_line((0, 0), (dim_offset_x - 2, 0))
    msp.add_line((0, height), (dim_offset_x - 2, height))
    msp.add_text(f"{height}", dxfattribs={
        "height": 3, "insert": (dim_offset_x - 8, height / 2 - 1.5),
    })

    # 孔
    holes = holes or []
    for h in holes:
        cx, cy, d = h.get("x", 0), h.get("y", 0), h.get("d", 10)
        msp.add_circle((cx, cy), radius=d / 2)
        # 标注
        msp.add_text(f"∅{d}", dxfattribs={
            "height": 2.5, "insert": (cx + d / 2 + 2, cy),
        })

    # 标题栏
    title_y = -20
    msp.add_lwpolyline(
        [(0, title_y), (width, title_y), (width, title_y - 15), (0, title_y - 15), (0, title_y)],
        close=True,
    )
    msp.add_text(title, dxfattribs={"height": 4, "insert": (3, title_y - 6)})
    if material:
        msp.add_text(f"材料: {material}", dxfattribs={"height": 2.5, "insert": (3, title_y - 12)})

    ts = datetime.now().strftime("%Y-%m-%d")
    msp.add_text(f"日期: {ts}", dxfattribs={"height": 2, "insert": (width - 40, title_y - 12)})

    out = Path(output_path) if output_path else _default_output("part_outline")
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out))

    return {"success": True, "path": str(out), "holes_count": len(holes)}


# ==================== 热处理温度曲线 ====================

def generate_heat_treatment_curve(
    steps: List[Dict],
    title: str = "热处理工艺曲线",
    output_path: str = None,
) -> Dict[str, Any]:
    """
    生成热处理温度曲线DXF

    Args:
        steps: [
            {"process": "升温", "start_temp": 20, "end_temp": 850, "duration_min": 60},
            {"process": "保温", "start_temp": 850, "end_temp": 850, "duration_min": 30},
            {"process": "淬火", "start_temp": 850, "end_temp": 50, "duration_min": 5},
            ...
        ]
    """
    ezdxf = _ensure_ezdxf()
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # 坐标系参数
    origin_x, origin_y = 30, 30
    x_scale = 2.0    # mm per minute
    y_scale = 0.15   # mm per °C
    max_temp = max(max(s.get("start_temp", 0), s.get("end_temp", 0)) for s in steps) if steps else 1000
    total_time = sum(s.get("duration_min", 0) for s in steps)

    chart_w = total_time * x_scale + 20
    chart_h = max_temp * y_scale + 20

    # 坐标轴
    msp.add_line((origin_x, origin_y), (origin_x + chart_w, origin_y))  # X轴
    msp.add_line((origin_x, origin_y), (origin_x, origin_y + chart_h))  # Y轴

    # 轴标签
    msp.add_text("时间(min)", dxfattribs={"height": 3, "insert": (origin_x + chart_w / 2, origin_y - 10)})
    msp.add_text("温度(°C)", dxfattribs={"height": 3, "insert": (origin_x - 25, origin_y + chart_h / 2)})

    # Y轴刻度
    for temp in range(0, int(max_temp) + 1, 100):
        y = origin_y + temp * y_scale
        msp.add_line((origin_x - 2, y), (origin_x + 2, y))
        msp.add_text(str(temp), dxfattribs={"height": 2, "insert": (origin_x - 15, y - 1)})

    # 绘制曲线
    current_time = 0
    points = []
    for s in steps:
        t_start = current_time
        t_end = current_time + s.get("duration_min", 0)
        temp_start = s.get("start_temp", 20)
        temp_end = s.get("end_temp", 20)

        x1 = origin_x + t_start * x_scale
        y1 = origin_y + temp_start * y_scale
        x2 = origin_x + t_end * x_scale
        y2 = origin_y + temp_end * y_scale

        msp.add_line((x1, y1), (x2, y2))
        points.append((x1, y1))

        # 标注工序名
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        msp.add_text(s.get("process", ""), dxfattribs={
            "height": 2.5, "insert": (mx, my + 5),
        })

        current_time = t_end

    # 标题
    msp.add_text(title, dxfattribs={
        "height": 5, "insert": (origin_x, origin_y + chart_h + 10),
    })

    out = Path(output_path) if output_path else _default_output("heat_treatment_curve")
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out))

    return {"success": True, "path": str(out), "steps_count": len(steps)}


# ==================== 参数化法兰盘 ====================

def generate_flange_dxf(
    outer_d: float = 100,
    inner_d: float = 60,
    bolt_circle_d: float = 80,
    bolt_count: int = 4,
    bolt_hole_d: float = 9,
    thickness: float = 20,
    material: str = "45#钢",
    output_path: str = None,
) -> Dict[str, Any]:
    """
    生成参数化法兰盘DXF图纸 (主视图+侧视图)

    Args:
        outer_d: 外径(mm)
        inner_d: 内径(mm)
        bolt_circle_d: 螺栓孔分布圆直径(mm)
        bolt_count: 螺栓孔数量
        bolt_hole_d: 螺栓孔直径(mm)
        thickness: 厚度(mm)
        material: 材料
    """
    ezdxf = _ensure_ezdxf()
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    cx, cy = 0, 0  # 主视图中心
    or_ = outer_d / 2
    ir = inner_d / 2
    bcr = bolt_circle_d / 2
    bhr = bolt_hole_d / 2

    # === 主视图 (正面) ===
    msp.add_circle((cx, cy), radius=or_)
    msp.add_circle((cx, cy), radius=ir)
    msp.add_circle((cx, cy), radius=bcr, dxfattribs={"linetype": "CENTER"})

    # 螺栓孔 (均布)
    for i in range(bolt_count):
        angle = math.radians(360 / bolt_count * i + 90)
        hx = cx + bcr * math.cos(angle)
        hy = cy + bcr * math.sin(angle)
        msp.add_circle((hx, hy), radius=bhr)

    # 中心线
    cl_ext = or_ + 10
    msp.add_line((cx - cl_ext, cy), (cx + cl_ext, cy))
    msp.add_line((cx, cy - cl_ext), (cx, cy + cl_ext))

    # 尺寸标注 (文字模拟)
    msp.add_text(f"∅{outer_d}", dxfattribs={"height": 3, "insert": (cx + or_ + 5, cy + 5)})
    msp.add_text(f"∅{inner_d}", dxfattribs={"height": 3, "insert": (cx + ir + 3, cy - 8)})
    msp.add_text(f"{bolt_count}-∅{bolt_hole_d} 均布", dxfattribs={"height": 2.5, "insert": (cx + bcr + bhr + 3, cy + bcr / 2)})
    msp.add_text(f"PCD ∅{bolt_circle_d}", dxfattribs={"height": 2, "insert": (cx - bcr - 20, cy + bcr + 5)})

    # === 侧视图 (右侧) ===
    sx = cx + or_ + 40  # 侧视图起始X
    # 外轮廓矩形
    msp.add_lwpolyline([
        (sx, cy - or_), (sx + thickness, cy - or_),
        (sx + thickness, cy + or_), (sx, cy + or_),
        (sx, cy - or_),
    ], close=True)
    # 内孔虚线
    msp.add_line((sx, cy - ir), (sx + thickness, cy - ir))
    msp.add_line((sx, cy + ir), (sx + thickness, cy + ir))
    # 厚度标注
    msp.add_text(f"{thickness}", dxfattribs={
        "height": 3, "insert": (sx + thickness / 2 - 3, cy - or_ - 8),
    })

    # === 标题栏 ===
    ty = cy - or_ - 25
    tw = or_ * 2 + thickness + 60
    msp.add_lwpolyline([
        (cx - or_ - 10, ty), (cx - or_ - 10 + tw, ty),
        (cx - or_ - 10 + tw, ty - 20), (cx - or_ - 10, ty - 20),
        (cx - or_ - 10, ty),
    ], close=True)
    msp.add_text(f"法兰盘 ∅{outer_d}×{thickness}", dxfattribs={"height": 4, "insert": (cx - or_ - 5, ty - 7)})
    msp.add_text(f"材料: {material}", dxfattribs={"height": 2.5, "insert": (cx - or_ - 5, ty - 15)})
    msp.add_text(f"比例: 1:1  日期: {datetime.now().strftime('%Y-%m-%d')}", dxfattribs={
        "height": 2, "insert": (cx + 20, ty - 15),
    })

    out = Path(output_path) if output_path else _default_output("flange")
    if not out.is_absolute():
        out = PROJECT_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out))

    return {
        "success": True,
        "path": str(out),
        "params": {
            "outer_d": outer_d, "inner_d": inner_d,
            "bolt_circle_d": bolt_circle_d, "bolt_count": bolt_count,
            "bolt_hole_d": bolt_hole_d, "thickness": thickness,
            "material": material,
        },
    }


# ==================== 自测 ====================

if __name__ == "__main__":
    print("=== DXF工艺图纸生成器 自测 ===\n")

    # 1. 工序流程图
    print("--- 工序流程图 ---")
    steps = [
        {"step": 1, "operation": "下料", "description": "45#钢棒料 ∅110×25", "tools_required": ["带锯床"]},
        {"step": 2, "operation": "粗车", "description": "车外圆∅102, 内孔∅58, 厚度21", "tools_required": ["CA6140车床"], "parameters": {"转速": "500RPM", "进给": "0.3mm/r"}},
        {"step": 3, "operation": "精车", "description": "车外圆∅100h7, 内孔∅60H7, 厚度20", "tools_required": ["CA6140车床"], "parameters": {"转速": "800RPM", "进给": "0.1mm/r"}},
        {"step": 4, "operation": "钻孔", "description": "钻4-∅6.8底孔(M8螺纹)", "tools_required": ["台钻", "∅6.8钻头"]},
        {"step": 5, "operation": "攻丝", "description": "攻M8螺纹×4", "tools_required": ["M8丝锥"]},
        {"step": 6, "operation": "热处理", "description": "调质处理 HRC28-32", "tools_required": ["箱式电炉"]},
        {"step": 7, "operation": "磨削", "description": "磨两端面 Ra1.6", "tools_required": ["平面磨床"]},
        {"step": 8, "operation": "检验", "description": "检查全部尺寸、粗糙度、硬度", "tools_required": ["三坐标", "粗糙度仪"]},
    ]
    r = generate_process_flow_dxf(steps, "45#钢法兰盘工艺流程图")
    print(f"  输出: {r['path']}")

    # 2. 法兰盘图纸
    print("\n--- 法兰盘参数化图纸 ---")
    r = generate_flange_dxf(outer_d=100, inner_d=60, bolt_circle_d=80, bolt_count=4, bolt_hole_d=9, thickness=20)
    print(f"  输出: {r['path']}")

    # 3. 热处理曲线
    print("\n--- 热处理温度曲线 ---")
    ht_steps = [
        {"process": "升温", "start_temp": 20, "end_temp": 850, "duration_min": 60},
        {"process": "保温淬火", "start_temp": 850, "end_temp": 850, "duration_min": 30},
        {"process": "水淬", "start_temp": 850, "end_temp": 50, "duration_min": 2},
        {"process": "升温", "start_temp": 50, "end_temp": 550, "duration_min": 40},
        {"process": "保温回火", "start_temp": 550, "end_temp": 550, "duration_min": 60},
        {"process": "空冷", "start_temp": 550, "end_temp": 20, "duration_min": 120},
    ]
    r = generate_heat_treatment_curve(ht_steps, "45#钢调质处理工艺曲线")
    print(f"  输出: {r['path']}")

    print("\n=== 自测完成 ===")
