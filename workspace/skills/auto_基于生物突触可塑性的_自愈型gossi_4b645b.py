"""
名称: auto_基于生物突触可塑性的_自愈型gossi_4b645b
描述: 基于生物突触可塑性的自愈型Gossip网络模块。
     该模块模拟生物神经网络的赫布学习机制，实现分布式网络拓扑的动态重构。
     通过突触增强（Hebbian Learning）和突触修剪机制，网络能自动识别
     高效链路并隔离故障或恶意节点，从而实现自我进化。
领域: cross_domain
"""

import logging
import random
import time
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BioGossipNetwork")

class PacketStatus(Enum):
    """数据包传输状态枚举"""
    SUCCESS = 1
    FAILURE = 2
    DUPLICATE = 3
    INVALID = 4

@dataclass
class NodeProfile:
    """节点配置文件，包含状态和身份信息"""
    node_id: str
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    reputation: float = 1.0  # 范围 0.0 到 1.0

@dataclass
class SynapseLink:
    """
    突触链路类：表示两个节点之间的连接权重。
    模拟生物突触特性，包含长时程增强(LTP)和长时程抑制(LTD)。
    """
    target_node_id: str
    weight: float = 0.5  # 范围 0.0 (断裂) 到 1.0 (强连接)
    last_transmission_time: float = field(default_factory=time.time)
    success_count: int = 0
    failure_count: int = 0
    
    # 生物参数
    DECAY_RATE = 0.05  # 突触衰减率
    LTP_FACTOR = 0.1   # 长时程增强因子
    LTD_FACTOR = 0.15  # 长时程抑制因子
    PRUNING_THRESHOLD = 0.1  # 修剪阈值，低于此值断开连接

class BioGossipNode:
    """
    基于生物突触可塑性的自愈型Gossip节点。
    
    功能特性：
    1. 赫布学习：成功交互的链路权重增加。
    2. 突触修剪：长期无用或错误率高的链路被移除。
    3. 自愈路由：根据权重概率选择下一跳，自动绕过故障节点。
    
    Example:
        >>> node_a = BioGossipNode("Node-A")
        >>> node_b = BioGossipNode("Node-B")
        >>> node_a.add_peer("Node-B")
        >>> # 模拟成功交互
        >>> node_a.update_synapse_plasticity("Node-B", PacketStatus.SUCCESS)
        >>> msg_id = node_a.generate_message_id("Hello AGI")
        >>> node_a.gossip_propagate(msg_id, "Hello AGI")
    """
    
    def __init__(self, node_id: str, max_peers: int = 20):
        """
        初始化节点。
        
        Args:
            node_id (str): 节点的唯一标识符。
            max_peers (int): 最大连接数，防止资源耗尽。
        """
        self.node_id = node_id
        self.max_peers = max_peers
        self.peers: Dict[str, SynapseLink] = {}
        self.received_messages: Set[str] = set()  # 消息去重缓存
        self.known_nodes: Dict[str, NodeProfile] = {}  # 网络拓扑认知
        
        logger.info(f"BioGossipNode [{self.node_id}] initialized.")

    def _validate_peer_existence(self, peer_id: str) -> bool:
        """辅助函数：检查节点是否存在"""
        return peer_id in self.peers

    def add_peer(self, peer_id: str) -> bool:
        """
        添加一个新的对等节点连接（突触生成）。
        
        Args:
            peer_id (str): 对端节点ID。
            
        Returns:
            bool: 是否成功添加。
        """
        if len(self.peers) >= self.max_peers:
            logger.warning(f"Node {self.node_id}: Max peers limit reached.")
            return False
        
        if not self._validate_peer_existence(peer_id):
            self.peers[peer_id] = SynapseLink(target_node_id=peer_id)
            self.known_nodes[peer_id] = NodeProfile(node_id=peer_id)
            logger.debug(f"Node {self.node_id}: New synapse formed with {peer_id}")
            return True
        return False

    def update_synapse_plasticity(self, peer_id: str, status: PacketStatus) -> None:
        """
        核心函数：根据传输结果更新突触权重（赫布学习/修剪）。
        
        逻辑：
        - SUCCESS: 增加权重，强化链路。
        - FAILURE/INVALID: 降低权重，惩罚链路。
        - 定期检查权重是否低于阈值以进行修剪。
        
        Args:
            peer_id (str): 目标节点ID。
            status (PacketStatus): 传输结果状态。
        """
        if not self._validate_peer_existence(peer_id):
            return

        link = self.peers[peer_id]
        current_time = time.time()
        
        # 基础衰减（模拟遗忘）
        time_delta = current_time - link.last_transmission_time
        link.weight = max(0.0, link.weight - (SynapseLink.DECAY_RATE * time_delta / 60.0))

        if status == PacketStatus.SUCCESS:
            # Long-Term Potentiation (LTP)
            link.weight = min(1.0, link.weight + SynapseLink.LTP_FACTOR)
            link.success_count += 1
            self.known_nodes[peer_id].reputation = min(1.0, self.known_nodes[peer_id].reputation + 0.05)
        elif status in [PacketStatus.FAILURE, PacketStatus.INVALID]:
            # Long-Term Depression (LTD)
            link.weight = max(0.0, link.weight - SynapseLink.LTD_FACTOR)
            link.failure_count += 1
            self.known_nodes[peer_id].reputation = max(0.0, self.known_nodes[peer_id].reputation - 0.1)
        
        link.last_transmission_time = current_time
        self._prune_synapse(peer_id)

    def _prune_synapse(self, peer_id: str) -> None:
        """
        内部函数：突触修剪。如果权重过低，移除连接。
        """
        link = self.peers[peer_id]
        if link.weight < SynapseLink.PRUNING_THRESHOLD:
            logger.warning(f"Node {self.node_id}: Pruning weak synapse to {peer_id} (Weight: {link.weight:.2f})")
            del self.peers[peer_id]
            # 保留节点档案作为记忆，但降低其全局评分
            if peer_id in self.known_nodes:
                self.known_nodes[peer_id].reputation *= 0.5

    def gossip_propagate(self, message_id: str, data: Any, fanout: int = 3) -> List[str]:
        """
        核心函数：基于权重的概率性广播。
        
        不再随机选择节点，而是根据突触权重进行轮盘赌选择，
        优先选择高权重（高可靠性）的链路。
        
        Args:
            message_id (str): 消息唯一哈希，用于去重。
            data (Any): 传输的数据负载。
            fanout (int): 每次传播的目标数量。
            
        Returns:
            List[str]: 被选中的目标节点ID列表。
        """
        if message_id in self.received_messages:
            logger.debug(f"Message {message_id} already seen. Dropping.")
            return []
        
        self.received_messages.add(message_id)
        
        if not self.peers:
            return []

        # 基于权重的概率选择
        targets = self._select_targets_by_weight(fanout)
        
        # 模拟发送逻辑 (实际应用中这里会是网络IO)
        # 在这里我们只是记录日志并返回目标，实际的数据传输逻辑应由上层调用者处理
        logger.info(f"Node {self.node_id} propagating {message_id} to targets: {targets}")
        
        return targets

    def _select_targets_by_weight(self, k: int) -> List[str]:
        """
        辅助函数：根据突触权重进行轮盘赌选择。
        
        Args:
            k (int): 需要选择的节点数量。
            
        Returns:
            List[str]: 选中的节点ID列表。
        """
        candidates = list(self.peers.keys())
        if not candidates:
            return []
            
        weights = [self.peers[cid].weight for cid in candidates]
        total_weight = sum(weights)
        
        if total_weight == 0:
            # 如果所有权重都归零，退化到随机选择以保持连通性
            return random.sample(candidates, min(k, len(candidates)))
            
        # 归一化权重
        norm_weights = [w / total_weight for w in weights]
        
        selected = []
        available_indices = list(range(len(candidates)))
        
        while len(selected) < k and available_indices:
            # 加权随机选择
            r = random.random()
            upto = 0
            selected_idx = -1
            
            # 构建当前剩余候选项的权重分布
            current_weights = [norm_weights[i] for i in available_indices]
            current_sum = sum(current_weights)
            if current_sum == 0: break
            current_norm = [w / current_sum for w in current_weights]

            for i, idx in enumerate(available_indices):
                if upto + current_norm[i] >= r:
                    selected_idx = idx
                    break
                upto += current_norm[i]
            else:
                # 浮点数精度问题兜底
                selected_idx = available_indices[-1]

            if selected_idx != -1:
                selected.append(candidates[selected_idx])
                # 从候选项中移除已选，避免重复
                available_indices.remove(selected_idx)
                
        return selected

    @staticmethod
    def generate_message_id(content: str) -> str:
        """生成唯一的消息ID"""
        return hashlib.sha256(f"{time.time()}-{content}".encode()).hexdigest()[:16]

