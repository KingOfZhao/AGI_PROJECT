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


# ==================== 17. 长上下文分块与连贯性保持 (维度8) ====================

def chunk_code_context(code: str, max_chunk_tokens: int = 3000,
                       overlap_lines: int = 5) -> Dict:
    """将长代码分块,保持跨块连贯性(重叠行+符号索引)"""
    if not code:
        return {"success": False, "error": "需要提供代码"}

    lines = code.split('\n')
    total_lines = len(lines)

    # 估算每行token
    avg_tokens_per_line = max(sum(len(l) for l in lines) / max(total_lines, 1) * 0.4, 1)
    lines_per_chunk = max(int(max_chunk_tokens / avg_tokens_per_line), 10)

    chunks = []
    i = 0
    while i < total_lines:
        end = min(i + lines_per_chunk, total_lines)

        # 尝试在函数/类边界处分割
        if end < total_lines:
            for j in range(end, max(end - 20, i + 10), -1):
                stripped = lines[j].strip() if j < total_lines else ""
                if stripped.startswith(('def ', 'class ', 'async def ', 'function ',
                                        'export ', 'public ', 'private ', '}')):
                    end = j
                    break

        chunk_lines = lines[i:end]
        chunk_text = '\n'.join(chunk_lines)

        # 提取该块的符号(函数/类名)
        symbols = []
        for line in chunk_lines:
            stripped = line.strip()
            if stripped.startswith('def '):
                name = stripped.split('(')[0].replace('def ', '')
                symbols.append(f"func:{name}")
            elif stripped.startswith('class '):
                name = stripped.split('(')[0].split(':')[0].replace('class ', '')
                symbols.append(f"class:{name}")

        chunks.append({
            "chunk_id": len(chunks),
            "start_line": i + 1,
            "end_line": end,
            "line_count": end - i,
            "estimated_tokens": int(len(chunk_text) * 0.4),
            "symbols": symbols,
            "content": chunk_text,
        })

        # 下一块从overlap_lines前开始(保持连贯)
        i = max(end - overlap_lines, end) if end >= total_lines else end - overlap_lines

    # 生成跨块符号索引
    symbol_index = {}
    for chunk in chunks:
        for sym in chunk["symbols"]:
            if sym not in symbol_index:
                symbol_index[sym] = []
            symbol_index[sym].append(chunk["chunk_id"])

    return {
        "success": True,
        "total_lines": total_lines,
        "total_chunks": len(chunks),
        "max_chunk_tokens": max_chunk_tokens,
        "overlap_lines": overlap_lines,
        "chunks": [{"chunk_id": c["chunk_id"], "start_line": c["start_line"],
                     "end_line": c["end_line"], "line_count": c["line_count"],
                     "estimated_tokens": c["estimated_tokens"],
                     "symbols": c["symbols"]} for c in chunks],
        "symbol_index": symbol_index,
        "full_chunks": chunks,  # 含content
    }


# ==================== 18. 低代码→高代码模板扩展 (维度88) ====================

CODE_TEMPLATES = {
    "crud_api": {
        "description": "REST CRUD API (Flask)",
        "params": ["resource_name", "fields"],
        "template": '''from flask import Flask, jsonify, request

app = Flask(__name__)
_{resource_name}_store = []
_next_id = 1

@app.route('/api/{resource_name}', methods=['GET'])
def list_{resource_name}():
    return jsonify({resource_name}_store)

@app.route('/api/{resource_name}', methods=['POST'])
def create_{resource_name}():
    global _next_id
    data = request.json
    data['id'] = _next_id
    _next_id += 1
    _{resource_name}_store.append(data)
    return jsonify(data), 201

@app.route('/api/{resource_name}/<int:id>', methods=['GET'])
def get_{resource_name}(id):
    item = next((x for x in _{resource_name}_store if x['id'] == id), None)
    return jsonify(item) if item else ('', 404)

@app.route('/api/{resource_name}/<int:id>', methods=['PUT'])
def update_{resource_name}(id):
    item = next((x for x in _{resource_name}_store if x['id'] == id), None)
    if not item:
        return ('', 404)
    item.update(request.json)
    return jsonify(item)

@app.route('/api/{resource_name}/<int:id>', methods=['DELETE'])
def delete_{resource_name}(id):
    global _{resource_name}_store
    _{resource_name}_store = [x for x in _{resource_name}_store if x['id'] != id]
    return ('', 204)
''',
    },
    "cli_tool": {
        "description": "CLI工具骨架 (argparse)",
        "params": ["tool_name", "description"],
        "template": '''#!/usr/bin/env python3
"""
{tool_name} - {description}
"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='{description}')
    parser.add_argument('input', help='输入文件/参数')
    parser.add_argument('-o', '--output', help='输出路径')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    args = parser.parse_args()

    # TODO: 实现核心逻辑
    if args.verbose:
        print(f"Processing: {{args.input}}")

    print(f"{tool_name} completed.")

if __name__ == '__main__':
    main()
''',
    },
    "dataclass_model": {
        "description": "数据模型 (dataclass + validation)",
        "params": ["model_name", "fields"],
        "template": '''from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class {model_name}:
    id: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ''

    def validate(self) -> List[str]:
        errors = []
        if self.id < 0:
            errors.append("id must be non-negative")
        return errors

    def to_dict(self) -> dict:
        return {{k: v for k, v in self.__dict__.items()}}

    @classmethod
    def from_dict(cls, data: dict) -> '{model_name}':
        return cls(**{{k: v for k, v in data.items() if k in cls.__dataclass_fields__}})
''',
    },
    "test_suite": {
        "description": "测试套件骨架 (pytest)",
        "params": ["module_name"],
        "template": '''import pytest
from unittest.mock import MagicMock, patch

class Test{module_name}:
    """Tests for {module_name}"""

    @pytest.fixture
    def instance(self):
        """Create test instance"""
        # TODO: return instance
        return None

    def test_creation(self, instance):
        """Test basic creation"""
        assert instance is not None

    def test_happy_path(self, instance):
        """Test normal operation"""
        # TODO: implement
        pass

    def test_edge_case(self, instance):
        """Test edge cases"""
        # TODO: implement
        pass

    def test_error_handling(self, instance):
        """Test error conditions"""
        # TODO: implement
        pass
''',
    },
}


def expand_template(template_name: str, **params) -> Dict:
    """将低代码模板扩展为完整的生产级代码"""
    if template_name not in CODE_TEMPLATES:
        available = list(CODE_TEMPLATES.keys())
        return {"success": False, "error": f"未知模板: {template_name}", "available": available}

    tpl = CODE_TEMPLATES[template_name]
    code = tpl["template"]

    # 替换参数
    for key, value in params.items():
        code = code.replace('{' + key + '}', str(value))

    # 检查未替换的参数
    missing = re.findall(r'\{(\w+)\}', code)
    # 过滤掉Python f-string内的变量引用
    real_missing = [m for m in missing if m in tpl.get("params", [])]

    return {
        "success": True,
        "template_name": template_name,
        "description": tpl["description"],
        "params_used": params,
        "missing_params": real_missing,
        "code": code,
        "line_count": len(code.split('\n')),
        "ready": len(real_missing) == 0,
    }


# ==================== 19. GitHub Issue解析与任务分解 (维度92) ====================

def parse_github_issue(issue_text: str) -> Dict:
    """解析GitHub Issue文本,提取结构化任务信息"""
    if not issue_text:
        return {"success": False, "error": "需要提供Issue文本"}

    result = {
        "title": "",
        "type": "unknown",
        "priority": "medium",
        "labels": [],
        "steps_to_reproduce": [],
        "expected_behavior": "",
        "actual_behavior": "",
        "tasks": [],
        "code_refs": [],
        "affected_files": [],
    }

    lines = issue_text.strip().split('\n')

    # 提取标题(第一行或#开头)
    for line in lines:
        stripped = line.strip()
        if stripped:
            result["title"] = stripped.lstrip('#').strip()
            break

    text_lower = issue_text.lower()

    # 分类Issue类型
    if any(kw in text_lower for kw in ['bug', '错误', 'error', 'crash', '崩溃', 'fix', '修复']):
        result["type"] = "bug"
        result["labels"].append("bug")
    elif any(kw in text_lower for kw in ['feature', '功能', '新增', 'add', 'enhancement', '需求']):
        result["type"] = "feature"
        result["labels"].append("enhancement")
    elif any(kw in text_lower for kw in ['refactor', '重构', 'optimize', '优化', 'performance']):
        result["type"] = "improvement"
        result["labels"].append("improvement")
    elif any(kw in text_lower for kw in ['doc', '文档', 'readme', 'typo']):
        result["type"] = "documentation"
        result["labels"].append("documentation")

    # 优先级检测
    if any(kw in text_lower for kw in ['urgent', '紧急', 'critical', 'blocker', '严重']):
        result["priority"] = "high"
    elif any(kw in text_lower for kw in ['minor', '次要', 'low', 'nice to have']):
        result["priority"] = "low"

    # 提取代码引用
    code_blocks = re.findall(r'```[\w]*\n(.*?)```', issue_text, re.DOTALL)
    result["code_refs"] = [block.strip()[:200] for block in code_blocks]

    # 提取文件路径引用
    file_refs = re.findall(r'[`\s]([a-zA-Z_][\w/]*\.\w{1,5})[`\s,.]', issue_text)
    result["affected_files"] = list(set(file_refs))[:10]

    # 提取复现步骤
    in_steps = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'(steps|复现|重现|reproduce)', stripped, re.IGNORECASE):
            in_steps = True
            continue
        if in_steps:
            if stripped.startswith(('- ', '* ', '1.', '2.', '3.', '4.', '5.')):
                result["steps_to_reproduce"].append(stripped.lstrip('-*0123456789. '))
            elif stripped.startswith('#') or not stripped:
                in_steps = False

    # 提取期望/实际行为
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if any(kw in stripped for kw in ['expected', '期望', '应该']):
            if i + 1 < len(lines):
                result["expected_behavior"] = lines[i + 1].strip()
        elif any(kw in stripped for kw in ['actual', '实际', '但是']):
            if i + 1 < len(lines):
                result["actual_behavior"] = lines[i + 1].strip()

    # 生成任务分解
    if result["type"] == "bug":
        result["tasks"] = [
            {"step": 1, "action": "复现问题", "detail": "在本地环境复现Issue描述的问题"},
            {"step": 2, "action": "定位根因", "detail": f"检查相关文件: {', '.join(result['affected_files'][:3]) or 'TBD'}"},
            {"step": 3, "action": "编写修复", "detail": "修复根因代码"},
            {"step": 4, "action": "添加测试", "detail": "添加回归测试防止复现"},
            {"step": 5, "action": "验证修复", "detail": "运行全部测试确认无副作用"},
        ]
    elif result["type"] == "feature":
        result["tasks"] = [
            {"step": 1, "action": "需求分析", "detail": "明确功能边界和验收条件"},
            {"step": 2, "action": "技术设计", "detail": "选择实现方案,评估影响范围"},
            {"step": 3, "action": "代码实现", "detail": "实现核心功能"},
            {"step": 4, "action": "测试覆盖", "detail": "编写单元测试+集成测试"},
            {"step": 5, "action": "文档更新", "detail": "更新README和API文档"},
        ]
    else:
        result["tasks"] = [
            {"step": 1, "action": "分析Issue", "detail": "理解问题范围"},
            {"step": 2, "action": "实施修改", "detail": "执行必要的代码修改"},
            {"step": 3, "action": "验证结果", "detail": "确认修改达到预期"},
        ]

    result["success"] = True
    result["task_count"] = len(result["tasks"])
    return result


# ==================== 20. 类型检查与边界测试强化 (维度3/HumanEval) ====================

def enforce_type_hints(code: str) -> Dict:
    """分析代码类型注解覆盖率,生成缺失的类型提示建议"""
    if not code:
        return {"success": False, "error": "需要提供代码"}

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"success": False, "error": f"语法错误: {e}"}

    functions = []
    typed_funcs = 0
    total_funcs = 0
    suggestions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total_funcs += 1
            func_info = {
                "name": node.name,
                "has_return_type": node.returns is not None,
                "params_total": 0,
                "params_typed": 0,
                "missing_types": [],
            }

            for arg in node.args.args:
                if arg.arg == 'self' or arg.arg == 'cls':
                    continue
                func_info["params_total"] += 1
                if arg.annotation is not None:
                    func_info["params_typed"] += 1
                else:
                    func_info["missing_types"].append(arg.arg)

            if func_info["has_return_type"] and func_info["params_typed"] == func_info["params_total"]:
                typed_funcs += 1

            if func_info["missing_types"]:
                suggestions.append(f"{node.name}(): 缺少参数类型 → {', '.join(func_info['missing_types'])}")
            if not func_info["has_return_type"]:
                suggestions.append(f"{node.name}(): 缺少返回类型")

            functions.append(func_info)

    coverage = typed_funcs / max(total_funcs, 1)

    # 检测常见类型错误模式
    type_issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, ast.Is) and isinstance(node.comparators[0], ast.Constant):
                    if node.comparators[0].value is not None:
                        type_issues.append(f"Line {node.lineno}: 使用'is'比较非None常量,应用'=='")

    return {
        "success": True,
        "total_functions": total_funcs,
        "fully_typed": typed_funcs,
        "type_coverage": round(coverage * 100, 1),
        "suggestions": suggestions[:20],
        "type_issues": type_issues,
        "rating": "A" if coverage > 0.8 else "B" if coverage > 0.5 else "C",
    }


# ==================== 21. UI组件与设计系统 (维度38) ====================

UI_COMPONENT_LIBRARY = {
    "button": {
        "html": '<button class="btn {variant}" {attrs}>{label}</button>',
        "variants": ["btn-primary", "btn-secondary", "btn-danger", "btn-ghost"],
        "css": ".btn { padding: 0.5rem 1rem; border-radius: 0.375rem; font-weight: 500; cursor: pointer; transition: all 0.2s; }\n.btn-primary { background: #3b82f6; color: white; }\n.btn-primary:hover { background: #2563eb; }\n.btn-secondary { background: #6b7280; color: white; }\n.btn-danger { background: #ef4444; color: white; }\n.btn-ghost { background: transparent; border: 1px solid #d1d5db; }",
    },
    "card": {
        "html": '<div class="card {variant}">\n  <div class="card-header">{title}</div>\n  <div class="card-body">{content}</div>\n</div>',
        "variants": ["card-default", "card-bordered", "card-elevated"],
        "css": ".card { border-radius: 0.5rem; overflow: hidden; }\n.card-header { padding: 1rem; font-weight: 600; }\n.card-body { padding: 1rem; }\n.card-default { background: white; }\n.card-bordered { border: 1px solid #e5e7eb; }\n.card-elevated { box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }",
    },
    "input": {
        "html": '<div class="input-group">\n  <label class="input-label" for="{id}">{label}</label>\n  <input class="input {variant}" id="{id}" type="{type}" placeholder="{placeholder}" {attrs}/>\n</div>',
        "variants": ["input-default", "input-error", "input-success"],
        "css": ".input-group { display: flex; flex-direction: column; gap: 0.25rem; }\n.input-label { font-size: 0.875rem; font-weight: 500; }\n.input { padding: 0.5rem 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem; }\n.input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.3); }\n.input-error { border-color: #ef4444; }\n.input-success { border-color: #10b981; }",
    },
    "modal": {
        "html": '<div class="modal-overlay" id="{id}">\n  <div class="modal">\n    <div class="modal-header">\n      <h3>{title}</h3>\n      <button class="modal-close" onclick="this.closest(\'.modal-overlay\').style.display=\'none\'">&times;</button>\n    </div>\n    <div class="modal-body">{content}</div>\n    <div class="modal-footer">{actions}</div>\n  </div>\n</div>',
        "variants": ["modal-sm", "modal-md", "modal-lg"],
        "css": ".modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 50; }\n.modal { background: white; border-radius: 0.5rem; width: 90%; max-width: 32rem; }\n.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid #e5e7eb; }\n.modal-body { padding: 1rem; }\n.modal-footer { padding: 1rem; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 0.5rem; }\n.modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; }",
    },
}


