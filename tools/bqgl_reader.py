#!/usr/bin/env python3
"""从bqgl.cc批量阅读小说，提取正文"""
from playwright.sync_api import sync_playwright
import os, sys, time, re

LIBRARY = os.path.expanduser("~/Desktop/AGI_PROJECT/knowledge/books")
BASE = "https://m.bqgl.cc"

def read_chapter(page, url):
    """读取一章正文"""
    page.goto(url, timeout=15000)
    time.sleep(1.5)
    
    el = page.query_selector("#chaptercontent")
    if not el:
        return ""
    
    text = el.text_content().strip()
    # 清理
    text = re.sub(r'\s+', '', text)  # 去空白
    # 去掉常见广告词
    text = re.sub(r'(百度搜索|笔趣阁|手机版|最新章节|天才一秒记住|请记住本书首发域名|最快的小说更新|小说网).*?(?=。|$)', '', text)
    return text

def get_chapters(page, book_url):
    """获取章节列表"""
    list_url = BASE + book_url.rstrip("/") + "/list.html"
    page.goto(list_url, timeout=15000)
    time.sleep(2)
    
    links = page.query_selector_all("a")
    chapters = []
    for a in links:
        href = a.get_attribute("href") or ""
        text = a.text_content().strip()
        if re.search(r'/\d+\.html$', href) and text and 2 < len(text) < 60:
            full_url = href if href.startswith("http") else BASE + href
            chapters.append((text, full_url))
    
    # 去重
    seen = set()
    clean = []
    for t, h in chapters:
        if h not in seen:
            seen.add(h)
            clean.append((t, h))
    return clean

def read_book(look_path, max_chapters=50):
    """读一本书"""
    os.makedirs(LIBRARY, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Get book name from main page
        page.goto(BASE + look_path, timeout=15000)
        time.sleep(2)
        title = page.title() or "unknown"
        name_match = re.search(r'_(.+?)_', title)
        book_name = name_match.group(1) if name_match else title.replace("笔趣阁","").strip()
        
        # Get chapter list
        chapters = get_chapters(page, look_path)
        total = min(len(chapters), max_chapters)
        print(f"《{book_name}》共 {len(chapters)} 章，读取前 {total} 章")
        
        # Read chapters
        all_text = []
        for i, (ch_title, ch_url) in enumerate(chapters[:total]):
            content = read_chapter(page, ch_url)
            if content and len(content) > 50:
                all_text.append(f"\n【{ch_title}】\n{content}")
            if (i+1) % 10 == 0:
                print(f"  {i+1}/{total}", flush=True)
        
        browser.close()
    
    full = "\n".join(all_text)
    path = os.path.join(LIBRARY, f"{book_name}.txt")
    with open(path, 'w') as f:
        f.write(full)
    
    print(f"✅ 《{book_name}》{len(full)} 字 → {path}")
    return path, len(full)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        read_book(sys.argv[1], int(sys.argv[2]))
    else:
        print("用法: python3 bqgl_reader.py /look/xxx [章节数]")
