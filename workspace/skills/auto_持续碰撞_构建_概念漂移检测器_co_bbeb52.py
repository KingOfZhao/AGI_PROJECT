"""
名称: auto_持续碰撞_构建_概念漂移检测器_co_bbeb52
描述: 【持续碰撞】构建'概念漂移检测器'。
     该模块用于在大型知识网络中监测节点的有效性。
     随着外部世界变化（如法律变更、事实更新），已固化的'真实节点'可能失效。
     本模块通过设定'半衰期'参数，结合外部信息检索验证，自动触发'重验证'流程，
     实现对网络中节点活性的实时监测与更新。
"""

import logging
import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """节点状态枚举"""
    ACTIVE = "active"
    STALE = "stale"
    INVALID = "invalid"
    PENDING_REVIEW = "pending_review"

@dataclass
class KnowledgeNode:
    """
    知识节点数据结构
    
    Attributes:
        node_id (str): 节点唯一标识符
        content_hash (str): 节点内容的哈希值，用于检测变更
        last_verified_time (datetime): 上次验证时间
        half_life_days (int): 半衰期（天），定义节点多久需要重验证
        status (NodeStatus): 当前节点状态
        metadata (Dict[str, Any]): 元数据信息
    """
    node_id: str
    content_hash: str
    last_verified_time: datetime
    half_life_days: int = 30
    status: NodeStatus = NodeStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.last_verified_time, datetime):
            raise ValueError("last_verified_time 必须是 datetime 对象")

