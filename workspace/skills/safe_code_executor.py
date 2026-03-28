#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe Code Executor — 解决 heredoc> 卡死问题的底层执行技能
==========================================================
问题根因:
  1. shell heredoc (<<'EOF') 在 subprocess/terminal 中经常卡在 heredoc> 提示
  2. python3 -c "code" 遇到引号嵌套、长代码时解析失败
  3. 管道 echo "code" | python3 遇到特殊字符时截断

解决方案:
  所有多行代码执行统一走 tempfile 模式:
    写入临时.py文件 → subprocess执行 → 捕获stdout/stderr → 清理临时文件

集成位置 (底层链路):
  - shell_executor.run_python()       → 替换为 safe_exec_python()
  - tool_controller.execute_python()  → 替换为 safe_exec_python()
  - coding_enhancer 代码验证          → 替换为 safe_exec_python()
  - 推演引擎的数据分析脚本           → 替换为 safe_exec_python()

作者: Zhao Dylan
日期: 2026-03-26
"""

import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SKILL_META = {
    "name": "safe_code_executor",
    "display_name": "安全代码执行器 (Anti-Heredoc)",
    "description": (
        "解决 heredoc> 卡死问题的底层代码执行技能。"
        "所有多行代码通过 tempfile 模式执行, 彻底避免 shell heredoc/引号嵌套/管道截断。"
    ),
    "tags": [
        "heredoc", "shell", "subprocess", "代码执行", "tempfile",
        "底层链路", "安全执行", "anti-heredoc",
    ],
    "capabilities": [
        "safe_exec_python: 安全执行Python代码(tempfile模式, 零heredoc)",
        "safe_exec_shell: 安全执行shell脚本(tempfile模式)",
        "safe_exec_analysis: 安全执行数据分析脚本(自动注入import)",
        "diagnose_heredoc: 诊断heredoc问题并给出修复建议",
    ],
    "version": "1.0",
    "status": "production",
    "truth_level": "L3_Capability",
}

# ==================== 核心: tempfile 执行模式 ====================

# heredoc问题的3种表现及对应的tempfile解法
HEREDOC_PROBLEM_PATTERNS = {
    "heredoc_hang": {
        "symptom": "终端卡在 heredoc> 提示符, 无法退出",
        "trigger": "python3 << 'PYEOF' 或 cat << EOF",
        "root_cause": "shell解析器等待结束标记, 但标记被转义/截断/丢失",
        "fix": "tempfile模式: 写入.py文件 → python3 file.py → 删除",
    },
    "quote_nesting": {
        "symptom": "SyntaxError 或命令被截断",
        "trigger": "python3 -c \"code with 'quotes' and \\\"escapes\\\"\"",
        "root_cause": "多层引号嵌套导致shell解析错误",
        "fix": "tempfile模式: 代码写入文件, 无需任何引号转义",
    },
    "pipe_truncation": {
        "symptom": "代码被截断, 只执行了一部分",
        "trigger": "echo \"long code\" | python3",
        "root_cause": "管道缓冲区限制 或 特殊字符($, `, !) 被shell展开",
        "fix": "tempfile模式: 代码完整写入文件, 无shell展开风险",
    },
}


def _find_python() -> str:
    """找到最佳Python解释器"""
    # 优先用venv
    venv_python = PROJECT_ROOT / "venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    # 其次用当前解释器
    return sys.executable


def safe_exec_python(
    code: str,
    cwd: Optional[str] = None,
    timeout: int = 60,
    env: Optional[Dict[str, str]] = None,
    description: str = "",
) -> Dict[str, Any]:
    """
    安全执行Python代码 — tempfile模式, 彻底避免heredoc问题

    核心流程:
      1. 将代码写入临时 .py 文件 (utf-8, 无需引号转义)
      2. subprocess.run(["python3", temp.py]) 执行
      3. 捕获 stdout + stderr
      4. 清理临时文件

    Args:
        code: Python代码字符串 (任意长度, 任意引号嵌套, 均安全)
        cwd: 工作目录
        timeout: 超时秒数
        env: 额外环境变量
        description: 执行说明 (用于日志)

    Returns:
        dict: {success, stdout, stderr, returncode, duration, temp_path}
    """
    if cwd is None:
        cwd = str(PROJECT_ROOT)

    python = _find_python()
    start = time.time()

    # 写入临时文件 (后缀.py, 不自动删除, 手动清理)
    fd, temp_path = tempfile.mkstemp(suffix=".py", prefix="safe_exec_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)

        # 构建环境变量
        run_env = {**os.environ}
        if env:
            run_env.update(env)
        # 确保PYTHONPATH包含项目根目录
        existing_pypath = run_env.get("PYTHONPATH", "")
        if str(PROJECT_ROOT) not in existing_pypath:
            run_env["PYTHONPATH"] = f"{PROJECT_ROOT}:{existing_pypath}" if existing_pypath else str(PROJECT_ROOT)

        # 执行 (无shell=True, 无heredoc, 无引号问题)
        result = subprocess.run(
            [python, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=run_env,
        )

        duration = round(time.time() - start, 3)

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:50000] if result.stdout else "",
            "stderr": result.stderr[:10000] if result.stderr else "",
            "returncode": result.returncode,
            "duration": duration,
            "temp_path": temp_path,
            "description": description,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"⚠ 执行超时 ({timeout}s)",
            "returncode": -1,
            "duration": timeout,
            "temp_path": temp_path,
            "description": description,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "duration": round(time.time() - start, 3),
            "temp_path": temp_path,
            "description": description,
        }
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def safe_exec_shell(
    script: str,
    cwd: Optional[str] = None,
    timeout: int = 30,
    shell: str = "/bin/bash",
) -> Dict[str, Any]:
    """
    安全执行shell脚本 — tempfile模式, 避免heredoc问题

    Args:
        script: shell脚本内容
        cwd: 工作目录
        timeout: 超时秒数
        shell: shell解释器路径
    """
    if cwd is None:
        cwd = str(PROJECT_ROOT)

    start = time.time()
    fd, temp_path = tempfile.mkstemp(suffix=".sh", prefix="safe_exec_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"#!/bin/bash\nset -e\n{script}")
        os.chmod(temp_path, 0o755)

        result = subprocess.run(
            [shell, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:50000] if result.stdout else "",
            "stderr": result.stderr[:10000] if result.stderr else "",
            "returncode": result.returncode,
            "duration": round(time.time() - start, 3),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False, "stdout": "", "stderr": f"⚠ 超时 ({timeout}s)",
            "returncode": -1, "duration": timeout,
        }
    except Exception as e:
        return {
            "success": False, "stdout": "", "stderr": str(e),
            "returncode": -1, "duration": round(time.time() - start, 3),
        }
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def safe_exec_analysis(
    code: str,
    data_path: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    安全执行数据分析脚本 — 自动注入常用import

    专为数据分析场景设计: 自动注入 json/re/os/sys/pathlib/collections,
    避免 heredoc 和引号问题。

    Args:
        code: 分析代码 (无需写import json等常用库)
        data_path: 数据文件路径 (自动注入为 DATA_PATH 变量)
        cwd: 工作目录
        timeout: 超时秒数
    """
    preamble = [
        "import json, re, os, sys, time",
        "from pathlib import Path",
        "from collections import Counter, defaultdict",
        "from datetime import datetime",
    ]
    if data_path:
        preamble.append(f'DATA_PATH = "{data_path}"')
    full_code = "\n".join(preamble) + "\n\n" + code

    return safe_exec_python(full_code, cwd=cwd, timeout=timeout, description="data_analysis")


