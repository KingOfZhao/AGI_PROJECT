"""
模块名称: dynamic_fault_ontology_builder
功能描述: 针对工业海量日志数据流，构建动态故障模式本体论。
          该模块实现了从日志数据中自动归纳故障拓扑结构的核心算法，
          支持非线性和级联故障的识别。

领域: Industrial AI
作者: AGI System
版本: 1.0.0
"""

import logging
import networkx as nx
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
from collections import Counter

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LogEvent:
    """
    单条日志事件的数据结构。
    
    Attributes:
        timestamp (datetime): 事件发生时间。
        event_id (str): 事件唯一标识符。
        source_component (str): 事件发生的源组件。
        target_component (Optional[str]): 受影响的目标组件（如果是关联事件）。
        severity (str): 事件严重程度 (INFO, WARN, ERROR, CRITICAL).
        message (str): 原始日志信息。
        embeddings (Optional[List[float]]): 日志语义向量（用于相似度计算）。
    """
    timestamp: datetime
    event_id: str
    source_component: str
    severity: str
    message: str
    target_component: Optional[str] = None
    embeddings: Optional[List[float]] = None

@dataclass
class OntologyGraph:
    """
    封装故障本体论图结构。
    """
    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    node_metadata: Dict[str, Dict] = field(default_factory=dict)

    def add_edge_with_evidence(self, u: str, v: str, evidence: List[str]):
        """添加带证据的边"""
        if not self.graph.has_edge(u, v):
            self.graph.add_edge(u, v, weight=0, evidence_ids=[])
        
        self.graph[u][v]['weight'] += 1
        self.graph[u][v]['evidence_ids'].extend(evidence)

class DynamicFaultOntologyConstructor:
    """
    动态故障本体论构建器。
    
    该类负责从原始日志流中提取实体、关系，并构建反映故障传播路径的拓扑结构。
    它不依赖预设规则，而是通过时间窗口内的共现频率和语义相似度进行归纳。
    """

    def __init__(self, time_window_seconds: int = 60, min_co_occurrence: int = 3):
        """
        初始化构建器。

        Args:
            time_window_seconds (int): 判定级联故障的时间窗口大小。
            min_co_occurrence (int): 构建边的最小共现次数阈值。
        """
        self.time_window = time_window_seconds
        self.min_co_occurrence = min_co_occurrence
        self.ontology = OntologyGraph()
        logger.info(f"Initialized Constructor with window={time_window_seconds}s, threshold={min_co_occurrence}")

    def _validate_log_stream(self, log_stream: List[Dict]) -> bool:
        """
        辅助函数：验证输入数据流格式。
        
        Args:
            log_stream: 原始日志字典列表。
            
        Returns:
            bool: 数据是否有效。
            
        Raises:
            ValueError: 如果数据格式不正确。
        """
        if not isinstance(log_stream, list):
            raise ValueError("Input must be a list of dictionaries.")
        
        required_keys = {"timestamp", "source", "severity", "message"}
        for i, log in enumerate(log_stream):
            if not required_keys.issubset(log.keys()):
                logger.error(f"Missing keys in log entry index {i}. Required: {required_keys}")
                return False
        return True

    def _parse_logs(self, raw_logs: List[Dict]) -> List[LogEvent]:
        """
        辅助函数：将原始字典解析为LogEvent对象列表。
        """
        parsed_events = []
        for log in raw_logs:
            try:
                # 模拟解析过程，实际场景可能需要更复杂的正则提取
                event = LogEvent(
                    timestamp=pd.to_datetime(log['timestamp']),
                    event_id=log.get('id', str(hash(log['message']))),
                    source_component=log['source'],
                    target_component=log.get('target'), # 可选
                    severity=log['severity'],
                    message=log['message']
                )
                parsed_events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse log: {log}. Error: {e}")
        return parsed_events

    def extract_causal_candidates(self, log_stream: List[Dict]) -> nx.DiGraph:
        """
        核心函数 1: 提取因果候选关系。
        
        基于时间序列分析和组件交互频率，初步构建潜在的故障传播图。
        使用滑动窗口检测紧随其后的异常事件。
        
        Args:
            log_stream (List[Dict]): 原始日志数据流。
            
        Returns:
            nx.DiGraph: 包含潜在因果边的有向图。
        """
        if not self._validate_log_stream(log_stream):
            return nx.DiGraph()

        events = self._parse_logs(log_stream)
        # 按时间排序
        events.sort(key=lambda x: x.timestamp)
        
        candidate_graph = nx.DiGraph()
        # 仅关注警告和错误级别
        anomalies = [e for e in events if e.severity in ['WARN', 'ERROR', 'CRITICAL']]
        
        logger.info(f"Processing {len(anomalies)} anomaly events for causal extraction.")

        for i, event_a in enumerate(anomalies):
            source = event_a.source_component
            candidate_graph.add_node(source, type='component', last_seen=event_a.timestamp)
            
            # 向前查找窗口内的后续故障
            for j in range(i + 1, len(anomalies)):
                event_b = anomalies[j]
                time_diff = (event_b.timestamp - event_a.timestamp).total_seconds()
                
                if time_diff > self.time_window:
                    break # 超出时间窗口
                
                if time_diff == 0:
                    continue # 同时刻事件可能非因果

                target = event_b.source_component
                if source != target:
                    # 添加有向边：source -> target (故障传播方向)
                    if candidate_graph.has_edge(source, target):
                        candidate_graph[source][target]['weight'] += 1
                    else:
                        candidate_graph.add_edge(source, target, weight=1)
        
        return candidate_graph

    def build_dynamic_ontology(self, candidate_graph: nx.DiGraph) -> OntologyGraph:
        """
        核心函数 2: 构建并精炼动态故障本体论。
        
        对候选图进行剪枝、归纳和验证。过滤掉噪声（低频边），
        并识别关键故障传播路径（拓扑结构）。
        
        Args:
            candidate_graph (nx.DiGraph): extract_causal_candidates 生成的粗粒度图。
            
        Returns:
            OntologyGraph: 精炼后的本体论图对象。
        """
        logger.info("Refining candidate graph into Fault Ontology...")
        
        # 1. 过滤低频边（去噪）
        edges_to_remove = [
            (u, v) for u, v, d in candidate_graph.edges(data=True) 
            if d['weight'] < self.min_co_occurrence
        ]
        candidate_graph.remove_edges_from(edges_to_remove)
        logger.info(f"Removed {len(edges_to_remove)} noisy edges below threshold {self.min_co_occurrence}")

        # 2. 识别核心故障模式（利用PageRank或中心度）
        # 孤立节点移除
        candidate_graph.remove_nodes_from(list(nx.isolates(candidate_graph)))
        
        if candidate_graph.number_of_nodes() == 0:
            logger.warning("No significant fault patterns found.")
            return self.ontology

        # 计算节点重要性
        try:
            pagerank_scores = nx.pagerank(candidate_graph, weight='weight')
            for node, score in pagerank_scores.items():
                self.ontology.node_metadata[node] = {'criticality_score': score}
        except nx.NetworkXException:
            logger.error("Graph is not strongly connected enough for PageRank.")

        # 3. 赋予图结构
        self.ontology.graph = candidate_graph
        
        # 4. 归纳拓扑模式（例如：识别是星型、链式还是环形故障）
        self._identify_topology_patterns()
        
        return self.ontology

    def _identify_topology_patterns(self) -> str:
        """
        辅助函数：识别图的整体拓扑模式。
        
        Returns:
            str: 识别出的模式类型。
        """
        g = self.ontology.graph
        if g.number_of_edges() == 0:
            return "ISOLATED"

        # 简单的启发式规则判断拓扑类型
        try:
            cycles = list(nx.simple_cycles(g))
            if cycles:
                logger.info(f"Detected CYCLIC fault patterns (Feedback Loops): {len(cycles)} cycles.")
                return "CYCLIC_CASCADE"
            
            # 检查是否为链式
            degrees = [d for n, d in g.degree() if d > 1]
            if np.mean(degrees) < 1.5:
                logger.info("Detected LINEAR propagation chain.")
                return "LINEAR_CASCADE"
            
            logger.info("Detected COMPLEX network structure.")
            return "COMPLEX_NETWORK"
            
        except Exception as e:
            logger.error(f"Error identifying patterns: {e}")
            return "UNKNOWN"

