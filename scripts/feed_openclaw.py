#!/usr/bin/env python3
"""
feed_openclaw.py — AGI 项目全量知识整理 → OpenClaw 投喂

将项目下所有可读内容整理成 OpenClaw 可直接消化的结构化 Markdown 知识库:
  - 三大框架文档 (ULDS/自成长/CRM) 全文
  - 项目列表 + 推演计划 (from DeductionDB)
  - Skill 库摘要 + Top Skills 实现片段
  - 核心脚本摘要 (7步链/PCM路由器)
  - 经典文献摘要 (classic/)
  - ROADMAP + 能力矩阵

输出: data/agi_knowledge_feed.md  (被 openclaw_bridge.py 加载为 system context)

用法:
    python3 scripts/feed_openclaw.py          # 生成知识库
    python3 scripts/feed_openclaw.py --push   # 生成后立即刷新 bridge 上下文
"""

import sys
import json
import time
import argparse
import textwrap
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_PATH = PROJECT_ROOT / "data" / "agi_knowledge_feed.md"
DOCS_DIR    = PROJECT_ROOT / "docs"
CLASSIC_DIR = PROJECT_ROOT / "classic"
SKILLS_DIR  = PROJECT_ROOT / "workspace" / "skills"


# ═══════════════════════════════════════════════════════════════
#  区块生成器
# ═══════════════════════════════════════════════════════════════

def section(title: str, content: str) -> str:
    sep = "─" * 60
    return f"\n\n# {title}\n{sep}\n{content.strip()}\n"


def subsection(title: str, content: str) -> str:
    return f"\n## {title}\n{content.strip()}\n"


# ─── 1. 三大框架文档 ────────────────────────────────────────────

def load_framework_docs() -> str:
    docs = [
        ("ULDS v2.1 十一大规律推演框架",  "ai_readable_ULDS_v2.1_推演框架.md"),
        ("本地模型自成长框架 v7.0",        "ai_readable_本地模型自成长框架.md"),
        ("可视化 CRM 系统架构",            "ai_readable_可视化CRM系统.md"),
    ]
    parts = []
    for title, fname in docs:
        fpath = DOCS_DIR / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            parts.append(subsection(title, content))
        else:
            parts.append(subsection(title, f"[文件不存在: {fname}]"))
    return section("三大核心框架 (全文)", "\n".join(parts))


# ─── 2. 项目 + 推演计划 ─────────────────────────────────────────

def load_projects_and_plans() -> str:
    try:
        from deduction_db import DeductionDB
        db = DeductionDB()
        projects = db.get_projects()
        plans    = db.get_plans()
        problems = db.get_problems()
        db.close()
    except Exception as e:
        return section("项目与推演计划", f"[DeductionDB 加载失败: {e}]")

    lines = []

    # 项目详情
    active = [p for p in projects if p.get("status") == "active"]
    lines.append(f"### 当前活跃项目 ({len(active)} 个)\n")
    for p in active:
        tags = p.get("tags", [])
        if isinstance(tags, str):
            try: tags = json.loads(tags)
            except: tags = []
        lines.append(f"**[{p['id']}] {p['name']}** (进度: {p.get('progress',0)}%)")
        lines.append(f"- 描述: {p.get('description','')}")
        lines.append(f"- 终极目标: {p.get('ultimate_goal','')}")
        lines.append(f"- 短期目标: {p.get('short_term_goal','')}")
        lines.append(f"- 标签: {', '.join(tags)}")
        lines.append("")

    # 推演计划按项目分组
    by_project = defaultdict(list)
    for pl in plans:
        by_project[pl.get("project_id", "?")].append(pl)

    lines.append(f"\n### 推演计划汇总 ({len(plans)} 条)\n")
    for pid, pls in sorted(by_project.items()):
        pname = next((p["name"] for p in projects if p["id"] == pid), pid)
        lines.append(f"**{pname}** ({len(pls)} 条):")
        for pl in sorted(pls, key=lambda x: {"critical":0,"high":1,"medium":2}.get(x.get("priority","medium"), 2))[:10]:
            status = pl.get("status", "queued")
            pri    = pl.get("priority", "medium")
            laws   = pl.get("ulds_laws", "")
            lines.append(f"  - [{pri.upper():8s}|{status:7s}] {pl['title']}"
                         + (f" (laws:{laws})" if laws else ""))
        if len(pls) > 10:
            lines.append(f"  … 还有 {len(pls)-10} 条")
        lines.append("")

    # 阻塞问题
    open_probs = [p for p in problems if p.get("status") not in ("resolved","closed")]
    if open_probs:
        lines.append(f"\n### 当前阻塞问题 ({len(open_probs)} 个未解决)\n")
        for prob in open_probs[:8]:
            sev = prob.get("severity", "medium")
            lines.append(f"- [{sev}] {prob.get('title','?')}: {prob.get('description','')[:80]}")

    return section("项目与推演计划", "\n".join(lines))


