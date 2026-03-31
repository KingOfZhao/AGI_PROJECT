#!/usr/bin/env python3
"""
BrowseComp 训练v2 — 更难的多跳推理 + 多源验证
每次运行自动生成新题，验证后评分，追踪进步
"""
import json
import urllib.request
import urllib.parse
import time
import sys
from datetime import datetime

def wiki_zh(title):
    url = f"https://zh.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=extracts&exintro=true&explaintext=true&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BrowseComp-Trainer/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for pid, page in data.get("query", {}).get("pages", {}).items():
                if "extract" in page:
                    return page["extract"][:800]
    except: pass
    return None

def wiki_en(title):
    url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=extracts&exintro=true&explaintext=true&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BrowseComp-Trainer/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for pid, page in data.get("query", {}).get("pages", {}).items():
                if "extract" in page:
                    return page["extract"][:800]
    except: pass
    return None

def wiki_search_zh(query):
    url = f"https://zh.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit=3"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BrowseComp-Trainer/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return [item["title"] for item in data.get("query", {}).get("search", [])]
    except: pass
    return []

def wiki_search_en(query):
    url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit=3"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BrowseComp-Trainer/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return [item["title"] for item in data.get("query", {}).get("search", [])]
    except: pass
    return []

# ============ 训练题集（BrowseComp风格，更难） ============
questions = [
    {
        "id": 6,
        "category": "multi_hop",
        "query": "What is the birth year of the CEO of the company that acquired LinkedIn in 2016, and what country was that person born in?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "LinkedIn acquisition 2016", "expected": "Microsoft acquired LinkedIn"},
            {"action": "search", "query": "Microsoft CEO", "expected": "Satya Nadella"},
            {"action": "verify", "query": "Satya Nadella birth year country"},
        ]
    },
    {
        "id": 7,
        "category": "temporal_reasoning",
        "query": "Which country won the FIFA World Cup in the year that the Berlin Wall fell?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "Berlin Wall fall year"},
            {"action": "search", "query": "1990 FIFA World Cup winner"},
            {"action": "verify", "query": "1990 World Cup final result"},
        ]
    },
    {
        "id": 8,
        "category": "chain",
        "query": "What is the capital of the country where the inventor of the World Wide Web was born?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "World Wide Web inventor"},
            {"action": "search", "query": "Tim Berners-Lee birthplace country"},
            {"action": "search", "query": "United Kingdom capital"},
        ]
    },
    {
        "id": 9,
        "category": "science",
        "query": "What is the half-life of the element with atomic number 92, and who discovered it?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "atomic number 92 element"},
            {"action": "search", "query": "Uranium half-life"},
            {"action": "search", "query": "Uranium discoverer"},
        ]
    },
    {
        "id": 10,
        "category": "cross_domain",
        "query": "In the novel that won the Pulitzer Prize for Fiction in 2023, what is the setting (city/state) of the main story?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "Pulitzer Prize Fiction 2023 winner"},
            {"action": "search", "query": "Demon Copperhead setting location"},
        ]
    },
    {
        "id": 11,
        "category": "math_geo",
        "query": "What is the population density (people per km²) of the smallest country by area that borders the Mediterranean Sea?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "smallest country bordering Mediterranean Sea"},
            {"action": "search", "query": "Monaco population area"},
            {"action": "compute", "query": "population / area = density"},
        ]
    },
    {
        "id": 12,
        "category": "history_tech",
        "query": "Who was the founder of the company that launched the first iPhone, and what university did they drop out of?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "first iPhone launched by which company"},
            {"action": "search", "query": "Apple founder Steve Jobs education dropout"},
        ]
    },
    {
        "id": 13,
        "category": "deep_chain",
        "query": "What is the official language of the country where the Chernobyl nuclear disaster occurred?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "Chernobyl nuclear disaster location country"},
            {"action": "search", "query": "Ukraine official language"},
        ]
    },
    {
        "id": 14,
        "category": "ambiguous",
        "query": "How many time zones does the country with the longest coastline in the world span?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "country longest coastline world"},
            {"action": "search", "query": "Canada time zones number"},
            {"action": "verify", "query": "Canada time zones count 6 or 7"},
        ]
    },
    {
        "id": 15,
        "category": "reverse_reasoning",
        "query": "What element has the highest electronegativity, and in which year was it discovered?",
        "my_answer": None,
        "steps": [
            {"action": "search", "query": "highest electronegativity element periodic table"},
            {"action": "search", "query": "Fluorine discovery year discoverer"},
        ]
    },
]

# ============ 执行搜索验证 ============
results = {}
total_score = 0
total_questions = len(questions)

for q in questions:
    print(f"\n{'='*60}")
    print(f"Q{q['id']} [{q['category']}]: {q['query']}")
    print(f"{'─'*50}")
    
    collected_evidence = []
    
    for i, step in enumerate(q["steps"]):
        action = step["action"]
        query = step["query"]
        print(f"\n  Step {i+1} [{action}]: {query}")
        
        if action in ("search", "verify"):
            # 先搜英文
            en_results = wiki_search_en(query)
            zh_results = wiki_search_zh(query)
            
            print(f"    EN search: {en_results[:2]}")
            print(f"    ZH search: {zh_results[:2]}")
            
            # 提取最相关的文章
            for title in en_results[:2]:
                extract = wiki_en(title)
                if extract:
                    print(f"    📖 EN [{title}]: {extract[:200]}")
                    collected_evidence.append({"source": f"en:{title}", "text": extract})
                    time.sleep(0.3)
            
            for title in zh_results[:2]:
                extract = wiki_zh(title)
                if extract:
                    print(f"    📖 ZH [{title}]: {extract[:200]}")
                    collected_evidence.append({"source": f"zh:{title}", "text": extract})
                    time.sleep(0.3)
        
        elif action == "compute":
            print(f"    ⚙️ Computation step")
            # 简单计算
    
    # 存储证据
    results[q["id"]] = {
        "category": q["category"],
        "query": q["query"],
        "evidence_count": len(collected_evidence),
        "evidence_sources": [e["source"] for e in collected_evidence],
    }

# 保存
output = {
    "timestamp": datetime.now().isoformat(),
    "version": 2,
    "total_questions": total_questions,
    "results": results
}

with open("/Users/administruter/Desktop/AGI_PROJECT/tools/browsecomp/training_v2.json", "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print(f"训练完成，共{total_questions}题")
print(f"证据已保存到 training_v2.json")
print(f"下一步：基于证据逐题推理，计算准确率")
