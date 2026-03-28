"""
工业代谢稳态调节器

该模块实现了基于生物负反馈回路的分布式集群调节系统。
通过模拟生物体的稳态调节机制（如血管舒张和免疫应答），
实现系统负载的自适应管理和故障自愈能力。

核心特性:
- 动态负载均衡（血管舒张效应）
- 故障隔离与恢复（免疫应答机制）
- 状态监控与反馈调节
- 自适应扩容缩容

典型应用场景:
1. 分布式订单处理系统
2. 实时数据流处理集群
3. 微服务架构下的资源调度
"""

import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque
import numpy as np

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IndustrialHomeostasisRegulator")


class NodeType(Enum):
    """节点类型枚举"""
    ORDER_PROCESSOR = auto()    # 订单处理节点
    DATA_ANALYZER = auto()      # 数据分析节点
    STORAGE_NODE = auto()       # 存储节点
    COMPUTE_NODE = auto()       # 计算节点


class HealthStatus(Enum):
    """节点健康状态枚举"""
    HEALTHY = auto()            # 健康
    STRESSED = auto()           # 压力过大
    INFECTED = auto()           # 感染（数据异常）
    RECOVERING = auto()         # 恢复中
    ISOLATED = auto()           # 已隔离


@dataclass
class NodeState:
    """节点状态数据结构"""
    node_id: str
    node_type: NodeType
    cpu_load: float = 0.0       # CPU负载 (0.0-1.0)
    memory_usage: float = 0.0   # 内存使用率 (0.0-1.0)
    request_rate: float = 0.0   # 请求速率 (请求/秒)
    error_rate: float = 0.0     # 错误率 (0.0-1.0)
    health_status: HealthStatus = HealthStatus.HEALTHY
    last_updated: float = field(default_factory=time.time)
    neighbors: List[str] = field(default_factory=list)
    rollback_snapshot: Optional[Dict] = None