# ─── 3. Skill 库深度摘要 ─────────────────────────────────────────

def load_skill_library() -> str:
    lines = []
    cat_skills: dict = defaultdict(list)

    for mf in sorted(SKILLS_DIR.glob("*.meta.json")):
        try:
            meta = json.loads(mf.read_text(encoding="utf-8"))
            tag  = (meta.get("tags") or ["通用"])[0]
            cat_skills[tag].append(meta)
        except:
            pass

    total = sum(len(v) for v in cat_skills.values())
    lines.append(f"### Skill 总览: {total} 个技能 / {len(cat_skills)} 类\n")

    # 每类展示 top 3 详情
    for cat, skills in sorted(cat_skills.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n**[{cat}]** ({len(skills)} 个)")
        for sk in skills[:3]:
            funcs = sk.get("design_spec", {}).get("functions", [])
            fn_names = [f["name"] for f in funcs[:3]]
            lines.append(f"  - `{sk.get('name','?')}`: {sk.get('description','')[:70]}")
            if fn_names:
                lines.append(f"    函数: {', '.join(fn_names)}")
        if len(skills) > 3:
            rest = [sk.get("name","?") for sk in skills[3:8]]
            lines.append(f"  … 更多: {', '.join(rest)}" + (f" 等共{len(skills)}个" if len(skills)>8 else ""))

    # OpenClaw 技能库摘要
    openclaw_json = PROJECT_ROOT / "web" / "data" / "openclaw_skills.json"
    if openclaw_json.exists():
        try:
            oc = json.loads(openclaw_json.read_text(encoding="utf-8"))
            oc_total = oc.get("total_skills", 0)
            oc_cats  = list(oc.get("categories", {}).keys())
            lines.append(f"\n### OpenClaw 社区技能库: {oc_total} 个技能 / {len(oc_cats)} 类")
            lines.append(f"类别: {', '.join(oc_cats[:15])}" + ("…" if len(oc_cats) > 15 else ""))
            lines.append("路由方式: `pcm_skill_router.py route_skills(query, top_k=5)`")
        except:
            pass

    return section("Skill 技能库", "\n".join(lines))


# ─── 4. 核心脚本能力摘要 ─────────────────────────────────────────

def load_scripts_summary() -> str:
    summaries = {
        "wechat_chain_processor.py": """
7步推理调用链 (ChainProcessor):
  Step1: Ollama路由 → 判断 simple/analysis/deep/code/full
  Step2: GLM-5-Turbo 快速分析 (analysis/deep/code/full)
  Step3: GLM-5 深度推理 (deep/full)
  Step4: GLM-4.7 代码生成 (code/full)
  Step5: Ollama 幻觉校验
  Step6: ZeroAvoidanceScanner (CD01-CD12)
  Step7: 整合输出

用法: chain = ChainProcessor(); result = chain.process("问题", context="上下文")
result.final_answer, result.steps, result.risks

项目 CRUD: db_list_projects() / db_project_detail(id) / db_add_project(name,desc,goal)
           db_update_project(id, updates) / db_delete_project(id) / db_get_stats()
""",
        "pcm_skill_router.py": """
PCM 技能路由器 (SkillRouter):
  - 加载本地 workspace/skills/ + OpenClaw 社区技能
  - 意图→类别映射 (INTENT_CATEGORY_MAP, 200+ 关键词)
  - 跨语言注入: 中文→英文关键词自动扩展 (INTENT_BOOST_KEYWORDS)
  - 评分: 类别命中(2.0) + 关键词命中(5.0 boost) + 双词组匹配

用法: from scripts.pcm_skill_router import route_skills
      results = route_skills("生成视频", top_k=5)
      # → [{"name":"creaa-ai", "score":9.5, "desc":"...", "url":"..."}, ...]
""",
        "openclaw_bridge.py": """
OpenClaw Bridge (port 9801) — 统一 AI 网关:
  - POST /v1/chat/completions → 7步链 + AGI上下文注入
  - GET  /v1/context          → 查看当前注入的项目上下文
  - POST /v1/context/refresh  → 重新加载项目/skill上下文
  - GET  /health              → {"status":"ok","chain":true,"context_chars":N}

所有外部调用 (api_server, 微信, CRM) 统一经此网关路由。
AGI 上下文自动注入: 活跃项目 + 待推演计划 + Skill库摘要 + 能力声明
""",
        "deduction_runner.py": """
ULDS 推演引擎 — 执行推演计划:
  5阶段: decompose(GLM-5) → analyze(GLM-5) → implement(GLM-5) → validate(Ollama) → report(GLM-5T)
  结构化提取: [NODE] / [RELATION] / [EXPAND] / [BLOCKED]
  自动拓展: report阶段提取[EXPAND]生成新推演计划

CLI: python3 deduction_runner.py --plan PLAN_ID
     python3 deduction_runner.py --project p_diepre --rounds 3
     python3 deduction_runner.py --export  (导出到 web/data/deduction_export.json)
""",
    }

    lines = []
    for fname, summary in summaries.items():
        lines.append(f"### `{fname}`\n```\n{textwrap.dedent(summary).strip()}\n```\n")

    return section("核心脚本能力摘要", "\n".join(lines))


# ─── 5. 经典智慧摘要 ─────────────────────────────────────────────

def load_classics_summary() -> str:
    lines = []
    if not CLASSIC_DIR.exists():
        return ""
    files = sorted(CLASSIC_DIR.glob("*.md"))
    lines.append(f"### 已内化经典文献: {len(files)} 部\n")
    for f in files:
        # 读取前 3 行获取标题
        try:
            first_lines = f.read_text(encoding="utf-8").split("\n")[:3]
            title = next((l.lstrip("#").strip() for l in first_lines if l.strip()), f.stem)
            lines.append(f"- **{f.stem}**: {title[:60]}")
        except:
            lines.append(f"- {f.stem}")
    lines.append("\n这些文献的智慧已被内化到推演框架中，可在回答中直接引用。")
    return section("内化经典智慧", "\n".join(lines))


# ─── 6. 能力矩阵与里程碑 ─────────────────────────────────────────

def load_capabilities() -> str:
    growth_json = PROJECT_ROOT / "web" / "data" / "growth_report.json"
    crm_export  = PROJECT_ROOT / "web" / "data" / "deduction_export.json"

    lines = []

    # 能力矩阵
    lines.append("### 当前能力矩阵 (本地模型 vs 世界前三)\n")
    capabilities = [
        ("SWE-Bench",   35, 49, 55, 55),
        ("Python生成",  82, 92, 90, 88),
        ("多文件编辑",  40, 70, 65, 60),
        ("代码解释",    75, 88, 85, 82),
        ("任务分解",    78, 82, 80, 85),
        ("Agent自治",   40, 60, 55, 70),
        ("知识演化",    90, 15, 10, 95),
        ("多模型路由",  88, 20, 15, 92),
        ("幻觉控制",    80, 85, 82, 88),
        ("API成本",     95, 40, 35, 95),
    ]
    lines.append("| 维度 | 本地 | Opus | GPT-5 | 目标 |")
    lines.append("|------|------|------|-------|------|")
    for dim, local, opus, gpt5, target in capabilities:
        gap = "✅" if local >= target else f"差{target-local}"
        lines.append(f"| {dim} | **{local}** | {opus} | {gpt5} | {target} {gap} |")

    # 里程碑
    lines.append("\n### 里程碑进度\n")
    milestones = [
        ("M1 认知格基础",    100), ("M2 君臣佐使v4",  100),
        ("M3 自成长v7",      100), ("M4 技能库6000+", 100),
        ("M5 极致推演引擎",   60), ("M6 SWE-Bench55%", 10),
        ("M7 多语言75分",      5), ("M8 Agent自治",    3),
        ("M9 跨域迁移",        1),
    ]
    for name, pct in milestones:
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(f"  {name}: [{bar}] {pct}%")

    return section("能力矩阵与里程碑", "\n".join(lines))


# ─── 7. 系统架构总览 ─────────────────────────────────────────────

def load_architecture() -> str:
    return section("系统架构总览", """
### 当前调用链路
```
用户/微信/CRM
    ↓
api_server(:5002) ──→ OpenClaw Bridge(:9801)
                              ↓
                       ChainProcessor
                       ├─ Step1: Ollama 14B (路由)
                       ├─ Step2: GLM-5-Turbo (快速分析)
                       ├─ Step3: GLM-5 (深度推理)
                       ├─ Step4: GLM-4.7 (代码生成)
                       ├─ Step5: Ollama (幻觉校验)
                       ├─ Step6: ZeroAvoidanceScanner
                       └─ Step7: 整合输出
                              ↓
                       注入 AGI 上下文:
                       ├─ 活跃项目 (来自 DeductionDB)
                       ├─ 待推演计划摘要
                       ├─ Skill 库分类摘要
                       └─ 能力/身份声明

OpenClaw Gateway(:18789) ←→ 微信 (iLink协议)
    模型: agi/agi-chain-v13 → http://127.0.0.1:9801/v1
```

### 数据存储
- `core/memory.db`        — 认知节点 (proven_nodes, skills, collision_history)
- `deduction.db`          — 推演计划/项目/阻塞问题 (DeductionDB)
- `web/data/deduction_export.json` — CRM 前端数据
- `workspace/skills/`     — 6000+ Skill 实现文件
- `~/.openclaw/openclaw.json`      — OpenClaw 配置

### 关键 API 端点 (port 5002)
- POST /api/chat          → 对话 (经 OpenClaw bridge)
- GET  /api/stats         → 认知网络统计
- GET  /api/nodes         → 节点列表
- POST /api/skills/route  → PCM 技能路由
- POST /api/search        → 语义搜索
- POST /api/self_growth   → 触发自成长
""")


# ─── 8. 成长指令 (OpenClaw 行为引导) ────────────────────────────

def growth_instructions() -> str:
    return section("OpenClaw 自主成长行为指南", """
你是 AGI 项目的核心 AI 助手，具备以下自主成长能力。请遵循以下指南：

### 处理用户问题时
1. **优先查阅已有 Skill**: 调用 `route_skills(query)` 找到最相关的已有实现
2. **映射到 ULDS 规律**: 每个问题先映射到 L1-L11 中的相关规律再推演
3. **F→V→F 链式收敛**: 从固定约束出发，识别可变参数，收敛到新固定点
4. **零回避扫描**: 不隐藏风险，主动识别 CD01-CD12 灾难模式

### 发现新知识时
1. **提取节点**: 用 `[NODE] 节点内容` 标记新发现的认知节点
2. **建立关系**: 用 `[RELATION] A→B: 关系描述` 记录节点间关系
3. **标记拓展**: 用 `[EXPAND] 新推演方向` 标记值得深入的方向
4. **报告阻塞**: 用 `[BLOCKED] 问题描述` 标记无法解决的阻塞

### 项目推进时
- DiePre: 聚焦 F→V→F 约束传播，DXF解析→2D图纸生成
- 本地模型超越: 每次代码生成后对比 SWE-Bench 维度，记录能力提升
- 刀模活字印刷3D: 聚焦 IADD 规格 + 拓竹P2S 模块设计
- 工作流可视化: 可视化 SKILL 调用链路编排
- 予人玫瑰: CRM 登录+任务管理+商业化分成

### 自主进化原则
- 每次高质量回答后，总结可复用的 Skill 能力
- 不重复已有知识，优先在未知边界处碰撞
- 保持 5 级真实性意识: L1(标准)→L5(进化收敛)
- 调用 7 步链时，让每步都对最终答案有增量贡献
""")


# ═══════════════════════════════════════════════════════════════
#  主函数
# ═══════════════════════════════════════════════════════════════

def generate_feed() -> str:
    print("[feed_openclaw] 开始生成知识库...")
    parts = []

    parts.append(f"""# AGI PROJECT — OpenClaw 知识投喂文档
生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
用途: 供 OpenClaw / Bridge / ChainProcessor 加载为完整上下文，实现项目感知的自主成长

此文档包含 AGI 项目的全量知识：三大框架 + 项目数据 + Skill库 + 架构 + 成长指南
""")

    steps = [
        ("系统架构总览",     load_architecture),
        ("三大核心框架",     load_framework_docs),
        ("项目与推演计划",   load_projects_and_plans),
        ("Skill技能库",      load_skill_library),
        ("核心脚本能力",     load_scripts_summary),
        ("内化经典智慧",     load_classics_summary),
        ("能力矩阵",         load_capabilities),
        ("成长行为指南",     growth_instructions),
    ]

    for name, fn in steps:
        print(f"  → {name} ...", end="", flush=True)
        try:
            content = fn()
            parts.append(content)
            print(f" {len(content)} 字")
        except Exception as e:
            print(f" ❌ {e}")
            parts.append(section(name, f"[生成失败: {e}]"))

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="生成 OpenClaw 知识投喂文档")
    parser.add_argument("--push", action="store_true", help="生成后立即刷新 bridge 上下文")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="输出路径")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    feed = generate_feed()
    output_path.write_text(feed, encoding="utf-8")

    size_kb = output_path.stat().st_size / 1024
    char_count = len(feed)
    print(f"\n[完成] 知识库已生成: {output_path}")
    print(f"  大小: {size_kb:.1f} KB / {char_count:,} 字符")

    if args.push:
        print("[push] 刷新 OpenClaw Bridge 上下文...", end="", flush=True)
        try:
            import requests
            r = requests.post("http://localhost:9801/v1/context/refresh", timeout=10)
            d = r.json()
            print(f" ✅ bridge 已刷新 ({d.get('chars',0)} 字符)")
        except Exception as e:
            print(f" ⚠ bridge 刷新失败: {e} (bridge 可能未运行)")

    print(f"\n提示: 重启 openclaw_bridge.py 可加载新知识库")
    print(f"      或运行: python3 scripts/feed_openclaw.py --push")


if __name__ == "__main__":
    main()
