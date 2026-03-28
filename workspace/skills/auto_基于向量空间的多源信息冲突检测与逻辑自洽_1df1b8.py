"""
高级技能模块：基于向量空间的多源信息冲突检测与逻辑自洽性验证
该模块实现了通过语义向量距离与逻辑蕴涵关系检测知识冲突的机制。
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, validator, Field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConflictType(Enum):
    """冲突类型枚举"""
    CONTEXTUAL_DIFFERENCE = "语境差异"  # 可共存，需细化语境
    LOGICAL_CONTRADICTION = "事实冲突"  # 逻辑矛盾，不可共存
    NO_CONFLICT = "无冲突"              # 无明显冲突
    UNKNOWN = "未知"                   # 无法确定

@dataclass
class KnowledgeNode:
    """知识节点数据结构"""
    node_id: str
    content: str
    embedding: np.ndarray
    domain: str = "general"
    weight: float = 1.0
    context: Dict[str, Union[str, float]] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}

class ConflictDetectionResult(BaseModel):
    """冲突检测结果模型"""
    node_a_id: str
    node_b_id: str
    conflict_type: ConflictType
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    resolution_strategy: Optional[str] = None

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("置信度必须在0到1之间")
        return v

class VectorSpaceConflictDetector:
    """基于向量空间的多源信息冲突检测器"""
    
    def __init__(self, 
                 semantic_threshold: float = 0.75,
                 logical_threshold: float = 0.85,
                 context_weight: float = 0.3):
        """
        初始化冲突检测器
        
        参数:
            semantic_threshold: 语义相似度阈值
            logical_threshold: 逻辑蕴涵阈值
            context_weight: 上下文权重
        """
        self.semantic_threshold = semantic_threshold
        self.logical_threshold = logical_threshold
        self.context_weight = context_weight
        self._validate_parameters()
        
    def _validate_parameters(self):
        """验证初始化参数"""
        if not 0 <= self.semantic_threshold <= 1:
            raise ValueError("语义阈值必须在0到1之间")
        if not 0 <= self.logical_threshold <= 1:
            raise ValueError("逻辑阈值必须在0到1之间")
        if not 0 <= self.context_weight <= 1:
            raise ValueError("上下文权重必须在0到1之间")
    
    def detect_conflict(self, 
                       node_a: KnowledgeNode, 
                       node_b: KnowledgeNode) -> ConflictDetectionResult:
        """
        检测两个知识节点之间的冲突
        
        参数:
            node_a: 第一个知识节点
            node_b: 第二个知识节点
            
        返回:
            ConflictDetectionResult: 冲突检测结果
        """
        try:
            # 计算语义相似度
            semantic_sim = self._cosine_similarity(node_a.embedding, node_b.embedding)
            
            # 计算上下文相似度
            context_sim = self._calculate_context_similarity(node_a.context, node_b.context)
            
            # 计算综合相似度
            combined_sim = (1 - self.context_weight) * semantic_sim + \
                          self.context_weight * context_sim
            
            # 判断冲突类型
            if combined_sim < self.semantic_threshold:
                return ConflictDetectionResult(
                    node_a_id=node_a.node_id,
                    node_b_id=node_b.node_id,
                    conflict_type=ConflictType.NO_CONFLICT,
                    confidence=1 - combined_sim,
                    explanation="语义距离过大，无直接冲突"
                )
            
            # 检查逻辑蕴涵关系
            logical_relation = self._check_logical_relation(node_a, node_b)
            
            if logical_relation > self.logical_threshold:
                return ConflictDetectionResult(
                    node_a_id=node_a.node_id,
                    node_b_id=node_b.node_id,
                    conflict_type=ConflictType.LOGICAL_CONTRADICTION,
                    confidence=logical_relation,
                    explanation="存在逻辑矛盾",
                    resolution_strategy="需要进一步验证或选择更可靠的来源"
                )
            elif logical_relation > self.semantic_threshold:
                return ConflictDetectionResult(
                    node_a_id=node_a.node_id,
                    node_b_id=node_b.node_id,
                    conflict_type=ConflictType.CONTEXTUAL_DIFFERENCE,
                    confidence=logical_relation,
                    explanation="语境差异导致的表面冲突",
                    resolution_strategy="可以通过细化语境条件来共存"
                )
            else:
                return ConflictDetectionResult(
                    node_a_id=node_a.node_id,
                    node_b_id=node_b.node_id,
                    conflict_type=ConflictType.NO_CONFLICT,
                    confidence=1 - logical_relation,
                    explanation="无逻辑冲突"
                )
                
        except Exception as e:
            logger.error(f"冲突检测失败: {str(e)}")
            raise RuntimeError(f"冲突检测过程中发生错误: {str(e)}")
    
    def batch_detect_conflicts(self, 
                             nodes: List[KnowledgeNode]) -> List[ConflictDetectionResult]:
        """
        批量检测节点列表中的冲突
        
        参数:
            nodes: 知识节点列表
            
        返回:
            List[ConflictDetectionResult]: 冲突检测结果列表
        """
        if len(nodes) < 2:
            logger.warning("节点数量不足，无法进行冲突检测")
            return []
            
        results = []
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                try:
                    result = self.detect_conflict(nodes[i], nodes[j])
                    if result.conflict_type != ConflictType.NO_CONFLICT:
                        results.append(result)
                except Exception as e:
                    logger.error(f"检测节点 {nodes[i].node_id} 和 {nodes[j].node_id} 冲突时出错: {str(e)}")
                    continue
                    
        return results
    
    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        计算两个向量的余弦相似度
        
        参数:
            vec_a: 第一个向量
            vec_b: 第二个向量
            
        返回:
            float: 余弦相似度
        """
        if vec_a.shape != vec_b.shape:
            raise ValueError("向量维度不匹配")
            
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return np.dot(vec_a, vec_b) / (norm_a * norm_b)
    
    def _calculate_context_similarity(self, 
                                    context_a: Dict[str, Union[str, float]], 
                                    context_b: Dict[str, Union[str, float]]) -> float:
        """
        计算两个上下文的相似度
        
        参数:
            context_a: 第一个上下文
            context_b: 第二个上下文
            
        返回:
            float: 上下文相似度
        """
        if not context_a or not context_b:
            return 0.0
            
        # 提取共同的键
        common_keys = set(context_a.keys()) & set(context_b.keys())
        if not common_keys:
            return 0.0
            
        # 计算共同键的相似度
        similarities = []
        for key in common_keys:
            val_a = context_a[key]
            val_b = context_b[key]
            
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                # 数值型相似度计算
                max_val = max(abs(val_a), abs(val_b))
                if max_val == 0:
                    similarities.append(1.0)
                else:
                    similarities.append(1 - abs(val_a - val_b) / max_val)
            elif isinstance(val_a, str) and isinstance(val_b, str):
                # 字符串相似度计算
                similarities.append(1.0 if val_a == val_b else 0.0)
                
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _check_logical_relation(self, 
                              node_a: KnowledgeNode, 
                              node_b: KnowledgeNode) -> float:
        """
        检查两个节点的逻辑关系
        
        参数:
            node_a: 第一个知识节点
            node_b: 第二个知识节点
            
        返回:
            float: 逻辑冲突程度 [0, 1]
        """
        # 这里实现简化的逻辑检查
        # 在实际应用中，可能需要使用更复杂的逻辑推理引擎
        
        # 检查内容是否包含否定词
        negation_words = ["不", "非", "无", "没有"]
        has_negation_a = any(word in node_a.content for word in negation_words)
        has_negation_b = any(word in node_b.content for word in negation_words)
        
        # 如果一个包含否定词而另一个不包含，可能有逻辑冲突
        if has_negation_a != has_negation_b:
            # 计算语义相似度作为基础冲突度
            semantic_sim = self._cosine_similarity(node_a.embedding, node_b.embedding)
            return semantic_sim * 0.8  # 调整系数
            
        return 0.0

