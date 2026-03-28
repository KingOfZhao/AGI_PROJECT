"""
系统脆弱性拓扑分析仪

将市场份额视为'生态位空间'，将资金流视为'能量流'。
不仅监测财富集中度，还要监测'单一物种依赖度'。
如果一个经济生态系统中，某个巨头企业（优势物种）倒塌会导致整个网络能量输送中断（级联灭绝），
则系统评级为脆弱。用于反垄断分析或供应链风险管理，识别隐形结构性风险。
"""

import networkx as nx
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class NodeMetrics:
    """存储单一节点的风险评估指标"""
    node_id: str
    market_share: float  # 生态位空间 (0.0 to 1.0)
    dependency_score: float  # 单一物种依赖度
    is_keystone_species: bool = False  # 是否为关键物种（巨头）
    downstream_impact: float = 0.0  # 级联灭绝影响范围

@dataclass
class SystemReport:
    """系统整体脆弱性报告"""
    system_fragility_index: float  # 系统脆弱性指数 (0.0-1.0)
    keystone_species: List[str]  # 关键物种列表
    cascade_risk_zones: List[str]  # 高风险传导区域
    rating: str  # 系统评级
    details: Dict = field(default_factory=dict)

class SystemVulnerabilityAnalyzer:
    """
    系统脆弱性拓扑分析仪
    
    使用生态学隐喻分析经济系统的结构稳定性。
    将资金流视为能量流，市场份额视为生态位，识别可能导致级联灭绝的关键节点。
    
    Attributes:
        graph (nx.DiGraph): 有向图，表示经济生态系统
        tolerance (float): 容错阈值，用于判断系统崩溃
    """
    
    def __init__(self, tolerance: float = 0.2):
        """
        初始化分析仪
        
        Args:
            tolerance (float): 系统崩溃阈值。当网络整体流量低于此比例时视为崩溃。
        """
        self.graph = nx.DiGraph()
        self.tolerance = tolerance
        self._node_metrics: Dict[str, NodeMetrics] = {}
        logger.info("System Vulnerability Analyzer initialized with tolerance: %.2f", tolerance)

    def _validate_input_data(self, nodes: List[Dict], edges: List[Dict]) -> bool:
        """验证输入数据的完整性和合法性"""
        if not nodes or not isinstance(nodes, list):
            logger.error("Invalid nodes data: must be a non-empty list")
            raise ValueError("Nodes data must be a non-empty list")
            
        required_node_keys = {'id', 'market_share'}
        for node in nodes:
            if not required_node_keys.issubset(node.keys()):
                logger.error("Node missing required keys: %s", node)
                raise ValueError(f"Node {node.get('id', 'UNKNOWN')} missing required keys")
            if not (0 <= node['market_share'] <= 1):
                logger.error("Invalid market share for node %s", node['id'])
                raise ValueError(f"Market share for {node['id']} must be between 0 and 1")
                
        logger.debug("Input data validation passed.")
        return True

    def build_ecosystem(self, nodes: List[Dict], edges: List[Dict]) -> None:
        """
        构建经济生态系统网络
        
        Args:
            nodes (List[Dict]): 节点列表，包含id和market_share
            edges (List[Dict]): 边列表，包含source, target, weight(资金流/能量)
            
        Example Input:
            nodes = [{'id': 'Corp_A', 'market_share': 0.4}, ...]
            edges = [{'source': 'Corp_A', 'target': 'SME_B', 'weight': 1000}, ...]
        """
        try:
            self._validate_input_data(nodes, edges)
            
            for node in nodes:
                self.graph.add_node(node['id'], market_share=node['market_share'])
                # 初始化指标
                self._node_metrics[node['id']] = NodeMetrics(
                    node_id=node['id'],
                    market_share=node['market_share'],
                    dependency_score=0.0
                )
            
            for edge in edges:
                u, v, w = edge['source'], edge['target'], edge.get('weight', 1.0)
                if u in self.graph and v in self.graph:
                    self.graph.add_edge(u, v, weight=w)
                else:
                    logger.warning(f"Edge ({u}->{v}) contains undefined nodes, skipping.")
                    
            logger.info(f"Ecosystem built with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")
            
        except Exception as e:
            logger.exception("Failed to build ecosystem")
            raise

    def _calculate_dependency_scores(self) -> None:
        """
        辅助函数：计算单一物种依赖度
        
        定义：节点i对节点j的依赖度 = 流入j的能量中来自i的比例
        这里计算节点i作为供应方的重要性
        """
        if not self.graph:
            return

        for node_id in self.graph.nodes():
            # 获取该节点流出的总能量（资金）
            out_flow = sum(data['weight'] for _, _, data in self.graph.out_edges(node_id, data=True))
            total_system_flow = sum(data['weight'] for _, _, data in self.graph.edges(data=True))
            
            if total_system_flow > 0:
                # 能量控制力：该节点控制的系统流量比例
                self._node_metrics[node_id].dependency_score = out_flow / total_system_flow
            else:
                self._node_metrics[node_id].dependency_score = 0.0
                
            # 标记关键物种：市场份额大或能量控制力强
            if (self._node_metrics[node_id].market_share > 0.2 or 
                self._node_metrics[node_id].dependency_score > 0.3):
                self._node_metrics[node_id].is_keystone_species = True

    def simulate_species_extinction(self, target_node: str) -> Tuple[float, Set[str]]:
        """
        核心函数：模拟单一物种灭绝（移除节点）导致的级联效应
        
        Args:
            target_node (str): 要移除的节点ID
            
        Returns:
            Tuple[float, Set[str]]: 
                - 影响因子（剩余系统能量占比）
                - 受影响的节点集合（级联灭绝物种）
        """
        if not self.graph.has_node(target_node):
            logger.warning(f"Node {target_node} not in graph.")
            return 1.0, set()

        # 复制图以避免破坏原数据
        G_sim = self.graph.copy()
        initial_energy = sum(d['weight'] for u, v, d in G_sim.edges(data=True))
        
        if initial_energy == 0:
            return 1.0, set()

        # 1. 初始灭绝：移除目标节点
        affected_nodes = {target_node}
        nodes_to_remove = {target_node}
        
        # 迭代模拟级联效应
        # 规则：如果一个节点的所有入流（能量来源）都被切断，该节点也会灭绝
        iteration = 0
        while nodes_to_remove:
            iteration += 1
            current_removals = set()
            
            for node in list(G_sim.nodes()):
                if node in affected_nodes:
                    continue
                
                # 检查入度（能量来源）
                predecessors = list(G_sim.predecessors(node))
                if not predecessors:
                    continue # 没有依赖的节点（根节点）不受影响
                    
                # 检查是否所有来源都已失效
                active_sources = [p for p in predecessors if p not in affected_nodes]
                
                if not active_sources:
                    current_removals.add(node)
                    
            if not current_removals:
                break
                
            affected_nodes.update(current_removals)
            # 注意：在NetworkX中移除节点会自动移除相关的边
            
        # 计算剩余能量
        # 创建排除受影响节点后的剩余图
        remaining_nodes = [n for n in G_sim.nodes() if n not in affected_nodes]
        G_remaining = G_sim.subgraph(remaining_nodes)
        remaining_energy = sum(d['weight'] for u, v, d in G_remaining.edges(data=True))
        
        impact_factor = remaining_energy / initial_energy
        logger.info(f"Extinction simulation for {target_node}: Impact Factor {impact_factor:.2f}, Affected {len(affected_nodes)} nodes")
        
        return impact_factor, affected_nodes

    def analyze_system_vulnerability(self) -> SystemReport:
        """
        核心函数：生成系统脆弱性分析报告
        
        Returns:
            SystemReport: 包含风险评级和关键物种的完整报告
        """
        if not self.graph:
            raise ValueError("Graph is empty. Call build_ecosystem first.")

        self._calculate_dependency_scores()
        
        keystone_species = []
        high_risk_nodes = []
        total_cascade_impact = 0.0
        
        nodes = list(self.graph.nodes())
        for node in nodes:
            if self._node_metrics[node].is_keystone_species:
                keystone_species.append(node)
                
            # 对每个关键物种进行灭绝模拟
            impact, affected = self.simulate_species_extinction(node)
            
            # 如果移除该节点导致系统崩溃（能量低于阈值）
            if impact < (1.0 - self.tolerance):
                high_risk_nodes.append(node)
                total_cascade_impact += (1.0 - impact)
                
        # 计算系统综合脆弱性指数
        # 基于高影响节点的数量和其造成的破坏程度
        if len(nodes) > 0:
            fragility_index = min(1.0, total_cascade_impact / len(nodes))
        else:
            fragility_index = 0.0
            
        # 评级逻辑
        if fragility_index > 0.7:
            rating = "CRITICAL (极易发生级联崩溃)"
        elif fragility_index > 0.4:
            rating = "FRAGILE (存在隐形结构性风险)"
        elif fragility_index > 0.1:
            rating = "STABLE (局部风险可控)"
        else:
            rating = "ROBUST (系统弹性强)"
            
        report = SystemReport(
            system_fragility_index=round(fragility_index, 4),
            keystone_species=keystone_species,
            cascade_risk_zones=high_risk_nodes,
            rating=rating,
            details={
                "total_nodes": len(nodes),
                "tolerance_setting": self.tolerance,
                "analysis_type": "Ecological Topology Analysis"
            }
        )
        
        logger.info(f"Analysis Complete. Rating: {rating}")
        return report

