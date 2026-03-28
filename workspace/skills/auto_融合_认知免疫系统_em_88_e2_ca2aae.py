"""
Module: auto_融合_认知免疫系统_em_88_e2_ca2aae
Description:
    融合'认知免疫系统'（em_88_E2_7469）、'效用衰减遗忘'（ho_88_O5_5292）与'自适应认知压缩'（ho_88_O2_2164）。
    系统在遭遇对抗样本或逻辑病毒攻击时，不仅能自动隔离受损节点，还能通过'遗忘'低效节点释放资源，
    并动态调整信息密度（压缩接口）来保护用户，从而实现类似生物免疫系统的自我修复和稳态维持。

Domain: cross_domain
Author: Advanced Python Engineer
Version: 1.0.0
"""

import logging
import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NodeState(Enum):
    """节点状态枚举"""
    ACTIVE = "active"
    ISOLATED = "isolated"
    ARCHIVED = "archived"


@dataclass
class CognitiveNode:
    """认知节点数据结构"""
    node_id: str
    data: Dict
    health_score: float = 1.0  # 范围 [0.0, 1.0]
    utility_score: float = 1.0  # 范围 [0.0, 1.0]
    creation_time: float = field(default_factory=time.time)
    last_access_time: float = field(default_factory=time.time)
    state: NodeState = NodeState.ACTIVE
    compression_level: int = 0  # 0: 无压缩, 1-3: 压缩等级

    def update_access(self):
        """更新访问时间"""
        self.last_access_time = time.time()