# 模拟网络环境运行示例
if __name__ == "__main__":
    # 1. 初始化网络节点
    node_alpha = BioGossipNode("Alpha")
    node_beta = BioGossipNode("Beta")
    node_gamma = BioGossipNode("Gamma")
    
    # 2. 建立连接 (突触生成)
    node_alpha.add_peer("Beta")
    node_alpha.add_peer("Gamma")
    
    # 3. 模拟网络交互与学习
    print("\n--- Simulating Network Traffic ---")
    
    # 场景 A: Alpha 与 Beta 交互顺畅
    for _ in range(5):
        node_alpha.update_synapse_plasticity("Beta", PacketStatus.SUCCESS)
        
    # 场景 B: Alpha 与 Gamma 交互糟糕 (丢包/恶意)
    for _ in range(3):
        node_alpha.update_synapse_plasticity("Gamma", PacketStatus.FAILURE)
        
    # 4. 检查突触权重
    print(f"Alpha -> Beta Weight: {node_alpha.peers['Beta'].weight:.2f} (Strong)")
    print(f"Alpha -> Gamma Weight: {node_alpha.peers['Gamma'].weight:.2f} (Weak/Depressed)")
    
    # 5. 触发修剪 (如果权重过低)
    # 继续惩罚 Gamma 直到断开
    print("\n--- Forcing Pruning of Gamma ---")
    node_alpha.update_synapse_plasticity("Gamma", PacketStatus.FAILURE)
    node_alpha.update_synapse_plasticity("Gamma", PacketStatus.FAILURE)
    
    # 检查 Gamma 是否还在列表中
    if "Gamma" not in node_alpha.peers:
        print("Result: Gamma has been pruned from Alpha's network view.")
    
    # 6. 模拟 Gossip 传播
    print("\n--- Propagating Message ---")
    msg_id = BioGossipNode.generate_message_id("Critical Data")
    # 此时 Alpha 应该只传播给 Beta (如果 Gamma 被修剪了)
    targets = node_alpha.gossip_propagate(msg_id, "Critical Data", fanout=2)
    print(f"Message sent to: {targets}")