#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: Web 研究引擎
核心能力: 搜索互联网 → 抓取页面 → 提取知识 → 结构化为认知节点
这是 AGI 获取外部新知识的关键通道，使其不局限于训练数据。

由 AGI v13.3 Cognitive Lattice 构建
"""

import sys
import json
import re
import urllib.request
import urllib.parse
import urllib.error
import ssl
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser

PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# 简易 HTML 文本提取器
class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._text = []
        self._skip = False
        self._skip_tags = {'script', 'style', 'nav', 'footer', 'header', 'noscript'}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False
        if tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr'):
            self._text.append('\n')

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self._text.append(text)

    def get_text(self):
        return ' '.join(self._text)


def fetch_url(url, timeout=15):
    """抓取 URL 内容，返回纯文本"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AGI-CognitiveLattice/1.0'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            charset = resp.headers.get_content_charset() or 'utf-8'
            html = resp.read().decode(charset, errors='replace')
            extractor = _TextExtractor()
            extractor.feed(html)
            text = extractor.get_text()
            # 清理多余空白
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r' {2,}', ' ', text)
            return {"success": True, "text": text[:15000], "url": url, "length": len(text)}
    except Exception as e:
        return {"success": False, "error": str(e), "url": url}


def search_web(query, num_results=5):
    """
    使用 DuckDuckGo HTML 搜索（无需 API key）
    返回搜索结果列表 [{title, url, snippet}]
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        
        results = []
        # 解析 DuckDuckGo HTML 结果
        # 匹配结果块
        blocks = re.findall(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )
        
        for href, title, snippet in blocks[:num_results]:
            # 清理 HTML 标签
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            # DuckDuckGo 的链接需要解码
            if '/l/?uddg=' in href:
                real_url = urllib.parse.unquote(href.split('uddg=')[1].split('&')[0])
            else:
                real_url = href
            
            if clean_title:
                results.append({
                    "title": clean_title,
                    "url": real_url,
                    "snippet": clean_snippet
                })
        
        return {"success": True, "query": query, "results": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e), "query": query, "results": []}


def extract_knowledge(text, topic, max_points=10):
    """用 LLM 从文本中提取结构化知识点"""
    import agi_v13_cognitive_lattice as agi
    
    prompt = [
        {"role": "system", "content": """你是知识提取专家。从给定文本中提取与主题相关的关键知识点。
输出 JSON 数组，每项：
[{"content": "一句话描述的知识点", "domain": "所属领域", "confidence": 0.0-1.0, "can_verify": true/false}]
只输出 JSON，不要其他文字。确保每个知识点是独立的、可验证的事实。"""},
        {"role": "user", "content": f"主题：{topic}\n\n文本（截取）：\n{text[:5000]}"}
    ]
    
    result = agi.llm_call(prompt)
    items = agi.extract_items(result)
    return items[:max_points]


def research_topic(topic, depth=1):
    """
    完整研究流程：搜索 → 抓取前N个结果 → 提取知识 → 返回结构化结果
    depth=1: 只搜索一次
    depth=2: 搜索后对关键发现再次搜索
    """
    all_knowledge = []
    sources = []
    
    # 第一轮搜索
    search_result = search_web(topic, num_results=3)
    if not search_result["success"]:
        return {"success": False, "error": search_result["error"], "knowledge": []}
    
    for r in search_result["results"]:
        page = fetch_url(r["url"])
        if page["success"] and len(page["text"]) > 100:
            knowledge = extract_knowledge(page["text"], topic)
            for k in knowledge:
                if isinstance(k, dict):
                    k["source_url"] = r["url"]
                    k["source_title"] = r["title"]
                    all_knowledge.append(k)
            sources.append({"url": r["url"], "title": r["title"], "text_length": page["length"]})
    
    # 深度搜索：用第一轮发现的关键概念再搜索
    if depth >= 2 and all_knowledge:
        # 取置信度最高的几个知识点作为新搜索词
        sorted_k = sorted(all_knowledge, key=lambda x: x.get('confidence', 0), reverse=True)
        new_queries = [k['content'] for k in sorted_k[:2] if isinstance(k, dict)]
        for nq in new_queries:
            sr2 = search_web(nq, num_results=2)
            if sr2["success"]:
                for r in sr2["results"]:
                    if r["url"] not in [s["url"] for s in sources]:
                        page = fetch_url(r["url"])
                        if page["success"] and len(page["text"]) > 100:
                            knowledge = extract_knowledge(page["text"], nq)
                            for k in knowledge:
                                if isinstance(k, dict):
                                    k["source_url"] = r["url"]
                                    all_knowledge.append(k)
                            sources.append({"url": r["url"], "title": r.get("title", ""), "text_length": page["length"]})
    
    # 去重
    seen = set()
    unique_knowledge = []
    for k in all_knowledge:
        content = k.get('content', '') if isinstance(k, dict) else str(k)
        if content and content not in seen:
            seen.add(content)
            unique_knowledge.append(k)
    
    return {
        "success": True,
        "topic": topic,
        "knowledge": unique_knowledge,
        "sources": sources,
        "total_points": len(unique_knowledge)
    }


def research_and_ingest(topic, lattice=None):
    """研究主题并将知识直接注入认知网络"""
    result = research_topic(topic, depth=1)
    if not result["success"]:
        return result
    
    ingested = 0
    if lattice:
        for k in result["knowledge"]:
            if isinstance(k, dict):
                content = k.get("content", "")
                domain = k.get("domain", "研究")
                confidence = k.get("confidence", 0.5)
                can_verify = k.get("can_verify", False)
                status = "known" if can_verify and confidence > 0.7 else "hypothesis"
                if content and len(content) > 5:
                    nid = lattice.add_node(content, domain, status, source="web_research", silent=True)
                    if nid:
                        ingested += 1
    
    result["ingested_nodes"] = ingested
    return result


# === 技能元数据 ===
SKILL_META = {
    "name": "Web研究引擎",
    "description": "搜索互联网→抓取页面→LLM提取知识→结构化为认知节点。AGI获取外部新知识的通道。",
    "tags": ["web搜索", "知识提取", "外部数据", "研究能力"],
    "created_at": datetime.now().isoformat(),
    "version": "1.0",
    "capabilities": ["search_web", "fetch_url", "extract_knowledge", "research_topic", "research_and_ingest"]
}

if __name__ == "__main__":
    print("=== Web 研究引擎自测 ===")
    sr = search_web("Python asyncio tutorial", num_results=3)
    print(f"搜索结果: {sr['count']} 条")
    for r in sr.get("results", []):
        print(f"  - {r['title'][:60]}")
        print(f"    {r['url'][:80]}")
    print("\n研究引擎自测完成")
