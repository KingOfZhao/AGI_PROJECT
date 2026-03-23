#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 编码能力增强模块
===========================
集成 pytest/coverage/bandit/ruff/cProfile/AST分析/代码审查 等工具，
作为 ToolController 的扩展工具集，系统性提升编码维度评分。

覆盖维度:
  - 19/20: 代码风格与命名规范 (ruff/black)
  - 23/24: OWASP安全扫描 (bandit)
  - 25/26/27: 测试生成与覆盖率 (pytest/coverage)
  - 16/18: 性能分析 (cProfile/memory_profiler)
  - 5/6: 多文件编辑/仓库理解 (AST分析)
  - 91: PR代码审查 (diff分析)
  - 93: 团队代码风格统一 (ruff/black/isort)
"""

import ast
import concurrent.futures
import json
import os
import re
import sqlite3 as _sqlite3
import subprocess
import sys
import time
import textwrap
import urllib.request
import urllib.error
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECT_ROOT = Path(__file__).parent


# ==================== 1. 代码风格检查与自动格式化 (维度19,20,93) ====================

def run_linter(code: str = "", file_path: str = "", fix: bool = False) -> Dict:
    """运行 ruff 代码检查器 (替代 flake8+pylint)"""
    target = file_path
    temp_file = None

    if code and not file_path:
        temp_file = PROJECT_ROOT / "workspace" / "outputs" / "_lint_temp.py"
        temp_file.write_text(code, encoding='utf-8')
        target = str(temp_file)

    if not target:
        return {"success": False, "error": "需要提供code或file_path"}

    try:
        cmd = ["ruff", "check", target, "--output-format=json"]
        if fix:
            cmd.append("--fix")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                cwd=str(PROJECT_ROOT))
        issues = []
        if result.stdout.strip():
            try:
                issues = json.loads(result.stdout)
            except json.JSONDecodeError:
                issues = [{"message": result.stdout[:500]}]

        # 也运行格式化检查
        fmt_result = subprocess.run(
            ["ruff", "format", "--check", "--diff", target],
            capture_output=True, text=True, timeout=15, cwd=str(PROJECT_ROOT))
        fmt_diff = fmt_result.stdout[:2000] if fmt_result.returncode != 0 else ""

        return {
            "success": True,
            "lint_issues": len(issues),
            "issues": issues[:20],
            "format_diff": fmt_diff,
            "needs_formatting": bool(fmt_diff),
            "summary": f"发现 {len(issues)} 个代码问题" + (", 需要格式化" if fmt_diff else ", 格式正确")
        }
    except FileNotFoundError:
        return {"success": False, "error": "ruff未安装. 运行: pip install ruff"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "检查超时"}
    finally:
        if temp_file and temp_file.exists():
            temp_file.unlink()


def auto_format(code: str = "", file_path: str = "") -> Dict:
    """自动格式化代码 (ruff format + isort)"""
    if code and not file_path:
        temp_file = PROJECT_ROOT / "workspace" / "outputs" / "_fmt_temp.py"
        temp_file.write_text(code, encoding='utf-8')
        file_path = str(temp_file)
    if not file_path:
        return {"success": False, "error": "需要提供code或file_path"}

    try:
        # isort (import排序)
        subprocess.run(["isort", file_path], capture_output=True, timeout=10)
        # ruff format
        subprocess.run(["ruff", "format", file_path], capture_output=True, timeout=10)
        formatted = Path(file_path).read_text(encoding='utf-8')
        return {"success": True, "formatted_code": formatted, "path": file_path}
    except FileNotFoundError:
        return {"success": False, "error": "ruff/isort未安装"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 2. 安全扫描 (维度23,24) ====================

def run_security_scan(code: str = "", file_path: str = "", project_dir: str = "") -> Dict:
    """运行 Bandit 安全扫描 (OWASP/SAST)"""
    target = file_path or project_dir
    temp_file = None

    if code and not target:
        temp_file = PROJECT_ROOT / "workspace" / "outputs" / "_sec_temp.py"
        temp_file.write_text(code, encoding='utf-8')
        target = str(temp_file)

    if not target:
        target = str(PROJECT_ROOT)

    try:
        cmd = ["bandit", "-r", target, "-f", "json", "-ll"]
        if os.path.isfile(target):
            cmd = ["bandit", target, "-f", "json", "-ll"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                                cwd=str(PROJECT_ROOT))
        report = {}
        if result.stdout.strip():
            try:
                report = json.loads(result.stdout)
            except json.JSONDecodeError:
                report = {"raw": result.stdout[:2000]}

        findings = report.get("results", [])
        metrics = report.get("metrics", {})

        severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in findings:
            sev = f.get("issue_severity", "LOW")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "success": True,
            "total_findings": len(findings),
            "severity": severity_counts,
            "findings": [
                {
                    "severity": f.get("issue_severity"),
                    "confidence": f.get("issue_confidence"),
                    "text": f.get("issue_text"),
                    "file": f.get("filename"),
                    "line": f.get("line_number"),
                    "cwe": f.get("issue_cwe", {}).get("id"),
                    "test_id": f.get("test_id"),
                }
                for f in findings[:20]
            ],
            "summary": f"安全扫描: {severity_counts['HIGH']}高/{severity_counts['MEDIUM']}中/{severity_counts['LOW']}低 风险"
        }
    except FileNotFoundError:
        return {"success": False, "error": "bandit未安装. 运行: pip install bandit"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "安全扫描超时"}
    finally:
        if temp_file and temp_file.exists():
            temp_file.unlink()


# ==================== 3. 测试运行与覆盖率 (维度25,26,27) ====================

def run_tests(test_path: str = "", file_path: str = "", verbose: bool = True) -> Dict:
    """运行 pytest 并收集覆盖率"""
    target = test_path or str(PROJECT_ROOT / "tests")

    try:
        cmd = [sys.executable, "-m", "pytest", target, "-v",
               "--tb=short", "--no-header", "-q"]
        if file_path:
            cmd.extend(["--cov=" + file_path, "--cov-report=term-missing"])
        else:
            cmd.extend(["--cov=.", "--cov-report=term-missing"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                cwd=str(PROJECT_ROOT))

        # 解析结果
        output = result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
        lines = output.split('\n')

        passed = failed = errors = 0
        for line in lines:
            if ' passed' in line:
                try:
                    passed = int(line.split(' passed')[0].strip().split()[-1])
                except (ValueError, IndexError):
                    pass
            if ' failed' in line:
                try:
                    failed = int(line.split(' failed')[0].strip().split()[-1])
                except (ValueError, IndexError):
                    pass
            if ' error' in line:
                try:
                    errors = int(line.split(' error')[0].strip().split()[-1])
                except (ValueError, IndexError):
                    pass

        return {
            "success": result.returncode == 0,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "output": output,
            "returncode": result.returncode,
            "summary": f"测试: {passed}通过, {failed}失败, {errors}错误"
        }
    except FileNotFoundError:
        return {"success": False, "error": "pytest未安装. 运行: pip install pytest pytest-cov"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "测试执行超时(120s)"}


def generate_test(code: str, function_name: str = "") -> Dict:
    """基于AST分析自动生成pytest测试用例框架"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"success": False, "error": f"代码语法错误: {e}"}

    tests = []
    imports = set()
    module_name = "_test_target"

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if function_name and node.name != function_name:
                continue
            fname = node.name
            args = [a.arg for a in node.args.args if a.arg != 'self']
            # 生成基本测试
            arg_values = ", ".join(["None" for _ in args])
            test_code = f"""def test_{fname}_basic():
    \"\"\"测试 {fname} 基本功能\"\"\"
    result = {fname}({arg_values})
    assert result is not None

def test_{fname}_edge_case():
    \"\"\"测试 {fname} 边界条件\"\"\"
    # TODO: 添加边界值测试
    pass

def test_{fname}_error_handling():
    \"\"\"测试 {fname} 异常处理\"\"\"
    import pytest
    # TODO: 测试异常输入
    # with pytest.raises(ValueError):
    #     {fname}(invalid_input)
    pass
"""
            tests.append(test_code)

        elif isinstance(node, ast.ClassDef):
            if function_name and node.name != function_name:
                continue
            cname = node.name
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
            fixture = f"""
import pytest

@pytest.fixture
def {cname.lower()}_instance():
    \"\"\"创建 {cname} 测试实例\"\"\"
    return {cname}()

"""
            method_tests = ""
            for m in methods[:10]:
                method_tests += f"""
def test_{cname}_{m}({cname.lower()}_instance):
    \"\"\"测试 {cname}.{m}\"\"\"
    result = {cname.lower()}_instance.{m}()
    assert result is not None
"""
            tests.append(fixture + method_tests)

    if not tests:
        return {"success": False, "error": "未找到可测试的函数或类"}

    test_file = f'''#!/usr/bin/env python3
"""自动生成的测试用例 — AGI v13.3 CodingEnhancer"""
import pytest
import sys
sys.path.insert(0, '.')

# TODO: 修改导入为实际模块名
# from module_name import *

{"".join(tests)}
'''
    return {
        "success": True,
        "test_code": test_file,
        "test_count": len(tests),
        "summary": f"生成了 {len(tests)} 组测试用例"
    }


