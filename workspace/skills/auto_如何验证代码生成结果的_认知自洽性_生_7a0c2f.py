"""
模块名称: auto_如何验证代码生成结果的_认知自洽性_生_7a0c2f
描述: 本模块构建了一个基于'真实节点'的上下文检查器，用于验证代码生成结果的认知自洽性。
      它不仅检查语法，还通过解析代码结构（AST）和语义特征，验证代码是否在特定业务领域
      （如爬虫、数据分析）包含了必须的子步骤（如异常处理、存储、配置），确保逻辑闭环。
"""

import ast
import logging
import json
import re
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DomainType(Enum):
    """支持的领域类型枚举"""
    WEB_SCRAPING = "web_scraping"
    DATA_ANALYSIS = "data_analysis"
    API_SERVICE = "api_service"
    FILE_PROCESSING = "file_processing"

@dataclass
class DomainContext:
    """
    领域上下文配置类。
    定义了特定领域为了达到'认知自洽'所必须包含的逻辑节点（关键步骤）。
    """
    domain: DomainType
    required_imports: Set[str] = field(default_factory=set)
    required_logic_nodes: Set[str] = field(default_factory=set)
    required_function_patterns: Set[str] = field(default_factory=set)

# 定义不同领域的自洽性规则
CONTEXT_RULES: Dict[DomainType, DomainContext] = {
    DomainType.WEB_SCRAPING: DomainContext(
        domain=DomainType.WEB_SCRAPING,
        required_imports={"requests", "bs4", "selenium", "scrapy", "httpx"},
        required_logic_nodes={"exception_handling", "storage_logic", "request_loop"},
        required_function_patterns={"def parse", "def save", "def get_html"}
    ),
    DomainType.DATA_ANALYSIS: DomainContext(
        domain=DomainType.DATA_ANALYSIS,
        required_imports={"pandas", "numpy", "matplotlib", "sklearn"},
        required_logic_nodes={"data_cleaning", "data_visualization", "model_training"},
        required_function_patterns={"def clean", "def train", "def plot"}
    )
}

class CodeAnalysisVisitor(ast.NodeVisitor):
    """
    AST访问者类，用于提取代码的语法特征。
    """
    def __init__(self):
        self.imports: Set[str] = set()
        self.function_names: Set[str] = set()
        self.has_try_except: bool = False
        self.loop_count: int = 0
        self.call_names: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.add(node.module.split('.')[0])
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.function_names.add(node.name)
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        self.has_try_except = True
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.loop_count += 1
        self.generic_visit(node)
    
    def visit_While(self, node: ast.While):
        self.loop_count += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 提取函数调用名称，例如 open(), to_csv()
        if isinstance(node.func, ast.Name):
            self.call_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.call_names.add(node.func.attr)
        self.generic_visit(node)

def detect_domain_heuristically(visitor: CodeAnalysisVisitor) -> Optional[DomainType]:
    """
    辅助函数：基于代码特征启发式地检测代码所属领域。
    
    Args:
        visitor (CodeAnalysisVisitor): 包含已解析AST特征的访问者对象。
    
    Returns:
        Optional[DomainType]: 检测到的领域类型，如果无法确定则返回None。
    """
    libs = visitor.imports
    
    # 简单的启发式规则
    if libs & {"requests", "bs4", "selenium", "scrapy", "httpx"}:
        return DomainType.WEB_SCRAPING
    if libs & {"pandas", "numpy", "sklearn", "torch", "matplotlib"}:
        return DomainType.DATA_ANALYSIS
    if libs & {"flask", "fastapi", "django"}:
        return DomainType.API_SERVICE
    
    return None

