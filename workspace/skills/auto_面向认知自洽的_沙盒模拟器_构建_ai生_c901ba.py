"""
面向认知自洽的'沙盒模拟器'构建模块

该模块实现了一个逻辑沙盒系统，用于在AI生成的知识接触真实世界前进行内部证伪。
通过模拟运行和逻辑一致性检查，过滤掉存在矛盾的假设性知识节点。

核心功能：
1. 沙盒环境模拟运行
2. 逻辑一致性验证
3. 认知自洽性评估

典型用例：
>>> sandbox = CognitiveSandbox()
>>> result = sandbox.simulate_hypothesis(code_snippet, expected_output)
>>> if result.is_consistent:
...     deploy_to_production()
"""

import ast
import inspect
import logging
import textwrap
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from functools import wraps

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """沙盒模拟结果数据结构"""
    is_consistent: bool
    execution_output: Any
    logical_errors: List[str]
    runtime_errors: List[str]
    performance_metrics: Dict[str, float]
    dependency_graph: Dict[str, List[str]]


class SandboxEnvironment:
    """
    沙盒环境类，提供隔离的执行环境
    
    特性：
    1. 限制危险操作
    2. 资源使用监控
    3. 执行跟踪
    
    使用示例：
    >>> env = SandboxEnvironment()
    >>> env.add_allowed_module('math')
    >>> result = env.execute("import math; math.sqrt(4)")
    """
    
    def __init__(self):
        self._allowed_modules = {'math', 'random', 'datetime'}
        self._execution_trace = []
        self._resource_limits = {
            'max_time': 5,  # 秒
            'max_memory': 10 * 1024 * 1024,  # 10MB
            'max_output_size': 1024  # 1KB
        }
    
    def add_allowed_module(self, module_name: str) -> None:
        """添加允许导入的模块"""
        if not isinstance(module_name, str):
            raise ValueError("模块名必须是字符串")
        self._allowed_modules.add(module_name)
    
    def execute(self, code: str, *args, **kwargs) -> Tuple[Any, List[str]]:
        """
        在沙盒中执行代码
        
        参数:
            code: 要执行的代码字符串
            *args: 传递给代码的参数
            **kwargs: 传递给代码的参数
            
        返回:
            tuple: (执行结果, 执行跟踪)
            
        异常:
            RuntimeError: 如果代码执行违反沙盒规则
        """
        if not isinstance(code, str):
            raise ValueError("代码必须是字符串")
            
        # 代码静态分析
        self._validate_code(code)
        
        # 创建受限的全局命名空间
        safe_globals = self._create_safe_globals()
        local_vars = {}
        
        try:
            # 记录执行开始
            self._execution_trace.append(f"开始执行: {code[:50]}...")
            
            # 执行代码
            exec(code, safe_globals, local_vars)
            
            # 获取执行结果
            result = local_vars.get('result', None)
            
            return result, self._execution_trace.copy()
            
        except Exception as e:
            logger.error(f"沙盒执行错误: {str(e)}")
            self._execution_trace.append(f"执行错误: {str(e)}")
            raise RuntimeError(f"沙盒执行失败: {str(e)}") from e
            
        finally:
            self._execution_trace.clear()
    
    def _validate_code(self, code: str) -> None:
        """验证代码安全性"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"语法错误: {e}") from e
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self._allowed_modules:
                        raise ValueError(f"不允许导入模块: {alias.name}")
                        
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('eval', 'exec', 'compile', 'open'):
                        raise ValueError(f"不允许调用函数: {node.func.id}")
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """创建安全的全局命名空间"""
        safe_builtins = {
            'print': lambda *args: None,  # 禁用实际输出
            'len': len,
            'range': range,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'True': True,
            'False': False,
            'None': None,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'isinstance': isinstance,
        }
        
        return {'__builtins__': safe_builtins}


class LogicalConsistencyValidator:
    """
    逻辑一致性验证器
    
    提供多种逻辑验证方法:
    1. 输入输出一致性
    2. 状态转换一致性
    3. 因果关系一致性
    
    示例:
    >>> validator = LogicalConsistencyValidator()
    >>> validator.add_rule("input_output", lambda i, o: o == i*2)
    >>> result = validator.validate(2, 4)
    """
    
    def __init__(self):
        self._validation_rules = {}
        self._validation_history = []
    
    def add_rule(self, name: str, rule_func: Callable) -> None:
        """添加验证规则"""
        if not callable(rule_func):
            raise ValueError("规则必须是可调用对象")
        self._validation_rules[name] = rule_func
    
    def validate(self, *args, **kwargs) -> bool:
        """执行所有验证规则"""
        results = []
        
        for name, rule in self._validation_rules.items():
            try:
                result = rule(*args, **kwargs)
                results.append((name, result))
                self._validation_history.append((name, result))
            except Exception as e:
                logger.warning(f"规则 {name} 验证失败: {e}")
                results.append((name, False))
                
        return all(result for _, result in results)
    
    def get_validation_history(self) -> List[Tuple[str, bool]]:
        """获取验证历史"""
        return self._validation_history.copy()


class CognitiveSandbox:
    """
    认知沙盒主类
    
    整合沙盒环境和逻辑验证，提供完整的认知自洽性模拟
    
    使用示例:
    >>> sandbox = CognitiveSandbox()
    >>> hypothesis = "def process(x): return x*2"
    >>> result = sandbox.simulate_hypothesis(hypothesis, input_value=5, expected_output=10)
    """
    
    def __init__(self):
        self.env = SandboxEnvironment()
        self.validator = LogicalConsistencyValidator()
        self._init_default_rules()
        
    def _init_default_rules(self) -> None:
        """初始化默认验证规则"""
        # 输入输出一致性规则
        self.validator.add_rule(
            "input_output",
            lambda input_val, output_val, expected: output_val == expected
        )
        
        # 类型一致性规则
        self.validator.add_rule(
            "type_consistency",
            lambda input_val, output_val, expected: type(output_val) == type(expected)
        )
        
        # 非空规则
        self.validator.add_rule(
            "non_empty",
            lambda input_val, output_val, expected: output_val is not None
        )
    
    def simulate_hypothesis(
        self,
        code: str,
        input_value: Any = None,
        expected_output: Any = None,
        additional_rules: Optional[List[Callable]] = None
    ) -> SimulationResult:
        """
        模拟假设性知识
        
        参数:
            code: 要测试的代码字符串
            input_value: 输入值
            expected_output: 预期输出
            additional_rules: 额外的验证规则
            
        返回:
            SimulationResult: 包含模拟结果的详细数据
        """
        # 添加额外规则
        if additional_rules:
            for i, rule in enumerate(additional_rules):
                self.validator.add_rule(f"custom_rule_{i}", rule)
        
        logical_errors = []
        runtime_errors = []
        performance_metrics = {}
        dependency_graph = {}
        
        try:
            # 预处理代码
            wrapped_code = self._wrap_code_for_execution(code)
            
            # 执行代码
            execution_output, trace = self.env.execute(wrapped_code, input_value)
            
            # 验证逻辑一致性
            is_consistent = self.validator.validate(
                input_value, execution_output, expected_output
            )
            
            # 收集错误信息
            if not is_consistent:
                logical_errors.append("逻辑一致性验证失败")
                logical_errors.extend(
                    f"规则 {name} 失败" 
                    for name, result in self.validator.get_validation_history() 
                    if not result
                )
            
            # 构建依赖图
            dependency_graph = self._build_dependency_graph(code)
            
        except Exception as e:
            runtime_errors.append(str(e))
            execution_output = None
            is_consistent = False
            
        return SimulationResult(
            is_consistent=is_consistent,
            execution_output=execution_output,
            logical_errors=logical_errors,
            runtime_errors=runtime_errors,
            performance_metrics=performance_metrics,
            dependency_graph=dependency_graph
        )
    
    def _wrap_code_for_execution(self, code: str) -> str:
        """包装代码以便捕获结果"""
        return textwrap.dedent(f"""
        {code}
        result = process(input_value)
        """)
    
    def _build_dependency_graph(self, code: str) -> Dict[str, List[str]]:
        """构建代码依赖图"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {}
            
        graph = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                graph[node.name] = [
                    n.id for n in ast.walk(node) 
                    if isinstance(n, ast.Name) and n.id != node.name
                ]
                
        return graph


