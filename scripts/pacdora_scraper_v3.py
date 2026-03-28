#!/usr/bin/env python3
"""
Pacdora 刀版图库爬虫 v3.0
一次 API 调用获取全部 ~6000 条刀版数据，下载原图到本地，存入数据库。

API: https://www.pacdora.cn/api/v2/models?pageSize=5999&current=1&dielineNameKey=all
图纸: https://oss.pacdora.cn/preview/dieline-{id}.png
效果图: https://oss.pacdora.cn/preview/mockup-{id}.jpg

用法:
    python3 pacdora_scraper_v3.py [数据库路径]
"""

import os
import sys
import json
import time
import random
import urllib.request
import urllib.error
import gzip
import ssl
import sqlite3
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── 路径 ─────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(
    PROJECT_ROOT, "项目清单", "刀模活字印刷3D项目", "推演数据", "dieline_library.db"
)
IMG_DIR = os.path.join(
    PROJECT_ROOT, "项目清单", "刀模活字印刷3D项目", "推演数据", "pacdora_images"
)

BASE_URL = "https://www.pacdora.cn"
API_URL = f"{BASE_URL}/api/v2/models?pageSize=5999&current=1&dielineNameKey=all"
OSS_BASE = "https://oss.pacdora.cn/preview"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


# ═══════════════════════════════════════════════════════════════════
#  HTTP
# ═══════════════════════════════════════════════════════════════════

def fetch_json(url: str) -> Optional[dict]:
    """GET JSON"""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip",
        "Referer": f"{BASE_URL}/dielines",
        "Origin": BASE_URL,
    })
    try:
        with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as resp:
            data = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
            return json.loads(data.decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  ✗ API 请求失败: {e}")
        return None


def download_image(url: str, save_path: str) -> bool:
    """下载图片到本地, 已存在则跳过"""
    if os.path.exists(save_path) and os.path.getsize(save_path) > 100:
        return True  # 已存在
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Referer": f"{BASE_URL}/dielines",
        })
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
            data = resp.read()
            if len(data) < 100:
                return False
            with open(save_path, "wb") as f:
                f.write(data)
            return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════
#  数据库
# ═══════════════════════════════════════════════════════════════════

