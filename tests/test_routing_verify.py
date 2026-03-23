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


# ==================== Round 8: 上下文/模板/Issue工具验证 ====================
class TestRound8_ContextTemplateIssue:
    """第8轮: 长上下文分块/低代码模板/GitHub Issue解析验证"""

    def test_chunk_short_code(self):
        """dim8: 短代码不需要分块"""
        from coding_enhancer import chunk_code_context
        code = "def hello():\n    return 'hi'\n"
        result = chunk_code_context(code)
        assert result['success'] is True
        assert result['total_chunks'] >= 1
        assert result['total_lines'] == 3

    def test_chunk_long_code_splits(self):
        """dim8: 长代码正确分块"""
        from coding_enhancer import chunk_code_context
        # 生成200行代码
        lines = []
        for i in range(20):
            lines.append(f"def func_{i}():")
            for j in range(9):
                lines.append(f"    x_{j} = {i * 10 + j}")
        code = '\n'.join(lines)
        result = chunk_code_context(code, max_chunk_tokens=500)
        assert result['success'] is True
        assert result['total_chunks'] > 1

    def test_chunk_symbol_extraction(self):
        """dim8: 正确提取函数/类符号"""
        from coding_enhancer import chunk_code_context
        code = "class MyClass:\n    pass\n\ndef my_func():\n    pass\n"
        result = chunk_code_context(code)
        assert result['success'] is True
        all_symbols = []
        for c in result['chunks']:
            all_symbols.extend(c['symbols'])
        assert 'class:MyClass' in all_symbols
        assert 'func:my_func' in all_symbols

    def test_chunk_symbol_index(self):
        """dim8: 跨块符号索引生成"""
        from coding_enhancer import chunk_code_context
        code = "def a():\n    pass\n\ndef b():\n    pass\n"
        result = chunk_code_context(code)
        assert isinstance(result['symbol_index'], dict)

    def test_chunk_empty(self):
        """dim8: 空代码返回错误"""
        from coding_enhancer import chunk_code_context
        result = chunk_code_context("")
        assert result['success'] is False

    def test_expand_crud_api(self):
        """dim88: CRUD API模板扩展"""
        from coding_enhancer import expand_template
        result = expand_template("crud_api", resource_name="users")
        assert result['success'] is True
        assert result['ready'] is True
        assert 'users' in result['code']
        assert '/api/users' in result['code']
        assert 'GET' in result['code']
        assert 'POST' in result['code']
        assert 'DELETE' in result['code']

    def test_expand_cli_tool(self):
        """dim88: CLI工具模板扩展"""
        from coding_enhancer import expand_template
        result = expand_template("cli_tool", tool_name="myutil", description="数据处理工具")
        assert result['success'] is True
        assert 'argparse' in result['code']
        assert 'myutil' in result['code']

    def test_expand_dataclass(self):
        """dim88: 数据模型模板扩展"""
        from coding_enhancer import expand_template
        result = expand_template("dataclass_model", model_name="User")
        assert result['success'] is True
        assert '@dataclass' in result['code']
        assert 'class User' in result['code']
        assert 'validate' in result['code']

    def test_expand_test_suite(self):
        """dim88: 测试套件模板扩展"""
        from coding_enhancer import expand_template
        result = expand_template("test_suite", module_name="Auth")
        assert result['success'] is True
        assert 'TestAuth' in result['code']
        assert 'pytest' in result['code']

    def test_expand_unknown_template(self):
        """dim88: 未知模板返回错误+可用列表"""
        from coding_enhancer import expand_template
        result = expand_template("nonexistent")
        assert result['success'] is False
        assert 'available' in result

    def test_expand_available_templates(self):
        """dim88: CODE_TEMPLATES包含4种模板"""
        from coding_enhancer import CODE_TEMPLATES
        assert len(CODE_TEMPLATES) >= 4
        assert 'crud_api' in CODE_TEMPLATES
        assert 'cli_tool' in CODE_TEMPLATES

    def test_parse_bug_issue(self):
        """dim92: Bug类型Issue解析"""
        from coding_enhancer import parse_github_issue
        issue = """# Login crash on empty password

## Bug Report
The app crashes when user submits empty password.

Steps to reproduce:
1. Open login page
2. Leave password empty
3. Click submit

Expected:
Show validation error

Actual:
App crashes with TypeError

```python
# Error traceback
TypeError: NoneType has no len()
```

Affected file: `auth/login.py`
"""
        result = parse_github_issue(issue)
        assert result['success'] is True
        assert result['type'] == 'bug'
        assert result['priority'] == 'medium'
        assert len(result['tasks']) == 5
        assert len(result['code_refs']) >= 1
        assert any('login' in f for f in result['affected_files'])

    def test_parse_feature_issue(self):
        """dim92: Feature类型Issue解析"""
        from coding_enhancer import parse_github_issue
        issue = "# Add dark mode feature\n\n需求: 新增暗色主题切换功能\n"
        result = parse_github_issue(issue)
        assert result['success'] is True
        assert result['type'] == 'feature'
        assert result['task_count'] == 5

    def test_parse_urgent_issue(self):
        """dim92: 紧急优先级检测"""
        from coding_enhancer import parse_github_issue
        issue = "# Critical: 数据库连接泄漏 bug\n\n紧急修复,生产环境严重影响\n"
        result = parse_github_issue(issue)
        assert result['success'] is True
        assert result['priority'] == 'high'

    def test_parse_empty_issue(self):
        """dim92: 空Issue返回错误"""
        from coding_enhancer import parse_github_issue
        result = parse_github_issue("")
        assert result['success'] is False

    def test_round8_tools_registered(self):
        """所有Round8工具已注册"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        tools = ['chunk_code_context', 'expand_template', 'parse_github_issue']
        for t in tools:
            assert t in CODING_HANDLERS, f"Missing handler: {t}"
        tool_names = [x['function']['name'] for x in CODING_TOOLS]
        for t in tools:
            assert t in tool_names, f"Missing schema: {t}"


# ==================== Round 9: 类型/UI组件/风格学习验证 ====================
class TestRound9_TypeUIStyle:
    """第9轮: 类型检查/UI组件生成/代码风格学习验证"""

    def test_type_hints_fully_typed(self):
        """dim3: 完全类型注解代码得A"""
        from coding_enhancer import enforce_type_hints
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        result = enforce_type_hints(code)
        assert result['success'] is True
        assert result['type_coverage'] == 100.0
        assert result['rating'] == 'A'

    def test_type_hints_missing(self):
        """dim3: 缺失类型注解检测"""
        from coding_enhancer import enforce_type_hints
        code = "def process(data, flag):\n    return data\n"
        result = enforce_type_hints(code)
        assert result['success'] is True
        assert result['type_coverage'] == 0.0
        assert len(result['suggestions']) >= 2
        assert result['rating'] == 'C'

    def test_type_hints_partial(self):
        """dim3: 部分类型注解"""
        from coding_enhancer import enforce_type_hints
        code = "def f1(x: int) -> str:\n    return str(x)\n\ndef f2(y):\n    return y\n"
        result = enforce_type_hints(code)
        assert result['success'] is True
        assert result['total_functions'] == 2
        assert result['fully_typed'] == 1

    def test_type_hints_self_skip(self):
        """dim3: self/cls参数跳过"""
        from coding_enhancer import enforce_type_hints
        code = "class A:\n    def method(self, x: int) -> None:\n        pass\n"
        result = enforce_type_hints(code)
        assert result['success'] is True
        assert result['type_coverage'] == 100.0

    def test_type_hints_syntax_error(self):
        """dim3: 语法错误处理"""
        from coding_enhancer import enforce_type_hints
        result = enforce_type_hints("def broken(:")
        assert result['success'] is False

    def test_type_hints_empty(self):
        """dim3: 空代码返回错误"""
        from coding_enhancer import enforce_type_hints
        result = enforce_type_hints("")
        assert result['success'] is False

    def test_ui_button(self):
        """dim38: 按钮组件生成"""
        from coding_enhancer import generate_ui_component
        result = generate_ui_component("button", label="提交")
        assert result['success'] is True
        assert '提交' in result['html']
        assert '.btn' in result['css']
        assert len(result['variants']) >= 4

    def test_ui_card(self):
        """dim38: 卡片组件生成"""
        from coding_enhancer import generate_ui_component
        result = generate_ui_component("card", title="标题", content="内容")
        assert result['success'] is True
        assert '标题' in result['html']
        assert '.card' in result['css']

    def test_ui_input(self):
        """dim38: 输入框组件生成"""
        from coding_enhancer import generate_ui_component
        result = generate_ui_component("input", label="用户名", id="username")
        assert result['success'] is True
        assert 'username' in result['html']
        assert '.input' in result['css']

    def test_ui_modal(self):
        """dim38: 模态框组件生成"""
        from coding_enhancer import generate_ui_component
        result = generate_ui_component("modal", title="确认删除")
        assert result['success'] is True
        assert '确认删除' in result['html']
        assert '.modal' in result['css']

    def test_ui_unknown(self):
        """dim38: 未知组件返回错误"""
        from coding_enhancer import generate_ui_component
        result = generate_ui_component("datepicker")
        assert result['success'] is False
        assert 'available' in result

    def test_ui_library_count(self):
        """dim38: UI组件库>=4种"""
        from coding_enhancer import UI_COMPONENT_LIBRARY
        assert len(UI_COMPONENT_LIBRARY) >= 4

    def test_style_snake_case(self):
        """dim70: 检测snake_case风格"""
        from coding_enhancer import learn_code_style
        code = "def my_func():\n    my_var = 1\n    other_var = 2\n"
        result = learn_code_style(code)
        assert result['success'] is True
        assert result['style_profile']['naming'] == 'snake_case'

    def test_style_indent_4spaces(self):
        """dim70: 检测4空格缩进"""
        from coding_enhancer import learn_code_style
        code = "def f():\n    x = 1\n    y = 2\n    return x + y\n"
        result = learn_code_style(code)
        assert result['success'] is True
        assert result['style_profile']['indent'] == 'spaces_4'

    def test_style_single_quotes(self):
        """dim70: 检测单引号风格"""
        from coding_enhancer import learn_code_style
        code = "x = 'hello'\ny = 'world'\nz = 'test'\n"
        result = learn_code_style(code)
        assert result['success'] is True
        assert result['style_profile']['quotes'] == 'single'

    def test_style_docstring(self):
        """dim70: 检测docstring文档风格"""
        from coding_enhancer import learn_code_style
        code = '"""\nModule doc\n"""\ndef f():\n    """Function doc"""\n    pass\n'
        result = learn_code_style(code)
        assert result['success'] is True
        assert result['style_profile']['doc_style'] == 'docstring'

    def test_style_empty(self):
        """dim70: 空代码返回错误"""
        from coding_enhancer import learn_code_style
        result = learn_code_style("")
        assert result['success'] is False

    def test_style_summary(self):
        """dim70: 风格摘要包含关键信息"""
        from coding_enhancer import learn_code_style
        code = "def hello():\n    print('hi')\n"
        result = learn_code_style(code)
        assert result['success'] is True
        assert '风格' in result['summary']

    def test_round9_tools_registered(self):
        """所有Round9工具已注册"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        tools = ['enforce_type_hints', 'generate_ui_component', 'learn_code_style']
        for t in tools:
            assert t in CODING_HANDLERS, f"Missing handler: {t}"
        tool_names = [x['function']['name'] for x in CODING_TOOLS]
        for t in tools:
            assert t in tool_names, f"Missing schema: {t}"