# 使用示例
if __name__ == "__main__":
    # 模拟 Q1 获取的数据流
    mock_data = [
        {"timestamp": "2023-10-27 10:00:00", "source": "Sensor_A", "severity": "ERROR", "message": "Read failure"},
        {"timestamp": "2023-10-27 10:00:05", "source": "Controller_B", "severity": "WARN", "message": "Signal unstable"},
        {"timestamp": "2023-10-27 10:00:10", "source": "Actuator_C", "severity": "CRITICAL", "message": "Overload"},
        {"timestamp": "2023-10-27 10:00:12", "source": "Controller_B", "severity": "ERROR", "message": "Connection lost"},
        {"timestamp": "2023-10-27 10:05:00", "source": "System_Core", "severity": "INFO", "message": "Reset"},
        # 重复模式以增加权重
        {"timestamp": "2023-10-27 11:00:00", "source": "Sensor_A", "severity": "ERROR", "message": "Read failure"},
        {"timestamp": "2023-10-27 11:00:05", "source": "Controller_B", "severity": "WARN", "message": "Signal unstable"},
        {"timestamp": "2023-10-27 11:00:10", "source": "Actuator_C", "severity": "CRITICAL", "message": "Overload"},
    ]

    # 初始化构建器
    constructor = DynamicFaultOntologyConstructor(time_window_seconds=30, min_co_occurrence=2)
    
    # 1. 提取因果候选
    causal_graph = constructor.extract_causal_candidates(mock_data)
    
    # 2. 构建本体论
    final_ontology = constructor.build_dynamic_ontology(causal_graph)
    
    # 输出结果
    print("\n--- Fault Ontology Structure ---")
    print(f"Nodes: {final_ontology.graph.nodes}")
    print(f"Edges: {final_ontology.graph.edges(data=True)}")
    print(f"Metadata: {final_ontology.node_metadata}")