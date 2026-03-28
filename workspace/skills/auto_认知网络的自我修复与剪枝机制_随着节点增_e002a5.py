"""
高级认知网络自我修复与剪枝系统
名称: auto_认知网络的自我修复与剪枝机制_随着节点增_e002a5
描述: 实现认知网络的免疫系统，通过证伪条件和矛盾检测进行节点修剪
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CognitiveNetworkRepair")


class NodeStatus(Enum):
    """认知节点状态枚举"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"
    DEAD = "dead"


@dataclass
class CognitiveNode:
    """认知网络节点数据结构"""
    node_id: str
    content: str
    creation_time: datetime
    last_validated: datetime
    falsification_conditions: Dict[str, Any]
    confidence: float
    status: NodeStatus
    dependencies: Set[str]
    mutual_exclusions: Set[str]

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "creation_time": self.creation_time.isoformat(),
            "last_validated": self.last_validated.isoformat(),
            "falsification_conditions": self.falsification_conditions,
            "confidence": self.confidence,
            "status": self.status.value,
            "dependencies": list(self.dependencies),
            "mutual_exclusions": list(self.mutual_exclusions)
        }


class CognitiveNetwork:
    """认知网络核心类，实现自我修复与剪枝机制"""

    def __init__(self):
        """初始化认知网络"""
        self.nodes: Dict[str, CognitiveNode] = {}
        self.prune_history: List[Dict[str, Any]] = []
        logger.info("Cognitive network initialized")

    def add_node(self, node: CognitiveNode) -> bool:
        """
        添加新节点到认知网络
        
        参数:
            node: 要添加的认知节点
            
        返回:
            bool: 是否添加成功
        """
        if not isinstance(node, CognitiveNode):
            logger.error("Invalid node type provided")
            return False
            
        if node.node_id in self.nodes:
            logger.warning(f"Node {node.node_id} already exists, updating instead")
            
        self.nodes[node.node_id] = node
        logger.info(f"Node {node.node_id} added to network")
        return True

    def validate_node(self, node_id: str, 
                     current_evidence: Dict[str, Any]) -> Optional[NodeStatus]:
        """
        验证单个节点是否仍然有效
        
        参数:
            node_id: 要验证的节点ID
            current_evidence: 当前证据数据
            
        返回:
            NodeStatus: 节点更新后的状态，None表示验证失败
        """
        if node_id not in self.nodes:
            logger.error(f"Node {node_id} not found in network")
            return None
            
        node = self.nodes[node_id]
        falsification = node.falsification_conditions
        
        # 检查证伪条件
        for condition, threshold in falsification.items():
            if condition in current_evidence:
                if isinstance(threshold, (int, float)) and current_evidence[condition] > threshold:
                    node.status = NodeStatus.DEAD
                    logger.info(f"Node {node_id} marked DEAD due to condition {condition}")
                    return NodeStatus.DEAD
                    
                if isinstance(threshold, str) and current_evidence[condition] == threshold:
                    node.status = NodeStatus.DEAD
                    logger.info(f"Node {node_id} marked DEAD due to condition {condition}")
                    return NodeStatus.DEAD
        
        # 更新验证时间
        node.last_validated = datetime.now()
        return node.status

    def detect_mutual_exclusions(self) -> List[Tuple[str, str]]:
        """
        检测网络中的互斥节点对
        
        返回:
            List[Tuple[str, str]]: 互斥节点对列表
        """
        mutual_pairs = []
        
        for node_id, node in self.nodes.items():
            for other_id in node.mutual_exclusions:
                if other_id in self.nodes and other_id > node_id:  # 避免重复记录
                    mutual_pairs.append((node_id, other_id))
                    logger.debug(f"Found mutual exclusion between {node_id} and {other_id}")
        
        return mutual_pairs

    def resolve_conflict(self, node_a: str, node_b: str, 
                        evidence: Dict[str, Any]) -> Optional[str]:
        """
        解决两个互斥节点之间的冲突
        
        参数:
            node_a: 第一个节点ID
            node_b: 第二个节点ID
            evidence: 用于解决冲突的证据数据
            
        返回:
            str: 被标记为DEAD的节点ID，None表示无法解决
        """
        if node_a not in self.nodes or node_b not in self.nodes:
            logger.error("One or both nodes not found in network")
            return None
            
        node_a_obj = self.nodes[node_a]
        node_b_obj = self.nodes[node_b]
        
        # 检查是否有节点已被证伪
        if node_a_obj.status == NodeStatus.DEAD:
            return node_a
        if node_b_obj.status == NodeStatus.DEAD:
            return node_b
            
        # 比较置信度和证据支持
        a_score = node_a_obj.confidence * evidence.get("support_" + node_a, 1.0)
        b_score = node_b_obj.confidence * evidence.get("support_" + node_b, 1.0)
        
        if a_score < b_score:
            node_a_obj.status = NodeStatus.DEAD
            logger.info(f"Conflict resolved: {node_a} marked DEAD in favor of {node_b}")
            return node_a
        elif b_score < a_score:
            node_b_obj.status = NodeStatus.DEAD
            logger.info(f"Conflict resolved: {node_b} marked DEAD in favor of {node_a}")
            return node_b
        else:
            logger.warning(f"Unable to resolve conflict between {node_a} and {node_b}")
            return None

    def prune_network(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行网络剪枝操作
        
        参数:
            evidence: 当前证据数据
            
        返回:
            Dict: 剪枝操作结果摘要
        """
        if not evidence:
            logger.error("No evidence provided for pruning")
            return {"error": "No evidence provided"}
            
        result = {
            "nodes_checked": 0,
            "nodes_deprecated": 0,
            "conflicts_resolved": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 1. 验证所有节点
        for node_id in list(self.nodes.keys()):
            self.validate_node(node_id, evidence)
            result["nodes_checked"] += 1
            
            if self.nodes[node_id].status == NodeStatus.DEAD:
                result["nodes_deprecated"] += 1
        
        # 2. 检测并解决冲突
        mutual_pairs = self.detect_mutual_exclusions()
        for pair in mutual_pairs:
            dead_node = self.resolve_conflict(pair[0], pair[1], evidence)
            if dead_node:
                result["conflicts_resolved"] += 1
        
        # 3. 记录剪枝历史
        self.prune_history.append(result)
        
        logger.info(f"Pruning complete: {result['nodes_deprecated']} nodes deprecated, "
                   f"{result['conflicts_resolved']} conflicts resolved")
        return result

    def get_network_status(self) -> Dict[str, Any]:
        """
        获取网络当前状态摘要
        
        返回:
            Dict: 网络状态摘要
        """
        active_nodes = sum(1 for node in self.nodes.values() if node.status == NodeStatus.ACTIVE)
        dead_nodes = sum(1 for node in self.nodes.values() if node.status == NodeStatus.DEAD)
        
        return {
            "total_nodes": len(self.nodes),
            "active_nodes": active_nodes,
            "dead_nodes": dead_nodes,
            "last_prune": self.prune_history[-1] if self.prune_history else None
        }

    def export_network(self, file_path: str) -> bool:
        """
        导出网络数据到文件
        
        参数:
            file_path: 目标文件路径
            
        返回:
            bool: 是否导出成功
        """
        try:
            data = {
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "prune_history": self.prune_history
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Network exported to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export network: {str(e)}")
            return False


# 使用示例
if __name__ == "__main__":
    # 创建认知网络实例
    network = CognitiveNetwork()
    
    # 添加几个示例节点
    geocentric = CognitiveNode(
        node_id="geocentric_model",
        content="The Earth is at the center of the universe",
        creation_time=datetime(2020, 1, 1),
        last_validated=datetime(2023, 1, 1),
        falsification_conditions={"stellar_parallax": True},
        confidence=0.3,
        status=NodeStatus.ACTIVE,
        dependencies=set(),
        mutual_exclusions={"heliocentric_model"}
    )
    
    heliocentric = CognitiveNode(
        node_id="heliocentric_model",
        content="The Sun is at the center of the solar system",
        creation_time=datetime(2020, 1, 1),
        last_validated=datetime(2023, 1, 1),
        falsification_conditions={"solar_parallax": False},
        confidence=0.9,
        status=NodeStatus.ACTIVE,
        dependencies=set(),
        mutual_exclusions={"geocentric_model"}
    )
    
    network.add_node(geocentric)
    network.add_node(heliocentric)
    
    # 使用证据进行剪枝
    evidence = {
        "stellar_parallax": True,  # 证伪地心说的证据
        "support_heliocentric_model": 1.2,
        "support_geocentric_model": 0.8
    }
    
    prune_result = network.prune_network(evidence)
    print("Pruning results:", prune_result)
    
    # 检查网络状态
    status = network.get_network_status()
    print("Network status:", status)
    
    # 导出网络数据
    network.export_network("cognitive_network_export.json")