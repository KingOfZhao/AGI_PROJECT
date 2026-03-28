#!/usr/bin/env python3
"""
skill_to_deduction_importer.py
将 workspace/skills/ 下所有 .meta.json 技能文件解析后，
按分类（primary tag）分组，批量写入 DeductionDB 的待推演列表。

目标：本地模型对 skill 库完全掌握，将技能转换成自身能力。

运行：
    python3 scripts/skill_to_deduction_importer.py
    python3 scripts/skill_to_deduction_importer.py --dry-run   # 只统计不写入
    python3 scripts/skill_to_deduction_importer.py --clear     # 先清空旧 skill 计划再导入
"""

import json
import sys
import time
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from deduction_db import DeductionDB

# ── 专属项目 ──────────────────────────────────────────────────
SKILL_PROJECT = {
    "id": "p_skill_mastery",
    "name": "Skill 能力内化工程",
    "description": "将 workspace/skills/ 的 6000+ 技能库系统化内化为本地模型的自身能力。"
                   "逐类推演：理解→复现→改进→融合，最终实现零提示直接调用。",
    "color": "#8b5cf6",
    "status": "active",
    "progress": 0,
    "tags": ["skill", "内化", "本地模型", "自成长"],
    "ultimate_goal": "本地 Ollama 模型完全掌握所有 skill，无需外部 API 即可独立完成任意任务",
    "short_term_goal": "每周推演 10 个类别，将掌握率提升至 80%+",
}

# ── 类别优先级映射 ──────────────────────────────────────────────
PRIORITY_MAP = {
    # critical
    "代码": "critical", "编程": "critical", "架构": "critical",
    "code": "critical", "python": "critical", "系统": "critical",
    # high
    "ai": "high", "机器学习": "high", "深度学习": "high", "推理": "high",
    "数据": "high", "分析": "high", "工具": "high", "API": "high",
    # medium (default)
}

# ── ULDS 规律映射（按类别注入最相关的规律）─────────────────────
ULDS_MAP = {
    "代码": "L1(数学公理) L3(化学/物质守恒→代码不变量) L9(可计算性)",
    "编程": "L1 L4(逻辑律) L9(可计算性 NP)",
    "架构": "L6(系统论 反馈环) L8(对称性 简化) L9",
    "ai": "L5(信息论 香农熵) L6 L10(演化动力学)",
    "数据": "L1 L5 L7(概率统计 3σ)",
    "工具": "L4(逻辑律) L9",
    "推理": "L4 L5 L11(认识论极限)",
}

def _get_priority(tags: List[str]) -> str:
    for t in tags:
        for kw, pri in PRIORITY_MAP.items():
            if kw.lower() in t.lower():
                return pri
    return "medium"

def _get_ulds(tags: List[str]) -> str:
    for t in tags:
        for kw, ulds in ULDS_MAP.items():
            if kw.lower() in t.lower():
                return ulds
    return "L1 L4 L9(可计算性)"

def _category_from_tags(tags: List[str], filename: str) -> str:
    """从 tags 提取主分类，fallback 到文件名前缀"""
    if tags:
        return tags[0]
    # fallback: 从文件名推断
    name = filename.replace("auto_", "").replace(".meta.json", "")
    for kw in ["代码", "ai", "数据", "架构", "工具", "推理", "python", "flutter", "web"]:
        if kw in name.lower():
            return kw
    return "通用"

