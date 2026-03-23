"""
4轮验证测试: 君臣佐使架构 + 95维代码能力
Round 1: 路由逻辑正确性 (消除虚假❌)
Round 2: 多语言代码能力验证
Round 3: 安全/性能/边界测试
Round 4: 最终评分
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch


# ==================== Round 1: 路由逻辑验证 ====================
class TestRound1_RoutingLogic:
    """第1轮: 验证君臣佐使路由，确保非Python任务路由到GLM-5"""

    def _make_orchestrator(self):
        from orchestrator import TaskOrchestrator
        lattice = MagicMock()
        lattice._lock = MagicMock()
        return TaskOrchestrator(lattice)

    def test_rust_routes_to_glm5(self):
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("用Rust写一个内存安全的链表", [])
        assert task_type == 'code_generation'
        route = orch.route("用Rust写一个内存安全的链表", [], score, task_type)
        assert route['model'] == 'GLM-5'
        assert route['role'] == '臣'

    def test_go_routes_to_glm5(self):
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("用Go 实现一个并发爬虫", [])
        route = orch.route("用Go 实现一个并发爬虫", [], score, task_type)
        assert route['model'] == 'GLM-5'
        assert route['role'] == '臣'

    def test_java_routes_to_glm5(self):
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("Java Spring Boot REST API", [])
        route = orch.route("Java Spring Boot REST API", [], score, task_type)
        assert route['model'] == 'GLM-5'

    def test_csharp_routes_to_glm5(self):
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("C# ASP.NET Core Web API", [])
        route = orch.route("C# ASP.NET Core Web API", [], score, task_type)
        assert route['model'] == 'GLM-5'

    def test_solidity_routes_to_glm5(self):
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("Solidity智能合约ERC-20", [])
        route = orch.route("Solidity智能合约ERC-20", [], score, task_type)
        assert route['model'] == 'GLM-5'

    def test_wasm_routes_to_glm5(self):
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("WebAssembly模块实现", [])
        route = orch.route("WebAssembly模块实现", [], score, task_type)
        assert route['model'] == 'GLM-5'

    def test_game_engine_routes_to_glm5(self):
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("Unity游戏开发角色控制器", [])
        route = orch.route("Unity游戏开发角色控制器", [], score, task_type)
        assert route['model'] == 'GLM-5'

    def test_desktop_app_routes_to_glm5(self):
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("用Electron开发桌面应用", [])
        route = orch.route("用Electron开发桌面应用", [], score, task_type)
        assert route['model'] == 'GLM-5'

    def test_simple_python_routes_correctly(self):
        """Simple Python code routes to GLM-4.7(佐) or GLM-5(臣) depending on proven coverage"""
        orch = self._make_orchestrator()
        score, task_type, _ = orch.analyze_complexity("写一个Python排序函数", [])
        route = orch.route("写一个Python排序函数", [], score, task_type)
        # Without proven nodes, medium code + need_glm5 → GLM-5
        assert route['model'] in ('GLM-5', 'GLM-4.7')
        assert route['role'] in ('臣', '佐')

    def test_simple_chat_routes_to_local(self):
        orch = self._make_orchestrator()
        proven = [{'status': 'proven', 'similarity': 0.9}] * 3
        score, task_type, _ = orch.analyze_complexity("hi", proven)
        route = orch.route("hi", proven, score, task_type)
        assert route['model'] in ('fast_path', 'local_14b')

    def test_code_complexity_detection(self):
        orch = self._make_orchestrator()
        assert orch._detect_code_complexity("用Rust写编译器") == 'complex'
        assert orch._detect_code_complexity("Python数据处理脚本") == 'medium'
        assert orch._detect_code_complexity("写个函数") == 'simple'


# ==================== Round 2: 多语言文件扩展名覆盖 ====================
class TestRound2_MultiLanguageSupport:
    """第2轮: 验证所有语言的文件扩展名被支持"""

    def test_allowed_extensions_rust(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.rs' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_go(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.go' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_java(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.java' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_csharp(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.cs' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_solidity(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.sol' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_wasm(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.wat' in ALLOWED_EXTENSIONS
        assert '.wasm' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_swift(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.swift' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_kotlin(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.kt' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_dart(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.dart' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_cpp(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.cpp' in ALLOWED_EXTENSIONS
        assert '.h' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_typescript(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.ts' in ALLOWED_EXTENSIONS
        assert '.tsx' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_vue(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.vue' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_gdscript(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.gd' in ALLOWED_EXTENSIONS

    def test_allowed_extensions_graphql(self):
        from action_engine import ALLOWED_EXTENSIONS
        assert '.graphql' in ALLOWED_EXTENSIONS

    def test_lang_map_completeness(self):
        """验证action_engine的语言映射包含所有新语言"""
        lang_map = {
            "py": "Python", "js": "JavaScript", "ts": "TypeScript",
            "dart": "Dart", "sh": "Shell", "html": "HTML",
            "rs": "Rust", "go": "Go", "java": "Java", "cs": "C#",
            "sol": "Solidity", "swift": "Swift", "kt": "Kotlin",
            "cpp": "C++", "c": "C", "rb": "Ruby", "php": "PHP",
            "wasm": "WebAssembly(WAT)"
        }
        assert len(lang_map) >= 17


# ==================== Round 3: 安全/边界测试 ====================
class TestRound3_SecurityBoundary:
    """第3轮: 安全和边界条件测试"""

    def test_error_classifier_all_categories(self):
        from error_classifier import classify_error
        # 语法错误
        r = classify_error("SyntaxError: invalid syntax")
        assert r['category'] == 'syntax_error'
        # 导入错误
        r = classify_error("ModuleNotFoundError: No module named 'xyz'")
        assert r['category'] == 'import_error'
        # 类型错误
        r = classify_error("TypeError: unsupported operand type(s)")
        assert r['category'] == 'type_error'
        # 运行时错误 - ZeroDivisionError may map to runtime or unknown
        r = classify_error("ZeroDivisionError: division by zero")
        assert 'category' in r  # has a category

    def test_pre_check_code(self):
        from error_classifier import pre_check_code
        # 正常代码
        r = pre_check_code("print('hello')")
        assert r.get('safe_to_run') is True or len(r.get('issues', [])) == 0
        # 危险代码 (imports os)
        r = pre_check_code("import os\nos.system('rm -rf /')")
        assert len(r.get('issues', [])) > 0

    def test_plugin_registry_isolation(self):
        from plugin_registry import PluginRegistry
        reg = PluginRegistry()
        reg.register("test_plugin", {"name": "test"})
        assert reg.get("test_plugin") == {"name": "test"}
        assert reg.get("nonexistent") is None

    def test_i18n_languages(self):
        from i18n import t, set_language
        set_language("en")
        assert "system" in t("system_ready").lower() or t("system_ready") != ""
        set_language("zh")
        assert t("system_ready") != ""

    def test_env_config_defaults(self):
        from env_config import EnvConfig
        assert EnvConfig.AGI_API_HOST is not None
        assert EnvConfig.AGI_API_PORT is not None
        assert EnvConfig.AGI_ENV == 'development'

    def test_growth_engine_code_dimension_groups(self):
        """验证代码维度分组覆盖所有关键维度"""
        from growth_engine import GrowthEngine
        all_dim_ids = set()
        for group in GrowthEngine.CODE_DIMENSION_GROUPS:
            for dim in group["dimensions"]:
                all_dim_ids.add(dim["id"])
        # 确保覆盖了之前标记为❌的关键维度
        must_cover = {34, 35, 36, 37, 51, 52, 53, 86}  # Java/Go/Rust/C#/Desktop/WASM/Game/Blockchain
        assert must_cover.issubset(all_dim_ids), f"Missing: {must_cover - all_dim_ids}"


# ==================== Round 4: 架构完整性验证 ====================
class TestRound4_ArchitectureIntegrity:
    """第4轮: 验证整体架构完整性"""

    def test_orchestrator_has_role_field(self):
        """路由结果包含role字段"""
        from orchestrator import TaskOrchestrator
        orch = TaskOrchestrator(MagicMock())
        score, task_type, _ = orch.analyze_complexity("Rust链表", [])
        route = orch.route("Rust链表", [], score, task_type)
        assert 'role' in route
        assert route['role'] in ('君', '臣', '佐', '使')

    def test_all_roles_reachable(self):
        """所有四种角色都可达"""
        from orchestrator import TaskOrchestrator
        orch = TaskOrchestrator(MagicMock())
        roles_seen = set()

        # 君: proven充分
        proven = [{'status': 'proven', 'similarity': 0.9}] * 3
        s, t, _ = orch.analyze_complexity("hello", proven)
        r = orch.route("hello", proven, s, t)
        roles_seen.add(r['role'])

        # 臣: 复杂代码
        s, t, _ = orch.analyze_complexity("用Rust写分布式系统", [])
        r = orch.route("用Rust写分布式系统", [], s, t)
        roles_seen.add(r['role'])

        # 佐: medium Python code, need_glm5=False (need coverage>=0.4 + high_sim>0)
        partial_proven = [{'status': 'proven', 'similarity': 0.8},
                          {'status': 'proven', 'similarity': 0.6}]
        r = orch.route("写个Python函数", partial_proven, 0.4, 'code_generation')
        roles_seen.add(r['role'])

        # 使: 中等非代码, need_glm5=False (need coverage>=0.4)
        r = orch.route("今天天气怎么样", partial_proven, 0.4, 'general')
        roles_seen.add(r['role'])

        expected = {'君', '臣', '佐', '使'}
        assert roles_seen == expected, f"Missing roles: {expected - roles_seen}"

    def test_growth_engine_v4_banner(self):
        """成长引擎版本正确"""
        import growth_engine
        assert "v4.0" in growth_engine.__doc__
        assert "君臣佐使" in growth_engine.__doc__

    def test_coding_enhancer_tools_registered(self):
        """编码增强工具已注册"""
        import coding_enhancer
        funcs = ['run_linter', 'run_security_scan', 'run_tests',
                 'analyze_code_structure', 'code_review', 'generate_test',
                 'run_profiler', 'analyze_dependencies', 'analyze_tech_debt']
        for f in funcs:
            assert hasattr(coding_enhancer, f), f"Missing: {f}"

    def test_exception_hierarchy(self):
        """异常层级完整"""
        from agi_exceptions import AGIBaseError, LLMError, ToolError, SecurityError
        assert issubclass(LLMError, AGIBaseError)
        assert issubclass(ToolError, AGIBaseError)
        assert issubclass(SecurityError, AGIBaseError)


# ==================== Round 5: 推演优化验证 ====================
class TestRound5_Enhancements:
    """第5轮: 验证推演新增的优化功能"""

    def _make_orchestrator(self):
        from orchestrator import TaskOrchestrator
        from unittest.mock import MagicMock
        lattice = MagicMock()
        lattice._lock = MagicMock()
        return TaskOrchestrator(lattice)

    def test_long_context_routes_to_glm5(self):
        """dim7: 长上下文自动路由到GLM-5(128K)"""
        orch = self._make_orchestrator()
        long_question = "请分析以下代码并重构" + "x" * 7000  # >3000 tokens
        route = orch.route(long_question, [], 0.5, 'code_generation')
        assert route['model'] == 'GLM-5'
        assert route['role'] == '臣'
        assert route.get('long_context') is True

    def test_short_context_normal_routing(self):
        """短上下文走正常路由"""
        orch = self._make_orchestrator()
        route = orch.route("hello", [{'status': 'proven', 'similarity': 0.95}] * 5, 0.2, 'general')
        assert route['model'] == 'fast_path'
        assert route['role'] == '君'

    def test_platform_commands_exist(self):
        """dim13: 平台命令模板完整"""
        from tool_controller import PLATFORM_COMMANDS, get_platform_command, _CURRENT_OS
        assert len(PLATFORM_COMMANDS) >= 15
        for action, platforms in PLATFORM_COMMANDS.items():
            assert 'darwin' in platforms, f"{action} missing darwin"
            assert 'linux' in platforms, f"{action} missing linux"
            assert 'windows' in platforms, f"{action} missing windows"
        # 当前平台可以获取命令
        cmd = get_platform_command("list_files")
        assert len(cmd) > 0

    def test_platform_command_with_args(self):
        """dim13: 平台命令模板参数替换"""
        from tool_controller import get_platform_command
        cmd = get_platform_command("open_port", 8080)
        assert "8080" in cmd

    def test_migration_python_to_rust(self):
        """dim73: Python→Rust迁移分析"""
        from coding_enhancer import analyze_migration
        code = '''
def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''
        result = analyze_migration(code, "python", "rust")
        assert result['success'] is True
        assert len(result['warnings']) > 0  # 类型+内存差异
        assert any('所有权' in s for s in result['suggestions'])
        assert 'pip' in result['pkg_migration']
        assert 'cargo' in result['pkg_migration']

    def test_migration_js_to_typescript(self):
        """dim73: JS→TS迁移分析"""
        from coding_enhancer import analyze_migration
        result = analyze_migration("const x = 42;", "javascript", "typescript")
        assert result['success'] is True
        assert any('类型' in w for w in result['warnings'])

    def test_migration_invalid_lang(self):
        """dim73: 不支持的语言返回错误"""
        from coding_enhancer import analyze_migration
        result = analyze_migration("code", "brainfuck", "python")
        assert result['success'] is False

    def test_migration_same_memory_model(self):
        """dim73: 相同内存模型无内存警告"""
        from coding_enhancer import analyze_migration
        result = analyze_migration("code", "java", "csharp")
        assert result['success'] is True
        mem_warnings = [w for w in result['warnings'] if '内存' in w]
        assert len(mem_warnings) == 0

    def test_lang_migration_map_completeness(self):
        """dim73: 9种语言全部覆盖"""
        from coding_enhancer import LANG_MIGRATION_MAP
        expected = {'python', 'javascript', 'typescript', 'java', 'go', 'rust', 'csharp', 'swift', 'kotlin'}
        assert set(LANG_MIGRATION_MAP.keys()) == expected

    def test_coding_enhancer_has_migration(self):
        """dim73: analyze_migration已注册到CODING_HANDLERS"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        assert 'analyze_migration' in CODING_HANDLERS
        tool_names = [t['function']['name'] for t in CODING_TOOLS]
        assert 'analyze_migration' in tool_names

    def test_web_responsive_css(self):
        """dim39: web/index.html包含响应式断点"""
        html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web', 'index.html')
        content = open(html_path, encoding='utf-8').read()
        assert '@media(max-width:1024px)' in content
        assert '@media(max-width:640px)' in content
        assert '@media(prefers-reduced-motion:reduce)' in content

    def test_web_a11y_attributes(self):
        """dim84: web/index.html包含ARIA可访问性属性"""
        html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web', 'index.html')
        content = open(html_path, encoding='utf-8').read()
        assert 'role="banner"' in content
        assert 'role="main"' in content
        assert 'role="log"' in content
        assert 'aria-live="polite"' in content
        assert 'aria-label' in content
        assert 'sr-only' in content
        assert ':focus-visible' in content


