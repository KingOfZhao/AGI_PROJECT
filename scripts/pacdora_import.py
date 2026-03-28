#!/usr/bin/env python3
"""
Pacdora 刀版数据导入 + 图片下载器 v2

用法:
  python3 pacdora_import.py import  /path/to/models.json   # 导入JSON到数据库(不下载图片)
  python3 pacdora_import.py download                        # 下载待处理图片(频率受控)
  python3 pacdora_import.py download --limit 100            # 只下载100条
  python3 pacdora_import.py stats                           # 查看统计

数据库表 pacdora_items 严格对应 API JSON 中每个 item 的所有字段,
额外增加 knife_local/image_local(本地路径) 和 knife_status/image_status(处理状态)。
"""

import os
import sys
import json
import time
import random
import sqlite3
import urllib.request
import urllib.error
import ssl
from datetime import datetime

# ─── 路径 ─────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(
    PROJECT_ROOT, "项目清单", "刀模活字印刷3D项目", "推演数据", "dieline_library.db"
)
IMG_BASE = os.path.join(
    PROJECT_ROOT, "项目清单", "刀模活字印刷3D项目", "推演数据", "pacdora_images"
)
DIELINE_DIR = os.path.join(IMG_BASE, "dielines")
MOCKUP_DIR = os.path.join(IMG_BASE, "mockups")

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# 下载频率控制 (模拟人类浏览行为)
DELAY_MIN = 2.0          # 每张图最小间隔 (秒)
DELAY_MAX = 5.0          # 每张图最大间隔 (秒)
LONG_PAUSE_EVERY = 30    # 每 N 张图做一次长暂停
LONG_PAUSE_MIN = 10.0    # 长暂停最小 (秒)
LONG_PAUSE_MAX = 25.0    # 长暂停最大 (秒)


