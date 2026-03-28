#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析DWG刀模文件, 提取盒型模板几何数据并存入数据库"""

import ezdxf
from ezdxf import bbox
import os
import sys
import json
import sqlite3
import math
from pathlib import Path
from collections import Counter

DWG_DIR = "/Users/administruter/Desktop/拉扯图形"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "box_templates.db")


def analyze_dwg(filepath):
    """解析单个DWG文件, 提取几何信息"""
    fname = os.path.basename(filepath)
    result = {
        "filename": fname,
        "filepath": filepath,
        "filesize": os.path.getsize(filepath),
        "error": None,
    }
    try:
        doc = ezdxf.readfile(filepath)
    except Exception as e:
        result["error"] = str(e)
        return result

    msp = doc.modelspace()
    entities = list(msp)
    result["entity_count"] = len(entities)

    # 实体类型统计
    type_counts = Counter(e.dxftype() for e in entities)
    result["entity_types"] = dict(type_counts.most_common())

    # 图层
    layers = []
    for l in doc.layers:
        layers.append({
            "name": l.dxf.name,
            "color": l.dxf.color if hasattr(l.dxf, 'color') else 0,
        })
    result["layers"] = layers
    result["layer_names"] = [l["name"] for l in layers]

    # 边界框
    try:
        cache = bbox.Cache()
        box = bbox.extents(msp, cache=cache)
        if box.has_data:
            w = box.extmax[0] - box.extmin[0]
            h = box.extmax[1] - box.extmin[1]
            result["bounds"] = {
                "min_x": round(box.extmin[0], 2),
                "min_y": round(box.extmin[1], 2),
                "max_x": round(box.extmax[0], 2),
                "max_y": round(box.extmax[1], 2),
            }
            result["width"] = round(w, 2)
            result["height"] = round(h, 2)
    except Exception:
        pass

    # 提取几何线段用于特征分析
    lines = []
    arcs = []
    circles = []
    polylines_data = []
    texts = []

    for e in entities:
        etype = e.dxftype()
        layer = e.dxf.layer if hasattr(e.dxf, 'layer') else "0"

        if etype == "LINE":
            s, t = e.dxf.start, e.dxf.end
            length = math.sqrt((t[0]-s[0])**2 + (t[1]-s[1])**2)
            angle = math.degrees(math.atan2(t[1]-s[1], t[0]-s[0])) % 360
            lines.append({
                "start": (round(s[0],2), round(s[1],2)),
                "end": (round(t[0],2), round(t[1],2)),
                "length": round(length, 2),
                "angle": round(angle, 1),
                "layer": layer,
            })
        elif etype == "ARC":
            arcs.append({
                "center": (round(e.dxf.center[0],2), round(e.dxf.center[1],2)),
                "radius": round(e.dxf.radius, 2),
                "start_angle": round(e.dxf.start_angle, 1),
                "end_angle": round(e.dxf.end_angle, 1),
                "layer": layer,
            })
        elif etype == "CIRCLE":
            circles.append({
                "center": (round(e.dxf.center[0],2), round(e.dxf.center[1],2)),
                "radius": round(e.dxf.radius, 2),
                "layer": layer,
            })
        elif etype in ("LWPOLYLINE", "POLYLINE"):
            try:
                pts = list(e.get_points(format='xy'))
                if pts:
                    polylines_data.append({
                        "point_count": len(pts),
                        "closed": e.closed if hasattr(e, 'closed') else False,
                        "layer": layer,
                    })
            except Exception:
                pass
        elif etype in ("TEXT", "MTEXT"):
            try:
                txt = e.dxf.text if etype == "TEXT" else e.text
                if txt:
                    texts.append({"text": txt.strip(), "layer": layer})
            except Exception:
                pass

    result["line_count"] = len(lines)
    result["arc_count"] = len(arcs)
    result["circle_count"] = len(circles)
    result["polyline_count"] = len(polylines_data)
    result["text_count"] = len(texts)
    result["texts"] = texts[:50]  # 保留前50个文本

    # 线段角度分布 (判断是否矩形为主)
    angle_bins = Counter()
    for ln in lines:
        a = ln["angle"]
        if a > 180: a -= 180
        bucket = round(a / 45) * 45
        angle_bins[bucket] = angle_bins.get(bucket, 0) + 1
    result["angle_distribution"] = dict(angle_bins)

    # 线段长度分布
    if lines:
        lengths = sorted(set(round(ln["length"],0) for ln in lines if ln["length"] > 1))
        result["unique_lengths"] = lengths[:30]
        result["avg_line_length"] = round(sum(ln["length"] for ln in lines) / len(lines), 1)

    # 层分布
    layer_entity_counts = Counter()
    for e in entities:
        lyr = e.dxf.layer if hasattr(e.dxf, 'layer') else "0"
        layer_entity_counts[lyr] += 1
    result["layer_entity_counts"] = dict(layer_entity_counts.most_common())

    # 盒型特征推断
    result["features"] = infer_box_features(result, lines, arcs, circles, texts)

    return result


