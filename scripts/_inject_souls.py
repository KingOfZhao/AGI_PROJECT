#!/usr/bin/env python3
"""将圣贤竞技场灵魂智慧写入知识库并刷新Bridge"""
import json
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARENA_FILE = PROJECT_ROOT / "data" / "sage_arena.json"
FEED_FILE = PROJECT_ROOT / "data" / "agi_knowledge_feed.md"

def main():
    arena = json.loads(ARENA_FILE.read_text())
    alive = [(n, s) for n, s in arena["sages"].items() if s["alive"]]
    alive.sort(key=lambda x: -sum(x[1]["abilities"].values()) / len(x[1]["abilities"]))

    print(f"存活灵魂: {len(alive)}")

    lines = [
        "",
        "",
        "# 圣贤竞技场灵魂 (益众生制度)",
        f"共{len(alive)}位灵魂存活, 每位400+能力维度",
        "",
        "## 前10灵魂核心哲学",
    ]
    for i, (n, s) in enumerate(alive[:10], 1):
        ph = s.get("philosophy", "")
        dm = s.get("domain", "")
        lines.append(f"{i}. **{n}**({dm}): {ph}")

    lines.append("")
    lines.append("## 灵魂思维模式(融入每次推演)")
    lines.append("回答问题时融合以下视角:")
    lines.append("- 哥伦布: 向未知出发")
    lines.append("- 莎士比亚: 结构化表达一切")
    lines.append("- 诺伊曼: 博弈最优策略")
    lines.append("- 居里夫人: 反复实验直到变成已知")
    lines.append("- 爱因斯坦: 想象力比知识重要")
    lines.append("- 老子: 无为而无不为")
    lines.append("- 毛泽东: 抓主要矛盾")
    lines.append("- 王阳明: 知行合一")
    lines.append("- 释迦牟尼: 缘起性空")
    lines.append("- 图灵: 形式化一切可计算")
    lines.append("")

    text = "\n".join(lines)

    with open(FEED_FILE, "a", encoding="utf-8") as f:
        f.write(text)
    print(f"已写入知识库: {len(text)} 字符")

    # 刷新 Bridge
    try:
        r = requests.post("http://127.0.0.1:9801/v1/context/refresh", timeout=5)
        d = r.json()
        print(f"Bridge 已刷新: {d.get('chars', 0)} 字符")
    except Exception as e:
        print(f"Bridge 刷新失败: {e}")

    # 打印前5
    for i, (n, s) in enumerate(alive[:5], 1):
        p = sum(s["abilities"].values()) / len(s["abilities"])
        print(f"  #{i} {n} (战力:{p:.1f}, 维度:{len(s['abilities'])})")

if __name__ == "__main__":
    main()