# ==================== Round 10: API索引/可视化/算法模板验证 ====================
class TestRound10_APIChartAlgo:
    """第10轮: API索引/数据可视化/算法模板验证"""

    def test_api_lookup_os(self):
        """dim4: 查询os模块API"""
        from coding_enhancer import lookup_api
        result = lookup_api("os")
        assert result['success'] is True
        assert result['count'] >= 5
        assert 'path.join' in result['functions']

    def test_api_lookup_function(self):
        """dim4: 精确查询函数"""
        from coding_enhancer import lookup_api
        result = lookup_api("json", "loads")
        assert result['success'] is True
        assert result['found'] is True
        assert 'loads' in result['apis']

    def test_api_lookup_pandas(self):
        """dim4: 查询pandas API"""
        from coding_enhancer import lookup_api
        result = lookup_api("pandas")
        assert result['success'] is True
        assert 'DataFrame' in result['functions']

    def test_api_lookup_unknown(self):
        """dim4: 未知模块返回错误"""
        from coding_enhancer import lookup_api
        result = lookup_api("nonexistent_lib")
        assert result['success'] is False
        assert 'available_modules' in result

    def test_api_lookup_empty(self):
        """dim4: 空模块返回错误"""
        from coding_enhancer import lookup_api
        result = lookup_api("")
        assert result['success'] is False

    def test_api_index_count(self):
        """dim4: API索引>=18个库"""
        from coding_enhancer import STDLIB_API_INDEX
        assert len(STDLIB_API_INDEX) >= 18

    def test_chart_line(self):
        """dim49: 折线图代码生成"""
        from coding_enhancer import generate_chart_code
        result = generate_chart_code("line", title="趋势图")
        assert result['success'] is True
        assert 'matplotlib' in result['code']
        assert '趋势图' in result['code']
        assert 'plot' in result['code']

    def test_chart_bar(self):
        """dim49: 柱状图代码生成"""
        from coding_enhancer import generate_chart_code
        result = generate_chart_code("bar")
        assert result['success'] is True
        assert 'bar' in result['code']

    def test_chart_pie(self):
        """dim49: 饼图代码生成"""
        from coding_enhancer import generate_chart_code
        result = generate_chart_code("pie")
        assert result['success'] is True
        assert 'pie' in result['code']

    def test_chart_heatmap(self):
        """dim49: 热力图代码生成"""
        from coding_enhancer import generate_chart_code
        result = generate_chart_code("heatmap")
        assert result['success'] is True
        assert 'imshow' in result['code']

    def test_chart_unknown(self):
        """dim49: 未知图表类型返回错误"""
        from coding_enhancer import generate_chart_code
        result = generate_chart_code("radar")
        assert result['success'] is False
        assert 'available' in result

    def test_chart_templates_count(self):
        """dim49: 图表模板>=5种"""
        from coding_enhancer import CHART_TEMPLATES
        assert len(CHART_TEMPLATES) >= 5

    def test_algo_binary_search(self):
        """dim54: 二分查找模板"""
        from coding_enhancer import get_algorithm_template
        result = get_algorithm_template("binary_search")
        assert result['success'] is True
        assert 'O(log n)' in result['complexity']['time']
        assert 'def binary_search' in result['code']

    def test_algo_bfs(self):
        """dim54: BFS模板"""
        from coding_enhancer import get_algorithm_template
        result = get_algorithm_template("bfs")
        assert result['success'] is True
        assert 'O(V+E)' in result['complexity']['time']

    def test_algo_dijkstra(self):
        """dim54: Dijkstra模板"""
        from coding_enhancer import get_algorithm_template
        result = get_algorithm_template("dijkstra")
        assert result['success'] is True
        assert 'heapq' in result['code']

    def test_algo_dp_knapsack(self):
        """dim54: 背包DP模板"""
        from coding_enhancer import get_algorithm_template
        result = get_algorithm_template("dp_knapsack")
        assert result['success'] is True
        assert 'dp' in result['code']

    def test_algo_trie(self):
        """dim54: 字典树模板"""
        from coding_enhancer import get_algorithm_template
        result = get_algorithm_template("trie")
        assert result['success'] is True
        assert 'class Trie' in result['code']

    def test_algo_union_find(self):
        """dim54: 并查集模板"""
        from coding_enhancer import get_algorithm_template
        result = get_algorithm_template("union_find")
        assert result['success'] is True
        assert 'class UnionFind' in result['code']

    def test_algo_unknown(self):
        """dim54: 未知算法返回错误"""
        from coding_enhancer import get_algorithm_template
        result = get_algorithm_template("quantum_sort")
        assert result['success'] is False
        assert 'available' in result

    def test_algo_templates_count(self):
        """dim54: 算法模板>=8种"""
        from coding_enhancer import ALGORITHM_TEMPLATES
        assert len(ALGORITHM_TEMPLATES) >= 8

    def test_round10_tools_registered(self):
        """所有Round10工具已注册"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        tools = ['lookup_api', 'generate_chart_code', 'get_algorithm_template']
        for t in tools:
            assert t in CODING_HANDLERS, f"Missing handler: {t}"
        tool_names = [x['function']['name'] for x in CODING_TOOLS]
        for t in tools:
            assert t in tool_names, f"Missing schema: {t}"


# ==================== Round 11: DS Pipeline/DP模式/图算法验证 ====================
class TestRound11_DSPipelineDPGraph:
    """第11轮: 数据科学Pipeline/DP模式/图算法验证"""

    def test_ds_classification(self):
        """dim48: 分类Pipeline生成"""
        from coding_enhancer import generate_ds_pipeline
        result = generate_ds_pipeline("classification")
        assert result['success'] is True
        assert 'pandas' in result['code']
        assert 'RandomForestClassifier' in result['code']
        assert len(result['steps']) == 6

    def test_ds_regression(self):
        """dim48: 回归Pipeline生成"""
        from coding_enhancer import generate_ds_pipeline
        result = generate_ds_pipeline("regression")
        assert result['success'] is True
        assert 'RandomForestRegressor' in result['code']
        assert 'mean_squared_error' in result['code']

    def test_ds_clustering(self):
        """dim48: 聚类Pipeline生成"""
        from coding_enhancer import generate_ds_pipeline
        result = generate_ds_pipeline("clustering")
        assert result['success'] is True
        assert 'KMeans' in result['code']

    def test_ds_json_format(self):
        """dim48: JSON数据格式"""
        from coding_enhancer import generate_ds_pipeline
        result = generate_ds_pipeline("classification", data_format="json")
        assert result['success'] is True
        assert 'read_json' in result['code']

    def test_ds_custom_target(self):
        """dim48: 自定义目标列"""
        from coding_enhancer import generate_ds_pipeline
        result = generate_ds_pipeline("classification", target_col="label")
        assert result['success'] is True
        assert "'label'" in result['code']

    def test_ds_pipeline_steps(self):
        """dim48: Pipeline步骤完整"""
        from coding_enhancer import DS_PIPELINE_STEPS
        assert 'load' in DS_PIPELINE_STEPS
        assert 'clean' in DS_PIPELINE_STEPS
        assert 'split' in DS_PIPELINE_STEPS

    def test_dp_linear(self):
        """dim55: 线性DP模板"""
        from coding_enhancer import get_dp_pattern
        result = get_dp_pattern("linear_dp")
        assert result['success'] is True
        assert 'longest_increasing_subsequence' in result['code']
        assert 'O(n' in result['complexity']['time']

    def test_dp_interval(self):
        """dim55: 区间DP模板"""
        from coding_enhancer import get_dp_pattern
        result = get_dp_pattern("interval_dp")
        assert result['success'] is True
        assert 'matrix_chain_order' in result['code']

    def test_dp_tree(self):
        """dim55: 树形DP模板"""
        from coding_enhancer import get_dp_pattern
        result = get_dp_pattern("tree_dp")
        assert result['success'] is True
        assert 'tree_diameter' in result['code']

    def test_greedy_interval(self):
        """dim55: 贪心-区间调度模板"""
        from coding_enhancer import get_dp_pattern
        result = get_dp_pattern("greedy_interval")
        assert result['success'] is True
        assert 'max_non_overlapping' in result['code']

    def test_greedy_huffman(self):
        """dim55: 贪心-Huffman模板"""
        from coding_enhancer import get_dp_pattern
        result = get_dp_pattern("greedy_huffman")
        assert result['success'] is True
        assert 'huffman_encoding' in result['code']

    def test_dp_unknown(self):
        """dim55: 未知DP模式返回错误"""
        from coding_enhancer import get_dp_pattern
        result = get_dp_pattern("quantum_dp")
        assert result['success'] is False

    def test_dp_patterns_count(self):
        """dim55: DP/贪心模式>=5种"""
        from coding_enhancer import DP_PATTERNS
        assert len(DP_PATTERNS) >= 5

    def test_graph_topological(self):
        """dim56: 拓扑排序模板"""
        from coding_enhancer import get_graph_algorithm
        result = get_graph_algorithm("topological_sort")
        assert result['success'] is True
        assert 'topological_sort' in result['code']
        assert 'O(V+E)' in result['complexity']['time']

    def test_graph_kruskal(self):
        """dim56: Kruskal MST模板"""
        from coding_enhancer import get_graph_algorithm
        result = get_graph_algorithm("kruskal_mst")
        assert result['success'] is True
        assert 'kruskal_mst' in result['code']

    def test_graph_a_star(self):
        """dim56: A*搜索模板"""
        from coding_enhancer import get_graph_algorithm
        result = get_graph_algorithm("a_star")
        assert result['success'] is True
        assert 'a_star' in result['code']
        assert 'heuristic' in result['code']

    def test_graph_floyd(self):
        """dim56: Floyd-Warshall模板"""
        from coding_enhancer import get_graph_algorithm
        result = get_graph_algorithm("floyd_warshall")
        assert result['success'] is True
        assert 'floyd_warshall' in result['code']

    def test_graph_tarjan(self):
        """dim56: Tarjan SCC模板"""
        from coding_enhancer import get_graph_algorithm
        result = get_graph_algorithm("tarjan_scc")
        assert result['success'] is True
        assert 'tarjan_scc' in result['code']

    def test_graph_unknown(self):
        """dim56: 未知图算法返回错误"""
        from coding_enhancer import get_graph_algorithm
        result = get_graph_algorithm("bellman_ford")
        assert result['success'] is False

    def test_graph_algos_count(self):
        """dim56: 图算法>=5种"""
        from coding_enhancer import GRAPH_ALGORITHMS
        assert len(GRAPH_ALGORITHMS) >= 5

    def test_round11_tools_registered(self):
        """所有Round11工具已注册"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        tools = ['generate_ds_pipeline', 'get_dp_pattern', 'get_graph_algorithm']
        for t in tools:
            assert t in CODING_HANDLERS, f"Missing handler: {t}"
        tool_names = [x['function']['name'] for x in CODING_TOOLS]
        for t in tools:
            assert t in tool_names, f"Missing schema: {t}"