def generate_ui_component(component_type: str, **params) -> Dict:
    """生成UI组件(HTML+CSS),支持多种变体"""
    if component_type not in UI_COMPONENT_LIBRARY:
        return {
            "success": False,
            "error": f"未知组件: {component_type}",
            "available": list(UI_COMPONENT_LIBRARY.keys()),
        }

    comp = UI_COMPONENT_LIBRARY[component_type]
    html = comp["html"]
    css = comp["css"]

    # 替换参数
    defaults = {"variant": comp["variants"][0], "label": "Button", "title": "Title",
                "content": "Content", "id": "comp-1", "type": "text",
                "placeholder": "", "attrs": "", "actions": ""}
    merged = {**defaults, **params}

    for key, value in merged.items():
        html = html.replace('{' + key + '}', str(value))

    return {
        "success": True,
        "component_type": component_type,
        "html": html,
        "css": css,
        "variants": comp["variants"],
        "params_used": {k: v for k, v in merged.items() if k in params},
    }


# ==================== 22. 代码风格学习与适配 (维度70) ====================

def learn_code_style(code: str) -> Dict:
    """分析代码风格特征:缩进/命名/引号/导入/文档风格"""
    if not code:
        return {"success": False, "error": "需要提供代码"}

    lines = code.split('\n')

    # 缩进风格
    indent_counts = {"spaces_2": 0, "spaces_4": 0, "tabs": 0}
    for line in lines:
        if line and not line.strip():
            continue
        leading = len(line) - len(line.lstrip())
        if leading > 0:
            if line[0] == '\t':
                indent_counts["tabs"] += 1
            elif leading % 4 == 0:
                indent_counts["spaces_4"] += 1
            elif leading % 2 == 0:
                indent_counts["spaces_2"] += 1

    indent_style = max(indent_counts, key=indent_counts.get) if any(indent_counts.values()) else "spaces_4"

    # 引号风格
    single_quotes = len(re.findall(r"'[^']*'", code))
    double_quotes = len(re.findall(r'"[^"]*"', code))
    quote_style = "single" if single_quotes > double_quotes else "double"

    # 命名风格
    names = re.findall(r'\bdef\s+(\w+)', code) + re.findall(r'\b(\w+)\s*=', code)
    snake_count = sum(1 for n in names if '_' in n and n.islower())
    camel_count = sum(1 for n in names if not '_' in n and any(c.isupper() for c in n[1:]))
    naming_style = "snake_case" if snake_count >= camel_count else "camelCase"

    # 导入风格
    imports = [l.strip() for l in lines if l.strip().startswith(('import ', 'from '))]
    has_grouped_imports = False
    prev_was_import = False
    for line in lines:
        stripped = line.strip()
        is_import = stripped.startswith(('import ', 'from '))
        if prev_was_import and not is_import and stripped == '':
            if any(l.strip().startswith(('import ', 'from ')) for l in lines[lines.index(line)+1:lines.index(line)+3] if lines.index(line)+1 < len(lines)):
                has_grouped_imports = True
                break
        prev_was_import = is_import

    # 文档风格
    has_docstrings = '"""' in code or "'''" in code
    has_comments = '#' in code
    doc_style = "docstring" if has_docstrings else "comments" if has_comments else "none"

    # 行长度统计
    line_lengths = [len(l) for l in lines if l.strip()]
    max_line = max(line_lengths) if line_lengths else 0
    avg_line = sum(line_lengths) / max(len(line_lengths), 1)

    style_profile = {
        "indent": indent_style,
        "quotes": quote_style,
        "naming": naming_style,
        "imports_grouped": has_grouped_imports,
        "doc_style": doc_style,
        "max_line_length": max_line,
        "avg_line_length": round(avg_line),
        "trailing_newline": code.endswith('\n'),
    }

    return {
        "success": True,
        "style_profile": style_profile,
        "total_lines": len(lines),
        "import_count": len(imports),
        "summary": f"风格: {indent_style}/{quote_style}/{naming_style}, 文档: {doc_style}, 最长行: {max_line}",
    }


# ==================== 23. 常用库API索引与补全 (维度4/BigCodeBench) ====================

STDLIB_API_INDEX = {
    "os": {"path.join": "str", "path.exists": "bool", "listdir": "List[str]", "makedirs": "None", "environ": "dict", "getcwd": "str", "remove": "None"},
    "json": {"loads": "Any", "dumps": "str", "load": "Any", "dump": "None"},
    "re": {"findall": "List[str]", "match": "Optional[Match]", "sub": "str", "search": "Optional[Match]", "compile": "Pattern", "split": "List[str]"},
    "pathlib": {"Path": "Path", "Path.read_text": "str", "Path.write_text": "int", "Path.exists": "bool", "Path.mkdir": "None", "Path.glob": "Generator"},
    "collections": {"defaultdict": "defaultdict", "Counter": "Counter", "OrderedDict": "OrderedDict", "deque": "deque", "namedtuple": "type"},
    "itertools": {"chain": "Iterator", "product": "Iterator", "combinations": "Iterator", "permutations": "Iterator", "groupby": "Iterator", "islice": "Iterator"},
    "functools": {"lru_cache": "Callable", "partial": "partial", "reduce": "Any", "wraps": "Callable", "cached_property": "property"},
    "typing": {"List": "type", "Dict": "type", "Optional": "type", "Union": "type", "Tuple": "type", "Any": "type", "Callable": "type"},
    "datetime": {"datetime.now": "datetime", "datetime.strftime": "str", "timedelta": "timedelta", "date.today": "date"},
    "sqlite3": {"connect": "Connection", "Connection.cursor": "Cursor", "Cursor.execute": "Cursor", "Cursor.fetchall": "List[tuple]"},
    "subprocess": {"run": "CompletedProcess", "Popen": "Popen", "check_output": "bytes", "PIPE": "int"},
    "hashlib": {"sha256": "hash", "md5": "hash", "sha1": "hash"},
    "requests": {"get": "Response", "post": "Response", "put": "Response", "delete": "Response", "Session": "Session"},
    "flask": {"Flask": "Flask", "jsonify": "Response", "request": "Request", "Blueprint": "Blueprint", "render_template": "str"},
    "pytest": {"fixture": "decorator", "mark.parametrize": "decorator", "raises": "context_manager", "approx": "ApproxBase"},
    "pandas": {"DataFrame": "DataFrame", "read_csv": "DataFrame", "read_json": "DataFrame", "Series": "Series", "concat": "DataFrame", "merge": "DataFrame"},
    "numpy": {"array": "ndarray", "zeros": "ndarray", "ones": "ndarray", "arange": "ndarray", "linspace": "ndarray", "reshape": "ndarray"},
    "logging": {"getLogger": "Logger", "basicConfig": "None", "debug": "None", "info": "None", "warning": "None", "error": "None", "FileHandler": "FileHandler"},
}


def lookup_api(module: str, function: str = "") -> Dict:
    """查询常用库API:返回函数签名、返回类型、使用示例"""
    if not module:
        return {"success": False, "error": "需要提供模块名", "available_modules": list(STDLIB_API_INDEX.keys())}

    module = module.lower().strip()
    if module not in STDLIB_API_INDEX:
        # 模糊匹配
        matches = [m for m in STDLIB_API_INDEX if module in m]
        if matches:
            return {"success": False, "error": f"未找到'{module}', 你是否想查询: {matches}"}
        return {"success": False, "error": f"未找到模块: {module}", "available_modules": list(STDLIB_API_INDEX.keys())}

    apis = STDLIB_API_INDEX[module]

    if function:
        function = function.strip()
        matching = {k: v for k, v in apis.items() if function.lower() in k.lower()}
        if not matching:
            return {"success": True, "module": module, "function": function, "found": False,
                    "available_functions": list(apis.keys())}
        return {"success": True, "module": module, "function": function, "found": True,
                "apis": matching, "count": len(matching)}

    return {
        "success": True,
        "module": module,
        "apis": apis,
        "count": len(apis),
        "functions": list(apis.keys()),
    }


# ==================== 24. 数据可视化代码生成 (维度49) ====================

CHART_TEMPLATES = {
    "line": {
        "description": "折线图 - 趋势变化",
        "code": '''import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot({x_data}, {y_data}, marker='o', linewidth=2, label='{label}')
ax.set_xlabel('{x_label}')
ax.set_ylabel('{y_label}')
ax.set_title('{title}')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('{output}')
plt.show()
''',
    },
    "bar": {
        "description": "柱状图 - 分类对比",
        "code": '''import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
ax.bar({categories}, {values}, color=colors[:len({categories})])
ax.set_xlabel('{x_label}')
ax.set_ylabel('{y_label}')
ax.set_title('{title}')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('{output}')
plt.show()
''',
    },
    "pie": {
        "description": "饼图 - 占比分析",
        "code": '''import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 8))
colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']
ax.pie({values}, labels={labels}, autopct='%1.1f%%', colors=colors[:len({values})],
       startangle=90, shadow=True)
ax.set_title('{title}')
plt.tight_layout()
plt.savefig('{output}')
plt.show()
''',
    },
    "scatter": {
        "description": "散点图 - 相关性分析",
        "code": '''import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter({x_data}, {y_data}, alpha=0.6, edgecolors='black', linewidth=0.5)
ax.set_xlabel('{x_label}')
ax.set_ylabel('{y_label}')
ax.set_title('{title}')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('{output}')
plt.show()
''',
    },
    "heatmap": {
        "description": "热力图 - 矩阵数据",
        "code": '''import matplotlib.pyplot as plt
import numpy as np

data = np.array({data})
fig, ax = plt.subplots(figsize=(10, 8))
im = ax.imshow(data, cmap='YlOrRd', aspect='auto')
fig.colorbar(im)
ax.set_title('{title}')
ax.set_xlabel('{x_label}')
ax.set_ylabel('{y_label}')
plt.tight_layout()
plt.savefig('{output}')
plt.show()
''',
    },
}


def generate_chart_code(chart_type: str, **params) -> Dict:
    """生成数据可视化代码(matplotlib)"""
    if chart_type not in CHART_TEMPLATES:
        return {"success": False, "error": f"未知图表类型: {chart_type}",
                "available": {k: v["description"] for k, v in CHART_TEMPLATES.items()}}

    tpl = CHART_TEMPLATES[chart_type]
    code = tpl["code"]

    defaults = {"title": "Chart", "x_label": "X", "y_label": "Y", "label": "data",
                "output": "chart.png", "x_data": "[1,2,3,4,5]", "y_data": "[10,20,15,25,30]",
                "categories": "['A','B','C','D']", "values": "[25,40,30,55]",
                "labels": "['A','B','C','D']", "data": "[[1,2],[3,4]]"}
    merged = {**defaults, **params}

    for key, value in merged.items():
        code = code.replace('{' + key + '}', str(value))

    return {
        "success": True,
        "chart_type": chart_type,
        "description": tpl["description"],
        "code": code,
        "params_used": {k: v for k, v in merged.items() if k in params},
        "line_count": len(code.split('\n')),
    }


# ==================== 25. 算法模板库与复杂度分析 (维度54) ====================

ALGORITHM_TEMPLATES = {
    "binary_search": {
        "name": "二分查找",
        "complexity": {"time": "O(log n)", "space": "O(1)"},
        "code": '''def binary_search(arr, target):
    """二分查找 - O(log n)"""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
''',
    },
    "bfs": {
        "name": "广度优先搜索",
        "complexity": {"time": "O(V+E)", "space": "O(V)"},
        "code": '''from collections import deque

def bfs(graph, start):
    """BFS - O(V+E)"""
    visited = set([start])
    queue = deque([start])
    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return result
''',
    },
    "dfs": {
        "name": "深度优先搜索",
        "complexity": {"time": "O(V+E)", "space": "O(V)"},
        "code": '''def dfs(graph, start, visited=None):
    """DFS - O(V+E)"""
    if visited is None:
        visited = set()
    visited.add(start)
    result = [start]
    for neighbor in graph.get(start, []):
        if neighbor not in visited:
            result.extend(dfs(graph, neighbor, visited))
    return result
''',
    },
    "dp_knapsack": {
        "name": "0-1背包",
        "complexity": {"time": "O(nW)", "space": "O(nW)"},
        "code": '''def knapsack(weights, values, capacity):
    """0-1背包 - O(nW)"""
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i-1][w]
            if weights[i-1] <= w:
                dp[i][w] = max(dp[i][w], dp[i-1][w-weights[i-1]] + values[i-1])
    return dp[n][capacity]
''',
    },
    "dijkstra": {
        "name": "Dijkstra最短路径",
        "complexity": {"time": "O((V+E)logV)", "space": "O(V)"},
        "code": '''import heapq

def dijkstra(graph, start):
    """Dijkstra - O((V+E)logV)"""
    dist = {start: 0}
    heap = [(0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float('inf')):
            continue
        for v, w in graph.get(u, []):
            nd = d + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist
''',
    },
    "merge_sort": {
        "name": "归并排序",
        "complexity": {"time": "O(n log n)", "space": "O(n)"},
        "code": '''def merge_sort(arr):
    """归并排序 - O(n log n)"""
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
''',
    },
    "trie": {
        "name": "字典树/前缀树",
        "complexity": {"time": "O(L) per op", "space": "O(N*L)"},
        "code": '''class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class Trie:
    """Trie - O(L) per operation"""
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True

    def search(self, word):
        node = self.root
        for ch in word:
            if ch not in node.children:
                return False
            node = node.children[ch]
        return node.is_end

    def starts_with(self, prefix):
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return False
            node = node.children[ch]
        return True
''',
    },
    "union_find": {
        "name": "并查集",
        "complexity": {"time": "O(α(n)) ≈ O(1)", "space": "O(n)"},
        "code": '''class UnionFind:
    """并查集 - 路径压缩+按秩合并"""
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        return True
''',
    },
}