def check_semantic_completeness(visitor: CodeAnalysisVisitor, context: DomainContext) -> Tuple[bool, List[str]]:
    """
    核心函数：检查代码的语义完整性（是否存在逻辑断层）。
    
    Args:
        visitor (CodeAnalysisVisitor): AST解析结果。
        context (DomainContext): 领域上下文规则。
        
    Returns:
        Tuple[bool, List[str]]: (是否自洽, 缺失的逻辑描述列表)
    """
    missing_nodes = []
    
    # 1. 检查异常处理
    if "exception_handling" in context.required_logic_nodes and not visitor.has_try_except:
        missing_nodes.append("缺少异常处理逻辑: 代码中没有发现 try-except 块，这对于生产级代码是危险的。")
        
    # 2. 检查存储逻辑 (针对爬虫或数据处理)
    # 检测常见的存储函数调用或文件操作
    storage_keywords = {"to_csv", "to_json", "save", "write", "open", "insert", "execute"}
    if "storage_logic" in context.required_logic_nodes:
        if not (visitor.call_names & storage_keywords):
            missing_nodes.append("缺少存储逻辑: 未检测到数据持久化操作 (如 save, write, to_csv)。")
            
    # 3. 检查循环/迭代逻辑
    if "request_loop" in context.required_logic_nodes and visitor.loop_count == 0:
        missing_nodes.append("缺少迭代逻辑: 对于批量任务，似乎缺少循环结构。

    # 4. 检查关键函数模式
    found_patterns = 0
    for pattern in context.required_function_patterns:
        # 简单的模糊匹配，检查定义的函数名是否包含关键词
        if any(pattern.replace("def ", "") in fn for fn in visitor.function_names):
            found_patterns += 1
    
    # 至少要包含一半的推荐函数模式
    if context.required_function_patterns and found_patterns < len(context.required_function_patterns) / 2:
        missing_nodes.append(f"关键步骤缺失: 推荐定义函数 {context.required_function_patterns}，但代码中定义了 {visitor.function_names}")

    is_consistent = len(missing_nodes) == 0
    return is_consistent, missing_nodes

def validate_code_cognitive_consistency(code_str: str, domain: Optional[DomainType] = None) -> Dict[str, Any]:
    """
    主入口函数：验证代码生成结果的认知自洽性。
    
    输入格式:
        code_str (str): 待验证的Python源代码字符串。
        domain (Optional[DomainType]): 指定的领域类型。如果为None，将尝试自动检测。
        
    输出格式:
        Dict[str, Any]: 包含验证结果的字典，结构如下：
        {
            "is_valid": bool,          # 语法是否有效
            "is_consistent": bool,     # 认知逻辑是否自洽
            "domain": str,             # 检测/使用的领域
            "missing_logic": List[str],# 缺失的逻辑描述
            "analysis": Dict[str, Any] # 解析出的代码特征
        }
    """
    result = {
        "is_valid": False,
        "is_consistent": False,
        "domain": "unknown",
        "missing_logic": [],
        "analysis": {}
    }
    
    # 1. 数据清洗与边界检查
    if not code_str or not isinstance(code_str, str):
        logger.error("输入代码为空或类型错误")
        result["missing_logic"] = ["输入代码为空"]
        return result
    
    code_str = code_str.strip()
    
    # 2. 语法验证
    try:
        tree = ast.parse(code_str)
        result["is_valid"] = True
        logger.info("AST语法解析成功。")
    except SyntaxError as e:
        logger.error(f"语法错误: {e}")
        result["missing_logic"] = [f"语法错误: {e}"]
        return result

    # 3. 提取代码特征
    try:
        visitor = CodeAnalysisVisitor()
        visitor.visit(tree)
        result["analysis"] = {
            "imports": list(visitor.imports),
            "functions": list(visitor.function_names),
            "has_exception_handling": visitor.has_try_except
        }
        logger.info(f"代码特征提取完成: {result['analysis']}")
    except Exception as e:
        logger.error(f"AST遍历出错: {e}")
        return result

    # 4. 确定领域上下文
    target_domain = domain
    if target_domain is None:
        target_domain = detect_domain_heuristically(visitor)
        
    if target_domain is None:
        logger.warning("无法确定代码领域，跳过深度自洽性检查。")
        result["is_consistent"] = True # 语法通过即视为基本自洽
        result["domain"] = "unknown"
        return result
        
    result["domain"] = target_domain.value
    context_rules = CONTEXT_RULES.get(target_domain)
    
    if not context_rules:
        logger.warning(f"领域 {target_domain} 缺少定义的上下文规则。")
        return result

    # 5. 认知自洽性检查
    is_consistent, missing = check_semantic_completeness(visitor, context_rules)
    
    result["is_consistent"] = is_consistent
    result["missing_logic"] = missing
    
    return result

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 示例1: 一个逻辑不完备的爬虫代码 (缺少异常处理和存储)
    incomplete_scraper_code = """
import requests
from bs4 import BeautifulSoup

def scrape_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    titles = soup.find_all('h1')
    # 仅仅打印，没有存储，没有异常处理
    for title in titles:
        print(title.text)
    """

    # 示例2: 一个逻辑相对完备的数据处理代码
    complete_analysis_code = """
import pandas as pd
import numpy as np

def process_data(file_path):
    try:
        df = pd.read_csv(file_path)
        # 数据清洗
        df = df.dropna()
        # 逻辑处理
        result = df.groupby('category').sum()
        # 存储
        result.to_json('output.json')
        return result
    except Exception as e:
        print(f"Error processing data: {e}")
    """

    print("--- 测试不完备的爬虫代码 ---")
    res1 = validate_code_cognitive_consistency(incomplete_scraper_code)
    print(json.dumps(res1, indent=2, ensure_ascii=False))

    print("\n--- 测试完备的分析代码 ---")
    res2 = validate_code_cognitive_consistency(complete_analysis_code, DomainType.DATA_ANALYSIS)
    print(json.dumps(res2, indent=2, ensure_ascii=False))