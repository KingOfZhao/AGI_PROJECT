import re
from typing import Dict, List, Optional, Tuple
import networkx as nx

class IntentIRBuilder:
    """
    构建自然语言意图到代码中间表示(IR)的转换器。
    
    该类将自然语言输入解析为中间表示(IR)，通过图结构处理歧义性，
    并将确定的逻辑结构转换为可执行的代码。
    
    Attributes:
        graph (nx.DiGraph): 存储IR的有向图结构
        node_counter (int): 用于生成唯一节点ID的计数器
        op_mapping (Dict[str, str]): 自然语言操作符到代码操作符的映射
    """
    
    def __init__(self):
        """初始化IR构建器"""
        self.graph = nx.DiGraph()
        self.node_counter = 0
        self.op_mapping = {
            "加": "+", "和": "+", "加上": "+",
            "减": "-", "减去": "-",
            "乘": "*", "乘以": "*",
            "除": "/", "除以": "/",
            "等于": "==", "是": "==",
            "大于": ">", "小于": "<",
            "并且": "and", "并且": "and",
            "或者": "or"
        }
    
    def _create_node(self, node_type: str, value: str, **attrs) -> int:
        """
        创建图节点
        
        Args:
            node_type: 节点类型 ('operation', 'operand', 'control')
            value: 节点值
            **attrs: 其他节点属性
            
        Returns:
            int: 创建的节点ID
        """
        node_id = self.node_counter
        self.node_counter += 1
        self.graph.add_node(node_id, type=node_type, value=value, **attrs)
        return node_id
    
    def _parse_expression(self, tokens: List[str], pos: int) -> Tuple[int, int]:
        """
        递归解析表达式并构建子图
        
        Args:
            tokens: 分词后的输入列表
            pos: 当前解析位置
            
        Returns:
            Tuple[int, int]: (根节点ID, 新的解析位置)
            
        Raises:
            ValueError: 语法错误或无效操作符
        """
        # 处理操作数
        if tokens[pos] in self.op_mapping:
            raise ValueError(f"操作符 '{tokens[pos]}' 不能作为操作数")
            
        # 处理字面量
        if tokens[pos].replace('.', '', 1).isdigit():
            node_id = self._create_node('operand', tokens[pos], literal=float(tokens[pos]))
            return node_id, pos + 1
            
        # 处理变量
        if tokens[pos].isalpha():
            node_id = self._create_node('operand', tokens[pos], variable=tokens[pos])
            return node_id, pos + 1
            
        # 处理括号表达式
        if tokens[pos] == '(':
            pos += 1
            left_node, pos = self._parse_expression(tokens, pos)
            
            # 获取操作符
            if pos >= len(tokens) or tokens[pos] not in self.op_mapping:
                raise ValueError(f"缺少操作符在位置 {pos}")
            op_node = self._create_node('operation', tokens[pos], op=self.op_mapping[tokens[pos]])
            pos += 1
            
            # 获取右操作数
            right_node, pos = self._parse_expression(tokens, pos)
            
            # 添加依赖关系
            self.graph.add_edge(op_node, left_node)
            self.graph.add_edge(op_node, right_node)
            
            if pos >= len(tokens) or tokens[pos] != ')':
                raise ValueError(f"缺少闭合括号在位置 {pos}")
            return op_node, pos + 1
            
        raise ValueError(f"无效的令牌 '{tokens[pos]}' 在位置 {pos}")
    
    def build_ir(self, input_text: str) -> nx.DiGraph:
        """
        构建中间表示(IR)图
        
        Args:
            input_text: 自然语言输入字符串
            
        Returns:
            nx.DiGraph: 构建的IR图
            
        Raises:
            ValueError: 输入解析错误
        """
        # 预处理输入
        tokens = re.findall(r"(\d+\.?\d*|\w+|[+\-*/()=<>])", input_text)
        if not tokens:
            raise ValueError("输入不能为空")
            
        # 重置图状态
        self.graph = nx.DiGraph()
        self.node_counter = 0
        
        # 解析表达式
        root_node, pos = self._parse_expression(tokens, 0)
        
        # 验证完整解析
        if pos != len(tokens):
            raise ValueError(f"未完全解析输入，剩余令牌: {tokens[pos:]}")
            
        return self.graph
    
    def generate_code(self, graph: nx.DiGraph) -> str:
        """
        从IR图生成Python代码
        
        Args:
            graph: IR有向图
            
        Returns:
            str: 生成的Python代码字符串
        """
        # 拓扑排序确保依赖关系正确
        try:
            sorted_nodes = list(nx.topological_sort(graph))
        except nx.NetworkXError:
            raise ValueError("IR图包含循环依赖")
            
        code_lines = []
        var_counter = 0
        var_map = {}
        
        for node in sorted_nodes:
            node_data = graph.nodes[node]
            
            if node_data['type'] == 'operand':
                if 'literal' in node_data:
                    var_name = f"var{var_counter}"
                    var_counter += 1
                    var_map[node] = var_name
                    code_lines.append(f"{var_name} = {node_data['literal']}")
                elif 'variable' in node_data:
                    var_map[node] = node_data['variable']
                    
            elif node_data['type'] == 'operation':
                # 获取操作数变量名
                predecessors = list(graph.predecessors(node))
                if len(predecessors) != 2:
                    raise ValueError(f"操作节点 {node} 需要两个操作数")
                    
                left_var = var_map.get(predecessors[0])
                right_var = var_map.get(predecessors[1])
                if not left_var or not right_var:
                    raise ValueError(f"操作数变量未定义在节点 {node}")
                    
                # 生成赋值语句
                var_name = f"var{var_counter}"
                var_counter += 1
                var_map[node] = var_name
                op = node_data['op']
                code_lines.append(f"{var_name} = {left_var} {op} {right_var}")
                
        return "\n".join(code_lines)
    
    def process_intent(self, intent: str) -> str:
        """
        处理自然语言意图并生成代码
        
        Args:
            intent: 自然语言输入字符串
            
        Returns:
            str: 生成的Python代码
            
        Raises:
            ValueError: 处理过程中出现的错误
        """
        try:
            ir_graph = self.build_ir(intent)
            return self.generate_code(ir_graph)
        except Exception as e:
            raise ValueError(f"意图处理失败: {str(e)}")


# 示例用法
if __name__ == "__main__":
    builder = IntentIRBuilder()
    
    # 测试用例1: 简单算术表达式
    intent1 = "计算 (2 加 3) 乘以 4"
    try:
        code1 = builder.process_intent(intent1)
        print(f"意图: {intent1}")
        print(f"生成的代码:\n{code1}\n")
    except ValueError as e:
        print(f"错误: {e}")
    
    # 测试用例2: 嵌套表达式
    intent2 = "计算 (5 除以 (2 加 3))"
    try:
        code2 = builder.process_intent(intent2)
        print(f"意图: {intent2}")
        print(f"生成的代码:\n{code2}\n")
    except ValueError as e:
        print(f"错误: {e}")
    
    # 测试用例3: 错误处理
    intent3 = "计算 2 加 3 乘以"  # 缺少操作数
    try:
        code3 = builder.process_intent(intent3)
        print(f"意图: {intent3}")
        print(f"生成的代码:\n{code3}\n")
    except ValueError as e:
        print(f"错误: {e}")