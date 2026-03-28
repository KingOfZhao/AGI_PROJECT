"""
模块名称: auto_认知自洽与冲突_当ai构建的_真实节点_b69314
描述: 该模块实现了AGI系统中的认知仲裁机制，用于解决AI构建的“真实节点”网络中的逻辑矛盾。
      核心功能是在“人类实践验证”（实践真理）与“逻辑自洽性”（逻辑完备）之间进行权衡与仲裁。

主要组件:
    - CognitiveNode: 定义认知节点的数据结构。
    - ConflictResolver: 核心冲突解决类，包含仲裁逻辑。

数据格式说明:
    - 输入: 节点列表(List[CognitiveNode])，包含属性如ID、置信度、验证来源等。
    - 输出: 仲裁结果对象(ArbitrationResult)，包含保留的节点、丢弃的节点及决策理由。
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeSource(Enum):
    """节点来源枚举，用于区分真理的依据类型"""
    HUMAN_VERIFIED = 1  # 人类实践验证（高优先级）
    LOGICAL_INFERENCE = 2  # 逻辑推理得出
    HYPOTHETICAL = 3  # 假设性/未验证

@dataclass
class CognitiveNode:
    """
    认知节点数据结构。
    
    Attributes:
        node_id (str): 节点唯一标识符。
        content (str): 节点包含的知识内容或逻辑陈述。
        consistency_score (float): 内部逻辑自洽性得分 (0.0 - 1.0)。
        source (NodeSource): 知识来源。
        connections (Set[str]): 与该节点相连的其他节点ID集合。
    """
    node_id: str
    content: str
    consistency_score: float = 0.5
    source: NodeSource = NodeSource.HYPOTHETICAL
    connections: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """数据验证：确保分数在合理范围内"""
        if not 0.0 <= self.consistency_score <= 1.0:
            logger.error(f"节点 {self.node_id} 一致性得分越界: {self.consistency_score}")
            raise ValueError("consistency_score 必须在 0.0 和 1.0 之间")
        if not isinstance(self.connections, set):
            self.connections = set(self.connections)

@dataclass
class ArbitrationResult:
    """仲裁结果数据结构"""
    retained_nodes: List[CognitiveNode]
    discarded_nodes: List[CognitiveNode]
    resolution_strategy: str
    reason: str

class CognitiveArbitrator:
    """
    认知仲裁器。
    
    负责处理认知图谱中的冲突，权衡“逻辑自洽性”与“人类实践验证”。
    """
    
    def __init__(self, human_practice_weight: float = 0.7, logic_weight: float = 0.3):
        """
        初始化仲裁器。
        
        Args:
            human_practice_weight (float): 人类实践验证的权重，默认0.7。
            logic_weight (float): 逻辑自洽性的权重，默认0.3。
        """
        if not abs((human_practice_weight + logic_weight) - 1.0) < 1e-6:
            logger.warning("权重之和不为1，将自动归一化")
            total = human_practice_weight + logic_weight
            self.human_weight = human_practice_weight / total
            self.logic_weight = logic_weight / total
        else:
            self.human_weight = human_practice_weight
            self.logic_weight = logic_weight
        logger.info(f"仲裁器初始化完成: 人类验证权重={self.human_weight}, 逻辑权重={self.logic_weight}")

    def _calculate_node_value(self, node: CognitiveNode) -> float:
        """
        辅助函数：计算节点的综合保留价值。
        
        综合价值 = (来源因子 * 人类权重) + (一致性得分 * 逻辑权重)
        其中来源因子：HUMAN_VERIFIED=1.0, LOGICAL_INFERENCE=0.6, HYPOTHETICAL=0.2
        
        Args:
            node (CognitiveNode): 待评估节点。
            
        Returns:
            float: 综合价值得分。
        """
        source_factor = 0.0
        if node.source == NodeSource.HUMAN_VERIFIED:
            source_factor = 1.0
        elif node.source == NodeSource.LOGICAL_INFERENCE:
            source_factor = 0.6
        else:
            source_factor = 0.2
            
        value = (source_factor * self.human_weight) + (node.consistency_score * self.logic_weight)
        return value

    def resolve_conflict(self, node_a: CognitiveNode, node_b: CognitiveNode, context: Optional[Dict] = None) -> ArbitrationResult:
        """
        核心函数1：解决两个互斥节点之间的冲突。
        
        决策逻辑：
        1. 计算两个节点的综合价值。
        2. 如果节点被标记为HUMAN_VERIFIED，且与其冲突节点非此类，则拥有绝对否决权（除非逻辑自洽性极低）。
        3. 否则，比较综合价值得分。
        
        Args:
            node_a (CognitiveNode): 冲突节点A。
            node_b (CognitiveNode): 冲突节点B。
            context (Optional[Dict]): 上下文信息，可能影响权重（当前版本暂未深度使用）。
            
        Returns:
            ArbitrationResult: 包含决策结果的详情对象。
        """
        logger.info(f"开始仲裁冲突: '{node_a.node_id}' vs '{node_b.node_id}'")
        
        # 边界检查：是否为同一节点
        if node_a.node_id == node_b.node_id:
            return ArbitrationResult([node_a], [], "Identity", "节点相同，无冲突。")

        # 特殊规则：人类验证节点优先（模拟“实践出真知”）
        # 如果A是人类验证，B不是，且A的一致性不是极低（<0.1），则保留A
        if node_a.source == NodeSource.HUMAN_VERIFIED and node_b.source != NodeSource.HUMAN_VERIFIED:
            if node_a.consistency_score > 0.1:
                return ArbitrationResult(
                    [node_a], [node_b], "HumanPracticePriority",
                    f"节点 {node_a.node_id} 经人类实践验证，优先于逻辑推理节点 {node_b.node_id}"
                )
        
        # 反之亦然
        if node_b.source == NodeSource.HUMAN_VERIFIED and node_a.source != NodeSource.HUMAN_VERIFIED:
            if node_b.consistency_score > 0.1:
                return ArbitrationResult(
                    [node_b], [node_a], "HumanPracticePriority",
                    f"节点 {node_b.node_id} 经人类实践验证，优先于逻辑推理节点 {node_a.node_id}"
                )

        # 常规规则：计算加权价值
        value_a = self._calculate_node_value(node_a)
        value_b = self._calculate_node_value(node_b)
        
        logger.debug(f"节点A价值: {value_a:.4f}, 节点B价值: {value_b:.4f}")

        if value_a >= value_b:
            retained, discarded = node_a, node_b
            reason = f"基于综合评分({value_a:.2f} > {value_b:.2f})，保留节点A。"
        else:
            retained, discarded = node_b, node_a
            reason = f"基于综合评分({value_b:.2f} > {value_a:.2f})，保留节点B。"

        return ArbitrationResult([retained], [discarded], "WeightedValueComparison", reason)

    def network_pruning(self, nodes: List[CognitiveNode], conflict_pairs: List[Tuple[str, str]]) -> List[CognitiveNode]:
        """
        核心函数2：基于冲突对列表对整个节点网络进行剪枝。
        
        Args:
            nodes (List[CognitiveNode]): 当前网络中的所有节点。
            conflict_pairs (List[Tuple[str, str]]): 互斥节点ID对的列表。
            
        Returns:
            List[CognitiveNode]: 经过仲裁后清理过的节点列表。
        """
        if not nodes:
            logger.warning("输入节点列表为空")
            return []
            
        node_map: Dict[str, CognitiveNode] = {n.node_id: n for n in nodes}
        retained_ids: Set[str] = set(node_map.keys())
        
        logger.info(f"开始网络剪枝，共 {len(nodes)} 个节点，{len(conflict_pairs)} 对冲突。")

        for id_a, id_b in conflict_pairs:
            if id_a not in node_map or id_b not in node_map:
                logger.warning(f"跳过无效冲突对: {id_a}, {id_b}")
                continue
                
            # 只有当两个节点目前都还存在于网络中时才进行仲裁
            if id_a in retained_ids and id_b in retained_ids:
                result = self.resolve_conflict(node_map[id_a], node_map[id_b])
                
                for discarded in result.discarded_nodes:
                    retained_ids.discard(discarded.node_id)
                    logger.info(f"移除节点: {discarded.node_id} (原因: {result.resolution_strategy})")

        final_nodes = [node_map[nid] for nid in retained_ids]
        return final_nodes

# 使用示例
if __name__ == "__main__":
    # 1. 创建节点
    node_human = CognitiveNode(
        node_id="earth_round", 
        content="地球是圆的", 
        consistency_score=0.9, 
        source=NodeSource.HUMAN_VERIFIED
    )
    
    node_logic_wrong = CognitiveNode(
        node_id="earth_flat", 
        content="地球是平的（基于局部观察推理）", 
        consistency_score=0.8,  # 内部逻辑可能自洽（局部视角），但违背事实
        source=NodeSource.LOGICAL_INFERENCE
    )
    
    node_logic_abstract = CognitiveNode(
        node_id="pi_equals_3", 
        content="PI等于3（简化模型）", 
        consistency_score=0.5, 
        source=NodeSource.HYPOTHETICAL
    )

    # 2. 初始化仲裁器
    arbitrator = CognitiveArbitrator(human_practice_weight=0.8, logic_weight=0.2)

    # 3. 解决单个冲突
    print("--- 单次冲突仲裁 ---")
    result = arbitrator.resolve_conflict(node_human, node_logic_wrong)
    print(f"策略: {result.resolution_strategy}")
    print(f"保留: {[n.node_id for n in result.retained_nodes]}")
    print(f"理由: {result.reason}")

    # 4. 网络剪枝示例
    print("\n--- 网络剪枝 ---")
    all_nodes = [node_human, node_logic_wrong, node_logic_abstract]
    # 假设 earth_round 与 earth_flat 冲突
    conflicts = [("earth_round", "earth_flat")]
    
    pruned_network = arbitrator.network_pruning(all_nodes, conflicts)
    print(f"剪枝后剩余节点数: {len(pruned_network)}")
    print(f"剩余节点IDs: {[n.node_id for n in pruned_network]}")