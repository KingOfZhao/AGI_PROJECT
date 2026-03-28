"""
结构化语境图谱模块

本模块实现了将代码的变量引用图升级为'认知语境图谱'的功能。通过向量空间算法
计算当前上下文与历史节点的'结构相似度'，实现代码逻辑的'隐喻级'复用。

核心功能:
1. 将代码解析为结构化语境节点
2. 构建向量化的认知语境图谱
3. 通过结构映射实现逻辑模式匹配

作者: AGI System
版本: 1.0.0
创建时间: 2023-11-15
"""

import ast
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum, auto
import hashlib
import json
from collections import defaultdict

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeType(Enum):
    """定义节点类型枚举"""
    VARIABLE = auto()
    FUNCTION = auto()
    CLASS = auto()
    CONTROL_FLOW = auto()
    EXPRESSION = auto()
    UNKNOWN = auto()


@dataclass
class ContextNode:
    """
    语境节点数据结构
    
    属性:
        node_id: 节点唯一标识符
        node_type: 节点类型
        name: 节点名称
        vector: 节点向量表示
        connections: 连接的节点ID列表
        metadata: 元数据字典
        source_code: 源代码片段
    """
    node_id: str
    node_type: NodeType
    name: str
    vector: np.ndarray = field(default_factory=lambda: np.zeros(128))
    connections: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_code: str = ""


class CodeParser:
    """
    代码解析器，将源代码解析为结构化语境节点
    """
    
    @staticmethod
    def parse_code(source_code: str) -> List[ContextNode]:
        """
        解析源代码为语境节点列表
        
        参数:
            source_code: 要解析的Python源代码字符串
            
        返回:
            语境节点列表
            
        异常:
            SyntaxError: 如果源代码有语法错误
        """
        if not source_code or not isinstance(source_code, str):
            logger.error("无效的源代码输入")
            return []
            
        try:
            tree = ast.parse(source_code)
            nodes = []
            
            # 遍历AST提取节点
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    node_id = hashlib.md5(
                        f"func_{node.name}_{node.lineno}".encode()
                    ).hexdigest()
                    
                    # 创建函数节点
                    func_node = ContextNode(
                        node_id=node_id,
                        node_type=NodeType.FUNCTION,
                        name=node.name,
                        source_code=ast.unparse(node) if hasattr(ast, 'unparse') else "",
                        metadata={
                            'args': [arg.arg for arg in node.args.args],
                            'lineno': node.lineno
                        }
                    )
                    nodes.append(func_node)
                    
                elif isinstance(node, ast.ClassDef):
                    node_id = hashlib.md5(
                        f"class_{node.name}_{node.lineno}".encode()
                    ).hexdigest()
                    
                    # 创建类节点
                    class_node = ContextNode(
                        node_id=node_id,
                        node_type=NodeType.CLASS,
                        name=node.name,
                        source_code=ast.unparse(node) if hasattr(ast, 'unparse') else "",
                        metadata={
                            'bases': [base.id for base in node.bases if isinstance(base, ast.Name)],
                            'lineno': node.lineno
                        }
                    )
                    nodes.append(class_node)
                    
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    node_id = hashlib.md5(
                        f"var_{node.id}_{node.lineno}".encode()
                    ).hexdigest()
                    
                    # 创建变量节点
                    var_node = ContextNode(
                        node_id=node_id,
                        node_type=NodeType.VARIABLE,
                        name=node.id,
                        metadata={'lineno': node.lineno}
                    )
                    nodes.append(var_node)
            
            logger.info(f"成功解析代码，生成 {len(nodes)} 个语境节点")
            return nodes
            
        except SyntaxError as e:
            logger.error(f"语法错误: {e}")
            raise
        except Exception as e:
            logger.error(f"解析代码时发生意外错误: {e}")
            return []


