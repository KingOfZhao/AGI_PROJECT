"""
模块名称: context_aware_intent_resolver
描述: 实现基于代码上下文感知的意图补全机制。

本模块旨在解决自然语言指令中模糊指代（如“优化它”、“重命名这个”）的消解问题。
通过构建抽象语法树(AST)和模拟项目依赖图，结合当前光标位置，
系统推断出模糊指代词（如'它'）对应的具体代码节点（函数、类或变量），
并将模糊意图锚定为结构化的代码节点ID。

主要组件:
    - CodeGraph: 模拟代码的图结构存储。
    - ContextAwareResolver: 核心解析类，包含AST分析和意图锚定逻辑。

依赖:
    - ast (标准库)
    - typing (标准库)
    - logging (标准库)
    - dataclasses (标准库)

作者: AGI System
版本: 1.0.0
"""

import ast
import logging
import textwrap
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeType(Enum):
    """代码节点类型枚举"""
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    MODULE = "module"

@dataclass
class CodeNode:
    """
    代码节点数据结构。
    
    属性:
        id: 节点的唯一标识符 (e.g., 'module.src.utils.calculate_hash')
        name: 节点名称
        type: 节点类型
        start_line: 起始行号
        end_line: 结束行号
        dependencies: 该节点依赖的其他节点ID列表
    """
    id: str
    name: str
    type: NodeType
    start_line: int
    end_line: int
    dependencies: List[str] = field(default_factory=list)

@dataclass
class CursorContext:
    """
    编辑器光标上下文信息。
    
    属性:
        file_path: 当前文件路径
        line: 当前行号 (1-based)
        column: 当前列号
        snippet: 光标周围的代码片段 (可选)
    """
    file_path: str
    line: int
    column: int
    snippet: Optional[str] = None