def get_algorithm_template(algorithm: str) -> Dict:
    """获取算法模板:代码+复杂度分析"""
    if not algorithm:
        return {"success": False, "error": "需要提供算法名称",
                "available": {k: v["name"] for k, v in ALGORITHM_TEMPLATES.items()}}

    algorithm = algorithm.lower().strip().replace(' ', '_').replace('-', '_')

    if algorithm in ALGORITHM_TEMPLATES:
        tpl = ALGORITHM_TEMPLATES[algorithm]
        return {
            "success": True,
            "algorithm": algorithm,
            "name": tpl["name"],
            "complexity": tpl["complexity"],
            "code": tpl["code"],
            "line_count": len(tpl["code"].split('\n')),
        }

    # 模糊匹配
    matches = {k: v["name"] for k, v in ALGORITHM_TEMPLATES.items()
               if algorithm in k or algorithm in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{algorithm}'", "similar": matches}

    return {"success": False, "error": f"未找到算法: {algorithm}",
            "available": {k: v["name"] for k, v in ALGORITHM_TEMPLATES.items()}}


# ==================== 26. 数据科学Pipeline生成 (维度48) ====================

DS_PIPELINE_STEPS = {
    "load": {
        "csv": "df = pd.read_csv('{path}')",
        "json": "df = pd.read_json('{path}')",
        "excel": "df = pd.read_excel('{path}')",
        "sql": "df = pd.read_sql('{query}', conn)",
    },
    "clean": [
        "df = df.dropna(subset={columns})",
        "df = df.drop_duplicates()",
        "df = df.fillna(df.median(numeric_only=True))",
        "df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')",
    ],
    "transform": [
        "df['{col}_log'] = np.log1p(df['{col}'])",
        "df['{col}_normalized'] = (df['{col}'] - df['{col}'].mean()) / df['{col}'].std()",
        "df = pd.get_dummies(df, columns={cat_cols})",
    ],
    "feature": [
        "from sklearn.preprocessing import StandardScaler",
        "scaler = StandardScaler()",
        "X_scaled = scaler.fit_transform(X)",
    ],
    "split": "X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)",
    "evaluate": [
        "from sklearn.metrics import accuracy_score, classification_report",
        "y_pred = model.predict(X_test)",
        "print(classification_report(y_test, y_pred))",
    ],
}


def generate_ds_pipeline(task: str = "classification", data_format: str = "csv",
                         target_col: str = "target") -> Dict:
    """生成数据科学Pipeline代码(加载→清洗→特征→训练→评估)"""
    if not task:
        return {"success": False, "error": "需要提供任务类型(classification/regression/clustering)"}

    code_lines = [
        "import pandas as pd",
        "import numpy as np",
        "from sklearn.model_selection import train_test_split",
        "",
        "# === Step 1: 数据加载 ===",
    ]

    load_code = DS_PIPELINE_STEPS["load"].get(data_format, DS_PIPELINE_STEPS["load"]["csv"])
    code_lines.append(load_code.replace("{path}", "data.csv").replace("{query}", "SELECT * FROM table"))
    code_lines.append(f"print(f'数据形状: {{df.shape}}')")
    code_lines.append(f"print(df.head())")
    code_lines.append("")

    code_lines.append("# === Step 2: 数据清洗 ===")
    for step in DS_PIPELINE_STEPS["clean"]:
        code_lines.append(step.replace("{columns}", f"['{target_col}']"))
    code_lines.append(f"print(f'清洗后: {{df.shape}}')")
    code_lines.append("")

    code_lines.append("# === Step 3: 特征工程 ===")
    code_lines.append(f"X = df.drop(columns=['{target_col}'])")
    code_lines.append(f"y = df['{target_col}']")
    code_lines.append("# 数值列标准化")
    code_lines.append("numeric_cols = X.select_dtypes(include=[np.number]).columns")
    code_lines.append("X[numeric_cols] = (X[numeric_cols] - X[numeric_cols].mean()) / X[numeric_cols].std()")
    code_lines.append("")

    code_lines.append("# === Step 4: 数据分割 ===")
    code_lines.append(DS_PIPELINE_STEPS["split"])
    code_lines.append(f"print(f'训练集: {{X_train.shape}}, 测试集: {{X_test.shape}}')")
    code_lines.append("")

    code_lines.append("# === Step 5: 模型训练 ===")
    if task == "classification":
        code_lines.extend([
            "from sklearn.ensemble import RandomForestClassifier",
            "model = RandomForestClassifier(n_estimators=100, random_state=42)",
        ])
    elif task == "regression":
        code_lines.extend([
            "from sklearn.ensemble import RandomForestRegressor",
            "model = RandomForestRegressor(n_estimators=100, random_state=42)",
        ])
    else:
        code_lines.extend([
            "from sklearn.cluster import KMeans",
            "model = KMeans(n_clusters=3, random_state=42)",
        ])
    code_lines.append("model.fit(X_train, y_train)")
    code_lines.append("")

    code_lines.append("# === Step 6: 评估 ===")
    if task == "classification":
        code_lines.extend([
            "from sklearn.metrics import accuracy_score, classification_report",
            "y_pred = model.predict(X_test)",
            "print(f'准确率: {accuracy_score(y_test, y_pred):.4f}')",
            "print(classification_report(y_test, y_pred))",
        ])
    elif task == "regression":
        code_lines.extend([
            "from sklearn.metrics import mean_squared_error, r2_score",
            "y_pred = model.predict(X_test)",
            "print(f'MSE: {mean_squared_error(y_test, y_pred):.4f}')",
            "print(f'R²: {r2_score(y_test, y_pred):.4f}')",
        ])
    else:
        code_lines.extend([
            "labels = model.predict(X_test)",
            "print(f'聚类标签分布: {pd.Series(labels).value_counts().to_dict()}')",
        ])

    code = '\n'.join(code_lines)
    return {
        "success": True,
        "task": task,
        "data_format": data_format,
        "target_col": target_col,
        "code": code,
        "steps": ["加载", "清洗", "特征工程", "分割", "训练", "评估"],
        "line_count": len(code_lines),
    }


# ==================== 27. DP模式与贪心策略模板 (维度55) ====================

DP_PATTERNS = {
    "linear_dp": {
        "name": "线性DP",
        "description": "最长递增子序列/最大子数组和",
        "complexity": {"time": "O(n²) / O(n)", "space": "O(n)"},
        "code": '''def longest_increasing_subsequence(nums):
    """最长递增子序列 - O(n²)"""
    if not nums:
        return 0
    n = len(nums)
    dp = [1] * n
    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    return max(dp)

def max_subarray_sum(nums):
    """最大子数组和 (Kadane) - O(n)"""
    max_sum = cur_sum = nums[0]
    for x in nums[1:]:
        cur_sum = max(x, cur_sum + x)
        max_sum = max(max_sum, cur_sum)
    return max_sum
''',
    },
    "interval_dp": {
        "name": "区间DP",
        "description": "矩阵链乘法/戳气球",
        "complexity": {"time": "O(n³)", "space": "O(n²)"},
        "code": '''def matrix_chain_order(dims):
    """矩阵链乘法 - O(n³)"""
    n = len(dims) - 1
    dp = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = float('inf')
            for k in range(i, j):
                cost = dp[i][k] + dp[k+1][j] + dims[i]*dims[k+1]*dims[j+1]
                dp[i][j] = min(dp[i][j], cost)
    return dp[0][n-1]
''',
    },
    "tree_dp": {
        "name": "树形DP",
        "description": "树的最大独立集/树的直径",
        "complexity": {"time": "O(n)", "space": "O(n)"},
        "code": '''def tree_diameter(adj):
    """树的直径 - O(n)"""
    n = len(adj)
    dp = [0] * n
    diameter = [0]
    visited = [False] * n

    def dfs(u):
        visited[u] = True
        max1 = max2 = 0
        for v in adj[u]:
            if not visited[v]:
                dfs(v)
                d = dp[v] + 1
                if d > max1:
                    max2 = max1
                    max1 = d
                elif d > max2:
                    max2 = d
        dp[u] = max1
        diameter[0] = max(diameter[0], max1 + max2)

    dfs(0)
    return diameter[0]
''',
    },
    "greedy_interval": {
        "name": "贪心-区间调度",
        "description": "最多不重叠区间/最少会议室",
        "complexity": {"time": "O(n log n)", "space": "O(1)"},
        "code": '''def max_non_overlapping(intervals):
    """最多不重叠区间 - O(n log n)"""
    intervals.sort(key=lambda x: x[1])
    count = 0
    end = float('-inf')
    for s, e in intervals:
        if s >= end:
            count += 1
            end = e
    return count
''',
    },
    "greedy_huffman": {
        "name": "贪心-Huffman编码",
        "description": "最优前缀编码",
        "complexity": {"time": "O(n log n)", "space": "O(n)"},
        "code": '''import heapq

def huffman_encoding(freq):
    """Huffman编码 - O(n log n)"""
    heap = [[f, [ch, '']] for ch, f in freq.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        lo = heapq.heappop(heap)
        hi = heapq.heappop(heap)
        for pair in lo[1:]:
            pair[1] = '0' + pair[1]
        for pair in hi[1:]:
            pair[1] = '1' + pair[1]
        heapq.heappush(heap, [lo[0] + hi[0]] + lo[1:] + hi[1:])
    return {ch: code for ch, code in heap[0][1:]}
''',
    },
}


def get_dp_pattern(pattern: str) -> Dict:
    """获取DP/贪心算法模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in DP_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in DP_PATTERNS:
        tpl = DP_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": tpl["name"],
            "description": tpl["description"],
            "complexity": tpl["complexity"],
            "code": tpl["code"],
            "line_count": len(tpl["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in DP_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到模式: {pattern}",
            "available": {k: v["name"] for k, v in DP_PATTERNS.items()}}


# ==================== 28. 图算法扩展 (维度56) ====================

GRAPH_ALGORITHMS = {
    "topological_sort": {
        "name": "拓扑排序",
        "complexity": {"time": "O(V+E)", "space": "O(V)"},
        "code": '''from collections import deque

def topological_sort(graph, n):
    """拓扑排序(Kahn) - O(V+E)"""
    in_degree = [0] * n
    for u in range(n):
        for v in graph.get(u, []):
            in_degree[v] += 1
    queue = deque([u for u in range(n) if in_degree[u] == 0])
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for v in graph.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
    return order if len(order) == n else []  # 空=有环
''',
    },
    "kruskal_mst": {
        "name": "Kruskal最小生成树",
        "complexity": {"time": "O(E log E)", "space": "O(V)"},
        "code": '''def kruskal_mst(edges, n):
    """Kruskal MST - O(E log E)"""
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px == py: return False
        if rank[px] < rank[py]: px, py = py, px
        parent[py] = px
        if rank[px] == rank[py]: rank[px] += 1
        return True

    edges.sort(key=lambda e: e[2])  # (u, v, weight)
    mst = []
    for u, v, w in edges:
        if union(u, v):
            mst.append((u, v, w))
            if len(mst) == n - 1:
                break
    return mst
''',
    },
    "a_star": {
        "name": "A*搜索",
        "complexity": {"time": "O(E log V)", "space": "O(V)"},
        "code": '''import heapq

def a_star(graph, start, goal, heuristic):
    """A*搜索 - O(E log V)"""
    open_set = [(heuristic(start, goal), 0, start, [start])]
    visited = set()
    while open_set:
        f, g, current, path = heapq.heappop(open_set)
        if current == goal:
            return path, g
        if current in visited:
            continue
        visited.add(current)
        for neighbor, weight in graph.get(current, []):
            if neighbor not in visited:
                ng = g + weight
                nf = ng + heuristic(neighbor, goal)
                heapq.heappush(open_set, (nf, ng, neighbor, path + [neighbor]))
    return [], float('inf')
''',
    },
    "floyd_warshall": {
        "name": "Floyd-Warshall全源最短路",
        "complexity": {"time": "O(V³)", "space": "O(V²)"},
        "code": '''def floyd_warshall(dist):
    """Floyd-Warshall - O(V³)"""
    n = len(dist)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    return dist
''',
    },
    "tarjan_scc": {
        "name": "Tarjan强连通分量",
        "complexity": {"time": "O(V+E)", "space": "O(V)"},
        "code": '''def tarjan_scc(graph, n):
    """Tarjan SCC - O(V+E)"""
    idx = [0]
    stack = []
    on_stack = [False] * n
    index = [-1] * n
    lowlink = [0] * n
    sccs = []

    def strongconnect(v):
        index[v] = lowlink[v] = idx[0]
        idx[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in graph.get(v, []):
            if index[w] == -1:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack[w]:
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v: break
            sccs.append(scc)

    for v in range(n):
        if index[v] == -1:
            strongconnect(v)
    return sccs
''',
    },
}


def get_graph_algorithm(algorithm: str) -> Dict:
    """获取图算法模板"""
    if not algorithm:
        return {"success": False, "error": "需要提供算法名",
                "available": {k: v["name"] for k, v in GRAPH_ALGORITHMS.items()}}

    algorithm = algorithm.lower().strip().replace(' ', '_').replace('-', '_')

    if algorithm in GRAPH_ALGORITHMS:
        tpl = GRAPH_ALGORITHMS[algorithm]
        return {
            "success": True,
            "algorithm": algorithm,
            "name": tpl["name"],
            "complexity": tpl["complexity"],
            "code": tpl["code"],
            "line_count": len(tpl["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in GRAPH_ALGORITHMS.items()
               if algorithm in k or algorithm in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{algorithm}'", "similar": matches}

    return {"success": False, "error": f"未找到算法: {algorithm}",
            "available": {k: v["name"] for k, v in GRAPH_ALGORITHMS.items()}}


# ==================== 29. 竞赛编程助手 (维度2/LiveCodeBench) ====================

CP_TRICKS = {
    "fast_io": {
        "name": "快速IO",
        "python": "import sys\ninput = sys.stdin.readline\nprint = sys.stdout.write",
        "cpp": "#include <bits/stdc++.h>\nusing namespace std;\nint main(){ios::sync_with_stdio(0);cin.tie(0);",
    },
    "mod_arithmetic": {
        "name": "模运算",
        "python": "MOD = 10**9 + 7\ndef modinv(a, m=MOD): return pow(a, m-2, m)\ndef modcomb(n, r, m=MOD):\n    if r > n: return 0\n    num = den = 1\n    for i in range(r): num = num*(n-i)%m; den = den*(i+1)%m\n    return num * modinv(den, m) % m",
    },
    "bit_manipulation": {
        "name": "位运算技巧",
        "python": "# 最低位1: x & (-x)\n# 去掉最低位1: x & (x-1)\n# 是否2的幂: x > 0 and (x & (x-1)) == 0\n# 子集枚举:\ns = mask\nwhile s > 0:\n    # process subset s\n    s = (s - 1) & mask",
    },
    "prefix_sum": {
        "name": "前缀和",
        "python": "from itertools import accumulate\nprefix = list(accumulate(arr, initial=0))\n# 区间和 [l, r] = prefix[r+1] - prefix[l]",
    },
    "binary_search_template": {
        "name": "二分答案模板",
        "python": "def check(mid): pass  # 判断mid是否满足条件\nlo, hi = 0, 10**18\nwhile lo < hi:\n    mid = (lo + hi) // 2\n    if check(mid): hi = mid\n    else: lo = mid + 1\n# lo 即为答案",
    },
    "segment_tree": {
        "name": "线段树",
        "python": "class SegTree:\n    def __init__(self, n):\n        self.n = n; self.tree = [0]*(4*n)\n    def update(self, i, val, node=1, lo=0, hi=None):\n        if hi is None: hi = self.n-1\n        if lo == hi: self.tree[node] = val; return\n        mid = (lo+hi)//2\n        if i <= mid: self.update(i, val, 2*node, lo, mid)\n        else: self.update(i, val, 2*node+1, mid+1, hi)\n        self.tree[node] = self.tree[2*node] + self.tree[2*node+1]\n    def query(self, l, r, node=1, lo=0, hi=None):\n        if hi is None: hi = self.n-1\n        if l > hi or r < lo: return 0\n        if l <= lo and hi <= r: return self.tree[node]\n        mid = (lo+hi)//2\n        return self.query(l, r, 2*node, lo, mid) + self.query(l, r, 2*node+1, mid+1, hi)",
    },
}


def get_cp_trick(trick: str) -> Dict:
    """获取竞赛编程技巧/模板"""
    if not trick:
        return {"success": False, "error": "需要提供技巧名称",
                "available": {k: v["name"] for k, v in CP_TRICKS.items()}}

    trick = trick.lower().strip().replace(' ', '_').replace('-', '_')

    if trick in CP_TRICKS:
        t = CP_TRICKS[trick]
        return {
            "success": True,
            "trick": trick,
            "name": t["name"],
            "code": t.get("python", ""),
            "cpp_code": t.get("cpp", ""),
            "languages": [k for k in t if k != "name"],
        }

    matches = {k: v["name"] for k, v in CP_TRICKS.items()
               if trick in k or trick in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{trick}'", "similar": matches}

    return {"success": False, "error": f"未找到: {trick}",
            "available": {k: v["name"] for k, v in CP_TRICKS.items()}}


# ==================== 30. ML模型选择器 (维度47) ====================

ML_MODEL_CATALOG = {
    "classification": {
        "logistic_regression": {"complexity": "低", "interpretable": True, "large_data": True, "params": {"C": 1.0, "max_iter": 100}},
        "random_forest": {"complexity": "中", "interpretable": True, "large_data": True, "params": {"n_estimators": 100, "max_depth": None}},
        "gradient_boosting": {"complexity": "高", "interpretable": False, "large_data": True, "params": {"n_estimators": 200, "learning_rate": 0.1, "max_depth": 5}},
        "svm": {"complexity": "中", "interpretable": False, "large_data": False, "params": {"C": 1.0, "kernel": "rbf"}},
        "knn": {"complexity": "低", "interpretable": True, "large_data": False, "params": {"n_neighbors": 5}},
    },
    "regression": {
        "linear_regression": {"complexity": "低", "interpretable": True, "large_data": True, "params": {}},
        "ridge": {"complexity": "低", "interpretable": True, "large_data": True, "params": {"alpha": 1.0}},
        "random_forest_regressor": {"complexity": "中", "interpretable": True, "large_data": True, "params": {"n_estimators": 100}},
        "gradient_boosting_regressor": {"complexity": "高", "interpretable": False, "large_data": True, "params": {"n_estimators": 200, "learning_rate": 0.1}},
        "svr": {"complexity": "中", "interpretable": False, "large_data": False, "params": {"C": 1.0, "kernel": "rbf"}},
    },
    "clustering": {
        "kmeans": {"complexity": "低", "interpretable": True, "large_data": True, "params": {"n_clusters": 3}},
        "dbscan": {"complexity": "中", "interpretable": True, "large_data": True, "params": {"eps": 0.5, "min_samples": 5}},
        "agglomerative": {"complexity": "高", "interpretable": True, "large_data": False, "params": {"n_clusters": 3}},
    },
}


def recommend_ml_model(task: str, data_size: str = "medium",
                       interpretable: bool = False) -> Dict:
    """根据任务类型和约束推荐ML模型"""
    if not task or task not in ML_MODEL_CATALOG:
        return {"success": False, "error": f"未知任务: {task}",
                "available_tasks": list(ML_MODEL_CATALOG.keys())}

    models = ML_MODEL_CATALOG[task]
    large = data_size in ("large", "big", "huge")

    ranked = []
    for name, info in models.items():
        score = 0
        if large and info["large_data"]:
            score += 2
        if interpretable and info["interpretable"]:
            score += 2
        if info["complexity"] == "低":
            score += 1
        elif info["complexity"] == "高":
            score += 0.5  # powerful models get a small boost
        ranked.append((name, info, score))

    ranked.sort(key=lambda x: -x[2])

    recommendations = []
    for name, info, score in ranked[:3]:
        recommendations.append({
            "model": name,
            "complexity": info["complexity"],
            "interpretable": info["interpretable"],
            "suggested_params": info["params"],
        })

    return {
        "success": True,
        "task": task,
        "data_size": data_size,
        "interpretable_required": interpretable,
        "recommendations": recommendations,
        "total_models": len(models),
    }


# ==================== 31. 框架速查表生成器 (维度71) ====================

FRAMEWORK_CHEATSHEETS = {
    "fastapi": {
        "name": "FastAPI",
        "category": "Python Web",
        "setup": "pip install fastapi uvicorn",
        "hello_world": '''from fastapi import FastAPI
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# uvicorn main:app --reload
''',
        "key_concepts": ["路由装饰器", "Pydantic模型", "依赖注入", "异步支持", "自动OpenAPI文档"],
        "common_patterns": {
            "CRUD": "@app.post('/items'), @app.get('/items/{id}'), @app.put('/items/{id}'), @app.delete('/items/{id}')",
            "中间件": "app.add_middleware(CORSMiddleware, allow_origins=['*'])",
            "数据库": "from sqlalchemy.ext.asyncio import AsyncSession",
        },
    },
    "nextjs": {
        "name": "Next.js",
        "category": "React Framework",
        "setup": "npx create-next-app@latest my-app",
        "hello_world": '''// app/page.tsx
export default function Home() {
  return <h1>Hello World</h1>
}
''',
        "key_concepts": ["App Router", "Server Components", "SSR/SSG/ISR", "API Routes", "Middleware"],
        "common_patterns": {
            "数据获取": "async function getData() { const res = await fetch('...'); return res.json() }",
            "动态路由": "app/blog/[slug]/page.tsx",
            "布局": "app/layout.tsx - 共享布局组件",
        },
    },
    "django": {
        "name": "Django",
        "category": "Python Web",
        "setup": "pip install django && django-admin startproject mysite",
        "hello_world": '''# views.py
from django.http import JsonResponse
def hello(request):
    return JsonResponse({"message": "Hello World"})

# urls.py
urlpatterns = [path('hello/', hello)]
''',
        "key_concepts": ["MTV架构", "ORM", "Admin后台", "中间件", "模板系统"],
        "common_patterns": {
            "模型": "class Article(models.Model): title = models.CharField(max_length=200)",
            "视图": "class ArticleViewSet(viewsets.ModelViewSet)",
            "序列化": "class ArticleSerializer(serializers.ModelSerializer)",
        },
    },
    "vue3": {
        "name": "Vue 3",
        "category": "Frontend Framework",
        "setup": "npm create vue@latest",
        "hello_world": '''<script setup>
import { ref } from 'vue'
const msg = ref('Hello World')
</script>
<template>
  <h1>{{ msg }}</h1>
</template>
''',
        "key_concepts": ["Composition API", "响应式ref/reactive", "组件", "Pinia状态管理", "Vue Router"],
        "common_patterns": {
            "状态": "const count = ref(0); const state = reactive({ items: [] })",
            "计算属性": "const doubled = computed(() => count.value * 2)",
            "监听": "watch(count, (newVal) => { console.log(newVal) })",
        },
    },
    "spring_boot": {
        "name": "Spring Boot",
        "category": "Java Web",
        "setup": "https://start.spring.io/ → 选择依赖 → 下载",
        "hello_world": '''@RestController
public class HelloController {
    @GetMapping("/")
    public String hello() {
        return "Hello World";
    }
}
''',
        "key_concepts": ["自动配置", "依赖注入", "JPA", "Spring Security", "Actuator监控"],
        "common_patterns": {
            "REST API": "@RestController + @GetMapping/@PostMapping",
            "数据层": "@Repository + JpaRepository<Entity, Long>",
            "服务层": "@Service + @Transactional",
        },
    },
    "gin": {
        "name": "Gin (Go)",
        "category": "Go Web",
        "setup": "go get -u github.com/gin-gonic/gin",
        "hello_world": '''package main
import "github.com/gin-gonic/gin"

func main() {
    r := gin.Default()
    r.GET("/", func(c *gin.Context) {
        c.JSON(200, gin.H{"message": "Hello World"})
    })
    r.Run(":8080")
}
''',
        "key_concepts": ["路由组", "中间件", "参数绑定", "JSON响应", "模板渲染"],
        "common_patterns": {
            "路由组": "api := r.Group('/api'); api.GET('/users', getUsers)",
            "中间件": "r.Use(gin.Logger(), gin.Recovery())",
            "参数": "c.Param('id'), c.Query('page'), c.ShouldBindJSON(&obj)",
        },
    },
}


def get_framework_cheatsheet(framework: str) -> Dict:
    """获取框架速查表"""
    if not framework:
        return {"success": False, "error": "需要提供框架名称",
                "available": {k: v["name"] for k, v in FRAMEWORK_CHEATSHEETS.items()}}

    framework = framework.lower().strip().replace(' ', '_').replace('-', '_')

    if framework in FRAMEWORK_CHEATSHEETS:
        cs = FRAMEWORK_CHEATSHEETS[framework]
        return {
            "success": True,
            "framework": framework,
            "name": cs["name"],
            "category": cs["category"],
            "setup": cs["setup"],
            "hello_world": cs["hello_world"],
            "key_concepts": cs["key_concepts"],
            "common_patterns": cs["common_patterns"],
            "pattern_count": len(cs["common_patterns"]),
        }

    matches = {k: v["name"] for k, v in FRAMEWORK_CHEATSHEETS.items()
               if framework in k or framework in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{framework}'", "similar": matches}

    return {"success": False, "error": f"未找到框架: {framework}",
            "available": {k: v["name"] for k, v in FRAMEWORK_CHEATSHEETS.items()}}


# ==================== 32. SWE-Agent Pipeline助手 (维度1) ====================

SWE_PIPELINE_STEPS = {
    "parse_issue": {
        "description": "解析GitHub Issue,提取bug描述/复现步骤/预期行为",
        "inputs": ["issue_text"],
        "outputs": ["bug_description", "reproduction_steps", "expected_behavior", "affected_files"],
    },
    "locate_code": {
        "description": "根据Issue关键词和堆栈追踪定位相关代码",
        "inputs": ["bug_description", "repo_structure"],
        "outputs": ["candidate_files", "relevant_functions", "search_queries"],
    },
    "generate_patch": {
        "description": "生成修复补丁(最小化变更)",
        "inputs": ["affected_files", "bug_description"],
        "outputs": ["patch_diff", "changed_lines", "risk_assessment"],
    },
    "generate_test": {
        "description": "为修复生成回归测试",
        "inputs": ["bug_description", "patch_diff"],
        "outputs": ["test_code", "test_name", "assertions"],
    },
    "verify_fix": {
        "description": "运行测试验证修复有效性",
        "inputs": ["test_code", "patch_diff"],
        "outputs": ["test_result", "coverage_delta", "side_effects"],
    },
}


def plan_swe_fix(issue_text: str) -> Dict:
    """为GitHub Issue生成SWE-Agent修复计划"""
    if not issue_text or len(issue_text.strip()) < 10:
        return {"success": False, "error": "Issue文本太短,需要至少10个字符"}

    text = issue_text.lower()
    # 分类Issue
    if any(kw in text for kw in ["error", "bug", "crash", "fail", "exception", "traceback"]):
        issue_type = "bug"
    elif any(kw in text for kw in ["feature", "add", "implement", "support", "enhancement"]):
        issue_type = "feature"
    elif any(kw in text for kw in ["refactor", "cleanup", "improve", "optimize"]):
        issue_type = "refactor"
    else:
        issue_type = "unknown"

    # 提取关键信息
    lines = issue_text.strip().split('\n')
    title = lines[0] if lines else "Untitled"

    # 提取文件引用
    import re
    file_refs = re.findall(r'[\w/]+\.\w{1,5}', issue_text)
    file_refs = list(set(f for f in file_refs if '.' in f and len(f) > 3))[:10]

    # 提取堆栈追踪
    has_traceback = 'traceback' in text or 'error' in text

    # 生成修复计划
    plan_steps = []
    for step_name, step_info in SWE_PIPELINE_STEPS.items():
        plan_steps.append({
            "step": step_name,
            "description": step_info["description"],
            "inputs": step_info["inputs"],
            "outputs": step_info["outputs"],
        })

    return {
        "success": True,
        "issue_type": issue_type,
        "title": title,
        "file_references": file_refs,
        "has_traceback": has_traceback,
        "pipeline": plan_steps,
        "pipeline_length": len(plan_steps),
        "estimated_complexity": "high" if issue_type == "feature" else "medium" if issue_type == "bug" else "low",
    }


# ==================== 33. NoSQL操作模板 (维度31) ====================

NOSQL_TEMPLATES = {
    "redis": {
        "name": "Redis",
        "connection": "import redis\nr = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)",
        "operations": {
            "string": "r.set('key', 'value')\nr.get('key')\nr.setex('key', 3600, 'value')  # TTL 1h",
            "hash": "r.hset('user:1', mapping={'name': 'Alice', 'age': 30})\nr.hgetall('user:1')",
            "list": "r.lpush('queue', 'task1', 'task2')\nr.rpop('queue')\nr.lrange('queue', 0, -1)",
            "set": "r.sadd('tags', 'python', 'redis')\nr.smembers('tags')\nr.sinter('tags1', 'tags2')",
            "sorted_set": "r.zadd('leaderboard', {'alice': 100, 'bob': 85})\nr.zrevrange('leaderboard', 0, 9, withscores=True)",
            "pub_sub": "# Publisher\nr.publish('channel', 'message')\n# Subscriber\np = r.pubsub()\np.subscribe('channel')\nfor msg in p.listen(): print(msg)",
            "cache_pattern": "def get_cached(key, fetch_fn, ttl=3600):\n    val = r.get(key)\n    if val is None:\n        val = fetch_fn()\n        r.setex(key, ttl, json.dumps(val))\n    return json.loads(val) if isinstance(val, str) else val",
        },
    },
    "mongodb": {
        "name": "MongoDB",
        "connection": "from pymongo import MongoClient\nclient = MongoClient('mongodb://localhost:27017/')\ndb = client['mydb']\ncol = db['users']",
        "operations": {
            "insert": "col.insert_one({'name': 'Alice', 'age': 30})\ncol.insert_many([{'name': 'Bob'}, {'name': 'Charlie'}])",
            "find": "col.find_one({'name': 'Alice'})\nlist(col.find({'age': {'$gt': 25}}).sort('age', -1).limit(10))",
            "update": "col.update_one({'name': 'Alice'}, {'$set': {'age': 31}})\ncol.update_many({}, {'$inc': {'age': 1}})",
            "delete": "col.delete_one({'name': 'Alice'})\ncol.delete_many({'age': {'$lt': 18}})",
            "aggregate": "col.aggregate([\n    {'$match': {'age': {'$gt': 20}}},\n    {'$group': {'_id': '$city', 'avg_age': {'$avg': '$age'}}},\n    {'$sort': {'avg_age': -1}}\n])",
            "index": "col.create_index([('name', 1)], unique=True)\ncol.create_index([('location', '2dsphere')])",
        },
    },
    "elasticsearch": {
        "name": "Elasticsearch",
        "connection": "from elasticsearch import Elasticsearch\nes = Elasticsearch(['http://localhost:9200'])",
        "operations": {
            "index": "es.index(index='users', id=1, document={'name': 'Alice', 'age': 30})",
            "search": "es.search(index='users', query={'match': {'name': 'Alice'}})",
            "bulk": "from elasticsearch.helpers import bulk\nactions = [{'_index': 'users', '_source': doc} for doc in docs]\nbulk(es, actions)",
            "aggregate": "es.search(index='users', aggs={'age_stats': {'stats': {'field': 'age'}}})",
        },
    },
}


def get_nosql_template(db: str, operation: str = "") -> Dict:
    """获取NoSQL数据库操作模板"""
    if not db:
        return {"success": False, "error": "需要提供数据库名",
                "available": {k: v["name"] for k, v in NOSQL_TEMPLATES.items()}}

    db = db.lower().strip()
    if db not in NOSQL_TEMPLATES:
        return {"success": False, "error": f"未找到: {db}",
                "available": {k: v["name"] for k, v in NOSQL_TEMPLATES.items()}}

    tpl = NOSQL_TEMPLATES[db]

    if operation:
        operation = operation.lower().strip()
        if operation in tpl["operations"]:
            return {
                "success": True,
                "db": db,
                "name": tpl["name"],
                "operation": operation,
                "code": tpl["operations"][operation],
                "connection": tpl["connection"],
            }
        return {"success": False, "error": f"未找到操作: {operation}",
                "available_ops": list(tpl["operations"].keys())}

    return {
        "success": True,
        "db": db,
        "name": tpl["name"],
        "connection": tpl["connection"],
        "operations": list(tpl["operations"].keys()),
        "operation_count": len(tpl["operations"]),
    }


# ==================== 34. 微服务架构模板 (维度41) ====================

MICROSERVICE_PATTERNS = {
    "api_gateway": {
        "name": "API Gateway",
        "description": "统一入口,路由/限流/认证",
        "code": '''from fastapi import FastAPI, Request
import httpx

app = FastAPI(title="API Gateway")
SERVICES = {
    "users": "http://user-service:8001",
    "orders": "http://order-service:8002",
    "products": "http://product-service:8003",
}

@app.api_route("/{service}/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def proxy(service: str, path: str, request: Request):
    if service not in SERVICES:
        return {"error": f"Unknown service: {service}"}
    url = f"{SERVICES[service]}/{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(request.method, url,
            headers=dict(request.headers), content=await request.body())
    return resp.json()
''',
    },
    "service_discovery": {
        "name": "服务发现",
        "description": "Consul/etcd服务注册与发现",
        "code": '''import consul

c = consul.Consul()

# 注册服务
c.agent.service.register(
    name="user-service",
    service_id="user-1",
    address="10.0.0.1",
    port=8001,
    check=consul.Check.http("http://10.0.0.1:8001/health", interval="10s")
)

# 发现服务
_, services = c.health.service("user-service", passing=True)
endpoints = [(s['Service']['Address'], s['Service']['Port']) for s in services]
''',
    },
    "circuit_breaker": {
        "name": "熔断器",
        "description": "防止级联故障(Hystrix模式)",
        "code": '''import time
from enum import Enum

class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = State.CLOSED
        self.last_failure_time = 0

    def call(self, func, *args, **kwargs):
        if self.state == State.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = State.HALF_OPEN
            else:
                raise Exception("Circuit is OPEN")
        try:
            result = func(*args, **kwargs)
            self.failure_count = 0
            self.state = State.CLOSED
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = State.OPEN
            raise
''',
    },
    "event_driven": {
        "name": "事件驱动",
        "description": "基于消息队列的异步通信",
        "code": '''import json
import redis

r = redis.Redis()

# 发布事件
def publish_event(event_type: str, data: dict):
    event = {"type": event_type, "data": data, "timestamp": time.time()}
    r.publish("events", json.dumps(event))

# 订阅事件
def subscribe_events(handler):
    p = r.pubsub()
    p.subscribe("events")
    for message in p.listen():
        if message["type"] == "message":
            event = json.loads(message["data"])
            handler(event)

# 使用
publish_event("user_created", {"user_id": 123, "name": "Alice"})
''',
    },
    "saga_pattern": {
        "name": "Saga模式",
        "description": "分布式事务补偿",
        "code": '''class SagaStep:
    def __init__(self, action, compensation):
        self.action = action
        self.compensation = compensation

class SagaOrchestrator:
    def __init__(self):
        self.steps = []
        self.completed = []

    def add_step(self, action, compensation):
        self.steps.append(SagaStep(action, compensation))

    def execute(self):
        for step in self.steps:
            try:
                step.action()
                self.completed.append(step)
            except Exception as e:
                self.compensate()
                raise Exception(f"Saga failed: {e}")

    def compensate(self):
        for step in reversed(self.completed):
            try:
                step.compensation()
            except Exception:
                pass  # log compensation failure
''',
    },
}


def get_microservice_pattern(pattern: str) -> Dict:
    """获取微服务架构模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in MICROSERVICE_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in MICROSERVICE_PATTERNS:
        p = MICROSERVICE_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "description": p["description"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in MICROSERVICE_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到模式: {pattern}",
            "available": {k: v["name"] for k, v in MICROSERVICE_PATTERNS.items()}}


# ==================== 35. JS/TS代码片段库 (维度33) ====================

JSTS_SNIPPETS = {
    "react_usestate": {
        "name": "React useState Hook",
        "lang": "tsx",
        "code": '''import { useState } from 'react';

const [count, setCount] = useState(0);
const [items, setItems] = useState<string[]>([]);
const [user, setUser] = useState<User | null>(null);

// 函数式更新
setCount(prev => prev + 1);
setItems(prev => [...prev, 'new item']);
''',
    },
    "react_useeffect": {
        "name": "React useEffect Hook",
        "lang": "tsx",
        "code": '''import { useEffect, useState } from 'react';

// 挂载时执行
useEffect(() => {
  fetchData();
  return () => cleanup(); // 卸载时清理
}, []);

// 依赖变化时执行
useEffect(() => {
  const subscription = subscribe(id);
  return () => subscription.unsubscribe();
}, [id]);
''',
    },
    "react_custom_hook": {
        "name": "React 自定义Hook",
        "lang": "tsx",
        "code": '''import { useState, useEffect } from 'react';

function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(url, { signal: controller.signal })
      .then(res => res.json())
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [url]);

  return { data, loading, error };
}
''',
    },
    "express_router": {
        "name": "Express Router模式",
        "lang": "ts",
        "code": '''import express, { Request, Response, NextFunction } from 'express';

const router = express.Router();

// 中间件
const authMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Unauthorized' });
  next();
};

router.get('/users', authMiddleware, async (req: Request, res: Response) => {
  const users = await UserService.findAll();
  res.json(users);
});

router.post('/users', async (req: Request, res: Response) => {
  const user = await UserService.create(req.body);
  res.status(201).json(user);
});

export default router;
''',
    },
    "ts_utility_types": {
        "name": "TypeScript工具类型",
        "lang": "ts",
        "code": '''// Partial - 所有属性可选
type UpdateUser = Partial<User>;

// Pick - 选择部分属性
type UserPreview = Pick<User, 'id' | 'name'>;

// Omit - 排除部分属性
type CreateUser = Omit<User, 'id' | 'createdAt'>;

// Record - 键值对映射
type UserMap = Record<string, User>;

// 条件类型
type NonNullable<T> = T extends null | undefined ? never : T;

// 泛型约束
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
''',
    },
    "ts_zod_validation": {
        "name": "Zod Schema验证",
        "lang": "ts",
        "code": '''import { z } from 'zod';

const UserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email(),
  age: z.number().int().positive().optional(),
  role: z.enum(['admin', 'user', 'guest']),
});

type User = z.infer<typeof UserSchema>;

// 验证
const result = UserSchema.safeParse(data);
if (result.success) {
  console.log(result.data); // 类型安全
} else {
  console.log(result.error.issues);
}
''',
    },
}


def get_jsts_snippet(snippet: str) -> Dict:
    """获取JS/TS代码片段"""
    if not snippet:
        return {"success": False, "error": "需要提供片段名",
                "available": {k: v["name"] for k, v in JSTS_SNIPPETS.items()}}

    snippet = snippet.lower().strip().replace(' ', '_').replace('-', '_')

    if snippet in JSTS_SNIPPETS:
        s = JSTS_SNIPPETS[snippet]
        return {
            "success": True,
            "snippet": snippet,
            "name": s["name"],
            "lang": s["lang"],
            "code": s["code"],
        }

    matches = {k: v["name"] for k, v in JSTS_SNIPPETS.items()
               if snippet in k or snippet in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{snippet}'", "similar": matches}

    return {"success": False, "error": f"未找到: {snippet}",
            "available": {k: v["name"] for k, v in JSTS_SNIPPETS.items()}}


# ==================== 36. Java企业级模式 (维度34) ====================

JAVA_PATTERNS = {
    "spring_rest_controller": {
        "name": "Spring REST Controller",
        "code": '''@RestController
@RequestMapping("/api/users")
public class UserController {
    @Autowired
    private UserService userService;

    @GetMapping
    public ResponseEntity<List<User>> getAll() {
        return ResponseEntity.ok(userService.findAll());
    }

    @GetMapping("/{id}")
    public ResponseEntity<User> getById(@PathVariable Long id) {
        return userService.findById(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<User> create(@Valid @RequestBody CreateUserDTO dto) {
        User user = userService.create(dto);
        return ResponseEntity.status(HttpStatus.CREATED).body(user);
    }
}
''',
    },
    "jpa_entity": {
        "name": "JPA Entity + Repository",
        "code": '''@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(unique = true, nullable = false)
    private String email;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<Order> orders = new ArrayList<>();

    @CreatedDate
    private LocalDateTime createdAt;
}

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    List<User> findByNameContaining(String name);

    @Query("SELECT u FROM User u WHERE u.createdAt > :date")
    List<User> findRecentUsers(@Param("date") LocalDateTime date);
}
''',
    },
    "service_layer": {
        "name": "Service + 事务管理",
        "code": '''@Service
@Transactional(readOnly = true)
public class UserService {
    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public List<User> findAll() {
        return userRepository.findAll();
    }

    @Transactional
    public User create(CreateUserDTO dto) {
        if (userRepository.findByEmail(dto.getEmail()).isPresent()) {
            throw new DuplicateException("Email already exists");
        }
        User user = new User();
        user.setName(dto.getName());
        user.setEmail(dto.getEmail());
        return userRepository.save(user);
    }

    @Transactional
    public void delete(Long id) {
        userRepository.deleteById(id);
    }
}
''',
    },
    "exception_handler": {
        "name": "全局异常处理",
        "code": '''@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(ResourceNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse(404, ex.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
            .map(e -> e.getField() + ": " + e.getDefaultMessage())
            .collect(Collectors.joining(", "));
        return ResponseEntity.badRequest().body(new ErrorResponse(400, message));
    }
}
''',
    },
    "design_pattern_builder": {
        "name": "Builder设计模式",
        "code": '''public class User {
    private final String name;
    private final String email;
    private final int age;

    private User(Builder builder) {
        this.name = builder.name;
        this.email = builder.email;
        this.age = builder.age;
    }

    public static class Builder {
        private String name;
        private String email;
        private int age;

        public Builder name(String name) { this.name = name; return this; }
        public Builder email(String email) { this.email = email; return this; }
        public Builder age(int age) { this.age = age; return this; }
        public User build() { return new User(this); }
    }
}
// 使用: new User.Builder().name("Alice").email("a@b.com").age(30).build();
''',
    },
}


def get_java_pattern(pattern: str) -> Dict:
    """获取Java企业级模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in JAVA_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in JAVA_PATTERNS:
        p = JAVA_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in JAVA_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in JAVA_PATTERNS.items()}}


# ==================== 37. Go并发模式 (维度35) ====================

GO_CONCURRENCY = {
    "goroutine_basic": {
        "name": "Goroutine基础",
        "code": '''package main

import (
    "fmt"
    "sync"
)

func worker(id int, wg *sync.WaitGroup) {
    defer wg.Done()
    fmt.Printf("Worker %d starting\\n", id)
    // do work
    fmt.Printf("Worker %d done\\n", id)
}

func main() {
    var wg sync.WaitGroup
    for i := 1; i <= 5; i++ {
        wg.Add(1)
        go worker(i, &wg)
    }
    wg.Wait()
}
''',
    },
    "channel_pipeline": {
        "name": "Channel Pipeline",
        "code": '''func generator(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        for _, n := range nums {
            out <- n
        }
        close(out)
    }()
    return out
}

func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        for n := range in {
            out <- n * n
        }
        close(out)
    }()
    return out
}

// 使用: for v := range square(generator(2, 3, 4)) { fmt.Println(v) }
''',
    },
    "worker_pool": {
        "name": "Worker Pool",
        "code": '''func workerPool(jobs <-chan int, results chan<- int, numWorkers int) {
    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for job := range jobs {
                result := process(job) // 处理任务
                results <- result
            }
        }(i)
    }
    go func() {
        wg.Wait()
        close(results)
    }()
}

func main() {
    jobs := make(chan int, 100)
    results := make(chan int, 100)
    workerPool(jobs, results, 5)
    for i := 0; i < 50; i++ { jobs <- i }
    close(jobs)
    for r := range results { fmt.Println(r) }
}
''',
    },
    "context_cancel": {
        "name": "Context取消",
        "code": '''func longRunningTask(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err() // context.Canceled or DeadlineExceeded
        default:
            // do work
            time.Sleep(100 * time.Millisecond)
        }
    }
}

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    go func() {
        if err := longRunningTask(ctx); err != nil {
            log.Printf("Task cancelled: %v", err)
        }
    }()

    // 提前取消
    time.Sleep(2 * time.Second)
    cancel()
}
''',
    },
    "select_fan_in": {
        "name": "Select Fan-in",
        "code": '''func fanIn(channels ...<-chan string) <-chan string {
    merged := make(chan string)
    var wg sync.WaitGroup
    for _, ch := range channels {
        wg.Add(1)
        go func(c <-chan string) {
            defer wg.Done()
            for v := range c {
                merged <- v
            }
        }(ch)
    }
    go func() {
        wg.Wait()
        close(merged)
    }()
    return merged
}

// 超时select
select {
case msg := <-ch:
    fmt.Println(msg)
case <-time.After(3 * time.Second):
    fmt.Println("timeout")
}
''',
    },
    "mutex_sync": {
        "name": "Mutex同步",
        "code": '''type SafeCounter struct {
    mu sync.RWMutex
    v  map[string]int
}

func (c *SafeCounter) Inc(key string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.v[key]++
}

func (c *SafeCounter) Get(key string) int {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.v[key]
}

// sync.Once - 只执行一次
var once sync.Once
once.Do(func() { initDB() })
''',
    },
}


def get_go_pattern(pattern: str) -> Dict:
    """获取Go并发模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in GO_CONCURRENCY.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in GO_CONCURRENCY:
        p = GO_CONCURRENCY[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in GO_CONCURRENCY.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in GO_CONCURRENCY.items()}}


# ==================== 38. Rust安全模式 (维度36) ====================

RUST_PATTERNS = {
    "ownership_borrow": {
        "name": "所有权与借用",
        "code": '''fn main() {
    let s1 = String::from("hello");
    let s2 = &s1; // 不可变借用
    println!("{}", s2);

    let mut s3 = String::from("hello");
    let s4 = &mut s3; // 可变借用
    s4.push_str(", world");

    // 移动语义
    let s5 = s1; // s1不再有效
    // println!("{}", s1); // 编译错误!
}

fn take_ownership(s: String) { println!("{}", s); }
fn borrow(s: &String) { println!("{}", s); }
fn borrow_mut(s: &mut String) { s.push_str("!"); }
''',
    },
    "lifetime": {
        "name": "生命周期标注",
        "code": '''// 显式生命周期
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}

// 结构体中的生命周期
struct Important<'a> {
    content: &'a str,
}

impl<'a> Important<'a> {
    fn level(&self) -> usize { self.content.len() }
}

// 静态生命周期
let s: &'static str = "I live forever";
''',
    },
    "enum_pattern_match": {
        "name": "枚举与模式匹配",
        "code": '''#[derive(Debug)]
enum Command {
    Quit,
    Echo(String),
    Move { x: i32, y: i32 },
    Color(u8, u8, u8),
}

fn process(cmd: Command) {
    match cmd {
        Command::Quit => println!("Quitting"),
        Command::Echo(msg) => println!("{}", msg),
        Command::Move { x, y } => println!("Moving to ({}, {})", x, y),
        Command::Color(r, g, b) => println!("#{:02x}{:02x}{:02x}", r, g, b),
    }
}

// if let简写
if let Command::Echo(msg) = cmd {
    println!("{}", msg);
}
''',
    },
    "error_handling": {
        "name": "错误处理(Result/Option)",
        "code": '''use std::fs;
use std::io;

#[derive(Debug)]
enum AppError {
    Io(io::Error),
    Parse(std::num::ParseIntError),
    Custom(String),
}

impl From<io::Error> for AppError {
    fn from(e: io::Error) -> Self { AppError::Io(e) }
}

fn read_config(path: &str) -> Result<String, AppError> {
    let content = fs::read_to_string(path)?; // ?自动转换
    Ok(content)
}

// Option处理
fn find_user(id: u32) -> Option<String> {
    if id == 1 { Some("Alice".into()) } else { None }
}
let name = find_user(1).unwrap_or("Unknown".into());
''',
    },
    "trait_impl": {
        "name": "Trait与泛型",
        "code": '''trait Summary {
    fn summarize(&self) -> String;
    fn default_summary(&self) -> String {
        String::from("(Read more...)")
    }
}

struct Article { title: String, content: String }

impl Summary for Article {
    fn summarize(&self) -> String {
        format!("{}: {}...", self.title, &self.content[..20])
    }
}

// 泛型约束
fn notify(item: &impl Summary) { println!("{}", item.summarize()); }

// where子句
fn compare<T>(a: &T, b: &T) -> bool
where T: PartialEq + std::fmt::Debug {
    a == b
}
''',
    },
}


def get_rust_pattern(pattern: str) -> Dict:
    """获取Rust安全模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in RUST_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in RUST_PATTERNS:
        p = RUST_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in RUST_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in RUST_PATTERNS.items()}}


# ==================== 39. C# .NET模式 (维度37) ====================

CSHARP_PATTERNS = {
    "aspnet_controller": {
        "name": "ASP.NET Core Controller",
        "code": '''[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;

    public UsersController(IUserService userService)
    {
        _userService = userService;
    }

    [HttpGet]
    public async Task<ActionResult<IEnumerable<User>>> GetAll()
    {
        var users = await _userService.GetAllAsync();
        return Ok(users);
    }

    [HttpGet("{id}")]
    public async Task<ActionResult<User>> GetById(int id)
    {
        var user = await _userService.GetByIdAsync(id);
        if (user == null) return NotFound();
        return Ok(user);
    }

    [HttpPost]
    public async Task<ActionResult<User>> Create([FromBody] CreateUserDto dto)
    {
        var user = await _userService.CreateAsync(dto);
        return CreatedAtAction(nameof(GetById), new { id = user.Id }, user);
    }
}
''',
    },
    "ef_core_model": {
        "name": "EF Core Model + DbContext",
        "code": '''public class User
{
    public int Id { get; set; }
    [Required, MaxLength(100)]
    public string Name { get; set; } = string.Empty;
    [Required, EmailAddress]
    public string Email { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public ICollection<Order> Orders { get; set; } = new List<Order>();
}

public class AppDbContext : DbContext
{
    public DbSet<User> Users => Set<User>();
    public DbSet<Order> Orders => Set<Order>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<User>(e => {
            e.HasIndex(u => u.Email).IsUnique();
            e.HasMany(u => u.Orders).WithOne(o => o.User);
        });
    }
}
''',
    },
    "linq_queries": {
        "name": "LINQ查询",
        "code": '''// 方法语法
var adults = users.Where(u => u.Age >= 18)
                  .OrderBy(u => u.Name)
                  .Select(u => new { u.Name, u.Email })
                  .ToList();

// 查询语法
var query = from u in users
            where u.Age >= 18
            orderby u.Name
            select new { u.Name, u.Email };

// 聚合
var avgAge = users.Average(u => u.Age);
var grouped = users.GroupBy(u => u.Department)
                   .Select(g => new { Dept = g.Key, Count = g.Count() });

// Join
var joined = from u in users
             join o in orders on u.Id equals o.UserId
             select new { u.Name, o.Total };
''',
    },
    "async_pattern": {
        "name": "异步模式(async/await)",
        "code": '''public class DataService
{
    private readonly HttpClient _httpClient;

    public async Task<List<Item>> FetchAllAsync(CancellationToken ct = default)
    {
        var response = await _httpClient.GetAsync("/api/items", ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<List<Item>>(ct)
               ?? new List<Item>();
    }

    public async Task<Item[]> FetchParallelAsync(int[] ids)
    {
        var tasks = ids.Select(id => FetchByIdAsync(id));
        return await Task.WhenAll(tasks);
    }

    public async IAsyncEnumerable<Item> StreamAsync(
        [EnumeratorCancellation] CancellationToken ct = default)
    {
        await foreach (var item in _dbContext.Items.AsAsyncEnumerable())
        {
            ct.ThrowIfCancellationRequested();
            yield return item;
        }
    }
}
''',
    },
    "di_service": {
        "name": "依赖注入配置",
        "code": '''// Program.cs
var builder = WebApplication.CreateBuilder(args);

// 注册服务
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddSingleton<ICacheService, RedisCacheService>();
builder.Services.AddTransient<IEmailService, SmtpEmailService>();
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("Default")));

// 中间件
var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.Run();

// 接口定义
public interface IUserService
{
    Task<User?> GetByIdAsync(int id);
    Task<User> CreateAsync(CreateUserDto dto);
}
''',
    },
}


def get_csharp_pattern(pattern: str) -> Dict:
    """获取C# .NET模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in CSHARP_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in CSHARP_PATTERNS:
        p = CSHARP_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in CSHARP_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in CSHARP_PATTERNS.items()}}