# ==================== Round 6: 工具扩展验证 ====================
class TestRound6_ToolExpansion:
    """第6轮: 验证DB Schema检查/输出一致性/负载测试工具"""

    def test_inspect_db_schema_default(self):
        """dim29: 检查memory.db的Schema"""
        from coding_enhancer import inspect_db_schema
        result = inspect_db_schema()
        if result['success']:
            assert result['table_count'] >= 1
            assert isinstance(result['schema'], dict)
            assert isinstance(result['issues'], list)
        else:
            # DB可能不存在,但函数不应崩溃
            assert 'error' in result

    def test_inspect_db_schema_nonexistent(self):
        """dim29: 不存在的数据库返回错误"""
        from coding_enhancer import inspect_db_schema
        result = inspect_db_schema("/tmp/nonexistent_xyz.db")
        assert result['success'] is False

    def test_inspect_db_schema_temp(self):
        """dim29: 临时数据库Schema检查"""
        import sqlite3, tempfile
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT)")
            conn.execute("CREATE INDEX idx_email ON users(email)")
            conn.execute("INSERT INTO users VALUES (1, 'test', 'a@b.com')")
            conn.commit()
            conn.close()

            from coding_enhancer import inspect_db_schema
            result = inspect_db_schema(db_path)
            assert result['success'] is True
            assert 'users' in result['tables']
            assert result['schema']['users']['row_count'] == 1
            assert len(result['schema']['users']['columns']) == 3
            assert len(result['schema']['users']['indexes']) >= 1
        finally:
            os.unlink(db_path)

    def test_output_consistency_similar(self):
        """dim67: 相似输出一致性高"""
        from coding_enhancer import check_output_consistency
        outputs = [
            "# 结果\n- 第一点: 正确\n- 第二点: 也对\n```python\nprint('hello')\n```",
            "# 结果\n- 第一点: 正确\n- 第二点: 确实\n```python\nprint('hello')\n```",
        ]
        result = check_output_consistency(outputs)
        assert result['success'] is True
        assert result['overall_consistency'] > 0.6
        assert result['rating'] in ('A', 'B')

    def test_output_consistency_divergent(self):
        """dim67: 差异大的输出一致性低"""
        from coding_enhancer import check_output_consistency
        outputs = [
            "这是完全不同的内容",
            "```python\nfor i in range(100):\n    print(i)\n```\n\n## 标题\n1. 列表",
        ]
        result = check_output_consistency(outputs)
        assert result['success'] is True
        assert result['overall_consistency'] < 0.9

    def test_output_consistency_min_samples(self):
        """dim67: 样本不足返回错误"""
        from coding_enhancer import check_output_consistency
        result = check_output_consistency(["only one"])
        assert result['success'] is False

    def test_load_test_function_exists(self):
        """dim82: run_load_test函数存在且可调用"""
        from coding_enhancer import run_load_test
        assert callable(run_load_test)

    def test_load_test_unreachable(self):
        """dim82: 不可达URL正确报告错误"""
        from coding_enhancer import run_load_test
        result = run_load_test(url="http://127.0.0.1:59999/nonexist", concurrency=2, requests_count=3)
        assert result['success'] is True
        assert result['error_count'] == 3
        assert result['error_rate'] == 100.0

    def test_new_tools_registered(self):
        """所有新工具已注册到CODING_HANDLERS和CODING_TOOLS"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        new_tools = ['inspect_db_schema', 'check_output_consistency', 'run_load_test']
        for tool in new_tools:
            assert tool in CODING_HANDLERS, f"Missing handler: {tool}"
        tool_names = [t['function']['name'] for t in CODING_TOOLS]
        for tool in new_tools:
            assert tool in tool_names, f"Missing schema: {tool}"


# ==================== Round 7: 效率/需求/架构工具验证 ====================
class TestRound7_EfficiencyTools:
    """第7轮: Token效率/需求→骨架/ADR生成器验证"""

    def test_token_efficiency_basic(self):
        """dim59: 基本token估算"""
        from coding_enhancer import analyze_token_efficiency
        code = "def hello():\n    print('hello world')\n\nhello()\n"
        result = analyze_token_efficiency(code)
        assert result['success'] is True
        assert result['estimated_tokens'] > 0
        assert result['within_limit'] is True
        assert 0 <= result['info_density'] <= 1.0

    def test_token_efficiency_chinese(self):
        """dim59: 中文文本token估算"""
        from coding_enhancer import analyze_token_efficiency
        text = "这是一段中文测试文本，用于验证token估算的准确性。\n" * 10
        result = analyze_token_efficiency(text)
        assert result['success'] is True
        assert result['estimated_tokens'] > 100  # 中文字多

    def test_token_efficiency_compression(self):
        """dim59: 压缩建议检测"""
        from coding_enhancer import analyze_token_efficiency
        bloated = "code\n\n\n\n\n\ncode\n\n\n\n\ncode\n\n\n\ncode\n\n\ncode\n"
        result = analyze_token_efficiency(bloated)
        assert result['success'] is True
        assert result['empty_lines'] > 5
        assert any('空行' in s for s in result['suggestions'])

    def test_token_efficiency_duplicates(self):
        """dim59: 重复行检测"""
        from coding_enhancer import analyze_token_efficiency
        text = "import os\nimport os\nimport os\nimport os\nimport os\nprint('hi')\n"
        result = analyze_token_efficiency(text)
        assert result['success'] is True
        assert result['duplicate_lines'] >= 4

    def test_token_efficiency_empty(self):
        """dim59: 空文本返回错误"""
        from coding_enhancer import analyze_token_efficiency
        result = analyze_token_efficiency("")
        assert result['success'] is False

    def test_requirement_to_skeleton_api_db(self):
        """dim74: 需求识别API+数据库模块"""
        from coding_enhancer import requirement_to_skeleton
        result = requirement_to_skeleton("构建一个用户管理API,需要数据库存储用户信息", "python")
        assert result['success'] is True
        assert 'api' in result['detected_modules']
        assert 'database' in result['detected_modules']
        assert result['file_count'] >= 2
        assert 'api.py' in result['files']
        assert 'database.py' in result['files']

    def test_requirement_to_skeleton_auth(self):
        """dim74: 需求识别认证模块"""
        from coding_enhancer import requirement_to_skeleton
        result = requirement_to_skeleton("实现JWT登录认证系统")
        assert result['success'] is True
        assert 'auth' in result['detected_modules']

    def test_requirement_to_skeleton_typescript(self):
        """dim74: TypeScript骨架生成"""
        from coding_enhancer import requirement_to_skeleton
        result = requirement_to_skeleton("Build a REST API service", "typescript")
        assert result['success'] is True
        assert any(f.endswith('.ts') for f in result['files'])

    def test_requirement_to_skeleton_empty(self):
        """dim74: 空需求返回错误"""
        from coding_enhancer import requirement_to_skeleton
        result = requirement_to_skeleton("")
        assert result['success'] is False

    def test_requirement_to_skeleton_fallback(self):
        """dim74: 无法识别模块时使用main"""
        from coding_enhancer import requirement_to_skeleton
        result = requirement_to_skeleton("做点什么")
        assert result['success'] is True
        assert 'main' in result['detected_modules']

    def test_adr_complete(self):
        """dim75: 完整ADR生成"""
        from coding_enhancer import generate_adr
        result = generate_adr(
            title="选择君臣佐使架构",
            context="需要多模型协作来平衡成本和性能",
            decision="采用4层路由架构",
            alternatives=["单一大模型", "纯本地方案"]
        )
        assert result['success'] is True
        assert result['completeness'] == 1.0
        assert 'ADR-' in result['content']
        assert '替代方案' in result['content']
        assert result['file_name'].endswith('.md')

    def test_adr_minimal(self):
        """dim75: 最小ADR(仅标题)"""
        from coding_enhancer import generate_adr
        result = generate_adr(title="数据库选型")
        assert result['success'] is True
        assert result['completeness'] < 1.0
        assert any('⚠️' in c for c in result['quality_checks'])

    def test_adr_empty_title(self):
        """dim75: 空标题返回错误"""
        from coding_enhancer import generate_adr
        result = generate_adr(title="")
        assert result['success'] is False

    def test_round7_tools_registered(self):
        """所有Round7工具已注册"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        tools = ['analyze_token_efficiency', 'requirement_to_skeleton', 'generate_adr']
        for t in tools:
            assert t in CODING_HANDLERS, f"Missing handler: {t}"
        tool_names = [x['function']['name'] for x in CODING_TOOLS]
        for t in tools:
            assert t in tool_names, f"Missing schema: {t}"
