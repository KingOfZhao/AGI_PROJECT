#!/usr/bin/env python3
"""
BrowseComp 自测 + 能力强化脚本
对每道题执行：搜索→验证→回答→评分
"""
import json
import sys
import re
from duckduckgo_search import DDGS

def search(query, max_results=3):
    """DuckDuckGo搜索"""
    try:
        results = DDGS().text(query, max_results=max_results)
        return [{"title": r["title"], "body": r["body"], "href": r["href"]} for r in results]
    except Exception as e:
        return [{"title": "error", "body": str(e), "href": ""}]

def evaluate(query, expected, steps):
    """对一道题执行搜索验证+回答"""
    print(f"\n{'='*60}")
    print(f"问题: {query}")
    print(f"预期答案: {expected}")
    print(f"推理步骤: {steps}")
    print(f"{'─'*40}")
    
    # 对每个步骤搜索验证
    all_results = {}
    for i, step in enumerate(steps):
        print(f"\n🔍 步骤{i+1}: {step}")
        results = search(step)
        all_results[f"step_{i}"] = results
        for r in results[:2]:
            print(f"  • {r['title'][:60]}")
            print(f"    {r['body'][:150]}")
    
    # 用完整问题搜索最终答案
    print(f"\n🔍 最终验证搜索: {query}")
    final_results = search(query)
    for r in final_results[:2]:
        print(f"  • {r['title'][:60]}")
        print(f"    {r['body'][:150]}")
    
    all_results["final"] = final_results
    return all_results

if __name__ == "__main__":
    queries = [
        {
            "id": 1,
            "query": "What is the population of the city where the headquarters of the company that acquired GitHub in 2018 is located?",
            "answer": "~874961 (San Francisco)",
            "steps": ["GitHub acquired by Microsoft 2018", "Microsoft headquarters city", "San Francisco population 2024"]
        },
        {
            "id": 2,
            "query": "Which university did the first author of the Transformer paper attend for undergraduate?",
            "answer": "USC (Ashish Vaswani)",
            "steps": ["Attention Is All You Need first author", "Ashish Vaswani undergraduate university"]
        },
        {
            "id": 3,
            "query": "In the country that won the most gold medals at the 2020 Summer Olympics, what is the highest-grossing domestic film of all time?",
            "answer": "需要确认",
            "steps": ["2020 Tokyo Olympics most gold medals country", "that country highest grossing domestic film"]
        },
        {
            "id": 4,
            "query": "What is the GDP per capita of the country whose national anthem was composed by Rabindranath Tagore?",
            "answer": "需要确认",
            "steps": ["Rabindranath Tagore national anthem which country", "India GDP per capita 2024", "Bangladesh GDP per capita 2024"]
        },
        {
            "id": 5,
            "query": "What is the atomic number of the element that is the most abundant in the Earth's crust, and who discovered it?",
            "answer": "Oxygen, 8, Scheele/Priestley",
            "steps": ["most abundant element Earth crust", "oxygen atomic number", "oxygen discoverer"]
        }
    ]
    
    all_outputs = {}
    for q in queries:
        results = evaluate(q["query"], q["answer"], q["steps"])
        all_outputs[q["id"]] = results
    
    # Save results
    with open("test_results.json", "w") as f:
        json.dump(all_outputs, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print("结果已保存到 test_results.json")