# ==================== 40. 移动应用模式 (维度50) ====================

MOBILE_PATTERNS = {
    "flutter_stateful": {
        "name": "Flutter StatefulWidget",
        "platform": "flutter",
        "code": '''class CounterPage extends StatefulWidget {
  const CounterPage({super.key});

  @override
  State<CounterPage> createState() => _CounterPageState();
}

class _CounterPageState extends State<CounterPage> {
  int _counter = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Counter')),
      body: Center(
        child: Text('$_counter', style: Theme.of(context).textTheme.headlineLarge),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => setState(() => _counter++),
        child: const Icon(Icons.add),
      ),
    );
  }
}
''',
    },
    "flutter_provider": {
        "name": "Flutter Provider状态管理",
        "platform": "flutter",
        "code": '''class UserNotifier extends ChangeNotifier {
  User? _user;
  bool _loading = false;

  User? get user => _user;
  bool get loading => _loading;

  Future<void> fetchUser(int id) async {
    _loading = true;
    notifyListeners();
    try {
      _user = await ApiService.getUser(id);
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}

// main.dart
void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => UserNotifier(),
      child: const MyApp(),
    ),
  );
}

// 消费
Consumer<UserNotifier>(
  builder: (ctx, notifier, _) => notifier.loading
      ? const CircularProgressIndicator()
      : Text(notifier.user?.name ?? 'No user'),
)
''',
    },
    "flutter_http": {
        "name": "Flutter HTTP请求",
        "platform": "flutter",
        "code": '''import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiService {
  static const _baseUrl = 'https://api.example.com';

  static Future<List<User>> getUsers() async {
    final response = await http.get(Uri.parse('$_baseUrl/users'));
    if (response.statusCode == 200) {
      final List data = json.decode(response.body);
      return data.map((e) => User.fromJson(e)).toList();
    }
    throw Exception('Failed: ${response.statusCode}');
  }

  static Future<User> createUser(Map<String, dynamic> body) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/users'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(body),
    );
    if (response.statusCode == 201) {
      return User.fromJson(json.decode(response.body));
    }
    throw Exception('Failed: ${response.statusCode}');
  }
}
''',
    },
    "swiftui_view": {
        "name": "SwiftUI View",
        "platform": "ios",
        "code": '''struct ContentView: View {
    @State private var count = 0
    @State private var items: [Item] = []
    @State private var isLoading = false

    var body: some View {
        NavigationStack {
            List(items) { item in
                NavigationLink(destination: DetailView(item: item)) {
                    HStack {
                        Image(systemName: item.icon)
                        Text(item.title)
                        Spacer()
                        Text("\\(item.count)")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Items (\\(count))")
            .toolbar {
                Button(action: { count += 1 }) {
                    Image(systemName: "plus")
                }
            }
            .task { await loadItems() }
            .overlay {
                if isLoading { ProgressView() }
            }
        }
    }

    func loadItems() async {
        isLoading = true
        defer { isLoading = false }
        items = await ApiService.fetchItems()
    }
}
''',
    },
    "swiftui_mvvm": {
        "name": "SwiftUI MVVM模式",
        "platform": "ios",
        "code": '''@MainActor
class UserViewModel: ObservableObject {
    @Published var users: [User] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    func fetchUsers() async {
        isLoading = true
        errorMessage = nil
        do {
            users = try await APIClient.shared.get("/users")
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct UserListView: View {
    @StateObject private var viewModel = UserViewModel()

    var body: some View {
        Group {
            if viewModel.isLoading {
                ProgressView()
            } else if let error = viewModel.errorMessage {
                Text(error).foregroundColor(.red)
            } else {
                List(viewModel.users) { user in
                    Text(user.name)
                }
            }
        }
        .task { await viewModel.fetchUsers() }
    }
}
''',
    },
}


