#!/usr/bin/env python3
"""基础科学知识采集 - 从公开来源获取"""
import os, re, json, time

SCIENCE = os.path.expanduser("~/Desktop/AGI_PROJECT/knowledge/books/science")
os.makedirs(SCIENCE, exist_ok=True)

# 基础科学核心主题和Wikipedia API
TOPICS = [
    ("经典力学", "Classical_mechanics"),
    ("量子力学", "Quantum_mechanics"),
    ("热力学", "Thermodynamics"),
    ("电磁学", "Electromagnetism"),
    ("统计力学", "Statistical_mechanics"),
    ("狭义相对论", "Special_relativity"),
    ("广义相对论", "General_relativity"),
    ("线性代数", "Linear_algebra"),
    ("微积分", "Calculus"),
    ("概率论", "Probability_theory"),
    ("信息论", "Information_theory"),
    ("进化论", "Evolution"),
    ("分子生物学", "Molecular_biology"),
    ("有机化学", "Organic_chemistry"),
    ("天体物理", "Astrophysics"),
    ("数论", "Number_theory"),
    ("拓扑学", "Topology"),
    ("博弈论", "Game_theory"),
    ("控制论", "Cybernetics"),
    ("复杂系统", "Complex_system"),
]

def fetch_wikipedia(title, lang="zh"):
    """从Wikipedia获取文章"""
    import urllib.request
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OpenClawAgent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("extract", "")
    except:
        return ""

def fetch_wikipedia_full(title, lang="zh"):
    """获取Wikipedia完整文章"""
    import urllib.request
    url = f"https://{lang}.wikipedia.org/w/api.php?action=query&titles={title}&prop=extracts&explaintext=1&exsectionformat=wiki&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OpenClawAgent/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                return page.get("extract", "")
    except:
        return ""

def main():
    print(f"采集 {len(TOPICS)} 个基础科学主题...\n")
    
    total = 0
    for zh_name, en_name in TOPICS:
        # 尝试中文Wiki
        text = fetch_wikipedia_full(zh_name, "zh")
        
        # 如果中文内容太少，补充英文
        if len(text) < 2000:
            en_text = fetch_wikipedia_full(en_name, "en")
            if len(en_text) > len(text):
                text = text + "\n\n--- English ---\n\n" + en_text
        
        if text:
            path = os.path.join(SCIENCE, f"{zh_name}.md")
            with open(path, 'w') as f:
                f.write(f"# {zh_name}\n\n")
                f.write(text)
            print(f"✅ {zh_name}: {len(text)} 字")
            total += len(text)
        else:
            print(f"❌ {zh_name}: 获取失败")
        
        time.sleep(0.5)  # polite
    
    print(f"\n总计: {total} 字")

if __name__ == "__main__":
    main()
