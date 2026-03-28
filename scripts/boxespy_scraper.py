#!/usr/bin/env python3
"""
boxes.py 开源盒型爬虫 + SVG 生成器
1. 爬取 https://boxes.hackerspace-bamberg.de/ 所有盒型及参数
2. 映射 Pacdora 分类
3. 调用 boxes.py API 生成默认尺寸 SVG 刀版图
4. 存入 dieline_library.db 和模版库

用法:
    python3 boxespy_scraper.py [数据库路径]
"""

import os
import sys
import json
import time
import random
import re
import sqlite3
import urllib.request
import urllib.error
import ssl
import gzip
from html.parser import HTMLParser
from typing import List, Dict, Optional, Set
from datetime import datetime

# ─── 路径 ─────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(
    PROJECT_ROOT, "项目清单", "刀模活字印刷3D项目", "推演数据", "dieline_library.db"
)
TEMPLATE_DIR = os.path.join(
    PROJECT_ROOT, "项目清单", "刀模活字印刷3D项目", "模版库"
)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

BOXES_BASE = "https://boxes.hackerspace-bamberg.de"

# ─── boxes.py 盒型 → Pacdora 分类映射 ────────────────────────────
CATEGORY_MAP = {
    # Boxes
    "ABox": ("折叠盒", "folding-box"),
    "AngledBox": ("异形盒", "folding-box"),
    "BasedBox": ("底座盒", "folding-box"),
    "BayonetBox": ("卡扣盒", "folding-box"),
    "CardBox": ("卡片盒", "folding-box"),
    "ClosedBox": ("封闭盒", "folding-box"),
    "Console": ("控制台盒", "display-box"),
    "Console2": ("控制台盒2", "display-box"),
    "Crate": ("板条箱", "shipping-box"),
    "DiceBox": ("骰子盒", "gift-box"),
    "DisplayCase": ("展示柜", "display-box"),
    "ElectronicsBox": ("电子元件盒", "storage-box"),
    "HalfBox": ("半开盒", "tray-box"),
    "HingeBox": ("铰链盒", "folding-box"),
    "IntegratedHingeBox": ("一体铰链盒", "folding-box"),
    "NotesHolder": ("便签盒", "folding-box"),
    "OpenBox": ("开口盒", "tray-box"),
    "PirateChest": ("宝箱盒", "gift-box"),
    "RegularBox": ("常规盒", "folding-box"),
    "SlidingDrawer": ("抽屉盒", "folding-box"),
    "SlidingLidBox": ("滑盖盒", "folding-box"),
    "TwoPiece": ("天地盖", "gift-box"),
    "UniversalBox": ("通用盒", "folding-box"),
    # Boxes with flex
    "FlexBox": ("弹性盒", "folding-box"),
    "FlexBox2": ("弹性盒2", "folding-box"),
    "FlexBox3": ("弹性盒3", "folding-box"),
    "FlexBox4": ("弹性盒4", "folding-box"),
    "FlexBox5": ("弹性盒5", "folding-box"),
    "HeartBox": ("心形盒", "gift-box"),
    "RoundedBox": ("圆角盒", "folding-box"),
    "ShutterBox": ("卷帘盒", "folding-box"),
    # Trays
    "CompartmentBox": ("分隔盒", "insert-box"),
    "DividerTray": ("分隔托盘", "tray-box"),
    "SmallPartsTray": ("零件托盘", "tray-box"),
    "TypeTray": ("活字托盘", "tray-box"),
    "TrayInsert": ("托盘内衬", "insert-box"),
    "TrayLayout": ("托盘布局", "tray-box"),
    # Shelves
    "DisplayShelf": ("展示架", "display-box"),
    "StorageShelf": ("储物架", "storage-box"),
    "StackableBin": ("可叠放箱", "storage-box"),
    # Misc relevant to packaging
    "PaperBox": ("纸盒", "folding-box"),
    "MagazineFile": ("杂志架", "folding-box"),
    "Folder": ("文件夹", "folding-box"),
    "BottleTag": ("瓶标签", "tag"),
}

