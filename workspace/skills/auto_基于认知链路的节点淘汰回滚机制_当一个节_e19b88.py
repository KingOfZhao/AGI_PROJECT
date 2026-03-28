"""
Module: cognitive_node_decommission_protocol.py
Description: 基于认知链路的节点淘汰回滚机制。
             Implements a rollback-compliant decommissioning protocol for cognitive nodes.
             It ensures that marking a node as 'pending elimination' triggers a dependency analysis,
             identifies affected high-level cognitive nodes, and executes a 'soft elimination'
             process (quarantine) before permanent removal.
Domain: system_safety
Author: Senior Python Engineer (AGI Systems)
"""

import logging
from enum import Enum, auto
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """节点状态枚举类"""
    ACTIVE = auto()
    PENDING_ELIMINATION = auto()
    QUARANTINED = auto()  # 隔离区状态 (软淘汰)
    ELIMINATED = auto()
    ERROR = auto()

class NodeType(Enum):
    """节点类型枚举"""
    PERCEPTION = "perception"       # 感知层
    MEMORY = "memory"              # 记忆层
    REASONING = "reasoning"        # 推理层 (高级认知节点)
    EXECUTION = "execution"        # 执行层

@dataclass
class CognitiveNode:
    """认知节点数据结构"""
    node_id: str
    name: str
    node_type: NodeType
    status: NodeStatus = NodeStatus.ACTIVE
    upstream_nodes: Set[str] = field(default_factory=set)   # 依赖的上游节点
    downstream_nodes: Set[str] = field(default_factory=set) # 被哪些节点依赖
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)

class CognitiveDependencyGraph:
    """
    认知依赖图管理器。
    维护节点间的关系，并执行淘汰逻辑。
    """

    def __init__(self):
        self.nodes: Dict[str, CognitiveNode] = {}
        self.quarantine_monitor: Dict[str, int] = {} # 记录隔离期间的错误计数

    def add_node(self, node: CognitiveNode) -> None:
        """添加节点到图中"""
        if not node.node_id or not node.name:
            raise ValueError("Node ID and Name cannot be empty.")
        self.nodes[node.node_id] = node
        logger.info(f"Node added: {node.node_id} ({node.node_type.value})")

    def link_nodes(self, upstream_id: str, downstream_id: str) -> None:
        """建立节点间的依赖关系 (Downstream depends on Upstream)"""
        if upstream_id not in self.nodes or downstream_id not in self.nodes:
            raise ValueError("Both nodes must exist to create a link.")
        
        # 下游节点记录上游依赖
        self.nodes[downstream_id].upstream_nodes.add(upstream_id)
        # 上游节点记录被谁依赖
        self.nodes[upstream_id].downstream_nodes.add(downstream_id)
        logger.info(f"Dependency created: {downstream_id} -> depends on -> {upstream_id}")

    def _identify_affected_high_level_nodes(self, start_node_id: str) -> List[CognitiveNode]:
        """
        [核心函数 1]
        分析依赖树，识别因节点失效而受影响的高级认知节点。
        
        Args:
            start_node_id: 被标记为淘汰的起始节点ID。
            
        Returns:
            受影响的高级节点列表（通常是Reasoning或Execution层）。
        """
        if start_node_id not in self.nodes:
            logger.error(f"Node {start_node_id} not found.")
            return []

        affected_nodes: Set[str] = set()
        visited: Set[str] = set()
        # BFS遍历下游节点（寻找谁依赖了它）
        queue = list(self.nodes[start_node_id].downstream_nodes)

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            
            visited.add(current_id)
            current_node = self.nodes.get(current_id)
            
            if current_node:
                # 如果是高级认知节点（此处定义为Reasoning或以上），加入结果
                if current_node.node_type in [NodeType.REASONING, NodeType.EXECUTION]:
                    affected_nodes.add(current_id)
                
                # 继续向上游查找（传递性：如果A依赖B，B依赖C，C失效会导致A失效）
                # 继续向下游传播（Correction: 依赖是 Downstream -> Upstream。如果 Upstream 失效，
                # Downstream 失效。如果 Downstream 是一个中间节点，我们需要继续检查谁依赖这个 Downstream）。
                queue.extend(current_node.downstream_nodes)

        result = [self.nodes[nid] for nid in affected_nodes if nid in self.nodes]
        logger.info(f"Impact analysis for {start_node_id}: Found {len(result)} high-level affected nodes.")
        return result

    def initiate_soft_elimination(self, node_id: str, check_dependencies: bool = True) -> bool:
        """
        [核心函数 2]
        启动软淘汰流程（进入隔离区）。
        这将暂时切断节点服务，但保留数据以供回滚。
        
        Args:
            node_id: 待淘汰节点ID。
            check_dependencies: 是否进行依赖检查。
            
        Returns:
            操作是否成功启动。
        """
        if node_id not in self.nodes:
            logger.error(f"Elimination failed: Node {node_id} does not exist.")
            return False

        node = self.nodes[node_id]
        
        # 数据验证：确保节点当前是Active的
        if node.status != NodeStatus.ACTIVE:
            logger.warning(f"Node {node_id} is already in state {node.status.name}, cannot initiate soft elimination.")
            return False

        # 1. 识别影响范围
        if check_dependencies:
            affected = self._identify_affected_high_level_nodes(node_id)
            if affected:
                logger.warning(
                    f"CRITICAL ALERT: Eliminating {node_id} will invalidate the following high-level nodes: "
                    f"{[n.name for n in affected]}"
                )
                # 在实际AGI系统中，这里可能会触发一个确认机制或自动补偿机制

        # 2. 进入隔离状态
        node.status = NodeStatus.QUARANTINED
        self.quarantine_monitor[node_id] = 0 # 重置错误计数器
        logger.info(f"Node {node_id} has entered QUARANTINE state. Monitoring for system stability...")
        
        return True

    def monitor_quarantine_health(self, node_id: str, error_triggered: bool = False) -> str:
        """
        [辅助函数]
        监控隔离区节点的系统反应。
        
        Args:
            node_id: 处于隔离区的节点ID。
            error_triggered: 模拟外部系统是否报告了因该节点缺失导致的错误。
            
        Returns:
            当前决策建议: 'ROLLBACK', 'SAFE_TO_DELETE', 'MONITORING'
        """
        if node_id not in self.quarantine_monitor:
            return "NOT_IN_QUARANTINE"

        if error_triggered:
            self.quarantine_monitor[node_id] += 1
            logger.warning(f"Error detected related to quarantined node {node_id}. Error count: {self.quarantine_monitor[node_id]}")
            
            # 阈值检查：如果错误超过3次，立即回滚
            if self.quarantine_monitor[node_id] >= 3:
                self._rollback_node(node_id)
                return "ROLLBACK"
        
        # 模拟时间窗口逻辑（这里简化处理，实际应结合时间戳）
        # 如果一切正常，返回监控中
        return "MONITORING"

    def _rollback_node(self, node_id: str) -> None:
        """内部方法：执行回滚操作"""
        if node_id in self.nodes:
            self.nodes[node_id].status = NodeStatus.ACTIVE
            del self.quarantine_monitor[node_id]
            logger.info(f"ROLLBACK TRIGGERED: Node {node_id} has been restored to ACTIVE state.")
            
    def permanently_delete_node(self, node_id: str) -> bool:
        """彻底删除节点"""
        if node_id not in self.nodes:
            return False
        
        if self.nodes[node_id].status != NodeStatus.QUARANTINED:
            logger.error("Cannot permanently delete a node that is not quarantined.")
            return False

        # 检查是否还有未处理的错误
        if self.quarantine_monitor.get(node_id, 0) > 0:
            logger.warning("Cannot delete node due to recent errors. Recommend rollback.")
            return False

        del self.nodes[node_id]
        del self.quarantine_monitor[node_id]
        logger.info(f"Node {node_id} has been permanently removed from the system.")
        return True

