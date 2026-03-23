#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: 软件工程师代理 — 让 AGI 具备完整的需求→代码实现能力
==========================================================

这是 AGI 最核心的代码能力模块，模拟 Cascade 处理需求的完整流程：

  Phase 1: 需求分析 — 自然语言 → 结构化需求规格
  Phase 2: 代码库理解 — 读取现有代码 → 提取架构/模式/惯例
  Phase 3: 方案设计 — 确定文件计划 + 技术选型 + 接口设计
  Phase 4: 代码生成 — 多文件生成 / 增量编辑（精准 old→new 替换）
  Phase 5: 测试验证 — 自动生成测试 → 执行 → 检查输出
  Phase 6: 调试修复 — 错误定位 → 根因分析 → 最小修复 → 回归验证

与 code_synthesizer 的区别:
  - code_synthesizer: 单文件脚本生成+自动纠错
  - software_engineer: 完整软件工程流程，多文件项目，增量编辑，架构感知
"""

import sys
import os
import json
import re
import subprocess
import tempfile
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

PROJECT_DIR = Path(__file__).parent.parent.parent
WORKSPACE_DIR = PROJECT_DIR / "workspace"
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(WORKSPACE_DIR))

VENV_PYTHON = str(PROJECT_DIR / "venv" / "bin" / "python")
if not Path(VENV_PYTHON).exists():
    VENV_PYTHON = sys.executable

EXEC_TIMEOUT = 30
MAX_DEBUG_ITERATIONS = 5


# ==================== LLM 调用 ====================

def _llm(messages, expect_json=False):
    """统一 LLM 调用"""
    import agi_v13_cognitive_lattice as agi
    result = agi.llm_call(messages)
    if expect_json:
        if isinstance(result, (list, dict)):
            return result
        raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
        # 尝试提取 JSON
        json_match = re.search(r'```(?:json)?\s*\n(.*?)```', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        try:
            return json.loads(raw)
        except:
            return {"raw": raw}
    raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
    return raw


def _llm_extract_code(raw_text, lang="python"):
    """从 LLM 输出中提取代码块"""
    pattern = rf'```(?:{lang})?\s*\n(.*?)```'
    match = re.search(pattern, raw_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 如果没有代码块标记，检查是否整段就是代码
    lines = raw_text.strip().split('\n')
    if any(kw in raw_text for kw in ['def ', 'class ', 'import ', 'from ']):
        # 去掉开头的非代码行
        start = 0
        for i, line in enumerate(lines):
            if any(line.strip().startswith(k) for k in ['#!', '# -*-', 'import', 'from', 'def', 'class', '#']):
                start = i
                break
        return '\n'.join(lines[start:]).strip()
    return raw_text.strip()


# ==================== Phase 1: 需求分析 ====================

def analyze_requirement(requirement: str, existing_context: str = "") -> Dict:
    """
    将自然语言需求转换为结构化规格。
    
    输出:
      - goal: 核心目标
      - features: 功能点列表
      - constraints: 约束条件
      - inputs_outputs: 输入输出定义
      - technical_hints: 技术选型建议
      - complexity: low/medium/high
      - needs_existing_code: bool
    """
    messages = [
        {"role": "system", "content": """你是一个需求分析专家。将用户的自然语言需求分解为结构化规格。

输出严格 JSON:
```json
{
  "goal": "核心目标（一句话）",
  "features": [
    {"id": "F1", "name": "功能名", "description": "描述", "priority": "must|should|nice"}
  ],
  "constraints": ["约束1", "约束2"],
  "inputs_outputs": {
    "inputs": ["输入描述"],
    "outputs": ["输出描述"]
  },
  "technical_hints": {
    "language": "python",
    "frameworks": [],
    "patterns": [],
    "data_structures": []
  },
  "complexity": "low|medium|high",
  "needs_existing_code": false,
  "file_estimate": 1
}
```