class CognitiveImmuneSystem:
    """
    认知免疫系统核心类。
    
    融合了免疫隔离、效用衰减遗忘和自适应压缩功能，用于维护AGI系统的认知稳态。
    
    Attributes:
        nodes (Dict[str, CognitiveNode]): 节点存储字典
        health_threshold (float): 健康度阈值，低于此值触发隔离
        utility_threshold (float): 效用阈值，低于此值触发遗忘
        max_compression_level (int): 最大压缩等级
        
    Example:
        >>> system = CognitiveImmuneSystem()
        >>> system.add_node("n1", {"info": "vital data"})
        >>> system.detect_and隔离_attack("n1", -0.5)
        >>> system.maintain_homeostasis()
    """

    def __init__(
        self,
        health_threshold: float = 0.3,
        utility_threshold: float = 0.2,
        max_compression_level: int = 3
    ):
        """
        初始化认知免疫系统。
        
        Args:
            health_threshold: 健康度阈值，必须介于0和1之间
            utility_threshold: 效用阈值，必须介于0和1之间
            max_compression_level: 最大压缩等级，必须大于0
        """
        # 参数验证
        if not (0.0 <= health_threshold <= 1.0):
            raise ValueError("health_threshold must be between 0.0 and 1.0")
        if not (0.0 <= utility_threshold <= 1.0):
            raise ValueError("utility_threshold must be between 0.0 and 1.0")
        if max_compression_level < 1:
            raise ValueError("max_compression_level must be at least 1")
            
        self.nodes: Dict[str, CognitiveNode] = {}
        self.health_threshold = health_threshold
        self.utility_threshold = utility_threshold
        self.max_compression_level = max_compression_level
        logger.info("Cognitive Immune System initialized with thresholds: health=%.2f, utility=%.2f",
                    self.health_threshold, self.utility_threshold)

    def add_node(self, node_id: str, data: Dict) -> bool:
        """
        添加新节点到系统。
        
        Args:
            node_id: 节点唯一标识符
            data: 节点存储的数据字典
            
        Returns:
            bool: 添加是否成功
            
        Raises:
            ValueError: 如果node_id已存在或data无效
        """
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node_id must be a non-empty string")
        if not isinstance(data, dict):
            raise ValueError("data must be a dictionary")
        if node_id in self.nodes:
            logger.warning("Attempted to add existing node_id: %s", node_id)
            return False
            
        self.nodes[node_id] = CognitiveNode(node_id=node_id, data=data)
        logger.info("Added new cognitive node: %s", node_id)
        return True

    def detect_and隔离_attack(self, node_id: str, impact: float) -> bool:
        """
        核心函数1: 检测并隔离攻击。
        
        模拟免疫系统的细胞隔离机制。当检测到异常健康度下降（攻击）时，
        自动将节点标记为隔离状态，防止逻辑病毒扩散。
        
        Args:
            node_id: 目标节点ID
            impact: 攻击影响值（负数表示伤害）
            
        Returns:
            bool: 是否触发了隔离
            
        Raises:
            KeyError: 如果节点不存在
        """
        if node_id not in self.nodes:
            raise KeyError(f"Node {node_id} not found")
            
        node = self.nodes[node_id]
        
        # 边界检查
        if not isinstance(impact, (int, float)):
            logger.error("Invalid impact type for node %s: %s", node_id, type(impact))
            return False
            
        # 更新健康度并限制在[0, 1]范围内
        node.health_score = max(0.0, min(1.0, node.health_score + impact))
        logger.debug("Node %s health updated to %.2f", node_id, node.health_score)
        
        # 免疫响应：隔离受损节点
        if node.health_score < self.health_threshold and node.state == NodeState.ACTIVE:
            node.state = NodeState.ISOLATED
            logger.warning("IMMUNE RESPONSE: Node %s isolated due to low health (%.2f)",
                          node_id, node.health_score)
            return True
            
        return False

    def apply_utility_decay_forget(self, decay_rate: float = 0.1) -> int:
        """
        核心函数2: 应用效用衰减遗忘。
        
        模拟生物遗忘机制。根据时间衰减效用值，并移除效用低于阈值的节点以释放资源。
        
        Args:
            decay_rate: 效用衰减率 (0.0-1.0)
            
        Returns:
            int: 被遗忘（移除）的节点数量
        """
        if not (0.0 <= decay_rate <= 1.0):
            raise ValueError("decay_rate must be between 0.0 and 1.0")
            
        nodes_to_remove = []
        current_time = time.time()
        
        for node_id, node in self.nodes.items():
            # 跳过已隔离节点，它们由免疫系统单独处理
            if node.state == NodeState.ISOLATED:
                continue
                
            # 计算时间衰减因子
            time_delta = current_time - node.last_access_time
            time_decay = math.exp(-decay_rate * time_delta / 3600)  # 每小时衰减
            
            # 更新效用分数
            node.utility_score *= time_decay
            
            # 标记低效用节点以供移除
            if node.utility_score < self.utility_threshold:
                nodes_to_remove.append(node_id)
                logger.info("FORGETTING: Node %s marked for removal (utility: %.4f)",
                           node_id, node.utility_score)
        
        # 执行移除
        for node_id in nodes_to_remove:
            del self.nodes[node_id]
            
        return len(nodes_to_remove)

    def _compress_data(self, data: Dict, level: int) -> Dict:
        """
        辅助函数: 数据压缩接口。
        
        根据压缩等级模拟数据压缩过程。高压缩等级节省空间但可能丢失细节。
        
        Args:
            data: 原始数据字典
            level: 压缩等级 (0-3)
            
        Returns:
            Dict: 压缩后的数据
        """
        if level == 0 or not data:
            return data
            
        compressed = {}
        # 简单模拟压缩：保留键，但简化值
        for k, v in data.items():
            if level == 1:
                # 轻度压缩：保留主要结构
                compressed[k] = str(v)[:50] + "..." if isinstance(v, str) and len(v) > 50 else v
            elif level == 2:
                # 中度压缩：仅保留摘要
                compressed[k] = f"<summary_{type(v).__name__}>"
            else:
                # 重度压缩：仅保留键
                compressed[k] = "<compressed>"
                
        return compressed

    def adapt_compression(self, stress_level: float) -> Dict[str, int]:
        """
        核心函数3: 自适应认知压缩。
        
        根据系统压力动态调整信息密度。高压力时增加压缩以保护核心功能。
        
        Args:
            stress_level: 系统压力值 (0.0-1.0)
            
        Returns:
            Dict[str, int]: 节点ID到新压缩等级的映射
        """
        if not (0.0 <= stress_level <= 1.0):
            raise ValueError("stress_level must be between 0.0 and 1.0")
            
        compression_map = {}
        
        # 根据压力计算目标压缩等级
        target_level = min(
            self.max_compression_level,
            int(stress_level * (self.max_compression_level + 1))
        )
        
        for node_id, node in self.nodes.items():
            if node.state == NodeState.ACTIVE:
                old_level = node.compression_level
                node.compression_level = target_level
                
                # 应用压缩
                node.data = self._compress_data(node.data, target_level)
                compression_map[node_id] = target_level
                
                if old_level != target_level:
                    logger.debug("ADAPTATION: Node %s compression changed %d -> %d",
                                node_id, old_level, target_level)
        
        logger.info("System compression adapted. Stress: %.2f, Target Level: %d",
                   stress_level, target_level)
        return compression_map

    def maintain_homeostasis(self) -> Tuple[int, int, Dict[str, int]]:
        """
        综合功能: 维持系统稳态。
        
        执行完整的免疫/遗忘/压缩周期。
        
        Returns:
            Tuple[int, int, Dict[str, int]]: 
                (隔离节点数, 遗忘节点数, 压缩映射)
        """
        logger.info("Starting homeostasis maintenance cycle...")
        
        # 1. 检测模拟攻击（这里简单模拟随机攻击检测）
        isolated_count = 0
        for node_id, node in list(self.nodes.items()):
            if node.state == NodeState.ACTIVE and node.health_score < self.health_threshold:
                node.state = NodeState.ISOLATED
                isolated_count += 1
        
        # 2. 应用遗忘机制
        forgotten_count = self.apply_utility_decay_forget()
        
        # 3. 计算系统压力并自适应压缩
        active_nodes = sum(1 for n in self.nodes.values() if n.state == NodeState.ACTIVE)
        isolated_nodes = sum(1 for n in self.nodes.values() if n.state == NodeState.ISOLATED)
        
        # 压力计算：隔离节点比例 + 低健康度节点比例
        stress = (isolated_nodes / len(self.nodes)) if self.nodes else 0.0
        stress += sum(1 - n.health_score for n in self.nodes.values() if n.state == NodeState.ACTIVE) / max(1, active_nodes)
        stress = min(1.0, stress)
        
        compression_map = self.adapt_compression(stress)
        
        logger.info("Homeostasis maintained. Isolated: %d, Forgotten: %d, Stress: %.2f",
                   isolated_count, forgotten_count, stress)
        
        return isolated_count, forgotten_count, compression_map


# 使用示例
if __name__ == "__main__":
    # 创建系统实例
    immune_system = CognitiveImmuneSystem(
        health_threshold=0.3,
        utility_threshold=0.2
    )
    
    # 添加测试节点
    immune_system.add_node("knowledge_base", {"type": "encyclopedia", "data": "..."})
    immune_system.add_node("temp_cache", {"temp": True, "value": 42})
    
    # 模拟攻击
    print("\n=== Simulating Attack ===")
    immune_system.detect_and隔离_attack("knowledge_base", -0.8)  # 严重攻击
    
    # 模拟时间流逝和遗忘
    print("\n=== Simulating Time Decay ===")
    time.sleep(1)  # 确保时间戳不同
    immune_system.nodes["temp_cache"].last_access_time -= 7200  # 模拟2小时前访问
    
    # 维持稳态
    print("\n=== Maintaining Homeostasis ===")
    isolated, forgotten, compression = immune_system.maintain_homeostasis()
    
    print(f"\nResults: Isolated={isolated}, Forgotten={forgotten}, Compression={compression}")
    print("Final system state:")
    for nid, node in immune_system.nodes.items():
        print(f"  {nid}: state={node.state.value}, health={node.health_score:.2f}, utility={node.utility_score:.2f}")