# ==================== 4. 性能分析 (维度16,18) ====================

def run_profiler(code: str, profile_type: str = "cpu") -> Dict:
    """运行性能分析 (cProfile/memory)"""
    temp_file = PROJECT_ROOT / "workspace" / "outputs" / "_profile_temp.py"

    if profile_type == "cpu":
        wrapper = f"""
import cProfile
import pstats
import io

def _profiled_code():
{textwrap.indent(code, '    ')}

profiler = cProfile.Profile()
profiler.enable()
_profiled_code()
profiler.disable()

stream = io.StringIO()
stats = pstats.Stats(profiler, stream=stream)
stats.sort_stats('cumulative')
stats.print_stats(20)
print(stream.getvalue())
"""
    else:  # memory
        wrapper = f"""
import tracemalloc
tracemalloc.start()

{code}

snapshot = tracemalloc.take_snapshot()
stats = snapshot.statistics('lineno')
print("=== 内存使用 Top 10 ===")
for stat in stats[:10]:
    print(stat)
current, peak = tracemalloc.get_traced_memory()
print(f"\\n当前内存: {{current/1024:.1f}} KB")
print(f"峰值内存: {{peak/1024:.1f}} KB")
tracemalloc.stop()
"""

    temp_file.write_text(wrapper, encoding='utf-8')
    try:
        result = subprocess.run(
            [sys.executable, str(temp_file)],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT))
        return {
            "success": result.returncode == 0,
            "profile_type": profile_type,
            "output": result.stdout[-3000:],
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "summary": f"{'CPU' if profile_type == 'cpu' else '内存'}分析完成"
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "分析超时(30s)"}
    finally:
        if temp_file.exists():
            temp_file.unlink()


# ==================== 5. AST代码分析 (维度5,6,72,90) ====================

def analyze_code_structure(code: str = "", file_path: str = "") -> Dict:
    """AST分析代码结构: 函数/类/导入/复杂度/依赖"""
    if file_path and not code:
        try:
            code = Path(file_path).read_text(encoding='utf-8')
        except Exception as e:
            return {"success": False, "error": f"读取文件失败: {e}"}

    if not code:
        return {"success": False, "error": "需要提供code或file_path"}

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"success": False, "error": f"语法错误: {e}"}

    functions = []
    classes = []
    imports = []
    global_vars = []
    complexity_score = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # 计算圈复杂度(简化版)
            cc = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                      ast.With, ast.Assert, ast.BoolOp)):
                    cc += 1
                if isinstance(child, ast.BoolOp):
                    cc += len(child.values) - 1

            args = [a.arg for a in node.args.args]
            decorators = [ast.dump(d) for d in node.decorator_list] if node.decorator_list else []
            body_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0

            functions.append({
                "name": node.name,
                "args": args,
                "line": node.lineno,
                "body_lines": body_lines,
                "cyclomatic_complexity": cc,
                "has_docstring": (isinstance(node.body[0], ast.Expr) and
                                  isinstance(node.body[0].value, ast.Constant) and
                                  isinstance(node.body[0].value.value, str)) if node.body else False,
                "decorators": len(decorators),
            })
            complexity_score += cc

        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
                "method_count": len(methods),
                "bases": [ast.dump(b) for b in node.bases],
            })

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "alias": alias.asname, "type": "import"})
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({"module": f"{module}.{alias.name}", "alias": alias.asname, "type": "from"})

    # 代码质量指标
    total_lines = len(code.split('\n'))
    doc_ratio = sum(1 for f in functions if f["has_docstring"]) / max(len(functions), 1)
    high_complexity = [f for f in functions if f["cyclomatic_complexity"] > 10]

    quality_issues = []
    if doc_ratio < 0.5:
        quality_issues.append(f"文档覆盖率低: {doc_ratio:.0%} 函数有docstring")
    if high_complexity:
        quality_issues.append(f"{len(high_complexity)}个函数圈复杂度>10: {[f['name'] for f in high_complexity]}")
    for f in functions:
        if f["body_lines"] > 50:
            quality_issues.append(f"函数 {f['name']} 过长({f['body_lines']}行)")

    return {
        "success": True,
        "total_lines": total_lines,
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "function_count": len(functions),
        "class_count": len(classes),
        "import_count": len(imports),
        "total_complexity": complexity_score,
        "avg_complexity": round(complexity_score / max(len(functions), 1), 1),
        "docstring_ratio": round(doc_ratio, 2),
        "quality_issues": quality_issues,
        "summary": (f"代码分析: {total_lines}行, {len(functions)}函数, {len(classes)}类, "
                    f"平均复杂度{complexity_score / max(len(functions), 1):.1f}, "
                    f"文档率{doc_ratio:.0%}, {len(quality_issues)}个质量问题")
    }