class ConceptDriftDetector:
    """
    概念漂移检测器
    
    用于监测知识网络中节点的活性，自动识别失效节点并触发重验证流程。
    
    Example:
        >>> detector = ConceptDriftDetector()
        >>> node = KnowledgeNode(
        ...     node_id="law_123",
        ...     content_hash="abc123",
        ...     last_verified_time=datetime.now() - timedelta(days=40)
        ... )
        >>> result = detector.check_node_drift(node)
        >>> if result['needs_review']:
        ...     print("Node needs re-verification")
    """
    
    def __init__(self, stale_threshold_multiplier: float = 0.8):
        """
        初始化检测器
        
        Args:
            stale_threshold_multiplier (float): 衰减阈值系数，当节点超过半衰期*系数时标记为STALE
        """
        self.stale_threshold_multiplier = stale_threshold_multiplier
        self._validation_cache: Dict[str, datetime] = {}
        
    def _calculate_decay_score(self, node: KnowledgeNode) -> float:
        """
        计算节点的衰减分数（辅助函数）
        
        基于指数衰减模型计算节点的活性分数。
        分数范围 [0, 1]，1表示刚刚验证，0表示完全衰减。
        
        Args:
            node (KnowledgeNode): 待计算的节点
            
        Returns:
            float: 衰减分数，越接近0表示越需要重新验证
            
        Raises:
            ValueError: 如果half_life_days <= 0
        """
        if node.half_life_days <= 0:
            raise ValueError("半衰期必须大于0")
            
        elapsed = (datetime.now() - node.last_verified_time).total_seconds() / 86400  # 转换为天
        decay_constant = 0.693 / node.half_life_days  # ln(2) / half_life
        score = pow(2, -decay_constant * elapsed)
        
        # 边界检查
        return max(0.0, min(1.0, score))
    
    def check_node_drift(self, node: KnowledgeNode) -> Dict[str, Any]:
        """
        检查单个节点的概念漂移状态（核心函数1）
        
        根据节点的半衰期和上次验证时间，判断节点是否需要重新验证。
        
        Args:
            node (KnowledgeNode): 待检查的知识节点
            
        Returns:
            Dict[str, Any]: 包含以下键的字典：
                - node_id: 节点ID
                - needs_review: 是否需要审核
                - decay_score: 衰减分数
                - recommended_action: 建议操作
                - current_status: 当前状态
                
        Example:
            >>> result = detector.check_node_drift(node)
            >>> print(result['decay_score'])
            0.75
        """
        if not isinstance(node, KnowledgeNode):
            raise TypeError("输入必须是 KnowledgeNode 类型")
            
        try:
            decay_score = self._calculate_decay_score(node)
            threshold = 1.0 - self.stale_threshold_multiplier
            
            needs_review = decay_score < threshold
            recommended_action = "none"
            
            if decay_score < 0.1:
                recommended_action = "immediate_revalidation"
                new_status = NodeStatus.INVALID
            elif decay_score < threshold:
                recommended_action = "schedule_revalidation"
                new_status = NodeStatus.STALE
            else:
                new_status = NodeStatus.ACTIVE
                
            # 更新状态
            if node.status != new_status:
                logger.info(f"节点 {node.node_id} 状态从 {node.status.value} 变更为 {new_status.value}")
                node.status = new_status
                
            return {
                "node_id": node.node_id,
                "needs_review": needs_review,
                "decay_score": round(decay_score, 4),
                "recommended_action": recommended_action,
                "current_status": node.status.value
            }
            
        except Exception as e:
            logger.error(f"检查节点 {node.node_id} 漂移时出错: {str(e)}")
            raise

    def batch_validate_network(
        self, 
        nodes: List[KnowledgeNode], 
        external_validator: Optional[callable] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量验证网络中的节点活性（核心函数2）
        
        扫描整个网络，识别需要重新验证的节点，并可选择性调用外部验证器。
        
        Args:
            nodes (List[KnowledgeNode]): 待验证的节点列表
            external_validator (Optional[callable]): 外部验证函数，接收node_id，返回bool
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: 分类后的验证报告，包含：
                - "needs_review": 需要审核的节点列表
                - "active": 活跃节点列表
                - "validation_errors": 验证出错的节点列表
                
        Input Format:
            nodes: List[KnowledgeNode] - 知识节点列表
            
        Output Format:
            {
                "needs_review": [{"node_id": str, "score": float, ...}, ...],
                "active": [{"node_id": str, "score": float}, ...],
                "validation_errors": [{"node_id": str, "error": str}, ...]
            }
            
        Example:
            >>> nodes = [node1, node2, node3]
            >>> report = detector.batch_validate_network(nodes)
            >>> print(f"需审核节点数: {len(report['needs_review'])}")
        """
        if not isinstance(nodes, list):
            raise TypeError("nodes 必须是列表")
            
        report = {
            "needs_review": [],
            "active": [],
            "validation_errors": []
        }
        
        logger.info(f"开始批量验证 {len(nodes)} 个节点...")
        
        for node in nodes:
            try:
                result = self.check_node_drift(node)
                
                if result["needs_review"]:
                    # 如果提供了外部验证器，尝试验证
                    if external_validator is not None:
                        try:
                            is_valid = external_validator(node.node_id)
                            if is_valid:
                                node.last_verified_time = datetime.now()
                                node.status = NodeStatus.ACTIVE
                                self._validation_cache[node.node_id] = datetime.now()
                                logger.info(f"外部验证通过: {node.node_id}")
                                report["active"].append({
                                    "node_id": node.node_id,
                                    "score": result["decay_score"],
                                    "external_validation": "passed"
                                })
                                continue
                        except Exception as ext_err:
                            logger.warning(f"外部验证失败 {node.node_id}: {str(ext_err)}")
                    
                    report["needs_review"].append(result)
                else:
                    report["active"].append({
                        "node_id": node.node_id,
                        "score": result["decay_score"]
                    })
                    
            except Exception as e:
                logger.error(f"处理节点 {node.node_id} 时发生错误: {str(e)}")
                report["validation_errors"].append({
                    "node_id": node.node_id,
                    "error": str(e)
                })
                
        logger.info(
            f"验证完成 - 活跃: {len(report['active'])}, "
            f"待审核: {len(report['needs_review'])}, "
            f"错误: {len(report['validation_errors'])}"
        )
        
        return report

# 使用示例
if __name__ == "__main__":
    # 创建模拟节点数据
    nodes = [
        KnowledgeNode(
            node_id="law_article_105",
            content_hash=hashlib.md5(b"old_law_content").hexdigest(),
            last_verified_time=datetime.now() - timedelta(days=45),
            half_life_days=30,
            metadata={"domain": "criminal_law", "jurisdiction": "CN"}
        ),
        KnowledgeNode(
            node_id="fact_capital_city",
            content_hash=hashlib.md5(b"beijing").hexdigest(),
            last_verified_time=datetime.now() - timedelta(days=5),
            half_life_days=365,  # 基础事实半衰期长
            metadata={"domain": "geography"}
        ),
        KnowledgeNode(
            node_id="tech_python_version",
            content_hash=hashlib.md5(b"3.11").hexdigest(),
            last_verified_time=datetime.now() - timedelta(days=100),
            half_life_days=60,
            metadata={"domain": "technology"}
        )
    ]
    
    # 初始化检测器
    detector = ConceptDriftDetector(stale_threshold_multiplier=0.75)
    
    # 单个节点检查示例
    single_result = detector.check_node_drift(nodes[0])
    print(f"\n单节点检查结果: {single_result}")
    
    # 模拟外部验证函数
    def mock_external_validator(node_id: str) -> bool:
        """模拟外部信息检索验证"""
        # 在实际场景中，这里会调用搜索引擎或知识图谱API
        return random.random() > 0.3  # 70%概率验证通过
    
    # 批量验证网络
    validation_report = detector.batch_validate_network(
        nodes, 
        external_validator=mock_external_validator
    )
    
    print("\n=== 验证报告 ===")
    print(f"需重新验证的节点: {len(validation_report['needs_review'])}")
    for item in validation_report['needs_review']:
        print(f"  - {item['node_id']}: 衰减分数 {item['decay_score']}, 建议 {item['recommended_action']}")
    
    print(f"\n活跃节点: {len(validation_report['active'])}")
    print(f"验证错误: {len(validation_report['validation_errors'])}")