class IndustrialHomeostasisRegulator:
    """
    工业代谢稳态调节器
    
    通过模拟生物体的稳态调节机制，实现分布式系统的自适应管理。
    
    核心功能:
    1. 监控集群节点状态（类似体温、血压监测）
    2. 触发血管舒张效应（负载均衡）
    3. 触发免疫应答（故障隔离与恢复）
    
    属性:
        nodes (Dict[str, NodeState]): 节点状态字典
        stress_threshold (float): 压力阈值 (0.0-1.0)
        infection_threshold (float): 感染阈值 (错误率阈值)
        feedback_history (deque): 反馈历史记录
    """
    
    def __init__(self, stress_threshold: float = 0.75, 
                 infection_threshold: float = 0.15,
                 history_size: int = 100):
        """
        初始化调节器
        
        参数:
            stress_threshold: 压力阈值，超过此值触发血管舒张
            infection_threshold: 感染阈值，错误率超过此值触发免疫应答
            history_size: 历史记录保存数量
        """
        self.nodes: Dict[str, NodeState] = {}
        self.stress_threshold = self._validate_threshold(stress_threshold)
        self.infection_threshold = self._validate_threshold(infection_threshold)
        self.feedback_history = deque(maxlen=history_size)
        self._setup_initial_nodes()
        
    def _validate_threshold(self, value: float) -> float:
        """验证阈值参数是否在有效范围内"""
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"阈值必须在0.0到1.0之间，当前值: {value}")
        return value
    
    def _setup_initial_nodes(self) -> None:
        """初始化默认节点配置"""
        default_nodes = [
            ("order_1", NodeType.ORDER_PROCESSOR),
            ("order_2", NodeType.ORDER_PROCESSOR),
            ("data_1", NodeType.DATA_ANALYZER),
            ("compute_1", NodeType.COMPUTE_NODE)
        ]
        
        for node_id, node_type in default_nodes:
            self.register_node(node_id, node_type)
    
    def register_node(self, node_id: str, node_type: NodeType, 
                     initial_state: Optional[Dict] = None) -> bool:
        """
        注册新节点到调节器
        
        参数:
            node_id: 节点唯一标识
            node_type: 节点类型
            initial_state: 初始状态参数
            
        返回:
            bool: 是否注册成功
        """
        if node_id in self.nodes:
            logger.warning(f"节点 {node_id} 已存在，更新状态")
            return False
            
        try:
            new_node = NodeState(node_id=node_id, node_type=node_type)
            
            if initial_state:
                for key, value in initial_state.items():
                    if hasattr(new_node, key):
                        setattr(new_node, key, value)
            
            self.nodes[node_id] = new_node
            logger.info(f"成功注册节点: {node_id} (类型: {node_type.name})")
            return True
            
        except Exception as e:
            logger.error(f"注册节点 {node_id} 失败: {str(e)}")
            return False
    
    def update_node_metrics(self, node_id: str, metrics: Dict[str, float]) -> bool:
        """
        更新节点指标数据
        
        参数:
            node_id: 节点ID
            metrics: 指标字典，包含cpu_load, memory_usage等
            
        返回:
            bool: 是否更新成功
            
        输入格式示例:
            {
                "cpu_load": 0.85,
                "memory_usage": 0.72,
                "request_rate": 150.0,
                "error_rate": 0.05
            }
        """
        if node_id not in self.nodes:
            logger.error(f"节点 {node_id} 不存在")
            return False
            
        node = self.nodes[node_id]
        
        try:
            # 数据验证和边界检查
            for key, value in metrics.items():
                if hasattr(node, key):
                    if key in ['cpu_load', 'memory_usage', 'error_rate']:
                        value = max(0.0, min(1.0, float(value)))
                    elif key == 'request_rate':
                        value = max(0.0, float(value))
                    setattr(node, key, value)
            
            node.last_updated = time.time()
            logger.debug(f"更新节点 {node_id} 指标: {metrics}")
            return True
            
        except Exception as e:
            logger.error(f"更新节点 {node_id} 指标失败: {str(e)}")
            return False
    
    def _detect_stress(self, node: NodeState) -> bool:
        """检测节点是否处于压力状态"""
        # 综合压力指标 = 加权平均负载
        composite_stress = (
            0.5 * node.cpu_load + 
            0.3 * node.memory_usage + 
            0.2 * (node.request_rate / 1000)  # 假设1000请求/秒为基准
        )
        
        return composite_stress > self.stress_threshold
    
    def _detect_infection(self, node: NodeState) -> bool:
        """检测节点是否感染（数据异常）"""
        return node.error_rate > self.infection_threshold
    
    def _vasodilation_response(self, stressed_node: NodeState) -> Dict[str, Union[str, List[str]]]:
        """
        血管舒张响应 - 动态扩容并分流负载
        
        模拟生物体在体温升高时的血管舒张效应，将负载分散到相邻节点。
        
        参数:
            stressed_node: 压力节点
            
        返回:
            响应结果字典，包含动作类型和受影响节点
        """
        logger.warning(f"检测到节点 {stressed_node.node_id} 压力过大，触发血管舒张响应")
        
        # 找出健康相邻节点
        healthy_neighbors = [
            n for n in self.nodes.values() 
            if (n.node_id != stressed_node.node_id and 
                n.health_status == HealthStatus.HEALTHY and
                n.node_type == stressed_node.node_type)
        ]
        
        if not healthy_neighbors:
            logger.error("无可用健康节点进行负载分流")
            return {"action": "vasodilation_failed", "reason": "no_healthy_neighbors"}
        
        # 选择负载最低的节点进行分流
        target_node = min(healthy_neighbors, key=lambda n: n.cpu_load)
        
        # 模拟负载分流
        load_transfer = min(0.3, stressed_node.cpu_load * 0.5)  # 转移不超过30%负载
        stressed_node.cpu_load -= load_transfer
        target_node.cpu_load += load_transfer
        
        # 记录反馈历史
        self.feedback_history.append({
            "timestamp": time.time(),
            "action": "vasodilation",
            "source": stressed_node.node_id,
            "target": target_node.node_id,
            "load_transferred": load_transfer
        })
        
        logger.info(f"负载分流: 从 {stressed_node.node_id} 转移 {load_transfer:.2f} 到 {target_node.node_id}")
        
        return {
            "action": "vasodilation",
            "source_node": stressed_node.node_id,
            "target_node": target_node.node_id,
            "load_transferred": load_transfer
        }
    
    def _immune_response(self, infected_node: NodeState) -> Dict[str, Union[str, List[str]]]:
        """
        免疫响应 - 隔离故障节点并尝试恢复
        
        模拟生物体对病原体的免疫应答，隔离故障节点并尝试回滚状态。
        
        参数:
            infected_node: 感染节点
            
        返回:
            响应结果字典，包含动作类型和恢复状态
        """
        logger.error(f"检测到节点 {infected_node.node_id} 数据异常，触发免疫响应")
        
        # 隔离节点
        infected_node.health_status = HealthStatus.ISOLATED
        
        # 查找健康节点接管工作
        healthy_nodes = [
            n for n in self.nodes.values() 
            if (n.node_id != infected_node.node_id and 
                n.health_status == HealthStatus.HEALTHY and
                n.node_type == infected_node.node_type)
        ]
        
        takeover_success = False
        takeover_node = None
        
        if healthy_nodes:
            takeover_node = min(healthy_nodes, key=lambda n: n.cpu_load)
            takeover_node.request_rate += infected_node.request_rate * 0.8  # 接管80%请求
            takeover_success = True
        
        # 尝试状态回滚
        recovery_status = "failed"
        if infected_node.rollback_snapshot:
            # 模拟回滚过程
            recovery_status = "initiated"
            infected_node.health_status = HealthStatus.RECOVERING
            logger.info(f"节点 {infected_node.node_id} 开始状态回滚")
        
        # 记录反馈历史
        self.feedback_history.append({
            "timestamp": time.time(),
            "action": "immune_response",
            "infected_node": infected_node.node_id,
            "takeover_node": takeover_node.node_id if takeover_node else None,
            "recovery_status": recovery_status
        })
        
        return {
            "action": "immune_response",
            "infected_node": infected_node.node_id,
            "takeover_node": takeover_node.node_id if takeover_node else None,
            "recovery_status": recovery_status,
            "isolation_status": "isolated"
        }
    
    def regulate_cluster(self) -> Dict[str, List[Dict]]:
        """
        执行集群稳态调节
        
        遍历所有节点，检测压力或感染状态，并触发相应响应。
        
        返回:
            包含所有响应动作的字典，格式如下:
            {
                "vasodilation_actions": [...],  # 血管舒张响应列表
                "immune_actions": [...]         # 免疫响应列表
            }
        """
        results = {
            "vasodilation_actions": [],
            "immune_actions": []
        }
        
        for node in list(self.nodes.values()):
            # 更新节点健康状态
            if self._detect_infection(node):
                node.health_status = HealthStatus.INFECTED
                response = self._immune_response(node)
                results["immune_actions"].append(response)
            elif self._detect_stress(node):
                node.health_status = HealthStatus.STRESSED
                response = self._vasodilation_response(node)
                results["vasodilation_actions"].append(response)
            else:
                node.health_status = HealthStatus.HEALTHY
        
        return results
    
    def get_cluster_status(self) -> Dict[str, Union[Dict, float, int]]:
        """
        获取集群整体状态
        
        返回:
            包含集群状态摘要的字典
        """
        if not self.nodes:
            return {"status": "no_nodes", "message": "集群中无注册节点"}
        
        # 计算集群级指标
        avg_cpu = np.mean([n.cpu_load for n in self.nodes.values()])
        avg_memory = np.mean([n.memory_usage for n in self.nodes.values()])
        avg_error_rate = np.mean([n.error_rate for n in self.nodes.values()])
        
        # 统计健康状态
        health_counts = {}
        for status in HealthStatus:
            health_counts[status.name] = sum(
                1 for n in self.nodes.values() 
                if n.health_status == status
            )
        
        return {
            "node_count": len(self.nodes),
            "average_cpu_load": round(float(avg_cpu), 3),
            "average_memory_usage": round(float(avg_memory), 3),
            "average_error_rate": round(float(avg_error_rate), 4),
            "health_status_distribution": health_counts,
            "stress_threshold": self.stress_threshold,
            "infection_threshold": self.infection_threshold,
            "last_updated": max(n.last_updated for n in self.nodes.values())
        }
    
    def save_rollback_snapshot(self, node_id: str, snapshot_data: Dict) -> bool:
        """
        保存节点状态快照用于回滚
        
        参数:
            node_id: 节点ID
            snapshot_data: 状态快照数据
            
        返回:
            bool: 是否保存成功
        """
        if node_id not in self.nodes:
            logger.error(f"节点 {node_id} 不存在")
            return False
            
        self.nodes[node_id].rollback_snapshot = {
            "timestamp": time.time(),
            "data": snapshot_data
        }
        logger.info(f"保存节点 {node_id} 状态快照")
        return True


