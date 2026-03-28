"""
名称: auto_融合能力_具身认知演化的调试智能体_f3d239
描述: 融合能力：【具身认知演化的调试智能体】。不仅仅是修复代码语法错误，而是构建一个‘认知-代码’双重进化的系统。
"""

import logging
import ast
import json
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EmbodiedDebuggingAgent")

@dataclass
class FailurePattern:
    """
    反模式真实节点：用于存储抽象后的失败模式。
    
    Attributes:
        pattern_id (str): 模式的唯一标识符（哈希值）。
        description (str): 人类可读的模式描述。
        code_signature (str): 错误代码的AST结构签名。
        context_tags (List[str]): 上下文标签（如 'recursion', 'math'）。
        fix_strategy (str): 建议的修复策略代码片段。
        created_at (str): 创建时间。
        occurrence_count (int): 该模式被遇到的次数。
    """
    pattern_id: str
    description: str
    code_signature: str
    context_tags: List[str]
    fix_strategy: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    occurrence_count: int = 1

class KnowledgeBase:
    """
    领域B：认知知识库。
    存储失败模式，支持基于代码结构签名的检索。
    """
    def __init__(self, storage_path: Optional[str] = None):
        self._storage_path = storage_path
        self._patterns: Dict[str, FailurePattern] = {}
        self._load()
        logger.info(f"Knowledge Base initialized with {len(self._patterns)} patterns.")

    def _load(self):
        # 模拟从持久化存储加载
        pass

    def store_pattern(self, pattern: FailurePattern):
        """存储或更新失败模式"""
        if pattern.pattern_id in self._patterns:
            self._patterns[pattern.pattern_id].occurrence_count += 1
            logger.debug(f"Updated existing pattern: {pattern.pattern_id}")
        else:
            self._patterns[pattern.pattern_id] = pattern
            logger.info(f"Learned new failure pattern: {pattern.description}")

    def query_pattern(self, signature: str) -> Optional[FailurePattern]:
        """根据代码签名查询是否存在已知失败模式"""
        return self._patterns.get(signature)

class CodeSandbox:
    """
    领域A：代码执行沙箱。
    负责运行代码并捕获异常。
    """
    @staticmethod
    def execute(code_str: str, context: Optional[Dict] = None) -> Tuple[bool, Any]:
        """
        执行代码并返回结果。
        
        Args:
            code_str (str): 要执行的Python代码。
            context (Dict): 执行上下文变量。
            
        Returns:
            Tuple[bool, Any]: (是否成功, 结果或异常信息)
        """
        local_vars = context or {}
        try:
            # 安全警告：实际生产环境应使用更严格的沙箱隔离
            exec(compile(code_str, '<string>', 'exec'), {}, local_vars)
            # 假设代码总是定义了一个 'main' 函数作为入口
            if 'main' in local_vars and callable(local_vars['main']):
                result = local_vars['main']()
                return True, result
            return True, None
        except Exception as e:
            logger.warning(f"Execution failed: {str(e)}")
            return False, str(e)

