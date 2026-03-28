#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI v13.3 核心模块测试套件
===========================
覆盖维度25-27: 测试用例生成/单元测试/集成测试
"""

# [PATH_BOOTSTRAP]
import sys as _sys, os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _d in [_PROJECT_ROOT, _os.path.join(_PROJECT_ROOT, 'core'), _os.path.join(_PROJECT_ROOT, 'api')]:
    if _d not in _sys.path:
        _sys.path.insert(0, _d)



import pytest
import sys
import os
import json
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==================== ToolController 测试 ====================

class TestPersistentRuntime:
    """测试持久化Python运行时"""

    def setup_method(self):
        from tool_controller import PersistentRuntime
        self.runtime = PersistentRuntime()

    def test_basic_execution(self):
        result = self.runtime.execute("x = 42\nprint(x)")
        assert result["success"] is True
        assert "42" in result["stdout"]

    def test_variable_persistence(self):
        self.runtime.execute("counter = 100")
        result = self.runtime.execute("print(counter + 1)")
        assert result["success"] is True
        assert "101" in result["stdout"]

    def test_import_works(self):
        result = self.runtime.execute("import math\nprint(math.pi)")
        assert result["success"] is True
        assert "3.14" in result["stdout"]

    def test_timeout_protection(self):
        result = self.runtime.execute("import time; time.sleep(60)", timeout=2)
        assert result["success"] is False
        assert "超时" in result.get("error", "")

    def test_syntax_error_handled(self):
        result = self.runtime.execute("def bad(:\n  pass")
        assert result["success"] is False
        assert "error" in result or "traceback" in result

    def test_reset_clears_variables(self):
        self.runtime.execute("persist_var = 999")
        self.runtime.reset()
        result = self.runtime.execute("print(persist_var)")
        assert result["success"] is False

    def test_stats_tracking(self):
        self.runtime.execute("x = 1")
        self.runtime.execute("y = 2")
        stats = self.runtime.stats
        assert stats["total_executions"] >= 2
        assert stats["successful"] >= 2


class TestToolExecution:
    """测试工具执行器"""

    def test_execute_tool_unknown(self):
        from tool_controller import execute_tool
        result = execute_tool("nonexistent_tool", {})
        assert result["success"] is False
        assert "未知工具" in result["error"]

    def test_shell_dangerous_blocked(self):
        from tool_controller import _exec_shell
        result = _exec_shell("rm -rf /")
        assert result["success"] is False
        assert "危险" in result["error"]

    def test_shell_safe_command(self):
        from tool_controller import _exec_shell
        result = _exec_shell("echo hello")
        assert result["success"] is True
        assert "hello" in result["stdout"]

    def test_read_file_nonexistent(self):
        from tool_controller import _read_file
        result = _read_file("/nonexistent/file.txt")
        assert result["success"] is False

    def test_write_and_read_file(self):
        from tool_controller import _write_file, _read_file
        test_path = str(PROJECT_ROOT / "workspace" / "outputs" / "_test_rw.txt")
        write_result = _write_file(test_path, "test content 测试")
        assert write_result["success"] is True
        read_result = _read_file(test_path)
        assert read_result["success"] is True
        assert "test content 测试" in read_result["content"]
        # cleanup
        os.unlink(test_path)

    def test_list_skills(self):
        from tool_controller import _list_skills
        result = _list_skills()
        assert result["success"] is True
        assert "count" in result
        assert isinstance(result["skills"], list)


# ==================== CodingEnhancer 测试 ====================

class TestCodingEnhancer:
    """测试编码增强模块"""

    def test_analyze_code_structure(self):
        from coding_enhancer import analyze_code_structure
        code = '''
def hello(name):
    """Say hello"""
    return f"Hello {name}"

class MyClass:
    def method(self):
        pass
'''
        result = analyze_code_structure(code=code)
        assert result["success"] is True
        assert result["function_count"] >= 1
        assert result["class_count"] >= 1
        assert result["total_lines"] > 0

    def test_analyze_code_syntax_error(self):
        from coding_enhancer import analyze_code_structure
        result = analyze_code_structure(code="def bad(:\n  pass")
        assert result["success"] is False

    def test_code_review(self):
        from coding_enhancer import code_review
        code = '''
import os
def process(data):
    result = eval(data)  # dangerous
    return result
'''
        result = code_review(code)
        assert result["success"] is True
        assert result["total_issues"] > 0
        assert any(i["type"] == "security" for i in result["issues"])

    def test_code_review_clean(self):
        from coding_enhancer import code_review
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        result = code_review(code)
        assert result["success"] is True
        assert result["grade"] in ("A", "A-")

    def test_generate_test(self):
        from coding_enhancer import generate_test
        code = '''
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
'''
        result = generate_test(code)
        assert result["success"] is True
        assert result["test_count"] >= 2
        assert "def test_" in result["test_code"]

    def test_analyze_dependencies(self):
        from coding_enhancer import analyze_dependencies
        result = analyze_dependencies(str(PROJECT_ROOT))
        assert result["success"] is True
        assert len(result["files"]) > 0
        assert "dependency_graph" in result

    def test_analyze_tech_debt(self):
        from coding_enhancer import analyze_tech_debt
        result = analyze_tech_debt(str(PROJECT_ROOT))
        assert result["success"] is True
        assert result["health"] in ("GOOD", "FAIR", "WARNING", "CRITICAL")
        assert "total_items" in result


# ==================== 异常层级测试 ====================

class TestExceptions:
    """测试自定义异常层级"""

    def test_exception_hierarchy(self):
        from agi_exceptions import (
            AGIBaseError, LLMError, LLMTimeoutError,
            ToolError, ToolNotFoundError, SecurityError
        )
        assert issubclass(LLMTimeoutError, LLMError)
        assert issubclass(LLMError, AGIBaseError)
        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(SecurityError, AGIBaseError)

    def test_exception_context(self):
        from agi_exceptions import LLMTimeoutError
        err = LLMTimeoutError("timeout after 30s", context={"model": "glm-4"})
        assert str(err) == "timeout after 30s"
        assert err.context["model"] == "glm-4"


# ==================== 日志系统测试 ====================

class TestLogger:
    """测试结构化日志系统"""

    def test_get_logger(self):
        from agi_logger import get_logger
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "agi.test_module"

    def test_metrics_collector(self):
        from agi_logger import MetricsCollector
        m = MetricsCollector()
        m.inc("requests_total", 1)
        m.inc("requests_total", 1)
        m.set_gauge("active_connections", 5)
        m.observe("response_time", 0.15)
        m.observe("response_time", 0.25)

        summary = m.get_summary()
        assert summary["counters"]["requests_total"] == 2
        assert summary["gauges"]["active_connections"] == 5

        prom = m.export_prometheus()
        assert "requests_total" in prom
        assert "active_connections" in prom


# ==================== 安全测试 ====================

@pytest.mark.security
class TestSecurity:
    """安全相关测试"""

    def test_sql_injection_prevention(self):
        """验证SQL注入已被参数化查询阻止"""
        from tool_controller import _query_knowledge
        # 这些恶意输入不应导致SQL错误或数据泄露
        malicious_inputs = [
            "'; DROP TABLE cognitive_nodes; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM sqlite_master --",
        ]
        for payload in malicious_inputs:
            result = _query_knowledge(payload, 3)
            # 应该安全返回(可能无结果),不应崩溃
            assert "success" in result

    def test_dangerous_shell_commands_blocked(self):
        from tool_controller import _exec_shell, DANGEROUS_KEYWORDS
        for kw in DANGEROUS_KEYWORDS:
            result = _exec_shell(f"echo test && {kw}")
            assert result["success"] is False

    def test_file_path_traversal(self):
        from action_engine import FileAction
        result = FileAction.create_file("/etc/passwd_test", "hack")
        assert result["success"] is False


# ==================== ActionEngine 测试 ====================

class TestActionEngine:
    """测试动作引擎"""

    def test_file_create_in_workspace(self):
        from action_engine import FileAction
        result = FileAction.create_file(
            "outputs/_test_action.txt", "test content", "test file")
        assert result["success"] is True
        # cleanup
        test_path = PROJECT_ROOT / "workspace" / "outputs" / "_test_action.txt"
        if test_path.exists():
            test_path.unlink()

    def test_file_read_nonexistent(self):
        from action_engine import FileAction
        result = FileAction.read_file("nonexistent_xyz.py")
        assert result["success"] is False

    def test_list_workspace(self):
        from action_engine import FileAction
        files = FileAction.list_workspace()
        assert isinstance(files, list)

    def test_skill_builder_list(self):
        from action_engine import SkillBuilder
        skills = SkillBuilder.list_skills()
        assert isinstance(skills, list)

    def test_detect_action_intent(self):
        from action_engine import _detect_action_intent
        assert _detect_action_intent("请创建一个Python脚本") is True
        assert _detect_action_intent("在桌面生成一个文件") is True
        assert _detect_action_intent("什么是量子力学") is False

    def test_run_python_code(self):
        from action_engine import ExecuteAction
        result = ExecuteAction.run_python(code="print('hello from test')")
        assert result["success"] is True
        assert "hello from test" in result["stdout"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
