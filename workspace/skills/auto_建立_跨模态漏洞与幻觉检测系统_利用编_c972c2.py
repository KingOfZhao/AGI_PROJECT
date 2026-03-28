"""
跨模态漏洞与幻觉检测系统

本模块实现了一个利用编译器技术（数据流分析）与NLP语义分析相结合的混合系统。
旨在检测代码中的安全漏洞、资源泄漏以及代码与文档意图不一致的“逻辑幻觉”。

核心功能：
1. 数据流分析：检测未初始化变量、资源泄漏（文件/连接未关闭）。
2. 意图一致性校验：利用NLP分析自然语言注释，对比代码实际控制流，发现逻辑冲突。

作者: AGI System
版本: 1.0.0
"""

import re
import ast
import logging
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CrossModalValidator")

class IssueSeverity(Enum):
    """问题严重等级"""
    CRITICAL = "CRITICAL"  # 严重漏洞/崩溃风险
    WARNING = "WARNING"    # 潜在问题/意图违背
    INFO = "INFO"          # 代码风格/建议

@dataclass
class ValidationIssue:
    """验证问题数据结构"""
    line_number: int
    issue_type: str
    message: str
    severity: IssueSeverity
    source: str  # 'compiler_logic' 或 'nlp_logic'

@dataclass
class CodeContext:
    """代码上下文信息"""
    source_code: str
    ast_tree: Optional[ast.AST] = None
    comments: Dict[int, str] = field(default_factory=dict)
    variables: Set[str] = field(default_factory=set)
    resources: Set[str] = field(default_factory=set)

class NLPIntentAnalyzer:
    """
    模拟NLP意图分析器
    在真实AGI场景中，这里会接入LLM（如GPT-4）进行语义理解。
    此处使用规则+关键词匹配来模拟高级语义分析。
    """
    
    def __init__(self):
        # 意图关键词映射
        self.intent_patterns = {
            'timeout_required': r'(必须|一定|need to).*(超时|退出|timeout|exit)',
            'security_sensitive': r'(加密|密码|机密|encrypt|password|secret)',
            'resource_management': r'(释放|关闭|释放资源|free|close|cleanup)'
        }

    def analyze_comment(self, comment_text: str) -> Dict[str, Any]:
        """
        分析单行注释的意图
        
        Args:
            comment_text: 注释文本
            
        Returns:
            包含意图标签的字典
        """
        intents = {}
        if not comment_text:
            return intents
            
        comment_text = comment_text.lower()
        
        for intent_name, pattern in self.intent_patterns.items():
            if re.search(pattern, comment_text, re.IGNORECASE):
                intents[intent_name] = True
                logger.debug(f"Detected intent '{intent_name}' in comment: {comment_text}")
                
        return intents

class DataFlowAnalyzer(ast.NodeVisitor):
    """
    数据流分析器 (基于AST)
    模拟编译器的静态分析过程，追踪变量生命周期和资源状态。
    """
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self.variables: Dict[str, str] = {} # var_name -> state ('defined', 'used', 'closed')
        self.resources: Dict[str, bool] = {} # var_name -> is_open
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
        # 函数结束时检查未关闭的资源
        self._check_resource_leaks()

    def visit_Assign(self, node: ast.Assign):
        # 简单的变量定义检测
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                self.variables[var_name] = 'defined'
                
                # 检测常见的资源打开模式 (模拟)
                if isinstance(node.value, ast.Call):
                    if hasattr(node.value.func, 'id') and node.value.func.id in ['open', 'connect']:
                        self.resources[var_name] = True
                        logger.debug(f"Resource opened: {var_name}")
        
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        # 检查未初始化使用
        if isinstance(node.ctx, ast.Load):
            if node.id not in self.variables:
                self.issues.append(
                    ValidationIssue(
                        line_number=node.lineno,
                        issue_type="UninitializedVariable",
                        message=f"Variable '{node.id}' might be used before initialization.",
                        severity=IssueSeverity.WARNING,
                        source="compiler_logic"
                    )
                )
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        # 检测上下文管理器 (良好的资源管理)
        for item in node.items:
            if isinstance(item.optional_vars, ast.Name):
                res_name = item.optional_vars.id
                self.resources[res_name] = False # Mark as safely managed
        self.generic_visit(node)

    def _check_resource_leaks(self):
        for res, is_open in self.resources.items():
            if is_open:
                self.issues.append(
                    ValidationIssue(
                        line_number=0, # 模拟全局行号
                        issue_type="ResourceLeak",
                        message=f"Resource '{res}' was opened but not explicitly closed or managed via 'with'.",
                        severity=IssueSeverity.CRITICAL,
                        source="compiler_logic"
                    )
                )

