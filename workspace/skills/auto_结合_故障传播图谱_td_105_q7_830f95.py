"""
高级AGI技能模块：基于故障传播图谱与生物免疫熔断的自愈系统

该模块实现了一个融合物理世界感知、逻辑推理与生物免疫机制的复杂系统。
核心功能包括：
1. 感知符号化：将物理震动信号转化为系统可理解的符号特征。
2. 故障传播预测：基于图算法预测潜在故障在网络中的扩散路径。
3. 生物毒性熔断：模拟生物免疫系统，对检测到的“病原体”（严重故障）
   实施隔离或清除，并在风险降低后尝试自我修复。

版本: 1.0.0
作者: AGI System Core
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AGI_Self_Healing_System")


class SystemState(Enum):
    """系统节点的健康状态枚举"""
    HEALTHY = 0
    WARNING = 1
    CRITICAL = 2
    ISOLATED = 3  # 被熔断隔离


@dataclass
class PhysicalSignal:
    """物理世界感知信号数据结构"""
    timestamp: float
    amplitude: float  # 震动幅度
    frequency: float  # 频率
    source_id: str    # 传感器ID


@dataclass
class SystemNode:
    """系统逻辑节点或设备节点"""
    node_id: str
    state: SystemState = SystemState.HEALTHY
    connections: Set[str] = field(default_factory=set)
    toxicity_level: float = 0.0  # 累积的毒性/异常程度
    load: float = 0.0  # 负载


class FaultPropagationGraph:
    """
    管理设备网络的拓扑结构及故障传播逻辑。
    对应技能：故障传播图谱 (td_105_Q7_3_4162)
    """

    def __init__(self):
        self.nodes: Dict[str, SystemNode] = {}
        logger.info("Fault Propagation Graph initialized.")

    def add_node(self, node_id: str, connections: Optional[List[str]] = None):
        """添加节点并建立连接"""
        if node_id in self.nodes:
            logger.warning(f"Node {node_id} already exists.")
            return

        node = SystemNode(node_id=node_id)
        if connections:
            node.connections.update(connections)
        
        self.nodes[node_id] = node
        logger.debug(f"Node {node_id} added with connections: {connections}")

    def predict_propagation_path(self, source_id: str) -> List[str]:
        """
        从源节点预测故障传播路径（基于BFS的简易模拟）。
        
        Args:
            source_id: 故障起始节点ID
            
        Returns:
            预测会受影响的节点ID列表（按传播顺序）
        """
        if source_id not in self.nodes:
            logger.error(f"Source node {source_id} not found.")
            return []

        path = []
        visited = set()
        queue = [source_id]

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            
            visited.add(current_id)
            current_node = self.nodes[current_id]
            
            # 假设故障会传播给状态不是 ISOLATED 的节点
            if current_node.state != SystemState.ISOLATED:
                path.append(current_id)
                
                # 在实际场景中，这里会有复杂的概率计算
                for neighbor_id in current_node.connections:
                    if neighbor_id not in visited and self.nodes[neighbor_id].state != SystemState.ISOLATED:
                        queue.append(neighbor_id)
        
        logger.info(f"Predicted propagation path from {source_id}: {path}")
        return path


class BioFuse:
    """
    生物毒性熔断器。
    对应技能：生物毒性熔断器 (ho_106_O1_4121)
    """

    def __init__(self, threshold_critical: float = 0.8, threshold_lethal: float = 0.95):
        self.threshold_critical = threshold_critical
        self.threshold_lethal = threshold_lethal
        logger.info(f"BioFuse initialized with Critical: {threshold_critical}, Lethal: {threshold_lethal}")

    def evaluate_toxicity(self, node: SystemNode, signal_symbol: Dict) -> float:
        """
        根据输入信号计算节点的毒性等级。
        
        Args:
            node: 系统节点
            signal_symbol: 经过符号化处理的信号特征
            
        Returns:
            更新后的毒性等级 (0.0 - 1.0)
        """
        # 模拟毒性累积逻辑：异常频率和幅度增加毒性
        base_toxicity = node.toxicity_level
        anomaly_score = signal_symbol.get('anomaly_score', 0.0)
        
        # 衰减因子，模拟系统自愈能力
        decay = 0.1 
        new_toxicity = max(0, (base_toxicity - decay) + anomaly_score * 0.5)
        
        return min(new_toxicity, 1.0)

    def trigger_fuse(self, node: SystemNode) -> bool:
        """
        决定是否触发熔断机制。
        
        Returns:
            bool: True 如果触发了熔断/隔离，否则 False
        """
        if node.toxicity_level >= self.threshold_lethal:
            logger.critical(f"BIO-FUSE TRIGGERED! Node {node.node_id} is LETHAL. Isolating...")
            node.state = SystemState.ISOLATED
            return True
        
        if node.toxicity_level >= self.threshold_critical:
            logger.warning(f"Node {node.node_id} in CRITICAL state. Alerting immune system.")
            node.state = SystemState.CRITICAL
            return False
            
        node.state = SystemState.HEALTHY if node.toxicity_level < 0.3 else SystemState.WARNING
        return False


def perceptual_symbolization(signal: PhysicalSignal) -> Dict:
    """
    将物理信号转化为符号化特征。
    对应技能：感知符号化 (td_105_Q1_3_4162)
    
    Args:
        signal: 原始物理信号
        
    Returns:
        包含符号特征的字典，例如 {'anomaly_score': float, 'pattern_type': str}
    """
    # 边界检查
    if signal.amplitude < 0 or signal.frequency < 0:
        raise ValueError("Signal amplitude and frequency must be non-negative.")
        
    logger.debug(f"Symbolizing signal from {signal.source_id}")
    
    # 简单的规则引擎：模拟特征提取
    # 在真实AGI中，这里可能是神经网络嵌入提取
    symbol = {
        "source": signal.source_id,
        "anomaly_score": 0.0,
        "pattern_type": "normal"
    }
    
    # 规则1: 高频震动视为异常
    if signal.frequency > 500.0:
        symbol['anomaly_score'] = 0.7
        symbol['pattern_type'] = "high_freq_vibration"
    
    # 规则2: 极端幅度视为冲击
    if signal.amplitude > 10.0:
        symbol['anomaly_score'] = 0.9
        symbol['pattern_type'] = "physical_shock"
        
    return symbol


class SelfHealingSystem:
    """
    整合所有组件的主控制器。
    """

    def __init__(self):
        self.graph = FaultPropagationGraph()
        self.fuse = BioFuse()
        logger.info("SelfHealingSystem online.")

    def setup_network(self, topology: Dict[str, List[str]]):
        """初始化网络拓扑"""
        for node_id, conns in topology.items():
            self.graph.add_node(node_id, conns)

    def process_signal(self, signal: PhysicalSignal):
        """
        处理单个信号的主循环。
        """
        try:
            # 1. 感知符号化
            symbol = perceptual_symbolization(signal)
            
            if symbol['anomaly_score'] > 0.1:
                # 2. 获取对应节点
                node = self.graph.nodes.get(signal.source_id)
                if not node:
                    logger.error(f"Signal from unknown node: {signal.source_id}")
                    return

                # 3. 更新毒性
                node.toxicity_level = self.fuse.evaluate_toxicity(node, symbol)
                
                # 4. 检查熔断
                is_isolated = self.fuse.trigger_fuse(node)
                
                # 5. 如果熔断，阻断传播；否则预测传播
                if is_isolated:
                    # 移除连接以阻断故障传播（图层面操作）
                    # 注意：实际可能只是标记状态，这里为了演示清除连接
                    logger.info(f"Severing connections for isolated node {node.node_id}")
                    # node.connections.clear() # 这会修改原图，需谨慎，此处仅作逻辑示意
                else:
                    # 预测如果此节点失效，影响范围多大
                    path = self.graph.predict_propagation_path(node.node_id)
                    if len(path) > 3:
                        logger.warning(f"Potential cascade failure detected! Path length: {len(path)}")

        except Exception as e:
            logger.error(f"Error processing signal: {e}", exc_info=True)


# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 1. 实例化系统
    system = SelfHealingSystem()
    
    # 2. 定义网络拓扑 (A->B->C->D)
    # A是传感器节点
    network_topology = {
        "sensor_A": ["controller_B"],
        "controller_B": ["actuator_C", "db_D"],
        "actuator_C": [],
        "db_D": []
    }
    system.setup_network(network_topology)
    
    # 3. 模拟正常信号
    normal_signal = PhysicalSignal(
        timestamp=time.time(),
        amplitude=0.5,
        frequency=50.0,
        source_id="sensor_A"
    )
    print("\n--- Processing Normal Signal ---")
    system.process_signal(normal_signal)
    
    # 4. 模拟异常信号（物理冲击）
    # 持续发送异常信号以触发熔断
    print("\n--- Processing Anomalous Signals (Shock) ---")
    for _ in range(5):
        shock_signal = PhysicalSignal(
            timestamp=time.time(),
            amplitude=12.0,  # High amplitude
            frequency=600.0, # High frequency
            source_id="sensor_A"
        )
        system.process_signal(shock_signal)
        time.sleep(0.1)
        
    # 5. 检查节点状态
    node_a = system.graph.nodes["sensor_A"]
    print(f"\nFinal State of Sensor A: {node_a.state.name}")
    print(f"Toxicity Level: {node_a.toxicity_level}")