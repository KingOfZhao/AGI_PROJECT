#!/usr/bin/env python3
"""
OpenClaw Skill Scanner + Safety Checker + PCM Integration
=========================================================
1. 解析 awesome-openclaw-skills 全部 30 个分类文件 (5200+ skills)
2. 安全扫描: 过滤恶意/高风险/加密货币/金融交易类 skill
3. 安全的开源 skill 保存到本地能力库 workspace/skills/openclaw/
4. 导出全部 skill 为 JSON 供 PCM 意图匹配
5. 生成 PCM watched/ 目录下的 skill 索引文件
"""

import re
import json
import hashlib
import datetime
from pathlib import Path
from collections import defaultdict

# ─────────────────────────── 路径配置 ───────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATEGORIES_DIR = PROJECT_ROOT / "awesome-openclaw-skills" / "categories"
LOCAL_SKILL_DIR = PROJECT_ROOT / "workspace" / "skills" / "openclaw"
PCM_WATCHED_DIR = PROJECT_ROOT / "pcm" / "intelligent-context-system" / "watched"
EXPORT_JSON_PATH = PROJECT_ROOT / "web" / "data" / "openclaw_skills.json"
REPORT_PATH = PROJECT_ROOT / "docs" / "openclaw_skill_scan_report.md"

# ─────────────────────────── 安全规则 ───────────────────────────

# 高风险关键词 (完全拒绝)
BLACKLIST_KEYWORDS = [
    # 加密货币/区块链/金融交易
    "crypto", "blockchain", "defi", "nft", "token swap", "token transfer",
    "wallet", "ethereum", "solana", "bitcoin", "polygon", "arbitrum",
    "uniswap", "liquidity pool", "staking", "yield farm", "airdrop",
    "polymarket", "betting", "bet on", "wager", "gambling",
    "trading bot", "trade signal", "forex", "stock trade",
    "cross-chain", "bridge token", "decentralized exchange",
    "smart contract deploy", "mint token", "burn token",
    "hedera", "near token", "bnb chain", "doginal", "inscription",
    "escrow payment", "x402", "l402",
    # 恶意/危险操作
    "red team", "exploit", "injection attack", "backdoor",
    "credential harvest", "phishing", "keylog", "rootkit",
    "malware", "ransomware", "trojan",
    "prompt injection", "jailbreak",
    # 间谍/隐私侵犯
    "spy", "surveillance", "track user", "scrape private",
]

# 中风险关键词 (需要审核，默认标记 warning)
WARN_KEYWORDS = [
    "payment", "billing", "credit card", "invoice",
    "password manager", "secret scan", "api key",
    "remote access", "ssh tunnel", "reverse shell",
    "ad campaign", "google ads", "facebook ads",
    "social media post", "auto tweet", "auto post",
    "vpn", "proxy", "tor",
    "influencer", "follower bot",
]

# 需要词边界匹配的黑名单关键词 (避免子串误杀)
BLACKLIST_WORD_BOUNDARY = [
    "dex",    # 避免匹配 index, codex, yandex
    "nft",    # 避免匹配 confetti 等
]

# 防御性工具白名单前缀 (这些 skill 是安全防护方，不应拦截)
DEFENSE_PREFIXES = [
    "anti-", "defense", "guard", "protect", "detect",
    "shield", "sentinel", "audit", "scanner", "monitor",
    "firewall", "security", "lock", "secure",
]

# 安全类别白名单 (这些类别默认信任度更高)
SAFE_CATEGORIES = {
    "coding-agents-and-ides", "cli-utilities", "devops-and-cloud",
    "git-and-github", "notes-and-pkm", "pdf-and-documents",
    "productivity-and-tasks", "search-and-research",
    "web-and-frontend-development", "ios-and-macos-development",
    "speech-and-transcription", "self-hosted-and-automation",
}

# ─────────────────────────── 解析器 ───────────────────────────

SKILL_LINE_RE = re.compile(
    r"^-\s+\[([^\]]+)\]\(([^)]+)\)\s*-\s*(.+)$"
)


def parse_category_file(filepath: Path) -> list[dict]:
    """解析一个分类 markdown 文件，提取所有 skill 条目"""
    skills = []
    category = filepath.stem  # e.g. "ai-and-llms"
    text = filepath.read_text(encoding="utf-8")

    for line in text.splitlines():
        line = line.strip()
        m = SKILL_LINE_RE.match(line)
        if m:
            name, url, description = m.group(1), m.group(2), m.group(3).strip()
            skills.append({
                "name": name,
                "url": url,
                "description": description,
                "category": category,
                "source": "openclaw",
            })
    return skills