# Usage Example
if __name__ == "__main__":
    # 1. 构造模拟数据：一个过度依赖单一巨头的供应链
    # Node A: 巨头企业 (市场份额 0.6)
    # Node B, C: 中间供应商
    # Node D, E, F: 下游小企业，主要依赖 A 的能量
    mock_nodes = [
        {'id': 'MegaCorp_A', 'market_share': 0.6},
        {'id': 'Supplier_B', 'market_share': 0.15},
        {'id': 'Supplier_C', 'market_share': 0.15},
        {'id': 'Retailer_D', 'market_share': 0.03},
        {'id': 'Retailer_E', 'market_share': 0.03},
        {'id': 'Retailer_F', 'market_share': 0.04},
    ]
    
    # B依赖A，D依赖B，E依赖B，C依赖A，F依赖C
    # 形成一个 A -> B -> D/E 和 A -> C -> F 的结构
    mock_edges = [
        {'source': 'MegaCorp_A', 'target': 'Supplier_B', 'weight': 500},
        {'source': 'MegaCorp_A', 'target': 'Supplier_C', 'weight': 500},
        {'source': 'Supplier_B', 'target': 'Retailer_D', 'weight': 200},
        {'source': 'Supplier_B', 'target': 'Retailer_E', 'weight': 200},
        {'source': 'Supplier_C', 'target': 'Retailer_F', 'weight': 200},
        # 假设还有一些内部流转
        {'source': 'Retailer_D', 'target': 'Retailer_E', 'weight': 50}, 
    ]
    
    try:
        analyzer = SystemVulnerabilityAnalyzer(tolerance=0.3)
        analyzer.build_ecosystem(mock_nodes, mock_edges)
        
        # 执行分析
        report = analyzer.analyze_system_vulnerability()
        
        print("\n--- System Vulnerability Report ---")
        print(f"Rating: {report.rating}")
        print(f"Fragility Index: {report.system_fragility_index}")
        print(f"Keystone Species (Dominant Players): {report.keystone_species}")
        print(f"Cascade Risk Zones (Single Points of Failure): {report.cascade_risk_zones}")
        
    except Exception as e:
        logger.error(f"An error occurred during execution: {e}")