def infer_box_features(info, lines, arcs, circles, texts):
    """推断盒型特征"""
    features = {}

    # 1. 尺寸推断 (从文件名)
    fname = info["filename"]
    import re
    dims = re.findall(r'(\d{2,4})\s*[xX×]\s*(\d{2,4})\s*[xX×]\s*(\d{2,4})', fname)
    if dims:
        features["dimensions_from_name"] = {"L": int(dims[0][0]), "W": int(dims[0][1]), "H": int(dims[0][2])}

    # 2. 瓦楞类型推断
    for flute in ["A楞", "B楞", "C楞", "E楞", "F楞", "AB楞", "BC楞", "BE楞"]:
        if flute in fname:
            features["flute_type"] = flute
            break

    # 3. 文本中的尺寸信息
    text_dims = []
    for t in texts:
        txt = t["text"]
        d = re.findall(r'(\d{2,4})\s*[xX×]\s*(\d{2,4})', txt)
        if d:
            text_dims.extend(d)
        # 检查常见标注
        if any(kw in txt for kw in ["刀", "压", "切", "折", "粘"]):
            features.setdefault("process_marks", []).append(txt[:30])

    if text_dims:
        features["dimensions_from_text"] = text_dims[:5]

    # 4. 结构特征
    angle_dist = info.get("angle_distribution", {})
    h_v_ratio = (angle_dist.get(0, 0) + angle_dist.get(180, 0)) + (angle_dist.get(90, 0))
    total_lines = sum(angle_dist.values()) or 1
    features["orthogonal_ratio"] = round(h_v_ratio / total_lines, 3)

    if arcs or circles:
        features["has_curves"] = True
        features["curve_count"] = len(arcs) + len(circles)
        # 锁扣特征: 小半径圆弧
        small_arcs = [a for a in arcs if a["radius"] < 10]
        if small_arcs:
            features["has_lock_tabs"] = True
            features["lock_tab_count"] = len(small_arcs)

    # 5. 盒型类型推断
    features["box_type"] = classify_box_type(info, features, lines, arcs)

    return features


def classify_box_type(info, features, lines, arcs):
    """粗略分类盒型"""
    fname = info["filename"].lower()
    ortho = features.get("orthogonal_ratio", 0)
    has_locks = features.get("has_lock_tabs", False)
    has_curves = features.get("has_curves", False)
    entity_count = info.get("entity_count", 0)

    # 文件名关键词
    if "地堆" in fname or "陈列" in fname:
        return "display_stand"
    if "围边" in fname:
        return "border_wrap"
    if "打孔" in fname or "孔位" in fname:
        return "punch_template"
    if "锁扣" in fname:
        return "lock_box"

    # 结构特征判断
    if ortho > 0.8 and not has_curves:
        if entity_count < 50:
            return "simple_tray"
        elif entity_count < 200:
            return "standard_rsc"  # 常规开槽箱
        else:
            return "complex_box"
    elif has_locks:
        return "lock_bottom_box"
    elif has_curves and features.get("curve_count", 0) > 10:
        return "die_cut_special"
    else:
        return "general_carton"


