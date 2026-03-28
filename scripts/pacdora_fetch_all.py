#!/usr/bin/env python3
"""
Pacdora API 分页抓取器

每次请求100条, 自动翻页直到获取全部数据(~5969条)
频率控制: 每页间隔3-6秒, 每10页长暂停15-30秒
数据保存为JSON文件, 然后自动调用 pacdora_import.py 入库

用法:
  python3 pacdora_fetch_all.py                    # 抓取全部 → 保存JSON → 入库
  python3 pacdora_fetch_all.py --fetch-only        # 只抓取, 不入库
  python3 pacdora_fetch_all.py --import-existing    # 跳过抓取, 直接导入已有JSON
"""

import os
import sys
import json
import time
import random
import urllib.request
import urllib.error
import ssl
from datetime import datetime

# ─── 配置 ─────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(
    PROJECT_ROOT, "项目清单", "刀模活字印刷3D项目", "推演数据"
)
OUTPUT_JSON = os.path.join(DATA_DIR, "pacdora_models_full.json")

API_BASE = "https://www.pacdora.cn/api/v2/models"
PAGE_SIZE = 100

# 频率控制
DELAY_MIN = 3.0          # 每页最小间隔 (秒)
DELAY_MAX = 6.0          # 每页最大间隔 (秒)
LONG_PAUSE_EVERY = 10    # 每N页长暂停
LONG_PAUSE_MIN = 15.0    # 长暂停最小 (秒)
LONG_PAUSE_MAX = 30.0    # 长暂停最大 (秒)

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def fetch_page(page: int, page_size: int = PAGE_SIZE) -> dict:
    """抓取一页数据"""
    url = f"{API_BASE}?pageSize={page_size}&current={page}&dielineNameKey=all"
    ua = random.choice(USER_AGENTS)
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Referer": "https://www.pacdora.cn/dielines",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.pacdora.cn",
    })

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
                raw = resp.read()
                data = json.loads(raw.decode("utf-8"))
                return data
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 10 + random.uniform(5, 15)
                print(f"    ✗ 第{page}页 尝试{attempt+1} 失败: {e}")
                print(f"      等待 {wait:.0f}s 后重试...")
                time.sleep(wait)
            else:
                print(f"    ✗ 第{page}页 {max_retries}次全部失败: {e}")
                return None


def human_delay(page_count: int):
    """模拟人类浏览频率"""
    if page_count > 0 and page_count % LONG_PAUSE_EVERY == 0:
        pause = random.uniform(LONG_PAUSE_MIN, LONG_PAUSE_MAX)
        print(f"  ☕ 已抓{page_count}页, 长暂停 {pause:.1f}s...")
        time.sleep(pause)
    else:
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        time.sleep(delay)