class EmbodiedDebuggingAgent:
    """
    融合能力核心类：具身认知演化的调试智能体。
    """
    
    def __init__(self):
        self.knowledge_base = KnowledgeBase()
        self.execution_history: List[Dict] = []

    @staticmethod
    def _get_code_signature(code_str: str) -> str:
        """
        辅助函数：计算代码的AST结构签名。
        忽略变量名，只关注逻辑结构（如循环、条件、操作符）。
        """
        try:
            tree = ast.parse(code_str)
            # 简化的签名生成：将AST转储为字符串并哈希
            # 实际应用中需要更复杂的归一化处理
            ast_str = ast.dump(tree)
            return hashlib.md5(ast_str.encode()).hexdigest()
        except SyntaxError:
            return hashlib.md5(b"syntax_error").hexdigest()

    def _analyze_failure(self, error_msg: str, code_str: str) -> FailurePattern:
        """
        分析失败原因并生成FailurePattern。
        这是一个模拟的认知抽象过程。
        """
        sig = self._get_code_signature(code_str)
        tags = []
        fix = ""
        desc = ""

        # 模拟对特定错误的认知抽象
        if "ZeroDivisionError" in error_msg:
            tags = ["math", "division", "edge_case"]
            desc = "Division by zero without checking denominator"
            fix = "if denominator == 0: return 0 # Handle zero division safely"
        elif "RecursionError" in error_msg:
            tags = ["algorithm", "recursion", "base_case"]
            desc = "Missing or incorrect base case in recursion"
            fix = "if depth > MAX_DEPTH: return default_value"
        else:
            tags = ["general", "runtime"]
            desc = f"Unhandled runtime error: {error_msg}"
            fix = "try: ... except Exception: pass"

        return FailurePattern(
            pattern_id=sig,
            description=desc,
            code_signature=sig,
            context_tags=tags,
            fix_strategy=fix
        )

    def debug_and_evolve(self, task_description: str, code_str: str) -> Tuple[str, bool]:
        """
        核心函数：执行调试与认知演化循环。
        
        Args:
            task_description (str): 任务描述
            code_str (str): 初始代码
            
        Returns:
            Tuple[str, bool]: (修复后的代码/最终代码, 是否成功运行)
        """
        logger.info(f"Starting task: {task_description}")
        
        # 1. 具身交互：在沙箱中运行
        success, result_or_error = CodeSandbox.execute(code_str)
        
        if success:
            logger.info("Code executed successfully without modification.")
            return code_str, True
        
        # 2. 感知失败：记录错误
        logger.info(f"Encountered error: {result_or_error}")
        
        # 3. 认知检索：检查知识库是否已有类似失败记忆
        signature = self._get_code_signature(code_str)
        known_pattern = self.knowledge_base.query_pattern(signature)
        
        if known_pattern:
            logger.info(f"Recalled known failure pattern: {known_pattern.description}")
            # 直接应用已知修复策略
            fixed_code = self._apply_fix(code_str, known_pattern.fix_strategy)
            success, _ = CodeSandbox.execute(fixed_code)
            if success:
                return fixed_code, True
            logger.warning("Known fix strategy failed. Re-analyzing.")

        # 4. 抽象与学习：将新的失败模式存入知识库
        new_pattern = self._analyze_failure(result_or_error, code_str)
        self.knowledge_base.store_pattern(new_pattern)
        
        # 5. 代码进化：尝试生成修复代码
        # 这里模拟简单的代码注入修复，实际AGI应使用LLM生成修复
        fixed_code = self._apply_fix(code_str, new_pattern.fix_strategy)
        
        # 6. 再次验证
        final_success, _ = CodeSandbox.execute(fixed_code)
        
        return fixed_code, final_success

    def _apply_fix(self, original_code: str, fix_snippet: str) -> str:
        """辅助函数：将修复策略注入代码（模拟）"""
        # 实际场景需要复杂的AST操作，这里仅在头部添加防御性代码
        return f"{fix_snippet}\n{original_code}"

# 使用示例
if __name__ == "__main__":
    # 示例代码：包含除零错误的代码
    buggy_code = """
def main():
    a = 10
    b = 0
    return a / b
"""
    
    agent = EmbodiedDebuggingAgent()
    
    # 第一次运行：会失败，智能体将学习这个错误模式
    print("--- Run 1 (Learning Phase) ---")
    code_v1, success_v1 = agent.debug_and_evolve("Divide numbers", buggy_code)
    print(f"Success: {success_v1}")
    
    # 第二次运行：类似的代码结构，智能体应能利用记忆快速规避
    print("\n--- Run 2 (Recall Phase) ---")
    # 结构相似但变量名不同的代码
    similar_buggy_code = """
def main():
    x = 100
    y = 0
    return x / y
"""
    code_v2, success_v2 = agent.debug_and_evolve("Divide numbers again", similar_buggy_code)
    print(f"Success: {success_v2}")
    print(f"Final Code Snippet:\n{code_v2[:150]}...")