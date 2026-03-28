"""
名称: auto_结构化认知网络的遗忘机制_为了防止_认知_9ca63f
描述: 结构化认知网络的遗忘机制：为了防止'认知自洽'演变为'认知僵化'，系统需要具备主动遗忘低价值节点的能力。
      本模块设计基于'实践验证频率'与'网络连接度'的衰减函数，自动降权或归档那些长期未被激活且未产生新连接的'僵尸节点'。
领域: software_engineering
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """认知网络中节点的状态枚举"""
    ACTIVE = "active"          # 活跃状态
    DORMANT = "dormant"        # 休眠状态
    ARCHIVED = "archived"      # 归档状态

@dataclass
class CognitiveNode:
    """
    认知网络节点数据结构
    
    Attributes:
        node_id (str): 节点唯一标识符
        weight (float): 节点权重 (0.0 - 1.0)，代表认知价值
        last_activated (int): 上次被激活的周期数（时间戳）
        activation_count (int): 历史被激活的总次数
        connections (Set[str]): 连接的其他节点ID集合
        status (NodeStatus): 节点当前状态
    """
    node_id: str
    weight: float = 1.0
    last_activated: int = 0
    activation_count: int = 0
    connections: Set[str] = field(default_factory=set)
    status: NodeStatus = NodeStatus.ACTIVE

    def __post_init__(self):
        """数据验证"""
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"权重必须在0.0到1.0之间，当前值: {self.weight}")
        if self.activation_count < 0:
            raise ValueError("激活次数不能为负数")

class CognitiveNetwork:
    """
    结构化认知网络管理类
    实现基于实践验证和网络连接度的遗忘机制
    """
    
    def __init__(self, current_cycle: int = 0):
        """
        初始化认知网络
        
        Args:
            current_cycle (int): 当前系统运行的周期数，用于时间衰减计算
        """
        self.nodes: Dict[str, CognitiveNode] = {}
        self.current_cycle = current_cycle
        self.decay_config = {
            'base_decay_rate': 0.1,      # 基础衰减率
            'connection_weight': 0.4,     # 连接度对衰减的影响权重
            'activation_weight': 0.6,     # 激活频率对衰减的影响权重
            'archive_threshold': 0.1,     # 归档阈值
            'dormant_cycles': 50          # 进入休眠状态的未激活周期数
        }
    
    def add_node(self, node: CognitiveNode) -> bool:
        """
        添加新节点到认知网络
        
        Args:
            node (CognitiveNode): 要添加的节点对象
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if node.node_id in self.nodes:
                logger.warning(f"节点 {node.node_id} 已存在，更新节点数据")
            
            self.nodes[node.node_id] = node
            logger.info(f"成功添加节点: {node.node_id}")
            return True
        except Exception as e:
            logger.error(f"添加节点 {node.node_id} 失败: {str(e)}")
            return False
    
    def _calculate_time_decay(self, node: CognitiveNode) -> float:
        """
        辅助函数：计算基于时间的衰减因子
        使用指数衰减函数模拟艾宾浩斯遗忘曲线
        
        Args:
            node (CognitiveNode): 目标节点
            
        Returns:
            float: 时间衰减因子 (0.0 - 1.0)
        """
        cycles_inactive = self.current_cycle - node.last_activated
        
        if cycles_inactive < 0:
            logger.warning(f"节点 {node.node_id} 的激活时间在未来，已修正")
            cycles_inactive = 0
        
        # 指数衰减: e^(-lambda * t)
        decay_factor = math.exp(-self.decay_config['base_decay_rate'] * cycles_inactive)
        return max(0.0, min(1.0, decay_factor))
    
    def _calculate_connection_factor(self, node: CognitiveNode) -> float:
        """
        辅助函数：计算基于连接度的保持因子
        连接度越高，节点越重要，衰减越慢
        
        Args:
            node (CognitiveNode): 目标节点
            
        Returns:
            float: 连接保持因子 (0.0 - 1.0)
        """
        connection_count = len(node.connections)
        
        # 使用sigmoid函数将连接数映射到(0,1)区间
        # 连接越多，因子越接近1，衰减越慢
        sigmoid_factor = 1 / (1 + math.exp(-0.1 * (connection_count - 10)))
        
        return sigmoid_factor
    
    def apply_forgetting_mechanism(self) -> Dict[str, List[str]]:
        """
        核心函数：应用遗忘机制
        基于实践验证频率与网络连接度对所有节点进行权重衰减和状态更新
        
        Returns:
            Dict[str, List[str]]: 包含三个列表的字典:
                - 'archived': 被归档的节点ID列表
                - 'dormant': 进入休眠状态的节点ID列表
                - 'active': 保持活跃的节点ID列表
        
        Example:
            >>> network = CognitiveNetwork(current_cycle=100)
            >>> node = CognitiveNode("concept_1", last_activated=10)
            >>> network.add_node(node)
            >>> result = network.apply_forgetting_mechanism()
            >>> print(result['archived'])
        """
        result = {
            'archived': [],
            'dormant': [],
            'active': []
        }
        
        if not self.nodes:
            logger.warning("认知网络为空，无需执行遗忘机制")
            return result
        
        logger.info(f"开始对 {len(self.nodes)} 个节点应用遗忘机制...")
        
        for node_id, node in list(self.nodes.items()):
            try:
                # 1. 计算各项衰减因子
                time_decay = self._calculate_time_decay(node)
                connection_factor = self._calculate_connection_factor(node)
                
                # 2. 综合计算新权重
                # 权重 = 原权重 * (时间衰减 * 激活权重 + 连接因子 * 连接权重)
                activation_part = time_decay * self.decay_config['activation_weight']
                connection_part = connection_factor * self.decay_config['connection_weight']
                retention_rate = activation_part + connection_part
                
                new_weight = node.weight * retention_rate
                new_weight = max(0.0, min(1.0, new_weight))  # 边界检查
                node.weight = new_weight
                
                # 3. 状态更新逻辑
                cycles_inactive = self.current_cycle - node.last_activated
                
                if new_weight < self.decay_config['archive_threshold']:
                    # 权重过低，归档节点
                    node.status = NodeStatus.ARCHIVED
                    result['archived'].append(node_id)
                    logger.debug(f"节点 {node_id} 已归档，最终权重: {new_weight:.4f}")
                elif cycles_inactive > self.decay_config['dormant_cycles']:
                    # 长期未激活，进入休眠
                    if node.status == NodeStatus.ACTIVE:
                        node.status = NodeStatus.DORMANT
                        result['dormant'].append(node_id)
                        logger.debug(f"节点 {node_id} 进入休眠状态")
                else:
                    result['active'].append(node_id)
                    
            except Exception as e:
                logger.error(f"处理节点 {node_id} 时发生错误: {str(e)}")
                continue
        
        logger.info(
            f"遗忘机制执行完成。归档: {len(result['archived'])}, "
            f"休眠: {len(result['dormant'])}, "
            f"活跃: {len(result['active'])}"
        )
        
        return result

    def clean_up_connections(self) -> int:
        """
        核心函数：清理网络中的无效连接
        移除指向已归档节点或不存在的节点的连接
        
        Returns:
            int: 总共移除的无效连接数
        """
        total_removed = 0
        
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.ARCHIVED:
                continue
                
            invalid_connections = set()
            for connected_id in node.connections:
                if (connected_id not in self.nodes or 
                    self.nodes[connected_id].status == NodeStatus.ARCHIVED):
                    invalid_connections.add(connected_id)
            
            if invalid_connections:
                node.connections -= invalid_connections
                total_removed += len(invalid_connections)
                logger.debug(
                    f"从节点 {node_id} 移除了 {len(invalid_connections)} 个无效连接"
                )
        
        if total_removed > 0:
            logger.info(f"网络清理完成，共移除 {total_removed} 个无效连接")
        
        return total_removed

