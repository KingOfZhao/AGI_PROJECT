#!/usr/bin/env python3
"""并发读取bqgl.cc小说 + 基础科学PDF"""
from playwright.sync_api import sync_playwright
import time, re, os, json
from concurrent.futures import ThreadPoolExecutor, as_completed

LIBRARY = os.path.expanduser("~/Desktop/AGI_PROJECT/knowledge/books")
NOVELS = os.path.join(LIBRARY, "novels")
SCIENCE = os.path.join(LIBRARY, "science")
os.makedirs(NOVELS, exist_ok=True)
os.makedirs(SCIENCE, exist_ok=True)

BASE = "https://m.bqgl.cc"

def get_real_base(page, look_path):
    """点击开始阅读，获取重定向后的真实域名和book_id"""
    page.goto(BASE + look_path, timeout=15000)
    time.sleep(2)
    page.click("a[href*='1.html']")
    time.sleep(5)
    real_url = page.url
    base_match = re.match(r'(https?://[^/]+)', real_url)
    base = base_match.group(1) if base_match else ""
    try:
        book_id = real_url.split("/book/")[1].split("/")[0]
    except:
        book_id = ""
    return base, book_id

def read_one_book(page, look_path, name, max_ch=200):
    """读一本书，返回字数和章节数"""
    try:
        base, book_id = get_real_base(page, look_path)
        if not base or not book_id:
            return name, 0, 0, "无法获取book_id"
        
        all_text = []
        ch = 1
        while ch <= max_ch:
            url = f"{base}/book/{book_id}/{ch}.html"
            try:
                page.goto(url, timeout=12000)
                time.sleep(1.2)
                content = page.query_selector("#chaptercontent")
                if not content:
                    break
                text = content.text_content().strip()
                if len(text) < 30:
                    break
                all_text.append(text)
                ch += 1
            except:
                break
        
        if not all_text:
            return name, 0, 0, "无内容"
        
        full = "\n".join(all_text)
        path = os.path.join(NOVELS, f"{name}.txt")
        with open(path, 'w') as f:
            f.write(full)
        return name, len(full), len(all_text), "ok"
    except Exception as e:
        return name, 0, 0, str(e)[:80]

def find_and_read(page, search_term, max_ch=200):
    """搜索并阅读一本书"""
    page.goto(f"{BASE}/s?q={search_term}", timeout=15000)
    time.sleep(2)
    
    links = page.query_selector_all("a")
    for a in links:
        href = a.get_attribute("href") or ""
        text = a.text_content().strip()
        if "/look/" in href and 2 < len(text) < 40:
            return read_one_book(page, href, search_term, max_ch)
    
    return search_term, 0, 0, "搜索无结果"

def main():
    # 要读的书单
    book_list = [
        # 小说
        "/look/9882/",   # 盗墓笔记
        "/look/9041/",   # 大奉打更人 (已读,跳过)
        "/look/9672/",   # 鬼吹灯
        "/look/9998/",   # 大道朝天
        "/look/58793/",  # 道诡异仙
        "/look/99990/",  # 光阴之外
        "/look/6828/",   # 深空彼岸
        "/look/7652/",   # 鹰视狼顾
        "/look/9100/",   # 迷踪谍影
        "/look/26303/",  # 大唐第一世家
    ]
    
    print(f"开始并发读取 {len(book_list)} 本书...")
    
    # 用多个浏览器并发（3个并行）
    results = []
    
    def read_book_task(look_path):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 获取书名
            page.goto(BASE + look_path, timeout=15000)
            time.sleep(2)
            links = page.query_selector_all("a")
            name = look_path.strip("/").replace("/","_")
            for a in links:
                text = a.text_content().strip()
                if len(text) > 2 and len(text) < 30 and text == text:
                    name = text
                    break
            
            result = read_one_book(page, look_path, name, 300)
            browser.close()
            return result
    
    # 3并发
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(read_book_task, bp): bp for bp in book_list}
        for future in as_completed(futures):
            name, chars, chapters, status = future.result()
            print(f"{'✅' if status=='ok' else '❌'} {name}: {chars}字 {chapters}章 ({status})")
            results.append((name, chars, chapters, status))
    
    # 汇总
    total_chars = sum(r[1] for r in results)
    total_books = sum(1 for r in results if r[3] == "ok")
    print(f"\n完成: {total_books}/{len(book_list)} 本, 共 {total_chars} 字")

if __name__ == "__main__":
    main()