分析原则:
- 识别所有隐含需求（错误处理、边界情况）
- 明确输入输出格式
- 评估复杂度：low=单函数, medium=多函数/类, high=多文件/模块
- 如果用户要求修改现有代码，needs_existing_code=true"""},
        {"role": "user", "content": f"需求：{requirement}\n\n{('现有代码上下文：' + existing_context[:2000]) if existing_context else ''}"}
    ]
    result = _llm(messages, expect_json=True)
    if isinstance(result, dict) and "goal" in result:
        return result
    return {
        "goal": requirement[:100],
        "features": [{"id": "F1", "name": "主功能", "description": requirement, "priority": "must"}],
        "constraints": [],
        "inputs_outputs": {"inputs": [], "outputs": []},
        "technical_hints": {"language": "python", "frameworks": [], "patterns": [], "data_structures": []},
        "complexity": "medium",
        "needs_existing_code": False,
        "file_estimate": 1
    }


# ==================== Phase 2: 代码库理解 ====================

def understand_codebase(project_dir: str, requirement: str) -> Dict:
    """读取并理解现有代码库（如果有的话），返回相关上下文"""
    try:
        from skills.codebase_analyzer import (
            analyze_project, get_relevant_context, build_file_context_for_llm
        )
    except ImportError:
        return {"context": "", "files": [], "architecture": "未知"}

    project = analyze_project(project_dir)
    relevant = get_relevant_context(project_dir, requirement, max_files=5)

    return {
        "project_type": project.get("project_type", "unknown"),
        "stats": project.get("stats", {}),
        "patterns": project.get("patterns", []),
        "entry_points": project.get("entry_points", []),
        "relevant_files": relevant.get("selected_files", []),
        "context": relevant.get("combined_context", ""),
        "dependency_graph": project.get("dependency_graph", {}).get("graph", {}),
    }


# ==================== Phase 3: 方案设计 ====================

def design_solution(requirement: str, spec: Dict, codebase_context: Dict = None) -> Dict:
    """
    根据需求规格设计技术方案。
    
    输出:
      - architecture: 架构描述
      - file_plan: [{path, purpose, is_new, key_components}]
      - interface_design: 公共接口
      - implementation_order: 文件实现顺序
    """
    context_part = ""
    if codebase_context and codebase_context.get("context"):
        context_part = f"""
现有代码库:
- 项目类型: {codebase_context.get('project_type', '?')}
- 相关文件: {codebase_context.get('relevant_files', [])}
- 代码模式: {codebase_context.get('patterns', [])}

已有代码摘要:
{codebase_context['context'][:3000]}
"""

    messages = [
        {"role": "system", "content": """你是软件架构师。根据需求规格设计技术方案。

输出严格 JSON:
```json
{
  "architecture": "架构描述（简洁）",
  "file_plan": [
    {
      "path": "相对文件路径",
      "purpose": "文件职责",
      "is_new": true,
      "is_edit": false,
      "key_components": ["类名/函数名"],
      "depends_on": ["依赖的其他文件路径"]
    }
  ],
  "interface_design": [
    {
      "name": "公共函数/类名",
      "signature": "函数签名",
      "description": "功能描述"
    }
  ],
  "implementation_order": ["文件路径按实现顺序"],
  "test_strategy": "测试策略描述"
}
```

设计原则:
- 遵循单一职责原则
- 如果复杂度为 low，使用单文件
- 如果需要修改现有文件，is_edit=true, is_new=false
- implementation_order 要考虑依赖关系（被依赖的先实现）
- 文件路径相对于 workspace 目录"""},
        {"role": "user", "content": f"""需求规格:
{json.dumps(spec, ensure_ascii=False, indent=2)}

{context_part}

请设计技术方案:"""}
    ]
    result = _llm(messages, expect_json=True)
    if isinstance(result, dict) and "file_plan" in result:
        return result
    # 回退到简单方案
    return {
        "architecture": "单文件实现",
        "file_plan": [{
            "path": "solution.py",
            "purpose": spec.get("goal", "实现需求"),
            "is_new": True,
            "is_edit": False,
            "key_components": [],
            "depends_on": []
        }],
        "interface_design": [],
        "implementation_order": ["solution.py"],
        "test_strategy": "单元测试 + 集成运行"
    }


# ==================== Phase 4: 代码生成 ====================

def generate_file_code(file_plan: Dict, requirement: str, spec: Dict,
                       existing_code: str = "", other_files_context: str = "") -> str:
    """为单个文件生成完整代码"""
    if file_plan.get("is_edit") and existing_code:
        return _generate_edit_patch(file_plan, requirement, existing_code, other_files_context)

    messages = [
        {"role": "system", "content": f"""你是一个精确的 Python 代码生成器。
