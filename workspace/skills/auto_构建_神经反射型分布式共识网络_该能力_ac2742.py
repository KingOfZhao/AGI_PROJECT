"""
Module: auto_build_reflexive_consensus_network_ac2742
Description: 构建神经反射型分布式共识网络。
             该模块实现了一种仿生学的分布式容灾机制。当网络遭遇大规模攻击或分区时，
             系统自动从强一致性的全局共识降级为基于局部感知的生物反射模式，
             确保核心服务的存活性，模拟生物脊髓反射机制。
Author: AGI System Core
Version: 1.0.0
"""

import logging
import time
import random
import threading
from enum import Enum, auto
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NeuroReflexiveNetwork")

class ConsensusMode(Enum):
    """定义共识模式的枚举类"""
    RAFT_GLOBAL = auto()    # 强一致性全局模式
    LOCAL_REFLEX = auto()   # 局部反射模式
    COMA = auto()           # 假死/深度休眠模式

@dataclass
class NetworkMetric:
    """网络状态指标数据结构"""
    latency_ms: float = 0.0
    packet_loss: float = 0.0
    active_nodes: int = 0
    total_nodes: int = 0
    last_heartbeat: float = field(default_factory=time.time)

    def is_healthy(self) -> bool:
        """检查网络指标是否处于健康状态"""
        return (
            self.latency_ms < 200 and 
            self.packet_loss < 0.1 and 
            self.active_nodes >= (self.total_nodes * 0.51)
        )

@dataclass
class NodeConfig:
    """节点配置数据结构"""
    node_id: str
    ip_address: str
    port: int
    neighbors: Set[str] = field(default_set_factory=set)
    is_core_service: bool = False

class ReflexiveConsensusCore:
    """
    神经反射型共识核心类。
    
    负责管理节点状态、监测网络健康度，并在危机时刻执行模式切换。
    
    Attributes:
        config (NodeConfig): 节点配置
        current_mode (ConsensusMode): 当前共识模式
        metrics (Dict[str, NetworkMetric]): 邻居节点的网络指标
        brain_buffer (List[str]): 全局模式下待确认的指令缓冲区
        reflex_actions (Dict[str, str]): 预定义的局部反射规则
    """

    def __init__(self, config: NodeConfig):
        """
        初始化共识核心。
        
        Args:
            config (NodeConfig): 节点的配置信息
        """
        if not config.node_id or not config.ip_address:
            raise ValueError("节点ID和IP地址不能为空")
        if config.port < 1024 or config.port > 65535:
            raise ValueError("端口号必须在 1024-65535 范围内")
            
        self.config = config
        self.current_mode = ConsensusMode.RAFT_GLOBAL
        self.metrics: Dict[str, NetworkMetric] = {}
        self.brain_buffer: List[str] = []
        self.reflex_actions = self._init_reflex_rules()
        self._lock = threading.RLock()
        
        logger.info(f"节点 {self.config.node_id} 初始化完成，默认模式: {self.current_mode.name}")

    def _init_reflex_rules(self) -> Dict[str, str]:
        """
        初始化生物反射规则映射表（脊髓逻辑）。
        
        Returns:
            Dict[str, str]: 触发条件到动作的映射
        """
        return {
            "high_traffic": "rate_limit_immediate",  # 类似触碰热物缩手
            "memory_overflow": "clear_cache_l1",     # 类似排泄反射
            "heartbeat_timeout": "restart_vital_process"  # 类似呼吸反射
        }

    def monitor_network_status(self, neighbor_metrics: Dict[str, NetworkMetric]) -> bool:
        """
        核心函数1: 监测网络状态并决定是否切换模式。
        
        这是系统的"痛觉感受器"。如果网络分区或延迟过高，触发降级。
        
        Args:
            neighbor_metrics (Dict[str, NetworkMetric]): 来自邻居节点的最新指标
            
        Returns:
            bool: 如果触发了模式切换返回 True，否则返回 False
            
        Raises:
            ValueError: 如果输入指标包含无效数据
        """
        with self._lock:
            if not neighbor_metrics:
                logger.warning("接收到空的指标数据，保持当前状态")
                return False

            # 数据验证
            for node_id, metric in neighbor_metrics.items():
                if not isinstance(metric, NetworkMetric):
                    raise ValueError(f"无效的指标类型: {node_id}")
                if metric.latency_ms < 0 or metric.packet_loss < 0:
                    raise ValueError(f"指标数值不能为负: {node_id}")

            self.metrics.update(neighbor_metrics)
            
            # 计算全局健康度
            healthy_neighbors = sum(1 for m in neighbor_metrics.values() if m.is_healthy())
            quorum_reachable = healthy_neighbors >= (len(self.config.neighbors) * 0.5)

            # 状态机转换逻辑
            switched = False
            
            if self.current_mode == ConsensusMode.RAFT_GLOBAL:
                if not quorum_reachable:
                    logger.warning(f"检测到分区或DDoS (健康邻居: {healthy_neighbors}), 切换至局部反射模式...")
                    self._switch_mode(ConsensusMode.LOCAL_REFLEX)
                    switched = True
            
            elif self.current_mode == ConsensusMode.LOCAL_REFLEX:
                if quorum_reachable:
                    logger.info("网络恢复仲裁能力，尝试复苏至全局共识...")
                    self._switch_mode(ConsensusMode.RAFT_GLOBAL)
                    switched = True
                elif self._check_local_grid_failure():
                    logger.critical("局部环境完全失效，进入假死/休眠模式...")
                    self._switch_mode(ConsensusMode.COMA)
                    switched = True
                    
            return switched

    def _switch_mode(self, new_mode: ConsensusMode) -> None:
        """
        辅助函数: 执行模式切换的具体逻辑。
        
        Args:
            new_mode (ConsensusMode): 目标模式
        """
        old_mode = self.current_mode
        self.current_mode = new_mode
        logger.info(f"模式切换: {old_mode.name} -> {new_mode.name}")
        
        if new_mode == ConsensusMode.LOCAL_REFLEX:
            # 降级处理：丢弃未完成的全局事务，保留核心状态
            self.brain_buffer = [cmd for cmd in self.brain_buffer if "CRITICAL" in cmd]
            logger.info("已清理非关键全局事务缓冲区")
            
        elif new_mode == ConsensusMode.COMA:
            # 假死处理：只保留最核心的监听线程
            self.brain_buffer.clear()
            logger.info("系统进入低功耗假死状态，仅维持心跳")

    def process_request(self, request_type: str, payload: str) -> Optional[str]:
        """
        核心函数2: 处理外部请求，根据当前模式做出响应。
        
        模拟生物体的运动控制：
        - 全局模式（全脑）：需要与其他节点协商确认
        - 反射模式（脊髓）：直接根据本地规则响应
        - 假死模式：拒绝非生命维持请求
        
        Args:
            request_type (str): 请求类型 (e.g., 'write', 'read', 'control')
            payload (str): 请求负载
            
        Returns:
            Optional[str]: 处理结果，如果请求被拒绝或忽略则返回 None
        """
        with self._lock:
            if self.current_mode == ConsensusMode.COMA:
                if request_type == "system_wake":
                    logger.info("接收到唤醒信号，正在复苏...")
                    self._switch_mode(ConsensusMode.LOCAL_REFLEX)
                    return "WAKING_UP"
                return None  # 假死状态拒绝服务

            if self.current_mode == ConsensusMode.LOCAL_REFLEX:
                # 局部反射：不经过全局共识，直接执行预设逻辑
                action = self.reflex_actions.get(request_type)
                if action:
                    logger.debug(f"反射响应触发: {request_type} -> {action}")
                    return f"REFLEX_EXECUTED:{action}"
                else:
                    # 未知请求在反射模式下被视为干扰，直接丢弃
                    logger.warning(f"反射模式下拒绝非标准请求: {request_type}")
                    return None

            # 默认 Raft 全局模式
            # 模拟 Raft 日志复制过程
            if len(self.brain_buffer) < 1000:  # 边界检查
                self.brain_buffer.append(f"{request_type}:{payload}")
                return "QUEUED_FOR_CONSENSUS"
            else:
                logger.error("全局缓冲区溢出")
                return "SYSTEM_OVERLOAD"

    def _check_local_grid_failure(self) -> bool:
        """
        内部辅助函数：检查局部环境是否完全失效。
        
        Returns:
            bool: 如果局部也失效返回 True
        """
        # 简单模拟：如果没有任何邻居指标，或者平均丢包率极高
        if not self.metrics:
            return True
        
        avg_loss = sum(m.packet_loss for m in self.metrics.values()) / len(self.metrics)
        return avg_loss > 0.8

