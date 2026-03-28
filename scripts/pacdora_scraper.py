#!/usr/bin/env python3
"""
Pacdora 刀版图库爬虫 v2.0
爬取 https://www.pacdora.cn/dielines 所有刀版条目，存入 dieline_library.db

核心策略:
  1. 从主页发现真实分类URL (后缀为 *-dielines / *-templates)
  2. 爬取每个分类页 → 提取 OG/meta + 嵌入JSON + 交叉链接
  3. 递归发现新分类URL直到无新链接
  4. 人类节奏: 每次请求间隔 3~6 秒随机延迟

用法:
    python3 pacdora_scraper.py [数据库路径]
"""

import os
import sys
import json
import time
import re
import random
import urllib.request
import urllib.parse
import urllib.error
import gzip
import ssl
import sqlite3
from datetime import datetime
from html.parser import HTMLParser
from typing import List, Dict, Optional, Set

# ─── 路径 ─────────────────────────────────────────────────────────
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "项目清单", "刀模活字印刷3D项目", "推演数据", "dieline_library.db"
)

BASE_URL = "https://www.pacdora.cn"
DIELINES_URL = f"{BASE_URL}/dielines"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# 从实际网站发现的真实分类URL (后缀 *-dielines / *-template(s))
SEED_CATEGORY_SLUGS = [
    "folding-box-dielines",
    "display-box-dielines",
    "tray-box-dielines",
    "tuck-end-box-dielines",
    "insert-box-dielines",
    "mailer-box-dielines",
    "paper-bag-dielines",
    "storage-box-dielines",
    "diy-box-template",
    "barbie-box-templates",
]


# ═══════════════════════════════════════════════════════════════════
#  HTML 解析: 从页面提取链接/图片/元数据
# ═══════════════════════════════════════════════════════════════════

class PageLinkExtractor(HTMLParser):
    """从 HTML 提取: /dielines/* 链接, /dieline/* 链接, 图片, OG标签, 标题"""

    def __init__(self):
        super().__init__()
        self.category_links: Set[str] = set()   # /dielines/xxx-dielines
        self.item_links: Set[str] = set()        # /dieline/xxx (单个模板)
        self.images: List[Dict] = []             # {src, alt}
        self.og: Dict[str, str] = {}             # og:title, og:description, og:image
        self.title = ""
        self.description = ""
        self._in_title = False
        self._in_a_href = ""
        self._a_text = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "title":
            self._in_title = True

        if tag == "meta":
            name = d.get("name", "")
            prop = d.get("property", "")
            content = d.get("content", "")
            if name == "description":
                self.description = content
            if prop.startswith("og:"):
                self.og[prop] = content

        if tag == "a":
            href = d.get("href", "")
            if href:
                full = href if href.startswith("http") else BASE_URL + href
                # 分类链接: /dielines/xxx (不是 /dieline/xxx 也不是 /dielines 本身)
                if re.match(r'^https?://www\.pacdora\.cn/dielines/[a-z0-9\-]+', full):
                    self.category_links.add(full.split("?")[0].rstrip("/"))
                # 单个模板: /dieline/xxx
                if "/dieline/" in href and "/dielines" not in href:
                    self.item_links.add(full.split("?")[0].rstrip("/"))
                self._in_a_href = full
                self._a_text = ""

        if tag == "img":
            src = d.get("src", "") or d.get("data-src", "") or d.get("data-original", "")
            alt = d.get("alt", "")
            if src and not src.startswith("data:"):
                self.images.append({"src": src, "alt": alt})

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "a":
            self._in_a_href = ""

    def handle_data(self, data):
        text = data.strip()
        if self._in_title and text:
            self.title = text
        if self._in_a_href and text:
            self._a_text += text


# ═══════════════════════════════════════════════════════════════════
#  HTTP: 模拟人类浏览器
# ═══════════════════════════════════════════════════════════════════

_request_count = 0

def human_delay():
    """模拟人类浏览节奏: 3~6秒随机延迟"""
    global _request_count
    _request_count += 1
    # 每5次请求多休息一下, 模拟阅读
    if _request_count % 5 == 0:
        d = random.uniform(5, 8)
    else:
        d = random.uniform(3, 6)
    print(f"    ⏳ 等待 {d:.1f}s (模拟人类浏览)...")
    time.sleep(d)