def scan_skills(skills_dir: Path) -> Dict[str, List[dict]]:
    """扫描所有 .meta.json，按主分类分组"""
    grouped: Dict[str, List[dict]] = defaultdict(list)
    total = 0
    errors = 0

    for f in sorted(skills_dir.glob("*.meta.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                meta = json.load(fh)
            tags = meta.get("tags", [])
            category = _category_from_tags(tags, f.name)
            grouped[category].append({
                "name": meta.get("name", f.stem),
                "description": meta.get("description", ""),
                "file": str(f.name),
                "tags": tags,
                "functions": [fn.get("name","") for fn in meta.get("design_spec", {}).get("functions", [])],
            })
            total += 1
        except Exception as e:
            errors += 1

    print(f"[扫描] 共 {total} 个 skill，{len(grouped)} 个分类，{errors} 个解析错误")
    return grouped

def build_plans(grouped: Dict[str, List[dict]]) -> List[dict]:
    """将分组转换为推演计划列表"""
    plans = []
    for category, skills in sorted(grouped.items(), key=lambda x: (-len(x[1]), x[0])):
        count = len(skills)
        # 拼接技能摘要（最多展示前15个）
        preview = skills[:15]
        skill_lines = "\n".join(
            f"  • {s['name']}: {s['description'][:60]}{'…' if len(s['description'])>60 else ''}"
            for s in preview
        )
        if count > 15:
            skill_lines += f"\n  … 还有 {count-15} 个技能"

        # 所有函数名列表（用于目标验证）
        all_funcs = list({fn for s in skills for fn in s["functions"] if fn})[:20]
        func_str = "、".join(all_funcs) if all_funcs else "见技能文件"

        tags_all = list({t for s in skills for t in s["tags"]})[:8]

        plan = {
            "id": f"dp_skill_{hashlib.md5(category.encode()).hexdigest()[:8]}",
            "project_id": SKILL_PROJECT["id"],
            "title": f"[内化] {category}类技能 ({count}个)",
            "description": (
                f"内化目标: 本地模型完全掌握「{category}」类别的 {count} 个 skill。\n\n"
                f"技能清单:\n{skill_lines}\n\n"
                f"核心函数: {func_str}\n"
                f"Tags: {', '.join(tags_all)}"
            ),
            "priority": _get_priority(tags_all),
            "status": "queued",
            "ulds_laws": _get_ulds(tags_all),
            "surpass_strategies": "理解接口→本地复现→边界测试→融入认知格→零提示直接调用",
            "target_metrics": {
                "skill_count": count,
                "category": category,
                "掌握标准": "能不查文档直接调用核心函数，输出符合预期",
                "验证方式": "Ollama 本地调用 + 单元测试通过",
                "目标掌握率": "100%",
            },
            "estimated_rounds": max(3, min(count // 5, 20)),
            "model_preference": "ollama_local",
        }
        plans.append(plan)

    # 按优先级排序
    pri_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    plans.sort(key=lambda p: (pri_order.get(p["priority"], 2), -p["target_metrics"]["skill_count"]))
    return plans

def import_to_db(plans: List[dict], db: DeductionDB, clear: bool = False) -> int:
    """写入推演计划，返回写入数量"""
    if clear:
        db.conn.execute(
            "DELETE FROM deduction_plans WHERE project_id=?", (SKILL_PROJECT["id"],)
        )
        db.conn.commit()
        print("[清空] 已删除旧 skill 推演计划")

    written = 0
    for plan in plans:
        db.add_plan(plan)
        written += 1

    return written

EXPORT_PATH = PROJECT_ROOT / "web" / "data" / "deduction_export.json"


def export_to_json(db: DeductionDB):
    """将 DeductionDB 全量数据导出到 web/data/deduction_export.json，
    供 CRM 前端 loadFromDB() 读取。"""
    projects = db.get_projects()
    # 修正 tags 字段（DB 存的是 JSON 字符串）
    for p in projects:
        if isinstance(p.get("tags"), str):
            try:
                p["tags"] = json.loads(p["tags"])
            except Exception:
                p["tags"] = []

    plans = db.get_plans()
    # 修正 target_metrics 字段
    for pl in plans:
        if isinstance(pl.get("target_metrics"), str):
            try:
                pl["target_metrics"] = json.loads(pl["target_metrics"])
            except Exception:
                pl["target_metrics"] = {}

    problems = db.get_problems()

    export = {
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "projects": projects,
        "deductions": plans,
        "problems": problems,
    }

    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2, default=str)

    print(f"[导出] {len(projects)} 个项目, {len(plans)} 条推演计划 → {EXPORT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="将 skill 库导入 CRM 待推演列表")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写入数据库")
    parser.add_argument("--clear", action="store_true", help="写入前先清空旧 skill 计划")
    parser.add_argument("--export-only", action="store_true", help="只导出 JSON，不扫描 skill")
    args = parser.parse_args()

    if args.export_only:
        db = DeductionDB()
        export_to_json(db)
        db.close()
        return

    skills_dir = PROJECT_ROOT / "workspace" / "skills"
    if not skills_dir.exists():
        print(f"[错误] 技能目录不存在: {skills_dir}")
        sys.exit(1)

    print(f"[开始] 扫描技能目录: {skills_dir}")
    grouped = scan_skills(skills_dir)
    plans = build_plans(grouped)

    print(f"\n[计划] 生成 {len(plans)} 条推演计划:")
    for p in plans[:10]:
        print(f"  [{p['priority'].upper():8s}] {p['title']}")
    if len(plans) > 10:
        print(f"  … 还有 {len(plans)-10} 条")

    if args.dry_run:
        print("\n[dry-run] 未写入数据库")
        return

    db = DeductionDB()

    # 确保专属项目存在
    db.upsert_project(SKILL_PROJECT)
    print(f"\n[项目] 已确保项目: {SKILL_PROJECT['name']}")

    written = import_to_db(plans, db, clear=args.clear)

    # 导出全量数据到 CRM 前端 JSON
    export_to_json(db)
    db.close()

    print(f"\n[完成] 写入 {written} 条推演计划，已刷新 CRM 数据文件")
    print(f"  打开 http://localhost:8890/crm.html 进入「待推演列表」查看")

if __name__ == "__main__":
    main()