class VectorEncoder:
    """
    向量编码器，将语境节点转换为向量表示
    """
    
    def __init__(self, vector_dim: int = 128):
        """
        初始化向量编码器
        
        参数:
            vector_dim: 向量维度，默认为128
        """
        if vector_dim <= 0 or not isinstance(vector_dim, int):
            logger.warning(f"无效的向量维度 {vector_dim}，使用默认值128")
            vector_dim = 128
            
        self.vector_dim = vector_dim
        # 模拟的词向量字典（实际应用中应从模型加载）
        self._word_vectors: Dict[str, np.ndarray] = {}
        
    def encode_node(self, node: ContextNode) -> np.ndarray:
        """
        将语境节点编码为向量
        
        参数:
            node: 语境节点
            
        返回:
            节点的向量表示
        """
        # 简单的哈希向量编码（实际应用中应使用预训练模型）
        hash_val = int(hashlib.md5(node.name.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))
        vector = np.random.randn(self.vector_dim)
        
        # 根据节点类型调整向量
        type_factor = {
            NodeType.FUNCTION: 1.2,
            NodeType.CLASS: 1.1,
            NodeType.VARIABLE: 1.0,
            NodeType.CONTROL_FLOW: 0.9,
            NodeType.EXPRESSION: 0.8,
            NodeType.UNKNOWN: 0.5
        }.get(node.node_type, 1.0)
        
        vector = vector * type_factor
        node.vector = vector
        return vector
    
    def encode_structure(self, nodes: List[ContextNode]) -> np.ndarray:
        """
        编码节点结构为单个向量
        
        参数:
            nodes: 节点列表
            
        返回:
            结构的向量表示
        """
        if not nodes:
            return np.zeros(self.vector_dim)
            
        vectors = [self.encode_node(node) for node in nodes]
        return np.mean(vectors, axis=0)


