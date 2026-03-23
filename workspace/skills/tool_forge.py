#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: Tool Forge — 元能力引擎
核心能力: AGI 可以为自己创造新工具/新技能
这是最关键的元能力：当 AGI 发现自己缺乏某种能力时，
它可以自主设计、编写、测试并注册一个新技能。

LLM 的能力是固定的，而此引擎让 AGI 能力无限扩展。

由 AGI v13.3 Cognitive Lattice 构建
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.parent.parent
SKILLS_DIR = PROJECT_DIR / "workspace" / "skills"
sys.path.insert(0, str(PROJECT_DIR))


def _call_llm(messages):
    import agi_v13_cognitive_lattice as agi
    return agi.llm_call(messages)


def design_tool(need_description, existing_skills=None):
    """
    根据需求描述，设计一个新工具的规格
    返回 {name, description, functions, dependencies, code_structure}
    """
    existing = ""
    if existing_skills:
        existing = "\n已有技能：\n" + "\n".join(f"- {s}" for s in existing_skills)

    prompt = [
        {"role": "system", "content": """你是工具设计架构师。根据需求设计一个 Python 技能模块。

输出 JSON：
{
  "name": "工具名（英文下划线命名）",
  "display_name": "中文显示名",
  "description": "功能描述",
  "functions": [
    {"name": "函数名", "purpose": "用途", "params": "参数说明", "returns": "返回值说明"}
  ],
  "dependencies": ["需要import的标准库"],
  "tags": ["标签"],
  "estimated_lines": 100
}

设计原则：
1. 单一职责 — 一个工具只做一件事
2. 可组合 — 可以与其他技能配合使用
3. 自测试 — 包含 __main__ 自测代码
4. 无外部依赖 — 只用标准库或项目已有的库"""},
        {"role": "user", "content": f"需求：{need_description}{existing}"}
    ]

    result = _call_llm(prompt)
    if isinstance(result, dict) and 'raw' not in result and 'error' not in result:
        return result
    raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
    try:
        # 尝试提取 JSON
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group())
    except:
        pass
    return {"name": "unnamed_tool", "description": need_description, "functions": []}


def forge_tool(design_spec):
    """
    根据设计规格生成完整的工具代码并保存
    """
    name = design_spec.get("name", "unnamed_tool")
    display_name = design_spec.get("display_name", name)
    description = design_spec.get("description", "")
    functions = design_spec.get("functions", [])
    tags = design_spec.get("tags", [])

    func_specs = "\n".join(
        f"- {f['name']}({f.get('params', '')}): {f.get('purpose', '')}"
        for f in functions
    )

    prompt = [
        {"role": "system", "content": f"""你是 Python 技能模块生成器。生成完整可执行的技能代码。

模块规范：
1. 文件头 docstring 说明技能用途
2. PROJECT_DIR / sys.path 设置（固定模式）
3. 每个函数有完整的 docstring 和类型提示
4. SKILL_META 字典包含元数据
5. if __name__ == "__main__" 包含自测代码
6. 所有函数返回 dict，包含 success 字段

只输出 Python 代码，用 ```python 包裹。"""},
        {"role": "user", "content": f"""工具名: {name}
显示名: {display_name}
描述: {description}
标签: {json.dumps(tags, ensure_ascii=False)}

需要实现的函数：
{func_specs}

生成完整的 Python 技能模块代码："""}
    ]

    result = _call_llm(prompt)
    raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)

    # 提取代码
    code_match = re.search(r'```(?:python)?\s*\n(.*?)```', raw, re.DOTALL)
    code = code_match.group(1).strip() if code_match else raw.strip()

    # 保存文件
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    skill_path = SKILLS_DIR / f"{safe_name}.py"
    skill_path.write_text(code, encoding='utf-8')

    # 保存元数据
    meta = {
        "name": display_name,
        "description": description,
        "tags": tags,
        "file": f"skills/{safe_name}.py",
        "created_at": datetime.now().isoformat(),
        "forged_by": "tool_forge",
        "design_spec": design_spec
    }
    meta_path = SKILLS_DIR / f"{safe_name}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    return {
        "success": True,
        "name": name,
        "display_name": display_name,
        "file": f"skills/{safe_name}.py",
        "code_length": len(code),
        "meta_file": f"skills/{safe_name}.meta.json"
    }