def get_mobile_pattern(pattern: str) -> Dict:
    """获取移动应用开发模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in MOBILE_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in MOBILE_PATTERNS:
        p = MOBILE_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "platform": p["platform"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in MOBILE_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in MOBILE_PATTERNS.items()}}


# ==================== 41. 桌面应用模式 (维度51) ====================

DESKTOP_PATTERNS = {
    "electron_main": {
        "name": "Electron主进程",
        "platform": "electron",
        "code": '''const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200, height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadFile('index.html');
}

app.whenReady().then(createWindow);
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// IPC通信
ipcMain.handle('read-file', async (event, filePath) => {
  const fs = require('fs').promises;
  return await fs.readFile(filePath, 'utf-8');
});
''',
    },
    "electron_preload": {
        "name": "Electron Preload安全桥接",
        "platform": "electron",
        "code": '''const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  readFile: (path) => ipcRenderer.invoke('read-file', path),
  onUpdateAvailable: (callback) =>
    ipcRenderer.on('update-available', (_event, info) => callback(info)),
  platform: process.platform,
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
});
''',
    },
    "tauri_command": {
        "name": "Tauri后端命令",
        "platform": "tauri",
        "code": '''use tauri::command;
use std::fs;

#[command]
fn read_file(path: String) -> Result<String, String> {
    fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![read_file, greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
''',
    },
    "tauri_frontend": {
        "name": "Tauri前端调用",
        "platform": "tauri",
        "code": '''import { invoke } from '@tauri-apps/api/tauri';
import { open } from '@tauri-apps/api/dialog';
import { readTextFile } from '@tauri-apps/api/fs';

async function greetUser() {
  const greeting = await invoke('greet', { name: 'World' });
  console.log(greeting);
}

async function openFile() {
  const selected = await open({
    multiple: false,
    filters: [{ name: 'Text', extensions: ['txt', 'md'] }],
  });
  if (selected) {
    const content = await readTextFile(selected as string);
    console.log(content);
  }
}
''',
    },
}


def get_desktop_pattern(pattern: str) -> Dict:
    """获取桌面应用模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in DESKTOP_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in DESKTOP_PATTERNS:
        p = DESKTOP_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "platform": p["platform"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in DESKTOP_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in DESKTOP_PATTERNS.items()}}


