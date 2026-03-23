#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能: 代码库分析器 — 让 AGI 具备阅读和理解代码的能力
核心能力:
  1. 扫描项目结构（文件树+依赖关系图）
  2. 解析 Python 文件（类/函数/导入/全局变量）
  3. 提取代码模式和架构惯例
  4. 构建文件间依赖图
  5. 生成上下文摘要供 LLM 精确编辑

这使 AGI 能像 Cascade 一样"先读懂代码，再精准修改"。
"""

import os
import sys
import ast
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))

# ==================== AST 解析器 ====================

def parse_python_file(filepath):
    """解析单个 Python 文件，提取结构信息"""
    filepath = Path(filepath)
    if not filepath.exists() or filepath.suffix != '.py':
        return {"error": f"文件不存在或非Python: {filepath}"}

    try:
        source = filepath.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return {"error": str(e)}

    result = {
        "path": str(filepath),
        "name": filepath.name,
        "lines": source.count('\n') + 1,
        "size_bytes": len(source.encode('utf-8')),
        "imports": [],
        "from_imports": [],
        "classes": [],
        "functions": [],
        "global_vars": [],
        "docstring": None,
        "parse_error": None,
    }

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        result["parse_error"] = f"SyntaxError: line {e.lineno}: {e.msg}"
        # 即使解析失败也尝试提取 import
        for line in source.split('\n'):
            stripped = line.strip()
            if stripped.startswith('import '):
                result["imports"].append(stripped)
            elif stripped.startswith('from '):
                result["from_imports"].append(stripped)
        return result

    # 模块级 docstring
    if (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, (ast.Str, ast.Constant))):
        ds = tree.body[0].value
        result["docstring"] = (ds.s if isinstance(ds, ast.Str)
                               else str(ds.value))[:500]

    for node in ast.walk(tree):
        # imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                result["from_imports"].append({
                    "module": module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno
                })

    # 顶层定义
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            cls_info = _parse_class(node, source)
            result["classes"].append(cls_info)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            fn_info = _parse_function(node, source)
            result["functions"].append(fn_info)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    result["global_vars"].append({
                        "name": target.id,
                        "line": node.lineno,
                        "value_preview": ast.get_source_segment(source, node.value)[:100] if hasattr(ast, 'get_source_segment') and ast.get_source_segment(source, node.value) else "..."
                    })

    return result


def _parse_class(node, source):
    """解析类定义"""
    methods = []
    class_vars = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append({
                "name": item.name,
                "args": [a.arg for a in item.args.args if a.arg != 'self'],
                "line": item.lineno,
                "end_line": getattr(item, 'end_lineno', item.lineno),
                "decorators": [_decorator_name(d) for d in item.decorator_list],
                "docstring": ast.get_docstring(item) or None,
                "is_async": isinstance(item, ast.AsyncFunctionDef),
            })
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    class_vars.append(target.id)

    bases = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(f"{_attr_chain(base)}")

    return {
        "name": node.name,
        "bases": bases,
        "line": node.lineno,
        "end_line": getattr(node, 'end_lineno', node.lineno),
        "docstring": ast.get_docstring(node) or None,
        "methods": methods,
        "class_vars": class_vars,
        "decorators": [_decorator_name(d) for d in node.decorator_list],
        "method_count": len(methods),
    }


def _parse_function(node, source):
    """解析函数定义"""
    args = []
    for a in node.args.args:
        arg_info = {"name": a.arg}
        if a.annotation:
            arg_info["type"] = _annotation_str(a.annotation)
        args.append(arg_info)

    return_type = None
    if node.returns:
        return_type = _annotation_str(node.returns)

    return {
        "name": node.name,
        "args": args,
        "return_type": return_type,
        "line": node.lineno,
        "end_line": getattr(node, 'end_lineno', node.lineno),
        "decorators": [_decorator_name(d) for d in node.decorator_list],
        "docstring": ast.get_docstring(node) or None,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
    }


def _decorator_name(node):
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return _attr_chain(node)
    elif isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return "?"


def _attr_chain(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _annotation_str(node):
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return _attr_chain(node)
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Subscript):
        return f"{_annotation_str(node.value)}[...]"
    return "?"


# ==================== 项目结构扫描 ====================

IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', '.venv', 'venv',
               '.tox', '.mypy_cache', '.pytest_cache', 'dist', 'build',
               '.egg-info', '.eggs'}
IGNORE_EXTS = {'.pyc', '.pyo', '.so', '.dylib', '.o', '.a', '.db', '.sqlite3'}


def scan_project_tree(root_dir, max_depth=5, max_files=200):
    """扫描项目目录结构"""
    root = Path(root_dir)
    if not root.is_dir():
        return {"error": f"目录不存在: {root_dir}"}

    files = []
    dirs = []
    total_lines = 0
    extensions = defaultdict(int)

    def _scan(path, depth):
        nonlocal total_lines
        if depth > max_depth or len(files) >= max_files:
            return
        try:
            items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return

        for item in items:
            rel = str(item.relative_to(root))
            if item.is_dir():
                if item.name in IGNORE_DIRS or item.name.startswith('.'):
                    continue
                dirs.append(rel)
                _scan(item, depth + 1)
            elif item.is_file():
                if item.suffix in IGNORE_EXTS:
                    continue
                if len(files) >= max_files:
                    return
                size = item.stat().st_size
                extensions[item.suffix] += 1
                line_count = 0
                if item.suffix in ('.py', '.js', '.ts', '.html', '.css', '.md',
                                   '.json', '.yaml', '.yml', '.toml', '.sh'):
                    try:
                        line_count = item.read_text(errors='replace').count('\n') + 1
                        total_lines += line_count
                    except:
                        pass
                files.append({
                    "path": rel,
                    "ext": item.suffix,
                    "size": size,
                    "lines": line_count,
                })

    _scan(root, 0)

    return {
        "root": str(root),
        "total_files": len(files),
        "total_dirs": len(dirs),
        "total_lines": total_lines,
        "extensions": dict(extensions),
        "files": files,
        "dirs": dirs,
    }


# ==================== 依赖图 ====================

def build_dependency_graph(root_dir, py_only=True):
    """构建项目内 Python 文件的依赖图"""
    root = Path(root_dir)
    graph = {}  # file -> [imports]
    all_modules = {}  # module_name -> file_path

    # 收集所有 Python 模块
    for py_file in root.rglob("*.py"):
        if any(p in py_file.parts for p in IGNORE_DIRS):
            continue
        rel = str(py_file.relative_to(root))
        module = rel.replace('/', '.').replace('\\', '.').rstrip('.py')
        if module.endswith('.__init__'):
            module = module[:-9]
        all_modules[module] = rel
        all_modules[py_file.stem] = rel  # 简短名

    for py_file in root.rglob("*.py"):
        if any(p in py_file.parts for p in IGNORE_DIRS):
            continue
        rel = str(py_file.relative_to(root))
        parsed = parse_python_file(py_file)
        deps = set()

        for imp in parsed.get("imports", []):
            if isinstance(imp, dict):
                mod = imp["module"]
            else:
                mod = str(imp).replace("import ", "").strip().split()[0]
            if mod in all_modules:
                deps.add(all_modules[mod])

        for imp in parsed.get("from_imports", []):
            if isinstance(imp, dict):
                mod = imp["module"]
            else:
                parts = str(imp).split()
                mod = parts[1] if len(parts) > 1 else ""
            if mod in all_modules:
                deps.add(all_modules[mod])

        graph[rel] = sorted(deps - {rel})

    return {
        "files": len(graph),
        "edges": sum(len(v) for v in graph.values()),
        "graph": graph,
        "modules": {k: v for k, v in all_modules.items()},
    }


# ==================== 上下文提取 (为 LLM 准备精确编辑上下文) ====================

def extract_edit_context(filepath, target_name=None, context_lines=5):
    """提取文件中目标函数/类的上下文，用于精确编辑
    
    如果指定 target_name，只返回该函数/类的代码及其周围上下文。
    否则返回文件摘要。
    """
    filepath = Path(filepath)
    if not filepath.exists():
        return {"error": f"文件不存在: {filepath}"}

    source = filepath.read_text(encoding='utf-8', errors='replace')
    lines = source.split('\n')

    if not target_name:
        # 返回文件级摘要
        parsed = parse_python_file(filepath)
        summary_parts = []
        if parsed.get("docstring"):
            summary_parts.append(f"# 文件说明: {parsed['docstring'][:200]}")
        summary_parts.append(f"# 文件: {filepath.name} ({parsed.get('lines',0)} 行)")
        for cls in parsed.get("classes", []):
            methods_str = ", ".join(m["name"] for m in cls["methods"][:10])
            summary_parts.append(f"class {cls['name']}({', '.join(cls['bases'])}):  # line {cls['line']}")
            summary_parts.append(f"    # 方法: {methods_str}")
        for fn in parsed.get("functions", []):
            args_str = ", ".join(a["name"] for a in fn["args"][:5])
            summary_parts.append(f"def {fn['name']}({args_str}):  # line {fn['line']}")
        return {
            "filepath": str(filepath),
            "summary": "\n".join(summary_parts),
            "parsed": parsed,
        }

    # 查找目标
    parsed = parse_python_file(filepath)
    target = None
    for cls in parsed.get("classes", []):
        if cls["name"] == target_name:
            target = cls
            break
        for method in cls.get("methods", []):
            if method["name"] == target_name:
                target = method
                break
    if not target:
        for fn in parsed.get("functions", []):
            if fn["name"] == target_name:
                target = fn
                break

    if not target:
        return {"error": f"未找到 '{target_name}' in {filepath.name}"}

    start = max(0, target["line"] - 1 - context_lines)
    end = min(len(lines), target.get("end_line", target["line"]) + context_lines)

    return {
        "filepath": str(filepath),
        "target": target_name,
        "start_line": start + 1,
        "end_line": end,
        "code": "\n".join(f"{i+start+1:4d}| {lines[i+start]}" for i in range(end - start)),
        "target_info": target,
    }


def build_file_context_for_llm(filepath, max_tokens_approx=3000):
    """为 LLM 构建紧凑的文件上下文，包含结构摘要+关键代码"""
    filepath = Path(filepath)
    if not filepath.exists():
        return ""

    source = filepath.read_text(encoding='utf-8', errors='replace')
    lines = source.split('\n')
    parsed = parse_python_file(filepath)

    parts = [f"=== {filepath.name} ({len(lines)} lines) ==="]

    # docstring
    if parsed.get("docstring"):
        parts.append(f'"""{parsed["docstring"][:200]}"""')

    # imports (compact)
    imports = []
    for imp in parsed.get("imports", []):
        if isinstance(imp, dict):
            imports.append(f"import {imp['module']}")
    for imp in parsed.get("from_imports", []):
        if isinstance(imp, dict):
            imports.append(f"from {imp['module']} import {imp['name']}")
    if imports:
        parts.append("# Imports: " + "; ".join(imports[:15]))

    # global vars
    gvars = parsed.get("global_vars", [])
    if gvars:
        parts.append("# Globals: " + ", ".join(g["name"] for g in gvars[:10]))

    # classes with method signatures
    for cls in parsed.get("classes", []):
        bases_str = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
        parts.append(f"\nclass {cls['name']}{bases_str}:  # L{cls['line']}-{cls['end_line']}")
        if cls.get("docstring"):
            parts.append(f'    """{cls["docstring"][:100]}"""')
        for m in cls["methods"]:
            args = ", ".join(a if isinstance(a, str) else a.get("name", "?") for a in m.get("args", []))
            async_prefix = "async " if m.get("is_async") else ""
            parts.append(f"    {async_prefix}def {m['name']}({args}):  # L{m['line']}")
            if m.get("docstring"):
                parts.append(f'        """{m["docstring"][:80]}"""')

    # top-level functions
    for fn in parsed.get("functions", []):
        args = ", ".join(a["name"] for a in fn["args"][:8])
        ret = f" -> {fn['return_type']}" if fn.get("return_type") else ""
        async_prefix = "async " if fn.get("is_async") else ""
        parts.append(f"\n{async_prefix}def {fn['name']}({args}){ret}:  # L{fn['line']}-{fn['end_line']}")
        if fn.get("docstring"):
            parts.append(f'    """{fn["docstring"][:100]}"""')

    context = "\n".join(parts)
    # 粗略截断
    if len(context) > max_tokens_approx * 4:
        context = context[:max_tokens_approx * 4] + "\n... (truncated)"
    return context


# ==================== 项目级分析 ====================

def analyze_project(root_dir):
    """完整项目分析：结构+依赖+模式识别"""
    root = Path(root_dir)
    tree = scan_project_tree(root)
    dep_graph = build_dependency_graph(root)

    # 识别项目类型
    project_type = "unknown"
    markers = {
        "flask": ["app.py", "api_server.py"],
        "django": ["manage.py", "settings.py"],
        "fastapi": ["main.py"],
        "cli": ["__main__.py"],
        "library": ["setup.py", "pyproject.toml"],
    }
    file_names = {Path(f["path"]).name for f in tree.get("files", [])}
    for ptype, pmarkers in markers.items():
        if any(m in file_names for m in pmarkers):
            project_type = ptype
            break

    # 检测依赖管理
    dep_files = []
    for f in tree.get("files", []):
        name = Path(f["path"]).name
        if name in ("requirements.txt", "pyproject.toml", "setup.py",
                     "Pipfile", "poetry.lock", "package.json"):
            dep_files.append(f["path"])

    # 找到入口点
    entry_points = []
    for f in tree.get("files", []):
        if f["ext"] == ".py":
            fpath = root / f["path"]
            try:
                content = fpath.read_text(errors='replace')
                if '__name__' in content and '__main__' in content:
                    entry_points.append(f["path"])
            except:
                pass

    # 识别架构模式
    patterns = []
    class_count = 0
    func_count = 0
    for f in tree.get("files", []):
        if f["ext"] == ".py":
            parsed = parse_python_file(root / f["path"])
            class_count += len(parsed.get("classes", []))
            func_count += len(parsed.get("functions", []))

    if class_count > func_count * 0.5:
        patterns.append("OOP-heavy")
    if class_count < func_count * 0.2:
        patterns.append("functional-style")
    if any("async" in str(f) for f in tree.get("files", [])):
        patterns.append("async-capable")

    return {
        "root": str(root),
        "project_type": project_type,
        "tree": tree,
        "dependency_graph": dep_graph,
        "dependency_files": dep_files,
        "entry_points": entry_points,
        "patterns": patterns,
        "stats": {
            "total_files": tree["total_files"],
            "total_lines": tree["total_lines"],
            "total_classes": class_count,
            "total_functions": func_count,
            "python_files": tree["extensions"].get(".py", 0),
        }
    }


def get_relevant_context(root_dir, task_description, max_files=5):
    """根据任务描述，智能选择最相关的文件上下文
    
    使用关键词匹配+依赖图来选择需要阅读的文件。
    这模拟了 Cascade 在编辑前"先读相关文件"的行为。
    """
    root = Path(root_dir)
    tree = scan_project_tree(root)
    dep_graph = build_dependency_graph(root)

    # 提取任务中的关键词
    task_lower = task_description.lower()
    keywords = set(re.findall(r'[a-zA-Z_]\w+', task_lower))

    scored_files = []
    for f in tree.get("files", []):
        if f["ext"] != ".py":
            continue
        fpath = root / f["path"]
        try:
            content = fpath.read_text(errors='replace').lower()
        except:
            continue

        score = 0
        # 文件名匹配
        fname_lower = Path(f["path"]).stem.lower()
        for kw in keywords:
            if kw in fname_lower:
                score += 10
            if kw in content:
                score += 1

        # 依赖图中心性（被更多文件引用的更重要）
        imports_count = sum(1 for deps in dep_graph.get("graph", {}).values()
                          if f["path"] in deps)
        score += imports_count * 2

        # 入口点加分
        if '__main__' in content and '__name__' in content:
            score += 5

        if score > 0:
            scored_files.append((score, f["path"]))

    scored_files.sort(reverse=True)
    selected = [fp for _, fp in scored_files[:max_files]]

    contexts = []
    for fp in selected:
        ctx = build_file_context_for_llm(root / fp)
        contexts.append(ctx)

    return {
        "selected_files": selected,
        "contexts": contexts,
        "combined_context": "\n\n".join(contexts),
    }


# ==================== 技能元数据 ====================
SKILL_META = {
    "name": "代码库分析器",
    "description": "扫描项目结构、解析代码、构建依赖图、提取编辑上下文。让AGI像Cascade一样先读懂代码再修改。",
    "tags": ["代码分析", "AST解析", "依赖图", "上下文提取"],
    "version": "1.0",
    "capabilities": [
        "parse_python_file", "scan_project_tree", "build_dependency_graph",
        "extract_edit_context", "build_file_context_for_llm", "analyze_project",
        "get_relevant_context"
    ]
}

if __name__ == "__main__":
    print("=== 代码库分析器自测 ===")
    project = analyze_project(PROJECT_DIR)
    print(f"项目类型: {project['project_type']}")
    print(f"文件数: {project['stats']['total_files']}")
    print(f"总行数: {project['stats']['total_lines']}")
    print(f"类: {project['stats']['total_classes']}")
    print(f"函数: {project['stats']['total_functions']}")
    print(f"入口: {project['entry_points']}")
    print(f"模式: {project['patterns']}")