def parse_all_categories() -> list[dict]:
    """解析全部分类文件"""
    all_skills = []
    if not CATEGORIES_DIR.exists():
        print(f"[ERROR] Categories dir not found: {CATEGORIES_DIR}")
        return all_skills

    for md_file in sorted(CATEGORIES_DIR.glob("*.md")):
        skills = parse_category_file(md_file)
        print(f"  📂 {md_file.name}: {len(skills)} skills")
        all_skills.extend(skills)

    return all_skills


# ─────────────────────────── 安全扫描 ───────────────────────────

class SkillSafetyScanner:
    """多层安全扫描器"""

    def __init__(self):
        self.stats = defaultdict(int)
        self.blocked_reasons = defaultdict(list)

    def scan(self, skill: dict) -> dict:
        """
        返回 skill 附加安全信息:
          safety_level: "safe" | "warning" | "blocked"
          safety_reasons: list[str]
        """
        reasons = []
        name_lower = skill['name'].lower()
        text = f"{name_lower} {skill['description']}".lower()

        # Layer 0: 防御性工具白名单豁免
        is_defensive = any(name_lower.startswith(p) or p in text[:80] for p in DEFENSE_PREFIXES)

        # Layer 1: 黑名单关键词 (子串匹配)
        for kw in BLACKLIST_KEYWORDS:
            if kw.lower() in text:
                if is_defensive and kw in ("prompt injection", "jailbreak", "exploit",
                                           "injection attack", "red team", "phishing"):
                    continue  # 防御性工具豁免攻击类关键词
                reasons.append(f"BLOCKED: blacklist keyword '{kw}'")

        # Layer 1b: 词边界匹配 (避免子串误杀)
        for kw in BLACKLIST_WORD_BOUNDARY:
            pattern = rf'\b{re.escape(kw)}\b'
            if re.search(pattern, text):
                if is_defensive:
                    continue
                reasons.append(f"BLOCKED: blacklist keyword '{kw}'")

        if reasons:
            skill["safety_level"] = "blocked"
            skill["safety_reasons"] = reasons
            self.stats["blocked"] += 1
            self.blocked_reasons["blacklist"].append(skill["name"])
            return skill

        # Layer 2: URL 安全检查
        url = skill.get("url", "")
        if not url.startswith("https://"):
            reasons.append("BLOCKED: non-HTTPS URL")
            skill["safety_level"] = "blocked"
            skill["safety_reasons"] = reasons
            self.stats["blocked"] += 1
            self.blocked_reasons["non_https"].append(skill["name"])
            return skill

        # Layer 3: 描述长度检查 (过短可能是垃圾)
        if len(skill["description"]) < 10:
            reasons.append("WARNING: description too short (<10 chars)")

        # Layer 4: 中风险关键词
        for kw in WARN_KEYWORDS:
            if kw.lower() in text:
                reasons.append(f"WARNING: risk keyword '{kw}'")

        # Layer 5: 类别信任度
        cat = skill.get("category", "")
        if cat in SAFE_CATEGORIES:
            # 白名单类别中的 warning 降级为 info
            reasons = [r.replace("WARNING:", "INFO:") if r.startswith("WARNING: risk keyword") else r for r in reasons]

        # 判定
        if any(r.startswith("BLOCKED:") for r in reasons):
            skill["safety_level"] = "blocked"
            self.stats["blocked"] += 1
        elif any(r.startswith("WARNING:") for r in reasons):
            skill["safety_level"] = "warning"
            self.stats["warning"] += 1
        else:
            skill["safety_level"] = "safe"
            self.stats["safe"] += 1

        skill["safety_reasons"] = reasons
        return skill

    def report(self) -> str:
        total = sum(self.stats.values())
        lines = [
            f"## 安全扫描报告",
            f"- **总计**: {total} skills",
            f"- **安全 (safe)**: {self.stats['safe']}",
            f"- **警告 (warning)**: {self.stats['warning']}",
            f"- **拦截 (blocked)**: {self.stats['blocked']}",
            "",
            "### 拦截原因分布",
        ]
        for reason, names in self.blocked_reasons.items():
            lines.append(f"- **{reason}**: {len(names)} skills")
        return "\n".join(lines)


# ─────────────────────────── 本地保存 ───────────────────────────