def init_db(db_path):
    """初始化盒型模板数据库"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS box_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL UNIQUE,
            filesize INTEGER,
            entity_count INTEGER DEFAULT 0,
            line_count INTEGER DEFAULT 0,
            arc_count INTEGER DEFAULT 0,
            circle_count INTEGER DEFAULT 0,
            polyline_count INTEGER DEFAULT 0,
            text_count INTEGER DEFAULT 0,
            width REAL,
            height REAL,
            bounds_json TEXT,
            entity_types_json TEXT,
            layer_names_json TEXT,
            layer_entity_counts_json TEXT,
            angle_distribution_json TEXT,
            unique_lengths_json TEXT,
            avg_line_length REAL,
            texts_json TEXT,
            features_json TEXT,
            box_type TEXT DEFAULT 'unknown',
            flute_type TEXT,
            orthogonal_ratio REAL,
            has_curves INTEGER DEFAULT 0,
            has_lock_tabs INTEGER DEFAULT 0,
            dimension_l REAL,
            dimension_w REAL,
            dimension_h REAL,
            parse_error TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS box_type_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT NOT NULL UNIQUE,
            display_name TEXT,
            description TEXT,
            template_count INTEGER DEFAULT 0,
            avg_entity_count REAL,
            avg_orthogonal_ratio REAL,
            common_flutes TEXT,
            dimension_range_json TEXT,
            common_layers_json TEXT,
            features_summary_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_bt_box_type ON box_templates(box_type);
        CREATE INDEX IF NOT EXISTS idx_bt_flute ON box_templates(flute_type);
        CREATE INDEX IF NOT EXISTS idx_bt_filename ON box_templates(filename);
    """)
    conn.commit()
    return conn


def save_template(conn, data):
    """保存单个模板到数据库"""
    features = data.get("features", {})
    dims = features.get("dimensions_from_name", {})

    conn.execute("""
        INSERT OR REPLACE INTO box_templates (
            filename, filepath, filesize, entity_count,
            line_count, arc_count, circle_count, polyline_count, text_count,
            width, height, bounds_json, entity_types_json,
            layer_names_json, layer_entity_counts_json,
            angle_distribution_json, unique_lengths_json, avg_line_length,
            texts_json, features_json, box_type, flute_type,
            orthogonal_ratio, has_curves, has_lock_tabs,
            dimension_l, dimension_w, dimension_h, parse_error
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("filename"),
        data.get("filepath"),
        data.get("filesize"),
        data.get("entity_count", 0),
        data.get("line_count", 0),
        data.get("arc_count", 0),
        data.get("circle_count", 0),
        data.get("polyline_count", 0),
        data.get("text_count", 0),
        data.get("width"),
        data.get("height"),
        json.dumps(data.get("bounds"), ensure_ascii=False) if data.get("bounds") else None,
        json.dumps(data.get("entity_types"), ensure_ascii=False),
        json.dumps(data.get("layer_names"), ensure_ascii=False),
        json.dumps(data.get("layer_entity_counts"), ensure_ascii=False),
        json.dumps(data.get("angle_distribution"), ensure_ascii=False),
        json.dumps(data.get("unique_lengths"), ensure_ascii=False),
        data.get("avg_line_length"),
        json.dumps(data.get("texts", []), ensure_ascii=False),
        json.dumps(features, ensure_ascii=False),
        features.get("box_type", "unknown"),
        features.get("flute_type"),
        features.get("orthogonal_ratio"),
        1 if features.get("has_curves") else 0,
        1 if features.get("has_lock_tabs") else 0,
        dims.get("L"),
        dims.get("W"),
        dims.get("H"),
        data.get("error"),
    ))
    conn.commit()


def extract_patterns(conn):
    """分析提炼盒型共性"""
    c = conn.cursor()

    # 按 box_type 分组统计
    c.execute("""
        SELECT box_type, COUNT(*) as cnt,
               AVG(entity_count) as avg_entities,
               AVG(orthogonal_ratio) as avg_ortho,
               GROUP_CONCAT(DISTINCT flute_type) as flutes
        FROM box_templates
        WHERE parse_error IS NULL
        GROUP BY box_type
        ORDER BY cnt DESC
    """)
    type_stats = c.fetchall()

    for row in type_stats:
        bt = row['box_type']
        # 获取该类型常见图层
        c.execute("""
            SELECT layer_names_json FROM box_templates
            WHERE box_type = ? AND parse_error IS NULL
        """, (bt,))
        all_layers = Counter()
        dim_ranges = {"L": [], "W": [], "H": []}
        for r in c.fetchall():
            try:
                layers = json.loads(r['layer_names_json'] or '[]')
                for l in layers:
                    all_layers[l] += 1
            except:
                pass

        c.execute("""
            SELECT dimension_l, dimension_w, dimension_h FROM box_templates
            WHERE box_type = ? AND dimension_l IS NOT NULL
        """, (bt,))
        for r in c.fetchall():
            if r['dimension_l']: dim_ranges["L"].append(r['dimension_l'])
            if r['dimension_w']: dim_ranges["W"].append(r['dimension_w'])
            if r['dimension_h']: dim_ranges["H"].append(r['dimension_h'])

        dim_range_json = {}
        for k, v in dim_ranges.items():
            if v:
                dim_range_json[k] = {"min": min(v), "max": max(v), "avg": round(sum(v)/len(v), 1)}

        display_names = {
            "standard_rsc": "标准开槽箱 (RSC)",
            "simple_tray": "简单托盘",
            "complex_box": "复杂盒型",
            "lock_bottom_box": "锁底盒",
            "die_cut_special": "异形模切",
            "general_carton": "通用纸箱",
            "display_stand": "陈列架/地堆",
            "border_wrap": "围边",
            "punch_template": "打孔模板",
            "lock_box": "锁扣盒",
            "unknown": "未分类",
        }

        conn.execute("""
            INSERT OR REPLACE INTO box_type_patterns (
                type_name, display_name, description, template_count,
                avg_entity_count, avg_orthogonal_ratio, common_flutes,
                dimension_range_json, common_layers_json, features_summary_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            bt,
            display_names.get(bt, bt),
            f"共{row['cnt']}个模板, 平均{row['avg_entities']:.0f}个实体",
            row['cnt'],
            round(row['avg_entities'], 1),
            round(row['avg_ortho'], 3) if row['avg_ortho'] else None,
            row['flutes'],
            json.dumps(dim_range_json, ensure_ascii=False),
            json.dumps(dict(all_layers.most_common(10)), ensure_ascii=False),
            json.dumps({
                "avg_entity_count": round(row['avg_entities'], 1),
                "avg_orthogonal_ratio": round(row['avg_ortho'], 3) if row['avg_ortho'] else None,
                "has_dims": bool(dim_range_json),
            }, ensure_ascii=False),
        ))
    conn.commit()
    return type_stats