# ==================== 诊断工具 ====================

def diagnose_heredoc(command: str) -> Dict[str, Any]:
    """
    诊断一条命令是否有heredoc风险, 并给出安全替代方案

    Args:
        command: 要诊断的shell命令

    Returns:
        dict: {has_risk, risk_type, original, safe_alternative, explanation}
    """
    risks = []

    # 检测 heredoc
    if "<<" in command:
        risks.append({
            "type": "heredoc_hang",
            "pattern": "<<",
            "explanation": "heredoc 在 subprocess/IDE终端中可能卡在 heredoc> 提示",
        })

    # 检测 python -c 长代码
    if "-c " in command and ("python" in command or "python3" in command):
        # 估算-c后代码长度
        idx = command.find("-c ")
        code_part = command[idx+3:]
        if len(code_part) > 200 or code_part.count("'") > 4 or code_part.count('"') > 4:
            risks.append({
                "type": "quote_nesting",
                "pattern": "python -c (long/complex)",
                "explanation": "长代码或多层引号嵌套导致shell解析失败",
            })

    # 检测 echo | python 管道
    if "echo" in command and "|" in command and "python" in command:
        risks.append({
            "type": "pipe_truncation",
            "pattern": "echo ... | python",
            "explanation": "管道中的特殊字符($, `, !)被shell展开或截断",
        })

    if not risks:
        return {"has_risk": False, "original": command, "safe_alternative": command}

    # 生成安全替代方案
    safe_alt = f"""# 安全替代方案: 使用 safe_code_executor
from workspace.skills.safe_code_executor import safe_exec_python

code = '''
<your_code_here>
'''
result = safe_exec_python(code)
print(result['stdout'])
if not result['success']:
    print(f"Error: {{result['stderr']}}")"""

    return {
        "has_risk": True,
        "risk_count": len(risks),
        "risks": risks,
        "original": command,
        "safe_alternative": safe_alt,
    }