def skill_to_meta_json(skill: dict) -> dict:
    """将 skill 转换为本地 meta.json 格式 (与现有 workspace/skills/*.meta.json 兼容)"""
    slug = re.sub(r"[^a-z0-9_]", "_", skill["name"].lower().replace("-", "_"))
    return {
        "name": skill["name"],
        "slug": slug,
        "description": skill["description"],
        "description_zh": "",  # 待翻译
        "tags": [skill["category"], "openclaw", "open_source"],
        "url": skill["url"],
        "source": "openclaw",
        "category": skill["category"],
        "safety_level": skill.get("safety_level", "unknown"),
        "safety_reasons": skill.get("safety_reasons", []),
        "created_at": datetime.datetime.now().isoformat(),
        "imported_by": "openclaw_skill_scanner",
    }


def save_safe_skills(skills: list[dict]) -> int:
    """将安全的 skill 保存到本地能力库"""
    LOCAL_SKILL_DIR.mkdir(parents=True, exist_ok=True)
    saved = 0

    for skill in skills:
        if skill.get("safety_level") not in ("safe", "warning"):
            continue

        meta = skill_to_meta_json(skill)
        slug = meta["slug"]
        filepath = LOCAL_SKILL_DIR / f"{slug}.meta.json"

        # 避免覆盖已有文件 (去重)
        if filepath.exists():
            # 用 hash 检查内容是否一致
            existing = json.loads(filepath.read_text(encoding="utf-8"))
            if existing.get("url") == meta["url"]:
                continue
            # 不同 URL 的同名 skill，加后缀
            h = hashlib.md5(meta["url"].encode()).hexdigest()[:6]
            filepath = LOCAL_SKILL_DIR / f"{slug}_{h}.meta.json"

        filepath.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        saved += 1

    return saved


# ─────────────────────────── PCM 导出 ───────────────────────────

def export_for_pcm(skills: list[dict]) -> dict:
    """导出全部安全 skill 为 PCM 可用的 JSON 格式"""
    safe_skills = [s for s in skills if s.get("safety_level") in ("safe", "warning")]

    # 按类别分组
    by_category = defaultdict(list)
    for s in safe_skills:
        by_category[s["category"]].append({
            "name": s["name"],
            "description": s["description"],
            "url": s["url"],
            "category": s["category"],
            "safety_level": s["safety_level"],
        })

    export = {
        "version": "1.0",
        "generated_at": datetime.datetime.now().isoformat(),
        "total_skills": len(safe_skills),
        "categories": dict(by_category),
        "skills_flat": [{
            "name": s["name"],
            "description": s["description"],
            "category": s["category"],
            "url": s["url"],
        } for s in safe_skills],
    }

    EXPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_JSON_PATH.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    return export


def generate_pcm_skill_index(skills: list[dict], top_per_cat: int = 10) -> Path:
    """
    生成 PCM watched/ 目录下的 skill 索引 markdown (精简版)。
    每个类别只保留 top_per_cat 个代表性 skill，总量控制在 500 行内，
    避免 PCM 上下文窗口溢出。
    """
    PCM_WATCHED_DIR.mkdir(parents=True, exist_ok=True)
    safe_skills = [s for s in skills if s.get("safety_level") in ("safe", "warning")]

    by_cat = defaultdict(list)
    for s in safe_skills:
        by_cat[s["category"]].append(s)

    lines = [
        "# AGI Skill Library Index (Summary)",
        f"Total: {len(safe_skills)} verified skills across {len(by_cat)} categories",
        f"Generated: {datetime.datetime.now().isoformat()}",
        "",
        "## Categories Overview",
    ]
    for cat in sorted(by_cat.keys()):
        lines.append(f"- **{cat.replace('-', ' ').title()}**: {len(by_cat[cat])} skills")
    lines.append("")

    for cat in sorted(by_cat.keys()):
        cat_skills = by_cat[cat]
        lines.append(f"## {cat.replace('-', ' ').title()} (Top {min(top_per_cat, len(cat_skills))} of {len(cat_skills)})")
        for s in cat_skills[:top_per_cat]:
            lines.append(f"- **{s['name']}**: {s['description'][:100]}")
        if len(cat_skills) > top_per_cat:
            lines.append(f"- ... and {len(cat_skills) - top_per_cat} more")
        lines.append("")

    index_path = PCM_WATCHED_DIR / "skill_library_index.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    return index_path


# ─────────────────────────── 报告生成 ───────────────────────────