为以下文件生成完整、可运行的代码。

要求:
1. 包含完整的 import 语句
2. 包含类型提示
3. 包含 docstring
4. 处理错误和边界情况
5. 代码必须可以直接运行
6. 遵循 PEP 8 风格
7. 只输出代码，用 ```python ``` 包裹
8. 如果有依赖其他文件，用正确的 import 路径

文件职责: {file_plan.get('purpose', '')}
关键组件: {file_plan.get('key_components', [])}"""},
        {"role": "user", "content": f"""需求: {requirement}

文件路径: {file_plan['path']}
职责: {file_plan.get('purpose', '')}

{('其他相关文件上下文:\n' + other_files_context[:2000]) if other_files_context else ''}

请生成此文件的完整代码:"""}
    ]
    raw = _llm(messages)
    return _llm_extract_code(raw)


def _generate_edit_patch(file_plan: Dict, requirement: str, existing_code: str,
                         other_context: str = "") -> str:
    """为现有文件生成增量编辑（精准替换）"""
    messages = [
        {"role": "system", "content": """你是代码编辑专家。对现有文件进行精准的增量编辑。

输出格式 — 一个 JSON 数组，每个元素是一次编辑操作:
```json
[
  {
    "action": "replace",
    "old_code": "要替换的原始代码（精确匹配，包含缩进）",
    "new_code": "替换后的新代码",
    "reason": "修改原因"
  },
  {
    "action": "insert_after",
    "anchor": "插入点之后的那行代码（精确匹配）",
    "new_code": "要插入的新代码",
    "reason": "插入原因"
  },
  {
    "action": "append",
    "new_code": "追加到文件末尾的代码",
    "reason": "追加原因"
  }
]
```

原则:
- 最小编辑：只改必须改的部分
- 保持原有代码风格和缩进
- 不要重写整个文件
- old_code 必须与文件中的代码完全匹配（包括空格和缩进）
- 如果需要添加 import，使用 insert_after 锚定到已有 import 后面"""},
        {"role": "user", "content": f"""需求: {requirement}

当前文件内容:
```python
{existing_code}
```

文件职责: {file_plan.get('purpose', '')}
{('其他上下文:\n' + other_context[:1000]) if other_context else ''}

请输出编辑操作:"""}
    ]
    result = _llm(messages, expect_json=True)
    if isinstance(result, list):
        return _apply_edits(existing_code, result)
    elif isinstance(result, dict) and "raw" in result:
        # 尝试从 raw 中提取
        raw = result["raw"]
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            try:
                edits = json.loads(json_match.group())
                return _apply_edits(existing_code, edits)
            except:
                pass
    # 如果编辑解析失败，回退到完整重写
    return _fallback_full_rewrite(file_plan, requirement, existing_code)


def _apply_edits(source: str, edits: list) -> str:
    """应用增量编辑操作到源代码"""
    result = source
    for edit in edits:
        action = edit.get("action", "replace")
        if action == "replace":
            old = edit.get("old_code", "")
            new = edit.get("new_code", "")
            if old and old in result:
                result = result.replace(old, new, 1)
        elif action == "insert_after":
            anchor = edit.get("anchor", "")
            new = edit.get("new_code", "")
            if anchor and anchor in result:
                result = result.replace(anchor, anchor + "\n" + new, 1)
        elif action == "append":
            new = edit.get("new_code", "")
            if new:
                result = result.rstrip() + "\n\n" + new + "\n"
    return result


def _fallback_full_rewrite(file_plan, requirement, existing_code):
    """增量编辑失败时回退到完整重写"""
    messages = [
        {"role": "system", "content": """根据需求重写整个文件。保留原有的好的部分，修改/添加需要的部分。
输出完整的可运行代码，用 ```python ``` 包裹。"""},
        {"role": "user", "content": f"""需求: {requirement}
文件职责: {file_plan.get('purpose', '')}

原始代码:
```python
{existing_code}
```

