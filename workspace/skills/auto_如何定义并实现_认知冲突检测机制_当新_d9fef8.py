"""
Module: cognitive_conflict_resolver.py
Description: 实现AGI系统中的认知冲突检测与信念修正机制。
             基于认知一致性原则和可证伪性逻辑，处理新旧节点间的逻辑矛盾。

Author: Senior Python Engineer
Version: 1.0.0
License: MIT
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConflictResolutionStrategy(Enum):
    """定义解决认知冲突的策略枚举"""
    KEEP_OLD = "KEEP_OLD"               # 抛弃新节点，保持旧节点
    ADOPT_NEW = "ADOPT_NEW"             # 修正旧节点，采纳新节点
    PARALLEL_BRANCH = "PARALLEL_BRANCH" # 创建并行分支，两者共存
    UNDECIDED = "UNDECIDED"             # 信息不足，暂不处理

@dataclass
class CognitiveNode:
    """
    认知节点数据结构。
    
    Attributes:
        id (str): 节点唯一标识符
        content (str): 节点内容描述
        truth_value (float): 真值 (0.0 到 1.0)
        evidence_weight (float): 证据权重/支持度 (0.0 到 1.0)，用于可证伪性计算
        is_axiom (bool): 是否为公理（公理性节点通常不可推翻）
        created_at (datetime): 创建时间
    """
    id: str
    content: str
    truth_value: float
    evidence_weight: float
    is_axiom: bool = False
    created_at: datetime = datetime.now()

class CognitiveConflictDetector:
    """
    认知冲突检测与解决器。
    
    负责检测新旧节点间的逻辑矛盾，并基于证据权重和可证伪性原则决定信念修正策略。
    """

    def __init__(self, falsifiability_threshold: float = 0.7, conflict_tolerance: float = 0.1):
        """
        初始化检测器。
        
        Args:
            falsifiability_threshold (float): 可证伪性阈值，用于判断证据强度。
            conflict_tolerance (float): 逻辑真值差异容忍度，低于此值不视为冲突。
        """
        if not (0.0 <= falsifiability_threshold <= 1.0):
            raise ValueError("falsifiability_threshold must be between 0.0 and 1.0")
        if not (0.0 <= conflict_tolerance <= 1.0):
            raise ValueError("conflict_tolerance must be between 0.0 and 1.0")
            
        self.falsifiability_threshold = falsifiability_threshold
        self.conflict_tolerance = conflict_tolerance
        self._node_registry: Dict[str, CognitiveNode] = {}
        logger.info("CognitiveConflictDetector initialized with threshold %.2f", falsifiability_threshold)

    def _validate_node(self, node: CognitiveNode) -> None:
        """
        辅助函数：验证节点数据的有效性。
        
        Args:
            node (CognitiveNode): 待验证的节点
            
        Raises:
            ValueError: 如果数据无效
        """
        if not node.id:
            raise ValueError("Node ID cannot be empty")
        if not (0.0 <= node.truth_value <= 1.0):
            raise ValueError(f"Truth value must be between 0.0 and 1.0, got {node.truth_value}")
        if not (0.0 <= node.evidence_weight <= 1.0):
            raise ValueError(f"Evidence weight must be between 0.0 and 1.0, got {node.evidence_weight}")

    def _calculate_conflict_intensity(self, val1: float, val2: float) -> float:
        """
        辅助函数：计算两个真值之间的冲突强度。
        使用简单的绝对差值作为冲突度量。
        
        Args:
            val1 (float): 节点1的真值
            val2 (float): 节点2的真值
            
        Returns:
            float: 冲突强度 (0.0 到 1.0)
        """
        return abs(val1 - val2)

    def register_node(self, node: CognitiveNode) -> None:
        """
        注册节点到认知库。
        
        Args:
            node (CognitiveNode): 待注册的节点
        """
        try:
            self._validate_node(node)
            self._node_registry[node.id] = node
            logger.debug(f"Node {node.id} registered successfully.")
        except ValueError as e:
            logger.error(f"Failed to register node {node.id}: {e}")
            raise

    def detect_and_resolve(self, new_node: CognitiveNode, existing_node_id: str) -> Tuple[ConflictResolutionStrategy, Dict[str, Any]]:
        """
        核心函数：检测新节点与现有权威节点之间的冲突，并决定解决策略。
        
        逻辑流程：
        1. 检查是否存在直接逻辑矛盾（真值差异是否超过容忍度）。
        2. 如果存在冲突，比较两者的证据权重（可证伪性）。
        3. 如果新节点证据权重大于阈值且远高于旧节点 -> 修正旧节点 (ADOPT_NEW)。
        4. 如果旧节点是公理或新节点证据不足 -> 抛弃新节点 (KEEP_OLD)。
        5. 如果两者证据相当且冲突剧烈 -> 创建并行分支 (PARALLEL_BRANCH)。
        
        Args:
            new_node (CognitiveNode): 新归纳的节点
            existing_node_id (str): 现有节点的ID
            
        Returns:
            Tuple[ConflictResolutionStrategy, Dict]: 包含解决策略和详细冲突报告的元组
            
        Raises:
            KeyError: 如果现有节点ID不存在
        """
        self._validate_node(new_node)
        
        if existing_node_id not in self._node_registry:
            logger.error(f"Existing node ID {existing_node_id} not found.")
            raise KeyError(f"Node {existing_node_id} not found in registry")
            
        old_node = self._node_registry[existing_node_id]
        
        # 1. 量化冲突
        conflict_intensity = self._calculate_conflict_intensity(new_node.truth_value, old_node.truth_value)
        
        report = {
            "new_node_id": new_node.id,
            "old_node_id": old_node.id,
            "conflict_intensity": conflict_intensity,
            "decision": None,
            "reasoning": ""
        }

        # 2. 检查是否构成需要处理的冲突
        if conflict_intensity <= self.conflict_tolerance:
            report["decision"] = ConflictResolutionStrategy.KEEP_OLD
            report["reasoning"] = "Conflict intensity below tolerance threshold. No action needed."
            logger.info(f"Low conflict ({conflict_intensity:.2f}) between {new_node.id} and {old_node.id}.")
            return ConflictResolutionStrategy.KEEP_OLD, report

        logger.warning(f"Detected significant conflict: {conflict_intensity:.2f} between {new_node.id} and {old_node.id}")

        # 3. 基于可证伪性原则决策
        # 如果旧节点是公理，除非有压倒性的证据，否则不修改（此处简化为绝对不修改）
        if old_node.is_axiom:
            report["decision"] = ConflictResolutionStrategy.KEEP_OLD
            report["reasoning"] = "Existing node is an axiom and cannot be overturned by standard revision."
            return ConflictResolutionStrategy.KEEP_OLD, report

        # 比较证据权重
        # 如果新节点的证据权重显著高于旧节点，并且高于可证伪性阈值
        if (new_node.evidence_weight > old_node.evidence_weight and 
            new_node.evidence_weight >= self.falsifiability_threshold):
            
            report["decision"] = ConflictResolutionStrategy.ADOPT_NEW
            report["reasoning"] = "New node has superior falsifiability evidence."
            # 实际执行修正操作（此处仅模拟更新注册表）
            self._update_belief(new_node, old_node)
            return ConflictResolutionStrategy.ADOPT_NEW, report
            
        # 如果旧节点权重更高，或者新节点证据不足
        elif old_node.evidence_weight >= new_node.evidence_weight:
            report["decision"] = ConflictResolutionStrategy.KEEP_OLD
            report["reasoning"] = "Existing node maintains stronger evidence or new node is weak."
            return ConflictResolutionStrategy.KEEP_OLD, report
            
        # 权重相当，无法简单判定，进入并行认知状态（认知失调）
        else:
            report["decision"] = ConflictResolutionStrategy.PARALLEL_BRANCH
            report["reasoning"] = "Conflicting evidence with similar weights. Creating parallel branch."
            self._create_branch(new_node, old_node)
            return ConflictResolutionStrategy.PARALLEL_BRANCH, report

    def _update_belief(self, new_node: CognitiveNode, old_node: CognitiveNode) -> None:
        """内部方法：执行信念更新逻辑"""
        logger.info(f"REVISING BELIEF: Replacing {old_node.id} with {new_node.id}")
        # 标记旧节点为非激活或删除（简化处理：直接替换）
        old_node.truth_value = new_node.truth_value # 模拟修正内容
        old_node.evidence_weight = new_node.evidence_weight

    def _create_branch(self, new_node: CognitiveNode, old_node: CognitiveNode) -> None:
        """内部方法：执行并行分支逻辑"""
        logger.info(f"PARALLEL BRANCH: Co-existing {old_node.id} and {new_node.id}")
        self.register_node(new_node)

# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 初始化系统
    resolver = CognitiveConflictDetector(falsifiability_threshold=0.6, conflict_tolerance=0.05)

    # 1. 创建一个权威的旧节点（例如：天鹅都是白色的）
    node_old = CognitiveNode(
        id="belief_swan_white",
        content="All swans are white",
        truth_value=1.0,
        evidence_weight=0.9,
        is_axiom=False
    )
    resolver.register_node(node_old)

    # 2. 场景A：弱冲突（新数据偏差小）
    node_weak = CognitiveNode(id="obs_swan_offwhite", content="Swan is slightly gray", truth_value=0.95, evidence_weight=0.5)
    strategy, report = resolver.detect_and_resolve(node_weak, "belief_swan_white")
    print(f"Scenario A Result: {strategy.name} - {report['reasoning']}")

    # 3. 场景B：强冲突，但新数据证据不足（谣言）
    node_rumor = CognitiveNode(id="rumor_swan_blue", content="Swans are blue", truth_value=0.0, evidence_weight=0.1)
    strategy, report = resolver.detect_and_resolve(node_rumor, "belief_swan_white")
    print(f"Scenario B Result: {strategy.name} - {report['reasoning']}")

    # 4. 场景C：强冲突，新数据证据确凿（发现黑天鹅）
    node_strong = CognitiveNode(id="obs_swan_black", content="Found a black swan", truth_value=0.0, evidence_weight=0.95)
    strategy, report = resolver.detect_and_resolve(node_strong, "belief_swan_white")
    print(f"Scenario C Result: {strategy.name} - {report['reasoning']}")
    
    # 5. 场景D：强冲突，证据相当（量子态叠加？）
    node_quantum = CognitiveNode(id="obs_swan_quantum", content="Swan is both colors", truth_value=0.5, evidence_weight=0.9)
    # 重置旧节点权重以便测试
    node_old.evidence_weight = 0.9 
    strategy, report = resolver.detect_and_resolve(node_quantum, "belief_swan_white")
    print(f"Scenario D Result: {strategy.name} - {report['reasoning']}")