def fetch_page(url: str, referer: str = DIELINES_URL) -> Optional[str]:
    """获取网页, 带人类延迟和重试"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for attempt in range(3):
        try:
            ua = USER_AGENTS[attempt % len(USER_AGENTS)]
            req = urllib.request.Request(url, headers={
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": referer,
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            })
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                code = resp.getcode()
                if code == 404:
                    print(f"    ✗ 404 跳过: {url}")
                    return None
                data = resp.read()
                enc = resp.headers.get("Content-Encoding", "")
                if enc == "gzip":
                    data = gzip.decompress(data)
                ct = resp.headers.get("Content-Type", "")
                charset = "utf-8"
                if "charset=" in ct:
                    charset = ct.split("charset=")[-1].split(";")[0].strip()
                return data.decode(charset, errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"    ✗ 404 跳过: {url}")
                return None
            if attempt < 2:
                wait = random.uniform(5, 10)
                print(f"    ⚠ HTTP {e.code}, 重试 {attempt+1}/2 (等{wait:.0f}s)...")
                time.sleep(wait)
            else:
                print(f"    ✗ 失败 {url}: HTTP {e.code}")
                return None
        except Exception as e:
            if attempt < 2:
                time.sleep(random.uniform(3, 6))
            else:
                print(f"    ✗ 失败 {url}: {e}")
                return None
    return None


def extract_json_blocks(html: str) -> List[dict]:
    """从 SPA HTML 中提取嵌入的 JSON 数据块"""
    results = []
    patterns = [
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
        r'window\.__INITIAL_STATE__\s*=\s*({.*?})(?:;|\s*<)',
        r'window\.__NUXT__\s*=\s*(\(function.*?\))\s*(?:;|\s*<)',
    ]
    for pat in patterns:
        for m in re.findall(pat, html, re.DOTALL):
            try:
                obj = json.loads(m)
                if isinstance(obj, dict):
                    results.append(obj)
            except (json.JSONDecodeError, TypeError):
                pass
    return results


def flatten_items_from_json(data, depth=0) -> List[Dict]:
    """递归从 JSON 中提取包含 name/title + image/coverUrl 的对象"""
    if depth > 6:
        return []
    items = []
    if isinstance(data, list):
        for item in data:
            items.extend(flatten_items_from_json(item, depth + 1))
    elif isinstance(data, dict):
        # 检查当前对象是否像一个模板条目
        name = data.get("name") or data.get("title") or data.get("templateName") or ""
        img = (data.get("image") or data.get("imageUrl") or data.get("coverUrl")
               or data.get("thumbnail") or data.get("cover") or "")
        url = data.get("url") or data.get("link") or data.get("detailUrl") or ""
        slug = data.get("slug") or data.get("id") or ""
        if name and (img or url or slug):
            items.append({
                "name": str(name),
                "image_url": str(img),
                "url": str(url),
                "slug": str(slug),
                "category": str(data.get("category") or data.get("categoryName") or ""),
                "description": str(data.get("description") or data.get("desc") or "")[:500],
            })
        # 递归子字段
        for key in data:
            if isinstance(data[key], (dict, list)):
                items.extend(flatten_items_from_json(data[key], depth + 1))
    return items


# ═══════════════════════════════════════════════════════════════════
#  数据库
# ═══════════════════════════════════════════════════════════════════

class PacdoraDB:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS pacdora_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT UNIQUE,
            category TEXT,
            subcategory TEXT,
            dieline_image_url TEXT,
            mockup_image_url TEXT,
            image_url TEXT,
            description TEXT,
            dimensions TEXT,
            tags TEXT DEFAULT '[]',
            formats TEXT DEFAULT '[]',
            boxes_py_type TEXT,
            source TEXT DEFAULT 'pacdora',
            scraped_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS pacdora_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE,
            url TEXT,
            name TEXT,
            description TEXT,
            og_image TEXT,
            item_count INTEGER DEFAULT 0,
            scraped_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_pi_category ON pacdora_items(category);
        CREATE INDEX IF NOT EXISTS idx_pi_name ON pacdora_items(name);
        """)
        self.conn.commit()

    def upsert_category(self, slug, url, name, desc="", og_image="", count=0):
        existing = self.conn.execute("SELECT id FROM pacdora_categories WHERE slug=?", (slug,)).fetchone()
        if existing:
            self.conn.execute(
                "UPDATE pacdora_categories SET name=?,description=?,og_image=?,item_count=? WHERE slug=?",
                (name, desc, og_image, count, slug))
        else:
            self.conn.execute(
                "INSERT INTO pacdora_categories (slug,url,name,description,og_image,item_count) VALUES (?,?,?,?,?,?)",
                (slug, url, name, desc, og_image, count))
        self.conn.commit()

    def upsert_item(self, item: dict) -> bool:
        url = item.get("url", "")
        if not url:
            return False
        existing = self.conn.execute("SELECT id FROM pacdora_items WHERE url=?", (url,)).fetchone()
        if existing:
            cols = [k for k in item if k not in ("url", "id")]
            if cols:
                sets = ", ".join(f"{k}=?" for k in cols)
                self.conn.execute(f"UPDATE pacdora_items SET {sets} WHERE url=?",
                                  [item[k] for k in cols] + [url])
                self.conn.commit()
            return False
        cols = [k for k in item if k != "id"]
        self.conn.execute(
            f"INSERT INTO pacdora_items ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})",
            [item[k] for k in cols])
        self.conn.commit()
        return True

    def counts(self):
        cats = self.conn.execute("SELECT COUNT(*) FROM pacdora_categories").fetchone()[0]
        items = self.conn.execute("SELECT COUNT(*) FROM pacdora_items").fetchone()[0]
        return cats, items

    def close(self):
        self.conn.close()


