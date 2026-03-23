#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD 文件识别与解析技能 — 真实 ezdxf 实现
=========================================
核心能力: 读取 DXF/DWG 文件 → 提取实体/尺寸/文本 → 输出结构化文本

支持格式:
  - DXF (R12–R2018): 直接用 ezdxf 解析
  - DWG: 需先用 ODA File Converter 转为 DXF (标记为人工处理)
  - STEP/IGES: 需 CadQuery/pythonocc (标记为人工处理)

参考: ezdxf (https://github.com/mozman/ezdxf)
由 AGI v13.3 Cognitive Lattice + Tool Controller 构建
"""

import os
import sys
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SKILL_META = {
    "name": "cad_file_recognizer",
    "display_name": "CAD文件识别与解析工具",
    "description": "用ezdxf真实解析DXF文件: 提取线段/圆/弧/文本/尺寸/块引用等实体, 输出结构化文本供LLM理解图纸内容",
    "tags": ["CAD", "DXF", "ezdxf", "文件识别", "几何形状", "尺寸提取", "工业制造"],
    "capabilities": [
        "parse_dxf: 解析DXF文件, 返回完整实体清单",
        "dxf_to_text: DXF文件转自然语言描述",
        "extract_entities: 提取指定类型实体(LINE/CIRCLE/ARC/TEXT/DIMENSION等)",
        "get_dimensions: 提取所有尺寸标注",
        "get_layers: 获取图层信息",
        "summarize_dxf: 生成DXF文件概要",
    ],
}


# ==================== 核心解析函数 ====================

def parse_dxf(file_path: str) -> Dict[str, Any]:
    """
    解析 DXF 文件, 返回完整的实体和元数据信息

    Args:
        file_path: DXF 文件路径 (绝对或相对于项目根目录)

    Returns:
        {
            "success": bool,
            "file": str,
            "version": str,
            "layers": [...],
            "entity_counts": {"LINE": n, "CIRCLE": n, ...},
            "entities": [...],  # 所有实体详情
            "texts": [...],     # 提取的文字内容
            "dimensions": [...], # 尺寸标注
            "bounds": {"min": [x,y], "max": [x,y]},
            "summary": str,     # 自然语言概要
        }
    """
    try:
        import ezdxf
    except ImportError:
        return {"success": False, "error": "ezdxf未安装, 请运行: pip install ezdxf"}

    p = Path(file_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / file_path

    if not p.exists():
        return {"success": False, "error": f"文件不存在: {p}"}

    ext = p.suffix.lower()
    if ext == '.dwg':
        return {
            "success": False,
            "error": "DWG格式需先转换为DXF。请使用ODA File Converter (https://www.opendesign.com/guestfiles/oda_file_converter) 转换后重试。",
            "action_required": "human",
        }
    if ext not in ('.dxf',):
        return {"success": False, "error": f"不支持的格式: {ext}。支持: .dxf (DWG需先转换)"}

    try:
        doc = ezdxf.readfile(str(p))
    except Exception as e:
        return {"success": False, "error": f"解析DXF失败: {e}"}

    msp = doc.modelspace()
    result = {
        "success": True,
        "file": str(p),
        "filename": p.name,
        "version": doc.dxfversion,
        "encoding": doc.encoding,
    }

    # 图层信息
    result["layers"] = []
    for layer in doc.layers:
        result["layers"].append({
            "name": layer.dxf.name,
            "color": layer.dxf.color,
            "is_on": layer.is_on(),
        })

    # 遍历所有实体
    entities = []
    entity_counts = {}
    texts = []
    dimensions = []
    all_x, all_y = [], []

    for e in msp:
        etype = e.dxftype()
        entity_counts[etype] = entity_counts.get(etype, 0) + 1
        entity_info = {"type": etype, "layer": e.dxf.layer if hasattr(e.dxf, 'layer') else "0"}

        try:
            if etype == "LINE":
                s, en = e.dxf.start, e.dxf.end
                entity_info["start"] = [round(s.x, 3), round(s.y, 3)]
                entity_info["end"] = [round(en.x, 3), round(en.y, 3)]
                length = math.sqrt((en.x - s.x)**2 + (en.y - s.y)**2)
                entity_info["length"] = round(length, 3)
                all_x.extend([s.x, en.x])
                all_y.extend([s.y, en.y])

            elif etype == "CIRCLE":
                c = e.dxf.center
                entity_info["center"] = [round(c.x, 3), round(c.y, 3)]
                entity_info["radius"] = round(e.dxf.radius, 3)
                entity_info["diameter"] = round(e.dxf.radius * 2, 3)
                all_x.append(c.x)
                all_y.append(c.y)

            elif etype == "ARC":
                c = e.dxf.center
                entity_info["center"] = [round(c.x, 3), round(c.y, 3)]
                entity_info["radius"] = round(e.dxf.radius, 3)
                entity_info["start_angle"] = round(e.dxf.start_angle, 1)
                entity_info["end_angle"] = round(e.dxf.end_angle, 1)
                all_x.append(c.x)
                all_y.append(c.y)

            elif etype in ("TEXT", "MTEXT"):
                text_content = ""
                if etype == "TEXT":
                    text_content = e.dxf.text if hasattr(e.dxf, 'text') else ""
                    if hasattr(e.dxf, 'insert'):
                        pos = e.dxf.insert
                        entity_info["position"] = [round(pos.x, 3), round(pos.y, 3)]
                elif etype == "MTEXT":
                    text_content = e.text if hasattr(e, 'text') else ""
                    if hasattr(e.dxf, 'insert'):
                        pos = e.dxf.insert
                        entity_info["position"] = [round(pos.x, 3), round(pos.y, 3)]
                entity_info["text"] = text_content
                if text_content.strip():
                    texts.append({"text": text_content.strip(), "layer": entity_info["layer"]})

            elif etype == "DIMENSION":
                dim_info = {"layer": entity_info["layer"]}
                if hasattr(e.dxf, 'text'):
                    dim_info["text"] = e.dxf.text
                if hasattr(e.dxf, 'defpoint'):
                    dp = e.dxf.defpoint
                    dim_info["defpoint"] = [round(dp.x, 3), round(dp.y, 3)]
                if hasattr(e.dxf, 'defpoint2'):
                    dp2 = e.dxf.defpoint2
                    dim_info["defpoint2"] = [round(dp2.x, 3), round(dp2.y, 3)]
                if hasattr(e, 'get_measurement'):
                    try:
                        dim_info["measurement"] = round(e.get_measurement(), 3)
                    except:
                        pass
                dimensions.append(dim_info)
                entity_info.update(dim_info)

            elif etype == "INSERT":
                entity_info["block_name"] = e.dxf.name if hasattr(e.dxf, 'name') else "?"
                if hasattr(e.dxf, 'insert'):
                    pos = e.dxf.insert
                    entity_info["position"] = [round(pos.x, 3), round(pos.y, 3)]

            elif etype == "LWPOLYLINE":
                points = list(e.get_points(format='xy'))
                entity_info["points_count"] = len(points)
                if points:
                    entity_info["first_point"] = [round(points[0][0], 3), round(points[0][1], 3)]
                    entity_info["last_point"] = [round(points[-1][0], 3), round(points[-1][1], 3)]
                    entity_info["is_closed"] = e.is_closed
                    for px, py in points:
                        all_x.append(px)
                        all_y.append(py)

            elif etype == "SPLINE":
                cp = list(e.control_points) if hasattr(e, 'control_points') else []
                entity_info["control_points_count"] = len(cp)

            elif etype == "ELLIPSE":
                c = e.dxf.center
                entity_info["center"] = [round(c.x, 3), round(c.y, 3)]
                all_x.append(c.x)
                all_y.append(c.y)

        except Exception:
            entity_info["parse_error"] = True

        entities.append(entity_info)

    result["entity_counts"] = entity_counts
    result["total_entities"] = sum(entity_counts.values())
    result["entities"] = entities[:500]  # 限制数量防止过大
    result["texts"] = texts
    result["dimensions"] = dimensions

    if all_x and all_y:
        result["bounds"] = {
            "min": [round(min(all_x), 3), round(min(all_y), 3)],
            "max": [round(max(all_x), 3), round(max(all_y), 3)],
            "width": round(max(all_x) - min(all_x), 3),
            "height": round(max(all_y) - min(all_y), 3),
        }

    # 生成概要
    result["summary"] = _generate_summary(result)
    return result


def _generate_summary(data: Dict) -> str:
    """从解析数据生成自然语言概要"""
    lines = [f"DXF文件: {data.get('filename', '?')} (版本: {data.get('version', '?')})"]
    lines.append(f"总实体数: {data.get('total_entities', 0)}")

    ec = data.get('entity_counts', {})
    if ec:
        parts = [f"{k}:{v}" for k, v in sorted(ec.items(), key=lambda x: -x[1])]
        lines.append(f"实体分布: {', '.join(parts)}")

    layers = data.get('layers', [])
    if layers:
        lines.append(f"图层({len(layers)}): {', '.join(l['name'] for l in layers[:10])}")

    bounds = data.get('bounds')
    if bounds:
        lines.append(f"图纸范围: {bounds['width']}×{bounds['height']} (从[{bounds['min'][0]},{bounds['min'][1]}]到[{bounds['max'][0]},{bounds['max'][1]}])")

    texts = data.get('texts', [])
    if texts:
        lines.append(f"文字标注({len(texts)}): {'; '.join(t['text'][:50] for t in texts[:10])}")

    dims = data.get('dimensions', [])
    if dims:
        measurements = [str(d.get('measurement', d.get('text', '?'))) for d in dims[:10]]
        lines.append(f"尺寸标注({len(dims)}): {', '.join(measurements)}")

    return "\n".join(lines)


def dxf_to_text(file_path: str, detail_level: str = "summary") -> Dict[str, Any]:
    """
    DXF文件转自然语言描述 — LLM友好输出

    Args:
        file_path: DXF文件路径
        detail_level: "summary"(概要) / "full"(完整) / "entities"(仅实体)

    Returns:
        {"success": bool, "text": str, "entity_count": int}
    """
    data = parse_dxf(file_path)
    if not data["success"]:
        return data

    if detail_level == "summary":
        return {"success": True, "text": data["summary"], "entity_count": data["total_entities"]}

    lines = [data["summary"], ""]

    if detail_level in ("full", "entities"):
        lines.append("=== 实体详情 ===")
        for e in data["entities"][:200]:
            etype = e["type"]
            layer = e.get("layer", "0")
            if etype == "LINE":
                lines.append(f"[{layer}] 线段: ({e['start'][0]},{e['start'][1]}) → ({e['end'][0]},{e['end'][1]}) 长度={e.get('length', '?')}")
            elif etype == "CIRCLE":
                lines.append(f"[{layer}] 圆: 中心({e['center'][0]},{e['center'][1]}) R={e['radius']} D={e['diameter']}")
            elif etype == "ARC":
                lines.append(f"[{layer}] 弧: 中心({e['center'][0]},{e['center'][1]}) R={e['radius']} 角度{e['start_angle']}°-{e['end_angle']}°")
            elif etype in ("TEXT", "MTEXT"):
                lines.append(f"[{layer}] 文字: \"{e.get('text', '')}\"")
            elif etype == "DIMENSION":
                lines.append(f"[{layer}] 尺寸: {e.get('measurement', e.get('text', '?'))}")
            elif etype == "INSERT":
                lines.append(f"[{layer}] 块引用: {e.get('block_name', '?')} at ({e.get('position', ['?','?'])})")
            elif etype == "LWPOLYLINE":
                lines.append(f"[{layer}] 多段线: {e['points_count']}点 {'闭合' if e.get('is_closed') else '开放'}")
            else:
                lines.append(f"[{layer}] {etype}")

    return {"success": True, "text": "\n".join(lines), "entity_count": data["total_entities"]}


def extract_entities(file_path: str, entity_type: str = None) -> Dict[str, Any]:
    """提取指定类型实体 (LINE/CIRCLE/ARC/TEXT/DIMENSION/INSERT/LWPOLYLINE等)"""
    data = parse_dxf(file_path)
    if not data["success"]:
        return data
    entities = data["entities"]
    if entity_type:
        entities = [e for e in entities if e["type"] == entity_type.upper()]
    return {"success": True, "count": len(entities), "entities": entities[:300]}


def get_dimensions(file_path: str) -> Dict[str, Any]:
    """提取所有尺寸标注"""
    data = parse_dxf(file_path)
    if not data["success"]:
        return data
    return {"success": True, "count": len(data["dimensions"]), "dimensions": data["dimensions"]}


def get_layers(file_path: str) -> Dict[str, Any]:
    """获取图层信息"""
    data = parse_dxf(file_path)
    if not data["success"]:
        return data
    return {"success": True, "count": len(data["layers"]), "layers": data["layers"]}


def summarize_dxf(file_path: str) -> Dict[str, Any]:
    """生成DXF文件一句话概要"""
    data = parse_dxf(file_path)
    if not data["success"]:
        return data
    return {"success": True, "summary": data["summary"]}


# ==================== 自测 ====================

if __name__ == "__main__":
    import tempfile
    import ezdxf

    print("=== CAD文件识别工具 自测 ===\n")

    # 创建测试DXF文件
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 0))
    msp.add_line((100, 0), (100, 50))
    msp.add_line((100, 50), (0, 50))
    msp.add_line((0, 50), (0, 0))
    msp.add_circle((50, 25), radius=10)
    msp.add_text("测试零件", dxfattribs={"height": 5, "insert": (10, 60)})
    msp.add_text("材料: 45#钢", dxfattribs={"height": 3, "insert": (10, 55)})

    test_path = Path(tempfile.mktemp(suffix=".dxf"))
    doc.saveas(str(test_path))
    print(f"测试文件: {test_path}")

    # 测试解析
    result = parse_dxf(str(test_path))
    print(f"\n解析成功: {result['success']}")
    print(f"实体计数: {result['entity_counts']}")
    print(f"文字: {result['texts']}")
    print(f"\n概要:\n{result['summary']}")

    # 测试DXF转文本
    text_result = dxf_to_text(str(test_path), "full")
    print(f"\n完整文本输出:\n{text_result['text']}")

    # 清理
    test_path.unlink(missing_ok=True)
    print("\n=== 自测完成 ===")