#!/usr/bin/env python3
"""微信读书阅读助手"""
from playwright.sync_api import sync_playwright
import os, sys, time, random

USER_DATA = os.path.expanduser("~/.openclaw/weread-profile")
BASE = "https://weread.qq.com"

def run(cmd):
    if cmd == "open":
        open_weread()
    elif cmd == "read":
        url = sys.argv[2] if len(sys.argv) > 2 else None
        read_book(url)
    elif cmd == "status":
        check_login()
    elif cmd == "scroll":
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 600
        scroll_read(duration)

def open_weread():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA, headless=False, viewport={"width": 1280, "height": 800})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BASE)
        print("已打开微信读书，请扫码登录", flush=True)
        print("按 Ctrl+C 关闭浏览器", flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            ctx.close()

def check_login():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA, headless=True, viewport={"width": 1280, "height": 800})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BASE, wait_until="networkidle", timeout=15000)
        title = page.title()
        url = page.url
        print(f"Title: {title}")
        print(f"URL: {url}")
        if "weread.qq.com" in url and "login" not in url.lower():
            print("✅ 已登录")
        else:
            print("❌ 未登录，请先运行: python3 weread.py open")
        ctx.close()

def scroll_read(duration=600):
    """模拟阅读滚动"""
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            USER_DATA, headless=False, viewport={"width": 1280, "height": 800})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        
        if len(sys.argv) > 2 and sys.argv[2].startswith("http"):
            page.goto(sys.argv[2])
        else:
            page.goto(BASE + "/web/shelf")
        
        print(f"开始模拟阅读，持续 {duration} 秒", flush=True)
        
        start = time.time()
        while time.time() - start < duration:
            # 模拟人类阅读行为
            scroll_amount = random.randint(200, 500)
            page.mouse.wheel(0, scroll_amount)
            
            # 随机暂停（模拟阅读速度）
            pause = random.uniform(3, 12)
            time.sleep(pause)
            
            elapsed = int(time.time() - start)
            remaining = duration - elapsed
            if elapsed % 60 == 0:
                print(f"  已读 {elapsed//60} 分钟，剩余 {remaining//60} 分钟", flush=True)
        
        print(f"✅ 阅读完成，共 {duration//60} 分钟", flush=True)
        ctx.close()

def read_book(url=None):
    if url:
        scroll_read(1800)
    else:
        print("用法: python3 weread.py read <book_url>")

if __name__ == "__main__":
    run(sys.argv[1]) if len(sys.argv) > 1 else open_weread()
