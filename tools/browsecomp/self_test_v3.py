#!/usr/bin/env python3
"""
BrowseComp自测v3 - 直接用Playwright搜索Google
"""
import asyncio
import json
import sys

async def google_search(query):
    """用Playwright搜索Google并返回结果"""
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(f"https://www.google.com/search?q={query}", timeout=15000)
            await page.wait_for_selector("div#search", timeout=10000)
            
            # 提取搜索结果
            results = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('div.g');
                    const data = [];
                    for (const item of items) {
                        const titleEl = item.querySelector('h3');
                        const snippetEl = item.querySelector('[data-sncf], .VwiC3b');
                        if (titleEl) {
                            data.push({
                                title: titleEl.textContent,
                                snippet: snippetEl ? snippetEl.textContent : ''
                            });
                        }
                    }
                    return data.slice(0, 3);
                }
            """)
            return results
        except Exception as e:
            return [{"title": "error", "snippet": str(e)}]
        finally:
            await browser.close()

async def main():
    queries = [
        {"id": 1, "query": "San Francisco population 2024 census"},
        {"id": 2, "query": "Ashish Vaswani undergraduate university education"},
        {"id": 3, "query": "2020 Tokyo Olympics most gold medals country"},
        {"id": 4, "query": "Rabindranath Tagore composed national anthem which countries"},
        {"id": 5, "query": "most abundant element Earth crust discoverer atomic number"},
        {"id": 6, "query": "USA highest grossing domestic film all time box office"},
        {"id": 7, "query": "Japan highest grossing domestic film all time box office"},
    ]
    
    all_results = {}
    for q in queries:
        print(f"\n🔍 Q{q['id']}: {q['query']}")
        results = await google_search(q["query"])
        all_results[q["id"]] = results
        for r in results:
            print(f"  • {r['title'][:80]}")
            print(f"    {r['snippet'][:150]}")
        print()
    
    with open("test_results_v3.json", "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print("Results saved.")

if __name__ == "__main__":
    asyncio.run(main())