# 使用示例
if __name__ == "__main__":
    # 初始化调节器
    regulator = IndustrialHomeostasisRegulator(
        stress_threshold=0.75,
        infection_threshold=0.15
    )
    
    # 注册新节点
    regulator.register_node("order_3", NodeType.ORDER_PROCESSOR)
    regulator.register_node("data_2", NodeType.DATA_ANALYZER)
    
    # 模拟更新节点指标
    regulator.update_node_metrics("order_1", {
        "cpu_load": 0.85,
        "memory_usage": 0.78,
        "request_rate": 1200,
        "error_rate": 0.02
    })
    
    regulator.update_node_metrics("order_2", {
        "cpu_load": 0.45,
        "memory_usage": 0.52,
        "request_rate": 800,
        "error_rate": 0.01
    })
    
    # 触发血管舒张响应
    print("\n触发压力测试...")
    regulator.update_node_metrics("order_1", {
        "cpu_load": 0.92,  # 超过压力阈值
        "memory_usage": 0.85
    })
    
    # 触发免疫响应
    print("\n触发感染测试...")
    regulator.update_node_metrics("data_1", {
        "error_rate": 0.18  # 超过感染阈值
    })
    
    # 执行调节
    regulation_results = regulator.regulate_cluster()
    print("\n调节结果:", regulation_results)
    
    # 获取集群状态
    cluster_status = regulator.get_cluster_status()
    print("\n集群状态:", cluster_status)
    
    # 保存快照
    regulator.save_rollback_snapshot("order_1", {"config": "v1.2", "data": [1, 2, 3]})