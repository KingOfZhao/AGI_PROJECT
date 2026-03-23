#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: 代码合成与自我纠错引擎
核心能力: 生成代码 → 执行 → 检测错误 → 自动修复 → 循环直到通过
这是 AGI 超越静态 LLM 的第一个关键能力：LLM 只能生成一次代码，
而此引擎可以无限迭代修正直到代码真正可运行。

由 AGI v13.3 Cognitive Lattice 构建
"""

import sys
import os
import json
import subprocess
import tempfile
import re
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))

VENV_PYTHON = str(PROJECT_DIR / "venv" / "bin" / "python")
if not Path(VENV_PYTHON).exists():
    VENV_PYTHON = sys.executable

MAX_FIX_ITERATIONS = 5
EXEC_TIMEOUT = 30


def _call_llm(messages):
    """调用 LLM"""
    import agi_v13_cognitive_lattice as agi
    return agi.llm_call(messages)


def generate_code(task_description, language="python", context=""):
    """让 LLM 生成代码"""
    prompt = [
        {"role": "system", "content": f"""你是一个精准的{language}代码生成器。
要求：
1. 只输出可直接执行的代码，不要解释
2. 包含完整的 import 语句
3. 代码必须有 main 入口，且在 __name__ == "__main__" 下调用
4. 输出结果要 print 出来
5. 不要使用任何需要用户输入的代码（如 input()）
6. 用 ```python 和 ``` 包裹代码"""},
        {"role": "user", "content": f"任务：{task_description}\n{('上下文：' + context) if context else ''}"}
    ]
    result = _call_llm(prompt)
    raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
    # 提取代码块
    code_match = re.search(r'```(?:python)?\s*\n(.*?)```', raw, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    # 如果没有代码块标记，尝试整段作为代码
    lines = raw.strip().split('\n')
    code_lines = [l for l in lines if not l.startswith('#') or l.startswith('#!') or l.startswith('# -*-')]
    if any('def ' in l or 'import ' in l or 'print(' in l for l in code_lines):
        return raw.strip()
    return raw.strip()


def execute_code(code, timeout=EXEC_TIMEOUT):
    """安全执行 Python 代码，返回 (success, stdout, stderr)"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=str(PROJECT_DIR / 'workspace')) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [VENV_PYTHON, tmp_path],
            capture_output=True, text=True,
            timeout=timeout,
            cwd=str(PROJECT_DIR / 'workspace')
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"执行超时 ({timeout}s)"
    except Exception as e:
        return False, "", str(e)
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def fix_code(code, error_msg, task_description):
    """让 LLM 修复代码错误"""
    prompt = [
        {"role": "system", "content": """你是代码修复专家。分析错误并修复代码。
只输出修复后的完整代码，用 ```python 和 ``` 包裹。
不要解释，只给代码。"""},
        {"role": "user", "content": f"""原始任务：{task_description}

当前代码：
```python
{code}
```

执行错误：
{error_msg}

请修复代码："""}
    ]
    result = _call_llm(prompt)
    raw = result.get('raw', str(result)) if isinstance(result, dict) else str(result)
    code_match = re.search(r'```(?:python)?\s*\n(.*?)```', raw, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    return raw.strip()


def synthesize_and_verify(task_description, language="python", context="", save_path=None):
    """
    核心函数：生成代码 → 执行 → 如果失败则修复 → 循环直到成功
    返回 {success, code, output, iterations, history}
    """
    history = []
    code = generate_code(task_description, language, context)
    
    for i in range(MAX_FIX_ITERATIONS):
        iteration = {"attempt": i + 1, "code_length": len(code)}
        
        success, stdout, stderr = execute_code(code)
        iteration["success"] = success
        iteration["stdout"] = stdout[:500]
        iteration["stderr"] = stderr[:500]
        
        if success:
            iteration["status"] = "PASS"
            history.append(iteration)
            
            # 保存成功的代码
            if save_path:
                save_full = PROJECT_DIR / 'workspace' / save_path
                save_full.parent.mkdir(parents=True, exist_ok=True)
                save_full.write_text(code, encoding='utf-8')
            
            return {
                "success": True,
                "code": code,
                "output": stdout,
                "iterations": i + 1,
                "history": history,
                "saved_to": save_path
            }
        
        iteration["status"] = "FAIL"
        history.append(iteration)
        
        # 自动修复
        code = fix_code(code, stderr or stdout, task_description)
    
    return {
        "success": False,
        "code": code,
        "output": stderr or stdout,
        "iterations": MAX_FIX_ITERATIONS,
        "history": history,
        "error": "达到最大修复次数仍未成功"
    }


def batch_synthesize(tasks):
    """批量合成多个代码任务"""
    results = []
    for task in tasks:
        desc = task if isinstance(task, str) else task.get('description', '')
        save = None if isinstance(task, str) else task.get('save_path')
        r = synthesize_and_verify(desc, save_path=save)
        results.append({"task": desc, **r})
    return results


# === 技能元数据 ===
SKILL_META = {
    "name": "代码合成与自我纠错引擎",
    "description": "生成代码→执行→检测错误→自动修复→循环验证。超越单次LLM生成的迭代式代码合成。",
    "tags": ["代码生成", "自我纠错", "迭代验证", "核心能力"],
    "created_at": datetime.now().isoformat(),
    "version": "1.0",
    "capabilities": ["generate_code", "execute_code", "fix_code", "synthesize_and_verify", "batch_synthesize"]
}

if __name__ == "__main__":
    print("=== 代码合成引擎自测 ===")
    result = synthesize_and_verify(
        "写一个函数计算给定列表中所有偶数的平方和，用 [1,2,3,4,5,6,7,8,9,10] 测试",
        save_path="self_test_even_squares.py"
    )
    print(f"成功: {result['success']}")
    print(f"迭代次数: {result['iterations']}")
    print(f"输出: {result['output'][:300]}")
    if result.get('saved_to'):
        print(f"已保存: {result['saved_to']}")
