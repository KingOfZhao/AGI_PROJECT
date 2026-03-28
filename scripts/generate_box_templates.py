#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 ezdxf 生成标准盒型 DXF 模板 + 解析入库
覆盖 FEFCO 常用盒型: 0201(RSC) / 0421(锁底) / 0711(天地盖) / 0301(管式) / 0501(滑盖) 等
"""

import ezdxf
import os
import sys
import json
import math
import sqlite3
from pathlib import Path
from collections import Counter
from datetime import datetime

# 输出目录
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "templates")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "box_templates.db")

# 确保目录存在
os.makedirs(TEMPLATE_DIR, exist_ok=True)


# ============================================================
# 盒型生成器
# ============================================================

def fefco_0201_rsc(L, W, H, flap=None):
    """FEFCO 0201 - 标准开槽箱 (Regular Slotted Container)
    最常见的纸箱，四片摇盖"""
    if flap is None:
        flap = W / 2  # 标准摇盖长度 = 宽度/2
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # 切割线图层 (红色)
    doc.layers.add("CUT", color=1)
    # 折线图层 (蓝色)
    doc.layers.add("CREASE", color=5)
    # 标注图层 (绿色)
    doc.layers.add("DIMENSION", color=3)

    # 箱体展开: 四面板 + 粘贴舌
    # 排列: 粘贴舌 | 面W | 面L | 面W | 面L
    panels = [15, W, L, W, L]  # 15mm粘贴舌
    x_offsets = [0]
    for p in panels:
        x_offsets.append(x_offsets[-1] + p)
    total_w = x_offsets[-1]

    # 底部摇盖
    y_bottom = 0
    y_body_bottom = flap
    y_body_top = flap + H
    y_top = flap + H + flap

    # 画箱体轮廓 (CUT层)
    # 底边
    msp.add_line((x_offsets[0], y_body_bottom), (x_offsets[-1], y_body_bottom), dxfattribs={"layer": "CUT"})
    # 顶边
    msp.add_line((x_offsets[0], y_body_top), (x_offsets[-1], y_body_top), dxfattribs={"layer": "CUT"})

    # 竖线 (折线)
    for i in range(1, len(x_offsets) - 1):
        msp.add_line((x_offsets[i], y_bottom), (x_offsets[i], y_top), dxfattribs={"layer": "CREASE"})

    # 左右边 (CUT)
    msp.add_line((x_offsets[0], y_body_bottom), (x_offsets[0], y_body_top), dxfattribs={"layer": "CUT"})
    msp.add_line((x_offsets[-1], y_body_bottom), (x_offsets[-1], y_body_top), dxfattribs={"layer": "CUT"})

    # 粘贴舌 (梯形)
    tab_w = 15
    tab_inset = 3
    pts_tab = [
        (0, y_body_bottom),
        (0, y_body_top),
        (-tab_w + tab_inset, y_body_top - tab_inset),
        (-tab_w + tab_inset, y_body_bottom + tab_inset),
    ]
    for i in range(len(pts_tab)):
        msp.add_line(pts_tab[i], pts_tab[(i+1) % len(pts_tab)], dxfattribs={"layer": "CUT"})

    # 摇盖 (4个面板各有上下摇盖)
    for idx in range(1, 5):
        x1 = x_offsets[idx]
        x2 = x_offsets[idx + 1]
        pw = x2 - x1

        # 下摇盖
        flap_h = min(flap, pw / 2 + 5)  # 不超过面板宽度一半
        msp.add_line((x1, y_body_bottom), (x1, y_body_bottom - flap_h), dxfattribs={"layer": "CUT"})
        msp.add_line((x2, y_body_bottom), (x2, y_body_bottom - flap_h), dxfattribs={"layer": "CUT"})
        msp.add_line((x1, y_body_bottom - flap_h), (x2, y_body_bottom - flap_h), dxfattribs={"layer": "CUT"})

        # 上摇盖
        msp.add_line((x1, y_body_top), (x1, y_body_top + flap_h), dxfattribs={"layer": "CUT"})
        msp.add_line((x2, y_body_top), (x2, y_body_top + flap_h), dxfattribs={"layer": "CUT"})
        msp.add_line((x1, y_body_top + flap_h), (x2, y_body_top + flap_h), dxfattribs={"layer": "CUT"})

    # 尺寸标注文字
    msp.add_text(f"FEFCO 0201 RSC  {L}x{W}x{H}mm",
                 dxfattribs={"layer": "DIMENSION", "height": 5}).set_placement((total_w/2, y_top + 15))

    return doc, {
        "fefco": "0201",
        "type": "RSC",
        "type_cn": "标准开槽箱",
        "L": L, "W": W, "H": H,
        "flap": round(flap, 1),
        "total_width": round(total_w, 1),
        "total_height": round(y_top, 1),
        "panels": 4,
        "features": ["top_flaps", "bottom_flaps", "glue_tab"],
    }


def fefco_0421_lock_bottom(L, W, H):
    """FEFCO 0421 - 锁底盒
    底部自动锁扣, 顶部插入式"""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    doc.layers.add("CUT", color=1)
    doc.layers.add("CREASE", color=5)
    doc.layers.add("DIMENSION", color=3)

    tab = 15  # 粘贴舌
    tuck = W * 0.8  # 插舌长度

    # 面板排列: tab | W | L | W | L
    panels = [tab, W, L, W, L]
    x = [0]
    for p in panels:
        x.append(x[-1] + p)

    y0 = 0  # 底锁底部
    y1 = W * 0.6  # 锁底高度
    y2 = y1 + H  # 箱体顶
    y3 = y2 + tuck  # 插舌顶

    # 箱体
    msp.add_line((x[1], y1), (x[-1], y1), dxfattribs={"layer": "CUT"})
    msp.add_line((x[1], y2), (x[-1], y2), dxfattribs={"layer": "CUT"})

    # 折线
    for i in [2, 3, 4]:
        msp.add_line((x[i], y0), (x[i], y3), dxfattribs={"layer": "CREASE"})

    # 侧边
    msp.add_line((x[1], y1), (x[1], y2), dxfattribs={"layer": "CUT"})
    msp.add_line((x[-1], y1), (x[-1], y2), dxfattribs={"layer": "CUT"})

    # 粘贴舌
    msp.add_line((x[1], y1), (x[0]+3, y1+3), dxfattribs={"layer": "CUT"})
    msp.add_line((x[0]+3, y1+3), (x[0]+3, y2-3), dxfattribs={"layer": "CUT"})
    msp.add_line((x[0]+3, y2-3), (x[1], y2), dxfattribs={"layer": "CUT"})

    # 锁底结构 (简化)
    for idx in [1, 2, 3, 4]:
        x1, x2 = x[idx], x[idx+1]
        pw = x2 - x1
        lock_h = pw * 0.5

        # 锁底片
        msp.add_line((x1, y1), (x1, y1 - lock_h), dxfattribs={"layer": "CUT"})
        msp.add_line((x2, y1), (x2, y1 - lock_h), dxfattribs={"layer": "CUT"})

        if idx in [1, 3]:  # W面 - 三角锁
            mid = (x1 + x2) / 2
            msp.add_line((x1, y1 - lock_h), (mid, y1 - lock_h - 8), dxfattribs={"layer": "CUT"})
            msp.add_line((mid, y1 - lock_h - 8), (x2, y1 - lock_h), dxfattribs={"layer": "CUT"})
        else:  # L面 - 矩形锁
            msp.add_line((x1, y1 - lock_h), (x2, y1 - lock_h), dxfattribs={"layer": "CUT"})

    # 顶部插舌 (面板2和4: L面)
    for idx in [2, 4]:
        x1, x2 = x[idx], x[idx+1]
        pw = x2 - x1
        msp.add_line((x1, y2), (x1, y2 + tuck), dxfattribs={"layer": "CUT"})
        msp.add_line((x2, y2), (x2, y2 + tuck), dxfattribs={"layer": "CUT"})
        # 插舌圆角
        msp.add_arc((x1 + pw/2, y2 + tuck), pw/2, 0, 180, dxfattribs={"layer": "CUT"})

    # 顶部耳朵 (面板1和3: W面)
    for idx in [1, 3]:
        x1, x2 = x[idx], x[idx+1]
        ear_h = H * 0.3
        msp.add_line((x1, y2), (x1, y2 + ear_h), dxfattribs={"layer": "CUT"})
        msp.add_line((x2, y2), (x2, y2 + ear_h), dxfattribs={"layer": "CUT"})
        msp.add_line((x1, y2 + ear_h), (x2, y2 + ear_h), dxfattribs={"layer": "CUT"})

    msp.add_text(f"FEFCO 0421 Lock Bottom  {L}x{W}x{H}mm",
                 dxfattribs={"layer": "DIMENSION", "height": 5}).set_placement((x[-1]/2, y3 + 15))

    return doc, {
        "fefco": "0421",
        "type": "lock_bottom",
        "type_cn": "锁底盒",
        "L": L, "W": W, "H": H,
        "tuck_length": round(tuck, 1),
        "features": ["lock_bottom", "tuck_top", "glue_tab", "ear_flaps"],
    }


def fefco_0711_telescope(L, W, H):
    """FEFCO 0711 - 天地盖 (上下盖套合)"""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    doc.layers.add("CUT", color=1)
    doc.layers.add("CREASE", color=5)
    doc.layers.add("DIMENSION", color=3)

    rim = H * 0.4  # 盖子边沿高度
    gap = 20  # 天盖和地盖之间的间距

    # === 天盖 (上方) ===
    lid_y_base = gap / 2
    # 底板
    msp.add_lwpolyline([
        (0, lid_y_base), (L, lid_y_base), (L, lid_y_base + W),
        (0, lid_y_base + W), (0, lid_y_base)
    ], dxfattribs={"layer": "CREASE"})

    # 四边翻边
    sides = [
        ((0, lid_y_base), (L, lid_y_base), (0, -1)),        # 下
        ((L, lid_y_base), (L, lid_y_base + W), (1, 0)),     # 右
        ((0, lid_y_base + W), (L, lid_y_base + W), (0, 1)), # 上
        ((0, lid_y_base), (0, lid_y_base + W), (-1, 0)),    # 左
    ]
    for (sx, sy), (ex, ey), (dx, dy) in sides:
        ox1, oy1 = sx + dx * rim, sy + dy * rim
        ox2, oy2 = ex + dx * rim, ey + dy * rim
        msp.add_line((sx, sy), (ox1, oy1), dxfattribs={"layer": "CUT"})
        msp.add_line((ex, ey), (ox2, oy2), dxfattribs={"layer": "CUT"})
        msp.add_line((ox1, oy1), (ox2, oy2), dxfattribs={"layer": "CUT"})

    msp.add_text("天盖 (LID)", dxfattribs={"layer": "DIMENSION", "height": 4}).set_placement((L/2, lid_y_base + W/2))

    # === 地盖 (下方) ===
    base_y = -(gap / 2 + W)
    msp.add_lwpolyline([
        (0, base_y), (L, base_y), (L, base_y + W),
        (0, base_y + W), (0, base_y)
    ], dxfattribs={"layer": "CREASE"})

    base_rim = H * 0.6  # 地盖边沿稍高
    sides_base = [
        ((0, base_y), (L, base_y), (0, -1)),
        ((L, base_y), (L, base_y + W), (1, 0)),
        ((0, base_y + W), (L, base_y + W), (0, 1)),
        ((0, base_y), (0, base_y + W), (-1, 0)),
    ]
    for (sx, sy), (ex, ey), (dx, dy) in sides_base:
        ox1, oy1 = sx + dx * base_rim, sy + dy * base_rim
        ox2, oy2 = ex + dx * base_rim, ey + dy * base_rim
        msp.add_line((sx, sy), (ox1, oy1), dxfattribs={"layer": "CUT"})
        msp.add_line((ex, ey), (ox2, oy2), dxfattribs={"layer": "CUT"})
        msp.add_line((ox1, oy1), (ox2, oy2), dxfattribs={"layer": "CUT"})

    msp.add_text("地盖 (BASE)", dxfattribs={"layer": "DIMENSION", "height": 4}).set_placement((L/2, base_y + W/2))

    msp.add_text(f"FEFCO 0711 Telescope  {L}x{W}x{H}mm",
                 dxfattribs={"layer": "DIMENSION", "height": 5}).set_placement((L/2, lid_y_base + W + rim + 15))

    return doc, {
        "fefco": "0711",
        "type": "telescope",
        "type_cn": "天地盖",
        "L": L, "W": W, "H": H,
        "lid_rim": round(rim, 1),
        "base_rim": round(base_rim, 1),
        "features": ["lid", "base", "rim_walls", "two_piece"],
    }


def fefco_0301_tube(L, W, H):
    """FEFCO 0301 - 管式盒 (插入式)"""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    doc.layers.add("CUT", color=1)
    doc.layers.add("CREASE", color=5)
    doc.layers.add("DIMENSION", color=3)

    tab = 15
    tuck = W * 0.75
    dust_flap = W * 0.4

    panels = [tab, W, L, W, L]
    x = [0]
    for p in panels:
        x.append(x[-1] + p)

    y0 = 0
    y1 = H

    # 箱体
    msp.add_line((x[0], y0), (x[-1], y0), dxfattribs={"layer": "CUT"})
    msp.add_line((x[0], y1), (x[-1], y1), dxfattribs={"layer": "CUT"})

    # 折线
    for i in range(1, 5):
        msp.add_line((x[i], y0 - tuck - 5), (x[i], y1 + tuck + 5), dxfattribs={"layer": "CREASE"})

    # 侧边
    msp.add_line((x[0], y0), (x[0], y1), dxfattribs={"layer": "CUT"})
    msp.add_line((x[-1], y0), (x[-1], y1), dxfattribs={"layer": "CUT"})

    # 粘贴舌
    msp.add_line((x[0], y0), (x[0] - tab + 3, y0 + 3), dxfattribs={"layer": "CUT"})
    msp.add_line((x[0] - tab + 3, y0 + 3), (x[0] - tab + 3, y1 - 3), dxfattribs={"layer": "CUT"})
    msp.add_line((x[0] - tab + 3, y1 - 3), (x[0], y1), dxfattribs={"layer": "CUT"})

    # 上下插舌和防尘翼
    for y_base, direction in [(y1, 1), (y0, -1)]:
        for idx in range(1, 5):
            x1, x2 = x[idx], x[idx+1]
            pw = x2 - x1

            if idx in [2, 4]:  # L面 - 插舌
                th = tuck * direction
                msp.add_line((x1, y_base), (x1 + 2, y_base + th), dxfattribs={"layer": "CUT"})
                msp.add_line((x2, y_base), (x2 - 2, y_base + th), dxfattribs={"layer": "CUT"})
                msp.add_line((x1 + 2, y_base + th), (x2 - 2, y_base + th), dxfattribs={"layer": "CUT"})
            else:  # W面 - 防尘翼
                dh = dust_flap * direction
                msp.add_line((x1, y_base), (x1, y_base + dh), dxfattribs={"layer": "CUT"})
                msp.add_line((x2, y_base), (x2, y_base + dh), dxfattribs={"layer": "CUT"})
                msp.add_line((x1, y_base + dh), (x2, y_base + dh), dxfattribs={"layer": "CUT"})

    msp.add_text(f"FEFCO 0301 Tube  {L}x{W}x{H}mm",
                 dxfattribs={"layer": "DIMENSION", "height": 5}).set_placement((x[-1]/2, y1 + tuck + 15))

    return doc, {
        "fefco": "0301",
        "type": "tube",
        "type_cn": "管式盒",
        "L": L, "W": W, "H": H,
        "tuck_length": round(tuck, 1),
        "dust_flap": round(dust_flap, 1),
        "features": ["tuck_top", "tuck_bottom", "dust_flaps", "glue_tab"],
    }


def display_stand(L, W, H, shelf_count=3):
    """陈列架/地堆"""
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    doc.layers.add("CUT", color=1)
    doc.layers.add("CREASE", color=5)
    doc.layers.add("DIMENSION", color=3)

    shelf_h = H / shelf_count
    total_h = H + 30  # 顶部挡板

    # 后背板
    msp.add_lwpolyline([
        (0, 0), (L, 0), (L, total_h), (0, total_h), (0, 0)
    ], dxfattribs={"layer": "CUT"})

    # 层板折线
    for i in range(1, shelf_count + 1):
        y = i * shelf_h
        msp.add_line((0, y), (L, y), dxfattribs={"layer": "CREASE"})

    # 侧翼 (右侧展开)
    wing_x = L + 5
    for i in range(shelf_count):
        y_base = i * shelf_h
        msp.add_lwpolyline([
            (wing_x, y_base), (wing_x + W, y_base),
            (wing_x + W, y_base + shelf_h), (wing_x, y_base + shelf_h),
        ], dxfattribs={"layer": "CUT"})

    msp.add_text(f"Display Stand {L}x{W}x{H}mm  {shelf_count} shelves",
                 dxfattribs={"layer": "DIMENSION", "height": 5}).set_placement((L/2, total_h + 15))

    return doc, {
        "fefco": "N/A",
        "type": "display_stand",
        "type_cn": "陈列架",
        "L": L, "W": W, "H": H,
        "shelf_count": shelf_count,
        "features": ["back_panel", "shelves", "side_wings"],
    }


# ============================================================
# 数据库
# ============================================================

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS box_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT UNIQUE,
            fefco_code TEXT,
            box_type TEXT NOT NULL,
            box_type_cn TEXT,
            dimension_l REAL,
            dimension_w REAL,
            dimension_h REAL,
            flute_type TEXT,
            entity_count INTEGER DEFAULT 0,
            line_count INTEGER DEFAULT 0,
            arc_count INTEGER DEFAULT 0,
            circle_count INTEGER DEFAULT 0,
            polyline_count INTEGER DEFAULT 0,
            text_count INTEGER DEFAULT 0,
            total_width REAL,
            total_height REAL,
            features_json TEXT,
            layers_json TEXT,
            source TEXT DEFAULT 'generated',
            thumbnail_svg TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS box_type_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fefco_code TEXT UNIQUE,
            type_key TEXT NOT NULL UNIQUE,
            type_cn TEXT NOT NULL,
            type_en TEXT,
            description TEXT,
            category TEXT,
            template_count INTEGER DEFAULT 0,
            common_dimensions_json TEXT,
            structure_features_json TEXT,
            fold_sequence_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS box_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_name TEXT NOT NULL UNIQUE,
            module_cn TEXT,
            category TEXT,
            dxf_data TEXT,
            parameters_json TEXT,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_bt_type ON box_templates(box_type);
        CREATE INDEX IF NOT EXISTS idx_bt_fefco ON box_templates(fefco_code);
        CREATE INDEX IF NOT EXISTS idx_bm_cat ON box_modules(category);
    """)
    conn.commit()
    return conn