# 适合刀模/包装的盒型 (从100+中筛选最相关的)
PACKAGING_BOX_TYPES = [
    "ABox", "AngledBox", "BasedBox", "CardBox", "ClosedBox",
    "Console", "Crate", "DiceBox", "DisplayCase", "HalfBox",
    "HingeBox", "IntegratedHingeBox", "NotesHolder", "OpenBox",
    "PirateChest", "RegularBox", "SlidingDrawer", "SlidingLidBox",
    "TwoPiece", "UniversalBox",
    "FlexBox", "FlexBox2", "FlexBox3", "FlexBox4", "FlexBox5",
    "HeartBox", "RoundedBox", "ShutterBox",
    "CompartmentBox", "DividerTray", "SmallPartsTray", "TypeTray",
    "TrayInsert", "TrayLayout",
    "DisplayShelf", "StorageShelf", "StackableBin",
    "PaperBox", "MagazineFile", "Folder",
]


# ═══════════════════════════════════════════════════════════════════
#  HTML 解析: 从盒型页面提取参数
# ═══════════════════════════════════════════════════════════════════

class BoxPageParser(HTMLParser):
    """解析 boxes.py 单个盒型页面, 提取表单参数和默认值"""

    def __init__(self):
        super().__init__()
        self.params: Dict[str, dict] = {}
        self.description = ""
        self.images: List[str] = []
        self._in_label = False
        self._current_label = ""
        self._in_desc = False
        self._desc_text = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)

        if tag == "input" and d.get("name"):
            name = d["name"]
            self.params[name] = {
                "type": d.get("type", "text"),
                "default": d.get("value", ""),
                "name": name,
            }

        if tag == "select" and d.get("name"):
            self.params[d["name"]] = {
                "type": "select",
                "default": "",
                "name": d["name"],
                "options": [],
            }

        if tag == "option":
            # Find parent select
            val = d.get("value", "")
            selected = "selected" in d
            # Attach to last select param
            for p in reversed(list(self.params.values())):
                if p["type"] == "select":
                    p["options"].append(val)
                    if selected:
                        p["default"] = val
                    break

        if tag == "img":
            src = d.get("src", "")
            if src and ("static" in src or "sample" in src or ".png" in src or ".svg" in src):
                self.images.append(src if src.startswith("http") else BOXES_BASE + "/" + src.lstrip("/"))

        if tag == "p" or tag == "div":
            cls = d.get("class", "")
            if "description" in cls or "help" in cls:
                self._in_desc = True

        if tag == "meta":
            if d.get("name") == "description":
                self.description = d.get("content", "")

    def handle_endtag(self, tag):
        if tag in ("p", "div") and self._in_desc:
            self._in_desc = False

    def handle_data(self, data):
        text = data.strip()
        if self._in_desc and text:
            self._desc_text.append(text)


# ═══════════════════════════════════════════════════════════════════
#  HTTP
# ═══════════════════════════════════════════════════════════════════

def human_delay():
    d = random.uniform(3, 5)
    print(f"    ⏳ 等待 {d:.1f}s...")
    time.sleep(d)


def fetch(url: str, accept: str = "text/html") -> Optional[bytes]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125.0.0.0",
                "Accept": accept,
                "Accept-Encoding": "gzip, deflate",
            })
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                data = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if enc == "gzip":
                    data = gzip.decompress(data)
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt < 2:
                time.sleep(random.uniform(3, 6))
        except Exception:
            if attempt < 2:
                time.sleep(random.uniform(2, 4))
    return None


def fetch_text(url: str) -> Optional[str]:
    data = fetch(url)
    return data.decode("utf-8", errors="replace") if data else None


# ═══════════════════════════════════════════════════════════════════
#  Gallery 解析: 提取所有盒型名称
# ═══════════════════════════════════════════════════════════════════

class GalleryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.box_types: List[Dict] = []
        self._current_category = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a":
            href = d.get("href", "")
            if href and not href.startswith("http") and not href.startswith("#") and href != "/":
                name = href.strip("/")
                if name and not name.startswith("static") and "." not in name:
                    self.box_types.append({
                        "name": name,
                        "url": f"{BOXES_BASE}/{name}",
                        "category": self._current_category,
                    })

    def handle_data(self, data):
        text = data.strip()
        if text in ("Boxes", "Boxes with flex", "Trays and Drawer Inserts",
                     "Shelves", "WallMounted", "Hole patterns",
                     "Parts and Samples", "Misc", "Unstable"):
            self._current_category = text


# ═══════════════════════════════════════════════════════════════════
#  数据库
# ═══════════════════════════════════════════════════════════════════

class TemplateDB:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS boxespy_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_type TEXT NOT NULL,
            url TEXT UNIQUE,
            category_en TEXT,
            category_zh TEXT,
            pacdora_category TEXT,
            description TEXT,
            params_json TEXT,
            default_x REAL,
            default_y REAL,
            default_h REAL,
            svg_path TEXT,
            image_url TEXT,
            source TEXT DEFAULT 'boxes.py',
            scraped_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_bt_type ON boxespy_templates(box_type);
        CREATE INDEX IF NOT EXISTS idx_bt_pacdora ON boxespy_templates(pacdora_category);
        """)
        self.conn.commit()

    def upsert(self, data: dict) -> bool:
        url = data.get("url", "")
        existing = self.conn.execute("SELECT id FROM boxespy_templates WHERE url=?", (url,)).fetchone()
        if existing:
            cols = [k for k in data if k not in ("url", "id")]
            if cols:
                sets = ", ".join(f"{k}=?" for k in cols)
                self.conn.execute(f"UPDATE boxespy_templates SET {sets} WHERE url=?",
                                  [data[k] for k in cols] + [url])
                self.conn.commit()
            return False
        cols = [k for k in data if k != "id"]
        self.conn.execute(
            f"INSERT INTO boxespy_templates ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})",
            [data[k] for k in cols])
        self.conn.commit()
        return True

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM boxespy_templates").fetchone()[0]

    def close(self):
        self.conn.close()


# ═══════════════════════════════════════════════════════════════════
#  主爬虫
# ═══════════════════════════════════════════════════════════════════

class BoxesPyScraper:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db = TemplateDB(db_path)
        self.new_count = 0
        self.svg_count = 0

    def scrape_gallery(self) -> List[Dict]:
        """爬取首页gallery获取所有盒型列表"""
        print("  爬取 boxes.py Gallery...")
        html = fetch_text(BOXES_BASE + "/")
        if not html:
            print("    ✗ Gallery 获取失败")
            return []
        parser = GalleryParser()
        parser.feed(html)
        print(f"    → 发现 {len(parser.box_types)} 个盒型")
        return parser.box_types

    def scrape_box_page(self, box_type: str) -> Dict:
        """爬取单个盒型页面, 提取参数和描述"""
        url = f"{BOXES_BASE}/{box_type}"
        html = fetch_text(url)
        if not html:
            return {"error": "fetch failed"}

        parser = BoxPageParser()
        try:
            parser.feed(html)
        except Exception:
            pass

        # 提取 title
        title_match = re.search(r'<title>(.*?)</title>', html)
        title = title_match.group(1) if title_match else box_type

        # 提取描述
        desc = parser.description
        if not desc and parser._desc_text:
            desc = " ".join(parser._desc_text)[:500]
        if not desc:
            # 从 HTML 正文中寻找描述
            desc_match = re.search(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
            if desc_match:
                desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()[:300]

        # 提取默认尺寸
        x = float(parser.params.get("x", {}).get("default", 0) or 0)
        y = float(parser.params.get("y", {}).get("default", 0) or 0)
        h = float(parser.params.get("h", {}).get("default", 0) or 0)

        return {
            "title": title,
            "description": desc,
            "params": parser.params,
            "images": parser.images,
            "default_x": x or 100,
            "default_y": y or 80,
            "default_h": h or 60,
        }

    def generate_svg(self, box_type: str, x: float = 100, y: float = 80, h: float = 60) -> Optional[str]:
        """调用 boxes.py API 生成 SVG"""
        url = f"{BOXES_BASE}/{box_type}?x={x}&y={y}&h={h}&format=svg&render=1"
        data = fetch(url, accept="image/svg+xml")
        if not data:
            return None

        text = data.decode("utf-8", errors="replace")
        if "<svg" not in text.lower():
            return None

        # 保存 SVG
        filename = f"{box_type}_{int(x)}x{int(y)}x{int(h)}.svg"
        filepath = os.path.join(TEMPLATE_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return filepath

    def scrape_all(self):
        print(f"\n{'='*60}")
        print(f"  boxes.py 盒型爬虫 + SVG 生成器")
        print(f"  目标: {BOXES_BASE}")
        print(f"  策略: Gallery→筛选包装相关→参数提取→SVG生成")
        print(f"  人类节奏: 3~5s/请求")
        print(f"{'='*60}\n")

        t0 = time.time()

        # Step 1: 爬取 gallery
        all_types = self.scrape_gallery()

        # Step 2: 筛选包装/刀模相关盒型
        target_types = [t for t in all_types if t["name"] in PACKAGING_BOX_TYPES]
        # 补充未在gallery中发现的
        found_names = {t["name"] for t in target_types}
        for name in PACKAGING_BOX_TYPES:
            if name not in found_names:
                target_types.append({"name": name, "url": f"{BOXES_BASE}/{name}", "category": "Boxes"})

        print(f"\nStep 2: 筛选包装相关盒型 → {len(target_types)} 个\n")

        # Step 3: 逐个爬取参数 + 生成 SVG
        for i, bt in enumerate(target_types):
            box_type = bt["name"]
            cat_zh, pacdora_cat = CATEGORY_MAP.get(box_type, ("其他", "folding-box"))
            print(f"  [{i+1}/{len(target_types)}] {box_type} ({cat_zh})")

            human_delay()

            # 爬取页面参数
            info = self.scrape_box_page(box_type)
            if "error" in info:
                print(f"    ✗ 页面获取失败, 跳过")
                continue

            print(f"    → 参数: {len(info['params'])} 个, 默认尺寸: {info['default_x']}×{info['default_y']}×{info['default_h']}")

            # 生成 SVG
            human_delay()
            svg_path = self.generate_svg(
                box_type,
                info["default_x"],
                info["default_y"],
                info["default_h"])

            if svg_path:
                self.svg_count += 1
                print(f"    → ✓ SVG: {os.path.basename(svg_path)}")
            else:
                svg_path = ""
                print(f"    → ⚠ SVG 生成失败")

            # 存入数据库
            record = {
                "box_type": box_type,
                "url": f"{BOXES_BASE}/{box_type}",
                "category_en": bt.get("category", "Boxes"),
                "category_zh": cat_zh,
                "pacdora_category": pacdora_cat,
                "description": info.get("description", "")[:500],
                "params_json": json.dumps(
                    {k: {"type": v["type"], "default": v["default"]}
                     for k, v in info["params"].items()},
                    ensure_ascii=False),
                "default_x": info["default_x"],
                "default_y": info["default_y"],
                "default_h": info["default_h"],
                "svg_path": svg_path,
                "image_url": info["images"][0] if info["images"] else "",
                "source": "boxes.py",
            }
            is_new = self.db.upsert(record)
            if is_new:
                self.new_count += 1

        # 统计
        elapsed = time.time() - t0
        total = self.db.count()
        print(f"\n{'='*60}")
        print(f"  ✅ boxes.py 爬取完成 ({elapsed:.1f}s)")
        print(f"  盒型总数: {total} (本次新增: {self.new_count})")
        print(f"  SVG生成: {self.svg_count} 个 → {TEMPLATE_DIR}")
        print(f"{'='*60}\n")

    def close(self):
        self.db.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    scraper = BoxesPyScraper(db_path)
    scraper.scrape_all()
    scraper.close()
