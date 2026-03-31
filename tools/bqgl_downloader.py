#!/usr/bin/env python3
"""bqgl.cc 全量下载器 v3
用Playwright一次性解析所有书的CDN域名，然后requests从CDN直接下载"""
from playwright.sync_api import sync_playwright
import requests, re, os, time, json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://m.bqgl.cc"
LIBRARY = os.path.expanduser("~/Desktop/AGI_PROJECT/knowledge/books/novels")
os.makedirs(LIBRARY, exist_ok=True)

BOOKS = {
    "/look/9041/": "大奉打更人",
    "/look/9882/": "盗墓笔记",
    "/look/9672/": "鬼吹灯",
    "/look/9998/": "大道朝天",
    "/look/58793/": "道诡异仙",
    "/look/99990/": "光阴之外",
    "/look/6828/": "深空彼岸",
    "/look/7652/": "鹰视狼顾",
    "/look/9100/": "迷踪谍影",
    "/look/26303/": "大唐第一世家",
    "/look/51248/": "道德经",
}

def resolve_all_books():
    """Playwright解析所有书的CDN域名和book_id"""
    print(f"🔍 解析 {len(BOOKS)} 本书的CDN地址...")
    resolved = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for look_path, name in BOOKS.items():
            try:
                page.goto(BASE + look_path, timeout=15000)
                time.sleep(1.5)
                page.click("a[href*='1.html']")
                time.sleep(4)
                
                url = page.url
                match = re.search(r'(https://[^/]+).*?/book/(\d+)/', url)
                if match:
                    resolved[look_path] = {
                        "name": name,
                        "cdn": match.group(1),
                        "book_id": match.group(2)
                    }
                    print(f"  ✅ {name}: {match.group(1)} → {match.group(2)}")
                else:
                    print(f"  ❌ {name}: 无法解析")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
        
        browser.close()
    
    # 保存映射
    with open(os.path.join(LIBRARY, "_book_map.json"), 'w') as f:
        json.dump(resolved, f, ensure_ascii=False, indent=2)
    
    return resolved

def get_chapter(cdn, book_id, ch):
    """requests读取单章"""
    url = f"{cdn}/book/{book_id}/{ch}.html"
    try:
        r = requests.get(url, timeout=12, headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"
        })
        r.raise_for_status()
        match = re.search(r'id="chaptercontent"[^>]*>(.*?)</div>', r.text, re.DOTALL)
        if match:
            text = match.group(1)
            text = re.sub(r'<br\s*/?>', '\n', text)
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'(请收藏|天才一秒记住|本书首发|最快更新|小说网|笔趣阁|最新章节|bqg\d|25bqg)[^\n]{0,60}', '', text)
            text = re.sub(r'https?://[^\s<>"\']+', '', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()
    except:
        pass
    return ""

def download_one_book(info):
    """下载单本书"""
    name = info["name"]
    cdn = info["cdn"]
    book_id = info["book_id"]
    
    out_path = os.path.join(LIBRARY, f"{name}.txt")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 5000:
        return name, os.path.getsize(out_path), True
    
    # 二分探测总章数
    lo, hi = 1, 5000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        t = get_chapter(cdn, book_id, mid)
        if t and len(t) > 20:
            lo = mid
        else:
            hi = mid - 1
    total = lo
    
    if total < 5:
        return name, 0, False
    
    chapters = []
    for ch in range(1, total + 1):
        t = get_chapter(cdn, book_id, ch)
        if t and len(t) > 20:
            chapters.append(t)
        else:
            break
        if ch % 100 == 0:
            print(f"    {ch}/{total}", flush=True)
        time.sleep(0.08)
    
    full = "\n\n".join(chapters)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(full)
    
    return name, len(full), False

def main():
    # Step 1: 解析
    resolved = resolve_all_books()
    
    if not resolved:
        print("❌ 无书可下载")
        return
    
    # Step 2: 并发下载（requests不需要Playwright，可以多线程）
    print(f"\n📥 开始下载 {len(resolved)} 本书...")
    
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(download_one_book, info): path for path, info in resolved.items()}
        for future in as_completed(futures):
            name, size, cached = future.result()
            tag = "⏭" if cached else "✅" if size > 0 else "❌"
            print(f"  {tag} {name}: {size:,} 字")
            results.append((name, size))
    
    total = sum(s for _, s in results)
    print(f"\n{'='*50}")
    print(f"总计: {total:,} 字 ({sum(1 for _,s in results if s > 0)}/{len(resolved)} 本)")

if __name__ == "__main__":
    main()
