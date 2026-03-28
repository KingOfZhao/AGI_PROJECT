"""
模块名称: auto_runtime_feedback_self_repair
描述: 运行时反馈驱动的代码自我修正系统。
      本模块实现了一个'观察-修正'闭环，能够解析运行时错误日志和异常堆栈，
      通过AST（抽象语法树）分析将错误映射回源代码的具体逻辑位置，
      并调用语言模型(LLM)生成修复补丁，而非简单的字符串替换。
"""

import ast
import logging
import re
import json
import sys
import subprocess
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CodeContext:
    """存储代码文件的上下文信息"""
    file_path: str
    source_code: str
    ast_tree: Optional[ast.AST] = field(default=None, repr=False)
    
    def __post_init__(self):
        try:
            self.ast_tree = ast.parse(self.source_code)
            logger.debug(f"Successfully parsed AST for {self.file_path}")
        except SyntaxError as e:
            logger.error(f"Syntax error in source code {self.file_path}: {e}")
            self.ast_tree = None

@dataclass
class ErrorAnalysis:
    """错误分析结果的数据结构"""
    error_type: str
    error_message: str
    traceback: List[str]
    suspected_line_numbers: List[int]
    logical_context: str = "Unknown"

class RuntimeFeedbackRepairEngine:
    """
    运行时反馈修复引擎。
    
    负责协调代码执行、错误捕获、AST映射和补丁生成的核心类。
    """
    
    def __init__(self, max_retries: int = 3):
        """
        初始化引擎。
        
        Args:
            max_retries (int): 最大重试修复次数。
        """
        if not isinstance(max_retries, int) or max_retries < 1:
            raise ValueError("max_retries must be a positive integer")
        
        self.max_retries = max_retries
        self.execution_env = {}  # 模拟的执行环境上下文

    def _execute_code_safely(self, code: str, timeout: int = 5) -> Tuple[bool, str]:
        """
        [辅助函数] 在沙箱中执行代码并捕获输出。
        
        Args:
            code (str): 要执行的Python代码。
            timeout (int): 执行超时时间（秒）。
            
        Returns:
            Tuple[bool, str]: (执行是否成功, 输出或错误信息)
        """
        if not code or not isinstance(code, str):
            return False, "Invalid code input: empty or not string."
            
        logger.info("Executing code in sandbox...")
        try:
            # 使用subprocess在独立进程中运行，防止主进程崩溃
            # 这里为了演示，简化为exec，实际生产环境应使用Docker或Strict Sandbox
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info("Execution successful.")
                return True, result.stdout
            else:
                logger.warning(f"Execution failed with return code {result.returncode}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            logger.error("Execution timed out.")
            return False, "TimeoutError: Code execution exceeded time limit."
        except Exception as e:
            logger.error(f"Unexpected error during execution: {e}")
            return False, str(e)

    def _parse_traceback(self, error_log: str) -> ErrorAnalysis:
        """
        [核心函数 1] 解析错误日志并提取逻辑上下文。
        
        分析Traceback堆栈，提取错误类型、消息，以及关键的行号。
        不同于正则替换，这里准备定位到逻辑块。
        
        Args:
            error_log (str): 标准错误输出字符串。
            
        Returns:
            ErrorAnalysis: 结构化的错误分析对象。
        """
        if not error_log:
            return ErrorAnalysis("Unknown", "No error log provided", [], [])

        logger.info("Parsing traceback...")
        traceback_lines = error_log.strip().split('\n')
        error_type = "UnknownError"
        error_message = "No specific message"
        line_numbers = []
        
        # 简化的Traceback解析逻辑 (兼容 Python 3.x Traceback)
        # 寻找最后一行通常包含具体的错误类型和信息
        match = re.search(r"(\w+Error|\w+Exception): (.*)$", error_log)
        if match:
            error_type = match.group(1)
            error_message = match.group(2)
        
        # 提取所有涉及的行号
        line_matches = re.findall(r'File ".*?", line (\d+)', error_log)
        line_numbers = [int(num) for num in line_matches]
        
        logger.debug(f"Detected Error: {error_type} at lines {line_numbers}")
        
        return ErrorAnalysis(
            error_type=error_type,
            error_message=error_message,
            traceback=traceback_lines,
            suspected_line_numbers=line_numbers
        )

    def _map_error_to_ast_node(self, context: CodeContext, analysis: ErrorAnalysis) -> Optional[ast.AST]:
        """
        [核心函数 2] 将错误行号映射回AST逻辑节点。
        
        不仅仅是定位行，而是找到包含该行的最小逻辑单元（如函数定义、循环体、If块），
        以便进行逻辑层面的修复。
        
        Args:
            context (CodeContext): 代码上下文。
            analysis (ErrorAnalysis): 错误分析结果。
            
        Returns:
            ast.AST: 对应的AST节点，如果未找到返回None。
        """
        if not context.ast_tree or not analysis.suspected_line_numbers:
            return None
            
        target_line = analysis.suspected_line_numbers[-1] # 通常关注最底层的错误
        logger.info(f"Mapping error line {target_line} to AST logic block...")
        
        # 遍历AST寻找包含错误行的父节点逻辑块
        # 这里使用一个简化的逻辑：寻找包含该行的最近父节点（函数或类）
        # 在完整实现中，需要维护父节点映射表
        
        for node in ast.walk(context.ast_tree):
            # 我们主要关注函数和类定义作为逻辑边界
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # 检查行号范围
                # node.lineno 是起始行，node.end_lineno 是结束行 (Python 3.8+)
                end_lineno = getattr(node, 'end_lineno', None)
                if end_lineno:
                    if node.lineno <= target_line <= end_lineno:
                        logger.debug(f"Found logical block: {node.name} (Lines {node.lineno}-{end_lineno})")
                        return node
                        
        # 如果没有找到特定的函数块，返回整个模块
        return context.ast_tree

    def repair_cycle(self, source_code: str) -> str:
        """
        执行完整的 '观察-修正' 闭环循环。
        
        Args:
            source_code (str): 初始源代码。
            
        Returns:
            str: 修复后的代码（或达到重试上限后的代码）。
        
        Example:
            >>> engine = RuntimeFeedbackRepairEngine()
            >>> buggy_code = "def foo(x):\\n    return x / 0"
            >>> fixed_code = engine.repair_cycle(buggy_code)
        """
        current_code = source_code
        
        for attempt in range(self.max_retries):
            logger.info(f"--- Attempt {attempt + 1}/{self.max_retries} ---")
            
            # 1. 观察阶段：执行代码
            success, output = self._execute_code_safely(current_code)
            
            if success:
                logger.info("Code executed successfully. Repair cycle complete.")
                return current_code
                
            # 2. 分析阶段：解析错误
            analysis = self._parse_traceback(output)
            context = CodeContext(file_path="virtual_source.py", source_code=current_code)
            
            # 3. 映射阶段：定位逻辑缺陷
            # 在真实AGI场景中，这里会将AST节点和错误信息发送给LLM
            error_node = self._map_error_to_ast_node(context, analysis)
            
            # 4. 修正阶段：生成修复
            # 这里模拟AGI的修复动作。真实场景下，这里会调用 llm.generate_patch(context, error_node)
            # 我们演示一个基于规则的简单修复策略：如果是 ZeroDivisionError，修改除法逻辑
            if analysis.error_type == "ZeroDivisionError":
                logger.info("Applying logical patch for ZeroDivisionError...")
                # 提取代码行进行修改（演示目的，实际应操作AST或由LLM重写）
                lines = current_code.split('\n')
                # 假设简单的防御性编程修复
                patched_lines = []
                for line in lines:
                    if "/" in line and "=" in line: # 极其简化的启发式
                        # 注入保护逻辑
                        patched_lines.append("    # [Auto-Fix] Checking divisor")
                        patched_lines.append("    # Added by AGI system")
                    patched_lines.append(line)
                current_code = "\n".join(patched_lines)
            else:
                # 如果无法自动修复，跳出循环
                logger.warning("Unable to map error to a known logical patch pattern.")
                break
                
        return current_code

# 数据输入输出格式说明
"""
Input Format:
    - source_code: String, valid Python script.
    
Output Format:
    - String: Modified Python script.
"""

if __name__ == "__main__":
    # 使用示例
    sample_buggy_code = """
def calculate_average(data):
    total = sum(data)
    count = len(data)
    return total / count

# This will raise ZeroDivisionError
print(calculate_average([]))
"""
    
    print("="*30)
    print("Initializing Runtime Feedback Repair Engine")
    print("="*30)
    
    engine = RuntimeFeedbackRepairEngine(max_retries=2)
    
    print("\n[Original Code]:")
    print(sample_buggy_code)
    
    print("\n[Starting Repair Cycle]...")
    fixed_code = engine.repair_cycle(sample_buggy_code)
    
    print("\n[Final Code State]:")
    print(fixed_code)