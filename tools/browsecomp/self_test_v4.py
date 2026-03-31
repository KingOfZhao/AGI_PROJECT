#!/usr/bin/env python3
"""
BrowseComp自测v4 - 使用Wikipedia API搜索验证
Wikipedia API是免费的，不需要网络翻墙
"""
import json
import urllib.request
import urllib.parse

def wiki_search(query):
    """Wikipedia搜索API"""
    url = f"https://zh.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&utf8&srlimit=3"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            results = []
            for item in data.get("query", {}).get("search", []):
                results.append({"title": item["title"], "snippet": item.get("snippet", "")})
            return results
    except Exception as e:
        return [{"title": "error", "snippet": str(e)}]

def wiki_extract(title):
    """提取Wikipedia文章摘要"""
    url = f"https://zh.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=extracts&exintro=true&explaintext=true&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                if "extract" in page:
                    return page["extract"][:500]
            return "No extract found"
    except Exception as e:
        return f"Error: {e}"

def en_wiki_extract(title):
    """英文Wikipedia摘要"""
    url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=extracts&exintro=true&explaintext=true&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                if "extract" in page:
                    return page["extract"][:500]
            return "No extract found"
    except Exception as e:
        return f"Error: {e}"

# ====== 测试开始 ======
print("=" * 60)
print("BrowseComp 自测 — Wikipedia API 搜索验证")
print("=" * 60)

questions = [
    {
        "id": 1,
        "query": "GitHub被微软收购2018 总部城市人口",
        "steps": [
            ("zh", "GitHub"),
            ("en", "San Francisco"),
        ]
    },
    {
        "id": 2,
        "query": "Transformer论文第一作者 本科大学",
        "steps": [
            ("en", "Ashish Vaswani"),
        ]
    },
    {
        "id": 3,
        "query": "2020奥运金牌最多国家 最高票房电影",
        "steps": [
            ("zh", "2020年夏季奥林匹克运动会奖牌榜"),
            ("en", "List of highest-grossing films in the United States"),
        ]
    },
    {
        "id": 4,
        "query": "Tagore国歌 国家GDP per capita",
        "steps": [
            ("zh", "罗宾德拉纳特·泰戈尔"),
            ("en", "India GDP per capita"),
        ]
    },
    {
        "id": 5,
        "query": "地壳最丰富元素 原子序数 发现者",
        "steps": [
            ("zh", "地壳元素丰度"),
            ("en", "Oxygen"),
        ]
    }
]

all_results = {}
for q in questions:
    print(f"\n{'─'*50}")
    print(f"Q{q['id']}: {q['query']}")
    print(f"{'─'*40}")
    
    q_results = {}
    for lang, term in q["steps"]:
        print(f"\n  📖 {lang.upper()}: {term}")
        
        # 搜索
        search_results = wiki_search(term) if lang == "zh" else wiki_search(term)
        print(f"  搜索结果: {search_results[0]['title'] if search_results else 'None'}")
        
        # 提取摘要
        if lang == "zh":
            extract = wiki_extract(term)
        else:
            extract = en_wiki_extract(term)
        print(f"  摘要: {extract[:300]}")
        q_results[term] = {"search": search_results, "extract": extract}
    
    all_results[q["id"]] = q_results

# 保存
with open("test_results_v4.json", "w") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print("结果已保存到 test_results_v4.json")