def init_db(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS pacdora_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id INTEGER UNIQUE,
        name TEXT,
        name_en TEXT,
        slug TEXT,
        detail_url TEXT,
        category TEXT,
        dieline_image_url TEXT,
        dieline_image_local TEXT,
        mockup_image_url TEXT,
        mockup_image_local TEXT,
        dieline_status TEXT DEFAULT 'pending',
        mockup_status TEXT DEFAULT 'pending',
        tags TEXT DEFAULT '[]',
        formats TEXT DEFAULT '["PDF","DXF","AI","JPG"]',
        raw_json TEXT,
        source TEXT DEFAULT 'pacdora_api',
        scraped_at TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_pi_model ON pacdora_items(model_id);
    CREATE INDEX IF NOT EXISTS idx_pi_name ON pacdora_items(name);
    CREATE INDEX IF NOT EXISTS idx_pi_cat ON pacdora_items(category);
    CREATE INDEX IF NOT EXISTS idx_pi_dl_status ON pacdora_items(dieline_status);
    CREATE INDEX IF NOT EXISTS idx_pi_mk_status ON pacdora_items(mockup_status);
    """)
    # 兼容旧表: 如果缺少 status 列则自动添加
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(pacdora_items)").fetchall()}
        if "dieline_status" not in cols:
            conn.execute("ALTER TABLE pacdora_items ADD COLUMN dieline_status TEXT DEFAULT 'pending'")
            conn.execute("ALTER TABLE pacdora_items ADD COLUMN mockup_status TEXT DEFAULT 'pending'")
            # 根据已有 local 路径回填状态
            conn.execute("UPDATE pacdora_items SET dieline_status='downloaded' WHERE dieline_image_local != '' AND dieline_image_local IS NOT NULL")
            conn.execute("UPDATE pacdora_items SET mockup_status='downloaded' WHERE mockup_image_local != '' AND mockup_image_local IS NOT NULL")
            conn.commit()
            print("  ℹ 已自动添加 dieline_status/mockup_status 列并回填状态")
    except Exception:
        pass
    conn.commit()
    return conn


def upsert_item(conn: sqlite3.Connection, item: dict) -> bool:
    """插入或更新, 返回是否新增。更新时不覆盖已下载的状态和本地路径"""
    mid = item["model_id"]
    exists = conn.execute(
        "SELECT id, dieline_status, mockup_status, dieline_image_local, mockup_image_local "
        "FROM pacdora_items WHERE model_id=?", (mid,)
    ).fetchone()
    if exists:
        # 保留已下载的状态和本地路径, 不被API数据覆盖
        dl_local = exists[3] if exists[1] == "downloaded" else item.get("dieline_image_local", "")
        mk_local = exists[4] if exists[2] == "downloaded" else item.get("mockup_image_local", "")
        dl_status = exists[1] if exists[1] == "downloaded" else item.get("dieline_status", "pending")
        mk_status = exists[2] if exists[2] == "downloaded" else item.get("mockup_status", "pending")
        conn.execute("""UPDATE pacdora_items SET
            name=?, name_en=?, slug=?, detail_url=?, category=?,
            dieline_image_url=?, dieline_image_local=?,
            mockup_image_url=?, mockup_image_local=?,
            dieline_status=?, mockup_status=?,
            tags=?, raw_json=?
            WHERE model_id=?""",
            (item["name"], item["name_en"], item["slug"], item["detail_url"],
             item["category"],
             item["dieline_image_url"], dl_local,
             item["mockup_image_url"], mk_local,
             dl_status, mk_status,
             item["tags"], item["raw_json"], mid))
        return False
    else:
        conn.execute("""INSERT INTO pacdora_items
            (model_id, name, name_en, slug, detail_url, category,
             dieline_image_url, dieline_image_local,
             mockup_image_url, mockup_image_local,
             dieline_status, mockup_status,
             tags, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (mid, item["name"], item["name_en"], item["slug"], item["detail_url"],
             item["category"],
             item["dieline_image_url"], item.get("dieline_image_local", ""),
             item["mockup_image_url"], item.get("mockup_image_local", ""),
             "pending", "pending",
             item["tags"], item["raw_json"]))
        return True


# ═══════════════════════════════════════════════════════════════════
#  解析 API 数据
# ═══════════════════════════════════════════════════════════════════

def parse_item(raw: dict) -> dict:
    """从 API JSON 对象解析为标准条目"""
    mid = raw.get("id") or raw.get("modelId") or 0
    name = raw.get("dielineName") or raw.get("name") or raw.get("title") or ""
    name_en = raw.get("dielineNameEn") or raw.get("nameEn") or ""
    slug = raw.get("slug") or raw.get("urlSlug") or ""
    category = raw.get("categoryName") or raw.get("category") or ""

    # 构造 URL
    if slug:
        detail_url = f"{BASE_URL}/dielines-detail/{slug}"
    else:
        detail_url = f"{BASE_URL}/dielines-detail/{mid}"

    # 图片 URL
    dieline_url = f"{OSS_BASE}/dieline-{mid}.png"
    mockup_url = f"{OSS_BASE}/mockup-{mid}.jpg"

    tags = raw.get("tags") or raw.get("labelList") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = [tags]

    return {
        "model_id": int(mid),
        "name": name,
        "name_en": name_en,
        "slug": slug,
        "detail_url": detail_url,
        "category": category,
        "dieline_image_url": dieline_url,
        "dieline_image_local": "",
        "mockup_image_url": mockup_url,
        "mockup_image_local": "",
        "tags": json.dumps(tags, ensure_ascii=False),
        "raw_json": json.dumps(raw, ensure_ascii=False, default=str),
    }


# ═══════════════════════════════════════════════════════════════════
#  图片下载 (多线程, 人类节奏)
# ═══════════════════════════════════════════════════════════════════

def download_item_images(item: dict, img_dir: str) -> dict:
    """下载一个条目的 dieline + mockup 图片, 返回带状态的 item"""
    mid = item["model_id"]
    dieline_dir = os.path.join(img_dir, "dielines")
    mockup_dir = os.path.join(img_dir, "mockups")
    os.makedirs(dieline_dir, exist_ok=True)
    os.makedirs(mockup_dir, exist_ok=True)

    # dieline
    dl_path = os.path.join(dieline_dir, f"dieline-{mid}.png")
    if download_image(item["dieline_image_url"], dl_path):
        item["dieline_image_local"] = dl_path
        item["dieline_status"] = "downloaded"
    else:
        item["dieline_status"] = "failed"

    # mockup
    mk_path = os.path.join(mockup_dir, f"mockup-{mid}.jpg")
    if download_image(item["mockup_image_url"], mk_path):
        item["mockup_image_local"] = mk_path
        item["mockup_status"] = "downloaded"
    else:
        item["mockup_status"] = "failed"

    return item


def get_pending_items(conn: sqlite3.Connection) -> list:
    """从数据库获取所有未完成下载的条目 (pending 或 failed)"""
    rows = conn.execute("""
        SELECT model_id, name, name_en, slug, detail_url, category,
               dieline_image_url, dieline_image_local,
               mockup_image_url, mockup_image_local,
               dieline_status, mockup_status, tags
        FROM pacdora_items
        WHERE dieline_status IN ('pending', 'failed')
           OR mockup_status IN ('pending', 'failed')
        ORDER BY model_id
    """).fetchall()
    items = []
    for r in rows:
        items.append({
            "model_id": r[0], "name": r[1], "name_en": r[2],
            "slug": r[3], "detail_url": r[4], "category": r[5],
            "dieline_image_url": r[6], "dieline_image_local": r[7] or "",
            "mockup_image_url": r[8], "mockup_image_local": r[9] or "",
            "dieline_status": r[10], "mockup_status": r[11],
            "tags": r[12] or "[]",
        })
    return items


def update_download_status(conn: sqlite3.Connection, item: dict):
    """更新单条记录的下载状态和本地路径"""
    conn.execute("""
        UPDATE pacdora_items SET
            dieline_image_local=?, dieline_status=?,
            mockup_image_local=?, mockup_status=?
        WHERE model_id=?
    """, (
        item.get("dieline_image_local", ""), item.get("dieline_status", "pending"),
        item.get("mockup_image_local", ""), item.get("mockup_status", "pending"),
        item["model_id"],
    ))
    conn.commit()


# ═══════════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════════

def print_download_stats(conn: sqlite3.Connection):
    """打印当前下载状态统计"""
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN dieline_status='downloaded' THEN 1 ELSE 0 END),
            SUM(CASE WHEN dieline_status='pending' THEN 1 ELSE 0 END),
            SUM(CASE WHEN dieline_status='failed' THEN 1 ELSE 0 END),
            SUM(CASE WHEN mockup_status='downloaded' THEN 1 ELSE 0 END),
            SUM(CASE WHEN mockup_status='pending' THEN 1 ELSE 0 END),
            SUM(CASE WHEN mockup_status='failed' THEN 1 ELSE 0 END)
        FROM pacdora_items
    """).fetchone()
    print(f"  数据库总计: {stats[0] or 0} 条")
    print(f"  图纸:   ✓已下载={stats[1] or 0}  ⏳待处理={stats[2] or 0}  ✗失败={stats[3] or 0}")
    print(f"  效果图: ✓已下载={stats[4] or 0}  ⏳待处理={stats[5] or 0}  ✗失败={stats[6] or 0}")
    return stats


def download_pending(conn: sqlite3.Connection, img_dir: str):
    """只下载未完成的图片 (pending + failed), 逐条更新状态"""
    pending = get_pending_items(conn)
    total = len(pending)
    if total == 0:
        print("  ✅ 所有图片均已下载, 无待处理项")
        return 0, 0

    print(f"  待处理: {total} 条 (pending + failed)")
    print(f"  图片目录: {img_dir}")
    print(f"  Ctrl+C 可随时中断, 进度已实时保存, 下次继续\n")

    os.makedirs(img_dir, exist_ok=True)
    dl_ok = 0
    dl_fail = 0
    batch_size = 10

    try:
        for batch_start in range(0, total, batch_size):
            batch = pending[batch_start:batch_start + batch_size]

            # 只下载状态为 pending/failed 的图片类型
            for item in batch:
                need_dieline = item["dieline_status"] in ("pending", "failed")
                need_mockup = item["mockup_status"] in ("pending", "failed")
                mid = item["model_id"]

                dieline_dir = os.path.join(img_dir, "dielines")
                mockup_dir = os.path.join(img_dir, "mockups")
                os.makedirs(dieline_dir, exist_ok=True)
                os.makedirs(mockup_dir, exist_ok=True)

                if need_dieline:
                    dl_path = os.path.join(dieline_dir, f"dieline-{mid}.png")
                    if download_image(item["dieline_image_url"], dl_path):
                        item["dieline_image_local"] = dl_path
                        item["dieline_status"] = "downloaded"
                        dl_ok += 1
                    else:
                        item["dieline_status"] = "failed"
                        dl_fail += 1

                if need_mockup:
                    mk_path = os.path.join(mockup_dir, f"mockup-{mid}.jpg")
                    if download_image(item["mockup_image_url"], mk_path):
                        item["mockup_image_local"] = mk_path
                        item["mockup_status"] = "downloaded"
                        dl_ok += 1
                    else:
                        item["mockup_status"] = "failed"
                        dl_fail += 1

                # 逐条实时更新数据库
                update_download_status(conn, item)

            done = min(batch_start + batch_size, total)
            pct = done * 100 // total
            print(f"  [{done}/{total}] {pct}%  ✓{dl_ok} ✗{dl_fail}")

            # 人类节奏: 每批间随机休息
            if done < total:
                time.sleep(random.uniform(1, 3))

    except KeyboardInterrupt:
        print(f"\n  ⚠ 用户中断, 进度已保存. 下次运行自动从未完成处继续.")

    return dl_ok, dl_fail


def main(db_path: str = DEFAULT_DB_PATH, resume_only: bool = False):
    print(f"\n{'='*60}")
    print(f"  Pacdora 刀版图库爬虫 v3.1 (断点续传)")
    print(f"  数据库: {db_path}")
    print(f"  图片目录: {IMG_DIR}")
    if resume_only:
        print(f"  模式: --resume (仅下载未完成图片, 不调用API)")
    print(f"{'='*60}\n")

    t0 = time.time()
    conn = init_db(db_path)

    # 检查数据库中是否有未完成的下载
    pending_count = conn.execute("""
        SELECT COUNT(*) FROM pacdora_items
        WHERE dieline_status IN ('pending','failed')
           OR mockup_status IN ('pending','failed')
    """).fetchone()[0]
    total_in_db = conn.execute("SELECT COUNT(*) FROM pacdora_items").fetchone()[0]

    # ── 决策: 是否需要调用 API ──
    if resume_only:
        # --resume 模式: 跳过 API, 直接下载未完成的
        if pending_count == 0:
            print("  ✅ 数据库中所有图片均已下载完成!")
            print_download_stats(conn)
            conn.close()
            return
        print(f"  数据库已有 {total_in_db} 条, 其中 {pending_count} 条图片未完成")
        print(f"\nStep 1: 跳过API调用, 直接处理未完成图片...")
    else:
        # 正常模式: 先看有没有未完成的
        if pending_count > 0 and total_in_db > 0:
            print(f"  ⚡ 发现 {pending_count} 条未完成下载 (数据库已有 {total_in_db} 条)")
            print(f"  优先处理未完成图片, 完成后再获取新数据\n")
            print(f"Step 1: 下载未完成图片...")
            dl_ok, dl_fail = download_pending(conn, IMG_DIR)
            print(f"  → 未完成处理: ✓{dl_ok} ✗{dl_fail}")

            # 重新检查是否还有未完成的
            remaining = conn.execute("""
                SELECT COUNT(*) FROM pacdora_items
                WHERE dieline_status IN ('pending','failed')
                   OR mockup_status IN ('pending','failed')
            """).fetchone()[0]
            if remaining > 0:
                print(f"  ⚠ 仍有 {remaining} 条未完成, 可能是网络问题, 稍后重试")
            print()

        # ── Step 2: 调用 API 获取全部数据 ──
        print("Step 2: 调用 API 获取所有刀版数据...")
        resp = fetch_json(API_URL)
        if not resp:
            print("  ✗ API 调用失败")
            if total_in_db > 0:
                print("  → 使用已有数据库数据继续下载未完成图片")
            else:
                print("  → 数据库为空, 退出")
                conn.close()
                return
        else:
            # 提取列表 (尝试常见 key)
            items_raw = []
            if isinstance(resp, list):
                items_raw = resp
            elif isinstance(resp, dict):
                for key in ("data", "list", "records", "items", "result", "rows"):
                    candidate = resp.get(key)
                    if isinstance(candidate, list) and len(candidate) > 0:
                        items_raw = candidate
                        break
                    elif isinstance(candidate, dict):
                        for subkey in ("list", "records", "items"):
                            sub = candidate.get(subkey)
                            if isinstance(sub, list) and len(sub) > 0:
                                items_raw = sub
                                break
                        if items_raw:
                            break
                if not items_raw:
                    print(f"  ⚠ API 返回结构: {list(resp.keys()) if isinstance(resp, dict) else type(resp)}")
                    for k, v in (resp.items() if isinstance(resp, dict) else []):
                        if isinstance(v, (list, dict)):
                            print(f"    {k}: {type(v).__name__} len={len(v) if isinstance(v, list) else len(v.keys())}")
                        else:
                            print(f"    {k}: {repr(v)[:80]}")

            print(f"  → 获取 {len(items_raw)} 条原始数据")

            if items_raw:
                # ── Step 3: 解析并入库 ──
                print("\nStep 3: 解析数据并写入数据库...")
                items = []
                for raw in items_raw:
                    if isinstance(raw, dict):
                        items.append(parse_item(raw))
                print(f"  → 解析 {len(items)} 条有效条目")

                new_count = 0
                for item in items:
                    if upsert_item(conn, item):
                        new_count += 1
                conn.commit()
                print(f"  → 入库完成 (新增 {new_count}, 更新 {len(items) - new_count})")

    # ── Step 4: 下载未完成图片 ──
    pending_now = conn.execute("""
        SELECT COUNT(*) FROM pacdora_items
        WHERE dieline_status IN ('pending','failed')
           OR mockup_status IN ('pending','failed')
    """).fetchone()[0]

    if pending_now > 0:
        print(f"\nStep 4: 下载未完成图片 ({pending_now} 条)...")
        dl_ok, dl_fail = download_pending(conn, IMG_DIR)
    else:
        dl_ok, dl_fail = 0, 0
        print(f"\nStep 4: 所有图片均已下载完成, 无需处理")

    # ── 最终统计 ──
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  ✅ 完成 ({elapsed:.1f}s)")
    print_download_stats(conn)

    cats = conn.execute(
        "SELECT category, COUNT(*) as c FROM pacdora_items GROUP BY category ORDER BY c DESC LIMIT 20"
    ).fetchall()
    if cats:
        print(f"  分类分布:")
        for row in cats:
            print(f"    {row[0] or '(未分类)'}: {row[1]} 条")
    print(f"{'='*60}\n")

    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pacdora 刀版图库爬虫 v3.1 (断点续传)")
    parser.add_argument("db_path", nargs="?", default=DEFAULT_DB_PATH, help="数据库路径")
    parser.add_argument("--resume", action="store_true", help="仅下载未完成图片, 不调用API")
    args = parser.parse_args()
    main(args.db_path, resume_only=args.resume)
