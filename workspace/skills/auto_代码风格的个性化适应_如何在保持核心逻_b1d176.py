"""
模块: auto_代码风格的个性化适应_如何在保持核心逻_b1d176
描述: 本模块提供了基于AST（抽象语法树）的代码风格迁移功能。它允许在保持代码核心逻辑
      （控制流、数据操作）不变的前提下，根据用户定义的配置规则（如命名风格、类结构等）
      对代码的"表层"（语法结构、标识符名称）进行重写。
作者: AGI System
版本: 1.0.0
"""

import ast
import logging
import re
import inflection
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义类型别名以增强可读性
AstNode = Union[ast.AST, ast.Expr, ast.stmt, ast.Name]

@dataclass
class StyleConfig:
    """
    风格配置数据类，用于定义代码重写的规则。
    
    Attributes:
        naming_convention (str): 变量命名风格，可选 'snake_case', 'camelCase', 'PascalCase'。
        use_classes (bool): 是否将孤立函数封装为类的静态方法。
        comment_density (str): 注释密度，当前版本主要用于标记，实际生成需LLM辅助。
    """
    naming_convention: str = 'snake_case'
    use_classes: bool = False
    comment_density: str = 'normal'

    def __post_init__(self):
        """数据验证"""
        if self.naming_convention not in ['snake_case', 'camelCase', 'PascalCase']:
            raise ValueError(f"不支持的命名风格: {self.naming_convention}")
        if self.comment_density not in ['sparse', 'normal', 'dense']:
            raise ValueError(f"不支持的注释密度: {self.comment_density}")


class StyleTransformer(ast.NodeTransformer):
    """
    AST访问者类，用于遍历和修改Python抽象语法树以适应特定风格。
    
    继承自 ast.NodeTransformer，实现具体的转换逻辑。
    """

    def __init__(self, config: StyleConfig):
        """
        初始化转换器。
        
        Args:
            config (StyleConfig): 风格配置对象。
        """
        self.config = config
        self._scope_stack: List[Dict[str, str]] = [{}]  # 用于处理变量作用域映射
        super().__init__()

    def _convert_name(self, name: str) -> str:
        """
        核心辅助函数：根据配置转换标识符名称。
        
        Args:
            name (str): 原始变量名或函数名。
            
        Returns:
            str: 转换后的名称。
        """
        try:
            # 假设输入可能是各种格式，先统一转为蛇形命名作为中间格式（简化的启发式处理）
            # 实际生产环境中需要更复杂的源风格检测
            base_name = name
            
            if self.config.naming_convention == 'snake_case':
                return inflection.underscore(base_name)
            elif self.config.naming_convention == 'camelCase':
                # 转为驼峰，首字母小写
                camel = inflection.camelize(base_name, False)
                return camel
            elif self.config.naming_convention == 'PascalCase':
                # 转为帕斯卡，首字母大写
                return inflection.camelize(base_name)
            return name
        except Exception as e:
            logger.warning(f"名称转换失败 '{name}': {e}")
            return name

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        """
        访问函数定义节点，重命名函数及其参数。
        """
        logger.debug(f"正在处理函数: {node.name}")
        
        # 保存当前作用域的映射
        old_scope = self._scope_stack[-1]
        new_scope = {}
        
        # 转换函数名
        node.name = self._convert_name(node.name)
        
        # 转换参数名
        for arg in node.args.args:
            original_name = arg.arg
            new_name = self._convert_name(original_name)
            new_scope[original_name] = new_name
            arg.arg = new_name
            
        # 处理函数体
        self._scope_stack.append(new_scope)
        self.generic_visit(node)
        self._scope_stack.pop()
        
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        """
        访问变量名称节点，根据作用域映射进行替换。
        注意：这会对所有变量生效，简单的逻辑重写可能会改变类名或库引用，
        实际AGI系统中需要过滤上下文（如排除import的模块名）。
        """
        # 简化演示：如果在作用域映射中找到了该变量（即它是参数或局部变量），则替换
        # 否则保持原样（假设是全局变量或导入的模块）
        for scope in reversed(self._scope_stack):
            if node.id in scope:
                node.id = scope[node.id]
                break
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        """
        演示：如果需要根据注释密度调整代码（AST层面主要是处理Docstring）。
        这里仅作为结构展示，实际上移除Docstring只需将node.value置为None。
        """
        # 真实的注释密度处理通常需要LLM在生成AST之前或之后介入，
        # 因为AST不包含行内注释，只包含Docstring。
        return node


