"""
幻觉代码过滤机制模块 (Hallucination Code Filter Mechanism)

本模块实现了一个基于AST（抽象语法树）的静态分析器，旨在过滤大模型生成的代码中的
"幻觉"内容。通过维护一个严格的"真实节点"白名单（即经过验证的API、库名和函数名），
确保生成的代码仅包含已知的、可执行的元素，从而强制AI在认知自洽的边界内工作。

版本: 1.0.0
作者: AGI System
"""

import ast
import logging
import json
from typing import List, Dict, Set, Optional, Any, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CodeSecurityError(Exception):
    """自定义异常：当代码包含未验证的节点时抛出。"""
    pass

class HallucinationFilter:
    """
    基于'真实节点'白名单的代码幻觉过滤器。
    
    该类解析Python代码字符串，遍历其抽象语法树，并将所有调用、属性和导入
    与预定义的白名单进行比对。
    
    Attributes:
        verified_apis (Set[str]): 已验证的API名称集合。
        verified_modules (Set[str]): 已验证的模块名称集合。
        verified_patterns (Set[str]): 已验证的代码模式（保留扩展）。
    """

    def __init__(self, whitelist_config: Dict[str, List[str]]):
        """
        初始化过滤器。
        
        Args:
            whitelist_config (Dict[str, List[str]]): 包含白名单配置的字典。
                期望键: 'apis', 'modules', 'patterns'.
        """
        self.verified_apis: Set[str] = set(whitelist_config.get('apis', []))
        self.verified_modules: Set[str] = set(whitelist_config.get('modules', []))
        self.verified_patterns: Set[str] = set(whitelist_config.get('patterns', []))
        
        logger.info("HallucinationFilter initialized with %d APIs and %d Modules.",
                    len(self.verified_apis), len(self.verified_modules))

    def _validate_syntax(self, code_str: str) -> ast.AST:
        """
        辅助函数：验证代码语法并生成AST。
        
        Args:
            code_str (str): 待检查的代码字符串。
            
        Returns:
            ast.AST: 解析后的抽象语法树根节点。
            
        Raises:
            SyntaxError: 如果代码包含语法错误。
        """
        try:
            tree = ast.parse(code_str)
            logger.debug("Code syntax parsed successfully.")
            return tree
        except SyntaxError as e:
            logger.error("Syntax error in generated code: %s", e)
            raise

    def _check_imports(self, node: ast.stmt) -> Optional[str]:
        """
        辅助函数：检查import语句是否在白名单中。
        
        Args:
            node (ast.stmt): AST节点，通常是Import或ImportFrom。
            
        Returns:
            Optional[str]: 如果发现非法导入，返回模块名；否则返回None。
        """
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in self.verified_modules:
                    return alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if module not in self.verified_modules:
                return module
        return None

    def scan_for_hallucinations(self, code_str: str) -> Tuple[bool, List[str]]:
        """
        核心函数：扫描代码并识别潜在的幻觉或未授权API调用。
        
        此函数执行静态分析，提取所有函数调用和属性访问，并与白名单交叉验证。
        
        Args:
            code_str (str): 待扫描的Python代码字符串。
            
        Returns:
            Tuple[bool, List[str]]: 
                - bool: 如果代码"干净"（所有节点均真实）则为True，否则为False。
                - List[str]: 检测到的违规节点/名称列表。
        
        Example Input:
            code_str = "import os\\nprint(os.listdir('.'))"
            
        Example Output:
            (True, [])
        """
        violations: List[str] = []
        
        try:
            tree = self._validate_syntax(code_str)
        except SyntaxError:
            return (False, ["SyntaxError: Invalid code structure"])

        # 遍历AST节点
        for node in ast.walk(tree):
            # 1. 检查导入
            illegal_import = self._check_imports(node)
            if illegal_import:
                violations.append(f"Illegal Import: {illegal_import}")
                # 不立即返回，收集所有错误以供调试
            
            # 2. 检查函数调用
            if isinstance(node, ast.Call):
                # 获取函数的完整名称 (例如 "requests.get")
                # 这里简化处理，仅检查直接的func Name或Attribute
                call_name = self._get_node_call_name(node.func)
                if call_name and call_name not in self.verified_apis:
                    violations.append(f"Unverified API Call: {call_name}")
            
            # 3. (可选) 检查危险属性访问 (如 __import__)
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith('_') and not node.attr.startswith('__'):
                    violations.append(f"Access to protected member: {node.attr}")

        is_clean = len(violations) == 0
        if not is_clean:
            logger.warning("Hallucination detected: %s", violations)
        
        return (is_clean, violations)

    def _get_node_call_name(self, node: ast.expr) -> str:
        """
        辅助函数：递归解析AST节点以构建完整的调用名称字符串。
        
        Args:
            node (ast.expr): 函数调用节点。
            
        Returns:
            str: 解析出的名称（如 "math.sqrt"）。
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_node_call_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        return ""

    def enforce_reality(self, code_str: str) -> str:
        """
        核心函数：强制执行真实性检查，如果发现幻觉则阻止代码。
        
        这是一个严格的门控函数，用于生产环境。
        
        Args:
            code_str (str): 待检查的代码。
            
        Returns:
            str: 验证通过的原始代码。
            
        Raises:
            CodeSecurityError: 如果检测到任何未验证的节点。
        """
        logger.info("Enforcing reality check on code block...")
        is_valid, issues = self.scan_for_hallucinations(code_str)
        
        if not is_valid:
            error_msg = f"Code rejected due to hallucination risks: {'; '.join(issues)}"
            logger.critical(error_msg)
            raise CodeSecurityError(error_msg)
            
        logger.info("Code passed reality check. Approved for execution.")
        return code_str

# 配置示例数据
DEFAULT_WHITELIST = {
    "modules": [
        "os", "sys", "math", "json", "datetime", "logging", 
        "typing", "collections", "functools", "itertools", "time"
    ],
    "apis": [
        "print", "len", "range", "str", "int", "float", "list", "dict", "set",
        "os.path.join", "os.getcwd", "json.dumps", "json.loads", 
        "math.sqrt", "math.pi", "logging.info", "time.sleep"
    ],
    "patterns": [
        "list_comprehension", "try_except_block"
    ]
}

if __name__ == "__main__":
    # 使用示例
    print("--- Initializing Hallucination Filter ---")
    filter_system = HallucinationFilter(DEFAULT_WHITELIST)
    
    # 测试用例 1: 合法代码
    safe_code = """