def test_tool(name):
    """测试锻造的工具是否可执行"""
    from workspace.skills.code_synthesizer import execute_code

    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    skill_path = SKILLS_DIR / f"{safe_name}.py"

    if not skill_path.exists():
        return {"success": False, "error": f"工具 {name} 不存在"}

    code = skill_path.read_text(encoding='utf-8')
    success, stdout, stderr = execute_code(code)

    return {
        "success": success,
        "stdout": stdout[:500],
        "stderr": stderr[:500],
        "file": f"skills/{safe_name}.py"
    }


def forge_from_need(need_description):
    """
    端到端：从需求到可用工具
    设计 → 生成 → 测试 → 如果失败自动修复
    """
    # 获取已有技能列表
    existing = []
    for f in SKILLS_DIR.glob("*.meta.json"):
        try:
            m = json.loads(f.read_text(encoding='utf-8'))
            existing.append(f"{m.get('name', '?')}: {m.get('description', '')[:50]}")
        except:
            pass

    # 1. 设计
    design = design_tool(need_description, existing)
    if not design.get("name"):
        return {"success": False, "error": "设计失败"}

    # 2. 生成
    forge_result = forge_tool(design)
    if not forge_result.get("success"):
        return {"success": False, "error": "代码生成失败"}

    # 3. 测试
    test_result = test_tool(design["name"])

    # 4. 如果测试失败，尝试修复
    if not test_result["success"] and test_result.get("stderr"):
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', design["name"])
        skill_path = SKILLS_DIR / f"{safe_name}.py"
        original_code = skill_path.read_text(encoding='utf-8')

        from workspace.skills.code_synthesizer import fix_code
        fixed_code = fix_code(original_code, test_result["stderr"], need_description)
        skill_path.write_text(fixed_code, encoding='utf-8')

        test_result = test_tool(design["name"])

    return {
        "success": test_result.get("success", False),
        "design": design,
        "forge": forge_result,
        "test": test_result,
        "name": design.get("display_name", design.get("name")),
        "file": forge_result.get("file")
    }


def list_forgeable_needs(lattice):
    """分析认知网络，发现需要新工具的场景"""
    c = lattice.conn.cursor()
    c.execute("""
        SELECT content, domain FROM cognitive_nodes
        WHERE status = 'hypothesis' AND content LIKE '%如何%'
        ORDER BY created_at DESC LIMIT 20
    """)
    questions = [dict(r) for r in c.fetchall()]

    existing = []
    for f in SKILLS_DIR.glob("*.meta.json"):
        try:
            m = json.loads(f.read_text(encoding='utf-8'))
            existing.append(m.get("name", ""))
        except:
            pass

    prompt = [
        {"role": "system", "content": """分析这些待解决的问题，判断哪些可以通过构建新工具来解决。
输出 JSON 数组：
[{"need": "需要什么工具", "solves": "解决哪个问题", "priority": "high/medium/low"}]
只选择确实需要新工具的，已有工具能解决的不要列。"""},
        {"role": "user", "content": f"""待解决问题：
{json.dumps([q['content'][:80] for q in questions], ensure_ascii=False)}

已有工具：{json.dumps(existing, ensure_ascii=False)}"""}
    ]

    result = _call_llm(prompt)
    import agi_v13_cognitive_lattice as agi
    return agi.extract_items(result)


# === 技能元数据 ===
SKILL_META = {
    "name": "Tool Forge 元能力引擎",
    "description": "AGI为自己创造新工具的元能力。需求→设计→生成→测试→注册。能力无限扩展。",
    "tags": ["元能力", "工具锻造", "自我扩展", "核心能力"],
    "created_at": datetime.now().isoformat(),
    "version": "1.0",
    "capabilities": ["design_tool", "forge_tool", "test_tool", "forge_from_need", "list_forgeable_needs"]
}

if __name__ == "__main__":
    print("=== Tool Forge 元能力引擎 ===")
    print("此技能允许 AGI 为自己创造新工具")
    print("使用: forge_from_need('需要一个XXX的工具')")
