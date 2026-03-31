#!/usr/bin/env python3
"""
BrowseComp自测v2 - 使用browser-use进行网页搜索
"""
import asyncio
import json
import sys

sys.path.insert(0, '/Users/administruter/Desktop/AGI_PROJECT/tools/browser-use-env/venv/lib/python3.12/site-packages')

async def search_and_answer(query, steps):
    """用browser-use搜索验证"""
    from browser_use import Agent, Browser
    
    browser = Browser(headless=True)
    
    # 用Google搜索每一步
    results = {}
    for i, step in enumerate(steps):
        search_task = f"Go to google.com and search for: {step}. Return the top 2 results with their titles and snippet text. Be concise."
        agent = Agent(task=search_task, browser=browser)
        try:
            result = await agent.run(max_steps=15)
            results[f"step_{i}"] = str(result)[:500]
            print(f"  Step {i}: {step}")
            print(f"  Result: {str(result)[:200]}")
        except Exception as e:
            results[f"step_{i}"] = f"Error: {e}"
            print(f"  Step {i}: ERROR - {e}")
    
    # 最终搜索
    final_task = f"Go to google.com and search for: {query}. Return the answer found. Be concise."
    agent = Agent(task=final_task, browser=browser)
    try:
        result = await agent.run(max_steps=15)
        results["final"] = str(result)[:500]
        print(f"  Final: {str(result)[:300]}")
    except Exception as e:
        results["final"] = f"Error: {e}"
        print(f"  Final: ERROR - {e}")
    
    await browser.close()
    return results

async def main():
    queries = [
        {
            "id": 1,
            "query": "San Francisco population 2024",
            "steps": ["San Francisco population 2024"]
        },
        {
            "id": 2,
            "query": "Ashish Vaswani undergraduate university",
            "steps": ["Ashish Vaswani undergraduate university USC"]
        },
        {
            "id": 3,
            "query": "2020 Olympics most gold medals country highest grossing film",
            "steps": ["2020 Tokyo Olympics gold medal count by country"]
        },
        {
            "id": 4,
            "query": "Tagore national anthem country GDP per capita",
            "steps": ["Rabindranath Tagore national anthem India Bangladesh"]
        },
        {
            "id": 5,
            "query": "most abundant element Earth crust atomic number discoverer",
            "steps": ["most abundant element Earth's crust oxygen discoverer"]
        }
    ]
    
    all_results = {}
    for q in queries:
        print(f"\n{'='*50}")
        print(f"Q{q['id']}: {q['query']}")
        try:
            results = await search_and_answer(q["query"], q["steps"])
            all_results[q["id"]] = results
        except Exception as e:
            all_results[q["id"]] = {"error": str(e)}
            print(f"  FATAL: {e}")
    
    with open("test_results_v2.json", "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print("\nResults saved to test_results_v2.json")

if __name__ == "__main__":
    asyncio.run(main())