class CrossModalValidator:
    """
    核心验证系统
    结合静态分析（编译器逻辑）与语义分析（NLP逻辑）。
    """
    
    def __init__(self):
        self.nlp_analyzer = NLPIntentAnalyzer()
        
    def _extract_comments(self, source_code: str) -> Dict[int, str]:
        """
        辅助函数：提取代码中的注释及其行号
        
        Args:
            source_code: 源代码字符串
            
        Returns:
            字典: {行号: 注释内容}
        """
        comments = {}
        lines = source_code.split('\n')
        for i, line in enumerate(lines, 1):
            # 简单的注释提取逻辑（支持 # 风格）
            if '#' in line:
                comment_part = line.split('#', 1)[1].strip()
                if comment_part:
                    comments[i] = comment_part
        return comments

    def validate_code_intent_alignment(self, source_code: str) -> List[ValidationIssue]:
        """
        核心函数：验证代码逻辑与自然语言意图的一致性
        
        此函数专门检测“逻辑正确但意图违背”的错误。
        例如：代码无死循环（编译器通过），但注释要求必须超时退出（NLP意图）。
        
        Args:
            source_code: 待检测的源代码
            
        Returns:
            验证问题列表
        """
        issues = []
        comments = self._extract_comments(source_code)
        
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            issues.append(ValidationIssue(
                line_number=e.lineno or 0,
                issue_type="SyntaxError",
                message=f"Code cannot be parsed: {e.msg}",
                severity=IssueSeverity.CRITICAL,
                source="compiler_logic"
            ))
            return issues

        # 1. NLP意图扫描
        intent_map: Dict[int, Dict[str, Any]] = {}
        for line_no, text in comments.items():
            intents = self.nlp_analyzer.analyze_comment(text)
            if intents:
                intent_map[line_no] = intents

        # 2. 结构化逻辑扫描 (检查控制流结构)
        # 这里我们检查是否存在特定的控制流结构来满足意图
        
        # 模拟检查：超时意图 vs 循环结构
        # 假设如果注释要求超时，代码中应该包含 'while' 或 'time' 相关调用
        has_timeout_intent = any('timeout_required' in intents for intents in intent_map.values())
        
        # 检查代码结构
        has_loop = any(isinstance(node, (ast.While, ast.For)) for node in ast.walk(tree))
        has_time_check = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                # 模拟检测 time.time() > xxx 之类的比较
                if isinstance(node.left, ast.Call) and hasattr(node.left.func, 'attr'):
                    if node.left.func.attr == 'time': # 简化判断
                        has_time_check = True

        # 跨模态验证逻辑
        if has_timeout_intent:
            if not (has_loop and has_time_check):
                # 找到提出该意图的行号
                intent_line = [k for k, v in intent_map.items() if 'timeout_required' in v][0]
                issues.append(ValidationIssue(
                    line_number=intent_line,
                    issue_type="IntentMismatch",
                    message="Comment requires timeout/exit behavior, but code lacks necessary timing control logic.",
                    severity=IssueSeverity.WARNING,
                    source="nlp_logic"
                ))

        return issues

    def perform_full_analysis(self, source_code: str) -> Tuple[bool, List[ValidationIssue]]:
        """
        执行完整的跨模态分析
        
        Args:
            source_code (str): 输入的Python源代码
            
        Returns:
            Tuple[bool, List]: (是否通过检查, 问题列表)
        """
        if not source_code or not isinstance(source_code, str):
            raise ValueError("Input must be a non-empty string.")
            
        logger.info("Starting Cross-Modal Vulnerability & Hallucination Analysis...")
        
        all_issues = []
        
        # 阶段 1: 编译器风格的数据流分析
        try:
            tree = ast.parse(source_code)
            analyzer = DataFlowAnalyzer()
            analyzer.visit(tree)
            all_issues.extend(analyzer.issues)
        except Exception as e:
            logger.error(f"AST Analysis failed: {e}")
            all_issues.append(ValidationIssue(
                0, "AnalysisException", str(e), IssueSeverity.CRITICAL, "system"
            ))

        # 阶段 2: NLP驱动的意图一致性分析
        intent_issues = self.validate_code_intent_alignment(source_code)
        all_issues.extend(intent_issues)
        
        # 结果汇总
        has_critical = any(issue.severity == IssueSeverity.CRITICAL for issue in all_issues)
        passed = not has_critical
        
        logger.info(f"Analysis complete. Issues found: {len(all_issues)}. Passed: {passed}")
        return passed, all_issues

# 使用示例
if __name__ == "__main__":
    # 示例代码：包含资源泄漏和意图违背
    test_code = """
def process_data(file_path):
    # This connection must timeout after 5 seconds (Intent: timeout_required)
    f = open(file_path, 'r')  # Issue: Resource Leak (no close/with)
    data = f.read()
    
    # Complex logic
    while True:
        do_something() 
        # Missing time check for timeout intent
    
    return data

def calculate_sum(a, b):
    # Security sensitive operation
    return a + result  # Issue: result is not defined
"""

    validator = CrossModalValidator()
    is_valid, issues = validator.perform_full_analysis(test_code)
    
    print(f"\n=== Validation Report ===")
    print(f"Code Valid: {is_valid}")
    print(f"Issues Detected: {len(issues)}")
    
    for issue in issues:
        print(f"[{issue.severity.value}] Line {issue.line_number}: {issue.message} (Source: {issue.source})")