#!/usr/bin/env python3
"""
browser-use 测试脚本 — 安全验证
用途：验证browser-use能否在本地Mac上运行
安全：只读操作，不修改任何外部资源
"""
import asyncio
import sys

async def test_browser_use():
    try:
        from browser_use import Agent, Browser
        print("✅ browser-use 导入成功")
        
        # 检查Playwright是否可用
        try:
            from playwright.async_api import async_playwright
            print("✅ Playwright 可用")
        except ImportError:
            print("❌ Playwright 未安装，运行: npx playwright install chromium")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_browser_use())
    sys.exit(0 if result else 1)
