"""
幻觉代码检测模块

本模块提供了一套用于检测大模型生成代码中潜在API幻觉的工具。
通过维护一个包含2621个已知节点的白名单，对AST解析出的函数调用进行事实核查，
从而拦截对不存在库函数的调用，提升AI生成代码的可靠性和安全性。

典型用例:
    >>> from auto_幻觉代码检测_大模型倾向于生成看似合理_77f3c3 import HallucinationDetector
    >>> whitelist = ["print", "open", "math.sqrt", "os.path.join"]
    >>> detector = HallucinationDetector(valid_api_whitelist=whitelist)
    >>> code = "import math\\nmath.sqrrt(25)" # typo in sqrt
    >>> result = detector.audit_code_block(code)
    >>> if result['has_errors']:
    ...     print(f"发现幻觉调用: {result['violations']}")

数据格式:
    输入: Python源代码字符串
    输出: 包含检测结果的字典，格式如下:
    {
        "has_errors": bool,
        "violations": List[Dict[str, str]],
        "statistics": Dict[str, int]
    }
"""

import ast
import logging
import re
from typing import List, Dict, Set, Any, Optional, Tuple

# 配置模块级日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HallucinationDetector:
    """
    大模型代码幻觉检测器。
    
    利用抽象语法树（AST）分析代码结构，提取所有函数调用节点，
    并将其与预定义的有效API白名单进行比对。
    
    Attributes:
        valid_apis (Set[str]): 存储已知有效API调用的集合。
        strict_mode (bool): 是否启用严格模式（默认为False）。
                            严格模式下，任何不在白名单中的调用都会报警；
                            非严格模式下，仅报警看起来像库调用（包含点号）的未知函数。
    """

    def __init__(self, valid_api_whitelist: List[str], strict_mode: bool = False) -> None:
        """
        初始化检测器实例。

        Args:
            valid_api_whitelist (List[str]): 有效API全名的列表（例如 'numpy.array'）。
            strict_mode (bool): 检测严格程度。
        
        Raises:
            ValueError: 如果白名单为空或类型错误。
        """
        if not isinstance(valid_api_whitelist, list):
            logger.error("白名单必须是一个列表。")
            raise ValueError("valid_api_whitelist must be a list")
        
        if len(valid_api_whitelist) < 1:
            logger.warning("初始化时提供了空白名单，所有调用将被视为违规（如果在严格模式下）。")

        # 使用集合提高查找效率 O(1)
        self.valid_apis: Set[str] = set(valid_api_whitelist)
        self.strict_mode = strict_mode
        logger.info(f"HallucinationDetector 初始化完成，加载了 {len(self.valid_apis)} 个白名单节点。")

    def _resolve_call_name(self, node: ast.Call) -> Optional[str]:
        """
        辅助函数：从AST Call节点解析出完整的函数名称字符串。
        
        支持解析:
        - func() -> "func"
        - obj.func() -> "obj.func"
        - mod.submod.func() -> "mod.submod.func"
        
        Args:
            node (ast.Call): AST调用节点。
            
        Returns:
            Optional[str]: 解析出的函数名字符串，如果无法解析则返回None。
        """
        try:
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                # 递归构建属性访问链
                return self._unparse_attribute_chain(node.func)
            else:
                return None
        except Exception as e:
            logger.debug(f"解析调用节点名称时出错: {e}")
            return None

    def _unparse_attribute_chain(self, node: ast.Attribute) -> str:
        """
        递归辅助函数：将嵌套的属性节点转换为字符串路径。
        
        Args:
            node (ast.Attribute): 属性节点。
            
        Returns:
            str: 完整的属性路径（例如 "os.path.join"）。
        """
        # 如果是简单的名称，停止递归
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        # 如果还是属性，继续递归
        elif isinstance(node.value, ast.Attribute):
            parent = self._unparse_attribute_chain(node.value)
            return f"{parent}.{node.attr}"
        # 其他情况（如函数返回值调用 func()()），暂不处理深度路径
        return node.attr

    def _validate_single_call(self, call_name: str) -> Tuple[bool, str]:
        """
        核心验证逻辑：检查单个调用是否在白名单中。
        
        Args:
            call_name (str): 提取出的函数调用名。
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误类型描述)
        """
        if not call_name:
            return True, "Unknown"

        # 1. 精确匹配
        if call_name in self.valid_apis:
            return True, "Valid"

        # 2. 模糊匹配逻辑（可选，用于处理 'list.append' 这种可能不需要注册的方法）
        # 在本实现中，我们主要关注库函数。
        
        # 3. 违规判定
        # 如果是非严格模式，我们主要关注看起来像库调用的（包含'.'）或者不在Python内置函数中的
        # 但为了演示"幻觉检测"，我们假设白名单是全量的
        
        if self.strict_mode:
            return False, "Unknown API in strict mode"
        
        # 非严格模式启发式：如果是简单的局部变量调用（无点号），可能动态生成的，放过
        if '.' not in call_name:
            return True, "Local/Dynamic call ignored"

        return False, "Potential Hallucination"

    def audit_code_block(self, source_code: str) -> Dict[str, Any]:
        """
        对给定的Python源代码字符串进行幻觉检测审计。
        
        Args:
            source_code (str): 待检测的Python代码。
            
        Returns:
            Dict[str, Any]: 包含检测结果的字典。
                - 'has_errors' (bool): 是否发现潜在幻觉。
                - 'violations' (List[Dict]): 违规详情列表。
                - 'statistics' (Dict): 统计信息。
                
        Raises:
            SyntaxError: 如果输入的代码有语法错误无法解析AST。
        """
        if not source_code or not isinstance(source_code, str):
            logger.warning("输入源代码为空或格式不正确。")
            return {"has_errors": False, "violations": [], "statistics": {"total_calls": 0}}

        logger.info("开始代码审计...")
        violations = []
        total_calls = 0
        valid_calls = 0

        try:
            # 解析AST
            tree = ast.parse(source_code)
        except SyntaxError as e:
            logger.error(f"代码语法错误，无法解析: {e}")
            raise SyntaxError(f"Input code contains syntax errors: {e}")

        # 遍历AST
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                total_calls += 1
                call_name = self._resolve_call_name(node)
                
                if call_name:
                    is_valid, reason = self._validate_single_call(call_name)
                    
                    if not is_valid:
                        # 获取行号
                        line_no = getattr(node, 'lineno', -1)
                        violation_info = {
                            "line": line_no,
                            "invalid_api": call_name,
                            "reason": reason,
                            "suggestion": "Check for typos or verify library existence"
                        }
                        violations.append(violation_info)
                        logger.warning(f"第 {line_no} 行发现可疑调用: {call_name}")
                    else:
                        valid_calls += 1
                
        has_errors = len(violations) > 0
        
        result = {
            "has_errors": has_errors,
            "violations": violations,
            "statistics": {
                "total_calls": total_calls,
                "valid_calls": valid_calls,
                "invalid_calls": len(violations)
            }
        }
        
        logger.info(f"审计完成。总调用: {total_calls}, 发现问题: {len(violations)}")
        return result