def analyze_dependencies(project_dir: str = "") -> Dict:
    """分析项目文件依赖关系图"""
    root = Path(project_dir) if project_dir else PROJECT_ROOT
    dep_graph = {}
    file_list = []

    for py_file in root.glob("*.py"):
        if py_file.name.startswith('_') and py_file.name != '__init__.py':
            continue
        try:
            code = py_file.read_text(encoding='utf-8')
            tree = ast.parse(code)
        except (SyntaxError, UnicodeDecodeError):
            continue

        deps = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split('.')[0]
                    if (root / f"{mod}.py").exists():
                        deps.add(mod)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split('.')[0]
                    if (root / f"{mod}.py").exists():
                        deps.add(mod)

        name = py_file.stem
        dep_graph[name] = list(deps)
        file_list.append(name)

    # 检测循环依赖
    cycles = []
    for a in dep_graph:
        for b in dep_graph.get(a, []):
            if a in dep_graph.get(b, []):
                pair = tuple(sorted([a, b]))
                if pair not in cycles:
                    cycles.append(pair)

    return {
        "success": True,
        "files": file_list,
        "dependency_graph": dep_graph,
        "circular_dependencies": [list(c) for c in cycles],
        "summary": f"项目依赖: {len(file_list)}文件, {sum(len(v) for v in dep_graph.values())}条依赖, {len(cycles)}个循环依赖"
    }


# ==================== 6. 代码审查 (维度91) ====================

def code_review(code: str, context: str = "") -> Dict:
    """自动代码审查: 安全+风格+性能+最佳实践"""
    issues = []

    # 安全检查
    security_patterns = [
        ("eval(", "HIGH", "使用eval()有代码注入风险，考虑使用ast.literal_eval()"),
        ("exec(", "HIGH", "使用exec()有代码注入风险"),
        ("__import__", "MEDIUM", "动态导入可能引入不可预期模块"),
        ("pickle.load", "HIGH", "pickle反序列化有任意代码执行风险"),
        ("yaml.load(", "MEDIUM", "使用yaml.safe_load()替代yaml.load()"),
        ("subprocess.call(", "MEDIUM", "使用subprocess.run()替代,并设置shell=False"),
        ("os.system(", "HIGH", "使用subprocess.run()替代os.system(),避免shell注入"),
        ("password", "LOW", "检查是否有硬编码密码"),
        ("api_key", "LOW", "检查是否有硬编码API密钥"),
        ("SELECT.*FROM.*WHERE.*%s" , "HIGH", "SQL查询使用字符串格式化,有注入风险"),
    ]

    for pattern, severity, message in security_patterns:
        if pattern.lower() in code.lower():
            line_num = 0
            for i, line in enumerate(code.split('\n'), 1):
                if pattern.lower() in line.lower():
                    line_num = i
                    break
            issues.append({
                "type": "security",
                "severity": severity,
                "message": message,
                "line": line_num,
                "pattern": pattern,
            })

    # 代码质量检查
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if len(stripped) > 120:
            issues.append({"type": "style", "severity": "LOW",
                           "message": f"行过长({len(stripped)}字符>120)", "line": i})
        if 'TODO' in line or 'FIXME' in line or 'HACK' in line:
            issues.append({"type": "maintenance", "severity": "LOW",
                           "message": f"发现TODO/FIXME标记", "line": i})
        if line.strip().startswith('except:') or line.strip() == 'except Exception:':
            issues.append({"type": "quality", "severity": "MEDIUM",
                           "message": "过于宽泛的异常捕获,应指定具体异常类型", "line": i})

    # 函数复杂度检查
    try:
        structure = analyze_code_structure(code=code)
        for f in structure.get("functions", []):
            if f["cyclomatic_complexity"] > 15:
                issues.append({"type": "complexity", "severity": "HIGH",
                               "message": f"函数 {f['name']} 圈复杂度过高({f['cyclomatic_complexity']}),建议拆分",
                               "line": f["line"]})
            elif f["cyclomatic_complexity"] > 10:
                issues.append({"type": "complexity", "severity": "MEDIUM",
                               "message": f"函数 {f['name']} 圈复杂度较高({f['cyclomatic_complexity']})",
                               "line": f["line"]})
    except Exception:
        pass

    high = sum(1 for i in issues if i["severity"] == "HIGH")
    med = sum(1 for i in issues if i["severity"] == "MEDIUM")
    low = sum(1 for i in issues if i["severity"] == "LOW")

    # 评级
    if high > 0:
        grade = "C" if high > 3 else "B"
    elif med > 3:
        grade = "B"
    elif med > 0 or low > 5:
        grade = "A-"
    else:
        grade = "A"

    return {
        "success": True,
        "grade": grade,
        "total_issues": len(issues),
        "high": high, "medium": med, "low": low,
        "issues": sorted(issues, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[x["severity"]]),
        "summary": f"代码审查评级: {grade} ({high}高/{med}中/{low}低风险)"
    }


