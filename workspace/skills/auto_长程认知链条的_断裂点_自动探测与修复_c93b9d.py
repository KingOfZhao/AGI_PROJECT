"""
模块: auto_长程认知链条的_断裂点_自动探测与修复_c93b9d
描述: Implementation of a mechanism to detect logical discontinuities ('fractures')
       in long-range cognitive chains and generate remediation queries.
       
       In an AGI context, reasoning often requires traversing a knowledge graph
       (e.g., A -> B -> C -> Conclusion). However, naive traversal can miss
       implicit logical gaps. This module introduces a 'Cognitive Friction' score
       to identify where explicit links are missing and generates 'Filler Node'
       queries to bridge the gap, preventing hallucination.
       
Author: Senior Python Engineer
Version: 1.0.0
"""

import logging
import dataclasses
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReasoningState(Enum):
    """定义推理链的状态"""
    CONCRETE = "CONCRETE"       # 基于确凿事实
    INFERRED = "INFERRED"       # 基于逻辑推导
    HYPOTHETICAL = "HYPOTHETICAL" # 基于假设
    UNKNOWN = "UNKNOWN"

@dataclasses.dataclass
class CognitiveNode:
    """
    认知节点：代表推理链中的一个概念或事实。
    
    Attributes:
        id (str): 节点唯一标识符
        content (str): 节点包含的文本或数据内容
        embedding (Optional[List[float]]): 节点的向量嵌入表示，用于语义计算
        state (ReasoningState): 节点的确定性状态
        metadata (Dict[str, Any]): 其他元数据
    """
    id: str
    content: str
    embedding: Optional[List[float]] = None
    state: ReasoningState = ReasoningState.UNKNOWN
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self):
        if not self.id or not self.content:
            raise ValueError("Node ID and Content cannot be empty.")

@dataclasses.dataclass
class CognitiveLink:
    """
    认知链接：代表两个节点之间的关系。
    
    Attributes:
        source_id (str): 源节点ID
        target_id (str): 目标节点ID
        weight (float): 链接强度 (0.0 到 1.0)
        is_verified (bool): 是否经过显式验证
    """
    source_id: str
    target_id: str
    weight: float = 0.5
    is_verified: bool = False

@dataclasses.dataclass
class FractureReport:
    """
    断裂点报告：描述检测到的逻辑断层。
    
    Attributes:
        fracture_id (str): 断裂点唯一ID
        start_node (CognitiveNode): 断裂起始节点
        end_node (CognitiveNode): 断裂结束节点
        friction_score (float): 计算出的认知摩擦力 (0-100)
        suggested_query (str): 系统生成的用于修复断层的查询语句
    """
    fracture_id: str
    start_node: CognitiveNode
    end_node: CognitiveNode
    friction_score: float
    suggested_query: str