# 示例用法和自测
if __name__ == "__main__":
    # 模拟的2621个节点白名单（这里简化为示例）
    MOCK_WHITELIST = [
        "print", "len", "range", "open", 
        "numpy.array", "numpy.zeros", 
        "pandas.DataFrame", "pandas.read_csv",
        "os.path.join", "os.listdir",
        "math.sqrt", "math.pow",
        "requests.get"
    ]
    
    # 包含幻觉代码的示例
    TEST_CODE = """
import numpy as np
import os

# 正确的调用
data = np.array([1, 2, 3])
print(len(data))

# 幻觉调用：函数名拼写错误
# 假设 np.arrayer 不存在
dummy = np.arrayer([4, 5, 6])

# 幻觉调用：完全虚构的库
# 假设 halucinate_lib 不在白名单中
result = halucinate_lib.do_magic()

# 动态生成调用（通常在非严格模式下忽略）
func_name = "test"
locals()[func_name]() 
"""

    print("--- 初始化检测器 ---")
    detector = HallucinationDetector(valid_api_whitelist=MOCK_WHITELIST, strict_mode=False)
    
    print("\n--- 运行检测 ---")
    try:
        report = detector.audit_code_block(TEST_CODE)
        
        print("\n--- 检测报告 ---")
        print(f"是否存在风险: {report['has_errors']}")
        print(f"统计信息: {report['statistics']}")
        print("违规详情:")
        for v in report['violations']:
            print(f"  [Line {v['line']}]: {v['invalid_api']} ({v['reason']})")
            
    except SyntaxError:
        print("代码语法分析失败。")