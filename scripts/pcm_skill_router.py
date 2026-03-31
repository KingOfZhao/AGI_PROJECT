#!/usr/bin/env python3
"""
PCM Skill Router — 智能技能发现与路由
======================================
核心机制: 意图识别 + 精准推送
- 从本地能力库 (workspace/skills/) 中加载全部 skill
- 基于用户意图进行多维匹配 (关键词 + 类别 + 语义相似度)
- 返回 Top-K 最匹配的 skill，供 LLM/Agent 使用

集成方式:
1. 独立使用: python pcm_skill_router.py "我想自动化部署到K8s"
2. API 模式: 作为模块被 api_server.py / growth_engine.py 等导入
3. PCM 联动: 生成索引到 pcm/watched/，PCM FileWatcher 自动感知
"""

import re
import json
from pathlib import Path
from collections import defaultdict

# ─────────────────────────── 路径 ───────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIRS = [
    PROJECT_ROOT / "workspace" / "skills",                    # 原有本地 skill
    PROJECT_ROOT / "workspace" / "skills" / "openclaw",       # 新导入的 openclaw skill
    PROJECT_ROOT / "skills",                                   # GitHub 导入的 skills (flutter/skills 等)
]
OPENCLAW_JSON = PROJECT_ROOT / "web" / "data" / "openclaw_skills.json"