class ContextAwareResolver:
    """
    上下文感知解析器。
    
    负责解析代码，构建AST，并结合光标位置推断用户意图所指的具体代码实体。
    """
    
    def __init__(self):
        self._nodes: Dict[str, CodeNode] = {}
        self._ast_cache: Dict[str, ast.AST] = {}
        logger.info("ContextAwareResolver initialized.")

    def _validate_input_code(self, code: str) -> bool:
        """验证输入代码是否有效"""
        if not code or not isinstance(code, str):
            logger.warning("Invalid input: Code is empty or not a string.")
            return False
        return True

    def parse_code_to_graph(self, source_code: str, file_path: str) -> List[CodeNode]:
        """
        核心函数1: 解析源代码并构建内部代码图。
        
        分析Python源代码，提取函数、类和顶层变量定义，
        并将其存储为图节点。这是后续上下文推断的基础。
        
        参数:
            source_code: Python源代码字符串
            file_path: 虚拟文件路径，用于生成唯一ID
            
        返回:
            提取到的CodeNode列表
            
        抛出:
            ValueError: 如果代码格式错误无法解析
        """
        if not self._validate_input_code(source_code):
            return []

        try:
            # 清理缩进并解析AST
            clean_code = textwrap.dedent(source_code)
            tree = ast.parse(clean_code)
            self._ast_cache[file_path] = tree
            
            extracted_nodes = []
            module_id = file_path.replace("/", ".")
            
            # 遍历AST
            for node in ast.walk(tree):
                node_id = ""
                code_node = None
                
                if isinstance(node, ast.FunctionDef):
                    node_id = f"{module_id}.{node.name}"
                    code_node = CodeNode(
                        id=node_id,
                        name=node.name,
                        type=NodeType.FUNCTION,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno
                    )
                elif isinstance(node, ast.ClassDef):
                    node_id = f"{module_id}.{node.name}"
                    code_node = CodeNode(
                        id=node_id,
                        name=node.name,
                        type=NodeType.CLASS,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno
                    )
                # 简单的变量提取 (仅限顶层赋值)
                elif isinstance(node, ast.Assign) and isinstance(node.parent, ast.Module): # type: ignore
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            node_id = f"{module_id}.var_{target.id}"
                            code_node = CodeNode(
                                id=node_id,
                                name=target.id,
                                type=NodeType.VARIABLE,
                                start_line=node.lineno,
                                end_line=node.lineno
                            )
                
                if code_node:
                    self._nodes[node_id] = code_node
                    extracted_nodes.append(code_node)
                    logger.debug(f"Parsed node: {code_node.id} ({code_node.type.value})")

            logger.info(f"Successfully parsed {len(extracted_nodes)} nodes from {file_path}")
            return extracted_nodes
            
        except SyntaxError as e:
            logger.error(f"SyntaxError parsing code: {e}")
            raise ValueError(f"Code parsing failed: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error during AST parsing: {e}")
            raise

    def resolve_fuzzy_intent(self, context: CursorContext) -> Optional[CodeNode]:
        """
        核心函数2: 解析模糊意图并锚定代码节点。
        
        根据光标位置，查找包含该位置的最近作用域内的代码节点。
        优先级: 函数 > 类 > 变量。
        
        参数:
            context: 包含文件路径、行列号的上下文对象
            
        返回:
            最匹配的CodeNode，如果未找到则返回None
        """
        logger.info(f"Resolving intent for cursor at {context.file_path}:{context.line}")
        
        # 简单的依赖图/AST查找逻辑
        # 在真实场景中，这里会查询图数据库或遍历AST
        candidates = [
            node for node in self._nodes.values() 
            if node.id.startswith(context.file_path.replace("/", ".")) 
            and node.start_line <= context.line <= node.end_line
        ]

        if not candidates:
            logger.warning("No context node found at cursor position.")
            return None

        # 排序逻辑：范围越小越精确（内层函数优先于外层函数），类型优先级
        # 这里使用简单的启发式：优先返回函数，其次类，最后变量
        def sort_key(n: CodeNode):
            type_priority = {
                NodeType.FUNCTION: 0,
                NodeType.CLASS: 1,
                NodeType.VARIABLE: 2
            }.get(n.type, 3)
            
            # 范围大小 (end - start)，越小越可能是由当前上下文直接指向的
            scope_size = n.end_line - n.start_line
            return (type_priority, scope_size)

        candidates.sort(key=sort_key)
        
        resolved_node = candidates[0]
        logger.info(f"Intent resolved to: {resolved_node.id} (Type: {resolved_node.type.value})")
        return resolved_node

    def get_node_dependencies(self, node_id: str) -> List[str]:
        """
        辅助函数: 获取特定节点的依赖项。
        
        用于验证上下文感知是否需要考虑跨文件的引用。
        
        参数:
            node_id: 代码节点ID
            
        返回:
            依赖节点ID列表
        """
        if node_id in self._nodes:
            return self._nodes[node_id].dependencies
        logger.warning(f"Node {node_id} not found in graph.")
        return []

# 为AST节点添加parent属性（辅助AST遍历）
def _add_parent_nodes(tree: ast.AST):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node # type: ignore

# ================= 使用示例 =================
if __name__ == "__main__":
    # 模拟用户代码
    sample_code = """
class DataProcessor:
    def __init__(self, source):
        self.source = source

    def clean_data(self):
        # 光标假设在这里，用户说"优化它"
        data = self.source.read()
        return data.strip()

def helper_function():
    pass
"""

    # 1. 初始化解析器
    resolver = ContextAwareResolver()
    
    try:
        # 2. 解析代码构建上下文图
        # 假设光标在 clean_data 函数内部，例如第8行
        file_name = "project/utils/processor.py"
        resolver.parse_code_to_graph(sample_code, file_name)
        
        # 预处理AST以支持父节点遍历（用于更复杂的推断，此处演示）
        if file_name in resolver._ast_cache:
            _add_parent_nodes(resolver._ast_cache[file_name])

        # 3. 构建光标上下文
        # 假设用户把光标放在第9行（data.strip()那一行）
        cursor_ctx = CursorContext(
            file_path=file_name,
            line=9,
            column=10
        )
        
        # 4. 执行意图解析
        target_node = resolver.resolve_fuzzy_intent(cursor_ctx)
        
        if target_node:
            print(f"\n--- 解析结果 ---")
            print(f"用户意图 '它' 被锚定为:")
            print(f"  节点ID: {target_node.id}")
            print(f"  名称: {target_node.name}")
            print(f"  类型: {target_node.type.value}")
            print(f"  行范围: {target_node.start_line}-{target_node.end_line}")
            print(f"----------------")
        else:
            print("无法解析意图。")

    except Exception as e:
        logger.error(f"Demo execution failed: {e}")