# ==================== 7. 浏览器自动化 (维度12) ====================

def run_browser_test(url: str, actions: List[Dict] = None, screenshot: bool = True) -> Dict:
    """Playwright浏览器自动化测试"""
    script = f"""
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        results = []

        try:
            await page.goto("{url}", timeout=15000)
            results.append({{"action": "navigate", "url": "{url}", "success": True,
                           "title": await page.title()}})
"""

    if actions:
        for act in actions:
            if act.get("type") == "click":
                script += f'            await page.click("{act["selector"]}")\n'
                script += f'            results.append({{"action": "click", "selector": "{act["selector"]}", "success": True}})\n'
            elif act.get("type") == "fill":
                script += f'            await page.fill("{act["selector"]}", "{act["value"]}")\n'
                script += f'            results.append({{"action": "fill", "selector": "{act["selector"]}", "success": True}})\n'
            elif act.get("type") == "wait":
                script += f'            await page.wait_for_selector("{act["selector"]}", timeout=5000)\n'
                script += f'            results.append({{"action": "wait", "selector": "{act["selector"]}", "success": True}})\n'

    if screenshot:
        ss_path = str(PROJECT_ROOT / "workspace" / "outputs" / "screenshot.png")
        script += f'            await page.screenshot(path="{ss_path}")\n'
        script += f'            results.append({{"action": "screenshot", "path": "{ss_path}", "success": True}})\n'

    script += """
        except Exception as e:
            results.append({"action": "error", "error": str(e), "success": False})
        finally:
            await browser.close()

        import json
        print(json.dumps(results, ensure_ascii=False))

asyncio.run(run())
"""

    temp_file = PROJECT_ROOT / "workspace" / "outputs" / "_browser_test.py"
    temp_file.write_text(script, encoding='utf-8')

    try:
        result = subprocess.run(
            [sys.executable, str(temp_file)],
            capture_output=True, text=True, timeout=30, cwd=str(PROJECT_ROOT))

        if result.returncode == 0 and result.stdout.strip():
            try:
                actions_result = json.loads(result.stdout)
                return {"success": True, "results": actions_result,
                        "summary": f"浏览器测试: {len(actions_result)}个操作完成"}
            except json.JSONDecodeError:
                return {"success": True, "output": result.stdout[:2000]}
        else:
            error = result.stderr[:1000] if result.stderr else "未知错误"
            if "playwright" in error.lower():
                return {"success": False, "error": "Playwright未安装. 运行: pip install playwright && playwright install chromium"}
            return {"success": False, "error": error}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "浏览器测试超时(30s)"}
    finally:
        if temp_file.exists():
            temp_file.unlink()


# ==================== 8. 技术债务分析 (维度89) ====================

def analyze_tech_debt(project_dir: str = "") -> Dict:
    """分析项目技术债务"""
    root = Path(project_dir) if project_dir else PROJECT_ROOT
    debt_items = []
    total_score = 0

    for py_file in root.glob("*.py"):
        if py_file.name.startswith('_'):
            continue
        try:
            code = py_file.read_text(encoding='utf-8')
            lines = code.split('\n')
        except (UnicodeDecodeError, PermissionError):
            continue

        # TODO/FIXME/HACK统计
        for i, line in enumerate(lines, 1):
            for marker in ['TODO', 'FIXME', 'HACK', 'XXX', 'WORKAROUND']:
                if marker in line:
                    debt_items.append({
                        "type": "todo_marker",
                        "file": py_file.name,
                        "line": i,
                        "marker": marker,
                        "text": line.strip()[:100],
                        "severity": "medium" if marker in ('FIXME', 'HACK') else "low",
                        "cost_hours": 1,
                    })
                    total_score += 2 if marker in ('FIXME', 'HACK') else 1

        # 代码复杂度检查
        try:
            structure = analyze_code_structure(code=code)
            for f in structure.get("functions", []):
                if f["cyclomatic_complexity"] > 15:
                    debt_items.append({
                        "type": "high_complexity",
                        "file": py_file.name,
                        "function": f["name"],
                        "complexity": f["cyclomatic_complexity"],
                        "severity": "high",
                        "cost_hours": 4,
                    })
                    total_score += 5
                if f["body_lines"] > 80:
                    debt_items.append({
                        "type": "long_function",
                        "file": py_file.name,
                        "function": f["name"],
                        "lines": f["body_lines"],
                        "severity": "medium",
                        "cost_hours": 2,
                    })
                    total_score += 3
        except Exception:
            pass

        # bare except检查
        bare_except_count = sum(1 for l in lines if l.strip().startswith('except:')
                                or l.strip() == 'except Exception:')
        if bare_except_count > 0:
            debt_items.append({
                "type": "bare_except",
                "file": py_file.name,
                "count": bare_except_count,
                "severity": "medium",
                "cost_hours": 1,
            })
            total_score += bare_except_count * 2

    total_cost = sum(d.get("cost_hours", 0) for d in debt_items)
    severity_map = {"high": 0, "medium": 0, "low": 0}
    for d in debt_items:
        severity_map[d.get("severity", "low")] += 1

    if total_score > 50:
        health = "CRITICAL"
    elif total_score > 30:
        health = "WARNING"
    elif total_score > 10:
        health = "FAIR"
    else:
        health = "GOOD"

    return {
        "success": True,
        "health": health,
        "total_score": total_score,
        "total_items": len(debt_items),
        "severity_counts": severity_map,
        "estimated_hours": total_cost,
        "items": sorted(debt_items, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x.get("severity", "low")]),
        "summary": f"技术债务: {health} (评分{total_score}, {len(debt_items)}项, 预计{total_cost}h修复)"
    }


# ==================== 11. 数据库Schema检查与迁移 (维度29) ====================