# ─────────────────────────── 意图-类别映射 ───────────────────────────
# 用户意图关键词 → 匹配的 skill 类别
INTENT_CATEGORY_MAP = {
    # 编程 & 开发
    "代码": ["coding-agents-and-ides", "web-and-frontend-development", "cli-utilities"],
    "编程": ["coding-agents-and-ides", "web-and-frontend-development"],
    "code": ["coding-agents-and-ides", "web-and-frontend-development", "cli-utilities"],
    "debug": ["coding-agents-and-ides"],
    "调试": ["coding-agents-and-ides"],
    "测试": ["coding-agents-and-ides"],
    "test": ["coding-agents-and-ides"],
    "重构": ["coding-agents-and-ides"],
    "refactor": ["coding-agents-and-ides"],

    # DevOps & 部署
    "部署": ["devops-and-cloud", "self-hosted-and-automation"],
    "deploy": ["devops-and-cloud", "self-hosted-and-automation"],
    "docker": ["devops-and-cloud"],
    "k8s": ["devops-and-cloud"],
    "kubernetes": ["devops-and-cloud"],
    "ci/cd": ["devops-and-cloud"],
    "云": ["devops-and-cloud"],
    "cloud": ["devops-and-cloud"],
    "aws": ["devops-and-cloud"],
    "服务器": ["devops-and-cloud", "self-hosted-and-automation"],

    # Git & GitHub
    "git": ["git-and-github"],
    "github": ["git-and-github"],
    "pr": ["git-and-github"],
    "pull request": ["git-and-github"],
    "commit": ["git-and-github"],

    # Web & 前端
    "前端": ["web-and-frontend-development"],
    "frontend": ["web-and-frontend-development"],
    "react": ["web-and-frontend-development"],
    "vue": ["web-and-frontend-development"],
    "css": ["web-and-frontend-development"],
    "html": ["web-and-frontend-development"],
    "网页": ["web-and-frontend-development"],
    "website": ["web-and-frontend-development"],

    # Flutter & Dart & 移动端
    "flutter": ["flutter", "mobile-development", "coding-agents-and-ides"],
    "dart": ["flutter", "mobile-development", "coding-agents-and-ides"],
    "widget": ["flutter", "mobile-development"],
    "statefulwidget": ["flutter"],
    "statelesswidget": ["flutter"],
    "provider": ["flutter"],
    "riverpod": ["flutter"],
    "bloc": ["flutter"],
    "getx": ["flutter"],
    "pubspec": ["flutter"],
    "pub.dev": ["flutter"],
    "flutter build": ["flutter"],
    "flutter run": ["flutter"],
    "hot reload": ["flutter"],
    "mobile": ["mobile-development", "flutter"],
    "ios": ["mobile-development", "flutter"],
    "android": ["mobile-development", "flutter"],
    "app": ["mobile-development", "flutter"],
    "移动端": ["mobile-development", "flutter"],
    "移动应用": ["mobile-development", "flutter"],
    "跨平台": ["mobile-development", "flutter"],
    "刀模app": ["flutter"],
    "diepre app": ["flutter"],

    # AI & LLM
    "ai": ["ai-and-llms"],
    "llm": ["ai-and-llms"],
    "模型": ["ai-and-llms"],
    "model": ["ai-and-llms"],
    "gpt": ["ai-and-llms"],
    "claude": ["ai-and-llms"],
    "推理": ["ai-and-llms"],
    "训练": ["ai-and-llms"],

    # 搜索 & 研究
    "搜索": ["search-and-research"],
    "search": ["search-and-research"],
    "研究": ["search-and-research"],
    "research": ["search-and-research"],
    "论文": ["search-and-research"],
    "paper": ["search-and-research"],

    # 文档 & PDF
    "文档": ["pdf-and-documents", "notes-and-pkm"],
    "document": ["pdf-and-documents", "notes-and-pkm"],
    "pdf": ["pdf-and-documents"],
    "笔记": ["notes-and-pkm"],
    "note": ["notes-and-pkm"],
    "知识库": ["notes-and-pkm"],

    # 自动化 & 浏览器
    "自动化": ["browser-and-automation", "self-hosted-and-automation", "productivity-and-tasks"],
    "automation": ["browser-and-automation", "self-hosted-and-automation"],
    "浏览器": ["browser-and-automation"],
    "browser": ["browser-and-automation"],
    "爬虫": ["browser-and-automation"],
    "scrape": ["browser-and-automation"],

    # 通信 & 协作
    "邮件": ["communication"],
    "email": ["communication"],
    "slack": ["communication"],
    "消息": ["communication"],
    "message": ["communication"],
    "聊天": ["communication"],

    # 图像 & 视频
    "图片": ["image-and-video-generation"],
    "image": ["image-and-video-generation"],
    "视频": ["image-and-video-generation"],
    "video": ["image-and-video-generation"],
    "生成图": ["image-and-video-generation"],
    "generate image": ["image-and-video-generation"],
    "generate video": ["image-and-video-generation"],
    "生成视频": ["image-and-video-generation"],
    "生成图片": ["image-and-video-generation"],
    "stream": ["media-and-streaming"],
    "播放": ["media-and-streaming"],
    "media": ["media-and-streaming"],
    "媒体": ["media-and-streaming"],

    # 安全
    "安全": ["security-and-passwords"],
    "security": ["security-and-passwords"],
    "密码": ["security-and-passwords"],
    "password": ["security-and-passwords"],
    "审计": ["security-and-passwords"],
    "audit": ["security-and-passwords"],

    # 智能家居 & IoT
    "智能家居": ["smart-home-and-iot"],
    "iot": ["smart-home-and-iot"],
    "home assistant": ["smart-home-and-iot"],

    # 日历 & 计划
    "日历": ["calendar-and-scheduling"],
    "calendar": ["calendar-and-scheduling"],
    "日程": ["calendar-and-scheduling"],
    "schedule": ["calendar-and-scheduling"],
    "会议": ["calendar-and-scheduling"],
    "meeting": ["calendar-and-scheduling"],

    # 语音 & 转录
    "语音": ["speech-and-transcription"],
    "speech": ["speech-and-transcription"],
    "转录": ["speech-and-transcription"],
    "transcription": ["speech-and-transcription"],
    "tts": ["speech-and-transcription"],
    "whisper": ["speech-and-transcription"],

    # iOS & macOS
    "ios": ["ios-and-macos-development", "apple-apps-and-services"],
    "macos": ["ios-and-macos-development", "apple-apps-and-services"],
    "swift": ["ios-and-macos-development"],
    "xcode": ["ios-and-macos-development"],
    "apple": ["apple-apps-and-services"],

    # 数据 & 分析
    "数据": ["data-and-analytics"],
    "data": ["data-and-analytics"],
    "分析": ["data-and-analytics"],
    "analytics": ["data-and-analytics"],
    "dashboard": ["data-and-analytics"],

    # CLI
    "命令行": ["cli-utilities"],
    "cli": ["cli-utilities"],
    "terminal": ["cli-utilities"],
    "终端": ["cli-utilities"],
    "shell": ["cli-utilities"],

    # 任务 & 生产力
    "任务": ["productivity-and-tasks"],
    "task": ["productivity-and-tasks"],
    "todo": ["productivity-and-tasks"],
    "项目管理": ["productivity-and-tasks"],
    "project": ["productivity-and-tasks"],

    # 营销
    "营销": ["marketing-and-sales"],
    "marketing": ["marketing-and-sales"],
    "seo": ["marketing-and-sales"],

    # 健康
    "健康": ["health-and-fitness"],
    "health": ["health-and-fitness"],
    "fitness": ["health-and-fitness"],
    "运动": ["health-and-fitness"],

    # 交通
    "交通": ["transportation"],
    "transport": ["transportation"],
    "地图": ["transportation"],
    "map": ["transportation"],
    "导航": ["transportation"],

    # 购物
    "购物": ["shopping-and-e-commerce"],
    "shopping": ["shopping-and-e-commerce"],
    "ecommerce": ["shopping-and-e-commerce"],
    "电商": ["shopping-and-e-commerce"],

    # [P0] ULDS v2.1 十一大规律通用推演框架
    "推演": ["core-framework", "ai-and-llms"],
    "规律": ["core-framework"],
    "十一大规律": ["core-framework"],
    "九大规律": ["core-framework"],
    "固定变量": ["core-framework"],
    "链式收敛": ["core-framework"],
    "约束": ["core-framework"],
    "constraint": ["core-framework"],
    "deduction": ["core-framework"],
    "framework": ["core-framework"],
    "ulds": ["core-framework"],
    "误差预算": ["core-framework"],
    "rss": ["core-framework"],
    "dfm": ["core-framework"],
    "制造": ["core-framework"],
    "manufacturing": ["core-framework"],
    "包装": ["core-framework"],
    "packaging": ["core-framework"],
    "刀模": ["core-framework"],
    "die cutting": ["core-framework"],
    "优化": ["core-framework"],
    "optimization": ["core-framework"],
    "演化": ["core-framework"],
    "evolution": ["core-framework"],
    "适应性": ["core-framework"],
    "adaptation": ["core-framework"],
    "认识论": ["core-framework"],
    "epistemology": ["core-framework"],
    "认知偏差": ["core-framework"],
    "cognitive bias": ["core-framework"],
    "局部最优": ["core-framework"],
    "细化": ["core-framework"],
    "refinement": ["core-framework"],

    # 自性技能链 (local skill chain v1-v7)
    "编码链": ["coding"],
    "编码能力": ["coding"],
    "链式调用": ["coding", "orchestration"],
    "链式编码": ["coding"],
    "技能协调": ["orchestration"],
    "节点注册": ["orchestration"],
    "多链": ["orchestration"],
    "技能生成": ["meta_evolution"],
    "自进化": ["meta_evolution"],
    "自主进化": ["meta_evolution"],
    "代码验证": ["testing"],
    "测试用例": ["testing"],
    "自动修复": ["testing"],
    "脚手架": ["scaffolding"],
    "项目生成": ["scaffolding"],
    "知识图谱": ["knowledge_graph"],
    "节点图谱": ["knowledge_graph"],
    "节点关系": ["knowledge_graph"],
    "无穷闭环": ["meta_evolution"],
    "本地模型": ["coding", "orchestration", "meta_evolution", "testing", "scaffolding", "knowledge_graph"],
}