# 使用示例
if __name__ == "__main__":
    # 创建示例节点
    node1 = KnowledgeNode(
        node_id="node1",
        content="多吃糖导致肥胖",
        embedding=np.random.rand(768),  # 实际应用中应使用真实的嵌入向量
        domain="health",
        context={"population": "general", "age_group": "adults"}
    )
    
    node2 = KnowledgeNode(
        node_id="node2",
        content="某特殊代谢人群多吃糖不肥胖",
        embedding=np.random.rand(768),  # 实际应用中应使用真实的嵌入向量
        domain="health",
        context={"population": "special_metabolism", "age_group": "adults"}
    )
    
    # 初始化检测器
    detector = VectorSpaceConflictDetector(
        semantic_threshold=0.7,
        logical_threshold=0.8,
        context_weight=0.3
    )
    
    # 检测冲突
    result = detector.detect_conflict(node1, node2)
    print(f"冲突类型: {result.conflict_type.value}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"解释: {result.explanation}")
    print(f"解决策略: {result.resolution_strategy or '无'}")
    
    # 批量检测示例
    nodes = [
        node1,
        node2,
        KnowledgeNode(
            node_id="node3",
            content="运动有助于减肥",
            embedding=np.random.rand(768),
            domain="fitness"
        )
    ]
    
    batch_results = detector.batch_detect_conflicts(nodes)
    print(f"\n批量检测结果: 发现 {len(batch_results)} 个潜在冲突")
    for res in batch_results:
        print(f"{res.node_a_id} vs {res.node_b_id}: {res.conflict_type.value}")