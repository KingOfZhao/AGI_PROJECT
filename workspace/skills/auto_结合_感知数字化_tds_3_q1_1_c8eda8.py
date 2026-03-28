"""
Module: auto_结合_感知数字化_tds_3_q1_1_c8eda8
Description: 构建 AGI 系统的高级数字孪生体模块。
             整合实时感知数据（TDS）、匠人直觉（HO）与动态本体（KG），
             实现从数据监测到认知决策的跨越。
Author: Senior Python Engineer (AGI System Core)
Date: 2023-10-27
Version: 1.0.0
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union
from enum import Enum

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DigitalTwin_AGI")


class HealthStatus(Enum):
    """设备健康状态枚举"""
    HEALTHY = "Healthy"
    WARNING = "Warning"
    CRITICAL = "Critical"
    UNKNOWN = "Unknown"


@dataclass
class SensorReading:
    """感知数字化流(TDS)数据结构"""
    sensor_id: str
    value: float
    unit: str
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.value, (int, float)):
            raise ValueError(f"Sensor value must be numeric, got {type(self.value)}")


@dataclass
class IntuitionModel:
    """匠人直觉模拟器(HO)决策边界模型"""
    parameter: str
    baseline: float
    warning_threshold: float  # 相对于基线的百分比偏差
    critical_threshold: float # 相对于基线的百分比偏差
    trend_sensitivity: float  # 趋势敏感度因子


@dataclass
class KnowledgeEdge:
    """动态本体映射器(KG)中的关系边"""
    source: str
    target: str
    relation_type: str  # e.g., "FUELS", "DRIVES", "CONTROLS"


class DigitalTwinCore:
    """
    数字孪生核心类：整合感知、直觉与知识图谱。
    实现故障推演与健康趋势预测。
    """

    def __init__(self, 
                 kg_edges: List[KnowledgeEdge], 
                 intuition_models: Dict[str, IntuitionModel]):
        """
        初始化数字孪生体。

        Args:
            kg_edges (List[KnowledgeEdge]): P&ID逻辑连接关系列表
            intuition_models (Dict[str, IntuitionModel]): 针对关键参数的匠人直觉模型
        """
        self.kg_graph = self._build_adjacency_list(kg_edges)
        self.models = intuition_models
        self.state_cache: Dict[str, SensorReading] = {}
        self.health_assessment: Dict[str, HealthStatus] = {}
        
        logger.info(f"Digital Twin initialized with {len(self.kg_graph)} nodes and {len(self.models)} models.")

    def _build_adjacency_list(self, edges: List[KnowledgeEdge]) -> Dict[str, List[str]]:
        """
        辅助函数：将边列表转换为邻接表以表示P&ID逻辑图。

        Args:
            edges (List[KnowledgeEdge]): 原始边列表

        Returns:
            Dict[str, List[str]]: 邻接表表示的图结构
        """
        graph: Dict[str, List[str]] = {}
        for edge in edges:
            if edge.source not in graph:
                graph[edge.source] = []
            graph[edge.source].append(edge.target)
            
            # 确保孤立节点也被记录
            if edge.target not in graph:
                graph[edge.target] = []
        return graph

    def ingest_realtime_data(self, data_stream: List[SensorReading]) -> Dict[str, HealthStatus]:
        """
        核心函数1：接收实时感知数据并更新孪生体状态。
        结合匠人直觉模型判断当前健康状态。

        Args:
            data_stream (List[SensorReading]): 一批实时传感器读数

        Returns:
            Dict[str, HealthStatus]: 更新后的各组件健康状态映射
        
        Raises:
            ValueError: 如果输入数据流为空
        """
        if not data_stream:
            logger.warning("Ingested empty data stream.")
            raise ValueError("Data stream cannot be empty")

        logger.debug(f"Processing {len(data_stream)} sensor readings...")
        
        for reading in data_stream:
            self.state_cache[reading.sensor_id] = reading
            
            # 获取对应的直觉模型
            model = self.models.get(reading.sensor_id)
            if model:
                deviation = abs(reading.value - model.baseline) / model.baseline
                
                if deviation >= model.critical_threshold:
                    self.health_assessment[reading.sensor_id] = HealthStatus.CRITICAL
                    logger.error(f"CRITICAL detected on {reading.sensor_id}: Value {reading.value}, Deviation {deviation:.2%}")
                elif deviation >= model.warning_threshold:
                    self.health_assessment[reading.sensor_id] = HealthStatus.WARNING
                    logger.warning(f"WARNING detected on {reading.sensor_id}: Value {reading.value}, Deviation {deviation:.2%}")
                else:
                    self.health_assessment[reading.sensor_id] = HealthStatus.HEALTHY
            else:
                # 无特定模型，标记为未知或根据通用规则处理
                self.health_assessment[reading.sensor_id] = HealthStatus.UNKNOWN

        return self.health_assessment

    def propagate_fault_logic(self, root_cause_id: str, depth: int = 3) -> Set[str]:
        """
        核心函数2：基于P&ID逻辑(知识图谱)推演故障传播路径。
        模拟故障在系统逻辑连接中的扩散。

        Args:
            root_cause_id (str): 初始发生故障的组件ID
            depth (int): 推演的深度层级

        Returns:
            Set[str]: 可能受到故障影响的组件ID集合
        
        Example:
            >>> twin.propagate_fault_logic("PUMP_01", depth=2)
            {'VALVE_01', 'HEAT_EXCHANGER_02'}
        """
        if root_cause_id not in self.kg_graph:
            logger.error(f"Root cause ID {root_cause_id} not found in Knowledge Graph.")
            return set()

        affected_nodes: Set[str] = set()
        queue = [(root_cause_id, 0)]
        
        logger.info(f"Starting fault propagation simulation from {root_cause_id}...")

        while queue:
            current_node, current_depth = queue.pop(0)
            
            if current_depth >= depth:
                continue

            # 获取下游节点
            neighbors = self.kg_graph.get(current_node, [])
            for neighbor in neighbors:
                if neighbor not in affected_nodes:
                    affected_nodes.add(neighbor)
                    logger.info(f"Potential impact detected: {neighbor} (via {current_node})")
                    queue.append((neighbor, current_depth + 1))
        
        return affected_nodes

    def get_system_overview(self) -> Dict[str, Union[float, str]]:
        """
        辅助函数：生成当前系统的综合摘要。
        
        Returns:
            Dict: 包含关键指标的摘要
        """
        critical_count = sum(1 for s in self.health_assessment.values() if s == HealthStatus.CRITICAL)
        return {
            "total_sensors_tracked": len(self.state_cache),
            "critical_alerts": critical_count,
            "system_status": "OPERATIONAL" if critical_count == 0 else "AT_RISK"
        }


# 使用示例
if __name__ == "__main__":
    try:
        # 1. 定义P&ID知识图谱连接 (模拟 tds_3_Q2_1 动态本体)
        pid_connections = [
            KnowledgeEdge("PUMP_01", "PIPE_01", "FUELS"),
            KnowledgeEdge("PIPE_01", "VALVE_01", "FLOWS_TO"),
            KnowledgeEdge("VALVE_01", "TANK_02", "FILLS"),
            KnowledgeEdge("SENSOR_TEMP_01", "TANK_02", "MONITORS")
        ]

        # 2. 定义匠人直觉模型 (模拟 ho_3_O2_7378 决策边界)
        intuition_rules = {
            "SENSOR_TEMP_01": IntuitionModel(
                parameter="Temperature",
                baseline=90.0,
                warning_threshold=0.10,  # +/- 10%
                critical_threshold=0.20,  # +/- 20%
                trend_sensitivity=0.5
            )
        }

        # 3. 实例化数字孪生体
        twin = DigitalTwinCore(kg_edges=pid_connections, intuition_models=intuition_rules)

        # 4. 模拟实时数据流 (模拟 tds_3_Q1_1 感知数字化)
        # 模拟一个高温异常
        mock_data = [
            SensorReading("SENSOR_TEMP_01", 110.5, "C"), # 异常值，偏离基线 > 20%
            SensorReading("PUMP_01", 1200.0, "RPM")
        ]

        # 5. 更新状态
        status_map = twin.ingest_realtime_data(mock_data)
        print(f"Current Status: {status_map.get('SENSOR_TEMP_01')}")

        # 6. 如果检测到异常，推演故障路径
        if status_map.get("SENSOR_TEMP_01") == HealthStatus.CRITICAL:
            print("Simulating fault propagation due to critical temperature...")
            # 注意：这里需要根据实际业务逻辑映射 Sensor 到 Equipment
            # 假设 SENSOR_TEMP_01 监控的是 TANK_02，或者触发相关的逻辑链
            # 这里为了演示图遍历，我们直接从 PIPE_01 开始推演
            impact = twin.propagate_fault_logic("PIPE_01", depth=2)
            print(f"Potential Impact Set: {impact}")

        # 7. 获取系统概览
        print(f"System Overview: {twin.get_system_overview()}")

    except Exception as e:
        logger.critical(f"System crash: {str(e)}", exc_info=True)