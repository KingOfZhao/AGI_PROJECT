"""
模块名称: ast_code_generator
描述: 这是一个基于抽象语法树（AST）的代码生成模块，旨在将结构化的意图数据转换为
      符合Python语法规范的可执行代码字符串。
      
      该模块通过构建AST节点树并将其反解析为源代码，确保了生成代码的语法正确性，
      避免了手动拼接字符串带来的注入风险和语法错误。

核心功能:
    1. 支持变量赋值、函数定义、基础运算等Python结构的生成。
    2. 提供基于Schema的结构化意图验证。
    3. 包含完善的日志记录和异常处理机制。

作者: AGI System
版本: 1.0.0
"""

import ast
import logging
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 数据结构定义 ---

@dataclass
class FunctionParameter:
    """函数参数的数据结构"""
    name: str
    type_hint: Optional[str] = None
    default: Optional[Any] = None

@dataclass
class StructuredIntent:
    """
    结构化意图数据结构
    用于指导AST代码生成的输入参数。
    
    Attributes:
        task_type (str): 任务类型，如 'assign', 'func_def', 'return'
        identifier (str): 标识符名称（如变量名或函数名）
        value (Any): 赋值的值或表达式组件
        parameters (List[Dict]): 函数参数列表
        body (List[StructedIntent]): 函数体或代码块内部的意图列表
    """
    task_type: str
    identifier: Optional[str] = None
    value: Optional[Any] = None
    parameters: Optional[List[Dict]] = None
    body: Optional[List['StructuredIntent']] = None

# --- 辅助函数 ---

def validate_intent_schema(intent_data: Dict[str, Any]) -> StructuredIntent:
    """
    验证输入的意图数据是否符合生成AST所需的基本Schema。
    
    Args:
        intent_data (Dict[str, Any]): 原始输入的JSON数据/字典。
        
    Returns:
        StructuredIntent: 验证并转换后的结构化意图对象。
        
    Raises:
        ValueError: 如果缺少必要的字段（如 task_type）。
    """
    if not isinstance(intent_data, dict):
        logger.error("输入意图必须是一个字典。")
        raise ValueError("Intent data must be a dictionary.")
    
    if 'task_type' not in intent_data:
        logger.error("缺少关键键: 'task_type'")
        raise ValueError("Missing required key: 'task_type'")
    
    # 简单的边界检查
    task_type = intent_data['task_type']
    if not isinstance(task_type, str) or not task_type.strip():
        raise ValueError("task_type must be a non-empty string.")
        
    logger.debug(f"验证通过，任务类型: {task_type}")
    
    # 这里为了简化，直接解包字典，实际生产中应递归验证嵌套结构
    return StructuredIntent(
        task_type=task_type,
        identifier=intent_data.get('identifier'),
        value=intent_data.get('value'),
        parameters=intent_data.get('parameters', []),
        body=intent_data.get('body', [])
    )

def parse_value_to_ast_node(value: Any) -> ast.AST:
    """
    将Python原生值转换为AST字面量节点。
    
    Args:
        value (Any): Python原生值 (str, int, float, bool, None)。
        
    Returns:
        ast.AST: 对应的AST节点 (Constant, Name, List 等)。
    """
    if value is None or isinstance(value, (int, float, str, bool)):
        return ast.Constant(value=value)
    elif isinstance(value, list):
        return ast.List(elts=[parse_value_to_ast_node(v) for v in value], ctx=ast.Load())
    elif isinstance(value, dict):
        # 简单处理：生成键值对列表，实际AST中字典是 Dict(keys, values)
        keys = [ast.Constant(value=k) for k in value.keys()]
        vals = [parse_value_to_ast_node(v) for v in value.values()]
        return ast.Dict(keys=keys, values=vals)
    else:
        # 如果是字符串形式的变量名（简单模拟）
        if isinstance(value, str) and value.isidentifier():
            return ast.Name(id=value, ctx=ast.Load())
        return ast.Constant(value=str(value))

# --- 核心生成函数 ---