# 示例使用
if __name__ == "__main__":
    # 创建认知沙盒实例
    sandbox = CognitiveSandbox()
    
    # 测试用例1: 有效的假设
    valid_hypothesis = """
    def process(x):
        return x * 2
    """
    result = sandbox.simulate_hypothesis(
        valid_hypothesis,
        input_value=5,
        expected_output=10
    )
    print(f"有效假设测试: {'通过' if result.is_consistent else '失败'}")
    
    # 测试用例2: 无效的假设
    invalid_hypothesis = """
    def process(x):
        return x + 2
    """
    result = sandbox.simulate_hypothesis(
        invalid_hypothesis,
        input_value=5,
        expected_output=10
    )
    print(f"无效假设测试: {'通过' if result.is_consistent else '失败'}")
    print(f"逻辑错误: {result.logical_errors}")
    
    # 测试用例3: 复杂逻辑验证
    complex_hypothesis = """
    def process(data):
        if isinstance(data, dict):
            return {k: v*2 for k, v in data.items()}
        elif isinstance(data, list):
            return [x*2 for x in data]
        else:
            return data*2
    """
    
    # 添加自定义规则
    def custom_dict_rule(input_val, output_val, expected):
        if isinstance(input_val, dict):
            return all(output_val[k] == v*2 for k, v in input_val.items())
        return True
    
    result = sandbox.simulate_hypothesis(
        complex_hypothesis,
        input_value={'a': 1, 'b': 2},
        expected_output={'a': 2, 'b': 4},
        additional_rules=[custom_dict_rule]
    )
    print(f"复杂假设测试: {'通过' if result.is_consistent else '失败'}")