def fetch_all() -> list:
    """分页抓取全部数据"""
    print(f"\n{'='*60}")
    print(f"  Pacdora API 分页抓取")
    print(f"  每页: {PAGE_SIZE} 条")
    print(f"  频率: 每页 {DELAY_MIN}-{DELAY_MAX}s, 每{LONG_PAUSE_EVERY}页暂停 {LONG_PAUSE_MIN}-{LONG_PAUSE_MAX}s")
    print(f"  Ctrl+C 可中断 (已抓数据会保存)")
    print(f"{'='*60}\n")

    all_items = []
    page = 1
    total_expected = None
    t0 = time.time()
    pages_fetched = 0

    # 检查是否有之前的中间结果
    partial_json = OUTPUT_JSON + ".partial"
    if os.path.exists(partial_json):
        with open(partial_json, "r", encoding="utf-8") as f:
            saved = json.load(f)
        all_items = saved.get("items", [])
        page = saved.get("next_page", 1)
        total_expected = saved.get("total", None)
        print(f"  📂 恢复上次进度: 已有{len(all_items)}条, 从第{page}页继续")

    try:
        while True:
            human_delay(pages_fetched)

            result = fetch_page(page)
            if result is None:
                print(f"  ⚠ 第{page}页抓取失败, 保存当前进度...")
                break

            if result.get("code") != 200:
                print(f"  ⚠ API 返回 code={result.get('code')}, msg={result.get('msg', '?')}")
                break

            if total_expected is None:
                total_expected = result.get("total", 0)
                total_pages = (total_expected + PAGE_SIZE - 1) // PAGE_SIZE
                print(f"  API total={total_expected}, 预计 {total_pages} 页\n")

            page_data = result.get("data", [])
            if not page_data:
                print(f"  第{page}页返回空数据, 抓取结束")
                break

            all_items.extend(page_data)
            pages_fetched += 1

            elapsed = time.time() - t0
            speed = pages_fetched / (elapsed / 60) if elapsed > 0 else 0
            remaining = total_expected - len(all_items) if total_expected else 0
            eta = remaining / (PAGE_SIZE * speed / 60) if speed > 0 else 0

            print(f"  页 {page:3d} | +{len(page_data):3d} 条 | "
                  f"累计 {len(all_items):5d}/{total_expected or '?'} | "
                  f"{speed:.1f}页/min | ETA≈{eta:.0f}s")

            # 检查是否完成
            if len(page_data) < PAGE_SIZE:
                print(f"\n  最后一页只有 {len(page_data)} 条, 抓取完成!")
                break
            if total_expected and len(all_items) >= total_expected:
                print(f"\n  已达到 total={total_expected}, 抓取完成!")
                break

            page += 1

            # 每5页保存中间结果 (防断点)
            if pages_fetched % 5 == 0:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(partial_json, "w", encoding="utf-8") as f:
                    json.dump({"items": all_items, "next_page": page + 1,
                               "total": total_expected}, f, ensure_ascii=False)

    except KeyboardInterrupt:
        print(f"\n\n  ⚠ 用户中断! 已抓 {len(all_items)} 条")

    # 保存中间进度
    if len(all_items) < (total_expected or float('inf')):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(partial_json, "w", encoding="utf-8") as f:
            json.dump({"items": all_items, "next_page": page + 1,
                       "total": total_expected}, f, ensure_ascii=False)
        print(f"  中间进度已保存: {partial_json}")
        print(f"  下次运行自动从第{page+1}页继续")

    return all_items


def save_full_json(items: list):
    """保存完整JSON"""
    os.makedirs(DATA_DIR, exist_ok=True)
    output = {
        "code": 200,
        "total": len(items),
        "data": items,
        "fetched_at": datetime.now().isoformat(),
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=None)

    size_mb = os.path.getsize(OUTPUT_JSON) / 1024 / 1024
    print(f"\n  ✅ 保存完整JSON: {OUTPUT_JSON}")
    print(f"     {len(items)} 条, {size_mb:.1f} MB")

    # 删除中间文件
    partial = OUTPUT_JSON + ".partial"
    if os.path.exists(partial):
        os.remove(partial)
        print(f"     已清理中间文件")


def run_import():
    """调用 pacdora_import.py 导入数据库"""
    import_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pacdora_import.py")
    if not os.path.exists(import_script):
        print(f"  ✗ 找不到导入脚本: {import_script}")
        return

    print(f"\n{'='*60}")
    print(f"  开始导入数据库...")
    print(f"{'='*60}")

    # 直接导入模块调用
    sys.path.insert(0, os.path.dirname(import_script))
    import pacdora_import as pi
    sys.argv = ["pacdora_import.py", "import", OUTPUT_JSON]
    pi.cmd_import(OUTPUT_JSON)


def main():
    fetch_only = "--fetch-only" in sys.argv
    import_existing = "--import-existing" in sys.argv

    if import_existing:
        if not os.path.exists(OUTPUT_JSON):
            print(f"✗ JSON文件不存在: {OUTPUT_JSON}")
            sys.exit(1)
        run_import()
        return

    # 抓取
    items = fetch_all()

    if not items:
        print("✗ 没有抓到数据")
        sys.exit(1)

    # 保存
    save_full_json(items)

    # 导入
    if not fetch_only:
        run_import()
    else:
        print(f"\n  下一步: python3 pacdora_import.py import {OUTPUT_JSON}")

    elapsed_info = f"共 {len(items)} 条"
    print(f"\n{'='*60}")
    print(f"  🎉 完成! {elapsed_info}")
    print(f"  JSON: {OUTPUT_JSON}")
    if not fetch_only:
        print(f"  下一步: python3 pacdora_import.py download --limit 50")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