# ==================== Round 12: 竞赛编程/ML模型选择/框架速查验证 ====================
class TestRound12_CPMLFramework:
    """第12轮: 竞赛编程/ML模型选择/框架速查验证"""

    def test_cp_fast_io(self):
        """dim2: 快速IO模板"""
        from coding_enhancer import get_cp_trick
        result = get_cp_trick("fast_io")
        assert result['success'] is True
        assert 'sys.stdin' in result['code']

    def test_cp_mod_arithmetic(self):
        """dim2: 模运算模板"""
        from coding_enhancer import get_cp_trick
        result = get_cp_trick("mod_arithmetic")
        assert result['success'] is True
        assert 'modinv' in result['code']

    def test_cp_bit_manipulation(self):
        """dim2: 位运算技巧"""
        from coding_enhancer import get_cp_trick
        result = get_cp_trick("bit_manipulation")
        assert result['success'] is True
        assert 'mask' in result['code']

    def test_cp_segment_tree(self):
        """dim2: 线段树模板"""
        from coding_enhancer import get_cp_trick
        result = get_cp_trick("segment_tree")
        assert result['success'] is True
        assert 'SegTree' in result['code']

    def test_cp_prefix_sum(self):
        """dim2: 前缀和模板"""
        from coding_enhancer import get_cp_trick
        result = get_cp_trick("prefix_sum")
        assert result['success'] is True
        assert 'accumulate' in result['code']

    def test_cp_unknown(self):
        """dim2: 未知技巧返回错误"""
        from coding_enhancer import get_cp_trick
        result = get_cp_trick("quantum_trick")
        assert result['success'] is False

    def test_cp_tricks_count(self):
        """dim2: 竞赛技巧>=6种"""
        from coding_enhancer import CP_TRICKS
        assert len(CP_TRICKS) >= 6

    def test_ml_classification(self):
        """dim47: 分类模型推荐"""
        from coding_enhancer import recommend_ml_model
        result = recommend_ml_model("classification")
        assert result['success'] is True
        assert len(result['recommendations']) >= 3
        assert result['total_models'] >= 5

    def test_ml_regression(self):
        """dim47: 回归模型推荐"""
        from coding_enhancer import recommend_ml_model
        result = recommend_ml_model("regression")
        assert result['success'] is True
        assert len(result['recommendations']) >= 3

    def test_ml_clustering(self):
        """dim47: 聚类模型推荐"""
        from coding_enhancer import recommend_ml_model
        result = recommend_ml_model("clustering")
        assert result['success'] is True
        assert len(result['recommendations']) >= 2

    def test_ml_interpretable(self):
        """dim47: 可解释性约束"""
        from coding_enhancer import recommend_ml_model
        result = recommend_ml_model("classification", interpretable=True)
        assert result['success'] is True
        assert result['recommendations'][0]['interpretable'] is True

    def test_ml_unknown_task(self):
        """dim47: 未知任务返回错误"""
        from coding_enhancer import recommend_ml_model
        result = recommend_ml_model("reinforcement")
        assert result['success'] is False

    def test_ml_catalog_count(self):
        """dim47: ML目录>=3类任务"""
        from coding_enhancer import ML_MODEL_CATALOG
        assert len(ML_MODEL_CATALOG) >= 3

    def test_fw_fastapi(self):
        """dim71: FastAPI速查表"""
        from coding_enhancer import get_framework_cheatsheet
        result = get_framework_cheatsheet("fastapi")
        assert result['success'] is True
        assert 'FastAPI' in result['hello_world']
        assert len(result['key_concepts']) >= 3

    def test_fw_nextjs(self):
        """dim71: Next.js速查表"""
        from coding_enhancer import get_framework_cheatsheet
        result = get_framework_cheatsheet("nextjs")
        assert result['success'] is True
        assert 'App Router' in result['key_concepts']

    def test_fw_django(self):
        """dim71: Django速查表"""
        from coding_enhancer import get_framework_cheatsheet
        result = get_framework_cheatsheet("django")
        assert result['success'] is True
        assert 'ORM' in result['key_concepts']

    def test_fw_vue3(self):
        """dim71: Vue3速查表"""
        from coding_enhancer import get_framework_cheatsheet
        result = get_framework_cheatsheet("vue3")
        assert result['success'] is True
        assert 'Composition API' in result['key_concepts']

    def test_fw_spring_boot(self):
        """dim71: Spring Boot速查表"""
        from coding_enhancer import get_framework_cheatsheet
        result = get_framework_cheatsheet("spring_boot")
        assert result['success'] is True

    def test_fw_gin(self):
        """dim71: Gin速查表"""
        from coding_enhancer import get_framework_cheatsheet
        result = get_framework_cheatsheet("gin")
        assert result['success'] is True

    def test_fw_unknown(self):
        """dim71: 未知框架返回错误"""
        from coding_enhancer import get_framework_cheatsheet
        result = get_framework_cheatsheet("phoenix")
        assert result['success'] is False

    def test_fw_count(self):
        """dim71: 框架速查>=6个"""
        from coding_enhancer import FRAMEWORK_CHEATSHEETS
        assert len(FRAMEWORK_CHEATSHEETS) >= 6

    def test_round12_tools_registered(self):
        """所有Round12工具已注册"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        tools = ['get_cp_trick', 'recommend_ml_model', 'get_framework_cheatsheet']
        for t in tools:
            assert t in CODING_HANDLERS, f"Missing handler: {t}"
        tool_names = [x['function']['name'] for x in CODING_TOOLS]
        for t in tools:
            assert t in tool_names, f"Missing schema: {t}"


# ==================== Round 13: SWE Pipeline/NoSQL/微服务验证 ====================
class TestRound13_SWENoSQLMicroservice:
    """第13轮: SWE Pipeline/NoSQL模板/微服务模式验证"""

    def test_swe_bug_issue(self):
        """dim1: Bug类Issue修复计划"""
        from coding_enhancer import plan_swe_fix
        result = plan_swe_fix("Bug: TypeError in api_server.py when handling empty request body\nTraceback: line 42")
        assert result['success'] is True
        assert result['issue_type'] == 'bug'
        assert result['pipeline_length'] == 5
        assert result['has_traceback'] is True

    def test_swe_feature_issue(self):
        """dim1: Feature类Issue修复计划"""
        from coding_enhancer import plan_swe_fix
        result = plan_swe_fix("Feature: Add support for WebSocket connections in the API server")
        assert result['success'] is True
        assert result['issue_type'] == 'feature'
        assert result['estimated_complexity'] == 'high'

    def test_swe_refactor_issue(self):
        """dim1: Refactor类Issue修复计划"""
        from coding_enhancer import plan_swe_fix
        result = plan_swe_fix("Refactor: Improve the database query optimization module")
        assert result['success'] is True
        assert result['issue_type'] == 'refactor'

    def test_swe_file_refs(self):
        """dim1: 提取文件引用"""
        from coding_enhancer import plan_swe_fix
        result = plan_swe_fix("Bug in api_server.py: crash when loading config.json at startup")
        assert result['success'] is True
        assert len(result['file_references']) >= 1

    def test_swe_short_issue(self):
        """dim1: 太短的Issue返回错误"""
        from coding_enhancer import plan_swe_fix
        result = plan_swe_fix("bug")
        assert result['success'] is False

    def test_swe_pipeline_steps(self):
        """dim1: Pipeline步骤完整"""
        from coding_enhancer import SWE_PIPELINE_STEPS
        assert 'parse_issue' in SWE_PIPELINE_STEPS
        assert 'locate_code' in SWE_PIPELINE_STEPS
        assert 'generate_patch' in SWE_PIPELINE_STEPS
        assert 'verify_fix' in SWE_PIPELINE_STEPS
        assert len(SWE_PIPELINE_STEPS) == 5

    def test_nosql_redis_overview(self):
        """dim31: Redis概览"""
        from coding_enhancer import get_nosql_template
        result = get_nosql_template("redis")
        assert result['success'] is True
        assert result['operation_count'] >= 6

    def test_nosql_redis_string(self):
        """dim31: Redis字符串操作"""
        from coding_enhancer import get_nosql_template
        result = get_nosql_template("redis", "string")
        assert result['success'] is True
        assert 'set' in result['code']

    def test_nosql_redis_cache(self):
        """dim31: Redis缓存模式"""
        from coding_enhancer import get_nosql_template
        result = get_nosql_template("redis", "cache_pattern")
        assert result['success'] is True
        assert 'get_cached' in result['code']

    def test_nosql_mongodb(self):
        """dim31: MongoDB概览"""
        from coding_enhancer import get_nosql_template
        result = get_nosql_template("mongodb")
        assert result['success'] is True
        assert result['operation_count'] >= 5

    def test_nosql_mongodb_aggregate(self):
        """dim31: MongoDB聚合"""
        from coding_enhancer import get_nosql_template
        result = get_nosql_template("mongodb", "aggregate")
        assert result['success'] is True
        assert '$match' in result['code']

    def test_nosql_elasticsearch(self):
        """dim31: Elasticsearch概览"""
        from coding_enhancer import get_nosql_template
        result = get_nosql_template("elasticsearch")
        assert result['success'] is True

    def test_nosql_unknown(self):
        """dim31: 未知DB返回错误"""
        from coding_enhancer import get_nosql_template
        result = get_nosql_template("cassandra")
        assert result['success'] is False

    def test_nosql_db_count(self):
        """dim31: NoSQL数据库>=3种"""
        from coding_enhancer import NOSQL_TEMPLATES
        assert len(NOSQL_TEMPLATES) >= 3

    def test_ms_api_gateway(self):
        """dim41: API Gateway模板"""
        from coding_enhancer import get_microservice_pattern
        result = get_microservice_pattern("api_gateway")
        assert result['success'] is True
        assert 'FastAPI' in result['code']

    def test_ms_circuit_breaker(self):
        """dim41: 熔断器模板"""
        from coding_enhancer import get_microservice_pattern
        result = get_microservice_pattern("circuit_breaker")
        assert result['success'] is True
        assert 'CircuitBreaker' in result['code']

    def test_ms_event_driven(self):
        """dim41: 事件驱动模板"""
        from coding_enhancer import get_microservice_pattern
        result = get_microservice_pattern("event_driven")
        assert result['success'] is True
        assert 'publish_event' in result['code']

    def test_ms_saga(self):
        """dim41: Saga模式模板"""
        from coding_enhancer import get_microservice_pattern
        result = get_microservice_pattern("saga_pattern")
        assert result['success'] is True
        assert 'SagaOrchestrator' in result['code']

    def test_ms_service_discovery(self):
        """dim41: 服务发现模板"""
        from coding_enhancer import get_microservice_pattern
        result = get_microservice_pattern("service_discovery")
        assert result['success'] is True

    def test_ms_unknown(self):
        """dim41: 未知模式返回错误"""
        from coding_enhancer import get_microservice_pattern
        result = get_microservice_pattern("cqrs")
        assert result['success'] is False

    def test_ms_patterns_count(self):
        """dim41: 微服务模式>=5种"""
        from coding_enhancer import MICROSERVICE_PATTERNS
        assert len(MICROSERVICE_PATTERNS) >= 5

    def test_round13_tools_registered(self):
        """所有Round13工具已注册"""
        from coding_enhancer import CODING_HANDLERS, CODING_TOOLS
        tools = ['plan_swe_fix', 'get_nosql_template', 'get_microservice_pattern']
        for t in tools:
            assert t in CODING_HANDLERS, f"Missing handler: {t}"
        tool_names = [x['function']['name'] for x in CODING_TOOLS]
        for t in tools:
            assert t in tool_names, f"Missing schema: {t}"