def build_ast_from_intent(intent: StructuredIntent) -> List[ast.stmt]:
    """
    核心函数1: 递归构建AST节点树。
    
    根据结构化意图，生成对应的AST语句节点列表。
    目前支持: 变量赋值, 函数定义, 返回语句, 表达式求值。
    
    Args:
        intent (StructuredIntent): 验证后的意图对象。
        
    Returns:
        List[ast.stmt]: AST语句节点列表。
        
    Raises:
        NotImplementedError: 当遇到不支持的task_type时抛出。
    """
    nodes = []
    
    try:
        if intent.task_type == "variable_assignment":
            if not intent.identifier:
                raise ValueError("Variable assignment requires an 'identifier'.")
            
            # 构建赋值目标
            target = ast.Name(id=intent.identifier, ctx=ast.Store())
            # 构建赋值源
            value_node = parse_value_to_ast_node(intent.value)
            
            assign_node = ast.Assign(targets=[target], value=value_node)
            nodes.append(assign_node)
            logger.info(f"生成变量赋值节点: {intent.identifier}")
            
        elif intent.task_type == "function_definition":
            if not intent.identifier:
                raise ValueError("Function definition requires an 'identifier'.")
            
            # 处理参数
            args_list = []
            defaults = []
            for param in intent.parameters:
                # 假设param是字典 {'name': 'x', 'default': None}
                arg_name = param.get('name')
                arg_default = param.get('default')
                
                args_list.append(ast.arg(arg=arg_name, annotation=None))
                if arg_default is not None:
                    defaults.append(parse_value_to_ast_node(arg_default))
                elif defaults:
                    # 如果中间有参数没有默认值但后面有，Python语法错误，这里简化处理
                    pass
                    
            args = ast.arguments(
                posonlyargs=[], args=args_list, kwonlyargs=[], 
                kw_defaults=[], defaults=defaults
            )
            
            # 递归处理函数体
            body_nodes = []
            if intent.body:
                for sub_intent_data in intent.body:
                    # 递归调用
                    sub_intent = StructuredIntent(**sub_intent_data)
                    body_nodes.extend(build_ast_from_intent(sub_intent))
            
            if not body_nodes:
                body_nodes.append(ast.Pass()) # 空函数体
            
            func_def = ast.FunctionDef(
                name=intent.identifier,
                args=args,
                body=body_nodes,
                decorator_list=[],
                returns=None
            )
            nodes.append(func_def)
            logger.info(f"生成函数定义节点: {intent.identifier}")
            
        elif intent.task_type == "return_statement":
            value_node = parse_value_to_ast_node(intent.value)
            ret_node = ast.Return(value=value_node)
            nodes.append(ret_node)
            
        else:
            logger.warning(f"不支持的意图类型: {intent.task_type}")
            raise NotImplementedError(f"Task type '{intent.task_type}' is not supported yet.")
            
    except Exception as e:
        logger.error(f"构建AST时发生错误: {str(e)}")
        raise

    return nodes

def generate_code_from_ast(nodes: List[ast.stmt], fix_missing_locations: bool = True) -> str:
    """
    核心函数2: 将AST节点列表转换为Python源代码字符串。
    
    Args:
        nodes (List[ast.stmt]): AST节点列表。
        fix_missing_locations (bool): 是否自动修复节点行号信息。
        
    Returns:
        str: 格式化后的Python源代码。
    """
    if not nodes:
        return ""
    
    try:
        # 创建一个模块节点来包裹这些语句
        module = ast.Module(body=nodes, type_ignores=[])
        
        if fix_missing_locations:
            # 必须修复位置信息，否则 ast.unparse 可能会失败
            ast.fix_missing_locations(module)
            
        # 使用Python 3.9+ 的 ast.unparse
        source_code = ast.unparse(module)
        logger.info("代码生成成功。")
        return source_code
        
    except AttributeError:
        logger.error("当前Python版本不支持 ast.unparse (需要 3.9+)。")
        return "# Error: Python version too low for ast.unparse"
    except Exception as e:
        logger.error(f"AST反解析失败: {str(e)}")
        raise

# --- 主入口与示例 ---

def generate_code_module(intent_json: Dict[str, Any]) -> str:
    """
    完整的生成流程：验证 -> 构建AST -> 生成代码。
    """
    try:
        # 1. 数据验证
        validated_intent = validate_intent_schema(intent_json)
        
        # 2. 构建AST
        ast_nodes = build_ast_from_intent(validated_intent)
        
        # 3. 生成代码
        return generate_code_from_ast(ast_nodes)
    except Exception as e:
        return f"# Code Generation Failed: {str(e)}"

if __name__ == "__main__":
    # 示例数据：生成一个计算两数之和并返回结果的函数
    sample_intent = {
        "task_type": "function_definition",
        "identifier": "calculate_sum",
        "parameters": [
            {"name": "a", "default": None},
            {"name": "b", "default": 0}
        ],
        "body": [
            {
                "task_type": "variable_assignment",
                "identifier": "result",
                "value": "a + b"  # 注意：这里作为字符串字面量，需要更复杂的解析器才能变成表达式
                                 # 为演示目的，这里会生成 result = "a + b"
                                 # 若要生成表达式，parse_value_to_ast_node 需要扩展识别字符串中的表达式
                                 # 此处演示字面量生成逻辑
            },
            {
                "task_type": "return_statement",
                "value": "result"
            }
        ]
    }
    
    # 为了演示更真实的AST能力，我们手动构建一个表达式赋值的意图模拟
    # (假设我们已经解析过表达式 "a + b" 为 BinOp 节点)
    
    print("--- 生成结果 1 (基于JSON输入) ---")
    code1 = generate_code_module(sample_intent)
    print(code1)
    
    print("\n--- 生成结果 2 (直接AST构建演示) ---")
    # 演示手动构建AST节点来生成更复杂的代码 (a + b * 10)
    expr_node = ast.BinOp(
        left=ast.Name(id='a', ctx=ast.Load()),
        op=ast.Add(),
        right=ast.BinOp(
            left=ast.Name(id='b', ctx=ast.Load()),
            op=ast.Mult(),
            right=ast.Constant(value=10)
        )
    )
    
    assign_node = ast.Assign(
        targets=[ast.Name(id='complex_result', ctx=ast.Store())],
        value=expr_node
    )
    
    code2 = generate_code_from_ast([assign_node])
    print(code2)