def main():
    print("=" * 60)
    print("  DWG 刀模文件解析器 — 盒型模板入库")
    print("=" * 60)

    # 收集所有DWG文件
    dwg_files = []
    for root, dirs, files in os.walk(DWG_DIR):
        for f in files:
            if f.lower().endswith('.dwg'):
                dwg_files.append(os.path.join(root, f))

    print(f"\n找到 {len(dwg_files)} 个DWG文件")
    print(f"数据库: {DB_PATH}\n")

    conn = init_db(DB_PATH)

    success = 0
    errors = 0
    for i, fp in enumerate(dwg_files):
        fname = os.path.basename(fp)
        print(f"[{i+1}/{len(dwg_files)}] 解析: {fname} ...", end=" ")
        data = analyze_dwg(fp)
        save_template(conn, data)
        if data.get("error"):
            print(f"ERROR: {data['error'][:60]}")
            errors += 1
        else:
            ft = data.get("features", {})
            print(f"OK  entities={data.get('entity_count',0)}  type={ft.get('box_type','?')}")
            success += 1

    print(f"\n解析完成: {success} 成功, {errors} 失败")

    # 提炼共性
    print("\n" + "=" * 60)
    print("  盒型共性分析")
    print("=" * 60)
    type_stats = extract_patterns(conn)

    for row in type_stats:
        print(f"\n  [{row['box_type']}] x{row['cnt']}")
        print(f"    平均实体数: {row['avg_entities']:.0f}")
        if row['avg_ortho']:
            print(f"    正交率: {row['avg_ortho']:.1%}")
        if row['flutes']:
            print(f"    瓦楞: {row['flutes']}")

    # 全局统计
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM box_templates WHERE parse_error IS NULL")
    total = c.fetchone()['total']
    c.execute("SELECT COUNT(DISTINCT box_type) as types FROM box_templates WHERE parse_error IS NULL")
    types = c.fetchone()['types']
    c.execute("SELECT AVG(entity_count) as avg_e FROM box_templates WHERE parse_error IS NULL")
    avg_e = c.fetchone()['avg_e']

    print(f"\n{'='*60}")
    print(f"  总计: {total} 个模板, {types} 种盒型")
    print(f"  平均实体数: {avg_e:.0f}")
    print(f"  数据库已保存: {DB_PATH}")
    print(f"{'='*60}")

    conn.close()


if __name__ == "__main__":
    main()