# ─────────────────────────── 跨语言关键词注入 ───────────────────────────
# 当检测到中文/短意图词时，自动注入对应的英文搜索词
INTENT_BOOST_KEYWORDS = {
    "视频": ["video", "generate", "create", "edit"],
    "图片": ["image", "generate", "photo", "picture"],
    "生成": ["generate", "create", "build"],
    "部署": ["deploy", "deployment", "kubernetes", "docker"],
    "自动化": ["automate", "automation", "workflow"],
    "搜索": ["search", "find", "query", "lookup"],
    "调试": ["debug", "debugger", "troubleshoot"],
    "测试": ["test", "testing", "unittest"],
    "文档": ["document", "docs", "documentation"],
    "数据": ["data", "analytics", "database"],
    "安全": ["security", "secure", "auth"],
    "邮件": ["email", "mail", "smtp"],
    "日历": ["calendar", "schedule", "event"],
    "语音": ["speech", "voice", "audio", "tts"],
    "笔记": ["note", "notes", "notebook"],
    "代码": ["code", "coding", "programming"],
    "编程": ["code", "programming", "develop"],
    "前端": ["frontend", "react", "vue", "css"],
    "浏览器": ["browser", "web", "chrome"],
    "爬虫": ["scrape", "crawl", "spider"],
    "翻译": ["translate", "translation", "i18n"],
    "购物": ["shopping", "ecommerce", "store"],
    "健康": ["health", "fitness", "medical"],
    "地图": ["map", "maps", "navigation", "geo"],
    "推理": ["reasoning", "inference", "llm"],
    "训练": ["training", "fine-tune", "model"],
    "论文": ["paper", "academic", "arxiv", "scholar", "literature"],
    "学术": ["academic", "research", "paper", "scholar"],
    "任务": ["task", "todo", "project", "manage"],
    "营销": ["marketing", "seo", "campaign", "ads"],
    "交通": ["transport", "traffic", "navigation", "route"],
    "智能家居": ["smart", "home", "iot", "device"],
    # [P0] ULDS v2.1 十一大规律推演
    "推演": ["reasoning", "deduction", "inference", "constraint"],
    "规律": ["law", "rule", "constraint", "universal"],
    "十一大规律": ["eleven", "laws", "universal", "deduction", "framework"],
    "九大规律": ["nine", "laws", "universal", "deduction", "framework"],
    "固定变量": ["fixed", "variable", "chain", "convergence"],
    "链式收敛": ["chain", "convergence", "constraint", "propagation"],
    "约束": ["constraint", "boundary", "limit", "range"],
    "误差": ["error", "tolerance", "RSS", "budget"],
    "制造": ["manufacturing", "DFM", "process", "production"],
    "包装": ["packaging", "box", "carton", "die"],
    "刀模": ["die", "cutting", "creasing", "packaging"],
    "优化": ["optimize", "optimization", "improve", "best"],
    "演化": ["evolution", "adaptation", "selection", "variation"],
    "适应性": ["adaptive", "fitness", "survival", "evolve"],
    "认识论": ["epistemology", "cognition", "bias", "limits"],
    "认知偏差": ["cognitive", "bias", "bounded", "rationality"],
    "局部最优": ["local", "optimum", "global", "escape"],
    "细化": ["refine", "refinement", "detail", "progressive"],
    # 自性技能链
    "编码链": ["chain", "coding", "generate", "refine"],
    "技能协调": ["orchestrate", "skill", "coordinate", "register"],
    "自进化": ["evolve", "generate", "skill", "auto"],
    "验证": ["validate", "test", "fix", "verify"],
    "脚手架": ["scaffold", "project", "generate", "structure"],
    "图谱": ["graph", "node", "relation", "knowledge"],
    "进化": ["evolve", "evolution", "self", "auto"],
    "链式": ["chain", "pipeline", "sequential"],
    "节点": ["node", "skill", "chain", "register"],
}

