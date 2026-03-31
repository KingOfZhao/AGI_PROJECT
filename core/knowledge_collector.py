"""
知识采集引擎 — 从网页/GitHub/开源项目获取新知识
==================================================
能力:
  1. curl快速抓取(静态页面/API)
  2. Playwright动态渲染(JS页面)
  3. BeautifulSoup结构化解析
  4. 知识提取→结构化→存储
"""

import json
import re
import time
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


@dataclass
class KnowledgeItem:
    """知识条目"""
    url: str
    title: str
    content: str          # 正文摘要 (500字以内)
    full_text: str        # 完整正文
    source_type: str      # github / web / docs
    tags: List[str]
    quality_score: float  # 0-1
    collected_at: str
    category: str = ""


class WebFetcher:
    """网页抓取"""
    
    @staticmethod
    def curl(url: str, timeout: int = 15) -> Tuple[int, str]:
        """快速抓取静态页面"""
        try:
            r = subprocess.run(
                ["curl", "-sL", "-A", "Mozilla/5.0", "--max-time", str(timeout), url],
                capture_output=True, text=True, timeout=timeout + 5
            )
            # Get HTTP code
            code_r = subprocess.run(
                ["curl", "-sL", "-o", "/dev/null", "-w", "%{http_code}", 
                 "-A", "Mozilla/5.0", "--max-time", str(timeout), url],
                capture_output=True, text=True, timeout=timeout + 5
            )
            return int(code_r.stdout.strip()), r.stdout
        except Exception as e:
            return 0, str(e)
    
    @staticmethod
    def playwright_fetch(url: str, timeout: int = 20) -> Tuple[int, str]:
        """动态渲染页面 (JS)"""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=timeout * 1000)
                page.wait_for_load_state("networkidle", timeout=timeout * 1000)
                text = page.content()
                browser.close()
                return 200, text
        except Exception as e:
            return 0, str(e)
    
    @staticmethod
    def github_api(endpoint: str) -> Optional[dict]:
        """GitHub REST API (公开端点, 无需认证)"""
        url = f"https://api.github.com{endpoint}"
        try:
            r = requests.get(url, timeout=10, 
                           headers={"Accept": "application/vnd.github.v3+json"})
            if r.status_code == 200:
                return r.json()
            return None
        except:
            return None
    
    @staticmethod
    def search_duckduckgo(query: str, max_results: int = 5) -> List[Dict]:
        """DuckDuckGo搜索 (无需API key)"""
        url = "https://html.duckduckgo.com/html/"
        try:
            r = requests.post(url, data={"q": query}, timeout=10,
                            headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return []
            
            results = []
            if HAS_BS4:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.select(".result__a")[:max_results]:
                    href = a.get("href", "")
                    # Extract URL from DDG redirect
                    match = re.search(r'uddg=([^&]+)', href)
                    if match:
                        actual_url = requests.utils.unquote(match.group(1))
                    else:
                        actual_url = href
                    results.append({
                        "title": a.get_text(strip=True),
                        "url": actual_url,
                    })
            return results
        except Exception as e:
            return []


class KnowledgeExtractor:
    """从HTML中提取结构化知识"""
    
    @staticmethod
    def extract_article(html: str, url: str = "") -> Dict:
        """提取文章正文"""
        if not HAS_BS4:
            return {"title": "", "content": html[:2000], "full_text": html}
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script/style/nav
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        # Title
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)
        h1 = soup.find("h1")
        if h1 and not title:
            title = h1.get_text(strip=True)
        
        # Main content (try article/main first, fallback to body)
        main = soup.find("article") or soup.find("main") or soup.find("body")
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)
        
        # Clean up
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        text = "\n".join(lines)
        
        return {
            "title": title,
            "content": text[:1000],
            "full_text": text,
        }


