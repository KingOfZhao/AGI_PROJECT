#!/usr/bin/env python3
"""调试Google搜索页面"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 试Bing
        print("=== Trying Bing ===")
        await page.goto("https://www.bing.com/search?q=San+Francisco+population+2024", timeout=20000)
        content = await page.content()
        # 提取文本
        text = await page.evaluate("() => document.body.innerText")
        print(text[:1000])
        
        # 截图
        await page.screenshot(path="bing_screenshot.png")
        print("\nScreenshot saved")
        
        await browser.close()

asyncio.run(main())