# ─────────────────────────── Skill 加载器 ───────────────────────────

class SkillLibrary:
    """本地 skill 能力库加载器"""

    def __init__(self):
        self.skills = []          # 全部 skill 列表
        self.by_category = defaultdict(list)
        self.by_name = {}
        self.keyword_index = defaultdict(set)  # 倒排索引: keyword → skill indices

    def load(self):
        """加载全部 skill"""
        # 1. 从 meta.json 文件加载
        for skill_dir in SKILL_DIRS:
            if not skill_dir.exists():
                continue
            for meta_file in skill_dir.glob("*.meta.json"):
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    skill = {
                        "name": meta.get("name", meta_file.stem),
                        "description": meta.get("description", ""),
                        "tags": meta.get("tags", []),
                        "category": meta.get("category", "unknown"),
                        "url": meta.get("url", ""),
                        "source": meta.get("source", "local"),
                        "safety_level": meta.get("safety_level", "unknown"),
                        "file": str(meta_file),
                    }
                    self._add_skill(skill)
                except Exception:
                    continue

        # 2. 从 openclaw JSON 加载 (如果 meta.json 较少)
        if OPENCLAW_JSON.exists() and len(self.skills) < 100:
            try:
                data = json.loads(OPENCLAW_JSON.read_text(encoding="utf-8"))
                for s in data.get("skills_flat", []):
                    if s["name"] not in self.by_name:
                        skill = {
                            "name": s["name"],
                            "description": s["description"],
                            "tags": [s.get("category", "")],
                            "category": s.get("category", "unknown"),
                            "url": s.get("url", ""),
                            "source": "openclaw",
                            "safety_level": "safe",
                        }
                        self._add_skill(skill)
            except Exception:
                pass

        self._build_keyword_index()
        return len(self.skills)

    def _add_skill(self, skill):
        idx = len(self.skills)
        self.skills.append(skill)
        self.by_category[skill["category"]].append(idx)
        self.by_name[skill["name"]] = idx

    def _build_keyword_index(self):
        """建立关键词倒排索引"""
        for idx, skill in enumerate(self.skills):
            # 提取 name 和 description 中的关键词
            text = f"{skill['name']} {skill['description']}".lower()
            # 分词 (英文按空格/标点，中文按2字及以上词组，不拆单字)
            words = re.findall(r"[a-z][a-z0-9]{1,}|[0-9]{2,}|[\u4e00-\u9fff]{2,}", text)
            for w in words:
                self.keyword_index[w].add(idx)
            # 也按 tag 建立索引 (使用同一分词器)
            for tag in skill.get("tags", []):
                for w in re.findall(r"[a-z][a-z0-9]{1,}|[0-9]{2,}|[\u4e00-\u9fff]{2,}", tag.lower()):
                    self.keyword_index[w].add(idx)