class KnowledgeCollector:
    """知识采集→存储pipeline"""
    
    def __init__(self, store_path: str = None):
        if store_path is None:
            store_path = str(Path(__file__).parent.parent / "data" / "knowledge_store.jsonl")
        self.store_path = Path(store_path)
        self.fetcher = WebFetcher()
        self.extractor = KnowledgeExtractor()
    
    def collect_url(self, url: str, use_playwright: bool = False, 
                    tags: List[str] = None) -> Optional[KnowledgeItem]:
        """采集单个URL"""
        if use_playwright:
            code, html = self.fetcher.playwright_fetch(url)
        else:
            code, html = self.fetcher.curl(url)
        
        if code != 200 or not html:
            return None
        
        article = self.extractor.extract_article(html, url)
        
        if not article["title"] and not article["content"]:
            return None
        
        # Quality: based on content length
        quality = min(1.0, len(article["content"]) / 500)
        
        item = KnowledgeItem(
            url=url,
            title=article["title"] or url,
            content=article["content"],
            full_text=article["full_text"],
            source_type="web",
            tags=tags or [],
            quality_score=quality,
            collected_at=datetime.now().isoformat(),
        )
        
        self._save(item)
        return item
    
    def collect_github_readme(self, repo: str, tags: List[str] = None) -> Optional[KnowledgeItem]:
        """采集GitHub项目README"""
        data = self.fetcher.github_api(f"/repos/{repo}/readme")
        if not data:
            return None
        
        import base64
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        
        item = KnowledgeItem(
            url=f"https://github.com/{repo}",
            title=f"GitHub: {repo}",
            content=content[:1000],
            full_text=content,
            source_type="github",
            tags=tags or ["github", repo.split("/")[0]],
            quality_score=min(1.0, len(content) / 1000),
            collected_at=datetime.now().isoformat(),
        )
        
        self._save(item)
        return item
    
    def search_and_collect(self, query: str, max_results: int = 3, 
                          tags: List[str] = None) -> List[KnowledgeItem]:
        """搜索并采集"""
        results = self.fetcher.search_duckduckgo(query, max_results)
        items = []
        for r in results:
            item = self.collect_url(r["url"], tags=tags)
            if item:
                items.append(item)
            time.sleep(1)  # Be polite
        return items
    
    def _save(self, item: KnowledgeItem):
        """追加到JSONL存储"""
        record = {
            "url": item.url,
            "title": item.title,
            "content": item.content,
            "source_type": item.source_type,
            "tags": item.tags,
            "quality": item.quality_score,
            "collected_at": item.collected_at,
        }
        with open(self.store_path, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def list_recent(self, n: int = 10) -> List[Dict]:
        """列出最近采集的知识"""
        if not self.store_path.exists():
            return []
        with open(self.store_path) as f:
            lines = f.readlines()
        return [json.loads(l) for l in lines[-n:]]
    
    def search_store(self, keyword: str) -> List[Dict]:
        """在已采集知识中搜索"""
        if not self.store_path.exists():
            return []
        results = []
        with open(self.store_path) as f:
            for line in f:
                record = json.loads(line)
                if keyword.lower() in record.get("title", "").lower() or \
                   keyword.lower() in record.get("content", "").lower():
                    results.append(record)
        return results


if __name__ == "__main__":
    collector = KnowledgeCollector()
    
    print("=" * 60)
    print("  知识采集引擎 — 能力测试")
    print("=" * 60)
    
    # Test 1: GitHub README
    print("\n--- 测试1: GitHub README采集 ---")
    for repo in ["openclaw/openclaw", "anthropics/anthropic-sdk-python"]:
        item = collector.collect_github_readme(repo, tags=["open-source", "ai-agent"])
        if item:
            print(f"  ✅ {item.title}: {len(item.content)} chars, quality={item.quality_score:.2f}")
        else:
            print(f"  ❌ {repo}")
        time.sleep(1)
    
    # Test 2: Web search
    print("\n--- 测试2: DuckDuckGo搜索 ---")
    results = collector.fetcher.search_duckduckgo("die cutting tolerance calculation formula", 3)
    for r in results:
        print(f"  {r['title']}: {r['url']}")
    
    # Test 3: Web fetch
    print("\n--- 测试3: 网页抓取 ---")
    code, html = collector.fetcher.curl("https://en.wikipedia.org/wiki/Statistical_tolerance_analysis")
    if code == 200:
        article = collector.extractor.extract_article(html)
        print(f"  ✅ Wikipedia: {article['title']}, {len(article['content'])} chars")
    
    # Test 4: GitHub trending
    print("\n--- 测试4: GitHub Trending (Python) ---")
    data = collector.fetcher.github_api("/search/repositories?q=stars:>1000+language:python&sort=stars&per_page=5")
    if data and "items" in data:
        for item in data["items"][:5]:
            print(f"  ⭐{item['stargazers_count']:6d} {item['full_name']}: {item['description'][:60]}")
    
    # Test 5: ClawHub explore
    print("\n--- 测试5: ClawHub热门skill ---")
    r = subprocess.run(["clawhub", "explore", "--limit", "5"], capture_output=True, text=True)
    print(r.stdout[:500])
    
    # Recent
    print("\n--- 最近采集 ---")
    for item in collector.list_recent(5):
        print(f"  [{item['source_type']}] {item['title'][:50]} (quality={item['quality']:.2f})")
