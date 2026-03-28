#!/usr/bin/env python3
"""
刀模图纸数据库导入工具
递归扫描目录，将所有 DWG/DXF 文件的元数据和几何实体存入 SQLite 数据库。
DXF 文件可直接用 ezdxf 解析实体; DWG 文件记录元数据(需 ODA 转换后再解析实体)。

用法:
    python3 dieline_db_ingest.py [目录路径] [数据库路径]
    python3 dieline_db_ingest.py   # 默认: 拉扯图形目录 → dieline_library.db
"""

import os
import sys
import json
import math
import sqlite3
import hashlib
import time
from datetime import datetime
from pathlib import Path

try:
    import ezdxf
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False
    print("⚠ ezdxf 未安装, DXF实体解析将跳过。pip install ezdxf")

# ─── 默认路径 ────────────────────────────────────────────────────
DEFAULT_SOURCE_DIR = "/Users/administruter/Desktop/拉扯图形"
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "项目清单", "刀模活字印刷3D项目", "推演数据", "dieline_library.db"
)
CAD_EXTENSIONS = {".dwg", ".dxf"}


# ═══════════════════════════════════════════════════════════════════
#  数据库
# ═══════════════════════════════════════════════════════════════════

class DielineDB:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self.db_path = db_path

    def _init_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS cad_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL UNIQUE,
            rel_path TEXT,
            extension TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            file_hash TEXT,
            client_name TEXT,
            dimensions_text TEXT,
            flute_type TEXT,
            entity_count INTEGER DEFAULT 0,
            line_count INTEGER DEFAULT 0,
            arc_count INTEGER DEFAULT 0,
            circle_count INTEGER DEFAULT 0,
            polyline_count INTEGER DEFAULT 0,
            text_count INTEGER DEFAULT 0,
            layer_names TEXT DEFAULT '[]',
            bbox_json TEXT,
            parsed INTEGER DEFAULT 0,
            parse_error TEXT,
            source TEXT DEFAULT 'local',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cad_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            entity_type TEXT NOT NULL,
            layer TEXT DEFAULT '0',
            role TEXT DEFAULT 'UNKNOWN',
            start_x REAL, start_y REAL,
            end_x REAL, end_y REAL,
            center_x REAL, center_y REAL,
            radius REAL,
            start_angle REAL, end_angle REAL,
            length_mm REAL DEFAULT 0,
            color INTEGER,
            linetype TEXT,
            extra_json TEXT,
            FOREIGN KEY (file_id) REFERENCES cad_files(id)
        );

        CREATE TABLE IF NOT EXISTS pacdora_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT UNIQUE,
            category TEXT,
            subcategory TEXT,
            image_url TEXT,
            description TEXT,
            dimensions TEXT,
            tags TEXT DEFAULT '[]',
            formats TEXT DEFAULT '[]',
            source TEXT DEFAULT 'pacdora',
            scraped_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_cad_files_client ON cad_files(client_name);
        CREATE INDEX IF NOT EXISTS idx_cad_files_ext ON cad_files(extension);
        CREATE INDEX IF NOT EXISTS idx_cad_entities_file ON cad_entities(file_id);
        CREATE INDEX IF NOT EXISTS idx_cad_entities_type ON cad_entities(entity_type);
        CREATE INDEX IF NOT EXISTS idx_cad_entities_role ON cad_entities(role);
        CREATE INDEX IF NOT EXISTS idx_pacdora_category ON pacdora_items(category);
        """)
        self.conn.commit()

    # ─── cad_files ───────────────────────────────────────────────

    def file_exists(self, filepath: str) -> bool:
        r = self.conn.execute("SELECT id FROM cad_files WHERE filepath=?", (filepath,)).fetchone()
        return r is not None

    def upsert_file(self, data: dict) -> int:
        existing = self.conn.execute(
            "SELECT id FROM cad_files WHERE filepath=?", (data["filepath"],)).fetchone()
        if existing:
            fid = existing["id"]
            cols = [k for k in data if k != "filepath"]
            sets = ", ".join(f"{k}=?" for k in cols)
            vals = [data[k] for k in cols] + [data["filepath"]]
            self.conn.execute(f"UPDATE cad_files SET {sets}, updated_at=datetime('now') WHERE filepath=?", vals)
            self.conn.commit()
            return fid
        else:
            cols = list(data.keys())
            placeholders = ",".join("?" for _ in cols)
            vals = [data[k] for k in cols]
            cur = self.conn.execute(
                f"INSERT INTO cad_files ({','.join(cols)}) VALUES ({placeholders})", vals)
            self.conn.commit()
            return cur.lastrowid

    # ─── cad_entities ────────────────────────────────────────────

    def clear_entities(self, file_id: int):
        self.conn.execute("DELETE FROM cad_entities WHERE file_id=?", (file_id,))
        self.conn.commit()

    def insert_entity(self, file_id: int, entity: dict):
        entity["file_id"] = file_id
        cols = list(entity.keys())
        placeholders = ",".join("?" for _ in cols)
        self.conn.execute(
            f"INSERT INTO cad_entities ({','.join(cols)}) VALUES ({placeholders})",
            [entity[k] for k in cols])

    def bulk_insert_entities(self, file_id: int, entities: list):
        self.clear_entities(file_id)
        for e in entities:
            self.insert_entity(file_id, e)
        self.conn.commit()

    # ─── pacdora_items ───────────────────────────────────────────

    def upsert_pacdora(self, data: dict) -> int:
        existing = self.conn.execute(
            "SELECT id FROM pacdora_items WHERE url=?", (data.get("url", ""),)).fetchone()
        if existing:
            pid = existing["id"]
            cols = [k for k in data if k != "url"]
            if cols:
                sets = ", ".join(f"{k}=?" for k in cols)
                vals = [data[k] for k in cols] + [data["url"]]
                self.conn.execute(f"UPDATE pacdora_items SET {sets} WHERE url=?", vals)
            self.conn.commit()
            return pid
        else:
            cols = list(data.keys())
            placeholders = ",".join("?" for _ in cols)
            cur = self.conn.execute(
                f"INSERT INTO pacdora_items ({','.join(cols)}) VALUES ({placeholders})",
                [data[k] for k in cols])
            self.conn.commit()
            return cur.lastrowid

    # ─── 查询 ───────────────────────────────────────────────────

    def get_file_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM cad_files").fetchone()[0]

    def get_entity_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM cad_entities").fetchone()[0]

    def get_pacdora_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM pacdora_items").fetchone()[0]

    def search_files(self, keyword: str = "", client: str = "", ext: str = "", limit: int = 50) -> list:
        q = "SELECT * FROM cad_files WHERE 1=1"
        params = []
        if keyword:
            q += " AND (filename LIKE ? OR dimensions_text LIKE ?)"
            params += [f"%{keyword}%", f"%{keyword}%"]
        if client:
            q += " AND client_name LIKE ?"
            params.append(f"%{client}%")
        if ext:
            q += " AND extension=?"
            params.append(ext)
        q += f" ORDER BY updated_at DESC LIMIT {limit}"
        return [dict(r) for r in self.conn.execute(q, params).fetchall()]

    def get_file_entities(self, file_id: int, role: str = None) -> list:
        if role:
            return [dict(r) for r in self.conn.execute(
                "SELECT * FROM cad_entities WHERE file_id=? AND role=?", (file_id, role))]
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM cad_entities WHERE file_id=?", (file_id,))]

    def get_stats(self) -> dict:
        files = self.get_file_count()
        entities = self.get_entity_count()
        pacdora = self.get_pacdora_count()
        parsed = self.conn.execute("SELECT COUNT(*) FROM cad_files WHERE parsed=1").fetchone()[0]
        by_ext = {}
        for r in self.conn.execute("SELECT extension, COUNT(*) as cnt FROM cad_files GROUP BY extension"):
            by_ext[r["extension"]] = r["cnt"]
        by_client = {}
        for r in self.conn.execute(
                "SELECT client_name, COUNT(*) as cnt FROM cad_files WHERE client_name IS NOT NULL "
                "GROUP BY client_name ORDER BY cnt DESC LIMIT 20"):
            by_client[r["client_name"]] = r["cnt"]
        return {
            "total_files": files, "parsed_files": parsed, "total_entities": entities,
            "pacdora_items": pacdora, "by_extension": by_ext, "top_clients": by_client,
        }

    def close(self):
        self.conn.close()


# ═══════════════════════════════════════════════════════════════════
#  文件扫描与解析
# ═══════════════════════════════════════════════════════════════════

def _file_hash(filepath: str) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_client_name(filepath: str, base_dir: str) -> str:
    """从文件名或路径提取客户名"""
    rel = os.path.relpath(filepath, base_dir)
    name = os.path.splitext(os.path.basename(filepath))[0]
    # 去除常见后缀
    for suffix in [".bak", " 副本", "（1）", "(1)", "-1", "-2", "_1", "_2"]:
        name = name.replace(suffix, "")
    # 如果文件在子目录中，子目录名可能是客户名
    parts = rel.split(os.sep)
    if len(parts) > 1:
        parent = parts[0]
        if parent not in ("dxf_output", "12订单", "昊席刀模", "聚松刀模图"):
            return parent
    return name.strip()


def _extract_dimensions(filename: str) -> str:
    """从文件名提取尺寸信息"""
    import re
    # 匹配 310X233X245 或 310x233x245 格式
    m = re.search(r'(\d{2,4})[xX×](\d{2,4})[xX×](\d{2,4})', filename)
    if m:
        return f"{m.group(1)}×{m.group(2)}×{m.group(3)}mm"
    return ""


def _extract_flute(filename: str) -> str:
    """从文件名提取楞型"""
    import re
    m = re.search(r'([A-F]楞|[A-F]瓦|BE楞|AB楞|BC楞)', filename)
    if m:
        return m.group(1)
    return ""


def _classify_layer(layer_name: str) -> str:
    """将图层名分类为角色"""
    ln = layer_name.upper()
    if any(k in ln for k in ("CUT", "模切", "切割", "刀", "DIE")):
        return "CUT"
    if any(k in ln for k in ("CREASE", "压痕", "折痕", "SCORE", "FOLD")):
        return "CREASE"
    if any(k in ln for k in ("PERF", "穿孔", "虚切")):
        return "PERF"
    if any(k in ln for k in ("GUIDE", "辅助", "REF", "CENTER")):
        return "GUIDE"
    if any(k in ln for k in ("DIM", "标注", "ANNO", "TEXT")):
        return "DIM"
    return "CUT"  # 默认为切割线


def parse_dxf_file(filepath: str) -> dict:
    """解析DXF文件，提取实体和元数据"""
    result = {
        "entities": [],
        "layers": [],
        "entity_count": 0,
        "line_count": 0, "arc_count": 0, "circle_count": 0,
        "polyline_count": 0, "text_count": 0,
        "bbox": None,
        "error": None,
    }

    if not HAS_EZDXF:
        result["error"] = "ezdxf not installed"
        return result

    try:
        doc = ezdxf.readfile(filepath)
    except Exception as e:
        result["error"] = str(e)[:500]
        return result

    msp = doc.modelspace()
    layers = set()
    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")

    def _update_bbox(x, y):
        nonlocal min_x, min_y, max_x, max_y
        if x is not None and y is not None:
            min_x, min_y = min(min_x, x), min(min_y, y)
            max_x, max_y = max(max_x, x), max(max_y, y)

    for entity in msp:
        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"
        layers.add(layer)
        role = _classify_layer(layer)
        color = entity.dxf.color if hasattr(entity.dxf, "color") else 0
        lt = entity.dxf.linetype if hasattr(entity.dxf, "linetype") else ""

        etype = entity.dxftype()

        if etype == "LINE":
            s, e = entity.dxf.start, entity.dxf.end
            length = math.hypot(e.x - s.x, e.y - s.y)
            _update_bbox(s.x, s.y)
            _update_bbox(e.x, e.y)
            result["entities"].append({
                "entity_type": "LINE", "layer": layer, "role": role,
                "start_x": round(s.x, 3), "start_y": round(s.y, 3),
                "end_x": round(e.x, 3), "end_y": round(e.y, 3),
                "length_mm": round(length, 3),
                "color": color, "linetype": lt,
            })
            result["line_count"] += 1

        elif etype == "ARC":
            cx, cy = entity.dxf.center.x, entity.dxf.center.y
            r = entity.dxf.radius
            sa = entity.dxf.start_angle
            ea = entity.dxf.end_angle
            arc_angle = (ea - sa) % 360
            arc_len = math.pi * r * arc_angle / 180
            sp_x = cx + r * math.cos(math.radians(sa))
            sp_y = cy + r * math.sin(math.radians(sa))
            ep_x = cx + r * math.cos(math.radians(ea))
            ep_y = cy + r * math.sin(math.radians(ea))
            _update_bbox(sp_x, sp_y)
            _update_bbox(ep_x, ep_y)
            result["entities"].append({
                "entity_type": "ARC", "layer": layer, "role": role,
                "start_x": round(sp_x, 3), "start_y": round(sp_y, 3),
                "end_x": round(ep_x, 3), "end_y": round(ep_y, 3),
                "center_x": round(cx, 3), "center_y": round(cy, 3),
                "radius": round(r, 3),
                "start_angle": round(sa, 2), "end_angle": round(ea, 2),
                "length_mm": round(arc_len, 3),
                "color": color, "linetype": lt,
            })
            result["arc_count"] += 1

        elif etype == "CIRCLE":
            cx, cy = entity.dxf.center.x, entity.dxf.center.y
            r = entity.dxf.radius
            _update_bbox(cx - r, cy - r)
            _update_bbox(cx + r, cy + r)
            result["entities"].append({
                "entity_type": "CIRCLE", "layer": layer, "role": role,
                "center_x": round(cx, 3), "center_y": round(cy, 3),
                "radius": round(r, 3),
                "length_mm": round(2 * math.pi * r, 3),
                "color": color, "linetype": lt,
            })
            result["circle_count"] += 1

        elif etype in ("LWPOLYLINE", "POLYLINE"):
            try:
                if etype == "LWPOLYLINE":
                    pts = list(entity.get_points(format="xyseb"))
                else:
                    pts = [(v.dxf.location.x, v.dxf.location.y, 0, 0, 0) for v in entity.vertices]
                total_len = 0
                for i in range(len(pts) - 1):
                    x1, y1 = pts[i][0], pts[i][1]
                    x2, y2 = pts[i + 1][0], pts[i + 1][1]
                    total_len += math.hypot(x2 - x1, y2 - y1)
                    _update_bbox(x1, y1)
                if pts:
                    _update_bbox(pts[-1][0], pts[-1][1])
                    result["entities"].append({
                        "entity_type": "POLYLINE", "layer": layer, "role": role,
                        "start_x": round(pts[0][0], 3), "start_y": round(pts[0][1], 3),
                        "end_x": round(pts[-1][0], 3), "end_y": round(pts[-1][1], 3),
                        "length_mm": round(total_len, 3),
                        "color": color, "linetype": lt,
                        "extra_json": json.dumps({"vertex_count": len(pts),
                                                   "closed": getattr(entity, "closed", False)}),
                    })
                result["polyline_count"] += 1
            except Exception:
                result["polyline_count"] += 1

        elif etype in ("TEXT", "MTEXT"):
            try:
                text = entity.dxf.text if hasattr(entity.dxf, "text") else ""
                ins = entity.dxf.insert if hasattr(entity.dxf, "insert") else None
                if ins:
                    _update_bbox(ins.x, ins.y)
                result["entities"].append({
                    "entity_type": "TEXT", "layer": layer, "role": "DIM",
                    "start_x": round(ins.x, 3) if ins else 0,
                    "start_y": round(ins.y, 3) if ins else 0,
                    "extra_json": json.dumps({"text": text[:200]}, ensure_ascii=False),
                    "color": color,
                })
                result["text_count"] += 1
            except Exception:
                result["text_count"] += 1

    result["entity_count"] = len(result["entities"])
    result["layers"] = sorted(layers)
    if min_x < float("inf"):
        result["bbox"] = {
            "min_x": round(min_x, 2), "min_y": round(min_y, 2),
            "max_x": round(max_x, 2), "max_y": round(max_y, 2),
            "width": round(max_x - min_x, 2), "height": round(max_y - min_y, 2),
        }

    return result


# ═══════════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════════

def ingest_directory(source_dir: str, db_path: str, force_reparse: bool = False):
    """递归扫描目录，将所有CAD文件导入数据库"""
    db = DielineDB(db_path)
    source_dir = os.path.abspath(source_dir)

    print(f"\n{'='*60}")
    print(f"  刀模图纸数据库导入")
    print(f"  源目录: {source_dir}")
    print(f"  数据库: {db_path}")
    print(f"{'='*60}\n")

    # 扫描文件
    cad_files = []
    for root, dirs, files in os.walk(source_dir):
        # 跳过隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in CAD_EXTENSIONS:
                cad_files.append(os.path.join(root, f))

    print(f"发现 {len(cad_files)} 个CAD文件\n")

    ingested = 0
    parsed = 0
    errors = 0
    skipped = 0
    t0 = time.time()

    for i, fp in enumerate(cad_files):
        filename = os.path.basename(fp)
        ext = os.path.splitext(filename)[1].lower()
        rel_path = os.path.relpath(fp, source_dir)

        # 进度
        if (i + 1) % 50 == 0 or i == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  [{i+1}/{len(cad_files)}] {rate:.1f} files/s ...")

        # 检查是否已导入且未变化
        if not force_reparse and db.file_exists(fp):
            skipped += 1
            continue

        # 基本元数据
        try:
            file_size = os.path.getsize(fp)
            fhash = _file_hash(fp)
        except Exception:
            errors += 1
            continue

        client = _extract_client_name(fp, source_dir)
        dims = _extract_dimensions(filename)
        flute = _extract_flute(filename)

        file_data = {
            "filename": filename,
            "filepath": fp,
            "rel_path": rel_path,
            "extension": ext,
            "file_size": file_size,
            "file_hash": fhash,
            "client_name": client,
            "dimensions_text": dims,
            "flute_type": flute,
            "source": "local",
        }

        # 解析DXF实体
        if ext == ".dxf" and HAS_EZDXF:
            parse_result = parse_dxf_file(fp)
            file_data["entity_count"] = parse_result["entity_count"]
            file_data["line_count"] = parse_result["line_count"]
            file_data["arc_count"] = parse_result["arc_count"]
            file_data["circle_count"] = parse_result["circle_count"]
            file_data["polyline_count"] = parse_result["polyline_count"]
            file_data["text_count"] = parse_result["text_count"]
            file_data["layer_names"] = json.dumps(parse_result["layers"], ensure_ascii=False)
            file_data["bbox_json"] = json.dumps(parse_result["bbox"]) if parse_result["bbox"] else None
            file_data["parsed"] = 1 if not parse_result["error"] else 0
            file_data["parse_error"] = parse_result["error"]

            fid = db.upsert_file(file_data)

            if parse_result["entities"]:
                db.bulk_insert_entities(fid, parse_result["entities"])
                parsed += 1
            elif parse_result["error"]:
                errors += 1
        else:
            # DWG: 仅记录元数据
            file_data["parsed"] = 0
            file_data["parse_error"] = "DWG binary format - needs ODA conversion" if ext == ".dwg" else None
            db.upsert_file(file_data)

        ingested += 1

    elapsed = time.time() - t0
    stats = db.get_stats()
    db.close()

    print(f"\n{'='*60}")
    print(f"  ✅ 导入完成 ({elapsed:.1f}s)")
    print(f"  新导入: {ingested} | 已解析DXF: {parsed} | 跳过: {skipped} | 错误: {errors}")
    print(f"  数据库统计:")
    print(f"    文件总数: {stats['total_files']}")
    print(f"    已解析: {stats['parsed_files']}")
    print(f"    实体总数: {stats['total_entities']}")
    print(f"    按格式: {stats['by_extension']}")
    print(f"    前10客户: {dict(list(stats['top_clients'].items())[:10])}")
    print(f"  数据库: {db_path}")
    print(f"{'='*60}\n")

    return stats


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOURCE_DIR
    dbp = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_DB_PATH
    ingest_directory(src, dbp)