# ─────────────────────────── 意图匹配路由器 ───────────────────────────

class SkillRouter:
    """
    基于 PCM 思想的 Skill 智能路由器:
    - 意图识别: 从用户输入提取意图关键词
    - 类别匹配: 意图 → 类别 → candidate skills
    - 关键词匹配: 倒排索引精确匹配
    - 综合评分: 类别相关性 × 关键词命中 × safety 权重
    """

    def __init__(self, library: SkillLibrary):
        self.library = library

    def route(self, user_input: str, top_k: int = 10) -> list[dict]:
        """
        核心路由: 用户输入 → Top-K 匹配 skill
        返回 list[{skill, score, match_reasons}]
        """
        user_input_lower = user_input.lower()
        words = set(re.findall(r"[a-z][a-z0-9]{1,}|[0-9]{2,}|[\u4e00-\u9fff]{2,}", user_input_lower))

        # Phase 0: 跨语言关键词注入 (中文→英文)
        injected = set()
        for zh_key, en_words in INTENT_BOOST_KEYWORDS.items():
            if zh_key in user_input_lower:
                injected.update(en_words)
        words.update(injected)

        # Phase 1: 类别匹配
        matched_categories = set()
        for keyword, categories in INTENT_CATEGORY_MAP.items():
            if keyword in user_input_lower:
                matched_categories.update(categories)

        # Phase 2: 收集候选 skill
        candidates = {}  # idx → {score, reasons}
        category_pool = set()  # 类别匹配仅作为候选池

        # 2a. 类别匹配 → 候选池 (不直接加分)
        for cat in matched_categories:
            for idx in self.library.by_category.get(cat, []):
                category_pool.add(idx)

        # 2b. 关键词匹配 (倒排索引)
        for w in words:
            for idx in self.library.keyword_index.get(w, set()):
                if idx not in candidates:
                    candidates[idx] = {"score": 0.0, "reasons": []}
                candidates[idx]["score"] += 1.5
                candidates[idx]["reasons"].append(f"keyword:{w}")

        # 2c. 类别+关键词交叉加分
        for idx in category_pool:
            if idx in candidates:
                # 类别+关键词双重命中: 高加分
                candidates[idx]["score"] += 3.0
                candidates[idx]["reasons"].append("category_boost")
            else:
                # 仅类别命中: 基础分入池 (中文查询常无关键词命中)
                candidates[idx] = {"score": 2.0, "reasons": ["category_match"]}

        # 2d. 直接名称匹配 (高权重)
        for w in words:
            if w in self.library.by_name:
                idx = self.library.by_name[w]
                if idx not in candidates:
                    candidates[idx] = {"score": 0.0, "reasons": []}
                candidates[idx]["score"] += 10.0
                candidates[idx]["reasons"].append(f"name_match:{w}")

        # Phase 3: 描述子串匹配 (仅对 Top-100 精细化，避免全量扫描)
        bigrams = self._bigrams(words)
        if bigrams:
            top_100 = sorted(candidates.items(), key=lambda x: x[1]["score"], reverse=True)[:100]
            for idx, meta in top_100:
                skill = self.library.skills[idx]
                desc = skill["description"].lower()
                for bigram in bigrams:
                    if bigram in desc:
                        meta["score"] += 2.0
                        meta["reasons"].append(f"desc_bigram:{bigram}")

        # Phase 4: 安全权重调整
        for idx, meta in candidates.items():
            skill = self.library.skills[idx]
            if skill.get("safety_level") == "blocked":
                meta["score"] = 0
            elif skill.get("safety_level") == "warning":
                meta["score"] *= 0.8

        # Phase 4.5: 本地技能加权 (local > openclaw)
        for idx, meta in candidates.items():
            skill = self.library.skills[idx]
            if skill.get("source") == "local":
                meta["score"] += 1.5
                meta["reasons"].append("local_boost")

        # Phase 5: 排序返回 Top-K
        ranked = sorted(candidates.items(), key=lambda x: x[1]["score"], reverse=True)

        results = []
        for idx, meta in ranked[:top_k]:
            if meta["score"] <= 0:
                continue
            skill = self.library.skills[idx]
            results.append({
                "name": skill["name"],
                "description": skill["description"],
                "category": skill["category"],
                "url": skill.get("url", ""),
                "source": skill.get("source", ""),
                "score": round(meta["score"], 2),
                "match_reasons": list(set(meta["reasons"]))[:5],
            })

        return results

    def _bigrams(self, words: set) -> list[str]:
        """生成词对"""
        word_list = sorted(words)
        bigrams = []
        for i in range(len(word_list)):
            for j in range(i + 1, min(i + 3, len(word_list))):
                bigrams.append(f"{word_list[i]} {word_list[j]}")
                bigrams.append(f"{word_list[j]} {word_list[i]}")
        return bigrams

    def route_and_format(self, user_input: str, top_k: int = 10) -> str:
        """路由并格式化为 LLM 可用的上下文"""
        results = self.route(user_input, top_k)
        if not results:
            return "[Skill Router] 未找到匹配的 skill。"

        lines = [f"[Skill Router] 为您的意图匹配到 {len(results)} 个相关技能:"]
        for i, r in enumerate(results, 1):
            lines.append(f"  {i}. **{r['name']}** (score={r['score']}, {r['category']})")
            lines.append(f"     {r['description']}")
            if r.get("url"):
                lines.append(f"     → {r['url']}")
        return "\n".join(lines)