class CognitiveContextGraph:
    """
    认知语境图谱
    
    将代码的变量引用图升级为认知语境图谱，支持结构相似度计算和隐喻级复用
    """
    
    def __init__(self, vector_dim: int = 128):
        """
        初始化认知语境图谱
        
        参数:
            vector_dim: 向量维度，默认为128
        """
        self.nodes: Dict[str, ContextNode] = {}
        self.encoder = VectorEncoder(vector_dim)
        self.structure_index: Dict[str, np.ndarray] = {}  # 结构向量索引
        self.pattern_library: Dict[str, List[str]] = defaultdict(list)  # 模式库
        
        logger.info(f"初始化认知语境图谱，向量维度: {vector_dim}")
        
    def add_context(self, source_code: str) -> bool:
        """
        添加新的代码上下文到图谱
        
        参数:
            source_code: Python源代码
            
        返回:
            是否添加成功
        """
        if not source_code:
            logger.warning("空源代码，忽略添加")
            return False
            
        try:
            nodes = CodeParser.parse_code(source_code)
            if not nodes:
                logger.warning("解析代码未生成任何节点")
                return False
                
            # 添加节点到图谱
            for node in nodes:
                self.encoder.encode_node(node)
                self.nodes[node.node_id] = node
                
            # 构建结构索引
            structure_vector = self.encoder.encode_structure(nodes)
            structure_id = hashlib.md5(source_code.encode()).hexdigest()
            self.structure_index[structure_id] = structure_vector
            
            # 识别并存储模式
            self._identify_patterns(nodes)
            
            logger.info(f"成功添加上下文，共 {len(nodes)} 个节点")
            return True
            
        except Exception as e:
            logger.error(f"添加上下文失败: {e}")
            return False
    
    def _identify_patterns(self, nodes: List[ContextNode]) -> None:
        """
        识别代码中的模式并存储到模式库
        
        参数:
            nodes: 节点列表
        """
        # 简单的模式识别：函数-变量依赖模式
        func_nodes = [n for n in nodes if n.node_type == NodeType.FUNCTION]
        var_nodes = [n for n in nodes if n.node_type == NodeType.VARIABLE]
        
        for func in func_nodes:
            # 查找函数中使用的变量
            for var in var_nodes:
                if var.name in func.source_code:
                    pattern_key = f"func_var_dep_{func.name}"
                    self.pattern_library[pattern_key].append(var.node_id)
                    
    def find_similar_structure(
        self, 
        query_code: str, 
        top_k: int = 3,
        threshold: float = 0.7
    ) -> List[Tuple[str, float]]:
        """
        查找与查询代码结构相似的历史上下文
        
        参数:
            query_code: 查询的代码字符串
            top_k: 返回的最相似结果数量
            threshold: 相似度阈值
            
        返回:
            元组列表，每个元组包含(结构ID, 相似度分数)
        """
        if not query_code:
            logger.warning("空查询代码")
            return []
            
        if top_k <= 0:
            logger.warning(f"无效的top_k值 {top_k}，使用默认值3")
            top_k = 3
            
        if not 0 <= threshold <= 1:
            logger.warning(f"无效的阈值 {threshold}，使用默认值0.7")
            threshold = 0.7
            
        try:
            # 解析查询代码
            query_nodes = CodeParser.parse_code(query_code)
            if not query_nodes:
                return []
                
            # 编码查询结构
            query_vector = self.encoder.encode_structure(query_nodes)
            
            # 计算与所有历史结构的相似度
            similarities = []
            for struct_id, struct_vector in self.structure_index.items():
                similarity = self._cosine_similarity(query_vector, struct_vector)
                if similarity >= threshold:
                    similarities.append((struct_id, similarity))
                    
            # 排序并返回top_k结果
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"查找相似结构失败: {e}")
            return []
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度
        
        参数:
            vec1: 第一个向量
            vec2: 第二个向量
            
        返回:
            余弦相似度分数
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def get_metaphor_mapping(
        self, 
        source_pattern: str, 
        target_context: str
    ) -> Dict[str, str]:
        """
        实现代码逻辑的隐喻级映射
        
        参数:
            source_pattern: 源模式名称
            target_context: 目标上下文代码
            
        返回:
            映射字典，键为源节点，值为目标节点
        """
        mapping: Dict[str, str] = {}
        
        if source_pattern not in self.pattern_library:
            logger.warning(f"模式 {source_pattern} 不存在于模式库中")
            return mapping
            
        try:
            # 解析目标上下文
            target_nodes = CodeParser.parse_code(target_context)
            if not target_nodes:
                return mapping
                
            # 获取源模式节点
            source_node_ids = self.pattern_library[source_pattern]
            source_nodes = [
                self.nodes[nid] for nid in source_node_ids 
                if nid in self.nodes
            ]
            
            # 简单的名称匹配映射（实际应用中应使用更复杂的结构映射算法）
            for source_node in source_nodes:
                for target_node in target_nodes:
                    if (source_node.node_type == target_node.node_type and 
                        self._cosine_similarity(source_node.vector, target_node.vector) > 0.8):
                        mapping[source_node.name] = target_node.name
                        break
                        
            logger.info(f"生成隐喻映射，共 {len(mapping)} 个映射关系")
            return mapping
            
        except Exception as e:
            logger.error(f"生成隐喻映射失败: {e}")
            return mapping
    
    def save_to_file(self, filepath: str) -> bool:
        """
        将图谱保存到文件
        
        参数:
            filepath: 文件路径
            
        返回:
            是否保存成功
        """
        try:
            data = {
                'nodes': {
                    nid: {
                        'node_id': node.node_id,
                        'node_type': node.node_type.name,
                        'name': node.name,
                        'vector': node.vector.tolist(),
                        'connections': node.connections,
                        'metadata': node.metadata,
                        'source_code': node.source_code
                    }
                    for nid, node in self.nodes.items()
                },
                'structure_index': {
                    sid: vec.tolist() 
                    for sid, vec in self.structure_index.items()
                },
                'pattern_library': dict(self.pattern_library)
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"图谱成功保存到 {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存图谱失败: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filepath: str) -> Optional['CognitiveContextGraph']:
        """
        从文件加载图谱
        
        参数:
            filepath: 文件路径
            
        返回:
            加载的图谱对象，失败返回None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            graph = cls()
            
            # 加载节点
            for nid, node_data in data['nodes'].items():
                node = ContextNode(
                    node_id=node_data['node_id'],
                    node_type=NodeType[node_data['node_type']],
                    name=node_data['name'],
                    vector=np.array(node_data['vector']),
                    connections=node_data['connections'],
                    metadata=node_data['metadata'],
                    source_code=node_data['source_code']
                )
                graph.nodes[nid] = node
                
            # 加载结构索引
            for sid, vec in data['structure_index'].items():
                graph.structure_index[sid] = np.array(vec)
                
            # 加载模式库
            graph.pattern_library = defaultdict(list, data['pattern_library'])
            
            logger.info(f"成功从 {filepath} 加载图谱")
            return graph
            
        except Exception as e:
            logger.error(f"加载图谱失败: {e}")
            return None


def demo_usage():
    """
    演示认知语境图谱的使用方法
    """
    # 示例代码1：数据处理函数
    code1 = """
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            processed = item * 2
            result.append(processed)
    return result
"""

    # 示例代码2：类似的处理函数
    code2 = """
def handle_items(items):
    output = []
    for element in items:
        if element != 0:
            transformed = element + 10
            output.append(transformed)
    return output
"""

    # 创建认知语境图谱
    graph = CognitiveContextGraph()
    
    # 添加代码上下文
    graph.add_context(code1)
    
    # 查找相似结构
    similar = graph.find_similar_structure(code2)
    print("相似结构:", similar)
    
    # 获取隐喻映射
    mapping = graph.get_metaphor_mapping(
        "func_var_dep_process_data", 
        code2
    )
    print("变量映射:", mapping)


if __name__ == "__main__":
    demo_usage()