def refactor_code_style(source_code: str, config: StyleConfig) -> str:
    """
    核心功能函数：将源代码字符串根据风格配置进行重构。
    
    Args:
        source_code (str): 输入的Python源代码字符串。
        config (StyleConfig): 风格配置对象。
        
    Returns:
        str: 重构后的Python源代码字符串。
        
    Raises:
        SyntaxError: 如果输入的源代码有语法错误。
        ValueError: 如果输入数据为空。
    """
    if not source_code or not source_code.strip():
        logger.error("输入代码为空")
        raise ValueError("源代码不能为空")

    logger.info("开始解析AST...")
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        logger.error(f"源代码语法错误: {e}")
        raise

    logger.info(f"应用风格转换: 命名风格={config.naming_convention}, 封装类={config.use_classes}")
    
    # 应用转换
    transformer = StyleTransformer(config)
    new_tree = transformer.visit(tree)
    
    # 修复AST中的位置信息（可选，用于确保某些生成工具正常工作）
    ast.fix_missing_locations(new_tree)
    
    # 将AST还原为代码
    # 注意：ast.unparse 是 Python 3.9+ 的功能。
    # 在旧版本中需要使用 astor 库或类似的第三方库。
    try:
        new_code = ast.unparse(new_tree)
    except AttributeError:
        logger.warning("当前Python版本不支持 ast.unparse (需要3.9+)，返回原始代码作为回退。")
        # 真实环境中应引入 astor.to_source(new_tree)
        new_code = source_code

    # 处理类封装逻辑（简单的后处理示例）
    if config.use_classes:
        # 这是一个简化的逻辑：如果代码只有顶层函数，且没有类，则包装在一个类中
        # 真实逻辑需要检查 new_tree 的顶层节点类型
        has_class = any(isinstance(node, ast.ClassDef) for node in new_tree.body)
        has_func = any(isinstance(node, ast.FunctionDef) for node in new_tree.body)
        
        if has_func and not has_class:
            logger.info("检测到顶层函数，正在封装为类...")
            # 获取缩进并包装代码
            # 注意：这里使用简单的文本处理，AST处理会非常复杂
            indented_code = "\n".join(["    " + line for line in new_code.splitlines()])
            new_code = f"class AutoGeneratedWrapper:\n{indented_code}"

    logger.info("代码重构完成。")
    return new_code


def validate_code_safety(code: str) -> bool:
    """
    辅助函数：验证代码的安全性，防止注入危险操作（基础检查）。
    
    Args:
        code (str): 源代码。
        
    Returns:
        bool: 如果代码包含潜在危险关键字则返回False，否则True。
    """
    forbidden_patterns = [
        r"import\s+os", 
        r"import\s+subprocess", 
        r"import\s+sys",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__"
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, code):
            logger.warning(f"检测到潜在不安全代码模式: {pattern}")
            return False
    return True


if __name__ == "__main__":
    # 示例输入数据
    sample_code = """
def Calculate_Sum(FirstNumber, SecondNumber):
    # This function calculates sum
    result = FirstNumber + SecondNumber
    return result

def Print_Report(UserName):
    print(f"Report for {UserName}")
    return True
"""

    print("--- 原始代码 ---")
    print(sample_code)

    # 1. 定义风格：转换为 snake_case (变量) + camelCase (函数)
    # 注意：当前的实现为了演示，统一了转换逻辑。
    # 我们设置为 camelCase
    style_cfg = StyleConfig(naming_convention='camelCase', use_classes=False)

    if validate_code_safety(sample_code):
        try:
            refactored_code = refactor_code_style(sample_code, style_cfg)
            print("\n--- 重构后代码 (camelCase) ---")
            print(refactored_code)
        except Exception as e:
            logger.error(f"重构过程中发生错误: {e}")
    else:
        print("代码未通过安全检查。")

    # 2. 定义风格：封装为类
    style_cfg_wrapped = StyleConfig(naming_convention='snake_case', use_classes=True)
    if validate_code_safety(sample_code):
        try:
            refactored_wrapped = refactor_code_style(sample_code, style_cfg_wrapped)
            print("\n--- 重构后代码 (Wrapped in Class) ---")
            print(refactored_wrapped)
        except Exception as e:
            logger.error(f"重构过程中发生错误: {e}")