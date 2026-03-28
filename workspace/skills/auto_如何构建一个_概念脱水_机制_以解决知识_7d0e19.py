"""
概念脱水机制

该模块旨在解决AGI知识库中的膨胀问题。通过评估知识节点的活度（基于最后访问时间和跨域碰撞频率），
将低活度节点进行“脱水”处理。处理策略包括：
1. 归档：将长期不用的节点移至冷存储。
2. 融合：将低活度细节节点合并到更高层级的抽象节点中。

领域: database_optimization
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Literal, Tuple
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConceptDehydrator")


class DehydrationAction(Enum):
    """脱水动作枚举"""
    ARCHIVE = "archive"  # 归档至冷数据层
    FUSE = "fuse"       # 融合进抽象节点
    KEEP = "keep"       # 保留在热数据层


@dataclass
class KnowledgeNode:
    """
    知识节点数据结构
    
    Attributes:
        id: 节点唯一标识符
        content: 节点内容摘要
        last_accessed: 最后一次被调用的时间戳
        cross_domain_hits: 参与“跨域碰撞”的次数
        abstraction_level: 抽象层级 (0=具体细节, 10=高度抽象)
        size_mb: 节点数据占用大小 (MB)
    """
    id: str
    content: str
    last_accessed: datetime
    cross_domain_hits: int
    abstraction_level: int
    size_mb: float = 1.0


@dataclass
class DehydrationResult:
    """
    脱水操作结果
    
    Attributes:
        node_id: 处理的节点ID
        action: 执行的动作
        target_id: 如果是融合动作，指向融合的目标节点ID
        space_saved: 节省的空间 (MB)
    """
    node_id: str
    action: DehydrationAction
    target_id: Optional[str] = None
    space_saved: float = 0.0


class ConceptDehydrator:
    """
    概念脱水机制核心类
    
    负责扫描知识库，计算节点活度，并执行相应的压缩或归档策略。
    """
    
    def __init__(self, inactivity_threshold_days: int = 90, min_cross_domain_hits: int = 2):
        """
        初始化脱水器
        
        Args:
            inactivity_threshold_days: 判定为“不活跃”的天数阈值
            min_cross_domain_hits: 判定为“有价值”的最小跨域碰撞次数
        """
        self.inactivity_threshold = timedelta(days=inactivity_threshold_days)
        self.min_cross_domain_hits = min_cross_domain_hits
        logger.info(f"Initialized Dehydrator with threshold: {inactivity_threshold_days} days")

    def _validate_node(self, node: KnowledgeNode) -> bool:
        """
        辅助函数：验证节点数据的有效性
        
        Args:
            node: 待验证的知识节点
            
        Returns:
            bool: 数据是否有效
            
        Raises:
            ValueError: 如果数据严重缺失或无效
        """
        if not node.id or not node.content:
            raise ValueError(f"Node ID or content is missing for node {node.id}")
        if node.abstraction_level < 0 or node.abstraction_level > 10:
            logger.warning(f"Node {node.id} has invalid abstraction level: {node.abstraction_level}")
            return False
        if node.size_mb < 0:
            raise ValueError(f"Node {node.id} has negative size")
        return True

    def _calculate_activity_score(self, node: KnowledgeNode, current_time: datetime) -> float:
        """
        核心函数1：计算节点的活度得分
        
        算法逻辑：
        Score = (CrossDomainHits + 1) / (DaysInactive + 1)
        值越高，代表节点越活跃且重要。
        
        Args:
            node: 知识节点
            current_time: 当前时间戳
            
        Returns:
            float: 活度得分
        """
        time_diff = current_time - node.last_accessed
        days_inactive = time_diff.total_seconds() / 86400.0  # 转换为天
        
        # 防止除以零，并给予基础权重
        score = (node.cross_domain_hits + 1) / (days_inactive + 1)
        
        logger.debug(f"Node {node.id} - Score: {score:.4f} (Hits: {node.cross_domain_hits}, Inactive: {days_inactive:.1f} days)")
        return score

    def _find_fusion_target(self, node: KnowledgeNode, all_nodes: List[KnowledgeNode]) -> Optional[KnowledgeNode]:
        """
        辅助函数：寻找合适的融合目标（更高层级的抽象节点）
        
        简单策略：寻找同源或内容相似且抽象层级更高的节点。
        在实际AGI系统中，这里会使用向量相似度匹配。
        
        Args:
            node: 待融合的低活度节点
            all_nodes: 全局节点列表
            
        Returns:
            Optional[KnowledgeNode]: 目标节点，如果找不到则返回None
        """
        # 模拟逻辑：寻找抽象层级比当前节点高1-2级的节点
        candidates = [
            n for n in all_nodes 
            if n.abstraction_level > node.abstraction_level 
            and n.id != node.id
        ]
        
        if not candidates:
            return None
            
        # 简单选择：返回层级最高的候选者（实际应用中应基于语义相似度）
        return max(candidates, key=lambda x: x.abstraction_level)

    def execute_dehydration(self, nodes: List[KnowledgeNode]) -> Tuple[List[KnowledgeNode], List[DehydrationResult]]:
        """
        核心函数2：执行脱水流程
        
        遍历所有节点，根据活度得分和层级决定是归档、融合还是保留。
        
        Args:
            nodes: 待处理的知识节点列表
            
        Returns:
            Tuple[List[KnowledgeNode], List[DehydrationResult]]: 
                - 保留在热数据层的节点列表
                - 脱水操作结果列表
        """
        current_time = datetime.now()
        active_nodes: List[KnowledgeNode] = []
        results: List[DehydrationResult] = []
        
        logger.info(f"Starting dehydration process for {len(nodes)} nodes...")
        
        for node in nodes:
            try:
                # 1. 数据验证
                if not self._validate_node(node):
                    continue
                    
                # 2. 计算活度
                score = self._calculate_activity_score(node, current_time)
                
                # 3. 决策逻辑
                is_inactive = (current_time - node.last_accessed) > self.inactivity_threshold
                is_low_value = node.cross_domain_hits < self.min_cross_domain_hits
                
                action = DehydrationAction.KEEP
                target_id = None
                
                if is_inactive and is_low_value:
                    # 策略分支：低层级节点尝试融合，高层级节点直接归档
                    if node.abstraction_level < 5:
                        fusion_target = self._find_fusion_target(node, nodes)
                        if fusion_target:
                            action = DehydrationAction.FUSE
                            target_id = fusion_target.id
                            logger.info(f"Fusing node {node.id} into {target_id}")
                        else:
                            action = DehydrationAction.ARCHIVE
                            logger.info(f"Archiving node {node.id} (no fusion target)")
                    else:
                        action = DehydrationAction.ARCHIVE
                        logger.info(f"Archiving high-level node {node.id}")
                
                # 4. 执行动作
                if action == DehydrationAction.KEEP:
                    active_nodes.append(node)
                else:
                    result = DehydrationResult(
                        node_id=node.id,
                        action=action,
                        target_id=target_id,
                        space_saved=node.size_mb
                    )
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Error processing node {node.id}: {e}")
                # 发生错误时保守处理，保留节点
                active_nodes.append(node)
                
        total_saved = sum(r.space_saved for r in results)
        logger.info(f"Dehydration complete. Kept: {len(active_nodes)}, Processed: {len(results)}. Saved: {total_saved:.2f} MB")
        
        return active_nodes, results


# 使用示例
if __name__ == "__main__":
    # 构造模拟数据
    now = datetime.now()
    
    test_nodes = [
        # 1. 高活度节点：最近访问，跨域碰撞多 -> 应保留
        KnowledgeNode(
            id="node_001", content="Active Concept", 
            last_accessed=now - timedelta(days=1), 
            cross_domain_hits=50, abstraction_level=3, size_mb=2.0
        ),
        # 2. 低活度低层级节点：很久未访问，无碰撞，层级低 -> 应融合
        KnowledgeNode(
            id="node_002", content="Obsolete Detail", 
            last_accessed=now - timedelta(days=100), 
            cross_domain_hits=0, abstraction_level=1, size_mb=0.5
        ),
        # 3. 低活度高层级节点：很久未访问，无碰撞，层级高 -> 应归档
        KnowledgeNode(
            id="node_003", content="Old Theory", 
            last_accessed=now - timedelta(days=200), 
            cross_domain_hits=0, abstraction_level=8, size_mb=5.0
        ),
        # 4. 边界情况：刚好在阈值边缘 -> 应保留
        KnowledgeNode(
            id="node_004", content="Borderline", 
            last_accessed=now - timedelta(days=89), 
            cross_domain_hits=1, abstraction_level=2, size_mb=1.0
        )
    ]
    
    # 实例化并运行
    dehydrator = ConceptDehydrator(inactivity_threshold_days=90)
    remaining_nodes, actions = dehydrator.execute_dehydration(test_nodes)
    
    # 打印结果
    print("\n--- Dehydration Report ---")
    for res in actions:
        print(f"Node: {res.node_id} | Action: {res.action.value} | Target: {res.target_id} | Saved: {res.space_saved}MB")
        
    print("\n--- Remaining Active Nodes ---")
    for node in remaining_nodes:
        print(f"Node: {node.id} | Content: {node.content}")