# ==================== 42. WebAssembly模式 (维度52) ====================

WASM_PATTERNS = {
    "rust_wasm_basic": {
        "name": "Rust→WASM基础",
        "code": '''use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[wasm_bindgen]
pub fn fibonacci(n: u32) -> u32 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

// 构建: wasm-pack build --target web
''',
    },
    "wasm_js_interop": {
        "name": "WASM-JS互操作",
        "code": '''use wasm_bindgen::prelude::*;

// 调用JS函数
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    fn log(s: &str);

    #[wasm_bindgen(js_namespace = Math)]
    fn random() -> f64;
}

// 导出给JS
#[wasm_bindgen]
pub struct ImageProcessor {
    width: u32,
    height: u32,
    pixels: Vec<u8>,
}

#[wasm_bindgen]
impl ImageProcessor {
    #[wasm_bindgen(constructor)]
    pub fn new(width: u32, height: u32) -> Self {
        Self { width, height, pixels: vec![0; (width * height * 4) as usize] }
    }

    pub fn grayscale(&mut self) {
        for chunk in self.pixels.chunks_mut(4) {
            let avg = (chunk[0] as u16 + chunk[1] as u16 + chunk[2] as u16) / 3;
            chunk[0] = avg as u8;
            chunk[1] = avg as u8;
            chunk[2] = avg as u8;
        }
    }
}
''',
    },
    "wasm_js_load": {
        "name": "JS加载WASM模块",
        "code": '''// 方式1: wasm-pack生成的模块
import init, { add, fibonacci, ImageProcessor } from './pkg/my_wasm.js';

async function main() {
  await init(); // 初始化WASM模块
  console.log(add(1, 2)); // 3
  console.log(fibonacci(10)); // 55

  const processor = new ImageProcessor(800, 600);
  processor.grayscale();
}
main();

// 方式2: 原生WebAssembly API
const response = await fetch('module.wasm');
const bytes = await response.arrayBuffer();
const { instance } = await WebAssembly.instantiate(bytes, {
  env: { memory: new WebAssembly.Memory({ initial: 256 }) }
});
console.log(instance.exports.add(1, 2));
''',
    },
    "wasm_wat_text": {
        "name": "WAT文本格式",
        "code": '''(module
  ;; 导入JS console.log
  (import "console" "log" (func $log (param i32)))

  ;; 内存
  (memory (export "memory") 1)

  ;; 加法函数
  (func $add (export "add") (param $a i32) (param $b i32) (result i32)
    local.get $a
    local.get $b
    i32.add
  )

  ;; 阶乘
  (func $factorial (export "factorial") (param $n i32) (result i32)
    (if (i32.le_s (local.get $n) (i32.const 1))
      (then (return (i32.const 1)))
    )
    (i32.mul
      (local.get $n)
      (call $factorial (i32.sub (local.get $n) (i32.const 1)))
    )
  )
)
''',
    },
}


