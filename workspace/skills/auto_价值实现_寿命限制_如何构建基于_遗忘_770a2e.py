"""
名称: auto_价值实现_寿命限制_如何构建基于_遗忘_770a2e
描述: 【价值实现-寿命限制】如何构建基于‘遗忘曲线’的节点激活机制，以对抗人类寿命限制导致的‘知识折旧’？
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ZombieKnowledgeManager")

class NodeStatus(Enum):
    """知识节点状态的枚举类"""
    ACTIVE = auto()       # 活跃状态
    DORMANT = auto()      # 休眠状态
    ZOMBIE = auto()       # 僵尸状态
    ARCHIVED = auto()     # 已归档

@dataclass
class KnowledgeNode:
    """
    知识节点的数据结构
    
    属性:
        node_id (str): 节点唯一标识符
        content (str): 知识内容
        created_at (datetime): 创建时间
        last_accessed (datetime): 最后访问时间
        access_count (int): 累计访问次数
        importance (float): 重要性评分(0-1)
        status (NodeStatus): 节点当前状态
        tags (List[str]): 分类标签
    """
    node_id: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5
    status: NodeStatus = NodeStatus.ACTIVE
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.importance <= 1:
            raise ValueError("重要性评分必须在0-1之间")
        if self.access_count < 0:
            raise ValueError("访问次数不能为负数")

class ZombieKnowledgeManager:
    """
    僵尸知识管理器，基于遗忘曲线机制管理知识节点
    
    该类实现了基于艾宾浩斯遗忘曲线的节点激活机制，能够:
    1. 识别长期未被访问的"僵尸知识"
    2. 根据重要性评分决定是否归档
    3. 触发知识复用或归档流程
    4. 确保认知网络反映最新环境
    
    使用示例:
        >>> manager = ZombieKnowledgeManager()
        >>> node = KnowledgeNode("001", "Python基础")
        >>> manager.add_node(node)
        >>> manager.access_node("001")
        >>> manager.update_all_nodes_status()
    """
    
    def __init__(self, decay_rate: float = 0.3, zombie_threshold: float = 0.1):
        """
        初始化知识管理器
        
        参数:
            decay_rate (float): 遗忘曲线衰减率(0-1)
            zombie_threshold (float): 激活度低于此值判定为僵尸知识(0-1)
        """
        if not 0 <= decay_rate <= 1:
            raise ValueError("衰减率必须在0-1之间")
        if not 0 <= zombie_threshold <= 1:
            raise ValueError("僵尸阈值必须在0-1之间")
            
        self.decay_rate = decay_rate
        self.zombie_threshold = zombie_threshold
        self.nodes: Dict[str, KnowledgeNode] = {}
        logger.info(f"初始化知识管理器，衰减率: {decay_rate}, 僵尸阈值: {zombie_threshold}")
    
    def add_node(self, node: KnowledgeNode) -> None:
        """
        添加新的知识节点
        
        参数:
            node (KnowledgeNode): 要添加的知识节点
            
        异常:
            ValueError: 如果节点ID已存在
        """
        if node.node_id in self.nodes:
            raise ValueError(f"节点ID {node.node_id} 已存在")
            
        self.nodes[node.node_id] = node
        logger.info(f"添加新节点: {node.node_id}, 内容: {node.content[:20]}...")
    
    def access_node(self, node_id: str, timestamp: Optional[datetime] = None) -> None:
        """
        访问知识节点，更新其访问时间和计数
        
        参数:
            node_id (str): 要访问的节点ID
            timestamp (datetime, optional): 指定访问时间，默认为当前时间
            
        异常:
            KeyError: 如果节点不存在
        """
        if node_id not in self.nodes:
            raise KeyError(f"节点ID {node_id} 不存在")
            
        node = self.nodes[node_id]
        node.last_accessed = timestamp or datetime.now()
        node.access_count += 1
        logger.debug(f"访问节点: {node_id}, 新计数: {node.access_count}")
    
    def _calculate_activation(self, node: KnowledgeNode, current_time: datetime) -> float:
        """
        计算节点的当前激活度(辅助函数)
        
        基于艾宾浩斯遗忘曲线公式: R = e^(-t/S)
        其中 t 是时间间隔，S 是记忆强度(与重要性相关)
        
        参数:
            node (KnowledgeNode): 知识节点
            current_time (datetime): 当前时间
            
        返回:
            float: 激活度评分(0-1)
        """
        time_delta = (current_time - node.last_accessed).total_seconds() / 86400  # 转换为天数
        memory_strength = node.importance * 10 + 1  # 转换为记忆强度
        activation = math.exp(-time_delta / memory_strength)
        
        # 应用衰减率
        activation *= (1 - self.decay_rate)
        return max(0.0, min(1.0, activation))
    
    def identify_zombie_nodes(self, current_time: Optional[datetime] = None) -> List[Tuple[str, float]]:
        """
        识别僵尸知识节点
        
        参数:
            current_time (datetime, optional): 当前时间，默认为系统时间
            
        返回:
            List[Tuple[str, float]]: 僵尸节点ID列表及其激活度
        """
        current_time = current_time or datetime.now()
        zombie_nodes = []
        
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.ARCHIVED:
                continue
                
            activation = self._calculate_activation(node, current_time)
            if activation < self.zombie_threshold:
                zombie_nodes.append((node_id, activation))
                node.status = NodeStatus.ZOMBIE
                logger.warning(f"发现僵尸知识: {node_id}, 激活度: {activation:.3f}")
        
        return zombie_nodes
    
    def handle_zombie_nodes(self, action: str = "reuse") -> Dict[str, NodeStatus]:
        """
        处理僵尸知识节点
        
        参数:
            action (str): 处理方式，"reuse"强制复用，"archive"归档
            
        返回:
            Dict[str, NodeStatus]: 处理后的节点状态映射
            
        异常:
            ValueError: 如果action参数无效
        """
        if action not in ["reuse", "archive"]:
            raise ValueError("action参数必须是'reuse'或'archive'")
            
        results = {}
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.ZOMBIE:
                if action == "reuse":
                    # 强制复用：重置访问时间和计数
                    node.last_accessed = datetime.now()
                    node.access_count += 1
                    node.status = NodeStatus.ACTIVE
                    logger.info(f"强制复用僵尸知识: {node_id}")
                else:
                    # 归档处理
                    node.status = NodeStatus.ARCHIVED
                    logger.info(f"归档僵尸知识: {node_id}")
                
                results[node_id] = node.status
        
        return results
    
    def update_all_nodes_status(self, current_time: Optional[datetime] = None) -> None:
        """
        更新所有节点的状态(核心函数)
        
        该方法会:
        1. 计算每个节点的当前激活度
        2. 更新节点状态(ACTIVE/DORMANT/ZOMBIE)
        3. 记录状态变更日志
        
        参数:
            current_time (datetime, optional): 当前时间，默认为系统时间
        """
        current_time = current_time or datetime.now()
        
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.ARCHIVED:
                continue
                
            activation = self._calculate_activation(node, current_time)
            
            if activation < self.zombie_threshold:
                new_status = NodeStatus.ZOMBIE
            elif activation < 0.5:
                new_status = NodeStatus.DORMANT
            else:
                new_status = NodeStatus.ACTIVE
                
            if node.status != new_status:
                logger.info(
                    f"节点状态变更: {node_id} {node.status.name} -> {new_status.name} "
                    f"(激活度: {activation:.3f})"
                )
                node.status = new_status

def demo_usage():
    """演示如何使用ZombieKnowledgeManager"""
    # 初始化管理器
    manager = ZombieKnowledgeManager(decay_rate=0.3, zombie_threshold=0.1)
    
    # 添加一些知识节点
    nodes = [
        KnowledgeNode("001", "Python基础", importance=0.7),
        KnowledgeNode("002", "机器学习算法", importance=0.9),
        KnowledgeNode("003", "过时的API", importance=0.3)
    ]
    
    for node in nodes:
        manager.add_node(node)
    
    # 模拟访问
    manager.access_node("001")
    manager.access_node("002")
    
    # 模拟时间流逝(设置过时节点为30天前访问)
    old_time = datetime.now() - timedelta(days=30)
    manager.access_node("003", timestamp=old_time)
    
    # 识别僵尸知识
    print("僵尸知识识别结果:", manager.identify_zombie_nodes())
    
    # 处理僵尸知识
    print("处理结果:", manager.handle_zombie_nodes(action="reuse"))
    
    # 更新所有节点状态
    manager.update_all_nodes_status()

if __name__ == "__main__":
    demo_usage()