def inspect_db_schema(db_path: str = "") -> Dict:
    """检查SQLite数据库Schema,列出所有表/列/索引/外键,检测迁移问题"""
    if not db_path:
        db_path = str(PROJECT_ROOT / "memory.db")

    if not Path(db_path).exists():
        return {"success": False, "error": f"数据库不存在: {db_path}"}

    try:
        conn = _sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cursor.fetchall()]

        schema_info = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [{"name": r[1], "type": r[2], "notnull": bool(r[3]),
                        "default": r[4], "pk": bool(r[5])} for r in cursor.fetchall()]

            cursor.execute(f"PRAGMA index_list({table})")
            indexes = [{"name": r[1], "unique": bool(r[2])} for r in cursor.fetchall()]

            cursor.execute(f"PRAGMA foreign_key_list({table})")
            fks = [{"table": r[2], "from": r[3], "to": r[4]} for r in cursor.fetchall()]

            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]

            schema_info[table] = {
                "columns": columns,
                "indexes": indexes,
                "foreign_keys": fks,
                "row_count": row_count,
            }

        # 检测潜在问题
        issues = []
        for table, info in schema_info.items():
            if not info["indexes"]:
                if info["row_count"] > 1000:
                    issues.append(f"{table}: {info['row_count']}行但无索引,查询可能慢")
            for col in info["columns"]:
                if col["type"] == "" or col["type"] is None:
                    issues.append(f"{table}.{col['name']}: 未指定类型")

        conn.close()
        return {
            "success": True,
            "db_path": db_path,
            "tables": tables,
            "table_count": len(tables),
            "schema": schema_info,
            "issues": issues,
            "migration_ready": len(issues) == 0,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 12. 输出一致性检查 (维度67) ====================

def check_output_consistency(outputs: List[str]) -> Dict:
    """检查多次输出的一致性:格式/结构/关键信息是否稳定"""
    if not outputs or len(outputs) < 2:
        return {"success": False, "error": "需要至少2个输出进行一致性对比"}

    n = len(outputs)
    lengths = [len(o) for o in outputs]
    avg_len = sum(lengths) / n
    len_variance = sum((l - avg_len) ** 2 for l in lengths) / n

    # 结构一致性: 检查代码块/列表/标题的出现模式
    patterns = {
        "code_blocks": r"```",
        "bullet_lists": r"^[-*]\s",
        "numbered_lists": r"^\d+\.\s",
        "headers": r"^#+\s",
    }

    structure_scores = {}
    for name, pattern in patterns.items():
        counts = [len(re.findall(pattern, o, re.MULTILINE)) for o in outputs]
        if max(counts) > 0:
            consistency = 1.0 - (max(counts) - min(counts)) / max(max(counts), 1)
        else:
            consistency = 1.0
        structure_scores[name] = round(consistency, 2)

    # 关键词一致性: 提取每个输出的top关键词
    all_words = []
    for o in outputs:
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z_]\w+', o)
        all_words.append(Counter(words))

    if all_words:
        common_keys = set.intersection(*[set(c.keys()) for c in all_words]) if all_words else set()
        keyword_overlap = len(common_keys) / max(len(set.union(*[set(c.keys()) for c in all_words])), 1)
    else:
        keyword_overlap = 0.0

    overall = (
        sum(structure_scores.values()) / max(len(structure_scores), 1) * 0.5
        + keyword_overlap * 0.3
        + (1.0 - min(len_variance / max(avg_len ** 2, 1), 1.0)) * 0.2
    )

    return {
        "success": True,
        "sample_count": n,
        "avg_length": round(avg_len),
        "length_variance": round(len_variance, 1),
        "structure_scores": structure_scores,
        "keyword_overlap": round(keyword_overlap, 2),
        "overall_consistency": round(overall, 2),
        "rating": "A" if overall > 0.8 else "B" if overall > 0.6 else "C",
    }


# ==================== 13. 基础负载测试 (维度82) ====================

def run_load_test(url: str = "", concurrency: int = 5, requests_count: int = 20) -> Dict:
    """基础HTTP负载测试: 并发请求+延迟统计+错误率"""
    if not url:
        url = "http://127.0.0.1:5002/api/health"

    results = []
    errors = 0

    def _single_request(i):
        start = time.time()
        try:
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'AGI-LoadTest/1.0')
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                _ = resp.read()
            elapsed = time.time() - start
            return {"request_id": i, "status": status, "latency_ms": round(elapsed * 1000, 1), "error": None}
        except Exception as e:
            elapsed = time.time() - start
            return {"request_id": i, "status": 0, "latency_ms": round(elapsed * 1000, 1), "error": str(e)}

    start_all = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_single_request, i) for i in range(requests_count)]
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            results.append(r)
            if r["error"]:
                errors += 1

    total_time = time.time() - start_all
    latencies = [r["latency_ms"] for r in results if not r["error"]]

    if latencies:
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        avg_latency = sum(latencies) / len(latencies)
    else:
        p50 = p95 = p99 = avg_latency = 0

    rps = requests_count / total_time if total_time > 0 else 0

    return {
        "success": True,
        "url": url,
        "total_requests": requests_count,
        "concurrency": concurrency,
        "total_time_s": round(total_time, 2),
        "requests_per_second": round(rps, 1),
        "error_count": errors,
        "error_rate": round(errors / requests_count * 100, 1),
        "latency_ms": {
            "avg": round(avg_latency, 1),
            "p50": round(p50, 1),
            "p95": round(p95, 1),
            "p99": round(p99, 1),
        },
        "rating": "A" if errors == 0 and avg_latency < 200 else
                  "B" if errors / requests_count < 0.05 else "C",
    }


# ==================== 14. Token效率分析与压缩 (维度59) ====================