# ==================== 便捷接口: 替代常见heredoc用法 ====================

def python_eval(expression: str) -> str:
    """安全求值单个Python表达式 (替代 python3 -c 'print(expr)')"""
    result = safe_exec_python(f"print({expression})", timeout=10)
    return result["stdout"].strip() if result["success"] else f"Error: {result['stderr']}"


def json_query(json_path: str, query_code: str) -> Dict[str, Any]:
    """
    安全查询JSON文件 (替代 heredoc + python3 组合)

    示例:
        json_query("/path/to/data.json", '''
            print(f"Total: {len(data)}")
            for item in data[:5]:
                print(item)
        ''')

    query_code中可直接使用变量 `data` (已加载的JSON数据)
    """
    code = f"""
import json
with open("{json_path}", encoding="utf-8") as f:
    data = json.load(f)
if isinstance(data, dict) and "data" in data:
    data = data["data"]  # 自动解包 {{"data": [...]}} 格式
{query_code}
"""
    return safe_exec_python(code, timeout=60, description=f"json_query:{Path(json_path).name}")


# ==================== 入口 ====================

if __name__ == "__main__":
    print("=== Safe Code Executor — Anti-Heredoc 测试 ===\n")

    # 测试1: 基本执行
    r = safe_exec_python('print("Hello from tempfile mode!")\nprint(2**100)')
    print(f"Test 1 (basic): {'✅' if r['success'] else '❌'} {r['stdout'].strip()}")

    # 测试2: 引号嵌套 (heredoc/python -c 会失败的场景)
    r = safe_exec_python("""
msg = 'He said "hello" and she said \\'goodbye\\''
nested = {"key": "value with 'quotes' and \\"doubles\\""}
print(f"msg={msg}")
print(f"nested={nested}")
""")
    print(f"Test 2 (quotes): {'✅' if r['success'] else '❌'} {r['stdout'].strip()[:100]}")

    # 测试3: 数据分析 (自动import)
    r = safe_exec_analysis("""
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
c = Counter(x % 3 for x in data)
print(f"Counter: {dict(c)}")
print(f"Sum: {sum(data)}, Avg: {sum(data)/len(data):.1f}")
""")
    print(f"Test 3 (analysis): {'✅' if r['success'] else '❌'} {r['stdout'].strip()}")

    # 测试4: 诊断
    diag = diagnose_heredoc("python3 << 'PYEOF'\nimport json\nprint('hello')\nPYEOF")
    print(f"Test 4 (diagnose): {'✅' if diag['has_risk'] else '❌'} risks={diag.get('risk_count', 0)}")

    # 测试5: JSON查询
    test_json = tempfile.mktemp(suffix=".json")
    Path(test_json).write_text('{"data": [{"name": "A"}, {"name": "B"}]}')
    r = json_query(test_json, 'print(f"Items: {len(data)}")\nfor d in data: print(d["name"])')
    print(f"Test 5 (json_query): {'✅' if r['success'] else '❌'} {r['stdout'].strip()}")
    os.unlink(test_json)

    print(f"\n✅ 全部测试完成 — heredoc 问题已彻底解决")