# ============================================================
# Usage Example
# ============================================================
if __name__ == "__main__":
    # 1. 初始化系统
    cog_system = CognitiveDependencyGraph()

    # 2. 创建节点 (模拟一个简单的认知链路)
    # Perception -> Memory -> Reasoning -> Execution
    node_p1 = CognitiveNode("p1", "Visual_Input", NodeType.PERCEPTION)
    node_m1 = CognitiveNode("m1", "Short_Term_Memory", NodeType.MEMORY)
    node_r1 = CognitiveNode("r1", "Threat_Assessment", NodeType.REASONING)
    node_e1 = CognitiveNode("e1", "Evade_Action", NodeType.EXECUTION)

    cog_system.add_node(node_p1)
    cog_system.add_node(node_m1)
    cog_system.add_node(node_r1)
    cog_system.add_node(node_e1)

    # 3. 建立依赖关系 (下游 -> 依赖 -> 上游)
    # e1 depends on r1; r1 depends on m1; m1 depends on p1
    cog_system.link_nodes("p1", "m1") # p1 is upstream of m1
    cog_system.link_nodes("m1", "r1") # m1 is upstream of r1
    cog_system.link_nodes("r1", "e1") # r1 is upstream of e1

    print("\n--- Starting Decommission Test ---")

    # 4. 尝试淘汰底层节点 p1 (Visual_Input)
    # 预期：系统应警告这会影响 Threat_Assessment 和 Evade_Action
    target_node = "p1"
    cog_system.initiate_soft_elimination(target_node)

    # 5. 模拟监控过程
    # 情况 A: 没有报错 (模拟中未调用 error_triggered)
    status = cog_system.monitor_quarantine_health(target_node, error_triggered=False)
    print(f"Current Status Recommendation: {status}")

    # 情况 B: 检测到严重报错 (模拟下游节点调用失败)
    # 假设外部系统报告了错误
    print("\n--- Simulating System Errors ---")
    status = cog_system.monitor_quarantine_health(target_node, error_triggered=True)
    print(f"Status after 1st error: {status}")
    
    status = cog_system.monitor_quarantine_health(target_node, error_triggered=True)
    print(f"Status after 2nd error: {status}")

    # 触发回滚阈值 (3次错误)
    status = cog_system.monitor_quarantine_health(target_node, error_triggered=True)
    print(f"Status after 3rd error: {status}")

    # 6. 验证回滚结果
    if cog_system.nodes[target_node].status == NodeStatus.ACTIVE:
        print(f"SUCCESS: Node {target_node} was successfully rolled back.")
    
    # 7. 尝试安全删除 (此时应该失败，因为状态已回滚为 Active)
    if not cog_system.permanently_delete_node(target_node):
        print("Deletion blocked as expected (Node is Active again).")