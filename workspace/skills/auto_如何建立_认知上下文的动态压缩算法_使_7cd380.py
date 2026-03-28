"""
模块名称: cognitive_context_compression
描述: 实现认知上下文的动态压缩算法，用于AGI系统长程代码生成过程中的上下文管理。
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CognitiveNode:
    """
    认知节点数据结构，表示上下文中的单个知识单元。
    
    属性:
        id (str): 节点唯一标识符
        content (str): 节点文本内容
        embedding (np.ndarray): 节点的向量嵌入表示
        metadata (Dict[str, Any]): 节点元数据(如类型、创建时间等)
        relevance_score (float): 与当前焦点的相关性得分
    """
    id: str
    content: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    relevance_score: float = 0.0

class CognitiveContextCompressor:
    """
    认知上下文动态压缩系统，用于管理长程代码生成过程中的上下文窗口限制问题。
    
    该系统通过以下方式工作:
    1. 将当前任务焦点编码为向量
    2. 从已有节点中检索最相关的Top-K个节点
    3. 动态构建压缩后的上下文窗口
    
    示例:
        >>> compressor = CognitiveContextCompressor()
        >>> nodes = [CognitiveNode(...), ...]  # 已有知识节点
        >>> current_focus = "正在设计用户认证系统的数据库Schema"
        >>> compressed_context = compressor.compress_context(nodes, current_focus, top_k=5)
    """
    
    def __init__(self, similarity_threshold: float = 0.75, max_nodes: int = 2175):
        """
        初始化认知上下文压缩器。
        
        参数:
            similarity_threshold (float): 节点相关性阈值(0-1)
            max_nodes (int): 系统支持的最大节点数
        """
        self.similarity_threshold = similarity_threshold
        self.max_nodes = max_nodes
        self._validate_parameters()
        
    def _validate_parameters(self) -> None:
        """验证初始化参数的有效性"""
        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("相似度阈值必须在0到1之间")
        if self.max_nodes <= 0:
            raise ValueError("最大节点数必须为正整数")
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        将文本编码为向量嵌入(模拟函数)。
        
        在实际应用中，这里应该调用真实的嵌入模型(如BERT、GPT等)
        
        参数:
            text (str): 要编码的文本
            
        返回:
            np.ndarray: 文本的向量表示(768维)
        """
        if not text or not isinstance(text, str):
            logger.warning("收到空文本或非字符串输入，返回零向量")
            return np.zeros(768)
            
        # 模拟嵌入过程 - 实际应用中应替换为真实模型调用
        # 这里使用随机向量作为示例
        np.random.seed(hash(text) % (2**32))
        return np.random.rand(768)
    
    def retrieve_relevant_nodes(
        self,
        nodes: List[CognitiveNode],
        current_focus: str,
        top_k: int = 5
    ) -> List[CognitiveNode]:
        """
        从节点集合中检索与当前焦点最相关的Top-K个节点。
        
        参数:
            nodes (List[CognitiveNode]): 候选节点集合
            current_focus (str): 当前任务焦点描述
            top_k (int): 要检索的节点数量
            
        返回:
            List[CognitiveNode]: 排序后的相关节点列表
            
        异常:
            ValueError: 如果输入参数无效
        """
        try:
            # 输入验证
            if not nodes:
                logger.warning("节点列表为空")
                return []
                
            if top_k <= 0:
                raise ValueError("top_k必须为正整数")
                
            if len(nodes) > self.max_nodes:
                logger.warning(f"节点数量({len(nodes)})超过系统限制({self.max_nodes})")
                
            # 编码当前焦点
            focus_embedding = self.encode_text(current_focus)
            
            # 计算所有节点的相关性得分
            relevant_nodes = []
            for node in nodes:
                similarity = cosine_similarity(
                    [focus_embedding], [node.embedding]
                )[0][0]
                
                if similarity >= self.similarity_threshold:
                    node.relevance_score = float(similarity)
                    relevant_nodes.append(node)
            
            # 按相关性排序并返回Top-K
            relevant_nodes.sort(key=lambda x: x.relevance_score, reverse=True)
            return relevant_nodes[:top_k]
            
        except Exception as e:
            logger.error(f"节点检索失败: {str(e)}")
            raise RuntimeError(f"节点检索过程中发生错误: {str(e)}") from e
    
    def compress_context(
        self,
        nodes: List[CognitiveNode],
        current_focus: str,
        max_tokens: int = 4096,
        top_k: int = 5
    ) -> Tuple[List[CognitiveNode], Dict[str, Any]]:
        """
        压缩上下文窗口，返回最相关的节点和统计信息。
        
        参数:
            nodes (List[CognitiveNode]): 所有可用认知节点
            current_focus (str): 当前任务焦点
            max_tokens (int): 最大允许的token数
            top_k (int): 初始检索的节点数量
            
        返回:
            Tuple[List[CognitiveNode], Dict[str, Any]]: 
                压缩后的节点列表和包含统计信息的字典
                
        异常:
            RuntimeError: 如果上下文压缩失败
        """
        stats = {
            'total_nodes': len(nodes),
            'initial_top_k': top_k,
            'final_nodes': 0,
            'compression_ratio': 0.0,
            'relevance_stats': {
                'max': 0.0,
                'min': 0.0,
                'avg': 0.0
            }
        }
        
        try:
            # 检索相关节点
            relevant_nodes = self.retrieve_relevant_nodes(nodes, current_focus, top_k)
            
            if not relevant_nodes:
                logger.warning("没有找到相关节点")
                return [], stats
                
            # 根据token限制进一步压缩
            compressed_nodes = []
            total_tokens = 0
            
            for node in relevant_nodes:
                # 简单估算token数 (实际应用中应使用tokenizer)
                node_tokens = len(node.content.split())
                
                if total_tokens + node_tokens <= max_tokens:
                    compressed_nodes.append(node)
                    total_tokens += node_tokens
                else:
                    break
            
            # 更新统计信息
            if compressed_nodes:
                scores = [n.relevance_score for n in compressed_nodes]
                stats.update({
                    'final_nodes': len(compressed_nodes),
                    'compression_ratio': len(compressed_nodes) / len(nodes) if nodes else 0,
                    'relevance_stats': {
                        'max': max(scores),
                        'min': min(scores),
                        'avg': sum(scores) / len(scores)
                    }
                })
                
            logger.info(f"上下文压缩完成: {stats}")
            return compressed_nodes, stats
            
        except Exception as e:
            logger.error(f"上下文压缩失败: {str(e)}")
            raise RuntimeError(f"上下文压缩过程中发生错误: {str(e)}") from e