class CognitiveChainValidator:
    """
    核心类：验证长程认知链条，检测断裂点并生成修复方案。
    """
    
    def __init__(self, friction_threshold: float = 0.75):
        """
        初始化验证器。
        
        Args:
            friction_threshold (float): 判定为'断裂'的摩擦力阈值 (0.0-1.0)。
                                        越高表示对逻辑严密性要求越高。
        """
        if not 0.0 <= friction_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        self.friction_threshold = friction_threshold
        logger.info(f"CognitiveChainValidator initialized with threshold: {friction_threshold}")

    def _calculate_semantic_distance(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        辅助函数：计算两个向量之间的语义距离（简化版余弦距离）。
        
        Args:
            vec_a (List[float]): 向量A
            vec_b (List[float]): 向量B
            
        Returns:
            float: 语义距离 (0.0 到 1.0)
        """
        if len(vec_a) != len(vec_b):
            logger.error("Vector dimension mismatch in semantic calculation.")
            raise ValueError("Vector dimensions must match")
            
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 1.0 # 最大距离
            
        similarity = dot_product / (norm_a * norm_b)
        # 转换为距离：距离 = 1 - 相似度
        return max(0.0, min(1.0, 1.0 - similarity))

    def calculate_cognitive_friction(self, node_a: CognitiveNode, node_b: CognitiveNode, link: Optional[CognitiveLink]) -> float:
        """
        核心函数 1: 计算两个相邻节点之间的'认知摩擦力'。
        
        摩擦力高意味着逻辑跳跃大，存在断层风险。
        计算因子：
        1. Semantic Distance (语义距离): 向量空间的距离。
        2. Link Verification (链接验证): 是否是已验证的链接。
        3. Reasoning State (推理状态): 节点本身的不确定性。
        
        Args:
            node_a (CognitiveNode): 起始节点
            node_b (CognitiveNode): 目标节点
            link (Optional[CognitiveLink]): 连接两者的链接对象
            
        Returns:
            float: 认知摩擦力分数 (0.0 到 100.0)
        """
        score = 0.0
        
        # 1. 语义距离检测 (权重 40%)
        if node_a.embedding and node_b.embedding:
            dist = self._calculate_semantic_distance(node_a.embedding, node_b.embedding)
            score += dist * 40.0
        else:
            # 如果没有嵌入向量，假设风险较高
            score += 20.0 

        # 2. 链接验证状态 (权重 30%)
        if link is None:
            # 如果根本没有链接对象，说明是强行拼接
            score += 30.0
        elif not link.is_verified:
            # 如果链接未验证
            score += 15.0
            # 考虑链接权重的影响
            score += (1.0 - link.weight) * 15.0
        
        # 3. 推理状态检查 (权重 30%)
        if node_b.state == ReasoningState.HYPOTHETICAL:
            score += 20.0
        if node_a.state == ReasoningState.HYPOTHETICAL:
            score += 10.0
            
        logger.debug(f"Friction between {node_a.id} -> {node_b.id}: {score}")
        return min(100.0, score)

    def detect_and_repair_chain(self, chain: List[CognitiveNode], links: Dict[Tuple[str, str], CognitiveLink]) -> List[FractureReport]:
        """
        核心函数 2: 遍历链条，检测断裂点并生成修复查询。
        
        Args:
            chain (List[CognitiveNode]): 认知链条（节点列表）。
            links (Dict[Tuple[str, str], CognitiveLink]): 节点间的链接字典，key为(id_a, id_b)。
            
        Returns:
            List[FractureReport]: 检测到的断裂点列表，包含修复建议。
        """
        if not chain:
            logger.warning("Empty chain provided for validation.")
            return []

        reports = []
        
        for i in range(len(chain) - 1):
            current_node = chain[i]
            next_node = chain[i+1]
            
            # 查找链接
            link_key = (current_node.id, next_node.id)
            current_link = links.get(link_key)
            
            # 计算摩擦力
            friction = self.calculate_cognitive_friction(current_node, next_node, current_link)
            
            # 判定是否断裂
            # 将 0-100 分数映射到阈值逻辑 (假设阈值 0.75 对应 75分)
            if friction > (self.friction_threshold * 100):
                logger.warning(f"Fracture detected between {current_node.id} and {next_node.id}. Score: {friction}")
                
                # 生成修复查询
                query = self._generate_filler_query(current_node, next_node)
                
                report = FractureReport(
                    fracture_id=f"fracture_{i}_{current_node.id}_{next_node.id}",
                    start_node=current_node,
                    end_node=next_node,
                    friction_score=friction,
                    suggested_query=query
                )
                reports.append(report)
                
        return reports

    def _generate_filler_query(self, start: CognitiveNode, end: CognitiveNode) -> str:
        """
        辅助函数：生成用于搜索中间节点的自然语言查询。
        
        策略：结合前后节点的关键内容，构造一个询问逻辑桥梁的问句。
        """
        # 简化的关键信息提取（实际AGI场景会使用摘要模型）
        start_preview = start.content[:50] + "..." if len(start.content) > 50 else start.content
        end_preview = end.content[:50] + "..." if len(end.content) > 50 else end.content
        
        query = (
            f"Search Query: What is the logical bridge connecting the concept '{start_preview}' "
            f"to the result '{end_preview}'? "
            f"Specifically looking for causality or intermediate steps."
        )
        return query

# 使用示例
if __name__ == "__main__":
    # 模拟数据：构建一个 A -> B -> C 的推理链
    # A: "天空呈蓝色" (Fact)
    # B: "瑞利散射现象" (Fact, high semantic jump from A)
    # C: "大海看起来是蓝色的" (Hypothesis)
    
    node_a = CognitiveNode(
        id="node_1", 
        content="The sky is blue during the day.", 
        embedding=[1.0, 0.0, 0.0], # 简化向量
        state=ReasoningState.CONCRETE
    )
    
    # 这个节点在语义上可能离A较远，且未显式链接
    node_b = CognitiveNode(
        id="node_2", 
        content="Rayleigh scattering disperses short wavelength light.", 
        embedding=[0.1, 0.9, 0.1], 
        state=ReasoningState.CONCRETE
    )
    
    # 这个是假设，且离B语义距离较远
    node_c = CognitiveNode(
        id="node_3", 
        content="Therefore, the ocean reflects the color of the sky.", 
        embedding=[0.8, 0.2, 0.0], 
        state=ReasoningState.HYPOTHETICAL
    )
    
    # 构建链条
    reasoning_chain = [node_a, node_b, node_c]
    
    # 模拟链接：A->B 存在但未验证，B->C 完全缺失
    existing_links = {
        ("node_1", "node_2"): CognitiveLink("node_1", "node_2", weight=0.4, is_verified=False)
        # node_2 -> node_3 的链接缺失
    }
    
    # 初始化验证器
    validator = CognitiveChainValidator(friction_threshold=0.6)
    
    # 运行检测
    print("--- Starting Cognitive Chain Validation ---")
    fractures = validator.detect_and_repair_chain(reasoning_chain, existing_links)
    
    print(f"\n--- Detected {len(fractures)} Fractures ---")
    for f in fractures:
        print(f"ID: {f.fracture_id}")
        print(f"Between: {f.start_node.id} -> {f.end_node.id}")
        print(f"Friction Score: {f.friction_score}")
        print(f"Repair Query: {f.suggested_query}")
        print("-" * 30)