# ═══════════════════════════════════════════════════════════════════
#  主爬虫
# ═══════════════════════════════════════════════════════════════════

class PacdoraScraper:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db = PacdoraDB(db_path)
        self.visited: Set[str] = set()
        self.to_visit: List[str] = []
        self.new_items = 0
        self.total_items = 0

    def _slug_from_url(self, url: str) -> str:
        return url.rstrip("/").split("/")[-1]

    def _category_name_from_slug(self, slug: str) -> str:
        """slug → 可读分类名"""
        name = slug.replace("-dielines", "").replace("-templates", "").replace("-template", "")
        return name.replace("-", " ").title()

    def scrape_page(self, url: str, category: str = "") -> dict:
        """爬取单个页面, 返回 {category_links, item_links, items, meta}"""
        result = {"category_links": set(), "item_links": set(), "items": [], "meta": {}}

        html = fetch_page(url, referer=DIELINES_URL)
        if not html:
            return result

        # 解析 HTML
        parser = PageLinkExtractor()
        try:
            parser.feed(html)
        except Exception:
            pass

        result["category_links"] = parser.category_links
        result["item_links"] = parser.item_links
        result["meta"] = {
            "title": parser.og.get("og:title", parser.title),
            "description": parser.og.get("og:description", parser.description),
            "image": parser.og.get("og:image", ""),
        }

        # 从图片中区分 CAD 刀版图(左侧) 和 3D 效果图(右侧)
        dieline_imgs = []
        mockup_imgs = []
        for img in parser.images:
            src = img["src"]
            alt = (img.get("alt") or "").lower()
            sl = src.lower()
            if any(k in sl or k in alt for k in ("dieline", "template", "刀版", "cad", "dxf", "svg")):
                dieline_imgs.append(src)
            elif any(k in sl or k in alt for k in ("mockup", "3d", "render", "preview", "效果")):
                mockup_imgs.append(src)
            elif "pacdora" in sl and ("png" in sl or "jpg" in sl or "webp" in sl):
                # 启发式: 第一张大图通常是组合图(左CAD+右3D)
                dieline_imgs.append(src)

        # 从 SPA JSON 提取条目
        json_blocks = extract_json_blocks(html)
        for block in json_blocks:
            flat = flatten_items_from_json(block)
            for item in flat:
                if not item.get("url") and item.get("slug"):
                    item["url"] = f"{BASE_URL}/dieline/{item['slug']}"
                if item.get("url") and not item["url"].startswith("http"):
                    item["url"] = BASE_URL + item["url"]
                item.setdefault("category", category)
                result["items"].append(item)

        # 从 item_links 生成条目
        for link in parser.item_links:
            slug = self._slug_from_url(link)
            name = slug.replace("-", " ").title()
            result["items"].append({
                "name": name,
                "url": link,
                "category": category,
                "image_url": "",
                "description": "",
            })

        # 附加图片信息
        for item in result["items"]:
            if not item.get("dieline_image_url") and dieline_imgs:
                item["dieline_image_url"] = dieline_imgs[0]
            if not item.get("mockup_image_url") and mockup_imgs:
                item["mockup_image_url"] = mockup_imgs[0]

        return result

    def scrape_all(self):
        print(f"\n{'='*60}")
        print(f"  Pacdora 刀版图库爬虫 v2.0")
        print(f"  目标: {DIELINES_URL}")
        print(f"  策略: 发现式爬取 + 人类节奏 (3~6s/页)")
        print(f"{'='*60}\n")

        t0 = time.time()

        # ── Step 1: 爬主页, 发现分类链接 ──
        print("Step 1: 爬取主页 → 发现分类...")
        self.visited.add(DIELINES_URL)
        main = self.scrape_page(DIELINES_URL)
        discovered = main["category_links"]
        print(f"  → 主页发现 {len(discovered)} 个分类链接")

        # 合并种子URL
        for slug in SEED_CATEGORY_SLUGS:
            discovered.add(f"{DIELINES_URL}/{slug}")

        # 保存主页条目
        for item in main["items"]:
            self._save_item(item)

        # ── Step 2: 逐个爬取分类页, 递归发现新分类 ──
        self.to_visit = sorted(discovered - self.visited)
        round_num = 0

        print(f"\nStep 2: 爬取分类页 (共 {len(self.to_visit)} 个待访问)...")

        while self.to_visit:
            url = self.to_visit.pop(0)
            if url in self.visited:
                continue
            self.visited.add(url)
            round_num += 1

            slug = self._slug_from_url(url)
            cat_name = self._category_name_from_slug(slug)
            print(f"\n  [{round_num}] 分类: {cat_name} ({slug})")

            human_delay()
            page_data = self.scrape_page(url, category=cat_name)
            meta = page_data["meta"]

            # 保存分类
            self.db.upsert_category(
                slug, url, meta.get("title", cat_name),
                meta.get("description", ""), meta.get("image", ""),
                len(page_data["items"]))

            # 保存条目
            saved = 0
            for item in page_data["items"]:
                if self._save_item(item):
                    saved += 1
            print(f"    → 标题: {meta.get('title', '?')[:50]}")
            print(f"    → 条目: {len(page_data['items'])} (新增 {saved})")
            print(f"    → 交叉链接: {len(page_data['category_links'])} 个分类")

            # 发现新分类
            new_cats = page_data["category_links"] - self.visited - set(self.to_visit)
            if new_cats:
                self.to_visit.extend(sorted(new_cats))
                print(f"    → 🔍 新发现 {len(new_cats)} 个分类: {[self._slug_from_url(u) for u in new_cats]}")

        # ── Step 3: 统计 ──
        elapsed = time.time() - t0
        cats, items = self.db.counts()
        print(f"\n{'='*60}")
        print(f"  ✅ 爬取完成 ({elapsed:.1f}s, {round_num}个分类页)")
        print(f"  分类数: {cats}")
        print(f"  条目总数: {items} (本次新增: {self.new_items})")
        print(f"  数据库: {self.db.conn.execute('PRAGMA database_list').fetchone()[2]}")
        print(f"{'='*60}\n")

    def _save_item(self, raw: dict) -> bool:
        url = raw.get("url", "")
        if not url:
            return False
        item = {
            "name": raw.get("name", ""),
            "url": url,
            "category": raw.get("category", ""),
            "image_url": raw.get("image_url", ""),
            "dieline_image_url": raw.get("dieline_image_url", ""),
            "mockup_image_url": raw.get("mockup_image_url", ""),
            "description": raw.get("description", "")[:500],
            "dimensions": raw.get("dimensions", ""),
            "tags": json.dumps(raw.get("tags", []), ensure_ascii=False) if isinstance(raw.get("tags"), list) else raw.get("tags", "[]"),
            "formats": json.dumps(["PDF", "DXF", "AI", "JPG"]),
            "source": "pacdora",
        }
        is_new = self.db.upsert_item(item)
        self.total_items += 1
        if is_new:
            self.new_items += 1
        return is_new

    def close(self):
        self.db.close()


# ═══════════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    scraper = PacdoraScraper(db_path)
    scraper.scrape_all()
    scraper.close()
