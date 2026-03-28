#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 错误分类器与修复策略
================================
自动分类代码执行错误，匹配修复策略，提升Agent迭代修复成功率。
对应维度10: Agent迭代修复成功率
对应维度69: 自我纠错能力
对应维度15: 运行时错误发生率(预检)
"""

import re
import ast
from typing import Dict, List, Optional, Tuple


# ==================== 错误分类 ====================

class ErrorCategory:
    IMPORT = "import_error"
    SYNTAX = "syntax_error"
    TYPE = "type_error"
    NAME = "name_error"
    INDEX = "index_error"
    KEY = "key_error"
    VALUE = "value_error"
    ATTRIBUTE = "attribute_error"
    FILE = "file_error"
    PERMISSION = "permission_error"
    TIMEOUT = "timeout_error"
    MEMORY = "memory_error"
    NETWORK = "network_error"
    API = "api_error"
    LOGIC = "logic_error"
    UNKNOWN = "unknown_error"


# ==================== 修复策略库 ====================

REPAIR_STRATEGIES = {
    ErrorCategory.IMPORT: {
        "priority": 1,
        "strategies": [
            {"name": "install_package", "description": "自动安装缺失的包",
             "template": "pip install {package}",
             "pattern": r"No module named '(\w+)'"},
            {"name": "fix_import_path", "description": "修复导入路径",
             "template": "检查sys.path或修改import语句"},
            {"name": "conditional_import", "description": "添加条件导入+回退",
             "template": "try:\n    import {mod}\nexcept ImportError:\n    {mod} = None"},
        ]
    },
    ErrorCategory.SYNTAX: {
        "priority": 0,
        "strategies": [
            {"name": "fix_syntax", "description": "修复语法错误(括号/缩进/冒号)",
             "template": "检查第{line}行附近的括号匹配/缩进/冒号"},
            {"name": "ast_validate", "description": "AST预校验",
             "template": "ast.parse(code) 预检"},
        ]
    },
    ErrorCategory.TYPE: {
        "priority": 2,
        "strategies": [
            {"name": "type_cast", "description": "添加类型转换",
             "template": "在操作前添加 int()/str()/float() 转换"},
            {"name": "none_check", "description": "添加None检查",
             "template": "if value is not None: ..."},
        ]
    },
    ErrorCategory.NAME: {
        "priority": 1,
        "strategies": [
            {"name": "define_variable", "description": "定义缺失变量",
             "template": "检查变量 '{name}' 是否已定义或拼写错误"},
            {"name": "scope_fix", "description": "修复作用域问题",
             "template": "检查变量是否在正确的作用域内"},
        ]
    },
    ErrorCategory.INDEX: {
        "priority": 2,
        "strategies": [
            {"name": "bounds_check", "description": "添加边界检查",
             "template": "if idx < len(collection): ..."},
            {"name": "safe_access", "description": "安全访问",
             "template": "collection[idx] if idx < len(collection) else default"},
        ]
    },
    ErrorCategory.KEY: {
        "priority": 2,
        "strategies": [
            {"name": "dict_get", "description": "使用.get()安全访问",
             "template": "dict.get(key, default_value)"},
            {"name": "key_check", "description": "先检查key存在性",
             "template": "if key in dict: ..."},
        ]
    },
    ErrorCategory.ATTRIBUTE: {
        "priority": 2,
        "strategies": [
            {"name": "hasattr_check", "description": "使用hasattr检查",
             "template": "if hasattr(obj, 'attr'): ..."},
            {"name": "type_check", "description": "检查对象类型",
             "template": "确认对象类型是否正确"},
        ]
    },
    ErrorCategory.FILE: {
        "priority": 2,
        "strategies": [
            {"name": "create_dir", "description": "创建缺失目录",
             "template": "Path(path).parent.mkdir(parents=True, exist_ok=True)"},
            {"name": "path_check", "description": "检查路径是否存在",
             "template": "if Path(path).exists(): ..."},
        ]
    },
    ErrorCategory.NETWORK: {
        "priority": 3,
        "strategies": [
            {"name": "retry", "description": "添加重试逻辑",
             "template": "for i in range(3):\n    try: ...\n    except: time.sleep(1)"},
            {"name": "timeout_increase", "description": "增加超时时间",
             "template": "timeout=30 → timeout=60"},
        ]
    },
    ErrorCategory.API: {
        "priority": 3,
        "strategies": [
            {"name": "api_key_check", "description": "检查API密钥",
             "template": "确认API key是否已配置且有效"},
            {"name": "rate_limit_wait", "description": "等待限流恢复",
             "template": "time.sleep(backoff)后重试"},
        ]
    },
}


def classify_error(error_text: str, traceback_text: str = "") -> Dict:
    """分类错误并返回修复建议"""
    full_text = f"{error_text}\n{traceback_text}".lower()

    # 错误类型匹配
    category = ErrorCategory.UNKNOWN
    details = {}

    if "modulenotfounderror" in full_text or "no module named" in full_text:
        category = ErrorCategory.IMPORT
        m = re.search(r"no module named '?(\w+)'?", full_text)
        if m:
            details["package"] = m.group(1)

    elif "syntaxerror" in full_text or "indentationerror" in full_text:
        category = ErrorCategory.SYNTAX
        m = re.search(r"line (\d+)", full_text)
        if m:
            details["line"] = int(m.group(1))

    elif "typeerror" in full_text:
        category = ErrorCategory.TYPE
        if "nonetype" in full_text:
            details["subtype"] = "none_operation"
        elif "unsupported operand" in full_text:
            details["subtype"] = "operand_mismatch"

    elif "nameerror" in full_text:
        category = ErrorCategory.NAME
        m = re.search(r"name '(\w+)' is not defined", full_text)
        if m:
            details["name"] = m.group(1)

    elif "indexerror" in full_text:
        category = ErrorCategory.INDEX

    elif "keyerror" in full_text:
        category = ErrorCategory.KEY
        m = re.search(r"keyerror: '?(\w+)'?", full_text)
        if m:
            details["key"] = m.group(1)

    elif "attributeerror" in full_text:
        category = ErrorCategory.ATTRIBUTE
        m = re.search(r"has no attribute '(\w+)'", full_text)
        if m:
            details["attribute"] = m.group(1)

    elif "filenotfounderror" in full_text or "no such file" in full_text:
        category = ErrorCategory.FILE

    elif "permissionerror" in full_text:
        category = ErrorCategory.PERMISSION

    elif "timeout" in full_text or "timed out" in full_text:
        category = ErrorCategory.TIMEOUT

    elif "memoryerror" in full_text or "out of memory" in full_text:
        category = ErrorCategory.MEMORY

    elif "connectionerror" in full_text or "urlerror" in full_text:
        category = ErrorCategory.NETWORK

    elif "401" in full_text or "403" in full_text or "api" in full_text:
        category = ErrorCategory.API

    # 获取修复策略
    strategy_info = REPAIR_STRATEGIES.get(category, {})
    strategies = strategy_info.get("strategies", [])

    # 填充模板
    resolved_strategies = []
    for s in strategies:
        template = s["template"]
        for k, v in details.items():
            template = template.replace(f"{{{k}}}", str(v))
        resolved_strategies.append({
            "name": s["name"],
            "description": s["description"],
            "action": template,
        })

    return {
        "category": category,
        "details": details,
        "priority": strategy_info.get("priority", 5),
        "strategies": resolved_strategies,
        "repair_prompt": _build_repair_prompt(category, error_text, details, resolved_strategies),
    }


def _build_repair_prompt(category: str, error: str, details: Dict,
                          strategies: List[Dict]) -> str:
    """生成修复指令prompt"""
    lines = [f"代码执行失败，错误类型: {category}"]
    lines.append(f"错误信息: {error[:200]}")

    if details:
        lines.append(f"错误细节: {details}")

    if strategies:
        lines.append("\n建议修复策略:")
        for i, s in enumerate(strategies, 1):
            lines.append(f"  {i}. {s['description']}: {s['action']}")

    lines.append("\n请按以上策略修复代码后重新执行。")
    return "\n".join(lines)


# ==================== 代码预检 (维度15: 降低运行时错误) ====================

def pre_check_code(code: str) -> Dict:
    """代码执行前预检: 语法/导入/常见问题"""
    issues = []

    # 1. 语法检查
    try:
        ast.parse(code)
    except SyntaxError as e:
        issues.append({
            "type": "syntax",
            "severity": "CRITICAL",
            "message": f"语法错误(行{e.lineno}): {e.msg}",
            "line": e.lineno,
            "auto_fixable": False,
        })
        return {"safe_to_run": False, "issues": issues}

    tree = ast.parse(code)

    # 2. 导入检查
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split('.')[0]
                if mod in ('os', 'sys', 'subprocess', 'shutil'):
                    issues.append({
                        "type": "security",
                        "severity": "WARNING",
                        "message": f"导入了系统模块: {mod} (请确认安全性)",
                        "line": node.lineno,
                        "auto_fixable": False,
                    })

    # 3. 常见问题检查
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # 无限循环检测
        if stripped.startswith('while True') and 'break' not in code[code.index(stripped):]:
            issues.append({
                "type": "logic",
                "severity": "WARNING",
                "message": f"行{i}: while True 未发现 break, 可能导致无限循环",
                "line": i,
                "auto_fixable": False,
            })
        # 硬编码密钥检测
        if re.search(r'(api_key|password|secret)\s*=\s*["\'][^"\']{8,}', stripped, re.I):
            issues.append({
                "type": "security",
                "severity": "HIGH",
                "message": f"行{i}: 疑似硬编码密钥/密码",
                "line": i,
                "auto_fixable": False,
            })

    critical = sum(1 for i in issues if i["severity"] == "CRITICAL")
    return {
        "safe_to_run": critical == 0,
        "issues": issues,
        "summary": f"预检: {len(issues)}个问题 ({critical}个严重)",
    }


# ==================== 修复历史学习 ====================

class RepairHistory:
    """记录修复历史，学习常见错误模式"""

    def __init__(self):
        self._history: List[Dict] = []

    def record(self, error_category: str, strategy_name: str, success: bool):
        self._history.append({
            "category": error_category,
            "strategy": strategy_name,
            "success": success,
        })

    def best_strategy(self, category: str) -> Optional[str]:
        """基于历史成功率返回最佳修复策略"""
        relevant = [h for h in self._history if h["category"] == category]
        if not relevant:
            return None

        strategy_scores = {}
        for h in relevant:
            s = h["strategy"]
            if s not in strategy_scores:
                strategy_scores[s] = {"success": 0, "total": 0}
            strategy_scores[s]["total"] += 1
            if h["success"]:
                strategy_scores[s]["success"] += 1

        best = max(strategy_scores.items(),
                   key=lambda x: x[1]["success"] / max(x[1]["total"], 1))
        return best[0]

    def stats(self) -> Dict:
        total = len(self._history)
        success = sum(1 for h in self._history if h["success"])
        return {
            "total_repairs": total,
            "success_rate": round(success / max(total, 1), 2),
            "by_category": {},
        }


# 全局修复历史
repair_history = RepairHistory()