# ─────────────────────────── 全局单例 ───────────────────────────

_library = None
_router = None


def get_router() -> SkillRouter:
    """获取全局 SkillRouter 单例"""
    global _library, _router
    if _router is None:
        _library = SkillLibrary()
        count = _library.load()
        _router = SkillRouter(_library)
        print(f"[SkillRouter] Loaded {count} skills, keyword index size: {len(_library.keyword_index)}")
    return _router


def route_skills(user_input: str, top_k: int = 10) -> list[dict]:
    """便捷函数: 路由 skill"""
    return get_router().route(user_input, top_k)


def route_skills_formatted(user_input: str, top_k: int = 10) -> str:
    """便捷函数: 路由 skill 并格式化"""
    return get_router().route_and_format(user_input, top_k)


# ─────────────────────────── CLI ───────────────────────────

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pcm_skill_router.py <用户输入>")
        print("Example: python pcm_skill_router.py '我想自动化部署到K8s'")
        print("         python pcm_skill_router.py 'help me debug React code'")
        print("         python pcm_skill_router.py '生成一个视频'")
        sys.exit(1)

    user_input = " ".join(sys.argv[1:])
    print(f"\n🎯 用户输入: {user_input}\n")
    print(route_skills_formatted(user_input, top_k=15))


if __name__ == "__main__":
    main()