请输出修改后的完整代码:"""}
    ]
    raw = _llm(messages)
    return _llm_extract_code(raw)


def generate_all_files(solution_design: Dict, requirement: str, spec: Dict,
                       project_dir: str = None) -> List[Dict]:
    """按实现顺序生成所有文件"""
    generated = []
    generated_context = ""

    impl_order = solution_design.get("implementation_order",
                                     [f["path"] for f in solution_design.get("file_plan", [])])
    plan_map = {f["path"]: f for f in solution_design.get("file_plan", [])}

    for file_path in impl_order:
        file_plan = plan_map.get(file_path, {"path": file_path, "purpose": "", "is_new": True})

        # 读取现有代码（如果是编辑模式）
        existing_code = ""
        if file_plan.get("is_edit") and project_dir:
            full_path = Path(project_dir) / file_path
            if full_path.exists():
                try:
                    existing_code = full_path.read_text(encoding='utf-8', errors='replace')
                except:
                    pass

        code = generate_file_code(file_plan, requirement, spec,
                                  existing_code=existing_code,
                                  other_files_context=generated_context)

        generated.append({
            "path": file_path,
            "code": code,
            "is_new": file_plan.get("is_new", True),
            "is_edit": file_plan.get("is_edit", False),
            "purpose": file_plan.get("purpose", ""),
        })

        # 将已生成的文件加入上下文（紧凑格式）
        generated_context += f"\n\n--- {file_path} ---\n{code[:1500]}"

    return generated


# ==================== Phase 5: 测试验证 ====================

def generate_tests(generated_files: List[Dict], requirement: str) -> str:
    """为生成的代码自动生成测试"""
    code_context = ""
    for f in generated_files:
        code_context += f"\n\n# === {f['path']} ===\n{f['code'][:2000]}"

    messages = [
        {"role": "system", "content": """你是测试工程师。为给定的代码生成全面的测试。

要求:
1. 生成一个独立的测试脚本 test_solution.py
2. 不使用 pytest，使用简单的 assert + try/except
3. 测试正常路径 + 边界情况 + 错误处理
4. 每个测试函数打印 PASS 或 FAIL
5. 在 __main__ 中运行所有测试并统计结果
6. 导入被测模块时使用正确的相对路径
7. 只输出代码，用 ```python ``` 包裹"""},
        {"role": "user", "content": f"""需求: {requirement}

代码:
{code_context}

请生成测试代码:"""}
    ]
    raw = _llm(messages)
    return _llm_extract_code(raw)


def run_code(code: str, filepath: str = None, timeout: int = EXEC_TIMEOUT,
             cwd: str = None) -> Dict:
    """执行代码并返回结果"""
    if filepath:
        target = Path(filepath)
    else:
        target = Path(tempfile.mktemp(suffix='.py', dir=str(WORKSPACE_DIR)))
        target.write_text(code, encoding='utf-8')

    work_dir = cwd or str(WORKSPACE_DIR)

    try:
        result = subprocess.run(
            [VENV_PYTHON, str(target)],
            capture_output=True, text=True,
            timeout=timeout,
            cwd=work_dir,
            env={**os.environ, "PYTHONPATH": f"{PROJECT_DIR}:{WORKSPACE_DIR}"}
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:5000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": f"超时 ({timeout}s)", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}
    finally:
        if not filepath and target.exists():
            try:
                target.unlink()
            except:
                pass


# ==================== Phase 6: 调试修复 ====================

def diagnose_and_fix(code: str, error: str, requirement: str,
                     test_code: str = "", iteration: int = 0) -> Dict:
    """诊断错误并生成修复"""
    messages = [
        {"role": "system", "content": """你是资深调试专家。分析错误的根本原因，然后进行最小化修复。

步骤:
1. 分析错误信息，定位出错的行号和原因
2. 确定根本原因（不是表面症状）
3. 设计最小修复方案
4. 输出修复后的完整代码

输出 JSON:
```json
{
  "diagnosis": "错误根因分析",
  "root_cause": "根本原因（一句话）",
  "fix_strategy": "修复策略（一句话）",
  "fixed_code": "修复后的完整代码"
}
```"""},
        {"role": "user", "content": f"""需求: {requirement}
修复迭代: {iteration + 1}/{MAX_DEBUG_ITERATIONS}

代码:
```python
{code}
```

错误信息:
{error[:2000]}

{('测试代码:\n```python\n' + test_code[:1000] + '\n```') if test_code else ''}