# 使用示例
if __name__ == "__main__":
    # 1. 配置节点
    config = NodeConfig(
        node_id="neuro_node_01",
        ip_address="192.168.1.100",
        port=8080,
        neighbors={"neuro_node_02", "neuro_node_03"},
        is_core_service=True
    )

    # 2. 初始化核心
    core = ReflexiveConsensusCore(config)
    
    # 3. 模拟正常请求
    print(f"响应: {core.process_request('write', 'data=100')}")

    # 4. 模拟网络分区/攻击发生
    attack_metrics = {
        "neuro_node_02": NetworkMetric(latency_ms=2000, packet_loss=0.9, active_nodes=0),
        "neuro_node_03": NetworkMetric(latency_ms=3000, packet_loss=0.95, active_nodes=0)
    }
    print("\n--- 模拟 DDoS 攻击 ---")
    core.monitor_network_status(attack_metrics)
    
    # 5. 此时系统应处于反射模式
    # 触发反射逻辑 (high_traffic)
    print(f"当前模式: {core.current_mode.name}")
    print(f"反射请求响应: {core.process_request('high_traffic', 'drop_packets')}")
    # 尝试普通写入 (应在反射模式下被拒绝或忽略)
    print(f"普通写入响应: {core.process_request('write', 'data=200')}")

    # 6. 模拟网络恢复
    print("\n--- 模拟网络复苏 ---")
    healthy_metrics = {
        "neuro_node_02": NetworkMetric(latency_ms=50, packet_loss=0.01, active_nodes=1),
        "neuro_node_03": NetworkMetric(latency_ms=60, packet_loss=0.01, active_nodes=1)
    }
    core.monitor_network_status(healthy_metrics)
    print(f"当前模式: {core.current_mode.name}")
    print(f"恢复后写入响应: {core.process_request('write', 'data=300')}")