def generate_report(all_skills: list[dict], scanner: SkillSafetyScanner, saved: int, export: dict) -> str:
    """生成完整的扫描报告"""
    lines = [
        "# OpenClaw Skill 扫描 & 安全审查报告",
        f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 概览",
        f"- **扫描源**: awesome-openclaw-skills (5200+ community skills)",
        f"- **解析总数**: {len(all_skills)} skills",
        f"- **保存到本地**: {saved} skills → `workspace/skills/openclaw/`",
        f"- **PCM 导出**: {export['total_skills']} skills → `web/data/openclaw_skills.json`",
        "",
        scanner.report(),
        "",
        "## 类别分布",
    ]

    cat_counts = defaultdict(lambda: {"safe": 0, "warning": 0, "blocked": 0})
    for s in all_skills:
        cat_counts[s["category"]][s.get("safety_level", "unknown")] += 1

    lines.append("| 类别 | Safe | Warning | Blocked | Total |")
    lines.append("|------|------|---------|---------|-------|")
    for cat in sorted(cat_counts.keys()):
        c = cat_counts[cat]
        total = c["safe"] + c["warning"] + c["blocked"]
        lines.append(f"| {cat} | {c['safe']} | {c['warning']} | {c['blocked']} | {total} |")

    lines.append("")
    lines.append("## 拦截的 Skill 列表 (前50)")
    blocked = [s for s in all_skills if s.get("safety_level") == "blocked"]
    for s in blocked[:50]:
        reasons = "; ".join(s.get("safety_reasons", []))
        lines.append(f"- **{s['name']}** ({s['category']}): {reasons}")

    lines.append("")
    lines.append("## PCM 集成说明")
    lines.append("""
### 工作原理
1. **FileWatcher**: PCM 的 FileWatcher 监控 `pcm/intelligent-context-system/watched/` 目录
2. **skill_library_index.md**: 全部安全 skill 的索引文件自动放入该目录
3. **IntentEngine**: 用户输入 → PCM 意图识别 → 从 skill 索引中匹配最相关的 skill
4. **ContextBuilder**: 匹配到的 skill 作为上下文推送给 LLM，无需全量加载

### 数据流
```
用户提问 → IntentEngine.analyze() → ContextBuilder.build()
                                        ↓
                                    relevantMemories 包含匹配的 skill
                                        ↓
                                    LLM 收到精准的 skill 上下文
```
""")

    report_text = "\n".join(lines)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    return report_text


# ─────────────────────────── 主流程 ───────────────────────────

def main():
    print("=" * 60)
    print("🔍 OpenClaw Skill Scanner + Safety Checker + PCM Integration")
    print("=" * 60)

    # Step 1: 解析全部分类
    print("\n📖 Step 1: 解析全部分类文件...")
    all_skills = parse_all_categories()
    print(f"   ✅ 共解析 {len(all_skills)} skills")

    # Step 2: 安全扫描
    print("\n🛡️  Step 2: 安全扫描...")
    scanner = SkillSafetyScanner()
    for skill in all_skills:
        scanner.scan(skill)
    print(f"   ✅ Safe: {scanner.stats['safe']} | Warning: {scanner.stats['warning']} | Blocked: {scanner.stats['blocked']}")

    # Step 3: 保存安全 skill 到本地
    print("\n💾 Step 3: 保存安全 skill 到本地能力库...")
    saved = save_safe_skills(all_skills)
    print(f"   ✅ 保存 {saved} skills → {LOCAL_SKILL_DIR}")

    # Step 4: 导出 PCM JSON
    print("\n📤 Step 4: 导出 PCM JSON...")
    export = export_for_pcm(all_skills)
    print(f"   ✅ 导出 {export['total_skills']} skills → {EXPORT_JSON_PATH}")

    # Step 5: 生成 PCM watched 索引
    print("\n📋 Step 5: 生成 PCM skill 索引...")
    index_path = generate_pcm_skill_index(all_skills)
    print(f"   ✅ 索引文件 → {index_path}")

    # Step 6: 生成报告
    print("\n📊 Step 6: 生成扫描报告...")
    report = generate_report(all_skills, scanner, saved, export)
    print(f"   ✅ 报告 → {REPORT_PATH}")

    # 摘要
    print("\n" + "=" * 60)
    print("✅ 全部完成!")
    print(f"   本地能力库: {LOCAL_SKILL_DIR}")
    print(f"   PCM JSON:   {EXPORT_JSON_PATH}")
    print(f"   PCM 索引:   {index_path}")
    print(f"   扫描报告:   {REPORT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