def analyze_token_efficiency(text: str, max_tokens: int = 8192) -> Dict:
    """分析文本token效率:估算token数、信息密度、压缩建议"""
    if not text:
        return {"success": False, "error": "需要提供文本"}

    # 粗估token: 中文≈1.5tok/字, 英文≈0.25tok/word
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    en_words = len(re.findall(r'[a-zA-Z]+', text))
    estimated_tokens = int(cn_chars * 1.5 + en_words * 1.3 + len(re.findall(r'[^\w\s]', text)) * 0.5)

    # 信息密度分析
    lines = text.split('\n')
    empty_lines = sum(1 for l in lines if not l.strip())
    comment_lines = sum(1 for l in lines if l.strip().startswith(('#', '//', '/*', '*')))
    code_lines = len(lines) - empty_lines - comment_lines

    # 重复内容检测
    seen_lines = set()
    duplicate_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped and stripped in seen_lines:
            duplicate_lines += 1
        seen_lines.add(stripped)

    # 压缩建议
    suggestions = []
    if empty_lines > len(lines) * 0.3:
        suggestions.append(f"空行过多({empty_lines}/{len(lines)}), 可压缩空行")
    if comment_lines > code_lines * 0.5 and code_lines > 0:
        suggestions.append(f"注释比例高({comment_lines}注释/{code_lines}代码), 可精简")
    if duplicate_lines > 3:
        suggestions.append(f"发现{duplicate_lines}行重复内容, 可去重")
    if estimated_tokens > max_tokens:
        suggestions.append(f"预估{estimated_tokens}tokens超出限制{max_tokens}, 需截断或分段")

    # 压缩后估算
    compressed_text = re.sub(r'\n{3,}', '\n\n', text)  # 压缩连续空行
    compressed_text = re.sub(r'[ \t]+\n', '\n', compressed_text)  # 去除行尾空格
    compressed_tokens = int(len(compressed_text) * estimated_tokens / max(len(text), 1))
    savings = estimated_tokens - compressed_tokens

    info_density = code_lines / max(len(lines), 1)

    return {
        "success": True,
        "estimated_tokens": estimated_tokens,
        "max_tokens": max_tokens,
        "utilization": round(estimated_tokens / max_tokens * 100, 1),
        "total_lines": len(lines),
        "code_lines": code_lines,
        "comment_lines": comment_lines,
        "empty_lines": empty_lines,
        "duplicate_lines": duplicate_lines,
        "info_density": round(info_density, 2),
        "compressed_tokens": compressed_tokens,
        "token_savings": savings,
        "savings_pct": round(savings / max(estimated_tokens, 1) * 100, 1),
        "suggestions": suggestions,
        "within_limit": estimated_tokens <= max_tokens,
    }


# ==================== 15. 需求→代码骨架 Pipeline (维度74) ====================

def requirement_to_skeleton(requirement: str, language: str = "python") -> Dict:
    """将自然语言需求转化为代码骨架:模块/类/函数/接口定义"""
    if not requirement:
        return {"success": False, "error": "需要提供需求描述"}

    language = language.lower().strip()

    # 关键词提取
    keywords = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z_]\w+', requirement)
    keyword_set = set(k.lower() for k in keywords if len(k) > 1)

    # 识别功能模块
    modules = []
    module_patterns = {
        "api": ["api", "接口", "端点", "endpoint", "rest", "graphql"],
        "database": ["数据库", "database", "db", "sql", "存储", "持久化", "表"],
        "auth": ["认证", "登录", "权限", "auth", "login", "token", "jwt"],
        "ui": ["界面", "前端", "ui", "页面", "组件", "component", "view"],
        "service": ["服务", "service", "业务", "逻辑", "处理"],
        "model": ["模型", "model", "实体", "entity", "schema"],
        "test": ["测试", "test", "验证", "断言"],
        "config": ["配置", "config", "设置", "环境"],
        "util": ["工具", "util", "helper", "辅助"],
    }

    req_lower = requirement.lower()
    for mod_name, patterns in module_patterns.items():
        if any(p in req_lower for p in patterns):
            modules.append(mod_name)

    if not modules:
        modules = ["main"]

    # 语言特定骨架模板
    skeletons = {}
    if language == "python":
        for mod in modules:
            skeleton = f'"""\n{mod} module - {requirement[:80]}\n"""\n'
            if mod == "api":
                skeleton += "from flask import Flask, jsonify, request\n\napp = Flask(__name__)\n\n\n@app.route('/api/v1/resource', methods=['GET'])\ndef list_resources():\n    \"\"\"TODO: 实现资源列表\"\"\"\n    raise NotImplementedError\n"
            elif mod == "database":
                skeleton += "import sqlite3\nfrom pathlib import Path\n\n\nclass Database:\n    def __init__(self, db_path: str):\n        self.conn = sqlite3.connect(db_path)\n        self._init_tables()\n\n    def _init_tables(self):\n        \"\"\"TODO: 创建表结构\"\"\"\n        raise NotImplementedError\n"
            elif mod == "auth":
                skeleton += "import hashlib\nimport secrets\n\n\nclass AuthService:\n    def login(self, username: str, password: str) -> dict:\n        \"\"\"TODO: 实现登录\"\"\"\n        raise NotImplementedError\n\n    def verify_token(self, token: str) -> bool:\n        \"\"\"TODO: 验证token\"\"\"\n        raise NotImplementedError\n"
            elif mod == "model":
                skeleton += "from dataclasses import dataclass\nfrom typing import Optional\n\n\n@dataclass\nclass BaseModel:\n    id: int\n    created_at: str = ''\n    updated_at: str = ''\n"
            elif mod == "test":
                skeleton += "import pytest\n\n\nclass TestMain:\n    def test_placeholder(self):\n        \"\"\"TODO: 实现测试\"\"\"\n        assert True\n"
            else:
                skeleton += f"class {mod.capitalize()}:\n    \"\"\"TODO: 实现{mod}模块\"\"\"\n\n    def run(self):\n        raise NotImplementedError\n"
            skeletons[f"{mod}.py"] = skeleton
    elif language in ("javascript", "typescript"):
        ext = "ts" if language == "typescript" else "js"
        for mod in modules:
            skeleton = f"// {mod} module - {requirement[:80]}\n"
            if mod == "api":
                skeleton += "import express from 'express';\n\nconst router = express.Router();\n\nrouter.get('/api/v1/resource', async (req, res) => {\n  // TODO: implement\n  res.json({ data: [] });\n});\n\nexport default router;\n"
            else:
                skeleton += f"export class {mod.capitalize()} {{\n  // TODO: implement\n  run(): void {{\n    throw new Error('Not implemented');\n  }}\n}}\n"
            skeletons[f"{mod}.{ext}"] = skeleton
    else:
        skeletons["main.txt"] = f"// {language} skeleton for: {requirement[:100]}\n// Modules: {', '.join(modules)}\n// TODO: implement"

    return {
        "success": True,
        "requirement": requirement[:200],
        "language": language,
        "detected_modules": modules,
        "keywords": list(keyword_set)[:20],
        "files": skeletons,
        "file_count": len(skeletons),
        "skeleton_summary": f"{len(modules)}个模块, {len(skeletons)}个文件骨架",
    }


# ==================== 16. 架构决策记录ADR生成 (维度75) ====================