# ═══════════════════════════════════════════════════════════════════
#  数据库 — 完整保留 JSON item 所有字段
# ═══════════════════════════════════════════════════════════════════

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pacdora_items (
    -- 主键
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,

    -- === API 原始字段 (全部保留) ===
    api_id              INTEGER,        -- item.id
    num                 INTEGER UNIQUE, -- 盒型编号 (唯一标识)
    name                TEXT,           -- 中文名
    showName            TEXT,           -- 显示名
    mockupName          TEXT,           -- 效果图名
    nameKey             TEXT,           -- URL slug (刀版)
    mockupNameKey       TEXT,           -- URL slug (效果图)

    -- 分类
    class1              TEXT,
    class2              TEXT,
    class3              TEXT,
    class2Bymodel       TEXT,           -- 所属分类名
    anchorName          TEXT,
    class2Namekey       TEXT,
    class2DielineNamekey TEXT,
    class2MockupNamekey TEXT,
    cate_id             INTEGER,
    def_science_id      INTEGER,

    -- 尺寸
    length              REAL,
    width               REAL,
    height              REAL,

    -- 排序/权重
    sort                INTEGER,
    is_enterprise       INTEGER,
    use_count           INTEGER,

    -- 图片原始URL
    knife               TEXT,           -- 刀版图纸 URL
    image               TEXT,           -- 效果图 URL

    -- 关键词
    keywords            TEXT,
    modelKeywords       TEXT,
    usageKeywords       TEXT,
    styleKeywords       TEXT,
    productKeywords     TEXT,

    -- 标签 (JSON数组)
    tags                TEXT,

    -- SEO/描述
    blankTitle          TEXT,
    blankAlt            TEXT,
    dielinesTitle       TEXT,
    dielinesAlt         TEXT,
    svgTitle            TEXT,
    svgAlt              TEXT,
    description         TEXT,

    -- 关联数据 (JSON)
    cate_info           TEXT,           -- JSON object
    modeSetting         TEXT,           -- JSON array (材质渲染选项)

    -- 其他
    liked               TEXT,
    demoProjectDataUrl  TEXT,
    create_time         TEXT,           -- API 原始时间戳
    update_time         TEXT,           -- API 原始时间戳

    -- === 本地扩展字段 ===
    knife_local         TEXT DEFAULT '',    -- 图纸本地路径
    image_local         TEXT DEFAULT '',    -- 效果图本地路径
    knife_status        TEXT DEFAULT 'pending',  -- pending / downloaded / failed / skipped
    image_status        TEXT DEFAULT 'pending',  -- pending / downloaded / failed / skipped
    imported_at         TEXT DEFAULT (datetime('now'))
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_pi_num ON pacdora_items(num);
CREATE INDEX IF NOT EXISTS idx_pi_name ON pacdora_items(name);
CREATE INDEX IF NOT EXISTS idx_pi_class2 ON pacdora_items(class2Bymodel);
CREATE INDEX IF NOT EXISTS idx_pi_knife_status ON pacdora_items(knife_status);
CREATE INDEX IF NOT EXISTS idx_pi_image_status ON pacdora_items(image_status);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 检测旧表 schema 是否兼容, 不兼容则迁移
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pacdora_items'")
    if cur.fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(pacdora_items)").fetchall()}
        if "knife_status" not in cols:
            # 旧表 schema 不兼容, 重命名旧表
            print("  ⚠ 检测到旧版 pacdora_items 表, 迁移为 pacdora_items_v1_backup...")
            conn.execute("DROP TABLE IF EXISTS pacdora_items_v1_backup")
            conn.execute("ALTER TABLE pacdora_items RENAME TO pacdora_items_v1_backup")
            conn.commit()

    conn.executescript(CREATE_TABLE_SQL)
    conn.executescript(CREATE_INDEX_SQL)
    conn.commit()
    return conn


def upsert_item(conn: sqlite3.Connection, item: dict) -> bool:
    """插入或更新, 按 num 去重。返回 True=新增, False=更新"""
    num = item["num"]
    exists = conn.execute("SELECT rowid FROM pacdora_items WHERE num=?", (num,)).fetchone()

    # JSON 数组/对象字段序列化
    tags_json = json.dumps(item.get("tags") or [], ensure_ascii=False)
    cate_info_json = json.dumps(item.get("cate_info") or {}, ensure_ascii=False)
    mode_setting_json = json.dumps(item.get("modeSetting") or [], ensure_ascii=False)

    vals = (
        item.get("id", 0),
        num,
        item.get("name", ""),
        item.get("showName", ""),
        item.get("mockupName", ""),
        item.get("nameKey", ""),
        item.get("mockupNameKey", ""),
        item.get("class1", ""),
        item.get("class2", ""),
        item.get("class3", ""),
        item.get("class2Bymodel", ""),
        item.get("anchorName", ""),
        item.get("class2Namekey", ""),
        item.get("class2DielineNamekey", ""),
        item.get("class2MockupNamekey", ""),
        item.get("cate_id", 0),
        item.get("def_science_id", 0),
        item.get("length", 0) or 0,
        item.get("width", 0) or 0,
        item.get("height", 0) or 0,
        item.get("sort", 0),
        item.get("is_enterprise", 0),
        item.get("use_count", 0),
        item.get("knife", ""),
        item.get("image", ""),
        item.get("keywords", ""),
        item.get("modelKeywords", ""),
        item.get("usageKeywords", ""),
        item.get("styleKeywords", ""),
        item.get("productKeywords", ""),
        tags_json,
        item.get("blankTitle", ""),
        item.get("blankAlt", ""),
        item.get("dielinesTitle", ""),
        item.get("dielinesAlt", ""),
        item.get("svgTitle", ""),
        item.get("svgAlt", ""),
        item.get("description", ""),
        cate_info_json,
        mode_setting_json,
        json.dumps(item.get("liked"), ensure_ascii=False),
        item.get("demoProjectDataUrl") or "",
        str(item.get("create_time", "")),
        str(item.get("update_time", "")),
    )

    if exists:
        conn.execute("""UPDATE pacdora_items SET
            api_id=?, num=?, name=?, showName=?, mockupName=?,
            nameKey=?, mockupNameKey=?,
            class1=?, class2=?, class3=?,
            class2Bymodel=?, anchorName=?, class2Namekey=?,
            class2DielineNamekey=?, class2MockupNamekey=?,
            cate_id=?, def_science_id=?,
            length=?, width=?, height=?,
            sort=?, is_enterprise=?, use_count=?,
            knife=?, image=?,
            keywords=?, modelKeywords=?, usageKeywords=?,
            styleKeywords=?, productKeywords=?,
            tags=?,
            blankTitle=?, blankAlt=?, dielinesTitle=?, dielinesAlt=?,
            svgTitle=?, svgAlt=?, description=?,
            cate_info=?, modeSetting=?,
            liked=?, demoProjectDataUrl=?,
            create_time=?, update_time=?
            WHERE num=?""", vals + (num,))
        return False
    else:
        conn.execute("""INSERT INTO pacdora_items (
            api_id, num, name, showName, mockupName,
            nameKey, mockupNameKey,
            class1, class2, class3,
            class2Bymodel, anchorName, class2Namekey,
            class2DielineNamekey, class2MockupNamekey,
            cate_id, def_science_id,
            length, width, height,
            sort, is_enterprise, use_count,
            knife, image,
            keywords, modelKeywords, usageKeywords,
            styleKeywords, productKeywords,
            tags,
            blankTitle, blankAlt, dielinesTitle, dielinesAlt,
            svgTitle, svgAlt, description,
            cate_info, modeSetting,
            liked, demoProjectDataUrl,
            create_time, update_time)
            VALUES (""" + ",".join(["?"] * len(vals)) + ")", vals)
        return True


# ═══════════════════════════════════════════════════════════════════
#  图片下载 (单线程 + 频率控制)
# ═══════════════════════════════════════════════════════════════════

def human_delay(count: int):
    """模拟人类浏览频率"""
    if count > 0 and count % LONG_PAUSE_EVERY == 0:
        pause = random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX)
        print(f"    ☕ 长暂停 {pause:.1f}s (已下载{count}张,休息一下)...")
        time.sleep(pause)
    else:
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def download_one(url: str, save_path: str) -> str:
    """
    下载单张图片。
    返回: 'downloaded' / 'skipped' / 'failed'
    """
    if not url or not url.startswith("http"):
        return "skipped"
    if os.path.exists(save_path) and os.path.getsize(save_path) > 500:
        return "downloaded"  # 已有
    try:
        ua = random.choice(USER_AGENTS)
        req = urllib.request.Request(url, headers={
            "User-Agent": ua,
            "Referer": "https://www.pacdora.cn/dielines",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
            data = resp.read()
            if len(data) < 200:
                return "failed"
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(data)
            return "downloaded"
    except Exception as e:
        print(f"    ✗ {url[:60]}... → {e}")
        return "failed"


def get_local_path(url: str, num: int, img_type: str) -> str:
    """根据URL和类型生成本地保存路径"""
    if img_type == "knife":
        ext = "png"
        if ".jpg" in url.lower() or ".jpeg" in url.lower():
            ext = "jpg"
        return os.path.join(DIELINE_DIR, f"dieline-{num}.{ext}")
    else:
        ext = "jpg"
        if ".png" in url.lower():
            ext = "png"
        return os.path.join(MOCKUP_DIR, f"mockup-{num}.{ext}")


# ═══════════════════════════════════════════════════════════════════
#  子命令: import
# ═══════════════════════════════════════════════════════════════════

def cmd_import(json_path: str):
    """导入JSON到数据库(不下载图片)"""
    if not os.path.exists(json_path):
        print(f"✗ 文件不存在: {json_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Pacdora 数据导入 (仅入库, 不下载图片)")
    print(f"  JSON: {json_path}")
    print(f"  数据库: {DB_PATH}")
    print(f"{'='*60}\n")

    t0 = time.time()

    # 读取
    print("Step 1: 读取 JSON...")
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        items = raw.get("data", [])
        total_api = raw.get("total", "?")
    elif isinstance(raw, list):
        items = raw
        total_api = len(raw)
    else:
        print("✗ JSON 格式无法识别"); sys.exit(1)

    print(f"  API total={total_api}, data数组={len(items)}")

    # 过滤有效条目
    valid = [it for it in items if isinstance(it, dict) and it.get("num")]
    print(f"  有效条目: {len(valid)}")

    # 入库
    print("\nStep 2: 写入数据库...")
    conn = init_db(DB_PATH)
    new_cnt = 0
    upd_cnt = 0
    for i, item in enumerate(valid):
        if upsert_item(conn, item):
            new_cnt += 1
        else:
            upd_cnt += 1
        if (i + 1) % 500 == 0:
            conn.commit()
            print(f"  [{i+1}/{len(valid)}] 新增={new_cnt} 更新={upd_cnt}")
    conn.commit()

    # 统计
    total_db = conn.execute("SELECT COUNT(*) FROM pacdora_items").fetchone()[0]
    cats = conn.execute(
        "SELECT class2Bymodel, COUNT(*) c FROM pacdora_items GROUP BY class2Bymodel ORDER BY c DESC"
    ).fetchall()
    pending_k = conn.execute("SELECT COUNT(*) FROM pacdora_items WHERE knife_status='pending'").fetchone()[0]
    pending_i = conn.execute("SELECT COUNT(*) FROM pacdora_items WHERE image_status='pending'").fetchone()[0]
    conn.close()

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"  ✅ 导入完成 ({elapsed:.1f}s)")
    print(f"  新增: {new_cnt}  更新: {upd_cnt}")
    print(f"  数据库总计: {total_db} 条")
    print(f"  图纸待下载: {pending_k}")
    print(f"  效果图待下载: {pending_i}")
    print(f"\n  分类 ({len(cats)} 个):")
    for row in cats:
        print(f"    {row[0] or '(空)'}: {row[1]}")
    print(f"\n  下一步: python3 pacdora_import.py download")
    print(f"{'='*60}\n")


# ═══════════════════════════════════════════════════════════════════
#  子命令: download (频率受控)
# ═══════════════════════════════════════════════════════════════════

def cmd_download(limit: int = 0):
    conn = init_db(DB_PATH)

    os.makedirs(DIELINE_DIR, exist_ok=True)
    os.makedirs(MOCKUP_DIR, exist_ok=True)

    def run_phase(status_value: str, dl_count: int, ok_count: int, fail_count: int, skip_count: int) -> tuple[int, int, int, int]:
        where_sql = "(knife_status=? OR image_status=?)"
        sql = f"""SELECT rowid, num, knife, image, knife_status, image_status
                 FROM pacdora_items
                 WHERE {where_sql}
                 ORDER BY use_count DESC"""
        params = (status_value, status_value)
        if limit > 0:
            sql += f" LIMIT {limit}"
        rows = conn.execute(sql, params).fetchall()
        total = len(rows)
        if total == 0:
            return dl_count, ok_count, fail_count, skip_count

        print(f"\n{'='*60}")
        print(f"  Pacdora 图片下载 (频率受控)")
        print(f"  阶段: {status_value}")
        print(f"  待处理: {total} 条")
        print(f"  频率: 每张 {DELAY_MIN}-{DELAY_MAX}s, 每{LONG_PAUSE_EVERY}张暂停 {LONG_PAUSE_MIN}-{LONG_PAUSE_MAX}s")
        print(f"  图纸目录: {DIELINE_DIR}")
        print(f"  效果图目录: {MOCKUP_DIR}")
        print(f"  Ctrl+C 可中断, 进度已保存, 下次继续")
        print(f"{'='*60}\n")

        t0 = time.time()
        try:
            for idx, row in enumerate(rows):
                rowid = row[0]
                num = row[1]
                knife_url = row[2]
                image_url = row[3]
                k_status = row[4]
                i_status = row[5]

                if k_status == status_value:
                    local_path = get_local_path(knife_url, num, "knife")
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 500:
                        status = "downloaded"
                    else:
                        human_delay(dl_count)
                        status = download_one(knife_url, local_path)
                        dl_count += 1

                    if status == "downloaded":
                        conn.execute("UPDATE pacdora_items SET knife_local=?, knife_status='downloaded' WHERE rowid=?",
                                     (local_path, rowid))
                        ok_count += 1
                    elif status == "skipped":
                        conn.execute("UPDATE pacdora_items SET knife_status='skipped' WHERE rowid=?", (rowid,))
                        skip_count += 1
                    else:
                        conn.execute("UPDATE pacdora_items SET knife_status='failed' WHERE rowid=?", (rowid,))
                        fail_count += 1

                if i_status == status_value:
                    local_path = get_local_path(image_url, num, "image")
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 500:
                        status = "downloaded"
                    else:
                        human_delay(dl_count)
                        status = download_one(image_url, local_path)
                        dl_count += 1

                    if status == "downloaded":
                        conn.execute("UPDATE pacdora_items SET image_local=?, image_status='downloaded' WHERE rowid=?",
                                     (local_path, rowid))
                        ok_count += 1
                    elif status == "skipped":
                        conn.execute("UPDATE pacdora_items SET image_status='skipped' WHERE rowid=?", (rowid,))
                        skip_count += 1
                    else:
                        conn.execute("UPDATE pacdora_items SET image_status='failed' WHERE rowid=?", (rowid,))
                        fail_count += 1

                conn.commit()

                done = idx + 1
                elapsed = time.time() - t0
                speed = dl_count / elapsed if elapsed > 0 else 0
                eta = (total - done) / speed / 60 if speed > 0 else 0
                print(f"  [{done}/{total}] num={num}  ✓{ok_count} ✗{fail_count} ⊘{skip_count}  "
                      f"速度={speed:.1f}张/min  ETA≈{eta:.0f}min")
        except KeyboardInterrupt:
            conn.commit()
            print(f"\n\n  ⚠ 用户中断, 进度已保存. 已处理 {idx+1}/{total}")
            print(f"  下次运行 'python3 pacdora_import.py download' 继续")
            raise

        return dl_count, ok_count, fail_count, skip_count

    dl_count = 0
    ok_count = 0
    fail_count = 0
    skip_count = 0

    try:
        dl_count, ok_count, fail_count, skip_count = run_phase("pending", dl_count, ok_count, fail_count, skip_count)
        if RETRY_FAILED_AFTER_PENDING:
            dl_count, ok_count, fail_count, skip_count = run_phase("failed", dl_count, ok_count, fail_count, skip_count)
    except KeyboardInterrupt:
        conn.close()
        return

    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN knife_status='downloaded' THEN 1 ELSE 0 END) as knife_ok,
            SUM(CASE WHEN knife_status='pending' THEN 1 ELSE 0 END) as knife_pending,
            SUM(CASE WHEN knife_status='failed' THEN 1 ELSE 0 END) as knife_fail,
            SUM(CASE WHEN image_status='downloaded' THEN 1 ELSE 0 END) as image_ok,
            SUM(CASE WHEN image_status='pending' THEN 1 ELSE 0 END) as image_pending,
            SUM(CASE WHEN image_status='failed' THEN 1 ELSE 0 END) as image_fail
        FROM pacdora_items
    """).fetchone()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  下载完成 (实际下载 {dl_count} 张)")
    print(f"  图纸: ✓{stats[1]} 待={stats[2]} ✗{stats[3]}")
    print(f"  效果图: ✓{stats[4]} 待={stats[5]} ✗{stats[6]}")
    print(f"{'='*60}\n")


# ═══════════════════════════════════════════════════════════════════
#  子命令: stats
# ═══════════════════════════════════════════════════════════════════

def cmd_stats():
    """查看数据库统计"""
    if not os.path.exists(DB_PATH):
        print(f"✗ 数据库不存在: {DB_PATH}")
        sys.exit(1)

    conn = init_db(DB_PATH)

    total = conn.execute("SELECT COUNT(*) FROM pacdora_items").fetchone()[0]
    if total == 0:
        print("数据库为空"); conn.close(); return

    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN knife_status='downloaded' THEN 1 ELSE 0 END),
            SUM(CASE WHEN knife_status='pending' THEN 1 ELSE 0 END),
            SUM(CASE WHEN knife_status='failed' THEN 1 ELSE 0 END),
            SUM(CASE WHEN knife_status='skipped' THEN 1 ELSE 0 END),
            SUM(CASE WHEN image_status='downloaded' THEN 1 ELSE 0 END),
            SUM(CASE WHEN image_status='pending' THEN 1 ELSE 0 END),
            SUM(CASE WHEN image_status='failed' THEN 1 ELSE 0 END),
            SUM(CASE WHEN image_status='skipped' THEN 1 ELSE 0 END)
        FROM pacdora_items
    """).fetchone()

    cats = conn.execute(
        "SELECT class2Bymodel, COUNT(*) c FROM pacdora_items GROUP BY class2Bymodel ORDER BY c DESC"
    ).fetchall()

    # 尺寸范围
    dims = conn.execute(
        "SELECT MIN(length), MAX(length), MIN(width), MAX(width), MIN(height), MAX(height) FROM pacdora_items"
    ).fetchone()

    conn.close()

    print(f"\n{'='*60}")
    print(f"  Pacdora 刀版数据库统计")
    print(f"  数据库: {DB_PATH}")
    print(f"{'='*60}")
    print(f"\n  总条目: {stats[0]}")
    print(f"\n  图纸 (knife):")
    print(f"    ✓ 已下载: {stats[1]}")
    print(f"    ⏳ 待处理: {stats[2]}")
    print(f"    ✗ 失败:   {stats[3]}")
    print(f"    ⊘ 跳过:   {stats[4]}")
    print(f"\n  效果图 (image):")
    print(f"    ✓ 已下载: {stats[5]}")
    print(f"    ⏳ 待处理: {stats[6]}")
    print(f"    ✗ 失败:   {stats[7]}")
    print(f"    ⊘ 跳过:   {stats[8]}")
    print(f"\n  尺寸范围:")
    print(f"    长: {dims[0]}-{dims[1]}mm")
    print(f"    宽: {dims[2]}-{dims[3]}mm")
    print(f"    高: {dims[4]}-{dims[5]}mm")
    print(f"\n  分类 ({len(cats)} 个):")
    for row in cats:
        print(f"    {row[0] or '(空)'}: {row[1]}")
    print(f"{'='*60}\n")


# ═══════════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 pacdora_import.py import  <json文件>  # 导入数据到库")
        print("  python3 pacdora_import.py download [--limit N] # 下载待处理图片")
        print("  python3 pacdora_import.py stats                # 查看统计")
        sys.exit(1)

    cmd = sys.argv[1]

    global RETRY_FAILED_AFTER_PENDING
    RETRY_FAILED_AFTER_PENDING = "--no-retry-failed" not in sys.argv

    if cmd == "import":
        if len(sys.argv) < 3:
            print("✗ 缺少 JSON 文件路径")
            sys.exit(1)
        cmd_import(sys.argv[2])

    elif cmd == "download":
        limit = 0
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])
        cmd_download(limit)

    elif cmd == "stats":
        cmd_stats()

    else:
        print(f"✗ 未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