请诊断并修复:"""}
    ]
    result = _llm(messages, expect_json=True)

    if isinstance(result, dict):
        fixed = result.get("fixed_code", "")
        if not fixed and "raw" in result:
            fixed = _llm_extract_code(result["raw"])
        if fixed:
            return {
                "diagnosis": result.get("diagnosis", ""),
                "root_cause": result.get("root_cause", ""),
                "fix_strategy": result.get("fix_strategy", ""),
                "fixed_code": fixed,
            }

    # 回退：直接让 LLM 输出修复后代码
    messages2 = [
        {"role": "system", "content": "修复以下代码的错误，只输出修复后的完整代码，用 ```python ``` 包裹。"},
        {"role": "user", "content": f"代码:\n```python\n{code}\n```\n\n错误:\n{error[:1500]}\n\n修复:"}
    ]
    raw = _llm(messages2)
    return {
        "diagnosis": "直接修复",
        "root_cause": error[:200],
        "fix_strategy": "代码重写修复",
        "fixed_code": _llm_extract_code(raw),
    }


# ==================== 主管线: 完整的需求→代码流程 ====================

def implement_requirement(requirement: str, project_dir: str = None,
                          save: bool = True, lattice=None) -> Dict:
    """
    完整的软件工程管线：需求 → 可运行代码
    
    这是 AGI 的核心能力入口，模拟 Cascade 的工作流。
    
    Args:
        requirement: 自然语言需求
        project_dir: 项目目录（如果需要读取现有代码）
        save: 是否保存生成的文件
        lattice: 认知网络实例（可选，用于注入产出）
        
    Returns:
        {success, files, test_result, iterations, phases}
    """
    phases = []
    work_dir = project_dir or str(WORKSPACE_DIR)

    # === Phase 1: 需求分析 ===
    _log("Phase 1: 需求分析")
    existing_context = ""
    if project_dir:
        codebase = understand_codebase(project_dir, requirement)
        existing_context = codebase.get("context", "")
    
    spec = analyze_requirement(requirement, existing_context)
    phases.append({
        "phase": "requirement_analysis",
        "result": {
            "goal": spec.get("goal", ""),
            "complexity": spec.get("complexity", "?"),
            "features": len(spec.get("features", [])),
            "file_estimate": spec.get("file_estimate", 1),
        }
    })
    _log(f"  需求分析完成: 复杂度={spec.get('complexity')}, 功能点={len(spec.get('features',[]))}")

    # === Phase 2: 代码库理解 ===
    codebase_ctx = None
    if spec.get("needs_existing_code") or project_dir:
        _log("Phase 2: 代码库理解")
        codebase_ctx = understand_codebase(work_dir, requirement)
        phases.append({
            "phase": "codebase_analysis",
            "result": {
                "project_type": codebase_ctx.get("project_type", "?"),
                "relevant_files": codebase_ctx.get("relevant_files", []),
            }
        })
        _log(f"  代码库分析完成: 类型={codebase_ctx.get('project_type')}, 相关文件={len(codebase_ctx.get('relevant_files',[]))}")
    else:
        _log("Phase 2: 跳过（新项目）")

    # === Phase 3: 方案设计 ===
    _log("Phase 3: 方案设计")
    design = design_solution(requirement, spec, codebase_ctx)
    phases.append({
        "phase": "solution_design",
        "result": {
            "architecture": design.get("architecture", ""),
            "files_planned": len(design.get("file_plan", [])),
            "implementation_order": design.get("implementation_order", []),
        }
    })
    _log(f"  方案设计完成: {len(design.get('file_plan',[]))} 个文件, 架构={design.get('architecture','?')[:50]}")

    # === Phase 4: 代码生成 ===
    _log("Phase 4: 代码生成")
    generated_files = generate_all_files(design, requirement, spec, project_dir=work_dir)
    phases.append({
        "phase": "code_generation",
        "result": {
            "files_generated": len(generated_files),
            "total_lines": sum(f["code"].count('\n') for f in generated_files),
        }
    })
    _log(f"  代码生成完成: {len(generated_files)} 个文件")

    # 保存文件
    saved_files = []
    if save:
        for f in generated_files:
            full_path = Path(work_dir) / f["path"]
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(f["code"], encoding='utf-8')
            saved_files.append(str(full_path))
            _log(f"  已保存: {f['path']}")

    # === Phase 5: 测试验证 ===
    _log("Phase 5: 测试验证")
    test_code = generate_tests(generated_files, requirement)

    test_result = run_code(test_code, cwd=work_dir)
    phases.append({
        "phase": "test_validation",
        "result": {
            "initial_success": test_result["success"],
            "stdout": test_result["stdout"][:500],
            "stderr": test_result["stderr"][:500],
        }
    })

    if test_result["success"]:
        _log(f"  测试通过！输出: {test_result['stdout'][:200]}")
    else:
        _log(f"  测试失败: {test_result['stderr'][:200]}")

    # === Phase 6: 调试修复（如果测试失败） ===
    debug_history = []
    if not test_result["success"]:
        _log("Phase 6: 调试修复")
        # 合并所有代码进行修复
        combined_code = "\n\n".join(
            f"# === {f['path']} ===\n{f['code']}" for f in generated_files
        )

        for iteration in range(MAX_DEBUG_ITERATIONS):
            error = test_result["stderr"] or test_result["stdout"]
            _log(f"  修复迭代 {iteration + 1}/{MAX_DEBUG_ITERATIONS}")

            fix = diagnose_and_fix(combined_code, error, requirement,
                                   test_code=test_code, iteration=iteration)
            debug_history.append({
                "iteration": iteration + 1,
                "diagnosis": fix.get("diagnosis", ""),
                "root_cause": fix.get("root_cause", ""),
            })

            fixed_code = fix.get("fixed_code", "")
            if not fixed_code:
                _log("  修复失败：未生成修复代码")
                break

            # 判断修复的是哪个文件
            if len(generated_files) == 1:
                generated_files[0]["code"] = fixed_code
                if save:
                    full_path = Path(work_dir) / generated_files[0]["path"]
                    full_path.write_text(fixed_code, encoding='utf-8')
            else:
                # 多文件情况：尝试拆分修复后的代码回各文件
                _redistribute_fixed_code(generated_files, fixed_code, work_dir, save)

            # 重新运行测试
            test_result = run_code(test_code, cwd=work_dir)
            if test_result["success"]:
                _log(f"  ✓ 修复成功！迭代 {iteration + 1} 次")
                break
            else:
                _log(f"  ✗ 仍然失败: {test_result['stderr'][:100]}")
                combined_code = "\n\n".join(
                    f"# === {f['path']} ===\n{f['code']}" for f in generated_files
                )

        phases.append({
            "phase": "debug_fix",
            "result": {
                "iterations": len(debug_history),
                "final_success": test_result["success"],
                "history": debug_history,
            }
        })

    # 保存测试文件
    if save and test_code:
        test_path = Path(work_dir) / "test_solution.py"
        test_path.write_text(test_code, encoding='utf-8')
        saved_files.append(str(test_path))

    # 注入认知网络
    if lattice and test_result.get("success"):
        _inject_to_lattice(lattice, requirement, spec, design, generated_files)

    return {
        "success": test_result.get("success", False),
        "requirement": requirement,
        "spec": spec,
        "design": {
            "architecture": design.get("architecture", ""),
            "file_plan": design.get("file_plan", []),
        },
        "files": [{"path": f["path"], "lines": f["code"].count('\n'),
                    "purpose": f.get("purpose", "")} for f in generated_files],
        "test_result": {
            "success": test_result.get("success", False),
            "stdout": test_result.get("stdout", "")[:1000],
        },
        "debug_iterations": len(debug_history),
        "phases": phases,
        "saved_files": saved_files,
    }


def _redistribute_fixed_code(generated_files, fixed_code, work_dir, save):
    """将修复后的合并代码重新分配回各文件"""
    for f in generated_files:
        marker = f"# === {f['path']} ==="
        idx = fixed_code.find(marker)
        if idx >= 0:
            start = idx + len(marker)
            # 找下一个文件标记
            next_marker = fixed_code.find("# === ", start + 1)
            if next_marker > 0:
                chunk = fixed_code[start:next_marker].strip()
            else:
                chunk = fixed_code[start:].strip()
            if chunk:
                f["code"] = chunk
                if save:
                    full_path = Path(work_dir) / f["path"]
                    full_path.write_text(chunk, encoding='utf-8')


def _inject_to_lattice(lattice, requirement, spec, design, generated_files):
    """将成功的实现注入认知网络"""
    try:
        # 注入需求节点
        lattice.add_node(
            f"[已实现需求] {spec.get('goal', requirement[:80])}",
            "实践产出", "proven", source="software_engineer", silent=True
        )
        # 注入架构决策
        arch = design.get("architecture", "")
        if arch:
            lattice.add_node(
                f"[架构决策] {arch[:200]}",
                "架构设计", "proven", source="software_engineer", silent=True
            )
        # 注入关键文件
        for f in generated_files[:3]:
            lattice.add_node(
                f"[代码产出] {f['path']}: {f.get('purpose', '')[:100]}",
                "实践产出", "proven", source="software_engineer", silent=True
            )
    except Exception:
        pass


def _log(msg):
    """日志输出"""
    try:
        from action_engine import _emit_step
        _emit_step("software_engineer", msg, "running")
    except:
        pass
    print(f"  [SWE] {msg}")


# ==================== 便捷函数 ====================

def quick_implement(requirement: str, save_path: str = None) -> Dict:
    """快捷实现：需求→单文件代码（适合简单任务）"""
    spec = analyze_requirement(requirement)
    if spec.get("complexity") == "high" or spec.get("file_estimate", 1) > 2:
        return implement_requirement(requirement, save=True)

    # 简单任务走快捷路径
    from skills.code_synthesizer import synthesize_and_verify
    return synthesize_and_verify(requirement, save_path=save_path)


def edit_existing_file(filepath: str, requirement: str) -> Dict:
    """编辑现有文件（增量修改）"""
    fpath = Path(filepath)
    if not fpath.exists():
        return {"success": False, "error": f"文件不存在: {filepath}"}

    existing_code = fpath.read_text(encoding='utf-8', errors='replace')
    file_plan = {
        "path": str(fpath.relative_to(WORKSPACE_DIR)) if str(fpath).startswith(str(WORKSPACE_DIR)) else fpath.name,
        "purpose": requirement,
        "is_new": False,
        "is_edit": True,
        "key_components": [],
    }

    new_code = generate_file_code(file_plan, requirement, {}, existing_code=existing_code)

    # 测试新代码
    test_result = run_code(new_code)
    if test_result["success"]:
        fpath.write_text(new_code, encoding='utf-8')
        return {
            "success": True,
            "path": str(fpath),
            "lines_before": existing_code.count('\n'),
            "lines_after": new_code.count('\n'),
            "test_output": test_result["stdout"][:500],
        }
    else:
        # 尝试修复
        fix = diagnose_and_fix(new_code, test_result["stderr"], requirement)
        fixed = fix.get("fixed_code", "")
        if fixed:
            test2 = run_code(fixed)
            if test2["success"]:
                fpath.write_text(fixed, encoding='utf-8')
                return {
                    "success": True,
                    "path": str(fpath),
                    "lines_before": existing_code.count('\n'),
                    "lines_after": fixed.count('\n'),
                    "test_output": test2["stdout"][:500],
                    "debug_fix": fix.get("diagnosis", ""),
                }
        return {
            "success": False,
            "error": test_result["stderr"][:500],
            "diagnosis": fix.get("diagnosis", ""),
        }


# ==================== 技能元数据 ====================

SKILL_META = {
    "name": "软件工程师代理",
    "description": "完整的需求→代码管线：需求分析→代码库理解→架构设计→多文件生成→测试验证→调试修复。模拟Cascade的工作流。",
    "tags": ["需求分析", "架构设计", "代码生成", "多文件", "调试修复", "核心能力"],
    "version": "1.0",
    "capabilities": [
        "analyze_requirement", "design_solution", "generate_all_files",
        "generate_tests", "diagnose_and_fix", "implement_requirement",
        "edit_existing_file", "quick_implement"
    ]
}

if __name__ == "__main__":
    print("=== 软件工程师代理自测 ===")
    result = implement_requirement(
        "创建一个通讯录管理系统，支持添加联系人(姓名+电话+邮箱)、按姓名搜索、列出所有联系人、删除联系人。"
        "数据保存在JSON文件中，程序运行时自动加载。提供命令行接口测试所有功能。"
    )
    print(f"\n成功: {result['success']}")
    print(f"文件: {[f['path'] for f in result['files']]}")
    print(f"调试迭代: {result['debug_iterations']}")
    for phase in result["phases"]:
        print(f"  {phase['phase']}: {phase['result']}")