def get_wasm_pattern(pattern: str) -> Dict:
    """获取WebAssembly模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in WASM_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in WASM_PATTERNS:
        p = WASM_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in WASM_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in WASM_PATTERNS.items()}}


# ==================== 43. 游戏引擎模式 (维度53) ====================

GAME_ENGINE_PATTERNS = {
    "unity_monobehaviour": {
        "name": "Unity MonoBehaviour",
        "engine": "unity",
        "code": '''using UnityEngine;

public class PlayerController : MonoBehaviour
{
    [SerializeField] private float moveSpeed = 5f;
    [SerializeField] private float jumpForce = 10f;
    private Rigidbody2D rb;
    private bool isGrounded;

    void Start()
    {
        rb = GetComponent<Rigidbody2D>();
    }

    void Update()
    {
        float moveX = Input.GetAxisRaw("Horizontal");
        rb.velocity = new Vector2(moveX * moveSpeed, rb.velocity.y);

        if (Input.GetButtonDown("Jump") && isGrounded)
        {
            rb.AddForce(Vector2.up * jumpForce, ForceMode2D.Impulse);
            isGrounded = false;
        }
    }

    void OnCollisionEnter2D(Collision2D collision)
    {
        if (collision.gameObject.CompareTag("Ground"))
            isGrounded = true;
    }
}
''',
    },
    "unity_scriptable_object": {
        "name": "Unity ScriptableObject",
        "engine": "unity",
        "code": '''using UnityEngine;

[CreateAssetMenu(fileName = "NewWeapon", menuName = "Game/Weapon")]
public class WeaponData : ScriptableObject
{
    public string weaponName;
    public int damage;
    public float attackSpeed;
    public Sprite icon;
    public AudioClip attackSound;

    public float DPS => damage * attackSpeed;
}

// 使用
public class WeaponSystem : MonoBehaviour
{
    [SerializeField] private WeaponData currentWeapon;

    public void Attack()
    {
        Debug.Log($"Attacking with {currentWeapon.weaponName} for {currentWeapon.damage} damage");
        AudioSource.PlayClipAtPoint(currentWeapon.attackSound, transform.position);
    }
}
''',
    },
    "godot_gdscript": {
        "name": "Godot GDScript",
        "engine": "godot",
        "code": '''extends CharacterBody2D

@export var speed: float = 200.0
@export var jump_velocity: float = -400.0

var gravity = ProjectSettings.get_setting("physics/2d/default_gravity")

func _physics_process(delta):
    if not is_on_floor():
        velocity.y += gravity * delta

    if Input.is_action_just_pressed("ui_accept") and is_on_floor():
        velocity.y = jump_velocity

    var direction = Input.get_axis("ui_left", "ui_right")
    if direction:
        velocity.x = direction * speed
    else:
        velocity.x = move_toward(velocity.x, 0, speed)

    move_and_slide()

func take_damage(amount: int) -> void:
    $HealthComponent.health -= amount
    if $HealthComponent.health <= 0:
        queue_free()
''',
    },
    "godot_signals": {
        "name": "Godot信号系统",
        "engine": "godot",
        "code": '''extends Node

signal health_changed(new_health: int)
signal player_died

@export var max_health: int = 100
var current_health: int = max_health

func take_damage(amount: int) -> void:
    current_health = max(0, current_health - amount)
    health_changed.emit(current_health)
    if current_health == 0:
        player_died.emit()

# 连接信号
func _ready():
    health_changed.connect(_on_health_changed)
    player_died.connect(_on_player_died)

func _on_health_changed(new_health: int) -> void:
    $HealthBar.value = new_health

func _on_player_died() -> void:
    get_tree().reload_current_scene()
''',
    },
}


def get_game_pattern(pattern: str) -> Dict:
    """获取游戏引擎模式模板"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in GAME_ENGINE_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in GAME_ENGINE_PATTERNS:
        p = GAME_ENGINE_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "engine": p["engine"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in GAME_ENGINE_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in GAME_ENGINE_PATTERNS.items()}}


# ==================== 44. 智能上下文路由 (维度7) ====================

CONTEXT_STRATEGIES = {
    "short": {
        "name": "短上下文(本地14B)",
        "max_tokens": 8192,
        "model": "local_14b",
        "strategy": "直接处理,无需分块",
        "tips": ["适合单文件编辑", "函数级代码生成", "快速问答"],
    },
    "medium": {
        "name": "中等上下文(GLM-4.5-Air)",
        "max_tokens": 32768,
        "model": "glm_4_5_air",
        "strategy": "符号索引+关键函数提取",
        "tips": ["多文件关联分析", "模块级重构", "API设计"],
    },
    "long": {
        "name": "长上下文(GLM-5 128K)",
        "max_tokens": 131072,
        "model": "glm_5",
        "strategy": "chunk_code_context分块+重叠行+符号索引",
        "tips": ["仓库级理解", "大型重构", "架构分析", "长文档生成"],
    },
}


def route_context(token_count: int, task_type: str = "general") -> Dict:
    """根据token数量和任务类型智能路由到最优上下文策略"""
    if token_count <= 0:
        return {"success": False, "error": "token_count必须>0"}

    complexity_boost = 1.0
    if task_type in ("refactor", "architecture", "migration"):
        complexity_boost = 1.5
    elif task_type in ("generate", "explain"):
        complexity_boost = 0.8

    effective = int(token_count * complexity_boost)

    if effective <= 6000:
        tier = "short"
    elif effective <= 28000:
        tier = "medium"
    else:
        tier = "long"

    strategy = CONTEXT_STRATEGIES[tier]
    return {
        "success": True,
        "input_tokens": token_count,
        "effective_tokens": effective,
        "task_type": task_type,
        "complexity_boost": complexity_boost,
        "tier": tier,
        "model": strategy["model"],
        "max_tokens": strategy["max_tokens"],
        "strategy": strategy["strategy"],
        "tips": strategy["tips"],
        "utilization": round(effective / strategy["max_tokens"] * 100, 1),
    }


# ==================== 45. 区块链智能合约 (维度86) ====================

SOLIDITY_PATTERNS = {
    "erc20_token": {
        "name": "ERC-20代币合约",
        "code": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyToken is ERC20, Ownable {
    uint256 public constant MAX_SUPPLY = 1_000_000 * 10**18;

    constructor() ERC20("MyToken", "MTK") Ownable(msg.sender) {
        _mint(msg.sender, MAX_SUPPLY);
    }

    function mint(address to, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }

    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
}
''',
    },
    "erc721_nft": {
        "name": "ERC-721 NFT合约",
        "code": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyNFT is ERC721, ERC721URIStorage, Ownable {
    uint256 private _nextTokenId;
    uint256 public mintPrice = 0.05 ether;

    constructor() ERC721("MyNFT", "MNFT") Ownable(msg.sender) {}

    function mint(string memory uri) external payable {
        require(msg.value >= mintPrice, "Insufficient payment");
        uint256 tokenId = _nextTokenId++;
        _safeMint(msg.sender, tokenId);
        _setTokenURI(tokenId, uri);
    }

    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage)
        returns (string memory) { return super.tokenURI(tokenId); }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721URIStorage)
        returns (bool) { return super.supportsInterface(interfaceId); }

    function withdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }
}
''',
    },
    "defi_staking": {
        "name": "DeFi质押合约",
        "code": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract Staking is ReentrancyGuard {
    IERC20 public stakingToken;
    uint256 public rewardRate = 100; // per second
    uint256 public lastUpdateTime;
    uint256 public rewardPerTokenStored;

    mapping(address => uint256) public userRewardPerTokenPaid;
    mapping(address => uint256) public rewards;
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    constructor(address _stakingToken) {
        stakingToken = IERC20(_stakingToken);
    }

    function stake(uint256 amount) external nonReentrant {
        _updateReward(msg.sender);
        totalSupply += amount;
        balances[msg.sender] += amount;
        stakingToken.transferFrom(msg.sender, address(this), amount);
    }

    function withdraw(uint256 amount) external nonReentrant {
        _updateReward(msg.sender);
        totalSupply -= amount;
        balances[msg.sender] -= amount;
        stakingToken.transfer(msg.sender, amount);
    }

    function _updateReward(address account) internal {
        rewardPerTokenStored = rewardPerToken();
        lastUpdateTime = block.timestamp;
        rewards[account] = earned(account);
        userRewardPerTokenPaid[account] = rewardPerTokenStored;
    }

    function rewardPerToken() public view returns (uint256) {
        if (totalSupply == 0) return rewardPerTokenStored;
        return rewardPerTokenStored +
            (block.timestamp - lastUpdateTime) * rewardRate * 1e18 / totalSupply;
    }

    function earned(address account) public view returns (uint256) {
        return balances[account] * (rewardPerToken() - userRewardPerTokenPaid[account]) / 1e18
            + rewards[account];
    }
}
''',
    },
    "hardhat_test": {
        "name": "Hardhat测试模板",
        "code": '''const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MyToken", function () {
  let token, owner, addr1;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const Token = await ethers.getContractFactory("MyToken");
    token = await Token.deploy();
  });

  it("Should have correct name and symbol", async function () {
    expect(await token.name()).to.equal("MyToken");
    expect(await token.symbol()).to.equal("MTK");
  });

  it("Should mint initial supply to owner", async function () {
    const balance = await token.balanceOf(owner.address);
    expect(balance).to.equal(ethers.parseEther("1000000"));
  });

  it("Should transfer tokens", async function () {
    await token.transfer(addr1.address, ethers.parseEther("100"));
    expect(await token.balanceOf(addr1.address))
      .to.equal(ethers.parseEther("100"));
  });

  it("Should fail if sender has insufficient balance", async function () {
    await expect(
      token.connect(addr1).transfer(owner.address, 1)
    ).to.be.reverted;
  });
});
''',
    },
}


def get_solidity_pattern(pattern: str) -> Dict:
    """获取Solidity智能合约模式"""
    if not pattern:
        return {"success": False, "error": "需要提供模式名",
                "available": {k: v["name"] for k, v in SOLIDITY_PATTERNS.items()}}

    pattern = pattern.lower().strip().replace(' ', '_').replace('-', '_')

    if pattern in SOLIDITY_PATTERNS:
        p = SOLIDITY_PATTERNS[pattern]
        return {
            "success": True,
            "pattern": pattern,
            "name": p["name"],
            "code": p["code"],
            "line_count": len(p["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in SOLIDITY_PATTERNS.items()
               if pattern in k or pattern in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{pattern}'", "similar": matches}

    return {"success": False, "error": f"未找到: {pattern}",
            "available": {k: v["name"] for k, v in SOLIDITY_PATTERNS.items()}}


# ==================== 46. VS Code LSP扩展脚手架 (维度63) ====================

VSCODE_EXT_TEMPLATES = {
    "extension_manifest": {
        "name": "package.json扩展清单",
        "code": '''{
  "name": "agi-coding-assistant",
  "displayName": "AGI Coding Assistant",
  "version": "0.1.0",
  "engines": { "vscode": "^1.85.0" },
  "categories": ["Programming Languages", "Linters", "Snippets"],
  "activationEvents": ["onLanguage:python", "onLanguage:javascript"],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [{
      "command": "agi.analyzeCode",
      "title": "AGI: Analyze Code"
    }],
    "configuration": {
      "title": "AGI Assistant",
      "properties": {
        "agi.serverUrl": { "type": "string", "default": "http://localhost:5000" },
        "agi.model": { "type": "string", "default": "local_14b" }
      }
    }
  }
}
''',
    },
    "lsp_server": {
        "name": "LSP Server实现",
        "code": '''from lsprotocol import types
from pygls.server import LanguageServer

server = LanguageServer("agi-lsp", "v0.1.0")

@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: types.DidOpenTextDocumentParams):
    _validate(params.text_document.uri)

@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def completions(params: types.CompletionParams):
    return types.CompletionList(is_incomplete=False, items=[
        types.CompletionItem(label="agi_suggest", kind=types.CompletionItemKind.Snippet),
    ])