def generate_adr(title: str, context: str = "", decision: str = "",
                 alternatives: List[str] = None) -> Dict:
    """生成Architecture Decision Record (ADR)"""
    if not title:
        return {"success": False, "error": "需要提供决策标题"}

    adr_number = int(time.time()) % 10000
    date = time.strftime("%Y-%m-%d")

    alternatives = alternatives or []
    alt_section = ""
    if alternatives:
        alt_section = "\n## 替代方案\n\n" + "\n".join(
            f"### 方案{i+1}: {alt}\n- **优势**: TODO\n- **劣势**: TODO\n" for i, alt in enumerate(alternatives)
        )

    adr_content = f"""# ADR-{adr_number:04d}: {title}

## 状态
- **状态**: 提议中 (Proposed)
- **日期**: {date}
- **决策者**: AGI System

## 上下文
{context or '描述问题背景和约束条件...'}

## 决策
{decision or '描述最终选择的方案...'}
{alt_section}
## 后果

### 正面影响
- TODO: 描述积极影响

### 负面影响
- TODO: 描述潜在风险

### 技术债务
- TODO: 描述引入的技术债务

## 参考
- [相关文档/讨论链接]
"""

    # 分析决策质量
    quality_checks = []
    if context:
        quality_checks.append("✅ 上下文已描述")
    else:
        quality_checks.append("⚠️ 缺少上下文描述")

    if decision:
        quality_checks.append("✅ 决策已明确")
    else:
        quality_checks.append("⚠️ 缺少决策描述")

    if alternatives:
        quality_checks.append(f"✅ {len(alternatives)}个替代方案")
    else:
        quality_checks.append("⚠️ 未列出替代方案")

    completeness = sum(1 for c in quality_checks if c.startswith("✅")) / len(quality_checks)

    return {
        "success": True,
        "adr_number": adr_number,
        "title": title,
        "content": adr_content,
        "quality_checks": quality_checks,
        "completeness": round(completeness, 2),
        "file_name": f"adr-{adr_number:04d}-{title.lower().replace(' ', '-')[:30]}.md",
    }


# ==================== 注册到ToolController ====================