def count_entities(doc):
    """统计DXF文档实体数"""
    msp = doc.modelspace()
    entities = list(msp)
    counts = Counter(e.dxftype() for e in entities)
    return {
        "total": len(entities),
        "LINE": counts.get("LINE", 0),
        "ARC": counts.get("ARC", 0),
        "CIRCLE": counts.get("CIRCLE", 0),
        "LWPOLYLINE": counts.get("LWPOLYLINE", 0),
        "TEXT": counts.get("TEXT", 0) + counts.get("MTEXT", 0),
    }


def save_template(conn, filepath, info, doc):
    """保存模板到DB"""
    ec = count_entities(doc)
    layers = [l.dxf.name for l in doc.layers]

    conn.execute("""
        INSERT OR REPLACE INTO box_templates (
            filename, filepath, fefco_code, box_type, box_type_cn,
            dimension_l, dimension_w, dimension_h, flute_type,
            entity_count, line_count, arc_count, circle_count, polyline_count, text_count,
            total_width, total_height, features_json, layers_json, source
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        os.path.basename(filepath),
        filepath,
        info.get("fefco"),
        info.get("type"),
        info.get("type_cn"),
        info.get("L"),
        info.get("W"),
        info.get("H"),
        info.get("flute_type"),
        ec["total"],
        ec["LINE"],
        ec["ARC"],
        ec["CIRCLE"],
        ec["LWPOLYLINE"],
        ec["TEXT"],
        info.get("total_width"),
        info.get("total_height"),
        json.dumps(info.get("features", []), ensure_ascii=False),
        json.dumps(layers, ensure_ascii=False),
        "generated",
    ))
    conn.commit()


def init_catalog(conn):
    """初始化盒型目录 (FEFCO标准)"""
    catalog = [
        ("0201", "RSC", "标准开槽箱", "Regular Slotted Container", "最常见纸箱, 四片摇盖", "slotted",
         {"L": [200, 600], "W": [150, 400], "H": [100, 500]},
         ["top_flaps", "bottom_flaps", "glue_tab"],
         ["fold_sides", "fold_bottom_flaps", "fold_top_flaps"]),
        ("0421", "lock_bottom", "锁底盒", "Lock Bottom Box", "底部自动锁合, 顶部插入式", "folding",
         {"L": [100, 400], "W": [80, 300], "H": [50, 300]},
         ["lock_bottom", "tuck_top", "glue_tab", "ear_flaps"],
         ["open_flat", "push_sides", "auto_lock_bottom", "tuck_top"]),
        ("0711", "telescope", "天地盖", "Telescope Box", "上下盖套合式", "rigid",
         {"L": [150, 500], "W": [100, 400], "H": [30, 200]},
         ["lid", "base", "rim_walls", "two_piece"],
         ["fold_base_walls", "fold_lid_walls", "assemble"]),
        ("0301", "tube", "管式盒", "Tube Style Box", "筒式, 上下插入", "folding",
         {"L": [100, 400], "W": [50, 250], "H": [80, 350]},
         ["tuck_top", "tuck_bottom", "dust_flaps", "glue_tab"],
         ["fold_sides", "fold_dust_flaps", "tuck_bottom", "tuck_top"]),
        ("N/A", "display_stand", "陈列架", "Display Stand", "POP展示架/地堆", "display",
         {"L": [300, 800], "W": [200, 500], "H": [500, 1500]},
         ["back_panel", "shelves", "side_wings"],
         ["fold_shelves", "fold_wings", "assemble"]),
    ]
    for fefco, key, cn, en, desc, cat, dims, features, fold_seq in catalog:
        conn.execute("""
            INSERT OR IGNORE INTO box_type_catalog (
                fefco_code, type_key, type_cn, type_en, description, category,
                common_dimensions_json, structure_features_json, fold_sequence_json
            ) VALUES (?,?,?,?,?,?,?,?,?)
        """, (fefco, key, cn, en, desc, cat,
              json.dumps(dims, ensure_ascii=False),
              json.dumps(features, ensure_ascii=False),
              json.dumps(fold_seq, ensure_ascii=False)))
    conn.commit()


def init_modules(conn):
    """初始化可拖拽模块库"""
    modules = [
        ("lock_tab", "锁扣", "closure", "自锁底锁扣结构", {"width": 20, "height": 15, "angle": 75}),
        ("tuck_flap", "插舌", "closure", "顶部/底部插入舌", {"length_ratio": 0.75, "taper": 2}),
        ("dust_flap", "防尘翼", "closure", "防尘翼/耳朵", {"height_ratio": 0.4}),
        ("glue_tab", "粘贴舌", "joint", "侧面粘合舌", {"width": 15, "inset": 3}),
        ("handle_hole", "提手孔", "feature", "椭圆形提手孔", {"width": 80, "height": 30, "radius": 10}),
        ("ventilation", "通风孔", "feature", "圆形通风孔", {"diameter": 25, "count": 4}),
        ("window_cutout", "开窗", "feature", "矩形开窗(展示产品)", {"width": 100, "height": 60, "corner_r": 5}),
        ("score_line", "压痕线", "fold", "折叠压痕线", {"type": "standard"}),
        ("perforation", "撕拉线", "feature", "易撕开口", {"tooth_width": 3, "gap": 2}),
        ("stacking_tab", "堆码凸耳", "structure", "堆码定位凸耳", {"width": 30, "height": 20}),
    ]
    for name, cn, cat, desc, params in modules:
        conn.execute("""
            INSERT OR IGNORE INTO box_modules (
                module_name, module_cn, category, description, parameters_json
            ) VALUES (?,?,?,?,?)
        """, (name, cn, cat, desc, json.dumps(params, ensure_ascii=False)))
    conn.commit()


def main():
    print("=" * 60)
    print("  盒型模板生成器 — DXF生成 + 入库")
    print("=" * 60)

    conn = init_db(DB_PATH)
    init_catalog(conn)
    init_modules(conn)
    print(f"DB: {DB_PATH}")
    print(f"DXF输出: {TEMPLATE_DIR}\n")

    # 生成多种尺寸的标准盒型
    templates = [
        # FEFCO 0201 RSC 多尺寸
        ("RSC_310x233x245", lambda: fefco_0201_rsc(310, 233, 245)),
        ("RSC_400x300x300", lambda: fefco_0201_rsc(400, 300, 300)),
        ("RSC_200x150x100", lambda: fefco_0201_rsc(200, 150, 100)),
        ("RSC_500x350x350", lambda: fefco_0201_rsc(500, 350, 350)),
        ("RSC_600x400x400", lambda: fefco_0201_rsc(600, 400, 400)),
        # FEFCO 0421 锁底盒
        ("LockBottom_200x150x200", lambda: fefco_0421_lock_bottom(200, 150, 200)),
        ("LockBottom_300x200x250", lambda: fefco_0421_lock_bottom(300, 200, 250)),
        ("LockBottom_150x100x150", lambda: fefco_0421_lock_bottom(150, 100, 150)),
        # FEFCO 0711 天地盖
        ("Telescope_300x200x80", lambda: fefco_0711_telescope(300, 200, 80)),
        ("Telescope_400x300x100", lambda: fefco_0711_telescope(400, 300, 100)),
        # FEFCO 0301 管式盒
        ("Tube_200x100x250", lambda: fefco_0301_tube(200, 100, 250)),
        ("Tube_150x80x200", lambda: fefco_0301_tube(150, 80, 200)),
        ("Tube_300x150x350", lambda: fefco_0301_tube(300, 150, 350)),
        # 陈列架
        ("Display_500x300x1200_3shelf", lambda: display_stand(500, 300, 1200, 3)),
        ("Display_400x250x800_2shelf", lambda: display_stand(400, 250, 800, 2)),
    ]

    for name, gen_fn in templates:
        filepath = os.path.join(TEMPLATE_DIR, f"{name}.dxf")
        print(f"  生成: {name}.dxf ...", end=" ")
        try:
            doc, info = gen_fn()
            doc.saveas(filepath)
            save_template(conn, filepath, info, doc)
            print(f"OK  ({info['type_cn']} {info['L']}x{info['W']}x{info['H']})")
        except Exception as e:
            print(f"ERROR: {e}")

    # 统计
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM box_templates")
    total = c.fetchone()['cnt']
    c.execute("SELECT COUNT(*) as cnt FROM box_type_catalog")
    types = c.fetchone()['cnt']
    c.execute("SELECT COUNT(*) as cnt FROM box_modules")
    modules = c.fetchone()['cnt']

    print(f"\n{'='*60}")
    print(f"  完成: {total} 个模板, {types} 种盒型, {modules} 个模块")
    print(f"  DB: {DB_PATH}")
    print(f"  DXF: {TEMPLATE_DIR}")
    print(f"{'='*60}")

    conn.close()


if __name__ == "__main__":
    main()
