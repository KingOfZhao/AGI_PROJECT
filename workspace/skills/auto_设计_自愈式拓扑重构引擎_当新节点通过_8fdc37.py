"""
自愈式拓扑重构引擎

该模块实现了一个模拟科学范式转移的网络拓扑重构系统。当新节点（理论）通过证伪
推翻旧节点时，系统会自动进行结构重组，重新计算受影响节点的权重和连接方向，
而不仅仅是简单删除节点。

核心功能:
- 范式转移检测与处理
- 网络拓扑自动重构
- 节点权重动态重计算
- 连接关系智能调整

数据格式:
输入: JSON格式的网络结构数据
输出: 重构后的网络结构数据
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TopologicalReconstructionEngine")


class NodeType(Enum):
    """节点类型枚举"""
    THEORY = auto()      # 理论节点
    EVIDENCE = auto()    # 证据节点
    PARADIGM = auto()    # 范式节点
    OBSERVATION = auto() # 观测节点


class EdgeType(Enum):
    """边类型枚举"""
    SUPPORTS = auto()    # 支持关系
    REFUTES = auto()     # 反驳关系
    DERIVES = auto()     # 推导关系
    SUPERSEDES = auto()  # 取代关系


@dataclass
class Node:
    """网络节点数据结构"""
    id: str
    type: NodeType
    content: str
    confidence: float = 1.0
    influence: float = 1.0
    connections: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"节点置信度必须在0-1之间: {self.confidence}")
        if not 0 <= self.influence <= 10:
            raise ValueError(f"节点影响力必须在0-10之间: {self.influence}")


@dataclass
class Edge:
    """网络边数据结构"""
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    
    def __post_init__(self):
        """数据验证"""
        if not 0 <= self.weight <= 10:
            raise ValueError(f"边权重必须在0-10之间: {self.weight}")


class TopologicalReconstructionEngine:
    """
    自愈式拓扑重构引擎
    
    该引擎处理科学范式转移时的网络重构，模拟人类科学革命时的知识体系更新过程。
    
    属性:
        nodes (Dict[str, Node]): 节点字典
        edges (Dict[Tuple[str, str], Edge]): 边字典
        paradigms (Set[str]): 当前范式节点集合
        version (int): 网络版本号
        
    示例:
        >>> engine = TopologicalReconstructionEngine()
        >>> engine.add_node(Node("geo_centric", NodeType.PARADIGM, "地心说"))
        >>> engine.add_node(Node("helio_centric", NodeType.THEORY, "日心说"))
        >>> engine.add_edge(Edge("helio_centric", "geo_centric", EdgeType.REFUTES))
        >>> engine.reconstruct_network("geo_centric", "日心说通过观测证据证伪了地心说")
    """
    
    def __init__(self):
        """初始化引擎"""
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[Tuple[str, str], Edge] = {}
        self.paradigms: Set[str] = set()
        self.version: int = 1
        logger.info("初始化自愈式拓扑重构引擎")
    
    def add_node(self, node: Node) -> bool:
        """
        添加节点到网络
        
        参数:
            node (Node): 要添加的节点
            
        返回:
            bool: 是否成功添加
            
        异常:
            ValueError: 如果节点ID已存在
        """
        if node.id in self.nodes:
            error_msg = f"节点ID已存在: {node.id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.nodes[node.id] = node
        if node.type == NodeType.PARADIGM:
            self.paradigms.add(node.id)
            
        logger.info(f"添加节点: {node.id} (类型: {node.type.name})")
        return True
    
    def add_edge(self, edge: Edge) -> bool:
        """
        添加边到网络
        
        参数:
            edge (Edge): 要添加的边
            
        返回:
            bool: 是否成功添加
            
        异常:
            ValueError: 如果源节点或目标节点不存在
        """
        if edge.source not in self.nodes or edge.target not in self.nodes:
            error_msg = f"源节点或目标节点不存在: {edge.source} -> {edge.target}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        key = (edge.source, edge.target)
        self.edges[key] = edge
        self.nodes[edge.source].connections.add(edge.target)
        
        logger.info(f"添加边: {edge.source} --[{edge.type.name}]--> {edge.target}")
        return True
    
    def _calculate_node_influence(self, node_id: str, depth: int = 0) -> float:
        """
        辅助函数: 递归计算节点影响力
        
        参数:
            node_id (str): 节点ID
            depth (int): 递归深度，防止无限递归
            
        返回:
            float: 计算后的节点影响力
            
        异常:
            ValueError: 如果节点不存在
        """
        if node_id not in self.nodes:
            error_msg = f"节点不存在: {node_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if depth > 5:  # 限制递归深度
            return self.nodes[node_id].influence
            
        node = self.nodes[node_id]
        total_influence = node.confidence
        
        # 遍历所有连接
        for connected_id in node.connections:
            edge_key = (node_id, connected_id)
            if edge_key in self.edges:
                edge = self.edges[edge_key]
                
                # 根据边类型调整影响力
                if edge.type == EdgeType.SUPPORTS:
                    factor = 1.2 * edge.weight
                elif edge.type == EdgeType.REFUTES:
                    factor = 0.8 / edge.weight
                elif edge.type == EdgeType.SUPERSEDES:
                    factor = 1.5 * edge.weight
                else:
                    factor = 1.0
                
                # 递归计算连接节点的影响
                connected_influence = self._calculate_node_influence(connected_id, depth + 1)
                total_influence += factor * connected_influence * 0.1
                
        # 归一化影响力
        normalized_influence = min(10.0, max(0.1, math.log(total_influence + 1) * 2))
        return normalized_influence
    
    def _adjust_edge_weights(self, affected_nodes: Set[str]) -> None:
        """
        辅助函数: 调整受影响节点的边权重
        
        参数:
            affected_nodes (Set[str]): 受影响的节点ID集合
        """
        for node_id in affected_nodes:
            if node_id not in self.nodes:
                continue
                
            for connected_id in list(self.nodes[node_id].connections):
                edge_key = (node_id, connected_id)
                if edge_key in self.edges:
                    edge = self.edges[edge_key]
                    
                    # 根据节点状态调整权重
                    source_node = self.nodes[node_id]
                    target_node = self.nodes[connected_id]
                    
                    # 如果源节点或目标节点置信度下降，则减弱边权重
                    confidence_factor = (source_node.confidence + target_node.confidence) / 2
                    new_weight = edge.weight * confidence_factor
                    
                    # 更新权重
                    edge.weight = max(0.1, min(10.0, new_weight))
                    logger.debug(f"调整边权重: {edge_key} -> {edge.weight:.2f}")
    
    def reconstruct_network(self, refuted_paradigm: str, evidence: str) -> Dict:
        """
        核心函数: 重构网络拓扑
        
        当范式被证伪时，执行网络重构:
        1. 降低被证伪范式节点的置信度
        2. 识别受影响的节点
        3. 重新计算节点权重和影响力
        4. 调整连接方向和强度
        
        参数:
            refuted_paradigm (str): 被证伪的范式节点ID
            evidence (str): 证伪证据描述
            
        返回:
            Dict: 重构后的网络状态摘要
            
        异常:
            ValueError: 如果范式节点不存在
        """
        if refuted_paradigm not in self.nodes:
            error_msg = f"范式节点不存在: {refuted_paradigm}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        logger.info(f"开始范式转移重构: 证伪 {refuted_paradigm}，证据: {evidence}")
        
        # 1. 降低被证伪范式的置信度
        old_paradigm = self.nodes[refuted_paradigm]
        old_paradigm.confidence *= 0.1  # 大幅降低置信度
        self.paradigms.discard(refuted_paradigm)
        
        # 2. 识别受影响的节点
        affected_nodes = set()
        
        # 添加直接连接的节点
        for connected_id in old_paradigm.connections:
            affected_nodes.add(connected_id)
            
        # 递归添加间接连接的节点
        frontier = list(old_paradigm.connections)
        while frontier:
            current = frontier.pop()
            if current in affected_nodes:
                continue
                
            affected_nodes.add(current)
            if current in self.nodes:
                frontier.extend(self.nodes[current].connections)
        
        logger.info(f"受影响节点数: {len(affected_nodes)}")
        
        # 3. 重新计算受影响节点的影响力
        for node_id in affected_nodes:
            if node_id not in self.nodes:
                continue
                
            new_influence = self._calculate_node_influence(node_id)
            old_influence = self.nodes[node_id].influence
            self.nodes[node_id].influence = new_influence
            
            # 如果节点影响力显著下降，降低其置信度
            if new_influence < old_influence * 0.7:
                self.nodes[node_id].confidence *= 0.9
                logger.debug(f"降低节点置信度: {node_id} -> {self.nodes[node_id].confidence:.2f}")
        
        # 4. 调整边权重
        self._adjust_edge_weights(affected_nodes)
        
        # 5. 寻找可能的新范式
        new_paradigms = []
        for node_id, node in self.nodes.items():
            if node.type == NodeType.PARADIGM and node_id != refuted_paradigm:
                new_paradigms.append((node_id, node.influence))
            elif node.type == NodeType.THEORY and node.influence > 5.0:
                # 高影响力理论可能升级为范式
                new_paradigms.append((node_id, node.influence * 0.8))
        
        # 按影响力排序
        new_paradigms.sort(key=lambda x: x[1], reverse=True)
        
        # 更新版本号
        self.version += 1
        
        # 生成重构摘要
        summary = {
            "version": self.version,
            "refuted_paradigm": refuted_paradigm,
            "affected_nodes": len(affected_nodes),
            "top_new_paradigms": new_paradigms[:3],
            "network_health": self._calculate_network_health(),
            "timestamp": logging.Formatter.default_time_format
        }
        
        logger.info(f"网络重构完成: 版本 {self.version}, 健康度 {summary['network_health']:.2f}")
        return summary
    
    def _calculate_network_health(self) -> float:
        """
        辅助函数: 计算网络健康度
        
        网络健康度基于:
        - 节点平均置信度
        - 范式节点存在性
        - 边权重分布
        
        返回:
            float: 网络健康度 (0-1)
        """
        if not self.nodes:
            return 0.0
            
        # 节点置信度
        avg_confidence = sum(n.confidence for n in self.nodes.values()) / len(self.nodes)
        
        # 范式节点存在性
        paradigm_health = 1.0 if self.paradigms else 0.5
        
        # 边权重分布 (理想情况权重分布均匀)
        if self.edges:
            weights = [e.weight for e in self.edges.values()]
            avg_weight = sum(weights) / len(weights)
            variance = sum((w - avg_weight) ** 2 for w in weights) / len(weights)
            edge_health = 1.0 / (1.0 + math.sqrt(variance))
        else:
            edge_health = 0.1
        
        # 综合健康度
        health = avg_confidence * 0.4 + paradigm_health * 0.3 + edge_health * 0.3
        return max(0.0, min(1.0, health))
    
    def export_network(self) -> Dict:
        """
        导出网络结构
        
        返回:
            Dict: 可序列化的网络结构
        """
        nodes_data = [
            {
                "id": n.id,
                "type": n.type.name,
                "content": n.content,
                "confidence": n.confidence,
                "influence": n.influence,
                "connections": list(n.connections)
            }
            for n in self.nodes.values()
        ]
        
        edges_data = [
            {
                "source": e.source,
                "target": e.target,
                "type": e.type.name,
                "weight": e.weight
            }
            for e in self.edges.values()
        ]
        
        return {
            "version": self.version,
            "nodes": nodes_data,
            "edges": edges_data,
            "paradigms": list(self.paradigms),
            "health": self._calculate_network_health()
        }


# 使用示例
if __name__ == "__main__":
    try:
        # 创建引擎实例
        engine = TopologicalReconstructionEngine()
        
        # 构建初始网络 (模拟托勒密地心说体系)
        engine.add_node(Node("geo_centric", NodeType.PARADIGM, "地心说", confidence=0.95, influence=9.5))
        engine.add_node(Node("epicycles", NodeType.THEORY, "本轮-均轮模型", confidence=0.8, influence=8.0))
        engine.add_node(Node("celestial_spheres", NodeType.THEORY, "天球层理论", confidence=0.7, influence=7.0))
        
        # 添加连接关系
        engine.add_edge(Edge("epicycles", "geo_centric", EdgeType.SUPPORTS, 8.0))
        engine.add_edge(Edge("celestial_spheres", "geo_centric", EdgeType.SUPPORTS, 6.0))
        
        # 添加新理论 (哥白尼日心说)
        engine.add_node(Node("helio_centric", NodeType.THEORY, "日心说", confidence=0.9, influence=5.0))
        engine.add_node(Node("planetary_motion", NodeType.THEORY, "行星运动定律", confidence=0.85, influence=6.0))
        
        # 添加证伪关系
        engine.add_edge(Edge("helio_centric", "geo_centric", EdgeType.REFUTES, 9.0))
        engine.add_edge(Edge("planetary_motion", "helio_centric", EdgeType.SUPPORTS, 7.0))
        
        # 执行范式转移重构
        result = engine.reconstruct_network(
            "geo_centric",
            "日心说通过金星相位和木星卫星的观测证据证伪了地心说"
        )
        
        # 输出结果
        print(f"网络重构完成 (版本 {result['version']})")
        print(f"受影响节点数: {result['affected_nodes']}")
        print(f"网络健康度: {result['network_health']:.2f}")
        print(f"潜在新范式: {result['top_new_paradigms']}")
        
        # 导出网络
        network_data = engine.export_network()
        print("\n导出网络结构:")
        print(f"节点数: {len(network_data['nodes'])}")
        print(f"边数: {len(network_data['edges'])}")
        
    except Exception as e:
        logger.error(f"示例运行失败: {str(e)}", exc_info=True)
        raise