@server.feature(types.TEXT_DOCUMENT_HOVER)
def hover(params: types.HoverParams):
    doc = server.workspace.get_text_document(params.text_document.uri)
    word = doc.word_at_position(params.position)
    return types.Hover(contents=types.MarkupContent(
        kind=types.MarkupKind.Markdown, value=f"**AGI**: `{word}`"))

def _validate(uri: str):
    doc = server.workspace.get_text_document(uri)
    diagnostics = []  # Run analysis here
    server.publish_diagnostics(uri, diagnostics)

if __name__ == "__main__":
    server.start_io()
''',
    },
    "extension_activate": {
        "name": "VS Code Extension激活",
        "code": '''import * as vscode from 'vscode';
import { LanguageClient, TransportKind } from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
  const serverModule = context.asAbsolutePath('server/lsp_server.py');
  const serverOptions = {
    run: { command: 'python', args: [serverModule], transport: TransportKind.stdio },
    debug: { command: 'python', args: [serverModule], transport: TransportKind.stdio },
  };
  const clientOptions = {
    documentSelector: [
      { scheme: 'file', language: 'python' },
      { scheme: 'file', language: 'javascript' },
    ],
  };
  client = new LanguageClient('agi-lsp', 'AGI LSP', serverOptions, clientOptions);
  client.start();

  context.subscriptions.push(
    vscode.commands.registerCommand('agi.analyzeCode', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const result = await client.sendRequest('agi/analyze', {
        uri: editor.document.uri.toString(),
      });
      vscode.window.showInformationMessage(`Analysis: ${JSON.stringify(result)}`);
    })
  );
}

export function deactivate() { return client?.stop(); }
''',
    },
    "diagnostic_provider": {
        "name": "诊断提供器",
        "code": '''import * as vscode from 'vscode';

const diagnosticCollection = vscode.languages.createDiagnosticCollection('agi');

export function updateDiagnostics(document: vscode.TextDocument): void {
  const diagnostics: vscode.Diagnostic[] = [];
  const text = document.getText();
  const lines = text.split('\\n');

  lines.forEach((line, i) => {
    // 检测TODO
    if (line.includes('TODO')) {
      diagnostics.push(new vscode.Diagnostic(
        new vscode.Range(i, line.indexOf('TODO'), i, line.length),
        'TODO found', vscode.DiagnosticSeverity.Information));
    }
    // 检测安全问题
    if (line.includes('eval(')) {
      diagnostics.push(new vscode.Diagnostic(
        new vscode.Range(i, line.indexOf('eval('), i, line.indexOf('eval(') + 5),
        'Avoid eval() - security risk', vscode.DiagnosticSeverity.Warning));
    }
  });

  diagnosticCollection.set(document.uri, diagnostics);
}
''',
    },
}


def get_vscode_template(template: str) -> Dict:
    """获取VS Code扩展开发模板"""
    if not template:
        return {"success": False, "error": "需要提供模板名",
                "available": {k: v["name"] for k, v in VSCODE_EXT_TEMPLATES.items()}}

    template = template.lower().strip().replace(' ', '_').replace('-', '_')

    if template in VSCODE_EXT_TEMPLATES:
        t = VSCODE_EXT_TEMPLATES[template]
        return {
            "success": True,
            "template": template,
            "name": t["name"],
            "code": t["code"],
            "line_count": len(t["code"].split('\n')),
        }

    matches = {k: v["name"] for k, v in VSCODE_EXT_TEMPLATES.items()
               if template in k or template in v["name"].lower()}
    if matches:
        return {"success": False, "error": f"未精确匹配'{template}'", "similar": matches}

    return {"success": False, "error": f"未找到: {template}",
            "available": {k: v["name"] for k, v in VSCODE_EXT_TEMPLATES.items()}}


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
    {
        "type": "function",
        "function": {
            "name": "chunk_code_context",
            "description": "将长代码分块保持连贯性:函数/类边界分割+重叠行+跨块符号索引。用于处理超长上下文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要分块的代码"},
                    "max_chunk_tokens": {"type": "integer", "description": "每块最大token数(默认3000)"},
                    "overlap_lines": {"type": "integer", "description": "块间重叠行数(默认5)"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "expand_template",
            "description": "低代码模板扩展为生产级代码。可用模板:crud_api/cli_tool/dataclass_model/test_suite。",
            "parameters": {
                "type": "object",
                "properties": {
                    "template_name": {"type": "string", "description": "模板名称(crud_api/cli_tool/dataclass_model/test_suite)"},
                    "resource_name": {"type": "string", "description": "资源名称(用于crud_api)"},
                    "tool_name": {"type": "string", "description": "工具名称(用于cli_tool)"},
                    "model_name": {"type": "string", "description": "模型名称(用于dataclass_model)"},
                    "module_name": {"type": "string", "description": "模块名称(用于test_suite)"},
                    "description": {"type": "string", "description": "描述(用于cli_tool)"}
                },
                "required": ["template_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parse_github_issue",
            "description": "解析GitHub Issue文本:自动分类(bug/feature/improvement)+优先级+代码引用+文件引用+任务分解。",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_text": {"type": "string", "description": "Issue的完整文本"}
                },
                "required": ["issue_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enforce_type_hints",
            "description": "分析Python代码类型注解覆盖率:检测缺失类型/返回值+常见类型错误模式+生成修复建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python代码"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_ui_component",
            "description": "生成UI组件(HTML+CSS)。可用组件:button/card/input/modal,支持多种变体和自定义参数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "component_type": {"type": "string", "description": "组件类型(button/card/input/modal)"},
                    "variant": {"type": "string", "description": "变体名称"},
                    "label": {"type": "string", "description": "按钮文本"},
                    "title": {"type": "string", "description": "标题"},
                    "content": {"type": "string", "description": "内容"}
                },
                "required": ["component_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "learn_code_style",
            "description": "分析代码风格特征:缩进/命名/引号/导入/文档风格,用于保持代码风格一致性。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要分析的代码"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_api",
            "description": "查询常用Python库API索引(18个库):返回函数名+返回类型。支持模糊匹配。",
            "parameters": {
                "type": "object",
                "properties": {
                    "module": {"type": "string", "description": "模块名(os/json/re/pandas/numpy等)"},
                    "function": {"type": "string", "description": "函数名(可选,用于精确查询)"}
                },
                "required": ["module"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_chart_code",
            "description": "生成matplotlib数据可视化代码。图表类型:line/bar/pie/scatter/heatmap。",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string", "description": "图表类型(line/bar/pie/scatter/heatmap)"},
                    "title": {"type": "string", "description": "图表标题"},
                    "x_data": {"type": "string", "description": "X轴数据"},
                    "y_data": {"type": "string", "description": "Y轴数据"}
                },
                "required": ["chart_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_algorithm_template",
            "description": "获取算法模板+复杂度分析。可用:binary_search/bfs/dfs/dp_knapsack/dijkstra/merge_sort/trie/union_find。",
            "parameters": {
                "type": "object",
                "properties": {
                    "algorithm": {"type": "string", "description": "算法名称"}
                },
                "required": ["algorithm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_ds_pipeline",
            "description": "生成完整数据科学Pipeline代码(加载→清洗→特征→分割→训练→评估)。支持classification/regression/clustering。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "任务类型(classification/regression/clustering)"},
                    "data_format": {"type": "string", "description": "数据格式(csv/json/excel/sql)"},
                    "target_col": {"type": "string", "description": "目标列名"}
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dp_pattern",
            "description": "获取DP/贪心模式模板。可用:linear_dp/interval_dp/tree_dp/greedy_interval/greedy_huffman。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_graph_algorithm",
            "description": "获取图算法模板。可用:topological_sort/kruskal_mst/a_star/floyd_warshall/tarjan_scc。",
            "parameters": {
                "type": "object",
                "properties": {
                    "algorithm": {"type": "string", "description": "图算法名称"}
                },
                "required": ["algorithm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cp_trick",
            "description": "获取竞赛编程技巧模板。可用:fast_io/mod_arithmetic/bit_manipulation/prefix_sum/binary_search_template/segment_tree。",
            "parameters": {
                "type": "object",
                "properties": {
                    "trick": {"type": "string", "description": "技巧名称"}
                },
                "required": ["trick"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_ml_model",
            "description": "根据任务类型和约束推荐ML模型(Top3)。支持classification/regression/clustering。",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "任务类型(classification/regression/clustering)"},
                    "data_size": {"type": "string", "description": "数据规模(small/medium/large)"},
                    "interpretable": {"type": "boolean", "description": "是否需要可解释性"}
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_framework_cheatsheet",
            "description": "获取框架速查表。可用:fastapi/nextjs/django/vue3/spring_boot/gin。含setup/hello_world/关键概念/常用模式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "framework": {"type": "string", "description": "框架名称"}
                },
                "required": ["framework"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plan_swe_fix",
            "description": "为GitHub Issue生成SWE-Agent修复计划(5步Pipeline:解析→定位→补丁→测试→验证)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_text": {"type": "string", "description": "Issue文本内容"}
                },
                "required": ["issue_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_nosql_template",
            "description": "获取NoSQL操作模板。可用DB:redis/mongodb/elasticsearch。支持指定操作类型。",
            "parameters": {
                "type": "object",
                "properties": {
                    "db": {"type": "string", "description": "数据库名称(redis/mongodb/elasticsearch)"},
                    "operation": {"type": "string", "description": "操作类型(可选,如string/hash/find/search)"}
                },
                "required": ["db"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_microservice_pattern",
            "description": "获取微服务架构模式模板。可用:api_gateway/service_discovery/circuit_breaker/event_driven/saga_pattern。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "微服务模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_jsts_snippet",
            "description": "获取JS/TS代码片段。可用:react_useState/react_useEffect/react_custom_hook/express_router/ts_utility_types/ts_zod_validation。",
            "parameters": {
                "type": "object",
                "properties": {
                    "snippet": {"type": "string", "description": "片段名称"}
                },
                "required": ["snippet"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_java_pattern",
            "description": "获取Java企业级模式。可用:spring_rest_controller/jpa_entity/service_layer/exception_handler/design_pattern_builder。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_go_pattern",
            "description": "获取Go并发模式。可用:goroutine_basic/channel_pipeline/worker_pool/context_cancel/select_fan_in/mutex_sync。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_rust_pattern",
            "description": "获取Rust安全模式。可用:ownership_borrow/lifetime/enum_pattern_match/error_handling/trait_impl。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_csharp_pattern",
            "description": "获取C# .NET模式。可用:aspnet_controller/ef_core_model/linq_queries/async_pattern/di_service。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_mobile_pattern",
            "description": "获取移动应用模式。可用:flutter_stateful/flutter_provider/flutter_http/swiftui_view/swiftui_mvvm。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_desktop_pattern",
            "description": "获取桌面应用模式。可用:electron_main/electron_preload/tauri_command/tauri_frontend。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_wasm_pattern",
            "description": "获取WebAssembly模式。可用:rust_wasm_basic/wasm_js_interop/wasm_js_load/wasm_wat_text。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_game_pattern",
            "description": "获取游戏引擎模式。可用:unity_monobehaviour/unity_scriptable_object/godot_gdscript/godot_signals。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "route_context",
            "description": "智能上下文路由。根据token数量和任务类型自动选择最优模型(short→14B/medium→GLM-4.5/long→GLM-5 128K)。",
            "parameters": {
                "type": "object",
                "properties": {
                    "token_count": {"type": "integer", "description": "输入token数量"},
                    "task_type": {"type": "string", "description": "任务类型:general/refactor/architecture/migration/generate/explain"}
                },
                "required": ["token_count"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_solidity_pattern",
            "description": "获取Solidity智能合约模式。可用:erc20_token/erc721_nft/defi_staking/hardhat_test。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "模式名称"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vscode_template",
            "description": "获取VS Code扩展开发模板。可用:extension_manifest/lsp_server/extension_activate/diagnostic_provider。",
            "parameters": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "模板名称"}
                },
                "required": ["template"]
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
    "chunk_code_context": lambda args: chunk_code_context(args.get("code", ""), args.get("max_chunk_tokens", 3000), args.get("overlap_lines", 5)),
    "expand_template": lambda args: expand_template(args.get("template_name", ""), **{k: v for k, v in args.items() if k != "template_name"}),
    "parse_github_issue": lambda args: parse_github_issue(args.get("issue_text", "")),
    "enforce_type_hints": lambda args: enforce_type_hints(args.get("code", "")),
    "generate_ui_component": lambda args: generate_ui_component(args.get("component_type", ""), **{k: v for k, v in args.items() if k != "component_type"}),
    "learn_code_style": lambda args: learn_code_style(args.get("code", "")),
    "lookup_api": lambda args: lookup_api(args.get("module", ""), args.get("function", "")),
    "generate_chart_code": lambda args: generate_chart_code(args.get("chart_type", ""), **{k: v for k, v in args.items() if k != "chart_type"}),
    "get_algorithm_template": lambda args: get_algorithm_template(args.get("algorithm", "")),
    "generate_ds_pipeline": lambda args: generate_ds_pipeline(args.get("task", "classification"), args.get("data_format", "csv"), args.get("target_col", "target")),
    "get_dp_pattern": lambda args: get_dp_pattern(args.get("pattern", "")),
    "get_graph_algorithm": lambda args: get_graph_algorithm(args.get("algorithm", "")),
    "get_cp_trick": lambda args: get_cp_trick(args.get("trick", "")),
    "recommend_ml_model": lambda args: recommend_ml_model(args.get("task", ""), args.get("data_size", "medium"), args.get("interpretable", False)),
    "get_framework_cheatsheet": lambda args: get_framework_cheatsheet(args.get("framework", "")),
    "plan_swe_fix": lambda args: plan_swe_fix(args.get("issue_text", "")),
    "get_nosql_template": lambda args: get_nosql_template(args.get("db", ""), args.get("operation", "")),
    "get_microservice_pattern": lambda args: get_microservice_pattern(args.get("pattern", "")),
    "get_jsts_snippet": lambda args: get_jsts_snippet(args.get("snippet", "")),
    "get_java_pattern": lambda args: get_java_pattern(args.get("pattern", "")),
    "get_go_pattern": lambda args: get_go_pattern(args.get("pattern", "")),
    "get_rust_pattern": lambda args: get_rust_pattern(args.get("pattern", "")),
    "get_csharp_pattern": lambda args: get_csharp_pattern(args.get("pattern", "")),
    "get_mobile_pattern": lambda args: get_mobile_pattern(args.get("pattern", "")),
    "get_desktop_pattern": lambda args: get_desktop_pattern(args.get("pattern", "")),
    "get_wasm_pattern": lambda args: get_wasm_pattern(args.get("pattern", "")),
    "get_game_pattern": lambda args: get_game_pattern(args.get("pattern", "")),
    "route_context": lambda args: route_context(args.get("token_count", 0), args.get("task_type", "general")),
    "get_solidity_pattern": lambda args: get_solidity_pattern(args.get("pattern", "")),
    "get_vscode_template": lambda args: get_vscode_template(args.get("template", "")),
}