import math
import json

def calculate_area(r):
    return math.pi * (r ** 2)

data = {"area": calculate_area(5)}
print(json.dumps(data))
"""
    
    print("\n--- Testing Safe Code ---")
    try:
        result = filter_system.enforce_reality(safe_code)
        print("Result: Code Approved.")
    except CodeSecurityError as e:
        print(f"Result: Code Rejected - {e}")

    # 测试用例 2: 幻觉代码 (不存在的库和API)
    hallucinated_code = """
import hyperspace # This library does not exist in whitelist
import numpy as np # Numpy not in whitelist

def activate_ai():
    # 'telepathy.connect' is a hallucinated API
    client = telepathy.connect(host='brain')
    client.think()
"""
    
    print("\n--- Testing Hallucinated Code ---")
    try:
        filter_system.enforce_reality(hallucinated_code)
        print("Result: Code Approved (Unexpected).")
    except CodeSecurityError as e:
        print(f"Result: Code Rejected (Expected). Details: {e}")

    # 测试用例 3: 部分合法但包含未验证API
    mixed_code = """
import os
# 'os.system' might be in module 'os', but 'rm -rf' is dangerous 
# and 'hacker_tool' is not verified.
os.system('rm -rf /')
hacker_tool.exploit()
"""
    print("\n--- Testing Mixed Code ---")
    is_clean, details = filter_system.scan_for_hallucinations(mixed_code)
    print(f"Clean: {is_clean}")
    print(f"Violations: {details}")