CODING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_linter",
            "description": "运行ruff代码检查器,检查代码风格/命名/导入排序问题。支持自动修复。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要检查的Python代码"},
                    "file_path": {"type": "string", "description": "要检查的文件路径"},
                    "fix": {"type": "boolean", "description": "是否自动修复(默认false)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_security_scan",
            "description": "运行Bandit安全扫描(SAST),检测SQL注入/XSS/代码注入等OWASP漏洞。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要扫描的代码"},
                    "file_path": {"type": "string", "description": "要扫描的文件"},
                    "project_dir": {"type": "string", "description": "要扫描的项目目录"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "运行pytest测试并收集覆盖率报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {"type": "string", "description": "测试文件/目录路径"},
                    "file_path": {"type": "string", "description": "要计算覆盖率的源文件"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_code",
            "description": "AST分析代码结构: 函数/类/导入/圈复杂度/文档覆盖率/质量问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要分析的代码"},
                    "file_path": {"type": "string", "description": "要分析的文件路径"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_review",
            "description": "自动代码审查:安全+风格+性能+最佳实践,输出评级(A/B/C)和问题列表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要审查的代码"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_profiler",
            "description": "运行CPU/内存性能分析。profile_type: cpu(默认)或memory。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要分析的代码"},
                    "profile_type": {"type": "string", "enum": ["cpu", "memory"], "description": "分析类型"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_browser_test",
            "description": "Playwright浏览器自动化:导航/点击/填表/截图。需先安装playwright。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "目标URL"},
                    "actions": {"type": "array", "description": "操作序列[{type,selector,value}]"},
                    "screenshot": {"type": "boolean", "description": "是否截图(默认true)"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_test",
            "description": "基于AST分析自动生成pytest测试用例框架。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要生成测试的源代码"},
                    "function_name": {"type": "string", "description": "指定函数名(可选)"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_tech_debt",
            "description": "分析项目技术债务:TODO标记/高复杂度/长函数/bare except等。输出健康评级和修复建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "项目目录(默认当前项目)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_migration",
            "description": "跨语言代码迁移分析:类型系统/内存模型/范式差异/AST特征检测。生成迁移提示和注意事项。支持Python/JS/TS/Java/Go/Rust/C#/Swift/Kotlin。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要迁移的源代码"},
                    "source_lang": {"type": "string", "description": "源语言(python/javascript/java/go/rust/csharp/swift/kotlin)"},
                    "target_lang": {"type": "string", "description": "目标语言"}
                },
                "required": ["code", "source_lang", "target_lang"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_db_schema",
            "description": "检查SQLite数据库Schema:表/列/索引/外键/行数,检测无索引大表等迁移问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "db_path": {"type": "string", "description": "数据库文件路径(默认memory.db)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_output_consistency",
            "description": "检查多次LLM输出的一致性:格式结构/关键词重叠/长度方差。评级A/B/C。",
            "parameters": {
                "type": "object",
                "properties": {
                    "outputs": {"type": "array", "items": {"type": "string"}, "description": "多次输出的文本列表(至少2个)"}
                },
                "required": ["outputs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_load_test",
            "description": "基础HTTP负载测试:并发请求+延迟统计(p50/p95/p99)+错误率+RPS。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "目标URL(默认本地health端点)"},
                    "concurrency": {"type": "integer", "description": "并发数(默认5)"},
                    "requests_count": {"type": "integer", "description": "总请求数(默认20)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_token_efficiency",
            "description": "分析文本token效率:估算token数/信息密度/重复检测/压缩建议。用于优化prompt和上下文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要分析的文本"},
                    "max_tokens": {"type": "integer", "description": "最大token限制(默认8192)"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "requirement_to_skeleton",
            "description": "将自然语言需求转化为代码骨架:自动识别模块(api/db/auth/ui/service)+生成文件结构。支持Python/JS/TS。",
            "parameters": {
                "type": "object",
                "properties": {
                    "requirement": {"type": "string", "description": "自然语言需求描述"},
                    "language": {"type": "string", "description": "目标语言(python/javascript/typescript)"}
                },
                "required": ["requirement"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_adr",
            "description": "生成Architecture Decision Record:标准ADR格式(状态/上下文/决策/替代方案/后果)+质量检查。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "决策标题"},
                    "context": {"type": "string", "description": "问题背景"},
                    "decision": {"type": "string", "description": "最终决策"},
                    "alternatives": {"type": "array", "items": {"type": "string"}, "description": "替代方案列表"}
                },
                "required": ["title"]
            }
        }
    },
]

# ==================== 10. 跨语言代码迁移 (维度73) ====================

# 语言特征映射表 — 用于生成迁移提示
LANG_MIGRATION_MAP = {
    "python": {"typing": "dynamic", "memory": "gc", "paradigm": "multi", "pkg": "pip"},
    "javascript": {"typing": "dynamic", "memory": "gc", "paradigm": "multi", "pkg": "npm"},
    "typescript": {"typing": "static", "memory": "gc", "paradigm": "multi", "pkg": "npm"},
    "java": {"typing": "static", "memory": "gc", "paradigm": "oop", "pkg": "maven/gradle"},
    "go": {"typing": "static", "memory": "gc", "paradigm": "procedural+interface", "pkg": "go mod"},
    "rust": {"typing": "static", "memory": "ownership", "paradigm": "multi", "pkg": "cargo"},
    "csharp": {"typing": "static", "memory": "gc", "paradigm": "oop", "pkg": "nuget"},
    "swift": {"typing": "static", "memory": "arc", "paradigm": "multi", "pkg": "spm"},
    "kotlin": {"typing": "static", "memory": "gc", "paradigm": "multi", "pkg": "gradle"},
}

def analyze_migration(code: str, source_lang: str, target_lang: str) -> Dict:
    """分析跨语言代码迁移的关键差异和注意事项"""
    source_lang = source_lang.lower().strip()
    target_lang = target_lang.lower().strip()

    src_info = LANG_MIGRATION_MAP.get(source_lang, {})
    tgt_info = LANG_MIGRATION_MAP.get(target_lang, {})

    if not src_info:
        return {"success": False, "error": f"不支持的源语言: {source_lang}"}
    if not tgt_info:
        return {"success": False, "error": f"不支持的目标语言: {target_lang}"}

    warnings = []
    suggestions = []

    # 类型系统差异
    if src_info["typing"] != tgt_info["typing"]:
        if src_info["typing"] == "dynamic" and tgt_info["typing"] == "static":
            warnings.append(f"类型系统: {source_lang}(动态)→{target_lang}(静态) 需要显式类型声明")
            suggestions.append("为所有变量添加类型注解，推断不确定的类型用泛型/any")
        else:
            warnings.append(f"类型系统: {source_lang}(静态)→{target_lang}(动态) 可简化类型声明")

    # 内存模型差异
    if src_info["memory"] != tgt_info["memory"]:
        warnings.append(f"内存模型: {source_lang}({src_info['memory']})→{target_lang}({tgt_info['memory']})")
        if tgt_info["memory"] == "ownership":
            suggestions.append("Rust需要严格所有权管理: 引用(&)、可变引用(&mut)、生命周期标注")
        elif tgt_info["memory"] == "arc":
            suggestions.append("Swift ARC: 注意循环引用(weak/unowned)，无需手动释放")

    # 范式差异
    if src_info["paradigm"] != tgt_info["paradigm"]:
        warnings.append(f"编程范式: {source_lang}({src_info['paradigm']})→{target_lang}({tgt_info['paradigm']})")

    # AST分析源代码特征
    code_features = []
    if source_lang == "python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    code_features.append("async函数")
                elif isinstance(node, ast.ListComp):
                    code_features.append("列表推导式")
                elif isinstance(node, ast.With):
                    code_features.append("上下文管理器")
                elif isinstance(node, (ast.Try, ast.ExceptHandler)):
                    code_features.append("异常处理")
        except SyntaxError:
            pass

    if code_features:
        unique_features = list(set(code_features))
        suggestions.append(f"源代码特征需特殊处理: {', '.join(unique_features)}")

    # 生成迁移提示
    migration_prompt = f"""将以下{source_lang}代码迁移到{target_lang}:
注意事项:
{chr(10).join(f'- {w}' for w in warnings)}
建议:
{chr(10).join(f'- {s}' for s in suggestions)}
包管理: {src_info['pkg']} → {tgt_info['pkg']}

源代码:
```{source_lang}
{code[:3000]}
```

请生成等价的{target_lang}代码，保持相同的功能和接口。"""

    return {
        "success": True,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "warnings": warnings,
        "suggestions": suggestions,
        "code_features": list(set(code_features)) if code_features else [],
        "migration_prompt": migration_prompt,
        "pkg_migration": f"{src_info['pkg']} → {tgt_info['pkg']}",
    }


# 工具处理器映射
CODING_HANDLERS = {
    "run_linter": lambda args: run_linter(args.get("code", ""), args.get("file_path", ""), args.get("fix", False)),
    "run_security_scan": lambda args: run_security_scan(args.get("code", ""), args.get("file_path", ""), args.get("project_dir", "")),
    "run_tests": lambda args: run_tests(args.get("test_path", ""), args.get("file_path", "")),
    "analyze_code": lambda args: analyze_code_structure(args.get("code", ""), args.get("file_path", "")),
    "code_review": lambda args: code_review(args.get("code", "")),
    "run_profiler": lambda args: run_profiler(args.get("code", ""), args.get("profile_type", "cpu")),
    "run_browser_test": lambda args: run_browser_test(args.get("url", ""), args.get("actions"), args.get("screenshot", True)),
    "generate_test": lambda args: generate_test(args.get("code", ""), args.get("function_name", "")),
    "analyze_tech_debt": lambda args: analyze_tech_debt(args.get("project_dir", "")),
    "analyze_migration": lambda args: analyze_migration(args.get("code", ""), args.get("source_lang", ""), args.get("target_lang", "")),
    "inspect_db_schema": lambda args: inspect_db_schema(args.get("db_path", "")),
    "check_output_consistency": lambda args: check_output_consistency(args.get("outputs", [])),
    "run_load_test": lambda args: run_load_test(args.get("url", ""), args.get("concurrency", 5), args.get("requests_count", 20)),
    "analyze_token_efficiency": lambda args: analyze_token_efficiency(args.get("text", ""), args.get("max_tokens", 8192)),
    "requirement_to_skeleton": lambda args: requirement_to_skeleton(args.get("requirement", ""), args.get("language", "python")),
    "generate_adr": lambda args: generate_adr(args.get("title", ""), args.get("context", ""), args.get("decision", ""), args.get("alternatives", [])),
}