def create_mock_nodes(num_nodes: int = 10) -> List[CognitiveNode]:
    """
    辅助函数: 创建模拟的认知节点用于测试。
    
    参数:
        num_nodes (int): 要创建的节点数量
        
    返回:
        List[CognitiveNode]: 模拟节点列表
    """
    mock_nodes = []
    node_types = ['sql_practice', 'orm_mapping', 'api_design', 'security', 'testing']
    
    for i in range(num_nodes):
        node_type = node_types[i % len(node_types)]
        content = f"这是关于{node_type}的示例内容节点 #{i+1}"
        
        # 创建模拟嵌入
        np.random.seed(i)
        embedding = np.random.rand(768)
        
        mock_nodes.append(CognitiveNode(
            id=f"node_{i+1}",
            content=content,
            embedding=embedding,
            metadata={
                'type': node_type,
                'source': 'mock_data',
                'created_at': f"2023-{i%12+1:02d}-{i%28+1:02d}"
            }
        ))
        
    return mock_nodes

if __name__ == "__main__":
    # 使用示例
    try:
        # 1. 初始化压缩器
        compressor = CognitiveContextCompressor(similarity_threshold=0.7)
        
        # 2. 创建模拟数据 (在实际应用中应从知识库加载)
        nodes = create_mock_nodes(50)
        print(f"创建了 {len(nodes)} 个模拟节点")
        
        # 3. 定义当前任务焦点
        current_focus = "正在设计用户认证系统的PostgreSQL数据库Schema，需要处理用户角色和权限管理"
        
        # 4. 执行上下文压缩
        compressed_nodes, stats = compressor.compress_context(
            nodes=nodes,
            current_focus=current_focus,
            max_tokens=2000,
            top_k=10
        )
        
        # 5. 输出结果
        print("\n压缩结果:")
        print(f"- 原始节点数: {stats['total_nodes']}")
        print(f"- 压缩后节点数: {stats['final_nodes']}")
        print(f"- 压缩率: {stats['compression_ratio']:.2%}")
        print("\n最相关节点:")
        for i, node in enumerate(compressed_nodes, 1):
            print(f"{i}. [{node.metadata['type']}] {node.content} (相关度: {node.relevance_score:.2f})")
            
    except Exception as e:
        logger.error(f"示例运行失败: {str(e)}")
        raise