# 使用示例
if __name__ == "__main__":
    # 1. 初始化认知网络
    network = CognitiveNetwork(current_cycle=100)
    
    # 2. 创建并添加节点
    # 活跃节点：经常被激活且连接度高
    active_node = CognitiveNode(
        node_id="core_concept",
        weight=0.9,
        last_activated=95,
        activation_count=50,
        connections={"sub_concept_1", "sub_concept_2"}
    )
    
    # 僵尸节点：长期未激活且无连接
    zombie_node = CognitiveNode(
        node_id="outdated_idea",
        weight=0.8,
        last_activated=10,
        activation_count=1,
        connections=set()
    )
    
    # 休眠节点：有连接但近期未激活
    dormant_node = CognitiveNode(
        node_id="background_knowledge",
        weight=0.6,
        last_activated=40,
        connections={"core_concept"}
    )
    
    network.add_node(active_node)
    network.add_node(zombie_node)
    network.add_node(dormant_node)
    
    # 3. 建立连接关系
    network.nodes["core_concept"].connections.add("background_knowledge")
    
    # 4. 执行遗忘机制
    result = network.apply_forgetting_mechanism()
    
    # 5. 清理无效连接
    removed_count = network.clean_up_connections()
    
    # 6. 输出结果
    print("\n=== 遗忘机制执行结果 ===")
    print(f"归档节点: {result['archived']}")
    print(f"休眠节点: {result['dormant']}")
    print(f"活跃节点: {result['active']}")
    print(f"清理的无效连接数: {removed_count}")
    
    print("\n=== 节点最终状态 ===")
    for node_id, node in network.nodes.items():
        print(
            f"ID: {node_id}, 权重: {node.weight:.4f}, "
            f"状态: {node.status.value}, 连接数: {len(node.connections)}"
        )